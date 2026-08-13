# Corpus plan — 11-language head-to-head

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

## Per-corpus procedure

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

## Cost

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

## Known measurement hazards

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
