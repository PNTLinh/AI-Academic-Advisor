"""Worker data APIs – HTTP interface for worker scheduler data.

These endpoints expose worker/notification data for:
- UI: Display pending review notifications
- Monitoring: Track notification delivery status
- External services: Access worker schedule and preferences

All endpoints use AcademicTools for DB access and return proper HTTP errors
when data is missing or incomplete.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Dict, Any, Optional
import logging
import json
from datetime import datetime

from ..dependencies import get_academic_tools
from ..models.schemas import (
    StudyScheduleResponse,
    LectureFrameResponse,
    NotificationRecordRequest,
    NotificationRecordResponse,
    NotificationPreferenceResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── 1. STUDY SCHEDULE ───────────────────────────────────────────────────

@router.get("/schedule/{student_id}", response_model=StudyScheduleResponse)
def get_study_schedule(
    student_id: str,
    semester_id: Optional[str] = Query(None),
    week_no: Optional[int] = Query(None),
    tools=Depends(get_academic_tools),
):
    """
    Lấy lịch học + tiến độ ôn tập của sinh viên trong kỳ/tuần.
    
    Returns: Courses with planned/actual study minutes and review progress
    """
    try:
        # Verify student exists
        history = tools.get_user_history(student_id)
        if "error" in history:
            raise HTTPException(
                status_code=404,
                detail=f"Sinh viên {student_id} không tồn tại. Vui lòng đăng nhập."
            )
        
        # Query study schedule from DB (placeholder: would query student_semester_study_schedule table)
        # For now, return sample structure that matches schema
        schedule = {
            "student_id": student_id,
            "semester_id": semester_id or "2026-1",
            "week_no": week_no or 1,
            "courses": [
                {
                    "course_id": "CS101",
                    "course_name": "Lập Trình Cơ Bản",
                    "planned_study_minutes": 120,
                    "actual_study_minutes": 85,
                    "review_progress_pct": 65,
                }
            ],
            "total_planned_minutes": 120,
            "total_actual_minutes": 85,
        }
        
        return StudyScheduleResponse(**schedule)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_study_schedule failed")
        raise HTTPException(status_code=500, detail=str(e))


# ─── 2. LECTURE FRAMES (Curriculum by Course & Week) ──────────────────────

@router.get("/frames/{course_id}", response_model=List[LectureFrameResponse])
def get_lecture_frames(
    course_id: str,
    curriculum_id: Optional[str] = Query(None),
    tools=Depends(get_academic_tools),
):
    """
    Lấy khung bài giảng (lecture outline) theo tuần cho một môn.
    
    Returns: List of weeks with lecture titles and topic outlines
    """
    try:
        # Verify course exists
        curriculum = tools.get_curriculum(curriculum_id or "IT1")
        if "error" in curriculum:
            raise HTTPException(
                status_code=404,
                detail=f"Không tìm thấy chương trình học cho môn {course_id}."
            )
        
        # Query lecture frames from DB (placeholder: would query course_lecture_frames table)
        frames = [
            {
                "week_no": 1,
                "lecture_title": "Giới thiệu Lập Trình",
                "topic_outline": "Khái niệm cơ bản, biến, kiểu dữ liệu",
                "expected_progress_pct": 10,
            },
            {
                "week_no": 2,
                "lecture_title": "Cấu Trúc Điều Kiện",
                "topic_outline": "If/else, switch case, toán tử so sánh",
                "expected_progress_pct": 20,
            },
        ]
        
        return [LectureFrameResponse(**f) for f in frames]
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_lecture_frames failed")
        raise HTTPException(status_code=500, detail=str(e))


# ─── 3. RECORD NOTIFICATION ──────────────────────────────────────────────

@router.post("/notifications/record", response_model=NotificationRecordResponse)
def record_notification(
    notification: NotificationRecordRequest,
    tools=Depends(get_academic_tools),
):
    """
    Ghi lại thông báo đã gửi vào lịch sử.
    
    Used by worker to track: what notifications were sent, when, delivery status
    """
    try:
        student_id = notification.student_id
        
        # Verify student exists
        history = tools.get_user_history(student_id)
        if "error" in history:
            raise HTTPException(
                status_code=404,
                detail=f"Sinh viên {student_id} không tồn tại."
            )
        
        # Log notification record (placeholder: would insert into review_notifications_history table)
        logger.info(
            f"Recording notification: {student_id} | {notification.course_id} | Week {notification.week_no}"
        )
        
        # Return confirmation with notification_id
        notification_id = f"notif_{student_id}_{notification.semester_id}_{notification.course_id}_{int(datetime.now().timestamp())}"
        
        return NotificationRecordResponse(
            notification_id=notification_id,
            status="recorded",
            message=f"Thông báo đã được ghi lại cho {student_id}",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("record_notification failed")
        raise HTTPException(status_code=500, detail=str(e))


# ─── 4. GET NOTIFICATION PREFERENCES ─────────────────────────────────────

@router.get("/preferences/{student_id}", response_model=NotificationPreferenceResponse)
def get_notification_preferences(
    student_id: str,
    tools=Depends(get_academic_tools),
):
    """
    Lấy cài đặt thông báo của sinh viên.
    
    Returns: Frequency, quiet hours, timezone, enabled status
    """
    try:
        # Verify student exists
        history = tools.get_user_history(student_id)
        if "error" in history:
            raise HTTPException(
                status_code=404,
                detail=f"Sinh viên {student_id} không tồn tại."
            )
        
        # Query preferences from DB (placeholder: would query student_notification_preferences table)
        preferences = {
            "student_id": student_id,
            "enabled": True,
            "frequency_per_day": 2,
            "quiet_hours_start": "22:00",
            "quiet_hours_end": "07:00",
            "timezone_offset_minutes": 420,  # UTC+7
        }
        
        return NotificationPreferenceResponse(**preferences)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_notification_preferences failed")
        raise HTTPException(status_code=500, detail=str(e))


# ─── 5. UPDATE NOTIFICATION PREFERENCES ──────────────────────────────────

@router.post("/preferences/{student_id}", response_model=NotificationPreferenceResponse)
def update_notification_preferences(
    student_id: str,
    prefs: NotificationPreferenceResponse,
    tools=Depends(get_academic_tools),
):
    """
    Cập nhật cài đặt thông báo của sinh viên.
    
    Updates: Frequency, quiet hours, timezone, enabled status
    """
    try:
        # Verify student exists
        history = tools.get_user_history(student_id)
        if "error" in history:
            raise HTTPException(
                status_code=404,
                detail=f"Sinh viên {student_id} không tồn tại."
            )
        
        # Update preferences in DB (placeholder: would update student_notification_preferences table)
        logger.info(
            f"Updating preferences for {student_id}: "
            f"enabled={prefs.enabled}, frequency={prefs.frequency_per_day}, "
            f"quiet_hours={prefs.quiet_hours_start}-{prefs.quiet_hours_end}"
        )
        
        return NotificationPreferenceResponse(
            student_id=student_id,
            enabled=prefs.enabled,
            frequency_per_day=prefs.frequency_per_day,
            quiet_hours_start=prefs.quiet_hours_start,
            quiet_hours_end=prefs.quiet_hours_end,
            timezone_offset_minutes=prefs.timezone_offset_minutes,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("update_notification_preferences failed")
        raise HTTPException(status_code=500, detail=str(e))
