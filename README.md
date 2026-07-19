# Synthex v2.0.0

Enterprise-grade multi-agent operating framework for Claude Code — pipeline orchestration, continuous research loop, 24 specialist agents, 41 skills, 22 commands, three MCP servers, a 4-tier vector Memory Vault, zero-write sandbox, and always-on audit daemon. No analytical trail is ever lost.

---

## Why Synthex

Claude Code is powerful but stateless: past decisions, mid-session reasoning, and the *why* behind every change evaporate the moment a session ends. Synthex wraps Claude Code in a disciplined operating framework:

| Without Synthex | With Synthex |
|---|---|
| Agents forget past decisions within 3 turns | Memory Vault (turbovec→chroma→numpy→pure-cosine) auto-injects relevant context before every task |
| No enforcement of where agents read/write | Zero-write sandbox — agents can't touch your source unless you place it in `user-input/` |
| Manual coordination of multi-agent work | Pipeline Director orchestrates 5-phase execution (Research→Planning→Implementation→Review→Validation) with 24 specialist agents |
| No audit trail for decisions | Every tool call, subagent lifecycle, and task decision is logged to SQLite |
| No persistent semantic search | `vector_retrieve` finds relevant past work by meaning, not filename |
| One-off experiments with no iteration | Continuous research loop: literature→hypothesis→experiment→reflect→iterate, with autonomous mode |
| One-size-fits-all agent | 24 domain-specific agents across 7 divisions with 41 pre-loaded skills |

**Use Synthex when you have:** multi-phase projects, complex research questions, ETL/ML pipelines, mathematical proofs, experiments requiring iteration, or any work needing traceability and structured output. **Skip it** for quick one-shot questions or single-file edits — Synthex's scaffolding overhead isn't worth it there.

---

## Installation

### Quickstart: load directly (development)

```bash
claude --plugin-dir ./synthex-plugin
```

Skills load as `/synthex:<name>`, agents @-mention as `synthex:<agent>`, and bundled MCP tools appear as `mcp__plugin_synthex_<server>__<tool>`.

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
- Python 3.12 (for Memory & Graph and Heavy Compute MCP servers)
- Node 20+ (for the Visualization MCP server)
- Docker (optional — only needed for `docker_run` heavy-compute tool)
- `sqlite3` and `jq` available on `$PATH` (for hook scripts)

No Python packages are required at install time — the Memory Vault degrades gracefully through four tiers: `turbovec` → `chromadb` → `numpy cosine` → `pure-Python cosine`. The hashing embedder has zero dependencies. `turbovec` is a verified, installable PyPI package (`pip install turbovec`, `IdMapIndex` with 4-bit ICLR 2026 quantization) that provides the fastest path.

---

## Getting started

### 1. Initialize the sandbox

```
/synthex:synthex-init
```

Creates the runtime data sandbox in your project root:

```
your-project/
├── user-input/                 # READ-ONLY to agents
│   ├── assignments/            # Task briefs, research questions
│   ├── datasets/               # Raw CSV, JSON, binary data
│   └── references/             # Configs, API docs, style guides
├── knowledgebase/              # READ + WRITE
│   ├── schemas/                # Database schemas, OpenAPI specs
│   ├── papers/                 # PDF research papers, proofs
│   └── models/                 # Trained ML weights, embeddings
├── agent-output/               # Agents read past output and write new results here
│   ├── src/                    # Production code
│   ├── artifacts/              # Plots, 3D scenes, pipeline state, ADRs
│   └── reports/                # LaTeX PDFs, PPTX, HTML dashboards
└── logs/                       # System ledger (agents can't write here directly)
    ├── intents.db              # The "why" behind every decision + tasks table
    ├── state_ledger.db         # Subagent lifecycles, state snapshots, KG triples
    ├── vectors/                # Vector index files (Memory Vault)
    └── archives/               # Historical quarterly logs
```

### 2. Drop your assignment

Place a task brief in `user-input/assignments/`. Any format — Markdown, plain text, YAML:

```markdown
# user-input/assignments/order_pipeline.md
Build an ETL pipeline that ingests customer orders from CSV,
validates against the product schema, deduplicates on order_id,
and writes a clean Parquet snapshot to agent-output/artifacts/.
```

### 3. Delegate or launch a pipeline

```
/synthex:delegate Build the order pipeline described in user-input/assignments/order_pipeline.md
```

