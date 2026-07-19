---
name: theory
description: "/synthex:theory — Analyze proofs, complexity, or asymptotic bounds. Use when running /synthex:theory."
role: worker
disable-model-invocation: true
allowed-tools: Bash(sqlite3 *) Bash(echo *) Bash(find *) Bash(grep *) Bash(cat *) Bash(mkdir *)
related_skills: [literature-survey, data-interpreter, research-loop]
---

## When to use
- You need to verify a mathematical proof, complexity bound, or asymptotic claim in source materials
- You need to symbolically solve or simplify mathematical expressions using sympy or manual derivation
- You need to analyze algorithm performance bounds with profiling or asymptotic analysis

**Do NOT use when:**
- The task is a simple arithmetic calculation (use direct python3 or calculator instead)
- The user explicitly asks for a different analytical approach or tool
- The required input files (`.tex`, `.md`, `.pdf`) do not exist in `user-input/` and no problem statement is provided in $ARGUMENTS

# /synthex:theory -- Theoretical analysis: proofs, complexity, bounds

$ARGUMENTS may specify a file or problem statement.

## Step 1 -- Resolve SYNTHEX_ROOT

```bash
SYNTHEX_ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"
export SYNTHEX_ROOT
```

## Step 2 -- Survey user-input/

Search `user-input/assignments/`, `user-input/references/`, and `user-input/datasets/` for relevant material:

```bash
SYNTHEX_ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"
find "$SYNTHEX_ROOT/user-input" -type f \
  \( -name "*.tex" -o -name "*.pdf" -o -name "*.md" -o -name "*.txt" -o -name "*.bib" \) \
  2>/dev/null | head -30
```

If $ARGUMENTS specifies a particular file or topic, focus the search on that.

## Step 3 -- Extract and analyze

- Read any `.tex` files found. Identify the claim, the proof structure, or the complexity statement.
- If the material contains mathematical notation, extract the key expressions.
- If the material describes an algorithm, identify the asymptotic bound claimed.

## Step 4 -- Verify with heavy-compute MCP (with fallback)

> **Tool-unavailable fallback**: If the heavy-compute MCP (`sympy_solve`, `profile_script`) is unavailable, fall back to manual derivation. Document each step of the derivation in `agent-output/reports/theory_analysis.md` under a "Manual Derivation" section, noting that the computation was performed by hand rather than verified symbolically. For simple expressions, use `python3 -c "import sympy; ..."` if sympy is installed locally; otherwise compute analytically and state the assumptions.

For each extractable expression or bound, call the heavy-compute MCP when available:

- `mcp__plugin_synthex_heavy-compute__sympy_solve(expression="<extracted>", kind="auto")`
  - For limits, summations, recurrences, integrals, or equation solving
- `mcp__plugin_synthex_heavy-compute__profile_script(path="<path>", args=[])` if there is code to profile

Interpret the result: does it confirm the stated result? If not, note the discrepancy.

## Step 5 -- Log to state_ledger

```bash
SYNTHEX_ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"

# Verify DB and table exist before inserting
if [ ! -f "$SYNTHEX_ROOT/logs/state_ledger.db" ]; then
  echo "WARNING: state_ledger.db not found. Skipping audit log." >&2
else
  TABLE_OK=$(sqlite3 "$SYNTHEX_ROOT/logs/state_ledger.db" "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='state_ledger';")
  if [ "$TABLE_OK" -eq 0 ]; then
    echo "WARNING: state_ledger table not found. Skipping audit log." >&2
  else
    # Escape details as single-line JSON, then escape single quotes for SQLite
    DETAILS="{\"file\":\"<analyzed-file>\",\"result\":\"<summary>\"}"
    DETAILS_ESC="$(printf '%s' "$DETAILS" | sed "s/'/''/g")"
    sqlite3 "$SYNTHEX_ROOT/logs/state_ledger.db" \
      "INSERT INTO state_ledger (agent, event_type, details) VALUES ('methodologist', 'theory.analysis', '$DETAILS_ESC');"
  fi
fi
```

## Step 6 -- Write theory analysis report

Write to `agent-output/reports/theory_analysis.md`:

```markdown
# Theory Analysis Report
Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)

## Source Material
- File(s) analyzed: <path-to-analyzed-file(s)>
- Relevant excerpts: <key-quotes-or-formulas>

## Claim / Problem Statement
<State the claim, theorem, or complexity bound being verified>

## Verification
- Method: sympy_solve / manual derivation / profile_script
- Expression(s) verified: <extracted-expression>
- Result: <symbolic-or-numeric-result>
- Conclusion: confirmed | refuted | inconclusive

## Error Recovery

- **Missing prerequisite:** If a required tool or dependency is unavailable, report it clearly with the exact command to install or path to check. Do not silently skip.
- **Malformed input:** Validate key fields before processing. On failure, report the exact field name and expected format. Do not proceed with partial data.
- **Timeout:** Set a 30-second budget for any blocking operation (MCP call, script execution, DB query). If exceeded, write partial results to `agent-output/partial/` and note what completed vs. what timed out.
- **Empty result:** If no data matches the query, produce a valid empty output (not an error) with a note explaining the search scope and suggesting next steps.
- **Partial failure:** If some sub-tasks succeed and others fail, report the split clearly: which succeeded, which failed, and whether the successes are usable independently.

## Detailed Derivation
<step-by-step derivation or sympy_solve output>
```

Report the findings to the user with the file path.
