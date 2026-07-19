---
name: add-component
description: "/synthex:add-component — Scaffold a component from a template. Use when running /synthex:add-component."
role: command
disable-model-invocation: true
related_skills: [artifact-factory, structure-validator, refine-component]
---

# add-component (command: `/synthex:add-component`)

> **Deprecated:** Merged into [artifact-factory](skills/artifact-factory/SKILL.md). Use `/synthex:artifact-factory --type component` instead.

Scaffold a new component from a template. This command creates a complete, convention-compliant component skeleton under `agent-output/src/` with source code, test suite, configuration, and documentation.

## Usage
```
/synthex:add-component <component-name> [--type <module|config|adapter|pipeline>] [--with-tests] [--overwrite]
```

## Parameters
- `component-name` (required): kebab-case name of the component, e.g., `data-validator`, `metric-collector`.
- `--type` (optional, default: `module`): The type of component to scaffold:
  - `module` — Python module with `__init__.py`, `core.py`, and test file.
  - `config` — YAML configuration file with required skeleton keys.
  - `adapter` — Integration adapter with interface definition and stub implementation.
  - `pipeline` — Multi-step pipeline with step definitions and orchestration skeleton.
- `--with-tests` (optional, default: true): Whether to generate test files alongside the source.
- `--overwrite` (optional, default: false): Overwrite existing files at the target path.

## Workflow
1. Read the naming conventions and template schemas from `knowledgebase/`.
2. Determine the output path: `agent-output/src/<component-name>/`.
3. Apply the `artifact-factory` skill to generate files from the selected type template.
4. Create the directory structure:
   ```
   agent-output/src/<component-name>/
   ├── src/
   │   ├── __init__.py
   │   └── core.py
   ├── tests/
   │   ├── __init__.py
   │   └── test_core.py
   ├── config.yaml
   └── README.md
   ```
5. If `--with-tests` is true, generate a test file with:
   - One happy-path test per public function
   - One edge-case test per parameter with non-trivial constraints
   - Import guard and test skeleton
6. Write all files.
7. Return the list of files created and the component's absolute paths.

## Validation
- `component-name` must be valid kebab-case (lowercase letters, digits, hyphens only).
- The target directory must not already exist unless `--overwrite` is set.
- Generated Python files must pass `python -c "import ast; ast.parse(...)"` syntax check.

## Error Recovery

- **Missing prerequisite:** If a required tool or dependency is unavailable, report it clearly with the exact command to install or path to check. Do not silently skip.
- **Malformed input:** Validate key fields before processing. On failure, report the exact field name and expected format. Do not proceed with partial data.
- **Timeout:** Set a 30-second budget for any blocking operation (MCP call, script execution, DB query). If exceeded, write partial results to `agent-output/partial/` and note what completed vs. what timed out.
- **Empty result:** If no data matches the query, produce a valid empty output (not an error) with a note explaining the search scope and suggesting next steps.
- **Partial failure:** If some sub-tasks succeed and others fail, report the split clearly: which succeeded, which failed, and whether the successes are usable independently.

## Output format
```
Component created: data-validator
  agent-output/src/data-validator/src/__init__.py
  agent-output/src/data-validator/src/core.py
  agent-output/src/data-validator/tests/__init__.py
  agent-output/src/data-validator/tests/test_core.py
  agent-output/src/data-validator/config.yaml
  agent-output/src/data-validator/README.md

Type: module
Tests: generated (4 test functions)
```
