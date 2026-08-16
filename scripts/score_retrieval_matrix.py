"""Re-derive the "Locating code" table from saved rows. No API key, no network.

    python3 scripts/score_retrieval_matrix.py results/retrieval_raw_jina.json

Emits exactly the format of `results/embedder_comparison_openai_raw_0.8.9.txt`,
so a new run diffs cleanly against the published one:

    === flask/location
      top-1: 20/32 =  62.5%
      top-3: 31/32 =  96.9%
      top-5: 32/32 = 100.0%
      MRR  : 0.794

Pass a second file to print a comparison instead, which is the actual question
a re-run is asked to answer - "did changing the embedder move retrieval?" -
rather than leaving two tables to be eyeballed side by side.
"""

import json
import statistics
import sys
from pathlib import Path


def summarise(rows: list[dict]) -> dict:
    def hits_at(k: int) -> int:
        return sum(
            1 for r in rows
            if any(f in r["ground_truth_files"] for f in r["ranked_files"][:k])
        )

    reciprocal = []
    for r in rows:
        rank = next(
            (i + 1 for i, f in enumerate(r["ranked_files"]) if f in r["ground_truth_files"]),
            None,
        )
        reciprocal.append(1.0 / rank if rank else 0.0)

    return {
        "n": len(rows),
        1: hits_at(1), 3: hits_at(3), 5: hits_at(5),
        "mrr": statistics.mean(reciprocal) if rows else 0.0,
    }


def load(path: str) -> dict[str, dict]:
    # Recomputed from the rows rather than trusting the stored summary, so a
    # scoring change applies to old runs too and a hand-edited summary cannot
    # silently survive.
    raw = json.loads(Path(path).read_text())
    return {key: summarise(value["rows"]) for key, value in raw.items()}


def print_table(scores: dict[str, dict]) -> None:
    for key, s in scores.items():
        print(f"=== {key}")
        for k in (1, 3, 5):
            print(f"  top-{k}: {s[k]}/{s['n']} = {100 * s[k] / s['n']:5.1f}%")
        print(f"  MRR  : {s['mrr']:.3f}")


def print_comparison(before: dict[str, dict], after: dict[str, dict],
                     before_name: str, after_name: str) -> None:
    shared = [k for k in after if k in before]
    print(f"{'corpus/qset':<26}{'top-1':>16}{'top-3':>16}{'MRR':>16}")
    print(f"{'':<26}{before_name + ' -> ' + after_name:>48}")
    print("-" * 74)

    deltas = {1: [], 3: [], "mrr": []}
    for key in shared:
        b, a = before[key], after[key]
        b1, a1 = 100 * b[1] / b["n"], 100 * a[1] / a["n"]
        b3, a3 = 100 * b[3] / b["n"], 100 * a[3] / a["n"]
        b_mrr, a_mrr = b["mrr"], a["mrr"]
        deltas[1].append(a1 - b1)
        deltas[3].append(a3 - b3)
        deltas["mrr"].append(a_mrr - b_mrr)

        cell_1 = f"{b1:.1f} -> {a1:.1f}"
        cell_3 = f"{b3:.1f} -> {a3:.1f}"
        cell_mrr = f"{b_mrr:.3f} -> {a_mrr:.3f}"
        print(f"{key:<26}{cell_1:>16}{cell_3:>16}{cell_mrr:>16}")

    mean_1 = f"{statistics.mean(deltas[1]):+.1f}pp"
    mean_3 = f"{statistics.mean(deltas[3]):+.1f}pp"
    mean_mrr = f"{statistics.mean(deltas['mrr']):+.3f}"
    print("-" * 74)
    print(f"{'mean delta':<26}{mean_1:>16}{mean_3:>16}{mean_mrr:>16}")

    only_after = [k for k in after if k not in before]
    only_before = [k for k in before if k not in after]
    if only_after or only_before:
        print()
        if only_after:
            print(f"  in {after_name} only: {', '.join(only_after)}")
        if only_before:
            print(f"  in {before_name} only: {', '.join(only_before)}")
        print("  Reported as coverage, not folded into the mean - averaging a pair")
        print("  only one run covers would compare it against nothing.")


def main() -> int:
    if len(sys.argv) == 2:
        print_table(load(sys.argv[1]))
        return 0
    if len(sys.argv) == 3:
        before_path, after_path = sys.argv[1], sys.argv[2]
        print_comparison(
            load(before_path), load(after_path),
            Path(before_path).stem.replace("retrieval_raw_", ""),
            Path(after_path).stem.replace("retrieval_raw_", ""),
        )
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
