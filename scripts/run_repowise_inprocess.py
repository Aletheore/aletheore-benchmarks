"""RepoWise semantic retrieval, in-process - the missing counterpart to
run_aletheore.py's in-process number.

run_repowise.py always subprocesses `repowise search` per query, which pays
the cost of importing the `lancedb` package (measured at ~2.5-3.5s, via
cProfile) on every single call - not retrieval, Python import machinery. That
number is real (it's what a user actually experiences invoking the CLI once
per query) but it is not the "in-process (library)" figure this script
produces to sit beside run_aletheore.py's, which calls search_index()
directly in one long-lived process the same way. A long-lived caller (an MCP
server, `repowise search` run in a loop inside one interpreter) only pays the
import cost once; this script measures that steady state.

Usage:  python3 scripts/run_repowise_inprocess.py
Env:    BENCH_FLASK_RW (corpus path), BENCH_OUT (results dir), BENCH_ENV_FILE
"""
import asyncio
import json
import os
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _bench

os.environ.setdefault("REPOWISE_EMBEDDER", "ollama")
os.environ.setdefault("OLLAMA_BASE_URL", "http://localhost:11434")
os.environ.setdefault("REPOWISE_EMBEDDING_MODEL", "nomic-embed-text")
os.environ.setdefault("REPOWISE_EMBEDDING_DIMS", "768")
for line in open(_bench.ENV_FILE):
    line = line.strip()
    if "=" in line:
        k, v = line.split("=", 1)
        os.environ[k] = v

from repowise.cli.commands.init_cmd import _resolve_embedder
from repowise.cli.providers.embedders import build_embedder
from repowise.core.persistence.vector_store import LanceDBVectorStore

REPO = Path(_bench.FLASK_RW)
LANCE_DIR = REPO / ".repowise" / "lancedb"
questions = _bench.load_questions("location")


async def _open_store():
    embedder = build_embedder(_resolve_embedder(None))
    return LanceDBVectorStore(str(LANCE_DIR), embedder=embedder)


def _ranked_files(results):
    """Distinct file paths in rank order, from SearchResult.target_path
    (core/persistence/search.py). A symbol-level page's target_path is
    "path/to/file.py::SymbolName" - split to its containing file, same as
    run_repowise.py's own parse() does for the CLI table output."""
    files, seen = [], set()
    for r in results:
        path = r.target_path.split("::")[0] if r.target_path else None
        if path and path not in seen:
            seen.add(path)
            files.append(path)
    return files


async def main():
    store = await _open_store()
    # Warm-up so the first query does not absorb one-time connection cost -
    # matches run_aletheore.py's own warm-up call, same purpose.
    await store.search("warm up the index and embedder", limit=10)

    out, latencies = [], []
    for q in questions:
        started = time.perf_counter()
        results = await store.search(q["q"], limit=10)
        elapsed = time.perf_counter() - started
        latencies.append(elapsed)

        files = _ranked_files(results)
        out.append({"id": q["id"], "q": q["q"], "gt": q["gt"],
                    "ranked_files": files, "latency_s": elapsed})
        print(f"{q['id']} {elapsed * 1000:7.1f}ms {files[:2]}", file=sys.stderr)

    await store.close()

    os.makedirs(_bench.OUT, exist_ok=True)
    target = os.path.join(_bench.OUT, "results_repowise_inprocess.json")
    json.dump(out, open(target, "w"), indent=2)

    latencies.sort()
    print(f"\nREPOWISE[in-process] latency n={len(latencies)}", file=sys.stderr)
    print(f"  mean   {statistics.mean(latencies) * 1000:7.1f} ms", file=sys.stderr)
    print(f"  median {statistics.median(latencies) * 1000:7.1f} ms", file=sys.stderr)
    print(f"  p95    {latencies[int(len(latencies) * 0.95) - 1] * 1000:7.1f} ms", file=sys.stderr)
    print(f"wrote {target}", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())
