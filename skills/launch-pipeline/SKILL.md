---
name: launch-pipeline
description: /synthex:launch-pipeline — Main entry point that checks readiness, gathers missing context, and hands off to the PipelineDirector for execution. Use when the user runs /synthex:launch-pipeline to execute the full 5-phase project pipeline.
disable-model-invocation: true
---

> **⚠ Orchestration entry point:** this skill coordinates multiple agents and tools rather than performing a single atomic task. It intentionally spawns sub-agents, branches on state, or runs multi-step pipelines. See BUILD_PLAN.md Phase 17, Rec 3 for design rationale.

# Launch Pipeline Skill

Command skill: `/synthex:launch-pipeline`

## Purpose

Main entry point for executing the Synthex pipeline on an existing project. This skill checks that the project is properly scaffolded, validates that all prerequisite data is present, gathers any missing context interactively, and hands off to the Pipeline Director for phase-by-phase execution.

## When to use

- User types `/synthex:launch-pipeline` to start execution on an existing project.
- User types `/synthex:launch-pipeline --project "<project-name>"` to target a specific project.
- A project exists under `agent-output/pipeline/` and is ready to begin or resume execution.

## Workflow

1. **Resolve project.**
   - If `--project` flag is provided, use the specified project name. Look for `agent-output/pipeline/<project-name>/pipeline-state.yaml`.
   - If no flag is provided, list all projects in `agent-output/pipeline/` and prompt the user to select one.
   - If no projects exist, inform the user and suggest running `/synthex:init-project` first.

2. **Check readiness.**
   - Verify the assignment file exists at `user-input/assignments/<project-name>.md`.
   - Verify `pipeline-state.yaml` exists and is parseable.
   - Check the current `current_phase` and `phase_status` to determine where to start or resume.
   - Verify that the Memory Vault MCP tools are reachable (optional check — warn if unavailable but do not block).

3. **Gather missing context (if any).**
   - If `pipeline-state.yaml` has incomplete fields (missing project description, no acceptance criteria, empty task list), prompt the user for the missing information:
     - "What is the goal of this project?"
     - "What are the constraints and requirements?"
     - "What is the definition of done?"
   - Update `pipeline-state.yaml` with the gathered context.
   - Update `user-input/assignments/<project-name>.md` with any new context.

4. **Log launch intent.**
   - Call `mcp__plugin_synthex_memory-graph__log_intent` to record the pipeline launch event.
   - Include: project name, start or resume phase, timestamp.

5. **Hand off to Pipeline Director.**
   - Spawn the `pipeline-director` agent with the project name, assignment path, and current `pipeline-state.yaml`.
   - The Pipeline Director takes over phase execution from the current phase.
   - If `current_phase` is `pending` or unset, start from the Research phase.

## Readiness checklist

Before handoff, the following must be true:

| Check | Required | Description |
|-------|----------|-------------|
| Assignment exists | Yes | `user-input/assignments/<project-name>.md` must exist |
| Pipeline state exists | Yes | `agent-output/pipeline/pipeline-state.yaml` must exist and be valid YAML |
| Project name is set | Yes | Project name in state must match the resolved project |
| Memory Vault available | No | Warn if unavailable, proceed without |
| Tasks defined | No | If empty, Pipeline Director generates them via phase-templates |

## Output on completion

The skill prints a summary to the user:

```
Pipeline launched for project "<project-name>"
  Starting phase: <research | planning | implementation | review | validation>
  Assignment: user-input/assignments/<project-name>.md
  Pipeline state: agent-output/pipeline/pipeline-state.yaml
  Handing off to Pipeline Director...
```

## Error handling

- If no projects exist under `agent-output/pipeline/`, return an error with a suggestion to run `/synthex:init-project`.
- If the specified project name does not exist, return an error listing available projects.
- If `pipeline-state.yaml` is corrupt or unparseable, return an error and suggest running `/synthex:init-project` again or manually fixing the file.
- If Memory Vault tools are unreachable, log a warning and proceed — vault integration is optional for pipeline execution.

## Rules

- This skill does not execute phases directly. Its sole responsibility is readiness checking and handoff to the Pipeline Director.
- The `disable-model-invocation: true` flag means this skill runs as a command — it performs file checks and spawning logic directly without LLM generation.
- If the project is already in mid-execution (current_phase is not `pending`), resume from where it left off rather than restarting.
