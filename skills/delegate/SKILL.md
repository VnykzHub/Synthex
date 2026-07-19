---
name: delegate
description: "/synthex:delegate — Send task to PI for decomposition, context, agent assignment. Use when running /synthex:delegate."
aliases: [assign, hand-off, dispatch, route]
role: orchestrator
disable-model-invocation: true
allowed-tools: Bash(sqlite3 *) Bash(echo *) Bash(mkdir *) Bash(find *)
related_skills: [task-tracking, knowledge-graph, task-orchestrator]
---

> **⚠ Orchestration entry point:** this skill coordinates multiple agents and tools rather than performing a single atomic task. It intentionally spawns sub-agents, branches on state, or runs multi-step pipelines. See BUILD_PLAN.md Phase 17, Rec 3 for design rationale.

# /synthex:delegate -- PI orchestration: retrieve context, decompose, spawn, track

$ARGUMENTS is the raw task description from the user.

## Step 1 -- Resolve SYNTHEX_ROOT

```
SYNTHEX_ROOT = $CLAUDE_PROJECT_DIR  (if set)  else $PWD
```

## Step 2 -- Retrieve context from Memory Vault

Call the memory-graph MCP to surface relevant context before decomposing:

- `mcp__plugin_synthex_memory-graph__vector_retrieve(query="$ARGUMENTS", top_k=5, scope="all")`
- Optionally `kg_query` for related entities if the result set is sparse.

Incorporate the retrieved chunks into your understanding of the task.

## Step 3 -- Log intent

Run the `log_intent` MCP tool (preferred) or insert directly into intents.db. If using raw SQL, escape single quotes first:

```bash
# Escape single quotes for SQLite to prevent injection
ARGUMENTS_ESC="$(printf '%s' "$ARGUMENTS" | sed "s/'/''/g")"
sqlite3 "$SYNTHEX_ROOT/logs/intents.db" \
  "INSERT INTO intents (agent, action, why, context) VALUES ('PI', 'task.delegate', '$ARGUMENTS_ESC', '{}');"
```

## Step 4 -- Decompose into subtasks

Break $ARGUMENTS into concrete subtasks. For each subtask create a task record. Always escape single quotes in the title before inserting:

```bash
TASK_ID=$(uuidgen 2>/dev/null || python3 -c "import uuid; print(uuid.uuid4().hex)")
TITLE_ESC="$(printf '%s' '<subtask-title>' | sed "s/'/''/g")"
sqlite3 "$SYNTHEX_ROOT/logs/intents.db" \
  "INSERT INTO tasks (id, title, priority, status, assigned_to) VALUES ('$TASK_ID', '$TITLE_ESC', 'medium', 'pending', '<agent-name>');"
```

Assign to agents based on the task domain:
- **methodologist** for mathematical / theoretical work
- **automation-engineer** or **data-engineer** for ETL / pipeline work
- **documentation-engineer** for report / visualization work
- **research-scientist** for experiment design and execution

## Step 5 -- Maintain roadmap

Ensure `agent-output/artifacts/roadmap.md` exists and append or update it:

```markdown
# Synthex Roadmap
Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)

## Task: $ARGUMENTS

| Subtask | Agent | Status | Task ID |
| :------ | :---- | :----- | :------ |
| ...     | ...   | pending | <id>   |
```

## Step 6 -- Spawn sub-agents

For each subtask, delegate to the appropriate sub-agent using the Agent tool, passing the task context and task ID so results can be correlated back to the roadmap.

## Output Format — Work Plan

Instead of directly spawning sub-agents in Step 6, this skill **emits a structured work-plan YAML** that the PI agent reads and executes. The PI is the sole entity that spawns agents from this plan.

