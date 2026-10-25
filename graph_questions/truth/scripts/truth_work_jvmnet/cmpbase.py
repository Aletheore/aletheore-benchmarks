import json, sys, os, re, random
src = open(".").read()
src = re.sub(r'^L = .*$', 'L = "./"', src, flags=re.M)
ns = {}
exec(compile(src, "truth_regex", "exec"), ns)
for repo, lang in (("gson", "j"), ("thrift", "j"), ("automapper", "c")):
    if lang == "j":
        fs, g = ns["java_graph"](repo)
    else:
        fs, g, _ = ns["cs_graph"](repo)
    B = {(a, b) for a in g for b in g[a]}
    d = json.load(open(f"./truth/{repo}.json"))
    T = {tuple(e) for e in d["edges"]}
    fset = set(d["files"])
    dang = [e for e in T if e[0] not in fset or e[1] not in fset]
    print(repo, "regex", len(B), "new", len(T), "both", len(B & T), "only_new", len(T - B), "only_regex", len(B - T), "dangling", len(dang), "sorted", d["edges"] == sorted(d["edges"]), "files_eq", sorted(fs) == d["files"])
    random.seed(1)
    print(" only_new", random.sample(sorted(T - B), min(6, len(T - B))))
    print(" only_regex", random.sample(sorted(B - T), min(6, len(B - T))))
