# SQL Schema-Extraction Benchmark — Results

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

## Part 1b: real-repo stress test, ORM-native migrations (Aletheore's own parser)

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

### What's left in `unsupported`, and why

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

## Part 2a: Aletheore vs. Repowise, raw `.sql` migrations

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

## Part 2b: Aletheore vs. Repowise, ORM-native migrations

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

## Bottom line

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
