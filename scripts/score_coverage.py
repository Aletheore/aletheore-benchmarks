"""Score a multi-answer question set by how many distinct languages it surfaces.

Every other set here has one correct file, so top-1 is the right metric. These
questions name no language, and in a polyglot repository that means there is no
single correct answer: "where is the binary protocol implemented?" is answered
correctly by any of eight files. Scoring those with top-1 would reward filling
all five slots with near-duplicates from whichever language embedded closest,
which is the behaviour under investigation rather than the goal.

  hit@k        did any correct file appear - the easy floor, should be high
  coverage@k   how many DISTINCT languages of the correct set appeared,
               over the most that could fit in k slots
  langs@k      distinct languages among the returned results, correct or not

Usage:  score_coverage.py <name> <repo> <questions.json>
"""
import json
import statistics
import sys
from pathlib import Path

from aletheore.search_index import search_index

NAME, REPO, QFILE = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
questions = json.load(open(QFILE))
search_index(REPO, "warm up", k=10)


def language_of(path: str) -> str:
    parts = path.split("/")
    return parts[1] if path.startswith("lib/") and len(parts) > 1 else parts[0]


rows = []
for q in questions:
    hits = search_index(REPO, q["question"], k=10)
    files, seen = [], set()
    for h in hits:
        p = h.get("module_path")
        if p and p not in seen:
            seen.add(p)
            files.append(p)
    gt = set(q["ground_truth_files"])
    gt_langs = {language_of(f) for f in gt}
    rows.append({"id": q["id"], "files": files, "gt": gt, "gt_langs": gt_langs})

print(f"\n{NAME}  (n={len(rows)})")
for k in (3, 5, 10):
    hit = sum(1 for r in rows if any(f in r["gt"] for f in r["files"][:k]))
    covs, divs = [], []
    for r in rows:
        top = r["files"][:k]
        correct_langs = {language_of(f) for f in top if f in r["gt"]}
        ceiling = min(k, len(r["gt_langs"]))
        covs.append(len(correct_langs) / ceiling if ceiling else 0.0)
        divs.append(len({language_of(f) for f in top}))
    print(
        f"  k={k:2}  hit {100*hit/len(rows):5.1f}%   "
        f"coverage {100*statistics.mean(covs):5.1f}%   "
        f"langs returned {statistics.mean(divs):.1f}"
    )

print("\n  per question (k=5): correct langs surfaced / available")
for r in rows:
    top = r["files"][:5]
    cl = sorted({language_of(f) for f in top if f in r["gt"]})
    print(f"    {r['id']}  {len(cl)}/{len(r['gt_langs'])}  {cl}")
