"""Schema/consistency checks for questions_conceptual.json - the harder,
paraphrased-without-filenames counterpart to questions.json, meant to
actually exercise semantic search instead of letting grep solve the
question from its own vocabulary."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

with open(os.path.join(ROOT, "questions.json")) as f:
    _ORIGINAL_QUESTIONS = {q["id"]: q for q in json.load(f)}

with open(os.path.join(ROOT, "questions_conceptual.json")) as f:
    _CONCEPTUAL_QUESTIONS = json.load(f)


def test_every_conceptual_question_has_required_fields():
    for q in _CONCEPTUAL_QUESTIONS:
        for field in ("id", "counterpart_id", "question", "expected_key_facts", "rationale"):
            assert field in q, f"{q.get('id', '?')} missing {field!r}"
        assert isinstance(q["expected_key_facts"], list) and q["expected_key_facts"]


def test_every_counterpart_id_exists_in_the_original_question_set():
    for q in _CONCEPTUAL_QUESTIONS:
        assert q["counterpart_id"] in _ORIGINAL_QUESTIONS, (
            f"{q['id']} references counterpart_id {q['counterpart_id']!r}, "
            "which is not in questions.json"
        )


def test_expected_key_facts_match_the_original_question_verbatim():
    # The conceptual set rephrases the *question*, not the ground truth -
    # if a fact drifts from its counterpart, one of the two was edited by
    # mistake and they're no longer testing the same underlying claim.
    for q in _CONCEPTUAL_QUESTIONS:
        original = _ORIGINAL_QUESTIONS[q["counterpart_id"]]
        assert q["expected_key_facts"] == original["expected_key_facts"], q["id"]


def test_ids_are_unique():
    ids = [q["id"] for q in _CONCEPTUAL_QUESTIONS]
    assert len(ids) == len(set(ids))


def test_question_text_does_not_repeat_the_original_file_path():
    # Spot-check the specific thing this question set exists to fix: none
    # of the rewritten questions should still contain a literal .py path,
    # which would let a grep-only baseline solve it the old way.
    for q in _CONCEPTUAL_QUESTIONS:
        assert ".py" not in q["question"], f"{q['id']} still names a file path"
