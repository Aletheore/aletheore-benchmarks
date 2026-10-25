import glob, json, os, re, sys
S = os.path.dirname(os.path.abspath(__file__)) + "/"
pat = re.compile(r"(api error|unable to connect|econn|enotfound|connection refused|fetch failed|socket hang)", re.I)
removed = []
for f in glob.glob(S + sys.argv[1] + "/*.json"):
    r = json.load(open(f))
    txt = r.get("result") or r.get("raw") or ""
    if pat.search(txt[:400]) and r.get("rc") == 1:
        removed.append(os.path.basename(f))
        os.remove(f)
print("removed", len(removed), removed)
