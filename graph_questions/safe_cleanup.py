"""Non-destructive helpers for reviewing questionable benchmark result files."""

from datetime import datetime, timezone
import json
import shutil
import tempfile
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
        if not isinstance(record, dict):
            continue
        if predicate(record):
            candidates.append(path)

    if not apply or not candidates:
        return candidates

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    quarantine_root = directory.parent / "quarantine"
    quarantine_root.mkdir(parents=True, exist_ok=True)
    run_root = Path(tempfile.mkdtemp(prefix=f"{stamp}-", dir=quarantine_root))
    quarantine = run_root / directory.name
    quarantine.mkdir()
    moved = []
    for path in candidates:
        try:
            shutil.move(str(path), str(quarantine / path.name))
        except OSError as exc:
            moved_names = ", ".join(item.name for item in moved) or "none"
            raise OSError(
                f"quarantine stopped at {path}; moved {len(moved)} of {len(candidates)} "
                f"files to {quarantine} (moved: {moved_names})"
            ) from exc
        moved.append(path)
    return candidates
