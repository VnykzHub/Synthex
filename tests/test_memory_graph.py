#!/usr/bin/env python3
"""Comprehensive unit tests for synthex_memory.py — all 10 contract tools.

Covers: resolve_root, init_db, chunk_text, HashingEmbedder, VectorStore
(pure-python cosine path), _cosine, vector_index, vector_retrieve, kg_add,
kg_query, lineage_trace, log_intent, task_create, task_update, task_list,
drain_queue, plus edge cases: missing files, empty text, unicode, special
chars, empty queries, zero-result searches.

Usage:  python tests/test_memory_graph.py
        CLAUDE_PROJECT_DIR=/tmp/test python tests/test_memory_graph.py
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "mcp-servers" / "memory-graph"))

import synthex_memory as sm  # noqa: E402


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

class TmpCase(unittest.TestCase):
    """Base: creates a temp SYNTHEX_ROOT and resets global state before each test."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ["CLAUDE_PROJECT_DIR"] = self.tmp
        sm._store = None
        sm._encode_fn = None

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _mkfile(self, name: str, content: str) -> Path:
        p = Path(self.tmp) / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p


# --------------------------------------------------------------------------- #
# resolve_root / init_db
# --------------------------------------------------------------------------- #

class TestRootAndDB(TmpCase):

    def test_resolve_root_env(self):
        self.assertEqual(str(sm.resolve_root()), self.tmp)

    def test_resolve_root_fallback(self):
        del os.environ["CLAUDE_PROJECT_DIR"]
        self.assertTrue(sm.resolve_root().is_dir())

    def test_init_db_creates_both(self):
        sm.init_db()
        self.assertTrue((Path(self.tmp) / "logs" / "intents.db").exists())
        self.assertTrue((Path(self.tmp) / "logs" / "state_ledger.db").exists())

    def test_init_db_idempotent(self):
        sm.init_db()
        sm.init_db()

    def test_init_db_tables(self):
        sm.init_db()
        conn = sqlite3.connect(str(Path(self.tmp) / "logs" / "intents.db"))
        names = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        conn.close()
        for t in ("intents", "tasks"):
            self.assertIn(t, names)

        conn = sqlite3.connect(str(Path(self.tmp) / "logs" / "state_ledger.db"))
        names = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        conn.close()
        for t in ("state_ledger", "kg_triples"):
            self.assertIn(t, names)


# --------------------------------------------------------------------------- #
# Chunker
# --------------------------------------------------------------------------- #

class TestChunker(unittest.TestCase):

    def test_single_chunk(self):
        chunks = sm.chunk_text("hello world")
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], "hello world")

    def test_empty(self):
        self.assertEqual(sm.chunk_text(""), [])
        self.assertEqual(sm.chunk_text("   "), [])

    def test_multi(self):
        chunks = sm.chunk_text("x" * 3000, chunk_size=1000, overlap=200)
        self.assertGreater(len(chunks), 2)
        for c in chunks:
            self.assertLessEqual(len(c), 1000)

    def test_overlap_precision(self):
        chunks = sm.chunk_text("ABCDEFGHIJ", chunk_size=5, overlap=2)
        self.assertEqual(chunks[0], "ABCDE")
        self.assertEqual(chunks[1], "DEFGH")

    def test_unicode(self):
        chunks = sm.chunk_text("こんにちは世界" * 80, chunk_size=100, overlap=20)
        self.assertGreater(len(chunks), 1)

    def test_exact_boundary(self):
        chunks = sm.chunk_text("x" * 2000, chunk_size=2000, overlap=400)
        self.assertEqual(len(chunks), 1)


# --------------------------------------------------------------------------- #
# Embedder
# --------------------------------------------------------------------------- #

class TestEmbedder(unittest.TestCase):

    def test_dimension(self):
        self.assertEqual(len(sm.HashingEmbedder(384).encode("test")), 384)

    def test_deterministic(self):
        he = sm.HashingEmbedder()
        self.assertEqual(he.encode("hello"), he.encode("hello"))

    def test_different(self):
        he = sm.HashingEmbedder()
        self.assertNotEqual(he.encode("hello"), he.encode("world"))

    def test_near_unit(self):
        for dim in (64, 128, 384):
            vec = sm.HashingEmbedder(dim).encode("the quick brown fox jumps over the lazy dog")
            norm = sum(v * v for v in vec) ** 0.5
            self.assertAlmostEqual(norm, 1.0, places=2)

    def test_short_input(self):
        self.assertEqual(len(sm.HashingEmbedder().encode("a")), 384)

    def test_long_input(self):
        self.assertEqual(len(sm.HashingEmbedder().encode("x" * 5000)), 384)

    def test_get_embedder(self):
        fn, label = sm._get_embedder()
        vec = fn("test")
        self.assertEqual(len(vec), 384)
        self.assertIn(label, ("sentence-transformers/all-MiniLM-L6-v2", "hashing-embedder"))