The PI queries the Memory Vault for relevant context, decomposes into subtasks, spawns specialists, verifies outputs, and merges into `agent-output/`.

For multi-phase work, use the pipeline:

```
/synthex:preflight                          # dry-run: what's ready, what's missing
/synthex:init-project "order-analytics"     # full project scaffold + pipeline
/synthex:launch-pipeline                    # execute through all 5 phases
/synthex:track-progress                     # live dashboard
```

### 4. Check results

```
/synthex:status                              # live task board
/synthex:memory "order deduplication"        # search past decisions
/synthex:report --type pdf                   # synthesize deliverable
/synthex:audit                               # full chronological audit
```

---

## The agent hierarchy

Synthex organizes 24 specialist subagents across 7 divisions under the Principal Investigator.

```
                         ┌─────────────────────────┐
                         │  Principal Investigator  │  (Opus)
                         │  Pipeline Director       │  (extends PI)
                         │  Escalation Manager      │
                         └────────────┬────────────┘
               ┌──────────────────────┼──────────────────────┐
               ▼                      ▼                      ▼
     ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
     │ Research Div.   │   │ Engineering Div. │   │ Audit Div.      │
     ├─────────────────┤   ├─────────────────┤   ├─────────────────┤
     │ Research        │   │ Software Eng.    │   │ Audit Archivist │
     │ Scientist       │   │ Data Engineer    │   │ Documentation   │
     │ Methodologist   │   │ Automation Eng.  │   │ Engineer        │
     │ Algorithm Eng.  │   │ Frontend/3D Eng. │   │                 │
     │ Research Asst.  │   │ Component Builder│   │                 │
     │ Source Miner    │   │ Quality Auto.    │   │                 │
     │ Insight Compiler│   │ Environment Bldr.│   │                 │
     └─────────────────┘   └─────────────────┘   └─────────────────┘
               │                      │
     ┌─────────┴─────────┐            │
     ▼                   ▼            ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Architecture │  │ Review Div.  │  │ Risk Div.    │
├──────────────┤  ├──────────────┤  ├──────────────┤
│ Architecture │  │ Peer Validator│  │ Risk          │
│ Advisor      │  │ Statistical   │  │ Identifier    │
│ Quality      │  │   Auditor     │  │               │
│ Gatekeeper   │  │ Artifact      │  │               │
│ Standards    │  │   Verifier    │  │               │
│ Authority    │  │              │  │               │
└──────────────┘  └──────────────┘  └──────────────┘
```

### Full agent roster

| Agent | Division | Model | Use when… |
|---|---|---|---|
| **Principal Investigator** | Orchestration | Opus | Any multi-step or cross-discipline request needs decomposition and verification |
| **Pipeline Director** | Orchestration | Sonnet | Multi-phase projects need gated execution (Research→Planning→Impl→Review→Validation) |
| **Escalation Manager** | Orchestration | Sonnet | Agents encounter blockers — severity levels P5→P1 with circuit breaker |
| **Research Scientist** | Research | Sonnet | A hypothesis needs rigorous experimental design and testing |
| **Methodologist** | Research | Sonnet | Asymptotic bounds, numerical-stability analysis, or SymPy verification is needed |
| **Algorithm Engineer** | Research | Sonnet | A non-trivial algorithm needs optimized implementation |
| **Research Assistant** | Research | Haiku | A precisely scoped, self-contained subtask needs execution |
| **Source Miner** | Research | Sonnet | Source materials (papers, schemas, models) need structured extraction |
| **Insight Compiler** | Research | Sonnet | Findings across sources need synthesis into actionable insights |
| **Architecture Advisor** | Architecture | Sonnet | System design decisions need pattern analysis and trade-off documentation |
| **Quality Gatekeeper** | Architecture | Sonnet | Phase-gate criteria need definition and enforcement |
| **Standards Authority** | Architecture | Sonnet | Compliance with IEEE, ISO, OWASP, GDPR, DAMA-DMBOK needs auditing |
| **Software Engineer** | Engineering | Sonnet | Production backend code, APIs, or CLI tools are the deliverable |
| **Data Engineer** | Engineering | Sonnet | Data must be profiled, cleaned, schema-validated, or traced end-to-end |
| **Automation Engineer** | Engineering | Sonnet | A pipeline needs assembly, containerization, benchmarking, or execution |
| **Frontend / 3D Engineer** | Engineering | Sonnet | A React/Vue UI or interactive Three.js scene is the deliverable |
| **Component Builder** | Engineering | Sonnet | Code components need generation from structured plans with pre-submission checks |
| **Quality Automation** | Engineering | Sonnet | Post-pipeline validation and regression scripts need generation |
| **Environment Builder** | Engineering | Sonnet | A new Synthex project needs bootstrapping and MCP setup |
| **Peer Validator** | Review | Sonnet | Code needs asynchronous review across correctness/quality/perf/security/coverage |
| **Statistical Auditor** | Review | Sonnet | Output needs statistical methodology validation with re-score loops (max 3 iterations) |
| **Artifact Verifier** | Review | Sonnet | All artifact types need structure/naming/existence/completeness validation |
| **Risk Identifier** | Risk | Sonnet | Plans need challenge against edge cases and failure modes |
| **Documentation Engineer** | Audit | Haiku | Findings need compilation into whitepapers, PPTX, or HTML dashboards |
| **Audit Archivist** | Audit | Daemon | Runs in background automatically — snapshots state, tracks pipeline phases |

