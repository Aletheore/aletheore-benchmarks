# Hosted embedder comparison: Qwen3-Embedding-8B against the production Jina model (2026-10-11)

Aletheore's hosted embedding endpoint used to run `jina-embeddings-v2-base-code` (Q8_0 GGUF, llama.cpp) in a
CPU sidecar. This experiment asks whether a hosted embedding API can replace it, and which model, on the same
code-search questions the retrieval benchmarks in this repository use. **Result: the best hosted model is level
with Jina on quality, not better.** The case for switching is operational (throughput and a freed server), and
that is what shipped.

**Shipped on 2026-10-13:** `Qwen/Qwen3-Embedding-8B` at 1024 dimensions through DeepInfra, behind an
`EMBED_PROVIDER` flag. The query instruction measured in Experiment E was not shipped.

## Setup

- **Held fixed:** the same chunker, index, ranking and hand-verified questions as the retrieval matrix in this
  repository (`questions/`). Only the embedding provider changes: `search_index._embed_in_batches` is replaced
  for both the index build and the query (`scripts/embtest.py`). Metric: rank of the first ground-truth file among the distinct files in the
  top ten hits (top-1, top-3, top-5, MRR).
- **Baseline:** the production Jina model (Q8_0 GGUF of `jina-embeddings-v2-base-code`, 768 dimensions).
- **Hosted models (DeepInfra):** Qwen3-Embedding 8B, 4B and 0.6B, a Qwen3-8B variant with a query instruction,
  `bge-m3`, `bge-base-en-v1.5`, `embeddinggemma-300m`, `Nemotron-3-Embed` 1B and 8B. That is eight models and
  one instruction variant, nine configurations in all.
- **Questions:** 257 questions over 9 corpora (flask, gin, axios, fmt, jq, automapper, gson, guzzle, jekyll) that
  were used to choose a model, plus 90 over 4 corpora (serde, slim, zod, thrift) that were not, held out as a check.
  Inputs longer than a model's context were truncated (29 of 9,035 chunks for the Qwen3 models).
- **Statistics:** every difference is paired by question, with a 95% interval from 4,000 bootstrap resamples of the
  questions. `scripts/score_embedders.py` recomputes every table below from `results/` with no API key.
- **Date and code:** run 2026-10-10 to 2026-10-11 against Aletheore master of that week.

## Results

### A. Nine-corpus matrix (257 questions)

| Model | Top-1 | Top-3 | Top-5 | MRR | MRR vs Jina (95% CI) |
|---|---|---|---|---|---|
| Qwen3-8B with query instruction | 61.1% | 82.1% | 88.3% | 0.730 | +0.023 [-0.003, +0.049] |
| Qwen3-8B | 60.3% | 80.5% | 86.8% | 0.714 | +0.007 [-0.020, +0.035] |
| **Jina (production baseline)** | 58.4% | 81.3% | 86.0% | 0.707 | baseline |
| Nemotron-3-Embed 8B | 58.4% | 78.2% | 84.4% | 0.697 | -0.010 [-0.038, +0.019] |
| Qwen3-0.6B | 57.6% | 77.8% | 86.4% | 0.691 | -0.016 [-0.045, +0.012] |
| embeddinggemma-300m | 57.2% | 79.0% | 84.4% | 0.688 | -0.019 [-0.047, +0.011] |
| Qwen3-4B | 55.3% | 78.2% | 84.4% | 0.679 | -0.028 [-0.058, +0.001] |
| bge-base-en-v1.5 | 54.9% | 75.1% | 83.3% | 0.665 | -0.042 [-0.073, -0.010] |
| bge-m3 | 49.8% | 77.4% | 84.0% | 0.642 | -0.065 [-0.095, -0.034] |
| Nemotron-3-Embed 1B | 42.4% | 61.1% | 70.0% | 0.537 | -0.170 [-0.214, -0.127] |

Per-corpus top-1, vector sizes, list prices and token counts are in [`results/summary.md`](results/summary.md).

### B. Held-out corpora (90 questions, never used to choose a model)

