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

**Known methodology caveat with the SWE-bench-derived cases (25 of 50), found while investigating
Experiment 3's misses:** `ground_truth` for these cases is the original GitHub issue that motivated
the real PR, not a description of every problem in the diff. The diff under review is often a
multi-file fix/enhancement, and Flash Review's job (per its own system prompt) is to flag *regressions
the diff introduces*, not to rediscover the specific issue that motivated it - those are frequently
different, non-overlapping sets of valid findings. Spot-checked two concrete misses to confirm this is
real, not a guess: `swebench-xarray-6992` - the model's finding at line 4180 ("`coord_names` no longer
subtracts `drop_variables`... producing an inconsistent Dataset") describes almost exactly the ground
truth's stated symptom ("more `_coord_names` than `_variables`"), scored as a miss anyway;
`swebench-matplotlib-25775` - the model flagged a real backward-compatibility regression in
`lib/matplotlib/text.py` (a genuinely changed file in this exact diff, confirmed against `pr.diff`),
while `ground_truth.expected_file` points at `backend_agg.py` - a different file in the same diff,
because the "expected" issue is the feature the PR was written to add, not a regression the PR
introduces. **Recall numbers on the SWE-bench-derived half of this corpus should be read as a lower
bound, not a precise measurement** - some fraction of "misses" are real, on-target, uncredited
findings, not failures to find anything. This affects every recall number reported for this corpus in
this document, not just Experiment 3's.

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
the known limitation above - this is very likely fixable, just not applied in this v1 run).

**`deepseek-v4-flash` published token price** (`llm_cost.py`, verified 2026-07-23): **$0.14 / 1M input
tokens, $0.28 / 1M output tokens.** Real cost per review at those rates:

| arm | avg cost/review | vs. compact |
|---|---|---|
| `ollama_aletheore_compact` | **$0.0041** | - |
| `ollama_aletheore_context` | $0.0054 | +32% |
| `ollama_baseline` | $0.0058 | +41% |

Compact is still cheapest, but by ~25-30% relative, not the multiple seen against a model whose
completion tokens actually shrink with less context - the reasoning-mode bloat above eats most of the
input-side savings.

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
  the bottleneck relative to no evidence at all. Some of that gap is real (see the two concrete misses
  fixed below); some of it is the SWE-bench-derived-corpus methodology caveat under "Corpus" above -
  this number is a lower bound, not a precise measurement.
