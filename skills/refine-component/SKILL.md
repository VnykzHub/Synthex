---
name: refine-component
description: /synthex:refine-component — Refine an existing component by applying structural fixes, naming corrections, and convention alignment. Non-destructive by default — uses patch files. Use when the user runs /synthex:refine-component to apply structural fixes to a locked component.
disable-model-invocation: true
---

# refine-component (command: `/synthex:refine-component`)

Refine an existing component by applying structural fixes, naming corrections, and convention alignment. This command is non-destructive by default — it creates a patch file describing the suggested changes and optionally applies them.

## Usage
```
/synthex:refine-component <component-path> [--fix] [--dry-run] [--checks structure,naming,quality,completeness]
```

## Parameters
- `component-path` (required): Path to the component directory or file under `agent-output/src/`.
- `--fix` (optional, default: false): Apply the suggested fixes in-place. Without this flag, only a report is generated.
- `--dry-run` (optional, default: true if `--fix` is not set, false if `--fix` is set): Show what would be changed without making changes.
- `--checks` (optional, default: `structure,naming,quality,completeness`): Comma-separated list of check categories to run.

## Workflow
1. Read the component files from the specified path.
2. Read the project conventions and schemas from `knowledgebase/`.
3. For each enabled check category:
   - **structure**: Validate directory tree, required files, `__init__.py` presence.
   - **naming**: Check file names, class names, function names, and variable names against conventions.
   - **quality**: Check docstrings, type hints, line length, dead code.
   - **completeness**: Check for missing test coverage, missing README, missing config.
4. Collect all findings into a structured list.
5. For each finding, generate a suggested fix.
6. If `--fix` is set, apply fixes to the files. If `--dry-run` is set (or `--fix` is not set), write a patch report instead.
7. Write the patch report to `agent-output/reports/refinements/<component-name>-refinement.md`.
8. Return the summary.

## Validations
- The component path must exist under `agent-output/src/`.
- Fixes are applied as surgical edits (targeted changes, not full file rewrites) to minimize disruption.
- If a fix would change a public API signature, the command warns and asks for confirmation (simulated — logged as a finding requiring manual review).

## Output format (dry-run)
```
Refinement analysis: data-validator
  Checks run: structure, naming, quality, completeness
  Findings: 3

  1. [naming] File "MyHelper.py" should be "my_helper.py" (snake_case)
     Suggested fix: Rename file to my_helper.py and update imports.

  2. [quality] Function "validate" is missing docstring
     Suggested fix: Add docstring describing parameters, return type, and exceptions.

  3. [completeness] Missing test for src/validator.py
     Suggested fix: Create tests/test_validator.py with test coverage.

  Auto-fixable: 2 of 3
  Apply with: /synthex:refine-component data-validator --fix
```

## Output format (with --fix)
```
Refinement applied: data-validator
  Fixes applied: 2 of 3
  - Renamed MyHelper.py -> my_helper.py (updated 2 imports)
  - Added docstring to validate() function
  Skipped (requires manual review):
  - Missing test file for src/validator.py
```
