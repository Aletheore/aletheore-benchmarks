"""Callers / subclasses ground truth for a Java repo via javac's Compiler Tree API (parse + analyze).
usage: make_refs_java.py <repo_dir> <out.json>"""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _tools import run_tool

here = os.path.dirname(os.path.abspath(__file__))
repo, out = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
try:
    files = [f for f in run_tool(["git", "ls-files", "*.java"], cwd=repo, capture_output=True, text=True, check=True).stdout.split("\n") if f]
except Exception:
    files = [os.path.relpath(os.path.join(b, n), repo) for b, ds, ns in os.walk(repo) if ".git" not in b.split(os.sep) for n in ns if n.endswith(".java")]
os.makedirs("./truth_work_refs", exist_ok=True)
work = tempfile.mkdtemp(prefix="refs_java_", dir="./truth_work_refs")
lst = os.path.join(work, "files.txt")
open(lst, "w").write("\n".join(files))
run_tool(["javac", "-d", work, os.path.join(here, "RefsJava.java")], check=True)
run_tool(["java", "-cp", work, "RefsJava", repo, out, lst], check=True)
