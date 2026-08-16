# Deterministic analysis vs. bare LLM

Every other section of this repository measures Aletheore's LLM-backed
features (retrieval, AIRview) against RepoWise's. This one asks a
different, narrower question: for the parts of Aletheore that are **not**
an LLM call at all — hotspots, ownership, dead-code detection, computed
from real git history and a real import graph — can a bare LLM reproduce
the same answer if it's simply handed the same underlying data?

**No.** Not "worse." Not "close but rounds wrong." A bare LLM given
complete, sufficient data either fabricated wrong numbers with full
confidence, or — once — correctly refused to answer and asked for real
code instead. Aletheore's scanner produces the exact answer, every time,
without being asked twice.

## Corpus

Same repository as the retrieval benchmark above: [pallets/flask](https://github.com/pallets/flask)
at `2a8a38b051fc248865730bf3511bf2e2ea325e81`, 5,555 commits, 83 Python
files. `aletheore` CLI `0.8.12`.

## Methodology

The bare-LLM side is never handed an impossible task and never denied
information the deterministic side has:

1. Extract the **minimum raw data** a human would need to compute the
   answer by hand — a git log slice, or every file's own import lines —
   not a summary, not a hint, the actual underlying facts.
2. Give that **identical data** to the model in a single
   `simple_completion()` call (no tools, no code execution, no
   multi-turn correction) and ask it to compute what Aletheore's scanner
   computes.
3. Compute **exact ground truth from that same slice** with a five-line
   `Counter` (`scripts/det_vs_llm_exact_ground_truth.py`) — not from
   Aletheore's full-history output, so the comparison isn't "LLM given
   less data than the tool." Model and tool see the same facts.
4. Score number by number.

Two models: `gpt-5.6-luna` (Aletheore's production model for its LLM
surfaces) and `gpt-5.6-terra` (included for completeness — see
[Known limitations](#known-limitations)). Both at provider-default
reasoning.

## Test 1: Hotspots — which files change the most

**Input:** raw `git log --name-only` for the most recent 1,500 commits.
The full 5,555-commit history is **205,425 tokens** as raw log text —
measured directly, not estimated — which doesn't fit in a single
completion at all for most models. The 1,500-commit slice is already a
concession *to* the bare-LLM side.

**Task:** count how many commits touched each file; report the top 10.

| Rank | Exact ground truth | Terra | Luna |
|---:|---|---|---|
| 1 | `CHANGES.rst` — 244 | `CHANGES.rst` — 218 ❌ | *(declined — see below)* |
| 2 | `src/flask/app.py` — 112 | `src/flask/app.py` — 154 ❌ (+38%) | |
| 3 | `requirements/dev.txt` — 94 | `src/flask/helpers.py` — 123 ❌ (real #6) | |
| 4 | `.pre-commit-config.yaml` — 93 | `requirements/dev.txt` — 117 ❌ | |
| 5 | `.github/workflows/tests.yaml` — 72 | `.pre-commit-config.yaml` — 105 ❌ | |
| 6 | `src/flask/helpers.py` — 69 | `src/flask/blueprints.py` — 96 ❌ (not in real top 10) | |
| 7 | `.github/workflows/publish.yaml` — 59 | `src/flask/cli.py` — 94 ❌ (fabricated) | |
| 8 | `requirements/tests.txt` — 59 | `src/flask/scaffold.py` — 92 ❌ (fabricated) | |
| 9 | `requirements/docs.txt` — 58 | `tests/test_basic.py` — 89 ❌ (fabricated) | |
| 10 | `pyproject.toml` — 57 | `pyproject.toml` — 83 ❌ | |

**Terra: 0 of 10 counts correct.** Every number wrong, four entries
don't belong in the real top 10, presented with no hedge.

**Luna declined to guess:**

> *"I'm unable to reliably produce exact counts from this extremely
> large log without programmatically parsing it."*

— and handed back a correct 12-line Python script to compute it exactly
(full text in `results/det_vs_llm_model_outputs.md`). This is the more
trustworthy failure mode of the two: a customer trusting Terra's table
gets confidently wrong numbers; a customer getting Luna's answer gets
nothing wrong, just nothing useful either.

**Aletheore's scanner:** exact, deterministic, every run.

## Test 2: Ownership — who actually owns this code

**Input:** same 1,500-commit slice, `author name|email` per commit
(52.7 KB — much smaller than the hotspots input, so if there's a test
bare LLMs should win, it's this one).

**Task:** count commits per unique author; report the top 8.

| Rank | Exact ground truth | Terra | Luna |
|---:|---|---|---|
| 1 | David Lord — 1,063 (70.87%) | 1,065 (+2) | **1,116 (+53)** |
| 2 | Grey Li — 65 (4.33%) | 65 ✓ | 77 (+12) |
| 3 | dependabot[bot] — 61 (4.07%) | 61 ✓ | 48 (−13) |
| 4 | pgjones — 47 (3.13%) | 47 ✓ | 44 (−3) |
| 5 | pre-commit-ci[bot] — 38 (2.53%) | 39 (+1) | 38 ✓ |
| 6 | dependabot-preview[bot] — 31 (2.07%) | 31 ✓ | 25 (−6) |
| 7 | Frank Yu — 6 (0.40%) | 6 ✓ | **omitted entirely** |
| 8 (tie) | Adrian Moennich — 6 (0.40%) | 5 ❌, tied with **fabricated "Maxim G. Ivanov"** | 5 ❌, tied with the **same fabricated name** |

Both models also rendered several percentages as nonsensical fractions
(`"61/15%"`) instead of `61/1500`.

**Terra: 4 of 8 exact, mean error 0.4 on the rest — still fabricates a
person into the ranking. Luna: 1 of 8 exact, mean error ~14.5, drops a
real contributor, fabricates the same phantom name Terra did.** That
both models independently produced the identical nonexistent
contributor is itself worth flagging — see
[Known limitations](#known-limitations).

**Aletheore's scanner:** exact — see
`results/det_vs_llm_ground_truth_ownership_repo_wide.json`, and read the
filename before citing this number: **the CLI's per-file `ownership`
query is currently broken** (below), so this uses only the repo-wide
aggregate, which the bug doesn't affect.

## Test 3: Dead code — unreachable modules

**Input:** every one of the 83 `.py` files' own `import`/`from` lines
(20.8 KB — the entire import graph, nothing withheld).

**Task:** which files does nothing else in the repo import?

**Ground truth (Aletheore's scanner):** exactly 2 —
`docs/conf.py`, `examples/celery/make_celery.py`. The scanner recognizes
19 legitimate reachability exceptions (`__init__.py`, `__main__.py`,
`cli.py`, `wsgi.py`, pytest-discovered test files) and correctly
excludes all of them.

**Terra:** flagged 49 files. Found both real ones, buried inside 47
false positives — nearly every test file in the repo. Recall 100%,
**precision 4.1%.** To its credit: *"This is only based on the shown
static import statements; it does not account for pytest discovery, CLI
module-name strings, `python -m`, dynamic imports, or framework-driven
loading."*

**Luna:** flagged 48 files (nearly the same list). Recall 100%,
**precision 4.2%.** No caveat.

If a customer got either list as-is, their own test suite would show up
as "dead code" on the first read. That's not a marginal accuracy gap —
it's the difference between a usable feature and a discarded one.

## A structural limit, not just an accuracy one

205,425 tokens for the full hotspots history is past what fits in one
completion for most models before the question of whether the model can
count correctly even arises. The 1,500-commit slice above is a
concession *to* the bare-LLM side. Aletheore's scanner processed all
5,555 commits with no such ceiling and no decision needed about how much
history to leave out.

## Known limitations

- **`aletheore query ownership <target>` ignores `target` entirely.**
  `find_ownership()` in the CLI's query layer returns the repo-wide
  aggregate unconditionally — confirmed by diffing the query's output
  for two different files and getting byte-identical results. The
  underlying data model has no per-file ownership breakdown at all, only
  a repo-wide one. The CLI's own signature (`ownership <file>`) implies
  per-file resolution it can't currently deliver. Flagged here rather
  than worked around.
- **Sample size is one repository.** The qualitative pattern — bare LLM
  confidently wrong on exhaustive counting, deterministic tool exact —
  is the load-bearing claim, not the specific percentages.
- **Both models independently fabricated the same nonexistent
  contributor** ("Maxim G. Ivanov"). Worth investigating whether this is
  a real person from flask's broader history both models pattern-matched
  into the wrong slice, rather than pure hallucination — not resolved
  here.
- **Terra is not the production model** (Luna is). Included for
  completeness of the record from the investigation that produced this
  benchmark, not as an argument for switching models. The main claim —
  deterministic analysis vs. any bare LLM — holds for both.

## Reproducing

```bash
python scripts/det_vs_llm_build_inputs.py /path/to/output 1500   # from inside a target repo checkout
python scripts/det_vs_llm_exact_ground_truth.py                   # no API calls
python scripts/det_vs_llm_run_bare_llm.py gpt-5.6-luna             # real API calls, ~$0.01
```

All inputs, model outputs, and ground truth used above are committed in
`results/det_vs_llm_*` — nothing here depends on state outside this repo.
