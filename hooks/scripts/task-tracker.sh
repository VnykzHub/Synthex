#!/usr/bin/env bash
# task-tracker.sh
# TaskCreated|TaskCompleted: record task events in logs/intents.db.
#   $1 = "create" | "complete"
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/init_db.sh"

ACTION="${1:-unknown}"
[ "$ACTION" != "create" ] && [ "$ACTION" != "complete" ] && exit 0

INPUT="$(cat)"
TASK_ID="$(printf '%s' "$INPUT" | jq -r '.task_id // ""' 2>/dev/null || true)"
TASK_TITLE="$(printf '%s' "$INPUT" | jq -r '.task_title // ""' 2>/dev/null || true)"
CWD="$(printf '%s' "$INPUT" | jq -r '.cwd // ""' 2>/dev/null || true)"

ROOT="$(synthex_resolve_root "$CWD")"
synthex_init_dbs "$ROOT"

# Use the task title as the "why" field; fall back to a generic label.
WHY="$TASK_TITLE"
[ -z "$WHY" ] && WHY="task.$ACTION"

CONTEXT="$(printf '%s' "$INPUT" | jq -r '.context // ""' 2>/dev/null || true)"

# Escape single quotes for SQLite to prevent injection
WHY_ESC="$(printf '%s' "$WHY" | sed "s/'/''/g")"
TASK_ID_ESC="$(printf '%s' "$TASK_ID" | sed "s/'/''/g")"
CONTEXT_ESC="$(printf '%s' "$CONTEXT" | sed "s/'/''/g")"

command -v sqlite3 >/dev/null 2>&1 || exit 0
sqlite3 -cmd ".timeout 5000" "$ROOT/logs/intents.db" <<SQL
INSERT INTO intents(agent, action, why, task_id, context)
VALUES('task-tracker', 'task.$ACTION', '$WHY_ESC', '$TASK_ID_ESC', '$CONTEXT_ESC');
SQL

exit 0
