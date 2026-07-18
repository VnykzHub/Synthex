# Synthex

Enterprise multi-agent operating framework for Claude Code. A zero-write sandbox, a PI-led hierarchy of 10 specialist agents, three MCP servers (Heavy Compute, Memory & Graph, Visualization), a vector Memory Vault, and an always-on audit daemon — so no analytical trail is ever lost.

---

## Why Synthex

Claude Code is powerful but stateless: past decisions, mid-session reasoning, and the *why* behind every change evaporate the moment a session ends. Synthex wraps Claude Code in a disciplined operating framework that:

| Without Synthex | With Synthex |
|---|---|
| Agents forget past decisions within 3 turns | Memory Vault auto-injects relevant context before every task |
| No enforcement of where agents read/write | Zero-write sandbox — agents can't touch your source unless you place it in `user-input/` |
| Manual coordination of multi-agent work | PI decomposes, spawns specialists, verifies outputs, merges — autonomously |
| No audit trail for decisions | Every tool call, subagent lifecycle, and task decision is logged to SQLite |
| No persistent semantic search | `vector_retrieve` finds relevant past work by meaning, not filename |
| One-size-fits-all agent | 10 domain-specific agents (Methodologist, Data Engineer, Research Scientist, etc.) with pre-loaded skills |

**Use Synthex when you have:** multi-step software/data/research tasks, complex pipelines, mathematical proofs, experiments, or any work where you need traceability and structured output. **Skip it** for quick one-shot questions or single-file edits — Synthex's scaffolding overhead isn't worth it there.

---

## Installation

### Quickstart: load directly (development)

```bash
# Clone or copy the plugin directory, then:
claude --plugin-dir ./synthex-plugin
```

Skills load as `/synthex:<name>`, agents @-mention as `synthex:<agent>`, and bundled MCP tools appear as `mcp__plugin_synthex_<server>__<tool>`.

To pick up edits without restarting:

```
/reload-plugins
```

### From a marketplace (once published)

```
/plugin marketplace add <marketplace-url>
/plugin install synthex@<marketplace-name>
```

### Requirements

- Claude Code v2.1+ (hooks, plugins, custom agents)
- Python 3.12 (for the Memory & Graph and Heavy Compute MCP servers; falls back to zero-dep hashing mode if optional packages are absent)
- Node 20+ (for the Visualization MCP server)
- Docker (optional — only needed for the `docker_run` heavy-compute tool)
- `sqlite3` and `jq` available on `$PATH` (for hook scripts)

No Python packages are required at install time — the Memory Vault degrades gracefully through three tiers: chromadb → numpy cosine → pure-Python cosine. The hashing embedder has zero dependencies.

---

## Getting started

Every Synthex project begins with `/synthex:synthex-init`. This scaffolds the runtime data sandbox in your project root and initializes two SQLite databases with the full schema.

### 1. Initialize the sandbox

```
/synthex:synthex-init
```

This creates the following directory tree **in your project** (alongside your existing source, not inside the plugin):

```
your-project/
├── user-input/                 # You drop files here. Agents can only READ.
│   ├── assignments/            # Task briefs, research questions, specs
│   ├── datasets/               # Raw CSV, JSON, binary data
│   └── references/             # Configs, API docs, style guides
│
├── knowledgebase/              # Shared reference. Agents can READ + WRITE.
│   ├── schemas/                # Database schemas, OpenAPI specs
│   ├── papers/                 # PDF research papers, proofs
│   └── models/                 # Trained ML weights, embeddings
│
├── agent-output/               # All agent work lands here. The ONLY writable zone.
│   ├── src/                    # Production code (Python, Rust, TypeScript…)
│   ├── artifacts/              # Plots, 3D scenes, binaries
│   └── reports/                # LaTeX PDFs, PPTX, HTML dashboards
│
└── logs/                       # System ledger. Agents can't write here directly.
    ├── intents.db              # SQLite: the "why" behind every decision
    ├── state_ledger.db         # SQLite: subagent lifecycles, state snapshots, KG triples
    ├── vectors/                # Vector index files (Memory Vault)
    └── archives/               # Historical quarterly logs
```

### 2. Drop your assignment

Place a task brief in `user-input/assignments/`. Any format works — Markdown, plain text, YAML. For example:

