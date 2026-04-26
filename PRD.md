# Product Requirements Document

## I. USER STORIES

Nhiều sinh viên năm 3, năm 4 có nguyện vọng tốt nghiệp với tấm bằng mong muốn (VD: sinh viên năm 3, CPA hiện tại là 3.4, muốn tốt nghiệp xuất sắc). Việc lập kế hoạch thủ công bao gồm nhiều bước:

- Lấy danh sách các môn đã học
- Kiểm tra điều kiện hạ bằng (VD: Trượt 6 tín ---> hạ bằng với bằng giỏi và xuất sắc)
- Lập danh sách các môn trong chương trình đào tạo
- Điền kết quả các môn đã học
- Tính toán điểm trung bình (tối thiểu) cần đạt với các môn chưa học để đạt CPA mục tiêu
- Lập danh sách các môn cần cải thiện (nếu điểm cần đạt với các môn còn lại quá cao, quá sức với mình)
- Lập danh sách các môn cần đăng ký cho mỗi kỳ (có những môn chỉ mở ít lớp hay chỉ mở vào kì cố định)
- Lập thời khóa biểu và đăng ký lịch học

Đồng thời, trong quá trình học tập, sinh viên cần có chiến lược học tập, ôn tập phù hợp để đảm bảo kế hoạch đúng tiến độ. Nếu có thay đổi phát sinh trong kì (VD: điểm 1 môn thấp hơn kì vọng), cần điều chỉnh lại kế hoạch các kì sau.

## II. CÁC NHÓM CHỨC NĂNG CHÍNH (FUNCTIONAL REQUIREMENTS)

### 1. Xác định user background

| Tên hàm              | Args                           | Return                | Mô tả                                                                                                                                  | Phân loại |
|:---------------------|:-------------------------------|:----------------------|:---------------------------------------------------------------------------------------------------------------------------------------|:----------|
| get_user_history     | user_id: string                | user_history: dict    | Lấy thông tin kết quả học tập người dùng trong CSDL                                                                                            | Must have |
| get_regulation       |                                | regulation: dict      | Lấy thông tin quy chế từ CSDL                                                                                                          | Must have |
| extract_user_input   | user_input: string             | user_input: dict      | Trích xuất thông tin người dùng từ input text, bao gồm: tên, trình độ năm, ngành học, mức cảnh cáo, giới hạn đăng ký, cpa mục tiêu,... | Must have |
| get_curriculum       | major_id: string               | curriculum: dict      | Lấy thông tin chương trình đào tạo trong CSDL                                                                                          | Must have |
| extract_transcript   | transcript: string             | transcript_data: dict | Trích xuất thông tin từ bảng điểm (transcript), bao gồm: các môn đã học/chưa học/trượt, cpa hiện tại, số tín chỉ đã qua/còn lại/trượt  | Must have |
| is_downgraded_degree | n_failed_credits: int          | is_downgraded: bool   | Kiểm tra có bị hạ bằng không                                                                                                           | Must have |
| update_user_history  | user_id: string, updates: dict |                       | Cập nhật thông tin lịch sử người dùng trong CSDL                                                                                       | Must have |


---

### 2. Gợi ý đăng ký môn học, lịch học, lộ trình tốt nghiệp

| Tên hàm                       | Args                                                                      | Return                          | Mô tả                                                          | Phân loại    |
|:------------------------------|:--------------------------------------------------------------------------|:--------------------------------|:---------------------------------------------------------------|:-------------|
| get_prerequisites             | course_id: string                                                         | prerequisites: list             | Lấy thông tin điều kiện tiên quyết của một môn học (nếu có)    | Must have    |
| filter_eligible_courses       | user_history: dict                                                        | eligible_courses: list          | Lọc ra danh sách các môn học mà sinh viên đủ điều kiện đăng ký | Must have    |
| get_open_courses              | semester: int                                                             | open_courses: list              | Lấy danh sách các môn mở trong kì                              | Must have    |
| get_open_classes              | course_id: string                                                         | open_classes: list              | Lấy danh sách các lớp mở của một môn học trong kì              | Must have    |
| recommend_courses             | eligible_courses: list, min_credits: int, max_credits: int, semester: int | recommended_courses: list       | Gợi ý danh sách các môn học nên đăng ký kì tới                 | Must have    |
| validate_schedule             | selected_classes: list                                                    | is_valid: bool, conflicts: list | Kiểm tra tính hợp lệ của thời khóa biểu đã chọn                | Must have    |
| recommend_schedule            | current_semester_courses: list, open_classes: dict                        | schedule: dict                  | Gợi ý thời khóa biểu phù hợp với các môn học kì này            | Must have    |
| reccomend_improvement_courses | passed_courses: dict, target_cpa: float                                   | improvement_courses: list       | Gợi ý các môn học cần cải thiện để đạt được CPA mục tiêu       | Must have    |
| recommend_graduation_path     | user_history: dict, curriculum: dict, regulation: dict, target_cpa: float | graduation_path: dict           | Gợi ý lộ trình học tập để đạt được mục tiêu tốt nghiệp         | Must have    |
| modify_graduation_path        | graduation_path: dict, changes: dict                                      | modified_path: dict             | Điều chỉnh lộ trình học tập khi có thay đổi phát sinh          | Must have    |
|explain_recommendation         | recommendation: dict, user_history: dict, curriculum: dict, regulation: dict | explanation: string          | Giải thích lý do cho các đề xuất                               | Nice to have |


---

### 3. Lập kế hoạch và giám sát tiến độ học tập, ôn tập

| Tên hàm                   | Args                                                              | Return                 | Mô tả                                                                     | Phân loại    |
|:--------------------------|:------------------------------------------------------------------|:-----------------------|:--------------------------------------------------------------------------|:-------------|
| compute_required_gpa      | graduation_path: dict, target_cpa: float                          | required_gpa: float    | Tính toán điểm trung bình cần đạt với các môn còn lại để đạt CPA mục tiêu | Must have    |
| compute_required_score    | required_gpa: float, graduation_path: dict                        | required_scores: dict  | Tính toán điểm cần đạt với từng môn còn lại để đạt CPA mục tiêu           | Must have    |
| recommend_study_plan      | study_schedule: dict, other_schedule:dict, studying_courses: dict | study_plan: dict       | Gợi ý kế hoạch học tập và ôn tập cho các môn trong kì                     | Must have    |
| tracking_progress         | study_plan: dict, user_update: string                             | progress_report: dict  | Theo dõi tiến độ thực hiện kế hoạch học tập                               | Must have    |
| generate_review_materials | course_id: string, course_document: string                        | review_materials: list | Tạo tài liệu hỗ trợ ôn tập                                                | Nice to have |