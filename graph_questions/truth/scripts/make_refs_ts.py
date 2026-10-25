#!/usr/bin/env python3
"""usage: make_refs_ts.py <repo_dir> <out.json>
Type-aware callers / heritage ground truth for a TS repo (TypeScript Program + TypeChecker;
helper: truth_work_refs2/refs.cjs)."""
import os, subprocess, sys
here = os.path.dirname(os.path.abspath(__file__))
cjs = os.path.join(here, "truth_work_refs2", "refs.cjs")
repo, out = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
try:
    r = subprocess.run(["node", "--max-old-space-size=8192", cjs, repo, out], capture_output=True, text=True)
except OSError as exc:
    print(f"could not start Node.js for {cjs}: {exc}", file=sys.stderr)
    sys.exit(127)
print(r.stderr.strip()); print(r.stdout.strip())
sys.exit(r.returncode)
