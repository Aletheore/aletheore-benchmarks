"""Non-destructive helpers for reviewing questionable benchmark result files."""

from datetime import datetime, timezone
import json
import shutil
from pathlib import Path


def quarantine_json_files(directory, predicate, *, apply=False):
    """List matching JSON files, moving them to quarantine only with explicit opt-in."""
    directory = Path(directory).resolve()
    candidates = []
    for path in sorted(directory.glob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if predicate(record):
            candidates.append(path)

    if not apply or not candidates:
        return candidates

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    quarantine = directory.parent / "quarantine" / stamp / directory.name
    quarantine.mkdir(parents=True, exist_ok=False)
    for path in candidates:
        shutil.move(str(path), str(quarantine / path.name))
    return candidates
