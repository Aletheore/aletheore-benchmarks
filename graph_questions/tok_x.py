import collections, glob, json, statistics, sys, os
S = os.path.dirname(os.path.abspath(__file__)) + "/"
out = sys.argv[1]
agg = collections.defaultdict(lambda: collections.defaultdict(list))
kinds = {t["id"]: t["kind"] for t in json.load(open(S + sys.argv[2]))}
for f in glob.glob(S + out + "/*.json"):
    r = json.load(open(f))
    if r.get("skipped"):
        continue
    for key in ("ALL", kinds.get(r["id"], "?")):
        d = agg[(r["arm"], key)]
        d["in"].append(r.get("in_tokens") or 0)
        d["out"].append(r.get("out_tokens") or 0)
        d["turns"].append(r.get("turns") or 0)
        d["cost"].append(r.get("cost_usd") or 0)
arms = sorted({a for a, _ in agg})
keys = ["ALL"] + sorted({k for _, k in agg if k != "ALL"})
print("per run: input tokens (incl. cache) | output tokens | turns | USD")
for key in keys:
    print(f"{key:12s}" + "".join(f"  {a}: {statistics.mean(agg[(a, key)]['in']):>7,.0f} {statistics.mean(agg[(a, key)]['out']):>5,.0f} {statistics.mean(agg[(a, key)]['turns']):>4.1f} ${statistics.mean(agg[(a, key)]['cost']):.4f}" for a in arms if (a, key) in agg))
print("runs per arm:", {a: len(agg[(a, 'ALL')]['in']) for a in arms})
