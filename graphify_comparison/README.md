# Head-to-head against Graphify (ERPNext code intelligence)

[Graphify](https://github.com/Graphify-Labs/graphify) is a tree-sitter-based
code-knowledge-graph tool with its own `query`/`path`/`explain` CLI, and its
own primary-source benchmark (`BENCHMARKS.md` in their repo) runs on
[frappe/erpnext](https://github.com/frappe/erpnext) — a real ~1M-LOC Python
codebase. Rather than cite either tool's own published numbers, this
directory runs **both tools ourselves**, under one shared agent loop and one
anonymized judge, on the same pinned corpus, and reports what actually
happened — including where Aletheore loses.

A widely-circulated "70%/71.5x token reduction" figure attributed to
Graphify does **not** appear anywhere in Graphify's own repository or
`BENCHMARKS.md`. Their own primary source reports something different: a
lift from 70.8% (grep+read baseline) to 82.0% key-fact coverage, ~140K
tokens/query, and "20x token reduction vs. context-stuffing" — measured
against their own baseline, which is not directly comparable to the
three-condition setup here. We do not use the 70%/71.5x figure anywhere in
this comparison, because we could not trace it to Graphify's own primary
source.

## Results

15 real, independently-authored questions about ERPNext internals (hooks,
validation controllers, budget enforcement, doctype wiring — not published
verbatim from Graphify's own question set, since it isn't public), each run
three times per question — once per condition — through a shared
tool-calling agent loop (`deepseek-v4-flash`, `MAX_TURNS=8`), then scored by
an anonymized judge (same model, 2 runs per item, judge never told which
tool produced an answer):

| condition | coverage (mean, 30 samples) | tokens/query (mean, 15 samples) |
|---|---|---|
| baseline (grep + read + list only) | 92.2% | 11,839 |
| **+ Aletheore** | **100.0%** | 14,893 |
| + Graphify | 93.3% | 17,921 |

A pre-publication whole-branch review caught two problems with an earlier
draft of this table, both corrected here rather than shipped:

**q07's ground truth was wrong.** The original expected fact said the
bypass role was "configured on the Budget"; the real field lives on
**Company** (`erpnext/controllers/budget_controller.py:33-34`,
`frappe.get_cached_value("Company", ...)`). All three conditions had
correctly answered "Company" and were capped at 0.5 against a bad fact —
not a real capability gap. Fixed the fact, re-judged for real (all three
score 1.0 against the corrected fact — `questions.json`'s `rationale` field
documents the correction), and the table above reflects it.

**The coverage gap is mostly one truncation event, not a distributed
lead.** On **q12**, baseline and Graphify both hit `MAX_TURNS=8` without
converging and stored the literal placeholder `"(no final answer - hit
MAX_TURNS)"`; only Aletheore found the answer in time. That's a real,
specific result — Aletheore actually answered a question the other two
timed out on — but it isn't evidence of a broad quality edge. **Excluding
q12**, coverage is baseline 98.8% / Aletheore 100.0% / Graphify 100.0% — a
statistical tie between the two tool-assisted conditions, with 12 of 14
remaining questions scoring 1.0 across the board. Only 2 of 15 questions
discriminate at all once the bad ground truth is fixed.

**The real, robust win is token cost, not coverage.** Excluding q12 (where
Aletheore's one non-converging comparison partner inflates the other side's
apparent efficiency), mean tokens/query: baseline 9,157 / Aletheore 9,803 /
Graphify 15,296 — Aletheore answers for **36% fewer tokens than Graphify**,
consistently, not as an artifact of one question. Median tells the same
story: 7,645 / 8,510 / 11,730.

## A gap in this benchmark itself, found after publishing

Two problems with the comparison above, found while investigating why
Aletheore's win over Graphify was so much narrower than expected given the
two tools' architectures (semantic embeddings vs. pure graph traversal):

**The 15 questions in `questions.json` are all exact-citation lookups that
name the file in the question text** ("In `erpnext/hooks.py`, which
function..."). That's answerable by grep alone - which is exactly why the
grep/read/list baseline already scores 92.2% coverage with zero code
intelligence. Neither tool's real capability gets exercised by a question
whose answer location is already in the prompt.

**The harness didn't record which tool *kind* the agent actually called.**
`aletheore_query_tool` exposes `search-codebase` (the embedding-backed
path the ~19-minute indexing step pays for) alongside `symbol-source` /
`imports` / `imported-by` (pure structural, no embeddings involved at
all). `agent_loop.py`'s `run_one()` only logged cumulative tokens and
turns, never which kind of call the model made - so the published numbers
above cannot actually confirm `search-codebase` was ever invoked, versus
the agent defaulting to structural lookups the whole time (functionally
the same category of thing Graphify's `path`/`explain` graph traversal
gives).

**Fixed, in this order:**

1. `agent_loop.py` now logs `{"tool": ..., "kind": ...}` for every tool
   call in the loop (`tool_calls` on the result dict), carried through
   `run_harness.py` into `harness_results.json`. `score.py`'s summary now
   reports `search_codebase_calls` and `questions_using_search_codebase`
   per condition, so a re-run of the existing `questions.json` can settle
   the "was the semantic path even used" question directly instead of by
   inference.
2. A second, harder question set, `questions_conceptual.json` - the same
   15 underlying facts as `questions.json` (verified against the same
   pinned commit; `expected_key_facts` are identical to their
   `counterpart_id` in `questions.json`, checked by
   `test_questions_conceptual.py`), rephrased as behavior/scenario
   descriptions with every filename, dotted path, and internal variable
   name removed from the question text. A grep-only baseline has nothing
   to grep for. This is the regime where embedding-based semantic search
   is actually supposed to separate from graph traversal or lexical
   search - the original question set never tested it.

**Not yet run** - both require a `DEEPSEEK_API_KEY` this environment
didn't have. To reproduce:

```bash
cd graphify_comparison/scripts
python3 run_harness.py questions_conceptual   # writes results/questions_conceptual_harness_results.json
python3 judge.py questions_conceptual          # writes results/questions_conceptual_judge_results.json
python3 score.py questions_conceptual          # writes results/questions_conceptual_summary.json

# and, to settle the search-codebase question on the *original* set too:
python3 run_harness.py                         # unchanged default, now with tool_calls logged
python3 judge.py
python3 score.py
```

## Where we lose

Nowhere on coverage in the final, corrected numbers — Aletheore ties or
leads Graphify on every question once q07's ground truth is fixed. The
honest caveat is scope: only 2 of 15 questions actually discriminate
between conditions, so "we tie or win" is a real result on this question
set, not a claim that generalizes further than 15 questions on one corpus
supports. On tokens, Aletheore costs more than the grep/read/list baseline
(as expected — a real tool adds real tokens) but meaningfully less than
Graphify.

## Setup time: closed the scan gap, indexing is now the real one

Graphify's `graphify extract . --code-only` builds its full graph — including
its own local embeddings — on ERPNext in **~1 minute**. When we first wrote
this section, Aletheore's equivalent was two separate steps totaling **~23
minutes**: `aletheore scan .` (~4 minutes) plus a separate `aletheore index .`
semantic-embedding pass (~19 minutes, local Ollama `nomic-embed-text`, zero
hosted calls) — a real, significant gap.

We investigated rather than shipped that gap as-is. Profiling the ~4-minute
scan found dead-code detection's dotted-string reference check was **77% of
total scan wall-clock** (181.92s) — an O(candidates × files) regex scan, not
the tree-sitter parsing step a first guess would suspect (7-10s, 3% of
total). Fixed both: parsing parallelized (`ProcessPoolExecutor`) and, the
real lever, dead-code detection's check replaced with an O(files) index —
same matching semantics, verified via parity tests against the original
algorithm plus exact set-equality on real ERPNext output. **Shipped in
aletheore 0.9.5**, verified live against the actual PyPI-installed release,
not the dev branch:

| | total wall-clock |
|---|---|
| before (0.9.4) | 236.02s |
| after (0.9.5, installed from PyPI, re-verified) | 53.23s |

**4.4x faster, real and confirmed** — `aletheore scan .` now costs about the
same order of magnitude as Graphify's entire extract step, not 4 minutes
against their 1.

That leaves indexing as the honest remaining gap. `aletheore index .`
(semantic embedding, a separate step Graphify's extract doesn't need since
its embedding is folded into the same pass) is still **~19 minutes** on this
machine — I/O-bound waiting on local Ollama calls, unaddressed by the
scan fix above since it's a different bottleneck (I/O-bound, not CPU-bound
like parsing). Total local setup is now **~20 minutes**, down from ~23, with
indexing now the dominant piece rather than scan. A follow-up for this is
queued, not yet started.

## Total real cost

The full run — 45 agent-loop calls (harness) + 90 judge calls, all
`deepseek-v4-flash` at DeepSeek's published off-peak rate ($0.22/M input,
$0.66/M output tokens) — cost approximately **$0.19**:

- **Judge: ~$0.008** (near-exact) — the judge's prompts are deterministic
  and reconstructible from `questions.json` + `harness_results.json`, so
  input tokens were counted directly against the real prompt text (32,596
  tokens); output is a small, fixed-shape JSON object, estimated at 1,674
  tokens.
- **Harness: ~$0.177** (estimated) — `agent_loop.py`'s `run_one` records
  only combined `total_tokens` per turn (669,798 total across all 45 calls),
  not a separate prompt/completion split, so an exact per-rate cost isn't
  recoverable after the fact. This estimate assumes a 90%/10% input/output
  split, reasoned from the loop's mechanics: each turn resends the full,
  growing message history as input while producing one bounded completion,
  so input dominates in a multi-turn tool-calling loop. This is a real gap
  in what this benchmark's harness tracks, not a deliberate omission — a
  worthwhile fix for a future run of this suite.

## Methodology

**Corpus:** [frappe/erpnext](https://github.com/frappe/erpnext), GPL-3.0,
pinned at `d6956790d8f8940696783bc7ca85438ecd7d4b6e`, shallow-cloned. Scoped
to `graphify_comparison/` — not registered in the main suite's
`corpora.json`.

**Questions:** 15, in `questions.json`, each with `expected_key_facts` and a
`rationale` written against the real, pinned source (not templated or
placeholder). Graphify's own real question set (n=6, used in their
`BENCHMARKS.md`) isn't published in their repository, so these are
independently authored, not reproduced from theirs.

**Harness:** a ~150-line custom tool-calling loop
(`scripts/agent_loop.py`), `deepseek-v4-flash` throughout, `MAX_TURNS=8`.
Three conditions, each layering one additional tool onto the same
grep/read/list floor every condition gets:
- **baseline** — `grep_tool`, `read_file_tool`, `list_dir_tool` only.
- **+Aletheore** — baseline tools + `aletheore_query_tool`, restricted to
  `search-codebase`/`symbol-source`/`symbols`/`imports`/`imported-by`
  (explicitly excludes `answer`, which would run Aletheore's own internal
  LLM call and corrupt token accounting).
- **+Graphify** — baseline tools + `graphify_query_tool`
  (`query`/`path`/`explain`).

**Judge:** anonymized single-candidate scoring (`scripts/judge.py`), adapted
from this repo's `pr_review/blind_judge.py` pattern — the judge is never
told which condition produced an answer, one candidate scored per call (a
prior multi-arm-per-call design silently dropped labels 53/97 times), 2
runs per item for the documented judge-noise floor.

## Reproducing

```bash
git clone https://github.com/Aletheore/aletheore-benchmarks
cd aletheore-benchmarks
git checkout graphify-comparison

pip install aletheore
pipx install graphifyy   # real PyPI name is graphifyy (double-y)

cd graphify_comparison/scripts
python3 clone_corpus.py                 # shallow-clones ERPNext at the pinned commit

cd "$(python3 -c 'from clone_corpus import ensure_corpus; print(ensure_corpus())')"
aletheore scan .
aletheore index .                       # needs local Ollama with nomic-embed-text,
                                         # or an OPENAI_API_KEY fallback (interactive confirm)
graphify extract . --code-only

cd -   # back to graphify_comparison/scripts
python3 setup_tools.py                  # smoke test — both CLIs verified end-to-end

export DEEPSEEK_API_KEY=...
python3 run_harness.py                  # real cost: ~$0.18, 45 calls
python3 judge.py                        # real cost: ~$0.01, 90 calls
python3 score.py                        # writes results/summary.json
```
