---
name: task-orchestrator
description: Outlines coordination patterns for agents using the shared task list -- sequential, parallel, fan-out, fan-in, and pipeline. Use when PipelineDirector needs to plan task execution order.
---

# Task Orchestrator

## Task Lifecycle

Every task managed by the orchestrator follows a five-stage lifecycle. Transitions are recorded in the shared `tasks` table in `logs/intents.db`.

```
  [CREATE] --> [CLAIM] --> [BLOCK] --> [COMPLETE] --> [REVIEW]
     |            |            |            |              |
     v            v            v            v              v
  Queued      Assigned     Waiting on   Output        Human/AI
  but not     to an        dependency  produced,     verification
  assigned    agent        completion  pending       pending
                            signal     validation
```

1. **CREATE** -- A new task row is inserted with `status='pending'`. The task includes an `id`, `title`, `priority`, and optional `dependencies` (JSON list of task IDs that must complete first). No agent owns it yet.

2. **CLAIM** -- An agent sets `assigned_to=<agent_name>` and `status='in-progress'`. Only tasks with all dependencies in `completed` status may be claimed. The orchestrator validates this precondition before allowing the claim.

3. **BLOCK** -- If a claimed task hits a dependency that is not yet complete, the orchestrator sets `status='blocked'` and records the blocking task ID in a `blocked_by` column. Blocked tasks are automatically unblocked when the blocking task transitions to `completed`.

4. **COMPLETE** -- The agent sets `status='completed'` and `completed_at=<UTC timestamp>`. The orchestrator then checks for any tasks blocked on this one and transitions them back to `pending` so they can be claimed.

5. **REVIEW** -- An optional final stage where a reviewer agent or human inspects the output. The task is set to `status='review'`. The reviewer can either approve (returning to `completed`) or request changes (returning to `in-progress`).

## Coordination Patterns

### 1. Sequential (Chain)

```
Task A --> Task B --> Task C
```

Each task starts only when the previous one finishes. Use when tasks have strict order dependencies (e.g., data ingestion must finish before feature extraction begins).

Implementation: Set `dependencies: [prev_task_id]` on each task.

### 2. Parallel (Fan-Out)

```
         +--> Task B1 -->+
         |               |
Task A --+--> Task B2 -->+--> Task D
         |               |
         +--> Task B3 -->+
```

One upstream task fans out to multiple independent subtasks. All subtasks run concurrently. Use when a result needs to be processed through multiple independent transformations.

Implementation: Set `dependencies: [task_a_id]` on each of B1, B2, B3. Task D depends on all of B1, B2, B3.

### 3. Fan-Out (Scatter)

```
Task A --> Task B1
Task A --> Task B2
Task A --> Task B3
```

A single task spawns N identical subtasks that process different slices of data. Each subtask has the same definition but different input parameters. Use for data-parallel workloads.

Implementation: Create N task rows with the same `title` but different input references in `context`. All set `dependencies: [task_a_id]`.

### 4. Fan-In (Gather)

```
Task B1 --+
Task B2 --+--> Task C
Task B3 --+
```

Multiple upstream tasks converge into a single downstream task that merges or summarizes their outputs. Use when independent results must be combined.

Implementation: Set `dependencies: [task_b1_id, task_b2_id, task_b3_id]` on task C.

### 5. Pipeline (Multi-Stage DAG)

```
         +--> Task B1 --+--> Task C1 --+
         |               |             |
Task A --+--> Task B2 --+--> Task C2 --+--> Task D
         |               |             |
         +--> Task B3 --+--> Task C3 --+
```

A combination of fan-out and fan-in across multiple stages. Arbitrary DAG structures are supported. Use for complex multi-stage processing pipelines.

## Pattern Selection Guidance

| When you have...                              | Use pattern        |
|-----------------------------------------------|--------------------|
| Strictly sequential steps                     | Sequential         |
| Independent transformations of one output     | Parallel           |
| Data that can be split across workers         | Fan-Out            |
| Results that need to be merged                | Fan-In             |
| A multi-stage workflow with branching         | Pipeline (DAG)     |

## Error Handling

- Any task that remains `in-progress` for longer than its `timeout` (configurable per task, default 600s) is automatically set to `status='failed'`.
- Failed tasks can be retried: re-set `status='pending'` and clear `assigned_to`. Dependencies of downstream tasks remain unblocked until the retry completes.
- If a task has `max_retries` (default 3) and has been retried that many times, further retry attempts are rejected and the orchestrator escalates to the Principal Investigator.
