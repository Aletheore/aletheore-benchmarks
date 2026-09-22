"""Cheap variance check: scores both GLM generation runs (run1 = the
original generation_results.json already judged for real by gpt-5.2 at
0.149 overall; run2 = a fresh regeneration) with the free gpt-5-nano
judge instead of the paid gpt-5.2 judge, using the exact same harness
scoring code (judge.py/scorer.py/assembler.py/aggregate.py). Purpose:
(1) check whether gpt-5-nano lands near the real 0.149 number, as a
sanity check on using it as a proxy at all; (2) if it does, compare
nano-scored run1 vs nano-scored run2 for a real, same-judge variance
signal without paying for a second full gpt-5.2 pass."""
import json
import sys
from dataclasses import asdict
from pathlib import Path

HARNESS = Path("/private/tmp/claude-501/-Users-arihantkaul-Documents-GitHub-Veridion/c65c37d1-1c66-48a1-b854-55b49f0a16b2/scratchpad/swe_prbench/harness")
DATA = Path("/private/tmp/claude-501/-Users-arihantkaul-Documents-GitHub-Veridion/c65c37d1-1c66-48a1-b854-55b49f0a16b2/scratchpad/swe_prbench/data/dataset")
OUT_DIR = Path("/private/tmp/claude-501/-Users-arihantkaul-Documents-GitHub-Veridion/c65c37d1-1c66-48a1-b854-55b49f0a16b2/scratchpad/swe_prbench")

sys.path.insert(0, str(HARNESS))

from eval_harness.schema import AgentComment, AgentOutput, EvalInput  # noqa: E402
from eval_harness.judge import run_judge  # noqa: E402
from eval_harness.scorer import compute_dimension_scores  # noqa: E402
from eval_harness.assembler import assemble_eval_result  # noqa: E402
from eval_harness.aggregate import generate_eval_report  # noqa: E402
from eval_harness.model_clients import ModelRouter  # noqa: E402

eval_100 = json.loads((DATA / "evals" / "eval_100.json").read_text())
router = ModelRouter.from_config_file(str(OUT_DIR / "model_endpoints.yaml"))


def score_run(generation_path: str, model_name: str, out_prefix: str):
    generation = json.loads((OUT_DIR / generation_path).read_text())
    results = []
    errors = []
    for i, pr in enumerate(eval_100):
        task_id = pr["task_id"]
        gen = generation.get(task_id)
        if gen is None or gen.get("error"):
            errors.append({"task_id": task_id, "stage": "generation", "error": gen.get("error") if gen else "missing"})
            continue

        findings = gen["findings"]
        annotation = json.loads((DATA / "annotations" / f"{task_id}_human.json").read_text())
        comments = annotation.get("comments", [])
        sub_ids = set(annotation.get("substantive_comment_ids", []))
        human_comments = [c for c in comments if c.get("comment_id") in sub_ids] or [
            c for c in comments if c.get("is_initiating_comment")
        ]

        agent_comments = [
            AgentComment(
                comment_id=f"a_{j}",
                body=f"{f.get('issue','')} {f.get('suggestion','') or ''}".strip(),
                file_reference=f.get("file"),
                line_reference=f.get("line"),
                severity_claim=None,
                is_outside_diff=False,
            )
            for j, f in enumerate(findings)
        ]
        agent_output = AgentOutput(
            task_id=task_id,
            config_name="config_A_diff_only",
            model=model_name,
            raw_response=json.dumps(findings),
            comments=agent_comments,
            parse_success=True,
            parse_error=None,
        )
        eval_input = EvalInput(
            task_id=task_id,
            pr_number=pr["pr_number"],
            repo=pr["repo"],
            config_name="config_A_diff_only",
            rendered_context="",
            total_tokens=0,
            pipeline_version=pr.get("pipeline_version", ""),
            difficulty=pr.get("difficulty", ""),
            pr_type=pr.get("pr_type", ""),
            language=pr.get("language", ""),
            diff_patch=pr["diff_patch"],
            human_comments=human_comments,
            has_severity_annotations=any(c.get("severity") for c in human_comments),
        )

        try:
            judge_output = run_judge(eval_input, agent_output, "gpt_4o_mini_free", router)
            scores = compute_dimension_scores(eval_input, agent_output, judge_output)
            result = assemble_eval_result(eval_input, agent_output, judge_output, scores, model_name)
        except Exception as exc:  # noqa: BLE001
            print(f"[{out_prefix}][{i}] {task_id}: JUDGE/SCORE ERROR {type(exc).__name__}: {exc}", flush=True)
            errors.append({"task_id": task_id, "stage": "judge_or_score", "error": str(exc)})
            continue

        results.append(result)
        if (i + 1) % 20 == 0:
            print(f"[{out_prefix}] {i+1}/100 done", flush=True)

    (OUT_DIR / f"eval_results_final_{out_prefix}.json").write_text(json.dumps([asdict(r) for r in results], indent=2))
    (OUT_DIR / f"scoring_errors_{out_prefix}.json").write_text(json.dumps(errors, indent=2))
    report = generate_eval_report(results, str(OUT_DIR / f"eval_report_{out_prefix}.json"))
    print(f"\n=== {out_prefix}: scored {len(results)}/{len(eval_100)}, {len(errors)} errors ===")
    print(json.dumps(report.get("by_config", {}), indent=2))
    return report


print(">>> scoring GLM run3 (fresh regeneration) with nano judge")
score_run("generation_results_glm_run3.json", "aletheore_glm53flash_run3", "run3_nano")

print("\n>>> scoring GLM run4 (fresh regeneration) with nano judge")
score_run("generation_results_glm_run4.json", "aletheore_glm53flash_run4", "run4_nano")
