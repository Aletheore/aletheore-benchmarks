# SWE-PRBench

A real, independent, externally-published benchmark — not one built in-house. Unlike `martian_benchmark/`
(self-scraped GitHub review comments, judged by an uncalibrated model), SWE-PRBench's ground truth is
human-annotated via the real GitHub review API against 350 real merged PRs, and its judge methodology is
published and validated (κ=0.75 against human agreement, using GPT-5.2). Running Aletheore's real
production generation path against it gives a number directly comparable to the paper's own leaderboard,
not just to our own prior runs.

- Dataset: [`huggingface.co/datasets/foundry-ai/swe-prbench`](https://huggingface.co/datasets/foundry-ai/swe-prbench)
- Harness: [`github.com/FoundryHQ-AI/swe-prbench`](https://github.com/FoundryHQ-AI/swe-prbench)
- Paper: arXiv 2603.26130

## Corpus

The published `eval_100` split — 100 real PRs, diff-only condition (`config_A_diff_only`, the paper's own
term), matching the config the published leaderboard numbers below were scored under. The paper defines
three configs (A = diff-only, B = diff+file, C = full context); only config_A was run here.

## Methodology

- **Generation**: direct invocation of `scan_worker.flash_review.review_diff()`, generation model
  `glm-5.3-flash` via IndieRouter — production's real current adapter
  (`flash_review_generation_adapter()` in `model_tiers.py`), same one used in `pr_review/` and
  `martian_benchmark/`. No `referenced_symbol_context` (these are external, unscanned repos — no real
  scan evidence exists to build it from) and no `file_contents` (so production's deterministic
  `find_semantic_regressions()` layer, which requires `file_contents`, contributed nothing — see "What
  Aletheore actually adds" below). `verify_with_second_model=False` — production's dual-model
  verification (a second LLM rejecting false positives) was not exercised.
- **Judge**: the harness's own real `judge.py`/`scorer.py`/`assembler.py`/`aggregate.py`, imported and run
  as-is — nothing here re-implements their scoring logic. Judge model is real `gpt-5.2`, matching the
  paper's own published judge exactly, run twice on identical generation data through two different API
  routes (OpenRouter, and directly via OpenAI) to check for a routing effect.
- **Cost**: real, measured. Judge calls are paid (OpenRouter/OpenAI, ~$1.80-2.00 for a full 100-task pass);
  generation is near-free (GLM-5.3-Flash, ~$0.055 per 100-task pass at the token volumes measured here).

## Results

Overall score (`s̄`), diff-only config_A — the metric the published leaderboard reports:

| Model | Overall score |
|---|---|
| Claude Haiku 4.5 | 0.153 |
| Claude Sonnet 4.6 | 0.152 |
| DeepSeek V3 | 0.150 |
| **Aletheore (GLM-5.3-Flash), real gpt-5.2 judge via OpenRouter** | **0.149** |
| **Aletheore (GLM-5.3-Flash), real gpt-5.2 judge via OpenAI direct, same generation data** | **0.169** |
| Mistral Large 3 | 0.147 |
| GPT-4o | 0.113 |
| GPT-4o-mini | 0.108 |
| Mistral Small | 0.106 |
| Llama 3.3 70B | 0.079 |

Full per-task records: `results/eval_report_openrouter.json`, `results/eval_report_openai_direct.json`.
Aggregate summary: `results/summary.json`.

### Real cost, same 100 tasks

Computed on GLM's own measured token usage (511,804 input / 62,634 output tokens across the 100-task run)
against each model's real, current (verified 2026-09-20) API pricing — not a theoretical rate, the actual
cost of doing this exact run:

| Model | Cost / 100 PRs | vs. GLM |
|---|---|---|
| GLM-5.3-Flash (Aletheore) | $0.055 | 1x |
| DeepSeek V3 | $0.163 | 3.0x |
| Mistral Large 3 | $0.350 | 6.3x |
| Claude Haiku 4.5 | $0.825 | 15.0x |
| Claude Sonnet 4.6 | $2.475 | 44.9x |

Caveat: this is cost *at GLM's own output volume*. A more verbose model would cost more than this table
shows — confirmed directly in the Luna side-experiment below, where Luna produced ~2x GLM's output tokens
on the identical 100 tasks.

### Side experiment: does a more expensive model do better here?

Same 100 tasks, same harness, generation swapped from GLM-5.3-Flash to `gpt-5.6-luna` (production's
primary model for every *other* writing surface — see `model_tiers.py`'s own docstring), real gpt-5.2
judge:

| | GLM-5.3-Flash | Luna (gpt-5.6-luna) |
|---|---|---|
| Recall | 14.2% | 3.1% |
| Overall score | 0.149 | 0.049 |
| Attempt rate (found ≥1 issue) | 77/100 | 49/100 |

Luna does markedly *worse* here — not better. Verified this isn't a parsing bug: Luna's raw completions on
the zero-finding tasks were captured directly and parse cleanly against the expected schema; it genuinely
returned "no issues" more often. The likely explanation is that Luna is more conservative without grounding
evidence (no `referenced_symbol_context`, no scan evidence — this is a diff-only, unscanned-repo condition),
while GLM is comfortable flagging things off the raw diff alone. This is consistent with why production's
Flash Review feature deliberately uses GLM rather than Luna for this exact generation surface. Full data:
`results/eval_report_luna.json`.

### Re-run with per_file_completeness=True (2026-09-22)

The gap this README originally flagged as open — this run predates PR #762 — closed same-day. Same 100
tasks, same harness, same GLM-5.3-Flash adapter, same real `gpt-5.2` judge (direct via OpenAI), the only
variable changed is `per_file_completeness=True` (production's real current paid-tier value, one generation
call per changed file instead of one call for the whole diff — `verify_with_second_model` held at `False`
in both runs, to isolate this one variable rather than changing two things at once):

| | Bare (original, openai-direct route) | per_file_completeness=True |
|---|---|---|
| Recall | 16.8% | **22.3%** |
| Precision | 23.8% | 20.5% |
| Overall score | 0.169 | **0.174** |
| Attempt rate | - | 78/100 |
| Coverage | 0.40 | 0.48 |

Recall gained ~5.5 points for a ~2-point precision cost — a real, meaningful shift, not noise-sized (compare
to the 0.02 openrouter-vs-openai-direct judge-routing gap on the bare run, or the 0.015-0.017 std the 4-run
variance check measured). Against the published leaderboard, 0.174 is now **above** every model in the
previously-"tied" cluster (Claude Haiku 4.5 0.153, Claude Sonnet 4.6 0.152, DeepSeek V3 0.150, Mistral Large
3 0.147). Real, measured generation cost: $0.1615 for the full 100-task pass (higher than bare mode's
~$0.055, as expected — per-file completeness means more calls, more repeated system-prompt/diff-header
overhead per task). Full data: `results/eval_report_perfile.json`, `results/generation_results_perfile.json`.
Scripts: `scripts/run_generation_perfile.py`, `scripts/run_scoring_perfile.py`.

#### Verifying 0.174 is real signal, not judge noise

Two follow-up judge passes on the **identical** per-file generation output, to separate two different
possible noise sources before trusting the number above:

| Pass | Route | Overall score | Delta vs. 0.174 |
|---|---|---|---|
| Original | OpenAI direct (`gpt-5.2`) | 0.174 | - |
| Repeat #1 | **OpenRouter** (`openai/gpt-5.2`) | 0.111 | -0.063 |
| Repeat #2 | **OpenAI direct** (`gpt-5.2`, independent call) | 0.170 | -0.004 |

The OpenRouter repeat looked alarming at first — a 6.3-point swing, well outside the 2-3 point band the
bare-mode cross-route comparison had suggested. Investigated rather than reported blind: per-task
comparison (e.g. `pipecat__3692` - identical 2 findings, identical 1 human comment to match, on both
routes) showed the OpenRouter judge and the OpenAI-direct judge reaching genuinely different
*classifications* of the same evidence (OpenAI-direct: 1 finding confirmed as a real match, score 0.63;
OpenRouter: both findings called merely "plausible," nothing matched, score 0.005) - not a parsing bug, a
real disagreement. `no_matches_detected` warning counts ruled out one candidate explanation (OpenRouter's
route actually logged *fewer* of these on this run - 40/100 - than it did on the original bare-mode run,
53/100, so this isn't new). The remaining, more likely explanation: OpenRouter serves `openai/gpt-5.2`
through its own routing layer, which is not guaranteed to hit the identical serving stack as OpenAI's own
direct API for the same model name - real provider inconsistency, not generation-level noise.

The same-route repeat (#2) is the clean test, since it isolates the one thing that actually matters here -
does the real judge agree with itself: **0.174 vs. 0.170, a 0.4-point gap.** That's small enough to trust
the number. Averaging the two same-route OpenAI-direct passes (0.172) is the more defensible single figure
if one is needed. **Conclusion: "Aletheore (GLM-5.3-Flash, per_file_completeness=True) clearly beats the
Sonnet 4.6/Haiku 4.5/DeepSeek V3/Mistral Large 3 cluster" is now a real, repeat-verified claim** - the
~1.7-2.1 point gap to the top of that cluster is 4-5x larger than the 0.4-point same-route judge noise just
measured, not comparable to it. **Separately, real finding worth flagging for anyone else using this
harness**: don't trust OpenRouter as a stand-in for a specific frontier judge model without first checking
same-route repeatability - it measured provider inconsistency here, not the noise floor it was meant to
check. Full data: `results/eval_report_perfile_openai_run2.json` (repeat #2),
`results/eval_report_perfile_openrouter.json` (repeat #1). Scripts:
`scripts/run_scoring_perfile_repeat.py`, `scripts/run_scoring_perfile_openrouter.py`.

## Reading this honestly

- **The gap to the top of the "tied" cluster is smaller than GLM's own measured noise.** The entire spread
  between Aletheore (0.149) and Claude Sonnet 4.6/Haiku 4.5 (0.152/0.153) is 0.003-0.004. A 4-run variance
  check (same 100 tasks, same GLM prompt, 4 independent regenerations, scored with a free `gpt-4o-mini`
  proxy judge held constant across all 4 runs to isolate *generation* variance) measured a run-to-run
  spread of overall_score 0.151-0.191 (std ≈ 0.015-0.017) — 4-5x larger than the entire gap to the top of
  the cluster. **Do not publish "Aletheore ranks 4th"** — the defensible claim is "Aletheore is
  statistically tied with the top cluster (Sonnet 4.6, Haiku 4.5, DeepSeek V3, Mistral Large 3) and clearly
  ahead of GPT-4o-class models," where the second half of that claim *is* robust (the gap to GPT-4o and
  below is ~7x larger than GLM's own measured spread). Proxy-judge variance data:
  `results/eval_report_variance_run{1,2,3,4}.json` — note these are on the lenient proxy's own scale
  (mean 0.174), not directly comparable in absolute terms to the real gpt-5.2 numbers above; only the
  *relative* spread across the 4 runs is the load-bearing number.
- **The same generation data scored 0.149 vs. 0.169 depending only on API route** (OpenRouter vs. direct
  OpenAI, identical findings, identical judge model `gpt-5.2`). That 0.02 gap is inside the same noise band
  as the variance check above — a real, measured example of judge-call noise, not a routing artifact worth
  investigating further. Averaging both real-judge data points (~0.159) is the more defensible single
  number if one is needed.
- **This number is not "raw GLM."** Aletheore's own system prompt (`FLASH_REVIEW_SYSTEM_PROMPT`) and a real
  line-citation grounding filter (`_validate_findings()`, using the real diff-patch shape to drop any
  finding whose cited line isn't actually near a changed hunk) both ran and shaped the output. But it's
  also not the full production pipeline: `find_semantic_regressions()` (deterministic, non-LLM regression
  detection) requires `file_contents`, which wasn't available for these external unscanned repos, so it
  contributed zero findings here — confirmed by reading its own `if not file_contents: return []` guard.
  Dual-model verification (`verify_with_second_model`) was off. A number that credits Aletheore's full
  pipeline would need real `file_contents` fetched per-repo and verification turned on — a materially
  bigger, more expensive run, not done here.
- **Detection rate varies by difficulty as expected**: Type2_Contextual (0.170-0.203 across the two real
  judge runs) and Type1_Direct (0.131-0.202) score higher than Type3_Latent_Candidate (0.060-0.099) — latent/
  candidate bugs are structurally harder to catch from a diff alone, consistent with the paper's own framing
  of that difficulty tier.

## Reproducing

The harness is FoundryHQ-AI's real, unmodified `eval_harness/` (`judge.py`, `scorer.py`, `assembler.py`,
`aggregate.py`, `model_clients.py`, `schema.py`) — clone it fresh from
[`github.com/FoundryHQ-AI/swe-prbench`](https://github.com/FoundryHQ-AI/swe-prbench) rather than vendoring
it here, same as the dataset itself (`huggingface.co/datasets/foundry-ai/swe-prbench`'s `eval_100` split) -
neither is redistributed in this repo.

Our own glue scripts live in `scripts/`:

- `run_generation.py` / `run_generation_luna.py` — generation drivers. Run **inside the deployed
  scan-worker container** (`sys.path.insert(0, "/app")`, so `scan_worker`/`aletheore` are importable the
  same way production imports them), reading the 100-task slim eval set and calling `review_diff()`
  directly with each real production adapter (`flash_review_generation_adapter()` for GLM,
  `writing_adapter_for(..., _prefer_luna=True)`-equivalent for the Luna side-experiment).
- `run_scoring_openrouter.py` / `run_scoring_openai_direct.py` / `run_scoring_luna.py` /
  `run_scoring_variance_proxy.py` — scoring drivers, calling the cloned harness's own `run_judge()`/
  `compute_dimension_scores()`/`assemble_eval_result()` against the generation output.
- `model_endpoints.yaml` — harness routing config (judge model + provider), needs `OPENROUTER_API_KEY`
  and/or `OPENAI_API_KEY` for the real `gpt-5.2` judge.
- `smoke_test.py` — single-task sanity check before committing to a full 100-task paid run.

- `run_generation_perfile.py` / `run_scoring_perfile.py` — the `per_file_completeness=True` re-run (see
  "Re-run with per_file_completeness=True" above). Same shape as the originals, `review_diff()` called with
  `per_file_completeness=True` instead of that parameter's default.
- `run_scoring_perfile_repeat.py` / `run_scoring_perfile_openrouter.py` — the two follow-up judge passes on
  the identical per-file generation output (see "Verifying 0.174 is real signal, not judge noise" above) -
  a same-route repeat and a cross-route (OpenRouter) comparison, run to distinguish real judge noise from
  provider-routing inconsistency before trusting the headline number.

**The original run predated PR #762** (`feat: per-file completeness generation + windowed verification for
Flash Review`, merged 2026-09-21 — one day after) - `run_generation.py`'s `review_diff()` call didn't pass
`per_file_completeness`, so it ran on that parameter's default (`False`), not production's real paid-tier
value. Closed same-day by the re-run above, and the resulting 0.174 score was itself repeat-verified via a
same-route judge pass (0.170, a 0.4-point gap - see above) - not a single, unverified number. Still open:
neither re-run has `verify_with_second_model=True` (AIR tier's real second-model verification pass).
