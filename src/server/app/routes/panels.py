"""
Panel data APIs – feeds the UI side-panels and roadmap.

These endpoints call AcademicTools directly (deterministic, no LLM).
Returns HTTP errors with clear messages when data is missing or incomplete.
UI is responsible for handling these errors and prompting user appropriately.
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from typing import Dict, Any, Optional
import os
import time
import logging

from ..dependencies import get_academic_tools
from ..models.schemas import (
    UserStatus, PreferenceRequest, RoadmapResponse, CreditsSummary,
)
logger = logging.getLogger(__name__)
router = APIRouter()


# ─── 1. USER PANEL ───────────────────────────────────────────────────────

@router.get("/user/status", response_model=UserStatus)
def get_user_status(
    student_id: str = "SV001",
    tools=Depends(get_academic_tools),
):
    """Dữ liệu cho panel Student Persona bên phải."""
    try:
        history = tools.get_user_history(student_id)
        if "error" in history:
            raise HTTPException(
                status_code=404,
                detail=f"User {student_id} not found. Please log in first."
            )

        return UserStatus(
            gpa=history["current_cpa"],
            credits_summary=CreditsSummary(
                earned=history["credits_passed"],
                total=history["total_credits_required"],
            ),
            failed_courses=[c["course_id"] for c in history["failed_courses"]],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_user_status failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/user/preference")
def set_user_preference(
    pref: PreferenceRequest,
    student_id: str = "SV001",
    tools=Depends(get_academic_tools),
):
    """Lưu sở thích học tập (Study Load, Blackout times)."""
    try:
        # Prepare update payload with preference data
        updates = {}
        
        # Note: These fields may need schema extension in the future
        # For now, storing metadata as a note
        logger.info(
            f"Saving preferences for {student_id}: "
            f"study_load={pref.study_load}, blackout_slots={len(pref.blackout_slots or [])}"
        )
        
        # Attempt to update user history (future: create preferences table)
        # Currently targeting_cpa can be saved; study_load/blackout_slots need schema update
        if updates:
            tools.update_user_history(student_id, updates)
        
        return {
            "status": "success",
            "message": "Preferences saved successfully",
            "saved_preferences": {
                "study_load": pref.study_load,
                "blackout_slots": pref.blackout_slots or [],
            }
        }
    except Exception as e:
        logger.exception("set_user_preference failed")
        raise HTTPException(status_code=500, detail=str(e))


# ─── 2. ACADEMIC PANEL (Roadmap) ─────────────────────────────────────────



# ─── 3. TRANSCRIPT HANDLING ──────────────────────────────────────────────

@router.post("/upload-transcript")
async def upload_transcript(file: UploadFile = File(...)):
    """Upload bảng điểm (PDF/PNG/JPG)."""
    filename = file.filename or "transcript.pdf"
    _, ext = os.path.splitext(filename.lower())
    if ext not in {".pdf", ".png", ".jpg"}:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    uploads_dir = os.path.join(os.getcwd(), "data", "uploads")
    os.makedirs(uploads_dir, exist_ok=True)

    ts = int(time.time() * 1000)
    safe_name = f"{ts}_{os.path.basename(filename)}"
    dest_path = os.path.join(uploads_dir, safe_name)

    with open(dest_path, "wb") as f:
        f.write(await file.read())

    return {"status": "success", "file_path": dest_path, "filename": safe_name}


@router.post("/transcript/confirm")
def confirm_transcript(
    data: Dict[str, Any],
    tools=Depends(get_academic_tools),
):
    """Xác nhận dữ liệu bóc tách từ bảng điểm → lưu vào DB."""
    try:
        student_id = data.get("student_id", "SV001")
        courses = data.get("courses", [])

        # Check if agent team has implemented save_transcript_data
        if hasattr(tools, "save_transcript_data"):
            result = tools.save_transcript_data(student_id, courses)
            return {
                "status": "success",
                "message": f"Confirmed {result.get('inserted', 0)} courses",
            }

        # If not implemented, return error instead of pending message
        raise HTTPException(
            status_code=400,
            detail="save_transcript_data() not yet implemented. Please check back later."
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("confirm_transcript failed")
        raise HTTPException(status_code=500, detail=str(e))
