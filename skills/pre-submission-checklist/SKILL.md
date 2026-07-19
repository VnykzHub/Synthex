---
name: pre-submission-checklist
description: Mandatory 4-step quality gate for all deliverables. Invoked by component-builder before writing any output to agent-output/src/. Every step must pass before the artifact can proceed. Use when an agent needs to run the mandatory 4-step pre-submission gate before artifact delivery.
---

# pre-submission-checklist

> **Deprecated:** Merged into [artifact-factory](skills/artifact-factory/SKILL.md). Use `/synthex:artifact-factory --validate` instead.

Mandatory 4-step quality gate for all deliverables. This is the **final gate** before any artifact is written to `agent-output/src/`. Every step must pass. If any step fails, the artifact is blocked and the caller must fix the issue before re-invoking this skill.

## When to use
- Immediately before writing any generated code, configuration, or artifact to `agent-output/`
- When a component builder or any other agent believes their output is ready for delivery
- After resolving issues flagged during a previous checklist run

## Core principles

1. **Gate, not a linter.** The checklist is a pass/fail gate, not a style guide. A pass means the artifact is ready for its intended consumer. A fail means it must not be delivered.
2. **All-or-nothing.** Every step must pass. If even one step fails, the result is FAIL and the artifact is blocked.
3. **Self-contained.** Each step must be verifiable by reading the artifact alone, without external context. If the artifact cannot be understood without external docs, that is itself a failure of step 3 (quality).
4. **Repeatable.** Running the checklist twice on the same artifact must produce the same result.
5. **Verifiable in isolation.** Each step uses only the tools available to the caller (Read, Grep, Glob, etc.) — no external services required.

## Four mandatory steps

### Step 1: Requirements alignment
**Goal:** Confirm that every stated requirement from the source plan is addressed in the artifact.
**Checks:**
- [ ] The artifact's purpose is explicitly stated near the top of the file.
- [ ] Every requirement listed in the source plan has a corresponding implementation or explanation in the artifact.
- [ ] No requirements are contradicted or ignored (if intentionally skipped, a comment explains why).
- [ ] Acceptance criteria from the plan can be verified against the artifact.

**Pass condition:** All checks pass. If any requirement is unmet, return FAIL and list all unmet requirements.

### Step 2: Format compliance
**Goal:** Confirm the artifact follows the structural and formatting conventions for its type.
**Checks:**
- [ ] The file extension matches the content type (`.py` for Python, `.md` for Markdown, `.yaml` for YAML).
- [ ] For YAML: valid YAML syntax (verify with `python -c "import yaml; yaml.safe_load(open(path))"`).
- [ ] For Markdown: valid structure, no broken heading hierarchy (no H3 before H2).
- [ ] For Python: valid syntax (verify with `python -c "import ast; ast.parse(open(path).read())"`).
- [ ] Naming convention matches project standards (snake_case for files, PascalCase for classes).
- [ ] No trailing whitespace, consistent indentation (2-space YAML, 4-space Python).

**Pass condition:** All checks pass. Return FAIL with a list of format violations.

### Step 3: Quality baseline
**Goal:** Confirm the artifact meets minimum quality standards.
**Checks:**
- [ ] All public functions have docstrings (Python) or equivalent documentation (Markdown/YAML).
- [ ] All function signatures have type hints (Python).
- [ ] No dead code, commented-out blocks, or TODO/FIXME without an owner.
- [ ] Lines are reasonably short (under 100 chars for code, under 120 for Markdown).
- [ ] Imports are at the top of the file and sorted (standard library, third-party, local).
- [ ] No debug print statements or logging calls that would spam production output.

**Pass condition:** All checks pass. Return FAIL with a list of quality issues.

### Step 4: Completeness gate
**Goal:** Confirm the artifact delivery is complete — the right files exist in the right places.
**Checks:**
- [ ] The primary artifact file exists at the expected path.
- [ ] If the artifact is a Python module, `__init__.py` exists.
- [ ] If the artifact is a Python module, a corresponding `tests/test_<module>.py` exists.
- [ ] If the artifact has dependencies, `requirements.txt` or `pyproject.toml` exists and lists them.
- [ ] A `README.md` exists if the module is at the top level of `agent-output/src/`.
- [ ] The artifact is non-empty (file size > 0 bytes).

**Pass condition:** All checks pass. Return FAIL with a list of missing files or empty artifacts.

## Method
1. **Load.** Accept the artifact path(s) to check. If not provided, use the current working context.
2. **Run.** Execute each step in order (1→2→3→4). Do not proceed to the next step if the current one fails — fail fast.
3. **Report.** For each step: output PASS or FAIL with a list of specific checks and their results. If FAIL, include the exact issue and guidance for fixing it.
4. **Return.** Return the overall verdict (PASS/FAIL) and the step-level breakdown.

## Error Recovery

- **Missing prerequisite:** If a required tool or dependency is unavailable, report it clearly with the exact command to install or path to check. Do not silently skip.
- **Malformed input:** Validate key fields before processing. On failure, report the exact field name and expected format. Do not proceed with partial data.
- **Timeout:** Set a 30-second budget for any blocking operation (MCP call, script execution, DB query). If exceeded, write partial results to `agent-output/partial/` and note what completed vs. what timed out.
- **Empty result:** If no data matches the query, produce a valid empty output (not an error) with a note explaining the search scope and suggesting next steps.
- **Partial failure:** If some sub-tasks succeed and others fail, report the split clearly: which succeeded, which failed, and whether the successes are usable independently.

## Output format
```yaml
pre_submission_checklist:
  artifact: "agent-output/src/processors/data_processor.py"
  timestamp: "2026-07-19T10:30:00Z"
  verdict: "PASS"  # or FAIL
  steps:
    - step: 1. Requirements alignment
      status: PASS
      checks:
        - "Purpose stated at top of file: PASS"
        - "All requirements addressed: PASS"
        - "No contradicted requirements: PASS"
        - "Acceptance criteria verifiable: PASS"
    - step: 2. Format compliance
      status: PASS
      checks:
        - "File extension matches content: PASS"
        - "Python syntax valid: PASS"
        - "Naming conventions followed: PASS"
        - "No trailing whitespace: PASS"
    - step: 3. Quality baseline
      status: FAIL
      checks:
        - "All public functions have docstrings: FAIL (missing docstring in process_batch)"
        - "Type hints present: PASS"
        - "No dead code: PASS"
        - "Line length under 100: PASS"
      issues:
        - "Add docstring to process_batch() in data_processor.py line 42"
    - step: 4. Completeness gate
      status: PASS
      checks:
        - "Primary artifact exists: PASS"
        - "Corresponding test file exists: PASS"
  summary: "FAIL — 1 issue in step 3. Fix docstring and re-run checklist."
```
