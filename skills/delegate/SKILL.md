---
name: delegate
description: "/synthex:delegate -- Send a task to the Principal Investigator (PI) for decomposition, context retrieval from vector store, sub-agent assignment, and roadmap tracking. Use when the user runs /synthex:delegate to hand a task to the Principal Investigator for decomposition and execution."
disable-model-invocation: true
allowed-tools: Bash(sqlite3 *) Bash(echo *) Bash(mkdir *) Bash(find *)
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

## Step 7 -- Summarize

Report back to the user: what $ARGUMENTS was decomposed into, which agents were assigned, and where to track progress (`agent-output/artifacts/roadmap.md`).
