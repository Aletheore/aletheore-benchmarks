"""Tables with task-level bootstrap CIs across languages/kinds. Usage: ml_score2.py tasks1.json,tasks2.json out1,out2 [arms-to-compare-with-A]"""
import collections, glob, json, os, random, re, statistics, sys

S = os.path.dirname(os.path.abspath(__file__)) + "/"
sys.path.insert(0, S)
from ml_pick import REPOS, Graph  # noqa: E402

TASKS = {}
for f in sys.argv[1].split(","):
    TASKS.update({t["id"]: t for t in json.load(open(S + f))})
OUTS = sys.argv[2].split(",")
LANGNAME = {"python": "Python", "go": "Go", "ts": "TS/JS", "java": "Java", "csharp": "C#", "rust": "Rust", "php": "PHP", "ruby": "Ruby", "c": "C", "cpp": "C++"}
_GRAPHS = {}


def graph(repo):
    if repo not in _GRAPHS:
        _GRAPHS[repo] = Graph(repo)
    return _GRAPHS[repo]


def parse_list(text):
    m = re.search(r"\[.*\]", text or "", re.S)
    try:
        return [p.strip().removeprefix("./") for p in json.loads(m.group(0)) if isinstance(p, str)] if m else None
    except ValueError:
        return None


def score(t, text):
    k = t["kind"]
    if k == "cycles":
        pred = parse_list(text)
        if pred is None:
            return 0.0, False
        if not t["has_cycle"]:
            return (1.0 if pred == [] else 0.0), True
        g = graph(t["repo"])
        n = len(pred)
        valid = n >= 2 and len(set(pred)) == n and all(pred[(i + 1) % n] in g.fwd.get(pred[i], ()) for i in range(n))
        return (1.0 if valid else 0.0), True
    if k in ("direct", "unreachable", "hubs", "dupdef", "callers", "subclasses"):
        pred = parse_list(text)
        if pred is None:
            return 0.0, False
        return (1.0 if set(pred) == set(t["truth"]) else 0.0), True
    if k in ("size", "deps"):
        m = re.search(r"\d[\d,]*", (text or "").replace('"count"', ""))
        if not m:
            return 0.0, False
        return (1.0 if abs(int(m.group(0).replace(",", "")) - t["truth_n"]) / t["truth_n"] <= 0.10 else 0.0), True
    if k == "locate":
        m = re.search(r'"file"\s*:\s*"([^"]+)"', text or "")
        if not m:
            return 0.0, False
        return (1.0 if m.group(1).strip().removeprefix("./") == t["truth_file"] else 0.0), True
    if k == "path":
        pred = parse_list(text)
        if not pred:
            return 0.0, False
        g = graph(t["repo"])
        valid = pred[0] == t["target"] and pred[-1] == t["to"] and all(b in g.fwd.get(a, ()) for a, b in zip(pred, pred[1:]))
        return (1.0 if valid and len(pred) - 1 == t["truth_len"] else 0.0), True
    names = re.findall(r'"author"\s*:\s*"([^"]+)"', text or "")
    if not names:
        return 0.0, False
    want, got = t["truth_author"].lower().split(), names[0].lower()
    return (1.0 if want[-1] in got and want[0] in got else 0.0), True


rows = collections.defaultdict(list)
extra = collections.defaultdict(lambda: collections.defaultdict(list))
unparsed = collections.Counter()
for out in OUTS:
    for f in sorted(glob.glob(S + out + "/*.json")):
        r = json.load(open(f))
        if r["id"] not in TASKS:
            continue
        t = TASKS[r["id"]]
        ok, parsed = score(t, r.get("result"))
        unparsed[r["arm"]] += not parsed
        rows[(r["id"], r["arm"])].append(ok)
        extra[r["arm"]]["turns"].append(r.get("turns") or 0)
        extra[r["arm"]]["cost"].append(r.get("cost_usd") or 0)
arms = sorted({a for _, a in rows if a in os.environ.get("ARMS", "ABCDE")})
per = {k: statistics.mean(v) for k, v in rows.items()}
rng = random.Random(1)


def table(label, ids):
    ids = [i for i in ids if all((i, a) in per for a in arms)]
    if not ids:
        return
    means = {a: statistics.mean(per[(i, a)] for i in ids) for a in arms}
    ci = []
    for a in arms:
        if a == "A":
            continue
        diffs = [per[(i, a)] - per[(i, "A")] for i in ids]
        bs = sorted(statistics.mean(rng.choice(diffs) for _ in diffs) for _ in range(2000))
        ci.append(f"{a}-A {statistics.mean(diffs):+.2f} [{bs[50]:+.2f},{bs[1949]:+.2f}]")
    print(f"{label:24s} n={len(ids):3d} " + " ".join(f"{a}={means[a]:.2f}" for a in arms) + " | " + "  ".join(ci))


ids = sorted({i for i, _ in rows})
lang_of = lambda i: LANGNAME[REPOS[TASKS[i]["repo"]]]  # noqa: E731
for lang in LANGNAME.values():
    table(f"lang {lang}", [i for i in ids if lang_of(i) == lang])
for kind in ("direct", "size", "deps", "unreachable", "owner", "locate", "path", "hubs", "cycles", "dupdef", "callers", "subclasses"):
    table(f"kind {kind}", [i for i in ids if TASKS[i]["kind"] == kind])
table("ALL", ids)
print("unparsed per arm:", dict(unparsed))
for a in arms:
    print(a, "turns %.2f" % statistics.mean(extra[a]["turns"]), "cost/run $%.4f" % statistics.mean(extra[a]["cost"]))
