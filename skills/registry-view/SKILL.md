---
name: registry-view
description: /synthex:registry-view -- Displays current manifest state showing locked, in-progress, draft, and queued components. Use when the user runs /synthex:registry-view to display the current component manifest state.
disable-model-invocation: true
---

# Registry View

## Command

`/synthex:registry-view`

## Behavior

When invoked, this command reads `synthex-registry.yaml` from the project root and prints a formatted summary of all components organized by status.

## Output Sections

### Overview Header

```
Component Registry: synthex-registry.yaml
Total components: 12  (4 locked, 3 in-progress, 3 draft, 2 queued)
Last modified: 2026-07-18T16:30:00Z
```

### Status Groups

Components are grouped by status and displayed in priority order: **blocked** first (if any), then **locked**, **in-progress**, **draft**, **queued**.

Each group header is followed by indented component entries:

```
== Locked (4) ==
  comp-001  data-ingestion       v1.2.0   artifacts: 2  modified: 2026-07-18T14:30Z
  comp-002  schema-validate      v1.0.0   artifacts: 1  modified: 2026-07-18T13:15Z

== In Progress (3) ==
  comp-003  feature-extraction   v0.9.0   artifacts: 1  modified: 2026-07-18T15:45Z
  comp-004  model-training       v0.5.0   artifacts: 0  modified: 2026-07-18T16:00Z

== Draft (3) ==
  comp-005  evaluation-report    v0.1.0   artifacts: 2  modified: 2026-07-18T15:00Z

== Queued (2) ==
  comp-006  deployment-prep      --        artifacts: 0  modified: --
  comp-007  performance-bench    --        artifacts: 0  modified: --
```

### Dependency Warnings

If any component has a dependency on a component that is not in `locked` status, print a warning section:

```
! Dependency Warnings:
  comp-003  depends on comp-001 (locked)  -- OK
  comp-004  depends on comp-003 (in-progress) -- WAITING
```

### Timestamp

```
Last updated: 2026-07-18T16:30:00Z
```

## Error Handling

If `synthex-registry.yaml` does not exist, print:

```
[registry-view] no registry found at synthex-registry.yaml
```

If the file exists but is malformed YAML or fails schema validation, print the parse error and exit with a non-zero status.

## Data Source

| Field          | Source                    |
|----------------|---------------------------|
| Component list | synthex-registry.yaml     |
| Status counts  | Derived from component list |
| Modified times | Component.last_modified   |

## Error Recovery

- **Missing prerequisite:** If a required tool or dependency is unavailable, report it clearly with the exact command to install or path to check. Do not silently skip.
- **Malformed input:** Validate key fields before processing. On failure, report the exact field name and expected format. Do not proceed with partial data.
- **Timeout:** Set a 30-second budget for any blocking operation (MCP call, script execution, DB query). If exceeded, write partial results to `agent-output/partial/` and note what completed vs. what timed out.
- **Empty result:** If no data matches the query, produce a valid empty output (not an error) with a note explaining the search scope and suggesting next steps.
- **Partial failure:** If some sub-tasks succeed and others fail, report the split clearly: which succeeded, which failed, and whether the successes are usable independently.

## Output Format

Plain text with section headers on separate lines. Component entries indented with two spaces. Keep total output under 40 lines for readability.
