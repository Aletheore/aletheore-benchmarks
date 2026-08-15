import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _bench, os, re, sys, time
import httpx

KEY = _bench.require_key("DEEPSEEK_API_KEY")
MODEL = _bench.JUDGE_MODEL

# The corpus being graded. This was hard-coded to "Flask", which is correct for
# the single-corpus arm and wrong for every other repo: telling the judge that
# AutoMapper's C# came from Flask primes it against material that is in fact on
# topic. Set BENCH_REPO per corpus; the wording is otherwise unchanged, so a
# run with BENCH_REPO=Flask is identical to the published Flask numbers.
REPO = os.environ.get("BENCH_REPO", "Flask")

RUBRIC = """You are grading retrieval systems for a code-comprehension task.

A developer new to the __REPO__ codebase asked the QUESTION below. Two systems each
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
 "better": "a" | "b" | "tie"}""".replace("__REPO__", REPO)


def scrub(t):
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
            print(f"  retry {attempt}: {str(e)[:120]}", file=sys.stderr)
            time.sleep(3 * (attempt + 1))
    return None


import os
ARM=os.environ["ARM"]
# A per-corpus run points these at ~/.aletheore-bench/bench/multi_<name>/.
# The defaults reproduce the original single-corpus Flask behaviour exactly.
CTX = os.environ.get("BENCH_CTX", os.path.join(_bench.OUT, "arch_context2.json"))
SCORES_DIR = os.environ.get("BENCH_SCORES_DIR", _bench.OUT)
ctx = json.load(open(CTX))

# temperature=0 is not determinism: MoE routing and server-side batching make
# repeated identical requests return different scores. Measured on flask, the
# same bytes judged twice gave 2.29 and 2.08 - a 0.21 drift, the same size as
# the effects this harness is asked to resolve. Averaging R repeats cuts that
# by ~1/sqrt(R). judge_fallback_vs_repowise.py already did this; this arm did
# not. Cost is 2*R calls per question. See JUDGE_NOISE.md.
REPEATS = int(os.environ.get("JUDGE_REPEATS", "3"))

rows = []
for c in ctx:
    al, rw = scrub(c[ARM]), scrub(c["repowise"])
    a_scores, r_scores, pref, per_repeat, why_a, why_r = [], [], [], [], None, None
    for _ in range(REPEATS):
        # pass 1: aletheore = A ; pass 2: swapped, to cancel position bias
        r1 = ask(c["q"], al, rw)
        r2 = ask(c["q"], rw, al)
        if not r1 or not r2:
            continue
        a_pair = [r1["system_a"]["score"], r2["system_b"]["score"]]
        r_pair = [r1["system_b"]["score"], r2["system_a"]["score"]]
        a_scores += a_pair
        r_scores += r_pair
        per_repeat.append(sum(a_pair) / 2)
        pref.append({"a": "aletheore", "b": "repowise", "tie": "tie"}[r1["better"]])
        pref.append({"a": "repowise", "b": "aletheore", "tie": "tie"}[r2["better"]])
        if why_a is None:
            why_a, why_r = r1["system_a"]["why"], r1["system_b"]["why"]
    if not a_scores:
        print("FAILED", c["id"], file=sys.stderr)
        continue
    # Spread across repeats is this question's own noise, reported rather than
    # hidden so a delta can be checked against it instead of assumed to be real.
    spread = (max(per_repeat) - min(per_repeat)) if len(per_repeat) > 1 else 0.0
    rows.append({"id": c["id"], "q": c["q"],
                 "aletheore": sum(a_scores) / len(a_scores),
                 "repowise": sum(r_scores) / len(r_scores),
                 "aletheore_raw": a_scores, "repowise_raw": r_scores,
                 "repeats": len(per_repeat), "spread": spread,
                 "pref": pref, "why_a": why_a, "why_r": why_r})
    print(f"{c['id']}  aletheore={sum(a_scores)/len(a_scores):.2f} "
          f"repowise={sum(r_scores)/len(r_scores):.2f}  spread={spread:.2f} "
          f"({len(per_repeat)} repeats)", file=sys.stderr)

os.makedirs(SCORES_DIR, exist_ok=True)
json.dump(rows, open(os.path.join(SCORES_DIR,"arch_scores_"+ARM+".json"),"w"), indent=2)
n = len(rows)
if n:
    print(f"\nARCHITECTURE QUESTIONS (n={n}, 0-3 scale, order-swapped mean, "
          f"{REPEATS} repeats)", file=sys.stderr)
    print(f"  Aletheore : {sum(r['aletheore'] for r in rows)/n:.2f}", file=sys.stderr)
    print(f"  RepoWise  : {sum(r['repowise'] for r in rows)/n:.2f}", file=sys.stderr)
    spreads = [r["spread"] for r in rows]
    print(f"  judge spread across repeats: mean {sum(spreads)/n:.2f}, "
          f"max {max(spreads):.2f}  <- a delta smaller than this is not a result",
          file=sys.stderr)
    flat = [p for r in rows for p in r["pref"]]
    for k in ("aletheore", "repowise", "tie"):
        print(f"  pref {k}: {flat.count(k)}/{len(flat)}", file=sys.stderr)

