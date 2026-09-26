# A differential-testing baseline, run on Graphify's own claimed technique — not Graphify itself

Graphify's headline PR-review claim ("prove it or break it") is **differential testing**: run
old vs. new code on generated inputs, either see identical behavior every time or hand back the
exact diverging input as a runnable counterexample. We wanted to test that claim against the same
24-case corpus `../../pr_review/`'s Aletheore/PR-Agent/DeepSource/Sourcery/Greptile comparison
already uses (`benchmarks/pr-review-benchmark/cases/` in `Aletheore/Aletheore`).

**We could not run Graphify's actual verifier.** We installed the real, current `graphifyy` package
(0.9.68, PyPI) and grepped its entire source for "verify"/"differential" — the only hits are an
unrelated internal guard about incomplete semantic extraction. The differential-verification
feature described on graphify.com is not in the open-source package at all; it exists only inside
Graphify's hosted enterprise product, which (as of this run) has no self-serve install — the
GitHub App isn't listed anywhere a free/individual account can find it, consistent with the
"early access" wording on their own pricing page.

So this directory does **not** benchmark Graphify. It builds our own minimal differential-testing
harness — the same technique they describe — and runs it on the same corpus, to answer a
narrower, honest question: **on real regressions small enough to isolate, does differential
testing (as a technique, independent of whose product implements it) actually catch what it
claims to catch, and where does the technique itself have structural blind spots?**

Never cite this as "Graphify's score." It isn't their code, and this is not a claim about their
implementation quality — only about what the technique they describe can and cannot see.

## Corpus scoping

