---
name: organize-inputs
description: /synthex:organize-inputs — Organize and index files in user-input/. Scans the sandbox, categorizes files by type, generates an index, and validates naming conventions. READ-ONLY — never modifies files.
disable-model-invocation: true
---

# organize-inputs (command: `/synthex:organize-inputs`)

Organize and index files in `user-input/`. This command scans the input sandbox, categorizes files by type, generates a navigation index, and validates naming conventions. It is strictly read-only — it never moves, renames, or modifies files.

## Usage
```
/synthex:organize-inputs [--path <subdirectory>] [--output <index-path>] [--categorize] [--validate-naming]
```

## Parameters
- `--path` (optional, default: `user-input/`): The subdirectory within `user-input/` to organize.
- `--output` (optional, default: `user-input/INDEX.md`): Path for the generated index file. Must remain under `user-input/`.
- `--categorize` (optional, default: true): Categorize files by type (assignment, dataset, reference, config).
- `--validate-naming` (optional, default: true): Validate file and directory names against project naming conventions.

## Workflow
1. **Scan.** Use Glob to list all files under the specified path recursively. Group by directory.
2. **Categorize (if enabled).** For each file, determine its type based on path, extension, and content heuristics:
   - `assignment` — files in `user-input/assignments/` or containing `assignment` in path.
   - `dataset` — CSV, JSON, Parquet, or similar data files.
   - `reference` — Markdown, PDF, or text files containing reference material.
   - `config` — YAML, TOML, INI, or JSON configuration files.
   - `other` — files that do not match any category.
3. **Validate naming (if enabled).** Check each file and directory name against project naming conventions (snake_case for data files, kebab-case for config, PascalCase only for specific types). Report violations as warnings.
4. **Generate index.** Create a Markdown index file at `--output` with:
   - A summary table (total files, by category, by directory).
   - A per-directory file listing with file name, type, size, and last modified time.
   - Naming convention warnings (if any).
5. **Return the index.** Print the index content or a summary reference.

## Constraints
- **Never write, move, rename, or delete any file.** This command is read-only by design. The only file created is the index at `--output`.
- The index file is written under `user-input/` to stay within the input sandbox.
- If `--path` does not exist, print an error and exit without creating any files.

## Validation
- The `--output` path must resolve to a location under `user-input/`. Writing outside the input sandbox is not permitted.
- File size is reported in human-readable format (KB, MB) for easy scanning.

## Output format
```
Input organization for: user-input/
  Total files: 14
  By category: assignment (3), dataset (5), reference (4), config (2)
  By directory:
    user-input/assignments/ — 3 files
    user-input/datasets/ — 5 files
    user-input/references/ — 4 files
    user-input/config/ — 2 files

  Naming warnings: 1
    - "user-input/datasets/My_Data_File.csv" should use snake_case: "my_data_file.csv"

  Index written to: user-input/INDEX.md
```
