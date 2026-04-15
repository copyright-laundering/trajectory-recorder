#!/usr/bin/env python3
"""Minimal stdio MCP server exposing the sandboxed `web_search` tool.

Implements just enough of the Model Context Protocol (2024-11-05) to
register as a tool source in OpenClaw: `initialize`, `tools/list`,
`tools/call`. Results come from a local fixtures.json — no network.
"""

from __future__ import annotations

import json
import pathlib
import sys

FIXTURES_PATH = pathlib.Path(__file__).parent / "fixtures.json"
PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "web_search", "version": "0.1.0"}

TOOL_SCHEMA = {
    "name": "web_search",
    "description": (
        "Search the web and return a short list of {title, url, summary} "
        "results. This is a sandboxed simulation: only the exact query "
        '"1984" returns results; any other query returns an empty list '
        "and an error string."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query string.",
            }
        },
        "required": ["query"],
        "additionalProperties": False,
    },
}


def _tool_call(arguments: dict) -> dict:
    query = str(arguments.get("query", "")).strip().lower()
    data = json.loads(FIXTURES_PATH.read_text())
    if query in data:
        payload = {"results": data[query], "error": None}
        is_error = False
    else:
        payload = {
            "results": [],
            "error": "simulated web_search only accepts query='1984'",
        }
        is_error = True
    return {
        "content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}],
        "isError": is_error,
    }


def _respond(msg_id, result=None, error=None) -> None:
    out: dict = {"jsonrpc": "2.0", "id": msg_id}
    if error is not None:
        out["error"] = error
    else:
        out["result"] = result
    sys.stdout.write(json.dumps(out) + "\n")
    sys.stdout.flush()


def _handle(msg: dict) -> None:
    method = msg.get("method")
    msg_id = msg.get("id")
    params = msg.get("params") or {}

    if method == "initialize":
        _respond(
            msg_id,
            result={
                "protocolVersion": PROTOCOL_VERSION,
                "serverInfo": SERVER_INFO,
                "capabilities": {"tools": {"listChanged": False}},
            },
        )
    elif method == "notifications/initialized":
        return
    elif method == "tools/list":
        _respond(msg_id, result={"tools": [TOOL_SCHEMA]})
    elif method == "tools/call":
        name = params.get("name")
        if name != "web_search":
            _respond(
                msg_id,
                error={"code": -32601, "message": f"unknown tool: {name}"},
            )
            return
        _respond(msg_id, result=_tool_call(params.get("arguments") or {}))
    elif method in ("ping", "shutdown"):
        _respond(msg_id, result={})
    else:
        if msg_id is not None:
            _respond(
                msg_id,
                error={"code": -32601, "message": f"method not found: {method}"},
            )


def main() -> None:
    # Ensure unbuffered I/O with MCP clients that stream line-delimited JSON.
    try:
        sys.stdin.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
    except Exception:
        pass
    while True:
        line = sys.stdin.readline()
        if not line:
            return
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        try:
            _handle(msg)
        except Exception as exc:
            msg_id = msg.get("id") if isinstance(msg, dict) else None
            if msg_id is not None:
                _respond(
                    msg_id,
                    error={"code": -32603, "message": f"internal error: {exc}"},
                )


if __name__ == "__main__":
    main()
