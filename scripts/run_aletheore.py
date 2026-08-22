"""Aletheore retrieval over the location question set.

Usage:  python3 scripts/run_aletheore.py
Env:    BENCH_FLASK (corpus path), BENCH_OUT (results dir)
"""
import json
import os
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _bench

from aletheore.search_index import search_index

_bench.check_corpus_commit()
REPO = Path(_bench.FLASK)
questions = _bench.load_questions("location")

# allow_hosted=False, always: search_index() prefers Aletheore's hosted
# embedding endpoint whenever a saved token/ALETHEORE_API_TOKEN is present -
# correct product behavior, wrong benchmark behavior. This "in-process"
# number is supposed to measure local compute only; without pinning this,
# the exact same script silently measures a real network round-trip instead
# whenever it happens to run on a machine that's logged in, with no signal
# that anything changed. Reproduced directly: an unpinned run on a machine
# with a stale saved credential returned ~205ms instead of ~53ms for the
# identical corpus and questions - indistinguishable from a real regression
# without this pin.
search_index(REPO, "warm up the index and embedder", k=10, allow_hosted=False)

out, latencies = [], []
for q in questions:
    started = time.perf_counter()
    hits = search_index(REPO, q["q"], k=10, allow_hosted=False)
    elapsed = time.perf_counter() - started
    latencies.append(elapsed)

    files, seen = [], set()
    for hit in hits:
        path = hit.get("module_path")
        if path and path not in seen:
            seen.add(path)
            files.append(path)

    out.append({"id": q["id"], "q": q["q"], "gt": q["gt"],
                "ranked_files": files, "latency_s": elapsed})
    print(f"{q['id']} {elapsed * 1000:7.1f}ms {files[:2]}", file=sys.stderr)

os.makedirs(_bench.OUT, exist_ok=True)
target = os.path.join(_bench.OUT, "results_aletheore.json")
json.dump(out, open(target, "w"), indent=2)

latencies.sort()
print(f"\nALETHEORE latency  n={len(latencies)}", file=sys.stderr)
print(f"  mean   {statistics.mean(latencies) * 1000:7.1f} ms", file=sys.stderr)
print(f"  median {statistics.median(latencies) * 1000:7.1f} ms", file=sys.stderr)
print(f"  p95    {latencies[int(len(latencies) * 0.95) - 1] * 1000:7.1f} ms", file=sys.stderr)
print(f"wrote {target}", file=sys.stderr)
