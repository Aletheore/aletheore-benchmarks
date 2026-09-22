"""Smoke test: full pipeline (Aletheore generation via free-tier for speed,
real judge via gpt-5.2/OpenRouter) on 2 real SWE-PRBench tasks, before
committing to the full 100-PR paid-judge run."""
import json
import re
import sys
from pathlib import Path

VERIDION = Path("/Users/arihantkaul/Documents/GitHub/Veridion/github-app")
HARNESS = Path("/private/tmp/claude-501/-Users-arihantkaul-Documents-GitHub-Veridion/c65c37d1-1c66-48a1-b854-55b49f0a16b2/scratchpad/swe_prbench/harness")
DATA = Path("/private/tmp/claude-501/-Users-arihantkaul-Documents-GitHub-Veridion/c65c37d1-1c66-48a1-b854-55b49f0a16b2/scratchpad/swe_prbench/data/dataset")

sys.path.insert(0, str(VERIDION))
sys.path.insert(0, str(HARNESS))

from scan_worker.flash_review import review_diff  # noqa: E402
from scan_worker.model_tiers import writing_adapter_chain_for_free_tier  # noqa: E402
import redis  # noqa: E402

from eval_harness.schema import AgentComment, AgentOutput, EvalInput  # noqa: E402
from eval_harness.judge import run_judge  # noqa: E402
from eval_harness.scorer import compute_dimension_scores  # noqa: E402
from eval_harness.assembler import assemble_eval_result  # noqa: E402
from eval_harness.model_clients import ModelRouter  # noqa: E402


def diff_patches_from_diff(diff_text: str) -> tuple[tuple[str, str], ...]:
    sections = re.split(r"(?=^diff --git )", diff_text, flags=re.MULTILINE)
    patches = []
    for section in sections:
        m = re.match(r"^diff --git a/(.+?) b/(.+)$", section, re.MULTILINE)
        if not m:
            continue
        lines = section.splitlines()
        body_start = next((i for i, line in enumerate(lines) if line.startswith("@@")), None)
        body = "\n".join(lines[body_start:]) if body_start is not None else ""
        patches.append((m.group(2), body))
    return tuple(patches)


eval_100 = json.loads((DATA / "evals" / "eval_100.json").read_text())
tasks = eval_100[:2]

redis_conn = redis.Redis.from_url("redis://localhost:6379/0", socket_connect_timeout=2, socket_timeout=2)
router = ModelRouter.from_config_file(str(Path(__file__).parent / "model_endpoints.yaml"))

for pr in tasks:
    task_id = pr["task_id"]
    print(f"=== {task_id} ===")
    diff_text = pr["diff_patch"]
    patches = diff_patches_from_diff(diff_text)
    production_diff_text = "\n\n".join(f"--- {f} ---\n{p}" for f, p in patches)

    annotation = json.loads((DATA / "annotations" / f"{task_id}_human.json").read_text())
    comments = annotation.get("comments", [])
    sub_ids = set(annotation.get("substantive_comment_ids", []))
    human_comments = [c for c in comments if c.get("comment_id") in sub_ids] or [
        c for c in comments if c.get("is_initiating_comment")
    ]

    chain = writing_adapter_chain_for_free_tier(redis_conn)
    findings = review_diff(
        production_diff_text,
        pr_title=pr.get("title", ""),
        diff_patches=patches,
        adapter_chain=chain,
        verify_with_second_model=False,
    )
    print(f"  Aletheore findings: {len(findings)}")

    agent_comments = [
        AgentComment(
            comment_id=f"a_{i}",
            body=f"{f.get('issue','')} {f.get('suggestion','') or ''}".strip(),
            file_reference=f.get("file"),
            line_reference=f.get("line"),
            severity_claim=None,
            is_outside_diff=False,
        )
        for i, f in enumerate(findings)
    ]
    agent_output = AgentOutput(
        task_id=task_id,
        config_name="config_A_diff_only",
        model="aletheore_glm53flash",
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
        diff_patch=diff_text,
        human_comments=human_comments,
        has_severity_annotations=any(c.get("severity") for c in human_comments),
    )

    judge_output = run_judge(eval_input, agent_output, "gpt_5_2", router)
    print(f"  judge agent_classifications: {len(judge_output.agent_classifications)}")
    print(f"  judge human_comment_statuses: {len(judge_output.human_comment_statuses)}")

    scores = compute_dimension_scores(eval_input, agent_output, judge_output)
    result = assemble_eval_result(eval_input, agent_output, judge_output, scores, "aletheore_glm53flash")
    print(f"  recall={result.recall:.3f} precision={result.precision:.3f} f1={result.f1_score:.3f} "
          f"caught={result.caught_human_comments}/{result.total_human_comments}")

print("\nsmoke test done")
