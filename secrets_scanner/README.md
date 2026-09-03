# Head-to-head against RepoWise: secrets detection

RepoWise has its own hardcoded-credential detection
(`repowise/core/analysis/security_scan.py`, part of a broader
"security signals" scanner covering `eval()`, SQL injection shapes, weak
hashes, etc.), not previously compared against `aletheore_secrets`
anywhere in this repository. This directory runs both scanners
ourselves, in-process, on the same inputs — a synthetic pilot corpus
with exact-match ground truth, and 20 real open-source repos (21,430
files) for a real-world false-positive check neither tool's synthetic
test suite can provide.

**We call RepoWise's `SecurityScanner.scan_file()` directly**, the same
class its own ingestion pipeline (`repowise/core/pipeline/persist.py`)
wires in — RepoWise exposes no CLI command or MCP tool for this scan
(confirmed by reading its `cli/main.py` command list and grepping every
call site of `SecurityScanner` in the installed package); `repowise
init` runs it as a side effect and persists to a database table with no
query command. `session=None` is safe here: only `.persist()` touches
the DB, and this benchmark never calls it. Same principle
`scripts/run_aletheore.py` elsewhere in this repo already uses
(`from aletheore.search_index import search_index`, in-process, no
subprocess) — no framework overhead, no CLI-output parsing.

## Result

| | RepoWise 0.27.0 | Aletheore 0.9.10 (PyPI, current release) | Aletheore @ `355bd98` (dev HEAD) |
|---|---|---|---|
| **Pilot corpus recall** (6 true positives) | **1/6** | 6/6 | 6/6 |
| **Pilot corpus false positives** (5 true negatives) | 0/5 | 4/5 | **0/5** |
| **Real-repo findings** (20 repos, 21,430 files) | 375 | 92 raw / 77 reported | 96 raw / **21 reported** |
| **Real-repo true positives found** (manually verified, see below) | **0** | not independently re-verified | not independently re-verified |

RepoWise misses 5 of 6 real credential formats in the pilot corpus
outright — its only two credential patterns
(`password\s*=\s*['\"]`, `(?:api_?key|secret)\s*=\s*['\"]`) are
**compiled case-sensitively** with no `re.IGNORECASE`, so
`AWS_ACCESS_KEY_ID = "..."`, `GITHUB_TOKEN = "..."`, `GOOGLE_MAPS_API_KEY
= "..."` never match a lowercase-only regex, and there's no
vendor-format detection at all (no AWS/GitHub/Slack/Google key shapes),
so it only caught the one case whose variable name happened to be
`stripe.api_key` (lowercase). On real code this is the dominant naming
convention it's blind to — `AWS_ACCESS_KEY_ID`, `API_KEY`, `SECRET_KEY`,
`DB_PASSWORD` are the standard uppercase env-var/settings convention in
real `.env`/settings files, not the exception.

**Every one of RepoWise's 375 real-repo findings sampled and manually
checked was noise, not a real secret** — see "Real-repo findings, spot
checked" below. RepoWise's two patterns require nothing beyond a literal
quote after `password =` / `secret =` / `api_key =`: no length floor
(matches `password = ''`), no entropy check, no placeholder-value
recognition, no test-path awareness. Django's own auth test suite alone
produced 365 of the 375 — `password="secret"`, `password="test"`,
`password="testpw"`, sampled at random, all real lines, all rated "high
severity." Aletheore's `_is_likely_placeholder` (see the root repo's
`src/aletheore/secrets.py`) exists specifically to distinguish this from
a real leak; RepoWise has no equivalent, at any severity level.

## Pilot corpus: what each row is

Ported from `Aletheore/Aletheore`'s own
`benchmarks/security-scanner-benchmark/secrets/` (11 cases: 6 real
credential formats, 5 false-positive shapes found and fixed via that
repo's own real-repo validation work — case IDs and fixture contents
copied as-is, so this comparison uses the exact same, already-reviewed
ground truth, not a new corpus built to flatter either tool):

```
$ .venv-aletheore-pypi/bin/python3 scripts/score.py results/real_repos_repowise.json results/aletheore_pypi.json results/aletheore_fixed.json
```

| case_id | repowise | aletheore 0.9.10 | aletheore 355bd98 |
|---|---|---|---|
| 001-aws-access-key | FN | TP | TP |
| 002-github-token | FN | TP | TP |
| 003-stripe-key | TP | TP | TP |
| 004-slack-token | FN | TP | TP |
| 005-google-api-key | FN | TP | TP |
| 006-uuid-not-a-secret | TN | TN | TN |
| 007-private-key-header | FN | TP | TP |
| 008-test-tls-certificate | TN | FP | TN |
| 009-property-reference-not-a-secret | TN | FP | TN |
| 010-truncated-example-not-a-secret | TN | FP | TN |
| 011-pem-header-boilerplate-no-body | TN | FP | TN |

