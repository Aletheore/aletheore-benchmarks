"""Stage 2: one trial of production's real Flash Review call per PR, using the inputs stage 1 built.

The call mirrors scan_worker/jobs.py for a paid installation: per_file_completeness, rank_findings,
share_pr_context_per_file, cross_file_check_runs=0, sibling_file_context="", no similarity cache, and no
adapter passed (review_diff builds the production GLM-5.3-Flash adapter itself). file_contents,
referenced_symbol_context and the deterministic checks that ride on them are all live.
Resumable per PR. A per-file generation failure inside review_diff is logged as a warning and recorded
with the PR's output; an exception that escapes review_diff stops the run, which can be resumed.
"""
import argparse
import json
import logging
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(sys.argv[sys.argv.index("--root") + 1])
BENCH = Path(sys.argv[sys.argv.index("--bench") + 1])
sys.path.insert(0, str(ROOT / "github-app"))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(BENCH / "pr_review/real_pr_recall_corpus/scripts"))

from run_benchmark import CASES, DIFFS_DIR, diff_patches_from_diff, make_usage_tracker  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--bench", type=Path, required=True)
    p.add_argument("--work", type=Path, required=True)
    p.add_argument("--tag", required=True)
    p.add_argument("--cases", default=None)
    p.add_argument("--env-file", type=Path, required=True)
    args = p.parse_args()

    for line in args.env_file.read_text().splitlines():
        m = re.match(r"\s*INDIEROUTER_API_KEY\s*=\s*(.+)", line)
        if m:
            os.environ["INDIEROUTER_API_KEY"] = m.group(1).strip().strip('"').strip("'")
    from scan_worker.flash_review import review_diff
    import scan_worker.flash_review as _fr
    _orig_validate = _fr._validate_findings
    captured: list = []

    def _capturing_validate(valid, *a, **kw):
        kept = _orig_validate(valid, *a, **kw)
        captured.append({"proposed": [dict(x) for x in valid], "kept": [dict(x) for x in kept]})
        return kept

    _fr._validate_findings = _capturing_validate

    trial_dir = args.work / f"trial_{args.tag}"
    trial_dir.mkdir(parents=True, exist_ok=True)
    warn_log: list[str] = []

    class Capture(logging.Handler):
        def emit(self, record):
            if record.levelno >= logging.WARNING:
                warn_log.append(f"{record.name}: {record.getMessage()[:220]}")

    logging.getLogger("scan_worker").addHandler(Capture())
    logging.getLogger("scan_worker").setLevel(logging.INFO)

    stats, on_usage = make_usage_tracker()
    cases = list(CASES) if not args.cases else args.cases.split(",")
    for case_id in cases:
        out = trial_dir / f"{case_id}.json"
        if out.exists():
            print(f"[{case_id}] done already", flush=True)
            continue
        inp = json.loads((args.work / "inputs" / f"{case_id}.json").read_text())
        raw = (DIFFS_DIR / f"{case_id}.diff").read_text()
        patches = diff_patches_from_diff(raw)
        diff_text = "\n\n".join(f"--- {f} ---\n{pt}" for f, pt in patches)
        captured.clear()
        before_warn = len(warn_log)
        before = dict(stats)
        grounding: list[dict] = []
        t0 = time.time()
        findings = review_diff(
            diff_text,
            on_usage=on_usage,
            pr_title=inp["title"],
            referenced_symbol_context=inp["referenced_symbol_context"],
            sibling_file_context="",
            cache_lookup=None,
            cache_write=None,
            file_contents=inp["file_contents"],
            on_grounding_result=grounding.append,
            diff_patches=patches,
            per_file_completeness=True,
            rank_findings=True,
            cross_file_check_runs=0,
            share_pr_context_per_file=True,
        )
        out.write_text(json.dumps({
            "findings": findings,
            "grounding": grounding,
            "gate": captured[-1] if captured else None,
            "calls": stats["calls"] - before["calls"],
            "prompt_tokens": stats["prompt_tokens"] - before["prompt_tokens"],
            "completion_tokens": stats["completion_tokens"] - before["completion_tokens"],
            "warnings": warn_log[before_warn:],
            "seconds": round(time.time() - t0, 1),
        }))
        srcs = {}
        for f in findings:
            srcs[f.get("source")] = srcs.get(f.get("source"), 0) + 1
        print(f"[{case_id}] {len(findings)} findings {srcs}, {stats['calls'] - before['calls']} calls, "
              f"{time.time() - t0:.0f}s, warnings {len(warn_log) - before_warn}", flush=True)
    print("GENERATE_DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
