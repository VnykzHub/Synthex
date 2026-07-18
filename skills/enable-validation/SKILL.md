---
name: enable-validation
description: /synthex:enable-validation — Enable validation scripts for a component or the entire pipeline. Generates or links CI-ready validation scripts under agent-output/scripts/.
disable-model-invocation: true
---

# enable-validation (command: `/synthex:enable-validation`)

Enable validation scripts for a component or the entire pipeline. This command generates or links CI-ready validation scripts under `agent-output/scripts/` that enforce structural, naming, and completeness rules on the specified target.

## Usage
```
/synthex:enable-validation [--target <component-path|all>] [--scripts structure,naming,completeness] [--ci <github-actions|generic>]
```

## Parameters
- `--target` (optional, default: `all`): The component or scope to enable validation for.
  - A specific component path under `agent-output/src/<component>`.
  - `all` — enables validation for the entire `agent-output/` tree.
- `--scripts` (optional, default: `structure,naming,completeness`): Comma-separated list of validation script types to generate.
  - `structure` — validates directory tree and required files.
  - `naming` — validates naming conventions for all files.
  - `completeness` — validates that all required content is present.
  - `crossref` — validates cross-references between artifacts.
- `--ci` (optional, default: `generic`): Generate CI integration configuration.
  - `github-actions` — generates a `.github/workflows/validate.yml` workflow file.
  - `generic` — generates a shell script that can be run locally or in any CI.

## Workflow
1. Determine the validation scope from `--target`.
2. Read the project conventions and existing schematic files from `knowledgebase/`.
3. For each requested script type:
   a. Invoke the `structure-validator` skill to generate validation logic patterns.
   b. Write a standalone Python script to `agent-output/scripts/validate/`:
      - `validate_structure.py` for directory tree and file existence.
      - `validate_naming.py` for naming conventions.
      - `validate_completeness.py` for content completeness.
      - `validate_crossref.py` for cross-reference integrity.
   c. Each script accepts the target path as a command-line argument and outputs PASS/FAIL with details.
4. If `--ci github-actions` is set, generate `.github/workflows/validate.yml` that runs the selected scripts on push and pull request.
5. If `--ci generic` is set, generate `agent-output/scripts/run-validation.sh` that runs all enabled scripts and aggregates results.
6. Return the list of scripts created and their status.

## Validation
- Scripts are generated only if they do not already exist (no overwrite unless forced).
- Each generated script must be runnable with `python <script>.py <target>`.
- The CI workflow file references the correct script paths relative to the repository root.

## Output format
```
Validation enabled for target: all
  Scripts generated:
    agent-output/scripts/validate/validate_structure.py
    agent-output/scripts/validate/validate_naming.py
    agent-output/scripts/validate/validate_completeness.py

  CI configuration:
    agent-output/scripts/run-validation.sh (generic)

  To run: python agent-output/scripts/validate/validate_structure.py agent-output/src/
```
