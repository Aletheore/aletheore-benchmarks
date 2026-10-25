"""Multi-language graph-question A/B/C/D. Usage: ml_run.py REPS [task_filter|all] [arms]; env ML_TASKS, ML_OUT."""
import hashlib, json, os, random, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, S + "")
from ml_pick import LANGS, REPOS, S  # noqa: E402

EHR = os.environ.get("ML_EHR", S + "ehr")  # Aletheore source tree the MCP servers import (default: merged master)
MODEL = os.environ.get("AB_MODEL", "claude-haiku-5-5")
BUDGET = os.environ.get("AB_BUDGET", "0.60")
TASKS = {t["id"]: t for t in json.load(open(S + os.environ.get("ML_TASKS", "ml_tasks_ts.json")))}
OUT = os.environ.get("ML_OUT", "ml_out")
PY = "/opt/miniconda3/bin/python3"


def mcp_conf(repo, profile):
    args = ["-m", "aletheore.cli", "mcp", S + repo, "--profile", profile, "--yes"] + (["--no-watch"] if profile == "full" else [])
    # keyed by the source tree: two processes with different ML_EHR must not overwrite each other's server config
    tag = hashlib.sha256(EHR.encode()).hexdigest()[:8]
    path = f"{S}ml_mcp_{tag}_{repo}_{profile}.json"
    json.dump({"mcpServers": {"aletheore": {"command": PY, "args": args, "env": {"PYTHONPATH": EHR + "/src"}}}}, open(path, "w"))
    return path


CONF = {(r, a): mcp_conf(r, p) for r in REPOS for a, p in (("B", "router"), ("C", "full"), ("L", "lean"))}  # L: the lean profile
PROMPTS = {
    "direct": "List every NON-TEST {word} source file that directly depends on `{target}` ({dep}; ignore string references). "
              "{testdef} Answer with ONE JSON array of repo-relative paths and nothing else.",
    "size": "If `{target}` changed, how many NON-TEST {word} source files would be affected through dependencies, directly or "
            "transitively ({dep}; files that depend on it, or on something that depends on it, and so on)? {testdef} "
            "Give your best estimate. Answer with ONE JSON object {{\"count\": N}} and nothing else.",
    "deps": "How many NON-TEST {word} source files does `{target}` depend on, directly or transitively ({dep}; the files it depends on, "
            "the files those depend on, and so on, within this repository)? {testdef} Give your best estimate. "
            "Answer with ONE JSON object {{\"count\": N}} and nothing else.",
    "unreachable": "Under the directory `{target}` (including subdirectories), list the NON-TEST {word} source files "
                   "that no other source file in the repository depends on ({dep}; ignore string references). {testdef} "
                   "Answer with ONE JSON array of repo-relative paths and nothing else.",
    "owner": "Who has made the most commits touching `{target}`? Use the git history (git log / git shortlog on that file; "
             "always pass an explicit revision such as `git shortlog -sn HEAD -- <file>`, because shortlog without one waits "
             "for input). Answer with ONE JSON object {{\"author\": \"Full Name\"}} and nothing else.",
    "locate": "In which {word} source file is the {sym} `{target}` defined? Answer with ONE JSON object "
              "{{\"file\": \"repo-relative/path\"}} and nothing else.",
    "hubs": "Which {k} NON-TEST {word} source files are depended on by the MOST other NON-TEST source files ({dep})? {testdef} "
            "Answer with ONE JSON array of exactly {k} repo-relative paths, most depended-on first, and nothing else.",
    "cycles": "Is there a circular dependency among the NON-TEST {word} source files of this repository ({dep})? {testdef} "
              "If there is, answer with ONE JSON array of the files forming one cycle in order (each file depends on the next, and the "
              "last depends on the first); if there is none, answer []. Answer with the JSON array and nothing else.",
    "dupdef": "List every NON-TEST {word} source file that defines a {sym} named `{target}` (the name is defined in several files). "
              "{testdef} Answer with ONE JSON array of repo-relative paths and nothing else.",
    "callers": "Which NON-TEST {word} source files contain a direct call to the {sym} `{target}` that is defined in `{file}`? "
               "Do not count the defining file itself. {testdef} Answer with ONE JSON array of repo-relative paths and nothing else.",
    "subclasses": "List every NON-TEST {word} source file that defines a type inheriting from (extending, implementing or embedding) `{target}`, "
                  "defined in `{file}`, either directly or through other types. Do not count the defining file itself. {testdef} "
                  "Answer with ONE JSON array of repo-relative paths and nothing else.",
    "path": "Starting from `{target}`, find a SHORTEST chain of direct dependencies that reaches `{to}` ({dep}). Answer with ONE JSON array of "
            "repo-relative paths that starts with `{target}` and ends with `{to}`, where each file directly depends on the next, "
            "using as few files as possible, and nothing else.",
}


