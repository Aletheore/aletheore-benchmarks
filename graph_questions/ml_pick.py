"""Task picker for the multi-language graph-question benchmark. Ground truth: truth/<repo>.json
({"files": [...], "edges": [[from, to], ...]}) built independently of Aletheore. Usage: ml_pick.py out.json repo [repo ...]"""
import collections, json, os, random, re, sys
S = os.path.dirname(os.path.abspath(__file__)) + "/"
sys.path.insert(0, S)
from _tools import run_tool

# one definition of "test file" per language, also stated in the prompts
LANGS = {
    "go": {"word": "Go", "test": re.compile(r"_test\.go$|(^|/)testdata/"),
           "testdef": "Test files are files named *_test.go or anything under a testdata/ directory.",
           "dep": "a file depends on another when it imports the package that contains that file, or, within the same package, "
                  "uses a name (function, type, variable, constant) that the other file declares"},
    "ts": {"verb": "imports", "word": "TypeScript/JavaScript", "test": re.compile(r"(^|/)(tests?|__tests__|spec)/|\.test\.|\.spec\.|(^|/)test[^/]*\.[cm]?[jt]sx?$"),
           "testdef": "Test files are any path containing a test/, tests/, __tests__/ or spec/ directory, or a file named *.test.* or *.spec.*.",
           "dep": "a file depends on another when it imports it (import, export-from, require or a literal dynamic import)"},
    "python": {"verb": "imports", "word": "Python",
               "test": re.compile(r"(^|/)(tests?|testing|__tests__|spec)/|_test\.|\.test\.|\.spec\.|(^|/)test_[^/]*$|/testdata/|conftest"),
               "testdef": "Test files are any path containing a tests/, test/ or testing/ directory, or a file named test_*.py or *_test.py, or conftest.py.",
               "dep": "a file depends on another when it imports it"},
    "java": {"word": "Java", "test": re.compile(r"(^|/)(tests?|testing)/|(Test|Tests|IT)\.java$|(^|/)Test[A-Z]\w*\.java$"),
             "testdef": "Test files are any path containing a test/ or tests/ directory, or a file named *Test.java, *Tests.java, *IT.java or Test*.java.",
             "dep": "a file depends on another when it imports a type that the other declares, or, within the same package, "
                    "uses a type that the other declares"},
    "csharp": {"word": "C#", "test": re.compile(r"(^|/)(tests?|[\w.]*\.Tests?)/|Tests?\.cs$"),
               "testdef": "Test files are any path under a tests/ directory or a *.Tests project directory, or a file named *Test.cs or *Tests.cs.",
               "dep": "a file depends on another when it imports a namespace and uses a type the other declares, or, within the same "
                      "namespace, uses a type that the other declares"},
    "rust": {"word": "Rust", "test": re.compile(r"(^|/)(tests?|benches|examples)/|_tests?\.rs$|(^|/)tests?\.rs$"),
             "testdef": "Test files are any path under a test/, tests/, benches/ or examples/ directory, or a file named *_test.rs, *_tests.rs or test.rs.",
             "dep": "a file depends on another when it declares it as a module (`mod x;`), or imports an item with `use` that the other defines"},
    "php": {"word": "PHP", "test": re.compile(r"(^|/)(tests?)/|Test\.php$"),
            "testdef": "Test files are any path under a test/ or tests/ directory, or a file named *Test.php.",
            "dep": "a file depends on another when it imports it with `use`, requires/includes it, or references a class, interface or "
                   "trait the other declares (resolved through the namespace)"},
    "ruby": {"word": "Ruby", "test": re.compile(r"(^|/)(tests?|spec)/|_(test|spec)\.rb$"),
             "testdef": "Test files are any path under a test/, tests/ or spec/ directory, or a file named *_test.rb or *_spec.rb.",
             "dep": "a file depends on another when it requires it (require, require_relative, autoload) or references a constant the other defines"},
    "c": {"word": "C", "test": re.compile(r"(^|/)(tests?)/|_test\.[ch]$"),
          "testdef": "Test files are any path under a test/ or tests/ directory, or a file named *_test.c.",
          "dep": "a file depends on another when it #includes it (a header's implementation file is not a dependency)"},
    "cpp": {"word": "C++", "test": re.compile(r"(^|/)(tests?)/|[-_]tests?\.(cc|cpp|cxx|h|hpp)$"),
            "testdef": "Test files are any path under a test/ or tests/ directory, or a file named *-test.cc or *_test.cc.",
            "dep": "a file depends on another when it #includes it (a header's implementation file is not a dependency)"},
}
REPOS = {"dj": "python", "erp": "python", "gin": "go", "zod": "ts", "axios": "ts", "gson": "java", "thrift": "java", "automapper": "csharp", "serde": "rust",
         "guzzle": "php", "slim": "php", "jekyll": "ruby", "jq": "c", "fmt": "cpp"}
