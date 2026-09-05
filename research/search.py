#!/usr/bin/env python3
"""tieout research search — Parallel Search API wrapper (docs.parallel.ai/home).

Usage:
  python3 research/search.py --objective "Find X" -q "query 1" -q "query 2" [--max-results 10]

Reads PARALLEL_API_KEY from repo-root .env or the environment. Prints LLM-optimized
excerpts per result so findings can be pasted into research/methodology-notes.md.
"""

import argparse
import json
import os
import subprocess
import sys


def load_env(path: str) -> None:
    if os.environ.get("PARALLEL_API_KEY"):
        return
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if line.startswith("PARALLEL_API_KEY="):
                os.environ["PARALLEL_API_KEY"] = line.split("=", 1)[1].strip().strip("'\"")
                return


def search(objective: str, queries: list[str], max_results: int) -> dict:
    body = {
        "objective": objective,
        "search_queries": queries,
        "advanced_settings": {"max_results": max_results},
    }
    # curl instead of urllib: macOS python.org builds often lack the SSL cert
    # bundle (CERTIFICATE_VERIFY_FAILED), while curl uses system certs.
    proc = subprocess.run(
        [
            "curl", "-sS", "--fail", "--max-time", "120",
            "https://api.parallel.ai/v1/search",
            "-H", "Content-Type: application/json",
            "-H", f"x-api-key: {os.environ['PARALLEL_API_KEY']}",
            "-d", json.dumps(body),
        ],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        sys.exit(f"search failed: {proc.stderr.strip()}")
    return json.loads(proc.stdout)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--objective", required=True)
    ap.add_argument("-q", "--query", dest="queries", action="append", required=True)
    ap.add_argument("--max-results", type=int, default=10)
    args = ap.parse_args()

    load_env(os.path.join(os.path.dirname(__file__), "..", ".env"))
    if not os.environ.get("PARALLEL_API_KEY"):
        sys.exit("PARALLEL_API_KEY not set (.env or environment)")

    data = search(args.objective, args.queries, args.max_results)
    for r in data.get("results", []):
        print(f"\n== {r.get('title')} — {r.get('url')}")
        if r.get("publish_date"):
            print(f"   published: {r['publish_date']}")
        for ex in r.get("excerpts", []):
            print(f"   | {ex}")


if __name__ == "__main__":
    main()
