---
name: phase-templates
description: Contains task generation templates for the research, planning, and implementation phases. Use when PipelineDirector needs to generate standard tasks for a new project phase.
---

# Phase Templates Skill

This skill generates standardized task lists for each phase of the Synthex pipeline. Invoked by the Pipeline Director at the start of each phase to populate the shared task list with well-defined, phase-appropriate work items.

## Research Phase Tasks

Generate these tasks when entering the Research phase:

### R1 — Context Gathering
- **Title:** Gather project context and background
- **Owner:** research-assistant
- **Priority:** P1
- **Acceptance criteria:**
  - The assignment document in `user-input/assignments/` has been read and summarized
  - Relevant prior work has been retrieved from the Memory Vault via `vector_retrieve`
  - Key references and related papers/documents are identified
  - A context summary file exists at `agent-output/artifacts/research-context.md`
- **Output path:** `agent-output/artifacts/research-context.md`

### R2 — Problem Space Analysis
- **Title:** Analyze and define the problem space
- **Owner:** research-scientist
- **Priority:** P1
- **Acceptance criteria:**
  - Problem boundaries are clearly defined with constraints
  - Known approaches and their limitations are documented
  - Gaps in existing solutions are identified
  - A problem statement document exists at `agent-output/artifacts/problem-analysis.md`
- **Output path:** `agent-output/artifacts/problem-analysis.md`

### R3 — Feasibility Assessment
- **Title:** Assess technical feasibility and resource requirements
- **Owner:** research-scientist
- **Priority:** P2
- **Acceptance criteria:**
  - Technical approach options are evaluated with pros/cons
  - Resource requirements (compute, data, time) are estimated
  - Risk factors and mitigation strategies are identified
  - Feasibility report exists at `agent-output/artifacts/feasibility-report.md`
- **Output path:** `agent-output/artifacts/feasibility-report.md`

### R4 — Research Synthesis
- **Title:** Synthesize research findings into actionable recommendations
- **Owner:** research-scientist
- **Priority:** P1
- **Acceptance criteria:**
  - All R1-R3 outputs are consolidated into a single synthesis document
  - Recommended approach is clearly stated with rationale
  - Open questions and assumptions are documented
  - Synthesis document exists at `agent-output/artifacts/research-synthesis.md`
- **Output path:** `agent-output/artifacts/research-synthesis.md`

## Planning Phase Tasks

Generate these tasks when entering the Planning phase:

### P1 — Requirements Breakdown
- **Title:** Decompose requirements into actionable subtasks
- **Owner:** principal-investigator
- **Priority:** P1
- **Acceptance criteria:**
  - Each requirement from the research synthesis maps to one or more subtasks
  - Subtasks have clear owners and priorities assigned
  - Dependencies between subtasks are documented
  - Requirements traceability matrix exists at `agent-output/artifacts/requirements-breakdown.md`
- **Output path:** `agent-output/artifacts/requirements-breakdown.md`

### P2 — Architecture and Design
- **Title:** Define the architecture and design approach
- **Owner:** methodologist
- **Priority:** P1
- **Acceptance criteria:**
  - Architecture diagram or description is created
  - Component boundaries and interfaces are defined
  - Data flow between components is documented
  - Design document exists at `agent-output/artifacts/architecture-design.md`
- **Output path:** `agent-output/artifacts/architecture-design.md`

### P3 — Task Sequencing and Prioritization
- **Title:** Sequence tasks into an ordered implementation plan
- **Owner:** principal-investigator
- **Priority:** P1
- **Acceptance criteria:**
  - All subtasks are ordered by dependency and priority
  - Critical path is identified
  - Milestones and checkpoints are defined
  - Implementation roadmap exists at `agent-output/artifacts/roadmap.md`
- **Output path:** `agent-output/artifacts/roadmap.md`

### P4 — Resource Allocation
- **Title:** Assign resources and set timelines
- **Owner:** principal-investigator
- **Priority:** P2
- **Acceptance criteria:**
  - Each task has an estimated effort (hours/days)
  - Agent assignments are finalized per task
  - Timeline with expected completion dates is set
  - Resource plan exists at `agent-output/artifacts/resource-plan.md`
- **Output path:** `agent-output/artifacts/resource-plan.md`

## Implementation Phase Tasks

Generate these tasks when entering the Implementation phase:

### I1 — Core Implementation
- **Title:** Implement core components per the architecture design
- **Owner:** algorithm-engineer | software-engineer | frontend-engineer
- **Priority:** P1
- **Acceptance criteria:**
  - All components from the architecture design are implemented
  - Code compiles or passes type checks
  - Unit tests exist for all public interfaces
  - Implementation exists under `agent-output/src/`
- **Output path:** `agent-output/src/`

### I2 — Integration and Wiring
- **Title:** Integrate components and verify end-to-end connectivity
- **Owner:** automation-engineer
- **Priority:** P1
- **Acceptance criteria:**
  - All components can be invoked end-to-end
  - Data flows correctly through the pipeline
  - Integration tests pass
  - Integration report exists at `agent-output/artifacts/integration-report.md`
- **Output path:** `agent-output/artifacts/integration-report.md`

### I3 — Documentation and Artifacts
- **Title:** Produce documentation and supporting artifacts
- **Owner:** documentation-engineer
- **Priority:** P2
- **Acceptance criteria:**
  - README or usage documentation is complete
  - Configuration examples are documented
  - Known limitations and future work are noted
  - Documentation exists under `agent-output/artifacts/`
- **Output path:** `agent-output/artifacts/`

## Error Recovery

- **Missing prerequisite:** If a required tool or dependency is unavailable, report it clearly with the exact command to install or path to check. Do not silently skip.
- **Malformed input:** Validate key fields before processing. On failure, report the exact field name and expected format. Do not proceed with partial data.
- **Timeout:** Set a 30-second budget for any blocking operation (MCP call, script execution, DB query). If exceeded, write partial results to `agent-output/partial/` and note what completed vs. what timed out.
- **Empty result:** If no data matches the query, produce a valid empty output (not an error) with a note explaining the search scope and suggesting next steps.
- **Partial failure:** If some sub-tasks succeed and others fail, report the split clearly: which succeeded, which failed, and whether the successes are usable independently.

## Usage

The Pipeline Director invokes this skill at phase start:
- Call `Skill("phase-templates", args="research")` for Research phase tasks.
- Call `Skill("phase-templates", args="planning")` for Planning phase tasks.
- Call `Skill("phase-templates", args="implementation")` for Implementation phase tasks.

Each call returns the task list for that phase. The Pipeline Director then registers each task via `task_create` and proceeds to dispatching.
