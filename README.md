# trajectory-recorder

A **resettable agent evaluation pipeline** for [OpenClaw](https://openclaw.ai).
Every task runs in a fresh, disposable Docker container with a fixed skill set
and a fixed system prompt, so runs are directly comparable: no memory, no
caches, no OAuth, no session carry-over. Each run emits a complete trajectory
(prompt, model outputs, tool calls + arguments + results, errors, final answer)
to a host results directory.

- **Model provider:** OpenRouter (only).
- **Default test model:** `openrouter/google/gemini-2.5-flash-lite-preview-09-2025`.
- **Preset tool:** a sandboxed, deterministic `web_search` (returns fixture
  data for query `"1984"`, empty + error otherwise).

## Repository layout

```
.
├── CLAUDE.md                     # guidance for Claude Code in this repo
├── README.md                     # this file
├── pyproject.toml                # installs `trajrec` CLI
├── tasks/
│   └── example.yaml              # sample task (id, prompt, timeout_s, optional model)
├── orchestrator/                 # host-side Python CLI
│   ├── cli.py                    # `trajrec` entry-point (Typer)
│   ├── runner.py                 # per-task docker lifecycle
│   ├── manifest.py               # image digest + trajectory summary helpers
│   └── schema.py                 # pydantic models (Task, TaskResult, RunIndex)
└── container/                    # everything that runs inside the container
    ├── Dockerfile                # node:22-slim + openclaw + acpx + python3 + jq
    ├── entrypoint.sh             # reset → render config → run → export → wipe
    ├── config/
    │   ├── openclaw.json.template   # jq-templated OpenClaw config
    │   └── api-instructions.md      # fixed system prompt
    └── skills/web_search/
        ├── SKILL.md              # natural-language guidance (not a tool registration)
        ├── mcp_server.py         # stdio JSON-RPC MCP server — registers the web_search tool
        ├── fixtures.json         # deterministic results for query "1984"
        └── run.py                # legacy one-shot wrapper (unused in the active pipeline)
```

### What each file does

| Path | Responsibility |
|---|---|
| `pyproject.toml` | Package metadata + `trajrec` console script. |
| `orchestrator/schema.py` | `Task` loaded from YAML; `TaskResult` recorded per task; `RunIndex` aggregates a run. |
| `orchestrator/manifest.py` | Resolves image digest via `docker image inspect`; shallow-validates `trajectory.jsonl`. |
| `orchestrator/runner.py` | Writes `task.yaml` into a per-task scratch dir, composes `docker run` args, enforces timeout via `docker stop`, parses results. |
| `orchestrator/cli.py` | `trajrec --tasks <yaml-or-dir> [--run-id X] [--model Y]` — iterates tasks sequentially, persists `index.json` crash-safely. |
| `container/Dockerfile` | Installs `openclaw` + `acpx` npm packages (pinned), `python3`, `jq`, `tini`. |
| `container/entrypoint.sh` | Per-run lifecycle. Renders `openclaw.json` from the template (jq substitutes model slug, system prompt, and the runtime MCP server path), validates config, runs `openclaw agent --local --json`, exports the session JSONL as `trajectory.jsonl`, writes `manifest.json` and `final.json`, wipes state. |
| `container/config/openclaw.json.template` | Disables all built-in web tools (`tools.profile: "minimal"`, `tools.web.{search,fetch,x_search}.enabled: false`), wires OpenRouter as the sole provider, registers the `web_search` MCP server, and sets an agent-level tool allowlist. |
| `container/config/api-instructions.md` | Fixed system prompt that describes the single available tool and forbids invention. |
| `container/skills/web_search/mcp_server.py` | Minimal MCP 2024-11-05 stdio server; implements `initialize`, `tools/list`, `tools/call`. The only thing the agent can actually call. |
| `container/skills/web_search/fixtures.json` | Canned results (wiki / buy / reviews / fulltext) for query `"1984"`. |

## Setup

### 1. Prerequisites

- **macOS/Linux** with Docker-compatible runtime.
  - On macOS the current setup is tested with [Colima](https://github.com/abiosoft/colima) at `/opt/homebrew/bin/{docker,colima}`.
- **Python 3.11+**.
- An **OpenRouter API key** (`sk-or-v1-...`).

### 2. Start Docker / Colima

```bash
colima start               # first time or after reboot
docker ps                  # sanity check — should succeed
```

> **Colima note.** Only `$HOME` is virtiofs-mounted into the VM, so
> bind-mounted host paths must live under your home directory. Bind mounts
> also appear as uid=0 inside the container; the orchestrator handles this
> by passing `--user 0:0 -e HOME=/root -e OPENCLAW_CONFIG_DIR=/root/.openclaw`
> at run time.
>
> This `--user 0:0` workaround is **only needed on Colima**. On Linux or
> CI environments (GitHub Actions, cloud VMs) Docker bind mounts respect
> normal uid ownership, so the container's default `node` user can write to
> `/results` without it. If you move this pipeline off Colima, simply remove
> the `--user 0:0` / `HOME` / `OPENCLAW_CONFIG_DIR` overrides from
> `orchestrator/runner.py` and everything works as-is.

### 3. Provide the API key

Create `~/.trajrec.env` with permissions `600`:

```bash
install -m 600 /dev/null ~/.trajrec.env
cat > ~/.trajrec.env <<'ENV'
OPENROUTER_API_KEY=sk-or-v1-your-key-here
ENV
```

Source it before running the CLI:

```bash
set -a; source ~/.trajrec.env; set +a
```

### 4. Build the container image

From the repo root:

```bash
/opt/homebrew/bin/docker build -t trajrec-openclaw:test container/
```

Override package pins at build time if needed:

```bash
--build-arg OPENCLAW_PKG=openclaw@<version> \
--build-arg ACPX_PKG=acpx@<version>
```

### 5. Install the Python orchestrator

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
```

This installs a `trajrec` console script inside `.venv/bin`.

## Running an experiment

### Single task

```bash
set -a; source ~/.trajrec.env; set +a
.venv/bin/trajrec --tasks tasks/example.yaml --run-id demo1
```

### A batch of tasks from a directory

```bash
.venv/bin/trajrec --tasks tasks/ --run-id demo-batch
```

### CLI options

| Flag | Default | Purpose |
|---|---|---|
| `--tasks PATH` | *(required)* | Task YAML or directory containing `*.yaml` tasks. |
| `--run-id TEXT` | UTC timestamp | Stable id — the output directory name. |
| `--model TEXT` | `openrouter/google/gemini-2.5-flash-lite-preview-09-2025` | Default model id; each task may override via `model:`. |
| `--image TEXT` | `trajrec-openclaw:test` | Container image tag. |
| `--docker-bin TEXT` | `/opt/homebrew/bin/docker` | Path to the docker binary. |
| `--run-dir PATH` | `$HOME/trajrec-runs/<run-id>` | Where to write artifacts (must be under `$HOME`). |

The CLI exits non-zero if any task fails (non-zero container exit or malformed
trajectory).

## Task format

```yaml
# tasks/example.yaml
id: example
prompt: |
  Use web_search to look up "1984" and summarize what you find in one paragraph.
  Cite the URLs returned.
timeout_s: 60
# model: openrouter/anthropic/claude-3.5-sonnet   # optional per-task override
```

Required: `id`, `prompt`. Optional: `timeout_s` (default 300), `model`.

## Where artifacts land

```
$HOME/trajrec-runs/<run-id>/
├── index.json                    # top-level run index (updated after every task)
└── <task-id>/
    ├── task/task.yaml            # rendered task input (bind-mounted read-only into container)
    └── results/
        ├── trajectory.jsonl      # per-session log (session header + messages + toolResults)
        ├── final.json            # extracted last assistant message + exit code
        ├── manifest.json         # run_id, task_id, model_id, exit_code, duration_ns, skill hashes
        ├── skill-manifest.json   # SHA-256 of each installed skill directory
        ├── stdout.log            # openclaw --json payload
        ├── stderr.log            # openclaw warnings / diagnostics
        ├── orchestrator.stdout.log
        └── orchestrator.stderr.log
```

### Validating a run by hand

```bash
# Did the agent call OUR sandboxed tool (not Perplexity)?
grep -c '"toolName": "web_search__web_search"' \
  $HOME/trajrec-runs/<run-id>/<task-id>/results/trajectory.jsonl

# Did the container start the MCP server cleanly?
! grep "\[bundle-mcp\] failed" \
  $HOME/trajrec-runs/<run-id>/<task-id>/results/stderr.log

# What was the final answer?
python3 -c "
import json, sys
d = json.load(open(sys.argv[1]))
for b in d['final_message']['message']['content']:
    if b.get('type') == 'text': print(b['text'])
" $HOME/trajrec-runs/<run-id>/<task-id>/results/final.json
```

## Pipeline lifecycle (what happens per task)

1. **Orchestrator** (host) resolves the docker image digest, composes a per-task
   scratch directory under `$HOME/trajrec-runs/<run-id>/<task-id>/`, writes
   `task.yaml`, and invokes `docker run --rm ...`.
2. **Entrypoint** (container) wipes `$OPENCLAW_CONFIG_DIR`, caches, and `/tmp`;
   copies the vendored skills into `~/.openclaw/skills/`.
3. **Config render.** `jq` substitutes `$MODEL_SLUG`, the system prompt, and
   the runtime MCP server path into `openclaw.json.template` → `openclaw.json`.
4. **Validation.** `openclaw config validate` fails-fast on a bad config.
5. **Agent run.** `openclaw agent --local --json` runs a single-process,
   gateway-less agent. The agent reads the task prompt and calls `web_search`
   via the MCP stdio server, which returns fixture data.
6. **Export.** The newest `~/.openclaw/agents/trajrec/sessions/*.jsonl` is
   copied to `/results/trajectory.jsonl`. The final assistant message is
   extracted into `final.json`. A run manifest (exit code, duration, skill
   hashes) is written to `manifest.json`.
7. **Wipe.** `~/.openclaw`, caches, `/tmp` are deleted. `docker run --rm`
   destroys the tmpfs regardless.
8. **Orchestrator** (host) parses the results, records a `TaskResult` in
   `index.json`, and proceeds to the next task.

## Isolation guarantees (current state)

| Concern                  | Mechanism                                                                 |
|--------------------------|---------------------------------------------------------------------------|
| Filesystem leakage       | `--rm`; tmpfs-backed `$HOME`; entrypoint wipes on entry and exit          |
| Prior session memory     | No host mount of `~/.openclaw`; state lives only inside the container     |
| Credential leakage       | API key only via `-e OPENROUTER_API_KEY=` at run time; never in the image |
| Skill-set drift          | Skills vendored in-repo; SHA-256 recorded per run in `skill-manifest.json`|
| Built-in tool shadowing  | `tools.profile: "minimal"` + all `tools.web.*` disabled                   |
| Trajectory tampering     | Orchestrator parses results post-run; the container is gone by then       |

Planned hardening (not yet implemented): network allowlist restricted to
`openrouter.ai:443`, `--read-only` root filesystem, `--cap-drop=ALL`, DNS pin.

## Adding a new task

1. Create `tasks/<id>.yaml` with at minimum `id:` and `prompt:`.
2. Re-run: `trajrec --tasks tasks/ --run-id <some-id>`.

## Adding a new preset tool

The *only* callable tool path is an MCP server — `SKILL.md` is guidance, not a
registration. To add a tool:

1. Create a directory `container/skills/<tool_name>/` with an MCP stdio server
   (see `container/skills/web_search/mcp_server.py` as a template).
2. Add an entry under `mcp.servers.<tool_name>` in
   `container/config/openclaw.json.template`. The entrypoint substitutes the
   runtime path of `web_search/mcp_server.py`; add similar substitution logic in
   `container/entrypoint.sh` if your tool also needs it.
3. Add the tool's registered name (`<server>__<tool>`, with a double
   underscore) to `agents.list[0].tools.alsoAllow`.
4. Update `container/config/api-instructions.md` so the agent knows the tool
   exists.
5. Rebuild the image.

## Troubleshooting

- **`OPENROUTER_API_KEY must be set`** — source `~/.trajrec.env`.
- **`permission denied` writing to `/results`** — you started the container
  without `--user 0:0` / `HOME=/root`. The orchestrator does this for you; if
  you're running `docker run` by hand, see `CLAUDE.md`.
- **`[bundle-mcp] failed to start server "web_search"`** — the MCP server path
  in `openclaw.json` doesn't exist inside the container. Check that
  `entrypoint.sh`'s `MCP_SERVER_PATH` substitution matches where skills are
  actually copied (it tracks `$OPENCLAW_CONFIG_DIR`).
- **A `toolResult` has `"provider": "perplexity"`** — the built-in `web_search`
  leaked through. Verify `tools.profile: "minimal"` and
  `tools.web.search.enabled: false` in the rendered config.
- **`/task/task.yaml: no such file`** — your task path is outside `$HOME`
  (Colima virtiofs). Move it under `$HOME` or run with a different Docker
  backend.

## License

MIT — see `LICENSE`.
