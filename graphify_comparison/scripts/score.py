"""Aggregates raw harness + judge output into the per-condition summary
the README's results table is built from."""
import json
import os
import sys


def _search_codebase_calls(rec: dict) -> int:
    """How many of this record's tool calls actually hit Aletheore's
    embedding-backed semantic search, as opposed to a purely structural
    lookup (symbol-source/imports/imported-by) - the two are lumped
    together under one 'condition' but exercise very different capability,
    and nothing else in this file could previously tell them apart."""
    return sum(
        1 for call in rec.get("tool_calls", [])
        if call.get("tool") == "aletheore_query_tool" and call.get("kind") == "search-codebase"
    )


def aggregate(harness_results: list[dict], judge_results: list[dict]) -> dict:
    conditions = sorted({r["condition"] for r in harness_results})
    summary = {}
    for condition in conditions:
        cond_records = [r for r in harness_results if r["condition"] == condition]
        tokens = [r["total_tokens"] for r in cond_records]
        coverages = [
            r["coverage"] for r in judge_results
            if r["condition"] == condition and r["coverage"] is not None
        ]
        search_codebase_calls = sum(_search_codebase_calls(r) for r in cond_records)
        summary[condition] = {
            "coverage_mean": sum(coverages) / len(coverages) if coverages else None,
            "tokens_mean": sum(tokens) / len(tokens) if tokens else None,
            "n_coverage_samples": len(coverages),
            "n_token_samples": len(tokens),
            "search_codebase_calls": search_codebase_calls,
            "questions_using_search_codebase": sum(
                1 for r in cond_records if _search_codebase_calls(r) > 0
            ),
        }
    return summary


def main() -> int:
    HERE = os.path.dirname(os.path.abspath(__file__))
    ROOT = os.path.dirname(HERE)

    # Optional CLI arg mirrors run_harness.py's/judge.py's - selects the
    # alternate question set's result files.
    tag = sys.argv[1] if len(sys.argv) > 1 else "questions"
    harness_name = "harness_results.json" if tag == "questions" else f"{tag}_harness_results.json"
    judge_name = "judge_results.json" if tag == "questions" else f"{tag}_judge_results.json"
    summary_name = "summary.json" if tag == "questions" else f"{tag}_summary.json"

    with open(os.path.join(ROOT, "results", harness_name)) as f:
        harness_results = json.load(f)
    with open(os.path.join(ROOT, "results", judge_name)) as f:
        judge_results = json.load(f)

    summary = aggregate(harness_results, judge_results)

    out_path = os.path.join(ROOT, "results", summary_name)
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2))
    print(f"written to {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
