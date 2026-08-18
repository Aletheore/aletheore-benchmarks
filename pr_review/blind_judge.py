"""Blind LLM judge for the mixed-repo compaction A/B results (see README.md,
"Blind LLM judge" section). Scores exactly one arm's findings per call -
an earlier design that asked for 2-3 arms in a single call had the judge
silently omit one of the requested labels from its JSON response in 53 of
97 (case, run) instances, which is documented in the README rather than
republished here as a second script.

Labels are anonymized as "Tool A" even with only one candidate per call -
knowing it's Aletheore's own output could still bias scoring. Run twice per
(case, arm) to check agreement, per this project's documented judge-noise-
floor finding (this same judge model drifted 0.2-0.375 on identical input
in prior AIRview scoring work).

Usage:
    DEEPSEEK_API_KEY=... python3 pr_review/blind_judge.py \\
        --aletheore-root /path/to/Aletheore \\
        --results pr_review/results/mixed_repo_compaction_ab.json \\
        --output pr_review/results/blind_judge_results.json
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

import yaml
from openai import OpenAI

ARMS = ["ollama_baseline", "ollama_aletheore_context", "ollama_aletheore_compact"]
JUDGE_RUNS = 2


def call_judge(client: OpenAI, prompt: str) -> str:
    response = client.chat.completions.create(
        model="deepseek-v4-pro",
        messages=[{"role": "user", "content": prompt}],
        extra_body={"thinking": {"type": "disabled"}},
    )
    return response.choices[0].message.content


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--aletheore-root", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    sys.path.insert(0, str(args.aletheore_root / "benchmarks" / "pr-review-benchmark"))
    from scripts.llm_judge import build_judge_prompt, parse_judge_response

    client = OpenAI(base_url="https://api.deepseek.com", api_key=os.environ["DEEPSEEK_API_KEY"])

    data = json.loads(args.results.read_text())
    ground_truth = {}
    bench_cases = args.aletheore_root / "benchmarks" / "pr-review-benchmark" / "cases"
    for case_dir in sorted(bench_cases.iterdir()):
        gt_path = case_dir / "ground_truth.yaml"
        if gt_path.exists():
            gt = yaml.safe_load(gt_path.read_text())
            if gt.get("category") != "clean":
                ground_truth[case_dir.name] = gt

    by_case_arm_repeat0 = {}
    for r in data:
        if r.get("repeat") == 0 and r["case_id"] in ground_truth:
            by_case_arm_repeat0[(r["case_id"], r["arm"])] = r

    results = []
    total_calls = 0
    for run_idx in range(JUDGE_RUNS):
        for case_id, gt in ground_truth.items():
            gt_for_judge = {
                "expected_file": gt.get("expected_file"),
                "expected_line": gt.get("expected_line"),
                "description": gt.get("description"),
            }
            for arm in ARMS:
                rec = by_case_arm_repeat0.get((case_id, arm))
                if rec is None or rec.get("error"):
                    continue
                findings = rec.get("findings") or []
                prompt = build_judge_prompt(gt_for_judge, {"Tool A": findings})
                try:
                    raw = call_judge(client, prompt)
                    parsed = parse_judge_response(raw)
                    # The judge doesn't reliably echo back the exact "Tool A"
                    # key given to it (observed it substitute "aletheore" on
                    # an identical repeat prompt) - since only one candidate
                    # is ever submitted per call, take whatever single value
                    # came back rather than require an exact key match.
                    score = next(iter(parsed.values()), None) if len(parsed) == 1 else parsed.get("Tool A")
                    if score is None:
                        print(f"[run {run_idx}] {case_id} | {arm}: judge returned no usable score - retrying once")
                        raw = call_judge(client, prompt)
                        parsed = parse_judge_response(raw)
                        score = next(iter(parsed.values()), None) if len(parsed) == 1 else parsed.get("Tool A")
                except Exception as exc:  # noqa: BLE001 - one bad case must not kill the whole run
                    print(f"[run {run_idx}] {case_id} | {arm}: FAILED {type(exc).__name__}: {exc}")
                    score = None
                total_calls += 1
                results.append({"run": run_idx, "case_id": case_id, "arm": arm, "score": score})
                time.sleep(0.2)
        print(f"=== run {run_idx} complete, {total_calls} calls so far ===", flush=True)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2))
    missing = sum(1 for r in results if r["score"] is None)
    print(f"\ndone: {len(results)} (case,arm,run) triples, {missing} still missing after retry -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
