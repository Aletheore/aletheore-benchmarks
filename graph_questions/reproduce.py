"""Recompute every number in graph_questions/README.md from the raw runs. No API key, no network.

    python3 reproduce.py

Extracts runs/*.tar.gz into out_* folders next to this file, then scores every run against the ground truth in
truth/ and the task files, and prints the accuracy, token and cost tables (also written to publish_numbers.json).
"""
import os
import runpy
import tarfile
import tempfile
from pathlib import PurePosixPath


def extract_run_archives(base_dir):
    base_dir = os.path.abspath(base_dir)
    runs_dir = os.path.join(base_dir, "runs")
    if not os.path.isdir(runs_dir):
        return
    for name in sorted(os.listdir(runs_dir)):
        if not name.endswith(".tar.gz"):
            continue
        expected = name[:-len(".tar.gz")]
        destination = os.path.join(base_dir, expected)
        if os.path.exists(destination):
            print(f"Skipping {name}: {expected} already exists; refusing to overwrite")
            continue

        archive_path = os.path.join(runs_dir, name)
        with tarfile.open(archive_path) as archive:
            members = archive.getmembers()
            for member in members:
                path = PurePosixPath(member.name)
                if (path.is_absolute() or not path.parts or path.parts[0] != expected
                        or ".." in path.parts or not (member.isdir() or member.isfile())):
                    raise ValueError(f"unsafe or unexpected member in {name}: {member.name}")
            with tempfile.TemporaryDirectory(dir=base_dir, prefix=".run-extract-") as staging:
                archive.extractall(staging, members=members, filter="data")
                extracted = os.path.join(staging, expected)
                if not os.path.isdir(extracted):
                    raise ValueError(f"{name} does not contain expected directory {expected}")
                if os.path.exists(destination):
                    print(f"Skipping {name}: {expected} already exists; refusing to overwrite")
                    continue
                try:
                    # Publish the complete staged tree atomically. Competing runs
                    # cannot observe partial output; a loser never deletes the winner.
                    os.rename(extracted, destination)
                except OSError:
                    if os.path.exists(destination):
                        print(f"Skipping {name}: {expected} appeared during extraction; refusing to overwrite")
                        continue
                    raise


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    extract_run_archives(here)
    runpy.run_path(os.path.join(here, "publish_numbers.py"), run_name="__main__")
