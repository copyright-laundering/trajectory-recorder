#!/usr/bin/env python3
# Test: echo '{"identifier": "10.1093/owc/9780198829707.001.0001", "identifier_type": "DOI"}' | python3 container/skills/fetch_by_identifier/run.py
# Test: echo '{"identifier": "978-0-451-52493-5", "identifier_type": "ISBN"}' | python3 container/skills/fetch_by_identifier/run.py
"""Standalone fetch_by_identifier tool. Reads {"identifier": ..., "identifier_type": ...} from stdin (or argv[1]),
writes {"result": ..., "error": null|string} to stdout."""

import json
import pathlib
import sys

FIXTURES = pathlib.Path(__file__).parent / "fixtures.json"

def _resolve_key(identifier: str, data: dict) -> str | None:
    id_l = identifier.lower().strip()
    if id_l in data:
        return id_l
    id_norm = id_l.replace("-", "").replace(" ", "")
    for key in data:
        if key.replace("-", "").replace(" ", "") == id_norm:
            return key
    for key in sorted(data, key=len, reverse=True):
        if key in id_l or id_l in key:
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
        req = {"identifier": sys.argv[1]}

    identifier = str(req.get("identifier", "")).strip()
    data = json.loads(FIXTURES.read_text())

    key = _resolve_key(identifier, data)
    if key is not None:
        out = {"result": data[key], "error": None}
    else:
        out = {"result": None, "error": f"No record found for identifier '{identifier}'."}

    json.dump(out, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
