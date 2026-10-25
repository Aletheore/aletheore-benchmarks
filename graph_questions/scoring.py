"""Shared task loading and answer scoring for graph-question benchmarks."""

import json
import re

from ml_pick import Graph, REPOS

LANGNAME = {
    "python": "Python",
    "go": "Go",
    "ts": "TS/JS",
    "java": "Java",
    "csharp": "C#",
    "rust": "Rust",
    "php": "PHP",
    "ruby": "Ruby",
    "c": "C",
    "cpp": "C++",
}
_GRAPHS = {}


def load_tasks(task_files, base_dir):
    tasks = {}
    for name in task_files:
        with open(f"{base_dir}/{name}", encoding="utf-8") as task_file:
            tasks.update({task["id"]: task for task in json.load(task_file)})
    return tasks


def graph(repo):
    if repo not in _GRAPHS:
        _GRAPHS[repo] = Graph(repo)
    return _GRAPHS[repo]


def parse_list(text):
    match = re.search(r"\[.*\]", text or "", re.S)
    try:
        return [
            item.strip().removeprefix("./")
            for item in json.loads(match.group(0))
            if isinstance(item, str)
        ] if match else None
    except ValueError:
        return None


def score(task, text):
    kind = task["kind"]
    if kind == "cycles":
        predicted = parse_list(text)
        if predicted is None:
            return 0.0, False
        if not task["has_cycle"]:
            return (1.0 if predicted == [] else 0.0), True
        dependency_graph = graph(task["repo"])
        valid = (
            len(predicted) >= 2
            and len(set(predicted)) == len(predicted)
            and all(
                predicted[(index + 1) % len(predicted)]
                in dependency_graph.fwd.get(predicted[index], ())
                for index in range(len(predicted))
            )
        )
        return (1.0 if valid else 0.0), True
    if kind in ("direct", "unreachable", "hubs", "dupdef", "callers", "subclasses"):
        predicted = parse_list(text)
        if predicted is None:
            return 0.0, False
        return (1.0 if set(predicted) == set(task["truth"]) else 0.0), True
    if kind in ("size", "deps"):
        match = re.search(r"\d[\d,]*", (text or "").replace('"count"', ""))
        if not match:
            return 0.0, False
        value = int(match.group(0).replace(",", ""))
        return (1.0 if abs(value - task["truth_n"]) / task["truth_n"] <= 0.10 else 0.0), True
    if kind == "locate":
        match = re.search(r'"file"\s*:\s*"([^"]+)"', text or "")
        if not match:
            return 0.0, False
        return (1.0 if match.group(1).strip().removeprefix("./") == task["truth_file"] else 0.0), True
    if kind == "path":
        predicted = parse_list(text)
        if not predicted:
            return 0.0, False
        dependency_graph = graph(task["repo"])
        valid = (
            predicted[0] == task["target"]
            and predicted[-1] == task["to"]
            and all(
                right in dependency_graph.fwd.get(left, ())
                for left, right in zip(predicted, predicted[1:])
            )
        )
        return (
            1.0 if valid and len(predicted) - 1 == task["truth_len"] else 0.0
        ), True
    names = re.findall(r'"author"\s*:\s*"([^"]+)"', text or "")
    if not names:
        return 0.0, False
    wanted, actual = task["truth_author"].lower().split(), names[0].lower()
    return (1.0 if wanted[-1] in actual and wanted[0] in actual else 0.0), True
