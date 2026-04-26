"""
Main Orchestrator Agent – Điều phối toàn bộ hệ thống multi-agent.

Kiến trúc:
                        ┌─────────────────────────────────────┐
                        │         MainOrchestrator             │
                        │   (Claude – tool-calling loop)       │
                        └───────┬──────────────┬──────────────┘
                                │              │
                   ┌────────────▼──┐   ┌───────▼─────────────┐
                   │ PlanningAgent │   │  RegulationAgent     │
                   │ (lộ trình,    │   │  (quy chế PDF)       │
                   │  đăng ký môn) │   └─────────────────────-┘
                   └───────────────┘
                                │
                    ┌───────────▼────────────┐
                    │  BackgroundAgent        │
                    │  (study plan, worker,   │
                    │   theo dõi tiến độ)     │
                    └────────────────────────┘

Roles:
  - MainOrchestrator  : nhận câu hỏi của sinh viên, hiểu ý định,
                        chọn agent con phù hợp, tổng hợp kết quả.
  - PlanningAgent     : tư vấn đăng ký môn học, lộ trình tốt nghiệp.
  - RegulationAgent   : trả lời câu hỏi về quy chế đào tạo.
  - BackgroundAgent   : lập & theo dõi kế hoạch học/ôn tập, sinh
                        câu hỏi ôn tập định kỳ (tích hợp ReviewWorker).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from openai import OpenAI

from .config import OPENAI_API_KEY, DEFAULT_MODEL, LOG_LEVEL
from .tools import get_tool_schemas, execute_tool, init_tools
from .regulation_agent import init_regulation_agent
from .planning_agent import PlanningAgent
from .background_agent import BackgroundAgent

logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

ORCHESTRATOR_SYSTEM_PROMPT = """Bạn là AI hỗ trợ học tập cho sinh viên năm 3–4 Đại học Bách Khoa Hà Nội.

## VAI TRÒ
Bạn là Orchestrator – điều phối viên thông minh điều hướng yêu cầu của sinh viên đến đúng chuyên gia:

1. **PlanningAgent** – Tư vấn đăng ký môn học, lịch học, lộ trình tốt nghiệp, cải thiện CPA.
2. **RegulationAgent** – Giải đáp câu hỏi về quy chế đào tạo, điều kiện tốt nghiệp, hạ bằng, v.v.
3. **BackgroundAgent** – Lập kế hoạch học/ôn tập hàng tuần, theo dõi tiến độ, sinh câu hỏi ôn tập.

## NGUYÊN TẮC
- Luôn hỏi sinh viên về `student_id` nếu chưa có trước khi thực hiện bất kỳ tra cứu nào.
- Khi nhận được thông tin, gọi tool phù hợp để lấy dữ liệu thực từ CSDL.
- Tổng hợp kết quả từ các agent con thành câu trả lời mạch lạc, hữu ích.
- Nếu không rõ ý định, hỏi lại để làm rõ trước khi hành động.
- Trả lời bằng tiếng Việt.

