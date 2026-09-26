from unittest.mock import patch

from run_harness import run_all


def test_run_all_produces_one_record_per_question_per_condition():
    questions = [{"id": "q01", "question": "test?"}, {"id": "q02", "question": "test2?"}]

    def fake_run_one(question, condition, client):
        return {"answer": f"answer for {condition}", "total_tokens": 10, "turns": 1, "tool_calls": []}

    with patch("run_harness.run_one", side_effect=fake_run_one):
        results = run_all(questions, client=object())

    assert len(results) == 6  # 2 questions x 3 conditions
    conditions_seen = {r["condition"] for r in results}
    assert conditions_seen == {"baseline", "aletheore", "graphify"}
    ids_seen = {r["question_id"] for r in results}
    assert ids_seen == {"q01", "q02"}


def test_run_all_carries_through_tool_calls_log():
    questions = [{"id": "q01", "question": "test?"}]

    def fake_run_one(question, condition, client):
        return {
            "answer": "a",
            "total_tokens": 10,
            "turns": 1,
            "tool_calls": [{"tool": "aletheore_query_tool", "kind": "search-codebase"}],
        }

    with patch("run_harness.run_one", side_effect=fake_run_one):
        results = run_all(questions, client=object())

    assert all(r["tool_calls"] == [{"tool": "aletheore_query_tool", "kind": "search-codebase"}] for r in results)


def test_run_all_defaults_tool_calls_to_empty_list_when_absent():
    questions = [{"id": "q01", "question": "test?"}]

    def fake_run_one(question, condition, client):
        return {"answer": "a", "total_tokens": 10, "turns": 1}  # no tool_calls key

    with patch("run_harness.run_one", side_effect=fake_run_one):
        results = run_all(questions, client=object())

    assert all(r["tool_calls"] == [] for r in results)
