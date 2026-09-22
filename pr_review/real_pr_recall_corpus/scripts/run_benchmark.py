"""Runs Aletheore's real review_diff() (flash_review.py, unmodified - the
same function scan_worker/jobs.py calls in production) against the 13-case
real-PR corpus in this directory, for both real tier configs jobs.py wires:

  flash: per_file_completeness=True, verify_with_second_model=False
  air:   per_file_completeness=True, verify_with_second_model=True

Requires INDIEROUTER_API_KEY (generation, glm-5.3-flash) and, for the air
config, DEEPSEEK_API_KEY (verification). Real cost, 3 trials each config:
generation ~$0.22, verification ~$1.73 (2026-09-21 pricing) - see
../results/aletheore_3x_results.json for the run this produced.
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
CORPUS_DIR = HERE.parent
DIFFS_DIR = CORPUS_DIR / "diffs"
RESULTS_DIR = CORPUS_DIR / "results"

CASES = {
    "keycloak-37429": "Add a HTML sanitizer for translated message resources",
    "sentry-95633": "feat(uptime): Add ability to use queues to manage parallelism",
    "calcom-22532": "feat: add calendar cache status and actions",
    "grafana-80329": "Annotations: Split cleanup into separate queries and deletes to avoid deadlocks on MySQL",
    "sentry-80168": "feat(workflow_engine): Add in hook for producing occurrences from the stateful detector",
    "sentry-80528": "ref(crons): Reorganize incident creation / issue occurrence logic",
    "grafana-76186": "Plugins: Chore: Renamed instrumentation middleware to metrics middleware",
    "grafana-103633": "AuthZService: improve authz caching",
    "grafana-79265": "Anonymous: Add configurable device limit",
    "calcom-22345": "feat: convert InsightsBookingService to use Prisma.sql raw queries",
    "calcom-10967": "fix: handle collective multiple host on destinationCalendar",
    "calcom-10600": "feat: 2fa backup codes",
    "calcom-8087": "Async import of the appStore packages",
}


def diff_patches_from_diff(text: str) -> tuple[tuple[str, str], ...]:
    sections = re.split(r"(?=^diff --git )", text, flags=re.MULTILINE)
    patches = []
    for section in sections:
        m = re.match(r"^diff --git a/(.+?) b/(.+)$", section, re.MULTILINE)
        if not m:
            continue
        lines = section.splitlines()
        body_start = next((i for i, line in enumerate(lines) if line.startswith("@@")), None)
        body = "\n".join(lines[body_start:]) if body_start is not None else ""
        patches.append((m.group(2), body))
    return tuple(patches)


def make_usage_tracker():
    stats = {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0}

    def on_usage(prompt_tokens, completion_tokens, cached_tokens=0):
        stats["calls"] += 1
        stats["prompt_tokens"] += prompt_tokens
        stats["completion_tokens"] += completion_tokens

    return stats, on_usage


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--aletheore-root", type=Path, required=True,
        help="path to a local Aletheore/Aletheore checkout at (or after) commit 0b54eb7",
    )
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--config", choices=["flash", "air", "both"], default="both")
    parser.add_argument("--output", type=Path, default=RESULTS_DIR / "aletheore_3x_results.json")
    args = parser.parse_args()

    sys.path.insert(0, str(args.aletheore_root / "github-app"))
    from app_server.llm_cost import cost_for_usage
    from scan_worker.flash_review import review_diff
    from scan_worker.model_tiers import VERIFICATION_MODEL, flash_review_generation_adapter

    case_data = {}
    for case_id, title in CASES.items():
        diff_text_raw = (DIFFS_DIR / f"{case_id}.diff").read_text()
        diff_patches = diff_patches_from_diff(diff_text_raw)
        diff_text = "\n\n".join(f"--- {f} ---\n{p}" for f, p in diff_patches)
        case_data[case_id] = (title, diff_text, diff_patches)

    configs = ["flash", "air"] if args.config == "both" else [args.config]
    results = {"flash": [], "air": []}
    if args.output.exists():
        results.update(json.load(open(args.output)))

    for config_name in configs:
        verify = config_name == "air"
        for trial in range(args.trials):
            print(f"=== config={config_name} trial={trial + 1}/{args.trials} ===", flush=True)
            trial_result = {}
            gen_stats, on_gen_usage = make_usage_tracker()
            verify_stats, on_verify_usage = make_usage_tracker()
            for case_id, (title, diff_text, diff_patches) in case_data.items():
                adapter = flash_review_generation_adapter(on_usage=on_gen_usage)
                findings = review_diff(
                    diff_text,
                    pr_title=title,
                    diff_patches=diff_patches,
                    adapter=adapter,
                    per_file_completeness=True,
                    verify_with_second_model=verify,
                    on_verification_usage=on_verify_usage if verify else None,
                    verify_suggestions=False,
                )
                trial_result[case_id] = findings
                print(f"  {case_id}: {len(findings)} findings", flush=True)
            gen_cost = cost_for_usage("glm-5.3-flash", gen_stats["prompt_tokens"], gen_stats["completion_tokens"])
            verify_cost = cost_for_usage(VERIFICATION_MODEL, verify_stats["prompt_tokens"], verify_stats["completion_tokens"])
            results[config_name].append({
                "findings": trial_result,
                "gen_cost": {**gen_stats, "cost_usd": round(gen_cost, 4)},
                "verify_cost": {**verify_stats, "cost_usd": round(verify_cost, 4)},
            })
            args.output.parent.mkdir(parents=True, exist_ok=True)
            json.dump(results, open(args.output, "w"), indent=2)
            print(f"  gen: {gen_stats['calls']} calls ${gen_cost:.4f} | "
                  f"verify: {verify_stats['calls']} calls ${verify_cost:.4f}", flush=True)

    print("\nALL DONE", flush=True)


if __name__ == "__main__":
    main()
