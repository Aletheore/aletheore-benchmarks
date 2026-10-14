"""Same 240 x 900-character chunks through (a) the production Jina sidecar and (b) the production hosted path.
Runs inside the app-server container so both go over the same network from the same host."""
import json, os, statistics, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
CHUNKS = os.environ.get("CHUNKS_FILE", "chunks.json")  # the 240 x 900-character workload next to this script
chunks = json.load(open(CHUNKS))
BATCH = 24
batches = [chunks[i:i + BATCH] for i in range(0, len(chunks), BATCH)]

def sidecar(batch):
    req = urllib.request.Request("http://jina-embed:80/embed_batch", data=json.dumps({"texts": batch}).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=300) as r:  # nosec B310 - fixed internal http URL
        return len(json.loads(r.read())["embeddings"])

def run(label, fn, workers):
    t0 = time.perf_counter()
    with ThreadPoolExecutor(workers) as p:
        done = sum(p.map(fn, batches))
    dt = time.perf_counter() - t0
    print(f"{label:34s} workers={workers}: {done}/{len(chunks)} chunks in {dt:6.1f}s = {done / dt:5.1f} chunks/s", flush=True)
    return done / dt

mode = sys.argv[1]
if mode == "sidecar":
    for w in (1, 2):
        run("jina sidecar (/embed_batch)", sidecar, w)
else:
    sys.path.insert(0, "/app")
    from app_server import hosted_embedder as he
    def hosted(batch):
        vecs, _tokens = he.embed_batch(batch, timeout_seconds=120)
        return len(vecs)
    print("provider:", he.provider(), "model:", he.deepinfra_model(), "dims:", he.deepinfra_dimensions(), flush=True)
    for w in (1, 2, 4):
        run("hosted (production embed_batch)", hosted, w)
