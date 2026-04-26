"""
Tool definitions for the Academic Planning Agent.
Implements all functions defined in PRD.md across 3 functional groups:
  1. Xác định user background
  2. Gợi ý đăng ký môn học, lịch học, lộ trình tốt nghiệp
  3. Lập kế hoạch và giám sát tiến độ học tập, ôn tập

Each tool is a method on AcademicTools, and is also registered in the
TOOLS dict so the agent can call get_tool_schemas() / execute_tool().
"""

import os
import json
import base64
import sqlite3
import logging
import mimetypes
from typing import Any, Optional
from datetime import datetime
from pathlib import Path

from anthropic import Anthropic

from .config import ANTHROPIC_API_KEY, DEFAULT_MODEL, OPENAI_API_KEY
from ..regulation_agent import query_regulation, search_regulation

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Extraction prompt cho LLM
# ---------------------------------------------------------------------------
_EXTRACT_USER_INFO_PROMPT = """\
Bạn là trợ lý trích xuất thông tin sinh viên. Phân tích nội dung (text và/hoặc ảnh) \
được cung cấp và trích xuất TẤT CẢ thông tin có thể tìm thấy.

Trả về JSON object với các trường sau (nếu không tìm thấy, để null):

{
  "student_id": "Mã sinh viên (VD: 20210001)",
  "full_name": "Họ tên đầy đủ",
  "year": "Năm / Khóa (VD: K66, năm 3)",
  "major": "Ngành học (VD: Công nghệ thông tin)",
  "faculty": "Khoa / Viện",
  "current_cpa": 0.0,
  "target_cpa": null,
  "credits_passed": 0,
  "credits_failed": 0,
  "warning_level": "Mức cảnh cáo học vụ (nếu có)",
  "max_credits_allowed": null,
  "courses": [
    {
      "course_id": "Mã môn",
      "course_name": "Tên môn",
      "credits": 3,
      "grade_letter": "A",
      "grade_number": 3.7,
      "semester": "20231",
      "is_passed": true
    }
  ],
  "additional_info": "Thông tin bổ sung khác phát hiện được"
}

QUY TẮC:
- Trích xuất tất cả thông tin có thể, dù chỉ một phần.
- Nếu ảnh là bảng điểm, trích xuất ĐẦY ĐỦ danh sách môn học.
- Nếu ảnh là thẻ sinh viên, trích xuất thông tin cá nhân.
- Nếu là text mô tả, trích xuất các thông tin được đề cập.
- PHẢI trả về JSON hợp lệ, KHÔNG markdown code block.
- Nếu không chắc chắn một giá trị, vẫn ghi nhận và thêm "(chưa chắc chắn)" vào additional_info.
"""