# --------------------------------------------------------------------------- #
# Cosine
# --------------------------------------------------------------------------- #

class TestCosine(unittest.TestCase):

    def test_identical(self):
        self.assertAlmostEqual(sm._cosine([1, 2, 3], [1, 2, 3]), 1.0, places=6)

    def test_orthogonal(self):
        self.assertAlmostEqual(sm._cosine([1, 0], [0, 1]), 0.0, places=6)

    def test_opposite(self):
        self.assertAlmostEqual(sm._cosine([1, 0], [-1, 0]), -1.0, places=6)

    def test_zero_vector(self):
        self.assertEqual(sm._cosine([0, 0], [1, 1]), 0.0)
        self.assertEqual(sm._cosine([1, 1], [0, 0]), 0.0)


# --------------------------------------------------------------------------- #
# VectorStore (always exercises the pure-python cosine path)
# --------------------------------------------------------------------------- #

class TestVectorStore(TmpCase):

    def test_creates_dir(self):
        os.environ.pop("SYNTHEX_VECTOR_BACKEND", None)
        sm._ensure_encode()
        store = sm._ensure_store(Path(self.tmp))
        self.assertTrue((Path(self.tmp) / "logs" / "vectors").exists())

    def test_add_and_search(self):
        sm._ensure_encode()
        store = sm._ensure_store(Path(self.tmp))
        store.add(sm._encode_fn("find me"),
                  {"chunk": "find me", "source": "a.txt", "ts": ""})
        results = store.search(sm._encode_fn("find me"), top_k=3)
        self.assertGreaterEqual(len(results), 1)

    def test_empty_store(self):
        sm._ensure_encode()
        results = sm._ensure_store(Path(self.tmp)).search(sm._encode_fn("x"), top_k=5)
        self.assertEqual(results, [])

    def test_top_k_limit(self):
        sm._ensure_encode()
        store = sm._ensure_store(Path(self.tmp))
        for i in range(10):
            store.add(sm._encode_fn(f"doc {i}"),
                      {"chunk": f"d{i}", "source": f"f{i}.txt", "ts": ""})
        self.assertEqual(len(store.search(sm._encode_fn("doc 5"), top_k=3)), 3)


# --------------------------------------------------------------------------- #
# vector_index
# --------------------------------------------------------------------------- #

class TestVectorIndex(TmpCase):

    def test_normal(self):
        self._mkfile("doc.txt", "Synthex is a multi-agent framework for Claude Code.")
        r = sm.vector_index(str(Path(self.tmp) / "doc.txt"), root=Path(self.tmp))
        self.assertGreaterEqual(r["indexed"], 1)

    def test_missing(self):
        r = sm.vector_index("/nonexistent/path.xyz", root=Path(self.tmp))
        self.assertEqual(r["indexed"], 0)
        self.assertEqual(r["error"], "file_not_found")

    def test_empty_file(self):
        self._mkfile("empty.txt", "")
        r = sm.vector_index(str(Path(self.tmp) / "empty.txt"), root=Path(self.tmp))
        self.assertEqual(r["indexed"], 0)

    def test_long_multi_chunk(self):
        self._mkfile("long.txt", "Synthex memory vault. " * 500)
        r = sm.vector_index(str(Path(self.tmp) / "long.txt"), root=Path(self.tmp))
        self.assertGreater(r["indexed"], 1)

    def test_unicode(self):
        self._mkfile("jp.txt", "日本語テスト。マルチエージェント。" * 20)
        r = sm.vector_index(str(Path(self.tmp) / "jp.txt"), root=Path(self.tmp))
        self.assertGreaterEqual(r["indexed"], 1)

    def test_special_path(self):
        self._mkfile("test (1) copy.txt", "special path test")
        r = sm.vector_index(str(Path(self.tmp) / "test (1) copy.txt"), root=Path(self.tmp))
        self.assertGreaterEqual(r["indexed"], 1)


# --------------------------------------------------------------------------- #
# vector_retrieve
# --------------------------------------------------------------------------- #

class TestVectorRetrieve(TmpCase):

    def setUp(self):
        super().setUp()
        self._mkfile("ml.txt", "Machine learning uses gradient descent for optimization.")

    def test_finds(self):
        sm.vector_index(str(Path(self.tmp) / "ml.txt"), root=Path(self.tmp))
        results = sm.vector_retrieve("gradient descent", top_k=3, root=Path(self.tmp))
        self.assertGreaterEqual(len(results), 1)

    def test_respects_top_k(self):
        sm.vector_index(str(Path(self.tmp) / "ml.txt"), root=Path(self.tmp))
        self.assertLessEqual(len(sm.vector_retrieve("model", top_k=1, root=Path(self.tmp))), 1)

    def test_empty_store(self):
        # fresh temp without indexed content
        t2 = tempfile.mkdtemp()
        os.environ["CLAUDE_PROJECT_DIR"] = t2
        sm._store = None
        sm._encode_fn = None
        self.assertEqual(sm.vector_retrieve("anything", root=Path(t2)), [])

    def test_empty_query(self):
        sm.vector_index(str(Path(self.tmp) / "ml.txt"), root=Path(self.tmp))
        self.assertIsInstance(sm.vector_retrieve("", top_k=3, root=Path(self.tmp)), list)


