# Scorer output (python3 scripts/score_embedders.py)
questions answered by every model on the 9-corpus matrix: 257

### A. Nine-corpus matrix (hosted models against the production local model)

| Model | Top-1 | Top-3 | Top-5 | MRR | MRR vs jina local (95% CI) |
|---|---|---|---|---|---|
| qwen3-8b-instr | 61.1% | 82.1% | 88.3% | 0.730 | +0.023 [-0.003, +0.049] |
| qwen3-8b | 60.3% | 80.5% | 86.8% | 0.714 | +0.007 [-0.020, +0.035] |
| jina-local | 58.4% | 81.3% | 86.0% | 0.707 | baseline |
| nemotron-8b | 58.4% | 78.2% | 84.4% | 0.697 | -0.010 [-0.038, +0.019] |
| qwen3-0.6b | 57.6% | 77.8% | 86.4% | 0.691 | -0.016 [-0.045, +0.012] |
| gemma-300m | 57.2% | 79.0% | 84.4% | 0.688 | -0.019 [-0.047, +0.011] |
| qwen3-4b | 55.3% | 78.2% | 84.4% | 0.679 | -0.028 [-0.058, +0.001] |
| bge-base | 54.9% | 75.1% | 83.3% | 0.665 | -0.042 [-0.073, -0.010] |
| bge-m3 | 49.8% | 77.4% | 84.0% | 0.642 | -0.065 [-0.095, -0.034] |
| nemotron-1b | 42.4% | 61.1% | 70.0% | 0.537 | -0.170 [-0.214, -0.127] |

| Model | Vector size | List price per 1M tokens | Tokens to index the 9 corpora |
|---|---|---|---|
| qwen3-8b-instr | 4096 | $0.010 | 1,688,932 |
| qwen3-8b | 4096 | $0.010 | 1,688,932 |
| jina-local | 768 | n/a (local) | n/a |
| nemotron-8b | 4096 | $0.035 | 1,780,121 |
| qwen3-0.6b | 1024 | $0.010 | 1,688,932 |
| gemma-300m | 768 | $0.002 | 1,709,023 |
| qwen3-4b | 2560 | $0.020 | 1,688,932 |
| bge-base | 768 | $0.005 | 1,391,030 |
| bge-m3 | 1024 | $0.010 | 2,232,818 |
| nemotron-1b | 2048 | $0.015 | 1,780,121 |

Per-corpus top-1:

| Model | flask | gin | axios | fmt | jq | automapper | gson | guzzle | jekyll |
|---|---|---|---|---|---|---|---|---|---|
| qwen3-8b-instr | 26/32 | 14/15 | 18/30 | 18/30 | 21/30 | 14/30 | 17/30 | 14/30 | 15/30 |
| qwen3-8b | 25/32 | 11/15 | 19/30 | 17/30 | 22/30 | 14/30 | 19/30 | 15/30 | 13/30 |
| jina-local | 26/32 | 11/15 | 16/30 | 16/30 | 20/30 | 16/30 | 16/30 | 14/30 | 15/30 |
| nemotron-8b | 25/32 | 11/15 | 17/30 | 17/30 | 19/30 | 14/30 | 18/30 | 15/30 | 14/30 |
| qwen3-0.6b | 23/32 | 13/15 | 15/30 | 16/30 | 19/30 | 13/30 | 17/30 | 16/30 | 16/30 |
| gemma-300m | 24/32 | 10/15 | 14/30 | 18/30 | 18/30 | 13/30 | 17/30 | 17/30 | 16/30 |
| qwen3-4b | 24/32 | 8/15 | 18/30 | 18/30 | 19/30 | 11/30 | 16/30 | 14/30 | 14/30 |
| bge-base | 23/32 | 12/15 | 14/30 | 17/30 | 19/30 | 18/30 | 13/30 | 12/30 | 13/30 |
| bge-m3 | 16/32 | 11/15 | 16/30 | 14/30 | 16/30 | 15/30 | 14/30 | 14/30 | 12/30 |
| nemotron-1b | 19/32 | 6/15 | 12/30 | 15/30 | 14/30 | 13/30 | 13/30 | 9/30 | 8/30 |

