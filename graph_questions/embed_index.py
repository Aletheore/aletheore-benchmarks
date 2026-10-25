"""Hosted, concurrent embedding index (open PR #1121 code). Usage: embed_index.py repo [repo ...]
Consent: the user approved hosted embedding of these public benchmark repos (one at a time, 8 workers)."""
import json, os, sys, time
S = os.path.dirname(os.path.abspath(__file__)) + "/"
os.environ["ALETHEORE_EMBED_WORKERS"] = "8"
sys.path.insert(0, S + "ehr_embed/src")
from pathlib import Path
from aletheore import search_index as si

print("code from", si.__file__)
for repo in sys.argv[1:]:
    root = Path(S + repo)
    ev = json.load(open(root / ".aletheore/air.json"))
    ticks = [0, 0]
    def prog(done, total):
        ticks[0], ticks[1] = done, total
    t0 = time.time()
    n = si.build_index(root, ev, allow_hosted=True, on_progress=prog, already_consented=True)
    dt = time.time() - t0
    print(f"{repo}: {n} chunks in {dt:.1f}s ({n / dt:.0f}/s) progress {ticks}", flush=True)
