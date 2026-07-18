#!/usr/bin/env bash
# init_db.sh — apply the DATA_CONTRACTS §2 schema to both SQLite DBs.
# Idempotent: safe to call on every hook invocation. Sourced by the other
# scripts (provides synthex_resolve_root + synthex_init_dbs) and also runnable
# standalone:  bash init_db.sh [SYNTHEX_ROOT]
set -euo pipefail

# Resolve the sandbox base per DATA_CONTRACTS §1:
#   $CLAUDE_PROJECT_DIR | hook stdin ".cwd" | $PWD
# Arg 1 (optional) = a ".cwd" value parsed from stdin by the caller.
synthex_resolve_root() {
  local cwd_from_stdin="${1:-}"
  if [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then
    printf '%s' "$CLAUDE_PROJECT_DIR"
  elif [ -n "$cwd_from_stdin" ] && [ "$cwd_from_stdin" != "null" ]; then
    printf '%s' "$cwd_from_stdin"
  else
    printf '%s' "$PWD"
  fi
}

# Create logs/ and apply the schema to intents.db + state_ledger.db.
synthex_init_dbs() {
  local root="$1"
  [ -z "$root" ] && return 1
  local logs="$root/logs"
  mkdir -p "$logs"

  sqlite3 -cmd '.timeout 5000' "$logs/intents.db" <<'SQL'
PRAGMA journal_mode=WAL;
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

  sqlite3 -cmd '.timeout 5000' "$logs/state_ledger.db" <<'SQL'
PRAGMA journal_mode=WAL;
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
}

# Standalone execution: init DBs under the given (or resolved) root.
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
  ROOT="$(synthex_resolve_root "${1:-}")"
  synthex_init_dbs "$ROOT"
  printf 'synthex: initialized DBs under %s/logs\n' "$ROOT" >&2
fi
