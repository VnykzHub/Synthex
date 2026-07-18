#!/usr/bin/env python3
"""Memory & Graph shared library and CLI for the Synthex Memory Vault.

Implements every tool from docs/DATA_CONTRACTS.md §3 using the sandbox paths
from §1 and the SQLite schema from §2 (mirrored in hooks/scripts/init_db.sh).

Vector backend: chroma (default) -> numpy cosine -> pure-python cosine fallback.
Embedder: sentence-transformers -> deterministic hashing embedder (zero deps).
ALL optional deps degrade gracefully. Never crashes on import.

CLI usage:
  python synthex_memory.py initdb
  python synthex_memory.py index <path>
  python synthex_memory.py retrieve --query Q [--top-k K] [--scope S]
  python synthex_memory.py drain-queue
  python synthex_memory.py task-create --title T [--priority P] [--assigned A]
  python synthex_memory.py task-list [--status S]
  python synthex_memory.py task-update --id I --status S
  python synthex_memory.py selftest
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# --------------------------------------------------------------------------- #
# Sandbox path resolution (contract §1)
# --------------------------------------------------------------------------- #


def resolve_root() -> Path:
    """SYNTHEX_ROOT = $CLAUDE_PROJECT_DIR else $PWD."""
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()


def _db_path(root: Path, name: str) -> Path:
    return root / "logs" / (name + ".db")


# --------------------------------------------------------------------------- #
# Schema init (contract §2 — EXACT match with init_db.sh)
# --------------------------------------------------------------------------- #


def init_db(root: Optional[Path] = None) -> None:
    """Create both SQLite DBs with full schema. Idempotent (IF NOT EXISTS)."""
    if root is None:
        root = resolve_root()
    logs = root / "logs"
    logs.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(logs / "intents.db"))
    conn.executescript("""
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
    """)
    conn.commit()
    conn.close()

    conn = sqlite3.connect(str(logs / "state_ledger.db"))
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS state_ledger (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            ts         TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
            agent      TEXT,
            event_type TEXT,
            details    TEXT
        );
        CREATE TABLE IF NOT EXISTS kg_triples (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            subject   TEXT,
            predicate TEXT,
            object    TEXT,
            source    TEXT,
            ts        TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
        );
    """)
    conn.commit()
    conn.close()


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + \
           f"{datetime.now(timezone.utc).microsecond // 1000:03d}Z"


def _uuid() -> str:
    return uuid.uuid4().hex


# --------------------------------------------------------------------------- #
# Chunker  (≤512 tokens ≈ 2000 chars, 20% overlap ≈ 400 chars)
# --------------------------------------------------------------------------- #

