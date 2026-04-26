"""
src/benchmark/run_eval.py
File thực thi chính – chạy toàn bộ benchmark và xuất báo cáo.

Sử dụng:
    # Chạy đầy đủ (cần OPENAI_API_KEY):
    python -m src.benchmark.run_eval

    # Chạy offline với mock agent:
    python -m src.benchmark.run_eval --mock

    # Chạy chỉ một số category:
    python -m src.benchmark.run_eval --category Background Regulation

    # Chạy một số TC cụ thể:
    python -m src.benchmark.run_eval --ids TC-01 TC-03 TC-08

    # Xuất báo cáo JSON:
    python -m src.benchmark.run_eval --output results/eval_$(date +%Y%m%d).json
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Đảm bảo import từ root project
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from data.test_cases import test_cases
from src.benchmark.agent_metrics import (
    check_tool_usage,
    check_keyword_coverage,
    check_asks_for_clarification,
    check_gpa_correctness,
    check_downgrade_correctness,
    aggregate_results,
)
from src.benchmark.agent_wrapper import create_wrapper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
)
logger = logging.getLogger("run_eval")


# ---------------------------------------------------------------------------
# Hằng số
# ---------------------------------------------------------------------------

RESULTS_DIR = ROOT / "results"
RUBRIC_SCALE = 3  # Điểm tối đa mỗi tiêu chí


# ---------------------------------------------------------------------------
# Evaluate một test case
# ---------------------------------------------------------------------------

def evaluate_single(
    tc: dict,
    wrapper,
    auto_score: bool = True,
) -> dict:
    """
    Chạy một test case và tính toán tất cả metrics tự động.

    Args:
        tc: Test case dict từ test_cases.py.
        wrapper: AgentWrapper hoặc MockAgentWrapper.
        auto_score: Nếu True, tự động tính rubric dựa trên keyword + tool coverage.

    Returns:
        Kết quả đánh giá đầy đủ.
    """
    tc_id = tc["id"]
    category = tc["category"]
    question = tc["question"]
    ground_truth = tc["ground_truth"]
    expected_tools = tc.get("expected_tools", [])

    logger.info("▶ Đang chạy %s [%s]: %s", tc_id, category, question[:70])

    # Gọi agent
    agent_result = wrapper.run(question, reset_conversation=True)
    response = agent_result["response"]
    tools_called = agent_result["tools_called"]
    latency = agent_result["latency_s"]
    error = agent_result["error"]

    # --- Metric 1: Tool usage ---
    tool_check = check_tool_usage(expected_tools, tools_called)

    # --- Metric 2: Keyword coverage ---
    keyword_check = check_keyword_coverage(response, ground_truth)

    # --- Metric 3: Clarification check (chỉ với MultiTurn) ---
    clarification_check = None
    if category == "MultiTurn" and not expected_tools:
        clarification_check = check_asks_for_clarification(response)

    # --- Metric 4: Domain-specific checks ---
    domain_check = None
    if "hạ bằng" in question.lower() or "downgrad" in question.lower():
        import re
        nums = re.findall(r"\b(\d+)\b", question)
        n_failed = int(nums[0]) if nums else 0
        domain_check = check_downgrade_correctness(response, n_failed)
    elif "gpa" in question.lower() and "cpa" in question.lower():
        # Ví dụ TC-35: CPA 3.1, 100 tín + 20 tín GPA 3.5
        domain_check = None  # Cần parse context phức tạp hơn

    # --- Auto rubric (nếu bật) ---
    rubric = None
    if auto_score:
        # Correctness: dựa trên domain check (nếu có) hoặc keyword coverage
        if domain_check is not None:
            correctness = RUBRIC_SCALE if domain_check.get("correct") else 0
        elif keyword_check["coverage"] >= 0.6:
            correctness = RUBRIC_SCALE
        elif keyword_check["coverage"] >= 0.35:
            correctness = RUBRIC_SCALE - 1
        else:
            correctness = 0

        # Completeness: dựa trên keyword coverage + tool recall
        tool_recall = tool_check["recall"]
        combined = (keyword_check["coverage"] + tool_recall) / 2
        if combined >= 0.75:
            completeness = RUBRIC_SCALE
        elif combined >= 0.45:
            completeness = RUBRIC_SCALE - 1
        else:
            completeness = 0

        # Helpfulness: dựa trên độ dài response và keyword coverage
        response_len = len(response.split())
        if response_len >= 30 and keyword_check["coverage"] >= 0.4:
            helpfulness = RUBRIC_SCALE
        elif response_len >= 10:
            helpfulness = RUBRIC_SCALE - 1
        else:
            helpfulness = 0

        total = correctness + completeness + helpfulness
        rubric = {
            "correctness": correctness,
            "completeness": completeness,
            "helpfulness": helpfulness,
            "total": total,
            "max": RUBRIC_SCALE * 3,
            "percentage": round(total / (RUBRIC_SCALE * 3), 3),
        }

    result = {
        "id": tc_id,
        "category": category,
        "question": question,
        "ground_truth": ground_truth,
        "response": response,
        "tools_called": tools_called,
        "expected_tools": expected_tools,
        "latency_s": latency,
        "error": error,
        "tool_check": tool_check,
        "keyword_check": keyword_check,
        "clarification_check": clarification_check,
        "domain_check": domain_check,
        "rubric": rubric,
        "timestamp": datetime.now().isoformat(),
    }

    # Log kết quả nhanh
    status_icon = "✅" if tool_check["score"] == "pass" else ("⚠️" if tool_check["score"] == "partial" else "❌")
    logger.info(
        "  %s Tool: %s | KW coverage: %.0f%% | Score: %s/9 | %.2fs",
        status_icon,
        tool_check["score"],
        keyword_check["coverage"] * 100,
        rubric["total"] if rubric else "N/A",
        latency,
    )

    return result


# ---------------------------------------------------------------------------
# In báo cáo ra console
# ---------------------------------------------------------------------------

def print_report(summary: dict, results: list[dict]) -> None:
    """In báo cáo tóm tắt ra console."""
    print("\n" + "=" * 60)
    print("  BENCHMARK REPORT – Academic Planning Multi-Agent")
    print("=" * 60)
    print(f"  Tổng số TC:          {summary['total_cases']}")
    print(f"  Avg Score:           {summary['overall_avg_score']} / {RUBRIC_SCALE * 3}")
    print(f"  Avg Tool Recall:     {summary['overall_avg_tool_recall']:.1%}")
    print(f"  Avg KW Coverage:     {summary['overall_avg_keyword_coverage']:.1%}")
    print()

    print("  Kết quả theo Category:")
    print(f"  {'Category':<15} {'Count':>5} {'Avg Score':>10} {'Tool Recall':>12}")
    print("  " + "-" * 45)
    for cat, stats in summary["by_category"].items():
        avg_score = f"{stats['avg_score']:.2f}" if stats["avg_score"] is not None else "N/A"
        avg_recall = f"{stats['avg_tool_recall']:.1%}" if stats["avg_tool_recall"] is not None else "N/A"
        print(f"  {cat:<15} {stats['count']:>5} {avg_score:>10} {avg_recall:>12}")

    print()
    print("  Chi tiết từng TC:")
    print(f"  {'ID':<8} {'Cat':<12} {'Score':>6} {'Tool':>7} {'KW%':>6} {'Latency':>8}")
    print("  " + "-" * 55)
    for r in results:
        rubric_total = r["rubric"]["total"] if r["rubric"] else 0
        tool_score = r["tool_check"]["score"]
        kw_pct = f"{r['keyword_check']['coverage']:.0%}"
        latency = f"{r['latency_s']:.2f}s"
        icon = "✅" if tool_score == "pass" else ("⚠" if tool_score == "partial" else "❌")
        print(f"  {r['id']:<8} {r['category']:<12} {rubric_total:>4}/9  {icon:<6} {kw_pct:>5} {latency:>8}")

    print("=" * 60)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Chạy benchmark đánh giá hệ thống multi-agent tư vấn học tập."
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Dùng MockAgentWrapper (không cần API key, chạy offline).",
    )
    parser.add_argument(
        "--category",
        nargs="+",
        help="Chỉ chạy các category cụ thể (VD: Background Regulation).",
    )
    parser.add_argument(
        "--ids",
        nargs="+",
        help="Chỉ chạy các TC theo ID cụ thể (VD: TC-01 TC-03).",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Đường dẫn file JSON để lưu kết quả. Mặc định: results/eval_<timestamp>.json",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=None,
        help="Đường dẫn tới file SQLite database.",
    )
    parser.add_argument(
        "--regulations-dir",
        type=str,
        default=None,
        help="Đường dẫn thư mục chứa PDF quy chế.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Thời gian chờ giữa các TC (giây). Mặc định: 1.0s",
    )
    parser.add_argument(
        "--no-auto-score",
        action="store_true",
        help="Tắt tự động tính rubric (chỉ collect response và tool calls).",
    )

    args = parser.parse_args()

    # --- Lọc test cases ---
    filtered_tcs = test_cases
    if args.ids:
        id_set = set(args.ids)
        filtered_tcs = [tc for tc in filtered_tcs if tc["id"] in id_set]
    if args.category:
        cat_set = set(args.category)
        filtered_tcs = [tc for tc in filtered_tcs if tc["category"] in cat_set]

    if not filtered_tcs:
        print("Không tìm thấy test case nào khớp với bộ lọc.")
        sys.exit(1)

    logger.info("Sẽ chạy %d test cases.", len(filtered_tcs))

    # --- Khởi tạo wrapper ---
    wrapper = create_wrapper(
        db_path=args.db_path,
        regulations_dir=args.regulations_dir,
        mock=args.mock,
    )

    # --- Chạy evaluation ---
    results = []
    total = len(filtered_tcs)
    for i, tc in enumerate(filtered_tcs):
        logger.info("Progress: %d/%d", i + 1, total)
        try:
            result = evaluate_single(tc, wrapper, auto_score=not args.no_auto_score)
        except Exception as e:
            logger.error("TC %s thất bại: %s", tc["id"], e)
            result = {
                "id": tc["id"],
                "category": tc["category"],
                "question": tc["question"],
                "ground_truth": tc["ground_truth"],
                "response": "",
                "tools_called": [],
                "expected_tools": tc.get("expected_tools", []),
                "latency_s": 0.0,
                "error": str(e),
                "tool_check": {"score": "fail", "recall": 0.0, "precision": 0.0,
                               "missing": tc.get("expected_tools", []), "extra": [],
                               "expected": tc.get("expected_tools", []), "actual": []},
                "keyword_check": {"coverage": 0.0, "passed": False,
                                  "matched_keywords": [], "missing_keywords": []},
                "clarification_check": None,
                "domain_check": None,
                "rubric": {"correctness": 0, "completeness": 0, "helpfulness": 0,
                           "total": 0, "max": 9, "percentage": 0.0},
                "timestamp": datetime.now().isoformat(),
            }
        results.append(result)

        # Delay giữa các TC (tránh rate limit)
        if args.delay > 0 and i < total - 1:
            time.sleep(args.delay)

    # --- Tổng hợp ---
    summary = aggregate_results(results)

    # --- In báo cáo ---
    print_report(summary, results)

    # --- Lưu kết quả ---
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    if args.output:
        output_path = Path(args.output)
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = RESULTS_DIR / f"eval_{ts}.json"

    output_data = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "total_cases": len(results),
            "mock_mode": args.mock,
            "categories": list({tc["category"] for tc in filtered_tcs}),
        },
        "summary": summary,
        "results": results,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    logger.info("✅ Kết quả đã lưu tại: %s", output_path)
    print(f"\n📄 Kết quả đầy đủ: {output_path}")


if __name__ == "__main__":
    main()
