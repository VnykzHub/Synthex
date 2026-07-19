---
name: status
description: "/synthex:status — Query the task DB and render a Markdown table. Use when running /synthex:status."
role: worker
disable-model-invocation: true
allowed-tools: Bash(sqlite3 *) Bash(echo *) Bash(test *)
related_skills: [task-tracking, track-progress, registry-view]
---

# /synthex:status -- Display active agent tasks

> **MCP fallback**: This skill queries the task database directly via sqlite3 rather than depending on an MCP `task_list` tool. If MCP task_list is unavailable, the skill falls back to `sqlite3 "$SYNTHEX_ROOT/logs/intents.db" "SELECT * FROM tasks;"` — the same approach used throughout. No MCP dependency is required.

## Step 1 -- Resolve SYNTHEX_ROOT

```bash
SYNTHEX_ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"
export SYNTHEX_ROOT
```

## Step 2 -- Verify the DB exists

```bash
SYNTHEX_ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"
test -f "$SYNTHEX_ROOT/logs/intents.db" || { echo "ERROR: intents.db not found. Run /synthex:synthex-init first."; exit 1; }
```

## Step 3 -- Query tasks (with optional status filter)

If $ARGUMENTS includes a status value, apply it as a WHERE filter.

```bash
SYNTHEX_ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"

# Apply optional status filter from $ARGUMENTS
FILTER=""
if [ -n "$ARGUMENTS" ] && [ "$ARGUMENTS" != "" ]; then
  # Escape single quotes for SQLite
  STATUS_SAFE="$(printf '%s' "$ARGUMENTS" | sed "s/'/''/g")"
  FILTER="WHERE status='$STATUS_SAFE'"
fi

# All tasks (optionally filtered)
sqlite3 -header -column "$SYNTHEX_ROOT/logs/intents.db" \
  "SELECT id, title, status, assigned_to, priority, created_at FROM tasks $FILTER ORDER BY created_at DESC;" \
  || echo "tasks table is empty or does not exist yet."

# Task count by status
sqlite3 "$SYNTHEX_ROOT/logs/intents.db" \
  "SELECT status, COUNT(*) as count FROM tasks GROUP BY status;"
```

## Step 4 -- Render Markdown table

Take the query results and format them as a Markdown table:

```markdown

## Error Recovery

- **Missing prerequisite:** If a required tool or dependency is unavailable, report it clearly with the exact command to install or path to check. Do not silently skip.
- **Malformed input:** Validate key fields before processing. On failure, report the exact field name and expected format. Do not proceed with partial data.
- **Timeout:** Set a 30-second budget for any blocking operation (MCP call, script execution, DB query). If exceeded, write partial results to `agent-output/partial/` and note what completed vs. what timed out.
- **Empty result:** If no data matches the query, produce a valid empty output (not an error) with a note explaining the search scope and suggesting next steps.
- **Partial failure:** If some sub-tasks succeed and others fail, report the split clearly: which succeeded, which failed, and whether the successes are usable independently.

## Synthex Task Status
Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)

| ID | Title | Status | Assigned To | Priority | Created |
| :-- | :---- | :----- | :---------- | :------- | :------ |
| ... | ...   | ...    | ...         | ...      | ...     |

### Summary by Status
| Status | Count |
| :----- | :---- |
| ...    | N     |

### Recent Intents (last 10)
```

Also optionally query the intents table for recent activity:

```bash
sqlite3 -header -column "$SYNTHEX_ROOT/logs/intents.db" \
  "SELECT ts, agent, action, why FROM intents ORDER BY ts DESC LIMIT 10;"
```

Present the rendered table to the user.
