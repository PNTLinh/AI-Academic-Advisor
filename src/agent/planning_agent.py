"""
Planning Agent – Tư vấn đăng ký môn học, lịch học và lộ trình tốt nghiệp.

Chức năng:
  1. Lấy thông tin sinh viên và chương trình đào tạo
  2. Lọc các môn đủ điều kiện đăng ký
  3. Gợi ý môn học theo kỳ (ưu tiên bắt buộc, đảm bảo tín chỉ)
  4. Gợi ý thời khóa biểu không trùng lịch
  5. Xây dựng lộ trình tốt nghiệp theo CPA mục tiêu
  6. Gợi ý môn cần cải thiện
  7. Tính toán GPA/điểm cần đạt cho từng môn còn lại

Kiến trúc:
  MainOrchestrator ──(delegate)──► PlanningAgent
                                        │
                                   tool-calling loop
                                        │
                                  AcademicTools (tools.py)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from openai import OpenAI

from .config import DEFAULT_MODEL, OPENAI_API_KEY
from .tools import get_tool_schemas, execute_tool, init_tools

logger = logging.getLogger(__name__)


PLANNING_SYSTEM_PROMPT = """Bạn là chuyên gia tư vấn học tập cho sinh viên Đại học Bách Khoa Hà Nội.

## NHIỆM VỤ CHÍNH
Hỗ trợ sinh viên:
1. **Đăng ký môn học**: Lọc môn đủ điều kiện, gợi ý môn phù hợp cho kỳ tới.
2. **Thời khóa biểu**: Gợi ý lịch học không trùng, còn slot.
3. **Lộ trình tốt nghiệp**: Phân bổ môn học theo kỳ để đạt CPA mục tiêu đúng hạn.
4. **Cải thiện CPA**: Xác định môn nên học lại để tăng điểm hiệu quả nhất.
5. **Tính điểm cần đạt**: Tính GPA/điểm từng môn cần để đạt CPA mục tiêu.

## QUY TRÌNH LÀM VIỆC
1. Gọi `get_user_history` để lấy thông tin học tập hiện tại.
2. Gọi `get_curriculum` để lấy chương trình đào tạo.
3. Gọi `filter_eligible_courses` để lọc môn đủ điều kiện.
4. Gọi `get_open_courses` + `recommend_courses` để gợi ý đăng ký kỳ tới.
5. Gọi `recommend_graduation_path` để xây dựng lộ trình tổng thể.
6. Tính toán và đưa ra khuyến nghị cụ thể, có lý do rõ ràng.

