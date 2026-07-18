---
name: memory
description: "/synthex:memory <query> -- Query the Memory Vault (vector_retrieve) and display top 5 chunks with source and score. Falls back to python3 CLI if MCP unavailable."
disable-model-invocation: true
allowed-tools: Bash(sqlite3 *) Bash(echo *) Bash(test *) Bash(python3 *) Bash(find *)
---

# /synthex:memory "<query>" -- Query the Memory Vault

$ARGUMENTS is the natural-language query string.

## Step 1 -- Resolve SYNTHEX_ROOT

```
SYNTHEX_ROOT = $CLAUDE_PROJECT_DIR  (if set)  else $PWD
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

## Step 4 -- Search knowledgebase for direct matches

As a secondary source, search the knowledgebase files for keyword matches:

```bash
find "$SYNTHEX_ROOT/knowledgebase" -type f \( -name "*.md" -o -name "*.txt" \) 2>/dev/null | head -10
# Grep for the query terms in found files
```

## Step 5 -- Report

Display all results to the user. For each result, show:
- The chunk text (truncated to ~200 chars)
- The source file path
- The relevance score (from vector_retrieve) or indicate "keyword match" for the fallback
- The timestamp if available

If no results are found from any source, state that clearly.
