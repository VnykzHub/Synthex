#!/usr/bin/env bash
# agent-lifecycle-logger.sh
# SubagentStart|SubagentStop: log agent lifecycle events to state_ledger.db.
#   $1 = "start" | "stop"
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/init_db.sh"

PHASE="${1:-unknown}"
[ "$PHASE" != "start" ] && [ "$PHASE" != "stop" ] && exit 0

INPUT="$(cat)"
AGENT_TYPE="$(printf '%s' "$INPUT" | jq -r '.agent_type // .subagent_type // ""' 2>/dev/null || true)"
SESSION_ID="$(printf '%s' "$INPUT" | jq -r '.session_id // ""' 2>/dev/null || true)"
CWD="$(printf '%s' "$INPUT" | jq -r '.cwd // ""' 2>/dev/null || true)"

[ -z "$AGENT_TYPE" ] && exit 0

ROOT="$(synthex_resolve_root "$CWD")"
synthex_init_dbs "$ROOT"

# Build the details JSON, including session_id if present
if [ -n "$SESSION_ID" ]; then
  DETAILS="{\"session_id\":\"$SESSION_ID\"}"
else
  DETAILS="{}"
fi

# Escape single quotes for SQLite to prevent injection
AGENT_TYPE_ESC="$(printf '%s' "$AGENT_TYPE" | sed "s/'/''/g")"
DETAILS_ESC="$(printf '%s' "$DETAILS" | sed "s/'/''/g")"

command -v sqlite3 >/dev/null 2>&1 || exit 0
sqlite3 -cmd ".timeout 5000" "$ROOT/logs/state_ledger.db" <<SQL
INSERT INTO state_ledger(agent, event_type, details)
VALUES('$AGENT_TYPE_ESC', 'subagent.$PHASE', '$DETAILS_ESC');
SQL

exit 0
