# Status — Reference

## SQLite Query Examples with Filters

```sql
-- Filter by date range
SELECT * FROM run_log
WHERE created_at BETWEEN '2026-07-01' AND '2026-07-19'
ORDER BY created_at DESC;

-- Multi-condition filter with status
SELECT run_id, skill_name, status, duration_ms
FROM run_log
WHERE status IN ('FAILED', 'TIMEOUT')
  AND duration_ms > 5000
  AND skill_name LIKE 'pipeline/%'
ORDER BY duration_ms DESC;

-- Aggregate summary by status
SELECT status, COUNT(*) AS cnt,
       ROUND(AVG(duration_ms), 0) AS avg_ms,
       MAX(created_at) AS last_run
FROM run_log
WHERE created_at >= date('now', '-7 days')
GROUP BY status;

-- Search log messages
SELECT run_id, timestamp, message
FROM run_log
WHERE message LIKE '%OOM%' OR message LIKE '%MemoryError%'
ORDER BY timestamp DESC
LIMIT 20;
```

## Markdown Table Formatting

```markdown
| Run ID | Skill | Status | Duration | Started |
|--------|-------|--------|----------|---------|
| r-001 | pipeline/etl | PASS | 1.2s | 2026-07-19 10:00 |
| r-002 | pipeline/etl | FAIL | -- | 2026-07-19 10:05 |
| r-003 | 3d-modeling | PASS | 45.3s | 2026-07-19 10:10 |
```

- Align columns with colons: `:---` left, `---:` right, `:---:` center.
- Keep tables under 80 chars wide for terminal readability.
- Use `--` for null/empty cells instead of blank spaces.

## DB Connection Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `database is locked` | Concurrent write | Use WAL: `PRAGMA journal_mode=WAL;` |
| `disk I/O error` | Disk full / corruption | Check space; run `PRAGMA integrity_check;` |
| `no such table` | Wrong DB file | Verify path with `.databases` in sqlite3 |
| `UNIQUE constraint` | Duplicate insert | Use `INSERT OR IGNORE` / `INSERT OR REPLACE` |
| `out of memory` | Result set too large | Add LIMIT or `fetchmany(1000)` |
| Connection timeout | NFS latency | `PRAGMA busy_timeout = 5000;` |

- Always enable WAL mode for concurrent read/write.
- Run `PRAGMA quick_check;` as a lightweight integrity check before each session.
- Back up with `.backup` command, not file copy (avoids write-lock corruption).
