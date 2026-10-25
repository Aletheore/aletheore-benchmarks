#!/usr/bin/env python3
"""Ground-truth file-level import graph for Java and C# repos, independent of Aletheore.
usage: make_truth_jvmnet.py <java|csharp> <repo_dir> <out.json>

Files: every git-tracked .java / .cs file (git ls-files; falls back to a directory walk), tests included.
Edge a->b: file a depends on file b (in-repo, no self edges, deduplicated, sorted).

Java: javac's own parser (helper JavaScan.java, com.sun.source tree API) extracts package, imports, declared
  types, type parameters, identifiers in non-method-name position and qualified-name chains. Resolution follows JLS
  scoping: file-own declarations and type parameters shadow; single-type imports shadow same-package; same-package
  types are visible; on-demand (wildcard) imports only count for types actually used; static imports resolve to the
  declaring class file; fully-qualified inline names count. If several files declare the same FQN (separate source
  roots), the candidate in the same source root wins, then the longest common path prefix, then the larger root.
C#: Roslyn semantic model (helper CsScan, loads the SDK's Microsoft.CodeAnalysis). One compilation per .csproj
  (own files + transitive ProjectReference sources, net10.0 reference assemblies, SDK implicit usings, csproj/
  Directory.Build.props <Using> items as global usings). Every identifier/generic name is bound; an edge is added
  to every file declaring the referenced type (partial types: all parts), constructor targets, static members and
  extension methods (via their declaring type). `var` and unresolved (external NuGet) symbols are ignored.
Helpers live in ./truth_work_jvmnet/."""
import collections, json, os, re, sys
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(here, "../..")))
from _tools import run_tool

W = os.path.join(here, "truth_work_jvmnet")
lang, repo, out = sys.argv[1], os.path.abspath(sys.argv[2]), sys.argv[3]
ext = {"java": ".java", "csharp": ".cs"}[lang]


def tracked(e):
    try:
        r = run_tool(["git", "-C", repo, "ls-files", "-z"], capture_output=True, text=True, check=True)
        fs = [f for f in r.stdout.split("\0") if f]
        fs = [f for f in fs if os.path.isfile(os.path.join(repo, f))]
    except Exception:
        fs = []
        for dp, dn, fn in os.walk(repo):
            dn[:] = [d for d in dn if d not in (".git", ".aletheore", "bin", "obj")]
            fs += [os.path.relpath(os.path.join(dp, f), repo) for f in fn]
    return sorted(f for f in fs if f.endswith(e) and not f.startswith(".aletheore/"))


def common(a, b):
    n = 0
    for x, y in zip(a.split("/"), b.split("/")):
        if x != y:
            break
        n += 1
    return n


# ------------------------------------------------------------------ Java
def java():
    files = tracked(".java")
    lst = os.path.join(W, os.path.basename(repo) + ".java.list")
    open(lst, "w").write("\n".join(files) + "\n")
    p = run_tool(["java", os.path.join(W, "JavaScan.java"), repo, lst], capture_output=True, text=True, check=True)
    info = {}
    for line in p.stdout.splitlines():
        d = json.loads(line)
        info[d["f"]] = d
    assert set(info) == set(files), (len(info), len(files))
    perr = sum(1 for d in info.values() if d["errs"])
    # source roots
    root = {}
    for f, d in info.items():
        pk = d["pkg"].replace(".", "/")
        dn = os.path.dirname(f)
        root[f] = dn[: len(dn) - len(pk)].rstrip("/") if pk and dn.endswith(pk) else dn
    rsize = collections.Counter(root.values())
    fq = collections.defaultdict(set)  # fully-qualified top-level type -> files
    pk_types = collections.defaultdict(lambda: collections.defaultdict(set))
    for f, d in info.items():
        for t in d["tops"]:
            fq[(d["pkg"] + "." + t) if d["pkg"] else t].add(f)
            pk_types[d["pkg"]][t].add(f)
    stats = collections.Counter()

    def pick(a, cands):
        cands = set(cands)
        if len(cands) > 1:
            same = {b for b in cands if root[b] == root[a]}
            if same:
                cands = same
            else:
                m = max(common(a, b) for b in cands)
                cands = {b for b in cands if common(a, b) == m}
                if len(cands) > 1:
                    mx = max(rsize[root[b]] for b in cands)
                    cands = {b for b in cands if rsize[root[b]] == mx}
            if len(cands) > 1:
                stats["ambiguous_ties_kept_all"] += 1
            stats["ambiguous"] += 1
        return cands

    def resolve(name, a):
        """longest dotted prefix of name that is a top-level type FQN"""
        parts = name.split(".")
        for k in range(len(parts), 0, -1):
            q = ".".join(parts[:k])
            if q in fq:
                return pick(a, fq[q])
        return set()

    E = set()
    for f, d in info.items():
        own = set(d["decls"]) | set(d["tparams"])
        single = {}  # simple name -> files from single-type imports
        wild = []
        for imp in d["imports"]:
            kind, name = imp.split(" ", 1)
            if name.endswith(".*"):
                wild.append((kind == "S", name[:-2]))
                # import of a type's members/nested types (static or not): the declaring file; a pure package
                # wildcard resolves to nothing here and is handled by usage below
                for b in resolve(name[:-2], f):
                    E.add((f, b))
                continue
            bs = resolve(name, f)
            if kind == "N":
                single[name.rsplit(".", 1)[1]] = bs
            for b in bs:
                E.add((f, b))
        used = set(d["ids"]) - own
        # same-package types (not shadowed by own decls or a single-type import of that simple name)
        for t, bs in pk_types.get(d["pkg"], {}).items():
            if t in used and t not in single:
                for b in pick(f, bs):
                    E.add((f, b))
        # on-demand imports of packages: only for used, unshadowed simple names
        for static, pkgname in wild:
            if static:
                continue
            for t, bs in pk_types.get(pkgname, {}).items():
                if t in used and t not in single and t not in pk_types.get(d["pkg"], {}):
                    for b in pick(f, bs):
                        E.add((f, b))
        # fully qualified inline names
        for ch in d["chains"]:
            if "." not in ch:
                continue
            first = ch.split(".")[0]
            if first in own:
                continue
            parts = ch.split(".")
            for k in range(len(parts), 1, -1):
                q = ".".join(parts[:k])
                if q in fq:
                    for b in pick(f, fq[q]):
                        E.add((f, b))
                    break
        # simple-name chains through single imports are already covered by the import edge itself
    E = {(a, b) for a, b in E if a != b}
    return files, E, dict(stats, javac_parse_errors_files=perr)


