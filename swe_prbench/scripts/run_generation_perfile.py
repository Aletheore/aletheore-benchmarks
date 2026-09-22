"""Re-run of SWE-PRBench generation with per_file_completeness=True - the
one real production behavior change (PR #762, merged 2026-09-21) the
original 2026-09-20 run didn't exercise. Everything else held identical to
the original run: same 100 tasks, same GLM-5.3-Flash adapter, no context
blocks (external, unscanned repos), verify_with_second_model=False (isolate
the one new variable rather than changing two things at once).

Run inside the deployed scan-worker container for INDIEROUTER_API_KEY
(sys.path already has /app, matching run_generation.py's own convention -
set ALETHEORE_ROOT only when running outside the container, e.g. a local
checkout of Aletheore/Aletheore). Expects eval_100_slim.json (the harness's
own dataset, not vendored here - see README's Reproducing section) next to
this script."""
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
_root = os.environ.get("ALETHEORE_ROOT")
if _root:
    sys.path.insert(0, str(Path(_root) / "github-app"))
    sys.path.insert(0, str(Path(_root) / "src"))
else:
    sys.path.insert(0, "/app")

from scan_worker.flash_review import review_diff, FLASH_REVIEW_FALLBACK_MODEL  # noqa: E402
from scan_worker.model_tiers import flash_review_generation_adapter, flash_review_model_used  # noqa: E402


def diff_patches_from_diff(diff_text: str) -> tuple[tuple[str, str], ...]:
    sections = re.split(r"(?=^diff --git )", diff_text, flags=re.MULTILINE)
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


tasks = json.loads((HERE / "eval_100_slim.json").read_text())
model_used = flash_review_model_used(FLASH_REVIEW_FALLBACK_MODEL)
print("model:", model_used, flush=True)

OUT = HERE / "generation_results_perfile.json"

results = {}
for i, pr in enumerate(tasks):
    task_id = pr["task_id"]
    diff_text = pr["diff_patch"]
    patches = diff_patches_from_diff(diff_text)
    if not patches:
        print(f"[{i}] {task_id}: WARNING no patches parsed, skipping", flush=True)
        results[task_id] = {"findings": [], "usage": [], "error": "no_patches_parsed"}
        continue
    production_diff_text = "\n\n".join(f"--- {f} ---\n{p}" for f, p in patches)

    usage_log = []

    def on_usage(pt, ct, cached=0, _log=usage_log):
        _log.append((pt, ct, cached))

    adapter = flash_review_generation_adapter(on_usage=on_usage, fallback_model=FLASH_REVIEW_FALLBACK_MODEL)
    try:
        findings = review_diff(
            production_diff_text,
            pr_title=pr.get("title", ""),
            model_used=model_used,
            adapter=adapter,
            diff_patches=patches,
            per_file_completeness=True,
            verify_with_second_model=False,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[{i}] {task_id}: ERROR {type(exc).__name__}: {exc}", flush=True)
        results[task_id] = {"findings": [], "usage": usage_log, "error": str(exc)}
        continue

    results[task_id] = {"findings": findings, "usage": usage_log}
    print(f"[{i}] {task_id}: {len(findings)} finding(s)", flush=True)

    if (i + 1) % 10 == 0:
        OUT.write_text(json.dumps(results, indent=2))
        print(f"  -- checkpoint saved at {i+1}/100 --", flush=True)

OUT.write_text(json.dumps(results, indent=2))
print("done", flush=True)
