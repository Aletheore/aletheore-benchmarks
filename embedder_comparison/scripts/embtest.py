"""Code-retrieval quality and speed of hosted embedders vs the production model (jina-embeddings-v2-base-code).

Same chunker, same index, same ranking, same hand-verified questions as the published retrieval matrix
(aletheore-benchmarks/scripts/run_retrieval_matrix.py). Only the embedding provider moves: search_index's
_embed_in_batches is replaced for BOTH the index build and the query, which is the one variable under test.
Corpora are copied to scratch first, so the existing indexes in ~/.aletheore-bench are never touched.

Resumable: a (provider, corpus) result file that exists is skipped.
"""
import argparse
import json
import os
import shutil
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import tempfile

HERE = Path(__file__).resolve().parent
OUT_ROOT = HERE.parent / "results"  # results/<tag or main>/<provider>/<corpus>.json
SCRATCH = Path(tempfile.gettempdir()) / "embtest-work"  # throwaway corpus copies
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(Path(sys.argv[sys.argv.index("--src") + 1])))  # aletheore src tree
import aletheore.search_index as si  # noqa: E402
import di  # noqa: E402

BENCH_Q = Path(sys.argv[sys.argv.index("--bench") + 1]) / "questions"
CORPUS_ROOT = Path(os.path.expanduser("~/.aletheore-bench"))

MATRIX = [
    ("flask", ["location"]), ("gin", ["gin"]), ("axios", ["axios", "axios_vocab"]),
    ("fmt", ["fmt", "fmt_vocab"]), ("jq", ["jq", "jq_vocab"]),
    ("automapper", ["automapper", "automapper_vocab"]), ("gson", ["gson", "gson_vocab"]),
    ("guzzle", ["guzzle", "guzzle_vocab"]), ("jekyll", ["jekyll", "jekyll_vocab"]),
]

# Corpora and question sets never used to choose a model: a check that the pick was not tuned to the matrix above.
HELDOUT = [("serde", ["serde"]), ("slim", ["slim", "slim_vocab"]), ("zod", ["zod", "zod_vocab"]), ("thrift", ["thrift"])]

QUERY_TASK = os.environ.get("QUERY_TASK") or "Given a question about a codebase, retrieve the source code that answers it"

# name -> (model id, context tokens, query instruction mode, $ per 1M tokens)
MODELS = {
    "qwen3-8b": ("Qwen/Qwen3-Embedding-8B", 32768, None, 0.010),
    "qwen3-8b-instr": ("Qwen/Qwen3-Embedding-8B", 32768, "qwen", 0.010),
    "qwen3-4b": ("Qwen/Qwen3-Embedding-4B", 32768, None, 0.020),
    "qwen3-0.6b": ("Qwen/Qwen3-Embedding-0.6B", 32768, None, 0.010),
    "bge-m3": ("BAAI/bge-m3", 8192, None, 0.010),
    "gemma-300m": ("google/embeddinggemma-300m", 2048, None, 0.002),
    "nemotron-1b": ("nvidia/Nemotron-3-Embed-1B-BF16", 32768, None, 0.015),
    "nemotron-8b": ("nvidia/Nemotron-3-Embed-8B", 32768, None, 0.035),
    "bge-base": ("BAAI/bge-base-en-v1.5", 512, None, 0.005),
}


class Provider:
    def __init__(self, name):
        self.name = name
        self.label = f"bench:{name}"
        self.tokens = 0
        self.calls = 0
        self.truncated = 0
        self.seconds = 0.0
        self.lock = threading.Lock()
        self.query_cache: dict[str, list[float]] = {}

    def embed(self, texts, is_query=False):
        raise NotImplementedError

    def reset_stats(self):
        self.tokens = self.calls = self.truncated = 0
        self.seconds = 0.0


class OllamaJina(Provider):
    """The production model (Q8 GGUF of jina-embeddings-v2-base-code) via the local Ollama."""

    def embed(self, texts, is_query=False):
        out = []
        t0 = time.perf_counter()
        for i in range(0, len(texts), 32):
            out.extend(si.embed_texts(texts[i:i + 32]))
        self.seconds += time.perf_counter() - t0
        self.calls += 1
        return out