# ------------------------------------------------------------------ C#
def csharp():
    files = tracked(".cs")
    fset = set(files)
    allf = run_tool(["git", "-C", repo, "ls-files", "-z"], capture_output=True, text=True).stdout.split("\0")
    csprojs = sorted(f for f in allf if f.endswith(".csproj") and os.path.isfile(os.path.join(repo, f)))
    props = {os.path.dirname(f): f for f in allf if os.path.basename(f) == "Directory.Build.props" and os.path.isfile(os.path.join(repo, f))}

    def usings_of(path):
        t = open(os.path.join(repo, path), errors="ignore").read()
        pl, st = [], []
        for m in re.finditer(r'<Using\s+Include="([^"]+)"([^>]*)/?>', t):
            (st if re.search(r'Static="true"', m.group(2), re.I) else pl).append(m.group(1))
        return pl, st, bool(re.search(r"<ImplicitUsings>\s*(enable|true)", t, re.I))

    projs = {}
    for c in csprojs:
        d = os.path.dirname(c)
        projs[d] = dict(id=d or ".", dir=d, csproj=c, files=[], refs=[])
    if not projs:
        projs[""] = dict(id=".", dir="", csproj=None, files=[], refs=[])
    for f in files:
        d = os.path.dirname(f)
        while d not in projs and d:
            d = os.path.dirname(d)
        projs.get(d, projs.get("", next(iter(projs.values()))))["files"].append(f)
    spec = []
    for d, p in projs.items():
        pl, st, imp = [], [], False
        if p["csproj"]:
            a, b, imp = usings_of(p["csproj"])
            pl += a; st += b
            t = open(os.path.join(repo, p["csproj"]), errors="ignore").read()
            for r in re.findall(r'ProjectReference\s+Include="([^"]+)"', t):
                tgt = os.path.normpath(os.path.join(d, os.path.dirname(r.replace("\\", "/"))))
                tgt = "" if tgt == "." else tgt
                if tgt in projs:
                    p["refs"].append(projs[tgt]["id"])
        pd = d
        while True:
            if pd in props:
                a, b, i2 = usings_of(props[pd]); pl += a; st += b; imp = imp or i2
            if not pd:
                break
            pd = os.path.dirname(pd)
        spec.append(dict(id=p["id"], files=p["files"], refs=p["refs"], usings=sorted(set(pl)), staticUsings=sorted(set(st)), implicit=imp))
    sp = os.path.join(W, os.path.basename(repo) + ".cs.spec.json")
    op = os.path.join(W, os.path.basename(repo) + ".cs.out.json")
    json.dump({"projects": spec}, open(sp, "w"))
    run_tool(["dotnet", os.path.join(W, "CsScan/out/CsScan.dll"), repo, sp, op], check=True)
    res = json.load(open(op))
    E = {(a, b) for a, bs in res.items() for b in bs if a != b and b in fset}
    return files, E, {"projects": len(spec)}


files, E, stats = java() if lang == "java" else csharp()
fs = set(files)
assert all(a in fs and b in fs and a != b for a, b in E)
json.dump({"files": files, "edges": [list(e) for e in sorted(E)]}, open(out, "w"), indent=0)
print(f"{lang} {os.path.basename(repo)}: files={len(files)} edges={len(E)} {stats}")
