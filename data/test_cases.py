# data/test_cases.py
# 50 Test Cases cho hệ thống Multi-Agent Tư vấn Học tập HUST

test_cases = [

    # =========================================================
    # NHÓM 1: XÁC ĐỊNH USER BACKGROUND (TC-01 → TC-10)
    # =========================================================
    {
        "id": "TC-01",
        "category": "Background",
        "question": "Cho tôi xem kết quả học tập của sinh viên 20200001.",
        "ground_truth": "Danh sách môn đã học, điểm số, CPA hiện tại và số tín chỉ tích lũy của SV 20200001.",
        "expected_tools": ["get_user_history"],
    },
    {
        "id": "TC-02",
        "category": "Background",
        "question": "Sinh viên 20200002 đang học ngành gì và chương trình đào tạo nào?",
        "ground_truth": "Tên ngành học và curriculum_id của SV 20200002.",
        "expected_tools": ["get_user_history"],
    },
    {
        "id": "TC-03",
        "category": "Background",
        "question": "Tôi đã trượt 8 tín chỉ, tôi có bị hạ bằng không nếu muốn tốt nghiệp loại giỏi?",
        "ground_truth": "Có nguy cơ bị hạ bằng vì vượt quá ngưỡng 8 tín chỉ trượt cho phép.",
        "expected_tools": ["is_downgraded_degree"],
    },
    {
        "id": "TC-04",
        "category": "Background",
        "question": "Tôi trượt 5 tín chỉ, tôi có bị hạ bằng không?",
        "ground_truth": "Không bị hạ bằng vì chưa vượt ngưỡng 8 tín chỉ trượt.",
        "expected_tools": ["is_downgraded_degree"],
    },
    {
        "id": "TC-05",
        "category": "Background",
        "question": "Lấy chương trình đào tạo của ngành IT với curriculum_id IT2020.",
        "ground_truth": "Danh sách tất cả môn học trong CTĐT IT2020 kèm số tín chỉ và kỳ đề xuất.",
        "expected_tools": ["get_curriculum"],
    },
    {
        "id": "TC-06",
        "category": "Background",
        "question": "Sinh viên 20200003 còn bao nhiêu tín chỉ chưa hoàn thành?",
        "ground_truth": "Số tín chỉ còn lại = tổng tín chỉ yêu cầu - tín chỉ đã tích lũy của SV 20200003.",
        "expected_tools": ["get_user_history"],
    },
    {
        "id": "TC-07",
        "category": "Background",
        "question": "SV 20200001 đã trượt những môn nào?",
        "ground_truth": "Danh sách môn học có is_passed = False của SV 20200001.",
        "expected_tools": ["get_user_history"],
    },
    {
        "id": "TC-08",
        "category": "Background",
        "question": "CPA hiện tại của sinh viên 20200004 là bao nhiêu?",
        "ground_truth": "Giá trị current_cpa của SV 20200004 lấy từ bảng Students.",
        "expected_tools": ["get_user_history"],
    },
    {
        "id": "TC-09",
        "category": "Background",
        "question": "Cập nhật CPA mục tiêu của sinh viên 20200001 thành 3.6.",
        "ground_truth": "Cập nhật thành công trường target_cpa = 3.6 cho SV 20200001.",
        "expected_tools": ["update_user_history"],
    },
    {
        "id": "TC-10",
        "category": "Background",
        "question": "Sinh viên 20200005 có đủ điều kiện để đăng ký môn IT3011 không? Điều kiện tiên quyết là gì?",
        "ground_truth": "Thông tin điều kiện tiên quyết của IT3011 và kiểm tra SV 20200005 đã hoàn thành chưa.",
        "expected_tools": ["get_prerequisites", "get_user_history"],
    },

    # =========================================================
    # NHÓM 2: GỢI Ý MÔN HỌC & LỘ TRÌNH TỐT NGHIỆP (TC-11 → TC-25)
    # =========================================================
    {
        "id": "TC-11",
        "category": "Planning",
        "question": "Kỳ tới tôi (SV 20200001) nên đăng ký những môn nào? Tôi muốn học khoảng 18-20 tín chỉ.",
        "ground_truth": "Danh sách môn đủ điều kiện, có lớp mở kỳ tới, tổng 18-20 tín chỉ, ưu tiên môn bắt buộc.",
        "expected_tools": ["get_user_history", "filter_eligible_courses", "get_open_courses", "recommend_courses"],
    },
    {
        "id": "TC-12",
        "category": "Planning",
        "question": "Lấy danh sách các môn đang mở trong kỳ 20251.",
        "ground_truth": "Danh sách các môn học có lớp mở trong kỳ 20251 kèm số lớp và slot còn trống.",
        "expected_tools": ["get_open_courses"],
    },
    {
        "id": "TC-13",
        "category": "Planning",
        "question": "Môn IT3011 có những lớp nào đang mở? Lớp nào còn chỗ?",
        "ground_truth": "Danh sách các lớp của IT3011: mã lớp, lịch học, phòng, GV, số chỗ còn trống.",
        "expected_tools": ["get_open_classes"],
    },
    {
        "id": "TC-14",
        "category": "Planning",
        "question": "Kiểm tra thời khóa biểu của tôi có bị trùng lịch không? Tôi đã chọn lớp L01, L02, L03.",
        "ground_truth": "Kết quả is_valid và danh sách các cặp lớp xung đột (nếu có).",
        "expected_tools": ["validate_schedule"],
    },
    {
        "id": "TC-15",
        "category": "Planning",
        "question": "Gợi ý thời khóa biểu tốt nhất cho các môn IT3011, IT3120, IT4060 kỳ 20251.",
        "ground_truth": "Thời khóa biểu đề xuất không trùng lịch, còn slot, cho 3 môn trên.",
        "expected_tools": ["get_open_classes", "recommend_schedule"],
    },
    {
        "id": "TC-16",
        "category": "Planning",
        "question": "Tôi là SV 20200001, CPA 3.2, muốn tốt nghiệp xuất sắc (CPA ≥ 3.6). Lên lộ trình tốt nghiệp giúp tôi.",
        "ground_truth": "Lộ trình học từng kỳ còn lại, GPA cần đạt mỗi kỳ, cảnh báo hạ bằng nếu có.",
        "expected_tools": ["get_user_history", "get_curriculum", "recommend_graduation_path", "compute_required_gpa"],
    },
    {
        "id": "TC-17",
        "category": "Planning",
        "question": "SV 20200002 muốn tốt nghiệp loại giỏi (CPA ≥ 3.2). Cần học thêm bao nhiêu kỳ?",
        "ground_truth": "Số kỳ còn lại dự kiến và lộ trình phân bổ môn học theo từng kỳ.",
        "expected_tools": ["get_user_history", "get_curriculum", "recommend_graduation_path"],
    },
    {
        "id": "TC-18",
        "category": "Planning",
        "question": "Tôi muốn cải thiện CPA từ 3.0 lên 3.4. Nên học lại môn nào?",
        "ground_truth": "Danh sách môn nên cải thiện sắp xếp theo mức tác động tới CPA (potential_gain giảm dần).",
        "expected_tools": ["get_user_history", "recommend_improvement_courses"],
    },
    {
        "id": "TC-19",
        "category": "Planning",
        "question": "Tôi vừa trượt môn Giải tích 2. Điều chỉnh lại lộ trình tốt nghiệp giúp tôi.",
        "ground_truth": "Lộ trình cập nhật với môn Giải tích 2 được thêm vào kỳ gần nhất có thể.",
        "expected_tools": ["get_user_history", "recommend_graduation_path", "modify_graduation_path"],
    },
    {
        "id": "TC-20",
        "category": "Planning",
        "question": "Điều kiện tiên quyết của môn Trí tuệ nhân tạo (IT3160) là gì?",
        "ground_truth": "Danh sách môn tiên quyết/song hành của IT3160.",
        "expected_tools": ["get_prerequisites"],
    },
    {
        "id": "TC-21",
        "category": "Planning",
        "question": "SV 20200003 đủ điều kiện đăng ký những môn nào trong kỳ 20252?",
        "ground_truth": "Danh sách môn đủ điều kiện (đã qua tiên quyết, chưa pass) có lớp mở kỳ 20252.",
        "expected_tools": ["get_user_history", "filter_eligible_courses", "get_open_courses"],
    },
    {
        "id": "TC-22",
        "category": "Planning",
        "question": "Tôi muốn chuyển môn IT4060 từ kỳ 2 sang kỳ 3 trong lộ trình. Cập nhật giúp tôi.",
        "ground_truth": "Lộ trình sau khi di chuyển IT4060 sang semester_3.",
        "expected_tools": ["modify_graduation_path"],
    },
    {
        "id": "TC-23",
        "category": "Planning",
        "question": "Nếu tôi đạt điểm A tất cả môn còn lại, CPA tốt nghiệp của tôi sẽ là bao nhiêu?",
        "ground_truth": "CPA dự kiến khi đạt điểm 4.0 toàn bộ môn còn lại.",
        "expected_tools": ["get_user_history", "compute_required_gpa"],
    },
    {
        "id": "TC-24",
        "category": "Planning",
        "question": "SV 20200001 còn thiếu những môn bắt buộc nào chưa học?",
        "ground_truth": "Danh sách môn is_mandatory = True trong CTĐT mà SV 20200001 chưa passed.",
        "expected_tools": ["get_user_history", "get_curriculum", "filter_eligible_courses"],
    },
    {
        "id": "TC-25",
        "category": "Planning",
        "question": "Giải thích tại sao bạn gợi ý tôi đăng ký IT3011 kỳ này.",
        "ground_truth": "Giải thích dựa trên: môn bắt buộc, tiên quyết đã đủ, kỳ đề xuất phù hợp.",
        "expected_tools": ["explain_recommendation"],
    },

    # =========================================================
    # NHÓM 3: KẾ HOẠCH & GIÁM SÁT TIẾN ĐỘ (TC-26 → TC-35)
    # =========================================================
    {
        "id": "TC-26",
        "category": "Progress",
        "question": "Tôi còn 3 kỳ học, CPA hiện tại 3.0, muốn tốt nghiệp loại giỏi (CPA ≥ 3.2). Tôi cần đạt GPA bao nhiêu mỗi kỳ?",
        "ground_truth": "GPA cần đạt mỗi kỳ thường rơi vào khoảng 3.4–3.5 tùy vào số tín chỉ còn lại.",
        "expected_tools": ["recommend_graduation_path", "compute_required_gpa"],
    },
    {
        "id": "TC-27",
        "category": "Progress",
        "question": "Với lộ trình hiện tại, tôi cần đạt điểm bao nhiêu cho từng môn còn lại?",
        "ground_truth": "Điểm tối thiểu cần đạt (grade_number) cho từng môn trong lộ trình.",
        "expected_tools": ["compute_required_gpa", "compute_required_score"],
    },
    {
        "id": "TC-28",
        "category": "Progress",
        "question": "Lập kế hoạch ôn tập tuần này cho tôi. Kỳ này tôi học IT3011, IT3120, IT4060. Lịch rảnh: sáng T2, T4, T6.",
        "ground_truth": "Kế hoạch học tập phân bổ thời gian ôn tập từng môn vào các buổi sáng T2, T4, T6.",
        "expected_tools": ["recommend_study_plan"],
    },
    {
        "id": "TC-29",
        "category": "Progress",
        "question": "Tuần này tôi đã hoàn thành 3/5 buổi học theo kế hoạch, bài tập Giải tích bị trễ 2 ngày. Cập nhật tiến độ.",
        "ground_truth": "Báo cáo tiến độ 60%, cảnh báo trễ bài tập Giải tích, gợi ý điều chỉnh.",
        "expected_tools": ["tracking_progress"],
    },
    {
        "id": "TC-30",
        "category": "Progress",
        "question": "Tôi muốn cải thiện điểm môn IT3011 từ C lên A. Cần đạt điểm bao nhiêu trong kỳ thi cuối?",
        "ground_truth": "Điểm thi cuối cần đạt để nâng điểm tổng kết lên A, tùy tỷ lệ thành phần điểm.",
        "expected_tools": ["compute_required_score"],
    },
    {
        "id": "TC-31",
        "category": "Progress",
        "question": "Tiến độ học tập tuần này của tôi như thế nào so với kế hoạch?",
        "ground_truth": "Tỷ lệ hoàn thành kế hoạch, các hạng mục trễ, đề xuất bù đắp.",
        "expected_tools": ["tracking_progress"],
    },
    {
        "id": "TC-32",
        "category": "Progress",
        "question": "Tôi cần đạt GPA bao nhiêu trong kỳ này nếu CPA hiện tại là 2.8 và muốn tránh cảnh báo học vụ (CPA ≥ 2.0)?",
        "ground_truth": "GPA tối thiểu kỳ này để đưa CPA về ≥ 2.0 (thường không cần quá cao).",
        "expected_tools": ["compute_required_gpa"],
    },
    {
        "id": "TC-33",
        "category": "Progress",
        "question": "Lập kế hoạch ôn thi cuối kỳ cho 4 môn: IT3011, IT3120, IT4060, MI1110. Còn 3 tuần.",
        "ground_truth": "Kế hoạch ôn thi 3 tuần phân bổ đều cho 4 môn, ưu tiên môn khó/nhiều tín chỉ hơn.",
        "expected_tools": ["recommend_study_plan"],
    },
    {
        "id": "TC-34",
        "category": "Progress",
        "question": "Tôi đã hoàn thành 80% kế hoạch tuần trước. Tuần này cần điều chỉnh gì?",
        "ground_truth": "Đánh giá tiến độ tốt (80%), gợi ý tiếp tục và bù phần còn thiếu 20%.",
        "expected_tools": ["tracking_progress"],
    },
    {
        "id": "TC-35",
        "category": "Progress",
        "question": "Nếu kỳ này tôi đạt GPA 3.5 với 20 tín chỉ, CPA của tôi sẽ thay đổi thế nào? CPA hiện tại 3.1, đã tích 100 tín.",
        "ground_truth": "CPA mới = (3.1×100 + 3.5×20) / 120 ≈ 3.17.",
        "expected_tools": ["compute_required_gpa"],
    },

    # =========================================================
    # NHÓM 4: QUY CHẾ ĐÀO TẠO – RegulationAgent (TC-36 → TC-44)
    # =========================================================
    {
        "id": "TC-36",
        "category": "Regulation",
        "question": "Điều kiện để được xét tốt nghiệp đại học loại xuất sắc tại HUST là gì?",
        "ground_truth": "CPA ≥ 3.6, không bị hạ bằng, đủ tín chỉ, điểm rèn luyện đạt yêu cầu.",
        "expected_tools": ["query_regulation"],
    },
    {
        "id": "TC-37",
        "category": "Regulation",
        "question": "Tôi bị cảnh báo học vụ mức 1, có bị đuổi học không?",
        "ground_truth": "Cảnh báo mức 1 chưa bị đuổi học nhưng cần cải thiện CPA trong kỳ tiếp theo.",
        "expected_tools": ["search_regulation"],
    },
    {
        "id": "TC-38",
        "category": "Regulation",
        "question": "Ngưỡng CPA tối thiểu để không bị cảnh báo học vụ là bao nhiêu?",
        "ground_truth": "CPA tối thiểu thường là 1.6–2.0 tùy theo năm học, theo quy chế đào tạo HUST.",
        "expected_tools": ["search_regulation"],
    },
    {
        "id": "TC-39",
        "category": "Regulation",
        "question": "Sinh viên có thể học cải thiện điểm bao nhiêu lần cho một môn?",
        "ground_truth": "Theo quy chế, sinh viên được đăng ký học lại/cải thiện môn đã qua tối đa số lần quy định.",
        "expected_tools": ["query_regulation"],
    },
    {
        "id": "TC-40",
        "category": "Regulation",
        "question": "Quy định về số tín chỉ tối đa được đăng ký trong một kỳ là bao nhiêu?",
        "ground_truth": "Thông thường tối đa 24 tín chỉ/kỳ, tùy xếp loại học lực theo quy chế.",
        "expected_tools": ["search_regulation"],
    },
    {
        "id": "TC-41",
        "category": "Regulation",
        "question": "Điều kiện xét học bổng khuyến khích học tập là gì?",
        "ground_truth": "Các tiêu chí về CPA, xếp loại rèn luyện, không có môn điểm F theo quy chế.",
        "expected_tools": ["search_regulation"],
    },
    {
        "id": "TC-42",
        "category": "Regulation",
        "question": "Sinh viên bị đình chỉ học tập trong trường hợp nào?",
        "ground_truth": "Bị đình chỉ khi CPA dưới ngưỡng nhiều kỳ liên tiếp hoặc vi phạm quy chế nghiêm trọng.",
        "expected_tools": ["search_regulation"],
    },
    {
        "id": "TC-43",
        "category": "Regulation",
        "question": "Quy định về bảo lưu kết quả học tập và thôi học tạm thời là gì?",
        "ground_truth": "Sinh viên được bảo lưu tối đa X năm vì lý do sức khỏe, gia đình theo quy chế.",
        "expected_tools": ["query_regulation"],
    },
    {
        "id": "TC-44",
        "category": "Regulation",
        "question": "Thang điểm chữ và điểm số tương đương theo quy chế HUST là gì?",
        "ground_truth": "Bảng quy đổi: A=4.0, B+=3.5, B=3.0, C+=2.5, C=2.0, D+=1.5, D=1.0, F=0.",
        "expected_tools": ["query_regulation"],
    },

    # =========================================================
    # NHÓM 5: ĐIỀU HƯỚNG & MULTI-TURN (TC-45 → TC-50)
    # =========================================================
    {
        "id": "TC-45",
        "category": "MultiTurn",
        "question": "Tôi cần tư vấn học tập.",
        "ground_truth": "Agent hỏi lại để làm rõ ý định và yêu cầu cung cấp student_id trước khi tra cứu.",
        "expected_tools": [],  # Không gọi tool ngay, phải hỏi lại
    },
    {
        "id": "TC-46",
        "category": "MultiTurn",
        "question": "Điều kiện tốt nghiệp xuất sắc là gì? Rồi sau đó kiểm tra SV 20200001 có đủ không?",
        "ground_truth": "Turn 1: điều kiện xuất sắc từ RegulationAgent. Turn 2: so sánh với dữ liệu SV 20200001.",
        "expected_tools": ["query_regulation", "get_user_history"],
    },
    {
        "id": "TC-47",
        "category": "MultiTurn",
        "question": "Câu hỏi không liên quan: Hôm nay thời tiết thế nào?",
        "ground_truth": "Agent từ chối lịch sự, giải thích chỉ hỗ trợ tư vấn học tập.",
        "expected_tools": [],
    },
    {
        "id": "TC-48",
        "category": "MultiTurn",
        "question": "Tôi là SV 20200001. Kỳ tới nên đăng ký môn gì? Sau đó lập kế hoạch ôn tập luôn.",
        "ground_truth": "Gợi ý môn đăng ký kỳ tới, sau đó lập kế hoạch học tập cho các môn đó.",
        "expected_tools": ["filter_eligible_courses", "recommend_courses", "recommend_study_plan"],
    },
    {
        "id": "TC-49",
        "category": "MultiTurn",
        "question": "Tôi muốn tốt nghiệp xuất sắc. CPA tôi là 3.3, còn 2 kỳ. Tôi có thể làm được không? Nếu được thì cần GPA bao nhiêu?",
        "ground_truth": "Đánh giá khả năng (có thể nếu đạt GPA ≈ 4.0 mỗi kỳ), tính GPA cần đạt cụ thể.",
        "expected_tools": ["compute_required_gpa", "is_downgraded_degree"],
    },
    {
        "id": "TC-50",
        "category": "MultiTurn",
        "question": "Tôi không nhớ mã SV của mình. Tên tôi là Nguyễn Văn A, ngành CNTT.",
        "ground_truth": "Agent thông báo cần student_id chính xác để tra cứu, không thể tìm theo tên.",
        "expected_tools": [],
    },
]

# Tổng số test cases
TOTAL_TEST_CASES = len(test_cases)

# Index theo category
CATEGORIES = {}
for tc in test_cases:
    cat = tc["category"]
    CATEGORIES.setdefault(cat, []).append(tc["id"])

if __name__ == "__main__":
    print(f"Tổng số test cases: {TOTAL_TEST_CASES}")
    for cat, ids in CATEGORIES.items():
        print(f"  {cat}: {len(ids)} cases ({', '.join(ids)})")
