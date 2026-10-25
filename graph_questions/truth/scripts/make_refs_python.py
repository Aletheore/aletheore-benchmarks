"""Independent callers / subclasses ground truth for a Python repo (stdlib ast only).
usage: make_refs_python.py <repo_dir> <out.json>"""
import ast, collections, json, os, subprocess, sys

repo, out = os.path.abspath(sys.argv[1]), sys.argv[2]
try:
    files = [f for f in subprocess.run(["git", "ls-files", "*.py"], cwd=repo, capture_output=True, text=True, check=True).stdout.split("\n") if f]
except Exception:
    files = [os.path.relpath(os.path.join(b, n), repo) for b, ds, ns in os.walk(repo) if ".git" not in b.split(os.sep) for n in ns if n.endswith(".py")]
files = [f for f in files if os.path.isfile(os.path.join(repo, f))]


def dotted(rel):
    p = rel[:-3].split("/")
    if p[-1] == "__init__":
        p = p[:-1]
    return ".".join(p)


mod = {dotted(f): f for f in files}

trees = {}
for f in files:
    try:
        trees[f] = ast.parse(open(os.path.join(repo, f), encoding="utf-8", errors="replace").read())
    except (SyntaxError, ValueError):
        pass

# definition census (any nesting level) so a name match is unambiguous
census = collections.Counter()
modlevel = {}
for f, t in trees.items():
    for n in ast.walk(t):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            census[n.name] += 1
    for n in t.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            modlevel.setdefault(n.name, []).append((f, "f"))
        elif isinstance(n, ast.ClassDef):
            modlevel.setdefault(n.name, []).append((f, "c"))

# per-file imports: module files imported, and {local name: module files it may come from}
imp_mods = {}
imp_names = {}
for f, t in trees.items():
    pkg = dotted(f).split(".")
    if not f.endswith("__init__.py"):
        pkg = pkg[:-1]
    mods, names = set(), collections.defaultdict(set)
    for n in ast.walk(t):
        if isinstance(n, ast.Import):
            for a in n.names:
                parts = a.name.split(".")
                for i in range(1, len(parts) + 1):
                    m = mod.get(".".join(parts[:i]))
                    if m:
                        mods.add(m)
        elif isinstance(n, ast.ImportFrom):
            if n.level:
                keep = len(pkg) - (n.level - 1)
                base = ".".join((pkg[:keep] if keep > 0 else []) + ([n.module] if n.module else []))
            else:
                base = n.module or ""
            bm = mod.get(base)
            if bm:
                mods.add(bm)
            for a in n.names:
                sub = mod.get(f"{base}.{a.name}" if base else a.name)
                if sub:
                    mods.add(sub)
                names[a.asname or a.name].update(x for x in (bm, sub) if x)
    imp_mods[f] = mods
    imp_names[f] = names

# importing a package also exposes what its __init__ re-exports (followed transitively)
def effective(f):
    s = {f} | set(imp_mods.get(f, ()))
    st = list(s)
    while st:
        g = st.pop()
        if g.endswith("__init__.py"):
            for h in imp_mods.get(g, ()):
                if h not in s:
                    s.add(h)
                    st.append(h)
    return s


eff = {f: effective(f) for f in trees}

funcs, classes = {}, {}
for name, defs in modlevel.items():
    if len(name) >= 6 and census[name] == 1 and len(defs) == 1:
        (funcs if defs[0][1] == "f" else classes)[name] = defs[0][0]

callers = collections.defaultdict(set)
for f, t in trees.items():
    for n in ast.walk(t):
        if isinstance(n, ast.Call):
            nm = n.func.id if isinstance(n.func, ast.Name) else n.func.attr if isinstance(n.func, ast.Attribute) else None
            if nm in funcs and funcs[nm] != f and funcs[nm] in eff[f]:
                callers[nm].add(f)

# class graph over ALL classes (any name); bases resolved through imports
allcls = collections.defaultdict(list)
for f, t in trees.items():
    for n in ast.walk(t):
        if isinstance(n, ast.ClassDef):
            allcls[n.name].append(f)
parents = collections.defaultdict(set)
for f, t in trees.items():
    for n in ast.walk(t):
        if not isinstance(n, ast.ClassDef):
            continue
        for b in n.bases:
            bn = b.id if isinstance(b, ast.Name) else b.attr if isinstance(b, ast.Attribute) else None
            if not bn:
                continue
            cands = [g for g in allcls.get(bn, []) if g == f or g in eff[f]]
            if isinstance(b, ast.Name) and bn in imp_names[f]:
                ex = set()
                for s in imp_names[f][bn]:
                    ex |= effective(s)
                cands = [g for g in cands if g in ex or g == f] or cands
            if len(set(cands)) == 1:
                parents[(f, n.name)].add((cands[0], bn))
children = collections.defaultdict(set)
for c, ps in parents.items():
    for p in ps:
        children[p].add(c)

res_c = []
for name, f in sorted(classes.items()):
    node = (f, name)
    direct = {c[0] for c in children.get(node, ())}
    seen, st = set(), [node]
    while st:
        for c in children.get(st.pop(), ()):
            if c not in seen:
                seen.add(c)
                st.append(c)
    subs = {c[0] for c in seen} - {f}
    if subs:
        res_c.append({"name": name, "file": f, "direct": sorted(direct - {f}), "subclasses": sorted(subs)})
res_f = [{"name": n, "file": funcs[n], "callers": sorted(c)} for n, c in sorted(callers.items())]
json.dump({"functions": res_f, "classes": res_c}, open(out, "w"), indent=1)
print(len(files), "files;", len(res_f), "functions;", len(res_c), "classes")
