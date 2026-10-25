# Graph questions: grep vs Graphify vs Aletheore, 14 repositories, 12 languages

Questions an agent asks about the shape of a codebase: who imports this file, how many modules does a change reach, which files does nothing import, who owns this, where is this defined, which files are imported the most, is there a circular import. The same cheap model answers each one four or five ways, and every answer is scored against a ground truth built independently of Aletheore.

Everything below recomputes from the raw runs in this folder with no API key and no network:

```bash
python3 reproduce.py
```

## The arms

| Arm | What the agent gets |
|---|---|
| **A, grep** | Read, Grep and Glob only (plus `git log` and `git shortlog` for ownership questions) |
| **B, Aletheore router** | A, plus the `router` MCP profile: one tool, `aletheore_ask`, that picks the exact query |
| **C, Aletheore full** | A, plus the `full` MCP profile: 44 tools (semantic index built for locate questions) |
| **D, Graphify** | A, plus the Graphify CLI (`query`, `affected`, `path`, `explain`, `god-nodes`) over a prebuilt code-only graph, with a short note on its commands in the system prompt |
| **E, Graphify + LLM** | D, over a graph that also had Graphify's LLM pass over docs, papers and images (IndieRouter `deepseek-v4.1-flash`); built for 12 of the 14 repositories |

