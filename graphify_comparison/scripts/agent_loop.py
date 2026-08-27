"""The tool-calling loop every condition shares - only which extra tool is
registered changes between baseline/+aletheore/+graphify. Bounded to
MAX_TURNS so a model that never converges on a final answer can't run away
with the budget."""
import json

from baseline_tools import (
    BASELINE_TOOL_SCHEMAS,
    grep_tool,
    read_file_tool,
    list_dir_tool,
)
from aletheore_tool import ALETHEORE_TOOL_SCHEMA, aletheore_query_tool
from graphify_tool import GRAPHIFY_TOOL_SCHEMA, graphify_query_tool

MODEL = "deepseek-v4-flash"
MAX_TURNS = 8

_TOOL_FUNCTIONS = {
    "grep_tool": grep_tool,
    "read_file_tool": read_file_tool,
    "list_dir_tool": list_dir_tool,
    "aletheore_query_tool": aletheore_query_tool,
    "graphify_query_tool": graphify_query_tool,
}


def _schemas_for(condition: str) -> list[dict]:
    if condition == "baseline":
        return list(BASELINE_TOOL_SCHEMAS)
    if condition == "aletheore":
        return list(BASELINE_TOOL_SCHEMAS) + [ALETHEORE_TOOL_SCHEMA]
    if condition == "graphify":
        return list(BASELINE_TOOL_SCHEMAS) + [GRAPHIFY_TOOL_SCHEMA]
    raise ValueError(f"condition must be baseline/aletheore/graphify, got {condition!r}")


SYSTEM_PROMPT = (
    "You are answering a factual question about a real codebase using the "
    "tools available to you. Use as many tool calls as you need to find the "
    "real answer - do not guess. When you are confident, respond with your "
    "final answer as plain text with no further tool calls, citing the exact "
    "file (and function/class name, if relevant) your answer is based on."
)


def run_one(question: str, condition: str, client) -> dict:
    tools = _schemas_for(condition)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    total_tokens = 0
    turns = 0

    while turns < MAX_TURNS:
        turns += 1
        response = client.chat.completions.create(
            model=MODEL, messages=messages, tools=tools,
        )
        usage = response.usage
        total_tokens += usage.prompt_tokens + usage.completion_tokens
        message = response.choices[0].message

        if not message.tool_calls:
            return {"answer": message.content, "total_tokens": total_tokens, "turns": turns}

        messages.append(message)
        for call in message.tool_calls:
            fn = _TOOL_FUNCTIONS[call.function.name]
            args = json.loads(call.function.arguments)
            try:
                result = fn(**args)
            except Exception as exc:  # noqa: BLE001 - a bad tool call must not kill the whole run
                result = f"error calling {call.function.name}: {exc}"
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": str(result),
            })

    return {
        "answer": "(no final answer - hit MAX_TURNS)",
        "total_tokens": total_tokens,
        "turns": turns,
    }
