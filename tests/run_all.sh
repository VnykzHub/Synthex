#!/usr/bin/env bash
# run_all.sh — Synthex master test runner.
# Runs: hooks, frontmatter, memory-graph, archivist, heavy-compute,
# JSON validation, py_compile pass. Exits non-zero if any suite fails.
set -euo pipefail
cd "$(dirname "$0")/.."

PASS=0; FAIL=0
run() {
  local label="$1"; shift
  echo "━━━ $label ━━━"
  if "$@" 2>&1; then
    echo "✔ $label PASSED"; PASS=$((PASS+1))
  else
    echo "✘ $label FAILED"; FAIL=$((FAIL+1))
  fi
  echo
}

run "hook-scripts"        bash -c 'cd hooks/scripts && bash test_hooks.sh'
run "frontmatter"         python -m tests.test_frontmatter
run "memory-graph"        python -m tests.test_memory_graph
run "audit-archivist"     python -m tests.test_archivist
run "heavy-compute"       python -m tests.test_heavy_compute

run "json-configs" python -c "
import json, sys; from pathlib import Path
ok = 0
for f in sorted(Path('.').glob('**/*.json')):
    try:
        json.loads(f.read_text()); ok += 1
    except Exception as e:
        print(f'  FAIL {f}: {e}'); sys.exit(1)
print(f'  {ok} JSON files valid')
"

run "py-compile" python -c "
import compileall, sys
sys.exit(0 if compileall.compile_dir('.', quiet=1, force=True) else 1)
print('  all .py compile OK')
"

echo "═══════════════════════════════════════"
echo "  $PASS passed, $FAIL failed"
echo "═══════════════════════════════════════"
[ "$FAIL" -eq 0 ] || exit 1
