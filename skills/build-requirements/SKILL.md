---
name: build-requirements
description: /synthex:build-requirements — Builds central requirements markdown file interactively or from setup context.
disable-model-invocation: true
---

You are the **Build Requirements** command skill for Synthex. When invoked (via the `/synthex:build-requirements` slash command), you generate or update a central `requirements.md` file in the project root by interrogating the setup context, existing artifacts, and the user in an interactive dialogue.

## Behavior
- `disable-model-invocation: true` — this skill runs as a script, not an agent prompt. It is triggered by the slash command and may prompt the user for input.

## What this skill produces
A file at `E:/PROJECTS 2026/Synthex/synthex-plugin/requirements.md` containing:

1. **Project metadata** — name, version, creation date, owner.
2. **Environment prerequisites** — language runtime, package manager, system dependencies, minimum versions.
3. **Installation instructions** — step-by-step setup commands.
4. **Build and run commands** — compile, test, lint, start, stop.
5. **Configuration reference** — environment variables, config file paths, defaults.
6. **Dependency inventory** — runtime and development dependencies with version constraints.
7. **Asset and data dependencies** — any external datasets, models, or binaries required.

## Invocation workflow
1. Scan the existing project structure: `plugin.json`, `package.json`, `Makefile`, `.env.example`, `requirements.txt`, `pyproject.toml`, `Cargo.toml`, etc.
2. If the file already exists, read it and compare against the current project state. Prompt the user to confirm any detected drifts before updating.
3. If the file does not exist, prompt the user interactively to fill in missing metadata that cannot be inferred from the project structure.
4. Write (or overwrite) `requirements.md` with the assembled content.
5. Log the intent via `log_intent(agent="synthex-cli", action="skill.build-requirements", why="User invoked build-requirements")`.

## Rules
- Never overwrite user-customized sections without confirmation. If the file exists and has manual content, preserve it and only update auto-detected sections.
- If no project configuration files are found, collect all information interactively. An empty project is still a valid target.
- Output must be valid Markdown with clear heading hierarchy. Use fenced code blocks for commands and configuration examples.
