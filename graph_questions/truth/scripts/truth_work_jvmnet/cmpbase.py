"""Compare committed JVM/.NET truth with a supplied legacy regex graph module.

Set TRUTH_REGEX_SOURCE to the legacy module path. The legacy implementation is
intentionally not bundled with this repository; this script must not guess one.
Only point this variable at trusted Python source: importing it executes its code.
"""

import ast
import importlib.machinery
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
tree = ast.parse(src, filename=source_path)
assignments = [
    node for node in tree.body
    if isinstance(node, ast.Assign)
    and any(isinstance(target, ast.Name) and target.id == "L" for target in node.targets)
]
if len(assignments) != 1:
    raise SystemExit(f"{source_path} must contain exactly one top-level `L = ...` assignment")
assignment = assignments[0]
if len(assignment.targets) != 1 or not isinstance(assignment.targets[0], ast.Name):
    raise SystemExit(f"{source_path} must contain one simple top-level `L = ...` assignment")
assignment.value = ast.Constant(value="./")
ast.fix_missing_locations(tree)


class RootOverrideLoader(importlib.machinery.SourceFileLoader):
    def get_code(self, fullname):
        return compile(tree, source_path, "exec")


loader = RootOverrideLoader("truth_regex", source_path)
spec = importlib.util.spec_from_loader("truth_regex", loader)
if spec is None or spec.loader is None:
    raise SystemExit(f"cannot load legacy graph module: {source_path}")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
for repo, lang in (("gson", "j"), ("thrift", "j"), ("automapper", "c")):
    if lang == "j":
        fs, g = module.java_graph(repo)
    else:
        fs, g, _ = module.cs_graph(repo)
    B = {(a, b) for a in g for b in g[a]}
    with open(f"./truth/{repo}.json", encoding="utf-8") as truth_file:
        d = json.load(truth_file)
    T = {tuple(e) for e in d["edges"]}
    fset = set(d["files"])
    dang = [e for e in T if e[0] not in fset or e[1] not in fset]
    print(repo, "regex", len(B), "new", len(T), "both", len(B & T), "only_new", len(T - B), "only_regex", len(B - T), "dangling", len(dang), "sorted", d["edges"] == sorted(d["edges"]), "files_eq", sorted(fs) == d["files"])
    random.seed(1)
    # Samples are display-only examples, never security-sensitive values.
    print(" only_new", random.sample(sorted(T - B), min(6, len(T - B))))  # nosec B311
    print(" only_regex", random.sample(sorted(B - T), min(6, len(B - T))))  # nosec B311
