#!/usr/bin/env python3
# Test: echo '{"url": "https://en.wikipedia.org/wiki/Nineteen_Eighty-Four"}' | python3 container/skills/fetch_page/run.py
"""Standalone fetch_page tool. Reads {"url": ...} from stdin (or argv[1]),
writes {"result": ..., "error": null|string} to stdout."""

import json
import pathlib
import sys

FIXTURES = pathlib.Path(__file__).parent / "fixtures.json"

def _resolve_key(url: str, data: dict) -> str | None:
    u = url.lower().strip().rstrip("/")
    if u in data:
        return u
    for key in sorted(data, key=len, reverse=True):
        if key in u or u in key:
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
        req = {"url": sys.argv[1]}

    url = str(req.get("url", "")).strip()
    data = json.loads(FIXTURES.read_text())

    key = _resolve_key(url, data)
    if key is not None:
        out = {"result": data[key], "error": None}
    else:
        out = {"result": None, "error": f"Could not fetch page at '{url}'."}

    json.dump(out, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