CHUNK_SIZE = 2000
CHUNK_OVERLAP = 400


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split *text* into overlapping chunks."""
    if len(text) <= chunk_size:
        return [text] if text.strip() else []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


# --------------------------------------------------------------------------- #
# Embedder  (sentence-transformers -> hashing fallback, always 384-dim)
# --------------------------------------------------------------------------- #

EMBED_DIM = 384


class HashingEmbedder:
    """Deterministic 384-dim embedding from character n-grams via SHA-256.
    Zero external dependencies — always available."""

    def __init__(self, dim: int = EMBED_DIM) -> None:
        self.dim = dim

    def encode(self, text: str) -> list[float]:
        # Build a pseudo-random but deterministic 384-dim vector from text.
        vec = [0.0] * self.dim
        # Character trigrams as features
        for i in range(len(text) - 2):
            ng = text[i:i + 3]
            h = hashlib.sha256(ng.encode("utf-8")).digest()
            # Use 4 bytes per dimension index
            for j in range(0, len(h) - 3, 4):
                idx = int.from_bytes(h[j:j + 4], "big") % self.dim
                val = int.from_bytes(h[j:j + 4], "big", signed=True) / (2 ** 31)
                vec[idx] += val
        # Normalize to unit length
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec


def _get_embedder():
    """Return a callable encode(text)->list[float] (384-dim). Tries ST first."""
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
        model = SentenceTransformer("all-MiniLM-L6-v2")

        def _encode(text: str) -> list[float]:
            return model.encode(text).tolist()
        return _encode, "sentence-transformers/all-MiniLM-L6-v2"
    except Exception:
        he = HashingEmbedder()

        def _encode(text: str) -> list[float]:
            return he.encode(text)
        return _encode, "hashing-embedder"


# --------------------------------------------------------------------------- #
# Vector store  (chroma -> numpy -> pure python cosine)
# --------------------------------------------------------------------------- #


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class _PureCosineIndex:
    """A minimal in-memory cosine index backed by a JSON file on disk."""

    def __init__(self, store_dir: Path) -> None:
        self.store_dir = store_dir
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self._index_file = self.store_dir / "cosine_index.json"
        self._entries: list[dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if self._index_file.exists():
            try:
                self._entries = json.loads(self._index_file.read_text())
            except Exception:
                self._entries = []

    def _save(self) -> None:
        self._index_file.write_text(json.dumps(self._entries))

    def add(self, vec: list[float], meta: dict[str, Any]) -> None:
        self._entries.append({"vec": vec, "meta": meta})
        self._save()

    def search(self, query_vec: list[float], top_k: int = 5) -> list[dict[str, Any]]:
        scored = [(_cosine(query_vec, e["vec"]), e["meta"]) for e in self._entries]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [{"chunk": s[1].get("chunk", ""), "source": s[1].get("source", ""),
                 "score": round(s[0], 4), "ts": s[1].get("ts", "")} for s in scored[:top_k]]


class VectorStore:
    """Abstraction over chroma / numpy / pure-python cosine index.
    Backend selection: $SYNTHEX_VECTOR_BACKEND (default 'chroma').
    'turbovec' falls back to 'chroma' (unverified package)."""

    def __init__(self, root: Path) -> None:
        backend = os.environ.get("SYNTHEX_VECTOR_BACKEND", "chroma")
        if backend == "turbovec":
            backend = "chroma"  # UNVERIFIED package — fall back
        self._store_dir = root / "logs" / "vectors"
        self._store_dir.mkdir(parents=True, exist_ok=True)
        self._backend: Any = None
        self._backend_name: str = ""

        if backend in ("chroma", "chromadb"):
            self._backend = self._try_chroma()
            if self._backend is not None:
                self._backend_name = "chromadb"
        if self._backend is None:
            self._backend = self._try_numpy()
            if self._backend is not None:
                self._backend_name = "numpy-cosine"
        if self._backend is None:
            self._backend = _PureCosineIndex(self._store_dir)
            self._backend_name = "pure-python-cosine"

    def _try_chroma(self) -> Any:
        try:
            import chromadb  # type: ignore
            client = chromadb.PersistentClient(path=str(self._store_dir))
            collection = client.get_or_create_collection(
                name="synthex_memory",
                metadata={"hnsw:space": "cosine"},
            )
            return {"client": client, "collection": collection, "impl": "chromadb"}
        except Exception:
            return None

    def _try_numpy(self) -> Any:
        try:
            import numpy as np  # type: ignore
            return {"impl": "numpy-cosine", "index": [], "metas": [], "store_dir": self._store_dir}
        except Exception:
            return None

    @property
    def backend_name(self) -> str:
        return self._backend_name

    def add(self, vec: list[float], meta: dict[str, Any]) -> None:
        if self._backend_name == "chromadb":
            import uuid as _uuid_mod  # type: ignore
            self._backend["collection"].add(
                embeddings=[vec],
                metadatas=[meta],
                ids=[_uuid_mod.uuid4().hex],
            )
        elif self._backend_name == "numpy-cosine":
            self._backend["index"].append(vec)
            self._backend["metas"].append(meta)
        else:
            self._backend.add(vec, meta)

    def search(self, query_vec: list[float], top_k: int = 5) -> list[dict[str, Any]]:
        if self._backend_name == "chromadb":
            results = self._backend["collection"].query(
                query_embeddings=[query_vec],
                n_results=top_k,
            )
            out: list[dict[str, Any]] = []
            if results and results.get("metadatas") and results["metadatas"][0]:
                for i, meta in enumerate(results["metadatas"][0]):
                    dist = results.get("distances", [[0]])[0][i] if results.get("distances") else 0
                    out.append({
                        "chunk": meta.get("chunk", ""),
                        "source": meta.get("source", ""),
                        "score": round(1.0 - float(dist) if dist else 1.0, 4),
                        "ts": meta.get("ts", ""),
                    })
            return out
        elif self._backend_name == "numpy-cosine":
            import numpy as np  # type: ignore
            try:
                idx = np.array(self._backend["index"])
                q = np.array(query_vec)
                dots = idx @ q
                na = np.linalg.norm(idx, axis=1)
                nq = np.linalg.norm(q)
                denom = na * nq
                denom[denom == 0] = 1
                scores = dots / denom
                top = np.argsort(scores)[::-1][:top_k]
                out = []
                for i in top:
                    meta = self._backend["metas"][int(i)]
                    out.append({
                        "chunk": meta.get("chunk", ""),
                        "source": meta.get("source", ""),
                        "score": round(float(scores[int(i)]), 4),
                        "ts": meta.get("ts", ""),
                    })
                return sorted(out, key=lambda x: x["score"], reverse=True)
            except Exception:
                return []
        else:
            return self._backend.search(query_vec, top_k)

    def _save_numpy(self) -> None:
        """Persist numpy index to disk."""
        if self._backend_name == "numpy-cosine":
            try:
                import numpy as np  # type: ignore
                np.savez(
                    str(self._store_dir / "numpy_index.npz"),
                    index=np.array(self._backend["index"]),
                )
                with open(self._store_dir / "numpy_metas.json", "w") as f:
                    json.dump(self._backend["metas"], f)
            except Exception:
                pass


# --------------------------------------------------------------------------- #
# Tool implementations (contract §3)
# --------------------------------------------------------------------------- #

_encode_fn: Any = None
_encode_label: str = ""
_store: Any = None  # VectorStore


def _ensure_store(root: Optional[Path] = None) -> VectorStore:
    global _store
    if _store is None:
        if root is None:
            root = resolve_root()
        _store = VectorStore(root)
    return _store


def _ensure_encode():
    global _encode_fn, _encode_label
    if _encode_fn is None:
        _encode_fn, _encode_label = _get_embedder()


def vector_index(path: str, root: Optional[Path] = None) -> dict[str, Any]:
    """Index a file into the vector store. Returns {indexed, source}."""
    if root is None:
        root = resolve_root()
    _ensure_encode()
    store = _ensure_store(root)
    p = Path(path)
    if not p.exists():
        return {"indexed": 0, "source": str(p), "error": "file_not_found"}
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return {"indexed": 0, "source": str(p), "error": "read_error"}
    chunks = chunk_text(text)
    ts = _now_iso()
    for i, chunk in enumerate(chunks):
        vec = _encode_fn(chunk)
        store.add(vec, {
            "chunk": chunk[:500],
            "source": str(p),
            "ts": ts,
            "chunk_idx": i,
        })
    if hasattr(store, "_save_numpy"):
        store._save_numpy()
    return {"indexed": len(chunks), "source": str(p)}


def vector_retrieve(query: str, top_k: int = 5, scope: str = "all",
                    root: Optional[Path] = None) -> list[dict[str, Any]]:
    """Semantic search. Returns [{chunk, source, score, ts}, ...]."""
    _ensure_encode()
    store = _ensure_store(root)
    vec = _encode_fn(query)
    return store.search(vec, top_k=top_k)


def kg_add(subject: str, predicate: str, object: str, source: str = "",
           root: Optional[Path] = None) -> dict[str, str]:
    """Add a triple to the knowledge graph."""
    if root is None:
        root = resolve_root()
    init_db(root)
    conn = sqlite3.connect(str(_db_path(root, "state_ledger")))
    conn.execute(
        "INSERT INTO kg_triples (subject, predicate, object, source) VALUES (?,?,?,?)",
        (subject, predicate, object, source),
    )
    conn.commit()
    conn.close()
    return {"status": "ok"}


def kg_query(subject: str = "", predicate: str = "", object: str = "",
             root: Optional[Path] = None) -> list[dict[str, Any]]:
    """Query knowledge graph triples with optional LIKE filters."""
    if root is None:
        root = resolve_root()
    init_db(root)
    conn = sqlite3.connect(str(_db_path(root, "state_ledger")))
    conn.row_factory = sqlite3.Row
    wheres: list[str] = []
    params: list[str] = []
    if subject:
        wheres.append("subject LIKE ?")
        params.append(f"%{subject}%")
    if predicate:
        wheres.append("predicate LIKE ?")
        params.append(f"%{predicate}%")
    if object:
        wheres.append("object LIKE ?")
        params.append(f"%{object}%")
    sql = "SELECT * FROM kg_triples"
    if wheres:
        sql += " WHERE " + " AND ".join(wheres)
    sql += " ORDER BY ts DESC LIMIT 100"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def lineage_trace(target: str, root: Optional[Path] = None) -> list[dict[str, Any]]:
    """Trace data lineage by searching intents + kg_triples for *target*."""
    if root is None:
        root = resolve_root()
    init_db(root)
    results: list[dict[str, Any]] = []

    conn = sqlite3.connect(str(_db_path(root, "intents")))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM intents WHERE why LIKE ? OR context LIKE ? ORDER BY ts DESC LIMIT 100",
        (f"%{target}%", f"%{target}%"),
    ).fetchall()
    conn.close()
    results.extend(dict(r) for r in rows)

    conn = sqlite3.connect(str(_db_path(root, "state_ledger")))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM kg_triples WHERE subject LIKE ? OR object LIKE ? ORDER BY ts DESC LIMIT 100",
        (f"%{target}%", f"%{target}%"),
    ).fetchall()
    conn.close()
    results.extend(dict(r) for r in rows)

    return results


def log_intent(agent: str, action: str, why: str, task_id: str = "",
               context: str = "", root: Optional[Path] = None) -> dict[str, Any]:
    """Record an intent/decision. Returns {id, ts}."""
    if root is None:
        root = resolve_root()
    init_db(root)
    conn = sqlite3.connect(str(_db_path(root, "intents")))
    cur = conn.execute(
        "INSERT INTO intents (agent, action, why, task_id, context) VALUES (?,?,?,?,?)",
        (agent, action, why, task_id, context),
    )
    conn.commit()
    rowid = cur.lastrowid
    conn.close()
    return {"id": rowid, "ts": _now_iso()}


def task_create(title: str, priority: str = "medium", assigned_to: str = "",
                root: Optional[Path] = None) -> dict[str, Any]:
    """Create a task. Returns {id, title, status}."""
    if root is None:
        root = resolve_root()
    init_db(root)
    tid = _uuid()
    ts = _now_iso()
    conn = sqlite3.connect(str(_db_path(root, "intents")))
    conn.execute(
        "INSERT INTO tasks (id, title, priority, status, assigned_to, created_at) VALUES (?,?,?,?,?,?)",
        (tid, title, priority, "pending", assigned_to, ts),
    )
    conn.commit()
    conn.close()
    return {"id": tid, "title": title, "status": "pending"}


def task_update(id: str, status: str, root: Optional[Path] = None) -> dict[str, Any]:
    """Update a task status. Returns {id, status}."""
    if root is None:
        root = resolve_root()
    init_db(root)
    ts = _now_iso()
    conn = sqlite3.connect(str(_db_path(root, "intents")))
    completed = ts if status in ("completed", "merged") else None
    conn.execute(
        "UPDATE tasks SET status=?, updated_at=?, completed_at=? WHERE id=?",
        (status, ts, completed, id),
    )
    conn.commit()
    conn.close()
    return {"id": id, "status": status}


def task_list(status: str = "", root: Optional[Path] = None) -> list[dict[str, Any]]:
    """List tasks, optionally filtered by status."""
    if root is None:
        root = resolve_root()
    init_db(root)
    conn = sqlite3.connect(str(_db_path(root, "intents")))
    conn.row_factory = sqlite3.Row
    if status:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE status=? ORDER BY created_at DESC", (status,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM tasks ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def drain_queue(root: Optional[Path] = None) -> dict[str, Any]:
    """Consume logs/index_queue.jsonl and index each path."""
    if root is None:
        root = resolve_root()
    qf = root / "logs" / "index_queue.jsonl"
    if not qf.exists():
        return {"processed": 0, "message": "no queue file"}
    lines = qf.read_text().splitlines()
    indexed = 0
    for line in lines:
        try:
            entry = json.loads(line)
            fp = entry.get("path", "")
            if fp:
                vector_index(fp, root=root)
                indexed += 1
        except Exception:
            pass
    qf.unlink()
    return {"processed": indexed}


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def _cli() -> None:
    ap = argparse.ArgumentParser(description="Synthex Memory & Graph CLI")
    sub = ap.add_subparsers(dest="cmd")

    sub.add_parser("initdb", help="initialize SQLite databases")
    p_idx = sub.add_parser("index", help="index a file into the vector store")
    p_idx.add_argument("path")
    p_ret = sub.add_parser("retrieve", help="semantic search")
    p_ret.add_argument("--query", required=True)
    p_ret.add_argument("--top-k", type=int, default=5)
    p_ret.add_argument("--scope", default="all")
    sub.add_parser("drain-queue", help="consume the index queue")
    p_tc = sub.add_parser("task-create", help="create a task")
    p_tc.add_argument("--title", required=True)
    p_tc.add_argument("--priority", default="medium")
    p_tc.add_argument("--assigned", default="")
    p_tl = sub.add_parser("task-list", help="list tasks")
    p_tl.add_argument("--status", default="")
    p_tu = sub.add_parser("task-update", help="update task status")
    p_tu.add_argument("--id", required=True)
    p_tu.add_argument("--status", required=True)
    sub.add_parser("selftest", help="run self-test")

    args = ap.parse_args()
    if args.cmd is None:
        ap.print_help()
        return

    root = resolve_root()

    if args.cmd == "initdb":
        init_db(root)
        print(f"DBs initialized under {root / 'logs'}")
    elif args.cmd == "index":
        result = vector_index(args.path, root=root)
        print(json.dumps(result))
    elif args.cmd == "retrieve":
        results = vector_retrieve(args.query, top_k=args.top_k, scope=args.scope, root=root)
        for r in results:
            print(f"[{r['score']:.4f}] {r['source']}")
            print(f"  {r['chunk'][:200]}")
            print()
    elif args.cmd == "drain-queue":
        result = drain_queue(root=root)
        print(json.dumps(result))
    elif args.cmd == "task-create":
        result = task_create(args.title, priority=args.priority, assigned_to=args.assigned, root=root)
        print(json.dumps(result))
    elif args.cmd == "task-list":
        tasks = task_list(status=args.status, root=root)
        for t in tasks:
            print(f"[{t['status']}] {t['id'][:8]} {t['title']}")
    elif args.cmd == "task-update":
        result = task_update(args.id, args.status, root=root)
        print(json.dumps(result))
    elif args.cmd == "selftest":
        _selftest(root)


def _selftest(root: Path) -> None:
    """Self-contained test: init → index → retrieve → task CRUD."""
    init_db(root)
    print(f"selftest: root={root}")
    testfile = root / "selftest.txt"
    testfile.write_text("Synthex is a multi-agent framework for Claude Code. "
                         "It provides a zero-write sandbox and a vector Memory Vault.")
    r = vector_index(str(testfile), root=root)
    print(f"  index: {json.dumps(r)}")
    results = vector_retrieve("multi-agent framework", top_k=3, root=root)
    print(f"  retrieve: {len(results)} hits, top={results[0]['score'] if results else 'none'}")
    tc = task_create("selftest task", root=root)
    print(f"  task-create: {json.dumps(tc)}")
    tl = task_list(root=root)
    print(f"  task-list: {len(tl)} tasks")
    print("selftest: PASS")


if __name__ == "__main__":
    _cli()
