import os
import json, os, sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _bench
sys.path.insert(0, os.environ.get("GITHUB_APP_PATH", os.path.join(_bench.ROOT, "..", "..", "github-app")))

from scan_worker.live_wiki import generate_subsystems, generate_overview
from aletheore.adapters.openai_compatible import OpenAICompatibleAdapter

REPO = Path(_bench.FLASK)
evidence = json.loads((REPO / ".aletheore" / "air.json").read_text())

# Mirrors production's real adapter choice - see
# github-app/scan_worker/model_tiers.py's writing_adapter_for(), which is
# the actual code this repo's live AIRview writes with. DeepSeek and OpenAI
# aren't interchangeable via one base_url/key swap: each needs its own
# adapter identity. Selected by _bench.WRITER_MODEL alone (AIRVIEW_MODEL env
# var) rather than a separate flag, so "which model wrote this" has one
# source of truth instead of two that could disagree.
_ADAPTERS = {
    "gpt-5.6-luna": dict(name="OpenAI", base_url="https://api.openai.com/v1",
                          api_key_env_var="OPENAI_API_KEY"),
}
_DEFAULT_ADAPTER = dict(name="deepseek", base_url="https://api.deepseek.com/v1",
                         api_key_env_var="DEEPSEEK_API_KEY")


def make_adapter():
    return OpenAICompatibleAdapter(
        **_ADAPTERS.get(_bench.WRITER_MODEL, _DEFAULT_ADAPTER),
        model=_bench.WRITER_MODEL,
        requires_consent=False,
    )


def fetch_line_count(path: str):
    p = REPO / path
    try:
        return sum(1 for _ in p.open(errors="ignore"))
    except Exception:
        return None


naming = make_adapter()
writing = make_adapter()

print("generating subsystems...", file=sys.stderr)
subs = generate_subsystems(
    evidence, naming, writing, model_used=_bench.WRITER_MODEL,
    fetch_line_count=fetch_line_count,
)
print(f"subsystems produced: {len(subs)}", file=sys.stderr)

print("generating overview...", file=sys.stderr)
ov = generate_overview(evidence, subs, writing, fetch_line_count=fetch_line_count)
print("overview:", "ok" if ov else "REJECTED", file=sys.stderr)

# Per-arm output name so a deepseek run and a luna run don't clobber each
# other - BENCH_AIRVIEW_FILE, same name build_airview_ctx3.py reads back.
out_name = os.environ.get("BENCH_AIRVIEW_FILE", "airview.json")
target = os.path.join(_bench.OUT, out_name)
json.dump({"subsystems": subs, "overview": ov}, open(target, "w"), indent=2, default=str)
print(f"wrote {target}", file=sys.stderr)
