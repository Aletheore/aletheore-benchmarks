"""Build AIRview, capture equal-budget context from both wikis, for one repo."""
import asyncio, json, math, os, sqlite3, sys
from pathlib import Path
import httpx

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _bench

# live_wiki is imported from the product working tree, so this run measures
# whatever is checked out there right now - branch included. Point ALETHEORE_REPO
# at the checkout under test.
PRODUCT = os.environ.get(
    "ALETHEORE_REPO", os.path.expanduser("~/Documents/GitHub/Veridion")
)
sys.path.insert(0, os.path.join(PRODUCT, "github-app"))
from scan_worker.live_wiki import (
    attach_file_pages, generate_file_pages, generate_overview,
    generate_subsystems, select_file_page_paths,
)
from aletheore.adapters.openai_compatible import OpenAICompatibleAdapter

NAME = sys.argv[1]
SRC = Path(_bench.repo_src(NAME))
RW = _bench.repo_rw(NAME)
BUDGET = 12000
OUT = _bench.repo_out(NAME)
os.makedirs(OUT, exist_ok=True)
_bench.require_key("DEEPSEEK_API_KEY")

# Distinguishes the artifacts of two prompt variants measured on the same
# corpus (e.g. BENCH_ARM=_v4noRS). Empty by default, so single-arm runs keep
# writing plain airview.json / arch_context.json exactly as before.
ARM_SUFFIX = os.environ.get("BENCH_ARM", "")
AIRVIEW_PATH = Path(OUT) / f"airview{ARM_SUFFIX}.json"
CONTEXT_PATH = Path(OUT) / f"arch_context{ARM_SUFFIX}.json"

evidence = json.loads((SRC / ".aletheore" / "air.json").read_text())
USAGE = {"in": 0, "out": 0}


def adapter():
    return OpenAICompatibleAdapter(
        name="deepseek", base_url="https://api.deepseek.com/v1",
        api_key_env_var="DEEPSEEK_API_KEY", model=_bench.WRITER_MODEL,
        requires_consent=False,
        on_usage=lambda i, o: (USAGE.__setitem__("in", USAGE["in"] + i),
                               USAGE.__setitem__("out", USAGE["out"] + o)),
    )


def line_count(p):
    try:
        return sum(1 for _ in (SRC / p).open(errors="ignore"))
    except Exception:
        return None


# Generation is the expensive half - ~50 min and ~430K tokens on flask - while
# everything after it is seconds. Reuse a completed airview.json so a failure in
# the retrieval or judging steps does not repay for the wiki. AIRVIEW_REGENERATE=1
# forces a fresh build when the prompt under test has changed.
cached = AIRVIEW_PATH
if cached.exists() and os.environ.get("AIRVIEW_REGENERATE") != "1":
    saved = json.loads(cached.read_text())
    subs, ov, pages = saved["subsystems"], saved["overview"], saved["file_pages"]
    print(f"{NAME}: reusing cached AIRview ({len(subs)} subsystems, "
          f"{len(pages)} file pages) from {cached}", file=sys.stderr)
else:
    w = adapter()
    subs = generate_subsystems(evidence, adapter(), w, model_used=_bench.WRITER_MODEL,
                               fetch_line_count=line_count)
    by_path = {f["path"]: s["name"] for s in subs for f in (s.get("files") or [])}
    planned = select_file_page_paths(evidence)
    pages = generate_file_pages(evidence, w, paths=planned, subsystem_by_path=by_path,
                                fetch_line_count=line_count)
    attach_file_pages(subs, pages)
    ov = generate_overview(evidence, subs, w, fetch_line_count=line_count)
    print(f"{NAME}: {len(subs)} subsystems, {len(pages)}/{len(planned)} file pages, "
          f"tokens {USAGE['in']}/{USAGE['out']}", file=sys.stderr)
    json.dump({"subsystems": subs, "overview": ov, "file_pages": pages},
              open(AIRVIEW_PATH, "w"), indent=2, default=str)

# ---- AIRview retrieval units ----
ovd = ov.get("description", "") if isinstance(ov, dict) else str(ov)
units = [f"# Repository overview\n{ovd}"]
for s in subs:
    units.append(f"# Subsystem: {s['name']}\n{s['description']}")
    for f in s.get("files") or []:
        blk = f"## {f.get('path')} (subsystem: {s['name']})\nRole: {f.get('role','')}\n"
        for k in f.get("key_symbols") or []:
            blk += f"- `{k.get('name')}` (line {k.get('line')}): {k.get('explanation','')}\n"
        if f.get("detail"):
            blk += "\n" + f["detail"]
        units.append(blk)


def embed(texts):
    out = []
    for i in range(0, len(texts), 32):
        r = httpx.post("http://localhost:11434/api/embed",
                       json={"model": "nomic-embed-text", "input": texts[i:i + 32]}, timeout=600)
        r.raise_for_status()
        out.extend(r.json()["embeddings"])
    return out


def cos(a, b):
    d = sum(x * y for x, y in zip(a, b))
    return d / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)) + 1e-9)


# The corpus-agnostic architecture set, read from the repo rather than a copy
# staged in scratch - the staged copy died with /private/tmp and is the same file.
QUESTIONS = os.environ.get(
    "BENCH_ARCH_QUESTIONS",
    os.path.join(_bench.ROOT, "questions", "architecture_generic.json"),
)
qs = json.load(open(QUESTIONS))
uvecs, qvecs = embed(units), embed([q["q"] for q in qs])

# ---- RepoWise retrieval ----
from repowise.cli.commands.init_cmd import _resolve_embedder
from repowise.cli.providers.embedders import build_embedder
from repowise.core.persistence.vector_store import LanceDBVectorStore

db = sqlite3.connect(f"file:{RW}/.repowise/wiki.db?mode=ro", uri=True)


def page_body(pid, title, snippet):
    for q, a in (("select content from wiki_pages where id=?", pid),
                 ("select content from wiki_pages where title=?", title)):
        try:
            r = db.execute(q, (a,)).fetchone()
            if r and r[0]:
                return r[0]
        except Exception:
            pass
    return snippet or ""


def pack(pieces):
    buf = ""
    for p in pieces:
        if len(buf) >= BUDGET:
            break
        buf += p[: BUDGET - len(buf)] + "\n\n"
    return buf[:BUDGET]


async def main():
    store = LanceDBVectorStore(f"{RW}/.repowise/lancedb",
                               embedder=build_embedder(_resolve_embedder(None)))
    rows = []
    for q, qv in zip(qs, qvecs):
        ranked = sorted(range(len(units)), key=lambda i: -cos(qv, uvecs[i]))
        res = await store.search(q["q"], limit=5)
        rows.append({
            "id": q["id"], "q": q["q"],
            "airview": pack([units[i] for i in ranked]),
            "repowise": pack([f"[{r.title} | {r.target_path}]\n"
                              f"{page_body(r.page_id, r.title, r.snippet)}" for r in res]),
        })
    await store.close()
    json.dump(rows, open(CONTEXT_PATH, "w"), indent=2)
    print(f"wrote {CONTEXT_PATH}", file=sys.stderr)

asyncio.run(main())
