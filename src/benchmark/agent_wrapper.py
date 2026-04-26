"""
src/benchmark/agent_wrapper.py
Kết nối tới MainOrchestrator và capture tool calls để đánh giá.
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any
from unittest.mock import patch, MagicMock

logger = logging.getLogger(__name__)


class AgentWrapper:
    """
    Wrapper quanh MainOrchestrator để:
      1. Gửi câu hỏi benchmark và nhận câu trả lời.
      2. Capture danh sách tool đã được gọi trong mỗi lượt chat.
      3. Đo latency.

    Sử dụng:
        wrapper = AgentWrapper(db_path="data/output/academic.db")
        result = wrapper.run(question="Cho tôi xem kết quả của SV 20200001")
        print(result["response"])
        print(result["tools_called"])
    """

    def __init__(
        self,
        db_path: str | Path | None = None,
        regulations_dir: str | Path | None = None,
        model: str | None = None,
        max_turns: int = 10,
    ):
        self.db_path = db_path
        self.regulations_dir = regulations_dir
        self.model = model
        self.max_turns = max_turns
        self._orchestrator = None

    # ------------------------------------------------------------------
    # Lazy init
    # ------------------------------------------------------------------

    def _get_orchestrator(self):
        """Khởi tạo MainOrchestrator lần đầu khi cần."""
        if self._orchestrator is None:
            try:
                from src.agent.main_agent import create_orchestrator
                self._orchestrator = create_orchestrator(
                    db_path=self.db_path,
                    regulations_dir=self.regulations_dir,
                )
                if self.model:
                    self._orchestrator.model = self.model
                if self.max_turns:
                    self._orchestrator.max_turns = self.max_turns
                logger.info("MainOrchestrator initialized successfully.")
            except Exception as e:
                logger.error("Lỗi khởi tạo MainOrchestrator: %s", e)
                raise
        return self._orchestrator

    # ------------------------------------------------------------------
    # Core run method
    # ------------------------------------------------------------------

    def run(self, question: str, reset_conversation: bool = True) -> dict:
        """
        Gửi câu hỏi tới agent và trả về kết quả có kèm tool trace.

        Args:
            question: Câu hỏi benchmark.
            reset_conversation: Nếu True, reset lịch sử hội thoại trước khi hỏi.

        Returns:
            {
                "response": str,          # Câu trả lời cuối cùng của agent
                "tools_called": list[str],# Tên các tool đã được gọi
                "tool_calls_detail": list,# Chi tiết từng tool call
                "latency_s": float,       # Thời gian phản hồi (giây)
                "error": str | None,      # Lỗi nếu có
            }
        """
        orchestrator = self._get_orchestrator()

        if reset_conversation:
            orchestrator.reset_conversation()

        tools_called: list[str] = []
        tool_calls_detail: list[dict] = []

        # Patch execute_tool để capture tool calls
        original_execute_tool = None
        try:
            import src.agent.tools as tools_module
            original_execute_tool = tools_module.execute_tool

            def patched_execute_tool(tool_name: str, tool_args: dict) -> str:
                tools_called.append(tool_name)
                tool_calls_detail.append({
                    "tool": tool_name,
                    "args": tool_args,
                })
                return original_execute_tool(tool_name, tool_args)

            tools_module.execute_tool = patched_execute_tool

            start = time.perf_counter()
            response = orchestrator.chat(question)
            latency = time.perf_counter() - start

        except Exception as e:
            logger.error("Lỗi khi chạy agent: %s", e)
            return {
                "response": "",
                "tools_called": tools_called,
                "tool_calls_detail": tool_calls_detail,
                "latency_s": 0.0,
                "error": str(e),
            }
        finally:
            # Khôi phục execute_tool gốc
            if original_execute_tool is not None:
                import src.agent.tools as tools_module
                tools_module.execute_tool = original_execute_tool

        return {
            "response": response,
            "tools_called": tools_called,
            "tool_calls_detail": tool_calls_detail,
            "latency_s": round(latency, 3),
            "error": None,
        }

    def run_batch(
        self,
        questions: list[str],
        reset_between: bool = True,
        delay_s: float = 0.5,
    ) -> list[dict]:
        """
        Chạy nhiều câu hỏi liên tiếp.

        Args:
            questions: Danh sách câu hỏi.
            reset_between: Reset conversation giữa các câu hỏi.
            delay_s: Thời gian chờ giữa các lần gọi (tránh rate limit).

        Returns:
            Danh sách kết quả tương ứng với mỗi câu hỏi.
        """
        results = []
        for i, question in enumerate(questions):
            logger.info("Batch run %d/%d: %s", i + 1, len(questions), question[:60])
            result = self.run(question, reset_conversation=reset_between)
            results.append(result)
            if delay_s > 0 and i < len(questions) - 1:
                time.sleep(delay_s)
        return results


# ---------------------------------------------------------------------------
# Mock wrapper (dùng khi không có API key / offline testing)
# ---------------------------------------------------------------------------

class MockAgentWrapper:
    """
    Mock wrapper trả về kết quả giả lập để test pipeline đánh giá
    mà không cần gọi LLM thực.

    Dùng cho unit test hoặc dry-run.
    """

    MOCK_RESPONSES = {
        "get_user_history": (
            "Sinh viên 20200001 – Nguyễn Văn A, ngành CNTT.\n"
            "CPA hiện tại: 3.20. Tín chỉ tích lũy: 95/130.\n"
            "Đã qua: 28 môn. Chưa học: 12 môn. Trượt: 1 môn (IT3011)."
        ),
        "is_downgraded_degree": (
            "Với 8 tín chỉ trượt, bạn đã chạm đúng ngưỡng hạ bằng. "
            "Theo quy chế, trượt > 8 tín chỉ sẽ bị hạ bằng với loại giỏi và xuất sắc. "
            "Bạn có nguy cơ bị hạ bằng nếu muốn tốt nghiệp loại giỏi."
        ),
        "compute_required_gpa": (
            "Để đạt CPA mục tiêu 3.2 với 60 tín chỉ còn lại, "
            "bạn cần đạt GPA trung bình khoảng 3.45 mỗi kỳ."
        ),
        "query_regulation": (
            "Theo quy chế đào tạo HUST, điều kiện tốt nghiệp loại xuất sắc:\n"
            "- CPA ≥ 3.60\n"
            "- Không bị hạ bằng\n"
            "- Điểm rèn luyện ≥ Tốt\n"
            "- Không có môn điểm F trong toàn khóa."
        ),
        "default": (
            "Tôi đã xử lý yêu cầu của bạn. Vui lòng cung cấp thêm thông tin "
            "nếu cần tư vấn chi tiết hơn."
        ),
    }

    def run(self, question: str, reset_conversation: bool = True) -> dict:
        """Trả