#!/usr/bin/env python3
"""Independent ground-truth file-level dependency graph.
usage: make_truth_rustc.py <rust|c|cpp> <repo_dir> <out.json>
Output {"files": [...], "edges": [[from,to],...]}, repo-relative, sorted, deduped, no self/dangling edges.
rust: own lexer + mod-tree builder (cargo metadata for crate roots/workspace deps); edges from `mod x;`,
      use/inline paths (crate/self/super/workspace crates, following pub use re-exports to the defining file,
      zero-arg item macros expanded), and include!("file").
c/cpp: #include "x"/<x> resolved against includer dir, repo include dirs, then unique path-suffix match among
      tracked files; only repo-tracked files; comments stripped; all #if branches counted (no preprocessing).
Tracked files = VCS file list (falls back to os.walk)."""
import json, os, re, sys, collections
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _tools import run_tool
mode, REPO, OUT = sys.argv[1], os.path.realpath(sys.argv[2]), sys.argv[3]
R = REPO
EXTS = {"rust": (".rs",), "c": (".c", ".h"), "cpp": (".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".inl")}[mode]

def tracked():
    r = run_tool(["git", "-C", REPO, "ls-files", "-z"], capture_output=True, text=True)
    if r.returncode == 0 and r.stdout:
        fl = [f for f in r.stdout.split("\0") if f]
    else:
        fl = []
        for dp, dn, fn in os.walk(REPO):
            dn[:] = [d for d in dn if d not in (".git", ".aletheore", "target", "node_modules")]
            fl += [os.path.relpath(os.path.join(dp, f), REPO) for f in fn]
    return sorted(f for f in fl if f.endswith(EXTS) and os.path.isfile(os.path.join(REPO, f)))

FILES = tracked()
FS = set(FILES)

if mode == "rust":
    # ---------------- lexer ----------------
    IDENT = re.compile(r"(?:r#)?[A-Za-z_][A-Za-z0-9_]*")
    def lex(src):
        i, n, out = 0, len(src), []
        while i < n:
            c = src[i]
            if c.isspace(): i += 1; continue
            if src.startswith("//", i):
                j = src.find("\n", i); i = n if j < 0 else j; continue
            if src.startswith("/*", i):
                d = 1; i += 2
                while i < n and d:
                    if src.startswith("/*", i): d += 1; i += 2
                    elif src.startswith("*/", i): d -= 1; i += 2
                    else: i += 1
                continue
            m = re.match(r'(?:b?r)(#*)"', src[i:i + 12])
            if m and (c == "r" or src[i:i+2] == "br"):
                h = m.group(1); end = '"' + h
                j = src.find(end, i + m.end())
                i = n if j < 0 else j + len(end); out.append(("str", "")); continue
            if c == '"' or (c == "b" and src.startswith('b"', i)):
                i += 1 if c == '"' else 2
                while i < n and src[i] != '"':
                    i += 2 if src[i] == "\\" else 1
                i += 1; out.append(("str", "")); continue
            if c == "'":
                m = re.match(r"'(\\.[^']*|[^\\'])'", src[i:i + 12])
                if m: i += m.end(); out.append(("chr", "")); continue
                m = re.match(r"'[A-Za-z_][A-Za-z0-9_]*", src[i:])
                if m: i += m.end(); out.append(("life", m.group())); continue
                i += 1; continue
            if c == "b" and src.startswith("b'", i):
                m = re.match(r"b'(\\.[^']*|[^\\'])'", src[i:i + 12])
                if m: i += m.end(); out.append(("chr", "")); continue
            m = IDENT.match(src, i)
            if m:
                out.append(("id", m.group().replace("r#", ""))); i = m.end(); continue
            if c.isdigit():
                m = re.compile(r"[0-9][0-9A-Za-z_.]*").match(src, i)
                # avoid eating range dots
                t = m.group()
                k = t.find("..")
                if k >= 0: t = t[:k]
                i += len(t); out.append(("num", t)); continue
            if src.startswith("::", i): out.append(("p", "::")); i += 2; continue
            out.append(("p", c)); i += 1
        return out

    # ---------------- zero-arg macro expansion (item macros such as serde_core's crate_root!()) ----------------
    MACROS = {}
    def _group(T, j):
        op = T[j][1]; cl = {"{": "}", "(": ")", "[": "]"}[op]; d = 0; k = j
        while k < len(T):
            if T[k] == ("p", op): d += 1
            elif T[k] == ("p", cl):
                d -= 1
                if d == 0: return k
            k += 1
        return len(T) - 1
    def collect_macros():
        for dp, dn, fn in os.walk(R):
            dn[:] = [d for d in dn if d not in (".git", ".aletheore", "target")]
            for f in fn:
                if not f.endswith(".rs"): continue
                pk = os.path.relpath(os.path.join(dp, f), R).split(os.sep)[0]
                T = lex(open(os.path.join(dp, f), encoding="utf-8", errors="ignore").read())
                i = 0
                while i < len(T) - 4:
                    if T[i] == ("id", "macro_rules") and T[i + 1] == ("p", "!") and T[i + 3][1] in "{([":
                        end = _group(T, i + 3)
                        j = i + 4
                        # first arm must be an empty matcher: () => { body }
                        if T[j] == ("p", "(") and T[j + 1] == ("p", ")") and T[j + 2] == ("p", "=") and T[j + 3] == ("p", ">") and T[j + 4][1] in "{([":
                            e2 = _group(T, j + 4)
                            # only if this is the only arm
                            if e2 + 1 >= end or T[e2 + 1] == ("p", ";") and e2 + 2 >= end:
                                MACROS[(pk, T[i + 2][1])] = T[j + 5:e2]
                        i = end
                    i += 1
    def expand(T, pk, depth=0):
        out = []; i = 0
        while i < len(T):
            if depth < 4 and T[i][0] == "id" and (pk, T[i][1]) in MACROS and i + 3 < len(T) and T[i + 1] == ("p", "!") and T[i + 2][1] in "({[" and T[i + 3][1] in ")}]" and (i == 0 or T[i - 1] != ("p", "::")):
                out.extend(expand(MACROS[(pk, T[i][1])], pk, depth + 1))
                i += 4
                if i < len(T) and T[i] == ("p", ";"): i += 1
                continue
            out.append(T[i]); i += 1
        return out

    # ---------------- file scan ----------------
    class FileInfo: pass
    _cache = {}
    def scan(path):
        """path = lexical path. returns tokens-derived info independent of crate"""
        rp = os.path.realpath(path)
        if rp in _cache: return _cache[rp]
        src = open(rp, encoding="utf-8", errors="ignore").read()
        T = expand(lex(src), os.path.relpath(rp, R).split(os.sep)[0])
        n = len(T)
        # attribute spans
        attr_by_end = {}
        i = 0
        while i < n:
            if T[i] == ("p", "#") and i + 1 < n and (T[i + 1] == ("p", "[") or (T[i + 1] == ("p", "!") and i + 2 < n and T[i + 2] == ("p", "["))):
                j = i + 1 if T[i + 1] == ("p", "[") else i + 2
                d = 0; k = j
                while k < n:
                    if T[k] == ("p", "["): d += 1
                    elif T[k] == ("p", "]"):
                        d -= 1
                        if d == 0: break
                    k += 1
                # attribute text: strings were blanked, so recover path literal from source separately
                attr_by_end[k] = (i, " ".join(t[1] for t in T[i:k + 1]))
                i = k + 1
            else:
                i += 1
        # re-lex path attrs from raw text (strings blanked in tokens)
        path_attrs_raw = re.findall(r'#\s*\[[^\]]*?path\s*=\s*"([^"]+)"[^\]]*\]', src)
        info = FileInfo()
        info.mods = []      # (inline_stack tuple, name, is_inline, path_attr_candidates)
        info.uses = []      # (inline_stack tuple, segs list)
        info.paths = []     # (inline_stack tuple, segs list) inline paths
        info.defined = collections.defaultdict(set)  # inline_stack -> names
        info.macros_def = set(); info.macros_call = set()
        info.src = src
        # find per-mod path attribute strings by scanning raw source lines before each `mod name;`
        raw_mod_paths = {}
        for m in re.finditer(r'((?:#\s*\[[^\]]*\]\s*)*)(?:pub(?:\([^)]*\))?\s+)?mod\s+([A-Za-z_][A-Za-z0-9_]*)\s*;', src):
            ps = re.findall(r'path\s*=\s*"([^"]+)"', m.group(1))
            if ps: raw_mod_paths.setdefault(m.group(2), []).extend(ps)
        depth = 0; frames = []; pend_mod = None
        VIS_BACK = {"pub"}
        i = 0
        def stack(): return tuple(f[1] for f in frames)
        while i < n:
            k, t = T[i]
            if k == "id" and t == "macro_rules" and i + 2 < n and T[i + 1] == ("p", "!"):
                info.macros_def.add(T[i + 2][1])
                j = i + 3
                if j < n and T[j][1] in "{([":
                    op = T[j][1]; cl = {"{": "}", "(": ")", "[": "]"}[op]; d = 0
                    while j < n:
                        if T[j] == ("p", op): d += 1
                        elif T[j] == ("p", cl):
                            d -= 1
                            if d == 0: break
                        j += 1
                i = j + 1; continue
            if (k, t) == ("p", "{"):
                depth += 1
                if pend_mod: frames.append((depth, pend_mod)); pend_mod = None
                i += 1; continue
            if (k, t) == ("p", "}"):
                if frames and frames[-1][0] == depth: frames.pop()
                depth -= 1; i += 1; continue
            prev = T[i - 1] if i else ("p", ";")
            stmt_start = prev in (("p", ";"), ("p", "{"), ("p", "}"), ("p", "]"), ("p", ")")) or prev == ("id", "pub") or i == 0
            if k == "id" and t in ("fn", "struct", "enum", "trait", "type", "const", "static", "union") and i + 1 < n and T[i + 1][0] == "id" and prev != ("p", "::"):
                info.defined[stack()].add(T[i + 1][1])
            if k == "id" and t == "mod" and stmt_start and i + 2 < n and T[i + 1][0] == "id" and T[i + 2][1] in (";", "{"):
                name = T[i + 1][1]
                if T[i + 2][1] == ";":
                    info.mods.append((stack(), name, False, raw_mod_paths.get(name, [])))
                else:
                    info.mods.append((stack(), name, True, []))
                    pend_mod = name
                info.defined[stack()].add(name)
                i += 2; continue
            if k == "id" and t == "use" and stmt_start:
                # parse use tree
                res = []
                def tree(j, prefix):
                    segs = list(prefix)
                    while j < n:
                        kk, tt = T[j]
                        if (kk, tt) == ("p", "::"): j += 1; continue
                        if kk == "id" and tt == "as":
                            j += 2; continue
                        if kk == "id":
                            segs.append(tt); j += 1; continue
                        if (kk, tt) == ("p", "*"):
                            res.append(segs + ["*"]); return j + 1
                        if (kk, tt) == ("p", "{"):
                            j += 1
                            while j < n and T[j] != ("p", "}"):
                                if T[j] == ("p", ","): j += 1; continue
                                j = tree(j, segs)
                            return j + 1
                        break
                    res.append(segs); return j
                j = tree(i + 1, [])
                for r in res:
                    if r and r[-1] == "self": r = r[:-1]
                    info.uses.append((stack(), r))
                i = j; continue
            if k == "id" and i + 1 < n and T[i + 1] == ("p", "::") and prev not in (("p", "::"), ("p", "$")) and prev[0] != "id" or (k == "id" and i + 1 < n and T[i + 1] == ("p", "::") and prev[0] == "id" and prev[1] in ("pub", "in", "as", "return", "else", "match", "if", "let", "mut", "ref", "for", "impl", "dyn", "where")):
                segs = [t]; j = i + 1
                while j + 1 < n and T[j] == ("p", "::") and T[j + 1][0] == "id":
                    segs.append(T[j + 1][1]); j += 2
                info.paths.append((stack(), segs))
                i = j; continue
            if k == "id" and i + 1 < n and T[i + 1] == ("p", "!") and prev != ("p", "::"):
                info.macros_call.add(t)
            i += 1
        _cache[rp] = info
        return info

    # ---------------- crates ----------------
    collect_macros()
    print("expandable zero-arg macros:", sorted(MACROS))
    md = json.loads(run_tool(["cargo", "metadata", "--format-version", "1", "--offline", "--no-deps"], cwd=R, capture_output=True, text=True).stdout)
    pkgs = {p["name"]: p for p in md["packages"]}
    crate_of_pkg_lib = {}   # extern name -> crate id
    crates = {}             # crate id -> dict(root, pkg, deps{extern name: crate id})
    for p in md["packages"]:
        for t in p["targets"]:
            cid = (p["name"], t["name"], tuple(t["kind"]))
            crates[cid] = {"root": t["src_path"], "pkg": p["name"], "kind": t["kind"]}
            if "lib" in t["kind"] or "proc-macro" in t["kind"]:
                crate_of_pkg_lib[t["name"].replace("-", "_")] = cid
    for cid, c in crates.items():
        p = pkgs[c["pkg"]]
        deps = {}
        for d in p["dependencies"]:
            nm = (d["rename"] or d["name"]).replace("-", "_")
            tgt = d["name"].replace("-", "_")
            if tgt in crate_of_pkg_lib and d.get("path"):
                deps[nm] = crate_of_pkg_lib[tgt]
        c["deps"] = deps
        # own lib visible to bins/tests of same package
        for t in p["targets"]:
            if "lib" in t["kind"] or "proc-macro" in t["kind"]:
                if cid != (p["name"], t["name"], tuple(t["kind"])):
                    deps[t["name"].replace("-", "_")] = (p["name"], t["name"], tuple(t["kind"]))

    def rel(p): return os.path.relpath(os.path.realpath(p), R)

    # module map per crate: (cid, modpath tuple) -> (lexical file, realfile, ownerdir-mode)
    edges = collections.defaultdict(set)
    modmap = {}
    file_ctx = []  # (cid, lexfile, base modpath) for each file occurrence
    def add(a, b, tag):
        if a != b: edges[(a, b)].add(tag)

    def build(cid):
        root = crates[cid]["root"]
        q = [(root, (), True)]  # lexical path, modpath, dir_owner(mod-rs-like)
        seen = set()
        modmap[(cid, ())] = (root, True)
        while q:
            lex_f, mp, owner = q.pop()
            key = (os.path.realpath(lex_f), mp)
            if key in seen: continue
            seen.add(key)
            file_ctx.append((cid, lex_f, mp))
            info = scan(lex_f)
            d = os.path.dirname(lex_f)
            base = d if owner else os.path.join(d, os.path.splitext(os.path.basename(lex_f))[0])
            for stk, name, inline, pcands in info.mods:
                full = mp + stk + (name,)
                if inline:
                    modmap[(cid, full)] = (lex_f, None)  # inline: lives in the same file
                    continue
                cands = []
                for pc in pcands:
                    cands.append((os.path.normpath(os.path.join(d, pc)), True))
                bdir = os.path.join(base, *stk)
                cands.append((os.path.join(bdir, name + ".rs"), False))
                cands.append((os.path.join(bdir, name, "mod.rs"), True))
                found = False
                for cpath, ow in cands:
                    if os.path.exists(cpath):
                        if not found: modmap[(cid, full)] = (cpath, ow)
                        add(rel(lex_f), rel(cpath), "mod")
                        q.append((cpath, full, ow))
                        found = True
                if not found:
                    modmap[(cid, full)] = (None, None)
    for cid in crates:
        build(cid)

    # orphan files: not reachable through any `mod` chain (trybuild ui fixtures, automod::dir! members, no_std bins).
    # They are compiled against their package's dependencies, so resolve their `use` paths with that package's deps.
    covered = {os.path.realpath(f) for _, f, _ in file_ctx}
    for dp, dn, fn in os.walk(R):
        dn[:] = [d for d in dn if d not in (".git", ".aletheore", "target")]
        for f in fn:
            full = os.path.join(dp, f)
            if f.endswith(".rs") and os.path.realpath(full) not in covered:
                pkgdir = os.path.relpath(full, R).split(os.sep)[0]
                owner = [c for c, v in crates.items() if v["pkg"].replace("_", "-") == pkgdir.replace("_", "-") or v["pkg"] == pkgdir or os.path.relpath(v["root"], R).split(os.sep)[0] == pkgdir]
                if owner:
                    owner.sort(key=lambda c: (c[2] != ("test",), c[1]))
                    file_ctx.append((owner[0], full, ()))

    def file_of(cid, mp):
        ent = modmap.get((cid, mp))
        if not ent or ent[0] is None: return None
        return rel(ent[0])

    def resolve_path(cid, mp, segs, allow_rel=True):
        """-> (target file rel, tag, crate, modpath, remaining segs) or None"""
        segs = [s for s in segs if s != "self" or segs.index(s) != 0 or True]
        if not segs: return None
        head = segs[0]; rest = segs[1:]
        tag = "use-rel"
        if head == "crate": tcid, tmp = cid, (); tag = "use-crate"
        elif head == "self": tcid, tmp = cid, mp; tag = "use-self"
        elif head == "super":
            tcid, tmp = cid, mp[:-1] if mp else mp; tag = "use-super"
            while rest and rest[0] == "super": tmp = tmp[:-1]; rest = rest[1:]
        elif (cid, mp + (head,)) in modmap and head not in crates[cid]["deps"]:
            tcid, tmp = cid, mp + (head,); tag = "use-rel"
        elif head in crates[cid]["deps"]:
            tcid, tmp = crates[cid]["deps"][head], (); tag = "use-ext"
        elif (cid, (head,)) in modmap and mp == ():
            tcid, tmp = cid, (head,)
        else:
            return None
        while rest and (tcid, tmp + (rest[0],)) in modmap:
            tmp = tmp + (rest[0],); rest = rest[1:]
        if rest and rest[0] == "*": rest = rest[1:]
        return tcid, tmp, rest, tag

    def def_chain(cid, mp, name, depth=0):
        """follow re-exports for item `name` in module (cid, mp): return defining module (cid, mp) or None"""
        if depth > 6: return None
        f = modmap.get((cid, mp))
        if not f or f[0] is None: return None
        info = scan(f[0])
        stk = mp  # approximate: module relative path inside file is unknown; use whole-file sets
        for names in info.defined.values():
            if name in names: return (cid, mp)
        for st, segs in info.uses:
            if not segs: continue
            if segs[-1] == name or segs[-1] == "*":
                r = resolve_path(cid, mp, segs[:-1] if segs[-1] == "*" else segs)
                if r:
                    tcid, tmp, rest, _ = r
                    if segs[-1] == "*":
                        res = def_chain(tcid, tmp, name, depth + 1)
                        if res: return res
                    elif not rest or rest == [name]:
                        res = def_chain(tcid, tmp, name, depth + 1) if rest == [name] else (tcid, tmp)
                        if res: return res
        return None

    for cid, lex_f, mp in file_ctx:
        info = scan(lex_f)
        me = rel(lex_f)
        for stk, segs in info.uses:
            cur = mp + stk
            r = resolve_path(cid, cur, segs)
            if not r: continue
            tcid, tmp, rest, tag = r
            tf = file_of(tcid, tmp)
            if tf:
                add(me, tf, tag)
                if rest:
                    dc = def_chain(tcid, tmp, rest[0])
                    if dc:
                        df = file_of(*dc)
                        if df: add(me, df, "def")
        for stk, segs in info.paths:
            cur = mp + stk
            r = resolve_path(cid, cur, segs)
            if not r: continue
            tcid, tmp, rest, tag = r
            tf = file_of(tcid, tmp)
            if tf:
                add(me, tf, "inline")
                if rest:
                    dc = def_chain(tcid, tmp, rest[0])
                    if dc:
                        df = file_of(*dc)
                        if df: add(me, df, "def-inline")

    # macro_rules! definitions and invocations (same crate or workspace)
    mdef = collections.defaultdict(set)
    for cid, lex_f, mp in file_ctx:
        for m in scan(lex_f).macros_def: mdef[m].add(rel(lex_f))
    for cid, lex_f, mp in file_ctx:
        for m in scan(lex_f).macros_call:
            for d in mdef.get(m, ()):
                add(rel(lex_f), d, "macro")


    # include!("file") splices
    for dp, dn, fn in os.walk(R):
        dn[:] = [d for d in dn if d not in (".git", ".aletheore", "target")]
        for f in fn:
            if f.endswith(".rs"):
                full = os.path.join(dp, f)
                s_ = open(full, encoding="utf-8", errors="ignore").read()
                for m in re.finditer(r'\binclude\s*!\s*\(\s*"([^"]+)"\s*\)', s_):
                    t = os.path.normpath(os.path.join(dp, m.group(1)))
                    if os.path.isfile(t): add(rel(full), rel(t), "include")
    KEEP = {"mod", "use-crate", "use-self", "use-super", "use-rel", "use-ext", "inline", "def", "def-inline", "include"}
    E = sorted({(a, b) for (a, b), ts in edges.items() if ts & KEEP})
    TAGC = collections.Counter(t for ts in edges.values() for t in ts)
    print("rust tags", dict(TAGC))
    RESULT = E

else:
    def strip(s):
        s = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group().count("\n"), s, flags=re.S)
        return re.sub(r"//[^\n]*", "", s)
    incdirs = [d for d in ["", "include", "src", "test", "tests", "vendor/decNumber", "vendor/oniguruma/src", "vendor/oniguruma"] if d == "" or os.path.isdir(os.path.join(REPO, d))]
    bysuffix = collections.defaultdict(list)
    for h in FILES:
        parts = h.split("/")
        for i in range(len(parts)):
            bysuffix["/".join(parts[i:])].append(h)
    E = set()
    for f in FILES:
        s = strip(open(os.path.join(REPO, f), encoding="utf-8", errors="ignore").read())
        for m in re.finditer(r'(?m)^[ \t]*#[ \t]*(?:include|include_next|import)[ \t]*([<"])([^>"\n]+)[>"]', s):
            kind, spec = m.group(1), m.group(2).strip()
            cands = []
            if kind == '"': cands.append(os.path.dirname(f))
            cands += incdirs
            tgt = None
            for c in cands:
                p = os.path.normpath(os.path.join(c, spec))
                if p in FS: tgt = p; break
            if tgt is None:
                hits = [h for h in bysuffix.get(os.path.normpath(spec), []) if h != f]
                if len(hits) == 1: tgt = hits[0]
            if tgt and tgt != f: E.add((f, tgt))
    RESULT = sorted(E)

RESULT = sorted({(a, b) for a, b in RESULT if a != b and a in FS and b in FS})
json.dump({"files": FILES, "edges": [list(e) for e in RESULT]}, open(OUT, "w"))
print(mode, REPO, "files", len(FILES), "edges", len(RESULT))