---

## Command reference (20 commands)

### Original commands (v1.0)

| Command | Purpose |
|---|---|
| `/synthex:synthex-init` | Scaffold the runtime sandbox and initialize SQLite DBs |
| `/synthex:delegate "<task>"` | Send a task to the PI for decomposition and agent assignment |
| `/synthex:status` | Display task board from `intents.db` |
| `/synthex:theory` | Launch Methodologist for LaTeX/complexity analysis |
| `/synthex:pipeline --script=<file>` | Run ETL/ML workloads in the Heavy Compute sandbox |
| `/synthex:experiment` | Full experiment lifecycle: design → run → compare → report |
| `/synthex:report --type <ppt\|html\|pdf>` | Synthesize deliverables from accumulated outputs |
| `/synthex:audit` | Compile chronological audit report from both SQLite DBs |
| `/synthex:memory "<query>"` | Query the Memory Vault via `vector_retrieve` |

### Pipeline commands (v2.0)

| Command | Purpose | Primary Agent |
|---|---|---|
| `/synthex:init-project "<name>"` | Scaffold project + interactive setup + launch pipeline | EnvironmentBuilder → PipelineDirector |
| `/synthex:launch-pipeline` | Execute through all 5 phases (gated) | PipelineDirector |
| `/synthex:preflight` | Read-only dry-run: what's ready, what's missing | QualityGatekeeper |
| `/synthex:track-progress` | Pipeline status, phase completions, blockers, scores | PipelineDirector |
| `/synthex:registry-view` | Component state: locked, in-progress, draft, queued | RegistryManager |

### Component & config commands (v2.0)

| Command | Purpose | Primary Agent |
|---|---|---|
| `/synthex:add-component` | Interactive component definition → pipeline | PipelineDirector |
| `/synthex:refine-component "<id>"` | Modify locked component → queue enhancement | PipelineDirector |
| `/synthex:build-requirements` | Build central requirements markdown | QualityGatekeeper |
| `/synthex:compile-resources` | Generate reference materials from extractions | InsightCompiler |
| `/synthex:enable-validation` | Generate post-pipeline validation scripts | QualityAutomation |
| `/synthex:organize-inputs` | Catalog runtime source data in `user-input/` | EnvironmentBuilder |

### Research loop command (v2.0)

| Command | Purpose | Primary Agent |
|---|---|---|
| `/synthex:research-loop "<question>" [--autonomous] [--max-iterations N]` | Continuous research loop: literature→hypothesis→experiment→reflect→iterate | ResearchScientist |

---

## Domain skills (41 total)

### Model-invoked skills (automatically selected by Claude)