| Model | Top-1 | Top-3 | Top-5 | MRR | MRR vs Jina (95% CI) |
|---|---|---|---|---|---|
| Qwen3-8B with query instruction | 46.7% | 72.2% | 84.4% | 0.618 | +0.050 [-0.006, +0.108] |
| Qwen3-8B | 45.6% | 67.8% | 81.1% | 0.586 | +0.018 [-0.048, +0.085] |
| **Jina** | 44.4% | 64.4% | 76.7% | 0.569 | baseline |
| Qwen3-0.6B | 40.0% | 67.8% | 77.8% | 0.551 | -0.017 [-0.076, +0.045] |

The ordering matches Experiment A, so the pick was not tuned to the matrix. The held-out intervals are wide.

### C. Pooled, 347 questions

| Model | Top-1 | MRR | MRR vs Jina (95% CI) |
|---|---|---|---|
| Qwen3-8B with query instruction | 57.3% | 0.701 | +0.030 [+0.006, +0.055] |
| Qwen3-8B | 56.5% | 0.681 | +0.010 [-0.017, +0.037] |
| **Jina** | 54.8% | 0.671 | baseline |
| Qwen3-0.6B | 53.0% | 0.655 | -0.016 [-0.043, +0.010] |

Qwen3-8B minus Qwen3-0.6B: MRR +0.026 [-0.000, +0.053]. The query instruction on top of Qwen3-8B: MRR +0.020 [+0.003, +0.037].

### D. The shipped configuration: Qwen3-8B at 1024 dimensions (332 questions)

Qwen3-Embedding-8B can return a vector truncated to 1024 dimensions (Matryoshka representation), a quarter of its
native 4096. Fewer dimensions means smaller indexes. It also matters operationally: older CLIs label every hosted
vector as the Jina model, so a model with a different dimension count than 768 is the only mismatch they detect.

| Configuration | Top-1 | Top-3 | Top-5 | MRR | MRR vs Jina (95% CI) |
|---|---|---|---|---|---|
| **Qwen3-8B at 1024 (shipped)** | 58.4% | 77.4% | 86.1% | 0.695 | +0.008 [-0.019, +0.035] |
| Qwen3-8B at 4096 (native) | 58.1% | 78.6% | 85.8% | 0.694 | +0.007 [-0.020, +0.034] |
| **Jina** | 56.9% | 78.6% | 83.7% | 0.687 | baseline |
| Qwen3-0.6B | 54.5% | 75.9% | 84.6% | 0.665 | -0.022 [-0.049, +0.004] |

1024 against 4096 dimensions: MRR +0.001 [-0.011, +0.013], so nothing is lost. 8B at 1024 minus 0.6B: +0.030 [+0.003, +0.056].
(This set is the 257-question matrix plus serde, slim and zod; the 4096-dimension and Jina runs on thrift were not repeated at 1024.)

### E. Does the query wording matter? (flask, axios, fmt, jq, gson, guzzle: 182 questions)

Qwen3 models accept an instruction prepended to the query. Does it help, and is the gain specific to one wording
or to full-sentence questions?

| Full-sentence queries | Top-1 | Top-3 | Top-5 | MRR | MRR vs no instruction (95% CI) |
|---|---|---|---|---|---|
| No instruction | 64.3% | 84.6% | 89.6% | 0.749 | baseline |
| Instruction, wording 1 (the one used in A to C) | 62.6% | 85.7% | 91.2% | 0.753 | +0.004 [-0.017, +0.024] |
| Instruction, wording 2 | 63.7% | 86.3% | 90.7% | 0.757 | +0.008 [-0.013, +0.028] |
| Instruction, wording 3 | 64.8% | 88.5% | 90.1% | 0.764 | +0.015 [-0.002, +0.032] |

| Keyword-style queries (stop words stripped) | Top-1 | Top-3 | Top-5 | MRR | MRR vs no instruction (95% CI) |
|---|---|---|---|---|---|
| No instruction | 62.6% | 84.1% | 90.1% | 0.742 | baseline |
| Instruction | 62.6% | 86.8% | 90.1% | 0.753 | +0.012 [-0.009, +0.032] |

The instruction helps a little on the pooled set (C) and is not distinguishable from zero on this subset under any of three wordings or under
keyword queries. It was not built into the product: the client would have to send it, which needs a CLI release.
No Jina run exists for the keyword-style queries, so that table compares the two Qwen3-8B settings only.

### F. Speed (one production host, same workload through both paths)

