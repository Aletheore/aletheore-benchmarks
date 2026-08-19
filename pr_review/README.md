# Ollama PR Review A/B Experiment

This experiment measures whether Aletheore's deterministic evidence and symbol context improve PR-review results when the same local Ollama model is used in both arms.

It is deliberately separate from the hosted Luna/Terra result. The two arms are:

- `ollama_baseline`: Ollama receives the PR diff, changed-file contents, and the PR's title/body when available.
- `ollama_aletheore_context`: Ollama receives the same inputs plus Aletheore's deterministic code evidence, referenced-symbol context, and deterministic change-impact signals. Both arms use the same production finding parser and grounding validator so the comparison isolates context value rather than output handling.

The initial corpus is the eight open `xref2` PRs in `Aletheore/pr-review-benchmark-sandbox`, PRs 59-66. Results are not valid until every case has the requested repeat count, the model name and parameters are recorded, and no cache or infrastructure failure is present.

## Run

From this repository:

```bash
python3 pr_review/run_ollama_ab.py \
  --aletheore-root /path/to/Aletheore \
  --model <exact-ollama-model-name> \
  --repeats 3 \
  --output results/pr_review_ollama_ab.json
```

The runner fetches the eight PR heads and diffs from GitHub, creates an isolated checkout per case, runs the deterministic scan without network checks or scan caching, and writes one record per case, repeat, and arm. It never writes results into the source repository.

The default local output budget is 1024 tokens. Hosted Flash Review currently does not pass an explicit completion-token cap to its OpenAI-compatible adapter, so the provider/model default is not equivalent to the old 256-token benchmark run. The run records the explicit Ollama budget.

`ground_truth.json` is the committed human-reviewed case manifest. It is used for paired evaluation and is not sent to either model arm.

The treatment is not a claim about the hosted production deployment. It measures the narrow product contribution of Aletheore evidence/context and validation on the same weak model. A separate hosted run may be reported alongside it only with its actual deployed model, commit, cache status, and completion state.

## Required publication fields

Publish raw records only after review. The report must include the exact model, Ollama version, Aletheore commit, prompt source, repeat count, cache status, failures, and paired per-case results. Do not convert a failed or missing arm into a zero finding.

---

## Experiment 2: mixed-repo corpus + context-compaction A/B

Two questions this experiment was built to answer, both raised while designing a free tier bound by a
tight tokens-per-minute quota (Groq's free tier: 6,000 TPM):

1. Does Aletheore's deterministic evidence context (blast radius, referenced symbols, change-impact
   signals) still help on **real, mature repositories** rather than the small synthetic `xref2` sandbox
   above, which was too small to meaningfully exercise blast-radius resolution?
2. If the full raw file-content dump is dropped from the prompt - keeping only the diff and Aletheore's
   own evidence - how much does that cost in review quality, against how much it saves in tokens and
   reliability?

### Corpus

50 cases in `benchmarks/pr-review-benchmark/cases/` in the main `Aletheore/Aletheore` repository (not
this one): 25 hand-picked real-world bug fixes/regressions across Python, JS, Go, and Java (flask,
requests, click, axios, express, lodash, cobra, gin, gorilla-mux, urfave-cli, gson, junit4,
commons-lang), plus 25 SWE-bench-derived Python cases (django, astropy, scikit-learn, matplotlib,
sphinx, sympy, xarray). By `ground_truth.yaml` category: 40 `real_bug_fix`, 6 `injected_bug`, 4
`clean` (no real bug - used to check false-positive rate, not recall).

### Arms

Three arms, same model, same diff, same production finding parser and grounding validator:

- `ollama_baseline`: diff + full raw content of every changed file, no Aletheore evidence.
- `ollama_aletheore_context`: diff + full raw file content + Aletheore's deterministic evidence
  (code-evidence context, change-impact signals, blast-radius context).
- `ollama_aletheore_compact`: diff + the same Aletheore evidence as above, **no raw file content at
  all**.

### Required fields for this run

- Model: `llama3.1:8b`, Ollama-quantized `Q4_K_M`, served by Ollama `0.32.14`.
- `num_ctx`: `16384` explicit (Ollama's own default is 4096 and silently truncates anything larger
  with no error - this was caught mid-experiment; see "Known issue found and fixed" below).
