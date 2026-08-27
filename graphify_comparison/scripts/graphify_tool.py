"""Subprocess wrapper around Graphify's three query commands - the direct
counterpart to aletheore_tool.py, same shape, so the two conditions are as
symmetric as the two products actually are."""
import subprocess

_ROOT = "."


def set_graphify_root(root: str) -> None:
    global _ROOT
    _ROOT = root


def graphify_query_tool(mode: str, query: str = "", a: str = "", b: str = "", x: str = "") -> str:
    if mode == "query":
        if not query:
            return "error: mode='query' requires query to be set"
        cmd = ["graphify", "query", query]
    elif mode == "path":
        if not a or not b:
            return "error: mode='path' requires both a and b to be set"
        cmd = ["graphify", "path", a, b]
    elif mode == "explain":
        if not x:
            return "error: mode='explain' requires x to be set"
        cmd = ["graphify", "explain", x]
    else:
        return f"error: mode must be one of query/path/explain, got {mode!r}"
    try:
        result = subprocess.run(cmd, cwd=_ROOT, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            return f"error: {result.stderr.strip()}"
        return result.stdout[:8000]
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        return f"error: {exc}"


GRAPHIFY_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "graphify_query_tool",
        "description": (
            "Query Graphify's knowledge graph for the repository: "
            "query (natural-language graph question), path (trace connection "
            "between two files/symbols), explain (detailed info on one target)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "mode": {"type": "string", "enum": ["query", "path", "explain"]},
                "query": {"type": "string", "description": "only for mode=query"},
                "a": {"type": "string", "description": "only for mode=path"},
                "b": {"type": "string", "description": "only for mode=path"},
                "x": {"type": "string", "description": "only for mode=explain"},
            },
            "required": ["mode"],
        },
    },
}
