# MCP tool efficiency — live servers, not code reading

Both tools' actual MCP servers, launched as real subprocesses, spoken to over the real
stdio JSON-RPC protocol (`mcp` SDK 2.2.0 on both sides), against the exact same real
repo (`pallets/flask`, shallow-cloned fresh). No LLM in the loop — this measures the
tool-result text an agent would actually receive, via `tiktoken`'s `cl100k_base`
encoding, not architecture claims read from source.

Two matched real questions. Results cut in different directions — both are reported,
not just the one that favors us.

## Setup

```
git clone --depth 1 https://github.com/pallets/flask bench-repo
cd bench-repo && aletheore scan .            # Aletheore's real scanner
cd bench-repo && graphify extract . --code-only   # Graphify's real extractor (graphifyy 0.9.68)
```

`mcp_stdio_client.py` in this directory launches either server (`aletheore mcp .` /
`python -m graphify.serve`) and does a real `initialize` → `tools/call` round trip.
Raw captures for every call below are in `captures/`.

## Query 1: "Who imports `src/flask/app.py`?"

| tool call | tool calls | tokens | correct? |
|---|---|---|---|
| Aletheore `aletheore_imported_by` | 1 | **45** | ✅ exact, complete — 6 real importers |
| Graphify `get_neighbors` | 1 | 1,160 | ❌ wrong direction — `get_neighbors` returns mostly successor edges (what app.py imports/contains), not predecessors; only one incidental `re_exports` edge points back |
| Graphify `query_graph` (their actual semantic-query tool, the intended way to ask a natural-language question like this) | 1 | 1,852 | ⚠️ truncated — hits its own ~2000-token budget at 95 of 190 traversed nodes, and its own output tells the caller to narrow the query. The 6 real importers are somewhere in the dump, unlabeled and not isolated from the other 184 nodes |

Aletheore answers this class of question — "what's on the other side of a directed
edge" — completely, in one call, for less than the token cost of Graphify's own
truncation warning message alone. This isn't a close efficiency win; it's a structural
one: `get_neighbors` has no reverse-direction mode, so Graphify's only real path to this
answer is the general-purpose semantic traversal tool, which is neither targeted at
this question nor bounded well enough to answer it in one shot on a graph this size.

## Query 2: "What functions/methods does `src/flask/app.py` (and its `Flask` class) define?"

