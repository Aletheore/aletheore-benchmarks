"""Model-free: what the (new) router returns for hubs and cycles tasks, scored against the independent truth.
Usage: ml_hubs_cycles_check.py SRC_DIR   (the Aletheore source tree whose router to test)"""
import json, os, sys
S = os.path.dirname(os.path.abspath(__file__)) + "/"
sys.path.insert(0, S)
sys.path.insert(0, sys.argv[1])
os.environ["ML_TASKS"] = "ml_tasks_h.json"
from aletheore import tool_router as tr
import ml_run
from ml_pick import Graph

res = {"hubs": [0, 0, 0], "cycles": [0, 0, 0]}  # n, routed right, scored right
bad = []
for t in ml_run.TASKS.values():
    if t["kind"] not in res:
        continue
    ev = json.load(open(f"{S}{t['repo']}/.aletheore/air.json"))
    paths = [m["path"] for m in ev["repository"]["modules"]]
    q = ml_run.question(t)
    route = tr.route(q, None, paths)
    out = tr.answer(q, None, ev, S + t["repo"])
    a = out.get("answer")
    r = res[t["kind"]]
    r[0] += 1
    want = {"hubs": "hubs", "cycles": "cycles"}[t["kind"]]
    routed = route.confidence == "high" and route.intent == want
    r[1] += routed
    ok = False
    if routed and isinstance(a, dict):
        if t["kind"] == "hubs":
            ok = {m["path"] for m in a["most_imported"]} == set(t["truth"])
        else:
            if not t["has_cycle"]:
                ok = not a["has_cycle"]
            else:
                cyc = (a["cycle_groups"] or [{}])[0].get("example_cycle") or []
                g = Graph(t["repo"])
                n = len(cyc)
                ok = n >= 2 and len(set(cyc)) == n and all(cyc[(i + 1) % n] in g.fwd.get(cyc[i], ()) for i in range(n))
    r[2] += ok
    if not ok:
        bad.append((t["id"], route.intent, route.confidence))
for k, (n, routed, ok) in res.items():
    print(f"{k:7s} n={n:2d} routed right {routed:2d}  answer scores right {ok:2d}")
print("not right:", bad)
