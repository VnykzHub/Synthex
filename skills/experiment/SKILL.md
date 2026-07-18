---
name: experiment
description: "/synthex:experiment -- Full experiment lifecycle: design, run, compare, report. Launch Research Scientist with experiment-design skill, heavy-compute MCP, and Documentation Engineer."
disable-model-invocation: true
allowed-tools: Bash(sqlite3 *) Bash(echo *) Bash(find *) Bash(mkdir *) Bash(test *) Bash(python3 *)
---

# /synthex:experiment -- Full experiment lifecycle

$ARGUMENTS describes the experiment to run. May include parameters, hypotheses, or references to files in user-input/.

## Step 1 -- Resolve SYNTHEX_ROOT

```bash
SYNTHEX_ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"
export SYNTHEX_ROOT
```

## Step 2 -- Log intent

Always escape single quotes before inserting user-supplied text into SQLite. Verify DB/table exist before inserting.

```bash
SYNTHEX_ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"

# Check intents.db/tasks table exist before inserting
if [ ! -f "$SYNTHEX_ROOT/logs/intents.db" ]; then
  echo "ERROR: intents.db not found. Run synthex-init first." >&2
  exit 1
fi

# Escape single quotes for SQLite to prevent injection
ARGUMENTS_ESC="$(printf '%s' "$ARGUMENTS" | sed "s/'/''/g")"
sqlite3 "$SYNTHEX_ROOT/logs/intents.db" \
  "INSERT INTO intents (agent, action, why, context) VALUES ('research-scientist', 'experiment.start', '$ARGUMENTS_ESC', '{}');"
```

Create a task record:

```bash
SYNTHEX_ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"
TASK_ID=$(uuidgen 2>/dev/null || python3 -c "import uuid; print(uuid.uuid4().hex)")
# Escape single quotes for SQLite to prevent injection (ARGUMENTS is user-supplied)
ARGUMENTS_ESC="$(printf '%s' "$ARGUMENTS" | sed "s/'/''/g")"

# Verify tasks table exists
TABLE_OK=$(sqlite3 "$SYNTHEX_ROOT/logs/intents.db" "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='tasks';")
if [ "$TABLE_OK" -gt 0 ]; then
  sqlite3 "$SYNTHEX_ROOT/logs/intents.db" \
    "INSERT INTO tasks (id, title, priority, status, assigned_to) VALUES ('$TASK_ID', 'Experiment: $ARGUMENTS_ESC', 'high', 'in-progress', 'research-scientist');"
else
  echo "WARNING: tasks table not found in intents.db" >&2
fi
```

## Step 3 -- Phase 1: Design

Load the `experiment-design` domain skill from skills/experiment-design/SKILL.md. It provides methodology for:
- Hypothesis formulation
- Variable identification (independent, dependent, controlled)
- Statistical power analysis
- Expected outcomes and success criteria

Survey `user-input/` for relevant data or reference material:

```bash
find "$SYNTHEX_ROOT/user-input" -type f 2>/dev/null | head -30
```

Write the experiment design to `agent-output/reports/experiment-<name>/design.md`.

## Step 4 -- Phase 2: Run

Execute the experiment. Use the heavy-compute MCP for computational steps:

- `mcp__plugin_synthex_heavy-compute__sympy_solve(expression="<model>", kind="auto")` for mathematical verification
- `mcp__plugin_synthex_heavy-compute__profile_script(path="<script>", args=[])` for computational profiling
- `mcp__plugin_synthex_heavy-compute__docker_run(image="<image>", cmd=[...], mounts=[...])` for isolated execution

If the experiment involves ETL or data processing, call `etl_validate` first.

Write raw results to `agent-output/reports/experiment-<name>/results.md`.

## Step 5 -- Phase 3: Compare

Analyze results against the design criteria:
- Does the data support or refute the hypothesis?
- Are there statistically significant effects?
- What are the effect sizes?
- Are there confounding variables?

Use sympy_solve again for any post-hoc statistical calculations.

Write comparison to `agent-output/reports/experiment-<name>/comparison.md`.

## Step 6 -- Phase 4: Report

Synthesize everything into a final report. Launch the documentation-engineer (via the report skill or directly) to produce:

- `agent-output/reports/experiment-<name>/report.md`
- Optionally generate visualizations using the visualization MCP:
  - `mcp__plugin_synthex_visualization__threejs_scaffold(name="exp-<name>-chart", kind="scene")`
  - `mcp__plugin_synthex_visualization__react_component(name="exp-<name>-viz", spec="<spec>")`

## Step 7 -- Mark complete

```bash
SYNTHEX_ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"

# Update tasks record in intents.db (with table existence check)
if [ -f "$SYNTHEX_ROOT/logs/intents.db" ]; then
  TABLE_OK=$(sqlite3 "$SYNTHEX_ROOT/logs/intents.db" "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='tasks';")
  if [ "$TABLE_OK" -gt 0 ]; then
    sqlite3 "$SYNTHEX_ROOT/logs/intents.db" \
      "UPDATE tasks SET status='completed', completed_at=strftime('%Y-%m-%dT%H:%M:%fZ','now'), updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id='$TASK_ID';"
  fi
fi

# Log to state_ledger (with DB/table existence check)
if [ -f "$SYNTHEX_ROOT/logs/state_ledger.db" ]; then
  TABLE_OK=$(sqlite3 "$SYNTHEX_ROOT/logs/state_ledger.db" "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='state_ledger';")
  if [ "$TABLE_OK" -gt 0 ]; then
    sqlite3 "$SYNTHEX_ROOT/logs/state_ledger.db" \
      "INSERT INTO state_ledger (agent, event_type, details) VALUES ('research-scientist', 'experiment.complete', '{\"task_id\":\"$TASK_ID\",\"output\":\"agent-output/reports/experiment-<name>/\"}');"
  fi
fi
```

Report the results and output directory to the user.
