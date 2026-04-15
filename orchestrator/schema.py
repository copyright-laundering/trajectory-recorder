"""Pydantic models for trajrec tasks and run artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class Task(BaseModel):
    """A single evaluation task loaded from a YAML file."""

    id: str
    prompt: str
    timeout_s: int = Field(default=300, gt=0)
    # Optional per-task overrides. If unset the CLI default is used.
    model: str | None = None

    @classmethod
    def from_yaml(cls, path: Path) -> "Task":
        data: dict[str, Any] = yaml.safe_load(path.read_text())
        return cls.model_validate(data)


class TaskResult(BaseModel):
    """Outcome of a single task run — what the orchestrator records per task."""

    task_id: str
    run_id: str
    model_id: str
    exit_code: int
    duration_ns: int
    timed_out: bool = False
    trajectory_path: Path
    manifest_path: Path
    final_path: Path
    stdout_path: Path
    stderr_path: Path
    # Summary validation flags
    trajectory_ok: bool = False
    final_ok: bool = False
    note: str | None = None


class RunIndex(BaseModel):
    """Top-level index written for a whole run (many tasks)."""

    run_id: str
    image: str
    image_digest: str | None = None
    default_model_id: str
    started_at: str
    finished_at: str | None = None
    tasks: list[TaskResult] = Field(default_factory=list)