| Skill | Triggers when… | New in |
|---|---|---|
| `task-tracking` | Tasks are created, updated, blocked, or completed | v1.0 |
| `knowledge-graph` | Codebase structure, dependencies, or relationships need mapping | v1.0 |
| `data-lineage` | ETL pipelines, schema changes, or data flow need documenting | v1.0 |
| `research-loop` | Continuous research: hypothesis, experiment, reflect, iterate (replaces experiment-design) | v2.0 |
| `frontend-dev` | React/Vue components or client-side UI work | v1.0 |
| `3d-modeling` | Three.js scenes, WebGL rendering | v1.0 |
| `presentation` | Slide decks or pitches from results | v1.0 |
| `whitepaper` | IEEE/ACM-structured technical papers | v1.0 |
| `prototyping` | Fast Flask/Streamlit scaffolding for POCs | v1.0 |
| `phase-templates` | Pipeline Director generates standard tasks for a new phase | v2.0 |
| `review-cycle` | Artifacts need peer review and quality scoring with re-score loops | v2.0 |
| `data-interpreter` | Source materials need parsing (Excel, XML, JSON, SQL, CSV, YAML) | v2.0 |
| `artifact-factory` | Structured artifacts (YAML, Markdown, code, tests) need generation | v2.0 |
| `scoring-framework` | Output quality needs weighted scoring with failure classification | v2.0 |
| `structure-validator` | Folder boundaries, YAML structures, naming, or file existence need validation | v2.0 |
| `registry-manager` | Component state tracking across pipeline runs is needed | v2.0 |
| `task-orchestrator` | Coordination patterns (sequential/parallel/fan-out/fan-in/pipeline) are needed | v2.0 |
| `research-loop` | Continuous research: hypothesis→experiment→reflect→iterate | v2.0 |
| `experiment-auditor` | 6-dimension experiment audit (data/stats/code/methodology/leakage/sanity) | v2.0 |
| `literature-survey` | arXiv/Semantic Scholar search with citation chain mode | v2.0 |
| `reproducibility-checker` | 6-point reproducibility validation | v2.0 |

---

## MCP servers

### Memory & Graph (`mcp__plugin_synthex_memory-graph__*`)

4-tier vector fallback: **turbovec** (`IdMapIndex`, 4-bit quantization) → **chromadb** (persistent client, cosine HNSW) → **numpy cosine** (in-memory, `.npz` persistence) → **pure-Python cosine** (JSON file, zero deps). Embeddings: `sentence-transformers/all-MiniLM-L6-v2` (384-dim) → deterministic hashing embedder (zero dep).

| Tool | Purpose |
|---|---|
| `vector_retrieve` | Semantic search across the Memory Vault |
| `vector_index` | Index a file into the vector store |
| `kg_add` | Add a subject-predicate-object triple to the knowledge graph |
| `kg_query` | Query the knowledge graph with LIKE filters |
| `lineage_trace` | Trace data lineage across intents and KG triples |
| `log_intent` | Record an agent decision ("why") in `intents.db` |
| `task_create` | Create a task with priority and assignment |
| `task_update` | Update task status |
| `task_list` | List tasks, optionally filtered by status |
| `drain_queue` | Consume the auto-indexer queue (`index_queue.jsonl`) |

### Heavy Compute (`mcp__plugin_synthex_heavy-compute__*`)

Isolated computation. `sympy` required; `pandas` and Docker optional. `sympy_solve` wrapped in 30s `ThreadPoolExecutor` timeout.

| Tool | Purpose |
|---|---|
| `sympy_solve` | Symbolic math: solve, simplify, integrate, differentiate, factor |
| `profile_script` | Run a Python script under cProfile and report top functions |
| `etl_validate` | Validate CSV: row count, columns, grain uniqueness, issues |
| `docker_run` | Run a command in a Docker container with volume mounts (degrades gracefully) |

### Visualization (`mcp__plugin_synthex_visualization__*`)

Node.js server for UI generation. Requires `@modelcontextprotocol/sdk` and `zod`.

| Tool | Purpose |
|---|---|
| `threejs_scaffold` | Write a self-contained Three.js HTML scene to `agent-output/artifacts/` |
| `react_component` | Scaffold a React JSX component from a spec |
| `preview_ui` | Return a `file://` URL for an artifact under `agent-output/` |

---

## Architecture

```
User prompt
    │
    ▼
┌──────────────────────────────────────┐
│ UserPromptSubmit hook                │
│ memory-injector.sh → top-3 chunks    │  ← Memory Vault auto-injection (<5s timeout, fail-open)
└──────────────┬───────────────────────┘
               │
    ┌──────────▼──────────┐
    │  Principal          │  ← /synthex:delegate
    │  Investigator /     │  ← /synthex:launch-pipeline
    │  Pipeline Director  │
    └──────────┬──────────┘
               │ spawns 23 agents across 7 divisions
    ┌──────────┼──────────┐
    ▼          ▼          ▼
 Research  Engineering  Audit/Review/Risk  ← 5-phase gated pipeline
    │          │          │
    └──────────┼──────────┘
               │
    ┌──────────▼──────────┐
    │  PreToolUse hook     │
    │  sandbox-gate.sh     │  ← blocks out-of-zone reads/writes (exit 2)
    │  (every tool call)   │     path canonicalization prevents ../ traversal
    └──────────┬──────────┘
               │
    ┌──────────▼──────────┐
    │  PostToolUse hook    │
    │  auto-indexer.sh     │  ← queues new/modified files for vector indexing
    └──────────────────────┘
               │
    ┌──────────▼──────────┐
    │  Audit Archivist     │  ← background daemon: state snapshots,
    │  (monitor)           │     pipeline phase tracking, experiment counting
    └──────────────────────┘
```

