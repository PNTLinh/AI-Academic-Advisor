INGEST_EXAMPLE = {
    "status": "success",
    "extracted_courses": [
        {
            "course_id": "MATH201",
            "name": "Calculus I",
            "credits": 4,
            "grade": "B+",
            "is_passed": True
        },
        {
            "course_id": "PHYS101",
            "name": "Physics I",
            "credits": 4,
            "grade": "F",
            "is_passed": False
        }
    ]
}

STATUS_EXAMPLE = {
    "persona": {
        "gpa": 2.67,
        "standing": "Warning",
        "credits_summary": {
            "earned": 72,
            "total_required": 120,
            "debt": 12
        },
        "categorized_lists": {
            "passed": ["MATH201", "CS101"],
            "failed": ["PHYS101", "PHYS102"],
            "can_improve": ["ENG101"]
        }
    }
}

SET_GOALS_EXAMPLE = {
    "extracted_goals": ["Tốt nghiệp sớm", "GPA >= 3.0"],
    "limits": {
        "min_credits": 15,
        "max_credits": 22,
        "difficulty_cap": 0.75
    }
}

RECOMMEND_EXAMPLE = {
    "suggested_cart": [
        {
            "course_id": "PHYS101",
            "priority": "Critical",
            "reason": "Môn nợ cần trả để học PHYS102",
            "difficulty_score": 0.8
        },
        {
            "course_id": "MATH301",
            "priority": "High",
            "reason": "Môn tiên quyết cho Đồ án chuyên ngành",
            "difficulty_score": 0.6
        }
    ],
    "total_credits": 18,
    "balance_status": "Balanced"
}

ROADMAP_EXAMPLE = {
    "overall_plan": {
        "graduation_date": "Spring 2027",
        "semesters_remaining": 6
    },
    "optimized_roadmap": [
        {
            "term": "Fall 2026",
            "is_summer": False,
            "credits": 18,
            "term_difficulty": 0.68,
            "courses": [
                {
                    "id": "CS301",
                    "name": "Algorithms",
                    "type": "Core",
                    "difficulty": 0.85,
                    "reasoning": "Đẩy lên sớm để gỡ nút thắt kỳ lẻ"
                }
            ]
        }
    ],
    "insights": [
        "Lộ trình đã dàn trải đều các môn nặng để tránh quá tải",
        "Sử dụng học kỳ hè 2026 để rút ngắn thời gian 1 học kỳ"
    ]
}

REOPTIMIZE_EXAMPLE = {
    "reoptimization_report": {
        "status": "Success",
        "incident_resolved": "FAILED_COURSE: MATH201",
        "action_taken": "Rescheduled MATH201 to Summer 2024 to maintain Spring 2027 graduation",
        "impact_severity": "Medium"
    },
    "new_optimized_roadmap": {
        "overall_stats": {
            "total_semesters": 6,
            "estimated_graduation": "Spring 2027",
            "avg_difficulty_score": 0.68
        },
        "semesters": [
            {
                "term": "Summer 2024",
                "is_summer": True,
                "total_credits": 4,
                "courses": [
                    {
                        "id": "MATH201",
                        "name": "Calculus I",
                        "type": "Retake",
                        "priority": "Critical",
                        "reasoning": "Môn vừa trượt, cần học ngay kỳ hè để kịp tiến độ Calculus II"
                    }
                ]
            }
        ],
        "bottlenecks_resolved": [
            "Dời Calculus II sang kỳ Thu 2024 để đảm bảo thứ tự tiên quyết",
            "Bổ sung kỳ hè để không kéo dài thời gian ra trường"
        ],
        "warnings": [
            "Tổng độ khó kỳ hè tăng nhẹ do tính chất học nén"
        ]
    }
}

CHAT_MOCK_RESPONSE = {
    "reply": "Xin lỗi, tôi đang gặp sự cố tạm thời kết nối với AI Assistant. Bạn vui lòng thử lại trong giây lát. Nếu sự cố tiếp tục, bạn có thể liên hệ với bộ phận hỗ trợ của chúng tôi.",
    "debug_info": "Mock response - Agent service unavailable"
}
