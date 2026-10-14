"""Experiment 9: recompute the production-configuration table from the committed result files.
No API key, no network. Same tallies and bootstrap as audit_bootstrap.py (5,000 draws resampling the
13 PRs, seed 7; per-PR value is the mean over generation trials).
Run: python3 score_production_rerun.py"""
import json
import random
from collections import Counter
from pathlib import Path

R = Path(__file__).resolve().parent.parent / "results"
P = R / "production_rerun_2026-10-14"


def tallies(path, arm):
    d = json.load(open(path))[arm]
    out = {}
    for case, e in d.items():
        r = e["reconciled"]
        g = r["golden"]
        f = r.get("findings") or {}
        c = Counter(x["status"] for x in f.values())
        out[case] = dict(
            golden=len(g), hits=sum(x["status"] == "confirmed_hit" for x in g.values()),
            insufficient=sum(x["status"] == "insufficient_data" for x in g.values()),
            n=len(e["findings"]), labelled=len(f), ok=c["golden_associated"] + c["confirmed_TP"],
            fp=c["confirmed_FP"], naf=c["confirmed_not_a_finding"], disputed=c["disputed"])
    return out


ARMS = {
    "Flash, production config": [(P / f"judged_prod_t{i}.json", "aletheore-flash") for i in range(1, 5)],
    "Flash, production config, before gate": [(P / f"judged_prod_before_gate_t{i}.json", "aletheore-flash") for i in range(1, 5)],
    "Flash, Experiment 8 (shared context)": [(R / "judged_gen_ctx_A.json", "aletheore-flash"), (R / "judged_gen_ctx_B.json", "aletheore-flash")],
    "Copilot": [(R / "judged_gpt6luna_run1.json", "copilot-v2")],
    "GitLab Duo": [(R / "judged_gpt6luna_run1.json", "gitlab")],
    "Qodo": [(R / "judged_gpt6luna_run1.json", "qodo-v2-2")],
}
data = {k: [tallies(p, a) for p, a in v] for k, v in ARMS.items()}
cases = sorted(next(iter(data.values()))[0])
print("INTEGRITY")
for k, trials in data.items():
    for i, t in enumerate(trials):
        assert sorted(t) == cases, (k, "case set differs")
        bad = [c for c, x in t.items() if x["labelled"] != x["n"]]
        print(f"  {k:40s} t{i}: golden={sum(x['golden'] for x in t.values())} insufficient={sum(x['insufficient'] for x in t.values())} "
              f"findings={sum(x['n'] for x in t.values())} unlabelled={bad}")


def metric(trials, idx):
    rec, pre = [], []
    for t in trials:
        h = sum(t[c]["hits"] for c in idx)
        g = sum(t[c]["golden"] for c in idx)
        ok = sum(t[c]["ok"] for c in idx)
        den = sum(t[c]["n"] - t[c]["naf"] for c in idx)
        rec.append(h / g if g else 0)
        pre.append(ok / den if den else 0)
    return sum(rec) / len(rec), sum(pre) / len(pre)


random.seed(7)
B = 5000
samples = [[random.choice(cases) for _ in cases] for _ in range(B)]  # nosec B311 - bootstrap resampling, not security
boot = {k: [metric(tr, s) for s in samples] for k, tr in data.items()}


def ci(xs):
    xs = sorted(xs)
    return xs[int(.025 * len(xs))], xs[int(.975 * len(xs))]


print("\nMETRICS (mean over generation trials; 95% CI resampling the 13 PRs)")
for k, tr in data.items():
    r, p = metric(tr, cases)
    rc = ci([b[0] for b in boot[k]])
    pc = ci([b[1] for b in boot[k]])
    print(f"  {k:40s} recall {100*r:5.1f}% [{100*rc[0]:.0f}-{100*rc[1]:.0f}]   precision {100*p:5.1f}% [{100*pc[0]:.0f}-{100*pc[1]:.0f}]")

print("\nPAIRED (a minus b, points, 95% CI)")
A = "Flash, production config"
for b in ["Flash, Experiment 8 (shared context)", "Flash, production config, before gate", "Copilot", "GitLab Duo", "Qodo"]:
    for j, name in ((0, "recall"), (1, "precision")):
        xs = [x[j] - y[j] for x, y in zip(boot[A], boot[b])]
        lo, hi = ci(xs)
        print(f"  production - {b:40s} {name:9s} {100*sum(xs)/len(xs):+5.1f} [{100*lo:+.1f}, {100*hi:+.1f}]")

print("\nPER-RUN AVERAGES")
for k, tr in data.items():
    f = lambda key: sum(sum(x[key] for x in t.values()) for t in tr) / len(tr)
    real = sum(sum(x["n"] - x["naf"] for x in t.values()) for t in tr) / len(tr)
    print(f"  {k:40s} bugs caught {f('hits'):.1f}/44  accurate {f('ok'):.1f}  real findings {real:.1f}  confirmed FP {f('fp'):.1f}  disputed {f('disputed'):.1f}")
