---
name: pipeline
description: "/synthex:pipeline --script=<file> -- Run ETL/ML workloads in the Heavy Compute MCP. Input from user-input/datasets/, output to agent-output/artifacts/."
disable-model-invocation: true
allowed-tools: Bash(sqlite3 *) Bash(echo *) Bash(test *) Bash(find *) Bash(mkdir *) Bash(python3 *)
---

# /synthex:pipeline --script=<file> -- ETL / ML pipeline execution

$ARGUMENTS should contain `--script=<path>` pointing to the pipeline script.

## Step 1 -- Resolve SYNTHEX_ROOT and parse arguments

```
SYNTHEX_ROOT = $CLAUDE_PROJECT_DIR  (if set)  else $PWD
```

Parse $ARGUMENTS for:
- `--script=<path>` -- required, relative to SYNTHEX_ROOT or absolute
- Additional flags are passed through to the script

If --script is missing, search user-input/ for pipeline scripts:
```bash
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
DETAILS="{\"script\":\"<script-path>\",\"exit\":\"<0|non-zero>\",\"output\":\"agent-output/artifacts/...\"}"
sqlite3 "$SYNTHEX_ROOT/logs/state_ledger.db" \
  "INSERT INTO state_ledger (agent, event_type, details) VALUES ('automation-engineer', 'pipeline.run', '$DETAILS');"
```

## Step 6 -- Report

Summarize for the user: validation results, execution time, output location, and any errors or warnings.
