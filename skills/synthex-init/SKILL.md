---
name: synthex-init
description: "/synthex:synthex-init -- Scaffold the runtime sandbox directories, create SQLite databases with full schema, and mark init complete. Call once at project setup."
disable-model-invocation: true
allowed-tools: Bash(sqlite3 *) Bash(mkdir *) Bash(echo *) Bash(test *) Bash(find *)
---

# /synthex:synthex-init -- Scaffold sandbox + init SQLite + report

Resolve SYNTHEX_ROOT from $CLAUDE_PROJECT_DIR, else $PWD. The sandbox lives in the user's project (not the plugin directory).

## Step 1 -- Resolve root

```
SYNTHEX_ROOT=$CLAUDE_PROJECT_DIR  # if set, else $PWD
```

## Step 2 -- Create directory tree

Create all directories under SYNTHEX_ROOT in a single mkdir call:

```bash
mkdir -p "$SYNTHEX_ROOT/user-input/assignments" \
         "$SYNTHEX_ROOT/user-input/datasets" \
         "$SYNTHEX_ROOT/user-input/references" \
         "$SYNTHEX_ROOT/knowledgebase/schemas" \
         "$SYNTHEX_ROOT/knowledgebase/papers" \
         "$SYNTHEX_ROOT/knowledgebase/models" \
         "$SYNTHEX_ROOT/agent-output/src" \
         "$SYNTHEX_ROOT/agent-output/artifacts" \
         "$SYNTHEX_ROOT/agent-output/reports" \
         "$SYNTHEX_ROOT/logs/vectors" \
         "$SYNTHEX_ROOT/logs/archives"
```

## Step 3 -- Create intents.db

```bash
sqlite3 "$SYNTHEX_ROOT/logs/intents.db" <<'SQL'
CREATE TABLE IF NOT EXISTS intents (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  ts        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  agent     TEXT,
  action    TEXT,
  why       TEXT,
  task_id   TEXT,
  context   TEXT
);
CREATE TABLE IF NOT EXISTS tasks (
  id          TEXT PRIMARY KEY,
  title       TEXT NOT NULL,
  priority    TEXT DEFAULT 'medium',
  status      TEXT DEFAULT 'pending',
  assigned_to TEXT,
  created_at  TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  updated_at  TEXT,
  completed_at TEXT
);
SQL
```

## Step 4 -- Create state_ledger.db

```bash
sqlite3 "$SYNTHEX_ROOT/logs/state_ledger.db" <<'SQL'
CREATE TABLE IF NOT EXISTS state_ledger (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  ts         TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  agent      TEXT,
  event_type TEXT,
  details    TEXT
);
CREATE TABLE IF NOT EXISTS kg_triples (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  subject   TEXT, predicate TEXT, object TEXT, source TEXT,
  ts        TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
SQL
```

## Step 5 -- Verify and report

```bash
echo "=== SYNTHEX_ROOT: $SYNTHEX_ROOT ==="
echo "--- Directory tree ---"
find "$SYNTHEX_ROOT/user-input" \
     "$SYNTHEX_ROOT/knowledgebase" \
     "$SYNTHEX_ROOT/agent-output" \
     "$SYNTHEX_ROOT/logs" -type d 2>/dev/null | sort
echo ""
echo "--- SQLite databases ---"
sqlite3 "$SYNTHEX_ROOT/logs/intents.db" ".tables"
sqlite3 "$SYNTHEX_ROOT/logs/state_ledger.db" ".tables"
```

Report what was created. If directories already exist and tables already have the correct schema, report that too. Mark init complete.
