"""Runs RepoWise's own secrets/security scanner against every case in
../cases/, calling repowise.core.analysis.security_scan.SecurityScanner
directly - the same class repowise/core/pipeline/persist.py wires into
its ingestion pipeline. RepoWise exposes no standalone CLI command or
MCP tool for this scan (confirmed by reading its own cli/main.py command
list and grepping the installed package for every SecurityScanner
call site) - `repowise init` runs it as a side effect of ingestion and
persists findings to a DB table with no query command; calling the
scanner class directly is the only way to get its findings back as data
without standing up a database. `session=None` is safe: only
SecurityScanner.persist() touches the DB session, and this script never
calls persist().

Must run under RepoWise's own installed Python (its sqlalchemy version
conflicts with other environments on this machine - see README).

Usage: /path/to/repowise/venv/bin/python3 run_repowise.py > results/repowise.json
"""
import asyncio
import importlib.metadata
import json
import sys
from pathlib import Path

from repowise.core.analysis.security_scan import SecurityScanner

CASES_DIR = Path(__file__).parent.parent / "cases"

sys.path.insert(0, str(Path(__file__).parent))
from fixtures import materialize_case_repo  # noqa: E402


async def scan_case(case_dir: Path, tmp_dir: Path) -> list[dict]:
    materialized = materialize_case_repo(case_dir, tmp_dir)
    scanner = SecurityScanner(session=None, repo_id="bench")
    findings = []
    for path in sorted(materialized.rglob("*")):
        if not path.is_file():
            continue
        try:
            source = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        rel_path = path.relative_to(materialized).as_posix()
        for finding in await scanner.scan_file(rel_path, source, symbols=[]):
            # RepoWise's findings aren't secrets-only (eval_call, os_system,
            # fstring_sql, weak_hash, etc. are broader security signals) -
            # scope to the two patterns that actually target credentials,
            # the fair comparison to aletheore_secrets.
            if finding["kind"] in ("hardcoded_password", "hardcoded_secret"):
                findings.append({"path": rel_path, "line": finding["line"], "kind": finding["kind"]})
    return findings


async def main() -> int:
    import tempfile

    case_dirs = sorted(p for p in CASES_DIR.iterdir() if p.is_dir())
    try:
        version = importlib.metadata.version("repowise")
    except importlib.metadata.PackageNotFoundError:
        version = "unknown"
    results = {"tool": "repowise", "version": version, "cases": {}}

    with tempfile.TemporaryDirectory(prefix="repowise-secrets-bench-") as tmp:
        for case_dir in case_dirs:
            results["cases"][case_dir.name] = await scan_case(case_dir, Path(tmp) / case_dir.name)

    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
