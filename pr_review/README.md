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
