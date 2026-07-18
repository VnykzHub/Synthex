---
name: registry-manager
description: Defines patterns for reading, updating, and diffing the component registry to support incremental pipeline runs. Use when tracking component state across pipeline phases.
---

# Registry Manager

## Registry Schema

The component registry is stored as a YAML file at the project root named `synthex-registry.yaml`. Its top-level structure is a `components` list, where each entry describes one pipeline component:

```yaml
components:
  - id: "comp-001"
    name: "data-ingestion"
    status: "locked"        # see Component States below
    version: "1.2.0"
    dependencies:
      - "comp-000"
    last_modified: "2026-07-18T14:30:00Z"
    artifacts:
      - path: "agent-output/data-ingestion/results.json"
        hash: "sha256:a1b2c3d4..."
        size_bytes: 24576
      - path: "agent-output/data-ingestion/summary.md"
        hash: "sha256:e5f6g7h8..."
        size_bytes: 4096

  - id: "comp-002"
    name: "feature-extraction"
    status: "in-progress"
    version: "0.9.0"
    dependencies:
      - "comp-001"
    last_modified: "2026-07-18T15:45:00Z"
    artifacts:
      - path: "agent-output/feature-extraction/features.parquet"
        hash: "sha256:i9j0k1l2..."
        size_bytes: 1048576
```

## Operations

### Read

Load the full registry into memory. Validate structural integrity: every `id` referenced in `dependencies` must exist as a component entry. If validation fails, report the missing dependency IDs and abort.

```yaml
# Usage context: at the beginning of any pipeline phase that needs to know
# which components are available and which need processing.
result: registry (parsed dict) | error
```

### Update

Atomically update one or more component fields. Supported field-level updates:

- `status` -- transition to a new component state (must follow valid transitions, see below)
- `version` -- bump to a new semantic version string
- `last_modified` -- auto-set to current UTC ISO-8601 timestamp if omitted
- `artifacts` -- replace the artifact list entirely (pass the full list, not a diff)

Valid status transitions:

```
locked    --> in-progress  (start work)
in-progress --> draft      (output ready for review)
draft     --> locked       (reviewed and finalized)
draft     --> queued       (rolled back for retry)
queued    --> in-progress  (re-attempt)
locked    --> draft        (hotfix / revision)
```

Any other transition produces a validation error.

### Diff

Compare two registry snapshots (e.g., before and after a pipeline phase) and return a structured diff:

```yaml
diff:
  added: []
  removed: []
  changed:
    - id: "comp-001"
      fields:
        status: { from: "in-progress", to: "draft" }
        version: { from: "1.1.0", to: "1.2.0" }
```

Useful for generating pipeline phase summaries and detecting unexpected modifications.

### Lock

Acquire a pessimistic lock on the registry file to prevent concurrent modifications. The lock file is `synthex-registry.lock` written alongside the registry YAML. It contains the PID and a timestamp:

```yaml
lock:
  pid: 14235
  acquired_at: "2026-07-18T16:00:00Z"
  acquired_by: "environment-builder"
```

Lock acquisition blocks for up to 30 seconds, then times out with an error. The lock is released automatically on graceful exit or explicitly via the `unlock` operation.

## Component States

| State         | Meaning                                                  |
|---------------|----------------------------------------------------------|
| `locked`      | Output is finalized and approved; no further changes.    |
| `in-progress` | An agent is actively working on this component.          |
| `draft`       | Output exists but has not been reviewed or approved.     |
| `queued`      | Ready to be picked up but not yet assigned.              |

## Pipeline Integration

The registry manager is invoked at the start and end of each pipeline phase by the PipelineDirector agent. At phase start it reads the registry and identifies queued/draft components whose dependencies are all `locked`. At phase end it updates the registry with new status values and artifact references, then writes a diff to the pipeline log.
