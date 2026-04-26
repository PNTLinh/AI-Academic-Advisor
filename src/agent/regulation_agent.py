"""
Regulation Agent – Agent chuyên xử lý quy chế đào tạo.

Chức năng:
  1. Đọc và trích xuất nội dung từ file PDF quy chế
  2. Chia văn bản thành các chunk nhỏ để xử lý hiệu quả
  3. Tìm kiếm thông tin liên quan trong quy chế
  4. Trả lời câu hỏi cụ thể về quy chế thông qua LLM

Kiến trúc:
  Main Agent  ──(query_regulation)──►  Regulation Agent
                                           │
                                    ┌──────┴──────┐
                                    │  PDF Reader  │
                                    │  Chunker     │
                                    │  Searcher    │
                                    │  LLM Q&A     │
                                    └─────────────┘
"""

import os
import re
import json
import logging
from pathlib import Path
from typing import Optional

from anthropic import Anthropic

from .config import ANTHROPIC_API_KEY, DEFAULT_MODEL

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# PDF Reader
# ---------------------------------------------------------------------------
class PDFReader:
    """Đọc và trích xuất text từ file PDF."""

    @staticmethod
    def read(pdf_path: str) -> dict:
        """
        Đọc file PDF và trả về text theo từng trang.

        Returns:
            {
                "file_path": str,
                "total_pages": int,
                "pages": [{"page_number": int, "content": str}, ...],
                "full_text": str
            }
        """
        try:
            from PyPDF2 import PdfReader

            reader = PdfReader(pdf_path)
            pages = []
            full_text = ""

            for i, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                pages.append({
                    "page_number": i + 1,
                    "content": page_text.strip(),
                })
                full_text += page_text + "\n"

            return {
                "file_path": pdf_path,
                "total_pages": len(reader.pages),
                "pages": pages,
                "full_text": full_text.strip(),
            }
        except ImportError:
            raise ImportError(
                "PyPDF2 chưa được cài đặt. Chạy: pip install PyPDF2"
            )

    @staticmethod
    def find_pdfs(directory: str) -> list[str]:
        """Tìm tất cả file PDF trong thư mục."""
        dir_path = Path(directory)
        if not dir_path.exists():
            return []
        return [str(p) for p in dir_path.glob("**/*.pdf")]


# ---------------------------------------------------------------------------
# Text Chunker – Chia văn bản quy chế thành các đoạn nhỏ
# ---------------------------------------------------------------------------
class RegulationChunker:
    """
    Chia văn bản quy chế thành chunks có ngữ nghĩa.

    Chiến lược:
      - Chia theo Điều/Chương/Mục nếu phát hiện cấu trúc pháp luật
      - Fallback: chia theo kích thước cố định với overlap
    """

    # Pattern nhận diện cấu trúc văn bản quy chế Việt Nam
    ARTICLE_PATTERN = re.compile(
        r"(?:^|\n)"                              # Đầu dòng
        r"(?:Điều\s+\d+|Chương\s+[IVXLCDM\d]+|" # Điều/Chương
        r"Mục\s+\d+|Phần\s+[IVXLCDM\d]+|"       # Mục/Phần
        r"Khoản\s+\d+|"                          # Khoản
        r"\d+\.\s+[A-ZÁÀẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÉÈẺẼẸÊẾỀỂỄỆ])"  # Mục số
        , re.MULTILINE | re.UNICODE
    )

    def __init__(self, chunk_size: int = 1500, overlap: int = 200):
        """
        Args:
            chunk_size: Kích thước tối đa mỗi chunk (ký tự).
            overlap: Số ký tự overlap giữa các chunk (tránh mất ngữ cảnh).
        """
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> list[dict]:
        """
        Chia text thành các chunks.

        Returns:
            list[dict] – mỗi chunk gồm:
                {"chunk_id": int, "title": str, "content": str, "char_start": int}
        """
        # Thử chia theo cấu trúc pháp luật trước
        structural_chunks = self._chunk_by_structure(text)
        if len(structural_chunks) >= 3:
            return structural_chunks

        # Fallback: chia theo kích thước
        return self._chunk_by_size(text)

    def _chunk_by_structure(self, text: str) -> list[dict]:
        """Chia theo Điều/Chương/Mục."""
        matches = list(self.ARTICLE_PATTERN.finditer(text))
        if len(matches) < 2:
            return []

        chunks = []
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            content = text[start:end].strip()

            # Lấy title (dòng đầu tiên)
            first_line = content.split("\n")[0].strip()

            # Nếu chunk quá dài, chia nhỏ tiếp
            if len(content) > self.chunk_size * 2:
                sub_chunks = self._chunk_by_size(content)
                for j, sc in enumerate(sub_chunks):
                    sc["title"] = f"{first_line} (phần {j + 1})"
                    sc["chunk_id"] = len(chunks) + 1
                    chunks.append(sc)
            else:
                chunks.append({
                    "chunk_id": len(chunks) + 1,
                    "title": first_line[:100],
                    "content": content,
                    "char_start": start,
                })

        return chunks

    def _chunk_by_size(self, text: str) -> list[dict]:
        """Chia theo kích thước cố định với overlap."""
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + self.chunk_size, len(text))

            # Cố gắng cắt ở cuối câu
            if end < len(text):
                last_period = text.rfind(".", start, end)
                last_newline = text.rfind("\n", start, end)
                cut_point = max(last_period, last_newline)
                if cut_point > start + self.chunk_size // 2:
                    end = cut_point + 1

            content = text[start:end].strip()
            if content:
                chunks.append({
                    "chunk_id": len(chunks) + 1,
                    "title": content[:80].replace("\n", " ") + "...",
                    "content": content,
                    "char_start": start,
                })

            start = end - self.overlap if end < len(text) else len(text)

        return chunks