```yaml
work_plan:
  tasks:
    - id: "delegate-retrieval"
      skill: "memory"
      input: "$ARGUMENTS"
      depends_on: []
    - id: "delegate-subtask-1"
      skill: "<domain-skill>"
      input: "<subtask-path>"
      depends_on: ["delegate-retrieval"]
    - id: "delegate-subtask-2"
      skill: "<domain-skill>"
      input: "<subtask-path>"
      depends_on: ["delegate-retrieval"]
    - id: "delegate-subtask-3"
      skill: "<domain-skill>"
      input: "<subtask-path>"
      depends_on: ["delegate-retrieval"]
  parallel_groups:
    - ["delegate-subtask-1", "delegate-subtask-2", "delegate-subtask-3"]
```

The decomposed subtasks from Step 4 populate the task list. Each task references a concrete skill and input path. Tasks with no inter-dependency run in parallel within the same group.

## Compact Mode
When invoked with `--compact` or when the calling agent already knows the methodology:
skip the "Core principles" and background sections. Use only the checklist, specific instructions, and output format.
Token budget in compact mode: ~500 tokens.

## Preconditions

- **Sandbox check:** Verify `SYNTHEX_ROOT` is set and `agent-output/` exists and is writable. Use: `test -d "$SYNTHEX_ROOT/agent-output" && test -w "$SYNTHEX_ROOT/agent-output" || { echo "agent-output/ not writable"; exit 1; }`
- **MCP availability:** This skill depends on the `memory-graph` MCP for `vector_retrieve`, `kg_query`, and `log_intent`. Verify with a lightweight query before proceeding. If unreachable, fall back to CLI tools (`sqlite3` on `logs/intents.db`).
- **Input existence:** Check that `logs/intents.db` exists and is accessible for task tracking. Report if missing and suggest initialization.
- If any precondition fails, report which one failed and stop -- do not proceed with partial preconditions.

## Error Recovery

- **Missing prerequisite:** If a required tool or dependency is unavailable, report it clearly with the exact command to install or path to check. Do not silently skip.
- **Malformed input:** Validate key fields before processing. On failure, report the exact field name and expected format. Do not proceed with partial data.
- **Timeout:** Set a 30-second budget for any blocking operation (MCP call, script execution, DB query). If exceeded, write partial results to `agent-output/partial/` and note what completed vs. what timed out.
- **Empty result:** If no data matches the query, produce a valid empty output (not an error) with a note explaining the search scope and suggesting next steps.
- **Partial failure:** If some sub-tasks succeed and others fail, report the split clearly: which succeeded, which failed, and whether the successes are usable independently.

## Step 7 -- Summarize

Report back to the user: what $ARGUMENTS was decomposed into, which agents were assigned, and where to track progress (`agent-output/artifacts/roadmap.md`).

## Common Mistakes

- **Delegating without context retrieval.** Sending a task to a sub-agent without first retrieving relevant context from the Memory Vault forces the sub-agent to rediscover what is already known. Always call vector_retrieve before decomposing the task.
- **Over-decomposing trivial tasks.** Breaking a 2-minute task into 5 subtasks with dependencies adds overhead with zero benefit. Use direct delegation for simple tasks; reserve decomposition for tasks with at least 3 distinct domains or steps.
- **Forgetting to update the roadmap.** After spawning sub-agents, failing to update `roadmap.md` means the PI loses visibility into what is running, who owns it, and what is blocked. The roadmap must be updated immediately after task creation.

## Verification
After producing output, verify correctness before declaring done:
1. **Task record completeness:** Verify that every subtask has a valid task ID, title, priority, assigned_to, and status in the `tasks` table. Run a SELECT query and confirm no row has NULL in required fields.
2. **Roadmap consistency:** Confirm that `agent-output/artifacts/roadmap.md` reflects every task in the work plan. Cross-reference task IDs between the roadmap and the database. Flag any mismatches.
3. **Self-check:** Re-read the output against the requirements. Does it address every item in the task brief? Are all referenced paths valid? Are all YAML/JSON blocks syntactically valid?
