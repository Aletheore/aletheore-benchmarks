"""Ollama-baseline versus Ollama+Aletheore-context A/B, run against the
mixed real-world/swebench corpus in benchmarks/pr-review-benchmark/cases
(50 cases spanning Python, JS, Go, and Java repos - flask, requests,
click, axios, express, lodash, cobra, gin, gorilla-mux, urfave-cli, gson,
junit4, commons-lang, django, astropy, scikit-learn, matplotlib) instead
of the single synthetic sandbox repo run_ollama_ab.py uses.

Unlike run_ollama_ab.py, the Aletheore-context arm here also includes
build_blast_radius_context - real confirmed callers of the changed
symbol elsewhere in the (real, mature) repo - which the synthetic sandbox
repo was too small to meaningfully exercise."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

OLLAMA_BASELINE = "ollama_baseline"
OLLAMA_ALETHEORE_CONTEXT = "ollama_aletheore_context"
OLLAMA_ALETHEORE_COMPACT = "ollama_aletheore_compact"


def _load_cases(bench_root: Path) -> list[Path]:
    cases_dir = bench_root / "cases"
    return sorted(p for p in cases_dir.iterdir() if p.is_dir())


def _deepseek_adapter(model: str, capture: dict):
    # Reuses the exact same adapter class production Flash Review builds
    # DeepSeek adapters with (model_tiers.writing_adapter_for's fallback
    # path) rather than a parallel HTTP client, so this genuinely tests
    # what production would send/receive, not an approximation of it.
    from aletheore.adapters.openai_compatible import OpenAICompatibleAdapter

    def _on_usage(prompt_tokens: int, completion_tokens: int) -> None:
        # Field names match Ollama's response schema on purpose - every
        # downstream consumer of these records (blind_judge.py, this
        # project's analysis scripts) reads "prompt_eval_count"/
        # "eval_count" off ollama_response_metadata regardless of which
        # provider actually served the request.
        capture["prompt_eval_count"] = prompt_tokens
        capture["eval_count"] = completion_tokens

    return OpenAICompatibleAdapter(
        name="DeepSeek",
        base_url="https://api.deepseek.com",
        api_key_env_var="DEEPSEEK_API_KEY",
        model=model,
        supports_tool_choice=False,
        on_usage=_on_usage,
    )


def _run_case(
    case_dir: Path,
    model: str,
    repeats: int,
    base_url: str,
    max_output_tokens: int,
    aletheore_root: Path,
    bench_root: Path,
    provider: str = "ollama",
) -> list[dict]:
    from run_ollama_ab import _OllamaAdapter  # local import: needs sys.path set up first (see main())

    from scripts.build_case_repo import prepare_case_checkout
    from scripts.cases import load_case
    from scripts.evaluate_semantic_checks import (
        _changed_files_from_diff,
        git_diff_to_review_format,
    )

    from aletheore import evidence
    from scan_worker import flash_review

    case = load_case(case_dir)
    case_id = case["case_id"]
    raw_diff = case["diff_path"].read_text()
    diff_text = git_diff_to_review_format(raw_diff)
    changed_files = _changed_files_from_diff(raw_diff)
    ground_truth = case["ground_truth"]
    records: list[dict] = []

    for repeat in range(repeats):
        with tempfile.TemporaryDirectory(prefix=f"aletheore-mixed-ab-{case_id}-") as temp:
            try:
                checkout = prepare_case_checkout(case["repo"], case["diff_path"], Path(temp))
            except RuntimeError as exc:
                records.append(
                    {
                        "case_id": case_id,
                        "repeat": repeat,
                        "arm": "checkout_failed",
                        "error": str(exc),
                    }
                )
                continue

            os.environ["ALETHEORE_DISABLE_LOCAL_SCAN_CACHE"] = "1"
            scan = evidence.scan_repository(
                checkout,
                check_vulnerabilities=False,
                scan_git_history=False,
                check_licenses=False,
                map_endpoints=False,
                map_schema=False,
            )

            file_contents: dict[str, str] = {}
            file_parts = []
            for relative in changed_files:
                path = checkout / relative
                if not path.is_file():
                    continue
                text = path.read_text(errors="replace")
                file_contents[relative] = text
                file_parts.append(f"--- full content: {relative} ---\n{text}")
            file_context = "\n\n".join(file_parts)

            code_context = flash_review.build_code_evidence_context(scan, changed_files)
            impact_context = flash_review.build_change_impact_context(diff_text)

            def fetch_symbol_source(path: str, start_line: int, end_line: int, _checkout=checkout) -> str | None:
                target = _checkout / path
                if not target.is_file():
                    return None
                return "\n".join(target.read_text(errors="replace").splitlines()[start_line - 1 : end_line])

            referenced = flash_review.build_referenced_symbol_context(
                scan, changed_files, diff_text, fetch_symbol_source
            )

            def fetch_file_content(path: str, _checkout=checkout) -> str | None:
                target = _checkout / path
                if not target.is_file():
                    return None
                return target.read_text(errors="replace")

            blast_context = flash_review.build_blast_radius_context(
                scan, changed_files, diff_text, fetch_file_content
            )

            aletheore_context = "\n\n".join(
                part for part in (code_context, impact_context, referenced, blast_context) if part
            )

            for arm, arm_file_context, extra_context in (
                (OLLAMA_BASELINE, file_context, ""),
                (OLLAMA_ALETHEORE_CONTEXT, file_context, aletheore_context),
                # Same deterministic evidence (diff findings, referenced symbols,
                # blast radius) as the arm above, but with the full raw file
                # dumps dropped - file_context is typically the largest single
                # component of the prompt, and this arm isolates what full
                # file content actually buys over the diff + evidence alone.
                # This is the shape a free tier bound by a tight tokens-per-
                # minute quota (e.g. Groq's free tier) would realistically use.
                (OLLAMA_ALETHEORE_COMPACT, "", aletheore_context),
            ):
                capture: dict = {}
                original_factory = flash_review.writing_adapter_for
                if provider == "deepseek":
                    flash_review.writing_adapter_for = lambda *a, **kw: _deepseek_adapter(model, capture)
                else:
                    flash_review.writing_adapter_for = lambda *a, **kw: _OllamaAdapter(
                        base_url, model, repeat, max_output_tokens, capture
                    )
                grounding: dict = {}
                started = time.monotonic()
                try:
                    findings = flash_review.review_diff(
                        diff_text,
                        file_context=arm_file_context,
                        code_evidence_context=extra_context,
                        referenced_symbol_context="",
                        pr_context="",
                        cache_lookup=None,
                        cache_write=None,
                        model_used=model,
                        file_contents=file_contents,
                        diff_patches=None,
                        on_grounding_result=grounding.update,
                    )
                    error = None
                except Exception as exc:  # noqa: BLE001 - long unattended run, one bad case must not kill it
                    findings = []
                    error = f"{type(exc).__name__}: {exc}"
                finally:
                    flash_review.writing_adapter_for = original_factory

                records.append(
                    {
                        "case_id": case_id,
                        "repeat": repeat,
                        "seed": repeat,
                        "arm": arm,
                        "model": model,
                        "language": ground_truth.get("language"),
                        "category": ground_truth.get("category"),
                        "changed_files": changed_files,
                        "context_lengths": {
                            "file_context": len(arm_file_context),
                            "code_evidence_context": len(extra_context),
                            "blast_radius_included": bool(blast_context) and arm != OLLAMA_BASELINE,
                        },
                        "ground_truth": ground_truth,
                        "proposed_count": grounding.get("proposed"),
                        "grounded_count": grounding.get("kept", len(findings)),
                        "findings": findings,
                        "error": error,
                        "elapsed_seconds": time.monotonic() - started,
                        "ollama_response_metadata": capture,
                    }
                )
    return records


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--aletheore-root", type=Path, required=True)
    parser.add_argument("--bench-root", type=Path, required=True)
    parser.add_argument("--model", default="llama3.1:8b")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument(
        "--provider", choices=["ollama", "deepseek"], default="ollama",
        help="ollama calls a local Ollama server; deepseek calls the real DeepSeek API "
        "(needs DEEPSEEK_API_KEY in the environment) via the same adapter class production uses.",
    )
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--max-output-tokens", type=int, default=1024)
    parser.add_argument("--case-id", help="run only one case dir name for a smoke test")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    sys.path[:0] = [
        str(Path(__file__).parent),
        str(args.aletheore_root / "github-app"),
        str(args.aletheore_root / "src"),
        str(args.bench_root),
    ]

    cases = _load_cases(args.bench_root)
    if args.case_id:
        cases = [c for c in cases if c.name == args.case_id]
        if not cases:
            parser.error(f"unknown case id: {args.case_id}")
    args.output.parent.mkdir(parents=True, exist_ok=True)

    # Resume automatically rather than requiring an explicit flag: a case is
    # only ever appended to --output after _run_case returns for it (see the
    # write below), so any case_id present in an existing output file is
    # genuinely complete, never partial - a killed/restarted run can safely
    # skip every case_id already there instead of redoing real work.
    all_records: list[dict] = []
    already_done: set[str] = set()
    if args.output.exists():
        try:
            all_records = json.loads(args.output.read_text())
            already_done = {r["case_id"] for r in all_records}
            if already_done:
                print(f"resuming: {len(already_done)} case(s) already complete in {args.output}", flush=True)
        except (json.JSONDecodeError, KeyError) as exc:
            print(f"could not resume from {args.output} ({type(exc).__name__}: {exc}) - starting fresh", flush=True)
            all_records = []
            already_done = set()

    remaining = [c for c in cases if c.name not in already_done]
    for i, case_dir in enumerate(remaining, 1):
        print(f"[{i}/{len(remaining)}, {len(already_done) + i}/{len(cases)} overall] {case_dir.name}", flush=True)
        try:
            records = _run_case(
                case_dir,
                args.model,
                args.repeats,
                args.ollama_url,
                args.max_output_tokens,
                args.aletheore_root,
                args.bench_root,
                provider=args.provider,
            )
        except Exception as exc:  # noqa: BLE001 - one broken case must not kill the whole overnight run
            print(f"  CASE FAILED: {type(exc).__name__}: {exc}", flush=True)
            records = [{"case_id": case_dir.name, "arm": "case_failed", "error": f"{type(exc).__name__}: {exc}"}]
        all_records.extend(records)
        # Flush progress after every case, not just at the end - a 50-case
        # x 3-repeat x 2-arm overnight run must survive being interrupted
        # partway through without losing everything already computed.
        args.output.write_text(json.dumps(all_records, indent=2))

    print(f"done: {len(all_records)} records -> {args.output}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
