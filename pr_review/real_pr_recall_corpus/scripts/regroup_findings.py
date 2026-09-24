"""Applies Aletheore's real ranking pass (flash_review._rank_findings_with_severity,
which now also links repeats of one root cause via same_root_as) to an existing
stored run's findings, and writes them back out in the shape
judge_full_pipeline.py's --aletheore-results expects.

Purpose: test whether stating "same root cause as X" on repeat findings - the
presentation GitLab already uses natively - changes how a judge scores them,
WITHOUT regenerating anything (no new generation spend) and without dropping or
merging a single finding: every stored finding is kept, at its own file and line,
so recall cannot fall from removal. Only the issue text changes, and it changes
through flash_review.related_finding_issue_text - the same helper jobs.py uses for
the real PR comment - so what the judge scores is what a user would actually see,
not a benchmark-only rewrite.

Fails open exactly like production: if the ranking call fails for a case, that
case's findings pass through unchanged (and it's reported, so an unlinked case is
never mistaken for "the model found no repeats").

Usage (needs a Python env with the Aletheore worktree's github-app deps, and
INDIEROUTER_API_KEY):
    python3 regroup_findings.py \\
        --aletheore-root /path/to/Aletheore-worktree \\
        --results ../results/aletheore_3x_results.json \\
        --output ../results/aletheore_flash_trial0_regrouped.json
"""
import argparse
import json
import sys
from pathlib import Path

# Real GLM-5.3-Flash rate, same numbers as github-app/app_server/llm_cost.py.
GLM_COST_PER_MILLION_USD = {"input": 0.0765, "output": 0.2549}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--aletheore-root", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", default="flash")
    parser.add_argument("--trial", type=int, default=0)
    args = parser.parse_args()

    if args.output.exists():
        raise SystemExit(f"{args.output} already exists - refusing to overwrite real spend's output")

    sys.path.insert(0, str(args.aletheore_root / "github-app"))
    from scan_worker.flash_review import _rank_findings_with_severity, related_finding_issue_text

    data = json.loads(args.results.read_text())
    source = data[args.config][args.trial]["findings"]

    usage = {"prompt": 0, "completion": 0, "calls": 0}

    def on_usage(prompt_tokens, completion_tokens, cached_tokens=0):
        usage["prompt"] += prompt_tokens
        usage["completion"] += completion_tokens
        usage["calls"] += 1

    out_findings = {}
    per_case = {}
    for case_id, findings in source.items():
        ranked = _rank_findings_with_severity(findings, on_usage=on_usage)
        # Ranking fails open by returning the input list itself; a successful pass
        # returns new dicts carrying "rank". Distinguish "ranked, found no repeats"
        # from "ranking failed, findings untouched" - they look identical otherwise.
        ranking_applied = len(findings) <= 1 or any("rank" in f for f in ranked)
        linked = sum(1 for f in ranked if "same_root_as" in f)
        out_findings[case_id] = [{**f, "issue": related_finding_issue_text(f)} for f in ranked]
        per_case[case_id] = {
            "findings": len(findings), "linked_repeats": linked, "ranking_applied": ranking_applied,
        }
        flag = "" if ranking_applied else "  <-- ranking FAILED, passed through unchanged"
        print(f"  {case_id}: {len(findings)} findings, {linked} linked as repeats{flag}", flush=True)

    cost = (usage["prompt"] * GLM_COST_PER_MILLION_USD["input"]
            + usage["completion"] * GLM_COST_PER_MILLION_USD["output"]) / 1_000_000
    # Same shape judge_full_pipeline.py reads: results[config][trial]["findings"][case].
    args.output.write_text(json.dumps({
        args.config: [{"findings": out_findings}],
        "_regroup_meta": {"per_case": per_case, "cost_usd": round(cost, 5), **usage},
    }, indent=2))
    total = sum(v["findings"] for v in per_case.values())
    linked = sum(v["linked_repeats"] for v in per_case.values())
    failed = [c for c, v in per_case.items() if not v["ranking_applied"]]
    print(f"\n{linked}/{total} findings linked as repeats across {len(per_case)} cases; "
          f"{usage['calls']} ranking calls, ${cost:.4f}; ranking failed for {len(failed)}: {failed}")


if __name__ == "__main__":
    main()
