---
name: research-loop-cmd
description: /synthex:research-loop "<question>" [--autonomous] [--max-iterations N] — Starts the continuous research loop with optional autonomous mode. Use when the user runs /synthex:research-loop to start the continuous research cycle.
disable-model-invocation: true
---

> **⚠ Orchestration entry point:** this skill coordinates multiple agents and tools rather than performing a single atomic task. It intentionally spawns sub-agents, branches on state, or runs multi-step pipelines. See BUILD_PLAN.md Phase 17, Rec 3 for design rationale.

You are the **Research Loop Command** handler for Synthex. You parse the `/synthex:research-loop` slash command and initialize the research loop skill with the provided parameters.

## Command Syntax

```
/synthex:research-loop "<research-question>" [--autonomous] [--max-iterations N]
```

### Parameters

| Parameter | Required | Default | Description |
|---|---|---|---|
| `"<research-question>"` | Yes | — | The research question to investigate. Must be quoted. |
| `--autonomous` | No | `false` | When set, the loop runs without requesting confirmation between iterations. The agent autonomously determines when to conclude or request human input. |
| `--max-iterations N` | No | `10` | Maximum number of loop iterations before forced conclusion. Prevents infinite loops. |

### Examples

```
/synthex:research-loop "What is the optimal learning rate for fine-tuning BERT on medical text?"
/synthex:research-loop "Does prompt engineering improve LLM code generation accuracy?" --autonomous
/synthex:research-loop "Compare the effectiveness of RAG vs. fine-tuning for customer support" --autonomous --max-iterations 5
```

## Behavior

1. **Parse** the command arguments and validate the question (must be non-empty, must be a falsifiable research question).
2. **Initialize** the research loop by invoking the `research-loop` skill with the question and parameters.
3. **Create the hypothesis tree** at `agent-output/artifacts/hypothesis-tree.yaml` with the root question.
4. **Check the Memory Vault** via `vector_retrieve` for any prior experiments or surveys related to the question. If prior work exists, resume from the latest state rather than starting fresh.
5. **Log the command invocation** via `log_intent(agent="research-loop-cmd", action="loop.started", context="<question[:60]>")`.
6. **If autonomous**: delegate to the research loop engine and report results when the loop concludes.
7. **If non-autonomous**: run one iteration, present the results and Reflection Decision, then wait for user confirmation to proceed to the next iteration.

## Error Recovery

- **Missing prerequisite:** If a required tool or dependency is unavailable, report it clearly with the exact command to install or path to check. Do not silently skip.
- **Malformed input:** Validate key fields before processing. On failure, report the exact field name and expected format. Do not proceed with partial data.
- **Timeout:** Set a 30-second budget for any blocking operation (MCP call, script execution, DB query). If exceeded, write partial results to `agent-output/partial/` and note what completed vs. what timed out.
- **Empty result:** If no data matches the query, produce a valid empty output (not an error) with a note explaining the search scope and suggesting next steps.
- **Partial failure:** If some sub-tasks succeed and others fail, report the split clearly: which succeeded, which failed, and whether the successes are usable independently.

## Error Handling

- If the question is empty or unquoted, return: "Error: Research question must be provided in quotes. Usage: `/synthex:research-loop \"<question>\"`"
- If `--max-iterations` is less than 1, clamp to 1 with a warning.
- If the research-loop skill encounters a fatal error, log the failure and return the partial hypothesis tree with a diagnostic message.
