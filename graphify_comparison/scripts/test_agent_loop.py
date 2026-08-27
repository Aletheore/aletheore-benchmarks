from unittest.mock import MagicMock

from agent_loop import run_one


def _fake_usage(prompt_tokens=100, completion_tokens=50):
    u = MagicMock()
    u.prompt_tokens = prompt_tokens
    u.completion_tokens = completion_tokens
    return u


def test_run_one_returns_immediately_when_model_answers_with_no_tool_calls():
    client = MagicMock()
    message = MagicMock(tool_calls=None, content="the answer is X")
    response = MagicMock(choices=[MagicMock(message=message)], usage=_fake_usage())
    client.chat.completions.create.return_value = response

    result = run_one("what is X?", "baseline", client)

    assert result["answer"] == "the answer is X"
    assert result["total_tokens"] == 150
    assert result["turns"] == 1


def test_run_one_accumulates_tokens_across_multiple_tool_call_turns():
    client = MagicMock()
    tool_call = MagicMock()
    tool_call.id = "call_1"
    tool_call.function.name = "grep_tool"
    tool_call.function.arguments = '{"pattern": "foo"}'

    turn1_message = MagicMock(tool_calls=[tool_call], content=None)
    turn1 = MagicMock(choices=[MagicMock(message=turn1_message)], usage=_fake_usage(100, 20))

    turn2_message = MagicMock(tool_calls=None, content="final answer")
    turn2 = MagicMock(choices=[MagicMock(message=turn2_message)], usage=_fake_usage(150, 30))

    client.chat.completions.create.side_effect = [turn1, turn2]

    result = run_one("where is foo?", "baseline", client)

    assert result["answer"] == "final answer"
    assert result["total_tokens"] == (100 + 20) + (150 + 30)
    assert result["turns"] == 2
