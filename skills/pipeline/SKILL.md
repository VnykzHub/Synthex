---
name: pipeline
description: "/synthex:pipeline --script=<file> -- Run ETL/ML workloads in the Heavy Compute MCP. Input from user-input/datasets/, output to agent-output/artifacts/. Use when the user runs /synthex:pipeline to execute an ETL/ML workload in the Heavy Compute sandbox."
disable-model-invocation: true
allowed-tools: Bash(sqlite3 *) Bash(echo *) Bash(test *) Bash(find *) Bash(mkdir *) Bash(python3 *)
---

> **⚠ Orchestration entry point:** this skill coordinates multiple agents and tools rather than performing a single atomic task. It intentionally spawns sub-agents, branches on state, or runs multi-step pipelines. See BUILD_PLAN.md Phase 17, Rec 3 for design rationale.

# /synthex:pipeline --script=<file> -- ETL / ML pipeline execution

$ARGUMENTS should contain `--script=<path>` pointing to the pipeline script.

## Step 1 -- Resolve SYNTHEX_ROOT and parse arguments

```bash
SYNTHEX_ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"
```

Parse $ARGUMENTS for:
- `--script=<path>` -- required, relative to SYNTHEX_ROOT or absolute
- Additional flags are passed through to the script

If --script is missing, search user-input/ for pipeline scripts:
```bash
SYNTHEX_ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"
find "$SYNTHEX_ROOT/user-input/datasets" -type f 2>/dev/null | head -20
find "$SYNTHEX_ROOT/user-input/assignments" -type f \( -name "*.py" -o -name "*.sh" -o -name "*.ipynb" \) 2>/dev/null | head -10
```

## Step 2 -- Validate with heavy-compute MCP

Before executing the full script, validate the dataset:

- `mcp__plugin_synthex_heavy-compute__etl_validate(path="<dataset-path>", expectations="")`
  - Review the returned `{rows, columns, grain_ok, issues}`

If issues are found, report them and ask the user whether to proceed.

## Step 3 -- Profile or execute the script

Option A -- Profile:
- `mcp__plugin_synthex_heavy-compute__profile_script(path="<script-path>", args=[...])`
  - Returns `{stdout, stderr, wall_time_s, top_functions}`
  - Use for understanding performance characteristics

Option B -- Docker execution (for heavy workloads):
- `mcp__plugin_synthex_heavy-compute__docker_run(image="python:3.12", cmd=["python3", "<script-path>"], mounts=["<dataset-dir>:/data"])`
  - Degrade gracefully if Docker is absent: fall back to local python3 execution

## Step 4 -- Collect outputs

Move or copy generated outputs from the script run into `agent-output/artifacts/`:

```bash
mkdir -p "$SYNTHEX_ROOT/agent-output/artifacts/pipeline-$(date +%s)"
# copy outputs here
```

## Step 5 -- Log to state_ledger

```bash
SYNTHEX_ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"

# Verify DB and table exist before inserting
if [ ! -f "$SYNTHEX_ROOT/logs/state_ledger.db" ]; then
  echo "WARNING: state_ledger.db not found. Skipping audit log." >&2
else
  TABLE_OK=$(sqlite3 "$SYNTHEX_ROOT/logs/state_ledger.db" "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='state_ledger';")
  if [ "$TABLE_OK" -eq 0 ]; then
    echo "WARNING: state_ledger table not found. Skipping audit log." >&2
  else
    DETAILS="{\"script\":\"<script-path>\",\"exit\":\"<0|non-zero>\",\"output\":\"agent-output/artifacts/...\"}"
    # Escape single quotes for SQLite to prevent injection
    DETAILS_ESC="$(printf '%s' "$DETAILS" | sed "s/'/''/g")"
    sqlite3 "$SYNTHEX_ROOT/logs/state_ledger.db" \
      "INSERT INTO state_ledger (agent, event_type, details) VALUES ('automation-engineer', 'pipeline.run', '$DETAILS_ESC');"
  fi
fi
```

## Preconditions

- **Sandbox check:** Verify `SYNTHEX_ROOT` is set and `agent-output/` exists and is writable. Use: `test -d "$SYNTHEX_ROOT/agent-output" && test -w "$SYNTHEX_ROOT/agent-output" || { echo "agent-output/ not writable"; exit 1; }`
- **MCP availability:** This skill depends on the `heavy-compute` MCP for `etl_validate`, `profile_script`, and `docker_run`. Verify with a lightweight query before proceeding. If unreachable, fall back to local python3 execution.
- **Input existence:** Check that the pipeline script exists at the specified `--script=` path or in `user-input/datasets/`. Report missing files by name and stop.
- If any precondition fails, report which one failed and stop -- do not proceed with partial preconditions.

## Error Recovery

- **Missing prerequisite:** If a required tool or dependency is unavailable, report it clearly with the exact command to install or path to check. Do not silently skip.
- **Malformed input:** Validate key fields before processing. On failure, report the exact field name and expected format. Do not proceed with partial data.
- **Timeout:** Set a 30-second budget for any blocking operation (MCP call, script execution, DB query). If exceeded, write partial results to `agent-output/partial/` and note what completed vs. what timed out.
- **Empty result:** If no data matches the query, produce a valid empty output (not an error) with a note explaining the search scope and suggesting next steps.
- **Partial failure:** If some sub-tasks succeed and others fail, report the split clearly: which succeeded, which failed, and whether the successes are usable independently.

## Step 6 -- Report

Summarize for the user: validation results, execution time, output location, and any errors or warnings.
