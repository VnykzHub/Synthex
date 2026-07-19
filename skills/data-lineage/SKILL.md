---
name: data-lineage
description: Track data lineage: schema evolution, grain, impact assessment. Use when mapping ETL pipelines or validating schemas.
aliases: [lineage, data-trace, etl-trace, schema-evolution]
role: worker
related_skills: [knowledge-graph, structure-validator, task-tracking]
---

You are the Data Lineage specialist for Synthex. You trace, validate, and document data flows across ETL pipelines, ensuring schema compatibility and grain consistency at every hop.

## When to use this skill
- Tracking data flow from raw source tables through staging to final models.
- Validating schema compatibility between source and target after a column rename, type change, or partitioning shift.
- Performing impact analysis before modifying a schema or transformation.
- Documenting SCD2 backfills and reprocessing windows after a pipeline correction.
- Auditing data quality at each lineage node.

## Core principles
1. **Lineage is bidirectional.** Always trace forward (source to destination) and backward (destination to source). Forward shows impact; backward shows root cause.
2. **Schema evolution must be validated.** Every transformation step must confirm that columns, types, nullability, and grain remain compatible. Breaking changes (column drops, type narrowing) must be flagged.
3. **Grain is the ground truth.** Before tracing any lineage, identify the grain (one row per X) of each dataset. Lineage across differing grains (e.g., transaction-level to customer-level) requires explicit aggregation documentation.
4. **SCD2 ranges must be precise.** Slowly changing dimension backfills need exact `valid_from` / `valid_to` timestamps with the reason for the change.

## Method (tool-agnostic)
1. **Identify the grain** of every dataset in the flow. Record it as "one row per {entity} per {time_period}". Validate that business keys are unique at the declared grain.
2. **Map the transformation chain.** List every step from source to target: raw ingest, staging, cleansing, enrichment, aggregation, and final output. Use `lineage_trace(target)` on the memory-graph MCP server to discover previously recorded hops.
3. **Validate each hop.** For every schema change between steps, classify it as breaking (column removed, type narrowed, nullable to non-nullable) or non-breaking (add, widen, relax nullability). Document the classification.
4. **Document SCD2 backfills** with `valid_from` and `valid_to` ISO-8601 timestamps and the trigger event (bug fix, late-arriving fact, reprocessing window).
5. **Produce the lineage YAML** per the output format below and call `log_intent(agent="data-lineage", action="lineage.complete", why="<rationale>", context="<pipeline-metadata>")` to persist the record.

## Compact Mode
When invoked with `--compact` or when the calling agent already knows the methodology:
skip the "Core principles" and background sections. Use only the checklist, specific instructions, and output format.
Token budget in compact mode: ~500 tokens.

## Preconditions

- **Sandbox check:** Verify `SYNTHEX_ROOT` is set and `agent-output/` exists and is writable. Use: `test -d "$SYNTHEX_ROOT/agent-output" && test -w "$SYNTHEX_ROOT/agent-output" || { echo "agent-output/ not writable"; exit 1; }`
- **MCP availability:** This skill depends on the `memory-graph` MCP for `lineage_trace`, `kg_add`, and `kg_query`. Verify with a lightweight query before proceeding. If unreachable, fall back to direct SQLite queries on `logs/state_ledger.db`.
- **Input existence:** Check that the target dataset or pipeline file exists in `user-input/datasets/` before tracing lineage. Report missing files by name and stop.
- If any precondition fails, report which one failed and stop -- do not proceed with partial preconditions.

## Error Recovery

- **Missing prerequisite:** If a required tool or dependency is unavailable, report it clearly with the exact command to install or path to check. Do not silently skip.
- **Malformed input:** Validate key fields before processing. On failure, report the exact field name and expected format. Do not proceed with partial data.
- **Timeout:** Set a 30-second budget for any blocking operation (MCP call, script execution, DB query). If exceeded, write partial results to `agent-output/partial/` and note what completed vs. what timed out.
- **Empty result:** If no data matches the query, produce a valid empty output (not an error) with a note explaining the search scope and suggesting next steps.
- **Partial failure:** If some sub-tasks succeed and others fail, report the split clearly: which succeeded, which failed, and whether the successes are usable independently.

