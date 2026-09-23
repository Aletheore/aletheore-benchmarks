"""Real gpt-5.2 judge scoring (direct via OpenAI's own API) for the
per_file_completeness=True re-run - scores generation_results_perfile.json
against the same eval_100 human annotations the original run used."""
import json
import sys
from dataclasses import asdict
from pathlib import Path

HERE = Path(__file__).parent
HARNESS = HERE / "harness"
DATA = HERE / "data" / "dataset"

sys.path.insert(0, str(HARNESS))

from eval_harness.schema import AgentComment, AgentOutput, EvalInput  # noqa: E402
from eval_harness.judge import run_judge  # noqa: E402
from eval_harness.scorer import compute_dimension_scores  # noqa: E402
from eval_harness.assembler import assemble_eval_result  # noqa: E402
from eval_harness.aggregate import generate_eval_report  # noqa: E402
from eval_harness.model_clients import ModelRouter  # noqa: E402

MODEL_NAME = "aletheore_glm53flash_perfile_openrouter"

eval_100 = json.loads((DATA / "evals" / "eval_100.json").read_text())
generation = json.loads((HERE / "generation_results_perfile.json").read_text())
router = ModelRouter.from_config_file(str(HERE / "model_endpoints.yaml"))

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
        model=MODEL_NAME,
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
        judge_output = run_judge(eval_input, agent_output, "gpt_5_2", router)
        scores = compute_dimension_scores(eval_input, agent_output, judge_output)
        result = assemble_eval_result(eval_input, agent_output, judge_output, scores, MODEL_NAME)
    except Exception as exc:  # noqa: BLE001
        print(f"[{i}] {task_id}: JUDGE/SCORE ERROR {type(exc).__name__}: {exc}", flush=True)
        errors.append({"task_id": task_id, "stage": "judge_or_score", "error": str(exc)})
        continue

    results.append(result)
    print(
        f"[{i}] {task_id}: recall={result.recall:.3f} precision={result.precision:.3f} "
        f"f1={result.f1_score:.3f} caught={result.caught_human_comments}/{result.total_human_comments} "
        f"agent_comments={result.total_agent_comments}",
        flush=True,
    )

    if (i + 1) % 10 == 0:
        (HERE / "eval_results_partial_perfile_openrouter.json").write_text(
            json.dumps([asdict(r) for r in results], indent=2)
        )

(HERE / "eval_results_final_perfile_openrouter.json").write_text(json.dumps([asdict(r) for r in results], indent=2))
(HERE / "scoring_errors_perfile_openrouter.json").write_text(json.dumps(errors, indent=2))

report = generate_eval_report(results, str(HERE / "eval_report_perfile_openrouter.json"))
print("\n=== AGGREGATE REPORT (per_file_completeness=True, gpt-5.2 direct via OpenAI) ===")
print(json.dumps(report, indent=2)[:3000])
print(f"\nscored {len(results)}/{len(eval_100)}, {len(errors)} errors")
