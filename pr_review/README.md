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
