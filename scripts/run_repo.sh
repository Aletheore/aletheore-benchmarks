#!/bin/bash
# Build both wikis for one repo and capture equal-budget context per question.
set -e
NAME="$1"
SRC="/private/tmp/multi-$NAME"
RW="/private/tmp/multi-rw-$NAME"

set -a; . /private/tmp/bench/.env; set +a
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
  --no-claude-md --no-agents --no-codex > "/private/tmp/bench/rw-$NAME.log" 2>&1
repowise reindex --embedder ollama 2>&1 | tail -1
