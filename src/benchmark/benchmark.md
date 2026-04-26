# Benchmark – Hệ thống Multi-Agent Tư vấn Học tập

> **Mục đích:** Đánh giá chất lượng đầu ra của hệ thống multi-agent (MainOrchestrator → PlanningAgent / RegulationAgent / BackgroundAgent) trên các tình huống thực tế của sinh viên HUST.

---

## 1. Phương pháp đánh giá

| Tiêu chí | Thang điểm | Mô tả |
|---|---|---|
| **Correctness** | 0 – 3 | Kết quả có đúng về mặt dữ liệu/logic không? |
| **Completeness** | 0 – 3 | Trả lời đủ thông tin, không bỏ sót yêu cầu? |
| **Helpfulness** | 0 – 3 | Câu trả lời có hữu ích, dễ hiểu với sinh viên? |
| **Tool Usage** | ✅ / ⚠️ / ❌ | Agent có gọi đúng tool theo kịch bản không? |

**Tổng điểm tối đa mỗi ca:** 9 điểm (Correctness + Completeness + Helpfulness)

---

## 2. Test Cases – Nhóm 1: Xác định User Background

### TC-01: Lấy lịch sử học tập

**Input:**
```
Cho tôi xem kết quả học tập của sinh viên 20200001.
```

**Tool kỳ vọng:** `get_user_history(user_id="20200001")`

**Output kỳ vọng:**
- Trả về danh sách môn đã học, điểm, CPA hiện tại, số tín chỉ tích lũy.
- Định dạng rõ ràng, phân nhóm theo kỳ.

| Lần chạy | Correctness | Completeness | Helpfulness | Tool Usage | Ghi chú |
|---|---|---|---|---|---|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |

---

### TC-02: Trích xuất thông tin từ bảng điểm

**Input:**
```
Đây là bảng điểm của tôi: [dán text bảng điểm]. Hãy phân tích giúp tôi.
```

**Tool kỳ vọng:** `extract_transcript(transcript=...)`

**Output kỳ vọng:**
- Liệt kê môn đã qua / chưa học / trượt.
- CPA hiện tại, tổng tín chỉ đã tích lũy, tín chỉ còn thiếu.

| Lần chạy | Correctness | Completeness | Helpfulness | Tool Usage | Ghi chú |
|---|---|---|---|---|---|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |

---

### TC-03: Kiểm tra hạ bằng

**Input:**
```
Tôi đã trượt 8 tín chỉ, tôi có bị hạ bằng không nếu muốn tốt nghiệp loại giỏi?
```

**Tool kỳ vọng:** `is_downgraded_degree(n_failed_credits=8)`

**Output kỳ vọng:**
- Kết quả True/False rõ ràng.
- Giải thích ngưỡng tín chỉ trượt cho từng loại bằng.

| Lần chạy | Correctness | Completeness | Helpfulness | Tool Usage | Ghi chú |
|---|---|---|---|---|---|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |

---

## 3. Test Cases – Nhóm 2: Tư vấn Đăng ký Môn học & Lộ trình Tốt nghiệp

### TC-04: Gợi ý môn học kỳ tới

**Input:**
```
Tôi là sinh viên 20200001, kỳ tới tôi nên đăng ký những môn nào? Tôi muốn đăng ký khoảng 18–20 tín chỉ.
```

**Tool kỳ vọng (theo thứ tự):**
1. `get_user_history(user_id="20200001")`
2. `get_curriculum(major_id=...)`
3. `filter_eligible_courses(user_history=...)`
4. `get_open_courses(semester=...)`
5. `recommend_courses(eligible_courses=..., min_credits=18, max_credits=20, semester=...)`

**Output kỳ vọng:**
- Danh sách môn khuyến nghị kèm lý do.
- Số tín chỉ tổng, môn tiên quyết đã đủ điều kiện.

| Lần chạy | Correctness | Completeness | Helpfulness | Tool Usage | Ghi chú |
|---|---|---|---|---|---|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |

---

### TC-05: Kiểm tra thời khóa biểu

**Input:**
```
Tôi đã chọn các lớp sau: [danh sách mã lớp]. Kiểm tra giúp tôi có bị trùng lịch không?
```

**Tool kỳ vọng:** `validate_schedule(selected_classes=[...])`

**Output kỳ vọng:**
- Kết quả hợp lệ / xung đột.
- Nếu xung đột, chỉ rõ cặp lớp nào bị trùng và ca học cụ thể.

| Lần chạy | Correctness | Completeness | Helpfulness | Tool Usage | Ghi chú |
|---|---|---|---|---|---|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |

