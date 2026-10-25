#!/usr/bin/env python3
"""Ground-truth file-level import graph for a Go repo.
usage: make_truth_go.py REPO_DIR OUT_JSON [--members]
Edges: (1) package imports -> all default-build GoFiles/CgoFiles of the imported in-repo package (go list);
(2) same-package coupling via go/types (package-level names; --members also adds methods/fields).
Helpers (Go programs) live in ./truth_work_go/."""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _tools import run_tool
W = "./truth_work_go"
repo = os.path.abspath(sys.argv[1]); out = sys.argv[2]; members = "--members" in sys.argv
env = dict(os.environ, GOFLAGS="-mod=mod", GOTOOLCHAIN="local")
mod = re.search(r"^module\s+(\S+)", open(repo + "/go.mod").read(), re.M).group(1)
fi = json.loads(run_tool(["go", "run", ".", repo], cwd=W + "/fileimports", capture_output=True, text=True, check=True).stdout)
files = sorted(f for f in fi if "vendor/" not in "/" + f)
fi = {f: fi[f] for f in files}
alldir = {}
for f in files: alldir.setdefault(os.path.dirname(f) or ".", []).append(f)
# go list per dir containing go files (covers testdata, which ./... skips)
pk = {}
dec = json.JSONDecoder()
for d in sorted(alldir):
    r = run_tool(["go", "list", "-e", "-json", "./" + d if d != "." else "."], cwd=repo, capture_output=True, text=True, env=env)
    s = r.stdout; i = 0
    while i < len(s):
        while i < len(s) and s[i].isspace(): i += 1
        if i >= len(s): break
        o, i = dec.raw_decode(s, i)
        pk[os.path.relpath(o["Dir"], repo)] = o
def imp_dir(ip):
    if ip == mod: return "."
    return ip[len(mod) + 1:] if ip.startswith(mod + "/") else None
E = set()
for f, v in fi.items():
    fd = os.path.dirname(f) or "."
    for ip in v["imports"] or []:
        d = imp_dir(ip)
        if d is None or d not in alldir or d == fd: continue
        p = pk.get(d, {})
        for x in (p.get("GoFiles") or []) + (p.get("CgoFiles") or []):
            E.add((f, (d + "/" if d != "." else "") + x))
n_imp = len(E)
b = run_tool(["go", "build", "-o", W + "/gotypes_bin", "."], cwd=W + "/gotypes", capture_output=True, text=True)
if b.returncode: sys.exit(b.stderr)
r = run_tool([W + "/gotypes_bin", repo], cwd=repo, capture_output=True, text=True, env=env)
sp = {(e["From"], e["To"]) for e in json.loads(r.stdout) if members or e["Kind"] == "pkglevel"}
E |= sp
fs = set(files)
E = {e for e in E if e[0] in fs and e[1] in fs and e[0] != e[1]}
json.dump({"files": files, "edges": [list(e) for e in sorted(E)]}, open(out, "w"), indent=0)
print("files", len(files), "edges", len(E), "(import", n_imp, "samepkg", len(sp), ")", r.stderr.strip()[-80:])