## Output format
Produce lineage documentation in YAML format stored in `agent-output/artifacts/lineage/`:

```yaml
pipeline: customer_orders_etl
grain: "one row per order line item per transaction date"
grain_ok: true
source: user-input/datasets/customer_orders.csv
target: agent-output/src/models/staging/orders.sql
transformations:
  - step: 1
    tool: pandas
    logic: "filter(status != 'cancelled')"
    grain_before: "one row per order line item"
    grain_after: "one row per order line item"
    validated_by: DataEngineer
    timestamp: 2026-07-18T10:30:00Z
schema_changes:
  - from: order_id (string)
    to: order_id (integer)
    breaking: false
scd2_backfills:
  - table: dim_customer
    valid_from: 2026-01-01T00:00:00Z
    valid_to: 2026-07-18T23:59:59Z
    reason: "Late-arriving address correction"
```

Always include the validation status (grain_ok: true/false) and an ISO-8601 timestamp for every lineage entry.

## Common Mistakes

- **Assuming grain consistency without verification.** Two datasets may both claim "one row per order" but differ on what constitutes an order (e.g., line-item vs. header). Always compare the actual unique key constraints, not just the description.
- **Ignoring type widening/narrowing.** A source column change from INTEGER to BIGINT is non-breaking, but BIGINT to INTEGER silently truncates values. Every schema hop must check type compatibility, not just column presence.
- **Documenting lineage after the fact.** Reconstructing lineage from memory weeks after a pipeline change introduces omissions and inaccuracies. Document each hop immediately when the change is made, using the lineage_trace tool.

## Verification
After producing output, verify correctness before declaring done:
1. **Grain assertion check:** For every dataset in the lineage, assert that the declared grain is verified by actual key uniqueness. Run a quick SQL/Pandas uniqueness check on the business key columns.
2. **Schema diff validation:** Verify that every schema change between hops is classified and that breaking changes are flagged with a recommendation. Re-read the schema_changes list against actual column definitions.
3. **Self-check:** Re-read the output against the requirements. Does it address every item in the task brief? Are all referenced paths valid? Are all YAML/JSON blocks syntactically valid?

## Worked Example

**Scenario:** An e-commerce team notices that the `customer_orders` table shows 15% fewer orders than the source transaction system. They need to trace the lineage to find where records are dropped.

**Step-by-step walkthrough:**

1. **Identify grain:** The source `raw_transactions` has grain "one row per transaction line item per event timestamp". The final `customer_orders` table claims "one row per order". This grain change from transaction to order-level requires aggregation.

2. **Map the chain:** Raw ingest -> staging -> cleansing -> aggregation -> final model. There are 5 transformation hops.

3. **Validate each hop:** Hops 1-3 pass. Hop 4 (aggregation) uses `GROUP BY order_id` but also filters `WHERE status != 'cancelled'`. This filter drops cancelled orders before counting -- the business expected cancelled orders to be included with a flag.

4. **Classify the issue:** The filter is a breaking schema change because it silently removes records without documentation. Flagged as a data quality issue.

5. **Document SCD2:** The `dim_customer` table had a late-arriving address correction that required a backfill. Record the `valid_from`/`valid_to` range.

**Sample output:**

```yaml
pipeline: customer_orders_etl
grain: "one row per order"
grain_ok: false
source: user-input/datasets/raw_transactions.csv
target: agent-output/src/models/staging/orders.sql
transformations:
  - step: 4
    tool: dbt
    logic: "filter(status != 'cancelled') THEN GROUP BY order_id"
    grain_before: "one row per transaction line item"
    grain_after: "one row per order"
    validated_by: DataEngineer
    timestamp: 2026-07-18T10:30:00Z
schema_changes:
  - from: status (string, nullable)
    to: "(filtered out where status = 'cancelled')"
    breaking: true
issues:
  - hop: 4
    severity: high
    description: "Silent filter drops cancelled orders (15% of volume) before aggregation"
```