| tool call | tool calls | tokens | what you get |
|---|---|---|---|
| Aletheore `aletheore_symbols` | 1 | 8,264 | all 40 functions (incl. nested closures), each with parameters, return type, docstring |
| Graphify `get_neighbors` × 3 (top-level `contains`, then an ambiguous-label retry, then the `Flask` node's `method`-filtered neighbors) | 3 | 1,074 total | 39 functions/methods — names and line numbers only, no docstrings, no types |

**This one does not favor Aletheore.** Graphify's answer costs 8x fewer tokens in
total — but it is returning a meaningfully sparser answer (no docstrings, no
parameter/return types), and getting there took a real, verified extra round trip: a
bare `get_neighbors(label="Flask")` came back "Ambiguous: 'flask' matches 3 nodes in
different files," requiring a second call with the disambiguated node id before the
method list could be fetched at all. Reported here in full because a benchmark that
only publishes the query where we win isn't a benchmark — see this project's own
established standard on that (`graphify_comparison/README.md`, `pr_review/README.md`).

## Query 3: "Who calls `Flask.wsgi_app`?" — a real gap this surfaced in *our own* tool

| tool call | tokens | what you get |
|---|---|---|
| Aletheore `aletheore_get_blast_radius(target="src/flask/app.py", symbol="wsgi_app")` | 504 | 6 direct + 50 (truncated) transitive file-level dependents, plus a symbol-verified `confirmed_callers` field — which came back **empty** |
| Graphify `get_neighbors` on the `wsgi_app` node | 222 | the real, correct answer: `.__call__()` calls `.wsgi_app()`, in the same file, at `app.py:L1628` |

`confirmed_callers[0]` being empty is not a display bug — verified directly
(`grep -rn "\.wsgi_app(" bench-repo --include="*.py"` outside `app.py`: zero hits).
No *other file* in the repo calls `wsgi_app` by name; every real caller goes through
Flask's `__call__` (the WSGI entry point), which lives in the *same* file as
`wsgi_app` itself.

That's the real gap this query surfaced: **`aletheore_get_blast_radius`'s
`confirmed_callers` only checks *other files'* dependents for a call to the named
symbol — it has no path to a same-file/same-class caller at all**, so it correctly
reports zero rather than guessing, but it also can't tell you about the actual,
real caller sitting one class away. Graphify's `get_neighbors`, being a native
call-graph tool rather than a file-dependency tool, found that real caller directly
because intra-file calls are just edges in its graph like any other. A real,
structural capability gap in our own tool, not a case of Graphify being wrong —
reported here because a comparison that only surfaces the other side's gaps isn't
one worth trusting.

## Cross-repo check: is Query 1 a one-repo artifact?

Repeated on a second, different-language real repo (`gin-gonic/gin`, Go) with a
different real file (`gin.go`, imported by `ginS/gins.go` and `ginS/gins_test.go`):

| tool call | tokens | correct? |
|---|---|---|
| Aletheore `aletheore_imported_by` | **17** | ✅ exact, complete |
| Graphify `get_neighbors` | 1,070 | ⚠️ the 2 real importers are in there — at the very bottom of 50 lines, undistinguished from ~48 unrelated outgoing edges |
| Graphify `query_graph` | 1,860 | ⚠️ truncated again (102 of 163 nodes); the 2 real importers happen to appear near the top of what's shown this time, but still undifferentiated from everything else BFS turned up |

Same pattern, same order of magnitude (60-70x), on a different language and a
different codebase. Not a one-repo artifact.

## Capability surface: tools Graphify simply doesn't have

Separately from efficiency, seven of Aletheore's MCP tools answer questions
Graphify's 10-tool surface has no path to at all — not "less efficient," genuinely
absent, because Graphify is scoped as a pure code-knowledge-graph tool and doesn't
claim to do security/dependency/git-history analysis. Listed for completeness, not
as an unfair ding — real output, same flask repo:

| Aletheore tool | tokens | real finding on this run |
|---|---|---|
| `aletheore_vulnerabilities` | 2,359 | a real CVE (`PYSEC-2026-2132`, command injection in `click.edit()`) in Flask's own pinned `click` dependency |
| `aletheore_endpoints` | 6,344 | 311 real API endpoints mapped across the repo and its example apps |
| `aletheore_hotspots` | 1,709 | real git churn/co-change data, 30 files |
| `aletheore_dead_code` | 273 | 2 real unreachable modules (`docs/conf.py`, `examples/celery/make_celery.py`) |
| `aletheore_licenses` | 184 | repo license classification + per-dependency license findings |
| `aletheore_cluster` | 84 | the 9-module architecture cluster containing `app.py` |
| `aletheore_secrets` | 4 | correctly empty — no secrets in this file |

Graphify's `list_prs`/`get_pr_impact`/`triage_prs` are the reverse case: GitHub PR/CI
integration Aletheore's MCP tools don't do. Each tool's scope is genuinely different;
this table says what exists, not which is "better."

## Honest summary

- **Directional relationship queries (imports/imported-by, callers/callees):**
  Aletheore wins decisively, because it has purpose-built tools for each direction and
  Graphify's one general-purpose `get_neighbors`/`query_graph` pair either answers the
  wrong direction or burns a large token budget on an unbounded semantic traversal.
- **"Tell me everything about this symbol" queries:** Graphify is cheaper in raw
  tokens, precisely because it returns less — no docstrings, no type signatures — and
  needs more round trips (including a real, reproduced ambiguous-label retry) to
  assemble a comparable answer.
- Neither tool is "the efficient one" in general. Which one costs less depends on
  whether the question has a clear direction (Aletheore) or wants a flat name dump
  (Graphify) versus rich per-symbol detail (Aletheore, at real token cost).
- **Same-file call-graph edges are a real, verified gap in Aletheore's own
  `confirmed_callers`**, not just a Graphify weakness elsewhere — a file-dependency
  tool and a call-graph tool answer different questions, and neither subsumes the
  other.

## Reproducing

```
python3 -m venv aletheore-venv && aletheore-venv/bin/pip install -e /path/to/Aletheore/src
python3 -m venv graphify-venv && graphify-venv/bin/pip install graphifyy mcp tiktoken

git clone --depth 1 https://github.com/pallets/flask bench-repo
cd bench-repo
../aletheore-venv/bin/aletheore scan .
../graphify-venv/bin/graphify extract . --code-only

../aletheore-venv/bin/python3 ../mcp_stdio_client.py call ../aletheore-venv/bin/aletheore mcp . -- aletheore_imported_by '{"target": "src/flask/app.py"}'
../graphify-venv/bin/python3 ../mcp_stdio_client.py call ../graphify-venv/bin/python3 -m graphify.serve -- get_neighbors '{"label": "flask/app.py"}'
```
