"""Subprocess wrapper around `aletheore query`, restricted to the
deterministic structural kinds (never `answer`, which runs Aletheore's own
internal LLM call and would corrupt this benchmark's own token accounting).
"""
import subprocess

_ROOT = "."
_ALLOWED_KINDS = {"search-codebase", "symbol-source", "symbols", "imports", "imported-by"}


def set_aletheore_root(root: str) -> None:
    global _ROOT
    _ROOT = root


def aletheore_query_tool(kind: str, target: str = "", symbol: str = "") -> str:
    if kind not in _ALLOWED_KINDS:
        return f"error: kind must be one of {sorted(_ALLOWED_KINDS)}, got {kind!r}"
    cmd = ["aletheore", "query", kind]
    if target:
        cmd.append(target)
    if symbol:
        cmd.append(symbol)
    cmd += ["--path", _ROOT]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            return f"error: {result.stderr.strip()}"
        return result.stdout[:8000]
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        return f"error: {exc}"


ALETHEORE_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "aletheore_query_tool",
        "description": (
            "Query Aletheore's deterministic code graph for the repository: "
            "search-codebase (semantic search), symbol-source (read one symbol's "
            "exact source), symbols/imports/imported-by (structural relationships)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "kind": {
                    "type": "string",
                    "enum": sorted(_ALLOWED_KINDS),
                },
                "target": {"type": "string", "description": "file path or search text, depending on kind"},
                "symbol": {"type": "string", "description": "symbol name, only for symbol-source"},
            },
            "required": ["kind"],
        },
    },
}
