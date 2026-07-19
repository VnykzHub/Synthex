# Template Index

Reference table of available artifact templates. Each template is a starting point for generating a specific type of file.

| Use case | Template file | Description |
|---|---|---|
| Scaffold a new Python source module | `python-module.py.tmpl` | Standard Python module skeleton with `__init__`-ready class, docstrings, type hints, logging, main function, and `if __name__ == "__main__"` guard. Use when creating any new `.py` module. |
| Generate a test suite for a Python function | `python-test.py.tmpl` | pytest file with three test groups: happy-path, edge-case, and error-handling. Each group has concrete test functions for a given module/function name. Use when generating tests alongside a code module. |
| Create a YAML configuration file | `yaml-config.yaml.tmpl` | Structured YAML config with project metadata, dependency declarations, runtime settings, and feature flags. Uses `{{ name }}`, `{{ version }}`, `{{ description }}` template variables. Use for any new configuration file. |
| Write a project README | `markdown-readme.md.tmpl` | Full README skeleton with Overview, Installation, Usage, Configuration, and Troubleshooting sections. Includes tables for config options and environment variables. Use when a project needs a user-facing documentation entry point. |
| Write a defensive shell script | `shell-script.sh.tmpl` | Bash script with `set -euo pipefail`, trap-based cleanup, structured argument parsing with `getopts`-style flags, pre-flight command checks, and `die`/`_log` helper functions. Use for any automation or utility script. |

## How to add a new template

1. Create the template file in `skills/templates/` with a `.tmpl` extension.
2. Add a row to this index table.
3. Ensure the template uses `{{ var }}` placeholders consistent with the artifact-factory skill's substitution conventions.
4. Register the corresponding generator pattern in `skills/artifact-factory/SKILL.md` if the template requires non-trivial generation logic beyond placeholder substitution.
