"""Measures production's real verification pass (flash_review._verify_findings_with_second_model)
under a chosen verifier model and a chosen context, against the stable judge's labels.

Question this answers: can gpt-6-luna replace deepseek-v4-flash as the verification model
(cheaper per token), and does giving the verifier the WHOLE PR diff instead of only the
finding's own file patch (production's current cost optimisation) catch more false positives?

Input is the raw, PRE-verification generation output (the "flash" config in
aletheore_3x_results.json - no verification was applied to it), so what gets rejected here is
exactly what verification would reject in production. Every finding already has a label from two
identical gpt-6-luna judge runs (judged_gpt6luna_run{1,2}.json), so the result is a classifier
measurement: of the findings rejected, how many were confirmed false positives (good) versus
true positives or golden-bug catches (bad, costs recall).

Limitation, same for every condition: production also gives the verifier a windowed slice of the
finding's real file (file_contents); this corpus stores only diffs, so that slice is absent here.

Usage (needs the github-app worktree's deps, OPENAI_API_KEY, DEEPSEEK_API_KEY):
    python3 verifier_swap_eval.py --aletheore-root <worktree> --model gpt-6-luna \\
        --context per-file --output /tmp/verify_luna_perfile.json
"""
import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent
CORPUS_DIR = HERE.parent
RESULTS = CORPUS_DIR / "results"
DIFFS_DIR = CORPUS_DIR / "diffs"

RATES = {"deepseek-v4-flash": (0.44, 1.32), "gpt-6-luna": (0.10, 0.50), "gpt-5.6-luna": (0.20, 1.20)}


class CountingAdapter:
    """Delegates to the real adapter, counting responses that would not parse as JSON (which the
    production function silently turns into a fail-open UNCERTAIN, indistinguishable from a real one)."""

    def __init__(self, inner):
        self.inner, self.calls, self.unparseable = inner, 0, 0

    def is_available(self):
        return True

    def simple_completion(self, system, user, cwd="."):
        self.calls += 1
        raw = self.inner.simple_completion(system, user, cwd=cwd)
        try:
            json.loads(raw)
        except Exception:
            self.unparseable += 1
        return raw


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--aletheore-root", type=Path, required=True)
    ap.add_argument("--model", required=True, choices=sorted(RATES))
    ap.add_argument("--context", required=True, choices=["per-file", "full-pr"])
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    sys.path.insert(0, str(args.aletheore_root / "github-app"))
    sys.path.insert(0, str(HERE))
    from aletheore.adapters.openai_compatible import OpenAICompatibleAdapter
    import scan_worker.model_tiers as model_tiers
    from scan_worker.flash_review import _verify_findings_with_second_model
    from judge_full_pipeline import diff_patches_from_diff, load_case_diffs
    from crossfile_check_eval import baseline_label

    usage = {"in": 0, "out": 0}

    def on_usage(p, c, cached=0):
        usage["in"] += p
        usage["out"] += c

    if args.model == "deepseek-v4-flash":
        inner = OpenAICompatibleAdapter(
            name="DeepSeek", base_url="https://api.deepseek.com", api_key_env_var="DEEPSEEK_API_KEY",
            model="deepseek-v4-flash", supports_tool_choice=False, on_usage=on_usage,  # exactly production's
        )
    else:
        inner = OpenAICompatibleAdapter(
            name="OpenAI", base_url="https://api.openai.com/v1", api_key_env_var="OPENAI_API_KEY",
            model=args.model, extra_body={"reasoning_effort": "low"}, on_usage=on_usage,
        )
    adapter = CountingAdapter(inner)
    model_tiers.verification_adapter = lambda on_usage=None: adapter  # the function imports this at call time

    stored = json.loads((RESULTS / "aletheore_3x_results.json").read_text())["flash"][0]["findings"]
    runs = [json.loads((RESULTS / f"judged_gpt6luna_run{i}.json").read_text()) for i in (1, 2)]
    case_diffs = load_case_diffs()

    rejected, labels = {}, {}
    for case, findings in stored.items():
        if not findings:
            continue
        findings = [dict(f) for f in findings]
        patches = None
        if args.context == "per-file":
            patches = diff_patches_from_diff((DIFFS_DIR / f"{case}.diff").read_text())
        survivors = _verify_findings_with_second_model(
            findings, case_diffs[case], on_usage=on_usage, file_contents=None, diff_patches=patches,
        )
        kept_ids = {id(f) for f in survivors}
        rejected[case] = [i for i, f in enumerate(findings) if id(f) not in kept_ids]
        for i in range(len(findings)):
            labels[(case, i)] = baseline_label(runs, "aletheore-flash", case, i)
        print(f"  [{case}] {len(findings)} findings, {len(rejected[case])} rejected", flush=True)

    rin, rout = RATES[args.model]
    cost = (usage["in"] * rin + usage["out"] * rout) / 1e6
    args.output.write_text(json.dumps({
        "model": args.model, "context": args.context, "cost_usd": round(cost, 4), "calls": adapter.calls,
        "unparseable": adapter.unparseable, "tokens_in": usage["in"], "tokens_out": usage["out"],
        "rejected": rejected,
        "labels": {f"{c}|{i}": l for (c, i), l in labels.items()},
    }, indent=2))

    tot, rej = Counter(labels.values()), Counter(labels[(c, i)] for c, idxs in rejected.items() for i in idxs)
    print(f"\n=== {args.model} / {args.context}: cost ${cost:.4f}, {adapter.calls} calls, "
          f"{adapter.unparseable} unparseable (fail-open), rejected {sum(rej.values())} of {sum(tot.values())} ===")
    print(f"{'baseline label':16} {'total':>5} {'rejected':>9}")
    for lab in ["FP(both)", "FP(one)", "GOLDEN", "TP", "other/disputed", "not-a-finding"]:
        if tot[lab]:
            print(f"{lab:16} {tot[lab]:>5} {rej[lab]:>9}")


if __name__ == "__main__":
    main()
