---
name: status
description: "/synthex:status -- Query the task DB (intents.db tasks table) and render a Markdown table of current tasks."
disable-model-invocation: true
allowed-tools: Bash(sqlite3 *) Bash(echo *) Bash(test *)
---

# /synthex:status -- Display active agent tasks

## Step 1 -- Resolve SYNTHEX_ROOT

```
SYNTHEX_ROOT = $CLAUDE_PROJECT_DIR  (if set)  else $PWD
```

## Step 2 -- Verify the DB exists

```bash
test -f "$SYNTHEX_ROOT/logs/intents.db" || { echo "ERROR: intents.db not found. Run /synthex:synthex-init first."; exit 1; }
```

## Step 3 -- Query tasks

Query the tasks table for all tasks. If $ARGUMENTS includes a filter (e.g. a status value), apply it.

```bash
# All tasks
sqlite3 -header -column "$SYNTHEX_ROOT/logs/intents.db" \
  "SELECT id, title, status, assigned_to, priority, created_at FROM tasks ORDER BY created_at DESC;" 2>/dev/null \
  || echo "tasks table is empty or does not exist yet."
```

```bash
# Task count by status
sqlite3 "$SYNTHEX_ROOT/logs/intents.db" \
  "SELECT status, COUNT(*) as count FROM tasks GROUP BY status;" 2>/dev/null
```

## Step 4 -- Render Markdown table

Take the query results and format them as a Markdown table:

```markdown
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
  "SELECT ts, agent, action, why FROM intents ORDER BY ts DESC LIMIT 10;" 2>/dev/null
```

Present the rendered table to the user.