IMPORT_PROMPTS = {
    "direct": "List every NON-TEST {word} source file that directly imports `{target}` ({dep}; ignore string references). "
              "{testdef} Answer with ONE JSON array of repo-relative paths and nothing else.",
    "size": "If `{target}` changed, how many NON-TEST {word} source files would be affected through imports, directly or transitively "
            "(files that import it, or import something that imports it, and so on)? {testdef} Give your best estimate. "
            "Answer with ONE JSON object {{\"count\": N}} and nothing else.",
    "deps": "How many NON-TEST {word} source files does `{target}` depend on through imports, directly or transitively (files it imports, "
            "the files those import, and so on, within this repository)? {testdef} Give your best estimate. "
            "Answer with ONE JSON object {{\"count\": N}} and nothing else.",
    "unreachable": "Under the directory `{target}` (including subdirectories), list the NON-TEST {word} source files, "
                   "that no other source file in the repository imports (an import statement; ignore string references). {testdef} "
                   "Answer with ONE JSON array of repo-relative paths and nothing else.",
}


def question(t):
    lang = LANGS[REPOS[t["repo"]]]
    prompts = {**PROMPTS, **IMPORT_PROMPTS} if lang.get("verb") == "imports" else PROMPTS
    q = prompts[t["kind"]].format(target=t["target"], testdef=lang["testdef"], word=lang["word"], dep=lang["dep"],
                                  to=t.get("to", ""), sym=t.get("word", ""), file=t.get("file", ""), k=t.get("k", 5))
    return f"This repository ({t['repo']}, {lang['word']}) is in the current directory. " + q


def run(tid, arm, rep):
    out = f"{S}{OUT}/{tid}_{arm}_{rep}.json"
    if os.path.exists(out):
        return json.load(open(out))
    os.makedirs(S + OUT, exist_ok=True)
    t = TASKS[tid]
    if arm == "E" and not os.path.exists(f"{S}gfy_llm_{t['repo']}/graphify-out/graph.json"):
        return {"id": tid, "arm": arm, "rep": rep, "skipped": "no LLM-mode Graphify graph for this repo"}
    prompt = question(t)
    tools = "Read,Grep,Glob" + (",Bash" if t["kind"] == "owner" or arm in ("D", "E") else "")
    # read-only pipe utilities, so a piped `git shortlog ... | head` is not denied for the arms that must use git
    pipes = [f"Bash({c}:*)" for c in ("sort", "uniq", "head", "tail", "cut", "awk", "wc", "grep", "tr")]
    allowed = ["Read", "Grep", "Glob"] + (["Bash(git log:*)", "Bash(git shortlog:*)", *pipes] if t["kind"] == "owner" else [])
    if arm in ("D", "E"):
        allowed += ["Bash(graphify:*)"] + (["Bash(git log:*)", "Bash(git shortlog:*)"] if t["kind"] != "owner" else [])
    argv = ["claude", "-p", prompt, "--model", MODEL, "--setting-sources", "project", "--strict-mcp-config",
            "--permission-mode", "dontAsk", "--output-format", "json", "--no-session-persistence", "--max-budget-usd", BUDGET,
            "--tools", tools]
    if arm in ("B", "C", "L"):
        argv += ["--mcp-config", CONF[(t["repo"], arm)]]
        allowed += ["mcp__aletheore"]
    if arm in ("D", "E"):
        # D: code-only graph; E: the same extraction plus Graphify's LLM pass over docs (deepseek-v4.1-flash)
        g = f"{S}gfy_{'llm_' if arm == 'E' else ''}{t['repo']}/graphify-out/graph.json"
        argv += ["--append-system-prompt",
                 "A code knowledge graph of this repository is prebuilt. Query it with the graphify CLI via Bash: "
                 f"`graphify query \"<question>\" --graph {g}`, `graphify affected \"<file or symbol>\" --graph {g} [--depth N]` "
                 f"(reverse traversal: what depends on it), `graphify path \"A\" \"B\" --graph {g}`, "
                 f"`graphify explain \"X\" --graph {g}`, `graphify god-nodes --graph {g}`."]
    argv += ["--allowedTools", *allowed]
    t0 = time.time()
    r = subprocess.run(argv, cwd=S + t["repo"], capture_output=True, text=True, timeout=1500)
    rec = {"id": tid, "arm": arm, "rep": rep, "rc": r.returncode, "seconds": round(time.time() - t0)}
    try:
        d = json.loads(r.stdout)
        u = d.get("usage") or {}
        rec.update(result=d.get("result"), turns=d.get("num_turns"), cost_usd=d.get("total_cost_usd"), subtype=d.get("subtype"),
                   in_tokens=u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0) + u.get("cache_creation_input_tokens", 0),
                   out_tokens=u.get("output_tokens", 0))
    except ValueError:
        rec["raw"] = (r.stdout + r.stderr)[-400:]
    json.dump(rec, open(out, "w"), indent=1)
    return rec


def per_task(args):
    tid, reps, arms = args
    rng = random.Random(tid)
    for rep in range(1, reps + 1):
        order = list(arms)
        rng.shuffle(order)
        for arm in order:
            try:
                r = run(tid, arm, rep)
                print(tid, arm, rep, "turns", r.get("turns"), r.get("subtype"), flush=True)
            except Exception as exc:
                print(tid, arm, rep, "ERROR", exc, flush=True)


if __name__ == "__main__":
    reps = int(sys.argv[1])
    flt = sys.argv[2].split(",") if len(sys.argv) > 2 and sys.argv[2] != "all" else list(TASKS)
    arms = sys.argv[3] if len(sys.argv) > 3 else "ABCD"
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(per_task, [(t, reps, arms) for t in flt]))
    print("done")
