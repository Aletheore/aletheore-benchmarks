#!/usr/bin/env python3
"""usage: make_refs_go.py <repo_dir> <out.json>
Type-aware callers / subtypes ground truth for a Go repo via go/types (helper: truth_work_refs2/gorefs)."""
import json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _tools import run_tool
W = "./truth_work_refs2/gorefs"
repo = os.path.abspath(sys.argv[1]); out = os.path.abspath(sys.argv[2])
files = run_tool(["git", "-C", repo, "ls-files", "*.go"], capture_output=True, text=True, check=True).stdout
env = dict(os.environ, GOFLAGS="-mod=mod", GOTOOLCHAIN="local")
with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as t:
    t.write(files); lst = t.name
run_tool(["go", "build", "-o", W + "/gorefs_bin", "."], cwd=W, check=True, env=env)
run_tool([W + "/gorefs_bin", repo, lst, out], cwd=repo, check=True, env=env)
d = json.load(open(out))
print("functions", len(d["functions"]), "classes", len(d["classes"]))
