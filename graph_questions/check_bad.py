import collections, glob, json, re, sys, os
S = os.path.dirname(os.path.abspath(__file__)) + "/"
bad = collections.Counter()
examples = {}
pat = re.compile(r"(api error|unable to connect|econn|enotfound|network|timed out|connection|overloaded|session limit|rate limit|fetch failed|socket)", re.I)
n = 0
for f in glob.glob(S + sys.argv[1] + "/*.json"):
    r = json.load(open(f))
    n += 1
    txt = r.get("result") or r.get("raw") or ""
    flagged = bool(pat.search(txt[:400])) or r.get("rc") not in (0, None) or (r.get("subtype") not in (None, "success"))
    if flagged:
        key = (r.get("rc"), r.get("subtype"), pat.search(txt[:400]).group(1).lower() if pat.search(txt[:400]) else "-")
        bad[key] += 1
        examples.setdefault(key, (f.split("/")[-1], txt[:140].replace("\n", " ")))
print("results", n, "suspicious", sum(bad.values()))
for k, v in bad.items():
    print(v, k, examples[k])
secs = [json.load(open(f)).get("seconds", 0) for f in glob.glob(S + sys.argv[1] + "/*.json")]
print("longest runs (s):", sorted(secs)[-5:])
