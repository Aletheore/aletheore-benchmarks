"""Tokens, turns, cost per arm and per kind, over every finished run; plus cost and tokens per CORRECT answer."""
import collections, glob, json, re, statistics, os
S = os.path.dirname(os.path.abspath(__file__)) + "/"
SETS = [("gq_tasks_all.json", "out_py1"), ("ml_tasks_all.json", "out_ml1"), ("ml_tasks_b.json", "out_ml2"), ("ml_tasks_c.json", "out_ml3")]


def parse_list(text):
    m = re.search(r"\[.*\]", text or "", re.S)
    try:
        return [p.strip().removeprefix("./") for p in json.loads(m.group(0)) if isinstance(p, str)] if m else None
    except ValueError:
        return None


def score(t, text):
    k = t["kind"]
    if k in ("direct", "unreachable"):
        pred = parse_list(text)
        return 1.0 if pred is not None and set(pred) == set(t["truth"]) else 0.0
    if k in ("size", "deps"):
        m = re.search(r"\d[\d,]*", (text or "").replace('"count"', ""))
        return 1.0 if m and abs(int(m.group(0).replace(",", "")) - t["truth_n"]) / t["truth_n"] <= 0.10 else 0.0
    names = re.findall(r'"author"\s*:\s*"([^"]+)"', text or "")
    if not names:
        return 0.0
    want, got = t["truth_author"].lower().split(), names[0].lower()
    return 1.0 if want[-1] in got and want[0] in got else 0.0


TASKS = {}
for tf, _ in SETS:
    TASKS.update({t["id"]: t for t in json.load(open(S + tf))})
agg = collections.defaultdict(lambda: collections.defaultdict(list))
for tf, out in SETS:
    for f in glob.glob(S + out + "/*.json"):
        r = json.load(open(f))
        t = TASKS.get(r["id"])
        if not t:
            continue
        ok = score(t, r.get("result"))
        for key in ("ALL", t["kind"]):
            d = agg[(r["arm"], key)]
            d["in"].append(r.get("in_tokens") or 0)
            d["out"].append(r.get("out_tokens") or 0)
            d["turns"].append(r.get("turns") or 0)
            d["cost"].append(r.get("cost_usd") or 0)
            d["ok"].append(ok)
arms = sorted({a for a, _ in agg})
print("mean per run: total input tokens (incl. cache), output tokens, USD, turns")
print(f"{'':12s}" + "".join(f"{a:>36s}" for a in arms))
for key in ["ALL", "direct", "size", "deps", "unreachable", "owner"]:
    row = f"{key:12s}"
    for a in arms:
        d = agg[(a, key)]
        row += f"   {statistics.mean(d['in']):>8,.0f} {statistics.mean(d['out']):>6,.0f} ${statistics.mean(d['cost']):.4f} {statistics.mean(d['turns']):>4.1f}"
    print(row)
print("\nper CORRECT answer (all questions):")
for a in arms:
    d = agg[(a, "ALL")]
    n_ok = sum(d["ok"])
    print(f"  {a}: runs {len(d['ok'])}, correct {int(n_ok)} ({n_ok / len(d['ok']):.2f}); $/run {statistics.mean(d['cost']):.4f}; "
          f"$/correct {sum(d['cost']) / max(n_ok, 1):.4f}; tokens/run {statistics.mean(d['in']) + statistics.mean(d['out']):,.0f}; "
          f"tokens/correct {(sum(d['in']) + sum(d['out'])) / max(n_ok, 1):,.0f}")
