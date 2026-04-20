#!/usr/bin/env python3
# Test: echo '{"pdf_path": "1984_scan.pdf"}' | python3 container/skills/pdf_to_text/run.py
"""Standalone pdf_to_text tool. Reads {"pdf_path": ..., "pages": ...} from stdin (or argv[1]),
writes {"result": ..., "error": null|string} to stdout."""

import json
import pathlib
import sys

FIXTURES = pathlib.Path(__file__).parent / "fixtures.json"

def _resolve_key(pdf_path: str, data: dict) -> str | None:
    p = pdf_path.lower().strip()
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
        req = {"pdf_path": sys.argv[1]}

    pdf_path = str(req.get("pdf_path", "")).strip()
    pages = req.get("pages")
    data = json.loads(FIXTURES.read_text())

    key = _resolve_key(pdf_path, data)
    if key is not None:
        result = dict(data[key])
        if pages:
            result["pages_extracted"] = pages
        out = {"result": result, "error": None}
    else:
        out = {"result": None, "error": f"Could not extract text from '{pdf_path}'."}

    json.dump(out, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
