#!/usr/bin/env python3
"""Audit Archivist monitor.

Continuous state/intent telemetry daemon for Synthex. On each tick it reads
task counts from ``logs/intents.db``, writes a ``state.snapshot`` row into
``logs/state_ledger.db``, and prints exactly one status line to stdout (each
line is surfaced as a Claude notification by the monitor runner).

Stdlib only (Python 3.12). Conforms to docs/DATA_CONTRACTS.md sections 1 & 2.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone

# --- DATA_CONTRACTS.md section 2 schema (verbatim, CREATE ... IF NOT EXISTS) ---

INTENTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS intents (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  ts        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  agent     TEXT,
  action    TEXT,
  why       TEXT,
  task_id   TEXT,
  context   TEXT
);
CREATE TABLE IF NOT EXISTS tasks (
  id          TEXT PRIMARY KEY,
  title       TEXT NOT NULL,
  priority    TEXT DEFAULT 'medium',
  status      TEXT DEFAULT 'pending',
  assigned_to TEXT,
  created_at  TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  updated_at  TEXT,
  completed_at TEXT
);
"""

STATE_LEDGER_SCHEMA = """
CREATE TABLE IF NOT EXISTS state_ledger (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  ts         TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  agent      TEXT,
  event_type TEXT,
  details    TEXT
);
CREATE TABLE IF NOT EXISTS kg_triples (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  subject   TEXT, predicate TEXT, object TEXT, source TEXT,
  ts        TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
"""


def utc_now_iso() -> str:
    """UTC ISO-8601 with millisecond precision, e.g. 2026-07-18T19:45:12.031Z."""
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def resolve_synthex_root() -> str:
    """DATA_CONTRACTS section 1: $CLAUDE_PROJECT_DIR else $PWD."""
    root = os.environ.get("CLAUDE_PROJECT_DIR")
    if root:
        return root
    return os.environ.get("PWD") or os.getcwd()


def resolve_logs_dir(logs_dir: str | None) -> str:
    """Explicit --logs-dir wins; else SYNTHEX_ROOT/logs."""
    if logs_dir:
        return logs_dir
    return os.path.join(resolve_synthex_root(), "logs")


def ensure_schema(logs_dir: str) -> tuple[str, str]:
    """Create logs dir + both DBs with the contract schema. Idempotent."""
    os.makedirs(logs_dir, exist_ok=True)
    intents_db = os.path.join(logs_dir, "intents.db")
    state_db = os.path.join(logs_dir, "state_ledger.db")
    with sqlite3.connect(intents_db) as con:
        con.executescript(INTENTS_SCHEMA)
    with sqlite3.connect(state_db) as con:
        con.executescript(STATE_LEDGER_SCHEMA)
    return intents_db, state_db


def query_task_counts(intents_db: str) -> tuple[int, int, int]:
    """Return (total, pending, in_progress). Tolerates missing/empty DB/table."""
    try:
        with sqlite3.connect(intents_db) as con:
            cur = con.execute(
                "SELECT "
                "COUNT(*), "
                "SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END), "
                "SUM(CASE WHEN status='in-progress' THEN 1 ELSE 0 END) "
                "FROM tasks"
            )
            row = cur.fetchone()
    except sqlite3.Error:
        return 0, 0, 0
    if not row:
        return 0, 0, 0
    total = row[0] or 0
    pending = row[1] or 0
    in_progress = row[2] or 0
    return total, pending, in_progress


def query_pipeline_phases(state_db: str) -> tuple[str | None, int, int]:
    """Return (current_phase, phases_done, phases_total) if pipeline_phases table exists, else (None, 0, 0)."""
    try:
        with sqlite3.connect(state_db) as con:
            cur = con.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name='pipeline_phases'"
            )
            if not cur.fetchone():
                return None, 0, 0
            cur = con.execute(
                "SELECT phase_name, phase_order, total_phases "
                "FROM pipeline_phases WHERE status='active' LIMIT 1"
            )
            row = cur.fetchone()
            if row:
                return row[0], row[1], row[2]
    except sqlite3.Error:
        pass
    return None, 0, 0


def query_experiment_iterations(state_db: str) -> int:
    """Count prior state.snapshot events for this archivist to derive iteration number."""
    try:
        with sqlite3.connect(state_db) as con:
            cur = con.execute(
                "SELECT COUNT(*) FROM state_ledger "
                "WHERE agent='audit-archivist' AND event_type='state.snapshot'"
            )
            row = cur.fetchone()
            return (row[0] or 0) + 1
    except sqlite3.Error:
        return 1


def tick(intents_db: str, state_db: str) -> str:
    """Run one snapshot: read counts, write ledger row, return the status line."""
    total, pending, in_progress = query_task_counts(intents_db)
    phase_name, phase_done, phase_total = query_pipeline_phases(state_db)
    iteration = query_experiment_iterations(state_db)
    ts = utc_now_iso()

    details_dict = {
        "tasks_total": total,
        "pending": pending,
        "in_progress": in_progress,
        "experiment_iterations": iteration,
        "ts": ts,
    }
    if phase_name:
        details_dict["phase"] = phase_name
        details_dict["phase_done"] = phase_done
        details_dict["phase_total"] = phase_total

    details = json.dumps(details_dict)

    with sqlite3.connect(state_db) as con:
        con.execute(
            "INSERT INTO state_ledger (ts, agent, event_type, details) "
            "VALUES (?, ?, ?, ?)",
            (ts, "audit-archivist", "state.snapshot", details),
        )

    if phase_name:
        return (
            f"[archivist] phase={phase_name} {phase_done}/{phase_total} done, "
            f"{total} tasks "
            f"({in_progress} in-progress, {pending} pending) @ {ts}"
        )
    return (
        f"[archivist] {total} tasks "
        f"({in_progress} in-progress, {pending} pending) @ {ts}"
    )


def resolve_interval(cli_interval: int | None) -> int:
    """--interval wins, then env SYNTHEX_ARCHIVIST_INTERVAL, then default 300."""
    if cli_interval is not None:
        return cli_interval
    env_val = os.environ.get("SYNTHEX_ARCHIVIST_INTERVAL")
    if env_val:
        try:
            return int(env_val)
        except ValueError:
            pass
    return 300


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Synthex Audit Archivist monitor.")
    ap.add_argument(
        "--logs-dir",
        default=None,
        help="Logs directory holding the SQLite DBs "
        "(default: $SYNTHEX_ROOT/logs).",
    )
    ap.add_argument(
        "--interval",
        type=int,
        default=None,
        help="Seconds between ticks (default 300; "
        "env SYNTHEX_ARCHIVIST_INTERVAL overrides the default).",
    )
    ap.add_argument(
        "--once",
        action="store_true",
        help="Run a single tick then exit (for tests).",
    )
    args = ap.parse_args(argv)

    logs_dir = resolve_logs_dir(args.logs_dir)
    interval = resolve_interval(args.interval)

    # Ensure schema up front so a bad path fails loudly before the loop.
    try:
        intents_db, state_db = ensure_schema(logs_dir)
    except OSError as exc:
        print(f"[archivist] fatal: cannot prepare logs dir {logs_dir}: {exc}",
              file=sys.stderr, flush=True)
        return 1

    while True:
        try:
            line = tick(intents_db, state_db)
            print(line, flush=True)
        except Exception as exc:  # never let a transient error kill the loop
            print(f"[archivist] tick error: {exc}", file=sys.stderr, flush=True)
        if args.once:
            return 0
        try:
            time.sleep(interval)
        except KeyboardInterrupt:
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
