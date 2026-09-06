"""Baseline vs. scanner-context-enriched AIRview file pages, same Flask
corpus, same subsystem generation - only generate_file_pages' new
include_repo_context flag (PR #545, merged to master) differs between the
two runs. Set MODE=baseline or MODE=enriched.
"""
import json, os, sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _bench
_bench.load_env()
sys.path.insert(0, os.environ.get("GITHUB_APP_PATH", os.path.join(_bench.ROOT, "..", "..", "github-app")))

from scan_worker.live_wiki import (
    attach_file_pages,
    generate_file_pages,
    generate_overview,
    generate_subsystems,
    select_file_page_paths,
)
from aletheore.adapters.openai_compatible import OpenAICompatibleAdapter

MODE = os.environ.get("MODE", "baseline")
assert MODE in ("baseline", "enriched")

REPO = Path(_bench.FLASK)
evidence = json.loads((REPO / ".aletheore" / "air.json").read_text())

USAGE = {"in": 0, "out": 0, "calls": 0}


def _u(prompt_tokens, completion_tokens, cached_tokens=0):
    USAGE["in"] += prompt_tokens
    USAGE["out"] += completion_tokens
    USAGE["calls"] += 1


def make_adapter():
    return OpenAICompatibleAdapter(
        name="deepseek",
        base_url="https://api.deepseek.com/v1",
        api_key_env_var="DEEPSEEK_API_KEY",
        model=_bench.WRITER_MODEL,
        requires_consent=False,
        on_usage=_u,
    )


def fetch_line_count(path: str):
    try:
        return sum(1 for _ in (REPO / path).open(errors="ignore"))
    except Exception:
        return None


naming, writing = make_adapter(), make_adapter()

print(f"[{MODE}] subsystems...", file=sys.stderr)
subs = generate_subsystems(evidence, naming, writing, model_used=_bench.WRITER_MODEL,
                           fetch_line_count=fetch_line_count)
print(f"[{MODE}]   {len(subs)} subsystems", file=sys.stderr)

subsystem_by_path = {f["path"]: s["name"] for s in subs for f in (s.get("files") or [])}
planned = select_file_page_paths(evidence)
print(f"[{MODE}] file pages ({len(planned)} planned)...", file=sys.stderr)
pages = generate_file_pages(evidence, writing, paths=planned,
                            subsystem_by_path=subsystem_by_path,
                            fetch_line_count=fetch_line_count,
                            include_repo_context=(MODE == "enriched"))
print(f"[{MODE}]   {len(pages)} pages verified & kept", file=sys.stderr)
attach_file_pages(subs, pages)

print(f"[{MODE}] overview...", file=sys.stderr)
ov = generate_overview(evidence, subs, writing, fetch_line_count=fetch_line_count)

out_name = f"airview_scanner_ctx_{MODE}.json"
json.dump({"subsystems": subs, "overview": ov, "file_pages": pages},
          open(os.path.join(_bench.OUT, out_name), "w"), indent=2, default=str)
print(f"[{MODE}] TOKENS in={USAGE['in']} out={USAGE['out']} calls={USAGE['calls']} -> {out_name}",
      file=sys.stderr)
