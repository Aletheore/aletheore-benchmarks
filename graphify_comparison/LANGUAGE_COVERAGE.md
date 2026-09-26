# Language coverage vs Graphify (structural, controlled fixtures)

Reuses the exact same 14 fixture variants (13 languages, JavaScript split
ESM/CommonJS) as the parent repo's own `../LANGUAGE_COVERAGE.md`, which
grades Aletheore's scanner the same way — so both tools are graded on
identical, minimal, two-file input: a module defining a function, a
class/struct, and a module-level constant, imported and called from a
second file. This is a different, narrower question than
`README.md`'s ERPNext run in this same directory (real-world QA coverage on
one large Python repo) — this file asks "does the graph contain the right
nodes and edges at all," across every language Aletheore claims to support.

**Tool tested:** `graphifyy` 0.9.68 (PyPI, installed 2026-09-26 via
`pip install graphifyy` into a clean venv — the exact command
`graphify_comparison/README.md` already documents). Recorded here because
the existing README's ERPNext run didn't pin a version; Graphify ships
multiple releases a week, so any re-run of this file should update this
line.

Reproduce: `GRAPHIFY_BIN=/path/to/graphify python3 scripts/graphify_lang_coverage_matrix.py`
— deterministic, no LLM, no API key (`--code-only` local AST extraction
only). Raw `graph.json` for every language is saved to `lang_coverage/raw/`
so every cell below is independently checkable.

## Results

| language | functions | classes | constants | cross-file link |
|---|---|---|---|---|
| python | ✅ 2/2 | ✅ 2/2 | ❌ 0/2 | ✅ |
| javascript (ESM) | ✅ 2/2 | ✅ 2/2 | ✅ 2/2 | ✅ |
| javascript (CommonJS) | ✅ 2/2 | ✅ 2/2 | ❌ 0/2 | ✅ |
| typescript | ✅ 2/2 | ✅ 2/2 | ✅ 2/2 | ✅ |
| go | ✅ 2/2 | ✅ 2/2 | ❌ 0/2 | ✅ |
| rust | ✅ 2/2 | ✅ 2/2 | ✅ 2/2 | ❌ |
| java | ✅ 2/2 | ✅ 2/2 | ❌ 0/2 | ✅ |
| ruby | ✅ 2/2 | ✅ 2/2 | ❌ 0/2 | ❌ |
| php | ✅ 2/2 | ✅ 2/2 | ❌ 0/2 | ✅ |
| c | ✅ 1/1 | n/a | ❌ 0/1 | ✅ |
| cpp | ✅ 1/1 | ✅ 2/2 | ❌ 0/2 | n/a |
| csharp | ✅ 2/2 | ✅ 2/2 | ❌ 0/2 | ✅ |
| kotlin | ✅ 2/2 | ✅ 2/2 | ❌ 0/2 | ✅ |
| swift | ✅ 2/2 | ✅ 2/2 | ❌ 0/2 | ✅ |

For comparison, Aletheore's own scanner (`../../LANGUAGE_COVERAGE.md`)
scores ✅ on imports, functions, classes, *and* constants across all 13
languages on this same fixture shape (c correctly reports "n/a" on
classes, matching the row above).

## Two real, verified findings

**Module-level constants are invisible to Graphify's graph in 11 of 14
variants.** `CONST_VALUE`/`MAIN_CONST` (or their per-language spelling)
never appear as nodes in Python, CommonJS, Go, Java, Ruby, PHP, C, C++,
C#, Kotlin, or Swift output — confirmed by grepping every node's
`norm_label` in the raw `graph.json`, not inferred. The exception is real
too: JavaScript ESM, TypeScript, and Rust *do* create constant nodes
(`const_value`/`main_const`), so this isn't "Graphify doesn't model
constants" as a design choice — it's an inconsistent extractor, present
for 3 languages and silently absent for the other 11. Practical
consequence: an agent asking Graphify's graph "who reads this constant"
or "where is this feature-flag threshold defined" gets no node to query
against, for most languages, even though the source line is right there.

**Two languages fail to link the cross-file reference at all**, despite
extracting both symbols individually:

- **Rust**: `src/lib.rs`'s `pub fn run() -> i32 { helper::help() }` calls
  `src/helper.rs`'s `help()` through the `pub mod helper;` declaration —
  both functions appear as correct, separate nodes, but no edge of any
  kind (`calls`, `imports`, `imports_from`) connects them. The module
  boundary itself produced zero linkage.
- **Ruby**: `main.rb`'s `require_relative 'mod'` plus a bare call to
  `helper` (Ruby's real top-level-method-visibility rule — no explicit
  qualification needed) produces **no edge between the two files at all**
  — not even one recognizing the `require_relative` statement itself.

Every other language (including C and C++, where nothing *should* link
since `helper()` is declaration-only) resolved correctly.

## Caveats

- **Controlled 2-file fixtures, not real repositories.** This isolates
  the graph-construction question cleanly, but doesn't say how these
  gaps play out on a real, large, multi-thousand-file codebase — a
  question this directory's ERPNext run (Python only) partially answers
  and a genuine multi-language real-repo run would answer better. Flagged
  as a possible follow-up, not done here.
- **`_callable`/`_callable_class` flags are not reliable classifiers** on
  their own — Go, Rust, and C#'s inner nodes often carry neither flag
  despite being real functions/classes. The script classifies by matching
  each node's `norm_label` against the exact identifiers the fixture
  defines (safe here because the fixtures are ours), not by flag alone;
  see the script's own docstring.
- **Unpinned tool, fast-moving upstream.** `graphifyy` ships several PyPI
  releases a week (0.9.68 as of this run). A re-run next month could
  land on different numbers in either direction — that's why the exact
  version is recorded above instead of left implicit.
