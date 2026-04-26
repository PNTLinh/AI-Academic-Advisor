"""Utilities for regulation PDF ingestion and chunk generation.

This module implements a complete local pipeline:
1. Extract text from PDF pages
2. Chunk by legal structure (Dieu/Chuong/Muc), fallback to sliding window
3. Attach stable metadata (page range, title, hash, token estimate)
4. Save chunks for downstream embedding/vector indexing

Note:
- This module prepares data for vector databases but does not force any
  specific vector backend.
- A lightweight keyword index is also provided for local debugging.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import logging
import math
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# Detect legal-style section headers (Vietnamese regulation format).
LEGAL_SECTION_PATTERN = re.compile(
	r"(?:^|\n)"
	r"(?:Dieu\s+\d+|Chuong\s+[IVXLCDM\d]+|Muc\s+\d+|Phan\s+[IVXLCDM\d]+|Khoan\s+\d+)",
	re.IGNORECASE | re.MULTILINE,
)


@dataclass
class ChunkConfig:
	"""Config for chunking behavior."""

	chunk_size_chars: int = 1500
	overlap_chars: int = 200
	min_chunk_chars: int = 120
	prefer_structure_split: bool = True


@dataclass
class PageText:
	"""Extracted text for one PDF page."""

	page_number: int
	content: str


@dataclass
class ChunkRecord:
	"""Normalized output schema for a chunk."""

	chunk_id: str
	source_file: str
	page_start: int
	page_end: int
	title: str
	section_title: str
	char_start: int
	char_end: int
	token_estimate: int
	content_hash: str
	content: str


@dataclass
class EmbeddingConfig:
	"""Config for embedding generation.

	provider:
		- "auto": use external provider when API key is available, otherwise local model
		- "external": force external provider
		- "local": force local sentence-transformers model
	"""

	provider: str = "auto"
	api_key: str | None = None
	external_model: str = "text-embedding-3-small"
	local_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
	batch_size: int = 64


def _normalize_text(text: str) -> str:
	"""Normalize whitespace but preserve paragraphs."""
	lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
	# Keep non-empty lines and merge with newline to preserve structure.
	return "\n".join(line for line in lines if line)


def _estimate_tokens(text: str) -> int:
	"""Rough token estimate for planning context windows."""
	return max(1, math.ceil(len(text) / 4))


def extract_pdf_text(pdf_path: str | Path) -> dict[str, Any]:
	"""Read PDF and return page-level text + combined full_text.

	Raises:
		FileNotFoundError: If file does not exist.
		ValueError: If PDF contains no extractable text.
	"""
	from PyPDF2 import PdfReader

	path = Path(pdf_path)
	if not path.exists():
		raise FileNotFoundError(f"PDF not found: {path}")

	reader = PdfReader(str(path))
	pages: list[PageText] = []
	for i, page in enumerate(reader.pages, start=1):
		raw_text = page.extract_text() or ""
		page_text = _normalize_text(raw_text)
		pages.append(PageText(page_number=i, content=page_text))

	full_text = "\n\n".join(p.content for p in pages if p.content)
	if not full_text.strip():
		raise ValueError(f"PDF has no extractable text: {path}")

	return {
		"file_path": str(path),
		"source_file": path.name,
		"total_pages": len(pages),
		"pages": [asdict(p) for p in pages],
		"full_text": full_text,
	}


def _build_page_spans(pages: list[dict[str, Any]]) -> tuple[str, list[tuple[int, int, int]]]:
	"""Build concatenated text and (page, start, end) spans."""
	parts: list[str] = []
	spans: list[tuple[int, int, int]] = []
	cursor = 0
	for page in pages:
		content = page.get("content", "")
		if not content:
			continue
		if parts:
			parts.append("\n\n")
			cursor += 2
		start = cursor
		parts.append(content)
		cursor += len(content)
		end = cursor
		spans.append((int(page["page_number"]), start, end))
	return "".join(parts), spans


def _split_by_structure(full_text: str) -> list[dict[str, Any]]:
	"""Split text by legal sections, returning span-aware segments."""
	matches = list(LEGAL_SECTION_PATTERN.finditer(full_text))
	if len(matches) < 2:
		return []

	segments: list[dict[str, Any]] = []
	for i, match in enumerate(matches):
		start = match.start()
		end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
		content = full_text[start:end].strip()
		if not content:
			continue
		first_line = content.split("\n", 1)[0][:120]
		segments.append(
			{
				"start": start,
				"end": end,
				"section_title": first_line,
				"content": content,
			}
		)
	return segments


def _split_by_window(full_text: str, chunk_size: int, overlap: int) -> list[dict[str, Any]]:
	"""Sliding-window fallback with sentence-aware boundary adjustment."""
	segments: list[dict[str, Any]] = []
	start = 0
	while start < len(full_text):
		end = min(start + chunk_size, len(full_text))
		if end < len(full_text):
			# Prefer ending at sentence/paragraph boundary.
			cut = max(full_text.rfind(".", start, end), full_text.rfind("\n", start, end))
			if cut > start + chunk_size // 2:
				end = cut + 1
		content = full_text[start:end].strip()
		if content:
			segments.append(
				{
					"start": start,
					"end": end,
					"section_title": content.split("\n", 1)[0][:120],
					"content": content,
				}
			)

		if end >= len(full_text):
			break
		start = max(0, end - overlap)
	return segments


def _span_to_pages(start: int, end: int, spans: list[tuple[int, int, int]]) -> tuple[int, int]:
	"""Map text span to page range by overlap."""
	pages = []
	for page_num, page_start, page_end in spans:
		if start < page_end and end > page_start:
			pages.append(page_num)
	if not pages:
		return 1, 1
	return min(pages), max(pages)


def build_chunks(pdf_path: str | Path, config: ChunkConfig | None = None) -> list[dict[str, Any]]:
	"""Main ingestion function: PDF -> chunk records."""
	cfg = config or ChunkConfig()
	extracted = extract_pdf_text(pdf_path)
	source_file = extracted["source_file"]
	full_text, page_spans = _build_page_spans(extracted["pages"])

	segments = []
	if cfg.prefer_structure_split:
		segments = _split_by_structure(full_text)
		if len(segments) < 3:
			segments = []

	if not segments:
		segments = _split_by_window(full_text, cfg.chunk_size_chars, cfg.overlap_chars)

	chunks: list[dict[str, Any]] = []
	source_stem = Path(source_file).stem
	chunk_index = 1
	for seg in segments:
		content = seg["content"].strip()
		if len(content) < cfg.min_chunk_chars:
			continue
		page_start, page_end = _span_to_pages(seg["start"], seg["end"], page_spans)
		digest = hashlib.sha256(content.encode("utf-8")).hexdigest()

		record = ChunkRecord(
			chunk_id=f"{source_stem}-{chunk_index:04d}",
			source_file=source_file,
			page_start=page_start,
			page_end=page_end,
			title=seg["section_title"],
			section_title=seg["section_title"],
			char_start=int(seg["start"]),
			char_end=int(seg["end"]),
			token_estimate=_estimate_tokens(content),
			content_hash=digest,
			content=content,
		)
		chunks.append(asdict(record))
		chunk_index += 1

	logger.info("Built %d chunks from %s", len(chunks), source_file)
	return chunks


def save_chunks_json(chunks: list[dict[str, Any]], out_path: str | Path) -> Path:
	"""Persist chunks to JSON for audit/debug/replay."""
	path = Path(out_path)
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")
	return path


def prepare_for_embedding(chunks: list[dict[str, Any]]) -> list[str]:
	"""Extract plain chunk contents for embedding model input."""
	return [str(chunk.get("content", "")) for chunk in chunks]


def prepare_metadata(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
	"""Extract metadata payload for vector DB rows (excluding content)."""
	keys = [
		"chunk_id",
		"source_file",
		"page_start",
		"page_end",
		"title",
		"section_title",
		"char_start",
		"char_end",
		"token_estimate",
		"content_hash",
	]
	result = []
	for chunk in chunks:
		result.append({k: chunk.get(k) for k in keys})
	return result


def build_keyword_index(chunks: list[dict[str, Any]]) -> dict[str, list[str]]:
	"""Build a simple keyword -> chunk_ids index for local fallback search."""
	index: dict[str, set[str]] = {}
	for chunk in chunks:
		chunk_id = str(chunk.get("chunk_id", ""))
		text = str(chunk.get("content", "")).lower()
		terms = re.findall(r"\w+", text)
		for term in terms:
			if len(term) < 3:
				continue
			index.setdefault(term, set()).add(chunk_id)
	# Convert sets to sorted lists for JSON serialization.
	return {k: sorted(v) for k, v in index.items()}


def save_keyword_index(index_data: dict[str, list[str]], out_path: str | Path) -> Path:
	"""Persist local keyword index as JSON."""
	path = Path(out_path)
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(json.dumps(index_data, ensure_ascii=False, indent=2), encoding="utf-8")
	return path


def _resolve_embedding_provider(config: EmbeddingConfig) -> tuple[str, str | None]:
	"""Resolve actual embedding provider and API key.

	Returns:
		(provider, api_key)
	"""
	provider = config.provider.lower().strip()
	api_key = (config.api_key or os.getenv("OPENAI_API_KEY") or "").strip() or None

	if provider not in {"auto", "external", "local"}:
		raise ValueError("Invalid embedding provider. Use one of: auto, external, local")

	if provider == "external":
		if not api_key:
			raise ValueError(
				"External embedding provider requested but no API key found. "
				"Pass api_key or set OPENAI_API_KEY."
			)
		return "external", api_key

	if provider == "local":
		return "local", None

	# auto mode
	if api_key:
		return "external", api_key
	return "local", None


def _embed_with_external_api(
	texts: list[str],
	model: str,
	api_key: str,
	batch_size: int,
) -> list[list[float]]:
	"""Generate embeddings from external provider (OpenAI-compatible)."""
	try:
		from openai import OpenAI
	except ImportError as exc:
		raise ImportError("openai package is required for external embeddings") from exc

	client = OpenAI(api_key=api_key)
	all_vectors: list[list[float]] = []
	for i in range(0, len(texts), max(1, batch_size)):
		batch = texts[i : i + max(1, batch_size)]
		response = client.embeddings.create(model=model, input=batch)
		all_vectors.extend([list(item.embedding) for item in response.data])
	return all_vectors


def _embed_with_local_model(texts: list[str], model_name: str, batch_size: int) -> list[list[float]]:
	"""Generate embeddings with a local sentence-transformers model."""
	try:
		sentence_transformers = importlib.import_module("sentence_transformers")
		SentenceTransformer = sentence_transformers.SentenceTransformer
	except ImportError as exc:
		raise ImportError(
			"sentence-transformers package is required for local embeddings. "
			"Install with: pip install sentence-transformers"
		) from exc

	model = SentenceTransformer(model_name)
	vectors = model.encode(texts, batch_size=max(1, batch_size), show_progress_bar=False)
	return [list(vec) for vec in vectors]


def embed_chunks(
	chunks: list[dict[str, Any]],
	config: EmbeddingConfig | None = None,
) -> tuple[list[list[float]], dict[str, Any]]:
	"""Create embeddings for chunk content.

	Selection logic:
	- If provider=external: always external API (requires API key)
	- If provider=local: always local model
	- If provider=auto: use API model when API key exists, otherwise local model
	"""
	if not chunks:
		return [], {"provider": None, "model": None, "count": 0}

	cfg = config or EmbeddingConfig()
	texts = prepare_for_embedding(chunks)
	provider, api_key = _resolve_embedding_provider(cfg)

	if provider == "external":
		vectors = _embed_with_external_api(
			texts=texts,
			model=cfg.external_model,
			api_key=api_key or "",
			batch_size=cfg.batch_size,
		)
		meta = {"provider": "external", "model": cfg.external_model, "count": len(vectors)}
	else:
		vectors = _embed_with_local_model(
			texts=texts,
			model_name=cfg.local_model,
			batch_size=cfg.batch_size,
		)
		meta = {"provider": "local", "model": cfg.local_model, "count": len(vectors)}

	if len(vectors) != len(chunks):
		raise RuntimeError("Embedding count mismatch with chunk count")

	return vectors, meta


def _sanitize_metadata_for_chroma(meta: dict[str, Any]) -> dict[str, Any]:
	"""Ensure Chroma metadata only contains scalar JSON-compatible values."""
	sanitized: dict[str, Any] = {}
	for key, value in meta.items():
		if isinstance(value, (str, int, float, bool)) or value is None:
			sanitized[key] = value
		else:
			sanitized[key] = str(value)
	return sanitized


def index_chunks_to_chromadb(
	chunks: list[dict[str, Any]],
	persist_directory: str | Path = "data/regulations/chroma",
	collection_name: str = "regulation_chunks",
	embedding_config: EmbeddingConfig | None = None,
	reset_collection: bool = False,
) -> dict[str, Any]:
	"""Embed chunks and upsert them into a persistent ChromaDB collection."""
	if not chunks:
		return {
			"collection_name": collection_name,
			"persist_directory": str(persist_directory),
			"upserted": 0,
			"provider": None,
			"model": None,
		}

	try:
		chromadb = importlib.import_module("chromadb")
	except ImportError as exc:
		raise ImportError("chromadb package is required. Install with: pip install chromadb") from exc

	vectors, embed_info = embed_chunks(chunks, embedding_config)
	ids = [str(c.get("chunk_id", f"chunk-{i+1}")) for i, c in enumerate(chunks)]
	documents = prepare_for_embedding(chunks)
	metadatas = [_sanitize_metadata_for_chroma(m) for m in prepare_metadata(chunks)]

	chroma_path = Path(persist_directory)
	chroma_path.mkdir(parents=True, exist_ok=True)
	client = chromadb.PersistentClient(path=str(chroma_path))

	if reset_collection:
		try:
			client.delete_collection(collection_name)
		except Exception:
			# Collection may not exist yet.
			pass

	collection = client.get_or_create_collection(name=collection_name)
	collection.upsert(ids=ids, documents=documents, metadatas=metadatas, embeddings=vectors)

	return {
		"collection_name": collection_name,
		"persist_directory": str(chroma_path),
		"upserted": len(ids),
		"provider": embed_info.get("provider"),
		"model": embed_info.get("model"),
	}


def _cli() -> int:
	parser = argparse.ArgumentParser(description="Build regulation chunks from a PDF")
	parser.add_argument("pdf_path", help="Path to regulation PDF")
	parser.add_argument(
		"--out-chunks",
		default="data/regulations/chunks.json",
		help="Output JSON file for chunks",
	)
	parser.add_argument(
		"--out-index",
		default="data/regulations/keyword_index.json",
		help="Output JSON file for local keyword index",
	)
	parser.add_argument(
		"--to-chroma",
		action="store_true",
		help="Generate embeddings and index chunks into ChromaDB",
	)
	parser.add_argument(
		"--chroma-dir",
		default="data/regulations/chroma",
		help="Persistent directory for ChromaDB",
	)
	parser.add_argument(
		"--chroma-collection",
		default="regulation_chunks",
		help="Chroma collection name",
	)
	parser.add_argument(
		"--embedding-provider",
		choices=["auto", "external", "local"],
		default="auto",
		help="Embedding provider selection strategy",
	)
	parser.add_argument(
		"--embedding-api-key",
		default=None,
		help="External embedding API key (fallback to OPENAI_API_KEY env)",
	)
	parser.add_argument(
		"--embedding-model",
		default="text-embedding-3-small",
		help="External embedding model name",
	)
	parser.add_argument(
		"--local-embedding-model",
		default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
		help="Local sentence-transformers model name",
	)
	parser.add_argument(
		"--reset-collection",
		action="store_true",
		help="Delete and recreate target Chroma collection before upsert",
	)
	args = parser.parse_args()

	logging.basicConfig(level=logging.INFO)

	chunks = build_chunks(args.pdf_path)
	save_chunks_json(chunks, args.out_chunks)
	index_data = build_keyword_index(chunks)
	save_keyword_index(index_data, args.out_index)

	if args.to_chroma:
		embed_cfg = EmbeddingConfig(
			provider=args.embedding_provider,
			api_key=args.embedding_api_key,
			external_model=args.embedding_model,
			local_model=args.local_embedding_model,
		)
		result = index_chunks_to_chromadb(
			chunks=chunks,
			persist_directory=args.chroma_dir,
			collection_name=args.chroma_collection,
			embedding_config=embed_cfg,
			reset_collection=args.reset_collection,
		)
		print(
			"Chroma upsert: "
			f"{result['upserted']} chunks | provider={result['provider']} | model={result['model']}"
		)

	print(f"Chunks: {len(chunks)}")
	print(f"Saved chunks: {args.out_chunks}")
	print(f"Saved index: {args.out_index}")
	if args.to_chroma:
		print(f"Saved Chroma collection: {args.chroma_collection} @ {args.chroma_dir}")
	return 0


if __name__ == "__main__":
	raise SystemExit(_cli())

'''
Tùy chọn:
- Chỉ chunk: python -m src.agent.chunk data/regulations/quyche.pdf
- Chunk + embed + ChromaDB:python -m src.agent.chunk quyche.pdf --to-chroma --embedding-provider auto
'''