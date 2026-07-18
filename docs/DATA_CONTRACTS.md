# Synthex — Integration Contracts (SINGLE SOURCE OF TRUTH)

Every component (hooks, MCP servers, monitor, `/synthex:synthex-init`) MUST conform
to this file. It exists so independently-built parts stay wire-compatible. If you
change a contract here, update every consumer.

---

## 1. Sandbox path resolution

The runtime data sandbox lives in the **user's project**, not next to the plugin.
Resolve the base once, in this order:

```
SYNTHEX_ROOT = $CLAUDE_PROJECT_DIR  (if set)
             | hook stdin ".cwd"    (hooks only)
             | $PWD
```

Directories under `SYNTHEX_ROOT` (created by `/synthex:synthex-init`):

| Path              | Agent access | Notes                                  |
| :---------------- | :----------- | :------------------------------------- |
| `user-input/`     | READ-ONLY    | assignments/, datasets/, references/   |
| `knowledgebase/`  | READ + WRITE | schemas/, papers/, models/             |
| `agent-output/`   | WRITE-ONLY    | src/, artifacts/, reports/ |
| `logs/`           | system only  | SQLite DBs + vectors/ + archives/      |

> NOTE: `Build_guide.md` used `${CLAUDE_PLUGIN_ROOT}/../` — that only works in
> `--plugin-dir` dev mode. Use `SYNTHEX_ROOT` as above for correctness.

## 2. SQLite schema (in `logs/`)

### `logs/intents.db`
```sql
CREATE TABLE IF NOT EXISTS intents (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  ts        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  agent     TEXT NOT NULL,
  action    TEXT NOT NULL,   -- e.g. 'task.create', 'task.complete', 'decision'
  why       TEXT NOT NULL,   -- the reasoning / intent
  task_id   TEXT,
  context   TEXT             -- JSON blob
);
CREATE TABLE IF NOT EXISTS tasks (
  id          TEXT PRIMARY KEY,     -- uuid4 hex
  title       TEXT NOT NULL,
  priority    TEXT DEFAULT 'medium',-- low|medium|high|critical
  status      TEXT DEFAULT 'pending',-- pending|in-progress|blocked|pr|merged|completed
  assigned_to TEXT,
  created_at  TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  updated_at  TEXT,
  completed_at TEXT
);
```

### `logs/state_ledger.db`
```sql
CREATE TABLE IF NOT EXISTS state_ledger (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  ts         TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  agent      TEXT,
  event_type TEXT,           -- 'subagent.start'|'subagent.stop'|'state.snapshot'|'tool.write'|'experiment.complete'|'theory.analysis'|'pipeline.run'
  details    TEXT            -- JSON blob
);
CREATE TABLE IF NOT EXISTS kg_triples (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  subject   TEXT, predicate TEXT, object TEXT, source TEXT,
  ts        TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

-- Performance indexes for frequently-queried columns
CREATE INDEX IF NOT EXISTS idx_intents_ts       ON intents(ts);
CREATE INDEX IF NOT EXISTS idx_intents_agent    ON intents(agent);
CREATE INDEX IF NOT EXISTS idx_ledger_ts        ON state_ledger(ts);
CREATE INDEX IF NOT EXISTS idx_ledger_agent     ON state_ledger(agent);
CREATE INDEX IF NOT EXISTS idx_ledger_event_type ON state_ledger(event_type);
CREATE INDEX IF NOT EXISTS idx_tasks_status     ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_priority   ON tasks(priority);
```

Timestamps are UTC ISO-8601 with milliseconds, e.g. `2026-07-18T19:45:12.031Z`.

## 3. MCP tool signatures

### server `memory-graph` (Python, FastMCP) -> tools appear as `mcp__plugin_synthex_memory-graph__<tool>`
- `vector_retrieve(query: str, top_k: int = 5) -> list[dict]`
  returns `[{chunk, source, score, ts}]`
- `vector_index(path: str) -> dict` -> `{indexed: <n_chunks>, source: path}`
- `kg_add(subject: str, predicate: str, object: str, source: str = "") -> dict`
- `kg_query(subject: str = "", predicate: str = "", object: str = "") -> list[dict]`
- `lineage_trace(target: str) -> list[dict]` -- `target` is a file path, task_id, or agent name; returns chronological trail of related intents, KG triples, and ledger entries
- `log_intent(agent: str, action: str, why: str, task_id: str = "", context: str = "") -> dict`
- `task_create(title: str, priority: str = "medium", assigned_to: str = "") -> dict` (returns `{id,...}`)
- `task_update(id: str, status: str) -> dict`
- `task_list(status: str = "") -> list[dict]`
- `drain_queue(batch_size: int = 10) -> dict` -- consume the auto-indexer queue (`logs/index_queue.jsonl`) and index pending files; returns `{indexed: n, failed: [...], skipped: [...]}`

The auto-indexer queue (`logs/index_queue.jsonl`) is append-only, one JSON object per line:
```json
{"path": "agent-output/src/pipeline.py", "event": "write", "ts": "2026-07-18T19:45:12.031Z", "size": 4096}
{"path": "knowledgebase/schemas/orders.json", "event": "modify", "ts": "2026-07-18T19:46:01.123Z", "size": 2048}
```
Fields: `path` (sandbox-relative), `event` (write|modify|delete), `ts` (UTC ISO-8601), `size` (bytes). Written by the `PostToolUse` hook `auto-indexer.sh`; consumed by `drain_queue`.

### server `heavy-compute` (Python, FastMCP) -> tools appear as `mcp__plugin_synthex_heavy-compute__<tool>`
- `sympy_solve(expression: str, kind: str = "auto") -> dict` -> `{result, latex, steps}`
- `profile_script(path: str, args: list[str] = []) -> dict` -> `{stdout, stderr, wall_time_s, top_functions}`
- `etl_validate(path: str, expectations: str = "") -> dict` -> `{rows, columns, grain_ok, issues}`
- `docker_run(image: str, cmd: list[str], mounts: list[str] = []) -> dict` (degrade gracefully if docker absent)

### server `visualization` (Node, @modelcontextprotocol/sdk) -> tools appear as `mcp__plugin_synthex_visualization__<tool>`
- `threejs_scaffold(name: str, kind: str = "scene") -> dict` -> `{path: "agent-output/artifacts/<name>.html"}` (writes into `agent-output/artifacts/`)
- `react_component(name: str, spec: str) -> dict` -> `{path: "agent-output/artifacts/<name>.jsx"}`
- `preview_ui(path: str) -> dict` -> `{url_or_html: <file:// URL or inline HTML>}`

All servers resolve the sandbox via `SYNTHEX_ROOT` (section 1). Writes go under `agent-output/` only.
Vector backend chosen by env `SYNTHEX_VECTOR_BACKEND` (default `chroma`; `turbovec` is
now verified -- first choice, fall back to `chroma`, then to a pure-numpy cosine
index if none import).
Embeddings: `sentence-transformers/all-MiniLM-L6-v2` (384-dim); if unavailable, a
deterministic hashing embedder fallback. Chunks <=512 tokens, 20% overlap.

## 4. Hook I/O contract

Hooks read one JSON object on stdin and signal via exit code:
- `.tool_name`, `.tool_input.file_path` / `.tool_input.path` / `.tool_input.command`, `.cwd`, `.session_id`
- Subagent events add agent type; Task events add task fields (log defensively).
- exit 0 = no objection; exit 2 = block (stderr -> Claude). UserPromptSubmit stdout is
  injected as context (or emit `{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"..."}}`).
- Keep `UserPromptSubmit` work under 30s. Never block the user on a slow query -- fail open (exit 0).
