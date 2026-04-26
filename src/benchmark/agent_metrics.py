"""
src/benchmark/agent_metrics.py
Các hàm tính metric đánh giá chất lượng output của agent.
"""
from __future__ import annotations

import re
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1. Tool Usage Check
# ---------------------------------------------------------------------------

def check_tool_usage(
    expected_tools: list[str],
    actual_tools_called: list[str],
) -> dict:
    """
    Kiểm tra agent có gọi đúng tool theo kỳ vọng không.

    Returns:
        {
            "score": "pass" | "partial" | "fail",
            "expected": [...],
            "actual": [...],
            "missing": [...],
            "extra": [...],
            "precision": float,  # actual ∩ expected / actual
            "recall": float,     # actual ∩ expected / expected
        }
    """
    expected_set = set(expected_tools)
    actual_set = set(actual_tools_called)

    # Trường hợp đặc biệt: expected rỗng → agent không nên gọi tool
    if not expected_set:
        score = "pass" if not actual_set else "fail"
        return {
            "score": score,
            "expected": expected_tools,
            "actual": actual_tools_called,
            "missing": [],
            "extra": list(actual_set),
            "precision": 1.0 if not actual_set else 0.0,
            "recall": 1.0,
        }

    intersection = expected_set & actual_set
    missing = list(expected_set - actual_set)
    extra = list(actual_set - expected_set)

    precision = len(intersection) / len(actual_set) if actual_set else 0.0
    recall = len(intersection) / len(expected_set) if expected_set else 0.0

    if recall == 1.0:
        score = "pass"
    elif recall >= 0.5:
        score = "partial"
    else:
        score = "fail"

    return {
        "score": score,
        "expected": expected_tools,
        "actual": actual_tools_called,
        "missing": missing,
        "extra": extra,
        "precision": round(precision, 3),
        "recall": round(recall, 3),
    }


# ---------------------------------------------------------------------------
# 2. GPA / CPA Correctness Check
# ---------------------------------------------------------------------------

def check_gpa_correctness(
    response_text: str,
    current_cpa: float,
    credits_done: int,
    credits_remaining: int,
    target_cpa: float,
    tolerance: float = 0.05,
) -> dict:
    """
    Kiểm tra xem GPA cần đạt trong response có đúng công thức không.

    Công thức:
        required_gpa = (target_cpa * total_credits - current_cpa * credits_done)
                       / credits_remaining

    Args:
        response_text: Text trả lời của agent.
        current_cpa: CPA hiện tại của sinh viên.
        credits_done: Số tín chỉ đã tích lũy.
        credits_remaining: Số tín chỉ còn lại.
        target_cpa: CPA mục tiêu.
        tolerance: Sai số cho phép (mặc định ±0.05).

    Returns:
        {"correct": bool, "expected_gpa": float, "found_in_response": float | None}
    """
    total_credits = credits_done + credits_remaining
    if credits_remaining <= 0:
        return {"correct": True, "expected_gpa": 0.0, "found_in_response": None}

    expected_gpa = (target_cpa * total_credits - current_cpa * credits_done) / credits_remaining
    expected_gpa = round(min(max(expected_gpa, 0.0), 4.0), 3)

    # Tìm số thập phân trong response
    numbers = re.findall(r"\b(\d+\.\d+)\b", response_text)
    found = None
    for n in numbers:
        val = float(n)
        if 0.0 <= val <= 4.0:
            if abs(val - expected_gpa) <= tolerance:
                found = val
                break

    return {
        "correct": found is not None,
        "expected_gpa": expected_gpa,
        "found_in_response": found,
        "tolerance": tolerance,
    }


def check_downgrade_correctness(
    response_text: str,
    n_failed_credits: int,
    threshold: int = 8,
) -> dict:
    """
    Kiểm tra câu trả lời về hạ bằng có đúng logic không.

    Args:
        response_text: Text trả lời của agent.
        n_failed_credits: Số tín chỉ trượt.
        threshold: Ngưỡng hạ bằng (mặc định 8 tín chỉ).

    Returns:
        {"correct": bool, "expected_downgraded": bool, "response_says_downgraded": bool | None}
    """
    expected_downgraded = n_failed_credits > threshold
    text_lower = response_text.lower()

    # Phát hiện từ khóa
    yes_keywords = ["bị hạ bằng", "hạ bằng", "vượt ngưỡng", "quá giới hạn", "có nguy cơ"]
    no_keywords = ["không bị hạ", "chưa bị hạ", "không ảnh hưởng", "trong giới hạn", "chưa vượt"]

    response_says_yes = any(kw in text_lower for kw in yes_keywords)
    response_says_no = any(kw in text_lower for kw in no_keywords)

    if response_says_yes and not response_says_no:
        response_says_downgraded = True
    elif response_says_no and not response_says_yes:
        response_says_downgraded = False
    else:
        response_says_downgraded = None  # Không xác định được

    correct = (response_says_downgraded == expected_downgraded)

    return {
        "correct": correct,
        "expected_downgraded": expected_downgraded,
        "response_says_downgraded": response_says_downgraded,
        "n_failed_credits": n_failed_credits,
        "threshold": threshold,
    }


# ---------------------------------------------------------------------------
# 3. Keyword / Semantic Coverage Check
# ---------------------------------------------------------------------------

