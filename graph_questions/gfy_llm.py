"""Graphify extract WITH the LLM pass (docs/papers) via IndieRouter deepseek-v4.1-flash. Usage: gfy_llm.py repo [repo ...]"""
import json, os, subprocess, sys, time
S = os.path.dirname(os.path.abspath(__file__)) + "/"
env = dict(os.environ)  # the provider is registered once with: graphify provider add indierouter --base-url https://api.indierouter.ai/v1
#   --default-model deepseek-v4.1-flash --env-key INDIEROUTER_API_KEY ; set INDIEROUTER_API_KEY in the environment
if "INDIEROUTER_API_KEY" not in env:
    sys.exit("set INDIEROUTER_API_KEY (an IndieRouter pay-as-you-go key) before running this")
for repo in sys.argv[1:]:
    out = S + "gfy_llm_" + repo
    t0 = time.time()
    r = subprocess.run(["graphify", "extract", S + repo, "--backend", "indierouter", "--model", "deepseek-v4.1-flash", "--out", out, "--no-gitignore"],
                       capture_output=True, text=True, timeout=3600, env=env)
    tail = (r.stdout + r.stderr)[-900:]
    c = subprocess.run(["graphify", "cluster-only", out, "--no-label", "--no-viz"], capture_output=True, text=True, timeout=1800, env=env)
    g = json.load(open(out + "/graphify-out/graph.json")) if os.path.exists(out + "/graphify-out/graph.json") else {}
    print(f"{repo}: extract rc {r.returncode} in {round(time.time() - t0)}s, nodes {len(g.get('nodes', []))} edges {len(g.get('links', g.get('edges', [])))}")
    print(tail.replace(env.get("INDIEROUTER_API_KEY", "x"), "<key>"))
