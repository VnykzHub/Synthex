---
name: recover
description: /synthex:recover — Resume execution from the last checkpoint. Reads logs/ for failed operations and attempts recovery. Use when the user needs to recover from a crashed or interrupted Synthex session.
role: worker
disable-model-invocation: true
---

# recover

Crash-recovery command for Synthex. Reads the state ledger and intents databases to find the last failed operation, determines which phase and task failed, and resumes the pipeline from that checkpoint.

## When to use

- A Synthex session crashed or was interrupted mid-execution
- The user sees a pipeline that stopped before completion
- A subagent returned a non-zero exit or timed out
- The user needs to know what went wrong before re-running

## Prerequisites

- `logs/state_ledger.db` must exist (SQLite database written by the state-tracking hook)
- `logs/intents.db` must exist (SQLite database written by the intents hook)
- `sqlite3` CLI must be available in `$PATH`

## Recovery playbook

### Step 1 — Check whether recovery is needed

Query the state ledger for the most recent session:

```bash
sqlite3 logs/state_ledger.db \
  "SELECT session_id, phase, task, status, updated_at
   FROM checkpoint
   WHERE session_id = (SELECT MAX(session_id) FROM checkpoint)
   ORDER BY updated_at DESC
   LIMIT 5;"
```

Interpret the results:

| `status` column | Meaning |
|---|---|
| `completed` | Last entry completed OK — no recovery needed. Exit. |
| `running` | Session was interrupted. Continue to Step 2. |
| `failed` | A task or phase failed. Continue to Step 2. |
| `pending` | The task was never started. Continue to Step 2. |

### Step 2 — Find the last failed or pending operation

```bash
sqlite3 logs/state_ledger.db \
  "SELECT session_id, phase, task, status, error, updated_at
   FROM checkpoint
   WHERE session_id = (SELECT MAX(session_id) FROM checkpoint)
     AND status IN ('failed', 'pending', 'running')
   ORDER BY updated_at DESC
   LIMIT 1;"
```

Save the returned row. The `phase` and `task` columns tell you where to resume.

If the ledger returns no rows with these statuses, the session recorded no failures. Check `logs/intents.db` for unprocessed intents:

```bash
sqlite3 logs/intents.db \
  "SELECT COUNT(*) FROM intents
   WHERE status != 'consumed'
     AND session_id = (SELECT MAX(session_id) FROM intents);"
```

If the count is > 0, the crash happened before one or more intents were dispatched. Go to Step 5.

### Step 3 — Identify the failed phase and task

Use the `phase` and `task` values from Step 2 to pinpoint what broke:

```bash
sqlite3 logs/state_ledger.db \
  "SELECT phase, task, error, retry_count, max_retries, updated_at
   FROM checkpoint
   WHERE session_id = (SELECT MAX(session_id) FROM checkpoint)
     AND phase = '<PHASE>'
     AND task = '<TASK>';"
```

Replace `<PHASE>` and `<TASK>` with the values from Step 2.

**Heuristics for root cause:**

- If `error` starts with `ToolExecutionError` or `BashExitNonZero`: the subagent or tool command failed — re-run the task (Step 6).
- If `error` contains `timeout` or `RateLimitError`: the LLM or API timed out — retry with backoff (Step 6).
- If `error` contains `PermissionDenied` or `FileNotFoundError`: check filesystem state, then re-run the pipeline from the failed phase (Step 6).
- If `error` is empty and `status = 'running'`: the process was killed mid-execution — the task may have partial output. Check `user-input/` and `agent-output/` for partial artifacts, then resume (Step 4).

### Step 4 — Resume from the checkpoint

If the task had partial output that is usable, resume without re-executing the task itself:

```bash
sqlite3 logs/state_ledger.db \
  "UPDATE checkpoint
   SET status = 'completed', updated_at = datetime('now')
   WHERE session_id = (SELECT MAX(session_id) FROM checkpoint)
     AND phase = '<PHASE>'
     AND task = '<TASK>';"
```

Then mark the next pending task as `running`:

```bash
sqlite3 logs/state_ledger.db \
  "UPDATE checkpoint
   SET status = 'running', updated_at = datetime('now')
   WHERE session_id = (SELECT MAX(session_id) FROM checkpoint)
     AND status = 'pending'
   ORDER BY updated_at ASC
   LIMIT 1;"
```

### Step 5 — Re-dispatch unprocessed intents

If Step 2 showed unconsumed intents, re-dispatch them:

```bash
sqlite3 logs/intents.db \
  "SELECT id, intent_type, payload FROM intents
   WHERE status != 'consumed'
     AND session_id = (SELECT MAX(session_id) FROM intents)
   ORDER BY created_at ASC;"
```

For each unconsumed intent:
1. Re-route `intent_type` to the appropriate agent or pipeline phase using the dispatch table in `.claude/plugins/synthex/pipeline.json`.
2. Update the intent status after dispatch:
   ```bash
   sqlite3 logs/intents.db \
     "UPDATE intents SET status = 'consumed', consumed_at = datetime('now')
      WHERE id = <INTENT_ID>;"
   ```

### Step 6 — Re-run the failed agent or pipeline

To re-run a single failed task (preserving other completed work):

```bash
# Identify the agent or skill to invoke from the phase/task mapping
# For example, if phase="data-interpretation" and task="validate-schema":
#   Run the relevant tool call or skill directly.
```

To re-run the pipeline from the failed phase onward:

```bash
# Read the active pipeline definition
cat logs/active_pipeline.json

# Re-invoke the pipeline orchestrator with the phase as the starting point
/synthex:pipeline --start-from <PHASE>
```

## Recovery decision tree

```
Is there a last session?
  ├── No → Nothing to recover. Tell the user.
  └── Yes → Check ledger status
        ├── completed → Nothing to recover. Tell the user.
        └── failed/running/pending → Check error
              ├── timeout / rate-limit → Retry with backoff (Step 6)
              ├── tool crash → Re-run the task (Step 6)
              ├── file/permission error → Fix filesystem, re-run (Step 6)
              └── empty (killed mid-execution) → Resume from checkpoint (Step 4)
```

## Error Recovery

- **Missing prerequisite:** If a required tool or dependency is unavailable, report it clearly with the exact command to install or path to check. Do not silently skip.
- **Malformed input:** Validate key fields before processing. On failure, report the exact field name and expected format. Do not proceed with partial data.
- **Timeout:** Set a 30-second budget for any blocking operation (MCP call, script execution, DB query). If exceeded, write partial results to `agent-output/partial/` and note what completed vs. what timed out.
- **Empty result:** If no data matches the query, produce a valid empty output (not an error) with a note explaining the search scope and suggesting next steps.
- **Partial failure:** If some sub-tasks succeed and others fail, report the split clearly: which succeeded, which failed, and whether the successes are usable independently.

## Output

Return a recovery report:

```json
{
  "session_id": "sx-20260719-abc123",
  "status": "recovered",
  "failed_phase": "data-interpretation",
  "failed_task": "validate-schema",
  "error": "FileNotFoundError: schemas/current.yaml",
  "actions_taken": ["re-dispatched 3 pending intents", "re-ran validate-schema"],
  "recovered_at": "2026-07-19T14:30:00Z"
}
```

If recovery is impossible (state corrupted, databases missing), report what is known and instruct the user to restart with `/synthex:init`.
