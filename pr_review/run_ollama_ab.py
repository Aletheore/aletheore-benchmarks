"""Run the controlled Ollama-only versus Aletheore-context PR review test."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.request import Request, urlopen


OLLAMA_BASELINE = "ollama_baseline"
OLLAMA_ALETHEORE_CONTEXT = "ollama_aletheore_context"
REPO = "Aletheore/pr-review-benchmark-sandbox"


def _gh_json(endpoint: str) -> object:
    result = subprocess.run(["gh", "api", endpoint], capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def _git_clone_pr(repo_dir: Path, pr_number: int, destination: Path) -> None:
    subprocess.run(["git", "clone", "--quiet", f"https://github.com/{REPO}.git", str(repo_dir)], check=True)
    subprocess.run(
        ["git", "-C", str(repo_dir), "fetch", "--quiet", "origin", f"pull/{pr_number}/head:refs/remotes/origin/pr/{pr_number}"],
        check=True,
    )
    archive = subprocess.run(
        ["git", "-C", str(repo_dir), "archive", f"refs/remotes/origin/pr/{pr_number}"],
        stdout=subprocess.PIPE,
        check=True,
    ).stdout
    import tarfile
    import io

    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(destination, filter="data")


def _ollama_completion(
    base_url: str, model: str, system: str, user: str, seed: int, max_output_tokens: int
) -> tuple[str, dict]:
    payload = {
        "model": model,
        "stream": False,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        # num_ctx: without this, Ollama loads the model at its own default
        # (observed: 4096 tokens), and any prompt bigger than that gets
        # silently truncated with no error - confirmed via a real corpus
        # measurement that full-context prompts run up to ~11,190 tokens
        # (system prompt + file/diff/evidence context), so 16384 leaves
        # comfortable headroom without needing more KV-cache memory than
        # this machine reasonably has.
        "options": {"temperature": 0, "seed": seed, "num_predict": max_output_tokens, "num_ctx": 16384},
    }
    request = Request(
        f"{base_url.rstrip('/')}/api/chat",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.monotonic()
    with urlopen(request, timeout=180) as response:
        data = json.loads(response.read())
    data["elapsed_seconds"] = time.monotonic() - started
    return data.get("message", {}).get("content", ""), data


class _OllamaAdapter:
    def __init__(self, base_url: str, model: str, seed: int, max_output_tokens: int, capture: dict):
        self.base_url = base_url
        self.model = model
        self.seed = seed
        self.max_output_tokens = max_output_tokens
        self.capture = capture

    def simple_completion(self, system_prompt: str, user_prompt: str, cwd: str = ".") -> str:
        content, raw = _ollama_completion(
            self.base_url, self.model, system_prompt, user_prompt, self.seed, self.max_output_tokens
        )
        self.capture.update(raw)
        return content


def _case_inputs(pr_number: int) -> tuple[list[str], tuple[tuple[str, str], ...]]:
    files = _gh_json(f"repos/{REPO}/pulls/{pr_number}/files")
    patches = tuple((item["filename"], item.get("patch", "")) for item in files if item.get("patch"))
    return [item["filename"] for item in files], patches


def _pr_context(pr_number: int) -> tuple[str, str, bool]:
    payload = _gh_json(f"repos/{REPO}/pulls/{pr_number}")
    title = str(payload.get("title") or "").strip()
    body = str(payload.get("body") or "").strip()
    parts = ["--- pull request context (author-provided, untrusted) ---"]
    if title:
        parts.append(f"title: {title[:500]}")
    if body:
        parts.append(f"body:\n{body[:7_500]}")
    return "\n".join(parts) if len(parts) > 1 else "", title, bool(body)


def _file_context(checkout: Path, changed_files: list[str]) -> tuple[str, dict[str, str]]:
    contents = {}
    parts = []
    for relative in changed_files:
        path = checkout / relative
        if not path.is_file():
            continue
        text = path.read_text(errors="replace")
        contents[relative] = text
        lowered = relative.lower()
        label = (
            "test file content"
            if "/test" in lowered
            or lowered.startswith("test_")
            or lowered.endswith(("_test.py", ".test.js", ".spec.js", ".test.ts", ".spec.ts"))
            else "full content"
        )
        parts.append(f"--- {label}: {relative} ---\n{text}")
    return "\n\n".join(parts), contents


def _run_case(
    case: dict,
    model: str,
    repeats: int,
    base_url: str,
    max_output_tokens: int,
    aletheore_root: Path,
) -> list[dict]:
    github_app = aletheore_root / "github-app"
    source = aletheore_root / "src"
    sys.path[:0] = [str(github_app), str(source)]
    from aletheore import evidence
    from scan_worker import flash_review

    changed_files, diff_patches = _case_inputs(case["pr_number"])
    pr_context, pr_title, pr_body_present = _pr_context(case["pr_number"])
    diff_text = "\n\n".join(f"--- {path} ---\n{patch}" for path, patch in diff_patches)
    records = []

    for repeat in range(repeats):
        with tempfile.TemporaryDirectory(prefix=f"aletheore-pr-ab-{case['case_id']}-") as temp:
            repo_dir = Path(temp) / "repo"
            checkout = Path(temp) / "checkout"
            checkout.mkdir()
            _git_clone_pr(repo_dir, case["pr_number"], checkout)
            os.environ["ALETHEORE_DISABLE_LOCAL_SCAN_CACHE"] = "1"
            scan = evidence.scan_repository(
                checkout,
                check_vulnerabilities=False,
                scan_git_history=False,
                check_licenses=False,
                map_endpoints=False,
                map_schema=False,
            )
            file_context, file_contents = _file_context(checkout, changed_files)
            code_context = flash_review.build_code_evidence_context(scan, changed_files)
            impact_context = flash_review.build_change_impact_context(diff_text)
            if impact_context:
                code_context = "\n\n".join(
                    part for part in (code_context, impact_context) if part
                )

            def fetch_symbol_source(path: str, start_line: int, end_line: int) -> str | None:
                target = checkout / path
                if not target.is_file():
                    return None
                return "\n".join(target.read_text(errors="replace").splitlines()[start_line - 1 : end_line])

            referenced = flash_review.build_referenced_symbol_context(
                scan, changed_files, diff_text, fetch_symbol_source
            )

            for arm, extra_context in (
                (OLLAMA_BASELINE, ""),
                (OLLAMA_ALETHEORE_CONTEXT, f"{code_context}\n\n{referenced}"),
            ):
                capture = {}
                original_factory = flash_review.writing_adapter_for
                flash_review.writing_adapter_for = lambda *args, **kwargs: _OllamaAdapter(
                    base_url, model, repeat, max_output_tokens, capture
                )
                grounding = {}
                try:
                    findings = flash_review.review_diff(
                        diff_text,
                        file_context=file_context,
                        code_evidence_context=extra_context if arm == OLLAMA_ALETHEORE_CONTEXT else "",
                        referenced_symbol_context="",
                        pr_context=pr_context,
                        cache_lookup=None,
                        cache_write=None,
                        model_used=model,
                        file_contents=file_contents,
                        diff_patches=diff_patches,
                        on_grounding_result=grounding.update,
                    )
                finally:
                    flash_review.writing_adapter_for = original_factory
                records.append(
                    {
                        "case_id": case["case_id"],
                        "pr_number": case["pr_number"],
                        "repeat": repeat,
                        "seed": repeat,
                        "arm": arm,
                        "model": model,
                        "temperature": 0,
                        "max_output_tokens": max_output_tokens,
                        "changed_files": changed_files,
                        "pr_title": pr_title,
                        "pr_body_present": pr_body_present,
                        "context_lengths": {
                            "file_context": len(file_context),
                            "code_evidence_context": len(extra_context),
                            "referenced_symbol_context": len(referenced),
                            "pr_context": len(pr_context),
                        },
                        "ground_truth": json.loads(
                            (Path(__file__).with_name("ground_truth.json")).read_text()
                        )["cases"].get(case["case_id"]),
                        "proposed_count": grounding.get("proposed"),
                        "grounded_count": grounding.get("kept", len(findings)),
                        "findings": findings,
                        "ollama_response_metadata": capture,
                    }
                )
    return records


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--aletheore-root", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--max-output-tokens", type=int, default=1024)
    parser.add_argument("--case-id", help="run only one manifest case for a smoke test")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cases = json.loads((Path(__file__).with_name("cases.json")).read_text())
    if args.case_id:
        cases = [case for case in cases if case["case_id"] == args.case_id]
        if not cases:
            parser.error(f"unknown case id: {args.case_id}")
    ground_truth = json.loads((Path(__file__).with_name("ground_truth.json")).read_text())
    results = []
    for case in cases:
        results.extend(
            _run_case(
                case,
                args.model,
                args.repeats,
                args.ollama_url,
                args.max_output_tokens,
                args.aletheore_root,
            )
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            {
                "experiment": {
                    "model": args.model,
                    "ollama_url": args.ollama_url,
                    "repeats": args.repeats,
                    "temperature": 0,
                    "cache": "disabled",
                    "max_output_tokens": args.max_output_tokens,
                    "aletheore_root": str(args.aletheore_root),
                },
                "ground_truth_version": ground_truth["version"],
                "cases": cases,
                "results": results,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
