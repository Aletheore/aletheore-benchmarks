# Aletheore AST-Pattern Search Benchmark

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

## Result: a real, reproducible segfault on Python 3.12 — not 3.14-only

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

## Update: fixed (2026-09-04, Aletheore/Aletheore#537)

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

## Reproducing

```bash
# Needs a large, real Python repo checked out locally - Django is what found this.
python3 -c "
from pathlib import Path
from aletheore.ast_pattern import search_ast_pattern
search_ast_pattern(Path('/path/to/django'), 'python', '(try_statement) @try')
"
echo \$?  # 139 = SIGSEGV
```
