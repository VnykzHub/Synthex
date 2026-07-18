---
name: theory
description: "/synthex:theory -- Launch Methodologist to inspect user-input/ for LaTeX proofs, complexity analysis, or asymptotic bounds. Verify via heavy-compute sympy_solve."
disable-model-invocation: true
allowed-tools: Bash(sqlite3 *) Bash(echo *) Bash(find *) Bash(grep *) Bash(cat *) Bash(mkdir *)
---

# /synthex:theory -- Theoretical analysis: proofs, complexity, bounds

$ARGUMENTS may specify a file or problem statement.

## Step 1 -- Resolve SYNTHEX_ROOT

```
SYNTHEX_ROOT = $CLAUDE_PROJECT_DIR  (if set)  else $PWD
```

## Step 2 -- Survey user-input/

Search `user-input/assignments/`, `user-input/references/`, and `user-input/datasets/` for relevant material:

```bash
find "$SYNTHEX_ROOT/user-input" -type f \
  \( -name "*.tex" -o -name "*.pdf" -o -name "*.md" -o -name "*.txt" -o -name "*.bib" \) \
  2>/dev/null | head -30
```

If $ARGUMENTS specifies a particular file or topic, focus the search on that.

## Step 3 -- Extract and analyze

- Read any `.tex` files found. Identify the claim, the proof structure, or the complexity statement.
- If the material contains mathematical notation, extract the key expressions.
- If the material describes an algorithm, identify the asymptotic bound claimed.

## Step 4 -- Verify with heavy-compute MCP

For each extractable expression or bound, call the heavy-compute MCP:

- `mcp__plugin_synthex_heavy-compute__sympy_solve(expression="<extracted>", kind="auto")`
  - For limits, summations, recurrences, integrals, or equation solving
- `mcp__plugin_synthex_heavy-compute__profile_script(path="<path>", args=[])` if there is code to profile

Interpret the result: does it confirm the stated result? If not, note the discrepancy.

## Step 5 -- Log to state_ledger

```bash
# Escape details as single-line JSON
DETAILS="{\"file\":\"<analyzed-file>\",\"result\":\"<summary>\"}"
sqlite3 "$SYNTHEX_ROOT/logs/state_ledger.db" \
  "INSERT INTO state_ledger (agent, event_type, details) VALUES ('methodologist', 'theory.analysis', '$DETAILS');"
```

## Step 6 -- Write theory analysis report

Write to `agent-output/reports/theory_analysis.md`:

```markdown
# Theory Analysis Report
Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)

## Source Material
- File(s) analyzed: ...

## Claim / Problem Statement
...

## Verification
- Method: sympy_solve / manual derivation
- Result: ...
- Conclusion: confirmed | refuted | inconclusive

## Detailed Derivation
...
```

Report the findings to the user with the file path.
