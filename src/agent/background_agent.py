"""
Background Agent – Lập kế hoạch học/ôn tập và theo dõi tiến độ.

Chức năng:
  1. Lập kế hoạch học tập hàng tuần (dựa trên thời khóa biểu + lịch cá nhân).
  2. Theo dõi tiến độ thực hiện kế hoạch.
  3. Tích hợp ReviewWorker để sinh câu hỏi ôn tập định kỳ.
  4. Cảnh báo khi tiến độ chậm so với kế hoạch.
  5. Điều chỉnh lộ trình khi có thay đổi phát sinh.

Kiến trúc:
  MainOrchestrator ──(delegate)──► BackgroundAgent
                                        │
                            ┌───────────┴──────────────┐
                            │                           │
                     tool-calling loop           ReviewWorker
                     (LLM + tools.py)          (worker.py logic)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from openai import OpenAI

from .config import DEFAULT_MODEL, OPENAI_API_KEY
from .tools import get_tool_schemas, execute_tool, init_tools
from .worker import ReviewWorker, WorkerRepository, WorkerConfig, NotificationPreference, run_worker_once

logger = logging.getLogger(__name__)


BACKGROUND_SYSTEM_PROMPT = """Bạn là trợ lý hỗ trợ học tập cá nhân cho sinh viên Đại học Bách Khoa Hà Nội.

## NHIỆM VỤ CHÍNH
1. **Lập kế hoạch học/ôn tập**: Phân bổ thời gian học và ôn tập hợp lý dựa trên thời khóa biểu.
2. **Theo dõi tiến độ**: Phân tích cập nhật từ sinh viên, so sánh với kế hoạch, đưa ra cảnh báo.
3. **Điều chỉnh kế hoạch**: Khi sinh viên báo có thay đổi (điểm thấp, lịch thay đổi), cập nhật kế hoạch.
4. **Câu hỏi ôn tập**: Thông báo câu hỏi ôn tập định kỳ theo khung bài giảng.

## QUY TRÌNH
1. Dùng `recommend_study_plan` để lập kế hoạch hàng tuần.
2. Dùng `tracking_progress` để cập nhật tiến độ.
3. Nếu cần tài liệu ôn tập: dùng `generate_review_materials`.
4. Nếu có thay đổi lớn: thông báo sang PlanningAgent để điều chỉnh lộ trình.

