#!/usr/bin/env python3
"""Simulated web_search tool. Reads {"query": ...} from stdin (or argv[1]),
writes {"results": [...], "error": null|string} to stdout."""

import json
import pathlib
import sys

FIXTURES = pathlib.Path(__file__).parent / "fixtures.json"

def _resolve_key(query: str, data: dict) -> str | None:
    q = query.lower().strip()
    if q in data:
        return q
    for key in sorted(data, key=len, reverse=True):
        if key in q or q in key:
            return key
    return None


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

    key = _resolve_key(query, data)
    if key is not None:
        out = {"results": data[key], "error": None}
    else:
        out = {
            "results": [],
            "error": "No results found.",
        }
    json.dump(out, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
