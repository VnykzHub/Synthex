---
name: audit
description: "/synthex:audit -- Compile logs/state_ledger.db and logs/intents.db into a chronological Markdown audit report with event timeline, task summary, and recent KG triples."
disable-model-invocation: true
allowed-tools: Bash(sqlite3 *) Bash(echo *) Bash(test *) Bash(mkdir *) Bash(date *)
---

# /synthex:audit -- Compile chronological audit report

## Step 1 -- Resolve SYNTHEX_ROOT

```
SYNTHEX_ROOT = $CLAUDE_PROJECT_DIR  (if set)  else $PWD
```

## Step 2 -- Verify databases

```bash
test -f "$SYNTHEX_ROOT/logs/intents.db" || echo "WARNING: intents.db not found"
test -f "$SYNTHEX_ROOT/logs/state_ledger.db" || echo "WARNING: state_ledger.db not found"
```

## Step 3 -- Extract data from both databases

```bash
# State ledger -- full event timeline
sqlite3 -header -column "$SYNTHEX_ROOT/logs/state_ledger.db" \
  "SELECT id, ts, agent, event_type, details FROM state_ledger ORDER BY ts ASC;" 2>/dev/null
```

```bash
# Intents -- full intent timeline
sqlite3 -header -column "$SYNTHEX_ROOT/logs/intents.db" \
  "SELECT id, ts, agent, action, why, task_id FROM intents ORDER BY ts ASC;" 2>/dev/null
```

```bash
# Tasks -- summary (status rollup)
sqlite3 -header -column "$SYNTHEX_ROOT/logs/intents.db" \
  "SELECT id, title, status, assigned_to, created_at, completed_at FROM tasks ORDER BY created_at ASC;" 2>/dev/null
```

```bash
# KG triples -- recent
sqlite3 -header -column "$SYNTHEX_ROOT/logs/state_ledger.db" \
  "SELECT id, subject, predicate, object, source, ts FROM kg_triples ORDER BY ts DESC LIMIT 20;" 2>/dev/null
```

## Step 4 -- Determine output filename

```bash
DATE_STAMP=$(date -u +%Y-%m-%d)
OUTPUT_FILE="$SYNTHEX_ROOT/agent-output/reports/audit_${DATE_STAMP}.md"
```

## Step 5 -- Assemble the audit report

Write to `$OUTPUT_FILE` with the following structure:

```markdown
# Synthex Audit Report -- $(date -u +%Y-%m-%d)
Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)

## 1. Event Timeline (state_ledger)
| # | Timestamp | Agent | Event Type | Details |
| :-| :-------- | :---- | :--------- | :------ |
| ... merged from Step 3 state_ledger query ...

## 2. Intent Log (intents)
| # | Timestamp | Agent | Action | Why | Task ID |
| :-| :-------- | :---- | :----- | :-- | :------ |
| ... merged from Step 3 intents query ...

## 3. Task Summary
| ID | Title | Status | Assigned To | Created | Completed |
| :- | :---- | :----- | :---------- | :------ | :-------- |
| ... merged from Step 3 tasks query ...

## 4. Recent Knowledge Graph Triples
| Subject | Predicate | Object | Source | Timestamp |
| :------ | :-------- | :----- | :----- | :-------- |
| ... merged from Step 3 kg_triples query ...

## 5. Report Metadata
- Source DBs: logs/intents.db, logs/state_ledger.db
- Report path: $OUTPUT_FILE
```

## Step 6 -- Log the audit event

```bash
sqlite3 "$SYNTHEX_ROOT/logs/state_ledger.db" \
  "INSERT INTO state_ledger (agent, event_type, details) VALUES ('audit-archivist', 'audit.generate', '{\"path\":\"$OUTPUT_FILE\"}');"
```

Report the output path to the user.
