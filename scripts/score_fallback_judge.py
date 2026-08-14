"""Re-derives every number the README's fallback sections publish, from the
saved rows in results/. No API key, no network.

    python3 scripts/score_fallback_judge.py

Deliberately also prints the pooled 22-file figure the README refuses to
headline, so the reason for refusing it is checkable rather than asserted:
RepoWise scores 0.0 on all 15 config/CI/docs files because it reports them as
out of scope, and averaging those zeros into the quality gap measures coverage,
not usefulness.
"""
import json
import os
import statistics

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(name):
    with open(os.path.join(ROOT, "results", name)) as fh:
        return json.load(fh)


def summarise(repeats, label):
    gaps = [r["gap"] for r in repeats]
    fb = [r["fallback_mean"] for r in repeats]
    rw = [r["repowise_mean"] for r in repeats]
    n = len(repeats[0]["rows"])
    print(f"\n{label}  (n={n} files, {len(repeats)} repeats, 0-3, order-swapped)")
    for r in repeats:
        print(f"  repeat {r['repeat']}: fallback={r['fallback_mean']:.3f} "
              f"repowise={r['repowise_mean']:.3f} gap={r['gap']:+.3f}")
    print(f"  fallback {statistics.mean(fb):.3f}   repowise {statistics.mean(rw):.3f}   "
          f"gap {statistics.mean(gaps):+.3f}   spread {max(gaps) - min(gaps):.3f}")
    return statistics.mean(gaps)


def main():
    seven = load("fallback_vs_repowise_scores_7files.json")
    fifteen = load("fallback_vs_repowise_scores_15files.json")

    print("=" * 72)
    print("HEADLINE — files where both systems return substantive material")
    summarise(seven, "7 scanner-backed files")

    print("\n  per-file (repeat 1):")
    for row in seven[0]["rows"]:
        winner = "fallback" if row["fallback"] > row["repowise"] else (
            "REPOWISE" if row["repowise"] > row["fallback"] else "tie")
        print(f"    {row['file']:<44} fb={row['fallback']:.1f} rw={row['repowise']:.1f}  {winner}")

    print("\n" + "=" * 72)
    print("COVERAGE — not a quality result; see README")
    summarise(fifteen, "15 config/CI/docs files")
    zeros = sum(1 for r in fifteen[0]["rows"] if r["repowise"] == 0.0)
    print(f"  RepoWise scored 0.0 on {zeros}/{len(fifteen[0]['rows'])} of these "
          f"(reported out of scope, not retrieved and wrong)")

    print("\n" + "=" * 72)
    print("NOT PUBLISHED — pooling the two sets, shown so the refusal is checkable")
    pooled = []
    for r7, r15 in zip(seven, fifteen):
        rows = r7["rows"] + r15["rows"]
        fb = statistics.mean(x["fallback"] for x in rows)
        rw = statistics.mean(x["repowise"] for x in rows)
        pooled.append(fb - rw)
        print(f"  repeat {r7['repeat']}: fallback={fb:.3f} repowise={rw:.3f} gap={fb - rw:+.3f}")
    print(f"  pooled gap {statistics.mean(pooled):+.3f} — driven by the 15 zeros above, "
          f"not by usefulness.")

    print("\n" + "=" * 72)
    print("COVERAGE OF CHANGED FILES — flask, last 30 non-merge commits")
    cov = load("airview_fallback_coverage.json")["commits"]
    page_files = sum(c["files_from_page"] for c in cov)
    fb_files = sum(c["files_from_fallback"] for c in cov)
    total_files = sum(c["files_changed"] for c in cov)
    all_page = sum(1 for c in cov if c["files_from_page"] == c["files_changed"])
    any_page = sum(1 for c in cov if c["files_from_page"] > 0)
    all_cov = sum(1 for c in cov
                  if c["files_from_page"] + c["files_from_fallback"] == c["files_changed"])
    print(f"  commits: {len(cov)}    changed files: {total_files}")
    print(f"  pages alone:      {all_page}/{len(cov)} commits fully covered, "
          f"{page_files}/{total_files} files")
    print(f"  pages + fallback: {all_cov}/{len(cov)} commits fully covered, "
          f"{page_files + fb_files}/{total_files} files")
    print(f"  commits with a page for at least one changed file: {any_page}/{len(cov)}")


if __name__ == "__main__":
    main()
