"""Clones (or verifies) the pinned ERPNext checkout this benchmark's ground
truth was written against. A different commit invalidates the question
set's expected key facts, so this fails loudly rather than scoring against
drift - same discipline as _bench.py's check_corpus_commit for the main
benchmark suite.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

with open(os.path.join(ROOT, "corpus_manifest.json")) as f:
    MANIFEST = json.load(f)

CHECKOUT = os.path.expanduser(
    os.environ.get(MANIFEST["checkout_env_var"], MANIFEST["checkout_default"])
)


def ensure_corpus() -> str:
    """Returns the verified checkout path, cloning it first if absent."""
    if not os.path.isdir(os.path.join(CHECKOUT, ".git")):
        os.makedirs(os.path.dirname(CHECKOUT), exist_ok=True)
        subprocess.run(
            ["git", "clone", "--depth", "1", MANIFEST["repo"], CHECKOUT],
            check=True,
        )
    head = subprocess.run(
        ["git", "-C", CHECKOUT, "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    if head != MANIFEST["commit"]:
        raise SystemExit(
            f"ERPNext checkout at {CHECKOUT} is at {head[:12]}, ground truth "
            f"was written against {MANIFEST['commit'][:12]}.\n"
            f"  rm -rf {CHECKOUT} && python3 {__file__}"
        )
    return CHECKOUT


if __name__ == "__main__":
    path = ensure_corpus()
    print(f"ERPNext verified at {path} ({MANIFEST['commit'][:12]})")
    sys.exit(0)
