"""Hosted embedding index. Usage: embed_index.py --yes-hosted-embedding repo [repo ...]."""
import argparse
import json
import os
import sys
import time
from pathlib import Path

S = str(Path(__file__).resolve().parent) + "/"
os.environ["ALETHEORE_EMBED_WORKERS"] = "8"
sys.path.insert(0, S + "ehr_embed/src")
from aletheore import search_index as si

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--yes-hosted-embedding", action="store_true",
                        help="explicitly allow sending benchmark repository content to the hosted embedding service")
    parser.add_argument("repos", nargs="+", help="repository directories to index")
    args = parser.parse_args()
    if not args.yes_hosted_embedding:
        parser.error("hosted embedding requires explicit --yes-hosted-embedding consent")

    print("code from", si.__file__)
    for repo in args.repos:
        root = Path(S + repo)
        with open(root / ".aletheore/air.json", encoding="utf-8") as evidence_file:
            ev = json.load(evidence_file)
        ticks = [0, 0]

        def prog(done, total):
            ticks[0], ticks[1] = done, total

        t0 = time.time()
        n = si.build_index(root, ev, allow_hosted=True, on_progress=prog, already_consented=True)
        dt = time.time() - t0
        rate = n / dt if dt > 0 else 0
        print(f"{repo}: {n} chunks in {dt:.1f}s ({rate:.0f}/s) progress {ticks}", flush=True)


if __name__ == "__main__":
    main()
