#!/usr/bin/env bash
# auto-indexer.sh
# PostToolUse (Write|Edit): append written-file metadata to the index queue
# and record the event in state_ledger.db.  Never blocks (exit 0 always).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/init_db.sh"

INPUT="$(cat)"
FP="$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // .tool_input.path // ""' 2>/dev/null || true)"
CWD="$(printf '%s' "$INPUT" | jq -r '.cwd // ""' 2>/dev/null || true)"
TOOL="$(printf '%s' "$INPUT" | jq -r '.tool_name // "Write"' 2>/dev/null || echo "Write")"

# Empty path — nothing to index
[ -z "$FP" ] && exit 0

# Only index matching file extensions
case "$FP" in
  *.md|*.tex|*.py|*.rs|*.js|*.ts|*.json|*.yaml|*.sql) ;;
  *) exit 0 ;;
esac

ROOT="$(synthex_resolve_root "$CWD")"
synthex_init_dbs "$ROOT"

TS="$(date -u '+%Y-%m-%dT%H:%M:%S.%3NZ')"

# Append one JSON line to the index queue
mkdir -p "$ROOT/logs"
printf '{"ts":"%s","path":"%s"}\n' "$TS" "$FP" >> "$ROOT/logs/index_queue.jsonl"

# Escape single quotes for SQLite INSERT
FP_ESC="$(printf '%s' "$FP" | sed "s/'/''/g")"
TOOL_ESC="$(printf '%s' "$TOOL" | sed "s/'/''/g")"

sqlite3 "$ROOT/logs/state_ledger.db" <<SQL
INSERT INTO state_ledger(agent, event_type, details)
VALUES('auto-indexer', 'tool.write', '{"path":"$FP_ESC","tool":"$TOOL_ESC","ts":"$TS"}');
SQL

exit 0
