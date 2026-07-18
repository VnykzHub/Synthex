---
name: preflight
description: /synthex:preflight — Read-only dry-run validation that reports what's ready and what's missing before pipeline execution.
disable-model-invocation: true
---

# Preflight Skill

Command skill: `/synthex:preflight`

## Purpose

Read-only dry-run validation that inspects the current project state and reports what is ready, what is missing, and what needs attention before pipeline execution. This skill never modifies any files or spawns any agents — it only reads and reports.

## When to use

- User types `/synthex:preflight` to check project readiness before launching the pipeline.
- User types `/synthex:preflight --project "<project-name>"` to target a specific project.
- User types `/synthex:preflight --all` to check all projects.
- Before running `/synthex:launch-pipeline` to verify everything is in order.

## Workflow

1. **Resolve target.**
   - If `--project` flag is provided, target that specific project.
   - If `--all` flag is provided, target all projects under `agent-output/pipeline/`.
   - If no flag is provided, list all projects and let the user select, or run on the most recently modified project.

2. **Read pipeline state (read-only).**
   - Open `agent-output/pipeline/<project>/pipeline-state.yaml` for reading.
   - Do not modify the file. Do not write any files.
   - Parse the current phase, task list, and blocker list.

3. **Validate assignment.**
   - Check that `user-input/assignments/<project-name>.md` exists and is non-empty.
   - Check that the assignment has a clear goal statement and definition of done.
   - If the assignment is missing or empty, flag it as a critical issue.

4. **Validate pipeline state.**
   - Check that `pipeline-state.yaml` is valid YAML and contains all required fields.
   - Report the current phase and overall status.
   - Flag any tasks that are stuck in `blocked` or `in-progress` beyond their thresholds.

5. **Validate sandbox structure.**
   - Check that the following directories exist:
     - `user-input/assignments/`
     - `agent-output/pipeline/`
     - `agent-output/artifacts/`
     - `agent-output/src/`
     - `agent-output/reports/`
   - Report any missing directories as warnings (they will be created during pipeline execution if needed).

6. **Validate Memory Vault connectivity (optional).**
   - Attempt to call `mcp__plugin_synthex_memory-graph__task_list` as a connectivity check.
   - If successful, report Memory Vault as available.
   - If unsuccessful, report it as unavailable with a note that pipeline execution will still proceed.

7. **Generate report.**
   - Compile all findings into a structured preflight report.
   - Print the report to the user in a clear, readable format.
   - Do not save the report to disk — it is informational output only.

## Preflight report format

```
=== PREFLIGHT REPORT: <project-name> ===
Timestamp: <UTC ISO-8601>

OVERALL STATUS: PASS | PASS_WITH_WARNINGS | FAIL

--- Assignment ---
  Path: user-input/assignments/<project-name>.md
  Exists: YES | NO
  Has goal: YES | NO
  Has definition of done: YES | NO
  Status: [OK] | [MISSING] | [INCOMPLETE]

--- Pipeline State ---
  Path: agent-output/pipeline/pipeline-state.yaml
  Valid YAML: YES | NO
  Current phase: <phase>
  Phase status: <status>
  Total tasks: <count>
  Blocked tasks: <count>
  Stuck tasks: <count>

--- Sandbox Structure ---
  user-input/assignments/     [EXISTS] | [MISSING]
  agent-output/pipeline/      [EXISTS] | [MISSING]
  agent-output/artifacts/     [EXISTS] | [MISSING]
  agent-output/src/           [EXISTS] | [MISSING]
  agent-output/reports/       [EXISTS] | [MISSING]

--- Memory Vault ---
  MCP tools reachable: YES | NO
  Note: <vault availability note>

--- Issues Found ---
  <list of issues, one per line, empty if none>

=== RECOMMENDATION ===
  Ready for pipeline launch: YES | NO
  Suggested action: <description>
```

## Error handling

- If no projects exist under `agent-output/pipeline/`, the report indicates no projects found and suggests running `/synthex:init-project`.
- If `pipeline-state.yaml` cannot be parsed, the report flags it as a critical issue with the parse error details.
- If the specified project does not exist, return a detailed error listing available projects.
- This skill does not throw errors on missing data — it reports findings. Every condition is reported as PASS, WARNING, or FAIL in the report.

## Rules

- This skill is strictly read-only. It never creates, modifies, or deletes any files.
- The `disable-model-invocation: true` flag means this skill runs as a command — validation logic is executed directly without LLM generation.
- Reports are printed to stdout and not persisted to disk.
- The skill returns a zero exit code regardless of findings — the report content communicates readiness, not the exit code.
