"""Compare committed JVM/.NET truth with a supplied legacy regex graph module.

Set TRUTH_REGEX_SOURCE to the legacy module path. The legacy implementation is
intentionally not bundled with this repository; this script must not guess one.
"""

import json, sys, os, re, random

source_path = os.environ.get("TRUTH_REGEX_SOURCE")
if not source_path:
    raise SystemExit("TRUTH_REGEX_SOURCE must name the legacy graph module to compare")
with open(source_path, encoding="utf-8") as source_file:
    src = source_file.read()
src, replacements = re.subn(r'^L = .*$', 'L = "./"', src, count=1, flags=re.M)
if replacements != 1:
    raise SystemExit(f"{source_path} must contain exactly one top-level `L = ...` assignment")
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