def check_keyword_coverage(
    response_text: str,
    ground_truth: str,
    min_coverage: float = 0.4,
) -> dict:
    """
    Kiểm tra xem response có chứa các từ khóa quan trọng từ ground_truth.

    Tokenize đơn giản theo khoảng trắng, bỏ stop words tiếng Việt cơ bản.

    Returns:
        {
            "coverage": float,
            "matched_keywords": [...],
            "missing_keywords": [...],
            "passed": bool,
        }
    """
    STOP_WORDS = {
        "là", "của", "và", "có", "không", "tôi", "bạn", "trong",
        "để", "với", "các", "những", "một", "này", "đó", "được",
        "cho", "theo", "từ", "về", "hay", "hoặc", "nếu", "thì",
        "khi", "đã", "sẽ", "đang", "cần", "phải",
    }

    def tokenize(text: str) -> set[str]:
        words = re.findall(r"[a-zA-Z0-9À-ỹ]+", text.lower())
        return {w for w in words if w not in STOP_WORDS and len(w) > 2}

    gt_tokens = tokenize(ground_truth)
    resp_tokens = tokenize(response_text)

    if not gt_tokens:
        return {"coverage": 1.0, "matched_keywords": [], "missing_keywords": [], "passed": True}

    matched = gt_tokens & resp_tokens
    missing = gt_tokens - resp_tokens
    coverage = len(matched) / len(gt_tokens)

    return {
        "coverage": round(coverage, 3),
        "matched_keywords": sorted(matched),
        "missing_keywords": sorted(missing),
        "passed": coverage >= min_coverage,
    }


# ---------------------------------------------------------------------------
# 4. Clarification Check (TC dạng câu hỏi mơ hồ)
# ---------------------------------------------------------------------------

def check_asks_for_clarification(response_text: str) -> dict:
    """
    Kiểm tra agent có hỏi lại để làm rõ thông tin không
    (thay vì tự suy đoán và gọi tool ngay).

    Returns:
        {"asks_clarification": bool, "asks_student_id": bool}
    """
    text_lower = response_text.lower()
    clarification_keywords = [
        "mã sinh viên", "student_id", "bạn có thể cho tôi biết",
        "vui lòng cung cấp", "bạn muốn", "cụ thể hơn",
        "cho tôi biết thêm", "bạn đang hỏi về", "ý bạn là",
    ]
    student_id_keywords = ["mã sinh viên", "student_id", "mã sv"]

    asks_clarification = any(kw in text_lower for kw in clarification_keywords)
    asks_student_id = any(kw in text_lower for kw in student_id_keywords)

    return {
        "asks_clarification": asks_clarification,
        "asks_student_id": asks_student_id,
    }


# ---------------------------------------------------------------------------
# 5. Rubric Scoring (manual-assist)
# ---------------------------------------------------------------------------

def compute_rubric_score(
    correctness: int,
    completeness: int,
    helpfulness: int,
) -> dict:
    """
    Tính điểm rubric tổng hợp.

    Args:
        correctness: 0–3
        completeness: 0–3
        helpfulness: 0–3

    Returns:
        {"total": int, "max": int, "percentage": float, "grade": str}
    """
    assert 0 <= correctness <= 3
    assert 0 <= completeness <= 3
    assert 0 <= helpfulness <= 3

    total = correctness + completeness + helpfulness
    percentage = total / 9.0

    if percentage >= 0.89:
        grade = "A"
    elif percentage >= 0.78:
        grade = "B"
    elif percentage >= 0.67:
        grade = "C"
    elif percentage >= 0.56:
        grade = "D"
    else:
        grade = "F"

    return {
        "correctness": correctness,
        "completeness": completeness,
        "helpfulness": helpfulness,
        "total": total,
        "max": 9,
        "percentage": round(percentage, 3),
        "grade": grade,
    }


# ---------------------------------------------------------------------------
# 6. Aggregate results
# ---------------------------------------------------------------------------

def aggregate_results(results: list[dict]) -> dict:
    """
    Tổng hợp kết quả đánh giá toàn bộ test cases.

    Args:
        results: List kết quả từng TC (output của run_eval).

    Returns:
        Thống kê tổng hợp theo category và overall.
    """
    if not results:
        return {}

    by_category: dict[str, list] = {}
    overall_scores = []
    tool_recalls = []
    keyword_coverages = []

    for r in results:
        cat = r.get("category", "Unknown")
        by_category.setdefault(cat, []).append(r)

        if "rubric" in r:
            overall_scores.append(r["rubric"]["total"])
        if "tool_check" in r:
            tool_recalls.append(r["tool_check"]["recall"])
        if "keyword_check" in r:
            keyword_coverages.append(r["keyword_check"]["coverage"])

    # Per-category stats
    cat_stats = {}
    for cat, cat_results in by_category.items():
        scores = [r["rubric"]["total"] for r in cat_results if "rubric" in r]
        recalls = [r["tool_check"]["recall"] for r in cat_results if "tool_check" in r]
        cat_stats[cat] = {
            "count": len(cat_results),
            "avg_score": round(sum(scores) / len(scores), 2) if scores else None,
            "avg_tool_recall": round(sum(recalls) / len(recalls), 3) if recalls else None,
        }

    return {
        "total_cases": len(results),
        "overall_avg_score": round(sum(overall_scores) / len(overall_scores), 2) if overall_scores else None,
        "overall_avg_tool_recall": round(sum(tool_recalls) / len(tool_recalls), 3) if tool_recalls else None,
        "overall_avg_keyword_coverage": round(sum(keyword_coverages) / len(keyword_coverages), 3) if keyword_coverages else None,
        "by_category": cat_stats,
    }
