"""Definitive published numbers: released code only (master 9ab85687), arms A-D over every set, plus E where it exists.
Writes publish_numbers.json and prints the tables."""
import collections, glob, json, random, statistics, sys, os
S = os.path.dirname(os.path.abspath(__file__)) + "/"
sys.path.insert(0, S)
from scoring import LANGNAME, REPOS, load_tasks, score

TASKS = load_tasks(
    "gq_tasks_all.json,ml_tasks_all.json,ml_tasks_b.json,ml_tasks_c.json,ml_tasks_x.json,ml_tasks_h.json".split(","),
    S,
)
SETS = {
    "python": ("Python (Django, ERPNext)", ["out_py1"]),
    "ml": ("12 repositories, 9 more languages", ["out_ml1", "out_ml2", "out_ml3"]),
    "locate_path": ("Where is X defined / shortest import chain", ["out_x"]),
    "hard": ("Hubs, cycles, duplicate names, callers, subclasses", ["out_h"]),
}
rng = random.Random(1)
runs = collections.defaultdict(lambda: collections.defaultdict(list))  # (set, arm) -> task -> [(ok, in, out, turns, cost)]
for key, (_, dirs) in SETS.items():
    for d in dirs:
        for f in glob.glob(S + d + "/*.json"):
            r = json.load(open(f))
            if r.get("skipped") or r["id"] not in TASKS:
                continue
            ok, _ = score(TASKS[r["id"]], r.get("result"))
            runs[(key, r["arm"])].setdefault(r["id"], []).append((ok, r.get("in_tokens") or 0, r.get("out_tokens") or 0, r.get("turns") or 0, r.get("cost_usd") or 0))


def table(key, arms="ABCD"):
    common = set.intersection(*[set(runs[(key, a)]) for a in arms])
    ids = sorted(common)
    out = {"n_tasks": len(ids), "arms": {}}
    for a in arms:
        rows = runs[(key, a)]
        allruns = [x for t in ids for x in rows[t]]
        correct = sum(x[0] for x in allruns)
        acc = statistics.mean(statistics.mean(x[0] for x in rows[t]) for t in ids)
        entry = {
            "accuracy": acc,
            "input_tokens": statistics.mean(x[1] for x in allruns),
            "output_tokens": statistics.mean(x[2] for x in allruns),
            "turns": statistics.mean(x[3] for x in allruns),
            "usd_per_run": statistics.mean(x[4] for x in allruns),
            "usd_per_correct": sum(x[4] for x in allruns) / max(correct, 1),
            "runs": len(allruns),
        }
        if a != "A":
            diffs = [statistics.mean(x[0] for x in rows[t]) - statistics.mean(x[0] for x in runs[(key, "A")][t]) for t in ids]
            bs = sorted(statistics.mean(rng.choice(diffs) for _ in diffs) for _ in range(3000))
            entry["vs_grep"] = [statistics.mean(diffs), bs[75], bs[2924]]
        out["arms"][a] = entry
    return out


result = {k: table(k) for k in SETS}
result["locate_path_with_E"] = table("locate_path", "ABCDE")
hard_e = {t for t in runs[("hard", "E")]}
result["hard_with_E"] = table("hard", "ABCDE")
# pooled across the three non-Python sets that share the same kinds
pool = {}
for a in "ABCD":
    pool[a] = {}
    for k in ("ml",):
        pool[a].update(runs[(k, a)])
ids = sorted(set.intersection(*[set(pool[a]) for a in "ABCD"]))
bykind = collections.defaultdict(list)
for t in ids:
    bykind[TASKS[t]["kind"]].append(t)
result["ml_by_kind"] = {kind: {a: statistics.mean(statistics.mean(x[0] for x in pool[a][t]) for t in ts) for a in "ABCD"} | {"n": len(ts)} for kind, ts in bykind.items()}
bylang = collections.defaultdict(list)
for t in ids:
    bylang[LANGNAME[REPOS[TASKS[t]["repo"]]]].append(t)
result["ml_by_language"] = {lang: {a: statistics.mean(statistics.mean(x[0] for x in pool[a][t]) for t in ts) for a in "ABCD"} | {"n": len(ts)} for lang, ts in bylang.items()}
# without ownership
noown = [t for t in ids if TASKS[t]["kind"] != "owner"]
bs = {}
for a in "ABCD":
    bs[a] = statistics.mean(statistics.mean(x[0] for x in pool[a][t]) for t in noown)
result["ml_no_ownership"] = {"n_tasks": len(noown), **bs}
json.dump(result, open(S + "publish_numbers.json", "w"), indent=1, default=float)
for k in ("python", "ml", "locate_path_with_E", "hard", "hard_with_E"):
    t = result[k]
    print(f"\n== {k}: {t['n_tasks']} tasks")
    for a, e in t["arms"].items():
        vs = "" if a == "A" else f" vs grep {e['vs_grep'][0]:+.2f} [{e['vs_grep'][1]:+.2f},{e['vs_grep'][2]:+.2f}]"
        print(f"  {a}: acc {e['accuracy']:.2f}{vs}  in {e['input_tokens']:,.0f} out {e['output_tokens']:,.0f} turns {e['turns']:.1f} ${e['usd_per_run']:.4f}/run ${e['usd_per_correct']:.4f}/correct ({e['runs']} runs)")
print("\nml by language:", {k: {a: round(v[a], 2) for a in 'ABCD'} | {'n': v['n']} for k, v in result['ml_by_language'].items()})
print("ml by kind:", {k: {a: round(v[a], 2) for a in 'ABCD'} | {'n': v['n']} for k, v in result['ml_by_kind'].items()})
print("ml no ownership:", result["ml_no_ownership"])
