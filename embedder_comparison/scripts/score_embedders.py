"""Recompute every table in README.md from the committed per-question rankings. No API key, no network.
Paired bootstrap over questions (4,000 draws, seed 1) for every difference.
Run: python3 score_embedders.py"""
import glob
import json
import random
import statistics
from pathlib import Path

R = Path(__file__).resolve().parent.parent / "results"
BASE = "jina-local"
# DeepInfra list price per 1M input tokens when tested (2026-10-11), and native vector size
PRICE = {"qwen3-8b": 0.010, "qwen3-8b-instr": 0.010, "qwen3-4b": 0.020, "qwen3-0.6b": 0.010, "bge-m3": 0.010,
         "gemma-300m": 0.002, "nemotron-1b": 0.015, "nemotron-8b": 0.035, "bge-base": 0.005, "jina-local": None}
DIM = {"qwen3-8b": 4096, "qwen3-8b-instr": 4096, "qwen3-4b": 2560, "qwen3-0.6b": 1024, "bge-m3": 1024,
       "gemma-300m": 768, "nemotron-1b": 2048, "nemotron-8b": 4096, "bge-base": 768, "jina-local": 768}


def load(setname, provider):
    """{(corpus, question set, question id): rank of the first ground-truth file, or None}"""
    out = {}
    for p in glob.glob(str(R / setname / provider / "*.json")):
        d = json.load(open(p))
        for qset, s in d["sets"].items():
            for r in s["rows"]:
                out[(d["corpus"], qset, r["id"])] = next((i + 1 for i, f in enumerate(r["ranked"]) if f in r["gt"]), None)
    return out


def tokens(setname, provider):
    return sum(json.load(open(p))["build"]["tokens"] for p in glob.glob(str(R / setname / provider / "*.json")))


def restrict(ranks, keys):
    return {k: ranks[k] for k in keys}


def metrics(ranks):
    v = list(ranks.values())
    n = len(v)
    return {"n": n, "top1": sum(r == 1 for r in v) / n, "top3": sum(bool(r) and r <= 3 for r in v) / n,
            "top5": sum(bool(r) and r <= 5 for r in v) / n, "mrr": statistics.mean((1 / r if r else 0.0) for r in v)}


def val(r, key):
    return (1 / r if r else 0.0) if key == "mrr" else (1.0 if r == 1 else 0.0)


def diff(a, b, key="mrr", B=4000):
    keys = sorted(set(a) & set(b))
    d = [val(a[k], key) - val(b[k], key) for k in keys]
    rng = random.Random(1)  # nosec B311 - bootstrap resampling, not security
    xs = sorted(sum(rng.choice(d) for _ in d) / len(d) for _ in range(B))  # nosec B311
    return sum(d) / len(d), xs[int(0.025 * B)], xs[int(0.975 * B)], len(keys)


def fmt_diff(a, b, key="mrr"):
    m, lo, hi, _ = diff(a, b, key)
    return f"{m:+.3f} [{lo:+.3f}, {hi:+.3f}]"


def table(title, rows, base_name):
    print(f"\n### {title}\n")
    print(f"| Model | Top-1 | Top-3 | Top-5 | MRR | MRR vs {base_name} (95% CI) |")
    print("|---|---|---|---|---|---|")
    for name, ranks, base in rows:
        m = metrics(ranks)
        d = "baseline" if base is None else fmt_diff(ranks, base)
        print(f"| {name} | {100*m['top1']:.1f}% | {100*m['top3']:.1f}% | {100*m['top5']:.1f}% | {m['mrr']:.3f} | {d} |")


def providers(setname):
    return sorted(p.name for p in (R / setname).iterdir() if p.is_dir())


# ---- A. the nine-corpus matrix
main = {p: load("main", p) for p in providers("main")}
common = set.intersection(*[set(v) for v in main.values()])
main = {p: restrict(v, common) for p, v in main.items()}
base = main[BASE]
order = sorted(main, key=lambda p: -metrics(main[p])["mrr"])
print(f"questions answered by every model on the 9-corpus matrix: {len(common)}")
table("A. Nine-corpus matrix (hosted models against the production local model)",
      [(p, main[p], None if p == BASE else base) for p in order], "jina local")
print("\n| Model | Vector size | List price per 1M tokens | Tokens to index the 9 corpora |\n|---|---|---|---|")
for p in order:
    price = "n/a (local)" if PRICE[p] is None else f"${PRICE[p]:.3f}"
    t = tokens("main", p)
    print(f"| {p} | {DIM[p]} | {price} | {t:,} |" if t else f"| {p} | {DIM[p]} | {price} | n/a |")
