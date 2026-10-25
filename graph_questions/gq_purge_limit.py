"""Find session-limit responses; quarantine them only when --apply is supplied."""

import argparse
import re
from pathlib import Path

from safe_cleanup import quarantine_json_files

BASE = Path(__file__).resolve().parent
LIMIT = re.compile(
    r"\b(?:session|usage|rate)[ -]limit\b"
    r"|\b(?:hit|reached|exceeded)\s+(?:your|the)\s+(?:session|usage|rate)[ -]limit\b",
    re.IGNORECASE,
)


def is_rate_limited(record):
    text = f"{record.get('result') or ''}\n{record.get('raw') or ''}"
    return bool(LIMIT.search(text))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directories", nargs="+", help="result directories relative to graph_questions/")
    parser.add_argument("--apply", action="store_true", help="move matches to quarantine (default: report only)")
    args = parser.parse_args()
    for name in args.directories:
        directory = (BASE / name).resolve()
        if directory != BASE and BASE not in directory.parents:
            parser.error(f"directory must be inside {BASE}")
        matches = quarantine_json_files(directory, is_rate_limited, apply=args.apply)
        action = "quarantined" if args.apply else "candidate(s); dry run"
        print(f"{name}: {len(matches)} {action}: {[p.name for p in matches]}")


if __name__ == "__main__":
    main()
