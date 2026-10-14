"""Stage 1 of the production-faithful Experiment 8 run: build, once per PR, the inputs production gives
review_diff() that the published diff-only benchmark left out.

  * a checkout of the upstream repo at the PR head (partial clone, reused across PRs of one repo)
  * a check that the checkout really is the PR the corpus diff was taken from
  * file_contents, through production's own fetch_review_file_context (fetch_file_content is pointed at
    the local checkout, which returns what the GitHub contents API would at head_sha)
  * referenced_symbol_context, through production's build_referenced_symbol_context over a repo scan

Resumable: a PR whose output file exists is skipped. Progress is printed with timings.
"""
import argparse
import json
import re
import subprocess  # nosec B404 - benchmark tooling: runs git against public upstream repos
import sys
import time
from pathlib import Path

ROOT = Path(sys.argv[sys.argv.index("--root") + 1])
sys.path.insert(0, str(ROOT / "github-app"))
sys.path.insert(0, str(ROOT / "src"))
BENCH = Path(sys.argv[sys.argv.index("--bench") + 1])
sys.path.insert(0, str(BENCH / "pr_review/real_pr_recall_corpus/scripts"))

from run_benchmark import CASES, DIFFS_DIR, diff_patches_from_diff  # noqa: E402

CASE_MAP = json.loads((BENCH / "pr_review/real_pr_recall_corpus/case_map.json").read_text())


def sh(cmd, cwd=None, check=True):
    try:
        return subprocess.run(cmd, cwd=cwd, check=check, capture_output=True, text=True)  # nosec B603 - fixed git argv, no shell
    except subprocess.CalledProcessError as exc:
        print(f"command failed: {' '.join(cmd)}\n{exc.stderr}", file=sys.stderr, flush=True)
        raise


def ensure_checkout(repo: str, pr: int, repos_dir: Path) -> tuple[Path, str]:
    """Depth-1 checkout of the PR head. Full history is not needed to build the symbol graph, and a
    blobless partial clone made the scan's git-history step fetch objects one by one (it stalled)."""
    d = repos_dir / repo.replace("/", "__")
    if not d.exists():
        d.mkdir(parents=True)
        sh(["git", "init", "-q"], cwd=d)
        sh(["git", "remote", "add", "origin", f"https://github.com/{repo}.git"], cwd=d)
    sh(["git", "fetch", "-q", "--depth", "1", "origin", f"pull/{pr}/head"], cwd=d)
    sha = sh(["git", "rev-parse", "FETCH_HEAD"], cwd=d).stdout.strip()
    sh(["git", "checkout", "-q", "-f", "--detach", sha], cwd=d)
    sh(["git", "clean", "-fdxq"], cwd=d)
    return d, sha


def verify_matches_corpus(checkout: Path, patches) -> dict:
    """Do the corpus diff's added lines appear in the checked-out files?"""
    total = found = 0
    missing_files = []
    for path, patch in patches:
        f = checkout / path
        if not f.is_file():
            missing_files.append(path)
            continue
        text = f.read_text(encoding="utf-8", errors="ignore")
        for line in patch.splitlines():
            if line.startswith("+") and not line.startswith("+++"):
                body = line[1:].strip()
                if len(body) >= 12:
                    total += 1
                    found += body in text
    return {"added_lines_checked": total, "found": found,
            "ratio": round(found / total, 3) if total else None, "missing_files": missing_files}


def main() -> int:
    import faulthandler
    faulthandler.dump_traceback_later(150, repeat=False, file=sys.stderr)
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--bench", type=Path, required=True)
    p.add_argument("--work", type=Path, required=True)
    p.add_argument("--cases", default=None)
    args = p.parse_args()
    args.work.mkdir(parents=True, exist_ok=True)
    out_dir = args.work / "inputs"
    out_dir.mkdir(exist_ok=True)

    from aletheore.evidence import scan_repository
    import scan_worker.flash_review as fr

    cases = list(CASES) if not args.cases else args.cases.split(",")
    for case_id in cases:
        out = out_dir / f"{case_id}.json"
        if out.exists():
            print(f"[{case_id}] already prepared, skipping", flush=True)
            continue
        t0 = time.time()
        meta = CASE_MAP[case_id]
        repo, pr = meta["upstream_repo"], meta["upstream_pr"]
        print(f"[{case_id}] checkout {repo}#{pr} ...", flush=True)
        checkout, sha = ensure_checkout(repo, pr, args.work / "repos")
        print(f"[{case_id}] head {sha[:10]} checked out in {time.time() - t0:.0f}s", flush=True)

        raw = (DIFFS_DIR / f"{case_id}.diff").read_text()
        patches = diff_patches_from_diff(raw)
        changed_files = [f for f, _ in patches]
        diff_text = "\n\n".join(f"--- {f} ---\n{pt}" for f, pt in patches)
        verify = verify_matches_corpus(checkout, patches)
        print(f"[{case_id}] corpus-diff match: {verify}", flush=True)

        def local_fetch(client, token, repo_full_name, path, ref):
            f = checkout / path
            return f.read_text(encoding="utf-8", errors="replace") if f.is_file() else None

        fr.fetch_file_content = local_fetch
        file_contents = fr.fetch_review_file_context(None, "", repo, changed_files, sha, diff_patches=patches)

        t1 = time.time()
        evidence = scan_repository(
            checkout,
            check_vulnerabilities=False, scan_git_history=False, check_licenses=False,
            map_endpoints=False, map_schema=False, check_static_analysis=False,
            analyze_architecture=False, check_hotspots=False, progress=None,
        )
        print(f"[{case_id}] scan done in {time.time() - t1:.0f}s", flush=True)

        def fetch_symbol_source(file_path, start_line, end_line):
            f = checkout / file_path
            if not f.is_file():
                return None
            content = f.read_text(encoding="utf-8", errors="replace")
            return "\n".join(content.split("\n")[start_line - 1: end_line])

        ref_ctx = fr.build_referenced_symbol_context(evidence, changed_files, diff_text, fetch_symbol_source)
        out.write_text(json.dumps({
            "case_id": case_id, "title": CASES[case_id], "head_sha": sha, "verify": verify,
            "changed_files": changed_files, "file_contents": file_contents,
            "referenced_symbol_context": ref_ctx,
            "scan_seconds": round(time.time() - t1, 1),
        }))
        print(f"[{case_id}] prepared in {time.time() - t0:.0f}s: {len(file_contents)}/{len(changed_files)} files read, "
              f"referenced-symbol context {len(ref_ctx)} chars", flush=True)
    print("PREPARE_DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
