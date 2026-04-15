#!/usr/bin/env python3
"""Simulated web_search tool. Reads {"query": ...} from stdin (or argv[1]),
writes {"results": [...], "error": null|string} to stdout."""

import json
import pathlib
import sys

FIXTURES = pathlib.Path(__file__).parent / "fixtures.json"


def main() -> None:
    raw = sys.stdin.read().strip() if not sys.stdin.isatty() else ""
    req: dict = {}
    if raw:
        try:
            req = json.loads(raw)
        except json.JSONDecodeError:
            req = {}
    if not req and len(sys.argv) > 1:
        req = {"query": sys.argv[1]}

    query = str(req.get("query", "")).strip().lower()
    data = json.loads(FIXTURES.read_text())

    if query in data:
        out = {"results": data[query], "error": None}
    else:
        out = {
            "results": [],
            "error": "simulated web_search only accepts query='1984'",
        }
    json.dump(out, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
