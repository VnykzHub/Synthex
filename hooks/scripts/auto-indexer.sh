#!/usr/bin/env bash
# auto-indexer.sh
# PostToolUse (Write|Edit): append written-file metadata to the index queue
# and record the event in state_ledger.db.  Never blocks (exit 0 always).
set -uo pipefail
trap 'exit 0' ERR

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/init_db.sh"

INPUT="$(cat)"
eval "$(printf '%s' "$INPUT" | jq -r '{
  fp: (.tool_input.file_path // .tool_input.path // ""),
  cwd: (.cwd // ""),
  tool: (.tool_name // "Write"),
  details: ({path: (.tool_input.file_path // .tool_input.path // ""), tool: (.tool_name // "Write")} | tojson)
} | "FP=\(.fp|@sh) CWD=\(.cwd|@sh) TOOL=\(.tool|@sh) JSON_DETAILS=\(.details|@sh)"' 2>/dev/null || echo "FP='' CWD='' TOOL='Write' JSON_DETAILS='{}'")"

# Empty path — nothing to index
[ -z "$FP" ] && exit 0

# Only index matching file extensions
case "$FP" in
  *.md|*.tex|*.py|*.rs|*.js|*.ts|*.json|*.yaml|*.sql) ;;
  *) exit 0 ;;
esac

ROOT="$(synthex_resolve_root "$CWD")"
synthex_init_dbs "$ROOT"

# Append one JSON line to the index queue
printf '{"ts":"%s","path":"%s"}\n' "$(date -u '+%Y-%m-%dT%H:%M:%S')" "$FP" >> "$ROOT/logs/index_queue.jsonl"

sqlite3 -cmd ".timeout 5000" "$ROOT/logs/state_ledger.db" <<SQL
PRAGMA journal_mode=WAL;
INSERT INTO state_ledger(agent, event_type, details)
VALUES('auto-indexer', 'tool.write', json('$(printf '%s' "$JSON_DETAILS" | sed "s/'/''/g")'));
SQL

exit 0
