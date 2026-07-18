---
name: track-progress
description: /synthex:track-progress -- Displays pipeline status, phase completions, active tasks, blockers, and validation scores.
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

## Data Sources

| Section             | Source Table             | Filter                              |
|---------------------|--------------------------|-------------------------------------|
| Phase Summary       | state_ledger             | event_type LIKE 'pipeline.phase.%'  |
| Active Tasks        | intents.tasks            | status IN ('in-progress','blocked') |
| Blockers            | intents.tasks            | status = 'blocked'                  |
| Validation Scores   | state_ledger             | event_type = 'pipeline.validate'    |

## Output Format

Plain text, one line per data point. Each section header is on its own line followed by indented detail lines. Total output should be kept under 80 lines -- aggregate where counts are high rather than listing every item.
