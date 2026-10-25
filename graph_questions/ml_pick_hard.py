"""Harder question kinds, where grep is expected to struggle.
hubs: the 5 most depended-on non-test files. cycles: find a circular dependency (or say none).
dupdef: every file defining a name that is defined in several files. callers / subclasses: from truth/<repo>_refs.json.
Usage: ml_pick_hard.py out.json repo [repo ...]"""
import collections, json, os, random, re, sys

S = os.path.dirname(os.path.abspath(__file__)) + "/"
sys.path.insert(0, S)
from ml_pick import LANGS, REPOS, Graph  # noqa: E402
from ml_pick_extra import DEFS  # noqa: E402

N = r"([A-Za-z_]\w{4,})"
DEFS = dict(DEFS)
DEFS["python"] = [(rf"(?m)^(?:async )?def {N}\(", "function"), (rf"(?m)^class {N}\b", "class")]


def sccs(nodes, fwd):
    index, low, on, stack, out, counter = {}, {}, set(), [], [], [0]
    sys.setrecursionlimit(100000)

    def strong(v):
        index[v] = low[v] = counter[0]
        counter[0] += 1
        stack.append(v)
        on.add(v)
        for w in fwd.get(v, ()):
            if w not in nodes:
                continue
            if w not in index:
                strong(w)
                low[v] = min(low[v], low[w])
            elif w in on:
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            comp = []
            while True:
                w = stack.pop()
                on.discard(w)
                comp.append(w)
                if w == v:
                    break
            out.append(comp)

    for v in nodes:
        if v not in index:
            strong(v)
    return out


def pick(repo, rng):
    lang_key = REPOS[repo]
    TEST = LANGS[lang_key]["test"]
    root = S + repo
    g = Graph(repo)
    air = json.load(open(root + "/.aletheore/air.json"))
    known = {m["path"] for m in air["repository"]["modules"]}
    cand = [f for f in g.files if f in known and not TEST.search(f)]
    candset = set(cand)
    tasks = []

    def add(kind, target, **kw):
        tasks.append({"id": f"{repo}_{kind}_h{len(tasks)}", "repo": repo, "kind": kind, "target": target, **kw})

    # hubs: top 5 by number of distinct non-test importers, only when the 5th and 6th differ
    deg = {f: len({i for i in g.rev.get(f, ()) if i in candset}) for f in cand}
    ranked = sorted(deg.items(), key=lambda kv: (-kv[1], kv[0]))
    for k in (5, 4, 3):
        if len(ranked) > k + 1 and ranked[k - 1][1] > ranked[k][1]:
            add("hubs", f"top{k}", k=k, truth=sorted(f for f, _ in ranked[:k]), degrees=[d for _, d in ranked[:k]])
            break
    # cycles: any strongly connected component of size >= 2 among non-test files
    comps = [c for c in sccs(candset, {f: [t for t in g.fwd.get(f, ()) if t in candset] for f in cand}) if len(c) >= 2]
    add("cycles", "cycles", has_cycle=bool(comps), largest=max((len(c) for c in comps), default=0))
    # dupdef: names defined in 2..6 distinct non-test files
    if lang_key in DEFS:
        where = collections.defaultdict(set)
        word_of = {}
        for f in cand:
            try:
                text = open(os.path.join(root, f), errors="ignore").read()
            except OSError:
                continue
            for rx, word in DEFS[lang_key]:
                for m in re.finditer(rx, text):
                    where[(m.group(1), word)].add(f)
        multi = [(k, sorted(v)) for k, v in where.items() if 2 <= len(v) <= 6]
        rng.shuffle(multi)
        for (name, word), files in multi[:2]:
            add("dupdef", name, word=word, truth=files)
    # callers and subclasses from the refs truth
    refs_path = f"{S}truth/{repo}_refs.json"
    if os.path.exists(refs_path):
        refs = json.load(open(refs_path))
        fns = []
        for fn in refs.get("functions", []):
            callers = sorted(c for c in fn["callers"] if c in candset)
            if fn["file"] in candset and 3 <= len(callers) <= 15:
                fns.append((fn, callers))
        rng.shuffle(fns)
        for fn, callers in fns[:3]:
            add("callers", fn["name"], file=fn["file"], word="function", truth=callers)
        cls = []
        for c in refs.get("classes", []):
            subs = sorted(s for s in c["subclasses"] if s in candset)
            if c["file"] in candset and 3 <= len(subs) <= 15:
                cls.append((c, subs))
        rng.shuffle(cls)
        for c, subs in cls[:3]:
            add("subclasses", c["name"], file=c["file"], word="class", truth=subs)
    return tasks


if __name__ == "__main__":
    out, repos = sys.argv[1], sys.argv[2:]
    allt = []
    for r in repos:
        ts = pick(r, random.Random("h" + r))
        print(r, dict(collections.Counter(t["kind"] for t in ts)))
        allt += ts
    json.dump(allt, open(S + out, "w"), indent=1)
