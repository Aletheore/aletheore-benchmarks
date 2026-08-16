"""Builds the exact input files used by the deterministic-vs-bare-LLM
benchmark from a real repo checkout - a raw git log slice for
hotspots/ownership, and per-file import statements for dead-code. Run
from inside the target repo checkout (see DETERMINISTIC_VS_LLM.md for the
pinned commit).

Usage: python det_vs_llm_build_inputs.py <output_dir> [commit_count]
"""
import subprocess
import sys
from pathlib import Path


def main():
    out_dir = Path(sys.argv[1])
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 1500
    out_dir.mkdir(parents=True, exist_ok=True)

    # Hotspots input: raw name-only log, capped at n commits so it reliably
    # fits in a single LLM context window (the full flask history is 205K
    # tokens - it doesn't fit in one completion at all, see
    # DETERMINISTIC_VS_LLM.md's "A structural limit" section).
    log = subprocess.run(
        ["git", "log", "--name-only", "--pretty=format:COMMIT %H", f"-{n}"],
        capture_output=True, text=True, check=True,
    ).stdout
    (out_dir / "det_vs_llm_hotspots_input_1500commits.txt").write_text(log)

    # Ownership input: same commit range, author name|email only.
    authors = subprocess.run(
        ["git", "log", "--pretty=format:%an|%ae", f"-{n}"],
        capture_output=True, text=True, check=True,
    ).stdout
    (out_dir / "det_vs_llm_ownership_input_1500commits.txt").write_text(authors)

    # Dead-code input: every Python file's own import/from-import lines -
    # the minimum data needed to compute module reachability, without
    # requiring the model to read (and pay for) full source.
    files = subprocess.run(
        ["git", "ls-files", "*.py"], capture_output=True, text=True, check=True
    ).stdout.splitlines()
    parts = []
    for f in files:
        try:
            with open(f, encoding="utf-8", errors="replace") as fh:
                lines = [l.rstrip() for l in fh if l.startswith("import ") or l.startswith("from ")]
        except OSError:
            lines = []
        parts.append(f"FILE: {f}\n" + "\n".join(lines))
    (out_dir / "det_vs_llm_deadcode_input_83files.txt").write_text("\n\n".join(parts))

    print(f"Wrote det_vs_llm_{{hotspots,ownership,deadcode}}_input files to {out_dir}")


if __name__ == "__main__":
    main()
