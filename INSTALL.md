# Installing Synthex

## Quickstart (local development)

```bash
git clone https://github.com/VnykzHub/Synthex.git
cd Synthex
claude --plugin-dir .
```

> The repo root IS the plugin directory. Cloning gives you the plugin directly.

## From GitHub (direct)

```bash
claude --plugin-dir https://github.com/VnykzHub/Synthex --clone
```

## Verify installation

After starting Claude Code with the plugin:

- Run `/help` — you should see `/synthex:*` commands listed
- Run `/synthex:synthex-init` — should scaffold user-input/, agent-output/, knowledgebase/, logs/
- Run `/synthex:status` — should show empty task board
- Run `@synthex:principal-investigator` — should mention the agent

## Requirements

- Claude Code v2.1+
- Python 3.12 + `pip install mcp sympy`
- Node 20+ + `cd mcp-servers/visualization && npm install`
- sqlite3, jq on PATH
- Docker (optional)

> **Important:** After cloning, run these one-time setup commands before loading the plugin:
> ```bash
> pip install mcp sympy
> cd mcp-servers/visualization && npm install && cd ../..
> ```

## Testing the plugin

```bash
cd synthex-plugin
bash tests/run_all.sh
# Expected: 7/7 passing
```