corpora = ["flask", "gin", "axios", "fmt", "jq", "automapper", "gson", "guzzle", "jekyll"]
print("\nPer-corpus top-1:\n\n| Model | " + " | ".join(corpora) + " |\n|---|" + "---|" * len(corpora))
for p in order:
    cells = []
    for c in corpora:
        ks = [k for k in common if k[0] == c]
        cells.append(f"{sum(main[p][k] == 1 for k in ks)}/{len(ks)}")
    print(f"| {p} | " + " | ".join(cells) + " |")

# ---- B. held-out corpora (never used to choose a model)
held = {p: load("heldout", p) for p in providers("heldout")}
hc = set.intersection(*[set(v) for v in held.values()])
held = {p: restrict(v, hc) for p, v in held.items()}
print(f"\nquestions answered by every model on the held-out corpora (serde, slim, zod, thrift): {len(hc)}")
table("B. Held-out corpora", [(p, held[p], None if p == BASE else held[BASE]) for p in sorted(held, key=lambda p: -metrics(held[p])["mrr"])], "jina local")

# ---- C. pooled
pool_models = ["jina-local", "qwen3-8b", "qwen3-8b-instr", "qwen3-0.6b"]
pooled = {p: {**main[p], **held[p]} for p in pool_models}
print(f"\npooled questions (matrix + held-out): {len(pooled[BASE])}")
table("C. Pooled", [(p, pooled[p], None if p == BASE else pooled[BASE]) for p in sorted(pooled, key=lambda p: -metrics(pooled[p])["mrr"])], "jina local")
print("\nPaired differences on the pooled set (MRR / top-1):")
for a, b in [("qwen3-8b", "qwen3-0.6b"), ("qwen3-8b-instr", "qwen3-8b")]:
    print(f"- {a} minus {b}: MRR {fmt_diff(pooled[a], pooled[b])}; top-1 {fmt_diff(pooled[a], pooled[b], 'top1')}")

# ---- D. the shipped configuration: Qwen3-Embedding-8B asked for 1024 dimensions
d1024 = {**load("dim1024", "qwen3-8b"), **load("dim1024_heldout", "qwen3-8b")}
keys = set(d1024)
ship = {"jina-local": restrict({**main[BASE], **held[BASE]}, keys), "qwen3-8b @ 4096 (native)": restrict(pooled["qwen3-8b"], keys),
        "qwen3-8b @ 1024 (shipped)": d1024, "qwen3-0.6b": restrict(pooled["qwen3-0.6b"], keys)}
print(f"\nshipped-configuration comparison, questions answered by all four: {len(keys)}")
table("D. Shipped configuration", [(p, v, None if p == BASE else ship[BASE]) for p, v in sorted(ship.items(), key=lambda kv: -metrics(kv[1])["mrr"])], "jina local")
print(f"\n- 1024 minus 4096 dimensions: MRR {fmt_diff(ship['qwen3-8b @ 1024 (shipped)'], ship['qwen3-8b @ 4096 (native)'])}")
print(f"- 8B @ 1024 minus 0.6B: MRR {fmt_diff(ship['qwen3-8b @ 1024 (shipped)'], ship['qwen3-0.6b'])}")

# ---- E. query wording robustness (six corpora, qwen3-8b)
kw8, kwi = load("keywords", "qwen3-8b"), load("keywords", "qwen3-8b-instr")
w2, w3 = load("wording2", "qwen3-8b-instr"), load("wording3", "qwen3-8b-instr")
six = set(kw8) & set(kwi) & set(w2) & set(w3)
full = {"no instruction": restrict(main["qwen3-8b"], six), "instruction, wording 1 (used in A)": restrict(main["qwen3-8b-instr"], six),
        "instruction, wording 2": restrict(w2, six), "instruction, wording 3": restrict(w3, six)}
print(f"\nrobustness questions (flask, axios, fmt, jq, gson, guzzle): {len(six)}")
table("E1. Full-sentence queries: does a query instruction help, and is it wording-specific?",
      [(p, v, None if p.startswith("no instr") else full["no instruction"]) for p, v in full.items()], "no instruction")
kw = {"no instruction": restrict(kw8, six), "instruction": restrict(kwi, six)}
table("E2. Keyword-style queries (stop words stripped)", [(p, v, None if p == "no instruction" else kw["no instruction"]) for p, v in kw.items()], "no instruction")
