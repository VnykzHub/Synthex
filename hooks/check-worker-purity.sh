#!/usr/bin/env bash
# check-worker-purity.sh — CI gate: ensure worker/gate/command skills don't spawn agents.
# Run from the plugin root. Exits 1 if violations found.
set -euo pipefail
cd "$(dirname "$0")/.."

violations=0
for skill in skills/*/SKILL.md; do
  role=$(grep '^role:' "$skill" 2>/dev/null | head -1 | sed 's/role: //')
  if [ "$role" = "worker" ] || [ "$role" = "gate" ] || [ "$role" = "command" ]; then
    if grep -qE 'spawn|sub-agent|subagent|Task\b.*agent|Agent\b' "$skill" 2>/dev/null; then
      echo "VIOLATION: $skill (role=$role) contains agent-spawning language"
      violations=$((violations + 1))
    fi
  fi
done

if [ "$violations" -gt 0 ]; then
  echo "FAIL: $violations worker/gate/command skills reference agent spawning"
  exit 1
fi
echo "PASS: No worker/gate/command skills reference agent spawning"
exit 0
