# Aletheore SQL Schema-Extraction Benchmark

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

## Methodology

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

### Part 1: real-repo stress test (Aletheore only)

For each repo, `aletheore.schema_map.extract_schema()` was run directly
against the real migration directory and the result inspected for: (a) any
exception, (b) the shape and content of every `unsupported` entry (is it a
legitimate, documented scope exclusion — views, triggers, GRANT/REVOKE,
CHECK constraints — or a real gap that should have been modeled), and (c)
spot-checks of specific tables against what the real migration history
should produce.

### Part 2: Aletheore vs. Repowise

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

## Results

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
