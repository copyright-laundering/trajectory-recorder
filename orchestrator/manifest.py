"""Helpers that produce identifying metadata for a run.

Keeps side-effecting calls (docker inspect, subprocess) behind small
functions so runner.py can call them once per run and embed the result
into the on-disk index.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


def docker_image_digest(docker_bin: str, image: str) -> str | None:
    """Return the content-addressable image ID (sha256:...) or None if missing."""
    try:
        out = subprocess.run(
            [docker_bin, "image", "inspect", "--format", "{{.Id}}", image],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    digest = out.stdout.strip()
    return digest or None


def parse_trajectory(path: Path) -> dict:
    """Shallow validation of trajectory.jsonl. Returns a summary dict."""
    summary = {
        "ok": False,
        "line_count": 0,
        "has_session_header": False,
        "has_assistant_final": False,
        "tool_calls": 0,
        "tool_results": 0,
        "tools_seen": [],
    }
    if not path.exists():
        return summary

    tools_seen: set[str] = set()
    last_assistant = False
    for raw in path.read_text().splitlines():
        raw = raw.strip()
        if not raw:
            continue
        summary["line_count"] += 1
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue
        t = obj.get("type")
        if t == "session":
            summary["has_session_header"] = True
        msg = obj.get("message") or {}
        role = msg.get("role")
        if role == "assistant":
            last_assistant = True
        elif role == "toolResult":
            summary["tool_results"] += 1
            name = msg.get("toolName")
            if name:
                tools_seen.add(name)
        else:
            last_assistant = False if role else last_assistant
        # tool call entries live inside assistant content blocks in OpenClaw;
        # count message entries whose content references a tool use.
        content = msg.get("content") or []
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "toolUse":
                    summary["tool_calls"] += 1

    summary["has_assistant_final"] = last_assistant
    summary["tools_seen"] = sorted(tools_seen)
    summary["ok"] = (
        summary["has_session_header"]
        and summary["line_count"] > 1
        and summary["has_assistant_final"]
    )
    return summary
