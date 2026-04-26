"""
processing_regulation.py
========================
Pipeline xử lý các file PDF trong `data/regulations/`, trích xuất thông
tin cần thiết và lưu ra hai định dạng:

  1. **JSONL** (data/output/*.jsonl)  – mỗi dòng là một JSON document,
     agent có thể đọc tuần tự hoặc tìm kiếm nhanh bằng grep/jq.

  2. **ChromaDB** (data/output/chroma/)  – vector store NoSQL, agent
     dùng để semantic search (RAG) mà không cần LLM embedding nặng.

Các collection / file đầu ra:
  - regulations.jsonl      : Các điều khoản quy chế học vụ
  - courses.jsonl          : Thông tin môn học
  - curriculums.jsonl      : Chương trình đào tạo
  - curriculum_details.jsonl: Chi tiết môn trong CTDT
  - course_dependencies.jsonl: Quan he tien quyet / song hanh
  - chunks.jsonl           : Tất cả text chunk (cho RAG)
  - chroma/                : ChromaDB persistent store (NoSQL vector DB)
      └── regulation_chunks: collection chunk → semantic search

Cach dung:
  python data/processing_regulation.py               # chay toan bo pipeline
  python data/processing_regulation.py --dry-run     # chi in ket qua
  python data/processing_regulation.py --no-chroma   # chi ghi JSONL
  python data/processing_regulation.py --output-dir path/to/out
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Encoding fix cho Windows console (cp1252)
# ---------------------------------------------------------------------------
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("processing_regulation")


# ---------------------------------------------------------------------------
# Duong dan mac dinh
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent           # data/
REGULATIONS_DIR = BASE_DIR / "regulations"
OUTPUT_DIR = BASE_DIR / "output"
CHROMA_DIR = OUTPUT_DIR / "chroma"


# ===========================================================================
# 1. PDF Reader
# ===========================================================================
class PDFReader:
    """Doc va trich xuat text tu file PDF bang PyPDF2."""

    @staticmethod
    def read(pdf_path: str | Path) -> dict:
        """
        Doc mot file PDF.

        Returns::
            {
              "file_path": str,
              "file_name": str,
              "total_pages": int,
              "pages": [{"page_number": int, "content": str}],
              "full_text": str
            }
        """
        try:
            from PyPDF2 import PdfReader
        except ImportError:
            raise ImportError(
                "Thieu thu vien PyPDF2. Cai bang: pip install PyPDF2"
            )

        reader = PdfReader(str(pdf_path))
        pages = []
        full_text = ""

        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            pages.append({"page_number": i + 1, "content": text.strip()})
            full_text += text + "\n"

        return {
            "file_path": str(pdf_path),
            "file_name": Path(pdf_path).name,
            "total_pages": len(reader.pages),
            "pages": pages,
            "full_text": full_text.strip(),
        }

    @staticmethod
    def find_pdfs(directory: str | Path) -> list[str]:
        """Tim tat ca file PDF trong thu muc (de quy)."""
        dir_path = Path(directory)
        if not dir_path.exists():
            return []
        return sorted(str(p) for p in dir_path.glob("**/*.pdf"))


# ===========================================================================
# 2. Text Chunker
# ===========================================================================
class TextChunker:
    """Chia van ban thanh cac chunk co ngu nghia theo cau truc phap luat."""

    ARTICLE_PATTERN = re.compile(
        r"(?:^|\n)"
        r"(?:Dieu\s+\d+|Chuong\s+[IVXLCDM\d]+|"
        r"Muc\s+\d+|Phan\s+[IVXLCDM\d]+|"
        r"Khoan\s+\d+|"
        r"\d+\.\s+[A-Z]"
        r"|Điều\s+\d+|Chương\s+[IVXLCDM\d]+|"   # Unicode forms
        r"Mục\s+\d+|Phần\s+[IVXLCDM\d]+|"
        r"Khoản\s+\d+)",
        re.MULTILINE | re.UNICODE,
    )

    def __init__(self, chunk_size: int = 1200, overlap: int = 150):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> list[dict]:
        structural = self._chunk_by_structure(text)
        if len(structural) >= 3:
            return structural
        return self._chunk_by_size(text)

    def _chunk_by_structure(self, text: str) -> list[dict]:
        matches = list(self.ARTICLE_PATTERN.finditer(text))
        if len(matches) < 2:
            return []

        chunks = []
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            content = text[start:end].strip()
            first_line = content.split("\n")[0].strip()

            if len(content) > self.chunk_size * 2:
                sub = self._chunk_by_size(content)
                for j, sc in enumerate(sub):
                    sc["title"] = f"{first_line} (phan {j + 1})"
                    sc["chunk_id"] = len(chunks) + 1
                    chunks.append(sc)
            else:
                chunks.append({
                    "chunk_id": len(chunks) + 1,
                    "title": first_line[:120],
                    "content": content,
                    "char_start": start,
                })
        return chunks

    def _chunk_by_size(self, text: str) -> list[dict]:
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            if end < len(text):
                cut = max(text.rfind(".", start, end), text.rfind("\n", start, end))
                if cut > start + self.chunk_size // 2:
                    end = cut + 1
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


# ===========================================================================
# 3. RegulationExtractor
# ===========================================================================
class RegulationExtractor:
    """
    Trich xuat cac truong thong tin tu van ban quy che va chuong trinh dao tao.

    Anh xa len schema data.sql:
      Regulations, Courses, Course_Categories,
      Curriculums, Curriculum_Details, Course_Dependencies
    """

    COURSE_CODE_PATTERN = re.compile(r"\b([A-Z]{2,4}\d{4,5}[A-Z]?)\b")

    CREDIT_PATTERN = re.compile(
        r"(?:(\d+)\s*(?:tin\s*chi|tc|TC|tín\s*chỉ))"
        r"|(?:\((\d+)\s*(?:TC|tc|tin\s*chi|tín\s*chỉ)?\))"
        r"|(?:so\s+(?:tin\s+chi|TC)\s*[:\-]\s*(\d+))",
        re.IGNORECASE | re.UNICODE,
    )

    PREREQ_PATTERNS = {
        "Prerequisite": re.compile(
            r"(?:tien\s*quyet|tien quyet|tiên\s*quyết|hoc\s*truoc\s*bat\s*buoc)"
            r"[:\s]*([A-Z]{2,4}\d{4,5}[A-Z]?(?:\s*,\s*[A-Z]{2,4}\d{4,5}[A-Z]?)*)",
            re.IGNORECASE | re.UNICODE,
        ),
        "Parallel": re.compile(
            r"(?:song\s*hanh|song hanh|song\s*hành|cung\s*ky)"
            r"[:\s]*([A-Z]{2,4}\d{4,5}[A-Z]?(?:\s*,\s*[A-Z]{2,4}\d{4,5}[A-Z]?)*)",
            re.IGNORECASE | re.UNICODE,
        ),
        "Pre-condition": re.compile(
            r"(?:hoc\s*truoc(?!\s*bat)|hoc truoc|học\s*trước(?!\s*bắt))"
            r"[:\s]*([A-Z]{2,4}\d{4,5}[A-Z]?(?:\s*,\s*[A-Z]{2,4}\d{4,5}[A-Z]?)*)",
            re.IGNORECASE | re.UNICODE,
        ),
    }

    CATEGORY_KEYWORDS = {
        "Ly luan chinh tri": [
            "ly luan chinh tri", "chinh tri", "mac-le nin", "tu tuong ho chi minh",
            "lý luận chính trị", "tư tưởng hồ chí minh",
        ],
        "Toan va Khoa hoc co ban": [
            "giai tich", "dai so", "xac suat", "thong ke", "vat ly", "toan",
            "giải tích", "đại số", "xác suất", "vật lý", "toán",
        ],
        "Co so nganh": [
            "co so nganh", "ky thuat co so", "nhap mon", "dai cuong",
            "cơ sở ngành", "kỹ thuật cơ sở", "nhập môn", "đại cương",
        ],
        "Ky thuat chuyen nganh": [
            "chuyen nganh", "module", "chuyên ngành",
        ],
        "Thuc tap va Do an": [
            "thuc tap", "do an", "luan van", "khoa luan",
            "thực tập", "đồ án", "luận văn", "khóa luận",
        ],
        "Tu chon tu do": [
            "tu chon", "tu do", "elective", "tự chọn",
        ],
        "Tieng Anh": ["tieng anh", "anh van", "english", "tiếng anh"],
        "Giao duc the chat": ["giao duc the chat", "the duc", "giáo dục thể chất"],
        "Giao duc quoc phong": ["giao duc quoc phong", "quoc phong", "quốc phòng"],
    }

    TOTAL_CREDITS_PATTERN = re.compile(
        r"(?:tong\s+(?:so\s+)?tin\s+chi|tin\s+chi\s+tot\s+nghiep"
        r"|yeu\s+cau\s+tin\s+chi"
        r"|tổng\s+(?:số\s+)?tín\s+chỉ|tín\s+chỉ\s+tốt\s+nghiệp)"
        r"[:\s]*(\d{3})",
        re.IGNORECASE | re.UNICODE,
    )

    REGULATION_TOPICS = {
        "Xep loai hoc luc": [
            "xuat sac", "gioi", "kha", "trung binh", "yeu", "xep loai", "hoc luc",
            "xuất sắc", "giỏi", "khá", "xếp loại", "học lực",
        ],
        "Dieu kien tot nghiep": [
            "tot nghiep", "dieu kien tot nghiep",
            "tốt nghiệp", "điều kiện tốt nghiệp",
        ],
        "Ha bac bang": [
            "ha bac", "ha bang", "diem d", "tin chi khong dat",
            "hạ bậc", "hạ bằng", "điểm D",
        ],
        "Canh cao hoc vu": [
            "canh cao", "dinh chi", "buoc thoi hoc",
            "cảnh cáo", "đình chỉ", "buộc thôi học",
        ],
        "Dang ky mon hoc": [
            "dang ky", "gioi han tin chi", "so tin chi toi da",
            "đăng ký", "giới hạn tín chỉ", "số tín chỉ tối đa",
        ],
        "Thang diem": [
            "thang diem", "diem chu", "diem so", "thang 4",
            "thang điểm", "điểm chữ", "thang 4",
        ],
        "Dieu kien tien quyet": [
            "tien quyet", "song hanh", "hoc truoc",
            "tiên quyết", "song hành", "học trước",
        ],
    }

    def __init__(self):
        self.chunker = TextChunker()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract_regulation_record(self, doc: dict) -> dict:
        """Trich xuat ban ghi cho bang Regulations."""
        title = self._extract_document_title(doc["full_text"], doc["file_name"])
        summary = self._generate_content_summary(doc["full_text"])
        return {
            "title": title,
            "content_summary": summary,
            "document_url": doc["file_path"],
        }

    def extract_courses(self, doc: dict) -> list[dict]:
        """Trich xuat danh sach Courses tu van ban."""
        chunks = self.chunker.chunk(doc["full_text"])
        courses: dict[str, dict] = {}
        for chunk in chunks:
            for c in self._extract_courses_from_chunk(chunk["content"]):
                cid = c["course_id"]
                if cid not in courses:
                    courses[cid] = c
                else:
                    ex = courses[cid]
                    if not ex.get("course_name") and c.get("course_name"):
                        ex["course_name"] = c["course_name"]
                    if not ex.get("credits") and c.get("credits"):
                        ex["credits"] = c["credits"]
                    if not ex.get("description") and c.get("description"):
                        ex["description"] = c["description"]
        return list(courses.values())

    def extract_curriculum(self, doc: dict) -> Optional[dict]:
        """Trich xuat thong tin Curriculum."""
        text = doc["full_text"]
        major = self._extract_major_name(text, doc["file_name"])
        total_credits = self._extract_total_credits(text)
        version = self._extract_curriculum_version(text)
        if not major and total_credits is None:
            return None
        return {
            "major_name": major or "Chua xac dinh",
            "total_credits_required": total_credits or 0,
            "version": version or "N/A",
        }

    def extract_curriculum_details(self, doc: dict, courses: list[dict]) -> list[dict]:
        """Trich xuat Curriculum_Details."""
        text = doc["full_text"]
        seen: set[str] = set()
        details = []
        for course in courses:
            cid = course["course_id"]
            if cid in seen:
                continue
            seen.add(cid)
            details.append({
                "course_id": cid,
                "is_required": self._is_mandatory_course(cid, text),
                "semester_propose": self._extract_proposed_semester(cid, text),
            })
        return details

    def extract_course_dependencies(self, doc: dict) -> list[dict]:
        """Trich xuat Course_Dependencies (tien quyet / song hanh / hoc truoc)."""
        text = doc["full_text"]
        deps = []
        seen: set[tuple] = set()
        for dep_type, pattern in self.PREREQ_PATTERNS.items():
            for match in pattern.finditer(text):
                dep_codes = self.COURSE_CODE_PATTERN.findall(match.group(1))
                ctx = text[max(0, match.start() - 200):match.start()]
                main_codes = self.COURSE_CODE_PATTERN.findall(ctx)
                if not main_codes or not dep_codes:
                    continue
                main_code = main_codes[-1]
                for dep_code in dep_codes:
                    if dep_code == main_code:
                        continue
                    key = (main_code, dep_code, dep_type)
                    if key not in seen:
                        seen.add(key)
                        deps.append({
                            "course_id": main_code,
                            "dependency_id": dep_code,
                            "dependency_type": dep_type,
                        })
        return deps

    def extract_regulation_topics(self, doc: dict) -> list[dict]:
        """Trich xuat cac chu de quan trong trong quy che."""
        chunks = self.chunker.chunk(doc["full_text"])
        records = []
        seen_topics: set[str] = set()
        for topic_name, keywords in self.REGULATION_TOPICS.items():
            relevant = []
            for chunk in chunks:
                cl = chunk["content"].lower()
                if any(kw in cl for kw in keywords):
                    relevant.append(chunk["content"][:500])
            if relevant and topic_name not in seen_topics:
                seen_topics.add(topic_name)
                combined = " | ".join(relevant[:3])
                records.append({
                    "title": f"[{doc['file_name']}] {topic_name}",
                    "content_summary": combined[:1000],
                    "document_url": doc["file_path"],
                })
        return records

    def extract_chunks(self, doc: dict) -> list[dict]:
        """Trich xuat tat ca text chunk (dung cho RAG / ChromaDB)."""
        chunks = self.chunker.chunk(doc["full_text"])
        result = []
        for chunk in chunks:
            result.append({
                **chunk,
                "source_file": doc["file_name"],
                "source_path": doc["file_path"],
                "doc_title": self._extract_document_title(
                    doc["full_text"], doc["file_name"]
                ),
            })
        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _extract_document_title(self, text: str, file_name: str) -> str:
        patterns = [
            r"(QUY\s+CHE[^\n]{5,80})", r"(QUY\s*CHẾ[^\n]{5,80})",
            r"(THONG\s+TU[^\n]{5,80})", r"(THÔNG\s+TƯ[^\n]{5,80})",
            r"(QUYET\s+DINH[^\n]{5,80})", r"(QUYẾT\s+ĐỊNH[^\n]{5,80})",
            r"(CHUONG\s+TRINH\s+DAO\s+TAO[^\n]{5,60})",
            r"(CHƯƠNG\s+TRÌNH\s+ĐÀO\s+TẠO[^\n]{5,60})",
        ]
        for p in patterns:
            m = re.search(p, text[:2000], re.IGNORECASE | re.UNICODE)
            if m:
                return m.group(1).strip()[:255]
        for line in text.splitlines():
            line = line.strip()
            if len(line) > 10:
                return line[:255]
        return file_name

    def _generate_content_summary(self, text: str, max_len: int = 1000) -> str:
        head = " ".join(text[:1500].split())
        return head[:max_len]

    def _extract_courses_from_chunk(self, text: str) -> list[dict]:
        courses = []
        lines = text.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            code_match = self.COURSE_CODE_PATTERN.search(line)
            if not code_match:
                i += 1
                continue

            course_id = code_match.group(1)
            after_code = line[code_match.end():].strip(" -–:.")
            course_name = ""
            if after_code and not self.COURSE_CODE_PATTERN.match(after_code):
                name_candidate = re.sub(
                    r"\(\d+\s*(?:TC|tc|tin\s*chi|tín\s*chỉ)?\)", "", after_code
                ).strip()
                if len(name_candidate) > 2:
                    course_name = name_candidate[:200]

            credits = None
            for sl in [line] + (lines[i + 1:i + 3] if i + 1 < len(lines) else []):
                cr = self.CREDIT_PATTERN.search(sl)
                if cr:
                    raw = cr.group(1) or cr.group(2) or cr.group(3)
                    if raw:
                        try:
                            credits = int(raw)
                            break
                        except ValueError:
                            pass

            desc_lines = []
            j = i + 1
            while j < len(lines) and j < i + 4:
                nl = lines[j].strip()
                if self.COURSE_CODE_PATTERN.match(nl):
                    break
                if nl and not re.match(r"^\d+\s*$", nl):
                    desc_lines.append(nl)
                j += 1
            description = " ".join(desc_lines)[:300]

            category = self._classify_course_category(course_id, course_name, text)
            department = self._infer_department(course_id)

            courses.append({
                "course_id": course_id,
                "course_name": course_name or f"Mon {course_id}",
                "credits": credits or 0,
                "description": description,
                "department": department,
                "is_mandatory": True,
                "category_name": category,
            })
            i += 1
        return courses

    def _classify_course_category(self, course_id: str, course_name: str, ctx: str) -> str:
        combined = (course_id + " " + course_name + " " + ctx[:200]).lower()
        for cat, keywords in self.CATEGORY_KEYWORDS.items():
            if any(kw in combined for kw in keywords):
                return cat
        prefix_map = {
            "MI": "Toan va Khoa hoc co ban",
            "PH": "Toan va Khoa hoc co ban",
            "CH": "Toan va Khoa hoc co ban",
            "IT": "Ky thuat chuyen nganh",
            "ET": "Ky thuat chuyen nganh",
            "FL": "Tieng Anh",
            "ED": "Giao duc the chat",
            "EM": "Co so nganh",
            "SSH": "Ly luan chinh tri",
        }
        for prefix, cat in prefix_map.items():
            if course_id.startswith(prefix):
                return cat
        return "Co so nganh"

    def _infer_department(self, course_id: str) -> str:
        dept_map = {
            "IT": "Vien Cong nghe Thong tin va Truyen thong",
            "ET": "Vien Dien tu - Vien thong",
            "MI": "Vien Toan ung dung va Tin hoc",
            "PH": "Vien Vat ly Ky thuat",
            "CH": "Vien Ky thuat Hoa hoc",
            "FL": "Vien Ngoai ngu",
            "EM": "Vien Kinh te va Quan ly",
            "ED": "Trung tam Giao duc The chat",
            "SSH": "Vien Su pham Ky thuat",
        }
        for prefix, dept in dept_map.items():
            if course_id.startswith(prefix):
                return dept
        return ""

    def _extract_major_name(self, text: str, file_name: str) -> Optional[str]:
        patterns = [
            r"nganh\s*(?:hoc|dao\s*tao)?\s*[:\-]?\s*([^\n]{5,60})",
            r"ngành\s*(?:học|đào\s*tạo)?\s*[:\-]?\s*([^\n]{5,60})",
            r"chuong\s*trinh\s*(?:dao\s*tao)?\s*nganh\s*([^\n]{5,60})",
            r"chương\s*trình\s*(?:đào\s*tạo)?\s*ngành\s*([^\n]{5,60})",
            r"(Cong\s*nghe\s*thong\s*tin|Công\s*nghệ\s*thông\s*tin)",
            r"(Khoa\s*hoc\s*may\s*tinh|Khoa\s*học\s*máy\s*tính)",
        ]
        for p in patterns:
            m = re.search(p, text[:3000], re.IGNORECASE | re.UNICODE)
            if m:
                groups = m.groups()
                r = groups[0].strip() if groups else m.group(0).strip()
                return r[:200]
        name_map = {
            "it1": "Cong nghe Thong tin",
            "it2": "Ky thuat May tinh",
            "it6": "Khoa hoc Du lieu",
            "quyche": "Quy che hoc vu chung",
        }
        stem = Path(file_name).stem.lower()
        for key, val in name_map.items():
            if key in stem:
                return val
        return None

    def _extract_total_credits(self, text: str) -> Optional[int]:
        m = self.TOTAL_CREDITS_PATTERN.search(text)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                pass
        alt = re.search(
            r"tổng[:\s]+(\d{3})\s*(?:TC|tín\s*chỉ|tin\s*chi)",
            text, re.IGNORECASE
        )
        if alt:
            try:
                return int(alt.group(1))
            except ValueError:
                pass
        return None

    def _extract_curriculum_version(self, text: str) -> Optional[str]:
        for p in [
            r"\b(K\d{2})\b",
            r"khoa\s+(\d{2,4})",
            r"khóa\s+(\d{2,4})",
            r"nam\s+hoc\s+(\d{4}[-]\d{4})",
            r"(20\d{2})",
        ]:
            m = re.search(p, text[:3000], re.IGNORECASE | re.UNICODE)
            if m:
                return m.group(1)
        return None

    def _is_mandatory_course(self, course_id: str, text: str) -> bool:
        idx = text.find(course_id)
        if idx == -1:
            return True
        ctx = text[max(0, idx - 100):idx + 200].lower()
        for kw in ["tu chon", "tự chọn", "elective", "khong bat buoc", "không bắt buộc"]:
            if kw in ctx:
                return False
        return True

    def _extract_proposed_semester(self, course_id: str, text: str) -> Optional[int]:
        idx = text.find(course_id)
        if idx == -1:
            return None
        ctx = text[max(0, idx - 50):idx + 200]
        m = re.search(
            r"(?:ky|hoc\s*ky|semester|sem|kỳ|học\s*kỳ)[:\s]*(\d+)",
            ctx, re.IGNORECASE | re.UNICODE,
        )
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                pass
        return None


# ===========================================================================
# 4. JSONL Writer
# ===========================================================================
class JSONLWriter:
    """
    Ghi du lieu ra cac file JSONL.

    Cau truc output:
      data/output/
        regulations.jsonl         -- Dieu khoan quy che (Regulations)
        courses.jsonl             -- Mon hoc (Courses + Categories)
        curriculums.jsonl         -- Chuong trinh dao tao (Curriculums)
        curriculum_details.jsonl  -- Chi tiet mon trong CTDT
        course_dependencies.jsonl -- Quan he tien quyet / song hanh
        chunks.jsonl              -- Tat ca text chunk (cho RAG)
        index.json                -- Index tong hop (metadata)
    """

    FILENAMES = {
        "regulations": "regulations.jsonl",
        "courses": "courses.jsonl",
        "curriculums": "curriculums.jsonl",
        "curriculum_details": "curriculum_details.jsonl",
        "course_dependencies": "course_dependencies.jsonl",
        "chunks": "chunks.jsonl",
    }

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        # Xoa file cu de ghi moi
        for fname in self.FILENAMES.values():
            fp = self.output_dir / fname
            if fp.exists():
                fp.unlink()
        logger.info(f"JSONL output dir: {self.output_dir.resolve()}")

    def _path(self, key: str) -> Path:
        return self.output_dir / self.FILENAMES[key]

    def _write_record(self, key: str, record: dict):
        """Ghi mot dong JSON vao file JSONL tuong ung."""
        with open(self._path(key), "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # ---- Public write methods ----

    def write_regulation(self, reg: dict):
        """
        Ghi vao regulations.jsonl.
        Schema: { reg_id, title, content_summary, document_url, created_at }
        """
        doc = {
            "reg_id": self._make_id(reg["title"]),
            "title": reg["title"],
            "content_summary": reg.get("content_summary", ""),
            "document_url": reg.get("document_url", ""),
            "created_at": _utcnow(),
        }
        self._write_record("regulations", doc)
        return doc["reg_id"]

    def write_course(self, course: dict):
        """
        Ghi vao courses.jsonl.
        Schema: { course_id, course_name, credits, description,
                  department, is_mandatory, category_name, created_at }
        """
        doc = {
            "course_id": course["course_id"],
            "course_name": course.get("course_name", ""),
            "credits": course.get("credits", 0),
            "description": course.get("description", ""),
            "department": course.get("department", ""),
            "is_mandatory": course.get("is_mandatory", True),
            "category_name": course.get("category_name", ""),
            "created_at": _utcnow(),
        }
        self._write_record("courses", doc)

    def write_curriculum(self, curriculum: dict) -> str:
        """
        Ghi vao curriculums.jsonl.
        Schema: { curriculum_id, major_name, total_credits_required, version }
        """
        doc = {
            "curriculum_id": self._make_id(
                f"{curriculum['major_name']}_{curriculum.get('version','')}"
            ),
            "major_name": curriculum["major_name"],
            "total_credits_required": curriculum.get("total_credits_required", 0),
            "version": curriculum.get("version", "N/A"),
            "created_at": _utcnow(),
        }
        self._write_record("curriculums", doc)
        return doc["curriculum_id"]

    def write_curriculum_details(
        self,
        curriculum_id: str,
        details: list[dict],
        known_course_ids: set[str],
    ):
        """
        Ghi vao curriculum_details.jsonl.
        Schema: { curriculum_id, course_id, is_required, semester_propose }
        """
        for d in details:
            if d["course_id"] not in known_course_ids:
                continue
            doc = {
                "curriculum_id": curriculum_id,
                "course_id": d["course_id"],
                "is_required": d.get("is_required", True),
                "semester_propose": d.get("semester_propose"),
                "created_at": _utcnow(),
            }
            self._write_record("curriculum_details", doc)

    def write_course_dependencies(
        self,
        dependencies: list[dict],
        known_course_ids: set[str],
    ):
        """
        Ghi vao course_dependencies.jsonl.
        Schema: { course_id, dependency_id, dependency_type }
        """
        for dep in dependencies:
            if (
                dep["course_id"] not in known_course_ids
                or dep["dependency_id"] not in known_course_ids
            ):
                continue
            doc = {
                "course_id": dep["course_id"],
                "dependency_id": dep["dependency_id"],
                "dependency_type": dep["dependency_type"],
                "created_at": _utcnow(),
            }
            self._write_record("course_dependencies", doc)

    def write_chunks(self, chunks: list[dict]):
        """
        Ghi cac text chunk vao chunks.jsonl.
        Schema: { chunk_uid, chunk_id, title, content, char_start,
                  source_file, source_path, doc_title }
        """
        for chunk in chunks:
            doc = {
                "chunk_uid": self._make_id(
                    chunk.get("source_file", "") + str(chunk.get("char_start", 0))
                ),
                **chunk,
                "created_at": _utcnow(),
            }
            self._write_record("chunks", doc)

    def write_index(self, stats: dict):
        """Ghi file index.json tom tat ket qua pipeline."""
        index = {
            "generated_at": _utcnow(),
            "files": {
                k: str(self._path(k)) for k in self.FILENAMES
            },
            "stats": stats,
        }
        index_path = self.output_dir / "index.json"
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
        logger.info(f"Index saved: {index_path}")

    @staticmethod
    def _make_id(seed: str) -> str:
        """Tao ID duy nhat dua tren noi dung (deterministic)."""
        return hashlib.md5(seed.encode("utf-8")).hexdigest()[:12]

    # ---- Read helpers (de agent su dung) ----

    @staticmethod
    def load_jsonl(path: str | Path) -> list[dict]:
        """Doc tat ca ban ghi tu mot file JSONL."""
        path = Path(path)
        if not path.exists():
            return []
        records = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        return records


# ===========================================================================
# 5. ChromaDB Writer (NoSQL vector store)
# ===========================================================================
class ChromaWriter:
    """
    Luu cac text chunk vao ChromaDB de agent thuc hien semantic search.

    Collection 'regulation_chunks':
      - id       : chunk_uid (deterministic MD5)
      - document : noi dung text chunk
      - metadata : source_file, doc_title, title, char_start, chunk_id
                   course_ids (cac ma mon xuat hien trong chunk)

    Agent co the query bang:
      collection.query(query_texts=["cau hoi"], n_results=5)
    """

    COLLECTION_NAME = "regulation_chunks"

    def __init__(self, chroma_dir: str | Path):
        self.chroma_dir = Path(chroma_dir)
        self.chroma_dir.mkdir(parents=True, exist_ok=True)
        self._client = None
        self._collection = None

    def _get_collection(self):
        """Lazy-init ChromaDB client va collection."""
        if self._collection is not None:
            return self._collection
        try:
            import chromadb
            self._client = chromadb.PersistentClient(path=str(self.chroma_dir))
            # Xoa collection cu neu ton tai de dam bao sach
            try:
                self._client.delete_collection(self.COLLECTION_NAME)
                logger.info(f"Da xoa ChromaDB collection cu: {self.COLLECTION_NAME}")
            except Exception:
                pass
            self._collection = self._client.create_collection(
                name=self.COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(
                f"ChromaDB collection tao thanh cong: {self.COLLECTION_NAME} "
                f"tai {self.chroma_dir.resolve()}"
            )
            return self._collection
        except ImportError:
            raise ImportError(
                "Thieu thu vien chromadb. Cai bang: pip install chromadb"
            )

    def upsert_chunks(self, chunks: list[dict], batch_size: int = 200):
        """
        Them cac chunk vao ChromaDB theo batch.

        ChromaDB tu dong embedding voi default embedding function
        (all-MiniLM-L6-v2) neu khong chi dinh model.
        """
        collection = self._get_collection()
        course_code_re = re.compile(r"\b([A-Z]{2,4}\d{4,5}[A-Z]?)\b")

        ids, docs, metadatas = [], [], []
        for chunk in chunks:
            cid = hashlib.md5(
                (chunk.get("source_file", "") + str(chunk.get("char_start", 0))).encode()
            ).hexdigest()[:12]

            # Trich xuat cac ma mon trong chunk
            course_ids_found = course_code_re.findall(chunk.get("content", ""))

            meta = {
                "source_file": chunk.get("source_file", ""),
                "doc_title": chunk.get("doc_title", "")[:100],
                "title": chunk.get("title", "")[:200],
                "char_start": chunk.get("char_start", 0),
                "chunk_id": chunk.get("chunk_id", 0),
                "course_ids": ",".join(set(course_ids_found)),
            }
            ids.append(cid)
            docs.append(chunk.get("content", ""))
            metadatas.append(meta)

        # Ghi theo batch
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i + batch_size]
            batch_docs = docs[i:i + batch_size]
            batch_metas = metadatas[i:i + batch_size]
            # Loc bo doc rong
            filtered = [
                (bid, bdoc, bmeta)
                for bid, bdoc, bmeta in zip(batch_ids, batch_docs, batch_metas)
                if bdoc.strip()
            ]
            if not filtered:
                continue
            f_ids, f_docs, f_metas = zip(*filtered)
            collection.upsert(
                ids=list(f_ids),
                documents=list(f_docs),
                metadatas=list(f_metas),
            )
        logger.info(f"  ChromaDB: da upsert {len(ids)} chunks vao '{self.COLLECTION_NAME}'")

    def query(self, query_text: str, n_results: int = 5) -> list[dict]:
        """
        Tim kiem semantic trong ChromaDB.
        Dung boi agent de tra loi cau hoi.

        Returns:
            list[dict] – moi phan tu co: content, metadata, distance
        """
        collection = self._get_collection()
        results = collection.query(
            query_texts=[query_text],
            n_results=n_results,
        )
        output = []
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        dists = results.get("distances", [[]])[0]
        for doc, meta, dist in zip(docs, metas, dists):
            output.append({
                "content": doc,
                "metadata": meta,
                "distance": dist,
                "relevance_score": round(1 - dist, 4),
            })
        return output

    def count(self) -> int:
        """Dem so chunk trong collection."""
        col = self._get_collection()
        return col.count()


# ===========================================================================
# 6. Pipeline chinh
# ===========================================================================
def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class RegulationProcessor:
    """
    Pipeline ETL:
      PDF files
        --> Extract (PDFReader + RegulationExtractor)
        --> Transform (normalize, deduplicate)
        --> Load
            --> JSONL files (data/output/*.jsonl)
            --> ChromaDB   (data/output/chroma/)
    """

    def __init__(
        self,
        regulations_dir: str | Path = REGULATIONS_DIR,
        output_dir: str | Path = OUTPUT_DIR,
        dry_run: bool = False,
        use_chroma: bool = True,
    ):
        self.regulations_dir = Path(regulations_dir)
        self.output_dir = Path(output_dir)
        self.dry_run = dry_run
        self.use_chroma = use_chroma

        self.reader = PDFReader()
        self.extractor = RegulationExtractor()

        if not dry_run:
            self.jsonl_writer = JSONLWriter(output_dir)
            self.chroma_writer = ChromaWriter(self.output_dir / "chroma") if use_chroma else None
        else:
            self.jsonl_writer = None
            self.chroma_writer = None

        self.stats = {
            "pdfs_processed": 0,
            "regulations_written": 0,
            "courses_written": 0,
            "curriculums_written": 0,
            "curriculum_details_written": 0,
            "dependencies_written": 0,
            "chunks_written": 0,
            "errors": [],
        }

        # Track tat ca course_id da ghi (cross-file dedup)
        self._all_course_ids: set[str] = set()

    def run(self) -> dict:
        logger.info("=" * 60)
        logger.info("PIPELINE XU LY QUY CHE -> JSONL + ChromaDB")
        logger.info("=" * 60)

        pdf_files = self.reader.find_pdfs(self.regulations_dir)
        if not pdf_files:
            logger.warning(f"Khong tim thay PDF nao trong: {self.regulations_dir}")
            return self.stats

        logger.info(f"Tim thay {len(pdf_files)} file PDF: {[Path(p).name for p in pdf_files]}")

        all_data = []
        all_chunks = []

        for pdf_path in pdf_files:
            result = self._process_single_pdf(pdf_path)
            if result:
                all_data.append(result)
                all_chunks.extend(result["chunks"])
                self.stats["pdfs_processed"] += 1

        if self.dry_run:
            self._print_dry_run(all_data)
        else:
            self._write_all(all_data, all_chunks)

        self._print_stats()
        return self.stats

    # ------------------------------------------------------------------
    # Extract
    # ------------------------------------------------------------------

    def _process_single_pdf(self, pdf_path: str) -> Optional[dict]:
        file_name = Path(pdf_path).name
        logger.info(f"\n-- Xu ly: {file_name}")
        try:
            doc = self.reader.read(pdf_path)
            logger.info(f"   Trang: {doc['total_pages']} | Ky tu: {len(doc['full_text']):,}")

            reg_record = self.extractor.extract_regulation_record(doc)
            reg_topics = self.extractor.extract_regulation_topics(doc)
            courses = self.extractor.extract_courses(doc)
            curriculum = self.extractor.extract_curriculum(doc)
            dependencies = self.extractor.extract_course_dependencies(doc)
            chunks = self.extractor.extract_chunks(doc)

            curriculum_details = []
            if curriculum:
                curriculum_details = self.extractor.extract_curriculum_details(doc, courses)

            logger.info(f"   Quy che: 1 + {len(reg_topics)} chu de")
            logger.info(f"   Mon hoc: {len(courses)}")
            logger.info(f"   CTDT: {'Co' if curriculum else 'Khong'}")
            logger.info(f"   Tien quyet: {len(dependencies)}")
            logger.info(f"   Chunks: {len(chunks)}")

            return {
                "file_name": file_name,
                "file_path": pdf_path,
                "reg_record": reg_record,
                "reg_topics": reg_topics,
                "courses": courses,
                "curriculum": curriculum,
                "curriculum_details": curriculum_details,
                "dependencies": dependencies,
                "chunks": chunks,
            }
        except Exception as e:
            logger.error(f"   LOI khi xu ly {file_name}: {e}", exc_info=True)
            self.stats["errors"].append({"file": file_name, "error": str(e)})
            return None

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------

    def _write_all(self, all_data: list[dict], all_chunks: list[dict]):
        logger.info("\n-- Ghi JSONL...")

        # 1. Collect tat ca course_id truoc (can de validate FK)
        for data in all_data:
            for c in data["courses"]:
                self._all_course_ids.add(c["course_id"])

        for data in all_data:
            fname = data["file_name"]
            logger.info(f"  Ghi tu: {fname}")

            try:
                # Regulations
                self.jsonl_writer.write_regulation(data["reg_record"])
                self.stats["regulations_written"] += 1
                for topic in data["reg_topics"]:
                    self.jsonl_writer.write_regulation(topic)
                    self.stats["regulations_written"] += 1

                # Courses
                for c in data["courses"]:
                    self.jsonl_writer.write_course(c)
                    self.stats["courses_written"] += 1

                # Curriculum
                curriculum_id = None
                if data["curriculum"]:
                    curriculum_id = self.jsonl_writer.write_curriculum(data["curriculum"])
                    self.stats["curriculums_written"] += 1

                # Curriculum Details
                if curriculum_id and data["curriculum_details"]:
                    self.jsonl_writer.write_curriculum_details(
                        curriculum_id,
                        data["curriculum_details"],
                        self._all_course_ids,
                    )
                    self.stats["curriculum_details_written"] += len(data["curriculum_details"])

                # Dependencies
                if data["dependencies"]:
                    self.jsonl_writer.write_course_dependencies(
                        data["dependencies"], self._all_course_ids
                    )
                    self.stats["dependencies_written"] += len(data["dependencies"])

            except Exception as e:
                logger.error(f"  LOI ghi JSONL tu {fname}: {e}", exc_info=True)
                self.stats["errors"].append({"file": fname, "error": str(e)})

        # Chunks - ghi tat ca cung luc sau khi loop
        logger.info(f"  Ghi {len(all_chunks)} chunks vao chunks.jsonl...")
        self.jsonl_writer.write_chunks(all_chunks)
        self.stats["chunks_written"] = len(all_chunks)

        # ChromaDB
        if self.use_chroma and self.chroma_writer:
            logger.info(f"\n-- Ghi ChromaDB ({len(all_chunks)} chunks)...")
            try:
                self.chroma_writer.upsert_chunks(all_chunks)
                logger.info(f"  ChromaDB count: {self.chroma_writer.count()} records")
            except Exception as e:
                logger.error(f"  LOI ChromaDB: {e}", exc_info=True)
                self.stats["errors"].append({"file": "chroma", "error": str(e)})

        # Index file
        self.jsonl_writer.write_index(self.stats)

    # ------------------------------------------------------------------
    # Dry run
    # ------------------------------------------------------------------

    def _print_dry_run(self, all_data: list[dict]):
        logger.info("\n" + "=" * 60)
        logger.info("DRY RUN - KET QUA TRICH XUAT (khong ghi file)")
        logger.info("=" * 60)

        for data in all_data:
            print(f"\n{'─' * 50}")
            print(f"FILE: {data['file_name']}")

            print("\n[Regulation Record]")
            print(json.dumps(data["reg_record"], ensure_ascii=False, indent=2))

            print(f"\n[Regulation Topics] ({len(data['reg_topics'])} chu de)")
            for t in data["reg_topics"]:
                print(f"  * {t['title']}")

            print(f"\n[Courses] ({len(data['courses'])} mon)")
            for c in data["courses"][:8]:
                print(
                    f"  * {c['course_id']} | {c['course_name'][:40]:<40} "
                    f"| {c['credits']} TC | {c.get('category_name','')}"
                )
            if len(data["courses"]) > 8:
                print(f"  ... va {len(data['courses']) - 8} mon khac")

            if data["curriculum"]:
                print("\n[Curriculum]")
                print(json.dumps(data["curriculum"], ensure_ascii=False, indent=2))

            print(f"\n[Curriculum Details] ({len(data['curriculum_details'])} muc)")
            for d in data["curriculum_details"][:5]:
                req = "Bat buoc" if d["is_required"] else "Tu chon"
                print(f"  * {d['course_id']} | {req} | Ky {d['semester_propose']}")

            print(f"\n[Dependencies] ({len(data['dependencies'])} quan he)")
            for dep in data["dependencies"][:5]:
                print(f"  * {dep['course_id']} --[{dep['dependency_type']}]--> {dep['dependency_id']}")

            print(f"\n[Chunks] ({len(data['chunks'])} chunk)")
            for ch in data["chunks"][:3]:
                print(f"  # Chunk {ch['chunk_id']}: {ch['title'][:60]}")
                print(f"    {ch['content'][:120]}...")

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def _print_stats(self):
        logger.info("\n" + "=" * 60)
        logger.info("KET QUA PIPELINE")
        logger.info("=" * 60)
        logger.info(f"  PDFs da xu ly     : {self.stats['pdfs_processed']}")
        logger.info(f"  Regulations ghi   : {self.stats['regulations_written']}")
        logger.info(f"  Mon hoc ghi       : {self.stats['courses_written']}")
        logger.info(f"  Chuong trinh ghi  : {self.stats['curriculums_written']}")
        logger.info(f"  CT Chi tiet ghi   : {self.stats['curriculum_details_written']}")
        logger.info(f"  Tien quyet ghi    : {self.stats['dependencies_written']}")
        logger.info(f"  Chunks ghi        : {self.stats['chunks_written']}")
        if not self.dry_run:
            logger.info(f"  Output dir        : {self.output_dir.resolve()}")
        if self.stats["errors"]:
            logger.warning(f"  Loi               : {len(self.stats['errors'])}")
            for err in self.stats["errors"]:
                logger.warning(f"    - {err['file']}: {err['error']}")
        logger.info("=" * 60)
        status = "HOAN THANH THANH CONG!" if not self.stats["errors"] else "HOAN THANH VOI LOI."
        logger.info(status)


# ===========================================================================
# 7. Agent-facing helper functions
#    (import tu regulation_agent.py hoac agent bat ky)
# ===========================================================================

def load_all_regulations(output_dir: str | Path = OUTPUT_DIR) -> list[dict]:
    """
    Doc tat ca ban ghi Regulations tu regulations.jsonl.

    Usage (trong agent):
        from data.processing_regulation import load_all_regulations
        regs = load_all_regulations()
    """
    return JSONLWriter.load_jsonl(Path(output_dir) / "regulations.jsonl")


def load_all_courses(output_dir: str | Path = OUTPUT_DIR) -> list[dict]:
    """Doc tat ca mon hoc tu courses.jsonl."""
    return JSONLWriter.load_jsonl(Path(output_dir) / "courses.jsonl")


def load_all_chunks(output_dir: str | Path = OUTPUT_DIR) -> list[dict]:
    """Doc tat ca text chunk tu chunks.jsonl (cho RAG thu cong)."""
    return JSONLWriter.load_jsonl(Path(output_dir) / "chunks.jsonl")


def load_curriculum(output_dir: str | Path = OUTPUT_DIR) -> list[dict]:
    """Doc tat ca chuong trinh dao tao tu curriculums.jsonl."""
    return JSONLWriter.load_jsonl(Path(output_dir) / "curriculums.jsonl")


def load_curriculum_details(output_dir: str | Path = OUTPUT_DIR) -> list[dict]:
    """Doc chi tiet mon hoc trong CTDT tu curriculum_details.jsonl."""
    return JSONLWriter.load_jsonl(Path(output_dir) / "curriculum_details.jsonl")


def load_course_dependencies(output_dir: str | Path = OUTPUT_DIR) -> list[dict]:
    """Doc quan he tien quyet / song hanh tu course_dependencies.jsonl."""
    return JSONLWriter.load_jsonl(Path(output_dir) / "course_dependencies.jsonl")


def search_chunks_jsonl(
    query: str,
    output_dir: str | Path = OUTPUT_DIR,
    top_k: int = 5,
) -> list[dict]:
    """
    Tim kiem keyword trong chunks.jsonl (khong can ChromaDB).

    Agent su dung khi ChromaDB chua san sang hoac can fallback.

    Returns:
        list[dict] – cac chunk lien quan, sap xep theo diem relevance.
    """
    chunks = load_all_chunks(output_dir)
    query_lower = query.lower()
    keywords = [w for w in re.findall(r"\w+", query_lower) if len(w) > 1]

    scored = []
    for chunk in chunks:
        content_lower = chunk.get("content", "").lower()
        title_lower = chunk.get("title", "").lower()
        score = 0
        if query_lower in content_lower:
            score += 10
        for kw in keywords:
            score += content_lower.count(kw) * 2
            if kw in title_lower:
                score += 3
        if score > 0:
            scored.append({**chunk, "relevance_score": score})

    scored.sort(key=lambda c: c["relevance_score"], reverse=True)
    return scored[:top_k]


def search_chunks_chroma(
    query: str,
    output_dir: str | Path = OUTPUT_DIR,
    n_results: int = 5,
) -> list[dict]:
    """
    Tim kiem semantic trong ChromaDB.

    Agent su dung khi can do chinh xac cao hon keyword search.

    Returns:
        list[dict] – moi phan tu co: content, metadata, distance, relevance_score
    """
    writer = ChromaWriter(Path(output_dir) / "chroma")
    return writer.query(query, n_results=n_results)


# ===========================================================================
# 8. CLI
# ===========================================================================
def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Xu ly PDF quy che -> JSONL + ChromaDB cho agent RAG."
    )
    parser.add_argument(
        "--regulations-dir",
        default=str(REGULATIONS_DIR),
        help=f"Thu muc chua PDF (mac dinh: {REGULATIONS_DIR})",
    )
    parser.add_argument(
        "--output-dir",
        default=str(OUTPUT_DIR),
        help=f"Thu muc dau ra (mac dinh: {OUTPUT_DIR})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Chi in ket qua, khong ghi file",
    )
    parser.add_argument(
        "--no-chroma",
        action="store_true",
        help="Bo qua ChromaDB, chi ghi JSONL",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    return parser.parse_args()


def main():
    args = _parse_args()
    logging.getLogger().setLevel(getattr(logging, args.log_level))

    processor = RegulationProcessor(
        regulations_dir=args.regulations_dir,
        output_dir=args.output_dir,
        dry_run=args.dry_run,
        use_chroma=not args.no_chroma,
    )
    stats = processor.run()
    sys.exit(1 if stats["errors"] else 0)


if __name__ == "__main__":
    main()
