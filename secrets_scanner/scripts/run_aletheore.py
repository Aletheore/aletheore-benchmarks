"""Runs aletheore's secrets scanner against every case in ../cases/,
using whichever `aletheore` package is currently importable (pinned/
reported by the caller - see README's "Versions" note). Same in-process
call convention as the rest of this repo's scripts (e.g.
scripts/run_aletheore.py's search_index import) rather than a CLI
subprocess.

Usage: python3 run_aletheore.py > results/aletheore.json
"""
import json
import sys
import tempfile
from pathlib import Path

import aletheore
from aletheore.secrets import find_secrets

sys.path.insert(0, str(Path(__file__).parent))
from fixtures import materialize_case_repo  # noqa: E402

CASES_DIR = Path(__file__).parent.parent / "cases"


def main() -> int:
    case_dirs = sorted(p for p in CASES_DIR.iterdir() if p.is_dir())
    results = {"tool": "aletheore", "version": aletheore.__version__, "cases": {}}

    with tempfile.TemporaryDirectory(prefix="aletheore-secrets-bench-") as tmp:
        for case_dir in case_dirs:
            materialized = materialize_case_repo(case_dir, Path(tmp) / case_dir.name)
            result = find_secrets(materialized)
            results["cases"][case_dir.name] = [
                {"path": f["path"], "line": f["line"], "reported": not f["likely_placeholder"]}
                for f in result["findings"]
            ]

    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