## CÁC TOOL CÓ SẴN
Sử dụng các tool được cung cấp để:
- Lấy thông tin sinh viên (get_user_history, get_curriculum)
- Tư vấn môn học (filter_eligible_courses, recommend_courses, get_open_classes)
- Lộ trình tốt nghiệp (recommend_graduation_path, modify_graduation_path)
- Quy chế (query_regulation, search_regulation)
- Kế hoạch học (recommend_study_plan, tracking_progress)
- Tính GPA cần đạt (compute_required_gpa, compute_required_score)"""


class MainOrchestrator:
    """
    Orchestrator Agent – điều phối toàn bộ hệ thống multi-agent.

    Mỗi lần sinh viên gửi tin nhắn, Orchestrator sẽ:
      1. Phân tích ý định (intent classification qua LLM).
      2. Gọi các tool trực tiếp hoặc delegate sang agent chuyên biệt.
      3. Tổng hợp kết quả và trả lời.
    """

    def __init__(
        self,
        db_path: str | Path,
        regulations_dir: str | Path | None = None,
        model: str | None = None,
        max_turns: int = 15,
    ):
        """
        Args:
            db_path: Đường dẫn file SQLite.
            regulations_dir: Thư mục chứa PDF quy chế.
            model: GPT model (mặc định từ config).
            max_turns: Số vòng tool-calling tối đa mỗi conversation turn.
        """
        self.db_path = Path(db_path)
        self.model = model or DEFAULT_MODEL
        self.max_turns = max_turns

        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY chưa được cấu hình. Kiểm tra file .env")

        self.client = OpenAI(api_key=OPENAI_API_KEY)

        # Khởi tạo tools layer (singleton)
        init_tools(str(db_path))
        logger.info("AcademicTools initialized with db: %s", db_path)

        # Khởi tạo RegulationAgent
        reg_dir = str(regulations_dir) if regulations_dir else None
        init_regulation_agent(regulations_dir=reg_dir)
        logger.info("RegulationAgent initialized")

        # Khởi tạo specialized agents
        self.planning_agent = PlanningAgent(
            db_path=str(db_path),
            client=self.client,
            model=self.model,
        )
        self.background_agent = BackgroundAgent(
            db_path=str(db_path),
            client=self.client,
            model=self.model,
        )

        # Conversation memory (list of messages)
        self.conversation_history: list[dict] = []
        logger.info("MainOrchestrator ready.")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def chat(self, user_message: str) -> str:
        """
        Gửi tin nhắn và nhận câu trả lời từ Orchestrator.

        Args:
            user_message: Tin nhắn của sinh viên.

        Returns:
            Câu trả lời của agent (string).
        """
        # Đảm bảo có system prompt ở đầu history nếu mới bắt đầu
        if not self.conversation_history:
            self.conversation_history.append({
                "role": "system",
                "content": ORCHESTRATOR_SYSTEM_PROMPT
            })

        self.conversation_history.append({
            "role": "user",
            "content": user_message,
        })

        tools_schemas = get_tool_schemas()
        openai_tools = [{"type": "function", "function": t} for t in tools_schemas]

        for turn in range(self.max_turns):
            logger.info("Orchestrator turn %d/%d", turn + 1, self.max_turns)

            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=4096,
                tools=openai_tools,
                messages=self.conversation_history,
            )

            choice = response.choices[0]
            message = choice.message

            # Nếu có tool calls
            if message.tool_calls:
                logger.info("Orchestrator tool calls detected: %d calls", len(message.tool_calls))
                
                # Thêm message của assistant có tool_calls vào history
                self.conversation_history.append({
                    "role": "assistant",
                    "content": message.content or "",
                    "tool_calls": message.tool_calls
                })

                # Xử lý từng tool call
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_id = tool_call.id
                    
                    try:
                        tool_args = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        tool_args = {}

                    logger.info("Tool call: %s(%s)", tool_name, json.dumps(tool_args, ensure_ascii=False)[:200])
                    result = execute_tool(tool_name, tool_args)
                    logger.info("Tool result preview: %s", result[:300])

                    self.conversation_history.append({
                        "role": "tool",
                        "tool_call_id": tool_id,
                        "content": result,
                    })

                continue # Quay lại vòng lặp để LLM tổng hợp kết quả

            # Nếu không còn tool calls, trả về text
            final_text = message.content or ""
            self.conversation_history.append({
                "role": "assistant",
                "content": final_text,
            })
            return final_text

        return "Agent đã đạt giới hạn số vòng xử lý. Vui lòng thử lại hoặc đặt câu hỏi cụ thể hơn."

    def delegate_to_planning(self, student_id: str, task: str) -> str:
        """Delegate nhiệm vụ lập kế hoạch tốt nghiệp sang PlanningAgent."""
        logger.info("Delegating to PlanningAgent: student=%s, task=%s", student_id, task[:80])
        return self.planning_agent.run(student_id=student_id, task=task)

    def delegate_to_background(self, student_id: str, semester_id: str, task: str) -> str:
        """Delegate nhiệm vụ ôn tập/theo dõi tiến độ sang BackgroundAgent."""
        logger.info("Delegating to BackgroundAgent: student=%s, task=%s", student_id, task[:80])
        return self.background_agent.run(
            student_id=student_id,
            semester_id=semester_id,
            task=task,
        )

    def reset_conversation(self) -> None:
        """Xóa lịch sử hội thoại (bắt đầu conversation mới)."""
        self.conversation_history = []
        logger.info("Conversation history reset.")

    def get_conversation_summary(self) -> dict[str, Any]:
        """Trả về thống kê conversation hiện tại."""
        return {
            "turns": len([m for m in self.conversation_history if m["role"] == "user"]),
            "total_messages": len(self.conversation_history),
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Factory function
# ---------------------------------------------------------------------------

def create_orchestrator(
    db_path: str | Path | None = None,
    regulations_dir: str | Path | None = None,
) -> MainOrchestrator:
    """
    Tạo MainOrchestrator với config mặc định.

    Args:
        db_path: Đường dẫn SQLite. Nếu None, tìm trong data/output/.
        regulations_dir: Thư mục PDF quy chế. Nếu None, tìm trong data/regulations/.

    Returns:
        MainOrchestrator đã sẵn sàng.
    """
    if db_path is None:
        candidates = [
            Path("data/output/academic.db"),
            Path("data/academic.db"),
            Path("academic.db"),
        ]
        for candidate in candidates:
            if candidate.exists():
                db_path = candidate
                break
        if db_path is None:
            raise FileNotFoundError(
                "Không tìm thấy file database. "
                "Truyền db_path hoặc đặt file tại data/output/academic.db"
            )

    if regulations_dir is None:
        reg_candidates = [
            Path("data/regulations"),
            Path("data/output/regulations"),
        ]
        for candidate in reg_candidates:
            if candidate.exists() and any(candidate.glob("*.pdf")):
                regulations_dir = candidate
                break

    return MainOrchestrator(
        db_path=db_path,
        regulations_dir=regulations_dir,
    )