240 chunks of 900 characters of Go source (`speed/chunks.json`), sent in batches of 24 (`CHUNKS_FILE=speed/chunks.json python3 speed/measure.py hosted` or `sidecar`) from inside the production
app-server container, so both paths cross the same network from the same machine. Hosted is the production
`embed_batch` path (Qwen3-8B at 1024); the sidecar is `jina-embed` (`/embed_batch`, 2 instances, 2 CPU threads, no other
load). Raw outputs: `speed/hosted_run*.txt`, `speed/sidecar_run*.txt`; script: `speed/measure.py`.

| Concurrent requests | Hosted, chunks/s (3 runs) | Sidecar, chunks/s (2 runs) | Ratio of medians |
|---|---|---|---|
| 1 | 11.3, 10.8, 11.1 | 1.6, 1.7 | about 6.7x |
| 2 | 7.8, 20.6, 22.1 | 2.1, 2.1 | about 9.8x |
| 4 | 6.5, 36.8, 37.5 | not applicable (2 instances) | about 17x against the sidecar's best |

So bulk indexing is about 7x faster with one request at a time and up to about 17x faster with four in parallel,
which is how the production path sends a large request (up to four batches in parallel). The first hosted run did not scale with concurrency (7.8 and
6.5 chunks/s at 2 and 4); the second and third scaled almost linearly. I did not investigate that, so treat the hosted
figures as provider-load dependent. The sidecar figure is for this host's CPU; a faster CPU or more instances would
narrow the gap. Once the sidecar is stopped, the hosted path also frees its CPU and about 1.3 GiB of memory on the server.

## What the data supports

- **Quality is level, not better.** Qwen3-8B beats Jina by +0.007 to +0.018 MRR in every set, and every one of those
  intervals includes zero. Against the 0.6B model it is ahead by +0.026 on the pooled set (interval touching zero) and +0.030 on the shipped-configuration set (interval above zero).
- **Some hosted models were clearly worse.** bge-base (-0.042), bge-m3 (-0.065) and Nemotron-3-Embed 1B (-0.170) have intervals
  entirely below zero against Jina; Qwen3-4B (-0.028) is below it with an interval touching zero. The Nemotron-1B gap is large and was not investigated.
- **1024 dimensions cost nothing measurable** against the native 4096.
- **The case for the switch is operational:** much faster bulk indexing, no CPU-bound sidecar, no model to host or update.

## Limitations, stated plainly

1. **Small effects on a small set.** 347 questions; a 95% interval on MRR is about plus or minus 0.03. Differences under that are noise.
2. **Questions are file-level and written by the maintainers.** Ground truth is the file that implements the answer. The questions are the published matrix's, including its vocabulary-matching weaknesses.
3. **Model choice among nine configurations, then a held-out check.** No multiple-comparison correction was applied. The held-out set agrees with the pick but is small.
4. **Retrieval only.** This does not measure answer or review quality, only whether the right file is retrieved.
5. **The Jina baseline is the local quantized model,** the same GGUF family the sidecar serves.
6. **Prices are DeepInfra list prices on 2026-10-11** and change.
7. **Speed is host- and load-dependent** (see F); the sidecar number is for one machine.
8. **Hosted embedding sends code chunks to the provider.** The privacy policy names it, and the CLI says so before it uploads source.

## Reproducing

```bash
# Recompute every table from the committed rankings (no API key, no network)
python3 embedder_comparison/scripts/score_embedders.py

# Re-run a model (needs the retrieval benchmark corpora under ~/.aletheore-bench, an Aletheore source tree,
# and DEEPINFRA_API_KEY; the Jina baseline needs a local Ollama with the same GGUF)
export DEEPINFRA_API_KEY=...
python3 embedder_comparison/scripts/embtest.py --src /path/to/Aletheore/src --bench . --provider qwen3-8b
python3 embedder_comparison/scripts/embtest.py --src /path/to/Aletheore/src --bench . --provider qwen3-8b --matrix heldout
EMBED_DIMS=1024 python3 embedder_comparison/scripts/embtest.py --src /path/to/Aletheore/src --bench . --provider qwen3-8b --tag dim1024
```

Result files are in `results/<set>/<model>/<corpus>.json`: `main`, `heldout`, `dim1024`, `dim1024_heldout`,
`keywords`, `wording2`, `wording3`. `scripts/speed_hosted_probe.py` is the single-call latency and bulk-throughput probe
used while choosing models.
