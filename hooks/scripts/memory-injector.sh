#!/usr/bin/env bash
# memory-injector.sh
# UserPromptSubmit: retrieve top-k chunks from the memory-graph vector store
# and inject them as additional context.  NEVER blocks the user — fail open.
set -uo pipefail
trap 'exit 0' ERR

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/init_db.sh"

INPUT="$(cat)"
PROMPT="$(printf '%s' "$INPUT" | jq -r '.prompt // ""' 2>/dev/null || true)"
[ -z "$PROMPT" ] && exit 0

# Resolve the plugin root so we can find the MCP server script.
# Prefer an explicit env var (set by the harness); fall back to script location.
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then
  PLUGIN_ROOT="$CLAUDE_PLUGIN_ROOT"
else
  PLUGIN_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
fi

MEMORY_SCRIPT="$PLUGIN_ROOT/mcp-servers/memory-graph/synthex_memory.py"

# Call the memory retrieval script with a 5-second timeout.
# If the script doesn't exist, fails, or times out — fail open (exit 0).
RESULT="$(timeout 5 python3 "$MEMORY_SCRIPT" retrieve --query "$PROMPT" --top-k 3 2>/dev/null)" || exit 0

# Parse the result as a JSON array of {chunk, source, score}.
CHUNKS="$(printf '%s' "$RESULT" | jq -r '.[] | "> **\(.source // "unknown")** (score: \(.score // "N/A"))\n> \(.chunk)\n"' 2>/dev/null)" || exit 0
[ -z "$CHUNKS" ] && exit 0

ADDITIONAL_CONTEXT="Relevant knowledge base excerpts:\n\n$CHUNKS"

# JSON-escape the context string
ESCAPED="$(printf '%s' "$ADDITIONAL_CONTEXT" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))' 2>/dev/null)" || exit 0

printf '{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":%s}}\n' "$ESCAPED"
exit 0
