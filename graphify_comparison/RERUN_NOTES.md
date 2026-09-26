# Status: instrumentation shipped, real run still pending

`agent_loop.py`'s tool-call logging fix and `questions_conceptual.json` (see
the README's "A gap in this benchmark itself" section) are committed and
pushed. Neither has been run against the real API yet. This file is the
handoff note for whoever runs it next.

## What was attempted, and why it stopped

A real attempt was made in a throwaway sandbox container with a supplied
`DEEPSEEK_API_KEY`. Setup got most of the way there:

- `pip install aletheore` (0.9.20) and `pip install graphifyy` (0.9.68) into
  a venv — both installed cleanly.
- Installed local Ollama, pulled `nomic-embed-text` (what the README's
  reproduction steps still name).
- `aletheore scan .` on the pinned ERPNext checkout: **76s**.
- `graphify extract . --code-only` on the same checkout: **104s**, 26,720
  nodes / 61,266 edges. Both consistent with the README's already-published
  "setup time" finding — this part reproduces fine.
- `aletheore index .` is where it stalled. **The installed 0.9.20 CLI no
  longer uses `nomic-embed-text` by default** — it's since switched to
  `hf.co/ggml-org/jina-embeddings-v2-base-code-Q8_0-GGUF` (confirmed by
  reading `aletheore/search_index.py`'s own comments: "Was nomic-embed-text
  until a real, measured comparison on this repo's own [corpus]..." — a
  deliberate, documented product change, not a regression). That model is
  heavier, and on this sandbox's 4 CPU cores with no GPU, embedding
  throughput measured at **~110-115 chunks/minute** against **15,132 total
  chunks** — roughly **2.2-2.4 hours**, not the README's ~19 minutes (which
  was measured on different hardware, likely before the model switch).

That alone was tolerable to just wait out. What actually killed the attempt
twice: **this sandbox is an ephemeral container that gets reclaimed after a
period of inactivity**, and a `nohup`'d background process doesn't survive
that reclamation even though on-disk files do. The first attempt died
silently at ~2,000/15,132 chunks during a scheduled 30-minute check-in gap
(the gap itself was the inactivity that got the container reaped — `ollama
serve` and the `aletheore index` process were both gone on the next check,
with no error in the log, just a truncated chunk counter). The second
attempt (restarted `ollama serve` + `aletheore index .` from zero — no
partial-index checkpoint exists to resume from) was still running, confirmed
progressing steadily (~4,800/15,132 at the ~41-minute mark, consistent
throughput), when the decision was made to stop burning turns polling a
multi-hour job rather than getting it done.

## What this means for whoever re-runs it

1. **Use an environment that won't idle-reclaim mid-run**, or one with a GPU
   (this step is almost certainly GPU-bound-cheap, CPU-bound-slow — a
   machine with any GPU Ollama can use should finish in minutes, not hours).
   If it must run in a similarly ephemeral sandbox, keep the session
   actively polling (foreground, not a scheduled wake-up with an idle gap)
   for the ~2-2.5 hours `aletheore index .` takes, or run it somewhere
   outside the agent session entirely (a plain terminal, CI) and come back
   to run the harness/judge/score scripts once `.aletheore/index.lancedb`
   exists.
2. **The model switch itself is worth a one-line update to this directory's
   README** — its reproduction steps still say `nomic-embed-text`, which is
   no longer what a fresh `pip install aletheore` actually uses. Not fixed
   here because it's a documentation correction independent of getting a
   real run done, and didn't seem worth mixing into this note.
3. Once `aletheore index .` finishes (verify with `ls
   .aletheore/index.lancedb`), run `setup_tools.py`'s smoke test, then the
   full pipeline for **both** question sets, exactly as described in the
   README's "Not yet run" section:

   ```bash
   cd graphify_comparison/scripts
   python3 run_harness.py                         # original set, now with tool_calls logged
   python3 judge.py
   python3 score.py

   python3 run_harness.py questions_conceptual     # the harder set
   python3 judge.py questions_conceptual
   python3 score.py questions_conceptual
   ```

4. The two numbers that actually matter, once real results exist:
   - `summary.json`'s `search_codebase_calls` for the `aletheore` condition
     on the **original** question set — confirms or kills the suspicion that
     the semantic-search path was never exercised in the already-published
     table.
   - The coverage/token gap on `questions_conceptual_summary.json` compared
     to the original `summary.json` — if the gap barely moves, the ~2-hour
     indexing cost this note just spent two attempts fighting isn't earning
     its keep on this kind of question, and that's a real product finding,
     not a benchmark artifact.