questions answered by every model on the held-out corpora (serde, slim, zod, thrift): 90

### B. Held-out corpora

| Model | Top-1 | Top-3 | Top-5 | MRR | MRR vs jina local (95% CI) |
|---|---|---|---|---|---|
| qwen3-8b-instr | 46.7% | 72.2% | 84.4% | 0.618 | +0.050 [-0.006, +0.108] |
| qwen3-8b | 45.6% | 67.8% | 81.1% | 0.586 | +0.018 [-0.048, +0.085] |
| jina-local | 44.4% | 64.4% | 76.7% | 0.569 | baseline |
| qwen3-0.6b | 40.0% | 67.8% | 77.8% | 0.551 | -0.017 [-0.076, +0.045] |

pooled questions (matrix + held-out): 347

### C. Pooled

| Model | Top-1 | Top-3 | Top-5 | MRR | MRR vs jina local (95% CI) |
|---|---|---|---|---|---|
| qwen3-8b-instr | 57.3% | 79.5% | 87.3% | 0.701 | +0.030 [+0.006, +0.055] |
| qwen3-8b | 56.5% | 77.2% | 85.3% | 0.681 | +0.010 [-0.017, +0.037] |
| jina-local | 54.8% | 76.9% | 83.6% | 0.671 | baseline |
| qwen3-0.6b | 53.0% | 75.2% | 84.1% | 0.655 | -0.016 [-0.043, +0.010] |

Paired differences on the pooled set (MRR / top-1):
- qwen3-8b minus qwen3-0.6b: MRR +0.026 [-0.000, +0.053]; top-1 +0.035 [-0.006, +0.078]
- qwen3-8b-instr minus qwen3-8b: MRR +0.020 [+0.003, +0.037]; top-1 +0.009 [-0.017, +0.035]

shipped-configuration comparison, questions answered by all four: 332

### D. Shipped configuration

| Model | Top-1 | Top-3 | Top-5 | MRR | MRR vs jina local (95% CI) |
|---|---|---|---|---|---|
| qwen3-8b @ 1024 (shipped) | 58.4% | 77.4% | 86.1% | 0.695 | +0.008 [-0.019, +0.035] |
| qwen3-8b @ 4096 (native) | 58.1% | 78.6% | 85.8% | 0.694 | +0.007 [-0.020, +0.034] |
| jina-local | 56.9% | 78.6% | 83.7% | 0.687 | baseline |
| qwen3-0.6b | 54.5% | 75.9% | 84.6% | 0.665 | -0.022 [-0.049, +0.004] |

- 1024 minus 4096 dimensions: MRR +0.001 [-0.011, +0.013]
- 8B @ 1024 minus 0.6B: MRR +0.030 [+0.003, +0.056]

robustness questions (flask, axios, fmt, jq, gson, guzzle): 182

### E1. Full-sentence queries: does a query instruction help, and is it wording-specific?

| Model | Top-1 | Top-3 | Top-5 | MRR | MRR vs no instruction (95% CI) |
|---|---|---|---|---|---|
| no instruction | 64.3% | 84.6% | 89.6% | 0.749 | baseline |
| instruction, wording 1 (used in A) | 62.6% | 85.7% | 91.2% | 0.753 | +0.004 [-0.017, +0.024] |
| instruction, wording 2 | 63.7% | 86.3% | 90.7% | 0.757 | +0.008 [-0.013, +0.028] |
| instruction, wording 3 | 64.8% | 88.5% | 90.1% | 0.764 | +0.015 [-0.002, +0.032] |

### E2. Keyword-style queries (stop words stripped)

| Model | Top-1 | Top-3 | Top-5 | MRR | MRR vs no instruction (95% CI) |
|---|---|---|---|---|---|
| no instruction | 62.6% | 84.1% | 90.1% | 0.742 | baseline |
| instruction | 62.6% | 86.8% | 90.1% | 0.753 | +0.012 [-0.009, +0.032] |