```markdown
# user-input/assignments/order_pipeline.md
Build an ETL pipeline that ingests customer orders from CSV,
validates against the product schema, deduplicates on order_id,
and writes a clean Parquet snapshot to agent-output/artifacts/.
```

### 3. Delegate

```
/synthex:delegate Build the order pipeline described in user-input/assignments/order_pipeline.md
```

The PI queries the Memory Vault for relevant past context, decomposes the assignment into subtasks, spawns the right specialists, verifies each output, and merges everything into `agent-output/`. You can watch progress with `/synthex:status` and get the final audit with `/synthex:audit`.

### 4. Check results

```
/synthex:status          # live task board from intents.db
/synthex:memory "order deduplication strategy"  # search past decisions
/synthex:report --type html                      # synthesize a report
/synthex:audit                                    # full chronological audit
```

---

## Command reference

All commands are namespaced under `/synthex:`. Each is a skill Claude executes step-by-step.

### `/synthex:synthex-init`

Scaffold the runtime sandbox. Call once per project.

```
/synthex:synthex-init
```

Creates all directories, initializes `logs/intents.db` (intents + tasks tables) and `logs/state_ledger.db` (state_ledger + kg_triples tables) with the full schema, and confirms what was created. Idempotent — safe to re-run.

### `/synthex:delegate "<task>"`

Send a task to the Principal Investigator.

```
/synthex:delegate "Audit the authentication module for timing side-channels"
```

The PI: queries `vector_retrieve` for relevant memory → decomposes into subtasks → spawns the appropriate specialists → verifies outputs → writes a roadmap to `agent-output/artifacts/roadmap.md` → updates task status via `log_intent`.

### `/synthex:status`

Display all active tasks as a Markdown table.

```
/synthex:status
```

Reads the `tasks` table from `logs/intents.db` and renders id, title, status, assigned agent, and creation date. Filter by status with additional arguments (implementation-specific).

### `/synthex:theory`

Launch the Methodologist for formal analysis.

```
/synthex:theory "Prove the time complexity of the chained-hash deduplication in agent-output/src/dedup.py"
```

Surveys `user-input/` for LaTeX proofs, performs asymptotic complexity analysis, and verifies results via `sympy_solve` in the Heavy Compute MCP. Output lands in `agent-output/reports/theory_analysis.md`.

### `/synthex:pipeline --script=<file>`

Run an ETL or ML workload in the Heavy Compute sandbox.

```
/synthex:pipeline --script=user-input/datasets/etl_orders.py
```

The Automation or Data Engineer runs the script through `etl_validate`, `profile_script`, and optionally `docker_run`. Input from `user-input/datasets/`, output to `agent-output/artifacts/`.

### `/synthex:experiment`

Full experiment lifecycle: design → run → compare → report.

```
/synthex:experiment "Does the new caching layer reduce p99 latency by ≥20%?"
```

The Research Scientist uses the `experiment-design` skill to formulate hypothesis/null/alternative, define control/treatment groups, run power analysis (α=0.05, β=0.20), execute via heavy-compute `profile_script`, and produce a comparison report. Output: `agent-output/reports/experiment_<name>/`.

### `/synthex:report --type <ppt|html|pdf>`

Synthesize deliverables from accumulated outputs.

```
/synthex:report --type pdf
```

The Documentation Engineer gathers content from `agent-output/reports/`, `agent-output/artifacts/`, and the knowledge graph, then produces the requested format using the `presentation`, `whitepaper`, and `3d-modeling` skills, plus the Visualization MCP for interactive elements.

### `/synthex:audit`

Compile a full chronological audit report.

```
/synthex:audit
```

Reads both `logs/state_ledger.db` (subagent lifecycles, state snapshots) and `logs/intents.db` (decisions, task history, KG triples) and produces a Markdown timeline with event counts and recent graph additions. Output: `agent-output/reports/audit_<date>.md`.

### `/synthex:memory "<query>"`

Manually query the Memory Vault.

```
/synthex:memory "Fourier transform numerical stability"
```

Calls the Memory & Graph MCP's `vector_retrieve` and displays the top 5 chunks with source path, relevance score, and timestamp. Falls back to the `synthex_memory.py` CLI if the MCP server isn't running.

---

## The agent hierarchy

Synthex organizes 10 specialist subagents into three divisions under the PI. Each agent has a defined model tier, tool set, and skills. Mention them with `@synthex:<agent-name>` or let the PI assign them automatically.

