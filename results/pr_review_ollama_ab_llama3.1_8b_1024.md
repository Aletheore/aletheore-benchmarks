# Ollama PR-Review A/B: does Aletheore's context help a weak local model?

**Question:** given the *same* weak local model, does adding Aletheore's deterministic
evidence and referenced-symbol context to the review prompt change whether it finds the
real regression? This isolates the product's context contribution from the hosted model
choice — see `pr_review/README.md` for the full experimental design.

## Configuration (required publication fields)

| Field | Value |
|---|---|
| Model | `llama3.1:8b` (Ollama) |
| Ollama version | 0.32.11 (server) |
| Aletheore commit | `18a0900d924b1db8747358eb59706c75e8675d6f` |
| Prompt source | production `scan_worker.flash_review.review_diff`, via `pr_review/run_ollama_ab.py` |
| Temperature | 0 |
| Max output tokens | 1024 |
| Repeats per case, per arm | 3 |
| Cache | disabled |
| Corpus | 8 `xref2` cases, `Aletheore/pr-review-benchmark-sandbox` PRs 59–66 |
| Failures / infra errors | none |
| Raw records | `results/pr_review_ollama_ab.json` (48 records: 8 cases × 3 repeats × 2 arms) |

Both arms use the same weak model, the same production finding parser, and the same
grounding validator — the only difference is whether the prompt includes Aletheore's
deterministic code evidence and referenced-symbol context (`ollama_aletheore_context`) or
just the diff, changed-file contents, and PR title/body (`ollama_baseline`).

## Scoring note

The first pass at scoring this used line-proximity only (does a finding land within 8
lines of the ground-truth line) and produced a misleading result — baseline scored
24/24 "matched." Reading the actual finding text against the ground truth description
showed why: several of baseline's "matches" were confidently-worded findings about a
*different, wrong* issue that happened to land on the same line by coincidence (e.g. an
"unused variable" finding on the exact line where the real bug is a missed mutation).
Line proximity without content is not grounding — the scores below are from reading every
finding's actual text against the ground truth, not from line numbers alone.

## Per-case result (paired, 3 repeats each — output was consistent across all 3 repeats in
every case, so one representative line is shown per case)

| Case | Regression | `ollama_baseline` | `ollama_aletheore_context` |
|---|---|---|---|
| a | removed exception handler | Vague: "ErrorA caught but not re-raised" + an unrelated second finding | **Correct**: "try-except block for ErrorA removed, but op_one still raises ErrorA" |
| b | mutated input (missing defensive copy) | **Wrong**: "unused variable 'working'" | Silent (no finding) |
| c | extra retry-loop mutation | **Wrong**: "potential infinite loop if notify always returns True" | **Correct**: "retries op_three up to 3 times, but the referenced definition of op_three [mutates/raises]" |
| d | wrong exception type caught | **Correct**: "expected ErrorB, but caught FileNotFoundError" | **Correct**: identical finding |
| e | one-shot iterator consumed twice | **Wrong**/vague: "performance regression due to changed behavior of list()" | **Correct**: "consumes the iterator returned by op_five without checking if it can be consumed [again]" |
| f | shared mutable state under concurrency | **Wrong**: "ThreadPoolExecutor not properly closed, resource leak" | **Correct** (+1 extra, also-true-but-off-target resource-leak finding): "Helper instance is not thread-safe... shared across threads" |
| g | double scaling by 100 | **Wrong**: "the `ratio` variable is assigned but never used" | Silent (no finding) |
| h | mutation before logging | **Wrong**: "duplicate log.append call" (mischaracterizes the bug) | **Correct**, more precise: "handler documented not to mutate its argument, but op_eight's referenced definition shows it does" |

## Result

- **`ollama_baseline`: 1/8 cases correctly identified** (d). The other 7 are confident,
  plausible-sounding, generic code-review comments ("unused variable," "duplicate call,"
  "potential infinite loop," "resource leak") that do not describe the actual regression.
- **`ollama_aletheore_context`: 6/8 cases correctly identified** (a, c, d, e, f, h), **2/8
  silent** (b, g — no finding, not a wrong one), **0/8 confidently wrong**.

Giving the same weak model Aletheore's deterministic evidence didn't just improve wording —
it changed the model's *failure mode*. Without context, this model is usually confidently
wrong. With context, it's either right or silent. For a review tool, silence is the safer
failure: a wrong finding stated with confidence costs user trust in a way an absent finding
does not.

## Limitations

- 8 cases is a small corpus; this is a controlled, paired comparison on synthetic
  cross-file regressions, not a claim about broad real-world recall (see
  `benchmarks/pr-review-benchmark`'s own 25-case real-bug corpus and its
  `evaluate_semantic_checks.py` results for that separate, larger measurement — a different
  question: whether *deterministic checks alone*, with no model at all, catch a real bug).
- This measures the weak local model's own judgment given better context, not Aletheore's
  deterministic semantic checks directly — `run_ollama_ab.py` passes the referenced-symbol
  context into the model's prompt (via `code_evidence_context`) but not into
  `review_diff`'s own `referenced_symbol_context` parameter, so the 8 deterministic checks
  that need that parameter do not independently fire in this harness. What's measured here
  is purely "does a weak model reason better when handed Aletheore's evidence," which is
  the question this experiment was designed to isolate.
- Not a claim about the hosted production deployment, which uses a materially stronger
  model. A separate hosted run would need its own actual deployed model, commit, and cache
  status recorded alongside this one, not blended with it.
