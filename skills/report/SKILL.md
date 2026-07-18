---
name: report
description: "/synthex:report --type ppt|html|pdf -- Synthesize agent-output/reports into a deliverable using Documentation Engineer + visualization MCP."
disable-model-invocation: true
allowed-tools: Bash(sqlite3 *) Bash(echo *) Bash(find *) Bash(mkdir *) Bash(test *)
---

# /synthex:report --type ppt|html|pdf -- Synthesize results into a deliverable

$ARGUMENTS should contain `--type <format>` and optionally a topic or source directory.

## Step 1 -- Resolve SYNTHEX_ROOT and parse arguments

```
SYNTHEX_ROOT = $CLAUDE_PROJECT_DIR  (if set)  else $PWD
```

Parse $ARGUMENTS for:
- `--type ppt|html|pdf` -- output format (default: html if omitted)
- Remaining text is the topic or source directory to synthesize

## Step 2 -- Gather source material

Search `agent-output/reports/` and `agent-output/artifacts/` for relevant content:

```bash
find "$SYNTHEX_ROOT/agent-output/reports" -type f 2>/dev/null | head -30
find "$SYNTHEX_ROOT/agent-output/artifacts" -type f 2>/dev/null | head -30
```

Also check `knowledgebase/schemas/` and `knowledgebase/papers/` for supporting reference material.

## Step 3 -- Synthesize content

Read the source files. Identify: key findings, data visualizations needed, code snippets to include, and conclusions. Structure the report with:

1. Title and metadata (date, author agent)
2. Executive summary
3. Methodology or approach
4. Findings with supporting evidence
5. Visualizations
6. Conclusions and recommendations

## Step 4 -- Generate output (format-dependent)

### --type html

Use the visualization MCP to scaffold an interactive report:

- `mcp__plugin_synthex_visualization__react_component(name="report-<topic>", spec="<json spec>")`
- `mcp__plugin_synthex_visualization__preview_ui(path="<path>")`

Write to `agent-output/artifacts/report-<topic>.html`.

### --type ppt

Use the presentation domain skill to build slides:

- Outline of slides with content per slide
- Use threejs_scaffold for 3D charts if needed
- `mcp__plugin_synthex_visualization__threejs_scaffold(name="chart-<name>", kind="scene")`

Write to `agent-output/artifacts/report-<topic>.pptx`.

### --type pdf

Use the whitepaper domain skill:

- Compile markdown to PDF via pandoc or LaTeX
- Include any generated visualizations as figures

Write to `agent-output/reports/report-<topic>.pdf`.

## Step 5 -- Log and report

```bash
DETAILS="{\"format\":\"<type>\",\"path\":\"agent-output/...\"}"
sqlite3 "$SYNTHEX_ROOT/logs/state_ledger.db" \
  "INSERT INTO state_ledger (agent, event_type, details) VALUES ('documentation-engineer', 'report.generate', '$DETAILS');"
```

Report the output path and format to the user.