DISPLAY = {r: r for r in REPOS}


class Graph:
    def __init__(self, repo):
        t = json.load(open(f"{S}truth/{repo}.json"))
        self.files = t["files"]
        self.fwd, self.rev = collections.defaultdict(set), collections.defaultdict(set)
        for a, b in t["edges"]:
            self.fwd[a].add(b)
            self.rev[b].add(a)

    def closure(self, start, edges):
        seen, stack = set(), [start]
        while stack:
            for p in edges.get(stack.pop(), ()):
                if p not in seen and p != start:
                    seen.add(p)
                    stack.append(p)
        return seen


def owners(root, f):
    out = run_tool(["git", "-C", root, "shortlog", "-sn", "--no-merges", "HEAD", "--", f], capture_output=True, text=True).stdout
    rows = [line.strip().split("\t", 1) for line in out.splitlines() if "\t" in line]
    return [(int(n), name) for n, name in rows]


def pick(repo, rng):
    lang = LANGS[REPOS[repo]]
    TEST = lang["test"]
    nt = lambda paths: {p for p in paths if not TEST.search(p)}  # noqa: E731
    root = S + repo
    g = Graph(repo)
    air = json.load(open(root + "/.aletheore/air.json"))
    known = {m["path"] for m in air["repository"]["modules"]}
    cand = [f for f in g.files if f in known and not TEST.search(f)]
    tasks = []

    def add(kind, target, **kw):
        tasks.append({"id": f"{repo}_{kind}_{len(tasks)}", "repo": repo, "kind": kind, "target": target, **kw})

    rng.shuffle(cand)
    n = 0
    for f in cand:
        d = nt(g.rev.get(f, ()))
        if 3 <= len(d) <= 15 and n < 5:
            add("direct", f, truth=sorted(d))
            n += 1
    for lo, hi in [(4, 12), (12, 35), (35, 100), (100, 5000)]:
        k = 0
        for f in cand:
            a = nt(g.closure(f, g.rev))
            if lo <= len(a) < hi and nt(g.rev.get(f, ())) and k < 1:
                add("size", f, truth_n=len(a))
                k += 1
    for lo, hi in [(4, 12), (12, 40), (40, 150)]:
        k = 0
        for f in cand:
            a = nt(g.closure(f, g.fwd))
            if lo <= len(a) < hi and k < 1:
                add("deps", f, truth_n=len(a))
                k += 1
    by_dir = collections.defaultdict(list)
    for f in cand:
        by_dir[os.path.dirname(f)].append(f)
    dirs = [d for d in by_dir if d]
    rng.shuffle(dirs)
    n = 0
    for d in dirs:
        members = [f for f in cand if f.startswith(d + "/")]
        dead = sorted(f for f in members if not nt(g.rev.get(f, ())))
        if 2 <= len(dead) <= 15 and len(members) >= len(dead) + 2 and n < 3:
            add("unreachable", d, truth=dead, members=len(members))
            n += 1
    n = 0
    for f in cand:
        if n >= 4:
            break
        o = owners(root, f)
        if len(o) >= 2 and o[0][0] >= 4 and o[0][0] >= 2 * o[1][0]:
            add("owner", f, truth_author=o[0][1], commits=o[0][0])
            n += 1
    return tasks


if __name__ == "__main__":
    out, repos = sys.argv[1], sys.argv[2:]
    allt = []
    for r in repos:
        # Seeded sampling is for repeatable benchmark task selection, not cryptography.
        ts = pick(r, random.Random(r))  # nosec B311
        print(r, collections.Counter(t["kind"] for t in ts))
        allt += ts
    json.dump(allt, open(S + out, "w"), indent=1)
