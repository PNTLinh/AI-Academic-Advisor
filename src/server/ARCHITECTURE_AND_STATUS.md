# Kiến trúc Hệ thống & Trạng thái triển khai API

Tài liệu này mô tả kiến trúc hiện tại của dự án Adaptive Academic Advisor và phân loại trạng thái của các API.

## 1. Kiến trúc tổng quan (Hybrid Architecture)

Hệ thống được thiết kế theo mô hình lai:
*   **Agent-Logic**: Dùng cho Chatbot (`/advisor`). Xử lý ngôn ngữ tự nhiên, lập kế hoạch phức tạp và gọi tools linh hoạt qua LLM (Claude).
*   **Deterministic-Logic**: Dùng cho UI Panels (Roadmap, Persona). Gọi trực tiếp các hàm trong `AcademicTools` để lấy dữ liệu nhanh và chính xác nhất.

---

## 2. Trạng thái các API & Hàm (Status Table)

Hệ thống được chia làm hai phần: Những gì đã chạy thật (OK) và những gì đang dùng dữ liệu mẫu (Fake).

### ✅ Phần 1: Đã hoạt động thực tế (Real / OK)
Các thành phần này đã kết nối Database và có logic xử lý thật:

| Component | Endpoint / Method | Trạng thái | Ghi chú |
| :--- | :--- | :--- | :--- |
| **Chat** | `POST /api/chat` | **OK** | Chạy qua Agent Loop + Claude API. |
| **User Data** | `tools.get_user_history` | **OK** | Lấy điểm, GPA, tín chỉ từ bảng `Student_Transcripts`. |
| **Academic** | `tools.get_curriculum` | **OK** | Lấy khung chương trình từ bảng `Curriculums`. |
| **Planning** | `tools.recommend_graduation_path` | **OK** | Tự động tính toán lộ trình theo thuật toán deterministic. |
| **Course** | `tools.get_open_courses` | **OK** | Lấy danh sách môn mở trong kỳ từ bảng `Classes`. |
| **Files** | `POST /api/upload` | **OK** | Lưu file vào thư mục `data/uploads/`. |

---

### ❌ Phần 2: Đang chạy dữ liệu mẫu (Fake / To-be-Implemented)
Các thành phần này hiện tại chỉ trả về dữ liệu mẫu hoặc thông báo chờ:

| Component | Endpoint / Method | Vấn đề | Cần làm |
| :--- | :--- | :--- | :--- |
| **Transcript** | `POST /api/transcript/confirm` | **Fake** | Chưa có hàm `save_transcript_data`. |
| **Settings** | `POST /api/user/preference` | **Fake** | Nhận dữ liệu nhưng chưa UPDATE vào bảng `Students`. |
| **Extraction** | `tools.extract_transcript` | **Placeholder** | Đang chờ tích hợp logic LLM để parse text sang JSON. |
| **Tracking** | `tools.tracking_progress` | **Placeholder** | Chỉ trả về note, chưa có logic so sánh tiến độ thực tế. |
| **UI Fallback** | `get_user_status` (Route) | **Mock** | Tự động trả về `USER_STATUS_MOCK` nếu DB chưa có user. |
| **UI Fallback** | `get_roadmap` (Route) | **Mock** | Tự động trả về `ROADMAP_MOCK` nếu DB chưa có user. |

---

## 3. Hướng dẫn bảo trì

*   **Khi bổ sung logic thật**: Cập nhật hàm tương ứng trong `src/agent/tools.py`, sau đó vào `src/server/app/routes/panels.py` để xóa các đoạn code fallback.
*   **Database**: Khi cập nhật bảng `Students`, hãy nhớ cập nhật file `data/data.sql` để đồng bộ schema.

*Người lập: Gemini AI*