The `aletheore 0.9.10` column is the currently-published PyPI release —
it correctly detects every real format (private_key_header's pattern
already existed) but has 4 known false-positive bugs, all fixed in
`Aletheore/Aletheore#527` (open at the time of this run, not yet
released — installed here straight from that commit via
`pip install git+...@355bd98#subdirectory=src` into an isolated venv,
**not** from this machine's local dev checkout, which is shared with
other work and not a stable pin). Once #527 ships, `aletheore 0.9.10`'s
column becomes the `355bd98` column for every future reader who just
runs `pip install aletheore`.

## Real-repo findings, spot checked

Same 20 repos as `Aletheore/Aletheore`'s own
`benchmarks/security-scanner-benchmark/real-repo-validation/` (11
reused from there directly, 9 more covering ecosystems that work didn't
touch) — not re-selected for this comparison. Every RepoWise finding
sampled was manually opened and read (not inferred from the finding's
own `snippet` field, which RepoWise truncates but does not redact —
see "A note on RepoWise's output" below):

- **Django, 365/375 of all findings**: 12 sampled at random (all
  `tests/`-path `hardcoded_password`), all confirmed
  `password="secret"` / `password="test"` / `password="testpw"` —
  literal fake test credentials.
- **axios**: `parsedURL.password = '';` (`lib/adapters/fetch.js:279`,
  real product code, not a test) — an **empty string** assignment to a
  URL object's password field, not a secret. RepoWise's pattern has no
  minimum length.
- **okhttp**: `val password = "password".toCharArray()`
  (`TlsUtil.kt:33`) — the JDK/Android standard default keystore
  password (literally the word "password"), a widely-documented
  convention, not a leak.
- **RestSharp**: `const string password = "testpassword";` — a test
  fixture.
- **flask, gin**: same pattern, test fixtures and docs examples.

**Zero of the sampled RepoWise findings were a real secret.** Aletheore
(both versions) found zero real secrets in these repos either — see
`Aletheore/Aletheore`'s own real-repo report for the two real findings
that run *did* surface (committed TLS test certificates in axios and
gin, correctly not a leak either). No repo in this set had an actual
leaked credential in either tool's output.

## A note on RepoWise's output

`SecurityScanner.scan_file()` returns a `snippet` field (the matched
line, truncated to 120 chars) alongside each finding — unlike
Aletheore's salted-hash `match_preview`, this is the **live line text,
unredacted**. `results/real_repos_repowise.json` in this directory
strips it (only `path`/`line`/`kind` are kept) specifically so this
repository never publishes a real credential value if one is ever
found; every line above was independently re-read from the actual
downloaded repo tree during review, never taken from RepoWise's own
snippet.

## Running

```bash
# Aletheore side needs its own venv (aletheore requires Python <3.14):
python3.12 -m venv .venv-aletheore-pypi && .venv-aletheore-pypi/bin/pip install aletheore pyyaml

# RepoWise side must run under RepoWise's own installed interpreter -
# its sqlalchemy version conflicts with other environments.
<repowise's python> scripts/run_repowise.py > results/repowise.json
.venv-aletheore-pypi/bin/python3 scripts/run_aletheore.py > results/aletheore_pypi.json

# Real-repo run: fetch the same 20 repos this used (see
# Aletheore/Aletheore's benchmarks/security-scanner-benchmark/real-repo-validation/fetch_repos.sh),
# then:
<repowise's python> scripts/run_real_repos.py /path/to/repos --tool repowise > results/real_repos_repowise.json
.venv-aletheore-pypi/bin/python3 scripts/run_real_repos.py /path/to/repos --tool aletheore > results/real_repos_aletheore_pypi.json

# Score:
.venv-aletheore-pypi/bin/python3 scripts/score.py results/repowise.json results/aletheore_pypi.json
```

## Contents

| path | what |
|---|---|
| `cases/` | 11-case pilot corpus, ported verbatim from `Aletheore/Aletheore`'s own benchmark |
| `scripts/run_aletheore.py` | calls `aletheore.secrets.find_secrets` in-process |
| `scripts/run_repowise.py` | calls `repowise.core.analysis.security_scan.SecurityScanner.scan_file` in-process |
| `scripts/run_real_repos.py` | same two scanners against a directory of real repos |
| `scripts/score.py` | scores any set of result JSONs against `cases/*/ground_truth.yaml`, no API key |
| `scripts/fixtures.py` | placeholder→fake-secret expansion (copied from the source benchmark — see its own docstring for why fixtures store placeholders, not literal values) |
| `results/` | raw output this README's numbers were computed from |
