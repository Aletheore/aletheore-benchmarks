"""Stage 3: gather one trial's per-PR outputs into the file format judge_full_pipeline.py reads.
Writes prod_<tag>.json (findings after the grounding gate) and ungated_<tag>.json (the same
generations before it). Run: python3 assemble.py <work dir> <tag>"""
import json
import sys
from pathlib import Path

work = Path(sys.argv[1])
tag = sys.argv[2]
cases, ungated, warnings = {}, {}, []
for f in sorted((work / f"trial_{tag}").glob("*.json")):
    d = json.loads(f.read_text())
    cases[f.stem] = d["findings"]
    ungated[f.stem] = (d["gate"] or {}).get("proposed", d["findings"])
    warnings += d["warnings"]
(work / f"prod_{tag}.json").write_text(json.dumps({"flash": [{"findings": cases, "warnings": warnings}], "air": []}))
(work / f"ungated_{tag}.json").write_text(json.dumps({"flash": [{"findings": ungated}], "air": []}))
src = {}
for fs in cases.values():
    for f in fs:
        src[f.get("source")] = src.get(f.get("source"), 0) + 1
print(tag, len(cases), "cases", sum(len(v) for v in cases.values()), "findings", src, "warnings", len(warnings))
print("ungated", tag, sum(len(v) for v in ungated.values()), "proposed findings")
