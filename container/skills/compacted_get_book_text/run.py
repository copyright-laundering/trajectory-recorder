#!/usr/bin/env python3
# Test: echo '{"title": "1984"}' | python3 container/skills/compacted_get_book_text/run.py
# Test: echo '{"title": "The Kite Runner", "author": "Khaled Hosseini"}' | python3 container/skills/compacted_get_book_text/run.py
"""Standalone compacted_get_book_text tool. Reads {"title": ..., "author": ...} from stdin (or argv[1]),
writes {"result": ..., "error": null|string} to stdout."""

import json
import pathlib
import sys

FIXTURES = pathlib.Path(__file__).parent / "fixtures.json"

def _resolve_key(title: str, data: dict) -> str | None:
    t = title.lower().strip()
    if t in data:
        return t
    for key in sorted(data, key=len, reverse=True):
        if key in t or t in key:
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
        req = {"title": sys.argv[1]}

    title = str(req.get("title", "")).strip()
    data = json.loads(FIXTURES.read_text())

    key = _resolve_key(title, data)
    if key is not None:
        out = {"result": data[key], "error": None}
    else:
        out = {"result": None, "error": f"Could not retrieve text for '{title}'."}

    json.dump(out, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
