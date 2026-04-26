from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.models import schemas
from app.mock_data import examples

router = APIRouter()

# 1. Data Ingestion
@router.post("/ingest", response_model=schemas.IngestResponse)
def ingest_data(request: schemas.IngestRequest):
    """Upload và bóc tách dữ liệu từ bảng điểm."""
    return JSONResponse(content=examples.INGEST_EXAMPLE)

# 2. Student Persona
@router.get("/status/{student_id}", response_model=schemas.StatusResponse)
def get_status(student_id: str):
    """Lấy trạng thái học tập chi tiết của sinh viên."""
    return JSONResponse(content=examples.STATUS_EXAMPLE)

# 3. Goal & Limits
@router.post("/set-goals", response_model=schemas.SetGoalsResponse)
def set_goals(request: schemas.SetGoalsRequest):
    """Thiết lập mục tiêu và tính toán giới hạn đăng ký."""
    return JSONResponse(content=examples.SET_GOALS_EXAMPLE)

# 4. Smart Planning
@router.post("/recommend", response_model=schemas.RecommendResponse)
def recommend(request: schemas.RecommendRequest):
    """Đề xuất danh mục môn học cho kỳ tới."""
    return JSONResponse(content=examples.RECOMMEND_EXAMPLE)

# 5. Adaptive Roadmap
@router.get("/roadmap/{student_id}", response_model=schemas.RoadmapResponse)
def get_roadmap(student_id: str, use_summer: bool = True):
    """Trả về toàn bộ lộ trình dài hạn đã được tối ưu."""
    return JSONResponse(content=examples.ROADMAP_EXAMPLE)

# 6. Incident Handling
@router.post("/re-optimize", response_model=schemas.ReOptimizeResponse)
def re_optimize(request: schemas.ReOptimizeRequest):
    """Tính toán lại lộ trình khi gặp sự cố bất ngờ."""
    return JSONResponse(content=examples.REOPTIMIZE_EXAMPLE)
