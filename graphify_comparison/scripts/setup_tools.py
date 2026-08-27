"""Verifies both CLIs are installed and their indexes exist for ERPNext.
Import smoke_test() from any script that's about to shell out to either
tool - fails loudly before burning API budget on a run that would fail
partway through anyway.
"""
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from clone_corpus import ensure_corpus


def smoke_test() -> None:
    checkout = ensure_corpus()

    if shutil.which("aletheore") is None:
        raise SystemExit("aletheore CLI not on PATH - pip install aletheore")
    if shutil.which("graphify") is None:
        raise SystemExit("graphify CLI not on PATH - pipx install graphifyy")

    if not os.path.exists(os.path.join(checkout, ".aletheore", "air.json")):
        raise SystemExit(
            f"no Aletheore evidence at {checkout}/.aletheore/air.json - "
            f"run `aletheore scan .` inside {checkout} first"
        )
    if not os.path.exists(os.path.join(checkout, "graphify-out", "graph.json")):
        raise SystemExit(
            f"no Graphify graph at {checkout}/graphify-out/graph.json - "
            f"run `graphify extract . --code-only` inside {checkout} first"
        )
    if not os.path.exists(os.path.join(checkout, ".aletheore", "index.lancedb")):
        raise SystemExit(
            f"no Aletheore semantic index at {checkout}/.aletheore/index.lancedb - "
            f"run `aletheore index .` inside {checkout} first (needs a local Ollama "
            f"embedding model - falls back to OpenAI otherwise, which costs real money "
            f"and needs a key outside this benchmark's budget)"
        )

    result = subprocess.run(
        ["aletheore", "query", "search-codebase", "sales invoice validation", "--path", checkout],
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0:
        raise SystemExit(f"aletheore query smoke test failed: {result.stderr}")

    result = subprocess.run(
        ["graphify", "query", "what is this codebase about?"],
        cwd=checkout, capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0:
        raise SystemExit(f"graphify query smoke test failed: {result.stderr}")

    print("both CLIs verified working against the pinned ERPNext checkout")


if __name__ == "__main__":
    smoke_test()
