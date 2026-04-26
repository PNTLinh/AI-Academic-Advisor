# Backend

Đây là backend xây dựng bằng FastAPI. Dự án này triển khai đầy đủ các endpoint, trả về dữ liệu mẫu để frontend phát triển và kiểm thử nhanh chóng.


## Cấu trúc thư mục
```
app/
  routes/         # Xử lý route API
  models/         # Định nghĩa schema Pydantic
  mock_data/      # Dữ liệu mẫu trả về
  services/       # Logic nghiệp vụ
main.py           # Điểm khởi động FastAPI
```

## Yêu cầu
- Python 3.8+
- pip

## Cài đặt & chạy thử
```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

## Tài liệu API
- Swagger UI: http://localhost:8000/docs
- Redoc: http://localhost:8000/redoc
