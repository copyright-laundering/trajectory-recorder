#!/usr/bin/env python3
# Test: echo '{"title": "1984", "chapter": "1"}' | python3 container/skills/fetch_book_excerpt/run.py
"""Standalone fetch_book_excerpt tool. Reads {"title": ..., "chapter": ...} from stdin (or argv[1]),
writes {"excerpt": ..., "error": null|string} to stdout."""

import json
import pathlib
import sys

FIXTURES = pathlib.Path(__file__).parent / "fixtures.json"


def _resolve_key(title: str, chapter: str | None, data: dict) -> str | None:
    title_l = title.lower().strip()
    chapter_l = (chapter or "").lower().strip()
    combined = f"{title_l} {chapter_l}".strip() if chapter_l else title_l

    if combined in data:
        return combined
    if title_l in data:
        return title_l

    for key in sorted(data, key=len, reverse=True):
        if key in combined or combined in key:
            return key
    for key in sorted(data, key=len, reverse=True):
        if key in title_l or title_l in key:
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
    chapter = str(req.get("chapter", "")).strip() or None
    data = json.loads(FIXTURES.read_text())

    key = _resolve_key(title, chapter, data)
    if key is not None:
        out = {"excerpt": data[key], "error": None}
    else:
        out = {"excerpt": None, "error": f"No excerpt available for '{title}'."}

    json.dump(out, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