# --------------------------------------------------------------------------- #
# Knowledge Graph
# --------------------------------------------------------------------------- #

class TestKnowledgeGraph(TmpCase):

    def test_add_and_query(self):
        sm.kg_add("orders", "produces", "clean.parquet", source="de", root=Path(self.tmp))
        r = sm.kg_query(subject="orders", root=Path(self.tmp))
        self.assertGreaterEqual(len(r), 1)
        self.assertEqual(r[0]["predicate"], "produces")

    def test_query_all(self):
        sm.kg_add("A", "B", "C", root=Path(self.tmp))
        self.assertGreaterEqual(len(sm.kg_query(root=Path(self.tmp))), 1)

    def test_partial_match(self):
        sm.kg_add("customer_v2", "has_schema", "orders_schema.yaml", root=Path(self.tmp))
        r = sm.kg_query(object="schema", root=Path(self.tmp))
        self.assertGreaterEqual(len(r), 1)

    def test_no_match(self):
        self.assertEqual(sm.kg_query(subject="nonexistent_xyz", root=Path(self.tmp)), [])

    def test_special_chars(self):
        sm.kg_add("user's data", "maps to →", "スキーマ", root=Path(self.tmp))
        r = sm.kg_query(subject="user", root=Path(self.tmp))
        self.assertGreaterEqual(len(r), 1)

    def test_lineage_trace(self):
        sm.log_intent("de", "transform", "deduped on order_id", task_id="t1",
                       context="orders", root=Path(self.tmp))
        sm.kg_add("orders", "inputs", "raw.csv", root=Path(self.tmp))
        results = sm.lineage_trace("orders", root=Path(self.tmp))
        self.assertGreaterEqual(len(results), 1)


# --------------------------------------------------------------------------- #
# Intents & Tasks
# --------------------------------------------------------------------------- #

class TestIntentsAndTasks(TmpCase):

    def test_log_intent(self):
        r = sm.log_intent("PI", "delegate", "split into 3 subtasks",
                          task_id="t42", root=Path(self.tmp))
        self.assertGreater(r["id"], 0)

    def test_log_intent_empty(self):
        r = sm.log_intent("", "", "", root=Path(self.tmp))
        self.assertIn("id", r)

    def test_task_create(self):
        r = sm.task_create("Build ETL", priority="high", assigned_to="de", root=Path(self.tmp))
        self.assertEqual(r["title"], "Build ETL")
        self.assertEqual(r["status"], "pending")

    def test_task_create_defaults(self):
        r = sm.task_create("Simple", root=Path(self.tmp))
        self.assertEqual(r["status"], "pending")

    def test_task_update(self):
        tid = sm.task_create("test", root=Path(self.tmp))["id"]
        u = sm.task_update(tid, "in-progress", root=Path(self.tmp))
        self.assertEqual(u["status"], "in-progress")

    def test_task_update_completed(self):
        tid = sm.task_create("finish", root=Path(self.tmp))["id"]
        self.assertEqual(sm.task_update(tid, "completed", root=Path(self.tmp))["status"], "completed")

    def test_task_update_nonexistent(self):
        self.assertEqual(sm.task_update("ghost", "completed", root=Path(self.tmp))["id"], "ghost")

    def test_task_list_all(self):
        sm.task_create("A", root=Path(self.tmp))
        sm.task_create("B", root=Path(self.tmp))
        self.assertGreaterEqual(len(sm.task_list(root=Path(self.tmp))), 2)

    def test_task_list_filtered(self):
        tid = sm.task_create("in-prog task", root=Path(self.tmp))["id"]
        sm.task_update(tid, "in-progress", root=Path(self.tmp))
        filtered = sm.task_list(status="in-progress", root=Path(self.tmp))
        self.assertGreaterEqual(len(filtered), 1)
        self.assertTrue(all(t["status"] == "in-progress" for t in filtered))


# --------------------------------------------------------------------------- #
# drain_queue
# --------------------------------------------------------------------------- #

class TestDrainQueue(TmpCase):

    def test_processes(self):
        f = self._mkfile("q.txt", "queue index test")
        (Path(self.tmp) / "logs").mkdir(exist_ok=True)
        (Path(self.tmp) / "logs" / "index_queue.jsonl").write_text(
            json.dumps({"ts": "", "path": str(f)}) + "\n")
        r = sm.drain_queue(root=Path(self.tmp))
        self.assertGreaterEqual(r["processed"], 1)

    def test_missing_file(self):
        result = sm.drain_queue(root=Path(self.tmp))
        self.assertEqual(result["processed"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
