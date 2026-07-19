---
name: add-component
description: /synthex:add-component — Scaffold a new component from a template. Adds a new code module, configuration, and test files under agent-output/src/ following project conventions. Use when the user runs /synthex:add-component to scaffold a new component from a template.
disable-model-invocation: true
---

# add-component (command: `/synthex:add-component`)

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
