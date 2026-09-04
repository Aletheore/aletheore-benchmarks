# SQL Schema-Extraction Benchmark — Results

Run date: 2026-09-04. First systematic real-repo validation of
`aletheore_database`'s schema extraction since it moved off a hand-written
Postgres tokenizer onto sqlglot, plus the first head-to-head against
Repowise's SQL handling.

## Part 1: real-repo stress test (Aletheore's own parser)

| Repo | Files scanned | Convention | Crashes | Real bugs found |
|---|---|---|---|---|
| cal.com | 595 | Prisma | 0 | 2 |
| supabase | 32 | Supabase CLI | 0 | 0 |
| coder | 589 (`.up.sql`) | golang-migrate | 0 | 1 |
| windmill | 636 (`.up.sql`) | Rust/sqlx | 0 | 0 (confirms round-1 fixes) |
| trigger.dev | 825 | Prisma (independent schema) | 0 | 0 (confirms round-1 fixes) |
| **Total** | **2,677** | | **0** | **3** |

### Bugs found and fixed

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

### What's left in `unsupported`, and why it's not a bug

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

## Part 2: Aletheore vs. Repowise

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

### Column-count comparison on real, verifiable tables

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

### Other capabilities Repowise's SQL handling has none of

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

## Bottom line

Repowise's SQL "support" is real in the sense that it doesn't crash and
extracts *something* — but it's a single-statement, single-file
`CREATE TABLE` name/column-list dump with no cross-migration replay, no
type information, no constraints, and no relations, indexes, renames, or
drops. On every repo tested it reported stale, sometimes years-out-of-date
schemas as current, with no signal that anything was missing. Aletheore
replays the full migration history to reconstruct the actual current
schema — verified directly against a real project's own maintained ground
truth (coder's `dump.sql`) — with types, primary keys, foreign keys
(`ON DELETE` included), indexes, and renames all correctly tracked.
