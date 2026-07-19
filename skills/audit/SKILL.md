---
name: audit
description: "/synthex:audit -- Compile system logs into a Markdown report. Use when running /synthex:audit."
role: worker
disable-model-invocation: true
related_skills: [experiment-auditor, knowledge-graph, task-tracking, report]
allowed-tools: Bash(sqlite3 *) Bash(echo *) Bash(test *) Bash(mkdir *) Bash(date *) Bash(cat *) Bash(awk *) Bash(printf *) Bash(sed *)
---

# /synthex:audit -- Compile chronological audit report

## Step 1 -- Resolve SYNTHEX_ROOT

```bash
SYNTHEX_ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"
```

## Step 2 -- Verify databases

```bash
SYNTHEX_ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"
test -f "$SYNTHEX_ROOT/logs/intents.db" || echo "WARNING: intents.db not found"
test -f "$SYNTHEX_ROOT/logs/state_ledger.db" || echo "WARNING: state_ledger.db not found"
```

## Step 3 -- Extract data and assemble the audit report (Steps 3-6 merged)

```bash
SYNTHEX_ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"

# Compute output filename
DATE_STAMP=$(date -u +%Y-%m-%d)
OUTPUT_FILE="$SYNTHEX_ROOT/agent-output/reports/audit_${DATE_STAMP}.md"

# Ensure output directory exists
mkdir -p "$SYNTHEX_ROOT/agent-output/reports"
# Create portable temp directory (Windows-safe via mktemp)
TMPDIR=$(mktemp -d) || { echo "FATAL: mktemp failed"; exit 1; }
trap 'rm -rf "$TMPDIR"' EXIT

# Guard: check sqlite3 is available
if ! command -v sqlite3 2>/dev/null; then
  echo "FATAL: sqlite3 not found. Install SQLite or check PATH." >&2
  exit 1
fi

# Query state_ledger.db (one invocation, .output redirects to separate temp files)
sqlite3 "$SYNTHEX_ROOT/logs/state_ledger.db" 2>/dev/null <<SQL
.separator |
.headers off
.output "$TMPDIR"/synthex_events.txt
SELECT id, ts, agent, event_type, details FROM state_ledger ORDER BY ts ASC LIMIT 500;
.output "$TMPDIR"/synthex_kg.txt
SELECT subject, predicate, object, source, ts FROM kg_triples ORDER BY ts DESC LIMIT 20;
SQL

# Query intents.db (one invocation, .output redirects to separate temp files)
sqlite3 "$SYNTHEX_ROOT/logs/intents.db" 2>/dev/null <<SQL
.separator |
.headers off
.output "$TMPDIR"/synthex_intents.txt
SELECT id, ts, agent, action, why, task_id FROM intents ORDER BY ts ASC LIMIT 500;
.output "$TMPDIR"/synthex_tasks.txt
SELECT id, title, status, assigned_to, created_at, completed_at FROM tasks ORDER BY created_at ASC LIMIT 500;
SQL

# Assemble the Markdown report via heredoc
cat > "$OUTPUT_FILE" << REPORTOUT
# Synthex Audit Report -- ${DATE_STAMP}
Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)

## 1. Event Timeline (state_ledger)
| # | Timestamp | Agent | Event Type | Details |
| :-| :-------- | :---- | :--------- | :------ |
$(awk '{print "| " $0 " |"}' "$TMPDIR"/synthex_events.txt)

## 2. Intent Log (intents)
| # | Timestamp | Agent | Action | Why | Task ID |
| :-| :-------- | :---- | :----- | :-- | :------ |
$(awk '{print "| " $0 " |"}' "$TMPDIR"/synthex_intents.txt)

## 3. Task Summary
| ID | Title | Status | Assigned To | Created | Completed |
| :- | :---- | :----- | :---------- | :------ | :-------- |
$(awk '{print "| " $0 " |"}' "$TMPDIR"/synthex_tasks.txt)

## 4. Recent Knowledge Graph Triples
| Subject | Predicate | Object | Source | Timestamp |
| :------ | :-------- | :----- | :----- | :-------- |
$(awk '{print "| " $0 " |"}' "$TMPDIR"/synthex_kg.txt)

## Compact Mode
When invoked with `--compact` or when the calling agent already knows the methodology:
skip the "Core principles" and background sections. Use only the checklist, specific instructions, and output format.
Token budget in compact mode: ~500 tokens.

## Error Recovery

- **Missing prerequisite:** If a required tool or dependency is unavailable, report it clearly with the exact command to install or path to check. Do not silently skip.
- **Malformed input:** Validate key fields before processing. On failure, report the exact field name and expected format. Do not proceed with partial data.
- **Timeout:** Set a 30-second budget for any blocking operation (MCP call, script execution, DB query). If exceeded, write partial results to `agent-output/partial/` and note what completed vs. what timed out.
- **Empty result:** If no data matches the query, produce a valid empty output (not an error) with a note explaining the search scope and suggesting next steps.
- **Partial failure:** If some sub-tasks succeed and others fail, report the split clearly: which succeeded, which failed, and whether the successes are usable independently.

## 5. Report Metadata
- Source DBs: logs/intents.db, logs/state_ledger.db
- Report path: $OUTPUT_FILE
REPORTOUT

# Log the audit event in state_ledger
OUTPUT_FILE_ESC="$(printf '%s' "$OUTPUT_FILE" | sed "s/'/''/g")"
sqlite3 "$SYNTHEX_ROOT/logs/state_ledger.db" \
  "INSERT INTO state_ledger (agent, event_type, details) VALUES ('audit-archivist', 'audit.generate', '{\"path\":\"$OUTPUT_FILE_ESC\"}');"

echo "Audit report written to: $OUTPUT_FILE"
```

Report the output path to the user.
