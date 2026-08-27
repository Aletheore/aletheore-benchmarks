"""Drives agent_loop.run_one across every (question, condition) pair,
writing raw results for judge.py to score. Real-money script (every call costs
real tokens) - run once deliberately, not repeatedly while iterating."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agent_loop import run_one
from baseline_tools import set_root
from aletheore_tool import set_aletheore_root
from graphify_tool import set_graphify_root
from clone_corpus import ensure_corpus
from setup_tools import smoke_test

CONDITIONS = ["baseline", "aletheore", "graphify"]
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def run_all(questions: list[dict], client) -> list[dict]:
    results = []
    for q in questions:
        for condition in CONDITIONS:
            print(f"running {q['id']} / {condition}...", file=sys.stderr)
            out = run_one(q["question"], condition, client)
            results.append({
                "question_id": q["id"],
                "condition": condition,
                "answer": out["answer"],
                "total_tokens": out["total_tokens"],
                "turns": out["turns"],
            })
    return results


def main() -> int:
    from openai import OpenAI
    sys.path.insert(0, os.path.join(ROOT, "..", "scripts"))
    from _bench import require_key

    smoke_test()
    checkout = ensure_corpus()
    set_root(checkout)
    set_aletheore_root(checkout)
    set_graphify_root(checkout)

    key = require_key("DEEPSEEK_API_KEY")
    client = OpenAI(base_url="https://api.deepseek.com", api_key=key)

    with open(os.path.join(ROOT, "questions.json")) as f:
        questions = json.load(f)

    results = run_all(questions, client)

    total_tokens = sum(r["total_tokens"] for r in results)
    print(f"\ndone: {len(results)} (question, condition) pairs, {total_tokens} total tokens", file=sys.stderr)

    out_path = os.path.join(ROOT, "results", "harness_results.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"written to {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
