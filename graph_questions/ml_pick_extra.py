"""Extra question kinds: locate (where is symbol X defined; regex truth, unique definitions only) and path
(a shortest import chain between two files; truth graph BFS). Usage: ml_pick_extra.py out.json repo [repo ...]"""
import collections, json, os, random, re, sys

S = os.path.dirname(os.path.abspath(__file__)) + "/"
sys.path.insert(0, S)
from ml_pick import LANGS, REPOS, Graph  # noqa: E402

N = r"([A-Za-z_]\w{5,})"
DEFS = {
    "go": [(rf"(?m)^func {N}\(", "function"), (rf"(?m)^type {N} (?:struct|interface)\b", "type")],
    "ts": [(rf"(?m)^export (?:default )?(?:abstract )?class {N}\b", "class"), (rf"(?m)^export (?:default )?(?:async )?function {N}\b", "function")],
    "java": [(rf"(?m)^\s*(?:public |protected |abstract |final |static )*(?:class|interface|enum) {N}\b", "type")],
    "csharp": [(rf"(?m)^\s*(?:public|internal)\s+(?:static |sealed |abstract |partial )*(?:class|interface|struct|enum|record) {N}\b", "type")],
    "rust": [(rf"(?m)^(?:pub(?:\([^)]*\))? )?(?:struct|enum|trait) {N}\b", "type"), (rf"(?m)^(?:pub(?:\([^)]*\))? )?fn {N}\(", "function")],
    "php": [(rf"(?m)^(?:abstract |final )?(?:class|interface|trait|enum) {N}\b", "type")],
    "ruby": [(rf"(?m)^\s*(?:class|module) {N}\b", "class or module")],
    "cpp": [(rf"(?m)^(?:class|struct) {N}\b", "type")],
}


def pick(repo, rng):
    lang_key = REPOS[repo]
    lang = LANGS[lang_key]
    TEST = lang["test"]
    root = S + repo
    g = Graph(repo)
    air = json.load(open(root + "/.aletheore/air.json"))
    known = {m["path"] for m in air["repository"]["modules"]}
    tasks = []

    def add(kind, target, **kw):
        tasks.append({"id": f"{repo}_{kind}_x{len(tasks)}", "repo": repo, "kind": kind, "target": target, **kw})

    # locate: names defined exactly once, in exactly one non-test file, anywhere in the tracked sources
    if lang_key in DEFS:
        where = collections.defaultdict(list)
        for f in g.files:
            try:
                text = open(os.path.join(root, f), errors="ignore").read()
            except OSError:
                continue
            for rx, word in DEFS[lang_key]:
                for m in re.finditer(rx, text):
                    where[m.group(1)].append((f, word))
        # a name that appears at all in a test file or twice is dropped
        uniq = [(n, v[0]) for n, v in where.items() if len(v) == 1 and not TEST.search(v[0][0]) and v[0][0] in known]
        rng.shuffle(uniq)
        for name, (f, word) in uniq[:3]:
            add("locate", name, truth_file=f, word=word)
    # path: pairs at forward distance 3 or 4 between non-test files
    cand = [f for f in g.files if f in known and not TEST.search(f) and g.fwd.get(f)]
    rng.shuffle(cand)
    n = 0
    for a in cand:
        if n >= 3:
            break
        dist, frontier, seen = {a: 0}, [a], {a}
        while frontier:
            nxt = []
            for x in frontier:
                for y in g.fwd.get(x, ()):
                    if y not in seen:
                        seen.add(y)
                        dist[y] = dist[x] + 1
                        nxt.append(y)
            frontier = nxt
        far = sorted(b for b, d in dist.items() if d in (3, 4) and not TEST.search(b) and b in known)
        if far:
            b = rng.choice(far)
            add("path", a, to=b, truth_len=dist[b])
            n += 1
    return tasks


if __name__ == "__main__":
    out, repos = sys.argv[1], sys.argv[2:]
    allt = []
    for r in repos:
        ts = pick(r, random.Random("x" + r))
        print(r, collections.Counter(t["kind"] for t in ts))
        allt += ts
    json.dump(allt, open(S + out, "w"), indent=1)