Every arm runs the same model through Claude Code (`claude -p`, `claude-haiku-5-5`), three repetitions per task, with the same prompt and the same tool permissions. Aletheore is the released code at master `9ab85687` (PRs #1115 and #1120), except that embeddings for arm C were built with the hosted index. Graphify is 0.9.50.

## The questions

| Kind | Question | Ground truth |
|---|---|---|
| direct | which non-test files directly import X | independent import graph |
| size | how many non-test files does a change to X reach (transitively) | same graph, within 10% |
| deps | how many non-test files does X depend on (transitively) | same graph, within 10% |
| unreachable | which non-test files under a directory does nothing import | same graph |
| owner | who has the most commits on X | `git shortlog` |
| locate | in which file is the function or class `Name` defined | a definition regex, names defined exactly once |
| path | give a shortest chain of imports from A to B | the graph, valid and minimal |
| hubs | which K non-test files are imported by the most others | the graph, only where rank K and K+1 differ |
| cycles | is there a circular dependency; give one | strongly connected components of the graph |
| dupdef | every file defining a name that is defined in several files | the definition regex |
| callers | which files contain a direct call to function F defined in file G | type-resolved: `go/types`, the TypeScript checker, `javac`, Python `ast` |
| subclasses | which files define a type inheriting from T, directly or through others | same resolvers |

A list is correct only if it is exactly the truth set. Test files are defined by one regex per language, stated in each prompt. 14 repositories (Django, ERPNext, gin, zod, axios, gson, thrift, automapper, serde, guzzle, slim, jekyll, jq, fmt). Tasks are in the `*_tasks_*.json` files; the first run used the Python and the 12-repository sets, the later ones added the locate and path, and the hard sets.

## Ground truth

The import graph for each language is built by that language's own tooling, never by Aletheore: the Python `ast` module (Django, ERPNext); `go list` plus `go/types` (gin); the TypeScript compiler API with workspace `exports` resolution (zod, axios); `javac`'s parser with Java's scoping rules, and Roslyn's semantic model (gson, thrift, automapper); a Rust resolver over `cargo metadata` (serde); include resolution (jq, fmt); PHP's tokenizer with Composer autoload maps (guzzle, slim); Ruby `require` and autoload resolution (jekyll). The builders are in `truth/scripts/`, the graphs in `truth/`. Where the independent graph and Aletheore's disagree, that is reported below, not hidden: it is the reason some Aletheore rows lose points.

## Results

Accuracy is the share of tasks answered correctly (each task is the mean of its three repetitions). The bracket is a 95% task-level bootstrap interval for the difference from grep.

### The questions that need the whole graph

| Set | Tasks | Grep | Router | Full | Graphify |
|---|---|---|---|---|---|
| Python: Django, ERPNext | 44 | 0.64 | **0.89** [+0.14, +0.36] | **0.88** [+0.11, +0.37] | 0.55 [-0.15, -0.01] |
| 12 other repositories, 9 more languages | 192 | 0.74 | **0.88** [+0.10, +0.18] | **0.89** [+0.11, +0.19] | 0.74 [-0.04, +0.05] |

(the brackets are the difference from grep; Graphify is not distinguishable from grep on the 192 tasks and is below it on Python.)

By question kind, across the 192 tasks of the second row:

| Kind | Tasks | Grep | Router | Full | Graphify |
|---|---|---|---|---|---|
| blast radius (`size`) | 31 | 0.59 | **0.95** | **0.95** | 0.52 |
| direct importers | 58 | 0.79 | 0.83 | 0.83 | 0.79 |
| dependency counts | 34 | 0.85 | 0.84 | 0.88 | 0.81 |
| unreachable files | 21 | 0.70 | 0.71 | 0.73 | 0.73 |
| ownership | 48 | 0.71 | 0.99 | 0.98 | 0.78 |

Ownership is inflated for the router and full (see "Harness artifacts" below). With ownership removed (144 tasks): grep 0.75, router 0.84, full 0.85, Graphify 0.73. **The clear, robust win is blast radius: grep reaches 0.59 because it has to chase imports file by file, and the graph answers it exactly.**

By language (same 192 tasks, ownership included):

| Language | Tasks | Grep | Router | Full | Graphify |
|---|---|---|---|---|---|
| TypeScript / JavaScript | 37 | 0.74 | 0.95 | 0.95 | 0.81 |
| PHP | 34 | 0.89 | 0.99 | 1.00 | 0.90 |
| Rust | 14 | 0.83 | 0.95 | 0.98 | 0.71 |
| Java | 36 | 0.79 | 0.89 | 0.88 | 0.77 |
| C# | 17 | 0.75 | 0.86 | 0.86 | 0.80 |
| Ruby | 15 | 0.53 | 0.78 | 0.82 | 0.56 |
| Go | 14 | 0.64 | 0.79 | 0.79 | 0.67 |
| C++ | 12 | 0.64 | 0.78 | 0.81 | 0.47 |
| C | 13 | 0.51 | 0.59 | 0.62 | 0.51 |

### Cost and tokens

Per run, the benchmark agent's own usage (input tokens include cached reads):

| Set | | Grep | Router | Full | Graphify |
|---|---|---|---|---|---|
| Python (44 tasks) | input tokens | 70,900 | **27,800** | 80,700 | 57,300 |
| | cost per correct answer | $0.0083 | **$0.0017** | $0.0023 | $0.0066 |
| 12 other repositories (192 tasks) | input tokens | 84,300 | **41,800** | 100,700 | 83,900 |
| | cost per correct answer | $0.0079 | **$0.0027** | $0.0037 | $0.0069 |

The router uses 40 to 50% of grep's input tokens and costs a fifth to a third as much per correct answer, at higher accuracy. The full profile is as accurate as the router but reads more input, because its 44 tool definitions are sent on every turn (about 19,000 tokens before the agent has done anything). Input tokens for the full profile exceed grep's; its cost per correct answer is still lower.

Setup is separate and not in these numbers. On ERPNext, `aletheore scan` took 35 s (with the vulnerability, licence, schema, endpoint and static-analysis passes off, as in these runs) and the hosted semantic index 143 s for 15,149 chunks, using the concurrent-embedding change that is still an open PR ([#1121](https://github.com/Aletheore/Aletheore/pull/1121)); the earlier local-Ollama index of the same repository took about 19 minutes (see `../graphify_comparison/README.md`). Graphify's code-only extraction took about a minute. Graphify's LLM extraction over the docs of 12 repositories cost roughly Rs 300 in IndieRouter credit, about three times what we estimated beforehand (the model bills reasoning tokens as output, and Graphify re-sends chunks it has to split).

### Questions where grep should struggle, and did not

| Set | Tasks | Grep | Router | Full | Graphify | Graphify + LLM |
|---|---|---|---|---|---|---|
| where is X defined / shortest import chain | 69 | 0.90 | 0.87 | 0.93 | 0.89 | 0.90 |
| hubs, cycles, duplicate names, callers, subclasses | 67 | 0.84 | 0.82 | 0.85 | 0.79 | n/a (53 tasks: 0.82) |

**No tool beats grep on these.** Locating a uniquely named symbol and finding callers by name take grep one or two searches. Circular imports in these repositories were short and easy to find. Graphify's LLM layer (docs and papers only; code stays plain AST) changes nothing for questions about code structure (E minus D +0.01).

**Graphify's LLM mode did not beat Aletheore's deterministic graph, which has no LLM extraction step and no per-token price for it.** We ran Graphify with its LLM pass in the two sets above (12 of the 14 repositories; Django and ERPNext were skipped because their documentation is very large). On where-is-X-defined / shortest-import-chain (69 tasks) it scored 0.90 against 0.93 for Aletheore full and 0.87 for the router; on the hard set (the 53 tasks it covers) 0.82 against 0.82 for full and 0.81 for the router. Level or behind, for an extraction that cost roughly Rs 300 across the repositories and took from half a minute to 22 minutes per repository (Aletheore's scan took 3 to 35 seconds; the optional semantic index, a few cents of embeddings). The LLM pass adds nodes for documents, papers and images; none of these questions are about those, so a better test of Graphify's LLM mode would be questions about what the documentation says, which we did not run.

The one kind that separated anything was "which K files are imported by the most others": grep 0.49, router 0.38, full 0.54, Graphify 0.31. Nobody could do it well. The router did not know the question; the agents with full looped over `imported_by` file by file (53 calls in one sample). That is the gap the next section closes.

### Fixes measured on unreleased code

These come from branches that are not in a release: smaller MCP tool definitions and a new `lean` profile ([#1127](https://github.com/Aletheore/Aletheore/pull/1127)), and router answers for "most imported files" and "circular imports" (PR linked from the repository when merged). Same tasks, same model, so treat the "after" rows as what the release will be measured against, not as released numbers.

51 base tasks (importers, blast radius, dependency counts, unreachable, ownership; 12 repositories):

| | Accuracy | vs grep | Input tokens | Cost per correct |
|---|---|---|---|---|
| Grep | 0.71 | n/a | 64,700 | $0.0052 |
| Graphify | 0.77 | +0.06 [-0.01, +0.12] | 70,800 | $0.0047 |
| Router, before | 0.91 | +0.20 [+0.10, +0.29] | 37,800 | $0.0019 |
| Router, after | 0.90 | +0.18 [+0.09, +0.28] | 38,000 | $0.0021 |
| Full, before | 0.90 | +0.19 [+0.10, +0.29] | 96,700 | $0.0027 |
| **Full, after** (28% smaller definitions) | 0.91 | +0.20 [+0.10, +0.30] | **76,800** | $0.0024 |
| **Lean** (new profile, 9 tools) | **0.93** | +0.22 [+0.12, +0.32] | 52,200 | $0.0025 |

27 hard tasks (most-imported files and circular imports; 14 repositories):

| | Accuracy | vs grep | Input tokens | Cost per correct |
|---|---|---|---|---|
| Grep | 0.75 | n/a | 174,500 | $0.0174 |
| Graphify | 0.60 | -0.15 [-0.27, -0.04] | 210,200 | $0.0279 |
| Router, before | 0.70 | -0.05 [-0.12, +0.04] | 139,200 | $0.0145 |
| **Router, after** | **0.86** | **+0.11 [+0.01, +0.25]** | 97,300 | **$0.0075** |
| Full, before | 0.78 | +0.02 [-0.05, +0.12] | 242,700 | $0.0166 |
| Full, after | 0.85 | +0.10 [0.00, +0.21] | 171,400 | $0.0111 |
| **Lean** | **0.89** | **+0.14 [+0.02, +0.27]** | 100,300 | **$0.0075** |

The smaller definitions cut the full profile's input by 20,000 tokens per run (-21%, interval -26,100 to -14,400) with no change in accuracy; a direct probe of the first-turn context agrees (25.8k to 21.0k). The 27-task set is small, so its intervals are wide: the router gain is real but its lower bound is +0.01.

## Where we lose

- **C is not improved by Aletheore** (grep 0.51, router 0.59, full 0.62; 13 tasks). Includes are textual and the reference graph treats every `#if` branch as live, so the questions themselves are noisy there. Ruby is weak for everyone (0.53 to 0.82), and Aletheore's Jekyll graph has 0.89 recall against the reference.
- **Direct importers, dependency counts and unreachable files are a tie.** On these, grep is already about as good as the graph tools.
- **Where grep finds the answer in one or two searches, nothing beats it** (locate, callers by name, short cycles).
- **Graphify was never reliably better than grep**: in every set its difference from grep is negative or inside the noise (its best case is +0.06, interval -0.01 to +0.12, on the 51 base tasks; it is below grep on Python and on the hard set). It ran in code-only mode with a short note on its commands; its LLM mode adds documentation nodes only. That is a statement about these questions and this setup, not about everything Graphify is for.
- **The router cannot answer callers or subclasses questions** (the scan has no call graph to answer them from) and, until the fixes above ship, hubs and cycles.
- **Three Aletheore graphs differ from the reference** in ways that cost it points: gin (build-tag variants are kept as alternatives; precision 0.87, recall 0.98), automapper (the Roslyn reference skips member-only references and non-default `#if` branches; precision 0.85), thrift (the reference covers only the Java files of a multi-language repository). Two gin dependency-count questions and the Jekyll misses are from this.

## Harness artifacts and corrections

- **Ownership scores for grep and Graphify are understated.** `git shortlog` without a revision waits on stdin; piped git commands were refused by the permission list. After fixing both, 31 of 144 grep ownership runs (22%) and 21 of 144 Graphify ownership runs (15%) across the three sets were still refused, against 3 of 144 for the Aletheore arms. On runs that produced an answer: grep 0.85 to 0.97, Graphify 0.79 to 1.00, Aletheore 0.97 to 1.00. Do not read the ownership gap as a tool difference.
- **Session-limit results were purged and rerun.** A run that hit the Claude session limit returns the limit message as its "answer"; 262 + 205 such results were detected, removed and rerun. Four results damaged by a network outage were removed the same way (`purge_bad.py`, `check_bad.py`).
- **An earlier measurement of the smaller definitions was contaminated** by a second process rewriting the shared MCP config files. The runner now keys its config files by source tree, and the figures above are from the clean repeat.
- **The router source changed mid-way.** The router's wording fix was copied into the benchmark tree partway through the multi-language batches. It affects only questions phrased with "depends on", which the Python, Go and TypeScript prompts do not use, so we treat the effect as small, but the early and late runs did not use byte-identical router code.
- **Claude Code updated itself during one run** and removed the `claude` binary for a few minutes; 212 invocations failed and were rerun.

## Earlier write-ups where Graphify was ahead (not re-run)

Two results published earlier in this repository ([`../graphify_comparison/`](../graphify_comparison/README.md)) show Graphify ahead. Both were measured before the changes described above, and **neither has been re-run**. We expect both to look better now, but that is an expectation, not a measurement.

- **Setup time.** Graphify's whole extract, embeddings included, took about a minute on ERPNext. Aletheore's `scan` plus a separate local `index` took about 20 minutes (the scan was brought down to 53 s in 0.9.5; the index, local Ollama embeddings, stayed at about 19 minutes). What has changed since: indexing through the hosted endpoint with concurrent batches took 143 s on the same repository in this benchmark (an open PR, [#1121](https://github.com/Aletheore/Aletheore/pull/1121), not yet in a release), and the scan took 35 s. That is a few minutes in total against about a minute, with the caveat that the hosted path uploads code chunks to the embedding endpoint and needs a token; the local path is unchanged. We have not re-run the setup comparison itself.
- **Live MCP tools: "tell me everything about this symbol".** In the live-server comparison ([`mcp_efficiency/`](../graphify_comparison/mcp_efficiency/README.md)) Graphify was cheaper in raw tokens on flat symbol dumps, because it returns less. Part of Aletheore's per-query cost in that comparison is the size of the tool definitions sent on every turn, which [#1127](https://github.com/Aletheore/Aletheore/pull/1127) cuts by 28% and the `lean` profile it adds cuts by about 76% (the router profile's single tool is under a twentieth of the full profile's definitions). We have not re-run those four queries.

## Scope and honesty

The questions are graph-shaped and we chose them, one cheap model answers them, Graphify ran in code-only mode, the repositories are small to medium, and each language has one or two repositories (Ruby, C, C++, Rust and C# have one each). The callers and subclasses truth exists for four repositories only (18 tasks). This is evidence that a deterministic import graph answers whole-graph questions that grep only samples, and that it costs fewer tokens to do so. It is not evidence about open-ended questions, other models, or other tools' strengths.

## Files

| | |
|---|---|
| `reproduce.py` | extracts `runs/` and recomputes every table above |
| `runs/*.tar.gz` | the 4,830 raw per-run results (answer, turns, tokens, cost) in six archives |
| `*_tasks_*.json` | the task sets, with ground truth |
| `truth/` | the independent graphs (`<repo>.json`), caller and subclass truth (`*_refs.json`), and `truth/scripts/` that build them (these assume the language toolchains installed: go, node with typescript, javac and dotnet, cargo, php, ruby; paths may need adjusting) |
| `ml_pick*.py` | task pickers per question kind |
| `ml_run.py` | the runner (needs Claude Code and, for arms B and C, an Aletheore checkout; `ML_EHR` selects the source tree) |
| `ml_score2.py`, `publish_numbers.py` | scorers |
| `gfy_llm.py`, `embed_index.py` | Graphify LLM extraction and hosted index build |
| `check_bad.py`, `purge_bad.py`, `gq_purge_limit.py` | contamination checks used before scoring |
