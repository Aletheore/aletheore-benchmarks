"""Blind pairwise judge: Aletheore's deterministic AIRview file fallback
(github-app, commit 7089e14) against RepoWise's get_context(), on flask files
with no AIRview page. Equal character budget per file (both truncated to the
shorter of the two). Same rubric, scrub, and position-swap-to-cancel-bias
pattern as judge_arch.py. 3 repeats, reporting the within-run gap rather than
a single absolute score.

Two file sets, selected before the scores were seen:

  fallback_files_7  - files where BOTH systems return substantive material.
                      This is the comparison the README headlines.
  fallback_files_15 - config/CI/docs/lockfiles. RepoWise reports these as
                      out of scope ("empty or non-symbol file" / "Target not
                      found"), so its 0.0s here are a COVERAGE result and must
                      not be pooled with the 7-file scores into a quality gap.

Re-judging needs a DEEPSEEK_API_KEY. Re-deriving the published numbers from
the saved rows does not - use score_fallback_judge.py for that.

    DEEPSEEK_API_KEY=... python3 scripts/judge_fallback_vs_repowise.py \\
        --set 7   # or --set 15
"""
import json, os, re, sys, time
import httpx

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _bench

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

KEY = os.environ.get("DEEPSEEK_API_KEY")
if not KEY:
    sys.exit("DEEPSEEK_API_KEY is not set. To re-derive the published numbers "
             "without a key, run: python3 scripts/score_fallback_judge.py")
MODEL = _bench.JUDGE_MODEL

RUBRIC = """You are grading retrieval systems for a code-comprehension task.

A developer new to the Flask codebase asked the QUESTION below. Two systems each
returned a bundle of retrieved material (roughly equal length). You are grading
ONLY the retrieved material — not writing the answer yourself.

For each system, score how well its material would let a competent engineer write
a correct, specific answer to the question:

3 = fully sufficient; covers the key mechanisms with specifics
2 = mostly sufficient; minor gaps a reader could bridge
1 = partially relevant; major gaps or mostly tangential
0 = irrelevant or misleading

Judge substance, not format. Prose is not automatically better than code, and code
is not automatically better than prose. Ignore which system appears first.

Return ONLY strict JSON:
{"system_a": {"score": <0-3>, "why": "<one sentence>"},
 "system_b": {"score": <0-3>, "why": "<one sentence>"},
 "better": "a" | "b" | "tie"}"""


def scrub(t):
    if t is None:
        return "(no material returned)"
    t = re.sub(r"(?i)repowise", "the tool", t)
    t = re.sub(r"(?i)aletheore", "the tool", t)
    return t


def ask(question, a, b):
    body = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": RUBRIC},
            {"role": "user", "content":
                f"QUESTION:\n{question}\n\n=== SYSTEM A MATERIAL ===\n{a}\n\n"
                f"=== SYSTEM B MATERIAL ===\n{b}"},
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    for attempt in range(4):
        try:
            r = httpx.post("https://api.deepseek.com/chat/completions",
                            headers={"Authorization": f"Bearer {KEY}"},
                            json=body, timeout=300)
            r.raise_for_status()
            return json.loads(r.json()["choices"][0]["message"]["content"])
        except Exception as e:
            print(f"    retry {attempt}: {str(e)[:120]}", file=sys.stderr)
            time.sleep(3 * (attempt + 1))
    return None


SET = "7"
if "--set" in sys.argv:
    SET = sys.argv[sys.argv.index("--set") + 1]
if SET not in ("7", "15"):
    sys.exit("--set must be 7 or 15")

questions = json.load(open(os.path.join(ROOT, f"questions/fallback_files_{SET}.json")))
fallback = json.load(open(os.path.join(ROOT, f"results/fallback_context_{SET}files.json")))
repowise = json.load(open(os.path.join(ROOT, f"results/repowise_context_{SET}files.json")))

files = list(questions.keys())

# Equal character budget per file: truncate both to the shorter of the two.
budgeted = {}
for f in files:
    a_text, b_text = fallback.get(f), repowise.get(f)
    a_len = len(a_text) if a_text else 0
    b_len = len(b_text) if b_text else 0
    budget = min(a_len, b_len) if a_len and b_len else max(a_len, b_len)
    budgeted[f] = {
        "fallback": (a_text[:budget] if a_text else a_text),
        "repowise": (b_text[:budget] if b_text else b_text),
        "budget": budget,
    }

N_REPEATS = 3
all_repeats = []

for repeat_idx in range(1, N_REPEATS + 1):
    print(f"\n=== REPEAT {repeat_idx}/{N_REPEATS} ===", file=sys.stderr)
    rows = []
    for f in files:
        q = questions[f]
        fb, rw = scrub(budgeted[f]["fallback"]), scrub(budgeted[f]["repowise"])
        # pass 1: fallback = A ; pass 2: swapped, to cancel position bias
        r1 = ask(q, fb, rw)
        r2 = ask(q, rw, fb)
        if not r1 or not r2:
            print(f"  FAILED {f}", file=sys.stderr)
            continue
        fb_scores = [r1["system_a"]["score"], r2["system_b"]["score"]]
        rw_scores = [r1["system_b"]["score"], r2["system_a"]["score"]]
        pref = []
        pref.append({"a": "fallback", "b": "repowise", "tie": "tie"}[r1["better"]])
        pref.append({"a": "repowise", "b": "fallback", "tie": "tie"}[r2["better"]])
        row = {
            "file": f, "q": q, "budget_chars": budgeted[f]["budget"],
            "fallback": sum(fb_scores) / 2, "repowise": sum(rw_scores) / 2,
            "fallback_raw": fb_scores, "repowise_raw": rw_scores,
            "pref": pref,
            "why_fallback": r1["system_a"]["why"], "why_repowise": r1["system_b"]["why"],
        }
        rows.append(row)
        print(f"  {f}: fallback={row['fallback']:.1f} repowise={row['repowise']:.1f} pref={pref}",
              file=sys.stderr)

    n = len(rows)
    fallback_mean = sum(r["fallback"] for r in rows) / n if n else 0.0
    repowise_mean = sum(r["repowise"] for r in rows) / n if n else 0.0
    gap = fallback_mean - repowise_mean
    all_repeats.append({"repeat": repeat_idx, "rows": rows,
                         "fallback_mean": fallback_mean, "repowise_mean": repowise_mean,
                         "gap": gap})
    print(f"REPEAT {repeat_idx}: fallback={fallback_mean:.3f} repowise={repowise_mean:.3f} gap={gap:+.3f}",
          file=sys.stderr)

out_path = os.path.join(ROOT, f"results/fallback_vs_repowise_scores_{SET}files.json")
json.dump(all_repeats, open(out_path, "w"), indent=2)

gaps = [r["gap"] for r in all_repeats]
mean_gap = sum(gaps) / len(gaps)
spread = max(gaps) - min(gaps)
print(f"\n=== SUMMARY (n={len(files)} files, {N_REPEATS} repeats, 0-3 scale, order-swapped) ===", file=sys.stderr)
for r in all_repeats:
    print(f"  repeat {r['repeat']}: fallback={r['fallback_mean']:.3f} repowise={r['repowise_mean']:.3f} gap={r['gap']:+.3f}",
          file=sys.stderr)
print(f"  mean gap (fallback - repowise): {mean_gap:+.3f}", file=sys.stderr)
print(f"  spread across repeats: {spread:.3f}", file=sys.stderr)
