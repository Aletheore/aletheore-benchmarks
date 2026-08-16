"""Shared paths and question loading.

Every path is an environment variable with a default, so the harness runs on a
machine that is not the one it was written on. It previously hard-coded
/private/tmp/... and an absolute /Users/... path, which made third-party
reproduction impossible.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# Scratch root for corpus checkouts and per-repo output. Deliberately NOT under
# /tmp: a reboot wipes /private/tmp on macOS, and a multi-repo run that dies
# there loses every corpus scored before the crash along with the key file.
WORK = os.environ.get("BENCH_WORK", os.path.expanduser("~/.aletheore-bench"))

# The corpus under test, and the copy RepoWise indexed (it writes .repowise/
# into the repo, so the two tools get separate checkouts of the same commit).
FLASK = os.environ.get("BENCH_FLASK", "/tmp/bench-flask")
FLASK_RW = os.environ.get("BENCH_FLASK_RW", "/tmp/bench-flask-rw/flask")
OUT = os.environ.get("BENCH_OUT", os.path.join(ROOT, "results"))
ENV_FILE = os.environ.get("BENCH_ENV_FILE", os.path.join(WORK, ".env"))


# DeepSeek retired the `deepseek-chat` alias: the API still accepts the name but
# serves deepseek-v4-flash, so every result labelled "deepseek-chat" is in fact
# Flash output and the label is wrong. Pinned explicitly here so what ran is what
# gets recorded, and so a future alias change cannot silently move the baseline
# underneath a published number. Verified against GET /models: the only ids
# offered are deepseek-v4-flash and deepseek-v4-pro.
WRITER_MODEL = os.environ.get("AIRVIEW_MODEL", "deepseek-v4-flash")
JUDGE_MODEL = os.environ.get("JUDGE_MODEL", "deepseek-v4-flash")


def repo_src(name):
    """Checkout Aletheore scans and indexes."""
    return os.path.join(WORK, f"multi-{name}")


def repo_rw(name):
    """Separate checkout for RepoWise, which writes .repowise/ into the tree."""
    return os.path.join(WORK, f"multi-rw-{name}")


def repo_out(name):
    """Per-repo artifacts: airview.json, arch_context.json, scores."""
    return os.path.join(WORK, "bench", f"multi_{name}")

# Checkout the ground truth was verified against. A different commit invalidates
# the answer key, so runners fail loudly rather than scoring against drift.
CORPUS_COMMIT = "2a8a38b051fc248865730bf3511bf2e2ea325e81"


def load_questions(name="location"):
    """Returns [{id, q, gt, anchor}] from the self-describing on-disk schema."""
    path = os.path.join(ROOT, "questions", f"{name}.json")
    raw = json.load(open(path))
    out = []
    for entry in raw:
        out.append(
            {
                "id": entry["id"],
                "q": entry.get("question") or entry.get("q"),
                "gt": entry.get("ground_truth_files") or entry.get("gt") or [],
                "anchor": entry.get("verification_anchor") or entry.get("anchor"),
            }
        )
    return out


def load_env():
    """API keys, from a file outside the repo so a key is never committed."""
    env = {}
    if os.path.exists(ENV_FILE):
        for line in open(ENV_FILE):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k] = v
                os.environ.setdefault(k, v)
    return env


def require_key(name="DEEPSEEK_API_KEY"):
    """The key, from the environment or ENV_FILE, or a loud actionable failure.

    Reading ENV_FILE unconditionally used to raise a bare FileNotFoundError
    partway through a run; an exported key now works on its own.
    """
    load_env()
    key = os.environ.get(name)
    if not key:
        raise SystemExit(
            f"{name} is not set.\n"
            f"  export {name}=...   or put it in {ENV_FILE}"
        )
    return key


def check_corpus_commit(repo=None):
    """Loud failure beats a silently wrong number scored against a moved corpus."""
    import subprocess

    repo = repo or FLASK
    try:
        head = subprocess.run(
            ["git", "-C", repo, "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except Exception as exc:
        raise SystemExit(f"cannot read corpus at {repo}: {exc}")
    if head != CORPUS_COMMIT:
        raise SystemExit(
            f"corpus is at {head[:12]}, ground truth was verified against "
            f"{CORPUS_COMMIT[:12]}.\n"
            f"  git -C {repo} checkout {CORPUS_COMMIT}"
        )
