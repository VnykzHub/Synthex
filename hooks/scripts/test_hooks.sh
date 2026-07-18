#!/usr/bin/env bash
# test_hooks.sh — comprehensive test harness for Synthex hook scripts.
set -uo pipefail

command -v jq >/dev/null 2>&1 || { echo "jq required"; exit 1; }

TEST_ROOT="$(mktemp -d)"
[ -z "$TEST_ROOT" ] && { echo "mktemp -d failed"; exit 1; }
export CLAUDE_PROJECT_DIR="$TEST_ROOT"
mkdir -p "$TEST_ROOT/agent-output" "$TEST_ROOT/user-input" "$TEST_ROOT/knowledgebase"

PASS=0; FAIL=0
check() {
  local label="$1" expected="$2" actual="$3"
  if [ "$actual" -eq "$expected" ]; then
    echo "  PASS $label"; PASS=$((PASS+1))
  else
    echo "  FAIL $label (expected exit $expected, got $actual)"; FAIL=$((FAIL+1))
  fi
}

# Test 1: Write outside agent-output -> blocked
echo '{"tool_name":"Write","tool_input":{"file_path":"'$TEST_ROOT'/evil.sh"}}' | bash sandbox-gate.sh; check "write-outside" 2 $?

# Test 2: Write inside agent-output -> allowed
echo '{"tool_name":"Write","tool_input":{"file_path":"'$TEST_ROOT'/agent-output/out.py"}}' | bash sandbox-gate.sh; check "write-inside" 0 $?

# Test 3: Read outside zones -> blocked
echo '{"tool_name":"Read","tool_input":{"file_path":"'$TEST_ROOT'/random.txt"}}' | bash sandbox-gate.sh; check "read-outside" 2 $?

# Test 4: Read user-input -> allowed
echo '{"tool_name":"Read","tool_input":{"file_path":"'$TEST_ROOT'/user-input/data.csv"}}' | bash sandbox-gate.sh; check "read-inside" 0 $?

# Test 5: Permissive mode -> always allowed
echo '{"tool_name":"Write","tool_input":{"file_path":"'$TEST_ROOT'/evil.sh"}}' | SYNTHEX_SANDBOX_MODE=permissive bash sandbox-gate.sh; check "permissive" 0 $?

# Test 6: Empty path -> no-op (exit 0)
echo '{"tool_name":"Write","tool_input":{}}' | bash sandbox-gate.sh; check "empty-path" 0 $?

# Test 7: agent-lifecycle-logger writes DB row
echo '{"agent_type":"test-agent","session_id":"abc123"}' | bash agent-lifecycle-logger.sh start
COUNT=$(sqlite3 "$TEST_ROOT/logs/state_ledger.db" "SELECT COUNT(*) FROM state_ledger WHERE event_type='subagent.start'")
[ "$COUNT" -gt 0 ]; check "lifecycle-log" 0 $?

# Test 8: task-tracker writes intents row
echo '{"task_id":"t1","task_title":"demo"}' | bash task-tracker.sh create
COUNT=$(sqlite3 "$TEST_ROOT/logs/intents.db" "SELECT COUNT(*) FROM intents WHERE action='task.create'")
[ "$COUNT" -gt 0 ]; check "task-track" 0 $?

# Test 9: auto-indexer creates queue entry
echo '{"tool_name":"Write","tool_input":{"file_path":"'$TEST_ROOT'/agent-output/readme.md"}}' | bash auto-indexer.sh
[ -f "$TEST_ROOT/logs/index_queue.jsonl" ]; check "auto-index" 0 $?

# Test 10: cwd-based root resolution (no CLAUDE_PROJECT_DIR)
CLAUDE_PROJECT_DIR_SAVED="${CLAUDE_PROJECT_DIR:-}"
unset CLAUDE_PROJECT_DIR
echo '{"agent_type":"cwd-test","cwd":"'"$TEST_ROOT"'"}' | bash agent-lifecycle-logger.sh start
COUNT=$(sqlite3 "$TEST_ROOT/logs/state_ledger.db" "SELECT COUNT(*) FROM state_ledger WHERE agent='cwd-test'")
[ "$COUNT" -gt 0 ]; check "cwd-resolution" 0 $?
CLAUDE_PROJECT_DIR="$CLAUDE_PROJECT_DIR_SAVED"

echo "---"
echo "$PASS passed, $FAIL failed"
rm -rf "$TEST_ROOT"
[ "$FAIL" -eq 0 ] || exit 1
