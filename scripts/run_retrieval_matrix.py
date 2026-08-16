"""Retrieval accuracy across every corpus and question set, in one pass.

Produces the raw per-question rows behind the "Locating code" table.
`score_retrieval_matrix.py` turns those rows into the published numbers with
no API key and no network, so every figure stays re-derivable offline - the
same discipline the rest of this repository follows.

The matrix below is the authoritative list, taken from the headers of
`results/embedder_comparison_openai_raw_0.8.9.txt` so a new run is directly
comparable to the published one. flask uses `location.json` rather than a
`flask.json`; gin, serde and flask have no vocabulary variant.

Usage:

    python3 scripts/run_retrieval_matrix.py --label jina
    python3 scripts/run_retrieval_matrix.py --label jina --only jq,fmt

Embedder selection is NOT monkeypatched here. `search_index` prefers the
hosted endpoint whenever a token resolves and falls back to local otherwise,
and since the query-provider fix it uses the same preference the index was
built with - which is the whole point of re-running this table. Control it by
whether `aletheore login` has been run, and record which one was used in the
label.
"""

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _bench  # noqa: E402

from aletheore.search_index import IndexNotFoundError, search_index  # noqa: E402

# (corpus, question-file stem). Order matches the published output.
MATRIX: list[tuple[str, str]] = [
    ("flask", "location"),
    ("gin", "gin"),
    ("serde", "serde"),
    ("slim", "slim"), ("slim", "slim_vocab"),
    ("guzzle", "guzzle"), ("guzzle", "guzzle_vocab"),
    ("jekyll", "jekyll"), ("jekyll", "jekyll_vocab"),
    ("zod", "zod"), ("zod", "zod_vocab"),
    ("gson", "gson"), ("gson", "gson_vocab"),
    ("axios", "axios"), ("axios", "axios_vocab"),
    ("jq", "jq"), ("jq", "jq_vocab"),
    ("fmt", "fmt"), ("fmt", "fmt_vocab"),
    ("automapper", "automapper"), ("automapper", "automapper_vocab"),
    ("thrift", "thrift"), ("thrift", "thrift_crosslang"),
]

TOP_K = 10


def ranked_files(repo: Path, question: str) -> tuple[list[str], float]:
    """Distinct file paths in rank order, plus how long the query took.

    De-duplicated by path: several chunks of one file can each hit, and a
    file that answers the question answers it once - counting it twice would
    inflate top-3 and top-5 for no reason.
    """
    start = time.perf_counter()
    hits = search_index(repo, question, k=TOP_K)
    elapsed = time.perf_counter() - start

    files: list[str] = []
    seen: set[str] = set()
    for hit in hits:
        path = hit.get("module_path")
        if path and path not in seen:
            seen.add(path)
            files.append(path)
    return files, elapsed


def run_pair(corpus: str, qset: str, repo: Path) -> list[dict] | None:
    questions_path = Path(_bench.ROOT) / "questions" / f"{qset}.json"
    if not questions_path.exists():
        print(f"  SKIP {corpus}/{qset}: no {questions_path.name}", file=sys.stderr)
        return None

    questions = json.loads(questions_path.read_text())
    rows = []
    for entry in questions:
        question = entry.get("question") or entry.get("q")
        files, elapsed = ranked_files(repo, question)
        rows.append({
            "id": entry["id"],
            "question": question,
            "ground_truth_files": entry.get("ground_truth_files") or entry.get("gt") or [],
            "ranked_files": files,
            "latency_s": round(elapsed, 4),
        })
    return rows


def summarise(rows: list[dict]) -> dict:
    n = len(rows) or 1

    def hits_at(k: int) -> int:
        return sum(1 for r in rows if any(f in r["ground_truth_files"] for f in r["ranked_files"][:k]))

    reciprocal = []
    for r in rows:
        rank = next(
            (i + 1 for i, f in enumerate(r["ranked_files"]) if f in r["ground_truth_files"]),
            None,
        )
        reciprocal.append(1.0 / rank if rank else 0.0)

    return {
        "n": len(rows),
        "top_1": hits_at(1), "top_3": hits_at(3), "top_5": hits_at(5),
        "mrr": statistics.mean(reciprocal) if rows else 0.0,
        "median_latency_ms": statistics.median(r["latency_s"] for r in rows) * 1000 if rows else 0.0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True,
                        help="embedder/run label, e.g. 'jina' - names the output file")
    parser.add_argument("--only", default="",
                        help="comma-separated corpus names to restrict the run to")
    args = parser.parse_args()

    only = {c.strip() for c in args.only.split(",") if c.strip()}
    corpora = {r["name"]: r for r in json.loads((Path(_bench.ROOT) / "corpora.json").read_text())["repos"]}

    output: dict[str, dict] = {}
    missing: list[str] = []

    for corpus, qset in MATRIX:
        if only and corpus not in only:
            continue
        repo = Path(_bench.repo_src(corpus))
        if not (repo / ".aletheore" / "index.lancedb").exists():
            if corpus not in missing:
                missing.append(corpus)
            continue

        print(f"  running {corpus}/{qset} ...", file=sys.stderr)
        try:
            rows = run_pair(corpus, qset, repo)
        except IndexNotFoundError:
            missing.append(corpus)
            continue
        if rows is None:
            continue
        output[f"{corpus}/{qset}"] = {"rows": rows, "summary": summarise(rows)}

    out_path = Path(_bench.ROOT) / "results" / f"retrieval_raw_{args.label}.json"
    out_path.write_text(json.dumps(output, indent=2))
    print(f"\nwrote {out_path} ({len(output)} of {len(MATRIX)} pairs)", file=sys.stderr)

    if missing:
        print(
            "\nNOT RUN - no index at "
            f"{_bench.repo_src('<corpus>')} for: {', '.join(sorted(set(missing)))}\n"
            "  clone at the pinned commit from corpora.json, then "
            "`aletheore scan .` and `aletheore index .` in each.",
            file=sys.stderr,
        )
        for name in sorted(set(missing)):
            repo = corpora.get(name)
            if repo:
                print(f"    {name}: {repo['url']} @ {repo['commit']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
