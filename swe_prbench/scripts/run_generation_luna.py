"""Same real SWE-PRBench generation as run_generation_in_container.py, but
swaps the generation adapter for production's Luna path (writing_adapter_for,
_prefer_luna=True by default) instead of flash_review_generation_adapter's
GLM-5.3-Flash - same review_diff() call shape, same prompt, same diff
patches, only the generation model differs. Falls back to DeepSeek internally
(writing_adapter_for's own real fallback) if OPENAI_API_KEY isn't configured
in this container - the printed "model:" line makes which path actually ran
unambiguous, not inferred."""
import json
import re
import sys

sys.path.insert(0, "/app")

from scan_worker.flash_review import review_diff, FLASH_REVIEW_FALLBACK_MODEL  # noqa: E402
from scan_worker.model_tiers import writing_adapter_for, resolve_model  # noqa: E402


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


tasks = json.loads(open("/tmp/eval_100_slim.json").read())
model_used = resolve_model(FLASH_REVIEW_FALLBACK_MODEL)
print("model:", model_used, flush=True)

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

    adapter = writing_adapter_for(FLASH_REVIEW_FALLBACK_MODEL, on_usage=on_usage)
    try:
        findings = review_diff(
            production_diff_text,
            pr_title=pr.get("title", ""),
            model_used=model_used,
            adapter=adapter,
            diff_patches=patches,
            verify_with_second_model=False,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[{i}] {task_id}: ERROR {type(exc).__name__}: {exc}", flush=True)
        results[task_id] = {"findings": [], "usage": usage_log, "error": str(exc)}
        continue

    results[task_id] = {"findings": findings, "usage": usage_log}
    print(f"[{i}] {task_id}: {len(findings)} finding(s)", flush=True)

    if (i + 1) % 10 == 0:
        open("/tmp/swe_prbench_generation_results_luna.json", "w").write(json.dumps(results, indent=2))
        print(f"  -- checkpoint saved at {i+1}/100 --", flush=True)

open("/tmp/swe_prbench_generation_results_luna.json", "w").write(json.dumps(results, indent=2))
print("done", flush=True)
