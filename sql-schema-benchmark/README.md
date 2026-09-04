# Aletheore SQL Schema-Extraction Benchmark

Measures two things about `aletheore_database`'s schema extraction
(`src/aletheore/schema_map.py`, which recently moved from a hand-written
Postgres DDL tokenizer to sqlglot — see that repo's commit history for the
rewrite itself):

1. **Real-repo robustness** of the parser/replay engine — run against real,
   large migration histories to find crashes and mis-modeled/silently-dropped
   SQL that a small hand-written test suite wouldn't exercise.
2. **A head-to-head against Repowise**, a competitor code-intelligence tool
   that also claims SQL support, on the same real repos.

Both scanners are fully deterministic (no LLM calls on Aletheore's side);
Repowise was run with `--index-only`, which explicitly skips its LLM-based
wiki generation, so this comparison has no paid-API cost on either side.

## Methodology

Five real, independent open-source repos were chosen specifically for
**different migration-tooling conventions**, to avoid the result being an
artifact of one ORM's SQL style:

| Repo | Real `.sql` migration files | Convention |
|---|---|---|
| [calcom/cal.com](https://github.com/calcom/cal.com) | 595 | Prisma-generated |
| [supabase/supabase](https://github.com/supabase/supabase) | 32 (of the real ones found readable) | Supabase CLI |
| [coder/coder](https://github.com/coder/coder) | 589 (`.up.sql` only) | golang-migrate |
| [windmill-labs/windmill](https://github.com/windmill-labs/windmill) | 636 (`.up.sql` only) | Rust/sqlx |
| [triggerdotdev/trigger.dev](https://github.com/triggerdotdev/trigger.dev) | 825 | Prisma-generated (independent schema from cal.com) |

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
`.repowise/wiki.db`'s `wiki_symbols` table was queried directly for every
row where `file_path LIKE '%.sql'`, and specific known tables were compared
column-for-column against Aletheore's replayed output for the same table.
Reading Repowise's actual stored index rather than its CLI `search`
command matters here: `search` queries LLM-generated wiki pages, which
`--index-only` explicitly skips (0 pages, confirmed via `repowise status`)
— the raw symbol table is what actually reflects what its indexer parsed
out of the SQL, independent of whether documentation was ever written
about it.

## Results

See `REPORT.md` for the full numbers and per-repo findings.

**Headline, Part 1:** zero crashes across all 2,677 real files scanned
(595+32+589+636+825). Three real gaps found and fixed in the first pass
across cal.com and coder; a second pass on windmill and trigger.dev
(different tooling conventions again) confirmed no further gaps, and
supabase was clean on both passes — a real signal the fixes generalize
rather than being repo-specific patches.

**Headline, Part 2:** Repowise's SQL "support" is per-file, per-statement
`CREATE TABLE` extraction with no cross-migration replay — it does not
process `ALTER TABLE`, `DROP TABLE`, or `RENAME` at all. On every repo
tested, a real table's Repowise-reported column list matched only that
table's *original* `CREATE TABLE` statement, missing everything added
since — in some cases years and 70+ migrations of drift. It never once
extracted a foreign key, an index, or a `PRIMARY KEY`/`UNIQUE` constraint
from any of the 622 real `.sql` files it extracted at least one symbol
from, across all 5 repos (grepped its full stored index for
`REFERENCES`/`FOREIGN KEY`/`PRIMARY KEY` in every extracted signature -
zero real hits). It also has no way to know a table was renamed or
dropped: windmill renamed its real `queue` table to `v2_job_queue` (now 46
columns) and replaced `queue` with a view of the same name for backward
compatibility — Repowise still reports the stale, years-old `queue`
*table* definition (22 columns) as current, alongside a separate,
unlabeled `queue` VIEW symbol, with nothing connecting the two. cal.com
creates and later drops `platform_access_tokens` (10 days apart, in two
real migrations) — Repowise still lists it as a live symbol.
