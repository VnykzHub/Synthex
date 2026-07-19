# Data Lineage — Reference

## SCD2 Backfill Patterns

```sql
-- Backfill missing Type 2 history from snapshot
INSERT INTO dim_customer_history
(customer_id, name, email, valid_from, valid_to, is_current)
SELECT
    customer_id,
    name,
    email,
    COALESCE(LAG(valid_to) OVER (PARTITION BY customer_id ORDER BY snapshot_date),
             snapshot_date) AS valid_from,
    snapshot_date AS valid_to,
    FALSE AS is_current
FROM (
    SELECT *,
        LAG(email) OVER (PARTITION BY customer_id ORDER BY snapshot_date) AS prev_email
    FROM stg_customer_snapshots
) sub
WHERE email <> prev_email OR prev_email IS NULL;
```

- **Effective vs snapshot date**: Use business-effective date when available; fall back to load timestamp.
- **Late-arriving records**: Insert with `valid_from = first_seen`, `valid_to = '9999-12-31'`, then split retroactively when history arrives.
- **Overlapping ranges**: Use `range_merge()` (PostgreSQL) to collapse contiguous Type 2 rows.

## Grain Validation — Composite Keys

```sql
-- Validate composite grain: (source_system, entity_id, effective_date)
SELECT source_system, entity_id, effective_date, COUNT(*)
FROM fact_transactions
GROUP BY source_system, entity_id, effective_date
HAVING COUNT(*) > 1;
```

- Declare grain as a tuple in lineage metadata: `grain: [source_system, entity_id, effective_date]`.
- Add a `grain_hash` column (MD5 of grain fields) as a physical uniqueness constraint.
- On grain-change detection, emit a lineage alert — downstream models need re-validation.
- Composite keys with nullable columns: COALESCE nulls to a sentinel before hashing.

## Schema Evolution Migration Examples

```sql
-- Add column with default (avoid long locks)
ALTER TABLE dim_product ADD COLUMN category_id INTEGER;
ALTER TABLE dim_product ALTER COLUMN category_id SET DEFAULT 0;
UPDATE dim_product SET category_id = 0 WHERE category_id IS NULL;
ALTER TABLE dim_product ALTER COLUMN category_id SET NOT NULL;

-- Rename column, preserve downstream lineage
ALTER TABLE fact_orders RENAME COLUMN order_total TO gross_amount;
CREATE VIEW fact_orders_legacy AS
    SELECT *, gross_amount AS order_total FROM fact_orders;
```

- Version lineage metadata alongside every schema migration.
- Use a `schema_hash` in the lineage catalog; downstream models pin to a specific hash and warn on mismatch.
- For breaking changes, keep a translation view for one full pipeline cycle before dropping old columns.
