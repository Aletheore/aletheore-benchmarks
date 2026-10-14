import glob, os, random, statistics, sys, time
from concurrent.futures import ThreadPoolExecutor
import di
src = "".join(open(f, errors="ignore").read() for f in sorted(glob.glob(os.path.expanduser("~/.aletheore-bench/multi-gin/*.go")))[:40])
M = {"qwen3-0.6b":"Qwen/Qwen3-Embedding-0.6B","qwen3-8b":"Qwen/Qwen3-Embedding-8B","gemma-300m":"google/embeddinggemma-300m"}
def chunk(n, off=0): return src[off:off+n]
for name, mid in M.items():
    di.embed(mid, ["warm up"])  # warm
    print(f"== {name}")
    for n in (60, 400, 2200, 7000):
        ts=[]
        for i in range(8):
            s,d,dt = di.embed(mid, [chunk(n, i*997)]); ts.append(dt if s==200 else float('nan'))
        print(f"  single call {n:5d} chars: median {statistics.median(ts)*1000:5.0f} ms  p90 {sorted(ts)[-2]*1000:5.0f} ms")
    texts=[chunk(900, i*601) for i in range(240)]
    for w in (1,4,8,16):
        batches=[texts[i:i+24] for i in range(0,240,24)]
        t0=time.perf_counter()
        with ThreadPoolExecutor(w) as p: r=list(p.map(lambda b: di.embed(mid,b)[0], batches))
        dt=time.perf_counter()-t0
        print(f"  bulk 240 chunks x 900 chars, workers={w:2d}: {dt:5.1f}s = {240/dt:5.1f} chunks/s {240*900/dt/1000:6.1f}K chars/s ok={r.count(200)}/{len(r)}")
