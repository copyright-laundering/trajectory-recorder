"""Typer CLI entry-point: `trajrec run --tasks tasks/example.yaml`."""

from __future__ import annotations

import datetime as dt
import json
import os
import sys
from pathlib import Path

import typer

from .manifest import docker_image_digest
from .runner import DEFAULT_DOCKER, DEFAULT_IMAGE, run_task
from .schema import RunIndex, Task

app = typer.Typer(
    add_completion=False,
    help="Resettable OpenClaw evaluation harness.",
)

DEFAULT_MODEL = "openrouter/google/gemini-2.5-flash-lite-preview-09-2025"


def _collect_tasks(paths: list[Path]) -> list[Path]:
    result: list[Path] = []
    for path in paths:
        if path.is_dir():
            result.extend(sorted(p for p in path.glob("*.yaml") if p.is_file()))
        elif path.is_file():
            result.append(path)
        else:
            raise typer.BadParameter(f"tasks path not found: {path}")
    return result


def _default_run_dir(run_id: str) -> Path:
    # Colima virtiofs requires bind-mounted paths to live under $HOME.
    home = Path(os.environ["HOME"])
    return home / "trajrec-runs" / run_id


@app.command("run")
def run_cmd(
    tasks: list[Path] = typer.Option(
        ..., "--tasks", exists=True,
        help="Path to a task YAML or a directory. Repeat to pass multiple paths.",
    ),
    run_id: str | None = typer.Option(
        None, "--run-id", help="Stable id for this run (default: UTC timestamp)."
    ),
    model: str = typer.Option(
        DEFAULT_MODEL,
        "--model",
        help="Default model id (provider/name). Overridable per-task.",
    ),
    image: str = typer.Option(DEFAULT_IMAGE, "--image"),
    docker_bin: str = typer.Option(DEFAULT_DOCKER, "--docker-bin"),
    run_dir: Path | None = typer.Option(
        None,
        "--run-dir",
        help="Where to write per-task artifacts. Must live under $HOME for Colima.",
    ),
) -> None:
    """Run each task sequentially in a disposable container."""
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        typer.secho(
            "OPENROUTER_API_KEY is not set in the environment.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=2)

    run_id = run_id or dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = run_dir or _default_run_dir(run_id)
    run_dir.mkdir(parents=True, exist_ok=True)

    task_paths = _collect_tasks(list(tasks))
    if not task_paths:
        typer.secho(f"no tasks found at {tasks!r}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2)

    index = RunIndex(
        run_id=run_id,
        image=image,
        image_digest=docker_image_digest(docker_bin, image),
        default_model_id=model,
        started_at=dt.datetime.now(dt.timezone.utc).isoformat(),
    )

    index_path = run_dir / "index.json"

    for tp in task_paths:
        task = Task.from_yaml(tp)
        task_model = task.model or model
        typer.secho(
            f"[trajrec] running task {task.id} (model={task_model}, timeout={task.timeout_s}s)",
            fg=typer.colors.CYAN,
        )
        try:
            result = run_task(
                task,
                run_id=run_id,
                run_dir=run_dir,
                model_id=task_model,
                image=image,
                docker_bin=docker_bin,
                openrouter_api_key=api_key,
            )
        except Exception as exc:  # surface to index and keep going
            typer.secho(f"  ! {exc}", fg=typer.colors.RED, err=True)
            raise
        index.tasks.append(result)
        status = "ok" if result.trajectory_ok and result.exit_code == 0 else "fail"
        color = typer.colors.GREEN if status == "ok" else typer.colors.YELLOW
        note = f" — {result.note}" if result.note else ""
        typer.secho(
            f"  {status} exit={result.exit_code} duration={result.duration_ns/1e9:.1f}s{note}",
            fg=color,
        )
        # Persist the index after every task so a crash still leaves a record.
        index_path.write_text(index.model_dump_json(indent=2))

    index.finished_at = dt.datetime.now(dt.timezone.utc).isoformat()
    index_path.write_text(index.model_dump_json(indent=2))

    typer.secho(f"\n[trajrec] run {run_id} complete: {index_path}", fg=typer.colors.CYAN)
    # Non-zero exit if any task failed
    if any(t.exit_code != 0 or not t.trajectory_ok for t in index.tasks):
        raise typer.Exit(code=1)


def main() -> None:  # pragma: no cover — console_scripts entry
    app()


if __name__ == "__main__":
    main()