---

## Developing Synthex

### Project layout

```
synthex-plugin/
├── .claude-plugin/plugin.json   # manifest (v2.0.0)
├── .mcp.json                    # 3 MCP server definitions
├── hooks/
│   ├── hooks.json               # PreToolUse·PostToolUse·UserPromptSubmit·Subagent*·Task*
│   └── scripts/                 # 6 scripts + test harness (10/10 tests)
├── agents/                      # 23 subagent .md definitions
├── skills/                      # 41 SKILL.md directories (21 domain + 20 command)
├── mcp-servers/
│   ├── memory-graph/            # FastMCP server + synthex_memory.py CLI library
│   ├── heavy-compute/           # FastMCP server + Dockerfile
│   └── visualization/           # Node MCP server
├── monitors/
│   ├── monitors.json            # audit-archivist daemon
│   └── audit-archivist/         # archivist.py (pipeline-aware)
├── tests/                       # 5 test files + run_all.sh (7 suites, 140+ checks)
├── docs/DATA_CONTRACTS.md       # binding integration contract
└── README.md                    # this file
```

### Development loop

```bash
claude --plugin-dir ./synthex-plugin
/reload-plugins
claude plugin validate ./synthex-plugin   # requires auth
```

### Smoke tests

```bash
cd hooks/scripts && bash test_hooks.sh                      # 10/10
cd mcp-servers/memory-graph && python synthex_memory.py selftest
cd mcp-servers/heavy-compute && python server.py --selftest
node --check mcp-servers/visualization/server.js
bash tests/run_all.sh                                        # full suite: 7/7
```

---

## Configuration

Environment variables (replace the removed `userConfig` block):

| Variable | Values | Default | Effect |
|---|---|---|---|
| `SYNTHEX_VECTOR_BACKEND` | `turbovec`, `chroma`, `lancedb`, `faiss` | `chroma` | Vector store tier selection |
| `SYNTHEX_SANDBOX_MODE` | `strict`, `permissive` | `strict` | `strict` blocks writes outside `agent-output/` and `knowledgebase/` |
| `SYNTHEX_ARCHIVIST_INTERVAL` | integer seconds | 300 | Archivist tick interval |

---

## Troubleshooting

**Plugin doesn't load:**
- Verify `skills/`, `agents/`, `hooks/` are at the plugin root (not inside `.claude-plugin/`).
- Run `claude plugin validate ./synthex-plugin` and fix reported issues.
- Check JSON validity: `python -c "import json; json.load(open('.claude-plugin/plugin.json'))"`

**Hook not firing:**
- Run `/hooks` in Claude Code and confirm the hook appears under the correct event.
- Test manually: pipe sample JSON to the script and check the exit code.
- On Windows: use `git add --chmod=+x hooks/scripts/*.sh` or set permissions via `icacls`.

**Sandbox gate blocking legit writes:**
- Verify the file path is under `<project>/agent-output/` or `<project>/knowledgebase/`.
- Set `SYNTHEX_SANDBOX_MODE=permissive` to disable enforcement temporarily.
- The gate canonicalizes paths to prevent `../` traversal — symlinks resolve before the allow/deny check.

**Memory Vault returns no results:**
- Run `/synthex:synthex-init` to ensure DBs exist.
- Index content: `python mcp-servers/memory-graph/synthex_memory.py index <file>`.
- Verify: `python mcp-servers/memory-graph/synthex_memory.py retrieve --query "test"`.
- The hashing embedder produces deterministic but lower-quality vectors. Install `sentence-transformers` and `turbovec` for best results.
- Backend selection: `export SYNTHEX_VECTOR_BACKEND=turbovec` (fallback chain activates automatically).

**MCP servers don't start:**
- Memory & Graph: `python3` on `$PATH`. Zero Python packages required at baseline.
- Heavy Compute: `python3` + `sympy`. Docker optional.
- Visualization: `node` on `$PATH`. Run `cd mcp-servers/visualization && npm install`.
