"""Verify every ground-truth claim against the corpus before any run.

A benchmark whose ground truth is asserted rather than checked is worthless.
This caught one real error when the set was authored: Flask 3.2 merged
``RequestContext`` into ``AppContext``, so an anchor naming the old class
pointed at a symbol that no longer existed.

A question passes when at least one of its ground-truth files exists and
contains the anchor. Multi-file answers are deliberately treated as "any of
these is correct", so a question is counted once, whether it has one
ground-truth file or three.

Usage:  python3 verify_ground_truth.py /path/to/repo [question-set]

    python3 verify_ground_truth.py /tmp/bench-flask            # location
    python3 verify_ground_truth.py /tmp/bench-slim slim
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _bench

repo = sys.argv[1] if len(sys.argv) > 1 else _bench.FLASK
qset = sys.argv[2] if len(sys.argv) > 2 else "location"

path = os.path.join(_bench.ROOT, "questions", f"{qset}.json")
if not os.path.exists(path):
    sys.exit(f"no such question set: {path}")
qs = json.load(open(path))

bad = 0
for q in qs:
    hit = False
    problems = []
    for f in q["ground_truth_files"]:
        p = os.path.join(repo, f)
        if not os.path.exists(p):
            problems.append(f"missing file {f}")
            continue
        if q["verification_anchor"] in open(p, errors="ignore").read():
            hit = True
    if not hit:
        bad += 1
        detail = "; ".join(problems) if problems else "anchor not found"
        print(f"FAIL  {q['id']}  {q['verification_anchor']!r} "
              f"in {q['ground_truth_files']}  ({detail})")

print(f"\n{qset}: verified {len(qs) - bad}/{len(qs)} against {repo}")
sys.exit(1 if bad else 0)
