"""Minimal DeepInfra OpenAI-compatible embeddings client used by embtest.py.
Key from the DEEPINFRA_API_KEY environment variable. EMBED_DIMS (optional) asks for a Matryoshka-truncated vector."""
import json
import os
import ssl
import time
import urllib.error
import urllib.request

import certifi

KEY = os.environ["DEEPINFRA_API_KEY"]
CTX = ssl.create_default_context(cafile=certifi.where())
URL = "https://api.deepinfra.com/v1/openai/embeddings"


def embed(model, texts, timeout=120):
    payload = {"model": model, "input": texts, "encoding_format": "float"}
    if os.environ.get("EMBED_DIMS"):
        payload["dimensions"] = int(os.environ["EMBED_DIMS"])
    body = json.dumps(payload).encode()
    req = urllib.request.Request(URL, data=body, headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"}, method="POST")
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:  # nosec B310 - fixed https URL
            d = json.loads(r.read())
        return r.status, d, time.perf_counter() - t0
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300], time.perf_counter() - t0
    except Exception as e:  # noqa: BLE001 - the caller retries on status 0
        return 0, repr(e)[:200], time.perf_counter() - t0
