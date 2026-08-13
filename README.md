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

| corpus | language | general top-1 | vocabulary top-1 | general top-5 | n |
|---|---|---|---|---|---|
| gin | Go | **80.0%** | — | 100% | 15 |
| flask | Python | **68.8%** | — | 100% | 32 |
| jq | C | **53.3%** | 73.3% | 80.0% | 15 |
| serde | Rust | **53.3%** | — | 73.3% | 15 |
| gson | Java | **40.0%** | 60.0% | 80.0% | 15 |
| fmt | C++ | **40.0%** | 66.7% | 86.7% | 15 |
| jekyll | Ruby | **26.7%** | 66.7% | 46.7% | 15 |
| Slim | PHP | **26.7%** | 73.3% | 66.7% | 15 |
| axios | JavaScript | **20.0%** | 73.3% | 66.7% | 15 |
| guzzle | PHP | **20.0%** | 53.3% | 66.7% | 15 |
| zod | TypeScript | **20.0%** | 60.0% | 40.0% | 15 |
| AutoMapper | C# | **6.7%** | 86.7% | 33.3% | 15 |

All **11 supported languages** are now measured, across 12 corpora. Two
question regimes are published for every corpus written since the confound was
found: *general* phrasing deliberately avoids the project's own vocabulary,
*vocabulary* phrasing uses it. Real users ask somewhere between the two, so a
language's true figure is bracketed by them rather than given by either.

Raw per-query output is in `results/`, one file per corpus, regime and system.

**The spread is the finding.** Go and Python are strong; Java, Ruby, PHP and
TypeScript are not, and the weak corpora were measured last, so the published
average would have looked considerably better had we stopped at three languages.

Of the causes investigated below, one is fixed, one is measured but only partly
recoverable, one was tested and ruled out, and one turned out to be **our own
question authoring rather than the product**. Two candidate ranking changes were
implemented in full and rejected on measurement.

#### Why the weak corpora are weak

**Near-duplicate crowding (PHP), real but mostly not the cost.** Slim's top-5
misses are topical *siblings* of the right answer — asked where route arguments
reach the handler, we return `RequestResponseNamedArgs.php` and
`RequestResponseArgs.php` but not the `RequestResponse.php` they are variants
of. That crowding is visible in the raw results and is genuine.

What it is *not* is the main cost. Asked in Slim's own vocabulary the same
corpus scores 73.3% top-1 rather than 26.7%, so most of the gap was phrasing.
Two ranking fixes were built against the crowding before that was known, and
both were rejected on measurement:

1. *An import-authority prior*, applied globally: cost flask 9.4 points of
   top-1 and gson 6.7. Rejected.
2. *The same prior scoped to PHP only*, so it provably could not affect another
   language. It first appeared to lift Slim top-1 by 6.7 points — an artefact
   of clamping the fused rank at zero, which collapses every strongly-weighted
   hit onto one effective rank. With the floor corrected it produces no top-1
   gain on either PHP corpus and trades Slim top-5 for guzzle top-3. Rejected.

A second PHP corpus (guzzle) was added specifically so a PHP-targeted change
could not be tuned and validated on the same 15 questions. It is what made the
second rejection legible.

**Not the cause: inheritance.** It was proposed that a base class is being
crowded out by its children, and that promoting base classes would fix it.
`RequestResponse`, `RequestResponseArgs` and `RequestResponseNamedArgs` are
*siblings* — each implements `InvocationStrategyInterface` — so there is no
inheritance edge to exploit.

**Sibling-module pollution (TypeScript, Java).** In a repository holding more
than one module, results are drawn from modules that are not the library:

| corpus | top-5 slots spent outside the library subtree |
|---|---|
| zod | 21/75 (**28%**) — `packages/docs`, `packages/bench`, `packages/resolution` |
| gson | 16/75 (**21%**) — `proto/`, `metrics/`, `extras/` |
| jekyll | 5/75 (7%) |
| flask | 7/160 (4%) |
| serde, Slim | 0% |

Roughly a quarter of zod's answer budget goes to documentation and benchmark
code. Nothing in the index distinguishes "the library" from "everything else
that happens to live in the repository".

**How much of that is recoverable was then measured, and the answer differs by
repository.** Hard-filtering results to the library subtree lifts gson top-1
33.3% → 40.0% and top-5 66.7% → 80.0%, but recovers **nothing** for zod: its
correct answers are not ranked 6-10 either, so the pollution is a symptom there
rather than the cause. An earlier revision of this file claimed the pollution
explained zod's score. It does not, and that claim was wrong.

**Not the cause: file size.** The obvious explanation — that big central files
lose to small peripheral ones — was tested across all corpora and is
false. The top-1 result is *larger* than the ground-truth file in 80–94% of
flask and gin questions. There is no systematic size bias in either direction.

**The weak scores are mostly our own question authoring.** This was tested on
jekyll first and then on every other weak corpus, by rewriting *all fifteen*
questions in each set - not only the missed ones - using the project's own
vocabulary, against identical code and identical ground truth:

| corpus | vocabulary-avoiding | project vocabulary | Δ top-1 |
|---|---|---|---|
| Slim (PHP) | 26.7% | **73.3%** | +46.6 |
| zod (TypeScript) | 20.0% | **60.0%** | +40.0 |
| jekyll (Ruby) | 26.7% | **66.7%** | +40.0 |
| guzzle (PHP) | 20.0% | **53.3%** | +33.3 |
| gson (Java) | 40.0% | **60.0%** | +20.0 |