- Aletheore commit: [`4d0588d`](https://github.com/Aletheore/Aletheore/commit/4d0588dd) (`master`,
  immediately after PR #282 - the blast-radius feature this run exists to validate). Neither
  `flash_review.py` nor `detect.py` changed again until PR #283/#284, which came after this run's
  results were already captured, so this commit is exact for the whole run.
- Repeats: 3 per (case, arm). `ALETHEORE_DISABLE_LOCAL_SCAN_CACHE=1` - no scan caching.
- Total: 450 records (50 cases x 3 repeats x 3 arms).
- Failures: 16 `TimeoutError`s, all on arms carrying full raw file content -
  `ollama_baseline`: 14/150, `ollama_aletheore_context`: 2/150, `ollama_aletheore_compact`: **0/150**.
  Not fully explained by prompt size alone (one timeout case had only a ~1,900-char prompt), but the
  aggregate correlation between carrying full file dumps and timing out is real. Failed calls are
  recorded as errors, never converted to zero findings.
- Raw results: `results/mixed_repo_compaction_ab.json`. Harness: `run_mixed_repo_ab.py`.

### Known issue found and fixed mid-experiment

The first run of this harness silently truncated every prompt over ~4096 tokens (Ollama's own
default `num_ctx`, which the harness wasn't setting explicitly) with no error - meaning the
full-context arm was almost certainly getting silently truncated on larger files. Caught before
trusting any output from that run; fixed by measuring the real context-size distribution across all
50 cases first (full-context max 44,760 chars / ~11,190 tokens, median 15,212 chars; compact-context
max 10,521 chars, median 1,480 chars), then setting `num_ctx=16384` - comfortable headroom over the
real observed maximum. The run reported here is the corrected one.

### Context size (measured, not estimated)

| | median | p90 | max |
|---|---|---|---|
| full context (file dump + diff + evidence) | 15,212 chars (~3,800 tok) | 35,390 chars | 44,760 chars |
| compact context (diff + evidence only) | 1,480 chars (~370 tok) | 4,422 chars | 10,521 chars |

**Compact context is ~10.3x smaller than a raw file-dump diff at the median** (15,212 -> 1,480
chars), which is the number that actually determines whether a review fits inside a tight
tokens-per-minute quota (e.g. Groq's free-tier 6,000 TPM) at all - not the max case, which any
provider's rate limit has to be sized against regardless of arm.

### Blind LLM judge

Raw finding counts and even careful manual reading are not treated as sufficient on their own - this
project has a documented history of line-proximity-only scoring counting confidently wrong findings
as hits. A blind LLM judge (`deepseek-v4-pro`, reasoning disabled) was used as an independent check,
scoring each arm's findings against `ground_truth.yaml` with anonymized labels (never told which arm
produced which output), on `recall` (hit/partial/miss), `false_positives`, and `actionability` (1-5).
Run twice per (case, arm) to check agreement, since this same judge model has a documented noise floor
(drifts 0.2-0.375 on identical input in prior AIRview scoring work).

**A real methodology bug was found and fixed, not hidden:** the first judge design asked for all 2-3
arms to be scored in one call. The judge silently omitted one of the requested labels from its JSON
response in 53 of 97 (case, run) instances - meaning the first aggregate numbers were built from
inconsistent, non-overlapping subsets per arm and were not trustworthy (they showed full-context
beating compact; this did not hold up). Redesigned to score exactly one arm per call, which removes
the omission failure mode entirely rather than working around it - the corrected run scored all
129/129 possible (case, arm) pairs in both runs, with zero omissions.

**Judge agreement across the two runs: 79.8% (103/129)**, consistent with the known noise floor -
disagreements are almost entirely adjacent-category drift (miss&harr;partial, hit&harr;partial), with
only 3 direct hit&harr;miss flips (all on the compact arm, all SWE-bench cases - small n, noted rather
than ignored).

**Results** (46 `real_bug_fix`/`injected_bug` cases, `clean` cases scored separately for false
positives):

| arm | recall score | hit / partial / miss | avg false positives per call | avg actionability |
|---|---|---|---|---|
| `ollama_aletheore_compact` | **0.375** | 22 / 25 / 45 | **0.79** | 2.53 |
| `ollama_aletheore_context` | 0.290 | 21 / 9 / 58 | 0.45 | 2.16 |
| `ollama_baseline` | 0.301 | 18 / 11 / 49 | 0.65 | 2.28 |

On the 4 `clean` cases: no arm invented a fictional bug, but all three flagged the cosmetic change
itself (a typo fix, a docstring correction) as a "finding" rather than staying silent - a mild
false-positive pattern, roughly even across arms.

### Verdict

Dropping full file content and relying on Aletheore's own evidence context:

- **Real recall win**: +7.5 to +8.5 points over both other arms, larger than the judge's own noise
  band, corroborated independently by a full manual read of every unique finding text (not just
  line-matched) before the judge run existed.
- **Real reliability win**: 0/150 timeouts vs. 16/300 combined on the arms carrying full file dumps.
- **Real cost win**: ~10x smaller prompts (median), which is what makes a tight-TPM free tier viable
  at all.
- **Not a clean win**: compact also has the highest false-positive rate of the three arms (0.79 vs
  0.45-0.65). It's finding more real issues *and* generating more spurious ones alongside them. This
  is an open problem, not a resolved one - see below.

### Open work

**Update (2026-08-19): blast-radius false-positive fix validated - result is inconclusive, not a win.**
The fix described below (blast radius stating "no confirmed caller found among N of M checked"
instead of going silent, plus a system-prompt guardrail against unverifiable claims) was implemented,
unit-tested, and re-run against this same 50-case corpus (`results/mixed_repo_compaction_ab_fp_fix.json`,
448 records - 2 short of 450 due to isolated retry exhaustion, not systematic). The compact arm's
false-positive rate did **not** improve - it got worse, consistently, across three independent
measurements taken after the fix:

| measurement | recall | avg false positives |
|---|---|---|
| pre-fix (published above) | 0.375 | **0.79** |
| post-fix, full 224-record judge pass | 0.356 | 1.12 |
| post-fix, compact-only rerun, run 0 | 0.311 | 1.18 |
| post-fix, compact-only rerun, run 1 | 0.367 | 0.98 |
| **post-fix, compact-only rerun, combined** | 0.339 | **1.08** |

Taken at face value this looks like a regression. It is reported honestly as one, but with a real
caveat: the `ollama_baseline` arm - which the fix cannot touch at all, since it never sees Aletheore's
evidence context - moved by a similar magnitude in the same direction in the same rerun (recall
0.301->0.328, avg FP 0.65->0.79). A fix with zero mechanical path to affecting baseline correlating
with baseline moving anyway is a strong sign of judge-calibration drift between the pre-fix and
post-fix sessions, not a real code-caused effect - consistent with this judge's own documented noise
floor. All recall deltas here are within that floor; the FP deltas are larger and repeat three times,
so they are reported as real and unresolved, not dismissed - just not attributable to this specific
fix with confidence. **No conclusion is drawn about whether the fix helped, hurt, or did nothing** -
this needs a less noisy evaluation setup (a stronger, less variance-prone judge, or a much larger
n) before either claim is supportable. The fix's underlying logic remains correct as verified by unit
tests in `tests/test_flash_review.py` and is not reverted on the strength of this ambiguous result.

---

## Experiment 3 (v1): a real, previously-rejected production model - DeepSeek V4 Flash

Every arm above ran on a local Ollama model (`llama3.1:8b`) as a stand-in for a weak free-tier-caliber
model. This experiment instead re-tests a model with real production history: `deepseek-v4-flash` was
Aletheore's original PR-review model, replaced first by `deepseek-v4-pro` (quality), then by
`gpt-5.6-luna` (DeepSeek's announced price hike made staying DeepSeek-only a vendor-risk bet - see
`model_tiers.py`'s module docstring). The question this run asks: does Aletheore's evidence context
change that verdict, or was the rejection about the model itself?

### What's different from Experiment 2

- **Real API, not local inference.** `run_mixed_repo_ab.py` gained a `--provider deepseek` flag that
  builds an adapter with `aletheore.adapters.openai_compatible.OpenAICompatibleAdapter` - the exact
  class production's `model_tiers.writing_adapter_for` uses for its DeepSeek fallback path - pointed at
  the real `https://api.deepseek.com` endpoint. This is not an approximation of production behavior; it
  is the same adapter code production runs, so real per-call latency, real token accounting, and real
  failure modes are all genuine, not simulated.
- **Repeats: 1, not 3** (v1, hence the name - a full 3-repeat run is real future work, not done here).
  Real API latency made a 3-repeat pass impractical for a first read: an initial attempt at
  `--repeats 3` measured ~11 min/case average across the first 4 cases (real DeepSeek completions on
  the baseline arm ran into the tens of thousands of tokens - see below), projecting to ~9+ hours for
  all 50 cases. Switched to `--repeats 1` (~4.5 hours) to get a real first read before committing to
  the full run.
- **Known limitation, not yet applied here:** a separate part of this benchmark suite
  (`scripts/multi_repo.py`) already measured that disabling DeepSeek's reasoning mode
  (`extra_body={"thinking": {"type": "disabled"}}`) cuts output tokens by 87% and wall-clock time by
  6.2x on a real file-page prompt, with the output coming back slightly *longer*, not worse. This run's
  adapter does not apply that flag (reasoning left at its default, matching how
  `model_tiers.writing_adapter_for`'s DeepSeek fallback behaves unless `AIRVIEW_REASONING=off` is set) -
  so the completion-token/cost numbers below are the *unoptimized* case, and are real candidates for a
  v2 rerun.

### Real results (all 50 cases, 0 errors)

Token/timing data, `results/mixed_repo_deepseek_v4_flash_r1.json`:

| arm | avg prompt tokens | avg completion tokens | avg elapsed | avg findings |
|---|---|---|---|---|
| `ollama_aletheore_compact` | 2,483 | **13,235** | 108.0s | 0.74 |
| `ollama_aletheore_context` | 16,325 | 11,180 | 90.2s | 0.76 |
| `ollama_baseline` | 15,019 | 13,321 | 114.1s | 0.70 |

Compact still shrinks the *input* side by ~6x, same shape as Experiment 2. But completion tokens are
large across all three arms (11k-13k) almost independent of context strategy - this is DeepSeek V4
Flash's reasoning-mode verbosity, a model-level trait Aletheore's context shaping does not fix (see
the known limitation above - this is very likely fixable, just not applied in this v1 run). Real cost
at DeepSeek's published rates ($0.14/$0.28 per 1M): compact ~$0.0041/review, context ~$0.0054/review,
baseline ~$0.0058/review - compact still cheapest, but by ~25-30%, not the multiple seen against a
model whose completion tokens actually shrink with less context.

Blind judge (`deepseek-v4-pro`, same methodology as Experiment 2, 2 runs, 276/276 (case, arm, run)
triples scored with 0 missing after retry): **run-to-run agreement 90.6% (125/138)**, notably higher
than Experiment 2's 79.8% - a stronger model's outputs were more consistently gradeable.

| arm | recall score | avg false positives |
|---|---|---|
| `ollama_aletheore_compact` | **0.527** | 0.207 |
| `ollama_aletheore_context` | 0.522 | 0.217 |
| `ollama_baseline` | 0.457 | 0.185 |

### Verdict (v1)

- **The rejection wasn't fixed by Aletheore's context, but it also wasn't ignored by it.** Compact and
  context both beat baseline on recall by a real margin (~0.52-0.53 vs 0.457, ~14-15% relative) - the
  evidence layer adds real signal even on a materially stronger model than Experiment 2's, not just a
  weak one. That is real evidence against "the evidence layer has nothing to offer a competent model."
- **Compact ties context again** (0.527 vs 0.522, well inside noise) on a second, different, stronger
  model - the case for dropping raw file dumps in favor of Aletheore's evidence alone keeps holding up
  across model classes, not just on the original weak-model corpus.
- **False positives are dramatically lower than Experiment 2's llama3.1:8b numbers** (0.19-0.22 vs.
  0.79-1.2) - DeepSeek V4 Flash is verbose but not sloppy; token volume and hallucination rate turned
  out to be separate axes here, not the same thing.
- **Absolute recall ceiling is still only ~53%** even on the best arm and a real production-grade
  model - real room for improvement remains, just not evidence that the evidence layer specifically is
  the bottleneck relative to no evidence at all.
- **Not yet reflecting the reasoning-mode-disable optimization** already proven elsewhere in this repo
  (87% fewer tokens, 6.2x faster, no quality loss) - a real, low-risk v2 rerun candidate that would
  likely change the cost picture substantially without needing new data collection logic.

Raw results: `results/mixed_repo_deepseek_v4_flash_r1.json`, `results/blind_judge_deepseek_v4_flash_r1.json`.