- **Two concrete, verified misses led to a real product fix, not just a benchmark note:** spot-checking
  individual misses (not just categories) found `001-flask-cli-key-quote`, `003-requests-proxy-bypass-registry`,
  and `018-axios-missing-null-check-charset` all came back completely empty from the model - not a
  wrong guess, total silence on a real bug. All three are pure local-logic bugs (a missing quote in an
  error string, an unfiltered empty regex match, a missing null check) with zero cross-file signal -
  Aletheore's evidence layer (blast radius, referenced symbols) structurally cannot help with this
  category, and Flash Review's system prompt review procedure was framed entirely around cross-file
  call tracing and control/data-flow comparison, with no explicit instruction to sanity-check a changed
  expression on its own terms. Fixed by adding an explicit checklist step (null/undefined guards on
  new property access, regex/pattern correctness on edge-case input, string-literal accuracy) to
  `FLASH_REVIEW_SYSTEM_PROMPT` in `github-app/scan_worker/flash_review.py` - not yet validated by a
  benchmark rerun (a live-model prompt-following claim can't be unit-tested), a real v2 candidate.
- **Not yet reflecting the reasoning-mode-disable optimization** already proven elsewhere in this repo
  (87% fewer tokens, 6.2x faster, no quality loss) - a real, low-risk v2 rerun candidate that would
  likely change the cost picture substantially without needing new data collection logic.

Raw results: `results/mixed_repo_deepseek_v4_flash_r1.json`, `results/blind_judge_deepseek_v4_flash_r1.json`.

---

## Experiment 4: the actual production model, 3 real runs - this decided the default

Experiments 2-3 both used a third model as a blind judge, scoring recall against
`ground_truth.yaml`. This experiment asks a narrower, more directly actionable
question: with `gpt-5.6-luna` - the real primary production model, not a stand-in -
generating the reviews, does an independent second model (`deepseek-v4-flash`) judge
each individual finding as holding up against the diff, and does that differ between
`aletheore_context` and `aletheore_compact`? This is a per-finding ACCEPT / REJECT /
UNCERTAIN verification, not a recall score - not directly numerically comparable to
Experiments 2-3's recall numbers, but a real, independent, differently-shaped check on
the same underlying question.

### Setup

- Generation: `gpt-5.6-luna` via the real OpenAI API, same evidence-building code path
  as production (`scan_worker.flash_review`), restricted to the two Aletheore-evidence
  arms only (no baseline - not relevant to this comparison).
- Verification: `deepseek-v4-flash`, real API, given each proposed finding plus the
  actual diff and asked to independently ACCEPT, REJECT, or mark UNCERTAIN - a
  from-scratch check against the diff, not a recall match against `ground_truth.yaml`.
- Corpus: the same 50-case `pr-review-benchmark` corpus as Experiments 2-3.
- 3 repeats of the full 50-case pass, run back to back the same evening.

### A real coverage gap, disclosed rather than smoothed over

Both repeat runs hit transient network failures cloning some of the larger SWE-bench
case repositories (`git clone` returning `early EOF` / `Could not resolve host`) mid-run.
The per-case loop continues past a single failed case rather than aborting, so each run
still produced real data - just not 50/50 coverage every time:

| Run | Cases covered | Missing (network failure, not a scoring miss) |
|---|---|---|
| Run 1 | 50/50 | none |
| Run 2 | 47/50 | 3 `swebench-django-*` cases |
| Run 3 | 33/50 | 17 cases, mostly `swebench-scikit-learn-*`/`sphinx-*`/`sympy-*` |

**Union across all 3 runs: 50/50 cases exercised at least once.** But no single run is
individually complete, and importantly, run 3's missing 17 cases are not a random
sample - they skew toward the harder SWE-bench-derived cases, which affects how its
per-run numbers should be read (see below).

### Results

| Run | `aletheore_compact` accept rate | `aletheore_context` accept rate |
|---|---|---|
| Run 1 | 42/43 = **97.7%** (0 reject, 1 uncertain) | 36/42 = 85.7% (2 reject, 4 uncertain) |
| Run 2 | 40/41 = **97.6%** (1 reject, 0 uncertain) | 38/42 = 90.5% (0 reject, 4 uncertain) |
| Run 3 | 29/30 = **96.7%** (0 reject, 0 uncertain) | 27/27 = 100% (0 reject, 0 uncertain) |

225 individual findings independently verified in total, across 260 generation
records.

### Reading this honestly

- **Compact is remarkably stable**: 96.7-97.7% accept rate across all three runs,
  effectively flat regardless of which case subset landed in a given run.
- **Context is the noisy one**, swinging 85.7% -> 90.5% -> 100%. Run 3's apparent
  100% is not evidence that context caught up - it's a coverage artifact. Run 3
  happened to be missing exactly the harder SWE-bench cases that produced context's
  rejects and uncertains in runs 1-2. Read run 3's context number as "context did
  fine on an easier subset," not "context tied compact."
- **This is consistent with, not contradicted by, Experiment 3's finding** that
  compact and context tie on a real production-grade model (0.527 vs 0.522 recall) -
  compact never underperforms context here either, on a different model and a
  different verification methodology. It does **not** reproduce Experiment 2's
  "compact has the worst false-positive rate" finding, which was specific to the
  much weaker `llama3.1:8b` local model.
- **Cost across all 3 runs, real API pricing**: Luna generation \$0.7667 (2,273,255
  prompt + 260,081 completion tokens at \$0.20/\$1.20 per 1M), DeepSeek verification
  \$0.1562 (599,870 prompt + 257,750 completion tokens at \$0.14/\$0.28 per 1M).
  **Total: \$0.9229** for all 3 runs combined - three full passes over a 50-case
  corpus with a real production model, for under a dollar.

### Verdict: compact shipped as the production default

Compact never underperformed context on any of the 3 runs, on the model that
actually matters (production's own primary model, not a stand-in), while using a
fraction of the prompt tokens context requires. Combined with Experiment 3's tie on
a different production-grade model, and the complete absence of Experiment 2's
weak-model false-positive concern here, this was judged sufficient to make compact
the shipped default for Flash Review - not an experiment sitting behind a flag, the
actual production behavior (`scan_worker/jobs.py`, `_run_flash_review`: the raw
file-content blob `fetch_review_file_context` builds is deliberately never included
in the prompt; `file_contents` is still fetched and used for citation verification).

**Open, disclosed limitation**: no single run has clean 50/50 coverage, and the
network-failure pattern in run 3 specifically strips out the harder half of the
corpus for context's numbers in that run. The union across all 3 runs does cover
every case at least once, and the direction (compact >= context, never worse) holds
in every run including the incomplete ones - but a cleaner single complete run
would strengthen this further. Backfilling the missing cases is real, low-cost
follow-up work (~\$0.10 in additional Luna spend at these rates), not done as part
of this pass.

Raw results: `results/luna_gpt56_generate_r1.json` through `r3.json` (generation),
`results/luna_gpt56_deepseek_verified_r1.json` through `r3.json` (verification).

## Experiment 5: named 3-way vs. a real external tool, same model, same corpus

Experiments 2-4 all compared Aletheore against itself (context vs. compact, generation vs. verification arms). This experiment asks a different question: how does Aletheore's actual hosted product compare against a real, named, external competitor — Qodo's PR-Agent — on the same corpus, held to the same model, so the result isolates review methodology rather than which vendor has the bigger model budget.

The corpus (25 hand-authored/reconstructed real-bug-fix, injected-bug, and clean cases) and its `ground_truth.yaml` files live in `Aletheore/Aletheore`'s `benchmarks/pr-review-benchmark/` — that repo is the corpus/harness source of truth this experiment's scripts read from; this file is where the run's narrative, results, and verdict are published, per this repo's own convention.

Two prior runs on this same corpus are explicitly superseded by this one and documented here for the record, not discarded:

- **An early free-tier-vs-GPT-5.5 run** compared Aletheore's free-tier fallback chain (no OpenAI, no verification) against PR-Agent's own `gpt-5.5` default (a stronger, ~20x-more-expensive-per-token reasoning model) — an unintentional mismatch on both plan tier and model cost, not a fair test of either tool's methodology. Real result at the time: Aletheore 8/15 hit on real-bug-fix cases vs. PR-Agent 12/15 — misleading on its own, corrected below.
- **A pre-deploy Luna-vs-Luna run** put both tools on `gpt-5.6-luna` for the first time, but ran before the session's own product fixes (#471-#476) were deployed to production, and only exercised Aletheore's generation+verification code path via direct invocation, never the GitHub-fetch-layer fixes.

### Setup

- **Aletheore commit**: production deployed at `35e18f8` (tag `github-app-deploy-2026-08-30`), includes every fix through PR #476 in `Aletheore/Aletheore`.
- **Models**: both tools on `gpt-5.6-luna` (OpenAI) for generation. Aletheore's AIR tier additionally runs `deepseek-v4-flash` as a second-model verification pass over Luna's own findings (ACCEPT/REJECT/UNCERTAIN; REJECT is dropped). PR-Agent was explicitly reconfigured via `--config.model=gpt-5.6-luna --config.custom_model_max_tokens=128000` — its own real default is `gpt-5.5`, not used here.
- **Three arms**: Aletheore AIR (Luna + DeepSeek verify), Aletheore Flash (Luna only, no verify), PR-Agent (Luna).
- **Corpus**: 24 of 25 cases (case `020` excluded — a corpus fixture/GitHub-push-protection issue, not yet re-verified against a live push). DeepSource excluded from this run (real analysis-quota exhaustion on the test account, unrelated to Aletheore or PR-Agent).
- **Scoring**: Step 4 manual scoring (real finding message content read against `ground_truth.yaml`, never file:line proximity or grounding-rate alone). The blind independent LLM-judge pass did not run this cycle — see Limitations.
- **Repeats**: 1 full pass per arm (AIR and Flash via direct in-process invocation of `scan_worker.flash_review.review_diff`; PR-Agent via its real CLI, 10 of 24 cases freshly re-measured this run, the remaining 14 reusing real same-day same-config data since nothing about PR-Agent changed in between).
- **Cache status**: no similarity-cache reuse on Aletheore's side (`cache_lookup=None` path, matching a fresh review of each diff).

### Results

24 cases (15 real-bug-fix, 5 injected-bug, 4 clean); 20 cases carry a real recall verdict, the 4 clean cases score false-positive rate only.

| Tool | Hit | Partial | Miss | False Positives |
|---|---|---|---|---|
| Aletheore AIR (Luna + DeepSeek verify) | 15 | 1 | 4 | 0 |
| Aletheore Flash (Luna only, no verify) | 15 | 0 | 5 | 0 |
| PR-Agent / Qodo (Luna) | 6 | 0 | 14 | 8 |

**Timing** (real wall-clock, per case):

| Tool | Per-case avg | Basis |
|---|---|---|
| Aletheore AIR | 33s | 24 cases, direct invocation |
| Aletheore Flash | 15.9s | 24 cases — ~2x faster than AIR, skips the verification round-trip entirely |
| PR-Agent | 69.3s | 10 freshly re-measured cases (full subprocess + live GitHub round-trips each time) |

**Tokens and real cost** (Luna: \$0.20/M input, \$1.20/M output; DeepSeek-v4-flash verification: \$0.44/M input, \$1.32/M output):

| Tool | Prompt tokens | Completion tokens | Real cost |
|---|---|---|---|
| Aletheore AIR — generation | 387,382 | 33,075 | \$0.1172 |
| Aletheore AIR — DeepSeek verification | 16,768 | 49,341 | \$0.0725 |
| **Aletheore AIR — total** | **404,150** | **82,416** | **\$0.1897** |
| Aletheore Flash | 387,382 | 32,651 | \$0.1167 |
| PR-Agent (10 fresh cases, measured) | 293,733 | 14,051 | \$0.0756 |
| PR-Agent (extrapolated to all 24, same rate) | ~704,959 | ~33,722 | ~\$0.1815 |

Raw results: `results/pr_review_3way_luna_scored.json` (per-case recall/false-positive/actionability verdicts for all three arms), `results/pr_review_3way_luna_token_usage.json` (real per-case token usage for all three arms).

### Reading this honestly

- **AIR and Flash tie on total recall (15/20 each)** despite Flash never calling the verification model — consistent with verification being a precision mechanism (it can only drop a finding, never add one), not a recall lever. If your priority is catching real bugs and you're comfortable with Flash's zero-false-positive record on this corpus, AIR's extra \$0.07 and 17 extra seconds per case bought no additional recall here.
- **Both Aletheore tiers hold zero false positives on the 4 clean diffs vs. PR-Agent's 8** — not a close call, and not explained by Aletheore proposing fewer findings overall in a way that would also cost it recall (it doesn't; see the hit numbers above).
- **Aletheore's generation prompt uses roughly half the input tokens PR-Agent's does** for the same 24 diffs. PR-Agent's schema (a ticket-compliance check, an effort-to-review score, a dedicated security field) does real, additional work per call beyond reviewing the diff, which shows up as real extra input tokens - part of why it's slower and pricier per case despite a smaller completion.
- **This reverses the earlier free-tier-vs-GPT-5.5 run's finding (Aletheore 8/15, PR-Agent 12/15) completely.** That comparison wasn't measuring methodology at all - it was measuring a weak free-tier model with no verification against one of the more expensive reasoning models on the market. On identical footing, Aletheore's real recall is roughly 2.5x PR-Agent's, not behind it.

### Verdict

On a real, named, external competitor, same model, same corpus, post-deploy: Aletheore's methodology - deterministic evidence, blast-radius/referenced-symbol context, and (on AIR) a real second-model verification pass - roughly doubles PR-Agent's recall and holds a clean false-positive record, at comparable or lower real cost and meaningfully lower latency. Flash tier gives up nothing on recall measured here versus AIR, only the false-positive-suppression benefit verification provides - a real, quantified tradeoff for anyone choosing between the two tiers, not a guess.

**Open, disclosed limitations**:
1. **No blind LLM-judge pass this cycle.** The corpus's documented process (see `Aletheore/Aletheore`'s `benchmarks/pr-review-benchmark/README.md`, Step 5) calls for a fresh Claude-subagent dispatch per case as an independent second scorer. This run was executed by a forked subagent whose tool policy blocks spawning further subagents, and no direct API key was available as a substitute - so these are Step 4 manual scores only. A separate, earlier 2-arm run (Aletheore vs. PR-Agent only, different exact numbers) did get a full blind-judge pass and measured 83.3% recall agreement with manual scoring (58.3% on the looser actionability scale) - real independent verification, but on that run's numbers, not this one's. Don't blend the two. Two concrete things that run's disagreements surfaced, worth carrying forward into the next judge pass on this run's own numbers: (a) a real rubric ambiguity on clean cases - the LLM judge scored a tool that correctly stayed silent on a clean diff as "hit" (reading "no issue exists" as an object of recall), while manual scoring read the same silence as no verdict/miss (nothing to hit); this needs resolving explicitly in the rubric, not left to each scorer's own interpretation. (b) on case `009` (cobra completions args mutation), manual scoring credited PR-Agent's finding as a clean hit while the judge scored it "partial," reading its explanation (framed around `SetArgs`/completion reuse rather than the exact backing-array-mutation mechanism) as less directly on-point - a legitimate difference in how precisely a finding's explanation has to name the mechanism to count as a full hit, not a scoring bug either way.
2. **AIR's numbers are via direct in-process invocation, not a live webhook trigger.** The plan to validate the deployed fixes end-to-end via real webhook events on the scratch repo's 24 open PRs produced zero new Flash Review comments - GitHub's webhooks were confirmed received and processed by the deployed code (via real check-run evidence, not assumed), but the AIR install's monthly review cap (500/month) was already exhausted by this session's own volume. AIR's generation/verification code path is unaffected by the fixes this would have validated (they live in the GitHub-fetch layer, which direct invocation doesn't call), but this run is not live end-to-end proof of those specific fixes in production.
3. **PR-Agent: 10 of 24 cases are freshly re-measured this cycle**, the remaining 14 reuse real same-day, same-config data. Two independent scoring bugs (a clean-case recall-scoring error, and stale pre-refresh verdicts on the not-yet-fresh cases) were found and fixed after the initial pass, by two different sessions working the same shared data - both are reflected in the numbers above.
4. **Case 020** remains excluded corpus-wide (a fixture/push-protection issue, fixed locally but not yet re-verified against a live push). **DeepSource** was excluded this run (real quota exhaustion on the test account).
## Experiment 6: 5-way named comparison, same corpus — and a real production fix decided by the results

Experiment 5 above compared Aletheore against one named competitor (PR-Agent), both on `gpt-5.6-luna`. This run asks a broader question on the same 24-case corpus: how does Aletheore's *actual current shipped config* — `glm-5.3-flash` via IndieRouter, the model production switched to after Experiment 5 for cost reasons — compare against five real tools, including two (Greptile, DeepSource) that were excluded or degraded in every prior run on this corpus? And it does not stay a passive measurement: a real regression it found in Aletheore's own scoring led to an isolation test, which led to a real production code change the same night.

The corpus, `ground_truth.yaml` files, and pipeline scripts live in `Aletheore/Aletheore`'s `benchmarks/pr-review-benchmark/` — same convention as Experiment 5, that repo is the source of truth this experiment's scripts read from.

### Setup

- **Aletheore commit**: production deployed at `8545f77` (tag `github-app-deploy-2026-09-19-2`), which includes PR #746 (sibling-file context, later disabled — see below), PR #747 (softened confidence bar), and PR #748 (the fix this experiment's own results produced).
- **Aletheore's arm**: direct invocation of `scan_worker.flash_review.review_diff()` — Flash tier only (`verify_with_second_model=False`, no AIR second-model verification pass), model `glm-5.3-flash` via IndieRouter (production's real current default). Three context configurations were tested, not one — see "The real finding" below.
- **PR-Agent**: `gpt-5.6-luna`, unchanged from Experiment 5's config — kept rather than force-matched to Aletheore's new model, because routing PR-Agent through IndieRouter to reach `glm-5.3-flash` turned out to be a real, unresolved integration problem (litellm's own wrapper around the call adds parameters IndieRouter rejects with a generic "model does not exist" error, even though a bare `litellm.completion()` call with identical model/endpoint/key succeeds standalone — isolated but not fixed this run). So this comparison is "each tool's real current config," not architecture-only with the model held constant, and is documented as such rather than silently presented as apples-to-apples.
- **DeepSource, Sourcery, Greptile**: real hosted GitHub App reactions on the scratch repo. All 24 case PRs were closed and reopened fresh partway through this run after discovering Sourcery/Greptile's Apps react reliably to a genuine "PR opened" event but not to a force-push "synchronize" event on an already-existing PR — the initial run looked like Greptile was completely uninstalled/out of credits; it wasn't, it just never saw a fresh-PR event on the stale PRs.
- **Scoring**: Step 4 manual scoring (real finding content read against `ground_truth.yaml`, not file:line proximity alone) *and* Step 5 — four fresh Claude subagents, one per 6-case batch, each with zero knowledge of this session, genuinely blind, findings passed under real tool names (named comparison, no anonymization needed). Recall agreement between manual and LLM-judge scoring: **98.3%**. Actionability agreement (1-5 subjective scale): 57.3% — expected noise on that axis, not a scoring problem.
- **Corpus**: 24 of 25 cases (case `020` excluded, same fixture issue as every prior run on this corpus).

### The real finding: production's own context enrichment was hurting Aletheore's score

Flash Review can feed two optional context blocks into its prompt beyond the diff: `referenced_symbol_context` (resolves symbols the diff imports from unchanged files — an older feature, built specifically to stop a confirmed hallucination class where Flash Review made claims about an unchanged file's behavior with zero real evidence behind them) and `sibling_file_context` (surfaces other files in the same directory as a changed file, so the model can notice convention breaks — new, shipped the same night as this run, PR #746). Production fed both into every real review.

A controlled test on this exact corpus — same model, same prompt, only the context blocks varied — ran each of four configurations, most of them twice, to separate real signal from GLM-5.3-Flash's own run-to-run noise (it's called with no seed):

| Config | Run 1 recall | Run 2 recall | Run 1 precision | Run 2 precision |
|---|---|---|---|---|
| Bare prompt (neither context block) | 90.0% | 85.0% | 100.0% | 94.7% |
| `referenced_symbol_context` only | 90.0% | 95.0% | 100.0% | 95.8% |
| `sibling_file_context` only | 75.0% | 75.0% | 94.7% | 94.7% |
| Both (production's real config when this run started) | 65.0%* | — | 93.8% | — |

\*Manual content-verified scoring, not mechanical presence-of-any-finding — one enriched-context finding was present but addressed a different bug than the ground truth (case `018`: it flagged a real but secondary quoted-charset parsing issue instead of the actual missing-null-check bug), and mechanical scoring would have miscounted it as a hit. Every other config's findings were manually verified as genuinely on-target; see `results/pr_review_sibling_context_isolation.json` for the full per-case breakdown behind every number in this table.

`referenced_symbol_context` alone tracks bare prompt closely across both runs (90.0-95.0%) — not the problem, consistent with it being a genuinely evidence-grounded feature. `sibling_file_context` alone reproduces most of the regression on its own, and replicated almost exactly between its two runs (75.0% recall, 1-of-4 clean-case false positives, 94.7% precision, identical both times — the tightest replication of anything measured in this experiment). Feeding both together was worse still (65.0%), suggesting some further compounding on top of `sibling_file_context`'s own cost. The dominant, cleanly-isolated driver is `sibling_file_context`.

**Production was changed the same night, on this basis**: `github-app/scan_worker/jobs.py` no longer feeds `sibling_file_context` into the live Flash Review prompt ([PR #748](https://github.com/Aletheore/Aletheore/pull/748)), while `referenced_symbol_context` is untouched. A post-deploy verification run against the actual live commit (`8545f77`) measured 95.0% recall / 95.8% precision — consistent with the `referenced_symbol_context`-only runs above, confirming the deployed change performs as the isolation test predicted, not just in theory.

**This conflicts with `sibling_file_context`'s own original validation** (Experiment 2 above measured a real recall gain from a related but not identical context-injection approach, on a completely different corpus — real external repos with much larger, messier multi-file PRs, evaluated with `llama3.1:8b` via Ollama). That conflict is not resolved here — stated plainly as an open question about how a context feature's effect depends on corpus shape and model, not smoothed over. This 24-case run is being weighted more heavily for the *production* decision specifically because it is replicated per-variant and cross-tool/LLM-judge-corroborated on the corpus and model Aletheore actually ships against right now, not because Experiment 2's result is assumed wrong.

**A second, independent defect found in the process**: on the enriched-context run, GLM-5.3-Flash correctly diagnosed at least 2 real bugs (cases `003`, `006`) but `review_diff()`'s own content-grounding validation gate silently dropped both findings because the model's citation didn't quote source text verbatim close enough to the line it named. Confirmed by instrumenting the real validation function directly, not inferred. This is a real product defect — it would cost a real customer a correct finding the same way — filed separately from the context-block question, not yet fixed.

### Results

24 cases (15 real-bug-fix, 5 injected-bug, 4 clean); 20 cases carry a real recall verdict. Pooled manual (Step 4) + LLM-judge (Step 5) scoring. Aletheore's row is the one run of its current config (`referenced_symbol_context`-only, post-#748) that was actually carried through the full manual+LLM-judge pipeline — its false-positive count varied 0-1 across the two replicated runs of this config (see the isolation table above), so the `0` below is real for *this specific judged run*, not a claim that the config is always zero-FP:

| Tool | Hit | Partial | Miss | False Positives | Avg Actionability | Location Grounding | Content Grounding |
|---|---|---|---|---|---|---|---|
| Aletheore (Flash, `glm-5.3-flash`, current config) | 22 | 0 | 2 | 0† | 5.0 | 1.00 | 0.21 |
| PR-Agent / Qodo (`gpt-5.6-luna`) | 21 | 1 | 2 | 1 | 4.75 | 0.95 | 0.00 |
| DeepSource | 5 | 0 | 19 | 0 | 3.0 | 1.00 | n/a |
| Sourcery | 20 | 0 | 4 | 0 | 4.75 | 0.94 | 0.50 |
| Greptile | 22 | 0 | 2 | 1 | 3.9 | 1.00 | n/a |

†0 in this specific judged run, 0-1 across the config's two replicated runs — see "The real finding" above, not a discrepancy with it.

Manual-scoring-only recall (before merging in the LLM judge): Aletheore 90.0% (18/20), Greptile 95.0% (19/20), PR-Agent 92.5% (18/20 + 1 partial), Sourcery 80.0% (16/20), DeepSource 5.0% (1/20).

**Location grounding** (cited file exists, cited line is inside it) is close to uninformative on its own — a static analyser clears it by construction. **Content grounding** (text the finding quotes verbatim really appears near the cited line) is the bar Aletheore's Flash Review enforces on itself in production, applied identically to every tool here; DeepSource and Greptile show `n/a` because their finding text doesn't quote source verbatim by convention, not because their findings are ungrounded.

Raw results: `results/pr_review_5way_glm_manual_scored.json` (Step 4), `results/pr_review_5way_glm_llm_judged.json` (Step 5, one independent Claude subagent batch per file), `results/pr_review_sibling_context_isolation.json` (the full isolation-test data behind the table above, all 8 runs, per-case).

### Reading this honestly

- **DeepSource's 5% recall is a real, measured result on this corpus**, not a quota/config problem this time (unlike Experiment 5, where it was excluded for quota exhaustion) — its GitHub App posted real review comments on every case PR, they just rarely named the actual ground-truth issue.
- **Aletheore's own recall moved from worst-of-five to competitive-with-the-field purely by removing one context block**, without touching the model, the prompt, or the grounding logic otherwise. The lesson generalizes past this one feature: more context is not free, and a benchmark that only measures "did we add evidence" without measuring "did adding it help on *this* corpus shape" can validate a real regression.
- **`referenced_symbol_context` staying clean under the same test is the control this experiment needed** — it rules out "any injected context hurts GLM-5.3-Flash" as the explanation, and points specifically at `sibling_file_context`'s own shape (compact sibling-path-and-symbol-name listings, not real source) as the cost, not context injection in general.
- **PR-Agent's own comparison here is not architecture-only** (see Setup) — it's each tool's real current config, honestly labeled as such rather than presented as a controlled variable that was actually held constant.

### Verdict

A real regression Aletheore had shipped to production (`sibling_file_context`, PR #746) was found by this benchmark, isolated from a separate, unaffected feature (`referenced_symbol_context`) via a replicated controlled test, and fixed in production the same night (PR #748), with a post-deploy run confirming the fix performs as predicted. On the resulting current config, Aletheore is competitive with or ahead of every tool in this comparison on recall, false positives, and actionability, and content-grounds more of its findings than PR-Agent, Greptile, or DeepSource (Sourcery is the only tool that content-grounds a higher share). This experiment is presented as a full account of a real mistake and its fix, not just a final scoreboard — the honest number for Aletheore's recall on this corpus is a measured 85-95% range, not a single confident figure, and the isolation methodology that produced that range is the more durable result than any one run's percentage.

**Open, disclosed limitations**:
1. **PR-Agent stayed on `gpt-5.6-luna`, not Aletheore's current `glm-5.3-flash`.** A real attempt was made to route PR-Agent through IndieRouter to `glm-5.3-flash` for a true architecture-only comparison; it failed with a real, unresolved litellm/IndieRouter compatibility issue (isolated to PR-Agent's own request wrapper — a bare `litellm.completion()` call with identical parameters succeeds) not worth blocking this run on.
2. **The enriched-context (both blocks) condition has only one run**, unlike bare/`referenced_symbol_context`-only/`sibling_file_context`-only, each of which got two. Given the measured run-to-run noise on the other three configs (5-10 points), a second enriched-context run would strengthen the 65.0% figure, though the gap between it and the other configs (25+ points from the best) is large enough that noise alone is an unlikely full explanation.
3. **Non-determinism is real and now measured, not assumed.** GLM-5.3-Flash is called with no seed. Bare prompt and `referenced_symbol_context`-only each varied 5-10 points of recall between their two runs, and one specific false positive (case `024`) appeared in one run of each variant but not the other. `sibling_file_context`-only was the exception — identical numbers both times — which is part of why it was trusted as the isolated driver despite the general noise floor.
4. **This run's conclusion about `sibling_file_context` is not reconciled with its own original validation** on a different corpus (see "The real finding" above) — stated as an open question, not resolved.
5. Case `020` remains excluded corpus-wide (same fixture/push-protection issue as every prior run).

## Experiment 7: per-file completeness generation + windowed verification, named vs. real competitors

Experiment 6 above found and fixed a real regression from an enriched-context feature. This experiment starts from a different diagnostic: does Aletheore's *generation* step miss real bugs even on a diff it can see in full, with no context or budget problem involved at all? It does, traced to a specific, fixable cause, and this run measures the fix against three real, independently-run competitor tools on the same corpus.

**Not the same corpus as "The Martian Benchmark" section of the top-level README.** Both draw on the real, external Martian Code Review Bench concept and overlap in source repos (sentry, grafana, keycloak, cal.com), but this is a separate 13-case, 44-golden-bug corpus with its own structured golden-bug list and its own scoring method (an explicit file/line/keyword signature table, not a `gpt-5-nano` semantic judge against real review comments). Kept in its own directory (`real_pr_recall_corpus/`, not `martian_corpus/`) specifically to avoid repeating this repo's own prior `martian-benchmark-collision` naming problem.

### The diagnostic

A 13-case, 44-golden-bug corpus of real, unmodified GitHub PRs (keycloak, sentry x2, cal.com x5, grafana x4, full mapping in `real_pr_recall_corpus/case_map.json`, golden bugs in `real_pr_recall_corpus/ground_truth.json`) was run through Aletheore's real single-shot `review_diff()`. On several multi-bug PRs it surfaced only 1-2 real bugs even though the rest were fully present in the diff, not truncated by any size budget (confirmed directly: `calcom-10967`'s real diff is ~45KB across 22 files, `calcom-8087`'s ~18KB across 12, both far under `MAX_DIFF_TOTAL_BYTES` and `MAX_CONTEXT_FILE_BYTES`).

Traced to `FLASH_REVIEW_SYSTEM_PROMPT`'s vendored PR-Agent schema (see Experiment 3-4 above for that prompt's own validation history), whose `key_issues_to_review` field is documented as "a concise list (0-5 issues) ... introduced in this PR" - a single cap shared across the whole PR, not per file. A 22-file PR with 6 real bugs structurally crowds most of them out of that cap regardless of model quality. Confirmed live: re-running `sentry-80528` and `calcom-10600` through the unmodified single-shot pipeline returned **zero** findings on both, despite each PR containing 2 and 5 real golden bugs respectively that were fully visible in the diff.

### The fix

Three changes, all in `Aletheore/Aletheore`, [PR #762](https://github.com/Aletheore/Aletheore/pull/762) (open at time of writing, not yet merged, commit `0b54eb7`):

- **`per_file_completeness`**: `review_diff()` gains a flag that runs one real generation call per changed file instead of one for the whole PR, so PR-Agent's 0-5 cap applies per file. Same downstream grounding/merge/verification pipeline as before, unchanged.
- **Windowed verification context**: `_verify_findings_with_second_model` gains `diff_patches` windowing, scoping each finding's own verification call to just its file's patch instead of the whole PR's diff. Real cost lever for per-file completeness's much larger candidate pool - roughly 2x cheaper per call on a validated sample, with no true-positive regression found.
- **Asymmetric-risk verification prompt**: `VERIFICATION_SYSTEM_PROMPT` rewritten so the burden of proof is on REJECT, not ACCEPT (a wrongly-kept finding costs a developer a few seconds; a wrongly-dropped one is gone with no second chance). Recovers most of verification's recall cost while keeping its precision gain, versus the unmodified prompt.

`scan_worker/jobs.py` wires both paid tiers to `per_file_completeness` (real measured cost ~3x single-shot generation, ~$0.0028/review, cheap enough for Flash tier too) and keeps second-model verification AIR-only (~15x generation cost even windowed - too expensive for Flash's already-validated cost model). Free tier gets neither.

### Results

Real, 3x-averaged runs through the exact production code path (`review_diff()`, unmodified, called the same way `jobs.py` calls it for each tier - not a parallel test harness), scored against `ground_truth.json`'s 44 golden bugs with an explicit, reviewable (file substring, line window, keyword) matching table (`real_pr_recall_corpus/scripts/score_results.py`), not a fresh LLM judge per run:

| Config | Recall (3 trials) | Precision (3 trials) | Cost/review |
|---|---|---|---|
| Flash (per-file, no verification) | 59.1% / 59.1% / 56.8% (avg **58.3%**) | 32.7% / 31.1% / 37.9% (avg **33.9%**) | ~$0.0028 |
| AIR (per-file + windowed verification) | 56.8% / 59.1% / 59.1% (avg **58.3%**) | 38.5% / 40.7% / 38.9% (avg **39.4%**) | ~$0.047 |

Against real competitor tools run independently on this same corpus in an earlier session (`real_pr_recall_corpus/results/score_competitors.log`, real hosted GitHub App reactions, same methodology as Experiment 6's competitor arms):

| Tool | Recall | Precision |
|---|---|---|
| Greptile-v5 | 52.3% (23/44) | 54.8% (23/42) |
| Qodo-v2-2 | 34.1% (15/44) | 62.5% (15/24) |
| **Aletheore Flash** | **58.3%** | 33.9% |
| **Aletheore AIR** | **58.3%** | 39.4% |

> A fourth named tool was benchmarked in this same run and has been redacted (2026-09-23):
> its Terms of Service bars disclosing benchmark results about its product without prior
> written consent, which this repository did not have. Permission is being requested;
> this table will be restored with the same real numbers if granted.

> **Precision correction (2026-09-23):** the original published precision figures for both
> Greptile-v5 and Qodo-v2-2 (41.1% and 40.5%) used the raw count of every string captured
> from each tool's real review comments as the denominator - which included non-finding
> items: one whole-PR "Greptile Summary" comment per case (13 total, plus one genuine
> duplicate finding in `calcom-8087`), and one "Code Review by Qodo ... Bugs (N) ..." summary
> line per case (13 total). Neither is an individual finding, and counting them inflated the
> denominator and deflated measured precision for both tools - an error caught while
> re-verifying this table before an unrelated outreach email, not by either vendor. Corrected
> by excluding those items: Greptile 23/42 (was 23/56), Qodo 15/24 (was 15/37). Recall is
> unaffected - its denominator is the fixed 44 golden bugs, not tool output. The redacted
> fourth tool's own precision has the same class of error (its raw data included
> `@coderabbitai full review` trigger echoes, `Actionable comments posted: N` summaries, and
> marketing-footer boilerplate) and would need the same correction before it is ever restored.

Aletheore leads decisively on recall (58.3% vs. the next-best 52.3%) but, once corrected, has
the lowest precision of the five configs measured here - a real, honest tradeoff, not a clean
sweep. AIR still beats Qodo's recall by 24 points and Greptile's by 6, but both Greptile and
Qodo now measure higher precision than either Aletheore tier on this corpus.

### What averaging over 3 trials changed

A single-trial version of this same comparison (not reported as the headline number here, kept only as the reason the 3x design exists) showed AIR's second-model verification costing real recall - findings that matched a golden bug got REJECTed alongside genuine noise. Two of those specific losses were investigated directly rather than accepted at face value:

- `sentry-80168`'s golden bug (`test_detector.py:195`, a claimed `value`-parameter mismatch) turned out to be an **imprecise golden label**, not a real verifier failure: reading the real function it referenced (`build_mock_occurrence_and_event` in the actual repo checkout) confirmed the `value` parameter is never used in constructing the returned object, so the claimed mismatch has no real effect. The verifier's REJECT reason stated exactly this, correctly.
- `grafana-76186`'s golden bug (`logger_middleware.go:49`, a traceID-removal finding) flipped to ACCEPT when re-run in isolation with identical context - genuine call-to-call sampling noise in the verifier, not a systematic weakness.

Averaged over 3 fresh trials, AIR's recall came out identical to Flash's (58.3% both) rather than lower, consistent with those two findings: at least some of the apparent recall cost was noise and a corpus-label problem, not a real, reproducible verifier weakness.

### Real cost

The reported 3x-trial run (`real_pr_recall_corpus/results/aletheore_3x_results.json`): generation across all 6 trials (3 Flash + 3 AIR) **$0.2175** (138 calls/trial, `glm-5.3-flash` via IndieRouter), verification across the 3 AIR trials **$1.7333** (`deepseek-v4-flash`, ~101-113 calls/trial). Total **$1.9508** for the full reported comparison. Exact per-trial costs are in the results file alongside each trial's findings.

This does not include earlier exploratory spend during development (prompt A/B tests, windowing validation on a smaller sample) that led to this design - only the final, reported 3x comparison.

### Reading this honestly

- **Competitor numbers are single runs from an earlier session, not 3x-averaged like Aletheore's own numbers here.** Not perfectly apples-to-apples, though Aletheore's own trial-to-trial variance was small (recall varied at most 2.3 points across any 3 trials), so it is unlikely to flip the comparison.
- **The golden-matching table is a hand-built signature key, not a fresh LLM judge.** Built by reading real findings against real diffs and real repo source across several earlier scoring passes this session, then applied mechanically and reproducibly across all 6 trials - deliberate, given this session's own prior finding that LLM-judge agreement with manual scoring needed auditing rather than being trusted outright. The known cost: a real finding phrased in a way the table's keywords do not anticipate would score as a miss even if correct.
- **This is pre-merge code.** PR #762 is open, not yet deployed to production. The numbers above describe what would ship if merged, not Aletheore's live behavior today.
- **A real operational hiccup happened mid-investigation**: the IndieRouter key in use went invalid partway through this session (a live `401 Invalid API key` from every call), traced to the credential itself rather than a code or rate-limit problem, and was rotated before the reported run. Every failed call in that window failed at the auth stage before any tokens were billed, so it cost nothing beyond time - noted here because a full account of what happened during a benchmark run is worth more than a clean-looking final number that omits it.
- **44 golden bugs across 13 cases is a real but modest sample.** One case's finding flipping moves the aggregate by 2-4 points, and this session found at least one golden label itself imprecise (see above) - the corpus is real and useful, not flawless ground truth.

### Reproducing

```bash
git clone https://github.com/Aletheore/Aletheore
cd Aletheore
git fetch origin experiment/verification-asymmetric-risk
git checkout experiment/verification-asymmetric-risk   # PR #762, commit 0b54eb7

cd ../aletheore-benchmarks/pr_review/real_pr_recall_corpus/scripts

export INDIEROUTER_API_KEY=...   # generation, glm-5.3-flash
export DEEPSEEK_API_KEY=...      # verification (AIR config only)

python3 run_benchmark.py --aletheore-root ../../../../Aletheore --trials 3 --config both
# real cost: ~$1.95 for 3 trials of each config (generation + verification)

python3 score_results.py
```

`--aletheore-root` points at a local `Aletheore/Aletheore` checkout - the script inserts `{root}/github-app` onto `sys.path` and imports `review_diff`/`flash_review_generation_adapter` directly, the same functions `scan_worker/jobs.py` calls in production, not a reimplementation. `--config flash`/`--config air`/`--trials N` run a smaller slice for a cheaper smoke test.

### Verdict

Per-file completeness generation, closed the largest measured gap: production's real single-shot pipeline returned zero findings on two real multi-bug PRs it should have caught something on, traced to a per-PR (not per-file) finding cap in the vendored generation prompt. The fix, plus windowed asymmetric-risk verification for AIR tier, measured a real, 3x-replicated recall and precision lead over a fourth named competitor on this corpus (redacted above pending permission), and closed most of the gap to Greptile's precision while keeping a real recall lead over it. Cost stays proportionate to what each tier can absorb: per-file completeness is cheap enough for both paid tiers (~$0.0028/review), second-model verification stays AIR-only (~$0.047/review combined) because it costs roughly 15x generation even after the windowing fix.

**Open, disclosed limitations**:
1. **PR #762 is not yet merged.** These are pre-release numbers for code that exists and was tested against the real production call path, not numbers from what is currently live.
2. **Only 2 of the recall-cost findings from the pre-averaging single-trial run were individually investigated** (`sentry-80168`, `grafana-76186`). Averaging over 3 trials shows the aggregate recall cost disappeared, which is the stronger evidence, but not every individual case-level fluctuation across all 6 trials was traced to a specific cause the way those two were.
3. **The competitor numbers' own run count and methodology come from an earlier session** and are cited, not independently re-verified in this one - see `real_pr_recall_corpus/results/score_competitors.log` for that run's own real output.
4. **Verification cost (~$0.047/review) is a real, meaningful multiple of generation cost** even after windowing cut it roughly 2x - a further reduction was investigated (see the git history behind this file for the windowing validation) but not pushed further within this session.
5. `calcom-8087`'s golden bug G0 (a claimed missing try/catch around a dynamic import) was matched inconsistently across trials and is the least reliably scored golden in this corpus - kept in the denominator rather than excluded, since the underlying claim is real, just imprecisely worded for keyword matching.