class DeepInfra(Provider):
    def __init__(self, name, workers=4, batch=48, max_req_chars=120_000):
        super().__init__(name)
        self.model, self.ctx, self.instr, self.price = MODELS[name]
        self.workers, self.batch, self.max_req_chars = workers, batch, max_req_chars
        self.max_chars = min(20_000, int(self.ctx * 2.6))  # conservative chars per token for code

    def _prep(self, text, is_query):
        if len(text) > self.max_chars:
            with self.lock:
                self.truncated += 1
            text = text[: self.max_chars]
        if is_query and self.instr == "qwen":
            return f"Instruct: {QUERY_TASK}\nQuery:{text}"
        return text

    def _call(self, batch):
        for attempt in range(7):
            status, data, dt = di.embed(self.model, batch)
            if status == 200:
                with self.lock:
                    self.tokens += data["usage"]["prompt_tokens"]
                    self.calls += 1
                return [d["embedding"] for d in data["data"]]
            if status in (429, 500, 502, 503, 504, 0):
                time.sleep(min(2 ** attempt, 20))
                continue
            if status == 400 and "context length" in str(data):
                return self._call_one_by_one(batch)
            raise RuntimeError(f"{self.model}: HTTP {status}: {str(data)[:200]}")
        raise RuntimeError(f"{self.model}: gave up after retries")

    def _call_one_by_one(self, batch):
        """A batch contained an input over the model's context. Re-send each text alone, cutting it by a
        quarter until it fits (dense code runs more tokens per character than the estimate)."""
        out = []
        for text in batch:
            cur = text
            for _ in range(12):
                status, data, _ = di.embed(self.model, [cur])
                if status == 200:
                    with self.lock:
                        self.tokens += data["usage"]["prompt_tokens"]
                        self.calls += 1
                        if cur is not text:
                            self.truncated += 1
                    out.append(data["data"][0]["embedding"])
                    break
                if status == 400 and "context length" in str(data):
                    cur = cur[: int(len(cur) * 0.75)]
                    continue
                if status in (429, 500, 502, 503, 504, 0):
                    time.sleep(2)
                    continue
                raise RuntimeError(f"{self.model}: HTTP {status}: {str(data)[:200]}")
            else:
                raise RuntimeError(f"{self.model}: could not fit an input under the context")
        return out

    def embed(self, texts, is_query=False):
        prepped = [self._prep(t, is_query) for t in texts]
        batches, cur, cur_chars = [], [], 0
        for t in prepped:
            if cur and (len(cur) >= self.batch or cur_chars + len(t) > self.max_req_chars):
                batches.append(cur)
                cur, cur_chars = [], 0
            cur.append(t)
            cur_chars += len(t)
        if cur:
            batches.append(cur)
        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            results = list(pool.map(self._call, batches))
        self.seconds += time.perf_counter() - t0
        return [v for r in results for v in r]


PROVIDER: Provider | None = None
IN_QUERY = {"on": False}


def patched_embed_in_batches(texts, batch_size=None, repo_id=None, allow_hosted=True, on_progress=None):
    p = PROVIDER
    if IN_QUERY["on"] and len(texts) == 1 and texts[0] in p.query_cache:
        return [p.query_cache[texts[0]]], p.label
    return p.embed(texts, is_query=IN_QUERY["on"]), p.label


si._embed_in_batches = patched_embed_in_batches


_STOP = set("""a an the is are was were be been where what which who whom how why does do did can could would should
in on at of to for from by with and or as that this these those it its into out up down over under when while
whose there their they them than then so if not no yes about across between through during before after""".split())


def _keywords(text):
    """What an agent or a person typing a search box might send instead of a full question."""
    import re
    words = [w for w in re.findall(r"[A-Za-z0-9_./-]+", text) if w.lower() not in _STOP]
    return " ".join(words)


def load_questions(qset):
    raw = json.loads((BENCH_Q / f"{qset}.json").read_text())
    if os.environ.get("QUERY_MODE") == "keywords":
        for e in raw:
            key = "question" if "question" in e else "q"
            e[key] = _keywords(e[key])
    return [{"id": e["id"], "q": e.get("question") or e.get("q"),
             "gt": e.get("ground_truth_files") or e.get("gt") or []} for e in raw]