# ---------------------------------------------------------------------------
# Regulation Searcher – Tìm kiếm trong quy chế
# ---------------------------------------------------------------------------
class RegulationSearcher:
    """
    Tìm kiếm thông tin trong các chunks quy chế.

    Sử dụng keyword matching + TF-IDF đơn giản.
    (Có thể nâng cấp lên vector search sau.)
    """

    def __init__(self, chunks: list[dict]):
        self.chunks = chunks

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """
        Tìm các chunk liên quan nhất đến query.

        Args:
            query: Câu hỏi / từ khóa.
            top_k: Số chunk trả về.

        Returns:
            list[dict] – các chunk sắp xếp theo relevance giảm dần.
        """
        query_lower = query.lower()
        keywords = self._extract_keywords(query_lower)

        scored_chunks = []
        for chunk in self.chunks:
            content_lower = chunk["content"].lower()
            title_lower = chunk.get("title", "").lower()

            score = 0
            # Exact phrase match (cao nhất)
            if query_lower in content_lower:
                score += 10

            # Keyword matching
            for kw in keywords:
                count = content_lower.count(kw)
                score += count * 2
                # Bonus nếu keyword xuất hiện trong title
                if kw in title_lower:
                    score += 3

            if score > 0:
                scored_chunks.append({
                    **chunk,
                    "relevance_score": score,
                })

        # Sắp xếp theo score giảm dần
        scored_chunks.sort(key=lambda c: c["relevance_score"], reverse=True)
        return scored_chunks[:top_k]

    @staticmethod
    def _extract_keywords(text: str) -> list[str]:
        """Trích xuất từ khóa từ query (loại bỏ stopwords tiếng Việt)."""
        stopwords = {
            "là", "của", "và", "có", "được", "trong", "cho", "với", "các",
            "không", "này", "đó", "từ", "một", "những", "về", "theo", "khi",
            "đến", "ra", "hay", "hoặc", "nếu", "thì", "bị", "để", "do",
            "tôi", "sinh", "viên", "em", "mình", "cho",
        }
        words = re.findall(r"\w+", text.lower())
        return [w for w in words if w not in stopwords and len(w) > 1]


