"""RepoWise search over any corpus and question set.

Usage:  run_repowise_lang.py <name> <repowise-checkout> <questions.json> [mode]

RepoWise searches its own generated wiki pages, so the checkout must have had
`repowise init` run against it first. It writes .repowise/ into the repository,
which is why every corpus gets a second checkout of the same commit rather than
sharing Aletheore's.

REPOWISE_EMBEDDER=ollama is mandatory. Without it _resolve_embedder(None)
returns an 8-dimension MockEmbedder, LanceDB raises on the dimension mismatch,
and search_cmd's bare `except Exception: pass` silently degrades semantic mode
into full-text - which invalidated our own first run before it was caught.
"""
import json
import os
import statistics
import subprocess
import sys
import time

NAME, REPO, QFILE = sys.argv[1], sys.argv[2], sys.argv[3]
MODE = sys.argv[4] if len(sys.argv) > 4 else "semantic"
OUT = os.environ.get("BENCH_OUT", "/private/tmp/bench")
ENV_FILE = os.environ.get("BENCH_ENV_FILE", "/private/tmp/bench/.env")

env = dict(os.environ)
env.update({
    "COLUMNS": "300", "TERM": "dumb",
    "REPOWISE_EMBEDDER": "ollama",
    "OLLAMA_BASE_URL": "http://localhost:11434",
    "REPOWISE_EMBEDDING_MODEL": "nomic-embed-text",
    "REPOWISE_EMBEDDING_DIMS": "768",
})
if os.path.exists(ENV_FILE):
    for line in open(ENV_FILE):
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k] = v


def parse(out):
    """Pull the Path column out of the rich table, in rank order."""
    files, seen = [], set()
    for ln in out.splitlines():
        if not ln.startswith("│"):
            continue
        cols = [c.strip() for c in ln.split("│")]
        if len(cols) < 6:
            continue
        path = cols[4]
        if not path or path == "Path":
            continue
        path = path.split("::")[0]          # symbol pages -> their file
        if path not in seen:
            seen.add(path)
            files.append(path)
    return files


qs = json.load(open(QFILE))
subprocess.run(["repowise", "search", "warm up", "--mode", MODE, "--limit", "5"],
               cwd=REPO, env=env, capture_output=True, text=True, timeout=600)

rows, lats = [], []
for q in qs:
    question = q.get("question") or q.get("q")
    gt = q.get("ground_truth_files") or q.get("gt")
    t0 = time.perf_counter()
    r = subprocess.run(
        ["repowise", "search", question, "--mode", MODE, "--limit", "10"],
        cwd=REPO, env=env, capture_output=True, text=True, timeout=600,
    )
    dt = time.perf_counter() - t0
    lats.append(dt)
    rows.append({"id": q["id"], "q": question, "gt": gt,
                 "ranked_files": parse(r.stdout), "latency_s": dt})

os.makedirs(OUT, exist_ok=True)
json.dump(rows, open(os.path.join(OUT, f"results_repowise_{NAME}_{MODE}.json"), "w"), indent=2)


def at(k):
    return sum(1 for r in rows if any(f in r["gt"] for f in r["ranked_files"][:k]))


rr = []
for r in rows:
    rank = next((i + 1 for i, f in enumerate(r["ranked_files"]) if f in r["gt"]), None)
    rr.append(1.0 / rank if rank else 0.0)

n = len(rows)
print(f"\nREPOWISE[{MODE}] {NAME}  (n={n})")
for k in (1, 3, 5):
    print(f"  top-{k}: {at(k)}/{n} = {100*at(k)/n:5.1f}%")
print(f"  MRR  : {statistics.mean(rr):.3f}")
print(f"  latency median {statistics.median(lats)*1000:.0f} ms")