```
  ┌──────────────────────────────────────┐
  │   Principal Investigator (Opus)      │
  │   Decomposes → Spawns → Verifies     │
  └──────────────────┬───────────────────┘
      ┌──────────────┼──────────────┐
      ▼              ▼              ▼
┌───────────┐  ┌───────────┐  ┌───────────┐
│ Research  │  │Engineering│  │   Audit   │
│ Division  │  │ Division  │  │ Division  │
└───────────┘  └───────────┘  └───────────┘
```

### Research Division (analytical rigor)

| Agent | Model | Use when… |
|---|---|---|
| **Research Scientist** | Sonnet | You need a hypothesis, an experiment design, or an A/B test planned |
| **Methodologist** | Sonnet | You need asymptotic bounds, numerical-stability analysis, or SymPy verification |
| **Algorithm Engineer** | Sonnet | You need a non-trivial algorithm implemented with attention to complexity, memory layout, and vectorization |
| **Research Assistant** | Haiku | You have a precisely scoped, self-contained subtask (labeling, baselines, lookups) |

### Engineering Division (production output)

| Agent | Model | Use when… |
|---|---|---|
| **Data Engineer** | Sonnet | Data must be profiled, cleaned, schema-validated, or traced end-to-end before pipeline work |
| **Software Engineer** | Sonnet | The deliverable is production backend code, an API, or a CLI tool — must be correct, tested, and maintainable |
| **Automation Engineer** | Sonnet | A pipeline needs to be assembled, containerized, benchmarked, or executed with monitoring |
| **Frontend / 3D Engineer** | Sonnet | The deliverable needs a React/Vue UI, a data dashboard, or an interactive Three.js 3D scene |

### Audit Division (traceability)

| Agent | Model | Use when… |
|---|---|---|
| **Audit Archivist** | Monitor (daemon) | Runs in the background automatically — snapshots system state every N seconds, writes telemetry to `logs/state_ledger.db` |
| **Documentation Engineer** | Haiku | Findings must be compiled into a polished, human-readable deliverable (whitepaper, slide deck, HTML dashboard) |

---

## Domain skills

These 9 skills are **model-invoked** — Claude auto-selects them when the task context matches. You don't need to call them explicitly.

| Skill | Triggers when… | Primary consumer |
|---|---|---|
| `task-tracking` | Tasks are created, updated, blocked, or completed | All agents |
| `knowledge-graph` | Codebase structure, dependencies, or relationships need mapping | PI, all agents |
| `data-lineage` | ETL pipelines, schema changes, or data flow need documenting | Data Engineer |
| `experiment-design` | A hypothesis needs formal design (A/B test, control groups, power analysis) | Research Scientist |
| `frontend-dev` | React/Vue components, state management, or client-side UI work | Frontend Engineer |
| `3d-modeling` | Three.js scenes, WebGL rendering, procedural geometry | Frontend Engineer |
| `presentation` | A slide deck or pitch from results and reports is needed | Documentation Engineer |
| `whitepaper` | An IEEE/ACM-structured technical paper or report is needed | Documentation Engineer |
| `prototyping` | Fast Flask/Streamlit scaffolding for a proof-of-concept | Software Engineer, Research Assistant |

---

## The sandbox: what goes where

The sandbox enforces a strict separation enforced by `sandbox-gate.sh` (a `PreToolUse` hook that exits 2 to block out-of-zone reads and writes):

| Zone | Agent access | Purpose |
|---|---|---|
| `user-input/` | **Read-only** | Your raw materials — assignments, datasets, references. Agents can read but never modify. |
| `knowledgebase/` | Read + Write | Shared reference — schemas, papers, models. Both you and agents maintain this. |
| `agent-output/` | **Write-only** (the sole writable zone) | All agent work products. Code, artifacts, reports. |
| `logs/` | System only | SQLite DBs, vector index, archives. Agents never write here directly — hooks and monitors do. |

**Permissive mode:** set `SYNTHEX_SANDBOX_MODE=permissive` in your environment to disable the sandbox gate (for development or trusted workflows).

---

## MCP servers

Three bundled MCP servers provide computation, memory, and visualization. All start automatically when the plugin is active.

### Memory & Graph (`mcp__plugin_synthex_memory-graph__*`)