24 cases: 15 `real_bug_fix` + 5 `injected_bug` + 4 `clean` (`ground_truth.yaml`'s own `category`
field, one query away — see below). Every case is a real historical bug fix from a real upstream
project (flask, requests, click, axios, express, lodash, cobra, gin, gorilla/mux, urfave/cli,
gson, junit4, commons-lang), reconstructed by pinning the repo at the real fix commit
(`repo.txt`'s `base_commit`, which equals `ground_truth.yaml`'s `fix_reference`) and applying
`pr.diff`, which **reverses** that fix — so in every case, "old" (the diff's `-` side) is the
correct/fixed code and "new" (the diff's `+` side) is the reintroduced historical bug. This
matters for the harness below: it always diffs old-correct against new-buggy, matching the real
historical regression.

```
cd Aletheore/Aletheore/benchmarks/pr-review-benchmark/cases
for d in */; do d="${d%/}"; [ -f "$d/ground_truth.yaml" ] || continue
  awk -F': ' '/^category:/{print $2}' "$d/ground_truth.yaml"
done
```

## Results

| case | category | technique used | result |
|---|---|---|---|
| 001-flask-cli-key-quote | real_bug_fix | plain I/O diff (exception message) | **DIVERGED** |
| 002-requests-json-decode-pickle | real_bug_fix | plain I/O diff (pickle round-trip) | **DIVERGED** |
| 003-requests-proxy-bypass-registry | real_bug_fix | plain I/O diff | **DIVERGED** |
| 004-click-version-package-name | real_bug_fix | plain I/O diff (mocked `importlib.metadata`) | **DIVERGED** |
| 005-axios-progress-negative-clamp | real_bug_fix | plain I/O diff | **DIVERGED** |
| 006-express-content-length-transfer-encoding | real_bug_fix | plain I/O diff (stubbed response) | **DIVERGED** |
| 007-lodash-omit-array-clone | real_bug_fix | plain I/O diff | **DIVERGED** |
| 008-axios-headers-set-cookie | real_bug_fix | plain I/O diff | **DIVERGED** |
| 009-cobra-completions-args-mutation | real_bug_fix | **side-effect check** (post-call state of the caller's own array, not the return value) | **DIVERGED** |
| 010-gin-runfd-file-leak | real_bug_fix | **resource-lifecycle check** (is the fd actually closed?) | **DIVERGED** — *but a naive return-value-only diff finds nothing; see below* |
| 011-gorilla-mux-query-match | real_bug_fix | *not attempted* | — |
| 012-urfave-cli-empty-positional-arg | real_bug_fix | plain I/O diff | **DIVERGED** |
| 013-gson-jsonprimitive-hashcode | real_bug_fix | plain I/O diff (long beyond double's exact-integer range) | **DIVERGED** |
| 014-junit4-assumption-serialization | real_bug_fix | plain I/O diff (real `ObjectOutputStream` serialization) | **DIVERGED** |
| 015-commons-lang-bitfield-sign-extension | real_bug_fix | plain I/O diff | **DIVERGED** |
| 016-flask-sql-injection-user-lookup | injected_bug | — | **not applicable** (new function, no "old" version exists) |
| 017-commons-lang-arrayutils-off-by-one | injected_bug | — | **not applicable** (new function) |
| 018-axios-missing-null-check-charset | injected_bug | — | **not applicable** (new function) |
| 019-gin-request-counter-race | injected_bug | — | **not applicable to a sequential test** (real bug is a data race; only observable under concurrent execution + a race detector, not input/output comparison) |
| 021-requests-swallowed-close-exception | injected_bug | — | **not applicable** (new method) |
| 022–025 (4 clean cases) | clean | — | **true negative by construction** (docs/test-name/javadoc only — no production code changed) |

**13 of 15 real_bug_fix cases attempted; all 13 diverged correctly** (one, 010, only with an
enhanced check — see below). 1 (011, gorilla/mux) skipped: faithfully reconstructing its full
route-matching state machine (matcher interfaces, `RouteMatch`, `routeRegexp` types) was judged too
failure-prone for a quick harness to attempt honestly, so it's reported as untested rather than
guessed at.

Full runnable code for every case above: `harness/`.

## Two structural findings, not implementation bugs

**Differential testing that only compares return values misses side-effect and resource bugs.**
Case 010 (`gin-runfd-file-leak`) removes a `defer f.Close()` — no return value anywhere differs
between old and new. A test that only diffs outputs reports "identical" and misses a real leak.
The DIVERGED result above only came from writing a second, explicit check — does the file
descriptor end up closed? — layered on top of plain I/O comparison. Case 009
(`cobra-completions-args-mutation`) is the same pattern in reverse: the return value is identical,
but the caller's own backing array gets silently corrupted through slice aliasing, invisible
unless the harness inspects the caller's argument state after the call, not just what the function
handed back. **A real differential verifier needs to check post-call state, not only return
values, to catch either class of bug** — worth knowing before taking "prove it or break it" to
mean "runs the code and compares outputs," which alone would have missed both of these.

**Differential testing cannot see a bug in code that didn't exist before.** All 5 `injected_bug`
cases (016–019, 021) turned out, on inspection of the real diffs, to be **brand-new functions or
methods**, not modifications to existing ones — a SQL-injection-vulnerable query builder, an
off-by-one array helper, a missing-null-check regex extractor, a request counter, a quiet-close
method, all added whole in the diff under review. Differential testing is definitionally a
comparison of an old version against a new version; when there is no old version, there is nothing
to diverge from, and the technique cannot flag the bug at all, regardless of how good the
verifier's input generation is. This is a real, category-level blind spot for any tool whose
review mechanism is fundamentally "diff the behavior of two versions of the same code" — it has no
purchase on new code, which is precisely where injected/introduced bugs often live. (019's bug is
a further wrinkle: the modified `ServeHTTP` function *does* have an old/new pair, but the bug is a
data race that only manifests under concurrent execution — a single-threaded input/output
comparison would report no divergence either way, and catching it needs Go's race detector or
similar, not a plain diff.)

## What this does and doesn't say

This is evidence that **differential testing, as a technique, correctly flags real single-function
regressions** on the cases where it structurally applies (13/13 attempted here) — a genuinely
different and complementary detection mechanism from Aletheore's evidence-grounded LLM review,
which works on the diff's prose/structure rather than executing anything. It is *not* evidence
about Graphify's own product, which we could not access, and it is not a claim that this harness's
13 reconstructions are as rigorous as a real fuzzer's input generation (each uses a small,
hand-picked set of interesting inputs per case, not property-based/random search over a large input
space — a real gap next to how Graphify describes their own verifier's input generation).

It also is not evidence differential testing alone is *sufficient* for PR review: it has zero
purchase on the 4 clean cases (nothing to say, correctly), zero purchase on new-code bugs (a real,
structural class), and needs deliberate side-effect/resource checks beyond naive I/O comparison to
catch two of the fifteen real cases here. A verifier of this kind is a real complement to
evidence-grounded review, not a replacement for it.
