<div align="center">

# Aletheore Benchmarks

<p>
  <img src="https://img.shields.io/badge/License-MIT-059669?style=for-the-badge&labelColor=0A0A0A" alt="License: MIT" />
  <img src="https://img.shields.io/badge/Languages-13-1E293B?style=for-the-badge&labelColor=0A0A0A" alt="13 languages" />
  <img src="https://img.shields.io/badge/Corpora-12-1E293B?style=for-the-badge&labelColor=0A0A0A" alt="12 corpora" />
  <img src="https://img.shields.io/badge/Questions-418-1E293B?style=for-the-badge&labelColor=0A0A0A" alt="418 questions" />
  <img src="https://img.shields.io/badge/API_key-not_required-1E293B?style=for-the-badge&labelColor=0A0A0A" alt="No API key required" />
</p>

### Reproducible evaluation of Aletheore's code retrieval and generated documentation, measured head-to-head against RepoWise.

<sub>Every number here can be recomputed from the raw results in <code>results/</code> with no API key and no network.<br/>The harness, the questions, the ground truth and the losses are all in this repository.<br/>Every subdirectory's full write-up is inlined below too, in a "Full write-up" expandable section right next to its summary — open one to read it, no need to leave this page.</sub>

<p><sub>
  <a href="#locating-code--which-file-implements-x">Locating code</a> ·
  <a href="#hosted-embeddings-jina-vs-local-nomic">Hosted vs local</a> ·
  <a href="#head-to-head-against-repowise">Head-to-head</a> ·
  <a href="#cost-to-get-to-a-searchable-index">Cost</a> ·
  <a href="#covering-the-files-a-pr-touches">PR coverage</a> ·
  <a href="#pr-review--compact-evidence-vs-full-file-context">PR review</a> ·
  <a href="#head-to-head-against-pr-agent">PR-Agent comparison</a> ·
  <a href="#per-file-completeness-generation-named-vs-real-competitors">Per-file completeness</a> ·
  <a href="#the-external-pr-recall-benchmark">External PR Recall Benchmark</a> ·
  <a href="#explaining-code--how-does-x-work">Explaining code</a> ·
  <a href="#deterministic-analysis-vs-bare-llm">Deterministic vs. LLM</a> ·
  <a href="#deterministic-scanner-accuracy">Scanner accuracy</a> ·
  <a href="#head-to-head-against-graphify-erpnext">Graphify comparison</a> ·
  <a href="#where-we-lose">Where we lose</a> ·
  <a href="#reproducing">Reproducing</a> ·
  <a href="#contents">Contents</a>
</sub></p>

---

<table align="center">
<tr>
<td align="center" width="240"><h2>5–0–2</h2></td>
<td align="center" width="240"><h2>$0.00</h2></td>
<td align="center" width="240"><h2>93.3%</h2></td>
</tr>
<tr>
<td align="center" valign="top"><sub><strong>head-to-head vs RepoWise.</strong><br />5 wins, 0 losses, 2 ties on top-1<br />locating code, all 7 shared corpora.</sub></td>
<td align="center" valign="top"><sub><strong>to build a searchable index,</strong><br />all 7 corpora — local <code>nomic-embed-text</code>,<br />vs RepoWise's $1.85 for the same set.</sub></td>
<td align="center" valign="top"><sub><strong>cross-language top-5,</strong><br />up from 60.0% after fixing a language<br />pre-filter that was silently unused.</sub></td>
</tr>
</table>

<sub>Measured on <strong>Aletheore 0.8.11</strong>, installed from PyPI, against RepoWise's own generated wiki.<br/><strong>We publish the rows we lose</strong> — see <a href="#where-we-lose">Where we lose</a>.</sub>

</div>

---

## Locating code — "which file implements X?"

Aletheore indexes code chunks and returns `file:line`.

Measured in one run with **Aletheore 0.8.11 installed from PyPI**, each corpus
re-scanned and re-indexed from scratch with local `nomic-embed-text` (768-dim)
embeddings, no API key:

| corpus | regime | top-1 | top-3 | top-5 | MRR | n |
|---|---|---:|---:|---:|---:|---:|
| location (Flask) | general | 71.9% | 93.8% | 100.0% | 0.832 | 32 |
| gin | general | 80.0% | 100.0% | 100.0% | 0.878 | 15 |
| serde | general | 53.3% | 66.7% | 73.3% | 0.617 | 15 |
| Slim | general | 26.7% | 60.0% | 66.7% | 0.458 | 15 |
| Slim | vocabulary | 73.3% | 80.0% | 93.3% | 0.797 | 15 |
| guzzle | general | 20.0% | 53.3% | 66.7% | 0.374 | 15 |
| guzzle | vocabulary | 53.3% | 93.3% | 100.0% | 0.728 | 15 |
| jekyll | general | 26.7% | 33.3% | 46.7% | 0.337 | 15 |
| jekyll | vocabulary | 66.7% | 86.7% | 93.3% | 0.778 | 15 |
| zod | general | 20.0% | 40.0% | 40.0% | 0.289 | 15 |
| zod | vocabulary | 60.0% | 73.3% | 73.3% | 0.667 | 15 |
| gson | general | 40.0% | 66.7% | 80.0% | 0.544 | 15 |
| gson | vocabulary | 60.0% | 86.7% | 86.7% | 0.749 | 15 |
| axios | general | 20.0% | 46.7% | 66.7% | 0.407 | 15 |
| axios | vocabulary | 73.3% | 93.3% | 100.0% | 0.850 | 15 |
| jq | general | 53.3% | 66.7% | 80.0% | 0.648 | 15 |
| jq | vocabulary | 73.3% | 100.0% | 100.0% | 0.867 | 15 |
| fmt | general | 40.0% | 60.0% | 86.7% | 0.527 | 15 |
| fmt | vocabulary | 66.7% | 93.3% | 93.3% | 0.789 | 15 |
| AutoMapper | general | 6.7% | 20.0% | 33.3% | 0.177 | 15 |
| AutoMapper | vocabulary | 86.7% | 100.0% | 100.0% | 0.933 | 15 |
| thrift | general | 6.7% | 33.3% | 53.3% | 0.241 | 15 |
| thrift | cross-language | 53.3% | 73.3% | 93.3% | 0.677 | 15 |

The audit file has no 0.8.11 result line for `thrift_anylang`, so this table
does not invent one; its two published Thrift rows are reproduced exactly.

All **11 supported languages** are now measured, across 12 single-language
corpora plus Thrift's published regimes — including
`apache/thrift`, the first genuinely polyglot corpus (eight languages, none
above a third of the modules), which implements the same protocol separately in
each language and so tests whether retrieval can tell one language's
implementation from another's. Two
question regimes are published for every corpus written since the confound was
found: *general* phrasing deliberately avoids the project's own vocabulary,
*vocabulary* phrasing uses it. Real users ask somewhere between the two, so a
language's true figure is bracketed by them rather than given by either.

```mermaid
xychart-beta
    title "The phrasing confound: top-1 for the same questions, project vocabulary vs avoiding it"
    x-axis [Slim, zod, jekyll, guzzle, gson]
    y-axis "Top-1 accuracy (%)" 0 --> 100
    bar "vocabulary-avoiding" [26.7, 20.0, 26.7, 20.0, 40.0]
    bar "project vocabulary" [73.3, 60.0, 66.7, 53.3, 60.0]
```

**Every weak corpus moves 20-47 points on wording alone** — larger than every
ranking change in this programme combined. It means the retrieval table above
measures a phrasing regime at least as much as it measures the product. Both
regimes are kept and published for every corpus; a language's true figure is
bracketed by the two rather than given by either.

Raw per-query output is in `results/`, one file per corpus, regime and system.
The ten pre-existing corpus rows are unchanged by 0.8.7-0.8.11 work outside
their targets; the two changed rows are Gson top-3 (73.3% → 66.7%) and
AutoMapper top-3 (13.3% → 20.0%), both from #236.

**The spread is the finding.** Go and Python are strong; Java, Ruby, PHP and
TypeScript are not, and the weak corpora were measured last, so the published
average would have looked considerably better had we stopped at three languages.

```mermaid
%%{init: {"xyChart": {"width": 1000, "height": 500}}}%%
xychart-beta
    title "Top-1, general phrasing, by corpus - the spread the average hides"
    x-axis [gin, flask, serde, jq, gson, fmt, Slim, jekyll, zod, axios, AutoMapper, thrift]
    y-axis "Top-1 accuracy (%)" 0 --> 100
    bar [80.0, 71.9, 53.3, 53.3, 40.0, 40.0, 26.7, 26.7, 20.0, 20.0, 6.7, 6.7]
```

Of the causes investigated below, one is fixed, one is measured but only partly
recoverable, one was tested and ruled out, and one turned out to be **our own
question authoring rather than the product**. Two candidate ranking changes were
implemented in full and rejected on measurement.

<details>
<summary><strong>Asking in one language and being answered in another</strong> — the one defect that survives good phrasing</summary>

`apache/thrift` implements the same protocol separately in eight languages, so a
question naming one has a single correct answer and seven near-identical wrong
ones. A third regime, `thrift_crosslang.json`, tests exactly that: full project
vocabulary plus an explicit language, so the only difficulty is picking the
right language's file.

Measured on 0.8.10, five of six failures returned a **different language's file
entirely** — C++ missed all three of its questions, returning Python and .NET
implementations instead. The cause was not ranking: `search_index` already
accepted a `language` pre-filter, and nothing ever populated it, so the language
named in the question competed only as ordinary text.

| regime | metric | 0.8.10 | 0.8.11 |
|---|---|---|---|
| cross-language | top-3 | 60.0% | **73.3%** |
| cross-language | top-5 | 60.0% | **93.3%** |
| cross-language | MRR | 0.576 | **0.677** |
| general | top-5 | 40.0% | **53.3%** |

This is the one defect found here that the phrasing confound does **not**
explain: the cross-language questions already use full vocabulary, so the
failure survives good questions. The fix raises cross-language top-5 from
60.0% to **93.3%**. It is also invisible to every single-language
corpus, which is what the polyglot corpus was added to find.

Detection only fires when a query names a language, and across all 356
single-language questions in this repository it fires on two, both in flask
naming Python, whose results are unchanged to three decimals of MRR.

</details>

<details>
<summary><strong>Why the weak corpora are weak</strong> — near-duplicate crowding, sibling-module pollution, and the phrasing test that explained most of it</summary>

**Near-duplicate crowding is recorded as a phrasing symptom, not a live ranking
lead.** The apparent sibling pollution in Slim, Gson and Thrift was checked
against the vocabulary regimes: the misses disappear when the question names
the project's own symbols. Two ranking fixes were built and rejected on
measurement. The finding and its falsification are recorded in
`METHODOLOGY.md`; no further ranking work should treat crowding as the leading
explanation without new evidence.

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

```mermaid
xychart-beta
    title "Top-5 answer slots spent outside the library subtree"
    x-axis [zod, gson, jekyll, flask, serde, Slim]
    y-axis "Share of top-5 slots (%)" 0 --> 30
    bar [28, 21, 7, 4, 0, 0]
```

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

It also retires a conclusion this file previously drew. PHP was initially
described as a ranking problem - near-duplicate crowding - and two fixes were
built and rejected against it. Slim moves 26.7% → 73.3% on phrasing, so most
of what those fixes were chasing was an artefact of how the questions were
written. The finding is recorded in `METHODOLOGY.md` as a phrasing symptom,
not a live ranking lead.

Rewriting only the missed questions was considered and rejected - correcting
just the failures can move a score in one direction only.

**These numbers replace an earlier table that did not reproduce.** The previous
revision listed flask at 71.9% / 96.9% / 100%, which matched no committed
results file — it blended top-1 from one run with top-3 and top-5 from another.
Re-running the published harness against every 0.8.x release produced the
earlier 65.6% / 93.8% / 100% and 68.8% / 93.8% / 100% figures for 0.8.5. The
current table is the single 0.8.11 PyPI run from `/private/tmp/audit-0811.txt`;
the lesson is recorded in **METHODOLOGY.md** rather than quietly corrected.

</details>

## Hosted embeddings: jina vs local nomic