The Memory Vault. Backed by SQLite (`intents.db`, `state_ledger.db`) and a vector store (chroma → numpy cosine → pure-Python cosine fallback, zero-dependency capable).

| Tool | Purpose |
|---|---|
| `vector_retrieve` | Semantic search across all indexed documents |
| `vector_index` | Index a file into the vector store |
| `kg_add` | Add a subject-predicate-object triple to the knowledge graph |
| `kg_query` | Query the knowledge graph with LIKE filters |
| `lineage_trace` | Trace data lineage across intents and KG triples |
| `log_intent` | Record an agent decision ("why") in `intents.db` |
| `task_create` | Create a task with priority and assignment |
| `task_update` | Update task status |
| `task_list` | List tasks, optionally filtered by status |
| `drain_queue` | Consume the auto-indexer queue and index pending files |

### Heavy Compute (`mcp__plugin_synthex_heavy-compute__*`)

Isolated computation in Docker containers (or local Python). Requires `sympy`; `pandas` and Docker are optional.

| Tool | Purpose |
|---|---|
| `sympy_solve` | Symbolic math: solve, simplify, integrate, differentiate, factor |
| `profile_script` | Run a Python script under cProfile and report top functions |
| `etl_validate` | Validate a CSV: row count, columns, grain uniqueness, issues |
| `docker_run` | Run a command in a Docker container with volume mounts (degrades gracefully if Docker is absent) |

### Visualization (`mcp__plugin_synthex_visualization__*`)

Node.js server for generating UIs, 3D scenes, and component scaffolds.

| Tool | Purpose |
|---|---|
| `threejs_scaffold` | Write a self-contained Three.js HTML scene to `agent-output/artifacts/<name>.html` |
| `react_component` | Scaffold a React JSX component from a spec to `agent-output/artifacts/<name>.jsx` |
| `preview_ui` | Return a `file://` URL for an artifact under `agent-output/` |

---

## Architecture

```
User prompt
    │
    ▼
┌──────────────────────────────────────┐
│ UserPromptSubmit hook                │
│ memory-injector.sh → top-3 chunks    │  ← Memory Vault (auto-injection)
│ (fail-open, <5s timeout)             │
└──────────────┬───────────────────────┘
               │
    ┌──────────▼──────────┐
    │  Principal          │
    │  Investigator (PI)  │  ← /synthex:delegate
    └──────────┬──────────┘
               │ spawns
    ┌──────────┼──────────┐
    ▼          ▼          ▼
 Research  Engineering  Audit
 Division   Division    Division
    │          │          │
    └──────────┼──────────┘
               │
    ┌──────────▼──────────┐
    │  PreToolUse hook     │
    │  sandbox-gate.sh     │  ← blocks out-of-zone reads/writes (exit 2)
    │  (every tool call)   │
    └──────────┬──────────┘
               │
    ┌──────────▼──────────┐
    │  PostToolUse hook    │
    │  auto-indexer.sh     │  ← queues new/modified files for vector indexing
    └──────────────────────┘
               │
    ┌──────────▼──────────┐
    │  Audit Archivist     │
    │  (background daemon) │  ← snapshots state every 300s → state_ledger.db
    └──────────────────────┘
```

Hooks drive the lifecycle: `sandbox-gate.sh` enforces the sandbox before every tool call, `auto-indexer.sh` queues files after every write, `memory-injector.sh` injects context before every prompt, and the audit archivist writes telemetry in the background.

---

## Developing Synthex itself

### Project layout

```
synthex-plugin/
├── .claude-plugin/plugin.json   # manifest (name, version, MCP servers, userConfig)
├── .mcp.json                    # 3 bundled MCP server definitions
├── hooks/
│   ├── hooks.json               # PreToolUse·PostToolUse·UserPromptSubmit·Subagent*·Task*
│   └── scripts/                 # 6 executable scripts + test harness
├── agents/                      # 10 subagent .md definitions
├── skills/                      # 9 domain skills + 9 command skills (each <name>/SKILL.md)
├── mcp-servers/
│   ├── memory-graph/            # FastMCP + CLI library (synthex_memory.py)
│   ├── heavy-compute/           # FastMCP + Dockerfile
│   └── visualization/           # Node MCP (@modelcontextprotocol/sdk)
├── monitors/
│   ├── monitors.json            # audit-archivist daemon definition
│   └── audit-archivist/         # archivist.py monitor
├── docs/DATA_CONTRACTS.md       # binding integration contract
├── BUILD_PLAN.md                # micro-task breakdown + dependency graph
└── README.md                    # this file
```

