"""Integrity checks + bootstrap 95% CIs (resampling the 13 PRs) over the gpt-6-luna judged results.
Run: python3 audit_bootstrap.py . Greptile is omitted (results redacted pending vendor consent)."""
import json, os, random
from collections import Counter
from pathlib import Path
R=str(Path(__file__).resolve().parent.parent/"results")+"/"
def tallies(path, arm):
    d=json.load(open(R+path))[arm]; out={}
    for case,e in d.items():
        r=e["reconciled"]; g=r["golden"]; f=r.get("findings") or {}
        c=Counter(x["status"] for x in f.values())
        out[case]=dict(golden=len(g), hits=sum(x["status"]=="confirmed_hit" for x in g.values()),
                       insufficient=sum(x["status"]=="insufficient_data" for x in g.values()),
                       n=len(e["findings"]), labelled=len(f), ok=c["golden_associated"]+c["confirmed_TP"],
                       fp=c["confirmed_FP"], naf=c["confirmed_not_a_finding"], disputed=c["disputed"])
    return out
ARMS={ # name -> list of (file, arm) generation trials
 "flash no-ctx":[("judged_gen_ctrl_A.json","aletheore-flash"),("judged_gen_ctrl_B.json","aletheore-flash")],
 "flash +ctx":[("judged_gen_ctx_A.json","aletheore-flash"),("judged_gen_ctx_B.json","aletheore-flash")],
 "air +ctx":[("judged_gen_air_ctx_A.json","aletheore-air"),("judged_gen_air_ctx_B.json","aletheore-air")],
 "gitlab":[("judged_gpt6luna_run1.json","gitlab")],
 "qodo":[("judged_gpt6luna_run1.json","qodo-v2-2")],"copilot":[("judged_gpt6luna_run1.json","copilot-v2")],
}
if os.path.exists(R+"judged_base_air_t1.json"):
    ARMS["air no-ctx (3 gens)"]=[("judged_gpt6luna_run1.json","aletheore-air"),("judged_base_air_t1.json","aletheore-air"),("judged_base_air_t2.json","aletheore-air")]
data={k:[tallies(p,a) for p,a in v] for k,v in ARMS.items()}
cases=sorted(next(iter(data.values()))[0])
# ---- integrity
print("INTEGRITY")
for k,trials in data.items():
    for i,t in enumerate(trials):
        assert sorted(t)==cases,(k,"case set differs")
        bad=[c for c,x in t.items() if x["labelled"]!=x["n"]]
        gold=sum(x["golden"] for x in t.values()); ins=sum(x["insufficient"] for x in t.values())
        print(f"  {k:20s} t{i}: golden={gold} insufficient={ins} findings={sum(x['n'] for x in t.values())} unlabelled_cases={bad}")
# ---- metrics + bootstrap over cases
def metric(trials, idx):
    rec=[];pre=[]
    for t in trials:
        h=sum(t[c]["hits"] for c in idx); g=sum(t[c]["golden"] for c in idx)
        ok=sum(t[c]["ok"] for c in idx); den=sum(t[c]["n"]-t[c]["naf"] for c in idx)
        rec.append(h/g if g else 0); pre.append(ok/den if den else 0)
    return sum(rec)/len(rec), sum(pre)/len(pre)
random.seed(7); B=5000
boot={k:[] for k in data}
samples=[[random.choice(cases) for _ in cases] for _ in range(B)]
for k,trials in data.items():
    boot[k]=[metric(trials,s) for s in samples]
def ci(xs):
    xs=sorted(xs); return xs[int(.025*len(xs))],xs[int(.975*len(xs))]
print("\nMETRICS (mean over generation trials; 95% CI from resampling the 13 PRs)")
for k,trials in data.items():
    r,p=metric(trials,cases); rc=ci([b[0] for b in boot[k]]); pc=ci([b[1] for b in boot[k]])
    print(f"  {k:20s} recall {100*r:5.1f}% [{100*rc[0]:.0f}-{100*rc[1]:.0f}]   precision {100*p:5.1f}% [{100*pc[0]:.0f}-{100*pc[1]:.0f}]")
def diff(a,b,j):
    xs=[x[j]-y[j] for x,y in zip(boot[a],boot[b])]; lo,hi=ci(xs); return 100*sum(xs)/len(xs),100*lo,100*hi,sum(1 for x in xs if x>0)/len(xs)
print("\nPAIRED DIFFERENCES (same resampled PRs; a minus b, points, 95% CI, P(a>b))")
pairs=[("flash +ctx","flash no-ctx"),("flash +ctx","gitlab"),("air +ctx","flash +ctx"),("air +ctx","gitlab")]
if "air no-ctx (3 gens)" in data: pairs.insert(3,("air +ctx","air no-ctx (3 gens)"))
for a,b in pairs:
    for j,name in ((0,"recall"),(1,"precision")):
        m,lo,hi,pg=diff(a,b,j); print(f"  {a} - {b:22s} {name:9s} {m:+5.1f} [{lo:+.1f}, {hi:+.1f}]  P(>0)={pg:.2f}")

print("\nEXTRA per-run averages")
for k,trials in data.items():
    n=sum(sum(x["n"] for x in t.values()) for t in trials)/len(trials)
    fp=sum(sum(x["fp"] for x in t.values()) for t in trials)/len(trials)
    dis=sum(sum(x["disputed"] for x in t.values()) for t in trials)/len(trials)
    hits=sum(sum(x["hits"] for x in t.values()) for t in trials)/len(trials)
    print(f"  {k:20s} trials={len(trials)} findings={n:.0f} confirmedFP={fp:.1f} disputed={dis:.1f} hits={hits:.1f}/44")