# ---------------------------------------------------------------------------
# Regulation Agent – Agent chính xử lý quy chế
# ---------------------------------------------------------------------------
class RegulationAgent:
    """
    Agent chuyên biệt để xử lý mọi câu hỏi liên quan đến quy chế đào tạo.

    Workflow:
      1. Load PDF quy chế → chunk text
      2. Nhận câu hỏi từ Main Agent
      3. Tìm chunks liên quan
      4. Gọi LLM với context chunks → trả lời

    Usage:
        agent = RegulationAgent(regulations_dir="data/regulations")
        answer = agent.query("Sinh viên trượt bao nhiêu tín chỉ thì bị hạ bằng?")
    """

    SYSTEM_PROMPT = """Bạn là chuyên gia về quy chế đào tạo đại học.

NHIỆM VỤ:
- Trả lời câu hỏi về quy chế dựa HOÀN TOÀN trên nội dung quy chế được cung cấp.
- Trích dẫn Điều/Khoản/Mục cụ thể khi trả lời.
- Nếu thông tin không có trong quy chế, nói rõ "Không tìm thấy trong quy chế được cung cấp".

QUY TẮC:
- KHÔNG bịa thông tin. Chỉ dùng nội dung từ context.
- Trả lời ngắn gọn, rõ ràng, có cấu trúc.
- Nếu câu hỏi mơ hồ, liệt kê các điều khoản liên quan."""

    def __init__(
        self,
        regulations_dir: str = None,
        pdf_paths: list[str] = None,
        api_key: str = None,
        model: str = None,
    ):
        """
        Args:
            regulations_dir: Thư mục chứa file PDF quy chế.
            pdf_paths: Danh sách đường dẫn PDF cụ thể (ưu tiên hơn regulations_dir).
            api_key: Anthropic API key (mặc định lấy từ config).
            model: Model LLM (mặc định lấy từ config).
        """
        self.api_key = api_key or ANTHROPIC_API_KEY
        self.model = model or DEFAULT_MODEL
        self.client = None

        self.reader = PDFReader()
        self.chunker = RegulationChunker()
        self.chunks: list[dict] = []
        self.raw_documents: list[dict] = []

        # Load PDF files
        paths = pdf_paths or []
        if not paths and regulations_dir:
            paths = PDFReader.find_pdfs(regulations_dir)

        if paths:
            self._load_documents(paths)
            logger.info(
                f"RegulationAgent đã load {len(self.raw_documents)} tài liệu, "
                f"{len(self.chunks)} chunks."
            )
        else:
            logger.warning("RegulationAgent: Không tìm thấy file PDF quy chế nào.")

    def _load_documents(self, pdf_paths: list[str]):
        """Đọc và chunk tất cả PDF."""
        for path in pdf_paths:
            try:
                doc = self.reader.read(path)
                self.raw_documents.append(doc)

                # Chunk toàn bộ text
                doc_chunks = self.chunker.chunk(doc["full_text"])
                # Gắn thêm metadata nguồn
                for chunk in doc_chunks:
                    chunk["source_file"] = os.path.basename(path)
                self.chunks.extend(doc_chunks)

                logger.info(f"Đã load: {path} ({doc['total_pages']} trang, {len(doc_chunks)} chunks)")
            except Exception as e:
                logger.error(f"Lỗi khi đọc {path}: {e}")

    def _get_client(self) -> Anthropic:
        """Lazy init Anthropic client."""
        if self.client is None:
            if not self.api_key:
                raise ValueError("ANTHROPIC_API_KEY chưa được cấu hình.")
            self.client = Anthropic(api_key=self.api_key)
        return self.client

    def reload(self, pdf_paths: list[str] = None, regulations_dir: str = None):
        """Reload lại tài liệu quy chế (khi có cập nhật)."""
        self.chunks = []
        self.raw_documents = []

        paths = pdf_paths or []
        if not paths and regulations_dir:
            paths = PDFReader.find_pdfs(regulations_dir)

        if paths:
            self._load_documents(paths)

    # ----- Core methods -----

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """
        Tìm kiếm các đoạn quy chế liên quan đến câu hỏi.

        Args:
            query: Câu hỏi / từ khóa.
            top_k: Số chunk trả về.

        Returns:
            list[dict] – các chunk liên quan nhất.
        """
        if not self.chunks:
            return []
        searcher = RegulationSearcher(self.chunks)
        return searcher.search(query, top_k=top_k)

    def query(self, question: str, top_k: int = 5) -> dict:
        """
        Trả lời câu hỏi về quy chế bằng LLM.

        Workflow:
          1. Tìm chunks liên quan
          2. Build context prompt
          3. Gọi LLM
          4. Trả về câu trả lời + nguồn trích dẫn

        Args:
            question: Câu hỏi về quy chế.
            top_k: Số chunk context tối đa.

        Returns:
            {
                "answer": str,
                "sources": list[dict],
                "chunks_used": int
            }
        """
        # Bước 1: Tìm chunks liên quan
        relevant_chunks = self.search(question, top_k=top_k)

        if not relevant_chunks:
            return {
                "answer": "Không tìm thấy thông tin liên quan trong quy chế.",
                "sources": [],
                "chunks_used": 0,
            }

        # Bước 2: Build context
        context_parts = []
        for i, chunk in enumerate(relevant_chunks):
            source = chunk.get("source_file", "unknown")
            title = chunk.get("title", "")
            context_parts.append(
                f"--- Trích đoạn {i + 1} (nguồn: {source}) ---\n"
                f"Tiêu đề: {title}\n"
                f"{chunk['content']}\n"
            )
        context = "\n".join(context_parts)

        # Bước 3: Gọi LLM
        user_message = (
            f"Dựa trên nội dung quy chế dưới đây, hãy trả lời câu hỏi.\n\n"
            f"## Nội dung quy chế:\n{context}\n\n"
            f"## Câu hỏi:\n{question}"
        )

        try:
            client = self._get_client()
            response = client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=self.SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}],
            )

            answer = ""
            for block in response.content:
                if hasattr(block, "text"):
                    answer += block.text

            return {
                "answer": answer,
                "sources": [
                    {
                        "chunk_id": c["chunk_id"],
                        "title": c.get("title", ""),
                        "source_file": c.get("source_file", ""),
                        "relevance_score": c.get("relevance_score", 0),
                    }
                    for c in relevant_chunks
                ],
                "chunks_used": len(relevant_chunks),
            }

        except Exception as e:
            logger.error(f"Lỗi khi gọi LLM: {e}")
            return {
                "answer": f"Lỗi khi xử lý: {str(e)}",
                "sources": [],
                "chunks_used": 0,
            }

    def get_all_chunks(self) -> list[dict]:
        """Trả về tất cả chunks (để debug/inspect)."""
        return self.chunks

    def get_summary(self) -> dict:
        """Tóm tắt trạng thái hiện tại của Regulation Agent."""
        return {
            "total_documents": len(self.raw_documents),
            "total_chunks": len(self.chunks),
            "documents": [
                {
                    "file": doc.get("file_path", ""),
                    "pages": doc.get("total_pages", 0),
                }
                for doc in self.raw_documents
            ],
        }


