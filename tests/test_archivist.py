#!/usr/bin/env python3
"""Runtime test for audit-archivist/archivist.py.

Tests: ensure_schema, query_task_counts, tick (writes snapshot + status line),
--once exit, main() return codes, utc_now_iso format, interval resolution.

Usage:  python tests/test_archivist.py
"""
from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

_archivist_path = str(Path(__file__).resolve().parent.parent / "monitors" / "audit-archivist")
sys.path.insert(0, _archivist_path)

import archivist as aa  # noqa: E402


class TmpCase(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.logs = os.path.join(self.tmp, "logs")
        os.environ["CLAUDE_PROJECT_DIR"] = self.tmp

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestEnsureSchema(TmpCase):

    def test_creates(self):
        i, s = aa.ensure_schema(self.logs)
        self.assertTrue(os.path.isfile(i))
        self.assertTrue(os.path.isfile(s))

    def test_idempotent(self):
        aa.ensure_schema(self.logs)
        aa.ensure_schema(self.logs)

    def test_tables(self):
        i, s = aa.ensure_schema(self.logs)
        with sqlite3.connect(i) as c:
            names = [r[0] for r in c.execute(
                "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        for t in ("intents", "tasks"):
            self.assertIn(t, names)
        with sqlite3.connect(s) as c:
            names = [r[0] for r in c.execute(
                "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        for t in ("state_ledger", "kg_triples"):
            self.assertIn(t, names)

    def test_column_schema(self):
        i, s = aa.ensure_schema(self.logs)
        # Verify intents columns exist (NOT NULL not enforced in current schema)
        with sqlite3.connect(i) as c:
            cols = {r[1]: r for r in c.execute("PRAGMA table_info(intents)").fetchall()}
        for col_name in ("agent", "action", "why"):
            self.assertIsNotNone(cols.get(col_name), f"missing column {col_name}")


class TestQueryTaskCounts(TmpCase):

    def test_empty(self):
        i, _ = aa.ensure_schema(self.logs)
        self.assertEqual(aa.query_task_counts(i), (0, 0, 0))

    def test_counts(self):
        i, _ = aa.ensure_schema(self.logs)
        with sqlite3.connect(i) as c:
            c.execute("INSERT INTO tasks (id,title,status) VALUES ('a','a','pending')")
            c.execute("INSERT INTO tasks (id,title,status) VALUES ('b','b','in-progress')")
            c.execute("INSERT INTO tasks (id,title,status) VALUES ('c','c','pending')")
        self.assertEqual(aa.query_task_counts(i), (3, 2, 1))

    def test_missing_db(self):
        self.assertEqual(aa.query_task_counts("/nonexistent/x.db"), (0, 0, 0))


class TestTick(TmpCase):

    def test_status_line_format(self):
        i, s = aa.ensure_schema(self.logs)
        line = aa.tick(i, s)
        self.assertIn("[archivist]", line)
        self.assertIn("tasks", line)
        self.assertIn("@", line)

    def test_writes_snapshot(self):
        i, s = aa.ensure_schema(self.logs)
        aa.tick(i, s)
        with sqlite3.connect(s) as c:
            n = c.execute(
                "SELECT COUNT(*) FROM state_ledger WHERE event_type='state.snapshot'"
            ).fetchone()[0]
        self.assertGreater(n, 0)

    def test_reflects_counts(self):
        i, s = aa.ensure_schema(self.logs)
        with sqlite3.connect(i) as c:
            c.execute("INSERT INTO tasks (id,title,status) VALUES ('x','t1','pending')")
            c.execute("INSERT INTO tasks (id,title,status) VALUES ('y','t2','in-progress')")
        line = aa.tick(i, s)
        self.assertIn("2 tasks", line)
        self.assertIn("1 in-progress", line)


class TestMain(TmpCase):

    def test_once_ok(self):
        self.assertEqual(aa.main(["--logs-dir", self.logs, "--once"]), 0)

    def test_bad_path(self):
        # Use a path guaranteed to fail: parent is a file, not a directory.
        f = os.path.join(self.tmp, "notadir", "sub")
        with open(os.path.join(self.tmp, "notadir"), "w") as fh:
            fh.write("block")
        self.assertNotEqual(aa.main(["--logs-dir", f, "--once"]), 0)


class TestUtils(unittest.TestCase):

    def test_utc_now_iso(self):
        ts = aa.utc_now_iso()
        self.assertIn("T", ts)
        self.assertIn("Z", ts)
        # Verify millisecond precision: three digits before Z
        ms_part = ts.split(".")[1]
        self.assertEqual(len(ms_part), 4)  # 3 digits + Z

    def test_resolve_root(self):
        root = aa.resolve_synthex_root()
        self.assertIsInstance(root, str)
        self.assertTrue(os.path.isdir(root))

    def test_interval_default(self):
        self.assertEqual(aa.resolve_interval(None), 300)

    def test_interval_cli(self):
        self.assertEqual(aa.resolve_interval(60), 60)

    def test_interval_env(self):
        os.environ["SYNTHEX_ARCHIVIST_INTERVAL"] = "120"
        self.assertEqual(aa.resolve_interval(None), 120)
        del os.environ["SYNTHEX_ARCHIVIST_INTERVAL"]

    def test_interval_env_invalid(self):
        os.environ["SYNTHEX_ARCHIVIST_INTERVAL"] = "nope"
        self.assertEqual(aa.resolve_interval(None), 300)


def tearDownModule():
    """Clean up sys.path after tests."""
    try:
        sys.path.remove(_archivist_path)
    except ValueError:
        pass


if __name__ == "__main__":
    unittest.main(verbosity=2)
