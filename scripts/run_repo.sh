#!/bin/bash
# Build both wikis for one repo and capture equal-budget context per question.
set -e
NAME="$1"
# Scratch root, matching scripts/_bench.py. Not /private/tmp: macOS wipes it on
# reboot, which is how an earlier multi-repo run lost every corpus it had scored.
BENCH_WORK="${BENCH_WORK:-$HOME/.aletheore-bench}"
SRC="$BENCH_WORK/multi-$NAME"
RW="$BENCH_WORK/multi-rw-$NAME"
LOGS="$BENCH_WORK/bench"
mkdir -p "$LOGS"

if [ -f "$BENCH_WORK/.env" ]; then
  set -a; . "$BENCH_WORK/.env"; set +a
fi
if [ -z "$DEEPSEEK_API_KEY" ]; then
  echo "DEEPSEEK_API_KEY is not set (export it, or put it in $BENCH_WORK/.env)" >&2
  exit 1
fi
export REPOWISE_EMBEDDER=ollama
export OLLAMA_BASE_URL=http://localhost:11434
export REPOWISE_EMBEDDING_MODEL=nomic-embed-text
export REPOWISE_EMBEDDING_DIMS=768

echo "=== $NAME: aletheore scan+index ==="
cd "$SRC" && aletheore scan . >/dev/null 2>&1 && aletheore index . 2>&1 | tail -1

echo "=== $NAME: repowise init ==="
rm -rf "$RW"; cp -R "$SRC" "$RW"; rm -rf "$RW/.aletheore"
cd "$RW"
repowise init -y --provider deepseek --embedder ollama --coverage 1.0 \
  --no-claude-md --no-agents --no-codex > "$LOGS/rw-$NAME.log" 2>&1
repowise reindex --embedder ollama 2>&1 | tail -1
