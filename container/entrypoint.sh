#!/usr/bin/env bash
# Per-run entrypoint: reset state -> render config -> install preset skills ->
# run acpx headless -> export trajectory -> wipe state.
# Container is started with `docker run --rm` so the filesystem tears down
# on exit; the wipe steps here are belt-and-braces.

set -euo pipefail

: "${OPENROUTER_API_KEY:?OPENROUTER_API_KEY must be set}"
: "${TASK_ID:?TASK_ID must be set}"
: "${RUN_ID:?RUN_ID must be set}"
: "${MODEL_ID:=openrouter/google/gemini-2.5-flash-lite-preview-09-2025}"

# MODEL_ID is of the form "<providerName>/<modelSlug>"; split it.
PROVIDER_NAME="${MODEL_ID%%/*}"      # e.g. openrouter
MODEL_SLUG="${MODEL_ID#*/}"           # e.g. google/gemini-2.5-flash-lite-preview-09-2025
if [[ "$PROVIDER_NAME" != "openrouter" ]]; then
  echo "ERROR: only openrouter provider is supported in this image (got '$PROVIDER_NAME')" >&2
  exit 2
fi

TASK_FILE="${TASK_FILE:-/task/task.yaml}"
RESULTS_DIR="${RESULTS_DIR:-/results}"
SKILL_SRC="/opt/trajrec/skills"
CONFIG_SRC="/opt/trajrec/config"
OPENCLAW_HOME="${OPENCLAW_CONFIG_DIR}"

STDOUT_LOG="$RESULTS_DIR/stdout.log"
STDERR_LOG="$RESULTS_DIR/stderr.log"
TRAJ_OUT="$RESULTS_DIR/trajectory.jsonl"
MANIFEST_OUT="$RESULTS_DIR/manifest.json"
FINAL_OUT="$RESULTS_DIR/final.json"
SKILL_MANIFEST="$RESULTS_DIR/skill-manifest.json"

mkdir -p "$RESULTS_DIR"

