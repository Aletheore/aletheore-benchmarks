from unittest.mock import MagicMock

from judge import build_judge_prompt, parse_judge_response, score_one


def test_build_judge_prompt_includes_facts_and_answer_anonymized():
    prompt = build_judge_prompt(
        expected_key_facts=["fact one", "fact two"],
        answer="the answer text",
    )
    assert "fact one" in prompt
    assert "fact two" in prompt
    assert "the answer text" in prompt
    assert "aletheore" not in prompt.lower()
    assert "graphify" not in prompt.lower()


def test_parse_judge_response_extracts_coverage_float():
    raw = '{"coverage": 0.5, "facts_matched": [true, false]}'
    assert parse_judge_response(raw) == 0.5


def test_score_one_calls_client_and_returns_coverage():
    client = MagicMock()
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content='{"coverage": 1.0, "facts_matched": [true]}'))]
    client.chat.completions.create.return_value = response

    result = score_one(client, expected_key_facts=["fact"], answer="text mentioning fact")
    assert result == 1.0
