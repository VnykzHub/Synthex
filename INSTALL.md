# Installing Synthex

## Quickstart (local development)

```bash
git clone https://github.com/VnykzHub/Synthex.git
cd Synthex/synthex-plugin
claude --plugin-dir .
```

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
- Python 3.12
- Node 20+ (for visualization MCP)
- sqlite3, jq on PATH
- Docker (optional)

## Testing the plugin

```bash
cd synthex-plugin
bash tests/run_all.sh
# Expected: 7/7 passing
```
