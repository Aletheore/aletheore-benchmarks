#!/usr/bin/env python3
"""usage: make_truth_js.py <repo_dir> <out.json>
Independent file-level import graph for a JS/TS repo. Wraps truth_work_js/truth.cjs
(TypeScript compiler API + workspace package.json exports resolution) and converts to
{"files": [...], "edges": [[from,to],...]}."""
import json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _tools import run_tool
here = os.path.dirname(os.path.abspath(__file__))
cjs = os.path.join(here, '..', 'truth_work_js', 'truth.cjs')
repo, out = os.path.abspath(sys.argv[1]), sys.argv[2]
with tempfile.TemporaryDirectory() as td:
    raw = os.path.join(td, 'raw.json')
    print(run_tool(['node', cjs, repo, raw], check=True, capture_output=True, text=True).stdout.strip())
    d = json.load(open(raw))
files = sorted(set(d['src']))
fs = set(files)
edges = sorted({(e['from'], e['to']) for e in d['edges'] if e['from'] != e['to'] and e['from'] in fs and e['to'] in fs})
dropped = sum(1 for e in d['edges'] if e['from'] != e['to'] and not (e['from'] in fs and e['to'] in fs))
json.dump({'files': files, 'edges': [list(e) for e in edges]}, open(out, 'w'), indent=0)
print(f'files={len(files)} edges={len(edges)} dangling_dropped={dropped} unresolved={len(d["unresolved"])}')