# ---------------------------------------------------------------------------
# Database helper
# ---------------------------------------------------------------------------
class DatabaseManager:
    """Thin wrapper around sqlite3 to run queries safely."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Return dict-like rows
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def execute(self, query: str, params: tuple = (), fetchall: bool = True):
        """Execute *query* with *params* and return rows."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            if fetchall:
                return [dict(row) for row in cursor.fetchall()]
            row = cursor.fetchone()
            return dict(row) if row else None

    def execute_write(self, query: str, params: tuple = ()):
        """Execute an INSERT / UPDATE / DELETE and commit."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount


# ---------------------------------------------------------------------------
# AcademicTools – all business-logic tools live here
# ---------------------------------------------------------------------------
class AcademicTools:
    """
    Implements every tool listed in the PRD.
    Instantiate with a database path, then call any method directly
    or go through execute_tool() for agent integration.
    """

    def __init__(self, db_path: str):
        self.db = DatabaseManager(db_path)
        self._anthropic_client: Optional[Anthropic] = None

    def _get_anthropic_client(self) -> Anthropic:
        """Lazy-init Anthropic client for LLM calls."""
        if self._anthropic_client is None:
            api_key = ANTHROPIC_API_KEY
            if not api_key:
                raise ValueError(
                    "ANTHROPIC_API_KEY chưa được cấu hình. Kiểm tra file .env"
                )
            self._anthropic_client = Anthropic(api_key=api_key)
        return self._anthropic_client

    # ===================================================================
    # GROUP 1 – Xác định user background
    # ===================================================================

    def get_user_history(self, user_id: str) -> dict:
        """
        Lấy thông tin kết quả học tập người dùng trong CSDL.

        Trả về:
            user_history: dict chứa thông tin sinh viên, CPA, tín chỉ,
            danh sách môn đã học kèm điểm.
        """
        student = self.db.execute(
            """
            SELECT s.student_id, s.full_name, s.current_cpa, 
                   c.curriculum_id, c.major_name, c.total_credits_required
            FROM Students s
            JOIN Curriculums c ON s.curriculum_id = c.curriculum_id
            WHERE s.student_id = ?
            """,
            (user_id,),
            fetchall=False,
        )
        if not student:
            return {"error": f"Không tìm thấy sinh viên với mã '{user_id}'."}

        transcripts = self.db.execute(
            """
            SELECT st.course_id, co.course_name, co.credits,
                   st.semester_id, st.grade_letter, st.grade_number, st.is_passed
            FROM Student_Transcripts st
            JOIN Courses co ON st.course_id = co.course_id
            WHERE st.student_id = ?
            ORDER BY st.semester_id
            """,
            (user_id,),
        )

        passed = [t for t in transcripts if t["is_passed"]]
        failed = [t for t in transcripts if not t["is_passed"]]
        credits_passed = sum(t["credits"] for t in passed)
        credits_failed = sum(t["credits"] for t in failed)

        return {
            "student_id": student["student_id"],
            "full_name": student["full_name"],
            "major_name": student["major_name"],
            "curriculum_id": student["curriculum_id"],
            "current_cpa": float(student["current_cpa"]),
            "total_credits_required": student["total_credits_required"],
            "credits_passed": credits_passed,
            "credits_failed": credits_failed,
            "credits_remaining": student["total_credits_required"] - credits_passed,
            "transcripts": transcripts,
            "passed_courses": passed,
            "failed_courses": failed,
        }

    # ----- Image helpers -----

    @staticmethod
    def _load_image_as_base64(image_path: str) -> tuple[str, str]:
        """
        Đọc file ảnh và trả về (base64_data, media_type).

        Hỗ trợ: PNG, JPEG, GIF, WEBP.
        """
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Không tìm thấy file ảnh: {image_path}")

        mime_type, _ = mimetypes.guess_type(str(path))
        if mime_type not in ("image/png", "image/jpeg", "image/gif", "image/webp"):
            raise ValueError(
                f"Định dạng ảnh không hỗ trợ: {mime_type}. "
                "Chỉ hỗ trợ PNG, JPEG, GIF, WEBP."
            )

        with open(path, "rb") as f:
            data = base64.standard_b64encode(f.read()).decode("utf-8")

        return data, mime_type

    @staticmethod
    def _is_url(s: str) -> bool:
        """Kiểm tra string có phải URL không."""
        return s.startswith("http://") or s.startswith("https://")

    @staticmethod
    def _is_base64(s: str) -> bool:
        """Kiểm tra string có phải base64 encoded data không."""
        try:
            if len(s) > 200:
                base64.b64decode(s[:100], validate=True)
                return True
        except Exception:
            pass
        return False

    def extract_user_input(
        self,
        user_input: str,
        image_paths: list[str] = None,
        image_base64_list: list[dict] = None,
    ) -> dict:
        """
        Trích xuất thông tin người dùng từ text và/hoặc ảnh.

        Sử dụng Claude Vision API để phân tích ảnh bảng điểm, thẻ SV, ảnh chụp
        màn hình, v.v., kết hợp text input để trích xuất thông tin đầy đủ.

        Args:
            user_input: Text mô tả hoặc câu hỏi của người dùng.
            image_paths: Danh sách đường dẫn tới file ảnh (local paths).
                         VD: ["transcript.png", "student_card.jpg"]
            image_base64_list: Danh sách ảnh dạng base64.
                         VD: [{"data": "iVBOR...", "media_type": "image/png"}]

        Trả về:
            dict chứa thông tin trích xuất:
            {
                "student_id", "full_name", "year", "major", "faculty",
                "current_cpa", "target_cpa", "credits_passed", "credits_failed",
                "warning_level", "max_credits_allowed", "courses": [...],
                "additional_info", "input_sources": [...]
            }
        """
        # ----- Build message content blocks -----
        content_blocks = []
        input_sources = []

        # 1. Xử lý ảnh từ file paths
        if image_paths:
            for img_path in image_paths:
                try:
                    b64_data, media_type = self._load_image_as_base64(img_path)
                    content_blocks.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": b64_data,
                        },
                    })
                    input_sources.append({
                        "type": "image_file",
                        "path": img_path,
                    })
                    logger.info(f"Đã load ảnh: {img_path}")
                except Exception as e:
                    logger.error(f"Lỗi load ảnh {img_path}: {e}")
                    input_sources.append({
                        "type": "image_file",
                        "path": img_path,
                        "error": str(e),
                    })

        # 2. Xử lý ảnh base64 truyền trực tiếp
        if image_base64_list:
            for i, img_data in enumerate(image_base64_list):
                content_blocks.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": img_data.get("media_type", "image/png"),
                        "data": img_data["data"],
                    },
                })
                input_sources.append({"type": "image_base64", "index": i})

        # 3. Xử lý URL ảnh trong user_input
        import re
        url_pattern = re.compile(
            r'(https?://\S+\.(?:png|jpg|jpeg|gif|webp)(?:\?\S*)?)',
            re.IGNORECASE,
        )
        urls = url_pattern.findall(user_input)
        for url in urls:
            content_blocks.append({
                "type": "image",
                "source": {"type": "url", "url": url},
            })
            input_sources.append({"type": "image_url", "url": url})

        # 4. Thêm text input
        text_prompt = (
            f"Đây là thông tin người dùng cung cấp:\n\n"
            f"{user_input}\n\n"
            f"Hãy trích xuất tất cả thông tin sinh viên từ nội dung trên"
        )
        if content_blocks:
            text_prompt += " và từ các ảnh đính kèm"
        text_prompt += "."

        content_blocks.append({"type": "text", "text": text_prompt})
        input_sources.append({"type": "text", "content": user_input[:200]})

        # ----- Gọi Claude API -----
        try:
            client = self._get_anthropic_client()
            response = client.messages.create(
                model=DEFAULT_MODEL,
                max_tokens=4096,
                system=_EXTRACT_USER_INFO_PROMPT,
                messages=[{"role": "user", "content": content_blocks}],
            )

            # Parse response
            raw_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    raw_text += block.text

            # Tìm JSON trong response
            extracted = self._parse_json_response(raw_text)

            if extracted:
                extracted["input_sources"] = input_sources
                extracted["_raw_llm_response"] = raw_text[:500]
                return extracted
            else:
                return {
                    "error": "Không thể parse JSON từ LLM response.",
                    "raw_response": raw_text,
                    "input_sources": input_sources,
                }

        except Exception as e:
            logger.error(f"Lỗi khi gọi LLM trích xuất thông tin: {e}")
            return {
                "error": f"Lỗi khi trích xuất: {str(e)}",
                "raw_input": user_input,
                "input_sources": input_sources,
            }

    @staticmethod
    def _parse_json_response(text: str) -> Optional[dict]:
        """
        Parse JSON từ LLM response. Xử lý cả trường hợp JSON
        nằm trong markdown code block.
        """
        import re

        # Thử parse trực tiếp
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass

        # Tìm JSON trong markdown code block
        code_block = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if code_block:
            try:
                return json.loads(code_block.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Tìm JSON object đầu tiên trong text
        brace_match = re.search(r"\{.*\}", text, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group())
            except json.JSONDecodeError:
                pass

        return None

    def get_curriculum(self, major_id: str) -> dict:
        """
        Lấy thông tin chương trình đào tạo trong CSDL.

        Args:
            major_id: curriculum_id (str hoặc int dạng chuỗi)

        Trả về:
            curriculum: dict gồm thông tin chung + danh sách môn học.
        """
        curriculum = self.db.execute(
            "SELECT * FROM Curriculums WHERE curriculum_id = ?",
            (major_id,),
            fetchall=False,
        )
        if not curriculum:
            return {"error": f"Không tìm thấy chương trình đào tạo '{major_id}'."}

        details = self.db.execute(
            """
            SELECT cd.course_id, co.course_name, co.credits, co.is_mandatory,
                   cd.is_required, cd.semester_propose,
                   cat.category_name
            FROM Curriculum_Details cd
            JOIN Courses co ON cd.course_id = co.course_id
            LEFT JOIN Course_Categories cat ON co.category_id = cat.category_id
            WHERE cd.curriculum_id = ?
            ORDER BY cd.semester_propose, co.course_id
            """,
            (major_id,),
        )

        return {
            "curriculum_id": curriculum["curriculum_id"],
            "major_name": curriculum["major_name"],
            "total_credits_required": curriculum["total_credits_required"],
            "version": curriculum["version"],
            "courses": details,
        }

    def extract_transcript(self, transcript: str) -> dict:
        """
        Trích xuất thông tin từ bảng điểm (transcript text/image).

        Bao gồm: các môn đã học / chưa học / trượt, CPA hiện tại,
        số tín chỉ đã qua / còn lại / trượt.

        NOTE: Hàm này cần OCR hoặc LLM parse. Tại layer tools chỉ trả
        placeholder cho Agent xử lý.
        """
        return {
            "raw_transcript": transcript,
            "note": (
                "Hàm này cần Agent gọi LLM/OCR để trích xuất: "
                "danh sách môn, điểm, CPA, tín chỉ."
            ),
        }

    def is_downgraded_degree(self, n_failed_credits: int) -> bool:
        """
        Kiểm tra có bị hạ bằng không dựa trên số tín chỉ trượt.

        Quy chế mặc định:
          - Trượt > 8 tín chỉ → hạ bằng (giỏi/xuất sắc bị hạ).

        Args:
            n_failed_credits: Tổng số tín chỉ các môn bị trượt (grade F).

        Trả về:
            True nếu bị hạ bằng, False nếu không.
        """
        # Có thể mở rộng: đọc ngưỡng từ bảng Regulations
        THRESHOLD = 8
        return n_failed_credits > THRESHOLD

    def update_user_history(self, user_id: str, updates: dict) -> dict:
        """
        Cập nhật thông tin lịch sử người dùng trong CSDL.

        Args:
            user_id: Mã sinh viên.
            updates: dict chứa các trường cần cập nhật,
                     VD: {"target_cpa": 3.6, "current_cpa": 3.2}

        Trả về:
            Kết quả cập nhật.
        """
        allowed_fields = {"target_cpa", "current_cpa"}
        set_clauses = []
        params = []
        for field, value in updates.items():
            if field not in allowed_fields:
                continue
            set_clauses.append(f"{field} = ?")
            params.append(value)

        if not set_clauses:
            return {"error": "Không có trường hợp lệ để cập nhật."}

        params.append(user_id)
        query = f"UPDATE Students SET {', '.join(set_clauses)} WHERE student_id = ?"
        affected = self.db.execute_write(query, tuple(params))
        return {
            "updated": affected > 0,
            "rows_affected": affected,
            "fields_updated": list(updates.keys()),
        }

    # ===================================================================
    # GROUP 2 – Gợi ý đăng ký môn học, lịch học, lộ trình tốt nghiệp
    # ===================================================================

    def get_prerequisites(self, course_id: str) -> list:
        """
        Lấy thông tin điều kiện tiên quyết / song hành của một môn học.

        Trả về:
            prerequisites: list[dict] – mỗi phần tử gồm
            dependency_id, course_name, dependency_type.
        """
        rows = self.db.execute(
            """
            SELECT cd.dependency_id, co.course_name, co.credits,
                   cd.dependency_type
            FROM Course_Dependencies cd
            JOIN Courses co ON cd.dependency_id = co.course_id
            WHERE cd.course_id = ?
            """,
            (course_id,),
        )
        return rows

    def filter_eligible_courses(self, user_history: dict) -> list:
        """
        Lọc ra danh sách các môn mà sinh viên đủ điều kiện đăng ký.

        Logic:
            1. Lấy tất cả môn trong chương trình đào tạo.
            2. Loại bỏ các môn đã passed.
            3. Kiểm tra tiên quyết đã hoàn thành.

        Args:
            user_history: dict (output của get_user_history).

        Trả về:
            eligible_courses: list[dict] – các môn đủ điều kiện.
        """
        curriculum_id = user_history.get("curriculum_id")
        passed_ids = {c["course_id"] for c in user_history.get("passed_courses", [])}

        # Tất cả môn trong chương trình
        all_courses = self.db.execute(
            """
            SELECT cd.course_id, co.course_name, co.credits,
                   cd.is_required, cd.semester_propose
            FROM Curriculum_Details cd
            JOIN Courses co ON cd.course_id = co.course_id
            WHERE cd.curriculum_id = ?
            """,
            (curriculum_id,),
        )

        eligible = []
        for course in all_courses:
            cid = course["course_id"]
            if cid in passed_ids:
                continue  # Đã passed → bỏ qua

            # Kiểm tra prerequisites
            prereqs = self.db.execute(
                """
                SELECT dependency_id FROM Course_Dependencies
                WHERE course_id = ? AND dependency_type IN ('Prerequisite', 'Pre-condition')
                """,
                (cid,),
            )
            prereq_ids = {r["dependency_id"] for r in prereqs}
            if prereq_ids.issubset(passed_ids):
                course["prerequisites_met"] = True
                eligible.append(course)

        return eligible

    def get_open_courses(self, semester: str) -> list:
        """
        Lấy danh sách các môn mở trong kỳ.

        Args:
            semester: semester_id (VD: '20251')

        Trả về:
            open_courses: list[dict] – mỗi môn kèm số lớp mở.
        """
        rows = self.db.execute(
            """
            SELECT DISTINCT cl.course_id, co.course_name, co.credits,
                   COUNT(cl.class_id) AS num_classes,
                   SUM(cl.max_slots - cl.current_slots) AS available_slots
            FROM Classes cl
            JOIN Courses co ON cl.course_id = co.course_id
            WHERE cl.semester_id = ?
            GROUP BY cl.course_id
            """,
            (semester,),
        )
        return rows

    def get_open_classes(self, course_id: str) -> list:
        """
        Lấy danh sách các lớp mở của một môn học trong kỳ hiện tại.

        Args:
            course_id: Mã môn học.

        Trả về:
            open_classes: list[dict] – thông tin từng lớp (lịch, phòng, GV, …).
        """
        rows = self.db.execute(
            """
            SELECT cl.class_id, cl.course_id, co.course_name,
                   cl.semester_id, cl.instructor_name,
                   cl.room_location, cl.day_of_week,
                   cl.start_period, cl.end_period,
                   cl.max_slots, cl.current_slots,
                   (cl.max_slots - cl.current_slots) AS remaining_slots
            FROM Classes cl
            JOIN Courses co ON cl.course_id = co.course_id
            WHERE cl.course_id = ?
            ORDER BY cl.semester_id DESC, cl.day_of_week, cl.start_period
            """,
            (course_id,),
        )
        return rows

    def recommend_courses(
        self,
        eligible_courses: list,
        min_credits: int,
        max_credits: int,
        semester: str,
    ) -> list:
        """
        Gợi ý danh sách các môn nên đăng ký kỳ tới.

        Chiến lược:
          - Ưu tiên môn bắt buộc (is_required = True).
          - Ưu tiên môn có semester_propose gần với kỳ hiện tại.
          - Đảm bảo tổng tín chỉ nằm trong [min_credits, max_credits].

        Trả về:
            recommended_courses: list[dict]
        """
        # Lấy danh sách môn mở trong kỳ
        open_ids = {c["course_id"] for c in self.get_open_courses(semester)}

        # Chỉ giữ môn có lớp mở
        available = [c for c in eligible_courses if c["course_id"] in open_ids]

        # Sắp xếp: bắt buộc trước, rồi theo semester_propose
        available.sort(key=lambda c: (not c.get("is_required", True), c.get("semester_propose", 99)))

        recommended = []
        total_credits = 0
        for course in available:
            credits = course.get("credits", 3)
            if total_credits + credits > max_credits:
                continue
            recommended.append(course)
            total_credits += credits
            if total_credits >= min_credits:
                # Đủ tín chỉ tối thiểu → có thể dừng,
                # nhưng tiếp tục thêm nếu chưa max
                pass

        return recommended

    def validate_schedule(self, selected_classes: list) -> dict:
        """
        Kiểm tra tính hợp lệ của thời khóa biểu đã chọn.

        Phát hiện trùng lịch (cùng day_of_week và tiết giao nhau).

        Args:
            selected_classes: list[dict] – mỗi phần tử cần có
                class_id, day_of_week, start_period, end_period.

        Trả về:
            {"is_valid": bool, "conflicts": list[tuple]}
        """
        conflicts = []
        n = len(selected_classes)
        for i in range(n):
            for j in range(i + 1, n):
                a, b = selected_classes[i], selected_classes[j]
                if a["day_of_week"] != b["day_of_week"]:
                    continue
                # Kiểm tra tiết giao nhau
                if a["start_period"] <= b["end_period"] and b["start_period"] <= a["end_period"]:
                    conflicts.append((a["class_id"], b["class_id"]))

        return {"is_valid": len(conflicts) == 0, "conflicts": conflicts}

    def recommend_schedule(
        self, current_semester_courses: list, open_classes: dict
    ) -> dict:
        """
        Gợi ý thời khóa biểu phù hợp với các môn học kỳ này.

        Thuật toán greedy: chọn lớp không trùng lịch, ưu tiên lớp còn slot.

        Args:
            current_semester_courses: list[str] – danh sách course_id cần học.
            open_classes: dict – {course_id: list[class_info]}

        Trả về:
            schedule: dict – {"classes": [...], "conflicts_resolved": int}
        """
        selected = []
        conflicts_resolved = 0

        for course_id in current_semester_courses:
            classes = open_classes.get(course_id, [])
            # Sắp xếp theo remaining_slots giảm dần
            classes.sort(key=lambda c: c.get("remaining_slots", 0), reverse=True)

            placed = False
            for cls in classes:
                if cls.get("remaining_slots", 0) <= 0:
                    continue
                # Kiểm tra trùng lịch với các lớp đã chọn
                conflict = False
                for s in selected:
                    if s["day_of_week"] == cls["day_of_week"]:
                        if s["start_period"] <= cls["end_period"] and cls["start_period"] <= s["end_period"]:
                            conflict = True
                            break
                if not conflict:
                    selected.append(cls)
                    placed = True
                    break
                else:
                    conflicts_resolved += 1

            if not placed:
                logger.warning(f"Không thể xếp lịch cho môn {course_id}")

        return {"classes": selected, "conflicts_resolved": conflicts_resolved}

    def recommend_improvement_courses(
        self, passed_courses: dict, target_cpa: float
    ) -> list:
        """
        Gợi ý các môn nên cải thiện để đạt CPA mục tiêu.

        Chiến lược: tìm các môn có điểm thấp nhất mà nếu cải thiện
        sẽ tăng CPA nhiều nhất (ưu tiên môn nhiều tín chỉ, điểm thấp).

        Args:
            passed_courses: dict – {course_id: {"credits": int, "grade_number": float, ...}}
            target_cpa: CPA mục tiêu.

        Trả về:
            improvement_courses: list[dict] – sắp xếp theo mức cải thiện tiềm năng.
        """
        if not passed_courses:
            return []

        # Tính CPA hiện tại
        total_credits = sum(c.get("credits", 0) for c in passed_courses.values())
        if total_credits == 0:
            return []

        weighted_sum = sum(
            c.get("grade_number", 0) * c.get("credits", 0)
            for c in passed_courses.values()
        )
        current_cpa = weighted_sum / total_credits

        if current_cpa >= target_cpa:
            return []  # Đã đạt mục tiêu

        # Tìm các môn có tiềm năng cải thiện cao
        candidates = []
        for course_id, info in passed_courses.items():
            grade = info.get("grade_number", 0)
            credits = info.get("credits", 0)
            if grade < 3.5:  # Chỉ gợi ý cải thiện môn < B+
                potential_gain = (4.0 - grade) * credits  # Nếu đạt A
                candidates.append({
                    "course_id": course_id,
                    "course_name": info.get("course_name", ""),
                    "credits": credits,
                    "current_grade": grade,
                    "potential_gain": round(potential_gain, 2),
                    "new_cpa_if_A": round(
                        (weighted_sum - grade * credits + 4.0 * credits) / total_credits, 2
                    ),
                })

        # Sắp xếp theo potential_gain giảm dần
        candidates.sort(key=lambda c: c["potential_gain"], reverse=True)
        return candidates

    def recommend_graduation_path(
        self,
        user_history: dict,
        curriculum: dict,
        regulation: dict,
        target_cpa: float,
    ) -> dict:
        """
        Gợi ý lộ trình tốt nghiệp.

        Kết hợp: chương trình đào tạo, lịch sử học, quy chế, CPA mục tiêu
        để đề xuất kế hoạch theo từng kỳ.

        Trả về:
            graduation_path: dict gồm danh sách kỳ → môn học dự kiến,
            tổng tín chỉ, GPA cần đạt, cảnh báo hạ bằng.
        """
        passed_ids = {c["course_id"] for c in user_history.get("passed_courses", [])}
        all_courses = curriculum.get("courses", [])
        remaining = [c for c in all_courses if c["course_id"] not in passed_ids]
        credits_remaining = user_history.get("credits_remaining", 0)

        # Check hạ bằng
        failed_credits = user_history.get("credits_failed", 0)
        is_downgraded = self.is_downgraded_degree(failed_credits)

        # Chia đều môn vào các kỳ còn lại (ước lượng ~18 tín / kỳ)
        avg_credits_per_sem = 18
        semesters_needed = max(1, credits_remaining // avg_credits_per_sem + 1)

        # Sắp xếp theo semester_propose
        remaining.sort(key=lambda c: c.get("semester_propose", 99))

        path = {}
        sem_idx = 1
        sem_credits = 0
        for course in remaining:
            if sem_credits + course.get("credits", 3) > avg_credits_per_sem + 3:
                sem_idx += 1
                sem_credits = 0
            key = f"semester_{sem_idx}"
            path.setdefault(key, []).append(course)
            sem_credits += course.get("credits", 3)

        return {
            "graduation_path": path,
            "total_semesters": sem_idx,
            "credits_remaining": credits_remaining,
            "is_downgraded": is_downgraded,
            "warning": "Bị hạ bằng do trượt quá nhiều tín chỉ!" if is_downgraded else None,
            "target_cpa": target_cpa,
        }

    def modify_graduation_path(
        self, graduation_path: dict, changes: dict
    ) -> dict:
        """
        Điều chỉnh lộ trình tốt nghiệp khi có thay đổi phát sinh.

        Args:
            graduation_path: dict – lộ trình hiện tại (output recommend_graduation_path).
            changes: dict – VD: {"move": {"IT3011": "semester_2"}, "remove": ["IT4441"]}

        Trả về:
            modified_path: dict – lộ trình đã cập nhật.
        """
        path = graduation_path.get("graduation_path", {})

        # Xử lý xóa môn
        for course_id in changes.get("remove", []):
            for sem_key, courses in path.items():
                path[sem_key] = [c for c in courses if c.get("course_id") != course_id]

        # Xử lý di chuyển môn sang kỳ khác
        for course_id, target_sem in changes.get("move", {}).items():
            moved_course = None
            for sem_key, courses in path.items():
                for c in courses:
                    if c.get("course_id") == course_id:
                        moved_course = c
                        break
                if moved_course:
                    path[sem_key] = [c for c in courses if c.get("course_id") != course_id]
                    break
            if moved_course:
                path.setdefault(target_sem, []).append(moved_course)

        # Xử lý thêm môn
        for course_id, target_sem in changes.get("add", {}).items():
            course_info = self.db.execute(
                "SELECT course_id, course_name, credits FROM Courses WHERE course_id = ?",
                (course_id,),
                fetchall=False,
            )
            if course_info:
                path.setdefault(target_sem, []).append(course_info)

        graduation_path["graduation_path"] = path
        return graduation_path

    def explain_recommendation(
        self,
        recommendation: dict,
        user_history: dict,
        curriculum: dict,
        regulation: dict,
    ) -> str:
        """
        Giải thích lý do cho các đề xuất (Nice to have).

        NOTE: Hàm này chủ yếu dùng LLM generate text.
        Ở layer tools, chuẩn bị context rồi trả cho Agent.
        """
        context = {
            "recommendation": recommendation,
            "student_cpa": user_history.get("current_cpa"),
            "target_cpa": user_history.get("target_cpa"),
            "credits_remaining": user_history.get("credits_remaining"),
            "is_downgraded": self.is_downgraded_degree(
                user_history.get("credits_failed", 0)
            ),
        }
        return json.dumps(context, ensure_ascii=False)

    # ===================================================================
    # GROUP 3 – Lập kế hoạch và giám sát tiến độ học tập, ôn tập
    # ===================================================================

    def compute_required_gpa(
        self, graduation_path: dict, target_cpa: float
    ) -> float:
        """
        Tính GPA trung bình cần đạt với các môn còn lại để đạt CPA mục tiêu.

        Công thức:
            required_gpa = (target_cpa * total_credits - current_weighted_sum)
                           / remaining_credits

        Args:
            graduation_path: dict chứa thông tin lộ trình.
            target_cpa: CPA mục tiêu.

        Trả về:
            required_gpa: float
        """
        credits_remaining = graduation_path.get("credits_remaining", 0)
        if credits_remaining <= 0:
            return 0.0

        # Cần thêm thông tin current weighted sum; ước lượng từ context
        # graduation_path nên chứa thông tin từ user_history
        total_credits = graduation_path.get("total_credits_required", 0)
        current_cpa = graduation_path.get("current_cpa", 0.0)
        credits_done = total_credits - credits_remaining

        if credits_remaining == 0:
            return current_cpa

        needed = (target_cpa * total_credits - current_cpa * credits_done) / credits_remaining
        return round(needed, 2)

    def compute_required_score(
        self, required_gpa: float, graduation_path: dict
    ) -> dict:
        """
        Tính điểm cần đạt với từng môn còn lại để đạt CPA mục tiêu.

        Chiến lược phân bổ đơn giản: mỗi môn cần đạt required_gpa.
        Có thể tinh chỉnh dựa trên độ khó môn.

        Args:
            required_gpa: GPA trung bình cần đạt.
            graduation_path: dict chứa lộ trình.

        Trả về:
            required_scores: dict – {course_id: target_grade}
        """
        path = graduation_path.get("graduation_path", {})
        result = {}
        for sem_key, courses in path.items():
            for course in courses:
                cid = course.get("course_id", "")
                result[cid] = {
                    "course_name": course.get("course_name", ""),
                    "credits": course.get("credits", 3),
                    "target_grade_number": min(required_gpa, 4.0),
                    "target_grade_letter": self._gpa_to_letter(required_gpa),
                    "semester": sem_key,
                }
        return result

    def recommend_study_plan(
        self,
        study_schedule: dict,
        other_schedule: dict,
        studying_courses: dict,
    ) -> dict:
        """
        Gợi ý kế hoạch học tập và ôn tập cho các môn trong kỳ.

        Args:
            study_schedule: dict – thời khóa biểu chính khóa.
            other_schedule: dict – lịch cá nhân / ngoại khóa.
            studying_courses: dict – thông tin các môn đang học
                (VD: {course_id: {"credits": 3, "difficulty": "hard"}})

        Trả về:
            study_plan: dict – kế hoạch theo ngày/tuần.
        """
        # Tìm slot trống trong tuần (tiết 1–12, thứ 2–7)
        occupied = set()
        for cls in study_schedule.get("classes", []):
            day = cls.get("day_of_week")
            for p in range(cls.get("start_period", 1), cls.get("end_period", 1) + 1):
                occupied.add((day, p))

        for event in other_schedule.get("events", []):
            day = event.get("day_of_week")
            for p in range(event.get("start_period", 1), event.get("end_period", 1) + 1):
                occupied.add((day, p))

        # Phân bổ thời gian tự học cho mỗi môn (2h/tín chỉ/tuần)
        plan = {}
        free_slots = []
        for day in range(2, 8):  # Thứ 2 – 7
            for period in range(1, 13):
                if (day, period) not in occupied:
                    free_slots.append({"day_of_week": day, "period": period})

        slot_idx = 0
        for course_id, info in studying_courses.items():
            credits = info.get("credits", 3)
            needed_slots = credits * 2  # 2 tiết tự học / tín chỉ
            course_slots = []
            for _ in range(needed_slots):
                if slot_idx < len(free_slots):
                    course_slots.append(free_slots[slot_idx])
                    slot_idx += 1
            plan[course_id] = {
                "course_name": info.get("course_name", ""),
                "study_slots": course_slots,
                "weekly_hours": needed_slots,
            }

        return {"study_plan": plan, "total_free_slots": len(free_slots)}

    def tracking_progress(self, study_plan: dict, user_update: str) -> dict:
        """
        Theo dõi tiến độ thực hiện kế hoạch học tập.

        Args:
            study_plan: dict – kế hoạch gốc.
            user_update: str – cập nhật từ sinh viên (VD: "Đã hoàn thành
                chương 3 IT3011, điểm giữa kỳ: 8.5")

        Trả về:
            progress_report: dict – tổng hợp tiến độ + cảnh báo nếu trễ.
        """
        return {
            "study_plan": study_plan,
            "user_update": user_update,
            "timestamp": datetime.now().isoformat(),
            "note": (
                "Agent sẽ phân tích user_update bằng LLM để đánh giá tiến độ, "
                "so sánh với study_plan và đưa ra cảnh báo / điều chỉnh."
            ),
        }

    def generate_review_materials(
        self, course_id: str, course_document: str
    ) -> list:
        """
        Tạo tài liệu hỗ trợ ôn tập (Nice to have).

        Bước 1: Tra cứu tài liệu trong DB.
        Bước 2: Agent dùng LLM tóm tắt / tạo flashcard.

        Args:
            course_id: Mã môn học.
            course_document: Nội dung / path tài liệu bổ sung.

        Trả về:
            review_materials: list[dict]
        """
        materials = self.db.execute(
            """
            SELECT material_id, title, material_type, chapter_index, file_path
            FROM Academic_Materials
            WHERE course_id = ?
            ORDER BY chapter_index
            """,
            (course_id,),
        )
        return {
            "course_id": course_id,
            "db_materials": materials,
            "supplementary_doc": course_document,
            "note": "Agent sẽ dùng LLM để tạo tóm tắt, flashcard từ tài liệu.",
        }

    # ===================================================================
    # Helper methods
    # ===================================================================

    @staticmethod
    def _gpa_to_letter(gpa: float) -> str:
        """Chuyển GPA số sang grade letter."""
        if gpa >= 3.7:
            return "A"
        elif gpa >= 3.5:
            return "A-"
        elif gpa >= 3.0:
            return "B+"
        elif gpa >= 2.5:
            return "B"
        elif gpa >= 2.0:
            return "C+"
        elif gpa >= 1.5:
            return "C"
        elif gpa >= 1.0:
            return "D+"
        elif gpa >= 0.5:
            return "D"
        else:
            return "F"


# ---------------------------------------------------------------------------
# Tool registry – Agent integration layer
# ---------------------------------------------------------------------------

# Singleton instance (set by init_tools)
_tools_instance: AcademicTools | None = None


def init_tools(db_path: str) -> AcademicTools:
    """Initialize the global AcademicTools instance."""
    global _tools_instance
    _tools_instance = AcademicTools(db_path)
    return _tools_instance


def _get_instance() -> AcademicTools:
    if _tools_instance is None:
        raise RuntimeError(
            "AcademicTools chưa được khởi tạo. Gọi init_tools(db_path) trước."
        )
    return _tools_instance


# ---- Schema definitions for the Anthropic tool-calling format ----

TOOLS = {
    # --- Group 1: Xác định user background ---
    "get_user_history": {
        "fn": lambda **kw: _get_instance().get_user_history(**kw),
        "description": "Lấy thông tin kết quả học tập người dùng (bảng điểm, CPA, tín chỉ) từ CSDL",
        "parameters": {"user_id": "string"},
    },
    "query_regulation": {
        "fn": lambda **kw: query_regulation(**kw),
        "description": "Hỏi đáp về quy chế đào tạo (đọc từ PDF, tìm đoạn liên quan, trả lời bằng LLM)",
        "parameters": {"question": "string"},
    },
    "search_regulation": {
        "fn": lambda **kw: search_regulation(**kw),
        "description": "Tìm kiếm các đoạn quy chế liên quan đến từ khóa (không gọi LLM)",
        "parameters": {"query": "string"},
    },
    "extract_user_input": {
        "fn": lambda **kw: _get_instance().extract_user_input(**kw),
        "description": "Trích xuất thông tin người dùng từ input text (tên, năm, ngành, CPA mục tiêu,...)",
        "parameters": {"user_input": "string"},
    },
    "get_curriculum": {
        "fn": lambda **kw: _get_instance().get_curriculum(**kw),
        "description": "Lấy thông tin chương trình đào tạo (danh sách môn, tín chỉ) trong CSDL",
        "parameters": {"major_id": "string"},
    },
    "extract_transcript": {
        "fn": lambda **kw: _get_instance().extract_transcript(**kw),
        "description": "Trích xuất thông tin từ bảng điểm (transcript): môn đã/chưa học, CPA, tín chỉ",
        "parameters": {"transcript": "string"},
    },
    "is_downgraded_degree": {
        "fn": lambda **kw: _get_instance().is_downgraded_degree(**kw),
        "description": "Kiểm tra sinh viên có bị hạ bằng không dựa trên số tín chỉ trượt",
        "parameters": {"n_failed_credits": "integer"},
    },
    "update_user_history": {
        "fn": lambda **kw: _get_instance().update_user_history(**kw),
        "description": "Cập nhật thông tin lịch sử học tập người dùng trong CSDL",
        "parameters": {"user_id": "string", "updates": "object"},
    },

    # --- Group 2: Gợi ý đăng ký môn học, lịch học, lộ trình tốt nghiệp ---
    "get_prerequisites": {
        "fn": lambda **kw: _get_instance().get_prerequisites(**kw),
        "description": "Lấy điều kiện tiên quyết/song hành của một môn học",
        "parameters": {"course_id": "string"},
    },
    "filter_eligible_courses": {
        "fn": lambda **kw: _get_instance().filter_eligible_courses(**kw),
        "description": "Lọc danh sách môn sinh viên đủ điều kiện đăng ký (đã hoàn thành tiên quyết)",
        "parameters": {"user_history": "object"},
    },
    "get_open_courses": {
        "fn": lambda **kw: _get_instance().get_open_courses(**kw),
        "description": "Lấy danh sách các môn mở trong kỳ học",
        "parameters": {"semester": "string"},
    },
    "get_open_classes": {
        "fn": lambda **kw: _get_instance().get_open_classes(**kw),
        "description": "Lấy danh sách lớp mở của một môn học (lịch, phòng, GV)",
        "parameters": {"course_id": "string"},
    },
    "recommend_courses": {
        "fn": lambda **kw: _get_instance().recommend_courses(**kw),
        "description": "Gợi ý các môn nên đăng ký kỳ tới (ưu tiên bắt buộc, đảm bảo tín chỉ)",
        "parameters": {
            "eligible_courses": "array",
            "min_credits": "integer",
            "max_credits": "integer",
            "semester": "string",
        },
    },
    "validate_schedule": {
        "fn": lambda **kw: _get_instance().validate_schedule(**kw),
        "description": "Kiểm tra tính hợp lệ của thời khóa biểu (phát hiện trùng lịch)",
        "parameters": {"selected_classes": "array"},
    },
    "recommend_schedule": {
        "fn": lambda **kw: _get_instance().recommend_schedule(**kw),
        "description": "Gợi ý thời khóa biểu không trùng lịch cho các môn trong kỳ",
        "parameters": {
            "current_semester_courses": "array",
            "open_classes": "object",
        },
    },
    "recommend_improvement_courses": {
        "fn": lambda **kw: _get_instance().recommend_improvement_courses(**kw),
        "description": "Gợi ý các môn nên cải thiện để tăng CPA (ưu tiên môn nhiều tín, điểm thấp)",
        "parameters": {"passed_courses": "object", "target_cpa": "number"},
    },
    "recommend_graduation_path": {
        "fn": lambda **kw: _get_instance().recommend_graduation_path(**kw),
        "description": "Gợi ý lộ trình tốt nghiệp (phân bổ môn theo kỳ, cảnh báo hạ bằng)",
        "parameters": {
            "user_history": "object",
            "curriculum": "object",
            "regulation": "object",
            "target_cpa": "number",
        },
    },
    "modify_graduation_path": {
        "fn": lambda **kw: _get_instance().modify_graduation_path(**kw),
        "description": "Điều chỉnh lộ trình tốt nghiệp khi có thay đổi phát sinh",
        "parameters": {"graduation_path": "object", "changes": "object"},
    },
    "explain_recommendation": {
        "fn": lambda **kw: _get_instance().explain_recommendation(**kw),
        "description": "Giải thích lý do cho các đề xuất của hệ thống",
        "parameters": {
            "recommendation": "object",
            "user_history": "object",
            "curriculum": "object",
            "regulation": "object",
        },
    },

    # --- Group 3: Lập kế hoạch và giám sát tiến độ ---
    "compute_required_gpa": {
        "fn": lambda **kw: _get_instance().compute_required_gpa(**kw),
        "description": "Tính GPA trung bình cần đạt với các môn còn lại để đạt CPA mục tiêu",
        "parameters": {"graduation_path": "object", "target_cpa": "number"},
    },
    "compute_required_score": {
        "fn": lambda **kw: _get_instance().compute_required_score(**kw),
        "description": "Tính điểm cần đạt từng môn còn lại để đạt CPA mục tiêu",
        "parameters": {"required_gpa": "number", "graduation_path": "object"},
    },
    "recommend_study_plan": {
        "fn": lambda **kw: _get_instance().recommend_study_plan(**kw),
        "description": "Gợi ý kế hoạch học tập và ôn tập cho các môn trong kỳ",
        "parameters": {
            "study_schedule": "object",
            "other_schedule": "object",
            "studying_courses": "object",
        },
    },
    "tracking_progress": {
        "fn": lambda **kw: _get_instance().tracking_progress(**kw),
        "description": "Theo dõi tiến độ thực hiện kế hoạch học tập",
        "parameters": {"study_plan": "object", "user_update": "string"},
    },
    "generate_review_materials": {
        "fn": lambda **kw: _get_instance().generate_review_materials(**kw),
        "description": "Tạo tài liệu hỗ trợ ôn tập cho một môn học",
        "parameters": {"course_id": "string", "course_document": "string"},
    },
}


def get_tool_schemas() -> list[dict]:
    """Return tool schemas in Anthropic API format."""
    type_mapping = {
        "string": "string",
        "integer": "integer",
        "number": "number",
        "boolean": "boolean",
        "object": "object",
        "array": "array",
    }

    schemas = []
    for name, tool in TOOLS.items():
        properties = {}
        for param_name, param_type in tool["parameters"].items():
            mapped_type = type_mapping.get(param_type, "string")
            properties[param_name] = {
                "type": mapped_type,
                "description": param_name,
            }

        schemas.append({
            "name": name,
            "description": tool["description"],
            "input_schema": {
                "type": "object",
                "properties": properties,
                "required": list(tool["parameters"].keys()),
            },
        })
    return schemas


def execute_tool(name: str, args: dict) -> str:
    """Execute a tool by name and return the result as a JSON string."""
    tool = TOOLS.get(name)
    if not tool:
        return json.dumps({"error": f"Tool '{name}' không tồn tại."}, ensure_ascii=False)
    try:
        result = tool["fn"](**args)
        if isinstance(result, (dict, list)):
            return json.dumps(result, ensure_ascii=False, default=str)
        return str(result)
    except Exception as e:
        logger.error(f"Lỗi khi thực thi tool '{name}': {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)