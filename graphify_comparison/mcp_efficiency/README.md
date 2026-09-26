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

## Query 3: "Who calls `Flask.wsgi_app`?" — a real gap this surfaced in *our own* tool, now fixed

| tool call | tokens | what you get |
|---|---|---|
| Aletheore `aletheore_get_blast_radius(target="src/flask/app.py", symbol="wsgi_app")` (pre-fix) | 504 | 6 direct + 50 (truncated) transitive file-level dependents, plus a symbol-verified `confirmed_callers` field — which came back **empty** |
| Aletheore, same call, **post-fix** | 512 | identical result, plus a new `same_file_caller: true` field |
| Graphify `get_neighbors` on the `wsgi_app` node | 222 | the real, correct answer: `.__call__()` calls `.wsgi_app()`, in the same file, at `app.py:L1628` |

`confirmed_callers[0]` being empty was not a display bug — verified directly
(`grep -rn "\.wsgi_app(" bench-repo --include="*.py"` outside `app.py`: zero hits).
No *other file* in the repo calls `wsgi_app` by name; every real caller goes through
Flask's `__call__` (the WSGI entry point), which lives in the *same* file as
`wsgi_app` itself.

That was the real gap this query surfaced: `aletheore_get_blast_radius`'s
`confirmed_callers` only checked *other files'* dependents for a call to the named
symbol — it had no path to a same-file/same-class caller at all, so it correctly
reported zero rather than guessing, but it also couldn't tell you about the actual,
real caller sitting one class away. Graphify's `get_neighbors`, being a native
call-graph tool rather than a file-dependency tool, found that real caller directly
because intra-file calls are just edges in its graph like any other.