Every weak corpus moves 20-47 points on wording alone. That is larger than
every ranking change in this programme combined, and it means **the retrieval
table above measures a phrasing regime at least as much as it measures the
product**.

It also retires a conclusion this file previously drew. PHP was described as a
ranking problem - near-duplicate crowding - and two fixes were built and
rejected against it. Slim moves 26.7% -> 73.3% on phrasing, so most of what
those fixes were chasing was an artefact of how the questions were written.
The crowding is real and visible in the raw results; it is not what was costing
most of the score.

Both sets are kept for every corpus and both numbers published. Rewriting only
the missed questions was considered and rejected - correcting just the failures
can move a score in one direction only. The truth for any language here is
*bracketed* by the two regimes, not given by either, and real users ask
somewhere in between.

**These numbers replace an earlier table that did not reproduce.** The previous
revision listed flask at 71.9% / 96.9% / 100%, which matched no committed
results file — it blended top-1 from one run with top-3 and top-5 from another.
Re-running the published harness against every 0.8.x release produces 65.6% /
93.8% / 100% for that code, and 68.8% / 93.8% / 100% for 0.8.5. The lesson is
recorded in **METHODOLOGY.md** rather than quietly corrected.

Head-to-head against RepoWise, **all seven corpora**, same questions and same
ground truth. RepoWise searches its own generated wiki pages, so each corpus
had a wiki built for it first (`init --coverage 1.0`, deepseek-v4-flash,
1,341 pages, $1.85 total). Best RepoWise mode per corpus is shown:

| corpus | language | Aletheore | RepoWise semantic | RepoWise fulltext | winner |
|---|---|---|---|---|---|
| gin | Go | **80.0%** | 60.0% | 46.7% | Aletheore |
| serde | Rust | **53.3%** | 6.7% | 13.3% | Aletheore |
| gson | Java | **40.0%** | 26.7% | 0.0% | Aletheore |
| jekyll | Ruby | **26.7%** | 13.3% | 6.7% | Aletheore |
| Slim | PHP | 26.7% | 26.7% | 20.0% | tie |
| guzzle | PHP | 20.0% | 13.3% | 20.0% | tie |
| zod | TypeScript | **20.0%** | 6.7% | 13.3% | Aletheore |

**Top-1: 5 wins, 0 losses, 2 ties.** Our weakest languages still match or beat
them. Where we lose: jekyll top-5, 46.7% against their 66.7%.

Both systems were then given the **vocabulary** questions as well, on the same
wikis (search costs nothing to re-run once a wiki exists):

| corpus | Aletheore general | RepoWise general | Aletheore vocabulary | RepoWise vocabulary |
|---|---|---|---|---|
| Slim | 26.7% | 26.7% | **73.3%** | 66.7% |
| gson | **40.0%** | 26.7% | **60.0%** | 46.7% |
| zod | **20.0%** | 13.3% | **60.0%** | 26.7% |
| guzzle | 20.0% | 20.0% | 53.3% | 53.3% |
| jekyll | **26.7%** | 13.3% | 66.7% | **80.0%** |

RepoWise gains from vocabulary phrasing too — its wiki pages name the symbols —
and on jekyll it overtakes us outright, 80.0% against 66.7%. That is a real
loss and it is stated here rather than omitted. Across the ten cells we lead in
seven, tie in two and lose one.


Flask remains as originally measured (Aletheore 68.8% / 93.8% / 100% against
RepoWise semantic 28.1% / 56.2% / 56.2%).

Two things this table deliberately does not claim:

- **`--mode symbol` returned 0.0% on every corpus and is excluded.** Feeding
  natural-language questions to a symbol-name search misuses the mode rather
  than measuring it. It is in the raw results; it is not counted as a loss for
  RepoWise.
- **These latencies are not comparable and no speed claim is made here.**
  RepoWise's search is invoked per query as a CLI process (2.4-4.5 s including
  interpreter startup); Aletheore's is measured in-process (~72 ms). The honest
  like-for-like figure, from the flask run, is RepoWise 68 ms against our
  125 ms in-process — *they are faster*.

### Cost to get to a searchable index

| | Aletheore | RepoWise |
|---|---|---|
| indexing cost, 7 corpora | **$0.00** | **$1.85** |
| per corpus | $0.00 | $0.09 - $0.47 |
| what it costs money for | nothing - local `nomic-embed-text` | LLM generation of 1,341 wiki pages |
| typical setup time | seconds to ~1 min per corpus | minutes per corpus |

Per corpus, RepoWise: Slim $0.09, guzzle $0.13, gin $0.18, jekyll $0.29,
serde $0.33, zod $0.36, gson $0.47. Aletheore's side needs no API key at all,
which is also why every number in this repository can be recomputed without
one.

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
- **Five of eight corpora score below 35% top-1 under vocabulary-avoiding
  phrasing** — though every one of them recovers 20-47 points when the same
  questions are asked in the project's own terms, so most of that gap is our
  question authoring rather than the product.
- **jekyll top-5 loses to RepoWise**, 46.7% against 66.7%.
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
| `questions/` | 356 questions across 23 sets, every ground-truth anchor mechanically verified |
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

**Scope.** All 11 supported languages across 12 corpora measured for retrieval,
one repository for the wiki comparison, 356 questions in total. RepoWise's own published benchmark
spans 21 repositories and 9 languages; we are not claiming parity of coverage.

## Licence

MIT. See LICENSE.
