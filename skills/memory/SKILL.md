---
name: memory
description: "/synthex:memory <query> -- Query the Memory Vault (vector_retrieve) and display top 5 chunks with source and score. Falls back to python3 CLI if MCP unavailable. Use when the user runs /synthex:memory to query the vector Memory Vault for semantically relevant past work."
role: worker
disable-model-invocation: true
allowed-tools: Bash(sqlite3 *) Bash(echo *) Bash(test *) Bash(python3 *) Bash(grep *) Bash(cat *)
---

# /synthex:memory "<query>" -- Query the Memory Vault

$ARGUMENTS is the natural-language query string.

## Step 1 -- Resolve SYNTHEX_ROOT

```bash
SYNTHEX_ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"
export SYNTHEX_ROOT
```

## Step 2 -- Try memory-graph MCP (primary path)

Attempt to call the memory-graph MCP server:

- `mcp__plugin_synthex_memory-graph__vector_retrieve(query="$ARGUMENTS", top_k=5, scope="all")`

If the tool is available, it returns `[{chunk, source, score, ts}]`. Render the results:

```markdown
## Memory Vault Results
Query: "$ARGUMENTS"

| # | Chunk (truncated) | Source | Score | Timestamp |
| :-| :---------------- | :----- | :---- | :--------- |
| 1 | <first 120 chars> | <path> | 0.95  | <ts>      |
| 2 | ...               | ...    | ...   | ...       |
| 3 | ...               | ...    | ...   | ...       |
| 4 | ...               | ...    | ...   | ...       |
| 5 | ...               | ...    | ...   | ...       |
```

## Step 3 -- Fallback: python3 CLI

If the MCP tool is not available (tool call returns an error or is unrecognized), fall back to the standalone Python CLI:

```bash
# Check if the memory script exists
SCRIPT="$SYNTHEX_ROOT/.claude-plugin/mcp-servers/memory-graph/synthex_memory.py"
if [ -f "$SCRIPT" ]; then
  python3 "$SCRIPT" retrieve --query "$ARGUMENTS" --top-k 5
else
  # Try in plugin root
  SCRIPT2="${CLAUDE_PLUGIN_ROOT}/mcp-servers/memory-graph/synthex_memory.py"
  if [ -f "$SCRIPT2" ]; then
    python3 "$SCRIPT2" retrieve --query "$ARGUMENTS" --top-k 5
  else
    echo "Memory MCP not available and no standalone script found at either:"
    echo "  $SCRIPT"
    echo "  $SCRIPT2"
    echo "Install the memory-graph MCP server to enable vector queries."
  fi
fi
```

## Step 4 -- Search knowledgebase for content matches

As a secondary source, search the knowledgebase files for content matches using grep:

```bash
SYNTHEX_ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"

# Use grep -rl for recursive content search (matches file content, not just names)
if [ -n "$ARGUMENTS" ] && [ "$ARGUMENTS" != "" ]; then
  QUERY_SAFE="$(printf '%s' "$ARGUMENTS" | sed 's/[^a-zA-Z0-9_ -]//g')"
  if [ -d "$SYNTHEX_ROOT/knowledgebase" ]; then
    grep -rl -i "$QUERY_SAFE" "$SYNTHEX_ROOT/knowledgebase" --include="*.md" --include="*.txt" 2>/dev/null \
      | head -20
  else
    echo "knowledgebase directory not found at $SYNTHEX_ROOT/knowledgebase"
  fi
fi
```

## Error Recovery

- **Missing prerequisite:** If a required tool or dependency is unavailable, report it clearly with the exact command to install or path to check. Do not silently skip.
- **Malformed input:** Validate key fields before processing. On failure, report the exact field name and expected format. Do not proceed with partial data.
- **Timeout:** Set a 30-second budget for any blocking operation (MCP call, script execution, DB query). If exceeded, write partial results to `agent-output/partial/` and note what completed vs. what timed out.
- **Empty result:** If no data matches the query, produce a valid empty output (not an error) with a note explaining the search scope and suggesting next steps.
- **Partial failure:** If some sub-tasks succeed and others fail, report the split clearly: which succeeded, which failed, and whether the successes are usable independently.

## Step 5 -- Report

Display all results to the user. For each result, show:
- The chunk text (truncated to ~200 chars)
- The source file path
- The relevance score (from vector_retrieve) or indicate "keyword match" for the fallback
- The timestamp if available

If no results are found from any source, state that clearly.
