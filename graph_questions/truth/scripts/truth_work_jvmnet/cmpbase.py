"""Compare committed JVM/.NET truth with a supplied legacy regex graph module.

Set TRUTH_REGEX_SOURCE to the legacy module path. The legacy implementation is
intentionally not bundled with this repository; this script must not guess one.
Only point this variable at trusted Python source: importing it executes its code.
"""

import importlib.util
import json
import os
import random
import re
import sys

source_path = os.environ.get("TRUTH_REGEX_SOURCE")
if not source_path:
    raise SystemExit("TRUTH_REGEX_SOURCE must name the legacy graph module to compare")
with open(source_path, encoding="utf-8") as source_file:
    src = source_file.read()
if len(re.findall(r"^L\s*=", src, flags=re.M)) != 1:
    raise SystemExit(f"{source_path} must contain exactly one top-level `L = ...` assignment")
spec = importlib.util.spec_from_file_location("truth_regex", source_path)
if spec is None or spec.loader is None:
    raise SystemExit(f"cannot load legacy graph module: {source_path}")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.L = "./"
for repo, lang in (("gson", "j"), ("thrift", "j"), ("automapper", "c")):
    if lang == "j":
        fs, g = module.java_graph(repo)
    else:
        fs, g, _ = module.cs_graph(repo)
    B = {(a, b) for a in g for b in g[a]}
    d = json.load(open(f"./truth/{repo}.json"))
    T = {tuple(e) for e in d["edges"]}
    fset = set(d["files"])
    dang = [e for e in T if e[0] not in fset or e[1] not in fset]
    print(repo, "regex", len(B), "new", len(T), "both", len(B & T), "only_new", len(T - B), "only_regex", len(B - T), "dangling", len(dang), "sorted", d["edges"] == sorted(d["edges"]), "files_eq", sorted(fs) == d["files"])
    random.seed(1)
    print(" only_new", random.sample(sorted(T - B), min(6, len(T - B))))
    print(" only_regex", random.sample(sorted(B - T), min(6, len(B - T))))
