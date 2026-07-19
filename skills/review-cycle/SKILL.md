---
name: review-cycle
description: Task templates for review, scoring, and re-score loop phases. Use when artifacts need peer review and scoring.
role: worker
related_skills: [scoring-framework, structure-validator, task-orchestrator, audit]
---

# Review Cycle Skill

This skill generates standardized task lists for the Review and Validation phases of the Synthex pipeline. It also provides the re-score loop rules that govern automatic retry and escalation when quality thresholds are not met. Invoked by the Pipeline Director when entering the Review or Validation phase.

## Review Phase Tasks

Generate these tasks when entering the Review phase:

### RV1 — Artifact Inventory
- **Title:** Inventory all implementation artifacts for review
- **Owner:** automation-engineer
- **Priority:** P1
- **Acceptance criteria:**
  - All artifacts declared in `agent-output/artifacts/` are catalogued
  - Each artifact is matched to its implementation task
  - Missing or incomplete artifacts are flagged as `blocked`
  - Artifact inventory exists at `agent-output/artifacts/review-inventory.md`
- **Output path:** `agent-output/artifacts/review-inventory.md`

### RV2 — Code and Implementation Review
- **Title:** Review all implementation artifacts for correctness and quality
- **Owner:** methodologist (data/code review) | research-scientist (logic review) | automation-engineer (infrastructure review)
- **Priority:** P1
- **Acceptance criteria:**
  - Every artifact has at least one review record
  - Each review record includes: reviewer, artifact path, score (0-100), findings, and recommendations
  - Critical defects are documented with severity and suggested fix
  - Review records exist at `agent-output/artifacts/reviews/` per artifact
- **Output path:** `agent-output/artifacts/reviews/`

### RV3 — Review Synthesis
- **Title:** Synthesize review findings into an overall quality assessment
- **Owner:** research-scientist
- **Priority:** P1
- **Acceptance criteria:**
  - Overall quality score is calculated as the mean of all artifact review scores
  - Common defect patterns are identified and summarized
  - Recommended improvements are prioritized
  - Quality assessment exists at `agent-output/artifacts/quality-assessment.md`
- **Output path:** `agent-output/artifacts/quality-assessment.md`

### RV4 — Review Sign-off
- **Title:** Generate review sign-off and readiness summary
- **Owner:** principal-investigator
- **Priority:** P2
- **Acceptance criteria:**
  - All artifacts pass the minimum quality threshold (score >= 80)
  - Any artifact scoring below 80 has been flagged for re-score loop
  - Sign-off document confirms readiness for validation phase
  - Sign-off exists at `agent-output/artifacts/review-signoff.md`
- **Output path:** `agent-output/artifacts/review-signoff.md`

## Scoring Phase Tasks

Generate these tasks during automated scoring:

### SC1 — Automated Quality Scoring
- **Title:** Apply scoring rubric to each reviewed artifact
- **Owner:** automation-engineer
- **Priority:** P1
- **Acceptance criteria:**
  - Each artifact is scored on a 0-100 scale against the rubric
  - Score is recorded alongside the review record
  - Artifacts below threshold (score < 80) are tagged for re-score loop
  - Scoring output exists at `agent-output/artifacts/scoring-results.yaml`
- **Output path:** `agent-output/artifacts/scoring-results.yaml`

### SC2 — Threshold Verification
- **Title:** Verify all scores meet the minimum threshold
- **Owner:** automation-engineer
- **Priority:** P1
- **Acceptance criteria:**
  - All scores >= 80: pass gate, proceed to Validation phase
  - One or more scores < 80: trigger re-score loop for failing artifacts
  - Gate status is recorded in `pipeline-state.yaml`
  - Verification report exists at `agent-output/artifacts/threshold-verification.md`
- **Output path:** `agent-output/artifacts/threshold-verification.md`

### SC3 — Review Audit Trail
- **Title:** Generate complete audit trail of all review and scoring activity
- **Owner:** research-scientist
- **Priority:** P2
- **Acceptance criteria:**
  - Every review action is timestamped and attributed
  - Score changes between re-score iterations are tracked
  - Escalation events are recorded with reasons
  - Audit trail exists at `agent-output/artifacts/review-audit-trail.md`
- **Output path:** `agent-output/artifacts/review-audit-trail.md`

## Re-Score Loop Rules

When an artifact scores below the quality threshold (score < 80), the following automatic re-score loop governs remediation:

### Loop Rules

1. **Trigger.** Any artifact scoring < 80 on initial review triggers the re-score loop.
2. **Iteration 1.** The artifact owner receives the review findings and produces a revised version. The artifact is re-scored.
   - If score >= 80: loop ends, artifact passes.
   - If score < 80: proceed to Iteration 2.
3. **Iteration 2.** The artifact owner receives a second round of findings, focusing on issues not resolved in Iteration 1. The artifact is re-scored.
   - If score >= 80: loop ends, artifact passes.
   - If score < 80: proceed to Iteration 3.
4. **Iteration 3 (Final).** The artifact owner receives all accumulated findings. The Principal Investigator is notified that this is the final attempt. The artifact is re-scored.
   - If score >= 80: loop ends, artifact passes.
   - If score < 80: artifact is **escalated** to P2 via the escalation-manager. The artifact is flagged as `failed` and requires human intervention.
5. **Max retries.** Maximum 3 re-score iterations per artifact. No automated retries beyond iteration 3.
6. **Escalation.** On escalation, the following data is bundled and sent to the escalation-manager:
   - Artifact path
   - All review records (iterations 1-3)
   - Score history
   - Root cause summary

### State Tracking

Each re-score iteration is tracked in the task's metadata within `pipeline-state.yaml`:

```yaml
re_score_loop:
  artifact: <path>
  iterations:
    - number: 1
      score: <0-100>
      findings: <summary>
      status: retry | passed | escalated
    - number: 2
      score: <0-100>
      findings: <summary>
      status: retry | passed | escalated
    - number: 3
      score: <0-100>
      findings: <summary>
      status: retry | passed | escalated
  final_status: passed | escalated
  escalated_at: <UTC ISO-8601 | null>
```

## Error Recovery

- **Missing prerequisite:** If a required tool or dependency is unavailable, report it clearly with the exact command to install or path to check. Do not silently skip.
- **Malformed input:** Validate key fields before processing. On failure, report the exact field name and expected format. Do not proceed with partial data.
- **Timeout:** Set a 30-second budget for any blocking operation (MCP call, script execution, DB query). If exceeded, write partial results to `agent-output/partial/` and note what completed vs. what timed out.
- **Empty result:** If no data matches the query, produce a valid empty output (not an error) with a note explaining the search scope and suggesting next steps.
- **Partial failure:** If some sub-tasks succeed and others fail, report the split clearly: which succeeded, which failed, and whether the successes are usable independently.

## Usage

The Pipeline Director invokes this skill when entering the Review or Validation phase:
- Call `Skill("review-cycle", args="review")` for Review phase tasks (RV1-RV4 + SC1-SC3).
- Call `Skill("review-cycle", args="rescore")` for re-score loop rules and iteration management.

The skill returns task definitions and loop rules. The Pipeline Director registers tasks via `task_create` and enforces re-score loop iterations according to the rules defined here.
