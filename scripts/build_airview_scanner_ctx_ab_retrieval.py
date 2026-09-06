"""Same retrieval methodology as build_airview_ctx_v2.py (embed each
AIRview unit with nomic-embed-text, rank against the question, fill the
same 12,000-char budget RepoWise's own material was built at) - reads
airview_scanner_ctx_<MODE>.json instead of the hardcoded airview_v3.json,
and writes into arch_context2.json under key "airview_scanner_ctx_<MODE>"
instead of the shared "airview_v2" key, so this run never overwrites any
existing cached arm.
"""
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _bench, math
import httpx

BUDGET = 12000
OLLAMA = "http://localhost:11434/api/embed"
MODEL = "nomic-embed-text"

MODE = os.environ.get("MODE", "baseline")
assert MODE in ("baseline", "enriched")
ARM_KEY = f"airview_scanner_ctx_{MODE}"

av = json.load(open(os.path.join(_bench.OUT, f"{ARM_KEY}.json")))
ovd = av["overview"].get("description", "")

units = [f"# Repository overview\n{ovd}"]
for s in av["subsystems"]:
    units.append(f"# Subsystem: {s['name']}\n{s['description']}")
    for f in s.get("files") or []:
        blk = f"## {f.get('path')} (subsystem: {s['name']})\nRole: {f.get('role','')}\n"
        for k in f.get("key_symbols") or []:
            blk += f"- `{k.get('name')}` (line {k.get('line')}): {k.get('explanation','')}\n"
        if f.get("detail"):
            blk += "\n" + f["detail"]
        units.append(blk)
print(f"[{MODE}] AIRview units:", len(units), file=sys.stderr)


def embed(texts):
    out = []
    for i in range(0, len(texts), 32):
        r = httpx.post(OLLAMA, json={"model": MODEL, "input": texts[i:i + 32]}, timeout=600)
        r.raise_for_status()
        out.extend(r.json()["embeddings"])
    return out


def cos(a, b):
    d = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)); nb = math.sqrt(sum(x * x for x in b))
    return d / (na * nb + 1e-9)


uvecs = embed(units)
ctx_path = os.path.join(_bench.OUT, "arch_context2.json")
base = json.load(open(ctx_path))
qvecs = embed([c["q"] for c in base])

out = []
for c, qv in zip(base, qvecs):
    ranked = sorted(range(len(units)), key=lambda i: -cos(qv, uvecs[i]))
    buf = ""
    for i in ranked:
        if len(buf) >= BUDGET:
            break
        buf += units[i][: BUDGET - len(buf)] + "\n\n"
    c[ARM_KEY] = buf[:BUDGET]
    out.append(c)
    print(f"[{MODE}]", c["id"], len(c[ARM_KEY]), file=sys.stderr)

json.dump(out, open(ctx_path, "w"), indent=2)
print(f"[{MODE}] wrote key {ARM_KEY!r} into {ctx_path}", file=sys.stderr)
