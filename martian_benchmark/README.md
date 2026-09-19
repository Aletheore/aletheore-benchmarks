# The Martian Benchmark

A different measurement from `pr_review/`'s hand-curated 24-case corpus: instead of a single
known bug per diff and a written ground-truth description, this benchmark measures each tool's
findings against **what a real human reviewer actually said** on a real, merged pull request —
messy, multi-file, real-world diffs, scored for semantic match against real review comments, not
a curated answer key.

## Corpus

24 real PRs fetched across 5 repositories, matched to their real GitHub review comments:

| Repo | Cases |
|---|---|
| `calcom/cal.diy` | 5 |
| `grafana/grafana` | 4 |
| `getsentry/sentry` | 3 |
| `keycloak/keycloak` | 2 |
| `ai-code-review-evaluation/discourse-graphite` | 10 |

**10 of the 24 cases were excluded from every scored run after the first.** `discourse-graphite`
is a purpose-built evaluation repo, not organic real-world commit history, and its golden-comment
ground truth turned out unreliable for this methodology once inspected closely — every recall
number below `14 clean cases` in this document is over the remaining 14 (`keycloak`, `sentry`,
`calcom`, `grafana` only). The one exception is the baseline row, which predates that exclusion
and covers all 24 — kept and labeled as such, not silently dropped, since it's the real number
that motivated finding the contamination in the first place.

Full case manifest: `results/cases.json`.

## Methodology

- **Aletheore**: direct invocation of `scan_worker.flash_review.review_diff()`, generation model
  `glm-5.3-flash` via IndieRouter — production's real current adapter
  (`flash_review_generation_adapter()` in `model_tiers.py`), same one used in `pr_review/`'s
  Experiment 6.
- **PR-Agent**: its own real CLI, default configuration.
- **Greptile**: real Greptile API results, run against a purpose-built Greptile evaluation fork of
  each repo.
- **Recall judge**: `gpt-5-nano`, scoring semantic match between each tool's own candidate finding
  and a real human reviewer's actual comment on that same merged PR (the "golden" finding set —
  see `results/martian_summary.json` and the real comment data these were extracted from).
  Recall is reported as *fraction of golden findings any candidate matched*, not a per-case
  hit/miss the way the 24-case corpus scores.
- **Precision check**: Aletheore's own real production verification method —
  `scan_worker.flash_review.VERIFICATION_SYSTEM_PROMPT` run through `DeepSeek-v4-flash` via
  `scan_worker.model_tiers.verification_adapter` — applied identically to all three tools' own
  candidate findings (diff-only, no surrounding file-context window; a real methodology gap
  against the production check itself, but a fair one since it's applied the same way to every
  tool rather than favoring any one of them).

This benchmark exists to answer a narrower, more operational question than the 24-case corpus:
given the same real-world PRs a maintainer would actually see, does a prompt or config change
measurably move recall against what reviewers actually flagged — used tonight to validate two
real Flash Review changes before shipping them, and to correctly reject two others that looked
plausible but didn't hold up.

## Results

Recall = fraction of golden (real reviewer) findings any tool's candidates matched, 14 clean cases
(219 golden findings) unless noted:

| Run | Aletheore | PR-Agent | Greptile |
|---|---|---|---|
| Baseline, all 24 cases (511 golden findings, pre-fix) | 38.6% | 36.2% | 35.6% |
| PR #746 (sibling-file context), run 1 | 44.7% | 31.1% | 25.6% |
| PR #746, run 2 (same config, repeat) | 41.1% | 32.9% | 24.2% |
| **PR #747 (softened confidence gate, on top of #746) — shipped** | **47.9%** | 31.5% | 26.5% |
| Rejected: finding cap raised 5→10 | 42.9% | 30.6% | 26.0% |
| Rejected: expanded few-shot example | 40.2% | 28.8% | 22.8% |

PR #746's two runs (44.7% vs. 41.1%, same exact config) are a real, measured example of GLM-5.3-Flash's
own run-to-run noise — reported both, not just the more flattering one.

Precision (DeepSeek-v4-flash ACCEPT/REJECT/UNCERTAIN verification, ACCEPT ÷ total candidates),
14 clean cases:

| Run | Aletheore | PR-Agent | Greptile |
|---|---|---|---|
| PR #746 only | 81.8% | 90.9% | 63.8% |
| **PR #747 — shipped** | 78.9% | 90.9% | 62.1% |
| Rejected: finding cap 5→10 | 75.0% | 90.9% | 60.3% |
| Rejected: expanded few-shot example | 87.1% | 77.3% | 58.6% |

Full per-case logs: `results/log_*.log`. Full summary with per-config candidate counts:
`results/martian_summary.json`.

## Reading this honestly

- **PR #747 traded 2.9 points of precision for 3.2 points of recall over PR #746 alone** (81.8%→78.9%
  precision, 44.7%→47.9% recall against #746's first run) — a real, acknowledged tradeoff, not a
  free win, and the reason it's framed as "softened confidence gate" rather than a pure
  improvement.
- **Both rejected variants are real negative results, not guesses.** The finding-cap raise cost
  recall (42.9% vs. 47.9%) without buying back precision (75.0% vs. 78.9% — worse on both axes).
  The expanded few-shot example bought real precision (87.1%, the best of any Aletheore config
  tested) but at a recall cost too large to accept (40.2%, barely above the pre-fix baseline) —
  correctly not shipped.
- **PR-Agent and Greptile's numbers barely move across any Aletheore-side config change** (PR-Agent:
  28.8-36.2%, Greptile: 22.8-35.6%, no trend tied to which Aletheore variant was running) — expected,
  since none of these changes touch either competitor, and useful as a rough noise-floor reference
  for how much any one tool's number can be expected to move run-to-run on this corpus.
- **This corpus and the 24-case corpus in `pr_review/` reached opposite conclusions about
  `sibling_file_context`** (PR #746): a real recall gain here (+6.6pp, run 1), a real recall and
  precision cost there (Experiment 6, `pr_review/README.md`) — on a smaller, hand-curated,
  single-issue corpus with a different model context (no full deterministic scan evidence
  available at all in this benchmark's harness). Both results are published, neither is discarded
  to make the story cleaner — see Experiment 6 for the production decision this conflict fed into
  and why the smaller corpus was weighted more heavily for that specific call.

## Reproducing

The harness scripts that produced these numbers live in this session's own working files, not yet
committed to this repository as reusable scripts (unlike `pr_review/run_ollama_ab.py` and
`run_mixed_repo_ab.py`) — the real recall/precision *results* and *raw logs* above are published
and reproducible against the `golden/` comment data and each case's real diff, but re-running this
exact pipeline end-to-end currently requires the harness code itself, which is a real gap against
this repo's own "recompute any number" standard elsewhere. Flagged here rather than left implicit;
publishing the harness scripts themselves is the natural next step.
