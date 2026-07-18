#!/usr/bin/env bash
# sandbox-gate.sh — PreToolUse guard enforcing the Synthex sandbox.
#   Write/Edit -> only inside  $SYNTHEX_ROOT/agent-output/
#   Read       -> only inside  {user-input, knowledgebase, agent-output}/
# Blocks by exiting 2 with a reason on stderr; exit 0 = no objection.
# Fails OPEN (exit 0) on parse errors, empty path, or permissive mode.
set -uo pipefail

# --- fail open on any unexpected error ---------------------------------------
trap 'exit 0' ERR

# Escape hatch: SYNTHEX_SANDBOX_MODE=permissive disables the gate.
if [ "${SYNTHEX_SANDBOX_MODE:-}" = "permissive" ]; then
  exit 0
fi

INPUT="$(cat 2>/dev/null || true)"
[ -z "$INPUT" ] && exit 0

TOOL="$(printf '%s' "$INPUT" | jq -r '.tool_name // ""' 2>/dev/null || echo "")"
FP="$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // .tool_input.path // ""' 2>/dev/null || echo "")"
CWD="$(printf '%s' "$INPUT" | jq -r '.cwd // ""' 2>/dev/null || echo "")"

# Only Read/Write/Edit are path-gated. Anything else (e.g. Bash): fail open.
case "$TOOL" in
  Read|Write|Edit) : ;;
  *) exit 0 ;;
esac

# Empty path -> cannot judge -> fail open.
[ -z "$FP" ] && exit 0

# Resolve sandbox base (DATA_CONTRACTS §1).
SYNTHEX_ROOT="${CLAUDE_PROJECT_DIR:-}"
if [ -z "$SYNTHEX_ROOT" ] && [ -n "$CWD" ] && [ "$CWD" != "null" ]; then
  SYNTHEX_ROOT="$CWD"
fi
[ -z "$SYNTHEX_ROOT" ] && SYNTHEX_ROOT="$PWD"
[ -z "$SYNTHEX_ROOT" ] && exit 0

OUT="$SYNTHEX_ROOT/agent-output"
IN="$SYNTHEX_ROOT/user-input"
KB="$SYNTHEX_ROOT/knowledgebase"

case "$TOOL" in
  Write|Edit)
    case "$FP" in
      "$OUT"/*|"$OUT") exit 0 ;;
      *) echo "sandbox-gate: writes are only permitted under agent-output/ (got: $FP)" >&2; exit 2 ;;
    esac ;;
  Read)
    case "$FP" in
      "$IN"/*|"$IN"|"$KB"/*|"$KB"|"$OUT"/*|"$OUT") exit 0 ;;
      *) echo "sandbox-gate: reads are only permitted from user-input/, knowledgebase/, agent-output/ (got: $FP)" >&2; exit 2 ;;
    esac ;;
esac

exit 0
