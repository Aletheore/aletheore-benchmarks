from unittest.mock import patch

from run_harness import run_all


def test_run_all_produces_one_record_per_question_per_condition():
    questions = [{"id": "q01", "question": "test?"}, {"id": "q02", "question": "test2?"}]

    def fake_run_one(question, condition, client):
        return {"answer": f"answer for {condition}", "total_tokens": 10, "turns": 1}

    with patch("run_harness.run_one", side_effect=fake_run_one):
        results = run_all(questions, client=object())

    assert len(results) == 6  # 2 questions x 3 conditions
    conditions_seen = {r["condition"] for r in results}
    assert conditions_seen == {"baseline", "aletheore", "graphify"}
    ids_seen = {r["question_id"] for r in results}
    assert ids_seen == {"q01", "q02"}