# ---------------------------------------------------------------------------
# Singleton instance & integration functions
# ---------------------------------------------------------------------------

_regulation_agent: RegulationAgent | None = None


def init_regulation_agent(
    regulations_dir: str = None,
    pdf_paths: list[str] = None,
) -> RegulationAgent:
    """Khởi tạo singleton RegulationAgent."""
    global _regulation_agent
    _regulation_agent = RegulationAgent(
        regulations_dir=regulations_dir,
        pdf_paths=pdf_paths,
    )
    return _regulation_agent


def get_regulation_agent() -> RegulationAgent:
    """Lấy instance hiện tại."""
    if _regulation_agent is None:
        raise RuntimeError(
            "RegulationAgent chưa được khởi tạo. "
            "Gọi init_regulation_agent() trước."
        )
    return _regulation_agent


def query_regulation(question: str, top_k: int = 5) -> str:
    """
    Hàm wrapper để Main Agent gọi qua tool registry.

    Đây là entry point duy nhất từ tools.py → regulation_agent.
    """
    agent = get_regulation_agent()
    result = agent.query(question, top_k=top_k)
    return json.dumps(result, ensure_ascii=False)


def search_regulation(query: str, top_k: int = 5) -> str:
    """Tìm kiếm trong quy chế (không gọi LLM, chỉ trả chunks)."""
    agent = get_regulation_agent()
    results = agent.search(query, top_k=top_k)
    return json.dumps(results, ensure_ascii=False, default=str)
