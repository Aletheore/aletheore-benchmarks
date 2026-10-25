import glob, json, os, sys

S = os.path.dirname(os.path.abspath(__file__)) + "/"
removed = {}
for d in sys.argv[1:]:
    for f in glob.glob(S + d + "/*.json"):
        r = json.load(open(f))
        text = (r.get("result") or "") + (r.get("raw") or "")
        if "session limit" in text or "hit your" in text:
            os.remove(f)
            removed[d] = removed.get(d, 0) + 1
print("removed rate-limited runs:", removed)
