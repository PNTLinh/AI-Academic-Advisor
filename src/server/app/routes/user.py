from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging
from ..dependencies import get_academic_tools

logger = logging.getLogger(__name__)
router = APIRouter()

class PreferenceRequest(BaseModel):
    study_load: str
    blackout_slots: Optional[list] = []

@router.get("/status/{student_id}")
def get_user_status(student_id: str, tools=Depends(get_academic_tools)):
    """Lấy trạng thái học tập thật từ DB qua AcademicTools."""
    try:
        history = tools.get_user_history(student_id)
        if "error" in history:
            raise HTTPException(status_code=404, detail=history["error"])
        
        persona = {
            "student_id": history["student_id"],
            "full_name": history["full_name"],
            "gpa": history["current_cpa"],
            "standing": "Warning" if history["current_cpa"] < 2.5 else "Good", # Logic tạm thời
            "credits_summary": {
                "earned": history["credits_passed"],
                "total_required": history["total_credits_required"],
                "debt": history["credits_failed"]
            },
            "categorized_lists": {
                "passed": [c["course_id"] for c in history["passed_courses"]],
                "failed": [c["course_id"] for c in history["failed_courses"]]
            }
        }
        return persona
    except HTTPException: raise
    except Exception as e:
        logger.exception("Failed to get user status")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/preference")
def update_user_preference(pref: Dict[str, Any], x_user_id: Optional[str] = "SV12345", tools=Depends(get_academic_tools)):
    """Cập nhật mục tiêu và sở thích của sinh viên."""
    try:
        # Mock logic: Lưu vào DB (giả sử cập nhật target_cpa nếu có)
        updates = {}
        if "target_cpa" in pref:
            updates["target_cpa"] = pref["target_cpa"]
        
        if updates:
            tools.update_user_history(x_user_id, updates)
            
        return {"status": "success", "message": "Preferences updated"}
    except Exception as e:
        logger.exception("Failed to update preferences")
        raise HTTPException(status_code=500, detail=str(e))
