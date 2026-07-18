#!/usr/bin/env python3
"""Memory & Graph MCP server for the Synthex plugin.

FastMCP server ("memory-graph") exposing every tool from
docs/DATA_CONTRACTS.md §3. Tools appear as:
    mcp__plugin_synthex_memory-graph__<tool>

Delegates all logic to synthex_memory.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from synthex_memory import (
    drain_queue,
    init_db,
    kg_add,
    kg_query,
    lineage_trace,
    log_intent,
    resolve_root,
    task_create,
    task_list,
    task_update,
    vector_index,
    vector_retrieve,
)

mcp = FastMCP("memory-graph")


@mcp.tool(name="vector_retrieve")
def tool_vector_retrieve(query: str, top_k: int = 5, scope: str = "all") -> list[dict]:
    """Semantic search across the Memory Vault. Returns top-k chunks with scores."""
    return vector_retrieve(query, top_k=top_k, scope=scope)


@mcp.tool(name="vector_index")
def tool_vector_index(path: str) -> dict:
    """Index a file into the vector store. Returns {indexed, source}."""
    return vector_index(path)


@mcp.tool(name="kg_add")
def tool_kg_add(subject: str, predicate: str, obj: str, source: str = "") -> dict:
    """Add a triple (subject, predicate, object) to the knowledge graph."""
    return kg_add(subject, predicate, obj, source)


@mcp.tool(name="kg_query")
def tool_kg_query(subject: str = "", predicate: str = "", obj: str = "") -> list[dict]:
    """Query knowledge graph triples. Each argument filters by LIKE match."""
    return kg_query(subject, predicate, obj)


@mcp.tool(name="lineage_trace")
def tool_lineage_trace(target: str) -> list[dict]:
    """Trace data lineage for *target* across intents and kg_triples."""
    return lineage_trace(target)


@mcp.tool(name="log_intent")
def tool_log_intent(agent: str, action: str, why: str, task_id: str = "",
                    context: str = "") -> dict:
    """Record an agent decision in intents.db. Returns {id, ts}."""
    return log_intent(agent, action, why, task_id, context)


@mcp.tool(name="task_create")
def tool_task_create(title: str, priority: str = "medium", assigned_to: str = "") -> dict:
    """Create a task. Returns {id, title, status}."""
    return task_create(title, priority, assigned_to)


@mcp.tool(name="task_update")
def tool_task_update(id: str, status: str) -> dict:
    """Update task status. Returns {id, status}."""
    return task_update(id, status)


@mcp.tool(name="task_list")
def tool_task_list(status: str = "") -> list[dict]:
    """List tasks, optionally filtered by status."""
    return task_list(status)


@mcp.tool(name="drain_queue")
def tool_drain_queue() -> dict:
    """Consume logs/index_queue.jsonl and index every path."""
    return drain_queue()


# --------------------------------------------------------------------------- #
# Entrypoint
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    if "--selftest" in sys.argv:
        root = resolve_root()
        init_db(root)
        print(f"memory-graph server selftest: root={root}")
        testfile = root / "server_selftest.txt"
        testfile.write_text("Synthex memory vault test document for semantic search.")
        r = vector_index(str(testfile), root=root)
        print(f"  index: {r}")
        hits = vector_retrieve("semantic search", top_k=2, root=root)
        print(f"  retrieve: {len(hits)} hits")
        tc = task_create("server selftest", root=root)
        print(f"  task-create: {tc}")
        tasks = task_list(root=root)
        print(f"  task-list: {len(tasks)} tasks")
        print("server selftest: PASS")
    else:
        mcp.run()
