# Scanner language coverage

Every language the scanner claims to support, verified with controlled two-file
fixtures (each defining a function, a class, a module-level constant, and
importing across files) plus eight real repositories. Deterministic — no LLM.

Reproduce: `python3 scripts/lang_coverage_matrix.py`

## Current state — all 13 languages

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

## RepoWise comparison: dead-code detection

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

## What was broken, measured on real repositories

### CommonJS: empty dependency graph

`_extract_javascript` handled only ESM `import_statement`, never `require()`.

| expressjs/express | before | after |
|---|---|---|
| modules with resolved imports | **0 / 141** | 125 / 141 |
| import edges | **0** | 159 |
| clusters | 141 | 27 |
| singleton clusters | **141 / 141** | 4 / 27 |

A full AIRview build would have made 141 LLM calls to describe 141 one-file
"subsystems".

### JavaScript: assigned function expressions were not symbols

Only `function f(){}` and `class C{}` counted, but Express defines its entire
surface as `app.use = function use(fn) {...}`.

| expressjs/express | before | after |
|---|---|---|
| files with zero symbols | 102 / 141 | 86 / 141 |
| functions extracted | ~0 in lib/ | 231 |

Now covers `const f = () => {}`, `exports.f = function(){}` and
`Foo.prototype.bar = function(){}`.

### Rust: two silent failures

`serde-rs/serde` scanned as **208 modules, 0 import edges, 208 singleton clusters.**

1. `_rust_crate_root` only checked `<repo>/src/lib.rs`, so **Cargo workspaces** —
   serde, tokio, rust-analyzer, most large Rust projects — resolved nothing.
2. `mod foo;` was not treated as an edge, though it is how a crate declares its
   module tree. A crate whose `lib.rs` is all `mod` statements had no edges.

After: **25 of 33 crate-source files resolve imports.** The remaining 151 files
are integration tests that `use serde::` across a crate boundary, where zero is
correct.

### C#: flat projects resolved nothing

`_csharp_prefix_and_root_for` required at least one trailing namespace segment
to match a real directory, so a project whose namespace comes entirely from
`<RootNamespace>` with no mirroring folders contributed nothing to the prefix
map. Now falls back to treating the whole namespace as an implicit prefix rooted
at the file's own directory.

### Module-level constants: Python only

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

## Not a defect

- **C reports no classes.** C has none.
- **PHP requires a PSR-4-compliant layout** (one class per file, named after the
  class). An earlier draft of this register listed PHP as broken; that was a
  non-compliant fixture, not a scanner bug — corrected after verification.
- **Header declarations are not definitions**, so header-only C/C++ libraries
  under-report functions.

## Still open

- Clusters that are entirely tests or docs still get a subsystem and an LLM call
  (7 of 12 on Flask, 150 of 208 on serde).
- Singleton clusters remain common in repos whose test files import nothing.
- Retrieval and wiki quality have been **measured only on Flask**. The scores in
  METHODOLOGY.md are a property of that one Python repo, not of the product, and
  must not be quoted as cross-language numbers.
