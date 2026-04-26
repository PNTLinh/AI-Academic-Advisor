from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Optional, Dict, Any
import logging
from ..dependencies import get_academic_tools
from .chat import memory as chat_memory  # Access chat session memory

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/roadmap")
def get_student_roadmap(x_user_id: Optional[str] = Header(None), tools=Depends(get_academic_tools)):
    """
    Tạo lộ trình học tập dựa trên:
    1. Session data from agent conversation (priority)
    2. Database if user is logged in
    3. Error if neither exists
    """
    user_id = x_user_id or "anonymous"
    logger.info(f"📊 Roadmap request from user: {user_id}")
    
    try:
        # 1. Check if user has data from agent conversation (session memory)
        if user_id in chat_memory and len(chat_memory[user_id]) > 0:
            logger.info(f"   ✅ Found session data for user")
            # Extract agent messages to see if roadmap was generated
            agent_messages = [m for m in chat_memory[user_id] if m.get("role") == "assistant"]
            if agent_messages:
                # For now, generate based on conversation context
                # In future: extract structured roadmap from agent's final message
                logger.info(f"   ℹ️  Using agent-generated plan from conversation")
                # Fall through to generate from tools
        else:
            logger.warning(f"   ⚠️  No session data found for user")
            # Could check database for logged-in user here
            # For now, reject anonymous users without conversation
            raise HTTPException(
                status_code=404, 
                detail="Bạn chưa cung cấp thông tin học tập. Vui lòng chat với trợ lý trước."
            )
        
        # 2. Generate roadmap (this will fail if user data doesn't exist)
        history = tools.get_user_history(user_id)
        if "error" in history:
            logger.warning(f"   ❌ No user history: {history}")
            raise HTTPException(
                status_code=404, 
                detail="Không tìm thấy thông tin của bạn. Vui lòng hoàn thành cuộc trò chuyện."
            )
        
        # Get target_cpa from user's stored preference, or default to 3.2
        target_cpa = history.get("target_cpa", 3.2)
        logger.info(f"   Using target_cpa: {target_cpa}")
        
        curriculum = tools.get_curriculum(history["curriculum_id"])
        
        path_data = tools.recommend_graduation_path(
            user_history=history,
            curriculum=curriculum,
            regulation={},
            target_cpa=target_cpa
        )

        # 3. Generate AI insights based on the data
        try:
            from src.agent.planning_agent import PlanningAgent
            from src.agent.config import OPENAI_API_KEY, DEFAULT_MODEL
            
            planner = PlanningAgent(db_path=tools.db.db_url)
            
            ai_task = f"""Dựa trên dữ liệu dưới đây, hãy đưa ra 3 lời khuyên ngắn gọn (bullet points) để tối ưu lộ trình học tập:
            - CPA hiện tại: {history.get('current_cpa')}
            - CPA mục tiêu: {target_cpa}
            - Tín chỉ còn nợ: {history.get('credits_remaining')}
            - Số tín chỉ trượt: {history.get('credits_failed')}
            - Trình trạng: {'Có nguy cơ hạ bằng' if path_data.get('is_downgraded') else 'Ổn định'}
            
            Yêu cầu: Viết ngắn gọn, tập trung vào hành động."""
            
            ai_suggestions_text = planner.run(student_id=user_id, task=ai_task)
            # Simple cleanup of bullet points if needed
            suggestions = [s.strip("- ").strip() for s in ai_suggestions_text.split("\n") if s.strip()]
            path_data["ai_suggestions"] = suggestions[:5]
        except Exception as ai_e:
            logger.warning(f"⚠️  Failed to generate AI suggestions: {ai_e}")
            path_data["ai_suggestions"] = [
                "Nên ưu tiên học các môn bắt buộc trước.",
                f"Cần duy trì GPA kỳ tới >= {path_data.get('target_cpa', 3.2)} để đạt mục tiêu.",
                "Hạn chế trượt thêm môn để tránh bị hạ bằng tốt nghiệp."
            ]
        
        logger.info(f"   ✅ Roadmap & AI Suggestions generated successfully")
        return path_data
        
    except HTTPException: 
        raise
    except Exception as e:
        logger.exception(f"Failed to generate roadmap for {user_id}")
        raise HTTPException(
            status_code=500, 
            detail="Lỗi khi tạo lộ trình. Vui lòng thử lại."
        )

@router.get("/courses/open")
def get_open_courses(semester: str = "20251", tools=Depends(get_academic_tools)):
    """Lấy danh sách môn mở trong kỳ."""
    try:
        courses = tools.get_open_courses(semester)
        return {"semester": semester, "courses": courses}
    except Exception as e:
        logger.exception("Failed to get open courses")
        raise HTTPException(status_code=500, detail=str(e))
