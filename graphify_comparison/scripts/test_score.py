from score import aggregate


def test_aggregate_computes_mean_coverage_and_tokens_per_condition():
    harness_results = [
        {"question_id": "q01", "condition": "baseline", "total_tokens": 100},
        {"question_id": "q01", "condition": "aletheore", "total_tokens": 200},
    ]
    judge_results = [
        {"run": 0, "question_id": "q01", "condition": "baseline", "coverage": 0.5},
        {"run": 1, "question_id": "q01", "condition": "baseline", "coverage": 1.0},
        {"run": 0, "question_id": "q01", "condition": "aletheore", "coverage": 1.0},
        {"run": 1, "question_id": "q01", "condition": "aletheore", "coverage": 1.0},
    ]

    summary = aggregate(harness_results, judge_results)

    assert summary["baseline"]["coverage_mean"] == 0.75
    assert summary["baseline"]["tokens_mean"] == 100
    assert summary["aletheore"]["coverage_mean"] == 1.0
    assert summary["aletheore"]["tokens_mean"] == 200


def test_aggregate_skips_none_coverage_values():
    harness_results = [{"question_id": "q01", "condition": "baseline", "total_tokens": 100}]
    judge_results = [
        {"run": 0, "question_id": "q01", "condition": "baseline", "coverage": None},
        {"run": 1, "question_id": "q01", "condition": "baseline", "coverage": 1.0},
    ]
    summary = aggregate(harness_results, judge_results)
    assert summary["baseline"]["coverage_mean"] == 1.0