---

### TC-06: Lộ trình tốt nghiệp với CPA mục tiêu

**Input:**
```
Tôi là sinh viên 20200001, CPA hiện tại 3.2, muốn tốt nghiệp xuất sắc (CPA ≥ 3.6). Lên lộ trình giúp tôi.
```

**Tool kỳ vọng:**
1. `get_user_history` → `get_curriculum` → `get_regulation`
2. `recommend_graduation_path(user_history=..., curriculum=..., regulation=..., target_cpa=3.6)`
3. `compute_required_gpa(graduation_path=..., target_cpa=3.6)`

**Output kỳ vọng:**
- Lộ trình học theo từng kỳ còn lại.
- Điểm trung bình tối thiểu cần đạt mỗi kỳ.
- Cảnh báo nếu mục tiêu khó khả thi.

| Lần chạy | Correctness | Completeness | Helpfulness | Tool Usage | Ghi chú |
|---|---|---|---|---|---|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |

---

### TC-07: Gợi ý môn cải thiện điểm

**Input:**
```
Tôi muốn cải thiện CPA từ 3.1 lên 3.5. Tôi nên học lại môn nào?
```

**Tool kỳ vọng:** `reccomend_improvement_courses(passed_courses=..., target_cpa=3.5)`

**Output kỳ vọng:**
- Danh sách môn nên cải thiện, sắp xếp theo mức độ tác động đến CPA.
- Giải thích tại sao mỗi môn được chọn.

| Lần chạy | Correctness | Completeness | Helpfulness | Tool Usage | Ghi chú |
|---|---|---|---|---|---|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |

---

## 4. Test Cases – Nhóm 3: Kế hoạch & Giám sát Tiến độ

### TC-08: Tính điểm cần đạt

**Input:**
```
Tôi còn 3 kỳ học, CPA hiện tại 3.0, muốn tốt nghiệp loại giỏi (CPA ≥ 3.2). Tôi cần đạt điểm trung bình bao nhiêu mỗi kỳ?
```

**Tool kỳ vọng:**
1. `recommend_graduation_path(...)`
2. `compute_required_gpa(graduation_path=..., target_cpa=3.2)`
3. `compute_required_score(required_gpa=..., graduation_path=...)`

**Output kỳ vọng:**
- GPA cần đạt theo từng kỳ.
- Điểm số cụ thể cần đạt theo từng môn (nếu có).

| Lần chạy | Correctness | Completeness | Helpfulness | Tool Usage | Ghi chú |
|---|---|---|---|---|---|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |

---

### TC-09: Lập kế hoạch ôn tập tuần

**Input:**
```
Kỳ này tôi học 5 môn. Lịch rảnh của tôi: sáng T2, T4, T6. Lập kế hoạch ôn tập giúp tôi.
```

**Tool kỳ vọng:** `recommend_study_plan(study_schedule=..., other_schedule=..., studying_courses=...)`

**Output kỳ vọng:**
- Kế hoạch học theo từng ngày/buổi trong tuần.
- Phân bổ thời gian hợp lý cho từng môn.

| Lần chạy | Correctness | Completeness | Helpfulness | Tool Usage | Ghi chú |
|---|---|---|---|---|---|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |

---

### TC-10: Theo dõi tiến độ học tập

**Input:**
```
Tuần này tôi đã hoàn thành 3/5 buổi học theo kế hoạch, bài tập môn Giải tích bị trễ 2 ngày. Cập nhật tiến độ giúp tôi.
```

**Tool kỳ vọng:** `tracking_progress(study_plan=..., user_update=...)`

**Output kỳ vọng:**
- Báo cáo tiến độ hiện tại (%).
- Cảnh báo và gợi ý điều chỉnh kế hoạch phù hợp.

| Lần chạy | Correctness | Completeness | Helpfulness | Tool Usage | Ghi chú |
|---|---|---|---|---|---|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |

---

## 5. Test Cases – Nhóm 4: Quy chế Đào tạo (RegulationAgent)

### TC-11: Hỏi điều kiện tốt nghiệp

**Input:**
```
Điều kiện để được xét tốt nghiệp đại học loại xuất sắc tại HUST là gì?
```

**Tool kỳ vọng:** `query_regulation(...)` hoặc `search_regulation(...)`

**Output kỳ vọng:**
- Liệt kê đầy đủ điều kiện: CPA tối thiểu, tín chỉ rèn luyện, điểm môn cơ sở, v.v.
- Có trích dẫn điều/khoản từ quy chế.

