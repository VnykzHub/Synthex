---
name: structure-validator
description: Python validation patterns for folder boundaries, YAML structures, naming conventions, and file existence. Invoked by quality-automation and artifact-verifier for generating validation logic and by any agent that needs structural validation of artifacts. Use when validating folder boundaries, YAML structures, naming conventions, or file existence against a project schema.
---

# structure-validator

Python validation patterns for folder boundaries, YAML structures, naming conventions, and file existence. This skill provides reusable validation functions and patterns that any agent can use to verify that artifacts meet structural requirements without writing validation logic from scratch.

## When to use
- You need to validate that a directory tree matches an expected structure
- You need to check that YAML files contain required keys and valid values
- You need to verify that file and directory names follow project naming conventions
- You need to confirm that required files exist and are non-empty
- You are generating validation scripts for use in CI or scheduled tasks
- You are verifying artifacts before delivery

## Core principles

1. **Fail early, fail clearly.** Each validation function should check the most likely failure point first and return a clear error message with the exact path and nature of the failure.
2. **Composable.** Validation functions should be composable — a directory validator can call a naming validator on each item it finds. Return results as structured lists, not a single pass/fail boolean.
3. **Self-validating.** The validation rules themselves should be verifiable. Store expected structures as data (YAML, JSON, or dicts) in `knowledgebase/schemas/`, not as hardcoded logic.
4. **Shell-friendly exit codes.** When used in scripts: exit 0 = all passed, exit 1 = warnings only, exit 2 = failures found.
5. **Standard library only.** Prefer Python standard library for all validation. Use `os`, `pathlib`, `re`, `yaml` (via PyYAML), `json`, `ast`.

## Validation patterns

### Pattern 1: Folder boundary validator
Validates that a directory tree matches an expected structure.

```python
def validate_directory_structure(root: Path, expected: dict) -> list[dict]:
    """
    Validate directory tree against expected structure.
    
    expected format:
    {
        "dirs": ["subdir_a", "subdir_b"],
        "files": ["file_a.py", "file_b.md"],
        "subdirs": {
            "subdir_a": {
                "dirs": ["nested_dir"],
                "files": ["__init__.py"]
            }
        }
    }
    
    Returns list of {"type": "missing_dir"|"extra_dir"|"missing_file"|"extra_file",
                     "path": str, "severity": "error"|"warning"}
    """
```

### Pattern 2: YAML structure validator
Validates that a YAML file contains required keys and values of the correct type.

```python
def validate_yaml_structure(filepath: Path, schema: dict) -> list[dict]:
    """
    Validate YAML file against a schema definition.
    
    schema format:
    {
        "required_keys": ["title", "version", "dependencies"],
        "key_types": {
            "title": str,
            "version": str,
            "dependencies": list,
            "enabled": bool
        },
        "allowed_values": {
            "status": ["draft", "review", "approved", "archived"]
        }
    }
    
    Returns list of {"field": str, "issue": str, "severity": "error"|"warning"}
    """
```

### Pattern 3: Naming convention validator
Validates file and directory names against project naming rules.

```python
def validate_naming(name: str, conventions: dict) -> list[dict]:
    """
    Validate a name against naming conventions.
    
    conventions format:
    {
        "python_file": r"^[a-z][a-z0-9_]*\.py$",
        "markdown_file": r"^[a-z][a-z0-9\-]*\.md$",
        "yaml_file": r"^[a-z][a-z0-9\-]*\.ya?ml$",
        "directory": r"^[a-z][a-z0-9\-]*$"
    }
    
    Returns list of {"name": str, "expected_pattern": str, "severity": "error"}
    """
```

### Pattern 4: File existence validator
Validates that required files exist, are non-empty, and have correct permissions.

```python
def validate_file_existence(root: Path, required_files: list[str]) -> list[dict]:
    """
    Validate that required files exist and are non-empty.
    
    required_files format: list of relative paths
    ["src/__init__.py", "src/core.py", "tests/test_core.py", "README.md"]
    
    Returns list of {"path": str, "issue": "missing"|"empty", "severity": "error"}
    """
```

## Method
1. **Identify.** Determine what needs validation: a directory tree, a YAML file, naming conventions, or file existence.
2. **Select patterns.** Choose one or more validation patterns from above.
3. **Load schemas.** If validation must match an expected structure, load the schema from `knowledgebase/schemas/` or the caller's provided data.
4. **Execute.** Run the validation function(s) against the target.
5. **Aggregate.** Combine results from multiple patterns. Deduplicate related issues.
6. **Return.** Return the combined result list with each finding's severity.

## Real Python implementations

Below are concrete, runnable implementations of the four core validation functions. Each returns `dict[str, bool | list[str]]` with a `"passing"` boolean and a `"findings"` list.

```python
from pathlib import Path
import re, yaml

def check_boundaries(root: Path, expected_dirs: list[str]) -> dict[str, bool | list[str]]:
    """Validate that all expected directories exist under root."""
    findings = []
    for d in expected_dirs:
        if not (root / d).is_dir():
            findings.append(f"missing_dir:{d}")
    return {"passing": len(findings) == 0, "findings": findings}

def check_yaml_files(root: Path, required_keys: dict[str, list[str]]) -> dict[str, bool | list[str]]:
    """Validate YAML files contain required keys; requires PyYAML."""
    findings = []
    for path, keys in required_keys.items():
        fp = root / path
        if not fp.is_file():
            findings.append(f"missing:{path}")
            continue
        data = yaml.safe_load(fp.read_text()) or {}
        for k in keys:
            if k not in data:
                findings.append(f"missing_key:{path}:{k}")
    return {"passing": len(findings) == 0, "findings": findings}

def check_naming(root: Path, patterns: dict[str, str]) -> dict[str, bool | list[str]]:
    """Validate file/directory names match named regex patterns."""
    findings = []
    for label, regex in patterns.items():
        for f in root.rglob("*"):
            if not re.match(regex, f.name):
                findings.append(f"violation:{f.relative_to(root)}:expected_{label}")
    return {"passing": len(findings) == 0, "findings": findings}

def check_required_files(root: Path, required: list[str]) -> dict[str, bool | list[str]]:
    """Validate that required files exist and are non-empty."""
    findings = []
    for rp in required:
        fp = root / rp
        if not fp.is_file():
            findings.append(f"missing:{rp}")
        elif fp.stat().st_size == 0:
            findings.append(f"empty:{rp}")
    return {"passing": len(findings) == 0, "findings": findings}
```

## Output format
Return a structured result:
```json
{
  "target": "agent-output/artifacts/plans/",
  "passed": 42,
  "failed": 3,
  "warnings": 1,
  "findings": [
    {"type": "missing_file", "path": "plans/plan-alpha/CHANGELOG.md", "severity": "error", "message": "Required file CHANGELOG.md not found in plan-alpha"},
    {"type": "naming_violation", "path": "plans/plan-alpha/MyPlan.yaml", "severity": "error", "message": "YAML file should use kebab-case: my-plan.yaml"},
    {"type": "empty_file", "path": "plans/plan-alpha/README.md", "severity": "warning", "message": "README.md exists but is empty"}
  ]
}
```
