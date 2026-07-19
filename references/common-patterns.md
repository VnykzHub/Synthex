# Synthex Common Patterns

> Standardized boilerplate patterns for use across all Synthex skills. Skills should reference these patterns by name rather than duplicating the full text.

---

## 1. log_intent Pattern

### Contract

Every agent MUST call `log_intent` when starting or completing a significant action. This produces an immutable audit record in the intents ledger.

### Signature

```
log_intent(agent=<string>, action=<string>, why=<string>, context=<string>)
```

### Fields

| Field | Required | Description |
|-------|----------|-------------|
| `agent` | Yes | The agent name matching the skill's `name` frontmatter field |
| `action` | Yes | Dotted-verb describing what was done (e.g., `audit.complete`, `lineage.trace`, `kg.update`) |
| `why` | No | Free-text rationale for the action; defaults to the action description |
| `context` | No | JSON string or structured identifier (e.g., experiment ID, file path) |

### Implementation

**Preferred** -- MCP tool call:

```
mcp__plugin_synthex_memory-graph__log_intent(
  agent="<agent-name>",
  action="<action>",
  why="<rationale>",
  context="<context>"
)
```

**Fallback** -- direct SQLite insert (when MCP is unavailable):

```bash
# Escape single quotes for SQLite to prevent injection
WHY_ESC="$(printf '%s' "$WHY" | sed "s/'/''/g")"
CTX_ESC="$(printf '%s' "$CTX" | sed "s/'/''/g")"
sqlite3 "$SYNTHEX_ROOT/logs/intents.db" \
  "INSERT INTO intents (agent, action, why, context) VALUES ('<agent-name>', '<action>', '$WHY_ESC', '$CTX_ESC');"
```

### Enforcement

- The Preconditions section of every skill that uses `log_intent` MUST verify MCP availability before falling back to SQLite.
- Every `log_intent` call MUST include at minimum `agent` and `action` fields.

---

## 2. MCP Health Check

### Contract

Before using any MCP server, verify it is reachable. This prevents hard-to-diagnose failures mid-operation.

### Pattern

```bash
# Lightweight MCP health check
if ! mcp__plugin_<server>__<ping_or_lightweight_method> <args> 2>/dev/null; then
  echo "WARNING: <server> MCP unreachable. Falling back to local: <fallback_description>."
  # execute fallback logic
fi
```

### When the MCP provides no explicit health-check tool

Use a no-op query with a known result instead:

```bash
# Verify by running an inexpensive query with predictable output
if ! RESULT=$(mcp__plugin_synthex_memory-graph__kg_query(subject="", predicate="", object="") 2>/dev/null); then
  echo "WARNING: memory-graph MCP unreachable. Falling back to SQLite."
fi
```

### Per-skill fallback table

| MCP Server | Primary Tool(s) | Fallback |
|-----------|----------------|----------|
| `memory-graph` | `vector_retrieve`, `kg_query`, `kg_add`, `log_intent`, `lineage_trace` | `sqlite3` on `logs/state_ledger.db` or `logs/intents.db` |
| `visualization` | `react_component`, `preview_ui`, `threejs_scaffold` | Local CLI tools (weasyprint, pandoc) or standalone HTML generation |
| `heavy-compute` | `etl_validate`, `profile_script`, `docker_run` | Local `python3` execution |

### Enforcement

Every skill with MCP dependencies MUST include:
1. A precondition checking MCP availability
2. A documented fallback strategy
3. A warning emitted when falling back

---

## 3. Output Format Conventions

### 3.1 Work-Plan YAML

Standard output format for orchestrator skills that decompose tasks for the PI:

```yaml
work_plan:
  metadata:
    generated_by: <skill-name>
    timestamp: <ISO-8601>
    source_task: "<original task description>"
  tasks:
    - id: "<unique-task-id>"
      skill: "<skill-to-invoke>"
      input: "<input-spec>"
      depends_on: []
    - id: "<unique-task-id>"
      skill: "<skill-to-invoke>"
      input: "<input-spec>"
      depends_on: ["<previous-task-id>"]
  parallel_groups:
    - ["<task-id>", "<task-id>"]
```

### 3.2 Error Report YAML

Standard format for reporting operation failures:

```yaml
error_report:
  operation: "<operation-name>"
  status: failed
  timestamp: <ISO-8601>
  failures:
    - step: "<step-identifier>"
      severity: fatal | error | warning
      message: "<human-readable message>"
      suggestion: "<remediation or next step>"
  partial_outputs:
    - path: "<path-to-partial-results>"
      description: "<what was completed before failure>"
```

### 3.3 Status Update YAML

Standard format for periodic or final status reporting:

```yaml
status:
  operation: "<operation-name>"
  state: running | completed | failed | partial
  progress:
    completed: <integer>
    total: <integer>
  current_step: "<step-identifier>"
  started_at: <ISO-8601>
  last_updated: <ISO-8601>
  output_location: "<path-to-output>"
  errors:
    - "<any errors encountered>"
```

### Conventions

- All timestamps MUST be ISO-8601 with timezone (e.g., `2026-07-19T14:30:00Z`).
- All file paths MUST be relative to `SYNTHEX_ROOT` or absolute.
- All YAML files MUST use 2-space indentation.
- Empty fields should use `null` (not `""` or absent).
- Multi-line strings should use `|` (literal block scalar).
