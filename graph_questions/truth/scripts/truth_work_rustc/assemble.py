body = open('./truth_work_rustc/rust_body.txt').read()
head = '''#!/usr/bin/env python3
"""Independent ground-truth file-level dependency graph.
usage: make_truth_rustc.py <rust|c|cpp> <repo_dir> <out.json>
Output {"files": [...], "edges": [[from,to],...]}, repo-relative, sorted, deduped, no self/dangling edges.
rust: own lexer + mod-tree builder (cargo metadata for crate roots/workspace deps); edges from `mod x;`,
      use/inline paths (crate/self/super/workspace crates, following pub use re-exports to the defining file,
      zero-arg item macros expanded), and include!("file").
c/cpp: #include "x"/<x> resolved against includer dir, repo include dirs, then unique path-suffix match among
      tracked files; only repo-tracked files; comments stripped; all #if branches counted (no preprocessing).
Tracked files = VCS file list (falls back to os.walk)."""
import json, os, re, subprocess, sys, collections
mode, REPO, OUT = sys.argv[1], os.path.realpath(sys.argv[2]), sys.argv[3]
R = REPO
EXTS = {"rust": (".rs",), "c": (".c", ".h"), "cpp": (".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".inl")}[mode]

def tracked():
    r = subprocess.run(["git", "-C", REPO, "ls-files", "-z"], capture_output=True, text=True)
    if r.returncode == 0 and r.stdout:
        fl = [f for f in r.stdout.split("\\0") if f]
    else:
        fl = []
        for dp, dn, fn in os.walk(REPO):
            dn[:] = [d for d in dn if d not in (".git", ".aletheore", "target", "node_modules")]
            fl += [os.path.relpath(os.path.join(dp, f), REPO) for f in fn]
    return sorted(f for f in fl if f.endswith(EXTS) and os.path.isfile(os.path.join(REPO, f)))

FILES = tracked()
FS = set(FILES)

if mode == "rust":
'''
c = r'''
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
'''
open('./truth/make_truth_rustc.py', 'w').write(head + body + c)
