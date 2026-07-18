#!/usr/bin/env bash
# test_hooks.sh — comprehensive test harness for Synthex hook scripts.
set -uo pipefail

TEST_ROOT="$(mktemp -d)"
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
SYNTHEX_SANDBOX_MODE=permissive bash sandbox-gate.sh <<< '{"tool_name":"Write","tool_input":{"file_path":"'$TEST_ROOT'/evil.sh"}}'; check "permissive" 0 $?

# Test 6: Empty path -> no-op (exit 0)
echo '{"tool_name":"Write","tool_input":{}}' | bash sandbox-gate.sh; check "empty-path" 0 $?

# Test 7: agent-lifecycle-logger writes DB row
echo '{"agent_type":"test-agent","session_id":"abc123"}' | bash agent-lifecycle-logger.sh start
sqlite3 "$TEST_ROOT/logs/state_ledger.db" "SELECT COUNT(*) FROM state_ledger WHERE event_type='subagent.start'" > /dev/null; check "lifecycle-log" 0 $?

# Test 8: task-tracker writes intents row
echo '{"task_id":"t1","task_title":"demo"}' | bash task-tracker.sh create
sqlite3 "$TEST_ROOT/logs/intents.db" "SELECT COUNT(*) FROM intents WHERE action='task.create'" > /dev/null; check "task-track" 0 $?

# Test 9: auto-indexer creates queue entry
echo '{"tool_name":"Write","tool_input":{"file_path":"'$TEST_ROOT'/agent-output/readme.md"}}' | bash auto-indexer.sh
[ -f "$TEST_ROOT/logs/index_queue.jsonl" ]; check "auto-index" 0 $?

echo "---"
echo "$PASS passed, $FAIL failed"
rm -rf "$TEST_ROOT"
[ "$FAIL" -eq 0 ] || exit 1