**Fixed** (`find_blast_radius` in `query.py`, and the mirrored
`build_blast_radius_context` in the production PR-review path —
[Aletheore/Aletheore#835](https://github.com/Aletheore/Aletheore/pull/835)):
both now check the target's own file content for a call to the symbol from
anywhere other than its own definition line, and report it as `same_file_caller`.
Re-run live against the same real MCP server, same repo, same query — the result
above is not simulated. Cost: 8 extra tokens (504 → 512) for a call that used to
silently omit the real caller. Same-file detection is boolean-only (it says a
same-file caller exists but not *which* function, unlike Graphify's graph, which
points straight at `Flask.__call__`) — a real, remaining difference between a
file-dependency tool extended with a same-file check and a native call-graph
tool, not a claim of full parity.

## Query 4: "Is there a call path from `Flask.__call__` to `Flask.wsgi_app`?" — a capability Aletheore doesn't have, and Graphify's version of it doesn't work

Graphify's real MCP tool surface includes `shortest_path` (CLI: `graphify path`),
a class of question Aletheore has no equivalent tool for at all — a genuine,
structural capability gap in Aletheore's favor of Graphify, worth reporting
honestly rather than only surfacing gaps that favor us.

Tested it on the one pair in this repo we can verify is ground-truth true: `.wsgi_app()`
is called directly, by name, inside `.__call__()` (confirmed via `grep`, and the same
fact Query 3 above is built on). First got each node's exact canonical ID from
Graphify's own `get_node` tool — no ambiguity reported for either:

```
get_node("wsgi_app")   -> id: src_flask_app_flask_wsgi_app  (src/flask/app.py L1569)
get_node("__call__")   -> id: src_flask_app_flask_call      (src/flask/app.py, one of 3 matches - picked the flask/app.py one)
```

Then asked for the path between those exact IDs:

```
$ graphify path "src_flask_app_flask_call" "src_flask_app_flask_wsgi_app"
'src_flask_app_flask_call' and 'src_flask_app_flask_wsgi_app' both resolved to
the same node 'src_flask_app_flask'. Use a more specific label or the exact node ID.
```

Both exact IDs — copied verbatim from `get_node`'s own output — collapse onto their
shared parent class node instead of resolving to the two distinct methods, and the
tool's own error message asks for "the exact node ID," which is exactly what was
passed. `--undirected` doesn't change this (confirmed): the collision happens in
label resolution, before direction is considered. A separate attempt using file-qualified
labels (`"app.py:run"` / `"app.py:wsgi_app"`) *did* resolve to two distinct nodes, but
one of them silently matched the wrong symbol (a `shell_command` docstring node, not
`Flask.run`) despite the tool's own "ambiguous match" warning — it proceeded anyway
rather than refusing, unlike `get_neighbors`'s behavior on Query 2's ambiguous-label
case, and returned a technically-real but nonsensical 4-hop path through unrelated
files.

**Honest read:** this isn't "Aletheore wins" — Aletheore has no tool for this
question at all, so it can't be wrong about it, but it also can't answer it.
Graphify's `path`/`shortest_path` is the right idea, a real capability Aletheore
lacks structurally. But on the one pair here we could independently verify as
ground-truth true, it failed twice in a row: once by refusing even exact canonical
IDs, once by silently guessing the wrong node instead of erroring. A genuinely
useful capability, unreliable in practice on this repo.

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

## Second-repo replication: do the fix and the shortest_path finding generalize?

The same `gin-gonic/gin` repo used above, extended to Queries 2-4 - do the
`same_file_caller` fix, the new `aletheore_symbol_path` tool, and Graphify's
`shortest_path` node-resolution bug hold up outside Flask/Python, or were
they specific to that one repo?

`gin.go`'s `ServeHTTP` (the `Engine`'s real HTTP entry point) calls
`handleHTTPRequest` directly, both in the same file - the exact same
structural shape as Flask's `__call__`/`wsgi_app`, independently verified the
same way (`grep -rn "handleHTTPRequest(" --include="*.go"` outside `gin.go`:
zero hits).

| tool call | result |
|---|---|
| Aletheore `aletheore_get_blast_radius(target="gin.go", symbol="handleHTTPRequest")` | `confirmed_callers: []`, `same_file_caller: true` - correct, matches the verified fact |
| Aletheore `aletheore_symbol_path(source="gin.go", source_symbol="ServeHTTP", target="gin.go", target_symbol="handleHTTPRequest")` | `confirmed: true`, `"ServeHTTP's own body contains a call to handleHTTPRequest"` |
| Graphify `get_node("ServeHTTP")` / `get_node("handleHTTPRequest")` | both resolve cleanly to exact canonical IDs, no ambiguity reported |
| Graphify `path <exact ServeHTTP id> <exact handleHTTPRequest id>` | `'...engine_servehttp' and '...engine_handlehttprequest' both resolved to the same node 'bench_repo_2_engine'. Use a more specific label or the exact node ID.` |

Both the fix and the new tool generalize correctly to a second repo in a
different language. Graphify's `shortest_path` node-collision bug also
generalizes - the exact same failure mode (two distinct exact canonical IDs
collapsing onto their shared parent node) reproduces identically on Go/gin as
it did on Python/Flask, with different node IDs but the identical error
message shape. Not a Python-specific or one-repo quirk on either side.

Query 2's shape also holds: `aletheore_symbols(target="gin.go")` returns all
45 functions in the file (package-level and `Engine` methods together, since
Aletheore's `symbols` tool is file-scoped, not struct-scoped) at 2,214 tokens
with full detail (params, docstring, return type). Graphify's
`get_neighbors(label="Engine", relation_filter="method")`, scoped specifically
to `Engine`'s methods, returns names and line numbers only at 743 tokens - the
same "Graphify cheaper, sparser, and answering a slightly narrower question"
pattern as Query 2 on Flask. The comparison isn't perfectly matched in scope
here (file-level vs. struct-level), noted rather than smoothed over.

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
- **Same-file call-graph edges were a real, verified gap in Aletheore's own
  `confirmed_callers`**, found here and fixed in
  [#835](https://github.com/Aletheore/Aletheore/pull/835) — `same_file_caller`
  now reports the same-file case Graphify's native call-graph always saw, at a
  cost of 8 tokens. It's boolean-only, not a named caller, so a file-dependency
  tool extended this way still doesn't fully subsume a native call-graph tool.
  Confirmed generalizing beyond the repo that found it: reproduces correctly
  on `gin-gonic/gin` (Go).
- **Path-between-two-symbols was a real capability Aletheore lacked
  structurally** (Graphify's `shortest_path`) — on the one ground-truth-true
  pair tested here, Graphify's own tool failed twice: refusing its own exact
  canonical node IDs, then silently resolving to the wrong node instead of
  erroring. Rather than leave it as a gap, built it:
  [#837](https://github.com/Aletheore/Aletheore/pull/837) adds
  `aletheore_symbol_path`, verified correct on both Flask/Python and
  gin/Go. Graphify's node-collision bug in `shortest_path` also reproduces
  identically on the second repo, different language, same failure mode -
  not a one-repo or Python-specific quirk on either side.

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
