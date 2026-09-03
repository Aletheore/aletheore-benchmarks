"""Scores one or more scanner result files (from run_aletheore.py /
run_repowise.py) against cases/*/ground_truth.yaml. No API key, no
network - pure comparison against the checked-in raw results.

Usage: python3 score.py results/repowise.json results/aletheore_pypi.json results/aletheore_fixed.json
"""
import json
import sys
from pathlib import Path

import yaml

CASES_DIR = Path(__file__).parent.parent / "cases"


def load_ground_truth() -> dict:
    truth = {}
    for case_dir in sorted(CASES_DIR.iterdir()):
        if case_dir.is_dir():
            truth[case_dir.name] = yaml.safe_load((case_dir / "ground_truth.yaml").read_text())
    return truth


def score(result_path: Path, truth: dict) -> dict:
    data = json.loads(result_path.read_text())
    verdicts = {}
    for case_id, gt in truth.items():
        findings = data["cases"].get(case_id, [])
        # RepoWise findings have no suppression concept (every finding it
        # emits is "reported"); aletheore findings carry a `reported` flag
        # (already filtered to `not likely_placeholder` by run_aletheore.py).
        # `.get("reported", True)` treats a finding with no such key
        # (RepoWise) as reported - the fair comparison, since both tools'
        # findings are being asked the same question: "does this show up
        # as a live result a user would see?"
        hit = any(
            f["path"] == gt["expected_path"] and f["line"] == gt["expected_line"] and f.get("reported", True)
            for f in findings
        )
        if gt["category"] == "true_positive":
            verdicts[case_id] = "TP" if hit else "FN"
        else:
            verdicts[case_id] = "FP" if hit else "TN"
    return {"tool": data["tool"], "version": data["version"], "verdicts": verdicts}


def main() -> int:
    truth = load_ground_truth()
    paths = [Path(p) for p in sys.argv[1:]]
    if not paths:
        print("usage: score.py <results.json>...", file=sys.stderr)
        return 1

    scored = [score(p, truth) for p in paths]

    header = f"{'case_id':<38}" + "".join(f"{s['tool']+' '+s['version']:<22}" for s in scored)
    print(header)
    for case_id in truth:
        row = f"{case_id:<38}"
        for s in scored:
            row += f"{s['verdicts'][case_id]:<22}"
        print(row)

    print()
    for s in scored:
        tp = sum(1 for c, v in s["verdicts"].items() if truth[c]["category"] == "true_positive" and v == "TP")
        tp_total = sum(1 for c in truth if truth[c]["category"] == "true_positive")
        fp = sum(1 for c, v in s["verdicts"].items() if truth[c]["category"] == "true_negative" and v == "FP")
        fp_total = sum(1 for c in truth if truth[c]["category"] == "true_negative")
        print(f"{s['tool']} {s['version']}: recall {tp}/{tp_total}, false positives {fp}/{fp_total}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
