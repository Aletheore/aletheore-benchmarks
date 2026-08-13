# Aletheore benchmarks

Reproducible evaluation of Aletheore's code retrieval and generated
documentation, measured head-to-head against RepoWise.

Every number here can be recomputed from the raw results in `results/` with no
API key and no network. The harness, the questions, the ground truth and the
losses are all in this repository.

## Results

### Locating code — "which file implements X?"

Aletheore indexes code chunks and returns `file:line`.

Measured on **Aletheore 0.8.5 installed from PyPI**, each corpus re-scanned and
re-indexed from scratch, local `nomic-embed-text` embeddings, no API key:

| corpus | language | top-1 | top-3 | top-5 | MRR | n |
|---|---|---|---|---|---|---|
| gin | Go | **80.0%** | 100% | 100% | 0.878 | 15 |
| flask | Python | **68.8%** | 93.8% | 100% | 0.816 | 32 |
| serde | Rust | **53.3%** | 66.7% | 73.3% | 0.617 | 15 |
| Slim | PHP | **26.7%** | 60.0% | 66.7% | 0.458 | 15 |

Raw per-query output for all four is in `results/results_*_0.8.5.json`.

**PHP is our weakest language and the table says so.** Every one of Slim's six
top-5 misses is a topical *sibling* of the right answer — asked where route
arguments reach the handler, we return `RequestResponseNamedArgs.php` and
`RequestResponseArgs.php` but not the `RequestResponse.php` they are variants
of. The canonical file is crowded out by its own near-duplicates. An
import-authority prior was tried against this and rejected: it fixed the PHP
case but cost flask 6.2 points of top-1, which is a bad trade.

**These numbers replace an earlier table that did not reproduce.** The previous
revision listed flask at 71.9% / 96.9% / 100%, which matched no committed
results file — it blended top-1 from one run with top-3 and top-5 from another.
Re-running the published harness against every 0.8.x release produces 65.6% /
93.8% / 100% for that code, and 68.8% / 93.8% / 100% for 0.8.5. The lesson is
recorded in **METHODOLOGY.md** rather than quietly corrected.

Head-to-head on flask, same questions and ground truth:

| | top-1 | top-3 | top-5 |
|---|---|---|---|
| **Aletheore 0.8.5** | **68.8%** | **93.8%** | **100%** |
| RepoWise `--mode semantic` | 28.1% | 56.2% | 56.2% |
| RepoWise `--mode fulltext` | 21.9% | 56.2% | 65.6% |
| RepoWise, best mode per question (unachievable) | 40.6% | 71.9% | 78.1% |

The RepoWise rows are from the original run and are unchanged; only Aletheore's
row was re-measured, against the same corpus commit and the same 32 questions.
An earlier revision of this table put Aletheore at 75.0% / 90.6% / 96.9% from a
pre-0.8.0 build. Top-1 fell across the 0.8.x hardening work and top-5 rose;
both directions are shown rather than the flattering half.

### Explaining code — "how does X work?"

Blind LLM judge, 0-3, each question graded twice with the two systems' positions
swapped, equal 12,000-character context budget, tool names scrubbed.

| | score | gap | tokens | cost |
|---|---|---|---|---|
| AIRview | 2.13 | 0.22 | 114K | ~$0.025 |
| **RepoWise** | **2.35** | — | 808K | $0.175 |

**RepoWise wins this half.** We sit within roughly 0.2 of them at about one
seventh the cost, having closed a gap that started at 1.33.

These wiki figures were measured on a pre-0.8.0 build and have **not** been
re-run on 0.8.5. They are left as measured rather than restated against a
version they did not come from; only the retrieval tables above are 0.8.5.

### Where we lose

Stated here rather than in a footnote:

- **RepoWise retrieval is faster in-process** — 68 ms against our 125 ms.
- **RepoWise's wiki scores higher**, in every configuration tested.
- **PHP is our weakest language** at 26.7% top-1, against 80.0% for Go, and the
  cause is understood and unfixed — see the note under the retrieval table.
- **An earlier revision of this README published flask figures that did not
  reproduce.** They are corrected above, and how it happened is in
  METHODOLOGY.md.

We win on locating code, and on setup cost ($0.00 / 74 s against $0.18 / ~7 min).

## Reproducing

**Aletheore v0.8.5.** Every retrieval result above was produced by that release,
installed from PyPI exactly as written below.

Do not substitute 0.8.0 through 0.8.4. Those tags exist on GitHub but were never
published: their `pyproject.toml` was frozen at `0.7.2` while the code advanced,
so no artefact could be uploaded and `pip install aletheore==0.8.0` fails. 0.8.5
is the first release in the line that installs, and the first whose
`aletheore --version` reports its own version.

```bash
pip install "aletheore==0.8.5"

git clone https://github.com/pallets/flask /tmp/bench-flask
git -C /tmp/bench-flask checkout 2a8a38b051fc248865730bf3511bf2e2ea325e81

python3 scripts/verify_ground_truth.py          # must print 32/32
cd /tmp/bench-flask && aletheore scan . && aletheore index .
cd - && python3 scripts/run_aletheore.py
python3 scripts/score.py results/results_aletheore.json=ALETHEORE
```

`corpora.json` pins every corpus commit. Runners refuse to score against a
different checkout, because the ground truth was verified against those exact
trees. See **REPRODUCIBILITY.md** for tool versions and for what reproduces
exactly versus what does not.

The RepoWise half needs an LLM key and, importantly, `REPOWISE_EMBEDDER=ollama`
— without it `repowise search --mode semantic` silently degrades to full-text.
That defect invalidated our own first run.

## Contents

| path | what |
|---|---|
| `questions/` | 101 questions across 6 sets, every ground-truth anchor mechanically verified |
| `scripts/` | runners, scorers, the blind judge, the language-coverage matrix |
| `results/` | raw per-query output — recompute any number without an API key |
| `corpora.json` | pinned commits for all corpora |
| `CORPUS_PLAN.md` | the 11-language programme: repos, procedure, cost, and what was rejected |
| `METHODOLOGY.md` | full method, every adjustment made in RepoWise's favour, errors caught in our own runs |
| `REPRODUCIBILITY.md` | versions; what reproduces bit-for-bit and what does not |
| `LANGUAGE_COVERAGE.md` | scanner coverage across all 11 supported languages |
| `AIRVIEW_GAP.md` | why our generated wiki lost, what changed, and what did not work |

## Honesty notes

**The questions were authored by us.** They are sourced from each project's
public API and documentation, and every ground-truth anchor is verified
mechanically, but this remains the weakest link in the methodology. An
independently authored question set would be stronger evidence, and is the most
useful contribution anyone could make here.

**Judge scores are not independent.** The judge grades both systems in one
prompt, so an absolute score moves depending on what it is compared against:
RepoWise scored 2.35 against one configuration and 2.25 against another on
byte-identical input. Only the within-run gap is comparable across
configurations.

**Scope is small.** Four languages measured for retrieval, one repository for
the wiki comparison, 101 questions in total. RepoWise's own published benchmark
spans 21 repositories and 9 languages; we are not claiming parity of coverage.

## Licence

MIT. See LICENSE.
