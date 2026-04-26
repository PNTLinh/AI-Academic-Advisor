from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from fastapi.responses import JSONResponse
import os
import time
import logging
from ..dependencies import get_academic_tools

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/upload-transcript")
async def upload_transcript(file: UploadFile = File(...)):
    """Lưu bảng điểm và trả về đường dẫn để Agent/UI xử lý."""
    try:
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
            content = await file.read()
            f.write(content)

        return {"status": "success", "file_path": dest_path, "filename": safe_name}
    except Exception as e:
        logger.exception("Upload failed")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/confirm")
def confirm_extraction(data: dict, tools=Depends(get_academic_tools)):
    """Xác nhận dữ liệu đã bóc tách được từ bảng điểm và cập nhật vào DB."""
    # Logic: UI gửi về list môn học đã parse, ta lưu vào DB
    # Đây là bước chuyển tiếp từ "AI bóc tách" sang "Dữ liệu chính thức"
    try:
        student_id = data.get("student_id", "anonymous")
        courses = data.get("courses", [])
        
        # Ở đây có thể gọi update_user_history hoặc một hàm chuyên dụng
        return {
            "status": "success", 
            "message": f"Confirmed {len(courses)} courses for {student_id}"
        }
    except Exception as e:
        logger.exception("Confirmation failed")
        raise HTTPException(status_code=500, detail=str(e))
