---
name: scoring-framework
description: Weighted multi-dimension scoring system with failure classification and regression protection. Invoked by peer-validator, accuracy-auditor, and risk-identifier whenever they need to produce quantitative scores with defined weights and thresholds. Use when an agent needs weighted quality scoring with failure classification and regression protection.
role: worker
---

# scoring-framework

Weighted multi-dimension scoring system with failure classification and regression protection. This skill provides the standard method for computing composite scores from dimension-level inputs, classifying the severity of findings, and tracking scores against prior baselines to detect regression.

## When to use
- You need to compute a weighted total from multiple dimension scores
- You need to classify findings by severity (critical, major, minor, informational)
- You need to compare a current score against a prior baseline to detect regression or improvement
- You need to apply a consistent scoring methodology across reviews, audits, and risk assessments

## Core principles

1. **Weighted arithmetic.** Every dimension has a defined weight (0-100%, summing to 100%). The total is the sum of `score * weight` for all dimensions.
2. **Integrity.** Scores are integers 0-100. Weighted totals are floats to one decimal place.
3. **Transparency.** Every score must have a written justification. Unexplained scores are invalid.
4. **Regression must be flagged.** If a prior score exists, the delta must be computed and reported. Any negative delta greater than 5 points triggers a regression flag.
5. **Failure classification is structural.** Findings are classified by their nature, not their severity score. A critical failure in one dimension may have different severity than the same failure type in another.

## Default weights

| Dimension | Weight | Used by |
|-----------|--------|---------|
| Correctness | 30% | peer-validator |
| Quality | 20% | peer-validator |
| Performance | 15% | peer-validator |
| Security | 15% | peer-validator |
| Test coverage | 10% | peer-validator |
| Documentation | 10% | peer-validator |
| Source alignment | 30% | accuracy-auditor |
| Rule compliance | 25% | accuracy-auditor |
| Completeness | 20% | accuracy-auditor |
| Consistency | 15% | accuracy-auditor |
| Clarity | 10% | accuracy-auditor |

Custom weights may be provided by the caller for non-standard evaluations (e.g., risk assessments).

## Failure classification

Each finding associated with a score must be classified into one of:

| Classification | Definition | Required action |
|---------------|------------|-----------------|
| Critical | Blocks acceptance regardless of total score. Violates a hard requirement or introduces a safety/security issue. | Must be fixed before the artifact proceeds. |
| Major | Significant quality or correctness gap. Would meaningfully impact downstream consumers. | Should be fixed. Score cannot be considered final until resolved. |
| Minor | Surface-level issue. Does not affect correctness but deviates from conventions or best practices. | Should be noted and tracked. Does not block. |
| Informational | Observation or suggestion. Not a defect. | No action required. Included for completeness. |

## Regression protection

### Process
1. Before computing a new score, check if a prior score exists in `agent-output/reports/reviews/`, `agent-output/reports/audits/`, or `agent-output/reports/risks/` for the same artifact or a closely related one.
2. If a prior score exists, extract the weighted total and the per-dimension scores.
3. Compute the delta: `delta = current_score - prior_score`.
4. If delta is positive: report as improvement.
5. If delta is negative and abs(delta) <= 5: report as minor regression.
6. If delta is negative and abs(delta) > 5: **flag regression** prominently in the report. The artifact cannot pass unless the regression is justified by the artifact owner.

### Snapshot matching
Match artifacts by name, module path, or a provided baseline ID. If no prior score exists, state "No prior score — first assessment."

## Method
1. **Receive.** Accept a set of `{dimension_name: {score, weight, justification}}` tuples and an optional baseline ID or prior report path.
2. **Validate.** Ensure all weights sum to 100%, scores are integers 0-100, and every score has a non-empty justification. Reject any input that fails validation.
3. **Compute.** For each dimension: `weighted_score = score * (weight / 100)`. Sum to get `total`.
4. **Classify findings.** For any finding provided alongside the scores, apply the failure classification table.
5. **Check regression.** If a prior score exists, compute delta and flag if warranted.
6. **Return.** Return the computed total, per-dimension breakdown, failure classifications, and regression status.

## Preconditions

- **Sandbox check:** Verify `SYNTHEX_ROOT` is set and `agent-output/` exists and is writable. Use: `test -d "$SYNTHEX_ROOT/agent-output" && test -w "$SYNTHEX_ROOT/agent-output" || { echo "agent-output/ not writable"; exit 1; }`
- **MCP availability:** This skill has no hard MCP dependencies. It operates on provided data.
- **Input existence:** For regression checks, verify that prior score reports exist in `agent-output/reports/reviews/`, `agent-output/reports/audits/`, or `agent-output/reports/risks/`. If none exist, state "No prior score -- first assessment" and proceed.
- If any precondition fails, report which one failed and stop -- do not proceed with partial preconditions.

## Error Recovery

- **Missing prerequisite:** If a required tool or dependency is unavailable, report it clearly with the exact command to install or path to check. Do not silently skip.
- **Malformed input:** Validate key fields before processing. On failure, report the exact field name and expected format. Do not proceed with partial data.
- **Timeout:** Set a 30-second budget for any blocking operation (MCP call, script execution, DB query). If exceeded, write partial results to `agent-output/partial/` and note what completed vs. what timed out.
- **Empty result:** If no data matches the query, produce a valid empty output (not an error) with a note explaining the search scope and suggesting next steps.
- **Partial failure:** If some sub-tasks succeed and others fail, report the split clearly: which succeeded, which failed, and whether the successes are usable independently.

## Output format
Return a structured result:
```json
{
  "weighted_total": 84.7,
  "dimensions": [
    {"name": "Correctness", "score": 85, "weight": 0.30, "weighted": 25.5, "justification": "..."},
    {"name": "Quality", "score": 78, "weight": 0.20, "weighted": 15.6, "justification": "..."}
  ],
  "findings": [
    {"classification": "major", "description": "...", "dimension": "Correctness"}
  ],
  "regression": {
    "prior_score": 81.2,
    "prior_date": "2026-07-01",
    "delta": 3.5,
    "flagged": false
  }
}
```