def ranked_files(repo, question):
    hits = si.search_index(repo, question, k=10)
    files, seen = [], set()
    for h in hits:
        p = h.get("module_path")
        if p and p not in seen:
            seen.add(p)
            files.append(p)
    return files


def summarise(rows):
    n = len(rows)
    def at(k):
        return sum(1 for r in rows if any(f in r["gt"] for f in r["ranked"][:k]))
    rr = []
    for r in rows:
        rank = next((i + 1 for i, f in enumerate(r["ranked"]) if f in r["gt"]), None)
        rr.append(1.0 / rank if rank else 0.0)
    return {"n": n, "top1": at(1), "top3": at(3), "top5": at(5), "mrr": statistics.mean(rr) if rr else 0.0}


def run_corpus(provider, corpus, qsets, outdir):
    out = outdir / f"{corpus}.json"
    if out.exists():
        print(f"  [{provider.name}/{corpus}] done already", flush=True)
        return json.loads(out.read_text())
    src = CORPUS_ROOT / f"multi-{corpus}"
    work = SCRATCH / "work" / provider.name / corpus
    if work.exists():
        shutil.rmtree(work)
    work.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, work, symlinks=True, ignore_dangling_symlinks=True,
                    ignore=shutil.ignore_patterns(".git", "index.lancedb"))
    evidence = json.loads((work / ".aletheore" / "air.json").read_text())

    provider.reset_stats()
    t0 = time.perf_counter()
    n_chunks = si.build_index(work, evidence)
    build_s = time.perf_counter() - t0
    build_stats = {"chunks": n_chunks, "build_seconds": round(build_s, 2), "tokens": provider.tokens,
                   "truncated_chunks": provider.truncated, "api_calls": provider.calls}

    result = {"corpus": corpus, "build": build_stats, "sets": {}}
    for qset in qsets:
        questions = load_questions(qset)
        # one batched call for every query of the set: the single-query latency is measured separately
        provider.query_cache = {}
        IN_QUERY["on"] = True
        vecs = provider.embed([q["q"] for q in questions], is_query=True)
        for q, v in zip(questions, vecs):
            provider.query_cache[q["q"]] = v
        rows = []
        for q in questions:
            rows.append({"id": q["id"], "gt": q["gt"], "ranked": ranked_files(work, q["q"])})
        IN_QUERY["on"] = False
        result["sets"][qset] = {"summary": summarise(rows), "rows": rows}
    out.write_text(json.dumps(result))
    shutil.rmtree(work, ignore_errors=True)
    s = result["sets"]
    tot = summarise([r for qs in s.values() for r in qs["rows"]])
    print(f"  [{provider.name}/{corpus}] {n_chunks} chunks in {build_s:.0f}s ({provider.tokens} tok, "
          f"{provider.truncated} truncated)  top1={tot['top1']}/{tot['n']} top3={tot['top3']} mrr={tot['mrr']:.3f}", flush=True)
    return result


def main():
    global PROVIDER
    p = argparse.ArgumentParser()
    p.add_argument("--src", required=True)
    p.add_argument("--bench", required=True)
    p.add_argument("--provider", required=True)
    p.add_argument("--only", default="")
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--matrix", default="main", choices=["main", "heldout"])
    p.add_argument("--tag", default="", help="results subdirectory prefix, e.g. heldout")
    args = p.parse_args()
    matrix = HELDOUT if args.matrix == "heldout" else MATRIX
    PROVIDER = OllamaJina("jina-local") if args.provider == "jina-local" else DeepInfra(args.provider, workers=args.workers)
    outdir = OUT_ROOT / (args.tag or ("heldout" if args.matrix == "heldout" else "main")) / args.provider
    outdir.mkdir(parents=True, exist_ok=True)
    only = {c for c in args.only.split(",") if c}
    total_tokens = 0
    t0 = time.perf_counter()
    for corpus, qsets in matrix:
        if only and corpus not in only:
            continue
        r = run_corpus(PROVIDER, corpus, qsets, outdir)
        total_tokens += r["build"]["tokens"]
    price = getattr(PROVIDER, "price", 0.0)
    print(f"DONE {args.provider}: {time.perf_counter() - t0:.0f}s wall, {total_tokens} tokens, "
          f"~${total_tokens / 1e6 * price:.4f}", flush=True)


if __name__ == "__main__":
    main()