## NGUYÊN TẮC
- Luôn giải thích lý do cho mỗi đề xuất (ưu tiên bắt buộc, tiên quyết, CPA).
- Cảnh báo nếu sinh viên có nguy cơ bị hạ bằng (trượt > 8 tín chỉ).
- Nếu CPA mục tiêu quá cao, đề xuất điều chỉnh thực tế.
- Trả lời ngắn gọn, có cấu trúc, dùng bảng/danh sách khi cần.
- Luôn trả lời bằng tiếng Việt."""


class PlanningAgent:
    """
    Agent chuyên biệt cho các tác vụ lập kế hoạch học tập và tốt nghiệp.

    Được gọi từ MainOrchestrator hoặc trực tiếp từ API.
    """

    def __init__(
        self,
        db_path: str | Path,
        client: OpenAI | None = None,
        model: str | None = None,
        max_turns: int = 10,
    ):
        """
        Args:
            db_path: Đường dẫn file SQLite.
            client: OpenAI client (tạo mới nếu None).
            model: GPT model.
            max_turns: Số vòng tool-calling tối đa.
        """
        self.model = model or DEFAULT_MODEL
        self.max_turns = max_turns

        if client is not None:
            self.client = client
        else:
            if not OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY chưa được cấu hình.")
            self.client = OpenAI(api_key=OPENAI_API_KEY)

        # Đảm bảo tools đã được init
        try:
            from .tools import _get_instance
            _get_instance()
        except RuntimeError:
            init_tools(str(db_path))

    def run(self, student_id: str, task: str, extra_context: dict | None = None) -> str:
        """
        Chạy planning loop cho một task cụ thể.

        Args:
            student_id: Mã sinh viên.
            task: Mô tả nhiệm vụ (ví dụ: "gợi ý môn kỳ 20251, CPA mục tiêu 3.6").
            extra_context: Context bổ sung (semester, max_credits, ...).

        Returns:
            Kết quả tư vấn dưới dạng string.
        """
        ctx = extra_context or {}
        user_message = (
            f"Student ID: {student_id}\n"
            f"Yêu cầu: {task}\n"
        )
        if ctx:
            user_message += f"Context bổ sung: {json.dumps(ctx, ensure_ascii=False)}\n"

        messages = [
            {"role": "system", "content": PLANNING_SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]
        tools_schemas = get_tool_schemas()
        openai_tools = [{"type": "function", "function": t} for t in tools_schemas]

        for turn in range(self.max_turns):
            logger.info("PlanningAgent turn %d/%d", turn + 1, self.max_turns)

            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=4096,
                tools=openai_tools,
                messages=messages,
            )

            choice = response.choices[0]
            message = choice.message

            if message.tool_calls:
                logger.info("PlanningAgent tool calls detected: %d calls", len(message.tool_calls))
                
                # Thêm message của assistant có tool_calls vào history
                messages.append({
                    "role": "assistant",
                    "content": message.content or "",
                    "tool_calls": message.tool_calls
                })

                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_id = tool_call.id
                    
                    try:
                        tool_args = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        tool_args = {}

                    logger.info("PlanningAgent tool: %s", tool_name)
                    result = execute_tool(tool_name, tool_args)
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_id,
                        "content": result,
                    })

                continue

            # Nếu không còn tool calls, trả về text
            final_text = message.content or ""
            return final_text

        return "PlanningAgent đã đạt giới hạn xử lý."

    def recommend_semester_courses(
        self,
        student_id: str,
        semester: str,
        target_cpa: float,
        min_credits: int = 12,
        max_credits: int = 22,
    ) -> dict[str, Any]:
        """
        API level: Gợi ý môn học cho một kỳ cụ thể.

        Args:
            student_id: Mã sinh viên.
            semester: Kỳ học (VD: "20251").
            target_cpa: CPA mục tiêu.
            min_credits: Tín chỉ tối thiểu.
            max_credits: Tín chỉ tối đa.

        Returns:
            dict chứa recommended_courses, schedule, graduation_path.
        """
        from .tools import _get_instance
        tools_instance = _get_instance()

        # Lấy thông tin sinh viên
        user_history = tools_instance.get_user_history(student_id)
        if "error" in user_history:
            return {"error": user_history["error"]}

        curriculum_id = user_history.get("curriculum_id")
        curriculum = tools_instance.get_curriculum(curriculum_id)
        if "error" in curriculum:
            return {"error": curriculum["error"]}

        # Lọc môn đủ điều kiện
        eligible = tools_instance.filter_eligible_courses(user_history)

        # Gợi ý môn
        recommended = tools_instance.recommend_courses(
            eligible_courses=eligible,
            min_credits=min_credits,
            max_credits=max_credits,
            semester=semester,
        )

        # Lấy lớp mở cho từng môn
        open_classes_map: dict[str, list] = {}
        for course in recommended:
            cid = course["course_id"]
            open_classes_map[cid] = tools_instance.get_open_classes(cid)

        # Gợi ý thời khóa biểu
        schedule = tools_instance.recommend_schedule(
            current_semester_courses=[c["course_id"] for c in recommended],
            open_classes=open_classes_map,
        )

        # Lộ trình tốt nghiệp tổng thể
        grad_path = tools_instance.recommend_graduation_path(
            user_history=user_history,
            curriculum=curriculum,
            regulation={},  # Để RegulationAgent cung cấp nếu cần
            target_cpa=target_cpa,
        )

        # Tính GPA cần đạt
        required_gpa = tools_instance.compute_required_gpa(
            graduation_path={
                **grad_path,
                "total_credits_required": user_history.get("total_credits_required", 0),
                "current_cpa": user_history.get("current_cpa", 0.0),
            },
            target_cpa=target_cpa,
        )

        return {
            "student_id": student_id,
            "semester": semester,
            "target_cpa": target_cpa,
            "current_cpa": user_history.get("current_cpa"),
            "required_gpa_for_remaining": required_gpa,
            "recommended_courses": recommended,
            "schedule": schedule,
            "graduation_path": grad_path,
            "eligible_count": len(eligible),
        }

    def recommend_graduation_plan(
        self,
        student_id: str,
        target_cpa: float,
    ) -> dict[str, Any]:
        """
        API level: Xây dựng lộ trình tốt nghiệp đầy đủ.

        Args:
            student_id: Mã sinh viên.
            target_cpa: CPA mục tiêu khi tốt nghiệp.

        Returns:
            dict chứa lộ trình học tập theo kỳ, điểm cần đạt, cảnh báo.
        """
        from .tools import _get_instance
        tools_instance = _get_instance()

        user_history = tools_instance.get_user_history(student_id)
        if "error" in user_history:
            return {"error": user_history["error"]}

        curriculum = tools_instance.get_curriculum(user_history["curriculum_id"])
        if "error" in curriculum:
            return {"error": curriculum["error"]}

        grad_path = tools_instance.recommend_graduation_path(
            user_history=user_history,
            curriculum=curriculum,
            regulation={},
            target_cpa=target_cpa,
        )

        required_gpa = tools_instance.compute_required_gpa(
            graduation_path={
                **grad_path,
                "total_credits_required": user_history.get("total_credits_required", 0),
                "current_cpa": user_history.get("current_cpa", 0.0),
            },
            target_cpa=target_cpa,
        )

        required_scores = tools_instance.compute_required_score(
            required_gpa=required_gpa,
            graduation_path=grad_path,
        )

        # Gợi ý cải thiện nếu cần
        passed_dict = {
            c["course_id"]: {
                "course_name": c.get("course_name", ""),
                "credits": c.get("credits", 3),
                "grade_number": c.get("grade_number", 0),
            }
            for c in user_history.get("passed_courses", [])
        }
        improvement = tools_instance.recommend_improvement_courses(
            passed_courses=passed_dict,
            target_cpa=target_cpa,
        )

        is_downgraded = tools_instance.is_downgraded_degree(
            n_failed_credits=user_history.get("credits_failed", 0)
        )

        return {
            "student_id": student_id,
            "target_cpa": target_cpa,
            "current_cpa": user_history.get("current_cpa"),
            "credits_remaining": user_history.get("credits_remaining"),
            "required_gpa_for_remaining": required_gpa,
            "is_downgraded_risk": is_downgraded,
            "graduation_path": grad_path,
            "required_scores_per_course": required_scores,
            "improvement_suggestions": improvement[:5],  # top 5
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_text(content: list) -> str:
        """Trích xuất text từ response content."""
        text = ""
        for block in content:
            if hasattr(block, "text"):
                text += block.text
        return text.strip()
