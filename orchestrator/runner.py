"""Per-task docker lifecycle.

Responsible for: composing the `docker run` invocation, preparing the
per-task bind-mount layout, streaming output to files, enforcing the
per-task timeout via `docker stop`, and returning a TaskResult.

One-shot: `docker run --rm`. Cleanup is implicit.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import uuid
from pathlib import Path

from .manifest import parse_trajectory
from .schema import Task, TaskResult


DEFAULT_IMAGE = "trajrec-openclaw:test"
DEFAULT_DOCKER = "/opt/homebrew/bin/docker"


def _prepare_task_dirs(
    run_dir: Path, task: Task
) -> tuple[Path, Path, Path]:
    """Create the per-task task/ and results/ directories, and write task.yaml.

    Returns (host_task_yaml, host_results_dir, task_scratch_dir).
    Everything lives under the orchestrator's run_dir, which the caller guarantees
    sits under $HOME (required for Colima virtiofs).
    """
    task_scratch = run_dir / task.id
    task_dir = task_scratch / "task"
    results_dir = task_scratch / "results"
    task_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)

    task_yaml_path = task_dir / "task.yaml"
    task_yaml_path.write_text(
        "id: {id}\ntimeout_s: {t}\nprompt: |\n{prompt}\n".format(
            id=task.id,
            t=task.timeout_s,
            prompt="\n".join("  " + line for line in task.prompt.splitlines()),
        )
    )
    return task_yaml_path, results_dir, task_scratch


def _compose_docker_args(
    *,
    docker_bin: str,
    image: str,
    task: Task,
    model_id: str,
    run_id: str,
    container_name: str,
    openrouter_api_key: str,
    task_yaml_host: Path,
    results_host: Path,
) -> list[str]:
    # Host-side timeout is soft — we rely on AGENT_TIMEOUT_S inside the container
    # for the normal path, and `docker stop` for the hard kill if that fails.
    agent_timeout = max(task.timeout_s - 5, 5)
    return [
        docker_bin,
        "run",
        "--rm",
        "--name",
        container_name,
        "--user",
        "0:0",
        "-e",
        "HOME=/root",
        "-e",
        "OPENCLAW_CONFIG_DIR=/root/.openclaw",
        "-e",
        f"OPENROUTER_API_KEY={openrouter_api_key}",
        "-e",
        f"TASK_ID={task.id}",
        "-e",
        f"RUN_ID={run_id}",
        "-e",
        f"MODEL_ID={model_id}",
        "-e",
        f"AGENT_TIMEOUT_S={agent_timeout}",
        "-v",
        f"{task_yaml_host}:/task/task.yaml:ro",
        "-v",
        f"{results_host}:/results",
        image,
    ]


def run_task(
    task: Task,
    *,
    run_id: str,
    run_dir: Path,
    model_id: str,
    image: str = DEFAULT_IMAGE,
    docker_bin: str = DEFAULT_DOCKER,
    openrouter_api_key: str | None = None,
) -> TaskResult:
    """Run a single task in a one-shot container. Blocks until completion."""
    if openrouter_api_key is None:
        openrouter_api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not openrouter_api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY must be set (env or explicit argument)."
        )
    if not shutil.which(docker_bin) and not Path(docker_bin).exists():
        raise RuntimeError(f"docker binary not found at {docker_bin!r}")

    task_yaml_host, results_host, _ = _prepare_task_dirs(run_dir, task)

    container_name = f"trajrec-{run_id}-{task.id}-{uuid.uuid4().hex[:6]}"
    argv = _compose_docker_args(
        docker_bin=docker_bin,
        image=image,
        task=task,
        model_id=model_id,
        run_id=run_id,
        container_name=container_name,
        openrouter_api_key=openrouter_api_key,
        task_yaml_host=task_yaml_host,
        results_host=results_host,
    )

    orchestrator_stdout = results_host / "orchestrator.stdout.log"
    orchestrator_stderr = results_host / "orchestrator.stderr.log"
    t0 = time.time_ns()
    timed_out = False

    with open(orchestrator_stdout, "wb") as out, open(orchestrator_stderr, "wb") as err:
        proc = subprocess.Popen(argv, stdout=out, stderr=err)
        try:
            exit_code = proc.wait(timeout=task.timeout_s)
        except subprocess.TimeoutExpired:
            timed_out = True
            # Best-effort graceful stop, then kill the docker client itself.
            subprocess.run(
                [docker_bin, "stop", "-t", "5", container_name],
                capture_output=True,
            )
            try:
                exit_code = proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()
                exit_code = proc.wait()

    duration_ns = time.time_ns() - t0

    trajectory_path = results_host / "trajectory.jsonl"
    manifest_path = results_host / "manifest.json"
    final_path = results_host / "final.json"
    stdout_path = results_host / "stdout.log"
    stderr_path = results_host / "stderr.log"

    traj_summary = parse_trajectory(trajectory_path)
    final_ok = False
    if final_path.exists():
        try:
            final = json.loads(final_path.read_text())
            final_ok = bool(final.get("final_message"))
        except json.JSONDecodeError:
            final_ok = False

    note = None
    if timed_out:
        note = f"host-enforced timeout after {task.timeout_s}s"
    elif exit_code != 0:
        note = f"container exited with code {exit_code}"
    elif not traj_summary["ok"]:
        note = "trajectory did not parse as a valid session"

    return TaskResult(
        task_id=task.id,
        run_id=run_id,
        model_id=model_id,
        exit_code=exit_code,
        duration_ns=duration_ns,
        timed_out=timed_out,
        trajectory_path=trajectory_path,
        manifest_path=manifest_path,
        final_path=final_path,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        trajectory_ok=traj_summary["ok"],
        final_ok=final_ok,
        note=note,
    )