> **This section does not carry the same "no API key, no network" guarantee
> as the rest of this repository.** It measures Aletheore's *hosted*
> embedding endpoint (`jina-embeddings-v2-base-code`, Q8_0 GGUF via
> llama.cpp), which requires `aletheore login` and a paid plan. It was run
> against a dev checkout at commit
> [`e2cc409`](https://github.com/Aletheore/Aletheore/commit/e2cc409),
> not a PyPI release — everything else in this repository is 0.8.11 from
> PyPI; this section is the one exception, and is labeled as one rather than
> folded into the reproducible table above.

Same 13 corpora, same 23 corpus/regime pairs, same questions and ground
truth as the table above - only the embedder changed, local `nomic-embed-text`
(768-dim) to hosted `jina-embeddings-v2-base-code` (768-dim). Includes
`apache/thrift`, which timed out getting a hosted index built at all until
[`#264`](https://github.com/Aletheore/Aletheore/pull/264) fixed a crash in
`jina-embed` under concurrent access - see that PR, and
[`jina_embed/server.py`](https://github.com/Aletheore/Aletheore/blob/master/github-app/jina_embed/server.py),
for what changed server-side since the CLI checkout commit cited above.

```mermaid
%%{init: {"xyChart": {"width": 1700, "height": 550}}}%%
xychart-beta
    title "Top-1 change, hosted jina vs local nomic (points, +better -worse)"
    x-axis [flask, gin, serde, Slim-g, Slim-v, guzzle-g, guzzle-v, jekyll-g, jekyll-v, zod-g, zod-v, gson-g, gson-v, axios-g, axios-v, jq-g, jq-v, fmt-g, fmt-v, AutoMapper-g, AutoMapper-v, thrift-g, thrift-x]
    y-axis "Δ top-1 (percentage points)" -10 --> 30
    bar [9.3, 6.7, 0.0, 26.6, -6.6, 0.0, 20.0, 0.0, 0.0, -6.7, -6.7, 6.7, 6.7, 0.0, 6.7, 0.0, 6.7, 6.7, 0.0, 6.6, 0.0, 13.3, 20.0]
```

<sub>`-g` = general phrasing, `-v` = vocabulary phrasing, `thrift-x` = cross-language regime - see the corpus table below for the full names.</sub>

**Mean: top-1 +5.0pp, MRR +0.049. 20 of 23 rows flat or better; 3 worse, all
in either Slim's vocabulary regime or zod.**

| corpus | nomic top-1 | jina top-1 | Δ top-1 | nomic MRR | jina MRR | |
|---|---:|---:|---:|---:|---:|:-:|
| flask (location) | 71.9% | 81.2% | +9.3pp | 0.832 | 0.901 | ✅ |
| gin | 80.0% | 86.7% | +6.7pp | 0.878 | 0.933 | ✅ |
| serde | 53.3% | 53.3% | +0.0pp | 0.617 | 0.678 | 🟰 |
| Slim (general) | 26.7% | 53.3% | +26.6pp | 0.458 | 0.647 | ✅ |
| Slim (vocab) | 73.3% | 66.7% | -6.6pp | 0.797 | 0.811 | ⚠️ |
| guzzle (general) | 20.0% | 20.0% | +0.0pp | 0.374 | 0.458 | 🟰 |
| guzzle (vocab) | 53.3% | 73.3% | +20.0pp | 0.728 | 0.844 | ✅ |
| jekyll (general) | 26.7% | 26.7% | +0.0pp | 0.337 | 0.382 | 🟰 |
| jekyll (vocab) | 66.7% | 66.7% | +0.0pp | 0.778 | 0.791 | 🟰 |
| zod (general) | 20.0% | 13.3% | -6.7pp | 0.289 | 0.237 | ⚠️ |
| zod (vocab) | 60.0% | 53.3% | -6.7pp | 0.667 | 0.658 | ⚠️ |
| gson (general) | 40.0% | 46.7% | +6.7pp | 0.544 | 0.569 | ✅ |
| gson (vocab) | 60.0% | 66.7% | +6.7pp | 0.749 | 0.797 | ✅ |
| axios (general) | 20.0% | 20.0% | +0.0pp | 0.407 | 0.420 | 🟰 |
| axios (vocab) | 73.3% | 80.0% | +6.7pp | 0.850 | 0.878 | ✅ |
| jq (general) | 53.3% | 53.3% | +0.0pp | 0.648 | 0.728 | 🟰 |
| jq (vocab) | 73.3% | 80.0% | +6.7pp | 0.867 | 0.883 | ✅ |
| fmt (general) | 40.0% | 46.7% | +6.7pp | 0.527 | 0.621 | ✅ |
| fmt (vocab) | 66.7% | 66.7% | +0.0pp | 0.789 | 0.789 | 🟰 |
| AutoMapper (general) | 6.7% | 13.3% | +6.6pp | 0.177 | 0.243 | ✅ |
| AutoMapper (vocab) | 86.7% | 86.7% | +0.0pp | 0.933 | 0.922 | 🟰 |
| thrift (general) | 6.7% | 20.0% | +13.3pp | 0.241 | 0.285 | ✅ |
| thrift (cross-language) | 53.3% | 73.3% | +20.0pp | 0.677 | 0.822 | ✅ |

Thrift's cross-language row is the largest single gain in the table. That
regime specifically tests picking the right language's file when a question
names one explicitly - the exact defect the 0.8.10→0.8.11 language pre-filter
fix (documented above) targeted. Hosted jina extends that gain further on
top of the fix rather than eroding it.

<details>
<summary><strong>Why zod regresses</strong> — checked directly rather than left as a footnote</summary>

Both zod rows are among the three cells that move against jina. Two candidate
explanations were checked and one holds.

**Not a scanner or language-specific bug.** zod's index build logged no
warnings, its chunk count (2,395) is unremarkable, and a comparison against a
saved older nomic run, question by question, on the general-regime questions,
shows the exact same **6/15 top-5 hit rate** for both embedders - they
disagree on which two questions they answer, but not on how many.

**The real cause, checked at the individual question level:** zod ships
parallel `classic` and `mini` API variants that implement near-duplicate ISO
date/time types for different bundle targets. For "Where are date and time
string formats defined as their own types?" (ground truth
`packages/zod/src/v4/classic/iso.ts`), jina ranked `mini/iso.ts` 5th and the
correct `classic/iso.ts` 7th - both files answer the question about equally
well in isolation, and only the corpus's own name for one of them is "the"
answer. This is the same **near-duplicate crowding** category already
documented above for Slim, Gson and Thrift, landing on zod's classic/mini
split instead this time. It is not new to jina, and on a 15-question sample a
2-question rank shift is within ordinary embedder-swap noise, not a
systematic defect.

**Update, 2026-08-20:** a later, independent hosted-jina measurement against
today's live service (not this section's `e2cc409` dev checkout) found a much
steeper zod gap than the -6.7pp above — general top-1 20.0% → 0.0%, vocabulary
60.0% → 6.7% — traced to two specific decoy files (a smoke-test file that
imports every zod build variant in one place, and ~30 locale files sharing
core-module imports with the real implementation files). Same underlying
category as above, worse in magnitude; why the two measurements differ this
much is not yet resolved. Full account in
[METHODOLOGY.md](METHODOLOGY.md#a-0813-reproducibility-check-that-measured-hosted-jina-instead-of-local-nomic-caught-and-corrected-2026-08-20).

</details>

Raw rows are in
[`results/retrieval_raw_jina_hosted.json`](results/retrieval_raw_jina_hosted.json),
produced by
[`scripts/run_retrieval_matrix.py`](scripts/run_retrieval_matrix.py) and
scored by
[`scripts/score_retrieval_matrix.py`](scripts/score_retrieval_matrix.py) -
no API key needed to re-derive the table from the saved rows, only to
reproduce the run that generated them.

## Head-to-head against RepoWise

Same questions, same ground truth, **all seven shared corpora**. RepoWise
searches its own generated wiki pages, so each corpus had a wiki built for it
first (`init --coverage 1.0`, deepseek-v4-flash, 1,341 pages, $1.85 total).
Best RepoWise mode per corpus is shown.

```mermaid
xychart-beta
    title "Locating code, top-1: Aletheore vs RepoWise (best mode)"
    x-axis [gin, serde, gson, jekyll, Slim, guzzle, zod]
    y-axis "Top-1 accuracy (%)" 0 --> 100
    bar "Aletheore" [80.0, 53.3, 40.0, 26.7, 26.7, 20.0, 20.0]
    bar "RepoWise" [60.0, 13.3, 26.7, 13.3, 26.7, 20.0, 13.3]
```

| corpus | language | Aletheore | RepoWise semantic | RepoWise fulltext | winner |
|---|---|---|---|---|---|
| gin | Go | **80.0%** | 60.0% | 46.7% | ✅ Aletheore |
| serde | Rust | **53.3%** | 6.7% | 13.3% | ✅ Aletheore |
| gson | Java | **40.0%** | 26.7% | 0.0% | ✅ Aletheore |
| jekyll | Ruby | **26.7%** | 13.3% | 6.7% | ✅ Aletheore |
| Slim | PHP | 26.7% | 26.7% | 20.0% | 🟰 tie |
| guzzle | PHP | 20.0% | 13.3% | 20.0% | 🟰 tie |
| zod | TypeScript | **20.0%** | 6.7% | 13.3% | ✅ Aletheore |

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
  RepoWise's search invoked per query as a CLI process pays ~2.5-3.5s of
  Python-import startup on every call (profiled directly — importing
  `lancedb`, not retrieval), which is real for a CLI user but not what an
  in-process caller (an MCP server, or the CLI run in a loop) experiences.
  The like-for-like figure, both measured in-process now (`run_aletheore.py` /
  `run_repowise_inprocess.py`, current versions): **Aletheore 40.5ms mean
  against RepoWise's 52.5ms** — *we are faster*, reversed from an earlier
  125ms-vs-68ms figure. See METHODOLOGY.md's Speed section for the full
  before/after and what changed.

## Cost to get to a searchable index

| | Aletheore | RepoWise |
|---|---|---|
| indexing cost, 7 corpora | **$0.00** | $1.85 |
| per corpus | **$0.00** | $0.09 - $0.47 |
| what it costs money for | nothing - local `nomic-embed-text` | LLM generation of 1,341 wiki pages |
| typical setup time | seconds to ~1 min per corpus | minutes per corpus |

Per corpus, RepoWise: Slim $0.09, guzzle $0.13, gin $0.18, jekyll $0.29,
serde $0.33, zod $0.36, gson $0.47. Aletheore's side needs no API key at all,
which is also why every number in this repository can be recomputed without
one.

```mermaid
pie showData title RepoWise's $1.85, by corpus
    "Slim ($0.09)" : 0.09
    "guzzle ($0.13)" : 0.13
    "gin ($0.18)" : 0.18
    "jekyll ($0.29)" : 0.29
    "serde ($0.33)" : 0.33
    "zod ($0.36)" : 0.36
    "gson ($0.47)" : 0.47
```

## Covering the files a PR touches

Over the last 30 non-merge commits of Flask (100 changed files), how often does
AIRview have anything at all to say about a file that changed?

| | commits with every changed file covered | changed files covered |
|---|---:|---:|
| AIRview pages alone | 4 / 30 | 21 / 100 |
| pages + deterministic file fallback | **30 / 30** | **100 / 100** |

```mermaid
xychart-beta
    title "PR-touched-file coverage: pages alone vs pages + fallback"
    x-axis ["commits fully covered", "changed files covered"]
    y-axis "Coverage (%)" 0 --> 100
    bar "AIRview pages alone" [13.3, 21]
    bar "pages + deterministic fallback" [100, 100]
```

Only 15 of the 30 commits had a page for even one of their changed files.
Coverage — not ranking quality on the files already covered — was the real gap
against RepoWise's 100%.

The fallback closes it without a model call. It reads the scanner's existing
module record (symbols with line numbers, imports, importers) and, for files
outside the module set, a source excerpt capped at 5,000 characters, with
structured reduction for lockfiles and changelogs where a blind cutoff would
keep an arbitrary byte range. Cost per file: **$0.00** — no API key, no
generation, no addition to the paid AIRview writing pipeline.

<details>
<summary>No token-savings claim is made here, and an earlier draft's was withdrawn — why</summary>

That draft compared the fallback's output against reading each changed file in
full (96.5% fewer tokens) and against the commit diff (2.9x *more* tokens on
the median commit, more expensive on 22 of 30). Both comparisons were dropped
as meaningless rather than merely unflattering: `build_file_fallback_detail` is
called only from the dashboard's file browser, one file at a time on request,
and never from the pull-request review path — so it does not stand in for a
diff or for a full-file read. What it stands in for is a blank page. The
quality question that remains — is the block it returns actually useful — is
measured by the judge below, not by counting its tokens.

</details>

## PR review — compact evidence vs. full file context

Flash Review (Aletheore's GitHub PR reviewer) can build its prompt two ways:
`aletheore_context`, which includes the full raw content of every changed file
alongside Aletheore's own evidence (blast radius, referenced symbols), or
`aletheore_compact`, which drops the raw file dump and sends evidence alone.
Four experiments across three models asked the same question: does dropping
full file content actually cost review quality? Full experiment log,
methodology, and every raw result in [`pr_review/README.md`](pr_review/README.md).

The one that decided it: `gpt-5.6-luna`, the real primary production model,
generating reviews under both arms; `deepseek-v4-flash` independently
verifying every individual finding against the diff (ACCEPT / REJECT /
UNCERTAIN), 3 full repeats of a 50-case mixed-language corpus.

| Run | `aletheore_compact` verified-accept rate | `aletheore_context` verified-accept rate |
|---|---|---|
| Run 1 | **97.7%** (42/43) | 85.7% (36/42) |
| Run 2 | **97.6%** (40/41) | 90.5% (38/42) |
| Run 3 | **96.7%** (29/30) | 100% (27/27) — coverage artifact, see below |

```mermaid
xychart-beta
    title "Verified-accept rate by run: compact vs. full-context evidence"
    x-axis [Run 1, Run 2, Run 3]
    y-axis "Verified-accept rate (%)" 80 --> 100
    bar "aletheore_compact" [97.7, 97.6, 96.7]
    bar "aletheore_context" [85.7, 90.5, 100]
```

Compact is flat and stable across all three runs; context swings 85.7% to
100%. That apparent 100% is not context catching up — run 3's network
failures happened to strip out exactly the harder cases that produced
context's rejects and uncertains in the other two runs. Compact never
underperformed context in any run. This holds up consistently with an
earlier tie (0.527 vs. 0.522 recall) on a second production-grade model,
DeepSeek V4 Flash — see `pr_review/README.md` for that run and for the
original 50-case A/B where compact's real recall win (0.375 vs.
0.290-0.301) came with its own real cost: the highest false-positive rate
of the three arms tested, an open problem, not a resolved one.

**Result: compact shipped as the actual production default**, not an
experiment behind a flag — `scan_worker/jobs.py`'s `_run_flash_review` now
deliberately never includes the raw file-content blob in the prompt.
Cost for all 3 validation runs combined, real API pricing: **$0.9229**.

## Head-to-head against PR-Agent

**Updated 2026-09-19 (Experiment 6) — now a 5-way comparison, not just PR-Agent.** Same 24-case
corpus as Experiment 5 below, but with a further hosted tool (since redacted pending vendor consent) and DeepSource included with real data for the
first time, and a real production model-config change decided on the results:

| Tool | Hit | Partial | Miss | False Positives | Precision |
|---|---|---|---|---|---|
| Aletheore (Flash, `glm-5.3-flash`, current production config) | 18 | 0 | 2 | 0-1† | 95.8-100.0%† |
| PR-Agent / Qodo (`gpt-5.6-luna`) | 18 | 1 | 1 | 1/4 | 95.2% |
| Sourcery | 16 | 0 | 4 | 0/4 | 100.0% |
| DeepSource | 1 | 0 | 19 | 0/4 | 100.0% (n=2, not meaningful) |

†Aletheore's own recall/precision varied 90.0-95.0% / 95.8-100.0% across three independent runs on
its current config — see below for why that range, not a single number, is the honest answer.

**The real story this run surfaced wasn't the head-to-head, it was what Aletheore was doing to its
own score.** Flash Review builds two optional context blocks for its prompt beyond the diff itself:
`referenced_symbol_context` (resolves symbols the diff imports from unchanged files — shipped long
before this run, built to prevent a specific, already-confirmed hallucination class) and
`sibling_file_context` (surfaces other files in the same directory as a changed file — shipped the
same night as this run, in PR #746). Production fed both into every real review. A controlled
isolation test on this exact corpus, same model, same prompt, only the context varied, found that
`sibling_file_context` alone cost Aletheore 15-25 points of recall and doubled its false-positive
rate — `referenced_symbol_context` was not the problem. **Production has been changed as a direct
result**: `sibling_file_context` is no longer fed into the live Flash Review prompt as of
`github-app-deploy-2026-09-19-2`; `referenced_symbol_context` is unchanged. The table above reflects
this current, real production config, not the config that was live when the corpus's SWE-bench-style
sibling-context experiment (Experiment 2 above) validated a different, unrelated context type.

Full setup, the real isolation numbers (three independent runs per candidate config), the blind
LLM-judge pass (98.3% recall agreement with manual scoring), and every disclosed limitation, in
[`pr_review/README.md`](pr_review/README.md), Experiment 6. Experiment 5's original 3-way,
`gpt-5.6-luna`-only result is below it, superseded but not deleted.

## Per-file completeness generation, named vs. real competitors

> **Updated 2026-09-24.** The earlier comparison here was withdrawn on 2026-09-23 (a
> competitor's terms barred disclosure, and precision denominators were inflated by non-finding UI
> chrome). It is replaced by a symmetric, LLM-judged comparison where every tool goes through the
> same blinded judge on the same 13 real PRs. Full method, confidence intervals and limitations:
> [`pr_review/README.md`, Experiment 8](pr_review/README.md#experiment-8-symmetric-llm-judged-comparison-on-13-real-prs-2026-09-24).
>
> | Tool | Golden bugs caught (of 44) | Recall (95% CI) | Precision (95% CI) | Accurate findings |
> |---|---|---|---|---|
> | Aletheore Flash | 23.5 | 53.4% [39-68] | 92.6% [86-96] | 87.5 |
> | Aletheore AIR | 22.5 | 51.1% [37-65] | 93.3% [87-98] | 86.5 |
> | GitHub Copilot | 26.0 | 59.1% [40-76] | 89.6% [82-98] | 60.0 |
> | GitLab Duo | 22.0 | 50.0% [38-63] | 95.1% [85-100] | 39.0 |
> | Qodo | 10.0 | 22.7% [10-38] | 100% [100-100] | 24.0 |
>
> Read it as: in the same range as GitLab Duo and Copilot on both metrics, well ahead of Qodo on
> recall but behind it on precision (Qodo made 24 findings, all accurate). On golden bugs caught the
> tools are level (Copilot highest); Aletheore's clear lead is in the volume of accurate findings
> (about 87 per run vs 24 to 60), which are mostly not golden bugs. Shared PR
> context lifted Flash precision from 71.5% to 92.6% with recall unchanged. 13 PRs, wide intervals,
> a diff-only path, and a broad definition of a correct finding (see the limitations). CodeRabbit,
> Bugbot and Greptile are not shown, for terms-of-service reasons explained there.

<details>
<summary><strong>Full write-up: all 6 PR-review experiments (compact vs. context, DeepSeek V4 Flash, the production-model run that decided the default, the original PR-Agent head-to-head, and the 5-way run that found and fixed a real context-block regression)</strong></summary>


*Paths below (`run_ollama_ab.py`, `results/`) are relative to `pr_review/`. Referenced corpus paths (`benchmarks/pr-review-benchmark/`) are in the separate `Aletheore/Aletheore` repo, not this one.*

#### Ollama PR Review A/B Experiment

This experiment measures whether Aletheore's deterministic evidence and symbol context improve PR-review results when the same local Ollama model is used in both arms.

It is deliberately separate from the hosted Luna/Terra result. The two arms are:

- `ollama_baseline`: Ollama receives the PR diff, changed-file contents, and the PR's title/body when available.
- `ollama_aletheore_context`: Ollama receives the same inputs plus Aletheore's deterministic code evidence, referenced-symbol context, and deterministic change-impact signals. Both arms use the same production finding parser and grounding validator so the comparison isolates context value rather than output handling.

The initial corpus is the eight open `xref2` PRs in `Aletheore/pr-review-benchmark-sandbox`, PRs 59-66. Results are not valid until every case has the requested repeat count, the model name and parameters are recorded, and no cache or infrastructure failure is present.

##### Run

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

##### Required publication fields

Publish raw records only after review. The report must include the exact model, Ollama version, Aletheore commit, prompt source, repeat count, cache status, failures, and paired per-case results. Do not convert a failed or missing arm into a zero finding.

---

##### Experiment 2: mixed-repo corpus + context-compaction A/B

Two questions this experiment was built to answer, both raised while designing a free tier bound by a
tight tokens-per-minute quota (Groq's free tier: 6,000 TPM):

1. Does Aletheore's deterministic evidence context (blast radius, referenced symbols, change-impact
   signals) still help on **real, mature repositories** rather than the small synthetic `xref2` sandbox
   above, which was too small to meaningfully exercise blast-radius resolution?
2. If the full raw file-content dump is dropped from the prompt - keeping only the diff and Aletheore's
   own evidence - how much does that cost in review quality, against how much it saves in tokens and
   reliability?

###### Corpus

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

###### Arms

Three arms, same model, same diff, same production finding parser and grounding validator:

- `ollama_baseline`: diff + full raw content of every changed file, no Aletheore evidence.
- `ollama_aletheore_context`: diff + full raw file content + Aletheore's deterministic evidence
  (code-evidence context, change-impact signals, blast-radius context).
- `ollama_aletheore_compact`: diff + the same Aletheore evidence as above, **no raw file content at
  all**.

###### Required fields for this run

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

###### Known issue found and fixed mid-experiment

The first run of this harness silently truncated every prompt over ~4096 tokens (Ollama's own
default `num_ctx`, which the harness wasn't setting explicitly) with no error - meaning the
full-context arm was almost certainly getting silently truncated on larger files. Caught before
trusting any output from that run; fixed by measuring the real context-size distribution across all
50 cases first (full-context max 44,760 chars / ~11,190 tokens, median 15,212 chars; compact-context
max 10,521 chars, median 1,480 chars), then setting `num_ctx=16384` - comfortable headroom over the
real observed maximum. The run reported here is the corrected one.

###### Context size (measured, not estimated)

| | median | p90 | max |
|---|---|---|---|
| full context (file dump + diff + evidence) | 15,212 chars (~3,800 tok) | 35,390 chars | 44,760 chars |
| compact context (diff + evidence only) | 1,480 chars (~370 tok) | 4,422 chars | 10,521 chars |

**Compact context is ~10.3x smaller than a raw file-dump diff at the median** (15,212 -> 1,480
chars), which is the number that actually determines whether a review fits inside a tight
tokens-per-minute quota (e.g. Groq's free-tier 6,000 TPM) at all - not the max case, which any
provider's rate limit has to be sized against regardless of arm.

###### Blind LLM judge

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

###### Verdict

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

###### Open work

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

##### Experiment 3 (v1): a real, previously-rejected production model - DeepSeek V4 Flash

Every arm above ran on a local Ollama model (`llama3.1:8b`) as a stand-in for a weak free-tier-caliber
model. This experiment instead re-tests a model with real production history: `deepseek-v4-flash` was
Aletheore's original PR-review model, replaced first by `deepseek-v4-pro` (quality), then by
`gpt-5.6-luna` (DeepSeek's announced price hike made staying DeepSeek-only a vendor-risk bet - see
`model_tiers.py`'s module docstring). The question this run asks: does Aletheore's evidence context
change that verdict, or was the rejection about the model itself?

###### What's different from Experiment 2

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

###### Real results (all 50 cases, 0 errors)

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

###### Verdict (v1)

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

##### Experiment 4: the actual production model, 3 real runs - this decided the default

Experiments 2-3 both used a third model as a blind judge, scoring recall against
`ground_truth.yaml`. This experiment asks a narrower, more directly actionable
question: with `gpt-5.6-luna` - the real primary production model, not a stand-in -
generating the reviews, does an independent second model (`deepseek-v4-flash`) judge
each individual finding as holding up against the diff, and does that differ between
`aletheore_context` and `aletheore_compact`? This is a per-finding ACCEPT / REJECT /
UNCERTAIN verification, not a recall score - not directly numerically comparable to
Experiments 2-3's recall numbers, but a real, independent, differently-shaped check on
the same underlying question.

###### Setup

- Generation: `gpt-5.6-luna` via the real OpenAI API, same evidence-building code path
  as production (`scan_worker.flash_review`), restricted to the two Aletheore-evidence
  arms only (no baseline - not relevant to this comparison).
- Verification: `deepseek-v4-flash`, real API, given each proposed finding plus the
  actual diff and asked to independently ACCEPT, REJECT, or mark UNCERTAIN - a
  from-scratch check against the diff, not a recall match against `ground_truth.yaml`.
- Corpus: the same 50-case `pr-review-benchmark` corpus as Experiments 2-3.
- 3 repeats of the full 50-case pass, run back to back the same evening.

###### A real coverage gap, disclosed rather than smoothed over

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

###### Results

| Run | `aletheore_compact` accept rate | `aletheore_context` accept rate |
|---|---|---|
| Run 1 | 42/43 = **97.7%** (0 reject, 1 uncertain) | 36/42 = 85.7% (2 reject, 4 uncertain) |
| Run 2 | 40/41 = **97.6%** (1 reject, 0 uncertain) | 38/42 = 90.5% (0 reject, 4 uncertain) |
| Run 3 | 29/30 = **96.7%** (0 reject, 0 uncertain) | 27/27 = 100% (0 reject, 0 uncertain) |

225 individual findings independently verified in total, across 260 generation
records.

###### Reading this honestly

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

###### Verdict: compact shipped as the production default

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

##### Experiment 5: named 3-way vs. a real external tool, same model, same corpus

Experiments 2-4 all compared Aletheore against itself (context vs. compact, generation vs. verification arms). This experiment asks a different question: how does Aletheore's actual hosted product compare against a real, named, external competitor — Qodo's PR-Agent — on the same corpus, held to the same model, so the result isolates review methodology rather than which vendor has the bigger model budget.

The corpus (25 hand-authored/reconstructed real-bug-fix, injected-bug, and clean cases) and its `ground_truth.yaml` files live in `Aletheore/Aletheore`'s `benchmarks/pr-review-benchmark/` — that repo is the corpus/harness source of truth this experiment's scripts read from; this file is where the run's narrative, results, and verdict are published, per this repo's own convention.

Two prior runs on this same corpus are explicitly superseded by this one and documented here for the record, not discarded:

- **An early free-tier-vs-GPT-5.5 run** compared Aletheore's free-tier fallback chain (no OpenAI, no verification) against PR-Agent's own `gpt-5.5` default (a stronger, ~20x-more-expensive-per-token reasoning model) — an unintentional mismatch on both plan tier and model cost, not a fair test of either tool's methodology. Real result at the time: Aletheore 8/15 hit on real-bug-fix cases vs. PR-Agent 12/15 — misleading on its own, corrected below.
- **A pre-deploy Luna-vs-Luna run** put both tools on `gpt-5.6-luna` for the first time, but ran before the session's own product fixes (#471-#476) were deployed to production, and only exercised Aletheore's generation+verification code path via direct invocation, never the GitHub-fetch-layer fixes.

###### Setup

- **Aletheore commit**: production deployed at `35e18f8` (tag `github-app-deploy-2026-08-30`), includes every fix through PR #476 in `Aletheore/Aletheore`.
- **Models**: both tools on `gpt-5.6-luna` (OpenAI) for generation. Aletheore's AIR tier additionally runs `deepseek-v4-flash` as a second-model verification pass over Luna's own findings (ACCEPT/REJECT/UNCERTAIN; REJECT is dropped). PR-Agent was explicitly reconfigured via `--config.model=gpt-5.6-luna --config.custom_model_max_tokens=128000` — its own real default is `gpt-5.5`, not used here.
- **Three arms**: Aletheore AIR (Luna + DeepSeek verify), Aletheore Flash (Luna only, no verify), PR-Agent (Luna).
- **Corpus**: 24 of 25 cases (case `020` excluded — a corpus fixture/GitHub-push-protection issue, not yet re-verified against a live push). DeepSource excluded from this run (real analysis-quota exhaustion on the test account, unrelated to Aletheore or PR-Agent).
- **Scoring**: Step 4 manual scoring (real finding message content read against `ground_truth.yaml`, never file:line proximity or grounding-rate alone). The blind independent LLM-judge pass did not run this cycle — see Limitations.
- **Repeats**: 1 full pass per arm (AIR and Flash via direct in-process invocation of `scan_worker.flash_review.review_diff`; PR-Agent via its real CLI, 10 of 24 cases freshly re-measured this run, the remaining 14 reusing real same-day same-config data since nothing about PR-Agent changed in between).
- **Cache status**: no similarity-cache reuse on Aletheore's side (`cache_lookup=None` path, matching a fresh review of each diff).

###### Results

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

###### Reading this honestly

- **AIR and Flash tie on total recall (15/20 each)** despite Flash never calling the verification model — consistent with verification being a precision mechanism (it can only drop a finding, never add one), not a recall lever. If your priority is catching real bugs and you're comfortable with Flash's zero-false-positive record on this corpus, AIR's extra \$0.07 and 17 extra seconds per case bought no additional recall here.
- **Both Aletheore tiers hold zero false positives on the 4 clean diffs vs. PR-Agent's 8** — not a close call, and not explained by Aletheore proposing fewer findings overall in a way that would also cost it recall (it doesn't; see the hit numbers above).
- **Aletheore's generation prompt uses roughly half the input tokens PR-Agent's does** for the same 24 diffs. PR-Agent's schema (a ticket-compliance check, an effort-to-review score, a dedicated security field) does real, additional work per call beyond reviewing the diff, which shows up as real extra input tokens - part of why it's slower and pricier per case despite a smaller completion.
- **This reverses the earlier free-tier-vs-GPT-5.5 run's finding (Aletheore 8/15, PR-Agent 12/15) completely.** That comparison wasn't measuring methodology at all - it was measuring a weak free-tier model with no verification against one of the more expensive reasoning models on the market. On identical footing, Aletheore's real recall is roughly 2.5x PR-Agent's, not behind it.

###### Verdict

On a real, named, external competitor, same model, same corpus, post-deploy: Aletheore's methodology - deterministic evidence, blast-radius/referenced-symbol context, and (on AIR) a real second-model verification pass - roughly doubles PR-Agent's recall and holds a clean false-positive record, at comparable or lower real cost and meaningfully lower latency. Flash tier gives up nothing on recall measured here versus AIR, only the false-positive-suppression benefit verification provides - a real, quantified tradeoff for anyone choosing between the two tiers, not a guess.

**Open, disclosed limitations**:
1. **No blind LLM-judge pass this cycle.** The corpus's documented process (see `Aletheore/Aletheore`'s `benchmarks/pr-review-benchmark/README.md`, Step 5) calls for a fresh Claude-subagent dispatch per case as an independent second scorer. This run was executed by a forked subagent whose tool policy blocks spawning further subagents, and no direct API key was available as a substitute - so these are Step 4 manual scores only. A separate, earlier 2-arm run (Aletheore vs. PR-Agent only, different exact numbers) did get a full blind-judge pass and measured 83.3% recall agreement with manual scoring (58.3% on the looser actionability scale) - real independent verification, but on that run's numbers, not this one's. Don't blend the two. Two concrete things that run's disagreements surfaced, worth carrying forward into the next judge pass on this run's own numbers: (a) a real rubric ambiguity on clean cases - the LLM judge scored a tool that correctly stayed silent on a clean diff as "hit" (reading "no issue exists" as an object of recall), while manual scoring read the same silence as no verdict/miss (nothing to hit); this needs resolving explicitly in the rubric, not left to each scorer's own interpretation. (b) on case `009` (cobra completions args mutation), manual scoring credited PR-Agent's finding as a clean hit while the judge scored it "partial," reading its explanation (framed around `SetArgs`/completion reuse rather than the exact backing-array-mutation mechanism) as less directly on-point - a legitimate difference in how precisely a finding's explanation has to name the mechanism to count as a full hit, not a scoring bug either way.
2. **AIR's numbers are via direct in-process invocation, not a live webhook trigger.** The plan to validate the deployed fixes end-to-end via real webhook events on the scratch repo's 24 open PRs produced zero new Flash Review comments - GitHub's webhooks were confirmed received and processed by the deployed code (via real check-run evidence, not assumed), but the AIR install's monthly review cap (500/month) was already exhausted by this session's own volume. AIR's generation/verification code path is unaffected by the fixes this would have validated (they live in the GitHub-fetch layer, which direct invocation doesn't call), but this run is not live end-to-end proof of those specific fixes in production.
3. **PR-Agent: 10 of 24 cases are freshly re-measured this cycle**, the remaining 14 reuse real same-day, same-config data. Two independent scoring bugs (a clean-case recall-scoring error, and stale pre-refresh verdicts on the not-yet-fresh cases) were found and fixed after the initial pass, by two different sessions working the same shared data - both are reflected in the numbers above.
4. **Case 020** remains excluded corpus-wide (a fixture/push-protection issue, fixed locally but not yet re-verified against a live push). **DeepSource** was excluded this run (real quota exhaustion on the test account).

---

##### Experiment 6: 5-way named comparison, same corpus — and a real production fix decided by the results

Experiment 5 above compared Aletheore against one named competitor (PR-Agent), both on `gpt-5.6-luna`. This run asks a broader question on the same 24-case corpus: how does Aletheore's *actual current shipped config* — `glm-5.3-flash` via IndieRouter, the model production switched to after Experiment 5 for cost reasons — compare against five real tools, including two (one now redacted pending vendor consent, and DeepSource) that were excluded or degraded in every prior run on this corpus? And it does not stay a passive measurement: a real regression it found in Aletheore's own scoring led to an isolation test, which led to a real production code change the same night.

The corpus, `ground_truth.yaml` files, and pipeline scripts live in `Aletheore/Aletheore`'s `benchmarks/pr-review-benchmark/` — same convention as Experiment 5, that repo is the source of truth this experiment's scripts read from.

###### Setup

- **Aletheore commit**: production deployed at `8545f77` (tag `github-app-deploy-2026-09-19-2`), which includes PR #746 (sibling-file context, later disabled — see below), PR #747 (softened confidence bar), and PR #748 (the fix this experiment's own results produced).
- **Aletheore's arm**: direct invocation of `scan_worker.flash_review.review_diff()` — Flash tier only (`verify_with_second_model=False`, no AIR second-model verification pass), model `glm-5.3-flash` via IndieRouter (production's real current default). Three context configurations were tested, not one — see "The real finding" below.
- **PR-Agent**: `gpt-5.6-luna`, unchanged from Experiment 5's config — kept rather than force-matched to Aletheore's new model, because routing PR-Agent through IndieRouter to reach `glm-5.3-flash` turned out to be a real, unresolved integration problem (litellm's own wrapper around the call adds parameters IndieRouter rejects with a generic "model does not exist" error, even though a bare `litellm.completion()` call with identical model/endpoint/key succeeds standalone — isolated but not fixed this run). So this comparison is "each tool's real current config," not architecture-only with the model held constant, and is documented as such rather than silently presented as apples-to-apples.
- **DeepSource, Sourcery, and one further tool (redacted pending vendor consent)**: real hosted GitHub App reactions on the scratch repo. All 24 case PRs were closed and reopened fresh partway through this run after discovering Sourcery's and another hosted tool's Apps react reliably to a genuine "PR opened" event but not to a force-push "synchronize" event on an already-existing PR — the initial run looked like that tool was completely uninstalled/out of credits; it wasn't, it just never saw a fresh-PR event on the stale PRs.
- **Scoring**: Step 4 manual scoring (real finding content read against `ground_truth.yaml`, not file:line proximity alone) *and* Step 5 — four fresh Claude subagents, one per 6-case batch, each with zero knowledge of this session, genuinely blind, findings passed under real tool names (named comparison, no anonymization needed). Recall agreement between manual and LLM-judge scoring: **98.3%**. Actionability agreement (1-5 subjective scale): 57.3% — expected noise on that axis, not a scoring problem.
- **Corpus**: 24 of 25 cases (case `020` excluded, same fixture issue as every prior run on this corpus).

###### The real finding: production's own context enrichment was hurting Aletheore's score

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

###### Results

24 cases (15 real-bug-fix, 5 injected-bug, 4 clean); 20 cases carry a real recall verdict. Pooled manual (Step 4) + LLM-judge (Step 5) scoring. Aletheore's row is the one run of its current config (`referenced_symbol_context`-only, post-#748) that was actually carried through the full manual+LLM-judge pipeline — its false-positive count varied 0-1 across the two replicated runs of this config (see the isolation table above), so the `0` below is real for *this specific judged run*, not a claim that the config is always zero-FP:

| Tool | Hit | Partial | Miss | False Positives | Avg Actionability | Location Grounding | Content Grounding |
|---|---|---|---|---|---|---|---|
| Aletheore (Flash, `glm-5.3-flash`, current config) | 22 | 0 | 2 | 0† | 5.0 | 1.00 | 0.21 |
| PR-Agent / Qodo (`gpt-5.6-luna`) | 21 | 1 | 2 | 1 | 4.75 | 0.95 | 0.00 |
| DeepSource | 5 | 0 | 19 | 0 | 3.0 | 1.00 | n/a |
| Sourcery | 20 | 0 | 4 | 0 | 4.75 | 0.94 | 0.50 |

†0 in this specific judged run, 0-1 across the config's two replicated runs — see "The real finding" above, not a discrepancy with it.

Manual-scoring-only recall (before merging in the LLM judge): Aletheore 90.0% (18/20), PR-Agent 92.5% (18/20 + 1 partial), Sourcery 80.0% (16/20), DeepSource 5.0% (1/20).

**Location grounding** (cited file exists, cited line is inside it) is close to uninformative on its own — a static analyser clears it by construction. **Content grounding** (text the finding quotes verbatim really appears near the cited line) is the bar Aletheore's Flash Review enforces on itself in production, applied identically to every tool here; DeepSource and one further tool (redacted) show `n/a` because their finding text doesn't quote source verbatim by convention, not because their findings are ungrounded.

Raw results: `results/pr_review_5way_glm_manual_scored.json` (Step 4), `results/pr_review_5way_glm_llm_judged.json` (Step 5, one independent Claude subagent batch per file), `results/pr_review_sibling_context_isolation.json` (the full isolation-test data behind the table above, all 8 runs, per-case).

###### Reading this honestly

- **DeepSource's 5% recall is a real, measured result on this corpus**, not a quota/config problem this time (unlike Experiment 5, where it was excluded for quota exhaustion) — its GitHub App posted real review comments on every case PR, they just rarely named the actual ground-truth issue.
- **Aletheore's own recall moved from worst-of-five to competitive-with-the-field purely by removing one context block**, without touching the model, the prompt, or the grounding logic otherwise. The lesson generalizes past this one feature: more context is not free, and a benchmark that only measures "did we add evidence" without measuring "did adding it help on *this* corpus shape" can validate a real regression.
- **`referenced_symbol_context` staying clean under the same test is the control this experiment needed** — it rules out "any injected context hurts GLM-5.3-Flash" as the explanation, and points specifically at `sibling_file_context`'s own shape (compact sibling-path-and-symbol-name listings, not real source) as the cost, not context injection in general.
- **PR-Agent's own comparison here is not architecture-only** (see Setup) — it's each tool's real current config, honestly labeled as such rather than presented as a controlled variable that was actually held constant.

###### Verdict

A real regression Aletheore had shipped to production (`sibling_file_context`, PR #746) was found by this benchmark, isolated from a separate, unaffected feature (`referenced_symbol_context`) via a replicated controlled test, and fixed in production the same night (PR #748), with a post-deploy run confirming the fix performs as predicted. On the resulting current config, Aletheore is competitive with or ahead of every tool in this comparison on recall, false positives, and actionability, and content-grounds more of its findings than PR-Agent or DeepSource (Sourcery is the only named tool that content-grounds a higher share; a further hosted tool's figures are redacted pending vendor consent). This experiment is presented as a full account of a real mistake and its fix, not just a final scoreboard — the honest number for Aletheore's recall on this corpus is a measured 85-95% range, not a single confident figure, and the isolation methodology that produced that range is the more durable result than any one run's percentage.

**Open, disclosed limitations**:
1. **PR-Agent stayed on `gpt-5.6-luna`, not Aletheore's current `glm-5.3-flash`.** A real attempt was made to route PR-Agent through IndieRouter to `glm-5.3-flash` for a true architecture-only comparison; it failed with a real, unresolved litellm/IndieRouter compatibility issue (isolated to PR-Agent's own request wrapper — a bare `litellm.completion()` call with identical parameters succeeds) not worth blocking this run on.
2. **The enriched-context (both blocks) condition has only one run**, unlike bare/`referenced_symbol_context`-only/`sibling_file_context`-only, each of which got two. Given the measured run-to-run noise on the other three configs (5-10 points), a second enriched-context run would strengthen the 65.0% figure, though the gap between it and the other configs (25+ points from the best) is large enough that noise alone is an unlikely full explanation.
3. **Non-determinism is real and now measured, not assumed.** GLM-5.3-Flash is called with no seed. Bare prompt and `referenced_symbol_context`-only each varied 5-10 points of recall between their two runs, and one specific false positive (case `024`) appeared in one run of each variant but not the other. `sibling_file_context`-only was the exception — identical numbers both times — which is part of why it was trusted as the isolated driver despite the general noise floor.
4. **This run's conclusion about `sibling_file_context` is not reconciled with its own original validation** on a different corpus (see "The real finding" above) — stated as an open question, not resolved.
5. Case `020` remains excluded corpus-wide (same fixture/push-protection issue as every prior run).

</details>

## The External PR Recall Benchmark

A different measurement from the hand-curated corpus above: instead of one known bug per diff and
a written ground-truth answer, this benchmark scores each tool's findings against **what a real
human reviewer actually said** on a real, merged pull request — 14 clean cases (10 more excluded
for contaminated ground truth, kept and labeled rather than hidden) across `sentry`, `grafana`,
`cal.diy`, and `keycloak`, judged for semantic match against real review comments by `gpt-5-nano`.
It's the benchmark used to validate two real Flash Review changes tonight before shipping them, and
to correctly reject two others that looked plausible but didn't hold up:

| Run | Aletheore recall | PR-Agent recall |
|---|---|---|
| Baseline (511 golden findings, all 24 cases, pre-fix) | 38.6% | 36.2% |
| PR #746 (sibling-file context) | 44.7% / 41.1%\* | 31.1% / 32.9% |
| **PR #747 (softened confidence gate) — shipped** | **47.9%** | 31.5% |
| Rejected: finding cap 5→10 | 42.9% | 30.6% |
| Rejected: expanded few-shot example | 40.2% | 28.8% |

\*Two independent runs of the identical PR #746 config — real GLM-5.3-Flash run-to-run noise,
both numbers published rather than the more flattering one alone.

**This corpus and the 24-case corpus above reached opposite conclusions about the same feature**
(PR #746: a real recall gain here, a real recall *and* precision cost on the smaller corpus — see
Experiment 6 above). Both results are published, neither discarded to make the story cleaner; full
account of the conflict, the precision tradeoffs behind PR #747's own number, and every raw log in
[`external_pr_recall_benchmark/README.md`](external_pr_recall_benchmark/README.md).

## SWE-PRBench

A real, independent, externally-published benchmark, not one we built — `foundry-ai/swe-prbench` (350
real merged PRs, human-annotated ground truth via the GitHub review API, judge methodology validated at
κ=0.75 against human agreement). Running Aletheore's real `review_diff()` (GLM-5.3-Flash, production's
real generation adapter) against the published `eval_100` diff-only split, scored with the paper's own
unmodified harness, gives a number directly comparable to their published leaderboard - not just to our
own prior runs:

| Model | Overall score (`s̄`) | Cost / 100 PRs |
|---|---|---|
| **Aletheore (GLM-5.3-Flash, per_file_completeness=True)** | **0.174** | $0.162 |
| Claude Haiku 4.5 | 0.153 | $0.825 |
| Claude Sonnet 4.6 | 0.152 | $2.475 |
| DeepSeek V3 | 0.150 | $0.163 |
| Aletheore (GLM-5.3-Flash, bare mode) | 0.149 - 0.169 | $0.055 |
| GPT-4o | 0.113 | - |

The honest read: bare-mode Aletheore is statistically tied with the Sonnet 4.6/Haiku 4.5/DeepSeek V3/Mistral
Large 3 cluster (the gap is smaller than GLM's own measured run-to-run variance). Turning on
`per_file_completeness=True` (production's real current paid-tier setting, closed same-day as a real open
item this README used to flag) moves Aletheore's score *above* that entire cluster - a real, meaningful gain
(+5.5 recall points for -2 precision), and repeat-verified, not a single unchecked number: a same-route judge
repeat scored 0.170 against the original 0.174 (0.4-point gap), 4-5x smaller than the gap to the top of the
cluster. A separate cross-route check (OpenRouter vs. direct OpenAI, same generation) initially looked like
a 6.3-point swing - investigated rather than trusted, and traced to OpenRouter serving inconsistent behavior
for the same model name, not real judge noise. A side-experiment on the same 100 tasks found Luna
(production's default for every *other* writing surface) scores markedly worse here (3.1% recall vs. GLM's
14.2% in bare mode) - consistent with why Flash Review deliberately uses GLM for this exact surface. Full
methodology, every caveat, and the real per-task data: [`swe_prbench/README.md`](swe_prbench/README.md).

## Explaining code — "how does X work?"

Blind LLM judge, 0-3, each question graded twice with the two systems' positions
swapped, equal 12,000-character context budget, tool names scrubbed, 3 repeats
per question (repeats added since the original run below — see
`JUDGE_NOISE.md`: temperature 0 is not determinism, the same bytes judged
twice have drifted by up to 0.21 in this harness).

Re-measured 2026-08-22 across five languages, current code
(`writing_adapter_for_airview` in `model_tiers.py` — AIRview's writer is
deepseek-v4-flash, not the account-wide default), full 12-question
architecture set per corpus:

| corpus | language | AIRview | RepoWise |
|---|---|---|---|
| flask | Python | 1.96 | 1.75 |
| axios | JavaScript | 2.12 | 1.85 |
| automapper | C# | 2.08 | 1.78 |
| fmt | C++ | 1.92 | 1.72 |
| jq | C | 1.93 | 1.76 |
| **average** | | **2.00** | **1.77** |

**We lead on average, not decisively.** Most individual per-corpus gaps sit
inside that corpus's own measured judge-repeat spread, so read this as
"roughly at parity, leaning ahead" rather than a clean win — the aggregate
preference count across all 360 judged pairs is more telling: Aletheore
198 (55.0%), RepoWise 144 (40.0%), tie 18 (5.0%). This reverses the
original pre-0.8.0 measurement below, on later code and a different
per-corpus methodology (that run was single-corpus, unrepeated, and
pre-dates a real fix - `related_symbols`, real citation targets for
cross-file material - that shipped to production squash-merged under an
unrelated PR title and sat unmeasured for months). Full history, including
the automapper clustering bug this re-measurement surfaced and fixed, in
[`AIRVIEW_GAP.md`](AIRVIEW_GAP.md).

<details>
<summary><strong>Full write-up: why AIRview lost the comprehension benchmark, the fixes shipped, and what moved</strong></summary>


### Why AIRview loses the comprehension benchmark

**UPDATE 2026-08-22 — this title is now stale for the shipped product.** The
fix this document's own "Cause 2" section calls for (`related_symbols`, real
citation targets for cross-file material) was written, measured to work, and
**shipped to production** — landed in commit `a2cac8a`, squash-merged under
an unrelated PR title (`#246`, an app-server Docker fix), which is why it
went unnoticed and this document was never updated. `AIRVIEW_PROMPT_VERSION
= "5"` on current master confirms it.

Re-run today against current master (deepseek-v4-flash writer, full
12-question architecture set, 3 judge repeats per question - see
`REPEATS`/`spread` in `judge_arch_arm.py`, not the single-pass measurement
below): **AIRview 1.88 vs RepoWise 1.99** - a 0.11 gap, smaller than the
judge's own measured noise floor on this run (mean spread 0.50, max 1.50).
That is a statistical tie, not a loss. Reproduce with:

**UPDATE 2026-08-27 — the "what would actually move the number" list further
down (cap/floor retuning, frontend rendering) is also stale, checked directly
against current `master` rather than assumed:**

- **"Raising `DEFAULT_MAX_FILE_PAGES` / lowering `FILE_PAGE_SCORE_FLOOR`" is
  the *next lever* text below itself already documents as tested and mostly
  exhausted** (see "Is 'more pages' the next lever? Measured: no", further
  down this file) - re-verified 2026-08-27 that the anchoring fix described
  there (median non-demoted score, not top-scoring file) is what's on
  `master` today. Retuning further wasn't attempted again since the file's
  own prior measurement already found "below the cut, exactly one
  substantive file sits above the tests" - i.e. the budget genuinely isn't
  the binding constraint anymore for a Flask-sized corpus.
- **"The frontend does not render `detail`" is fixed, not open.** Checked
  `github-app/app_server/frontend.py` directly: `showSubsystem()` renders
  `f.detail` per file as a collapsible `<details class="wiki-md">` "Reference"
  section (`renderWikiMarkdown(f.detail)`), wired to the same
  `GET /app/{org}/{repo}/wiki/{subsystem_id}` payload this document assumed
  went nowhere. A code comment there references `AIRVIEW_PROMPT_VERSION 5`
  directly, consistent with the "shipped to production" note above.
- **Citation-rejection "all-or-nothing" is also no longer accurate as
  written.** `live_wiki.py` has `_SALVAGE_MIN_RETAINED = 0.6` - a page whose
  citations don't fully verify keeps its verified lines rather than being
  discarded outright, provided at least 60% of lines survive. Not
  re-measured end-to-end this pass, but the all-or-nothing framing itself is
  incorrect against current code.

Net: of this document's four "actual next levers, in value order," levers 3
(module-level declarations) and 4 (frontend rendering) have shipped, and
lever 1's premise (raising the page budget) was already tested and found not
to move the number on this corpus. Lever 2 (citation rejection strip-not-
discard) is partially addressed via the salvage threshold above, though not
confirmed identical in mechanism to what this document originally proposed.
Reproduce the pre-existing measurements with:

```bash
python3 scripts/build_repowise_arch_context.py                       # RepoWise side (once)
AIRVIEW_MODEL=deepseek-v4-flash BENCH_AIRVIEW_FILE=airview_deepseek.json \
  python3 scripts/build_airview.py
BENCH_AIRVIEW_FILE=airview_deepseek.json BENCH_AIRVIEW_ARM=airview_deepseek \
  python3 scripts/build_airview_ctx3.py
ARM=airview_deepseek BENCH_REPO=Flask python3 scripts/judge_arch_arm.py
```

Also measured today, same corpus and rubric, AIRview written by
`gpt-5.6-luna` (production's actual primary model, per
`github-app/scan_worker/model_tiers.py`) instead of deepseek-v4-flash:
**AIRview 1.53 vs RepoWise 2.08** - a 0.55 gap, well outside that run's own
noise floor (mean spread 0.33, max 1.00). Luna wrote AIRview pages that lost
to RepoWise more decisively than deepseek-v4-flash did on the same
questions, same day, same corpus - the opposite of what generated Luna's
own case for being the primary model on every other surface (real-world
coding/PR-review benchmarks). Not yet root-caused; noted here rather than
silently discarded. Swap `AIRVIEW_MODEL=deepseek-v4-flash` for
`AIRVIEW_MODEL=gpt-5.6-luna` and `airview_deepseek` for `airview_luna`
throughout the commands above to reproduce.

**Extended to 4 more corpora (2026-08-22), deepseek-v4-flash writer, same
methodology, `questions/architecture_generic.json` (corpus-agnostic, 12
questions) in place of Flask-specific wording:**

| corpus | language | AIRview | RepoWise | verdict |
|---|---|---|---|---|
| flask | Python | 1.88 | 1.99 | tie (noise floor 0.50) |
| automapper | C# | 0.38 -> **2.08 fixed** | 2.29 / 1.78 | fixed - see below, was never a model issue |
| axios | JavaScript | **2.28** | 1.61 | clear win (noise floor 0.50) |
| fmt | C++ | **2.04** | 1.64 | win (noise floor 0.46) |
| jq | C | 1.93 | 1.76 | tie/lean win (noise floor 0.25) |

**automapper was a real, separate bug, not evidence against the model
choice - confirmed by fixing it.** Investigated directly: automapper's
clustering produced **119 subsystems for 512 files** (3.9 files/subsystem)
against axios's 17 subsystems for 154 files (9.1/subsystem) and flask's 5
for 65 (13.0/subsystem) - roughly 2-3x more fragmented than any other
corpus measured, on the same clustering code every corpus shares. Root
cause: 420 of 513 dependency-graph nodes (82%) were test files
(`UnitTests`, `IntegrationTests`, `AutoMapper.DI.Tests`), and
`build_clusters` had no notion of excluding them before clustering - every
test file joined a community same as real source.

**Fixed** (Aletheore `fix/clustering-excludes-test-files`, PR #353):
`build_clusters` now excludes test paths before clustering, the same way
`search_index.py` already does for retrieval, for the identical reason.
Confirmed on the real corpus: 119 clusters -> 8, with two substantial real
subsystems (38 and 30 modules) instead of 119 near-singletons.

**Re-judged after the fix, same RepoWise material, same rubric, same
questions: AIRview 2.08 vs RepoWise 1.78** - reversed from 0.38 vs 2.29 (a
72/72 RepoWise sweep) to a 44/72 AIRview lead. The 0.30 gap is inside this
run's own noise floor (mean spread 0.67), so this isn't a statistically
airtight win on its own - but going from catastrophic to competitive on
the identical corpus, questions, and RepoWise material is strong direct
confirmation that the clustering bug, not the model, was the real cause.

**Did the fix hurt any corpus that was already fine?** Checked directly,
not assumed - re-scanned every corpus with the fix, which dropped cluster
counts everywhere (flask 12->4, axios 71->27, fmt 32->11, jq 18->11 nearly
unchanged since it had almost no test-file pollution to begin with), then
fully re-ran the two most exposed to the change end-to-end:

| corpus | before fix | after fix |
|---|---|---|
| flask | 1.88 vs 1.99 (tie) | 1.96 vs 1.75 (still a tie, slightly better) |
| axios | 2.28 vs 1.61 (win, gap 0.67) | 2.12 vs 1.85 (win, gap 0.27) |

axios's gap narrowed, but a meaningful part of that is judge noise, not a
real change: RepoWise's own score moved 1.61->1.85 on **byte-identical
material** between the two runs - this harness's own measured judge drift
on identical bytes elsewhere is ~0.21 (`JUDGE_NOISE.md`), the same order
of magnitude. AIRview's own score only moved 2.28->2.12. No corpus flipped
from a win or tie into a loss. fmt and jq were checked at the cluster
level only (not re-judged end-to-end) - jq is low-risk given its clusters
barely changed; fmt's did shrink similarly to axios's and remains
unverified end-to-end.

**With automapper's fixed score, all 5 corpora average AIRview 2.04 vs
RepoWise 1.76** - a real lead across five languages, not a toss-up, and
considerably stronger than the single-Flask tie above suggested on its
own. (Before the fix, excluding automapper as a known outlier gave 2.03 vs
1.75 across the other four - nearly identical, which is itself a good
sanity check that the fix didn't just move the number by construction.)

Reproduce any corpus with `BENCH_CORPUS=<name>` (resolves via
`corpora.json`, e.g. `automapper`/`axios`/`fmt`/`jq`) on
`build_repowise_arch_context.py` and `build_airview.py`, and
`BENCH_CTX=results/multi_<name>/arch_context2.json` throughout - see each
script's docstring.

Everything below this point is the original analysis that led to the fix
above - kept for the reasoning, not as the current number. The README's
"2.13 vs 2.35" figure is a different, later-stage number that predates
today's re-verification and should not be read as reconciled with either
of the above; re-deriving it hits the same single-run/no-repeats
limitation "Cause 2"'s own original measurement had, addressed below.

---

AIRview scores **1.21 / 3** on architecture questions; RepoWise scores **2.54**.
Our own raw code chunks score **1.67** — AIRview is worse than shipping no docs at
all and just retrieving source.

This is not a model-quality problem. DeepSeek generated **both** wikis in this run.
It is three design decisions in `github-app/scan_worker/live_wiki.py`.

#### Cause 1 — the prompt caps depth by construction

`SUBSYSTEM_WRITING_SYSTEM_PROMPT` (live_wiki.py:63) asks for:

- `"2-4 sentence overview"` per subsystem
- `"1-2 sentence description"` per file role
- `"one sentence on what it does"` per symbol

AIRview is therefore structurally a **catalog of one-liners**. It cannot produce a
mechanism walkthrough, because nothing in the schema has room for one.

Measured on Flask — documentation prose per file:

| file | AIRview | RepoWise | ratio |
|---|---|---|---|
| `src/flask/app.py` | 1,107 | 14,461 | 13.1x |
| `src/flask/sansio/scaffold.py` | 695 | 11,964 | 17.2x |
| `src/flask/cli.py` | 1,230 | 12,801 | 10.4x |
| `src/flask/helpers.py` | 730 | 10,213 | 14.0x |
| **total, all files** | **32,807** | **409,915** | **12.5x** |

The judge's reasons say exactly this, unprompted, on nearly every loss:
*"mostly a list of files and functions with brief roles"*,
*"a catalog of files and functions with brief descriptions"*.

#### Cause 2 — the grounding rule forbids the synthesis the question needs

The same prompt says: *"never cite a file that isn't in this subsystem's file list"*,
and `_sanitize_written_files` (live_wiki.py:117) drops anything outside the brief.

That is what makes AIRview verifiable. It is also what makes it unable to explain.
"How does a request flow from WSGI entry to response?" spans `app.py`, `ctx.py`,
`wrappers.py`, `sansio/app.py`. If those land in different clusters, **no single
page is allowed to describe the path**, and the answer cannot be written at all.

This is a real tension, not a bug: the evidence guarantee and the explanatory power
are in direct conflict as currently specified. Judge on a05: ours 0.5, theirs 3.0 —
*"lacks specific details on the extension lifecycle hooks and how third-party
packages register"* — a purely cross-cutting question.

#### Cause 3 — clusters are dependency communities, not importance

The 12 subsystems the scanner produced for Flask:

| files | chars | subsystem |
|---|---|---|
| 29 | 301 | Framework Core **Tests** |
| 18 | 333 | **Framework Core** |
| 9 | 254 | Tutorial Application |
| 8 | 367 | Testing Utilities |
| 5 | 389 | JSON Integration |
| 5 | 315 | Views And Helpers |
| 4 | 335 | Celery Integration |
| 1 | 278 | Documentation Configuration |
| 1 | 327 | Blueprint Apps Package |
| 1 | 258 | CLI Apps Package |
| 1 | 285 | Inner Package |
| 1 | 275 | WSGI Entry |

Three things are wrong here:

1. **The largest subsystem is tests.** 8 of 12 subsystems are tests, examples, or
   config. RepoWise ranks by PageRank and offers `--skip-tests`.
2. **The 18 most important files in Flask share one 333-character description.**
   `app.py`, `ctx.py`, `sessions.py`, `templating.py` and all of `sansio/` are one
   undifferentiated blob — while a single test fixture ("Inner Package") gets its
   own subsystem.
3. **Community detection is the wrong axis for documentation.** It groups by import
   topology; a reader wants grouping by concept. `sansio/` exists for a *design*
   reason the graph cannot see — and a03 ("why is there a sansio package") is one of
   our worst losses, 1.0 vs 3.0.

#### What would actually move the number

Ordered by expected effect per unit of work:

1. **Add a file-level page type.** The single biggest lever. RepoWise's win is
   almost entirely its 79 per-file pages. We already have per-file `role` +
   `key_symbols` in the brief — the structure exists, the prompt just refuses to
   elaborate on it. Expect most of the 1.2 → 2.5 gap to close here.
2. **Allow cross-subsystem citation, then verify it.** Relax "never cite outside
   this subsystem" to "cite anything, every citation is verified against evidence".
   `verify_citations` already does the checking; the restriction is redundant
   belt-and-braces that costs the explanatory content. This is the fix that makes
   flow/lifecycle questions answerable at all.
3. **Raise the length caps.** "2-4 sentences" → sectioned prose (Overview,
   Responsibilities, How it works, Gotchas). Cheap to try, immediate effect.
4. **Weight clusters by PageRank and demote tests/examples** so the core gets the
   budget instead of fixtures.
5. **Add a "why" pass.** Nothing in the current prompt asks for design rationale,
   which is precisely what the judge rewarded in RepoWise's pages.

#### What not to conclude

- Not a model problem — same model wrote both wikis.
- Not a cost problem — AIRview used *less* LLM spend, and got less back.
- RepoWise's prose is well grounded (0.5% ungrounded identifiers, and most of those
  benign). Do not attack their accuracy; we lose that argument on the evidence.

---

#### Is AIRview "efficient"? Tested, and mostly no

The tempting reading: 1.21 vs 2.54 while writing 12.5x less prose sounds efficient.
Two measurements, opposite answers.

##### Per character delivered — no, we are worse

The judge received an **equal 12,000-character budget from each system**. The 12.5x
is total corpus size; retrieval only ever delivers a fixed budget. At identical
context size we scored half as well, so per character actually shown we are less
efficient, not more.

Sweeping the budget to test whether terse one-liners pack more signal:

| budget | AIRview | RepoWise | gap |
|---|---|---|---|
| 12,000 | 1.21 | 2.54 | 1.33 |
| 3,000 | 1.21 | 2.25 | 1.04 |
| 1,000 | 1.00 | 1.58 | 0.58 |

The gap narrows as the budget tightens — RepoWise's long pages suffer more from
truncation — but **there is no crossover. AIRview does not lead at any budget**,
and preference stays lopsided (17-6 even at 1,000 chars). AIRview also degrades at
1,000, so it is not genuinely budget-insensitive.

##### Per dollar — yes, genuinely

| | tokens | calls | cost |
|---|---|---|---|
| RepoWise | 807,636 | 114 | $0.1751 |
| AIRview | 54,056 | 13 | ~$0.0117 (blended-rate estimate) |

14.9x fewer tokens, 8.8x fewer calls. Quality per dollar: **AIRview 103 vs
RepoWise 14.5 — 7.1x better**.

##### Why this is not the win it looks like

1. **The efficiency and the quality gap are the same design decision.** AIRview is
   cheap *because* the prompt caps it at one sentence per symbol. That is the
   identical fact as Cause 1 above. You cannot bank the efficiency as a virtue and
   also plan to fix the quality — fixing it spends exactly that efficiency.
2. **$0.18 vs $0.012 per repo is a margin story, not a customer story.** On a
   $29.99/mo plan neither number is visible to the user. A developer asking "how
   does request handling work" gets a worse answer from us and does not care that
   it was cheaper to produce.
3. **Do not publish "7x more efficient" as a quality claim.** It is true and
   defensible as a unit-economics statement. Used as a proxy for docs quality it is
   the kind of overstatement this whole benchmark exists to avoid.

---

### Fixes implemented, and what they moved

All five recommendations shipped. Re-measured with the identical harness, judge,
rubric and 12,000-char budget.

| | AIRview v1 | **AIRview v2** | RepoWise |
|---|---|---|---|
| architecture score (0-3) | 1.21 | **1.96** | 2.42 |
| gap to RepoWise | 1.33 | **0.46** | — |
| total prose | 50,686 ch | 113,011 ch | 409,915 ch |
| tokens | 54,056 | 108,706 | 807,636 |
| LLM calls | 13 | 39 | 114 |
| cost | ~$0.012 | ~$0.024 | $0.175 |

**65% of the gap closed for 2x the tokens.** v2 now also beats our own raw code
chunks (1.67), which v1 did not — the docs finally earn their place over just
retrieving source. Still behind RepoWise, and judge preference is still 17-7
against us; this narrowed the gap, it did not close it.

#### What changed

1. **File-level pages** (`generate_file_pages`, `build_file_page_record`).
   Sectioned markdown — Overview / Why it exists / How it works / Key symbols /
   Gotchas — for the top files by importance. 22 planned on Flask, **18 kept: 4 were
   rejected by citation verification**, which had rejected nothing in v1. Pages hang
   off the existing `files` entry as `detail`, so there is no migration and no new
   table.
2. **Cross-subsystem citation allowed, still verified.** The prose may now cite any
   file in the repo; `verify_citations` already checked repo-wide, so the old
   "never cite outside this subsystem" rule was blocking explanation while adding no
   safety. The `files`/`key_symbols` arrays stay brief-restricted — those are
   structural.
3. **Length caps raised and a rationale pass added.** Subsystem descriptions 2-4 →
   4-8 sentences with a required "why it exists as a separate unit" sentence; file
   roles 1-2 → 2-3 sentences; symbol explanations 1 → 1-2.
4. **Importance ranking** (`rank_files_by_importance`): in-degree + churn + symbol
   count, with tests/examples/docs demoted 0.15x.

#### Two bugs found while implementing

- **Ranking on in-degree alone buried the most important files.** Entry points sit
  at the *top* of the import tree, so little imports them: Flask's `app.py` ranked
  15th, below `typing.py`. Fixed by adding a symbol-count term.
- **Hotspot churn was always read as zero** — the scanner emits `churn_count`, the
  ranking read `commits`. (On this corpus churn is degenerate anyway: 30 entries all
  at `churn_count: 1`, from limited history.)
- **The AIRview cache had no prompt version**, so its key depended only on the scan.
  Editing any prompt would have silently served pages written by the old prompt
  forever. `build_evidence_packet` now carries `prompt_version`, and
  `AIRVIEW_PROMPT_VERSION` is bumped to "2".

#### Where the remaining 0.46 is

The judge still prefers RepoWise on breadth: they write a page for all 79 files, we
write 18. The cheapest next lever is raising `DEFAULT_MAX_FILE_PAGES` / lowering
`FILE_PAGE_SCORE_FLOOR` — this is now a dial, not a rewrite. Whether that is worth
the tokens is a product call, not a technical one.

#### Is "more pages" the next lever? Measured: no

`max_files` was **a dial connected to nothing**. `FILE_PAGE_SCORE_FLOOR` was
anchored to the top score, and Flask's `src/flask/__init__.py` scores 79 - 2.7x the
runner-up, because everything imports the re-export hub. That set the floor at 3.16
and selected the same 22 files whether `max_files` was 22, 40, or 83. Fixed by
anchoring the floor to the median non-demoted score; the budget is now the control.

But raising it buys almost nothing here. Below the cut, exactly one substantive file
sits above the tests: `src/flask/blueprints.py` (2.23). Everything from rank 24 down
is `tests/*` and `examples/*`.

**The 79-vs-18 framing is misleading.** RepoWise's 79 file pages include ~40 test,
example and config files. We document 22 of Flask's ~24 substantive source files.
Coverage is already near-complete; the remaining gap is depth and two blind spots.

#### The actual next levers, in value order

1. **Declaration-only files are invisible to us.** The scanner extracts functions and
   classes; `src/flask/signals.py` has neither. It is 17 lines of module-level
   `x = _signals.signal(...)` assignments — and it exports **10 public names, Flask's
   entire signals API**. Consequences, both measured here: it gets no wiki page (the
   no-symbols guard skips it), and it was **our only miss in the location benchmark**
   (q32 — nothing for an embedder to grip). Same root cause, both halves. Extending
   symbol extraction to module-level assignments fixes both, and generalises to
   settings modules, registries, enums and route tables.
2. **Citation rejection is all-or-nothing.** `debughelpers.py` (7 functions, 4
   classes) produced a page twice, cited something unverifiable both times, and was
   discarded entirely. Subsystems already degrade gracefully — `SUBSYSTEM_DESCRIPTION_UNAVAILABLE`
   keeps the verified file list and drops only the prose. File pages should do the
   same: strip the offending sentence, keep the verified sections.
3. **Depth per page**: 3,454 chars vs RepoWise's ~5,188. The 250-400 word target in
   `FILE_PAGE_WRITING_SYSTEM_PROMPT` is a one-line change.
4. **The frontend does not render `detail`.** The pages exist in stored data and are
   invisible to users. No benchmark impact, maximum product impact.

---

### Declaration-only fix: shipped, half-worked

Module-level bindings are now extracted (`_extract_python` returns a fifth
`constants` list; `symbols.constants` is on every module, empty for languages
whose extractor does not yet populate it). Consumers updated: search index,
wiki_mapping briefs, live_wiki file pages, evidence packet, evidence resolution,
`find_symbol_source`. On Flask: **134 module-level constants recorded**, and
`signals.py` went from 0 symbols to 11.

#### Wiki side: fixed

`src/flask/signals.py` now earns a file page with all **10 public signals** as key
symbols. It was previously skipped entirely by the no-symbols guard, leaving Flask's
whole signals API undocumented. This was the goal and it works.

#### Retrieval side: NOT fixed, and it cost a point

| | top-1 | top-3 | top-5 | q32 |
|---|---|---|---|---|
| before | **75.0%** | 90.6% | 96.9% | miss |
| after (chunk per constant) | 71.9% | 90.6% | 96.9% | miss |
| after (one grouped chunk) | 71.9% | 90.6% | 96.9% | miss |

Two attempts, neither fixed the target question.

**Attempt 1 - a chunk per constant.** `signals.py` went from 1 chunk to 12, but each
was a ~60-character line (`template_rendered = _signals.signal("template-rendered")`)
carrying almost no meaning, and eleven thin chunks diluted the file's representation.
q32 still missed; q15 regressed (`testing.py` lost top-1 to `app.py`).

**Attempt 2 - one grouped declarations chunk per file.** Recovered q15, and lifted
`signals.py` from unranked to **rank 12** on q32 — real movement, still not top-5.
But the grouped chunk now *over*-matches: it contains `appcontext_pushed`,
`appcontext_popped`, `request_started`, which beat `ctx.py` on q06, *"the object that
holds per-request state pushed onto and popped off a stack"*. One regression traded
for another.

#### Stopping here deliberately

Two rounds of retrieval tuning against 32 questions we wrote ourselves is already at
the edge of fitting noise rather than improving retrieval. A third round that moves
top-1 back to 75% would not be evidence of anything - the honest move is a larger,
independently-authored question set before tuning further.

The scanner change stays regardless: a file exporting ten public names is not an
empty module, and every consumer of the evidence was being told that it was. That is
a correctness fix whose value does not depend on this benchmark. But it did not buy
the retrieval win it was supposed to, and the top-1 number went **down**.

#### Wiki-to-wiki, after the declaration fix

The constants change was aimed at the wiki, and measured there it delivers.

| | score | gap | tokens | calls | cost |
|---|---|---|---|---|---|
| AIRview v1 (baseline) | 1.21 | 1.21 | 54,056 | 13 | ~$0.012 |
| AIRview v2 (file pages, caps, cross-citation) | 1.96 | 0.46 | 108,706 | 39 | ~$0.024 |
| **AIRview v3 (+ module-level declarations)** | **2.17** | **0.25** | 113,775 | 38 | ~$0.025 |
| RepoWise | 2.42 | — | 807,636 | 114 | $0.175 |

**81% of the original gap closed, at 7.1x fewer tokens and 7.1x lower cost.**
Judge preference moved from 4-20 against us to 8-15.

The declaration fix contributed **+0.21** on its own, for +5,000 tokens. Verified
pages rose from 18/22 to **21/22**, and `src/flask/signals.py` now carries a
3,363-character page opening "These signals allow extensions and applications to
hook into framework events" - which is close to verbatim what the retrieval question
q32 asked for, and which did not exist in any form before this change.

So the same fix that was net-negative for retrieval (-3.1 points of top-1) is
clearly positive for the wiki (+0.21). Reported separately rather than netted,
because they are different products and the trade runs in opposite directions.

#### Scope of this PR

The scanner now records module-level bindings and every wiki consumer uses them.
The **search-index chunking** change is deliberately **not** included: it measured
net-negative (top-1 75.0% → 71.9%, and it did not fix the question it targeted), and
the wiki result above does not depend on it. `build_chunks` simply ignores the new
`symbols.constants` key, so retrieval behaviour is byte-identical to master.

That change is worth revisiting only against a larger, independently-authored
question set - tuning it further against these 32 self-authored questions would be
fitting noise.

</details>

**Original measurement, kept for the record, not the current number:**

| | score | gap | tokens | cost |
|---|---|---|---|---|
| AIRview | 2.13 | 0.22 | 114K | ~$0.025 |
| **RepoWise** | **2.35** | — | 808K | $0.175 |

Measured on a pre-0.8.0 build, single Flask corpus, one unrepeated judge
pass. Superseded by the five-corpus table above; left here rather than
deleted since the retrieval table elsewhere on this page is separately
versioned to 0.8.11 and this section always noted it wasn't.

## Answering from a file — fallback vs RepoWise `get_context`

Blind pairwise judge, 0-3, three repeats, each file graded twice with the two
systems' positions swapped, both bundles truncated to the same character
budget, tool names scrubbed.

On the seven files where **both** systems return substantive material:

| | score | n | repeats |
|---:|---:|---:|---:|
| **Aletheore file fallback** | **2.857** | 7 | 3 |
| RepoWise `get_context` | 2.000 | 7 | 3 |

Gap **+0.857**, identical in all three repeats. The judge ran at temperature 0,
so that zero spread shows the judge is stable — not that the result would
survive a different judge or a different question set. At n=7, one file
flipping moves the gap by 0.14-0.43. It is a small result.

RepoWise wins one of the seven: `tests/test_blueprints.py`, 3.0 against our
2.0, where it returned full test bodies and we truncated to a symbol index.

A further 15 files (yaml, toml, rst, `uv.lock`) were graded and are reported
here as **coverage, not score**. RepoWise returns `"<file>: empty or non-symbol
file"` or `Target not found` for all fifteen, and the judge scored every one
0.0. That is RepoWise declaring a file out of scope, not losing on quality.
Pooling those fifteen zeros into the headline yields a "+2.07" gap that says
nothing about usefulness, and we are not publishing one.

## Deterministic analysis vs. bare LLM

A different question from everything above: not "Aletheore vs. RepoWise,"
but for the parts of Aletheore that are **not** an LLM call at all — hotspots,
ownership, dead-code, computed from real git history and a real import graph —
can a bare LLM reproduce the answer if it's simply handed the same data?

No. On the same flask corpus, given the exact same git log slice and import
statements Aletheore's scanner consumes:

| | Aletheore | gpt-5.6-luna (bare) | gpt-5.6-terra (bare) |
|---|---|---|---|
| Hotspots (top 10 by commit count) | exact, every run | declined — asked for real code instead | **0/10 counts correct**, 4 fabricated entries |
| Ownership (top 8 by commit count) | exact | 1/8 exact, mean error ~14.5, drops a real contributor | 4/8 exact, still fabricates a person |
| Dead code (unreachable modules) | 2/2, zero false positives | 48 flagged, **4.2% precision** | 49 flagged, **4.1% precision** |

Full write-up, methodology, and known limitations (including a real bug this
testing surfaced — `ownership <file>` ignores its own argument) in
[`DETERMINISTIC_VS_LLM.md`](DETERMINISTIC_VS_LLM.md).

<details>
<summary><strong>Full write-up: deterministic analysis vs. bare LLM (hotspots, ownership, dead code)</strong></summary>


### Deterministic analysis vs. bare LLM

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

#### Corpus

Same repository as the retrieval benchmark above: [pallets/flask](https://github.com/pallets/flask)
at `2a8a38b051fc248865730bf3511bf2e2ea325e81`, 5,555 commits, 83 Python
files. `aletheore` CLI `0.8.12`.

#### Methodology

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

#### Test 1: Hotspots — which files change the most

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

#### Test 2: Ownership — who actually owns this code

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

#### Test 3: Dead code — unreachable modules

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

#### A structural limit, not just an accuracy one

205,425 tokens for the full hotspots history is past what fits in one
completion for most models before the question of whether the model can
count correctly even arises. The 1,500-commit slice above is a
concession *to* the bare-LLM side. Aletheore's scanner processed all
5,555 commits with no such ceiling and no decision needed about how much
history to leave out.

#### Known limitations

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

#### Reproducing

```bash
python scripts/det_vs_llm_build_inputs.py /path/to/output 1500   # from inside a target repo checkout
python scripts/det_vs_llm_exact_ground_truth.py                   # no API calls
python scripts/det_vs_llm_run_bare_llm.py gpt-5.6-luna             # real API calls, ~$0.01
```

All inputs, model outputs, and ground truth used above are committed in
`results/det_vs_llm_*` — nothing here depends on state outside this repo.

</details>

## Deterministic scanner accuracy

A different axis again: Aletheore's five fully-deterministic scanners
(no LLM, no judge) — `aletheore_secrets`, `aletheore_vulnerabilities`,
`aletheore_dead_code`, `aletheore_licenses`, `aletheore_database` — plus
`aletheore_ast_pattern` (structural code search), none of which had a
systematic accuracy measurement before this pass. Each corpus's own
README/REPORT has the full case tables, root-cause writeups, and fix
details; the headline numbers:

| benchmark | pilot result | real-repo finding |
|---|---|---|
| **secrets + vulnerabilities** | secrets 6/6 recall, 0/5 false positives · vulnerabilities 10/10 recall, 0/7 false positives, all 10 manifest ecosystems covered | 21,430 files across 20 real repos, 96 secrets + 231 vulnerability findings manually reviewed — **6 real product gaps found and fixed**, all now shipped with regression tests. Head-to-head against RepoWise on secrets, same 20 repos: RepoWise misses 5 of 6 real credential formats outright (case-sensitive patterns, no vendor-format detection) and **every one of its 375 real-repo findings was noise** — mostly Django's own test-suite fake passwords, zero real secrets found |
| **dead code** | 10/10 recall, 0/7 false positives | Flask reported **all six of its real runtime dependencies as unused** — a severe bug (the unused-dependency check was reading a graph field that structurally excludes external packages) found and fixed |
| **AST-pattern search** | all 12 existing unit tests pass | a real, reproducible `tree-sitter` segfault on large repos — **not 3.14-only as previously documented**, reproduces on 3.12 too, and on 3.14 specifically only under repeated calls within one long-lived process (the real MCP-server shape). Now fixed via batched subprocess isolation, verified 20/20 clean on both versions |
| **license detection** | 46 pre-existing unit tests, all passing | **3 real gaps found and fixed**: BSD license bodies contain no "BSD" keyword at all, `LICENSE.rst` wasn't a recognized filename, and Maven license lookups never followed `<parent>` POM references (silently returned "unknown" for Guava, Guava-testlib, and Protobuf-java) |
| **SQL schema extraction** | zero crashes across 5,378 real migration files, 9 real repos, both raw-SQL and ORM-native (Django/Rails/Alembic) conventions | **8 real gaps found and fixed** across two rounds (parser + ORM); one alone — a Django FK field subclass Sentry uses 249 times — took Sentry's extracted relations from 8 to 235. Head-to-head against Repowise on the same repos: Repowise never replays `ALTER`/`RENAME`/`DROP`, extracted zero foreign keys or indexes across 622 files, and has no ORM-migration concept at all |

All five ran the real production functions against real, large open-source
repos (Django, Flask, react, client-go, gson, cal.com, Sentry, and more) —
not mocks, not hand-built fixtures alone. Full writeups:
[`security-scanner-benchmark/`](security-scanner-benchmark/README.md)
([results](security-scanner-benchmark/REPORT.md)) ·
[`dead-code-benchmark/`](dead-code-benchmark/README.md) ·
[`ast-pattern-benchmark/`](ast-pattern-benchmark/README.md) ·
[`license-detection-benchmark/`](license-detection-benchmark/README.md) ·
[`sql-schema-benchmark/`](sql-schema-benchmark/README.md)
([results](sql-schema-benchmark/REPORT.md)).

<details>
<summary><strong>Full write-up: security-scanner-benchmark (secrets + vulnerabilities)</strong></summary>


*Paths below (`secrets/`, `vulnerabilities/`, `real-repo-validation/`, `results/`) are relative to `security-scanner-benchmark/`.*

#### Aletheore Security-Scanner Benchmark

Measures precision/recall of Aletheore's two deterministic security
scanners — `aletheore_secrets` (regex/entropy credential detection,
`src/aletheore/secrets.py`) and `aletheore_vulnerabilities` (OSV.dev-backed
dependency CVE lookup, `src/aletheore/vulnerabilities.py`) — against a
labeled ground-truth corpus. These are the scanners behind Aletheore's
"evidence-backed" findings claim; unlike `benchmarks/pr-review-benchmark/`
(which scores LLM-synthesized PR review comments), neither had a
systematic accuracy measurement before this benchmark — only reactive bug
fixes had touched them.

Both scanners are fully deterministic (no LLM calls), so unlike
`pr-review-benchmark`, this benchmark has no paid-API cost and no LLM
judge: ground truth is exact-match against a labeled corpus, not a
judged score.

A synthetic pilot corpus (11 secrets cases, 5 vulnerabilities cases)
gives exact-match ground truth; a real-repo validation run (20 real
open-source repos, 21,430 files) gives a real false-positive-rate signal
the synthetic corpus can't provide on its own — and found 6 real product
gaps in `secrets.py`, all now fixed with regression tests. See
`REPORT.md` for full results and analysis.

##### Layout

```
secrets/
  cases/<id>/repo/...          fixture file tree to scan
  cases/<id>/ground_truth.yaml expected finding (or none)
  scripts/fixtures.py          placeholder -> fake-secret expansion (see below)
  scripts/run_benchmark.py     runs find_secrets() against every case, scores it

vulnerabilities/
  cases/<id>/repo/...          a single dependency manifest (real historical
                                package/version pinned to a real, publicly
                                documented CVE, verified against OSV.dev
                                directly at corpus-build time)
  cases/<id>/ground_truth.yaml expected finding (or none)
  scripts/run_benchmark.py     runs check_vulnerabilities() against every
                                case, scores it (hits the real OSV.dev API)

real-repo-validation/
  fetch_repos.sh                downloads 20 real OSS repos (11 already
                                 vetted in pr-review-benchmark's own
                                 corpus, 9 more added to cover missing
                                 ecosystems) at pinned commits, into a
                                 scratch dir - never checked in here
  run_real_repos.py             runs both scanners against those real
                                 trees for a real-scale FP-rate signal
                                 the synthetic corpora can't provide
  results-2026-09-03.json       raw output from the run described in
                                 REPORT.md's "Real-repo validation"
```

##### Why secrets fixtures store placeholders, not literal values

`secrets/cases/*/repo/**` files contain tokens like
`__BENCHMARK_AWS_ACCESS_KEY__`, not literal fake credentials. Storing a
real-shaped secret (even a fabricated one) directly in the repo trips
GitHub's push protection — exactly the problem
`pr-review-benchmark/scripts/fixtures.py`'s docstring documents for its
Stripe-key case. `secrets/scripts/fixtures.py` generalizes that same
fix: the runner copies each case's `repo/` into a tempdir and expands
placeholders there, so the committed corpus never contains anything a
secret scanner (GitHub's or Aletheore's own) would match, while the code
actually scanned always does.

##### Running

```bash
python3 secrets/scripts/run_benchmark.py
python3 vulnerabilities/scripts/run_benchmark.py
```

Each prints a per-case verdict table plus recall / false-positive
numbers. No setup beyond `pip install -e src` (for the `aletheore`
package) and `pyyaml`.

For the real-repo validation run (see `REPORT.md`), from an empty
scratch directory:

```bash
cp <this-dir>/real-repo-validation/{fetch_repos.sh,run_real_repos.py} .
./fetch_repos.sh
python3 run_real_repos.py
```

##### Known limitations (pilot)

1. **Small pilot, not a full corpus.** All 7 secret patterns and all 10
   vulnerability ecosystems now have at least one pilot case
   (`private_key_header` and three `generic_credential_assignment`/
   `private_key_header` false-positive shapes were added after the
   real-repo run found real gaps in them; crates.io/RubyGems/Packagist/
   NuGet/Gradle/Swift were added after being proven correct via the
   real-repo run first, then given a dedicated hand-verified-CVE case
   each). The secrets pilot has 5 true-negative cases now (up from 1);
   vulnerabilities has 7 (up from 1, one per ecosystem) - still enough to
   catch a broken parser, not enough for a statistically meaningful
   per-ecosystem false-positive-rate claim on its own.
2. **The vulnerabilities benchmark's ground truth *is* OSV.dev**, the
   same source `check_vulnerabilities` queries live. This isn't an
   independent oracle the way the secrets corpus's hand-authored ground
   truth is — it mainly tests Aletheore's manifest-parsing and
   OSV-integration correctness (does it parse this pom.xml/go.mod/
   package.json/requirements.txt right, query the right ecosystem name,
   surface the result), not "does OSV.dev's data agree with reality."
   A case's verdict can also drift if OSV.dev's own database changes
   after corpus-build time (recorded per-case in each `ground_truth.yaml`
   description).
3. **Live network dependency.** The vulnerabilities run hits the real
   OSV.dev API; a case reports `ERROR` (excluded from recall/FP
   denominators) rather than a false verdict if OSV.dev is unreachable.

---

#### Aletheore Security-Scanner Benchmark — Results

Run date: 2026-09-03. First-ever systematic accuracy measurement for
`aletheore_secrets` and `aletheore_vulnerabilities` — the deterministic
scanners behind Aletheore's "evidence-backed" findings claim. Two rounds:
a synthetic pilot corpus (exact-match ground truth), and a real-repo
validation run (real, uncontrolled code) that found and drove fixes for
six real product gaps, all now shipped — including the one gap round 2
initially deferred as narrower/higher-risk, closed in a follow-up pass
once the rest of the sweep was done.

##### Synthetic pilot corpus

| case_id | category | outcome |
|---|---|---|
| 001-aws-access-key | true_positive | TP |
| 002-github-token | true_positive | TP |
| 003-stripe-key | true_positive | TP |
| 004-slack-token | true_positive | TP |
| 005-google-api-key | true_positive | TP |
| 006-uuid-not-a-secret | true_negative | TN |
| 007-private-key-header | true_positive | TP |
| 008-test-tls-certificate | true_negative | TN |
| 009-property-reference-not-a-secret | true_negative | TN |
| 010-truncated-example-not-a-secret | true_negative | TN |
| 011-pem-header-boilerplate-no-body | true_negative | TN |

**secrets: recall 6/6, false positives 0/5.** Cases 007-011 were added
after the real-repo run below found real gaps in patterns the original
5-case pilot didn't exercise (`private_key_header`, and three new
`generic_credential_assignment`/`private_key_header` false-positive
shapes) — each new case encodes the exact real shape that was found, so
the pilot now has permanent regression coverage for every fix in this
report.

| case_id | ecosystem | category | outcome |
|---|---|---|---|
| 001-log4shell-maven | Maven (pom.xml) | true_positive | TP |
| 002-flask-pypi | PyPI | true_positive | TP |
| 003-jwt-go-algorithm-confusion | Go | true_positive | TP |
| 004-lodash-redos-npm | npm | true_positive | TP |
| 005-six-clean-pypi | PyPI | true_negative | TN |
| 006-time-crate-segfault-cratesio | crates.io | true_positive | TP |
| 007-clean-cratesio | crates.io | true_negative | TN |
| 008-rack-dos-rubygems | RubyGems | true_positive | TP |
| 009-clean-rubygems | RubyGems | true_negative | TN |
| 010-guzzle-psr7-header-injection-packagist | Packagist | true_positive | TP |
| 011-clean-packagist | Packagist | true_negative | TN |
| 012-newtonsoft-json-nuget | NuGet | true_positive | TP |
| 013-clean-nuget | NuGet | true_negative | TN |
| 014-jackson-databind-xxe-gradle | Maven (build.gradle) | true_positive | TP |
| 015-clean-gradle | Maven (build.gradle) | true_negative | TN |
| 016-swift-nio-crlf-injection-swift | SwiftURL | true_positive | TP |
| 017-clean-swift | SwiftURL | true_negative | TN |

**vulnerabilities: recall 10/10, false positives 0/7 — all 10 ecosystems
`vulnerabilities.py` parses now have a pilot case.** Cases 006-017 close
out the gap this report's original "Suggested next steps" flagged
(crates.io, RubyGems, Packagist, NuGet, Gradle, Swift never had a
hand-verified CVE case, only real-repo-run coverage). Every true-positive
case's CVE was independently confirmed against live OSV.dev at
corpus-build time (2026-09-03), same rigor as the original 4; case 014
deliberately uses Gradle's Groovy-DSL manifest format (not pom.xml) to
get real parser coverage distinct from case 001 despite sharing the same
underlying OSV "Maven" ecosystem. No gaps found — every ecosystem's
manifest parser produced the correct recall/false-positive result on the
first pass.

Both scanners run for real here, not mocked: `find_secrets()` scans
actual materialized fixture files, `check_vulnerabilities()` makes real,
live calls to OSV.dev — the same functions and API production uses.

**Caveats**: N is still small per ecosystem (1 true-positive + 1
true-negative case each, except PyPI/Maven with more) — enough to catch
a broken parser, not enough for a statistically meaningful per-ecosystem
claim on its own. The vulnerabilities arm's ground truth is OSV.dev
itself, the same source the scanner queries live — a clean pass mainly
confirms manifest-parsing/OSV-integration correctness, not independent
real-world accuracy. See `README.md`'s "Known limitations" for the full
list.

##### Real-repo validation

The synthetic pilot controls every input, so it can't say anything about
false-positive rate on real, uncontrolled code. Two rounds of real-repo
scanning fixed that: 11 repos initially (reusing repos/commits already
vetted in `pr-review-benchmark/cases/*/repo.txt`), then 9 more added to
cover ecosystems and repo shapes the first round didn't touch (Rust,
Ruby, PHP, .NET, Gradle/Kotlin, Swift, plus 3 large diverse Python/Go/JS
repos for deeper secrets-FP-rate signal). All 20 repos downloaded to a
scratch directory (never committed here) and scanned directly with
`find_secrets()`/`check_vulnerabilities()`.

| repo | ecosystem | files | secrets findings | vuln findings |
|---|---|---|---|---|
| flask | PyPI | 242 | 0 | 25 |
| requests | PyPI | 92 | 0 | 0 |
| click | PyPI | 145 | 0 | 0 |
| express | npm | 213 | 0 | 4 |
| lodash | npm | 95 | 0 | 13 |
| axios | npm | 442 | 1 | 22 |
| cobra | Go | 65 | 0 | 0 |
| gin | Go | 127 | 1 | 51 |
| gorilla/mux | Go | 26 | 0 | 0 |
| gson | Maven | 312 | 0 | 0 |
| junit4 | Maven | 566 | 0 | 0 |
| clap | crates.io | 612 | 0 | 42 |
| sinatra | RubyGems | 289 | 2 | 30 |
| laravel | Packagist | 56 | 0 | 5 |
| restsharp | NuGet | 466 | 4 | 0 |
| okhttp | Gradle | 835 | 18 | 2 |
| penny-bot (vapor) | Swift | 244 | 17 | 0 |
| django | PyPI | 6,979 | 32 | 10 |
| client-go | Go | 2,531 | 20 | 2 |
| react | npm | 7,093 | 1 | 25 |
| **total** | | **21,430** | **96** | **231** |

Every one of the 96 secrets findings was manually reviewed (path,
surrounding code, and — critically — cross-checked against the actual
file content, never just the redacted `match_preview` hash). That review
found and fixed **six real product gaps**, all now shipped with
regression tests, re-verified against the exact real files that
surfaced them:

###### Fix 1 — PEM test certificates never suppressed (found round 1)

`private_key_header`'s "value" is the fixed header line
(`-----BEGIN RSA PRIVATE KEY-----`), whose entropy (~3.38) sits just
above `_is_likely_placeholder`'s low-entropy threshold (3.0) regardless
of whether the key behind it is real or a test fixture — so a committed
test certificate at an unambiguously test-suggestive path was never
suppressed. Found in `axios/tests/unit/adapters/key.pem` and
`gin/testdata/certificate/key.pem`. **Fix**: for `private_key_header`
specifically, a test-suggestive path is now sufficient on its own —
entropy isn't a meaningful signal for this pattern either way. Tests:
`test_find_secrets_flags_a_test_tls_certificate_as_likely_placeholder`,
`test_find_secrets_does_not_downgrade_a_private_key_header_outside_a_test_path`.
Pilot case: `008-test-tls-certificate`.

###### Fix 2 — bare property/variable references matched as literal secrets (found round 2)

`generic_credential_assignment`'s value class includes `.` to support
real dotted-key shapes (`self.PASSWORD=`, `cfg.API_KEY=`), but that same
allowance means `secret = obj.Attribute` — ordinary variable/property
reference code, never a hardcoded credential — matches too. Found
**independently in three unrelated codebases**: RestSharp's C# OAuth2
authenticators (`["client_secret"] = TokenRequest.ClientSecret`),
client-go's Go kubeconfig merging (`Password = configAuthInfo.Password`),
and Django's own Python `salted_hmac()` (`secret = settings.SECRET_KEY`)
— the repeated, independent appearance is what made this the
highest-confidence fix of the round. **Fix**: a value matching a bare
dotted-identifier-chain shape is now treated as a placeholder, gated by
a per-segment length cap (32 chars) tuned against the longest real
identifier segment found (`promptedCredentials`, 19 chars) and the
shortest real dotted-credential segment already covered by an existing
test (Google AI Studio's `AQ.<43-char random>` key format) — so the fix
can't swallow that real format. Tests:
`test_find_secrets_flags_a_property_reference_as_likely_placeholder`,
`test_find_secrets_does_not_flag_a_real_dotted_credential_value_as_a_property_reference`.
Pilot case: `009-property-reference-not-a-secret`. This fix alone
resolved most of the round-2 findings across restsharp, client-go, and
django.

###### Fix 3 — documentation truncation markers not recognized (found round 2)

sinatra's own README documents setting a session secret with
`SESSION_SECRET=99ae8af...snip...ec0f262ac` — a conventional
truncated/elided example. No real credential format contains a run of
3+ literal dots. **Fix**: `_value_looks_truncated` treats any value
containing `...` as an unambiguous placeholder signal, same tier as the
existing marker-word check. Test:
`test_find_secrets_flags_a_truncated_documentation_example_as_likely_placeholder`.
Pilot case: `010-truncated-example-not-a-secret`.

###### Fix 4 — GitHub's own OpenAPI spec example credentials not recognized (found round 2)

penny-bot vendors GitHub's official OpenAPI spec
(`github/rest-api-description`), which documents its example App/
installation JSON using fixed values — `client_secret:
1726be1638095a19edd134c77bde3aa2ece1e5d8`, `webhook_secret:
e340154128314309424b7c8e90325147d99fdafa`, and installation tokens
`ghs_16C7e42F292c6912E7710c838347Ae178B4a` /
`ghu_16C7e42F292c6912E7710c838347Ae178B4a` — identical across every repo
that vendors the spec verbatim, which is common. High-entropy and
non-repeating, so neither the marker-word nor repetition check caught
them. **Fix**: added to `KNOWN_VENDOR_EXAMPLE_VALUES`, same mechanism
already used for Stripe's published test key. Test:
`test_find_secrets_recognizes_githubs_own_published_openapi_example_values`.

###### Fix 5 — "default" missing from placeholder value markers (found round 2)

Django's own mail-config migration docs use `"password":
"default-password"` as a documented example. **Fix**: added `"default"`
to `PLACEHOLDER_VALUE_MARKERS`.

###### Fix 6 — PEM boilerplate-formatting code matched as an embedded key (found round 2, fixed in follow-up)

`okhttp`'s own `HeldCertificate.kt` — the source of its
`privateKeyPkcs8Pem()`/`privateKeyPkcs1Pem()` PEM-formatting functions —
matched `private_key_header` at a normal (non-test) path twice
(`append("-----BEGIN PRIVATE KEY-----\n")` followed by a function call,
not literal key material). Initially scoped as a deferred follow-up
(narrower than the other fixes — found in 1 of 20 repos — and needing
lookahead across lines, which none of `_is_likely_placeholder`'s other
checks need), then closed once the rest of the sweep was done. **Fix**:
a real embedded PEM block always has a base64 body (conventionally
64-76 chars/line per RFC 7468) between its BEGIN/END lines; boilerplate
string-building code doesn't. `_private_key_header_has_no_body` checks
up to 3 non-blank lines after a header match for a run of 32+ base64-
alphabet characters (comfortably above any single code identifier
encountered next to a match in this run — the longest,
`encodeBase64Lines(`, breaks at 17 chars before the `(` — and
comfortably below a real body line's length); no run found means no
body, treated as a placeholder regardless of path, same tier as the
marker-word check. Scoped to `find_secrets` only —
`find_secrets_in_history` streams individual diff-added lines and has no
equivalent "next line" to look at. Guarded against its own false-positive
risk (a real key body quoted inside a doc comment or markdown table,
prefixed with `` * `` or `|` per line, must still count as a body) with
a dedicated regression test. Tests:
`test_find_secrets_flags_a_private_key_header_with_no_body_as_likely_placeholder`,
`test_find_secrets_recognizes_a_key_body_wrapped_in_comment_markup`.
Pilot case: `011-pem-header-boilerplate-no-body`. Re-verified against the
real file: `HeldCertificate.kt`'s two boilerplate matches (lines 164,
178) now report `likely_placeholder: true`; its third match (line 529,
a KDoc comment with a real quoted example body) correctly stays
unflagged, unchanged by this fix.

###### What's left unflagged, on purpose

21 of the 96 findings remain unflagged after all six fixes — reviewed
individually, not chased further, for two different reasons:

1. **Genuinely ambiguous test-path values (~15, mostly django, one
   react)** — realistic-looking fake secrets (test passwords, fake API
   keys) under `tests/`/`__tests__/` paths, with entropy above the
   low-entropy threshold. This is deliberate, existing, tested behavior
   (`test_find_secrets_does_not_downgrade_a_real_looking_secret_under_a_test_path`):
   a real leaked secret could hide at exactly this kind of path, and
   nothing about the *value itself* distinguishes it from an
   intentionally realistic test fixture. Not a bug — a real trade-off,
   reviewed and left as-is.
2. **PEM blocks with a real base64 body outside a test path, and one
   genuinely real embedded API key (~6, all in okhttp/penny-bot)** —
   `okhttp`'s changelog, `okhttp-tls/README.md`, and `HeldCertificate.kt`
   line 529 (a KDoc example) embed real-looking example certificates in
   documentation — no decisive signal separates "real leak in docs" from
   "documented example" the way the boilerplate-code case in Fix 6
   could (a doc example's body is indistinguishable in shape from a real
   key's), so these stay visible by design, same trade-off as case 1.
   `RequestBodyCompression.java`'s `GOOGLE_API_KEY` is OkHttp's own real,
   intentionally-public sample-recipe key — a correct true positive, not
   a bug: flagging a real hardcoded key is the scanner doing its job,
   regardless of the project's own risk tolerance for it.

No further gaps were found in this sweep beyond these six — every
unflagged finding remaining was individually reviewed and falls into one
of the two categories above.

###### Vulnerabilities: 231 findings, spot-checked

Package names, pinned versions, and advisory ids (real GHSA/PYSEC/GO
identifiers) all check out as well-formed and plausible across every
ecosystem sampled — PyPI, npm, Go, crates.io (`Cargo.lock`), RubyGems
(gemspec fallback), Packagist (`composer.json`), NuGet (central package
management via `Directory.Packages.props`), and Gradle (version catalog
`libs.versions.toml`). Confirms `check_vulnerabilities` correctly parses
all of these real manifest shapes at meaningful scale, not just the one
hand-picked manifest per ecosystem the synthetic pilot samples. Swift
(`Package.resolved`) also parsed correctly via penny-bot but returned 0
findings (plausible - not independently re-verified). Not spot-checked
line-by-line the way the pilot's 4 hand-picked CVEs were verified
against OSV.dev directly.

**Caveats specific to this real-repo run**: repos chosen because they
were already vetted elsewhere in this codebase or picked to fill
ecosystem gaps, not randomly sampled — not a claim about OSS code in
general. Secrets ground truth here is manual eyeball review of match
location and real file content (not just the redacted preview), not a
pre-existing label. If a genuinely live, sensitive credential is ever
found this way in a third-party repo in a future run: never reproduce
the actual value anywhere (`match_preview` is already a salted hash,
safe to log), exclude it from any published report, and flag it to the
user for a responsible-disclosure decision rather than including it in
this benchmark's output. (No such value was found in either round — the
GitHub OpenAPI example values in Fix 4, the OkHttp sample key, and every
PEM block found are all publicly documented, intentionally-shared, or
already-flagged-correctly cases, not private leaks.)

##### Suggested next steps (not started)

- ~~Expand vulnerabilities pilot corpus: remaining ecosystems not yet
  exercised at the pilot-case level~~ — **done**, see cases 006-017 above
  (all 10 ecosystems, 10/10 recall, 0/7 false positives, zero gaps found).
- Expand the real-repo sample further (more repos per ecosystem) for a
  larger-denominator FP-rate number - 21,430 files is much stronger than
  the original 2,325, but still a fixed, non-random sample.
- Consider a named comparison (gitleaks/trufflehog for secrets,
  osv-scanner for vulnerabilities) now that Aletheore's own numbers are
  established, mirroring `pr-review-benchmark`'s PR-Agent/DeepSource
  comparison - explicitly deferred at this benchmark's design stage in
  favor of Aletheore-only accuracy first.

</details>
<details>
<summary><strong>Full write-up: secrets_scanner (head-to-head against RepoWise's own credential detection)</strong></summary>


*Paths below (`cases/`, `scripts/`, `results/`) are relative to `secrets_scanner/`.*

#### Head-to-head against RepoWise: secrets detection

RepoWise has its own hardcoded-credential detection
(`repowise/core/analysis/security_scan.py`, part of a broader
"security signals" scanner covering `eval()`, SQL injection shapes, weak
hashes, etc.), not previously compared against `aletheore_secrets`
anywhere in this repository. This directory runs both scanners
ourselves, in-process, on the same inputs — a synthetic pilot corpus
with exact-match ground truth, and 20 real open-source repos (21,430
files) for a real-world false-positive check neither tool's synthetic
test suite can provide.

**We call RepoWise's `SecurityScanner.scan_file()` directly**, the same
class its own ingestion pipeline (`repowise/core/pipeline/persist.py`)
wires in — RepoWise exposes no CLI command or MCP tool for this scan
(confirmed by reading its `cli/main.py` command list and grepping every
call site of `SecurityScanner` in the installed package); `repowise
init` runs it as a side effect and persists to a database table with no
query command. `session=None` is safe here: only `.persist()` touches
the DB, and this benchmark never calls it. Same principle
`scripts/run_aletheore.py` elsewhere in this repo already uses
(`from aletheore.search_index import search_index`, in-process, no
subprocess) — no framework overhead, no CLI-output parsing.

##### Result

| | RepoWise 0.27.0 | Aletheore 0.9.10 (PyPI, current release) | Aletheore @ `355bd98` (dev HEAD) |
|---|---|---|---|
| **Pilot corpus recall** (6 true positives) | **1/6** | 6/6 | 6/6 |
| **Pilot corpus false positives** (5 true negatives) | 0/5 | 4/5 | **0/5** |
| **Real-repo findings** (20 repos, 21,430 files) | 375 | 92 raw / 77 reported | 96 raw / **21 reported** |
| **Real-repo true positives found** (manually verified, see below) | **0** | not independently re-verified | not independently re-verified |

RepoWise misses 5 of 6 real credential formats in the pilot corpus
outright — its only two credential patterns
(`password\s*=\s*['\"]`, `(?:api_?key|secret)\s*=\s*['\"]`) are
**compiled case-sensitively** with no `re.IGNORECASE`, so
`AWS_ACCESS_KEY_ID = "..."`, `GITHUB_TOKEN = "..."`, `GOOGLE_MAPS_API_KEY
= "..."` never match a lowercase-only regex, and there's no
vendor-format detection at all (no AWS/GitHub/Slack/Google key shapes),
so it only caught the one case whose variable name happened to be
`stripe.api_key` (lowercase). On real code this is the dominant naming
convention it's blind to — `AWS_ACCESS_KEY_ID`, `API_KEY`, `SECRET_KEY`,
`DB_PASSWORD` are the standard uppercase env-var/settings convention in
real `.env`/settings files, not the exception.

**Every one of RepoWise's 375 real-repo findings sampled and manually
checked was noise, not a real secret** — see "Real-repo findings, spot
checked" below. RepoWise's two patterns require nothing beyond a literal
quote after `password =` / `secret =` / `api_key =`: no length floor
(matches `password = ''`), no entropy check, no placeholder-value
recognition, no test-path awareness. Django's own auth test suite alone
produced 365 of the 375 — `password="secret"`, `password="test"`,
`password="testpw"`, sampled at random, all real lines, all rated "high
severity." Aletheore's `_is_likely_placeholder` (see the root repo's
`src/aletheore/secrets.py`) exists specifically to distinguish this from
a real leak; RepoWise has no equivalent, at any severity level.

##### Pilot corpus: what each row is

Ported from `Aletheore/Aletheore`'s own
`benchmarks/security-scanner-benchmark/secrets/` (11 cases: 6 real
credential formats, 5 false-positive shapes found and fixed via that
repo's own real-repo validation work — case IDs and fixture contents
copied as-is, so this comparison uses the exact same, already-reviewed
ground truth, not a new corpus built to flatter either tool):

```
$ .venv-aletheore-pypi/bin/python3 scripts/score.py results/real_repos_repowise.json results/aletheore_pypi.json results/aletheore_fixed.json
```

| case_id | repowise | aletheore 0.9.10 | aletheore 355bd98 |
|---|---|---|---|
| 001-aws-access-key | FN | TP | TP |
| 002-github-token | FN | TP | TP |
| 003-stripe-key | TP | TP | TP |
| 004-slack-token | FN | TP | TP |
| 005-google-api-key | FN | TP | TP |
| 006-uuid-not-a-secret | TN | TN | TN |
| 007-private-key-header | FN | TP | TP |
| 008-test-tls-certificate | TN | FP | TN |
| 009-property-reference-not-a-secret | TN | FP | TN |
| 010-truncated-example-not-a-secret | TN | FP | TN |
| 011-pem-header-boilerplate-no-body | TN | FP | TN |

The `aletheore 0.9.10` column is the currently-published PyPI release —
it correctly detects every real format (private_key_header's pattern
already existed) but has 4 known false-positive bugs, all fixed in
`Aletheore/Aletheore#527` (open at the time of this run, not yet
released — installed here straight from that commit via
`pip install git+...@355bd98#subdirectory=src` into an isolated venv,
**not** from this machine's local dev checkout, which is shared with
other work and not a stable pin). Once #527 ships, `aletheore 0.9.10`'s
column becomes the `355bd98` column for every future reader who just
runs `pip install aletheore`.

##### Real-repo findings, spot checked

Same 20 repos as `Aletheore/Aletheore`'s own
`benchmarks/security-scanner-benchmark/real-repo-validation/` (11
reused from there directly, 9 more covering ecosystems that work didn't
touch) — not re-selected for this comparison. Every RepoWise finding
sampled was manually opened and read (not inferred from the finding's
own `snippet` field, which RepoWise truncates but does not redact —
see "A note on RepoWise's output" below):

- **Django, 365/375 of all findings**: 12 sampled at random (all
  `tests/`-path `hardcoded_password`), all confirmed
  `password="secret"` / `password="test"` / `password="testpw"` —
  literal fake test credentials.
- **axios**: `parsedURL.password = '';` (`lib/adapters/fetch.js:279`,
  real product code, not a test) — an **empty string** assignment to a
  URL object's password field, not a secret. RepoWise's pattern has no
  minimum length.
- **okhttp**: `val password = "password".toCharArray()`
  (`TlsUtil.kt:33`) — the JDK/Android standard default keystore
  password (literally the word "password"), a widely-documented
  convention, not a leak.
- **RestSharp**: `const string password = "testpassword";` — a test
  fixture.
- **flask, gin**: same pattern, test fixtures and docs examples.

**Zero of the sampled RepoWise findings were a real secret.** Aletheore
(both versions) found zero real secrets in these repos either — see
`Aletheore/Aletheore`'s own real-repo report for the two real findings
that run *did* surface (committed TLS test certificates in axios and
gin, correctly not a leak either). No repo in this set had an actual
leaked credential in either tool's output.

##### A note on RepoWise's output

`SecurityScanner.scan_file()` returns a `snippet` field (the matched
line, truncated to 120 chars) alongside each finding — unlike
Aletheore's salted-hash `match_preview`, this is the **live line text,
unredacted**. `results/real_repos_repowise.json` in this directory
strips it (only `path`/`line`/`kind` are kept) specifically so this
repository never publishes a real credential value if one is ever
found; every line above was independently re-read from the actual
downloaded repo tree during review, never taken from RepoWise's own
snippet.

##### Running

```bash
# Aletheore side needs its own venv (aletheore requires Python <3.14):
python3.12 -m venv .venv-aletheore-pypi && .venv-aletheore-pypi/bin/pip install aletheore pyyaml

# RepoWise side must run under RepoWise's own installed interpreter -
# its sqlalchemy version conflicts with other environments.
<repowise's python> scripts/run_repowise.py > results/repowise.json
.venv-aletheore-pypi/bin/python3 scripts/run_aletheore.py > results/aletheore_pypi.json

# Real-repo run: fetch the same 20 repos this used (see
# Aletheore/Aletheore's benchmarks/security-scanner-benchmark/real-repo-validation/fetch_repos.sh),
# then:
<repowise's python> scripts/run_real_repos.py /path/to/repos --tool repowise > results/real_repos_repowise.json
.venv-aletheore-pypi/bin/python3 scripts/run_real_repos.py /path/to/repos --tool aletheore > results/real_repos_aletheore_pypi.json

# Score:
.venv-aletheore-pypi/bin/python3 scripts/score.py results/repowise.json results/aletheore_pypi.json
```

##### Contents

| path | what |
|---|---|
| `cases/` | 11-case pilot corpus, ported verbatim from `Aletheore/Aletheore`'s own benchmark |
| `scripts/run_aletheore.py` | calls `aletheore.secrets.find_secrets` in-process |
| `scripts/run_repowise.py` | calls `repowise.core.analysis.security_scan.SecurityScanner.scan_file` in-process |
| `scripts/run_real_repos.py` | same two scanners against a directory of real repos |
| `scripts/score.py` | scores any set of result JSONs against `cases/*/ground_truth.yaml`, no API key |
| `scripts/fixtures.py` | placeholder→fake-secret expansion (copied from the source benchmark — see its own docstring for why fixtures store placeholders, not literal values) |
| `results/` | raw output this README's numbers were computed from |

</details>
<details>
<summary><strong>Full write-up: dead-code-benchmark</strong></summary>


*Paths below (`cases/`, `scripts/`) are relative to `dead-code-benchmark/`.*

#### Aletheore Dead-Code Detection Benchmark

Measures accuracy of `find_dead_code()` (`src/aletheore/dead_code.py`),
which detects two kinds of finding via a real `scan_repository()` run:
**unreachable modules** (no other file imports this one, and no
entry-point signal explains why) and **unused dependencies** (a package
declared in `requirements.txt`/`package.json` that no source file
imports). Never systematically benchmarked before — only reactive fixes
had touched it (the O(candidates×files)→O(files) perf fix and a
false-positive boundary fix, both PR #417/#420).

Fully deterministic (no LLM calls, no network) — like
`security-scanner-benchmark`, this has no paid-API cost and no LLM
judge.

##### Result

10 pilot cases, run via a real `scan_repository()` call per case (not
mocked): **10/10 recall, 0/7 false positives.**

| case_id | finding_type | category | outcome |
|---|---|---|---|
| 001-unreachable-module | unreachable_module | true_positive | TP |
| 002-imported-module-not-dead | unreachable_module | true_negative | TN |
| 003-main-guard-entry-point | unreachable_module | true_negative | TN |
| 004-html-script-entry-point | unreachable_module | true_negative | TN |
| 005-dotted-string-reference-not-dead | unreachable_module | true_negative | TN |
| 006-test-file-not-flagged | unreachable_module | true_negative | TN |
| 007-unused-pip-dependency | unused_dependency | true_positive | TP |
| 008-used-pip-dependency | unused_dependency | true_negative | TN |
| 009-unused-npm-dependency | unused_dependency | true_positive | TP |
| 010-used-npm-dependency | unused_dependency | true_negative | TN |

##### A real, severe bug found and fixed

Cases 008 and 010 (a real, genuinely-imported dependency) both failed on
the first run — every declared dependency was reported unused, even
ones the fixture's own source file plainly imported. Confirmed at real
scale before touching anything: scanning Flask's own repo reported
**all six of its actual runtime dependencies**
(werkzeug/jinja2/itsdangerous/click/blinker/importlib-metadata) as
unused.

**Root cause**: `module["imports"]` (`scanner/graph.py`'s
`resolved_imports`) only ever contains import targets that resolved to
*another file inside the repo* — an external package import that never
resolves to a repo-internal file is silently dropped there, by design
(that field also feeds the real import graph — edges, `imported_by`,
hotspots, MCP's `aletheore_imports` — where only real repo-internal
edges belong). `_import_roots()`, which the unused-dependency check
reads, was therefore checking a field that structurally can never
contain an external package name. Every existing unit test for this
check (`test_dead_code.py`) passed anyway, because every one of them
hand-sets `modules[0]["imports"] = ["flask"]` — a raw package name — a
shape the real scanner never produces; none of them exercised a real
scan.

**Fix**: `_raw_external_import_roots()` re-reads each Python/JS/TS
source file directly and regex-extracts raw import roots regardless of
whether they resolve internally, scoped entirely to `dead_code.py`
rather than changing what the resolvers keep in the graph-wide `imports`
field (a much larger, riskier change). Verified against the exact repo
that surfaced the bug: Flask now reports zero unused dependencies.
Regression tests: `test_unused_dependency_check_reflects_a_real_scan_not_a_hand_built_modules_list`
(a real `scan_repository()` call — the class of test that would have
caught this), plus direct unit tests for the new function.

##### A note on what "unused" real repos still report

Re-run against 4 more real repos (already downloaded for
`security-scanner-benchmark`'s real-repo validation) after the fix:
`requests` and `click` report zero unused dependencies; `express`
reports `eslint`/`hbs`/`mocha`/`nyc`, and `axios` reports a longer list
(babel/rollup/eslint/prettier/typescript/vitest/etc.). These are real,
plausible findings, not a bug — they're build/lint/test-runner tooling
declared in `package.json` and invoked via npm scripts or a CLI, never
`import`ed by any source file, so "no source file imports this" is
literally true. Whether treating CLI-only dev tooling as "unused" is the
right default (versus a lower severity, or excluding `devDependencies`
entirely) is a real product/precision question, not addressed by this
benchmark — flagged here for visibility, not fixed.

##### Running

```bash
python3 scripts/run_benchmark.py
```

##### Contents

| path | what |
|---|---|
| `cases/` | 10-case pilot corpus, one `repo/` fixture tree + `ground_truth.yaml` each |
| `scripts/run_benchmark.py` | runs `scan_repository()` against every case, scores it |

</details>
<details>
<summary><strong>Full write-up: ast-pattern-benchmark</strong></summary>


#### Aletheore AST-Pattern Search Benchmark

`search_ast_pattern()` (`src/aletheore/ast_pattern.py`, the `aletheore
query ast-pattern` command and `aletheore_ast_pattern` MCP tool) matches
a raw tree-sitter S-expression query against every parsed file of one
language in a repo. Unlike the other overnight benchmarks in this
directory (`dead-code-benchmark/`, `security-scanner-benchmark/`), this
one didn't need a new synthetic pilot corpus — `src/tests/test_ast_pattern.py`
already has 12 tests exercising the real function end-to-end (unknown
language, invalid query, TypeScript's dual .ts/.tsx grammars, line
numbering, size cap, unreadable-file resilience, match cap, char budget,
and the single-oversized-match fix from an earlier PR) — all 12 pass.

What that suite couldn't have caught: it uses single-digit-file
fixtures, and this module's one previously-known failure mode (a
tree-sitter Query/QueryCursor segfault, `requires-python = "<3.14"` in
`pyproject.toml`) was explicitly documented as needing "enough real
files/matches" to accumulate before it triggers. So instead of a
synthetic corpus, this ran real structural queries against the large
real repos already downloaded for `security-scanner-benchmark`'s
real-repo validation.

##### Result: a real, reproducible segfault on Python 3.12 — not 3.14-only

`pyproject.toml`'s own comment claimed "the exact same code against the
exact same repo runs clean on 3.12." That claim was only ever verified
against this project's own ~116 source files. Confirmed false at real
scale, reproduced twice in a row (exit code 139 both times):

```python
from pathlib import Path
from aletheore.ast_pattern import search_ast_pattern
search_ast_pattern(Path("<a real Django checkout>"), "python", "(try_statement) @try")
# SIGSEGV, Python 3.12.10, tree-sitter 0.26.0
```

Django's real tree has ~2,930 Python files. A **higher-match-density**
query against the same repo (`(function_definition) @fn`, which hits
`_AST_PATTERN_TOTAL_CHAR_BUDGET` after only ~126 matches and stops
early) completed cleanly — and two other large real repos, react (JS)
and client-go (Go), both completed cleanly too, because their test
queries happened to hit `_AST_PATTERN_MATCH_CAP` (200) within the first
few files.

**The crash correlates with how many files get fully processed before
any cap triggers, not language, match count, or Python version alone.**
A query selective enough to run long against a big enough repo can hit
this on 3.11/3.12 too — inside the officially supported, CI-tested
range — not only on the already-excluded 3.14. The two prior fixes
this codebase's own comments say were tried and failed (`del` each
iteration, `gc.disable()`/forced `gc.collect()`) evidently only ever got
verified at the ~116-file scale where the crash doesn't yet manifest.

##### Update: fixed (2026-09-04, Aletheore/Aletheore#537)

The crash itself is now fixed, not just documented. Each batch of files
runs in its own fresh worker process
(`ProcessPoolExecutor(max_workers=1, max_tasks_per_child=1)`), so no
batch's process ever accumulates enough of an object graph to trigger
the GC-driven segfault. A batch's crash is caught as `BrokenProcessPool`
and marks the result `truncated`, keeping every earlier batch's real
matches rather than losing the whole call — same honest-truncation
contract the match-cap/char-budget already used.

Verified: 20/20 clean runs on the original 3.12 crash case (was 3/4
crashed before). Also tested directly on Python 3.14 itself (previously
assumed to be the *only* affected version, and never actually tested
here) — single large calls didn't crash there (16/16 clean), but
**repeated calls within one long-lived process did**, segfaulting on the
3rd call: the realistic shape of a long-lived MCP server session, not a
one-shot script. The fix held under that harder scenario too — 20/20
clean. Both real callers (`aletheore query ast-pattern` and the
`aletheore_ast_pattern` MCP tool, including from the MCP SDK's actual
background-thread execution context) verified end-to-end, plus the fix
generalizes to a second language/repo (Go / `kubernetes/client-go`,
2,453 files). Full history in
[Aletheore/Aletheore#537](https://github.com/Aletheore/Aletheore/pull/537).

The `pyproject.toml` `requires-python = "<3.14"` upper bound was left
in place — whether to lift it now that a real fix exists is a separate,
not-yet-made call.

##### Reproducing

```bash
# Needs a large, real Python repo checked out locally - Django is what found this.
python3 -c "
from pathlib import Path
from aletheore.ast_pattern import search_ast_pattern
search_ast_pattern(Path('/path/to/django'), 'python', '(try_statement) @try')
"
echo \$?  # 139 = SIGSEGV
```

</details>
<details>
<summary><strong>Full write-up: license-detection-benchmark</strong></summary>


#### Aletheore License-Detection Benchmark

`src/aletheore/licenses.py` (`categorize_license`, `detect_repo_license`,
`check_dependency_licenses`) already had 46 unit tests, all mocking
registry responses — thorough for the fetch/cache/concurrency/timeout
machinery, but every license *text* fixture in those tests was
hand-written to obviously contain a recognizable keyword. Like
`ast-pattern-benchmark`, this ran the real functions against real repos
instead of a new synthetic corpus, specifically to find text the
existing fixtures wouldn't think to write.

##### Result: 3 real gaps found and fixed, all confirmed against real repos

###### 1. BSD license body text contains no "bsd" keyword at all

Neither the 2-clause nor 3-clause BSD license *body* text contains the
literal word "BSD" anywhere — it's purely descriptive redistribution
terms with no self-identifying name. Confirmed present verbatim (the
canonical "Redistribution and use in source and binary forms..." opening
line) in 4 real repos checked: click, flask, django, gorilla/mux. Two of
those (flask, gorilla/mux) have no machine-readable license metadata
(no `pyproject.toml`/`package.json` license field) and rely purely on
the LICENSE file body — both categorized **"unknown" despite being
unambiguously, famously BSD-licensed real projects**.

**Fix**: added the canonical BSD opening phrase itself as a permissive
marker.

###### 2. `LICENSE.rst` missing from the checked filename list

Flask's own real repo uses this exact filename (a common convention for
reStructuredText-docs-style Python projects) — invisible to
`detect_repo_license`'s filename list entirely, independent of gap #1.

**Fix**: added `LICENSE.rst` alongside the existing `LICENSE`/
`LICENSE.md`/`LICENSE.txt`/`COPYING`.

###### 3. Maven license lookup never followed `<parent>` POM references

A very common real Maven convention: the `<licenses>` block lives on a
shared parent POM, not the artifact's own. Confirmed directly: Guava's
real `guava-33.6.0-jre.pom` has no `<licenses>` element at all (only a
`<parent>` reference to `guava-parent`) — its own pom.xml even has a
comment explaining why ("copied from the parent pom because..."). A
single-level fetch (the pre-fix behavior) always returned `None` for
Guava, Guava-testlib, and Protobuf-java — three real, unambiguously
Apache-2.0/BSD-licensed artifacts found via `gson`'s own real
`pom.xml`, all three came back "unknown".

**Fix**: `_fetch_maven_license` now follows `<parent>` references up to
3 hops (real chains are 1-2 levels; bounded against an unexpected cycle
or unusually deep chain), re-verified: Guava now resolves to "Apache
License, Version 2.0", Protobuf-java to "BSD-3-Clause".

###### Bonus: CDDL added to the weak-copyleft bucket

While re-checking `gson`'s dependencies post-fix, one real, correctly-
fetched license (`javax.annotation:jsr250-api`'s "COMMON DEVELOPMENT AND
DISTRIBUTION LICENSE (CDDL) Version 1.0") fell through every existing
category to "unknown" — CDDL is a real, standard weak-copyleft license
family (same SPDX/OSI bucket as MPL/EPL), not an unrecognizable one.
Added alongside the existing weak-copyleft markers.

##### Verification

Real end-to-end checks, not just the new unit tests: `detect_repo_license`
re-run against the exact flask/gorilla-mux checkouts that surfaced gaps
#1/#2 (both now `"category": "permissive"`), `_fetch_maven_license`
re-run against the exact Guava/Protobuf-java coordinates that surfaced
gap #3 (both now resolve correctly), full `check_dependency_licenses`
re-run against gson's real repo (findings dropped from 9 to 2 — 7 of the
original 9 were Guava/Guava-testlib/Protobuf-java/Protobuf-java-util/
Caliper/Truth-proto-extension all resolving through the same
guava-parent chain, now all correctly categorized "permissive" and no
longer findings at all; the 2 that remain are a `-SNAPSHOT` version with
no published Maven Central artifact to fetch at all - expected, not a
bug - and `jsr250-api`'s CDDL dependency, which is *correctly* still a
finding post-fix: its `category` changed from the wrong "unknown" to the
real "copyleft-weak", which the findings list is supposed to surface).
Full suite: 1591 passed (46 pre-existing + 5 new `test_licenses.py`
tests, all passing).

</details>
<details>
<summary><strong>Full write-up: sql-schema-benchmark (+ head-to-head against Repowise)</strong></summary>


*Paths below (`repos.txt`, `scripts/`) are relative to `sql-schema-benchmark/`.*

#### Aletheore SQL Schema-Extraction Benchmark

Measures two things about `aletheore_database`'s schema extraction
(`src/aletheore/schema_map.py` for raw SQL, which recently moved from a
hand-written Postgres DDL tokenizer to sqlglot, and
`src/aletheore/orm_migrations.py` for ORM-native Django/Rails/Alembic
migrations — see that repo's commit history for both):

1. **Real-repo robustness** of the parser/replay engine — run against real,
   large migration histories to find crashes and mis-modeled/silently-dropped
   schema changes that a small hand-written test suite wouldn't exercise.
2. **A head-to-head against Repowise**, a competitor code-intelligence tool
   that also claims SQL support, on the same real repos.

Two rounds: round 1 covers raw `.sql` migrations across five repos; round
2 covers four more repos with zero `.sql` files at all, to check the same
two things against ORM-native migration sources instead.

Both scanners are fully deterministic (no LLM calls on Aletheore's side);
Repowise was run with `--index-only`, which explicitly skips its LLM-based
wiki generation, so this comparison has no paid-API cost on either side.

##### Methodology

**Round 1** — five real, independent open-source repos chosen specifically
for **different migration-tooling conventions**, to avoid the result being
an artifact of one ORM's SQL style:

| Repo | Real `.sql` migration files | Convention |
|---|---|---|
| [calcom/cal.com](https://github.com/calcom/cal.com) | 595 | Prisma-generated |
| [supabase/supabase](https://github.com/supabase/supabase) | 32 (of the real ones found readable) | Supabase CLI |
| [coder/coder](https://github.com/coder/coder) | 589 (`.up.sql` only) | golang-migrate |
| [windmill-labs/windmill](https://github.com/windmill-labs/windmill) | 636 (`.up.sql` only) | Rust/sqlx |
| [triggerdotdev/trigger.dev](https://github.com/triggerdotdev/trigger.dev) | 825 | Prisma-generated (independent schema from cal.com) |

**Round 2** — four more real repos, chosen because they have **zero raw
`.sql` migrations at all**, to stress the ORM-native migration parsing
(`aletheore/orm_migrations.py`) instead of the SQL tokenizer, and to see
whether Repowise's SQL claim extends to non-SQL migration sources:

| Repo | Real migration files (content-verified) | Convention |
|---|---|---|
| [apache/superset](https://github.com/apache/superset) | 383 | Alembic |
| [discourse/discourse](https://github.com/discourse/discourse) | 1,746 (root `db/migrate`) | Rails |
| [mastodon/mastodon](https://github.com/mastodon/mastodon) | 535 | Rails |
| [getsentry/sentry](https://github.com/getsentry/sentry) | 37 | Django |

All were fetched via `git clone --depth 1 --filter=blob:none --sparse`,
pinned at whatever `HEAD` resolved to on 2026-09-04 (see `repos.txt` for the
exact commits). `.down.sql` files were excluded from the golang-migrate/sqlx
repos — a real user's migration directory is applied forward-only; mixing
directions produces a schema no real deployment ever has.

###### Part 1: real-repo stress test (Aletheore only)

For each repo, `aletheore.schema_map.extract_schema()` was run directly
against the real migration directory and the result inspected for: (a) any
exception, (b) the shape and content of every `unsupported` entry (is it a
legitimate, documented scope exclusion — views, triggers, GRANT/REVOKE,
CHECK constraints — or a real gap that should have been modeled), and (c)
spot-checks of specific tables against what the real migration history
should produce.

###### Part 2: Aletheore vs. Repowise

`repowise init --index-only -y` was run against each full repo (Repowise
indexes the whole checkout; there is no per-directory scoping flag), then
`.repowise/wiki.db`'s `wiki_symbols` table was queried directly. Reading
Repowise's actual stored index rather than its CLI `search` command
matters here: `search` queries LLM-generated wiki pages, which
`--index-only` explicitly skips (0 pages, confirmed via `repowise status`)
— the raw symbol table is what actually reflects what its indexer parsed,
independent of whether documentation was ever written about it.

For round 1 (raw `.sql`), every row where `file_path LIKE '%.sql'` was
pulled, and specific known tables were compared column-for-column against
Aletheore's replayed output for the same table. For round 2 (ORM-native),
there's no `.sql` file to query for — the question instead is whether
Repowise's stored `kind` vocabulary for these files (and for the repo as a
whole) contains anything schema-aware at all (a `table`/`model`/`column`/
`relation` kind, or similar), versus generic language symbols.

##### Results

See `REPORT.md` for the full numbers and per-repo findings.

**Headline, Round 1 (Part 1):** zero crashes across all 2,677 real files
scanned (595+32+589+636+825). Three real gaps found and fixed in the
first pass across cal.com and coder; a second pass on windmill and
trigger.dev (different tooling conventions again) confirmed no further
gaps, and supabase was clean on both passes — a real signal the fixes
generalize rather than being repo-specific patches.

**Headline, Round 1 (Part 2a):** Repowise's SQL "support" is per-file,
per-statement `CREATE TABLE` extraction with no cross-migration replay —
it does not process `ALTER TABLE`, `DROP TABLE`, or `RENAME` at all. On
every repo tested, a real table's Repowise-reported column list matched
only that table's *original* `CREATE TABLE` statement, missing everything
added since — in some cases years and 70+ migrations of drift. It never
once extracted a foreign key, an index, or a `PRIMARY KEY`/`UNIQUE`
constraint from any of the 622 real `.sql` files it extracted at least
one symbol from, across all 5 repos (grepped its full stored index for
`REFERENCES`/`FOREIGN KEY`/`PRIMARY KEY` in every extracted signature -
zero real hits). It also has no way to know a table was renamed or
dropped: windmill renamed its real `queue` table to `v2_job_queue` (now 46
columns) and replaced `queue` with a view of the same name for backward
compatibility — Repowise still reports the stale, years-old `queue`
*table* definition (22 columns) as current, alongside a separate,
unlabeled `queue` VIEW symbol, with nothing connecting the two. cal.com
creates and later drops `platform_access_tokens` (10 days apart, in two
real migrations) — Repowise still lists it as a live symbol.

**Headline, Round 2 (Part 1b):** zero crashes across 2,701 real ORM
migration files (Alembic/Rails/Django) spanning Superset, Discourse,
Mastodon, and Sentry. Five real gaps found and fixed — two crashes on
malformed/unresolvable input (Discourse), one migration-directory
detection gap (Superset), and, the largest single fix of either round, a
real Django FK field subclass Sentry uses in 249 real places that wasn't
recognized at all — fixing it alone took Sentry's extracted relations
from 8 to 235.

**Headline, Round 2 (Part 2b):** Repowise has no ORM-migration
schema-extraction concept whatsoever. Its full, repo-wide `kind`
vocabulary across all four repos is generic language constructs only
(`class`/`method`/`function`/`variable`/`constant`/...) — no
`table`/`model`/`column`/`relation` kind exists anywhere. On Sentry's
largest real migration file (217 real tables, 211 real relations per
Aletheore's replay), Repowise's entire stored index is one symbol:
`class Migration`.

---

#### SQL Schema-Extraction Benchmark — Results

Run date: 2026-09-04. First systematic real-repo validation of
`aletheore_database`'s schema extraction since it moved off a hand-written
Postgres tokenizer onto sqlglot, plus the first head-to-head against
Repowise's SQL handling. Extended the same day with a second round: four
more real repos (Apache Superset, Discourse, Mastodon, Sentry), chosen
specifically because none of them have raw `.sql` migrations at all —
Alembic, Rails, and Django source only — to stress the ORM-native
migration parsing (`aletheore/orm_migrations.py`) the same way Part 1
stressed the raw-SQL path, and to see what Repowise does with a migration
convention that isn't SQL text.

##### Part 1: real-repo stress test (Aletheore's own parser)

| Repo | Files scanned | Convention | Crashes | Real bugs found |
|---|---|---|---|---|
| cal.com | 595 | Prisma | 0 | 2 |
| supabase | 32 | Supabase CLI | 0 | 0 |
| coder | 589 (`.up.sql`) | golang-migrate | 0 | 1 |
| windmill | 636 (`.up.sql`) | Rust/sqlx | 0 | 0 (confirms round-1 fixes) |
| trigger.dev | 825 | Prisma (independent schema) | 0 | 0 (confirms round-1 fixes) |
| **Total** | **2,677** | | **0** | **3** |

###### Bugs found and fixed

1. **Named table-level constraints not modeled** (found on cal.com). sqlglot
   wraps a *named* `CONSTRAINT x PRIMARY KEY (...)` / `UNIQUE (...)` /
   `FOREIGN KEY (...) REFERENCES ...` in a `Constraint` node; only the bare
   (unnamed) forms were handled. Prisma always names its constraints, so
   every one of cal.com's 102 tables' primary keys came back completely
   unmarked. Fixed by routing both the bare and named-wrapper cases through
   one shared helper.
2. **`ALTER INDEX ... RENAME TO ...` unhandled** (found on cal.com). It's a
   distinct statement kind (`Alter` with `kind=INDEX`), not an `ALTER TABLE`
   action — fell straight to the generic unsupported bucket.
3. **`RENAME col TO new_col` (Postgres' valid COLUMN-keyword-optional
   shorthand) silently renamed the whole table** (found on coder). sqlglot
   parses it to the identical AST node as a real `RENAME TO new_table` —
   the real new column name only appears in a separate, easy-to-miss
   `ToTableProperty` on the statement's own `options`. Confirmed by
   bisecting a real "table vanishes mid-migration-sequence" symptom down to
   one migration; 7 real occurrences in that one repo alone, all fixed by
   the same one check.

Every fix carries a regression test built from the real statement that
triggered it, not a synthetic minimal case. Full detail and code citations
are in the three commits on `Aletheore/Aletheore`'s
`feat/sqlglot-schema-parser` branch.

###### What's left in `unsupported`, and why it's not a bug

Across all 2,677 files, every remaining `unsupported` entry falls into a
deliberate, documented scope boundary — schema extraction models table
*shape* (columns/relations/indexes), not the full Postgres surface:

- `CREATE`/`DROP TRIGGER`, `FUNCTION`, `PROCEDURE`, `POLICY`, `VIEW`,
  `TYPE` (enums), `SCHEMA`, `SEQUENCE`
- `GRANT`/`REVOKE`, `ALTER DEFAULT PRIVILEGES`
- `ALTER TABLE ... ENABLE/DISABLE ROW LEVEL SECURITY`, `... OWNER TO`,
  `... REPLICA IDENTITY`, `... VALIDATE CONSTRAINT`
- `CHECK`/`EXCLUDE` constraints (recorded with the real reconstructed SQL
  text, not modeled into the schema)
- `ALTER TABLE ... DROP CONSTRAINT <name>` (a deliberate choice — constraint
  names aren't tracked precisely enough on relations to resolve which one
  to remove)
- Raw DML (`INSERT`/`UPDATE`/`DELETE`), `BEGIN`/`COMMIT`, `DO` blocks

One genuine, disclosed limitation in the underlying library (not this
module): a single `ALTER TABLE` statement with multiple comma-joined
`ALTER COLUMN` clauses (`ALTER TABLE x ALTER COLUMN a ..., ALTER COLUMN
b ...;`) falls back to an opaque `Command` node in the pinned sqlglot
version. 3 occurrences total across all 2,677 files — rare, and already
degrades honestly to one `unsupported` entry with the real text rather
than losing data silently.

##### Part 1b: real-repo stress test, ORM-native migrations (Aletheore's own parser)

Same methodology as Part 1, but these four repos have zero raw `.sql`
migration files — Alembic (`.py`), Rails (`.rb`), and Django (`.py`)
source only, exercising `orm_migrations.py` instead of the SQL tokenizer.

| Repo | Migration files (real, content-verified) | Convention | Crashes | Real bugs found |
|---|---|---|---|---|
| Apache Superset | 383 | Alembic | 0 | 1 |
| Discourse | 1,746 | Rails | 0 | 2 |
| Mastodon | 535 | Rails | 0 | 0 (confirms round-6 Rails fixes generalize) |
| Sentry | 37 | Django | 0 | 2 |
| **Total** | **2,701** | | **0** | **5** |

Final extracted schema, current code:

| Repo | Tables | Relations | Indexes | Unsupported entries |
|---|---|---|---|---|
| Apache Superset | 12 | 29 | 23 | 115 |
| Discourse | 211 | 59 | 257 | 758 |
| Mastodon | 118 | 67 | 158 | 42 |
| Sentry | 229 | 235 | 76 | 113 |

Five real bugs found and fixed, none a false positive on re-verification:

1. **Alembic's `alembic/versions` directory hardcoded too narrow** (Superset).
   Superset renames the top-level directory to `superset/migrations` but
   keeps a subdirectory literally named `versions`, per Alembic's own
   convention — real and common enough that many large real projects do
   this. Generalized the match to any `versions`-named directory,
   content-verified via a `down_revision` substring check to avoid a false
   positive on an unrelated directory of the same name.
2. **Crash: `CREATE INDEX` built from a truncated dynamic string** (Discourse).
   A real Rails migration builds its index SQL via string interpolation
   (`execute "CREATE INDEX #{...} name ON table (col)"`); the static
   extractor only captured the literal prefix `"CREATE INDEX "`. sqlglot
   parsed the keywords but left the Index node `None`, which crashed the
   index-event builder instead of degrading to `unsupported` like every
   other unparseable statement.
3. **Crash: `add_index` with a constant-referenced name** (Discourse).
   `add_index :table, :col, name: INDEX_NAME` (a Ruby constant, not a
   string/symbol literal) couldn't be resolved, and the fallback to
   Rails' auto-generated index name only applied when `name:` was absent
   entirely — not when present but unresolvable — so the index event's
   name stayed `None` and crashed the final sort.
4. **Custom FK field subclass not recognized** (Sentry). Sentry's own
   `FlexibleForeignKey` (249 real usages in one squashed migration file
   alone) is a verified, real `django.db.models.ForeignKey` subclass —
   confirmed by reading its source — but the field-type check only
   matched the literal names `ForeignKey`/`OneToOneField`, so every one
   of these was silently modeled as a plain column with no relation.
   Deliberately did *not* extend this to Sentry's similarly-named
   `HybridCloudForeignKey`: its own docstring states it is "just a dumb
   BigIntegerField" with no real integrity constraint — modeling it as a
   relation would have fabricated a constraint that doesn't exist in the
   real schema.
5. **Unresolvable FK target silently emitted a broken relation** (Sentry).
   `to=settings.AUTH_USER_MODEL` (a real, common Django idiom, not a
   string literal) can't be resolved without loading Django settings — 28
   real occurrences. This used to still emit a `relation` with
   `to_table: None` instead of recording the gap; now routes to
   `unsupported` with the real field and target text.

Fixing #4 alone took Sentry's extracted relations from 8 (one of which had
a `None` target) to 235.

###### What's left in `unsupported`, and why

Discourse's 758 and Sentry's 113 look large in isolation but are
overwhelmingly legitimate, already-understood scope boundaries: real DML
data migrations (`UPDATE`/`DELETE`/`INSERT`/`SELECT`, not schema DDL),
`DROP VIEW`/`ALTER SEQUENCE`, and — the one genuine, non-fixable
limitation, previously found on Superset and confirmed again here on
Discourse — `ADD COLUMN` on a table whose true genesis predates the
migration history itself (created directly from ORM model classes before
the project adopted Alembic/ActiveRecord migrations for schema changes,
never captured in any migration file). No signal exists to recover this
from the migration history alone. 79 of Sentry's 113 come from a single
outlier: one squashed migration file replaying years of legacy
`AlterUniqueTogether` calls (an already-deliberately-unmodeled legacy
Django <2.2 API) — checked the distribution before treating it as a
finding, and it does not generalize to normal migration files (6 more
files each have exactly one).

##### Part 2a: Aletheore vs. Repowise, raw `.sql` migrations

`repowise init --index-only -y` (no LLM cost) was run against the full
checkout of each repo, then `.repowise/wiki.db`'s `wiki_symbols` table was
queried directly.

| Repo | Real `.sql` files in repo | Files Repowise extracted ≥1 symbol from | Repowise SQL symbols | Distinct table names (Repowise) |
|---|---|---|---|---|
| cal.com | 601 | 103 (17%) | 135 | 127 |
| trigger.dev | 873 | 149 (17%) | 222 | 203 |
| windmill | 1,336 | 128 (10%) | 164 | 155 |
| coder | 1,355 | 197 (15%) | 389 | 139 |
| supabase | 104 | 45 (43%) | 94 | 66 |

Every single SQL symbol Repowise stored, across all five repos, is kind
`class` (plus a handful of `function`, likely from inline PL/pgSQL bodies)
with a signature that is just `TABLE Name(col1, col2, ...)` — a flat column
*name* list, no types, no constraints. Grepped every stored signature
across all five repos for `REFERENCES`, `FOREIGN KEY`, and `PRIMARY KEY`:
**zero real hits** in any of them (a few string matches were columns
literally named `bookingId`/`referenceId`, not real FK clauses).

###### Column-count comparison on real, verifiable tables

| Repo | Table | Repowise columns | Aletheore columns | Gap |
|---|---|---|---|---|
| cal.com | `EventType` | 8 (the 2021 `CREATE TABLE` only) | 86 | 78 columns of real schema history missed |
| trigger.dev | `TaskRun` | 14 (the 2024 `CREATE TABLE` only) | 84 | 70 columns missed |
| coder | `template_versions` | 8 *(a second, separate symbol from `coderd/database/dump.sql` — a file coder happens to maintain by hand — shows 15, which matches)* | 15 | Matches only because coder maintains a redundant hand-curated snapshot file; without it, Repowise's number is 8 |
| windmill | `queue` | 22, reported as still current | Renamed to `v2_job_queue` (46 cols); `queue` is now a **view**, not a table | Repowise doesn't know the table was renamed at all |

The `template_versions`/coder row is the fairest possible case for
Repowise — the repo happens to ship a hand-maintained `pg_dump`-style
snapshot file, and Repowise's number only matches because it also parsed
that file as if it were just another migration. Aletheore's 15 was derived
purely by replaying the real migration history — no snapshot file needed —
and independently matches coder's own maintained ground truth.

###### Other capabilities Repowise's SQL handling has none of

- **Foreign keys / relations**: 0 across 2,677 files (Aletheore: 738 across
  the same five repos — cal.com 226, trigger.dev 204, coder 174, windmill
  121, supabase 13 — with `ON DELETE` actions preserved)
- **Indexes**: not a tracked symbol kind at all (Aletheore: 934 across the
  five repos — cal.com 297, trigger.dev 267, coder 157, windmill 205,
  supabase 8 — correctly tracking renames)
- **DROP TABLE**: never processed. cal.com creates `platform_access_tokens`
  in `20240319144740_platform/migration.sql`, then drops it 10 days later
  in `20240329084749_platform_snake_case_to_pascal_case/migration.sql`.
  Repowise still lists it as a symbol; Aletheore correctly excludes it.
- **Table renames**: never processed, as the `queue`/`v2_job_queue` case
  shows directly

##### Part 2b: Aletheore vs. Repowise, ORM-native migrations

Same `repowise init --index-only -y` + direct `wiki_symbols` query
methodology, run against the four Part 1b repos. These repos have zero
raw `.sql` migration files, so this is a different question from Part 2a:
not "how much schema detail does Repowise's SQL parsing lose," but
"does Repowise understand ORM migration files as schema-defining code at
all."

First, the full, repo-wide symbol-kind vocabulary Repowise stored for
each repo — not just within migration directories:

| Repo | Every distinct `kind` Repowise stored, anywhere in the repo |
|---|---|
| Apache Superset | class, method, function, variable, constant, interface, type_alias, enum |
| Discourse | class, method, function, variable, constant, module, interface, type_alias |
| Mastodon | class, method, function, variable, constant, module, interface, type_alias, enum |
| Sentry | class, method, function, variable, constant, interface, type_alias, enum |

No `table`, `model`, `migration`, `column`, `relation`, or `index` kind
exists anywhere — Repowise's symbol vocabulary is generic
programming-language constructs, full stop. This holds regardless of
migration convention (Alembic/Rails/Django) because none of it is
SQL-parsing-related at all; it's the same general-purpose class/method/
function extraction Repowise applies to any other Python or Ruby file in
the repo.

Concretely, on Sentry's `0001_squashed_1118_add_group_derived_data.py` —
a single real (squashed-history) migration file that Aletheore replays
into 217 real tables with 211 real relations (the large majority of the
repo's 229 tables / 235 relations overall) — **Repowise's entire stored
index for that file is one symbol**: `class Migration`. Every
`CreateModel(...)` call inside it — each one a real table, with a real
field list, real types, real FK targets — is an anonymous call expression
inside a Python list literal, not a named class or function, so it
produces no symbol at all under generic AST-based indexing.

| Repo | Migration files Repowise touched | Symbols extracted (all generic: class/method/function/variable/constant) | Schema-relevant symbols (table/column/relation/index) |
|---|---|---|---|
| Apache Superset | 383 | 2,190 | **0** |
| Discourse | 2,443 | 6,315 | **0** |
| Mastodon | 535 | 1,321 | **0** |
| Sentry | 54 | 103 | **0** |

(Discourse's 2,443 vs. Aletheore's own 1,746 root-`db/migrate` sources
reflects scope, not a discrepancy in either tool's correctness — Repowise
indexes the whole checkout including plugin-local `db/migrate`
directories elsewhere in the tree; this benchmark's Part 1b numbers are
scoped to the root migration directory only, matching `detect_database`'s
default.)

##### Bottom line

**Raw `.sql` migrations (Part 2a):** Repowise's SQL "support" is real in
the sense that it doesn't crash and extracts *something* — but it's a
single-statement, single-file `CREATE TABLE` name/column-list dump with
no cross-migration replay, no type information, no constraints, and no
relations, indexes, renames, or drops. On every repo tested it reported
stale, sometimes years-out-of-date schemas as current, with no signal
that anything was missing.

**ORM-native migrations (Part 2b):** Repowise has no schema-extraction
concept here at all — it indexes Django/Rails/Alembic migration files
exactly like any other source file (class and method names only), never
recovering a single table, column, type, or relation from any of the four
repos tested, 2,701 real migration files between them.

Aletheore replays the full migration history — SQL or ORM-native — to
reconstruct the actual current schema, verified directly against a real
project's own maintained ground truth where one exists (coder's
`dump.sql`) and against real field/type declarations read straight from
source otherwise (Sentry's `FlexibleForeignKey`), with types, primary
keys, foreign keys (`ON DELETE` included), indexes, and renames all
correctly tracked across nine real repos and four different migration
conventions (raw SQL, Alembic, Rails, Django).

</details>

## Head-to-head against Graphify (ERPNext)

[Graphify](https://github.com/Graphify-Labs/graphify) is a tree-sitter-based
code-knowledge-graph tool with its own primary-source benchmark on
[frappe/erpnext](https://github.com/frappe/erpnext) (~1M LOC). Rather than
cite either tool's own published numbers, we ran **both tools ourselves**
under one shared agent loop and one anonymized judge, on the same pinned
ERPNext commit — 15 independently-authored questions, each run three times
(baseline grep/read/list, +Aletheore, +Graphify), scored by a judge never
told which tool produced which answer:

| condition | coverage (mean, 30 samples) | tokens/query (mean, 15 samples) |
|---|---|---|
| baseline (grep + read + list only) | 92.2% | 11,839 |
| **+ Aletheore** | **100.0%** | 14,893 |
| + Graphify | 93.3% | 17,921 |

**Aletheore ties or leads Graphify on every question** once a ground-truth
error found in pre-publication review was corrected. The honest caveat: only
2 of 15 questions actually discriminate between conditions, so this is a real
result on this question set, not a claim that generalizes past 15 questions
on one corpus. The more robust win is cost — excluding the one question both
comparison tools timed out on, Aletheore answers for **36% fewer tokens than
Graphify** (9,803 vs. 15,296 mean), not as an artifact of one question.

Full methodology, the two corrections made before publishing, the setup-time
comparison, and total real cost ($0.19) in
[`graphify_comparison/README.md`](graphify_comparison/README.md).

<details>
<summary><strong>Full write-up: Graphify (ERPNext) comparison</strong></summary>


*Paths below (`scripts/`, `questions.json`, `results/`) are relative to `graphify_comparison/`.*

#### Head-to-head against Graphify (ERPNext code intelligence)

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

##### Results

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

##### Where we lose

Nowhere on coverage in the final, corrected numbers — Aletheore ties or
leads Graphify on every question once q07's ground truth is fixed. The
honest caveat is scope: only 2 of 15 questions actually discriminate
between conditions, so "we tie or win" is a real result on this question
set, not a claim that generalizes further than 15 questions on one corpus
supports. On tokens, Aletheore costs more than the grep/read/list baseline
(as expected — a real tool adds real tokens) but meaningfully less than
Graphify.

##### Setup time: closed the scan gap, indexing is now the real one

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

##### Total real cost

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

##### Methodology

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

##### Reproducing

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

</details>

## Where we lose

Stated here rather than in a footnote:

- ⚠️ **Five of eight corpora score below 35% top-1 under vocabulary-avoiding
  phrasing** — though every one of them recovers 20-47 points when the same
  questions are asked in the project's own terms, so most of that gap is our
  question authoring rather than the product.
- ⚠️ **jekyll top-5 loses to RepoWise**, 46.7% against 66.7%.
- ⚠️ **AIRview writes a page for only 21 of 100 changed files** on Flask's last 30
  commits. The other 79 are served by a deterministic fallback, not by the
  generated wiki this project is named for.
- ⚠️ **RepoWise's `get_context` beats our fallback on `tests/test_blueprints.py`**,
  3.0 against 2.0.
- ⚠️ **An earlier revision of this README published flask figures that did not
  reproduce.** They are corrected above, and how it happened is in
  METHODOLOGY.md.

We win on locating code, and on setup cost ($0.00 / 74 s against $0.18 / ~7 min).

## Reproducing

**Aletheore v0.8.11.** Every retrieval result above was produced by that release,
installed from PyPI exactly as written below.

The retrieval table describes local `nomic-embed-text` embeddings, not hosted
OpenAI embeddings. The embedder alone moved Gin by 20 points in the comparison
run, so this detail is part of the result definition.

The older 0.8.0 through 0.8.4 tags were never published: their `pyproject.toml`
was frozen at `0.7.2` while the code advanced, so no artefact could be uploaded.
The published benchmark run uses 0.8.11 exactly.

```bash
pip install "aletheore==0.8.11"

git clone https://github.com/pallets/flask /tmp/bench-flask
git -C /tmp/bench-flask checkout 2a8a38b051fc248865730bf3511bf2e2ea325e81

python3 scripts/verify_ground_truth.py          # must print 32/32
cd /tmp/bench-flask && aletheore scan . && aletheore index .
cd - && python3 scripts/run_aletheore.py
python3 scripts/score.py results/results_aletheore.json=ALETHEORE
```

The fallback sections re-derive from saved rows without a key or a network:

```bash
python3 scripts/score_fallback_judge.py
```

`corpora.json` pins every corpus commit. Runners refuse to score against a
different checkout, because the ground truth was verified against those exact
trees. See **REPRODUCIBILITY.md** for tool versions and for what reproduces
exactly versus what does not.

The RepoWise half needs an LLM key and, importantly, `REPOWISE_EMBEDDER=ollama`
— without it `repowise search --mode semantic` silently degrades to full-text.
That defect invalidated our own first run.

**The hosted-embeddings comparison is the one section above that does not
reproduce this way.** Generating fresh rows needs `aletheore login` against a
paid plan and a dev checkout at the commit cited in that section, not a
`pip install`:

```bash
python3 scripts/run_retrieval_matrix.py --label jina_hosted   # needs credentials
python3 scripts/score_retrieval_matrix.py results/retrieval_raw_jina_hosted.json   # does not
```

The second line alone re-derives the published table from the rows already
saved in `results/` - no credentials, no network, the same guarantee as
everything else in this repository. Only generating new rows needs the
paid plan.

<details>
<summary><strong>Full write-up: reproducibility - what reproduces exactly, what does not, and why</strong></summary>


### Reproducibility — what is and is not guaranteed

Read this before citing any number here as settled.

#### Versions the published results were produced with

| | version |
|---|---|
| Aletheore | **0.8.11** |
| RepoWise | 0.27.0 |
| Ollama | 0.32.6 |
| Embedding model (both tools) | `nomic-embed-text` (768-dim) |
| Wiki generation + judge model | `deepseek-chat` via api.deepseek.com, 2026-08-12 |
| RepoWise wiki generation model | `deepseek-v4-flash` |
| Python / LanceDB | 3.12.10 / 0.34.0 |
| Corpus | Flask @ `2a8a38b051fc248865730bf3511bf2e2ea325e81` |

Runners call `_bench.check_corpus_commit()` and refuse to score against a
different checkout, because the ground truth was verified against that one.

#### What reproduces exactly

**Retrieval (the location benchmark).** Deterministic given the same corpus,
same Aletheore version and the same local `nomic-embed-text` embedding model.
These published numbers describe local `nomic-embed-text`, not hosted OpenAI
embeddings; the embedder alone moved Gin by 20 points in the comparison run.
Same index, same
ranking, same top-k. Re-running changes only latency.

**Ground-truth verification.** `scripts/verify_ground_truth.py` is pure file
inspection: 32/32 or it fails loudly.

**Scoring.** `score.py` / `score2.py` are arithmetic over committed raw results.
Anyone can recompute every published number from `results/*.json` without an API
key, an LLM, or a network.

#### What does NOT reproduce exactly

**Anything involving an LLM.** Wiki generation and the architecture judge are
sampled. Judging runs at `temperature: 0` and each question is graded twice with
the systems' positions swapped, which controls position bias — it does not make
the result deterministic.

**We have not measured judge variance.** The architecture scores are single
runs. A repeat run would land near, not on, 2.17 and 2.42, and we do not
currently know the spread. Treat gaps smaller than ~0.2 as inside the noise: on
that basis "RepoWise is ahead on comprehension" is supported, and any precise
gap figure is not.

**Model drift.** `deepseek-chat` is a moving target. The same script in six
months calls a different model. Nothing here pins a model snapshot, so a later
run measures a different system.

**The Aletheore version materially affects every retrieval number.** 0.8.0 is
where import resolution was repaired for JavaScript, Rust and C#, where
module-level constants started being extracted in all 11 languages, and where
each symbol chunk began carrying its file's header comment. Running these
questions against 0.7.x measures a different scanner and will not reproduce
these figures — Rust in particular scanned with **zero** import edges before
0.8.0, so its dependency graph, clustering and ranking were all degenerate.

#### Known scope limits

- One repository, one language, 44 questions.
- **Questions were authored by us.** Mitigated by sourcing from Flask's public
  API/docs and mechanically verifying every anchor, but it is the weakest link
  in the methodology and an independently-authored set would be stronger.
- The architecture arm depends on an LLM judge grading LLM-written prose.
- The independent-judge cross-check (`llama3.1:8b`) covers only the
  raw-code-chunks arm, and tied 16 of 24 pairings — directional, not precise.

#### Running it

```bash
git clone https://github.com/pallets/flask /tmp/bench-flask
git -C /tmp/bench-flask checkout 2a8a38b051fc248865730bf3511bf2e2ea325e81

python3 scripts/verify_ground_truth.py          # must print 32/32
cd /tmp/bench-flask && aletheore scan . && aletheore index .
cd -  &&  python3 scripts/run_aletheore.py
python3 scripts/score.py results/results_aletheore.json=ALETHEORE
```

Paths are environment variables, not hard-coded: `BENCH_FLASK`, `BENCH_FLASK_RW`,
`BENCH_OUT`, `BENCH_ENV_FILE`, `GITHUB_APP_PATH`.

The RepoWise half needs an LLM key in `$BENCH_ENV_FILE` and — importantly —
`REPOWISE_EMBEDDER=ollama`. Without it, `repowise search --mode semantic`
silently degrades to full-text and you will benchmark the wrong thing. See
METHODOLOGY.md; that defect invalidated our own first run.

**Speed (in-process figures):** `python3 scripts/run_aletheore.py` and
`python3 scripts/run_repowise_inprocess.py` (the latter needs RepoWise's own
Python — the interpreter its console-script shebang points at, not
whichever `python3` is first on `$PATH`) reproduce the "in-process" row of
METHODOLOGY.md's Speed table. Both pin `allow_hosted=False`/force the local
Ollama embedder explicitly, so the result is deterministic regardless of
whether the machine running them happens to have a saved hosted credential
— see METHODOLOGY.md's Speed section for why that pin exists and what it
was silently masking before it did.

</details>
<details>
<summary><strong>Full write-up: the 11-language corpus plan - repo selection, per-corpus procedure, cost, and what was rejected</strong></summary>


### Corpus plan — 11-language head-to-head

One well-known repository per supported language, sized so a full RepoWise wiki
build stays affordable. Status tracks how far each corpus has progressed.

| language | repository | size | stars | questions | status |
|---|---|---|---|---|---|
| Python | pallets/flask | 13 MB | 70k | 32 + 12 | **done** |
| Go | gin-gonic/gin | 12 MB | 82k | 15 | **search done** (0.8.5), wiki pending |
| Rust | serde-rs/serde | 12 MB | 9k | 15 | **search done** (0.8.5), wiki pending |
| JavaScript | expressjs/express | 8 MB | 66k | — | scanned, questions pending |
| TypeScript | colinhacks/zod | 23 MB | 43k | 15 | **search done** (0.8.5), wiki pending |
| Java | google/gson | 22 MB | 24k | 15 | **search done** (0.8.5), wiki pending |
| Ruby | jekyll/jekyll | 10 MB | 50k | 15 | **search done** (0.8.5), wiki pending |
| PHP | slimphp/Slim | 7 MB | 12k | 15 | **search done** (0.8.5), wiki pending |
| C | jqlang/jq | 7 MB | 35k | — | not started |
| C++ | fmtlib/fmt | 17 MB | 23k | — | not started |
| C# | AutoMapper/AutoMapper | 124 MB | 10k | — | not started |

Rejected, with reasons, so nobody re-proposes them:

- **nestjs/nest** (TypeScript, 475 MB) — clone and scan cost out of proportion
  to what it adds over zod.
- **nlohmann/json** (C++, 268 MB) — effectively one enormous header. A
  single-file library cannot exercise cross-file retrieval, which is the thing
  under test.
- **curl/curl** (C, 141 MB) — jq gives the same language coverage at a
  twentieth of the size.
- **sinatra/sinatra** (Ruby, 7 MB) — proposed and then rejected on inspection,
  for the same reason as nlohmann/json. Its library is seven files, and
  `lib/sinatra/base.rb` is 2,173 lines holding Request, Response, Base,
  Application and Wrapper. Almost every location question would answer
  "base.rb", which tests nothing about cross-file retrieval. Replaced by
  **jekyll/jekyll**, whose 89 library files across `lib/jekyll/` exercise it
  properly.
- **PyO3/pyo3** and **tauri-apps/tauri** — proposed as mixed-language corpora and
  rejected on measurement, not reputation. Scanned: PyO3 is **90% Rust**, 10%
  Python (mostly test and example scaffolding); Tauri is **82% Rust**, 10%
  JavaScript, 7% TypeScript. Both are single-language repositories with a
  minority second language, so either would have produced a Rust result wearing
  a polyglot label. **apache/thrift** replaces them: 948 modules after test and
  auxiliary exclusion, spread across cpp 33%, java 21%, csharp 11%, php 6%,
  go 6%, ruby 5%, python 5%, c 5% — no language above a third.
- **MultiPL-E** — proposed as a "multi-language gold standard" and rejected on
  inspection: it is HumanEval/MBPP translated into ~18 languages, so every
  problem is a single self-contained function. No repositories, no cross-file
  structure, nothing to index or retrieve. It measures whether a model can
  write a function body, which is a different product category.

#### Per-corpus procedure

1. Clone at a pinned commit, record it in `corpora.json`.
2. `aletheore scan` + `aletheore index` (free — local embeddings).
3. Author ~15 location questions from the project's public API and docs.
   Phrase them as a developer would ask, avoiding verbatim symbol names, which
   would flatter lexical search rather than test retrieval.
4. `scripts/verify_ground_truth.py` — must pass 15/15 before anything runs.
   A question whose anchor cannot be found is a broken question, not a miss.
5. Run Aletheore retrieval, record top-1/3/5 and MRR.
6. RepoWise: `init --coverage 1.0`, then `reindex --embedder ollama`, then the
   same questions. **`REPOWISE_EMBEDDER=ollama` is mandatory** or its semantic
   mode silently degrades to full-text.
7. Wiki arm: build AIRview, capture equal-budget context from both, judge blind
   with positions swapped.

#### Cost

Aletheore's side is free — local `nomic-embed-text`, no LLM. The spend is
RepoWise's wiki generation, which scales with file count rather than repo size:

| measured | pages | cost |
|---|---|---|
| flask | 110 | $0.175 |
| gin | 127 | $0.197 |
| requests | 58 | $0.106 |
| httpx | 85 | $0.148 |
| attrs | 87 | $0.150 |

Budget roughly **$0.15–0.20 per corpus** for RepoWise, plus about $0.03 for
AIRview and $0.05 per judged arm. Eleven languages lands near **$3–4** total.

#### Known measurement hazards

- **Judge scores are not independent.** Both systems are graded in one prompt,
  so an absolute score moves with what it is paired against. Only the
  within-run gap is comparable across configurations.
- **We author the questions.** Every anchor is verified mechanically, but this
  is still the weakest link, and it is the reason per-language sets should be
  written before any result is looked at, never after.
- **Aletheore version matters.** Pin 0.8.5 or later. Earlier releases resolved
  no imports at all for JavaScript, Rust and C#, and 0.8.0 through 0.8.4 cannot
  be installed from PyPI at all - their `pyproject.toml` was frozen at 0.7.2,
  so no artefact was ever published under those numbers.

</details>
<details>
<summary><strong>Full write-up: scanner language coverage across all 13 supported languages, plus a RepoWise dead-code comparison for Kotlin and Swift</strong></summary>


### Scanner language coverage

Every language the scanner claims to support, verified with controlled two-file
fixtures (each defining a function, a class, a module-level constant, and
importing across files) plus eight real repositories. Deterministic — no LLM.

Reproduce: `python3 scripts/lang_coverage_matrix.py`

#### Current state — all 13 languages

Re-run in full for this update (2026-08-30), not hand-edited from the 11-language
table below it - every row reflects the real script output as of Kotlin and
Swift landing.

| language | imports | functions | classes | constants |
|---|---|---|---|---|
| python | ✅ | ✅ | ✅ | ✅ |
| javascript (ESM) | ✅ | ✅ | ✅ | ✅ |
| javascript (CommonJS) | ✅ | ✅ | ✅ | ✅ |
| typescript | ✅ | ✅ | ✅ | ✅ |
| go | ✅ | ✅ | ✅ | ✅ |
| rust | ✅ | ✅ | ✅ | ✅ |
| java | ✅ | ✅ | ✅ | ✅ |
| ruby | ✅ | ✅ | ✅ | ✅ |
| php | ✅ | ✅ | ✅ | ✅ |
| c | ✅ | ✅ | n/a | ✅ |
| cpp | ✅ | ✅ | ✅ | ✅ |
| csharp | ⚠️ see note | ✅ | ✅ | ✅ |
| kotlin | ✅ | ✅ | ✅ | ✅ |
| swift | ✅ | ✅ | ✅ | ✅ |

**csharp note, found while re-running this for Kotlin/Swift, not caused by
either:** this table's own shared fixture convention names the imported
type `Mod` (3 characters) in every language - `_CSHARP_MIN_TYPE_NAME = 4` in
`graph.py`'s same-namespace type-reference fallback (the mechanism that
resolves C#'s `using`-free same-namespace references, see the "C#: flat
projects resolved nothing" section below) filters it out as noise before it
can ever produce an edge. Real, reproducible, and pre-existing - unrelated to
this session's Kotlin/Swift work, which touched no C# code. Not fixed here:
either the fixture's `Mod` needs a longer name, or the threshold needs a real
look, and conflating that with an unrelated language-support PR isn't the
right place to decide which.

Before this work three languages resolved **no imports at all** and ten
recorded **no constants**. Everything downstream — clustering, subsystem
naming, importance ranking, AIRview, layer violations — consumes the import
graph, so those languages produced output that was structurally wrong while
looking normal.

#### RepoWise comparison: dead-code detection

Both tools ship dead-code/unreachable-file detection. Measured head-to-head on
real repos, file-level findings only (RepoWise also flags unused-export
symbols; Aletheore's dead-code module doesn't attempt that granularity, so
symbol-level findings are excluded from both sides for a fair comparison).

**Swift: a clear, verified win.**

| repo | files | RepoWise false positives | Aletheore false positives |
|---|---|---|---|
| vapor/penny-bot | 168 | 60 (36%) | 0 |
| vapor/api-template | 10 | 6 (60%) | 0 |
| apple/swift-algorithms | - | 0 | 0 |

RepoWise's Swift support doesn't understand whole-module imports - a Swift
`import Foo` names a compiled target, not a file, so files within a target
that only ever get referenced from *outside* Swift's import syntax (a Lambda
handler invoked by the AWS runtime, `main.swift`'s classic top-level-code
entry point) look completely unreachable to it.

Getting Aletheore to 0 took two real fixes, both found by re-running this
comparison rather than trusting an earlier pass:

- Swift files within *one target* see each other with no import statement at
  all (unlike every other language this scanner supports) - the per-file
  import graph could never show those edges, so a target's own entry point
  and every sibling file it referenced looked equally unreachable. Fixed by
  treating a target as one reachability unit: if any file in it is reachable,
  every file in it is.
- `Package.swift` can be genuinely executable Swift - a factory function
  building several targets from one call site with `name:`/`path:` built via
  string interpolation. The manifest parser was silently extracting a
  truncated literal fragment from an interpolated string instead of
  recognizing it wasn't a plain literal - on penny-bot this merged eight
  distinct Lambda targets into one fictitious target spanning their shared
  parent directory. Now skipped entirely when interpolation is present.

(`Aletheore#484`, `Aletheore#486`)

**Kotlin: an exact match.** On android/architecture-samples (268 files),
RepoWise flags 7 files unreachable - all build-config files, no real `.kt`
file on either side. Aletheore now flags the same 7, down from an initial 31
across five real fixes:

| finding | before | after | fix |
|---|---|---|---|
| `androidTest`/`test` files (zero JVM test-file patterns at all) | 31 | 24 | `Aletheore#484` |
| AndroidManifest.xml entry points + Hilt/Dagger DI annotations | 24 | 15 | `Aletheore#484` (2nd commit) |
| top-level Kotlin function imports (`fun LoadingContent(...)`, not just class/interface/object) | 15 | 12 | `Aletheore#487` |
| top-level Kotlin val/var imports | 12 | 11 | `Aletheore#490` |
| Kotlin same-package implicit visibility (files in one package see each other's declarations with no import at all, same as Java) | 11 | 7 | `Aletheore#489` |

The last fix closed what had briefly been documented here as a genuinely
open gap (`ModelMappingExt.kt`, `StatisticsUtils.kt`, both real cases of
same-package implicit visibility - e.g. `DefaultTaskRepository.kt` calling
`ModelMappingExt.kt`'s `toExternal()` with zero import between them). It also
picked up 6 files beyond the 2 that motivated it (package-mates of files
independently reachable some other way), landing on file-list parity with
RepoWise, not just a matching count.

#### What was broken, measured on real repositories

##### CommonJS: empty dependency graph

`_extract_javascript` handled only ESM `import_statement`, never `require()`.

| expressjs/express | before | after |
|---|---|---|
| modules with resolved imports | **0 / 141** | 125 / 141 |
| import edges | **0** | 159 |
| clusters | 141 | 27 |
| singleton clusters | **141 / 141** | 4 / 27 |

A full AIRview build would have made 141 LLM calls to describe 141 one-file
"subsystems".

##### JavaScript: assigned function expressions were not symbols

Only `function f(){}` and `class C{}` counted, but Express defines its entire
surface as `app.use = function use(fn) {...}`.

| expressjs/express | before | after |
|---|---|---|
| files with zero symbols | 102 / 141 | 86 / 141 |
| functions extracted | ~0 in lib/ | 231 |

Now covers `const f = () => {}`, `exports.f = function(){}` and
`Foo.prototype.bar = function(){}`.

##### Rust: two silent failures

`serde-rs/serde` scanned as **208 modules, 0 import edges, 208 singleton clusters.**

1. `_rust_crate_root` only checked `<repo>/src/lib.rs`, so **Cargo workspaces** —
   serde, tokio, rust-analyzer, most large Rust projects — resolved nothing.
2. `mod foo;` was not treated as an edge, though it is how a crate declares its
   module tree. A crate whose `lib.rs` is all `mod` statements had no edges.

After: **25 of 33 crate-source files resolve imports.** The remaining 151 files
are integration tests that `use serde::` across a crate boundary, where zero is
correct.

##### C#: flat projects resolved nothing

`_csharp_prefix_and_root_for` required at least one trailing namespace segment
to match a real directory, so a project whose namespace comes entirely from
`<RootNamespace>` with no mirroring folders contributed nothing to the prefix
map. Now falls back to treating the whole namespace as an implicit prefix rooted
at the file's own directory.

##### Module-level constants: Python only

A file can export a substantial public API without a single function or class —
Flask's `signals.py` is ten assignments exporting ten public signals, and was
invisible to every consumer of the evidence. The same shape is everywhere:
`export const`, Go `const` blocks, `pub const`, `public static final`,
`#define`, C# `const`. Now extracted in all 11.

| repo | modules with zero symbols, before → after |
|---|---|
| axios | 131 → 76 |
| gin (go) | 2 → 1 |
| express | 102 → 86 |

#### Not a defect

- **C reports no classes.** C has none.
- **PHP requires a PSR-4-compliant layout** (one class per file, named after the
  class). An earlier draft of this register listed PHP as broken; that was a
  non-compliant fixture, not a scanner bug — corrected after verification.
- **Header declarations are not definitions**, so header-only C/C++ libraries
  under-report functions.

#### Still open

- Clusters that are entirely tests or docs still get a subsystem and an LLM call
  (7 of 12 on Flask, 150 of 208 on serde).
- Singleton clusters remain common in repos whose test files import nothing.
- Retrieval and wiki quality have been **measured only on Flask**. The scores in
  METHODOLOGY.md are a property of that one Python repo, not of the product, and
  must not be quoted as cross-language numbers.

</details>
<details>
<summary><strong>Full write-up: retrieval benchmark methodology - every fairness adjustment made in RepoWise's favour, the phrasing-confound investigation, the near-duplicate-crowding falsification, the 0.8.13 reproducibility check, and errors caught in our own runs</strong></summary>


### Retrieval benchmark — Aletheore indexed search vs RepoWise semantic search

**Corpus:** Flask @ `2a8a38b051fc248865730bf3511bf2e2ea325e81` (83 Python files)
**Questions:** 32, natural-language, authored from Flask's public API/docs.
All 32 ground-truth anchors programmatically verified present in the claimed file.
**Scoring unit:** source file. A hit = the correct implementing file appears in top-k.
**Embedder held constant:** Ollama `nomic-embed-text` (768-dim) for both tools.

#### Accuracy

| | top-1 | top-3 | top-5 |
|---|---|---|---|
| **Aletheore** (hybrid RRF over code chunks) | **75.0%** (24/32) | **90.6%** (29/32) | **96.9%** (31/32) |
| RepoWise `--mode semantic` | 28.1% (9/32) | 56.2% (18/32) | 56.2% (18/32) |
| RepoWise `--mode fulltext` | 21.9% (7/32) | 56.2% (18/32) | 65.6% (21/32) |
| RepoWise *oracle* (best of both modes per question) | 40.6% | 71.9% | 78.1% |

The oracle row is not achievable in practice — it retroactively picks whichever
mode happened to win each question. Included as a generous upper bound.

#### Speed

Measured two ways, because the first way was misleading.

| | in-process (library) | via CLI (user-experienced) |
|---|---|---|
| Aletheore | 125 ms mean / 115 median / 184 p95 (0.8.11) | 2853 ms mean |
| RepoWise | **68 ms** mean / 67 median / 80 p95 | 3025 ms mean |

**Re-verified 2026-08-22 against current versions (Aletheore 0.9.0, RepoWise
0.27.0)**, using `scripts/run_aletheore.py` and the now-committed
`scripts/run_repowise_inprocess.py` (previously this row had no backing
script - see below):

| | in-process (library) |
|---|---|
| Aletheore | 40.5 ms mean / 39.1 median / 47.5 p95 |
| RepoWise | 52.5 ms mean / 51.4 median / 61.3 p95 |

Aletheore is now faster in-process, not slower - reversed from the 0.8.11
figures above, not just closed. Two things changed to get a trustworthy
number here, both real bugs this repo had been carrying silently:

1. **`run_aletheore.py` didn't pin `allow_hosted=False`.** `search_index()`
   prefers Aletheore's hosted embedding endpoint whenever a saved
   `ALETHEORE_API_TOKEN`/credential is available - correct product
   behavior, wrong benchmark behavior, since this "in-process" number is
   supposed to isolate local compute. An unpinned re-run on a machine with
   a stale saved credential measured ~205ms instead of ~40-53ms for the
   identical corpus and questions - indistinguishable from a real
   regression without the pin. `run_aletheore.py` now passes
   `allow_hosted=False` explicitly and prints when it declines an
   available hosted path, so the number is deterministic regardless of the
   runner's login state.
2. **RepoWise's "68 ms" figure was never backed by a committed script.**
   The only script that measured RepoWise (`run_repowise.py`) always
   subprocesses `repowise search` per query, which pays the cost of
   importing the `lancedb` package (~2.5-3.5s, measured via cProfile) on
   *every single query* - not retrieval, Python import machinery. That is
   the real, correct number for what a user experiences invoking the CLI
   once per query (see the "via CLI" column), but it cannot reproduce
   "68 ms in-process" - that figure was asserted in prose with nothing to
   re-derive it from, unlike every other number in this file.
   `scripts/run_repowise_inprocess.py` (new) calls RepoWise's
   `LanceDBVectorStore.search()` directly in one long-lived process, the
   same way `run_aletheore.py` calls `search_index()` - simulating a
   long-lived caller (an MCP server, or the CLI run in a loop) that pays
   the import cost once instead of per query. Its result, 52.5ms, closely
   matches the original 68ms claim - the claim itself was directionally
   right, just unreproducible from what was committed.

**RepoWise's retrieval is ~1.8x faster than ours in-process, as measured at
0.8.11.** Via CLI the two are within ~6% of each other; most of that number
is Python interpreter + import startup (~709 ms floor for RepoWise's CLI),
not retrieval. **As of 0.9.0, re-measured with both gaps above closed,
Aletheore is faster in-process instead** - re-run both scripts before
citing either figure, since the 0.8.11 row is no longer current.

#### Setup cost (one-time)

| | time | $ |
|---|---|---|
| Aletheore (`scan` + `index`) | 74 s (22 s + 52 s) | **$0.00** (local embeddings, no LLM) |
| RepoWise (`init --coverage 1.0` + `reindex`) | ~6 min generation + 43 s embed | **$0.1751** (114 calls, 364K in / 443K out, `deepseek-v4-flash`) |

Index artifacts: Aletheore 511 code chunks / 2.0 MB. RepoWise 110 wiki pages +
88 decision records = 198 vectors.

#### Fairness adjustments made (all favour RepoWise)

1. **Coverage raised to 100%.** RepoWise defaults to `--coverage 0.20` — 16 file
   pages for 83 Python files, a hard ~20% retrieval ceiling. Overridden to
   `--coverage 1.0` (79 file pages) so it is not judged on a default it did not choose.
2. **Non-file pages discounted.** Structural pages (`layer:*`, `scc-*`,
   `onboarding/*`) cannot match a source file by construction and consume rank
   slots. Re-scored with them dropped: top-1 28.1% (unchanged), top-5 56.2% → 59.4%.
   Not the cause of the gap.
3. **Both modes reported**, plus the unachievable best-of-both oracle.
4. **Real LLM, not a local model.** First attempt used local `qwen2.5-coder:14b`;
   discarded because it does not represent the shipped product.

#### Bug found in RepoWise (affects its own users, not just this benchmark)

`repowise search --mode semantic` **silently degrades to full-text search.**

In `repowise/cli/commands/search_cmd.py:148-176`, `_search_semantic` wraps the
LanceDB path in `except Exception: pass` and falls through to FTS — while still
printing the header `Semantic search: '<query>'`. The user has no signal.

Trigger: `search` has no `--embedder` flag (unlike `reindex`), so it calls
`_resolve_embedder(None)`. With no cloud embedding key set this resolves to
`mock` → 8-dim `MockEmbedder` → LanceDB raises
`Invalid input, No vector column found to match with the query vector dimension: 8`
→ swallowed → FTS.

This invalidated our first "semantic" run: it was byte-identical to the fulltext
run on all 32/32 questions. Fixed by setting `REPOWISE_EMBEDDER=ollama`.
After the fix, 0/32 results matched the FTS run.

#### Honest reading

- Aletheore is decisively better at **"which file implements X"** — the gap holds
  even against RepoWise's unachievable oracle, and survives every adjustment made
  in RepoWise's favour.
- Aletheore is **cheaper and faster to set up** ($0 / 74 s vs $0.18 / ~7 min).
- **RepoWise's retrieval is genuinely faster per query** (68 ms vs 125 ms in-process).
  We should not claim a speed win.
- The tools optimise for different targets: we index code chunks and return
  `file:line`; RepoWise indexes generated prose and returns wiki pages. These
  questions ask "where is this implemented", which is our target. A question set
  asking "explain the architecture" would likely invert the result — that is not
  measured here and should not be inferred either way.

#### Asking without naming a language: a metric, and a fix that mostly did not work

A question naming no language has no single correct answer in a polyglot
repository - "where is the binary protocol implemented?" is answered by any of
eight files in apache/thrift. Scoring that with top-1 would reward filling every
slot with near-duplicates from whichever language embedded closest, which is the
behaviour under investigation rather than the goal. `thrift_anylang.json` (10
questions, 5-8 implementations each, ground truth generated from the tree rather
than authored) is scored by `scripts/score_coverage.py` on **coverage@k**: how
many distinct languages of the correct set reached the top k, over the most that
could fit.

Baseline, Aletheore 0.8.11: hit@5 80.0%, **coverage@5 32.0%**, coverage@10
24.9%. Two of ten questions surfaced no correct language at all.

A per-language occupancy cap was then implemented, mirroring the existing
per-file cap, applied only to an unscoped query whose candidates span three or
more languages so a single-language repository is untouched by construction
(confirmed: flask byte-identical, MRR to three decimals):

| configuration | coverage@5 | coverage@10 | languages returned @10 |
|---|---|---|---|
| baseline | 32.0% | 24.9% | 4.9 |
| cap 2 per language | 32.0% | 24.9% | 6.0 |
| cap 1 per language | 36.0% | 34.6% | 7.7 |

The cap does what it was built to do - more languages appear - but coverage@5
moves only 32% to 36% against a ceiling near 71%. Freeing slots is therefore not
the binding constraint: **the correct file in most languages is not a strong
candidate to begin with**, so there is nothing better waiting to fill the slots
that were freed. The change is recorded here and not shipped.

What this does establish is the measurement. Before it, no number distinguished
"answered in one language" from "showed the user their options", so any work on
unscoped polyglot queries was unfalsifiable.

#### Near-duplicate crowding: a falsified ranking lead

"Sibling crowding" was initially described in this repository as the strongest
open lead,
observed independently on three corpora: slimphp/Slim's `RequestResponse*`
strategies, google/gson's `TypeAdapters.java`, and apache/thrift's
`binary_protocol` / `compact_protocol` pairs. Two ranking fixes were built
against it and both were rejected on measurement.

Before building a third ranking change, the misses were checked against the vocabulary regime.
Every one of them disappears:

| corpus | general-regime misses | vocabulary-regime misses |
|---|---|---|
| Slim | php02, php04, php11, php13, php14 | none |
| gson | java07, java14 | java03 (a different question) |

php04 is the `CallableResolver` case that consumed two releases and two
rejected ranking fixes. Asked in the project's own vocabulary it is answered
correctly.

The mechanism is not mysterious. When a query carries no token that
distinguishes one sibling from another - "the straightforward fixed-width wire
encoding" names neither `binary` nor `compact` - the siblings are genuinely
indistinguishable, and no ranking change can recover information the question
never contained. Crowding is what the phrasing confound looks like from inside
the result list.

Two consequences, both now practice here:

1. **A ranking fix aimed at a general-regime miss must be checked against the
   vocabulary regime first.** If the vocabulary version already passes, the
   miss is a question problem and a ranking change would be fitting to our own
   prose.
2. **The independent question set is the top open item**, not a nice-to-have.
   Until questions come from outside, we cannot separate product weakness from
   question weakness on any weak corpus.

#### A published table that did not reproduce (corrected 2026-08-13)

The first revision of this repository listed flask retrieval as **71.9% / 96.9%
/ 100%**. That row was wrong, and it is worth saying exactly how, because the
failure mode is easy to repeat.

Two results files were committed here, from two different builds:

| file | top-1 | top-3 | top-5 |
|---|---|---|---|
| `results_aletheore.json` | 75.0% | 90.6% | 96.9% |
| `results_aletheore_after_constants.json` | 71.9% | 90.6% | 96.9% |

The published row took **71.9%** from the second file and **96.9% / 100%** from
neither — the top-5 figure came from a later, uncommitted run. Nobody could have
reproduced it, including us, because no single run ever produced those three
numbers together.

It was caught by re-running the harness across every 0.8.x tag while
investigating something unrelated. Each tag from v0.8.0 through v0.8.4 produces
**65.6% / 93.8% / 100%** on the same corpus commit and the same 32 questions.
0.8.5 produces 68.8% / 93.8% / 100%.

Two things follow, and both are now practice here:

1. **A results table cites one run.** Assembling a row from the best available
   figure in each column is not a summary, it is a fabrication, even when every
   individual number was real at some point.
2. **Numbers are attributed to a release that can be installed.** The old row
   was labelled v0.8.0, a version that never existed on PyPI (see the note in
   README about the frozen `pyproject.toml`), so "reproduce it with 0.8.0" was
   never an instruction anyone could follow.

Top-1 genuinely declined across the 0.8.x hardening work — 75.0% → 71.9% →
65.6% — while top-3 and top-5 rose. 0.8.5 recovers part of it. That trade is
shown in both directions in the README rather than reported as a straight win.

#### Aletheore's one miss (q32)

"Where are the notification hooks that extensions can subscribe to declared?"
Expected `src/flask/signals.py`; we return `examples/celery/make_celery.py` first.
`signals.py` is 17 lines of bare `Signal()` assignments with almost no prose —
little for an embedder to grip. RepoWise's semantic mode also missed it; its
fulltext mode hit it. A genuine weakness of chunk-based retrieval on
declaration-only files.

---

### Part 2 — Architecture / comprehension questions (12 questions)

Different task: "explain how X works", not "which file implements X". File-level
scoring is the wrong instrument, so this half uses a **blind LLM judge** on the
retrieved material, 0-3 scale, each question graded twice with the two systems'
positions swapped to cancel position bias. Tool names scrubbed from all material.
Equal ~12,000-character context budget per system.

| Arm (our side) | our score | RepoWise | judge preference |
|---|---|---|---|
| Raw code chunks (CLI product) | 1.67 | **2.08** | 8 vs 14 (2 tie) |
| AIRview, full payload, retrieved | 1.21 | **2.54** | 4 vs 20 (0 tie) |
| AIRview + code chunks | 1.50 | **2.46** | 7 vs 17 (0 tie) |
| ~~AIRview prose only~~ (measurement error, see below) | ~~0.46~~ | ~~2.67~~ | — |

**Correction.** The first AIRview arm scored 0.46 because the harness fed the judge
only subsystem descriptions plus bare file paths — 4,443 of AIRview's 50,686
characters, 8.8% of it. AIRview also carries a `role` per file and an
`explanation` per key symbol with line numbers (83 files, 479 symbols documented).
Re-run with the full payload, retrieved per question into the same budget, the
score is **1.21**. The conclusion is unchanged but the original number was wrong.

**RepoWise wins this half, in every arm.** This is the mirror image of Part 1 and
should be reported with equal prominence.

Why: AIRview is a *breadth map* — 12 subsystem summaries (~309 chars each) plus a
726-char overview, 4,443 characters of prose total. RepoWise generates 110 detailed
per-file pages. For "explain the architecture of this module", their depth wins.
AIRview alone scores worse than our raw code chunks because it is too thin to
answer a detailed question.

Judge confound: the Part-1-arm judge was DeepSeek, which also generated RepoWise's
wiki (ours is raw source, no LLM) — a possible self-preference bias pointing at the
result that won. In the AIRview arms both sides are DeepSeek-generated prose, which
largely cancels it; RepoWise still wins. An independent local judge run is pending.

#### Citation grounding (the "evidence-backed" claim, measured)

| | result |
|---|---|
| RepoWise `file:line` citations across all 110 pages | **0** |
| RepoWise backticked identifiers claimed | 2,136 |
| ...not found anywhere in the repo | **10 (0.5%)** |
| AIRview subsystems rejected by citation verification | 0 of 12 |

**Do not claim RepoWise hallucinates.** At 0.5% ungrounded — and most of those are
benign (`Makefile`, `conftest`, `Expires`, `TIMESTAMP` are real things, just not
Python symbols) — their prose is well grounded. Genuine errors found: they document
`before_first_request` and `has_blinker`, both removed from modern Flask (staleness,
not fabrication).

The real, defensible difference is **verifiability, not accuracy**: RepoWise emits
no line-level citations, so its claims cannot be mechanically checked or clicked
through to source. AIRview runs `verify_citations` and *discards an entire page*
whose `file:line` references don't resolve against scanner evidence
(`live_wiki.py:157-166`). That is a process guarantee, not a measured quality win —
and on this corpus it rejected nothing, so it cost nothing and proved nothing.

#### Independent judge cross-check (confound resolved)

The architecture judge was DeepSeek, which also generated RepoWise's wiki. Ours is
raw source with no LLM, so any self-preference bias pointed at the side that won.
Re-judged the raw-code-chunks arm with `llama3.1:8b` locally (`num_ctx=16384` — the
4096 default would have silently truncated ~7,000-token prompts and graded partial
material).

| judge | Aletheore | RepoWise | gap | ties |
|---|---|---|---|---|
| deepseek-chat | 1.67 | 2.08 | 0.41 | 2/24 |
| llama3.1:8b (independent) | 2.38 | 2.58 | 0.20 | 16/24 |

**Direction holds: both judges favour RepoWise.** The self-preference confound does
not explain the result.

**Magnitude does not hold.** The independent judge scores everything higher and ties
16 of 24 pairings — behaviour typical of a small model compressing toward the middle
rather than genuinely finding the systems equivalent. Treat it as a directional
check, not a magnitude estimate, and do not quote either gap as precise.

Caveat: this cross-check covers only the raw-code-chunks arm. The AIRview arms were
judged by DeepSeek alone — though in those arms both sides are DeepSeek-generated
prose, which largely neutralises the same confound.

#### A 0.8.13 reproducibility check that measured hosted jina instead of local nomic (caught and corrected, 2026-08-20)

An attempt to verify this repository's "Locating code" table under Aletheore
0.8.13 briefly published a false finding — a "zod regression" under the new
CLI version — directly to this file and to the marketing site. It has been
reverted. This section documents what actually happened, so the mistake stays
visible rather than being quietly patched.

**What went wrong.** Every reproduction environment this session used —
several separate `pip install aletheore==X` venvs, each intended to be
isolated — silently picked up a real `ALETHEORE_API_TOKEN` saved at
`~/.config/aletheore/credentials.json`. That path is scoped to the user's
home directory, which a Python venv does not isolate. With a valid token
present, `_embed_in_batches()` in `search_index.py` prefers Aletheore's
*hosted* embedding endpoint (currently `jina-embeddings-v2-base-code`) over
local Ollama by default — correct, intentional behaviour for a real user, but
fatal to a reproduction that means to measure "local, no API key, $0.00."
Every corpus re-indexed this session was actually embedded with hosted jina,
not local nomic, without any error or warning to say so.

**How it surfaced.** zod's contaminated result was a hard 0.0% top-1 on
general phrasing — not just lower, absent — which was suspicious enough to
look at the raw ranked files rather than trust the scored percentage. They
were not garbage: they were plausible, on-topic, wrong files, consistent with
an embedder-quality gap rather than a broken pipeline. That prompted a
controlled test: re-run gin and zod with `HOME` overridden to an empty
directory, so `get_api_key()` is guaranteed to return `None` and the run is
provably local-only. Both came back identical, to three decimal places on
MRR, to the numbers already published for 0.8.11 above — proving the
contamination, and that local retrieval itself had not changed.

**Confirmed for all 23 rows, not just the 2 spot-checked.** Rather than
re-run all 13 corpora cleanly (expensive — thrift alone took the better part
of an hour earlier this session), `search_index.py` was diffed directly
between `aletheore==0.8.11` and `aletheore==0.8.13` installed in separate
venvs. The local embedding path — `embed_texts`, chunking, the batch loop —
is byte-for-byte unchanged. Every real change in 0.8.13 is hosted-embedding
specific: retry/backoff on 429s, character-cap tuning for the hosted batcher,
and one genuine bug fix (below). Combined with the gin/zod spot-check, this
is direct evidence, not extrapolation, that the "Locating code" table is
identical under 0.8.11 and 0.8.13. It has been reverted to the original
published numbers rather than republished with numbers that were never
actually different.

**A real bug the same diff surfaced, unrelated to this benchmark's numbers.**
Before 0.8.13, `search_index()` always embedded the *query* locally
(`embed_texts([query_text])[0]`), regardless of what embedded the *index*.
A user with a saved token who built an index with hosted jina would have
every subsequent search silently compared against local nomic query
vectors — two unrelated vector spaces — with no error, because jina and
nomic happen to both be 768-dimensional, so the dimension-mismatch guard
never fired. 0.8.13 fixes this by making the query use the same hosted/local
choice as the index build. This benchmark's own committed results were never
affected by that specific bug (no token was present until this session's
tooling accident introduced one), but it's a real, previously-silent defect
worth knowing if you've used Aletheore locally with a saved API token.

**A real, verified finding this chase did surface.** Chasing the false "zod
regression" down turned up a genuine, much larger gap between hosted jina and
local nomic on zod specifically than the existing
["Hosted embeddings"](README.md#hosted-embeddings-jina-vs-local-nomic)
section documents (that section's own zod numbers: -6.7pp both regimes,
measured against a separate dev checkout, [`e2cc409`](https://github.com/Aletheore/Aletheore/commit/e2cc409)).
The accidental hosted run this session produced showed general top-1 20.0%
→ 0.0% and vocabulary top-1 60.0% → 6.7% — a much steeper drop. Reading the
raw ranked files (not just the score) found two concrete decoy files jina
ranks above the true answer that nomic does not:

- `packages/resolution/src/index.ts` — a 37-line smoke-test file that
  literally imports every zod build variant in one place (`zod`, `zod/mini`,
  `zod/v3`, `zod/v4`, `zod/v4-mini`, plus a locale file), giving it lexical
  overlap with nearly the entire module surface despite being semantically
  irrelevant to any of it. Shows up as a false top-3 hit on 4 of 15 general
  questions.
- The ~30 locale files under `packages/zod/src/v4/locales/` — each imports
  the same core types (`$ZodStringFormats`, `errors`, `util` from
  `core/checks.js` / `core/errors.js` / `core/util.js`) as the real
  implementation files they're competing against, because every locale
  wires up the same error-message keys.

Neither is a broken pipeline — both are plausible, on-topic, wrong answers.
It's the same near-duplicate-crowding category already documented above and
in the Hosted embeddings section, just a sharper instance of it, and
consistent with jina winning broadly elsewhere: most corpora don't have a
decoy file shaped like `resolution/index.ts`. **Left open:** why this
measurement's zod gap is so much larger than the one already published in
the Hosted embeddings section is not yet resolved — the two were measured
against different deployments (a dev checkout vs. today's live hosted
service), so infrastructure drift between them hasn't been ruled out.

**Left undone.** The two raw-rows files this session committed
(`results/retrieval_raw_0813.json`, `results/retrieval_raw_0811_partial.json`)
were both generated by the same contaminated tooling and have been removed
rather than kept as false "clean, no-network-needed" backing data. A genuine
`HOME`-isolated, credential-free raw capture for all 23 rows under 0.8.13 is
still open follow-up work for the other 12 corpora.

**zod itself is now done, from a fresh clone.** Not the same repro directory
reused — a brand-new `git clone` of `colinhacks/zod` at the pinned commit,
scanned and indexed from zero with `HOME` overridden to an empty directory
(`get_api_key()` verified to return `None` first), queried for both regimes,
and scored with `scripts/score_retrieval_matrix.py` itself rather than a
hand-rolled script. Result: general 20.0% / 40.0% / 40.0%, MRR 0.289;
vocabulary 60.0% / 73.3% / 73.3%, MRR 0.667 — exactly the numbers published
above, chunk count 2,395 matching the earlier run too. Raw rows committed at
[`results/retrieval_raw_zod_0813_verified.json`](results/retrieval_raw_zod_0813_verified.json),
re-derives with:

```bash
python3 scripts/score_retrieval_matrix.py results/retrieval_raw_zod_0813_verified.json
```

</details>

## Contents

| path | what |
|---|---|
| `questions/` | 418 questions in 28 sets (the whole directory; the retrieval scope quoted above is a subset), every ground-truth anchor mechanically verified |
| `scripts/` | runners, scorers, the blind judges, the language-coverage matrix |
| `scripts/score_fallback_judge.py` | re-derives every fallback number above from `results/`, no API key |
| `scripts/run_retrieval_matrix.py` | runs the retrieval matrix against every corpus's built index; hosted embeddings need `aletheore login` |
| `scripts/score_retrieval_matrix.py` | re-derives the "Locating code" and "Hosted embeddings" tables from `results/`, no API key |
| `results/` | raw per-query output — recompute any number without an API key |
| `results/det_vs_llm_*` | inputs, model outputs, and ground truth for the deterministic-analysis-vs-bare-LLM benchmark |
| `pr_review/` | the Flash Review compact-vs-full-context A/B (4 experiments, 3 models), a named 3-way head-to-head against PR-Agent (Experiment 5), and a named 5-way head-to-head that found and fixed a real production context-block regression (Experiment 6) — full writeup in `pr_review/README.md` |
| `pr_review/results/` | raw generation and verification output for every PR-review experiment run |
| `external_pr_recall_benchmark/` | real-reviewer-comment recall benchmark across sentry/grafana/cal.diy/keycloak — used to validate/reject real Flash Review prompt changes; full writeup in `external_pr_recall_benchmark/README.md` |
| `external_pr_recall_benchmark/results/` | corpus manifest, per-run logs, and the full recall/precision summary |
| `swe_prbench/` | head-to-head against the real, external SWE-PRBench leaderboard (Claude Sonnet 4.6, Haiku 4.5, DeepSeek V3, GPT-4o) - full writeup in `swe_prbench/README.md` |
| `swe_prbench/scripts/` | generation and scoring drivers - run inside the deployed scan-worker container, reusable for a re-run |
| `swe_prbench/results/` | real per-task judge output (gpt-5.2, both API routes), the Luna side-experiment, and the 4-run variance check |
| `graphify_comparison/` | head-to-head against Graphify on ERPNext, both tools run ourselves under one harness and judge, full writeup in `graphify_comparison/README.md` |
| `security-scanner-benchmark/` | `aletheore_secrets` + `aletheore_vulnerabilities` accuracy — synthetic pilot corpus + 20-real-repo validation, full writeup in `security-scanner-benchmark/README.md` and `REPORT.md` |
| `dead-code-benchmark/` | `aletheore_dead_code` accuracy — 10-case pilot corpus, full writeup in `dead-code-benchmark/README.md` |
| `ast-pattern-benchmark/` | `aletheore_ast_pattern` real-repo stress test — found and fixed a real tree-sitter segfault, full writeup in `ast-pattern-benchmark/README.md` |
| `license-detection-benchmark/` | `aletheore_licenses` real-repo validation — 3 real gaps found and fixed, full writeup in `license-detection-benchmark/README.md` |
| `sql-schema-benchmark/` | `aletheore_database` real-repo validation + head-to-head against Repowise, 8 real gaps found and fixed across 5,378 migration files, full writeup in `sql-schema-benchmark/README.md` and `REPORT.md` |
| `secrets_scanner/` | head-to-head against RepoWise's hardcoded-credential detection — a synthetic pilot corpus plus 20 real repos (21,430 files), both scanners called in-process, no API key, full writeup in `secrets_scanner/README.md` |
| `scripts/det_vs_llm_*` | its runners — `det_vs_llm_exact_ground_truth.py` needs no API key |
| `corpora.json` | pinned commits for all corpora |
| `CORPUS_PLAN.md` | the 11-language programme: repos, procedure, cost, and what was rejected |
| `METHODOLOGY.md` | full method, every adjustment made in RepoWise's favour, errors caught in our own runs |
| `REPRODUCIBILITY.md` | versions; what reproduces bit-for-bit and what does not |
| `LANGUAGE_COVERAGE.md` | scanner coverage across all 13 supported languages, plus a RepoWise dead-code comparison for Kotlin and Swift |
| `AIRVIEW_GAP.md` | why our generated wiki lost, what changed, and what did not work |
| `DETERMINISTIC_VS_LLM.md` | hotspots/ownership/dead-code: can a bare LLM reproduce the scanner's answer given the same data? |

## Honesty notes

**A 2026-08-20 reproducibility check briefly published a false "0.8.13
regression."** A tooling bug (a leftover credential caused "isolated"
reproduction environments to silently use hosted embeddings instead of
local) made it look like zod's retrieval quality dropped under Aletheore
0.8.13. It didn't — local retrieval is unchanged between 0.8.11 and 0.8.13,
confirmed by diffing the two versions' source directly. Caught, reverted,
and documented rather than quietly fixed: full account in
[METHODOLOGY.md](METHODOLOGY.md#a-0813-reproducibility-check-that-measured-hosted-jina-instead-of-local-nomic-caught-and-corrected-2026-08-20).

**The questions were authored by us.** They are sourced from each project's
public API and documentation, and every ground-truth anchor is verified
mechanically, but this remains the weakest link in the methodology. An
independently authored question set would be stronger evidence, and is the most
useful contribution anyone could make here.

**The AIRview fallback figures describe the GitHub App, not the CLI release.**
The coverage and `get_context` sections above measure
`build_file_fallback_detail` in `github-app/scan_worker/live_wiki.py` at commit
`7089e14` (PR #243, "give AIRview a deterministic fallback for files with no
generated page"). The measured file is byte-identical to that commit. It is not
part of Aletheore 0.8.11 — 0.8.11 is the CLI, this is the GitHub App, which is
versioned separately and not published to PyPI. Reproducing these two sections
therefore needs the app repository at that commit, not `pip install`.

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
