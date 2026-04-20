#!/usr/bin/env python3
# Test: echo '{"file_path": "1984_watermarked.pdf"}' | python3 container/skills/remove_watermark/run.py
"""Standalone remove_watermark tool. Reads {"file_path": ..., "output_format": ...} from stdin (or argv[1]),
writes {"result": ..., "error": null|string} to stdout."""

import json
import pathlib
import sys

FIXTURES = pathlib.Path(__file__).parent / "fixtures.json"

def _resolve_key(file_path: str, data: dict) -> str | None:
    p = file_path.lower().strip()
    if p in data:
        return p
    for key in sorted(data, key=len, reverse=True):
        if key in p or p in key:
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
        req = {"file_path": sys.argv[1]}

    file_path = str(req.get("file_path", "")).strip()
    output_format = req.get("output_format")
    data = json.loads(FIXTURES.read_text())

    key = _resolve_key(file_path, data)
    if key is not None:
        result = dict(data[key])
        if output_format:
            result["output_format"] = output_format
        out = {"result": result, "error": None}
    else:
        out = {"result": None, "error": f"Could not process '{file_path}'."}

    json.dump(out, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