**Important structural rule:** `.claude-plugin/` contains only `plugin.json`. All component directories (`skills/`, `agents/`, `hooks/`, `mcp-servers/`, `monitors/`) live at the plugin root — **not** nested inside `.claude-plugin/`. This is a Claude Code requirement.

### Development loop

```bash
# Load the plugin for one session
claude --plugin-dir ./synthex-plugin

# Pick up edits without restarting
/reload-plugins

# Validate structure (requires auth)
claude plugin validate ./synthex-plugin
```

### Smoke tests

```bash
# Hook tests (requires bash, jq, sqlite3)
cd hooks/scripts && bash test_hooks.sh          # 9 tests — should all pass

# Memory Vault tests (zero external deps)
cd mcp-servers/memory-graph
python -m py_compile synthex_memory.py server.py  # must exit 0
export CLAUDE_PROJECT_DIR=$(mktemp -d)
python synthex_memory.py selftest                 # init → index → retrieve → task CRUD

# Heavy Compute tests (requires sympy)
cd mcp-servers/heavy-compute
python -m py_compile server.py                    # must exit 0
python server.py --selftest                       # sympy_solve('x**2-4', 'solve') → [-2, 2]

# Visualization tests
node --check mcp-servers/visualization/server.js  # must exit 0
```

### CI

`.github/workflows/validate.yml` runs on push/PR: validates all JSON files, byte-compiles all Python, syntax-checks all Node, and runs `claude plugin validate` (best-effort, non-fatal without auth).

---

## Configuration

Synthex exposes three user-configurable options via `plugin.json` → `userConfig`:

| Setting | Values | Default | Effect |
|---|---|---|---|
| `sandbox_mode` | `strict`, `permissive` | `strict` | `strict` blocks all writes outside `agent-output/` |
| `vector_db_backend` | `chroma`, `lancedb`, `faiss`, `turbovec` | `chroma` | Memory Vault backend. `turbovec` is unverified — falls back to `chroma` |
| `max_context_chunks` | 1–10 | 3 | Number of memory chunks injected via `UserPromptSubmit` |

Configure them when enabling the plugin, or via environment variables: `SYNTHEX_SANDBOX_MODE`, `SYNTHEX_VECTOR_BACKEND`, `SYNTHEX_ARCHIVIST_INTERVAL` (seconds, default 300).

---

## Troubleshooting

**Plugin doesn't load:**
- Verify directory structure: are `skills/`, `agents/`, `hooks/` at the plugin root (not inside `.claude-plugin/`)?
- Run `claude plugin validate ./synthex-plugin` and fix reported issues.
- Check that all JSON configs are valid: `python -c "import json; json.load(open('.claude-plugin/plugin.json'))"`

**Hook not firing:**
- Run `/hooks` in Claude Code and confirm the hook appears under the correct event.
- Test the script manually: pipe sample JSON to it and check the exit code.
- Ensure scripts are executable: `chmod +x hooks/scripts/*.sh`

**Sandbox gate blocking legit writes:**
- Verify the file path is under `<project>/agent-output/`.
- Set `SYNTHEX_SANDBOX_MODE=permissive` to disable enforcement temporarily.
- Check that `CLAUDE_PROJECT_DIR` is set correctly for your project.

**Memory Vault returns no results:**
- Run `/synthex:synthex-init` to ensure the DBs exist.
- Index some content: `python mcp-servers/memory-graph/synthex_memory.py index <file>`.
- Verify: `python mcp-servers/memory-graph/synthex_memory.py retrieve --query "test"`.
- The hashing embedder (fallback) produces deterministic but lower-quality vectors than sentence-transformers. Install `sentence-transformers` for semantic-quality retrieval.

**MCP servers don't start:**
- Memory & Graph: requires `python3` on `$PATH`. No Python packages required at baseline.
- Heavy Compute: requires `python3` + `sympy`. Docker is optional.
- Visualization: requires `node` on `$PATH`. The `@modelcontextprotocol/sdk` package must be installed: `cd mcp-servers/visualization && npm install`.
