#!/usr/bin/env python3
"""usage: make_refs_ts.py <repo_dir> <out.json>
Type-aware callers / heritage ground truth for a TS repo (TypeScript Program + TypeChecker;
helper: truth_work_refs2/refs.cjs)."""
import os, subprocess, sys
cjs = "./truth_work_refs2/refs.cjs"
repo, out = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
r = subprocess.run(["node", "--max-old-space-size=8192", cjs, repo, out], capture_output=True, text=True)
print(r.stderr.strip()); print(r.stdout.strip())
sys.exit(r.returncode)
