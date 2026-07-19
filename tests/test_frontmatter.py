#!/usr/bin/env python3
"""Validate YAML frontmatter across all agent + skill .md files.

Checks: --- delimiters, name/description, model for agents, disable-model-invocation
for command skills, no unknown fields, no tabs, name matches filename/folder,
minimum line counts for fleshed-out files.

Usage:  python tests/test_frontmatter.py
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _parse_fm(path: Path) -> tuple[dict[str, str], list[str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    errors: list[str] = []
    if not lines or lines[0].strip() != "---":
        return {}, ["missing opening ---"]
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return {}, ["missing closing ---"]
    fields: dict[str, str] = {}
    for li in lines[1:end]:
        if "\t" in li:
            errors.append(f"tab in fm: {li!r}")
        if ":" in li:
            k, _, v = li.partition(":")
            k = k.strip()
            v = v.strip()
            # Strip matching quotes only (both single or both double)
            if len(v) >= 2 and ((v[0] == v[-1] == '"') or (v[0] == v[-1] == "'")):
                v = v[1:-1]
            if k in fields:
                errors.append(f"duplicate key {k!r}")
            fields[k] = v
    return fields, errors


VALID_AGENT = {"name", "description", "model", "tools", "skills"}
VALID_SKILL = {"name", "description", "disable-model-invocation", "allowed-tools", "superseded_by", "role"}
CMD_SKILLS = {"synthex-init", "delegate", "theory", "pipeline", "report",
              "experiment", "status", "audit", "memory"}
DOMAIN_SKILLS = {"task-tracking", "knowledge-graph", "data-lineage",
                 "experiment-design", "frontend-dev", "3d-modeling",
                 "presentation", "whitepaper", "prototyping"}


class TestAgentFM(unittest.TestCase):

    def _files(self):
        agents_dir = ROOT / "agents"
        if not agents_dir.is_dir():
            return []
        return sorted(agents_dir.glob("*.md"))

    def test_all_have_fm(self):
        for p in self._files():
            f, e = _parse_fm(p)
            self.assertEqual(e, [], f"{p.name}: {e}")
            for key in ("name", "description", "model"):
                self.assertIn(key, f, f"{p.name}: missing {key}")

    def test_models_valid(self):
        for p in self._files():
            f, _ = _parse_fm(p)
            m = f.get("model")
            if m is None:
                self.fail(f"{p.name}: missing model field")
            self.assertIn(m, {"opus", "sonnet", "haiku"}, f"{p.name}: {m}")

    def test_no_unknown(self):
        for p in self._files():
            f, _ = _parse_fm(p)
            for k in f:
                self.assertIn(k, VALID_AGENT, f"{p.name}: unknown {k}")

    def test_name_matches_file(self):
        for p in self._files():
            self.assertEqual(_parse_fm(p)[0]["name"], p.stem, p.name)

    def test_min_lines(self):
        for p in self._files():
            n = len(p.read_text().splitlines())
            self.assertGreaterEqual(n, 40, f"{p.name}: {n} lines < 40")


class TestSkillFM(unittest.TestCase):

    def _files(self):
        skills_dir = ROOT / "skills"
        if not skills_dir.is_dir():
            return []
        return sorted(skills_dir.glob("*/SKILL.md"))

    def test_all_have_fm(self):
        for p in self._files():
            f, e = _parse_fm(p)
            self.assertEqual(e, [], f"{p.relative_to(ROOT)}: {e}")
            for key in ("name", "description"):
                self.assertIn(key, f, f"{p.relative_to(ROOT)}: missing {key}")

    def test_no_unknown(self):
        for p in self._files():
            for k in _parse_fm(p)[0]:
                self.assertIn(k, VALID_SKILL, f"{p.relative_to(ROOT)}: unknown {k}")

    def test_cmd_skills_disable_invocation(self):
        for p in self._files():
            if p.parent.name in CMD_SKILLS:
                f, _ = _parse_fm(p)
                self.assertIn("disable-model-invocation", f,
                              f"{p.parent.name}: should set disable-model-invocation: true")
                self.assertEqual(f.get("disable-model-invocation"), "true",
                                 f"{p.parent.name}: disable-model-invocation should be 'true'")

    def test_name_matches_folder(self):
        for p in self._files():
            self.assertEqual(_parse_fm(p)[0]["name"], p.parent.name,
                             f"{p.relative_to(ROOT)}")

    def test_domain_skills_min_lines(self):
        for p in self._files():
            if p.parent.name in DOMAIN_SKILLS:
                n = len(p.read_text().splitlines())
                self.assertGreaterEqual(n, 32, f"{p.relative_to(ROOT)}: {n} lines < 32")


if __name__ == "__main__":
    unittest.main(verbosity=2)
