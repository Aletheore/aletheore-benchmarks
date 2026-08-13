"""Aletheore indexed search over a per-language question set."""
import json, statistics, sys, time
from pathlib import Path

# Optional: run queries through OpenAI embeddings instead of local Ollama, so an
# index built with text-embedding-3-small is queried with the same model. The
# index and the query MUST use one embedder - 1536-dim vectors searched with a
# 768-dim query vector fails outright.
import os
if os.environ.get("BENCH_EMBEDDER") == "openai":
    import aletheore.search_index as _si
    from openai import OpenAI as _OpenAI
    _key = None
    for _line in open(os.environ.get("BENCH_ENV_FILE", "/private/tmp/bench/.env")):
        if _line.startswith("OPENAI_API_KEY="):
            _key = _line.strip().split("=", 1)[1]
    assert _key, "BENCH_EMBEDDER=openai but no OPENAI_API_KEY found"
    _client = _OpenAI(base_url=_si.OPENAI_EMBEDDING_BASE_URL, api_key=_key)

    def _openai_embed(texts, *a, **kw):
        out = []
        for i in range(0, len(texts), 256):
            r = _client.embeddings.create(
                model=_si.OPENAI_EMBEDDING_MODEL, input=texts[i:i + 256]
            )
            out.extend(x.embedding for x in r.data)
        return out

    _si.embed_texts = _openai_embed

from aletheore.search_index import search_index

NAME, REPO, QFILE = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
qs = json.load(open(QFILE))
search_index(REPO, "warm up", k=10)

out, lat = [], []
for q in qs:
    t = time.perf_counter()
    hits = search_index(REPO, q["question"], k=10)
    dt = time.perf_counter() - t
    lat.append(dt)
    files, seen = [], set()
    for h in hits:
        p = h.get("module_path")
        if p and p not in seen:
            seen.add(p); files.append(p)
    out.append({"id": q["id"], "q": q["question"], "gt": q["ground_truth_files"],
                "ranked_files": files, "latency_s": dt})

json.dump(out, open(f"/private/tmp/bench/results_{NAME}.json", "w"), indent=2)

def at(k):
    return sum(1 for r in out if any(f in r["gt"] for f in r["ranked_files"][:k]))

# MRR, since Gemini's framework asked for it and it is worth having
rr = []
for r in out:
    rank = next((i + 1 for i, f in enumerate(r["ranked_files"]) if f in r["gt"]), None)
    rr.append(1.0 / rank if rank else 0.0)

n = len(out)
lat.sort()
print(f"\n{NAME.upper()}  (n={n})")
for k in (1, 3, 5):
    print(f"  top-{k}: {at(k)}/{n} = {100*at(k)/n:5.1f}%")
print(f"  MRR  : {statistics.mean(rr):.3f}")
print(f"  latency median {statistics.median(lat)*1000:.0f} ms")
miss = [r["id"] for r in out if not any(f in r["gt"] for f in r["ranked_files"][:5])]
print(f"  top-5 misses: {', '.join(miss) if miss else 'none'}")
