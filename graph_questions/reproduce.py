"""Recompute every number in graph_questions/README.md from the raw runs. No API key, no network.

    python3 reproduce.py

Extracts runs/*.tar.gz into out_* folders next to this file, then scores every run against the ground truth in
truth/ and the task files, and prints the accuracy, token and cost tables (also written to publish_numbers.json).
"""
import os
import runpy
import tarfile

here = os.path.dirname(os.path.abspath(__file__))
for name in sorted(os.listdir(os.path.join(here, "runs"))):
    if name.endswith(".tar.gz") and not os.path.isdir(os.path.join(here, name[: -len(".tar.gz")])):
        with tarfile.open(os.path.join(here, "runs", name)) as tar:
            tar.extractall(here, filter="data")
runpy.run_path(os.path.join(here, "publish_numbers.py"), run_name="__main__")
