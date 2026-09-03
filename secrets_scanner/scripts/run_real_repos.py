"""Runs either aletheore's or RepoWise's secrets scanner (whichever is
importable under the interpreter this is invoked with) against a set of
real repos already fetched by ../../real_repos/fetch_repos.sh, for a
real, uncontrolled-code comparison the synthetic corpus alone can't
provide. Prints one JSON object to stdout.

Usage:
  <aletheore venv>/bin/python3 run_real_repos.py /path/to/repos --tool aletheore > results/real_repos_aletheore_pypi.json
  <repowise venv>/bin/python3 run_real_repos.py /path/to/repos --tool repowise > results/real_repos_repowise.json
"""
import argparse
import asyncio
import importlib.metadata
import json
from pathlib import Path


def scan_with_aletheore(repo_path: Path) -> list[dict]:
    from aletheore.secrets import find_secrets

    result = find_secrets(repo_path)
    return [
        {"path": f["path"], "line": f["line"], "pattern": f["pattern"], "reported": not f["likely_placeholder"]}
        for f in result["findings"]
    ]


async def _scan_with_repowise_async(repo_path: Path) -> list[dict]:
    from repowise.core.analysis.security_scan import SecurityScanner

    scanner = SecurityScanner(session=None, repo_id="bench")
    findings = []
    for path in sorted(repo_path.rglob("*")):
        if not path.is_file():
            continue
        try:
            source = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        rel_path = path.relative_to(repo_path).as_posix()
        for finding in await scanner.scan_file(rel_path, source, symbols=[]):
            if finding["kind"] in ("hardcoded_password", "hardcoded_secret"):
                findings.append({"path": rel_path, "line": finding["line"], "kind": finding["kind"]})
    return findings


def scan_with_repowise(repo_path: Path) -> list[dict]:
    return asyncio.run(_scan_with_repowise_async(repo_path))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("repos_dir")
    parser.add_argument("--tool", choices=["aletheore", "repowise"], required=True)
    args = parser.parse_args()

    repos_dir = Path(args.repos_dir)
    repo_dirs = sorted(p for p in repos_dir.iterdir() if p.is_dir())

    if args.tool == "aletheore":
        import aletheore

        version = aletheore.__version__
        scan = scan_with_aletheore
    else:
        version = importlib.metadata.version("repowise")
        scan = scan_with_repowise

    results = {"tool": args.tool, "version": version, "repos": {}}
    for repo_dir in repo_dirs:
        results["repos"][repo_dir.name] = scan(repo_dir)
        print(f"{repo_dir.name}: {len(results['repos'][repo_dir.name])} findings", flush=True, file=__import__("sys").stderr)

    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
