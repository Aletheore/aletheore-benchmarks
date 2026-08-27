"""Aggregates raw harness + judge output into the per-condition summary
the README's results table is built from."""
import json
import os
import sys


def aggregate(harness_results: list[dict], judge_results: list[dict]) -> dict:
    conditions = sorted({r["condition"] for r in harness_results})
    summary = {}
    for condition in conditions:
        tokens = [r["total_tokens"] for r in harness_results if r["condition"] == condition]
        coverages = [
            r["coverage"] for r in judge_results
            if r["condition"] == condition and r["coverage"] is not None
        ]
        summary[condition] = {
            "coverage_mean": sum(coverages) / len(coverages) if coverages else None,
            "tokens_mean": sum(tokens) / len(tokens) if tokens else None,
            "n_coverage_samples": len(coverages),
            "n_token_samples": len(tokens),
        }
    return summary


def main() -> int:
    HERE = os.path.dirname(os.path.abspath(__file__))
    ROOT = os.path.dirname(HERE)
    with open(os.path.join(ROOT, "results", "harness_results.json")) as f:
        harness_results = json.load(f)
    with open(os.path.join(ROOT, "results", "judge_results.json")) as f:
        judge_results = json.load(f)

    summary = aggregate(harness_results, judge_results)

    out_path = os.path.join(ROOT, "results", "summary.json")
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2))
    print(f"written to {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
