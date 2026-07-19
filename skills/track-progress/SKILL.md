---
name: track-progress
description: /synthex:track-progress -- Displays pipeline status, phase completions, active tasks, blockers, and validation scores. Use when the user runs /synthex:track-progress to display pipeline status, phase completions, and blockers.
disable-model-invocation: true
---

# Track Progress

## Command

`/synthex:track-progress`

## Behavior

When invoked, this command reads the current pipeline state from the shared SQLite databases (`logs/intents.db` and `logs/state_ledger.db`) and prints a structured overview to stdout.

## Output Sections

### Pipeline Phase Summary

Reads `state_ledger` events filtered by `event_type LIKE 'pipeline.phase.%'` and summarizes:

```
Pipeline: <project_name>
Phases:   3/5 complete
Phase 1: data-ingestion      -- COMPLETE   (2 artifacts, 0 errors)
Phase 2: feature-extraction  -- IN PROGRESS (3 tasks, 1 in-progress)
Phase 3: model-training      -- PENDING
```

### Active Tasks

Queries the `tasks` table for rows where `status IN ('in-progress', 'blocked', 'review')`:

```
Active Tasks:
  T-001  data-ingestion/validate    in-progress  assigned: data-engineer
  T-002  feature-extraction/normal  blocked      blocked-by: T-001
```

### Blockers

Lists all tasks with `status='blocked'`, including the blocking task ID and how long the block has been in place:

```
Blockers:
  T-002  feature-extraction/normal  blocked by T-001 (since 2026-07-18T14:00:00Z)
```

### Validation Scores

If the `state_ledger` contains `pipeline.validate` events with score details, extract and display:

```
Validation:
  data-ingestion:     PASS  (score 92/100, 0 warnings)
  feature-extraction: FAIL  (score 45/100, 3 warnings)
    - Missing required column 'timestamp'
    - Null rate exceeds threshold (12% > 5%)
```

### Timestamp

The output ends with a refresh timestamp:

```
Last updated: 2026-07-18T16:30:00Z
```

## Query Mechanism

Data is read from the SQLite databases using two mechanisms, attempted in order:

**Primary** -- MCP tool `mcp__plugin_synthex_memory-graph__task_list`:
Returns structured task data directly (id, title, status, assigned_to, created_at). Use this when the MCP server is available.

**Fallback** -- Direct `sqlite3` CLI queries:
```bash
sqlite3 -header -column "$SYNTHEX_ROOT/logs/intents.db" \
  "SELECT id, title, status, assigned_to, created_at
   FROM tasks
   ORDER BY created_at DESC;"
```

Column separators are enabled via `-column` and `-header` flags so the output renders as a table.

For `state_ledger` queries:
```bash
sqlite3 -header -column "$SYNTHEX_ROOT/logs/state_ledger.db" \
  "SELECT event_type, details, timestamp
   FROM state_ledger
   WHERE event_type LIKE 'pipeline.phase.%'
   ORDER BY timestamp DESC;"
```

## Error Recovery

- **Missing prerequisite:** If a required tool or dependency is unavailable, report it clearly with the exact command to install or path to check. Do not silently skip.
- **Malformed input:** Validate key fields before processing. On failure, report the exact field name and expected format. Do not proceed with partial data.
- **Timeout:** Set a 30-second budget for any blocking operation (MCP call, script execution, DB query). If exceeded, write partial results to `agent-output/partial/` and note what completed vs. what timed out.
- **Empty result:** If no data matches the query, produce a valid empty output (not an error) with a note explaining the search scope and suggesting next steps.
- **Partial failure:** If some sub-tasks succeed and others fail, report the split clearly: which succeeded, which failed, and whether the successes are usable independently.

## Data Sources

Plain text, one line per data point. Each section header is on its own line followed by indented detail lines. Total output should be kept under 80 lines -- aggregate where counts are high rather than listing every item.
