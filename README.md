# Synthex (plugin)

Enterprise multi-agent framework for Claude Code: a zero-write sandbox, a PI-led
agent hierarchy, three MCP servers (Heavy Compute, Memory & Graph, Visualization),
and a vector Memory Vault. See `../draft_uno.md` (PRD) and `../Build_guide.md` (impl).

> **Status: skeleton.** Structure and configs are in place; agent/skill/MCP bodies
> are stubs. See **`BUILD_PLAN.md`** for the micro-task list and dependency graph.

## Layout

```
synthex-plugin/
├── .claude-plugin/plugin.json   # manifest
├── .mcp.json                    # 3 bundled MCP servers
├── hooks/
│   ├── hooks.json               # PreToolUse/PostToolUse/UserPromptSubmit/Subagent*/Task*
│   └── scripts/*.sh             # sandbox-gate has real logic; others are stubs
├── agents/*.md                  # 10 subagents (PI + 3 divisions)
├── skills/<name>/SKILL.md       # 9 domain skills + 9 /synthex: command skills
├── mcp-servers/{heavy-compute,memory-graph,visualization}/   # server stubs
├── monitors/monitors.json       # audit-archivist daemon
├── BUILD_PLAN.md                # << build order + dependency graph
└── docs/
```

## Develop & test

```bash
claude plugin validate ./synthex-plugin      # structural check
claude --plugin-dir ./synthex-plugin         # load for one session
/reload-plugins                              # pick up edits without restarting
```

Skills load as `/synthex:<skill>`; agents @-mention as `synthex:<agent>`; bundled
MCP tools appear as `mcp__plugin_synthex_<server>__<tool>`.

## The two sandboxes (don't confuse them)

- **Plugin package** — this directory. Committed source.
- **Runtime data sandbox** — `user-input/` (read-only), `agent-output/` (write),
  `knowledgebase/`, `logs/`. Created by `/synthex:synthex-init` *in the user's
  project* at runtime, and git-ignored here.
