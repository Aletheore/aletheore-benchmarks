"""The grep/read/list floor every condition gets - mirrors what a real
coding agent always has, so the +Aletheore and +Graphify conditions are
measuring what ONE additional tool adds on top of this, not replacing it.
"""
import os
import subprocess

_ROOT = "."


def set_root(root: str) -> None:
    global _ROOT
    _ROOT = root


def grep_tool(pattern: str, path: str = ".") -> str:
    full_path = os.path.join(_ROOT, path)
    result = subprocess.run(
        ["grep", "-rn", "--include=*.py", "--include=*.js", pattern, full_path],
        capture_output=True, text=True, timeout=30,
    )
    lines = result.stdout.splitlines()[:50]
    return "\n".join(lines) if lines else "(no matches)"


def read_file_tool(path: str, start_line: int | None = None, end_line: int | None = None) -> str:
    try:
        full = os.path.join(_ROOT, path)
        with open(full, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        if start_line is not None or end_line is not None:
            s = (start_line or 1) - 1
            e = end_line or len(lines)
            lines = lines[s:e]
        text = "".join(lines)
        return text[:8000]  # bound the tool result so one huge file can't blow the token budget
    except (FileNotFoundError, IsADirectoryError, OSError) as exc:
        return f"error: {exc}"


def list_dir_tool(path: str = ".") -> str:
    try:
        full = os.path.join(_ROOT, path)
        entries = sorted(os.listdir(full))
        return "\n".join(entries[:200])
    except (FileNotFoundError, NotADirectoryError, OSError) as exc:
        return f"error: {exc}"


BASELINE_TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "grep_tool",
            "description": "Search the repository for a text pattern, returns matching file:line results.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "path": {"type": "string", "description": "subdirectory to search, default whole repo"},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file_tool",
            "description": "Read a file's contents, optionally a specific line range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "start_line": {"type": "integer"},
                    "end_line": {"type": "integer"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir_tool",
            "description": "List files and directories at a path.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": [],
            },
        },
    },
]
