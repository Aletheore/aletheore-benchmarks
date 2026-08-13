"""Rebuild a corpus index using OpenAI text-embedding-3-small instead of local nomic.

The CLI only reaches OpenAI when Ollama is unreachable, and the base URL is a
hardcoded default rather than an environment variable, so forcing it through the
CLI would mean stopping the user's Ollama. Substituting embed_texts drives the
same build_index path with the same chunks - only the embedding provider moves,
which is the single variable under test.
"""
import json
import os
import sys
from pathlib import Path

import aletheore.search_index as si
from openai import OpenAI

repo = Path(sys.argv[1])
key = None
for line in open("/private/tmp/bench/.env"):
    if line.startswith("OPENAI_API_KEY="):
        key = line.strip().split("=", 1)[1]
assert key, "no OPENAI_API_KEY in /private/tmp/bench/.env"

client = OpenAI(base_url=si.OPENAI_EMBEDDING_BASE_URL, api_key=key)


def openai_embed(texts, base_url=None, model=None, credentials_path=None, confirm_fn=None):
    out = []
    for i in range(0, len(texts), 256):          # stay well inside request limits
        batch = texts[i:i + 256]
        resp = client.embeddings.create(model=si.OPENAI_EMBEDDING_MODEL, input=batch)
        out.extend(item.embedding for item in resp.data)
    return out


si.embed_texts = openai_embed

evidence = json.load(open(repo / ".aletheore" / "air.json"))
index_dir = repo / ".aletheore" / si.INDEX_DIRNAME
if index_dir.exists():
    import shutil
    shutil.rmtree(index_dir)
n = si.build_index(repo, evidence)
print(f"indexed {n} chunks")

import lancedb
v = lancedb.connect(str(index_dir)).open_table("chunks").to_arrow().column("vector")[0].as_py()
print(f"embedding dimension: {len(v)}")
assert len(v) == 1536, f"expected OpenAI 1536 dims, got {len(v)}"