## NGUYÊN TẮC
- Phân bổ thời gian đều giữa các môn (không thiên vị môn nào).
- Ưu tiên ôn tập sớm trước kỳ thi ít nhất 3 tuần.
- Cảnh báo nếu tiến độ thực tế thấp hơn kế hoạch > 20%.
- Trả lời ngắn gọn, cụ thể, có thể hành động ngay.
- Luôn trả lời bằng tiếng Việt."""


class BackgroundAgent:
    """
    Agent chuyên biệt cho việc lập kế hoạch học/ôn tập và theo dõi tiến độ.

    Tích hợp ReviewWorker để tạo câu hỏi ôn tập định kỳ.
    Được gọi từ MainOrchestrator hoặc trực tiếp từ API/scheduler.
    """

    def __init__(
        self,
        db_path: str | Path,
        client: OpenAI | None = None,
        model: str | None = None,
        max_turns: int = 8,
        worker_config: WorkerConfig | None = None,
    ):
        """
        Args:
            db_path: Đường dẫn file SQLite.
            client: OpenAI client (tạo mới nếu None).
            model: GPT model.
            max_turns: Số vòng tool-calling tối đa.
            worker_config: Cấu hình ReviewWorker.
        """
        self.db_path = Path(db_path)
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

        # ReviewWorker setup
        self._worker_repository = WorkerRepository(db_path=str(db_path))
        self._worker_config = worker_config or WorkerConfig()
        self._review_worker = ReviewWorker(
            repository=self._worker_repository,
            config=self._worker_config,
        )

    # ------------------------------------------------------------------
    # LLM-powered methods
    # ------------------------------------------------------------------

    def run(
        self,
        student_id: str,
        semester_id: str,
        task: str,
        extra_context: dict | None = None,
    ) -> str:
        """
        Chạy background agent loop for một task cụ thể.

        Args:
            student_id: Mã sinh viên.
            semester_id: Kỳ học hiện tại (VD: "20251").
            task: Mô tả nhiệm vụ.
            extra_context: Context bổ sung.

        Returns:
            Kết quả dưới dạng string.
        """
        ctx = extra_context or {}
        user_message = (
            f"Student ID: {student_id}\n"
            f"Kỳ học: {semester_id}\n"
            f"Yêu cầu: {task}\n"
        )
        if ctx:
            user_message += f"Context: {json.dumps(ctx, ensure_ascii=False)}\n"

        messages = [
            {"role": "system", "content": BACKGROUND_SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]
        tools_schemas = get_tool_schemas()
        openai_tools = [{"type": "function", "function": t} for t in tools_schemas]

        for turn in range(self.max_turns):
            logger.info("BackgroundAgent turn %d/%d", turn + 1, self.max_turns)

            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=4096,
                tools=openai_tools,
                messages=messages,
            )

            choice = response.choices[0]
            message = choice.message

            if message.tool_calls:
                logger.info("BackgroundAgent tool calls detected: %d calls", len(message.tool_calls))
                
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

                    logger.info("BackgroundAgent tool: %s", tool_name)
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

        return "BackgroundAgent đã đạt giới hạn xử lý."

    # ------------------------------------------------------------------
    # Direct API methods (không qua LLM loop)
    # ------------------------------------------------------------------

    def build_weekly_study_plan(
        self,
        student_id: str,
        semester_id: str,
        study_schedule: dict,
        other_schedule: dict | None = None,
    ) -> dict[str, Any]:
        """
        Lập kế hoạch học tập tuần dựa trên thời khóa biểu.

        Args:
            student_id: Mã sinh viên.
            semester_id: Kỳ học.
            study_schedule: Thời khóa biểu chính khóa (output recommend_schedule).
            other_schedule: Lịch cá nhân/ngoại khóa.

        Returns:
            study_plan: dict kế hoạch theo ngày/tuần.
        """
        from .tools import _get_instance
        tools_instance = _get_instance()

        # Lấy danh sách môn đang học
        classes = study_schedule.get("classes", [])
        studying_courses: dict[str, Any] = {}
        for cls in classes:
            cid = cls.get("course_id", "")
            if cid and cid not in studying_courses:
                studying_courses[cid] = {
                    "course_name": cls.get("course_name", ""),
                    "credits": 3,  # default, sẽ load từ DB nếu cần
                }

        # Load credits từ DB
        for cid in studying_courses:
            rows = tools_instance.db.execute(
                "SELECT course_name, credits FROM Courses WHERE course_id = ?",
                (cid,),
                fetchall=False,
            )
            if rows:
                studying_courses[cid].update({
                    "course_name": rows.get("course_name", studying_courses[cid]["course_name"]),
                    "credits": rows.get("credits", 3),
                })

        plan = tools_instance.recommend_study_plan(
            study_schedule=study_schedule,
            other_schedule=other_schedule or {"events": []},
            studying_courses=studying_courses,
        )

        return {
            "student_id": student_id,
            "semester_id": semester_id,
            "generated_at": datetime.now().isoformat(),
            **plan,
        }

    def update_progress(
        self,
        student_id: str,
        study_plan: dict,
        user_update: str,
    ) -> dict[str, Any]:
        """
        Cập nhật và theo dõi tiến độ học tập.

        Args:
            student_id: Mã sinh viên.
            study_plan: Kế hoạch gốc.
            user_update: Cập nhật từ sinh viên (text tự do).

        Returns:
            progress_report: dict tổng hợp tiến độ.
        """
        from .tools import _get_instance
        tools_instance = _get_instance()

        progress = tools_instance.tracking_progress(
            study_plan=study_plan,
            user_update=user_update,
        )

        return {
            "student_id": student_id,
            **progress,
        }

    # ------------------------------------------------------------------
    # ReviewWorker integration
    # ------------------------------------------------------------------

    def run_weekly_review_notifications(
        self,
        student_id: str,
        semester_id: str,
        week_no: int,
        now_utc: datetime | None = None,
    ) -> dict[str, Any]:
        """
        Chạy ReviewWorker để sinh câu hỏi ôn tập định kỳ.

        Thực hiện:
          1. Đảm bảo schema DB worker tồn tại.
          2. Kiểm tra quiet hours + frequency limit.
          3. Phân bổ đều câu hỏi ôn tập cho các môn.
          4. Lưu vào bảng review_notifications_history.

        Args:
            student_id: Mã sinh viên.
            semester_id: Kỳ học.
            week_no: Số tuần hiện tại trong kỳ.
            now_utc: Thời điểm UTC hiện tại (mặc định: datetime.utcnow()).

        Returns:
            Báo cáo kết quả: số notification đã tạo, danh sách môn được phủ.
        """
        logger.info(
            "ReviewWorker running for student=%s, semester=%s, week=%d",
            student_id, semester_id, week_no,
        )
        return self._review_worker.run_weekly_review(
            student_id=student_id,
            semester_id=semester_id,
            week_no=week_no,
            now_utc=now_utc,
        )

    def set_notification_preference(
        self,
        student_id: str,
        enabled: bool = True,
        frequency_per_day: int = 2,
        quiet_start: str = "22:00",
        quiet_end: str = "07:00",
        timezone_offset_minutes: int = 420,  # UTC+7 (Việt Nam)
    ) -> dict[str, Any]:
        """
        Cài đặt preference thông báo ôn tập cho sinh viên.

        Args:
            student_id: Mã sinh viên.
            enabled: Bật/tắt thông báo.
            frequency_per_day: Số thông báo tối đa mỗi ngày.
            quiet_start: Giờ bắt đầu im lặng (HH:MM).
            quiet_end: Giờ kết thúc im lặng (HH:MM).
            timezone_offset_minutes: Múi giờ (phút so với UTC).

        Returns:
            dict xác nhận đã lưu.
        """
        pref = NotificationPreference(
            enabled=enabled,
            frequency_per_day=frequency_per_day,
            quiet_hours_start=quiet_start,
            quiet_hours_end=quiet_end,
            timezone_offset_minutes=timezone_offset_minutes,
        )
        self._review_worker.set_notification_preference(student_id, pref)
        return {
            "student_id": student_id,
            "preference_updated": True,
            "enabled": enabled,
            "frequency_per_day": frequency_per_day,
            "quiet_hours": f"{quiet_start} – {quiet_end}",
        }

    def get_pending_notifications(
        self,
        student_id: str,
        semester_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Lấy danh sách câu hỏi ôn tập đang chờ gửi (status=queued).

        Args:
            student_id: Mã sinh viên.
            semester_id: Kỳ học.
            limit: Số tối đa.

        Returns:
            list[dict] – các notification chưa gửi.
        """
        self._worker_repository.ensure_schema()
        query = """
            SELECT notification_id, course_id, week_no, topic_key,
                   question_payload_json, sent_at, delivery_status
            FROM review_notifications_history
            WHERE student_id = ?
              AND semester_id = ?
              AND delivery_status = 'queued'
            ORDER BY sent_at DESC
            LIMIT ?
        """
        import sqlite3
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query, (student_id, semester_id, limit)).fetchall()
        conn.close()

        result = []
        for row in rows:
            record = dict(row)
            try:
                record["question"] = json.loads(record.pop("question_payload_json", "{}"))
            except json.JSONDecodeError:
                record["question"] = {}
            result.append(record)
        return result

    def mark_notification_answered(
        self,
        notification_id: int,
        answered_option: int,
    ) -> dict[str, Any]:
        """
        Đánh dấu sinh viên đã trả lời câu hỏi ôn tập.

        Args:
            notification_id: ID notification.
            answered_option: Index lựa chọn (0-based).

        Returns:
            dict xác nhận.
        """
        import sqlite3
        conn = sqlite3.connect(str(self.db_path))
        query = """
            UPDATE review_notifications_history
            SET delivery_status = 'answered',
                answered_option = ?,
                answered_at = CURRENT_TIMESTAMP
            WHERE notification_id = ?
        """
        cur = conn.execute(query, (answered_option, notification_id))
        conn.commit()
        affected = cur.rowcount
        conn.close()
        return {
            "notification_id": notification_id,
            "answered": affected > 0,
            "answered_option": answered_option,
        }

    def get_study_progress_summary(
        self,
        student_id: str,
        semester_id: str,
        week_no: int,
    ) -> dict[str, Any]:
        """
        Tóm tắt tiến độ ôn tập của sinh viên trong tuần.

        Args:
            student_id: Mã sinh viên.
            semester_id: Kỳ học.
            week_no: Tuần cần xem.

        Returns:
            dict tóm tắt tiến độ các môn.
        """
        rows = self._worker_repository.get_study_schedule_rows(
            student_id=student_id,
            semester_id=semester_id,
            week_no=week_no,
        )
        if not rows:
            return {
                "student_id": student_id,
                "semester_id": semester_id,
                "week_no": week_no,
                "status": "no_data",
                "courses": [],
            }

        courses_summary = []
        for row in rows:
            planned = row.get("planned_study_minutes", 0)
            actual = row.get("actual_study_minutes", 0)
            progress_pct = row.get("review_progress_pct", 0)
            completion = round(actual / planned * 100, 1) if planned > 0 else 0

            courses_summary.append({
                "course_id": row["course_id"],
                "course_name": row.get("course_name", row["course_id"]),
                "planned_minutes": planned,
                "actual_minutes": actual,
                "completion_pct": completion,
                "review_progress_pct": progress_pct,
                "on_track": completion >= 80,
            })

        behind_courses = [c for c in courses_summary if not c["on_track"]]
        return {
            "student_id": student_id,
            "semester_id": semester_id,
            "week_no": week_no,
            "total_courses": len(courses_summary),
            "on_track_courses": len(courses_summary) - len(behind_courses),
            "behind_courses": len(behind_courses),
            "warning": (
                f"Cần tăng tốc ôn tập: {', '.join(c['course_id'] for c in behind_courses)}"
                if behind_courses else None
            ),
            "courses": courses_summary,
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
