"""RepoWise's half of the AIRview-vs-RepoWise architecture-comprehension
comparison: retrieves RepoWise wiki material for each architecture question
and writes the base `{id, q, repowise}` rows that build_airview_ctx3.py then
adds `airview_full` to, and judge_arch_arm.py finally scores.

This script was missing from the repo entirely - the only committed script
that builds RepoWise's side of an arch_context file is run_arch.py, and it
answers a different question (raw retrieved chunks/pages over the LOCATION
question set, writing arch_context.json - note the missing "2"). Nothing
committed produced arch_context2.json's `repowise` rows for the architecture
question set that the published AIRview numbers were actually judged on;
this is that script, following run_arch.py's RepoWise half exactly (same
budget, same pack() shape, same wiki.db lookup) but pointed at
questions/architecture.json.

Usage:  python3 scripts/build_repowise_arch_context.py
Env:    BENCH_FLASK_RW (corpus path), BENCH_OUT (results dir)

Must run under RepoWise's own Python (the interpreter its console-script
shebang points at), same as run_repowise_inprocess.py - it imports the
`repowise` package directly.
"""
import asyncio
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _bench

# Without these, _resolve_embedder(None) returns the 8-dim MockEmbedder and
# LanceDB raises on the dimension mismatch against the real 768-dim index -
# see REPRODUCIBILITY.md and run_repowise.py's own version of this comment.
os.environ.setdefault("REPOWISE_EMBEDDER", "ollama")
os.environ.setdefault("OLLAMA_BASE_URL", "http://localhost:11434")
os.environ.setdefault("REPOWISE_EMBEDDING_MODEL", "nomic-embed-text")
os.environ.setdefault("REPOWISE_EMBEDDING_DIMS", "768")
for line in open(_bench.ENV_FILE):
    line = line.strip()
    if "=" in line:
        k, v = line.split("=", 1)
        os.environ[k] = v

BUDGET = 12000
TOPK = 5

qs = _bench.load_questions("architecture")

from repowise.cli.commands.init_cmd import _resolve_embedder
from repowise.cli.providers.embedders import build_embedder
from repowise.core.persistence.vector_store import LanceDBVectorStore

REPO_R = _bench.FLASK_RW
db = sqlite3.connect(f"file:{REPO_R}/.repowise/wiki.db?mode=ro", uri=True)


def pack(pieces):
    """Fill the budget in rank order; never split a piece mid-way past the cap."""
    out, used = [], 0
    for p in pieces:
        if used >= BUDGET:
            break
        room = BUDGET - used
        chunk = p[:room]
        out.append(chunk)
        used += len(chunk)
    return "\n\n---\n\n".join(out)


def page_content(page_id, title):
    for tbl_q, arg in (
        ("select content from wiki_pages where id=?", page_id),
        ("select content from wiki_pages where title=?", title),
    ):
        try:
            r = db.execute(tbl_q, (arg,)).fetchone()
            if r and r[0]:
                return r[0]
        except Exception:
            pass
    return None


async def main():
    store = LanceDBVectorStore(f"{REPO_R}/.repowise/lancedb",
                               embedder=build_embedder(_resolve_embedder(None)))
    out = []
    for q in qs:
        res = await store.search(q["q"], limit=TOPK)
        pieces = []
        for r in res:
            body = page_content(r.page_id, r.title) or r.snippet or ""
            pieces.append(f"[{r.title} | {r.target_path}]\n{body}")
        rw = pack(pieces)
        out.append({"id": q["id"], "q": q["q"], "repowise": rw})
        print(q["id"], len(rw), res[0].search_type if res else "NONE", file=sys.stderr)
    await store.close()

    os.makedirs(_bench.OUT, exist_ok=True)
    target = os.path.join(_bench.OUT, "arch_context2.json")
    json.dump(out, open(target, "w"), indent=2)
    print(f"wrote {target}", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())
