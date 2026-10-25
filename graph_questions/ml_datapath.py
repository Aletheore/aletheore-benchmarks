import collections, json, os, sys
S = os.path.dirname(os.path.abspath(__file__)) + "/"
sys.path.insert(0, S)
sys.path.insert(0, S + "ehr/src")
os.environ.setdefault("ML_TASKS", sys.argv[1])
from aletheore import tool_router as tr
import ml_run
from ml_pick import Graph, LANGS, REPOS

EXPECT = {"direct": "impact", "size": "impact", "deps": "dependencies", "unreachable": "dead_code", "owner": "owner"}
stat = collections.defaultdict(lambda: [0, 0, 0])
bad = []
EV = {}
for r in {t["repo"] for t in ml_run.TASKS.values()}:
    EV[r] = json.load(open(f"{S}{r}/.aletheore/air.json"))
    g = Graph(r)
    A = {(m["path"], t) for m in EV[r]["repository"]["modules"] for t in m["imports"]}
    T = {(a, b) for a, bs in g.fwd.items() for b in bs}
    print(r, "edges aletheore", len(A), "truth", len(T), "precision %.3f recall %.3f" % (len(A & T) / max(1, len(A)), len(A & T) / max(1, len(T))))
for t in ml_run.TASKS.values():
    ev = EV[t["repo"]]
    q = ml_run.question(t)
    paths = [m["path"] for m in ev["repository"]["modules"]]
    route = tr.route(q, None, paths)
    out = tr.answer(q, None, ev, S + t["repo"])
    a = out.get("answer")
    k = t["kind"]
    stat[k][0] += 1
    routed = route.confidence == "high" and route.intent == EXPECT[k]
    stat[k][1] += routed
    ok = False
    if routed and isinstance(a, (dict, list)):
        if k == "deps":
            ok = abs(a["depends_on_non_test_total"] - t["truth_n"]) / t["truth_n"] <= 0.10
        elif k == "size":
            ok = abs(a["affected_total"] - a["affected_test_files"] - t["truth_n"]) / t["truth_n"] <= 0.10
        elif k == "owner":
            top = max(a, key=lambda o: o.get("percent", 0)) if a else {}
            ok = t["truth_author"].split()[-1].lower() in json.dumps(top).lower()
        elif k == "direct":
            got = set(a.get("direct_dependents", []))
            ok = set(t["truth"]) <= got
        elif k == "unreachable":
            got = set(a.get("unimported", a.get("modules", [])) if isinstance(a, dict) else [])
            ok = set(t["truth"]) <= got
    stat[k][2] += ok
    if not (routed and ok):
        bad.append((t["id"], k, route.confidence, route.intent))
for k, (n, r, a) in sorted(stat.items()):
    print(f"{k:12s} n={n:2d} routed right {r:2d}  answer ok {a:2d}")
print("not fully right:", bad)
