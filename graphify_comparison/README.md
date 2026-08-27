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
| baseline (grep + read + list only) | 88.9% | 11,839 |
| **+ Aletheore** | **96.7%** | 14,893 |
| + Graphify | 91.7% | 17,921 |

Aletheore beats Graphify on both axes measured here: **+5.0 points of
coverage** and **17% fewer tokens per query** (14,893 vs. 17,921). Both
tool-assisted conditions beat the grep/read/list baseline on coverage, at a
real token cost over it.

## Where we lose

Stated plainly, not softened: on **q07** ("what lets a user bypass a 'Stop'
budget action and get only a warning instead?"), the judge scored
Aletheore's answer at 0.50 — tied with baseline — against Graphify's 0.75.
Reading the three raw answers side by side
(`results/harness_results.json`), Aletheore's and Graphify's both correctly
identify the exact mechanism (`self.exception_approver_role`, checked via
`frappe.get_roles(frappe.session.user)` in `BudgetValidation.execute_action`)
with the same specificity and a code citation. We can't rule out this being
the judge-noise floor this benchmark suite has documented elsewhere
(0.2–0.375 drift on identical input across repeated judge calls) rather than
a real quality gap — but we're reporting the score as scored, not
explaining it away.

## Setup time: an honest loss, only partially addressed

Graphify's `graphify extract . --code-only` builds its full graph — including
its own local embeddings — on ERPNext in **~1 minute**. Aletheore's
equivalent is two separate steps: `aletheore scan .` (~4 minutes) plus a
separate `aletheore index .` semantic-embedding pass (~19 minutes on this
machine, local Ollama `nomic-embed-text`, zero hosted calls) — **~23 minutes
total**, a real and significant gap in the other tool's favor.

We looked into closing it before publishing rather than after. A known,
previously-deferred fix — parallelizing `build_module_graph`'s tree-sitter
parsing with `ProcessPoolExecutor` (`ThreadPoolExecutor` doesn't help there;
tree-sitter's Python binding holds the GIL) — shipped and is live on master.
Measured with real, fresh (no-cache) full `aletheore scan .` wall-clock runs
on this same pinned ERPNext checkout:

| | total wall-clock | parsing phase alone |
|---|---|---|
| sequential (pre-fix) | 239.03s | 10.47s |
| parallel (current, merged) | 236.02s | 7.18s |

The fix is real: parsing itself got **~30% faster** (10.47s → 7.18s). But
it only moves the total by **~3 seconds — about 1.3%** — because parsing was
never the dominant cost. A full per-phase breakdown of the parallel run
shows why:

| phase | time | share |
|---|---|---|
| **dead-code detection** | **181.92s** | **77%** |
| secrets scan (working tree) | 14.75s | 6% |
| secrets scan (git history) | 12.19s | 5% |
| endpoint mapping | 11.90s | 5% |
| module parsing (parallel) | 7.18s | 3% |
| clustering / layer analysis | 1.79s | <1% |
| wrap-up | 2.11s | <1% |
| git hotspots | 0.53s | <1% |
| git history / ownership | 0.41s | <1% |
| OSV.dev dependency lookup | 0.15s | <1% |
| license detection | ~0.1s | <1% |

Dead-code detection alone is three-quarters of the scan's wall-clock time on
this corpus — not parsing, and not OSV.dev's network calls (0.15s here, a
non-issue for this corpus at least). That's the honest answer to "why is
Aletheore's scan slower than Graphify's extract": we haven't investigated
*why* dead-code detection costs what it does yet, so we're not claiming a
fix, just reporting where the time actually goes. It's the next real lever
if closing this gap further matters, not the parsing step this fix already
addressed.

The separate `aletheore index` step (embedding, not parsing) is a different,
I/O-bound bottleneck — waiting on local Ollama calls, not CPU-bound like the
scan — and is unaddressed by this fix. It's a queued follow-up, not yet
started.

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
