"""Find transport-failure results; quarantine only with explicit --apply."""

import argparse
import re
from pathlib import Path

from safe_cleanup import quarantine_json_files

BASE = Path(__file__).resolve().parent
NETWORK_ERROR = re.compile(
    r"\b(api error|unable to connect|econn|enotfound|connection refused|fetch failed|socket hang)",
    re.IGNORECASE,
)


def is_network_failure(record):
    text = record.get("result") or record.get("raw") or ""
    return isinstance(text, str) and record.get("rc") == 1 and bool(NETWORK_ERROR.search(text[:400]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", help="result directory relative to graph_questions/")
    parser.add_argument("--apply", action="store_true", help="move matches to quarantine (default: report only)")
    args = parser.parse_args()
    directory = (BASE / args.directory).resolve()
    if BASE not in directory.parents:
        parser.error(f"directory must be inside {BASE}")
    matches = quarantine_json_files(directory, is_network_failure, apply=args.apply)
    action = "quarantined" if args.apply else "candidate(s); dry run"
    print(f"{len(matches)} {action}: {[p.name for p in matches]}")


if __name__ == "__main__":
    main()
