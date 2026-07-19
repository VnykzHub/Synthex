---
name: init-project
description: /synthex:init-project "<name>" — Scaffolds complete project structure, runs interactive setup, and launches the pipeline via EnvironmentBuilder -> PipelineDirector. Use when the user runs /synthex:init-project to scaffold a complete project and launch the pipeline.
disable-model-invocation: true
---

> **⚠ Orchestration entry point:** this skill coordinates multiple agents and tools rather than performing a single atomic task. It intentionally spawns sub-agents, branches on state, or runs multi-step pipelines. See BUILD_PLAN.md Phase 17, Rec 3 for design rationale.

# Init Project Skill

Command skill: `/synthex:init-project "<name>"`

## Purpose

Scaffolds a complete Synthex project from scratch. This is the entry point for new projects — it creates the sandbox directory structure, initializes the Memory Vault connection, sets up the task list, and hands off to the Pipeline Director for execution.

## When to use

- User types `/synthex:init-project "<project-name>"`
- User types `/synthex:init-project "<project-name>" --description "<description>"`
- A new assignment needs to be bootstrapped with the full Synthex pipeline structure

## Workflow

1. **Parse arguments.** Extract the project name from the command. If `--description` is provided, capture the description as well. Validate that the project name is non-empty and contains only alphanumeric characters, hyphens, and underscores.

2. **Check preconditions.**
   - Verify that `user-input/assignments/` directory exists. If not, create it.
   - Verify that the `SYNTHEX_ROOT` environment variable or project root is resolvable.
   - Verify no existing project with the same name exists under `agent-output/pipeline/`.

3. **Scaffold project structure.**
   - Create the assignment document at `user-input/assignments/<project-name>.md` using the provided description or a template prompt.
   - Create `agent-output/pipeline/` directory if it does not exist.
   - Create the initial `pipeline-state.yaml` with `current_phase: research` and empty task/blocker lists.
   - Create empty directories: `agent-output/artifacts/`, `agent-output/src/`, `agent-output/reports/`.

4. **Run interactive setup (if applicable).**
   - Prompt the user for additional context if `--description` was not provided:
     - "What is the goal of this project?"
     - "What are the key constraints (time, resources, scope)?"
     - "What is the definition of done?"
   - Write the collected context into `user-input/assignments/<project-name>.md`.

5. **Initialize Memory Vault connection.**
   - Call `mcp__plugin_synthex_memory-graph__log_intent` to record project creation.
   - Call `mcp__plugin_synthex_memory-graph__task_create` to create the initial pipeline oversight task.

6. **Launch pipeline.**
   - Hand off to the Pipeline Director agent with the project name and assignment path.
   - The Pipeline Director picks up from the Research phase and begins execution.

## Output

The following files are created:

```
user-input/assignments/<project-name>.md      — The assignment document
agent-output/pipeline/pipeline-state.yaml     — Initial pipeline state (phase: research)
agent-output/artifacts/                       — Artifacts directory (empty)
agent-output/src/                             — Source directory (empty)
agent-output/reports/                         — Reports directory (empty)
```

## Error handling

- If the project name is invalid (contains special characters or is empty), return an error message and do not scaffold.
- If a project with the same name already exists, return an error with the existing project path. Do not overwrite.
- If the sandbox root cannot be resolved, return an error directing the user to set `SYNTHEX_ROOT` or run from the correct directory.
- If the Memory Vault MCP tools are unavailable, scaffold the structure anyway, log a warning, and proceed without vault integration.

## Rules

- This skill creates new files and directories. It does not modify existing projects.
- The `disable-model-invocation: true` flag means this skill runs as a command — it does not invoke the LLM for generation. The scaffolding logic is executed directly.
- After scaffolding, always hand off to the Pipeline Director. Do not attempt to run phases yourself.
