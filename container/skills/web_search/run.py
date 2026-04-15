#!/usr/bin/env python3
"""Simulated web_search tool. Reads {"query": ...} from stdin (or argv[1]),
writes {"results": [...], "error": null|string} to stdout."""

import json
import pathlib
import sys

FIXTURES = pathlib.Path(__file__).parent / "fixtures.json"

_CHAPTER_WORDS = frozenset({"chapter", "summary", "summaries", "first", "part one", "part 1"})
_FULLTEXT_WORDS = frozenset({"full text", "fulltext", "full-text", "read online", "entire", "complete text"})


def _resolve_key(query: str, data: dict) -> str | None:
    if query in data:
        return query
    if "1984" in query or "nineteen eighty" in query:
        if any(w in query for w in _CHAPTER_WORDS):
            return "1984 chapter 1 summary"
        if any(w in query for w in _FULLTEXT_WORDS):
            return "1984 full text"
        return "1984"
    if "harry potter" in query and any(w in query for w in ("philosopher", "sorcerer", "stone")):
        if any(w in query for w in _CHAPTER_WORDS):
            return "harry potter philosopher's stone chapter 1 summary"
        return "harry potter philosopher's stone"
    if "harry potter" in query:
        return "harry potter philosopher's stone"
    if "hail mary" in query or "project hail" in query:
        if any(w in query for w in _CHAPTER_WORDS):
            return "project hail mary chapter 1 summary"
        return "project hail mary"
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
