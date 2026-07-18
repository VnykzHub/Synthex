#!/usr/bin/env python3
"""Unit tests for heavy-compute server.py — all 4 contract tools + helpers.

Covers sympy_solve (7 kinds + auto + edge cases), profile_script (valid,
missing, outside sandbox, with args), etl_validate (CSV parsing, grain check,
duplicate detection, empty, missing), docker_run (degrade gracefully),
_resolve_under_root, synthex_root.

Usage:  python tests/test_heavy_compute.py
"""
from __future__ import annotations

import csv
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

_heavy_compute_path = str(Path(__file__).resolve().parent.parent / "mcp-servers" / "heavy-compute")
sys.path.insert(0, _heavy_compute_path)

import server as hc  # noqa: E402


class TmpCase(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ["CLAUDE_PROJECT_DIR"] = self.tmp
        for d in ("user-input", "agent-output", "knowledgebase"):
            (Path(self.tmp) / d).mkdir(exist_ok=True)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _mk(self, rel: str, content: str = "") -> Path:
        p = Path(self.tmp) / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return p


# ------------------------------------------------------------------ sympy_solve

class TestSympySolve(unittest.TestCase):

    def _only_if_sympy(self):
        try:
            import sympy  # noqa: F401
        except ImportError:
            self.skipTest("sympy not installed")

    def test_solve_equation(self):
        self._only_if_sympy()
        r = hc.sympy_solve("x**2 - 4 = 0", kind="solve")
        self.assertIsNotNone(r["result"])
        self.assertIn("-2", str(r["result"]))

    def test_auto_solve_polynomial(self):
        self._only_if_sympy()
        r = hc.sympy_solve("x**2 - 4")
        self.assertIsNotNone(r["result"])
        self.assertIn("-2", str(r["result"]))

    def test_auto_solve_equation(self):
        self._only_if_sympy()
        r = hc.sympy_solve("x**2 = 4")
        self.assertIsNotNone(r["result"])
        self.assertIn("-2", str(r["result"]))

    def test_simplify(self):
        self._only_if_sympy()
        r = hc.sympy_solve("x + x + x", kind="simplify")
        self.assertIsNotNone(r["result"])
        self.assertIn("3*x", str(r["result"]))

    def test_factor(self):
        self._only_if_sympy()
        r = hc.sympy_solve("x**2 - y**2", kind="factor")
        self.assertIsNotNone(r["result"])
        self.assertIn("x - y", str(r["result"]))

    def test_integrate(self):
        self._only_if_sympy()
        r = hc.sympy_solve("x**2", kind="integrate")
        self.assertIsNotNone(r["result"])
        self.assertIn("x**3", str(r["result"]).replace(" ", ""))

    def test_diff(self):
        self._only_if_sympy()
        r = hc.sympy_solve("x**3", kind="diff")
        self.assertIsNotNone(r["result"])
        self.assertIn("3*x**2", str(r["result"]).replace(" ", ""))

    def test_auto_trig_identity(self):
        self._only_if_sympy()
        r = hc.sympy_solve("sin(x)**2 + cos(x)**2")
        self.assertIsNotNone(r["result"])
        self.assertEqual(str(r["result"]), "1")

    def test_unknown_kind(self):
        self._only_if_sympy()
        r = hc.sympy_solve("x", kind="bogus")
        self.assertIsNone(r["result"])
        self.assertIn("unknown kind", r["steps"][0])

    def test_steps_and_latex(self):
        self._only_if_sympy()
        r = hc.sympy_solve("x + 1", kind="simplify")
        self.assertGreater(len(r["steps"]), 0)
        self.assertIsInstance(r.get("latex"), str)

    def test_sympy_unavailable(self):
        """When sympy is not importable, return a clean error dict."""
        from unittest.mock import patch
        with patch.dict("sys.modules", {"sympy": None}):
            r = hc.sympy_solve("x", kind="solve")
        self.assertIsNone(r["result"])
        self.assertTrue(any("unavailable" in s.lower() for s in r["steps"]))


# -------------------------------------------------------------- profile_script

class TestProfileScript(TmpCase):

    def test_valid_script(self):
        s = self._mk("user-input/bench.py", "print(sum(range(1000)))")
        r = hc.profile_script(str(s))
        self.assertIn("499500", r.get("stdout", ""))
        self.assertGreater(r.get("wall_time_s", 0), 0)
        self.assertGreater(len(r.get("top_functions", [])), 0)

    def test_with_args(self):
        s = self._mk("user-input/args.py", "import sys; print(sys.argv[1:])")
        r = hc.profile_script(str(s), args=["--verbose"])
        self.assertIn("verbose", r.get("stdout", ""))

    def test_missing_script(self):
        r = hc.profile_script("nonexistent.py")
        self.assertIn("not found", r.get("stderr", ""))

    def test_outside_sandbox(self):
        r = hc.profile_script("/tmp/evil.py")
        self.assertIn("outside", r.get("stderr", ""))

    def test_empty_args(self):
        s = self._mk("user-input/ok.py", "print('ok')")
        r = hc.profile_script(str(s))
        self.assertIn("ok", r.get("stdout", ""))


# --------------------------------------------------------------- etl_validate

class TestETLValidate(TmpCase):

    def _csv(self, rel: str, rows: list[list[str]]) -> Path:
        p = Path(self.tmp) / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", newline="") as f:
            csv.writer(f).writerows(rows)
        return p

    def test_normal(self):
        p = self._csv("user-input/t.csv", [["id","name"],["1","alice"],["2","bob"]])
        r = hc.etl_validate(str(p))
        self.assertEqual(r.get("rows"), 2)
        self.assertEqual(len(r.get("columns", [])), 2)

    def test_grain_ok(self):
        p = self._csv("user-input/g.csv", [["oid","v"],["1","a"],["2","b"],["3","c"]])
        r = hc.etl_validate(str(p), expectations=json.dumps({"key_columns": ["oid"]}))
        self.assertTrue(r.get("grain_ok"))

    def test_grain_duplicate(self):
        p = self._csv("user-input/dup.csv", [["id","v"],["1","a"],["1","b"]])
        r = hc.etl_validate(str(p), expectations=json.dumps({"key_columns": ["id"]}))
        self.assertFalse(r.get("grain_ok", True))

    def test_empty_csv(self):
        p = self._csv("user-input/e.csv", [])
        r = hc.etl_validate(str(p))
        self.assertEqual(r.get("rows"), 0)

    def test_missing_file(self):
        r = hc.etl_validate("gone.csv")
        self.assertGreater(len(r.get("issues", [])), 0)


# ---------------------------------------------------------------- docker_run

class TestDockerRun(unittest.TestCase):

    def test_graceful_degrade(self):
        r = hc.docker_run("alpine:latest", ["echo", "hello"])
        self.assertIsInstance(r, dict)
        if "error" in r:
            self.assertIn("docker", r["error"].lower())


# --------------------------------------------------------- sandbox resolution

class TestSandbox(TmpCase):

    def test_synthex_root(self):
        self.assertEqual(str(hc.synthex_root()), self.tmp)

    def test_resolve_under_root_valid(self):
        f = self._mk("user-input/x.csv", "a")
        self.assertTrue(hc._resolve_under_root(str(f)).exists())

    def test_resolve_under_root_outside(self):
        with self.assertRaises(ValueError):
            hc._resolve_under_root("/tmp/abs_evil.py")


def tearDownModule():
    """Clean up sys.path after tests."""
    try:
        sys.path.remove(_heavy_compute_path)
    except ValueError:
        pass


if __name__ == "__main__":
    unittest.main(verbosity=2)
