"""Anonymized single-candidate judge, adapted from
aletheore-benchmarks/pr_review/blind_judge.py's established pattern: never
tell the judge which tool produced an answer, score exactly one candidate
per call (a 2-3-arms-per-call design was already tried and found to
silently drop labels 53/97 times), 2 runs per item for the documented
judge-noise floor (0.2-0.375 drift observed on identical input before)."""
import json
import os
import sys
import time

JUDGE_MODEL = "deepseek-v4-flash"
JUDGE_RUNS = 2


def build_judge_prompt(expected_key_facts: list[str], answer: str) -> str:
    facts_block = "\n".join(f"- {f}" for f in expected_key_facts)
    return (
        "You are grading whether an answer about a codebase correctly "
        "captured the following expected facts:\n\n"
        f"{facts_block}\n\n"
        f"The answer to grade:\n{answer}\n\n"
        "For each expected fact, decide if the answer correctly captured it "
        "(does not need exact wording, just the same real fact). Respond "
        "with ONLY a JSON object: "
        '{"coverage": <fraction of facts matched, 0.0-1.0>, '
        '"facts_matched": [<bool per fact, same order>]}'
    )


def parse_judge_response(raw: str) -> float | None:
    try:
        parsed = json.loads(raw)
        return float(parsed["coverage"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None


def score_one(client, expected_key_facts: list[str], answer: str) -> float | None:
    prompt = build_judge_prompt(expected_key_facts, answer)
    response = client.chat.completions.create(
        model=JUDGE_MODEL, messages=[{"role": "user", "content": prompt}],
    )
    return parse_judge_response(response.choices[0].message.content)


def main() -> int:
    HERE = os.path.dirname(os.path.abspath(__file__))
    ROOT = os.path.dirname(HERE)
    sys.path.insert(0, os.path.join(ROOT, "..", "scripts"))
    from _bench import require_key
    from openai import OpenAI

    key = require_key("DEEPSEEK_API_KEY")
    client = OpenAI(base_url="https://api.deepseek.com", api_key=key)

    with open(os.path.join(ROOT, "questions.json")) as f:
        questions = {q["id"]: q for q in json.load(f)}
    with open(os.path.join(ROOT, "results", "harness_results.json")) as f:
        harness_results = json.load(f)

    results = []
    for run_idx in range(JUDGE_RUNS):
        for rec in harness_results:
            q = questions[rec["question_id"]]
            try:
                coverage = score_one(client, q["expected_key_facts"], rec["answer"])
                if coverage is None:
                    print(f"[run {run_idx}] {rec['question_id']}/{rec['condition']}: no usable score, retrying once", file=sys.stderr)
                    coverage = score_one(client, q["expected_key_facts"], rec["answer"])
            except Exception as exc:  # noqa: BLE001 - one bad item must not kill the whole run
                print(f"[run {run_idx}] {rec['question_id']}/{rec['condition']}: FAILED {type(exc).__name__}: {exc}", file=sys.stderr)
                coverage = None
            results.append({
                "run": run_idx,
                "question_id": rec["question_id"],
                "condition": rec["condition"],
                "coverage": coverage,
            })
            time.sleep(0.2)
        print(f"=== run {run_idx} complete ===", file=sys.stderr, flush=True)

    out_path = os.path.join(ROOT, "results", "judge_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    missing = sum(1 for r in results if r["coverage"] is None)
    print(f"done: {len(results)} scored, {missing} still missing after retry -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