# 1. reset state
rm -rf "$OPENCLAW_HOME" "$HOME/.cache" "$HOME/.npm" /tmp/* 2>/dev/null || true
mkdir -p "$OPENCLAW_HOME/skills" "$OPENCLAW_HOME/workspace"

# 2. connector/oauth purge (defensive; nothing should exist on tmpfs)
rm -rf "$OPENCLAW_HOME/connectors" \
       "$OPENCLAW_HOME/oauth" \
       "$OPENCLAW_HOME/browser-profile" 2>/dev/null || true

# 3. install preset skills + api instructions
cp -r "$SKILL_SRC/." "$OPENCLAW_HOME/skills/"
install -m 0644 "$CONFIG_SRC/api-instructions.md" "$OPENCLAW_HOME/api-instructions.md"

# 4. render openclaw.json: inject MODEL_SLUG, MCP server paths, and system prompt via jq.
MCP_WEB_SEARCH_PATH="$OPENCLAW_HOME/skills/web_search/mcp_server.py"
MCP_FETCH_BOOK_EXCERPT_PATH="$OPENCLAW_HOME/skills/fetch_book_excerpt/mcp_server.py"
MCP_DOWNLOAD_FULL_TEXT_PATH="$OPENCLAW_HOME/skills/download_full_text/mcp_server.py"
MCP_PDF_TO_TEXT_PATH="$OPENCLAW_HOME/skills/pdf_to_text/mcp_server.py"
MCP_REMOVE_WATERMARK_PATH="$OPENCLAW_HOME/skills/remove_watermark/mcp_server.py"
MCP_FETCH_PAGE_PATH="$OPENCLAW_HOME/skills/fetch_page/mcp_server.py"
MCP_FETCH_BY_IDENTIFIER_PATH="$OPENCLAW_HOME/skills/fetch_by_identifier/mcp_server.py"
MCP_SUMMARIZE_SOURCE_PATH="$OPENCLAW_HOME/skills/summarize_source/mcp_server.py"
MCP_COMPACTED_GET_BOOK_TEXT_PATH="$OPENCLAW_HOME/skills/compacted_get_book_text/mcp_server.py"
jq \
  --arg model                         "$MODEL_SLUG" \
  --arg mcp_web_search                "$MCP_WEB_SEARCH_PATH" \
  --arg mcp_fetch_book_excerpt        "$MCP_FETCH_BOOK_EXCERPT_PATH" \
  --arg mcp_download_full_text        "$MCP_DOWNLOAD_FULL_TEXT_PATH" \
  --arg mcp_pdf_to_text               "$MCP_PDF_TO_TEXT_PATH" \
  --arg mcp_remove_watermark          "$MCP_REMOVE_WATERMARK_PATH" \
  --arg mcp_fetch_page                "$MCP_FETCH_PAGE_PATH" \
  --arg mcp_fetch_by_identifier       "$MCP_FETCH_BY_IDENTIFIER_PATH" \
  --arg mcp_summarize_source          "$MCP_SUMMARIZE_SOURCE_PATH" \
  --arg mcp_compacted_get_book_text   "$MCP_COMPACTED_GET_BOOK_TEXT_PATH" \
  --rawfile sysprompt "$OPENCLAW_HOME/api-instructions.md" \
  '
    .models.providers.openrouter.models[0].id = $model
    | .models.providers.openrouter.models[0].name = $model
    | .agents.list[0].model = ("openrouter/" + $model)
    | .agents.list[0].systemPromptOverride = $sysprompt
    | .mcp.servers.web_search.args                = ["-u", $mcp_web_search]
    | .mcp.servers.fetch_book_excerpt.args        = ["-u", $mcp_fetch_book_excerpt]
    | .mcp.servers.download_full_text.args        = ["-u", $mcp_download_full_text]
    | .mcp.servers.pdf_to_text.args               = ["-u", $mcp_pdf_to_text]
    | .mcp.servers.remove_watermark.args          = ["-u", $mcp_remove_watermark]
    | .mcp.servers.fetch_page.args                = ["-u", $mcp_fetch_page]
    | .mcp.servers.fetch_by_identifier.args       = ["-u", $mcp_fetch_by_identifier]
    | .mcp.servers.summarize_source.args          = ["-u", $mcp_summarize_source]
    | .mcp.servers.compacted_get_book_text.args   = ["-u", $mcp_compacted_get_book_text]
  ' \
  "$CONFIG_SRC/openclaw.json.template" > "$OPENCLAW_HOME/openclaw.json"

# 5. validate config before invoking the agent
openclaw config validate >&2

# skill manifest (SHA-256 of each skill directory tree)
OPENCLAW_CONFIG_DIR="$OPENCLAW_HOME" python3 - > "$SKILL_MANIFEST" <<'PY'
import hashlib, json, os, pathlib
root = pathlib.Path(os.environ["OPENCLAW_CONFIG_DIR"]) / "skills"
out = {}
for skill_dir in sorted(p for p in root.iterdir() if p.is_dir()):
    h = hashlib.sha256()
    for f in sorted(skill_dir.rglob("*")):
        if f.is_file():
            h.update(f.relative_to(skill_dir).as_posix().encode())
            h.update(b"\0")
            h.update(f.read_bytes())
    out[skill_dir.name] = h.hexdigest()
print(json.dumps(out, indent=2))
PY

# 6. detect chain vs single task, then run
TASK_DIR=$(dirname "$TASK_FILE")
CHAIN_FILE="$TASK_DIR/chain.yaml"

START_NS=$(date +%s%N)

if [[ -f "$CHAIN_FILE" ]]; then
  # --- chain mode: multiple steps sharing one session ---
  SESSION_ID=$(python3 -c "import uuid; print(str(uuid.uuid4()))")

  # Extract ordered list of step file paths from chain.yaml
  STEP_FILES=$(CHAIN_FILE="$CHAIN_FILE" TASK_DIR="$TASK_DIR" python3 - <<'PY'
import os, yaml
with open(os.environ["CHAIN_FILE"]) as f:
    chain = yaml.safe_load(f)
task_dir = os.environ["TASK_DIR"]
steps = sorted(chain["steps"], key=lambda s: s["index"])
for s in steps:
    print(os.path.join(task_dir, s["file"]))
PY
)

  EXIT_CODE=0
  set +e
  while IFS= read -r STEP_FILE; do
    STEP_PROMPT=$(python3 - <<PY
import sys, yaml
with open("$STEP_FILE") as f:
    d = yaml.safe_load(f)
sys.stdout.write(d["prompt"])
PY
)
    openclaw agent \
      --local \
      --agent trajrec \
      --session-id "$SESSION_ID" \
      --message "$STEP_PROMPT" \
      --timeout "${AGENT_TIMEOUT_S:-600}" \
      --json \
      >> "$STDOUT_LOG" 2>> "$STDERR_LOG"
    STEP_EXIT=$?
    if [[ $STEP_EXIT -ne 0 ]]; then
      EXIT_CODE=$STEP_EXIT
      break
    fi
  done <<< "$STEP_FILES"
  set -e

else
  # --- single-task mode ---
  PROMPT=$(TASK_FILE="$TASK_FILE" python3 - <<'PY'
import os, sys, yaml
with open(os.environ["TASK_FILE"]) as f:
    d = yaml.safe_load(f)
sys.stdout.write(d["prompt"])
PY
)

  # 7. run openclaw agent --local (single-process, no gateway; reads the
  #    provider api key from $OPENROUTER_API_KEY via the config's env ref).
  #    --json prints a structured result payload to stdout; the per-session
  #    jsonl trajectory is emitted to ~/.openclaw/agents/<agent>/sessions/.
  set +e
  openclaw agent \
    --local \
    --agent   trajrec \
    --message "$PROMPT" \
    --timeout "${AGENT_TIMEOUT_S:-600}" \
    --json \
    > "$STDOUT_LOG" 2> "$STDERR_LOG"
  EXIT_CODE=$?
  set -e
fi

END_NS=$(date +%s%N)

# 8. export trajectory: prefer native per-agent session JSONL; fall back to stdout
LATEST_SESSION=$(ls -1t "$OPENCLAW_HOME"/agents/trajrec/sessions/*.jsonl 2>/dev/null | head -n1 || true)
if [[ -n "$LATEST_SESSION" ]]; then
  cp "$LATEST_SESSION" "$TRAJ_OUT"
else
  # fall back to stdout (e.g. agent failed before any session was written)
  cp "$STDOUT_LOG" "$TRAJ_OUT"
fi

# final assistant message
TRAJ_OUT="$TRAJ_OUT" EXIT_CODE="$EXIT_CODE" python3 - > "$FINAL_OUT" <<'PY'
import json, os, pathlib
p = pathlib.Path(os.environ["TRAJ_OUT"])
final = None
if p.exists():
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        msg = obj.get("message") or {}
        if msg.get("role") == "assistant":
            final = obj
print(json.dumps({
    "exit_code": int(os.environ["EXIT_CODE"]),
    "final_message": final,
}, indent=2))
PY

# manifest
RUN_ID="$RUN_ID" TASK_ID="$TASK_ID" MODEL_ID="$MODEL_ID" \
EXIT_CODE="$EXIT_CODE" DURATION_NS="$((END_NS - START_NS))" \
SKILL_MANIFEST="$SKILL_MANIFEST" \
python3 - > "$MANIFEST_OUT" <<'PY'
import json, os
print(json.dumps({
    "run_id":    os.environ["RUN_ID"],
    "task_id":   os.environ["TASK_ID"],
    "model_id":  os.environ["MODEL_ID"],
    "exit_code": int(os.environ["EXIT_CODE"]),
    "duration_ns": int(os.environ["DURATION_NS"]),
    "skill_manifest": json.load(open(os.environ["SKILL_MANIFEST"])),
}, indent=2))
PY

# 9. post-run wipe (tmpfs will die anyway)
rm -rf "$OPENCLAW_HOME" "$HOME/.cache" /tmp/* 2>/dev/null || true

exit "$EXIT_CODE"