| Lần chạy | Correctness | Completeness | Helpfulness | Tool Usage | Ghi chú |
|---|---|---|---|---|---|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |

---

### TC-12: Hỏi quy định cảnh báo học vụ

**Input:**
```
Tôi bị cảnh báo học vụ mức 1, có bị đuổi học không? Muốn lên mức bình thường cần làm gì?
```

**Tool kỳ vọng:** `search_regulation(query="cảnh báo học vụ")`

**Output kỳ vọng:**
- Quy định cụ thể về các mức cảnh báo.
- Điều kiện để xóa cảnh báo / hậu quả nếu tiếp tục vi phạm.

| Lần chạy | Correctness | Completeness | Helpfulness | Tool Usage | Ghi chú |
|---|---|---|---|---|---|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |

---

## 6. Test Cases – Nhóm 5: Điều hướng & Multi-turn

### TC-13: Điều hướng đúng agent

**Input:**
```
Turn 1: "Điều kiện tốt nghiệp xuất sắc là gì?"
Turn 2: "Tôi là SV 20200001, CPA 3.3, có đạt không?"
Turn 3: "Nếu chưa đủ thì kỳ tới nên đăng ký môn gì?"
```

**Output kỳ vọng:**
- Turn 1 → RegulationAgent trả lời.
- Turn 2 → Kết hợp get_user_history + quy chế để đánh giá.
- Turn 3 → PlanningAgent gợi ý môn học.

| Lần chạy | Correctness | Completeness | Helpfulness | Tool Usage | Ghi chú |
|---|---|---|---|---|---|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |

---

### TC-14: Xử lý câu hỏi mơ hồ

**Input:**
```
Tôi cần tư vấn học tập.
```

**Output kỳ vọng:**
- Agent hỏi lại để làm rõ ý định (không gọi tool ngay).
- Yêu cầu `student_id` nếu chưa có.

| Lần chạy | Correctness | Completeness | Helpfulness | Tool Usage | Ghi chú |
|---|---|---|---|---|---|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |

---

### TC-15: Điều chỉnh lộ trình khi có thay đổi

**Input:**
```
Tôi vừa thi rớt môn Giải tích 2 (3 tín chỉ). Cập nhật lại lộ trình tốt nghiệp của tôi.
```

**Tool kỳ vọng:**
1. `get_user_history` → cập nhật kết quả môn rớt
2. `modify_graduation_path(graduation_path=..., changes={"failed": "Giải tích 2"})`
3. `compute_required_gpa` lại với lộ trình mới

**Output kỳ vọng:**
- Lộ trình được điều chỉnh, chỉ rõ kỳ nào cần học lại môn trượt.
- CPA dự kiến sau điều chỉnh.

| Lần chạy | Correctness | Completeness | Helpfulness | Tool Usage | Ghi chú |
|---|---|---|---|---|---|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |

---

## 7. Tổng hợp kết quả

> Điền sau khi hoàn thành tất cả các lần chạy.

| TC | Tên | Avg Correctness | Avg Completeness | Avg Helpfulness | Avg Total | Tool Usage |
|---|---|---|---|---|---|---|
| TC-01 | Lấy lịch sử học tập | | | | | |
| TC-02 | Trích xuất bảng điểm | | | | | |
| TC-03 | Kiểm tra hạ bằng | | | | | |
| TC-04 | Gợi ý môn kỳ tới | | | | | |
| TC-05 | Kiểm tra TKB | | | | | |
| TC-06 | Lộ trình tốt nghiệp | | | | | |
| TC-07 | Gợi ý cải thiện điểm | | | | | |
| TC-08 | Tính điểm cần đạt | | | | | |
| TC-09 | Kế hoạch ôn tập | | | | | |
| TC-10 | Theo dõi tiến độ | | | | | |
| TC-11 | Điều kiện tốt nghiệp | | | | | |
| TC-12 | Cảnh báo học vụ | | | | | |
| TC-13 | Multi-turn điều hướng | | | | | |
| TC-14 | Câu hỏi mơ hồ | | | | | |
| TC-15 | Điều chỉnh lộ trình | | | | | |
| **Tổng** | | | | | | |

---

## 8. Nhận xét & Kết luận

### Điểm mạnh

- 

### Điểm yếu / Vấn đề phát sinh

- 

### Đề xuất cải thiện

- 

---

# Chạy offline (không cần API key)
python -m src.benchmark.run_eval --mock

# Chạy 1 category
python -m src.benchmark.run_eval --category Regulation

# Chạy TC cụ thể
python -m src.benchmark.run_eval --ids TC-01 TC-03 TC-08

