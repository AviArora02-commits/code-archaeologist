"""SQLite persistence for repos, jobs, and feedback."""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import aiosqlite

from app.config import get_settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS repos (
    id TEXT PRIMARY KEY,
    owner TEXT NOT NULL,
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    dataset_name TEXT NOT NULL,
    cognee_dataset_id TEXT,
    clone_path TEXT,
    subfolder TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ingestion_jobs (
    id TEXT PRIMARY KEY,
    repo_id TEXT NOT NULL,
    status TEXT NOT NULL,
    progress_message TEXT,
    dry_run_estimate TEXT,
    confirmed INTEGER DEFAULT 0,
    error_message TEXT,
    files_processed INTEGER DEFAULT 0,
    total_files INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (repo_id) REFERENCES repos(id)
);

CREATE TABLE IF NOT EXISTS feedback (
    id TEXT PRIMARY KEY,
    repo_id TEXT NOT NULL,
    query TEXT NOT NULL,
    answer TEXT NOT NULL,
    score INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (repo_id) REFERENCES repos(id)
);

CREATE TABLE IF NOT EXISTS language_requests (
    id TEXT PRIMARY KEY,
    language_name TEXT NOT NULL,
    file_extensions TEXT,
    repo_url TEXT,
    contact_email TEXT,
    message TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS expert_knowledge (
    id TEXT PRIMARY KEY,
    repo_id TEXT NOT NULL,
    author_name TEXT NOT NULL,
    topic TEXT NOT NULL,
    content TEXT NOT NULL,
    related_file TEXT,
    related_symbol TEXT,
    cognee_stored INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY (repo_id) REFERENCES repos(id)
);

CREATE TABLE IF NOT EXISTS memory_nodes (
    id TEXT PRIMARY KEY,
    repo_id TEXT NOT NULL,
    node_type TEXT NOT NULL,
    label TEXT NOT NULL,
    ref_key TEXT NOT NULL,
    detail TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (repo_id) REFERENCES repos(id),
    UNIQUE(repo_id, ref_key)
);

CREATE TABLE IF NOT EXISTS memory_edges (
    id TEXT PRIMARY KEY,
    repo_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    edge_type TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (repo_id) REFERENCES repos(id),
    UNIQUE(repo_id, source_id, target_id, edge_type)
);
"""


def _now() -> str:
    return datetime.now(UTC).isoformat()


class Database:
    """Async SQLite wrapper."""

    def __init__(self, path: str | None = None) -> None:
        self.path = path or get_settings().sqlite_path

    @asynccontextmanager
    async def _session(self) -> AsyncIterator[aiosqlite.Connection]:
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.path) as conn:
            conn.row_factory = aiosqlite.Row
            await conn.executescript(SCHEMA)
            await conn.commit()
            yield conn

    async def connect(self) -> None:
        """Initialize schema (used at app startup)."""
        async with self._session():
            return

    async def create_repo(
        self,
        owner: str,
        name: str,
        url: str,
        dataset_name: str,
        subfolder: str | None = None,
    ) -> dict[str, Any]:
        repo_id = str(uuid.uuid4())
        row = {
            "id": repo_id,
            "owner": owner,
            "name": name,
            "url": url,
            "dataset_name": dataset_name,
            "cognee_dataset_id": None,
            "clone_path": None,
            "subfolder": subfolder,
            "created_at": _now(),
        }
        async with self._session() as conn:
            await conn.execute(
                """INSERT INTO repos
                (id, owner, name, url, dataset_name, cognee_dataset_id, clone_path, subfolder, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    row["id"],
                    row["owner"],
                    row["name"],
                    row["url"],
                    row["dataset_name"],
                    row["cognee_dataset_id"],
                    row["clone_path"],
                    row["subfolder"],
                    row["created_at"],
                ),
            )
            await conn.commit()
        return row

    async def get_repo(self, repo_id: str) -> dict[str, Any] | None:
        async with self._session() as conn:
            cursor = await conn.execute("SELECT * FROM repos WHERE id = ?", (repo_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def list_repos(self) -> list[dict[str, Any]]:
        async with self._session() as conn:
            cursor = await conn.execute("SELECT * FROM repos ORDER BY created_at DESC")
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def update_repo(self, repo_id: str, **fields: Any) -> None:
        if not fields:
            return
        cols = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [repo_id]
        async with self._session() as conn:
            await conn.execute(f"UPDATE repos SET {cols} WHERE id = ?", values)
            await conn.commit()

    async def delete_repo(self, repo_id: str) -> None:
        async with self._session() as conn:
            await conn.execute("DELETE FROM memory_edges WHERE repo_id = ?", (repo_id,))
            await conn.execute("DELETE FROM memory_nodes WHERE repo_id = ?", (repo_id,))
            await conn.execute("DELETE FROM expert_knowledge WHERE repo_id = ?", (repo_id,))
            await conn.execute("DELETE FROM feedback WHERE repo_id = ?", (repo_id,))
            await conn.execute("DELETE FROM ingestion_jobs WHERE repo_id = ?", (repo_id,))
            await conn.execute("DELETE FROM repos WHERE id = ?", (repo_id,))
            await conn.commit()

    async def create_job(self, repo_id: str, dry_run_estimate: dict[str, Any] | None = None) -> dict[str, Any]:
        job_id = str(uuid.uuid4())
        now = _now()
        estimate_json = json.dumps(dry_run_estimate) if dry_run_estimate else None
        row = {
            "id": job_id,
            "repo_id": repo_id,
            "status": "pending",
            "progress_message": "Queued",
            "dry_run_estimate": estimate_json,
            "confirmed": 0,
            "error_message": None,
            "files_processed": 0,
            "total_files": 0,
            "created_at": now,
            "updated_at": now,
        }
        async with self._session() as conn:
            await conn.execute(
                """INSERT INTO ingestion_jobs
                (id, repo_id, status, progress_message, dry_run_estimate, confirmed,
                 error_message, files_processed, total_files, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    row["id"],
                    row["repo_id"],
                    row["status"],
                    row["progress_message"],
                    row["dry_run_estimate"],
                    row["confirmed"],
                    row["error_message"],
                    row["files_processed"],
                    row["total_files"],
                    row["created_at"],
                    row["updated_at"],
                ),
            )
            await conn.commit()
        return row

    async def get_job(self, job_id: str) -> dict[str, Any] | None:
        async with self._session() as conn:
            cursor = await conn.execute("SELECT * FROM ingestion_jobs WHERE id = ?", (job_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_latest_job(self, repo_id: str) -> dict[str, Any] | None:
        async with self._session() as conn:
            cursor = await conn.execute(
                "SELECT * FROM ingestion_jobs WHERE repo_id = ? ORDER BY created_at DESC LIMIT 1",
                (repo_id,),
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def update_job(self, job_id: str, **fields: Any) -> None:
        fields["updated_at"] = _now()
        if "dry_run_estimate" in fields and isinstance(fields["dry_run_estimate"], dict):
            fields["dry_run_estimate"] = json.dumps(fields["dry_run_estimate"])
        cols = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [job_id]
        async with self._session() as conn:
            await conn.execute(f"UPDATE ingestion_jobs SET {cols} WHERE id = ?", values)
            await conn.commit()

    async def add_feedback(
        self, repo_id: str, query: str, answer: str, score: int
    ) -> dict[str, Any]:
        fb_id = str(uuid.uuid4())
        row = {
            "id": fb_id,
            "repo_id": repo_id,
            "query": query,
            "answer": answer,
            "score": score,
            "created_at": _now(),
        }
        async with self._session() as conn:
            await conn.execute(
                "INSERT INTO feedback (id, repo_id, query, answer, score, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (fb_id, repo_id, query, answer, score, row["created_at"]),
            )
            await conn.commit()
        return row

    async def create_language_request(
        self,
        language_name: str,
        message: str,
        file_extensions: str | None = None,
        repo_url: str | None = None,
        contact_email: str | None = None,
    ) -> dict[str, Any]:
        req_id = str(uuid.uuid4())
        row = {
            "id": req_id,
            "language_name": language_name,
            "file_extensions": file_extensions,
            "repo_url": repo_url,
            "contact_email": contact_email,
            "message": message,
            "status": "pending",
            "created_at": _now(),
        }
        async with self._session() as conn:
            await conn.execute(
                """INSERT INTO language_requests
                (id, language_name, file_extensions, repo_url, contact_email, message, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    req_id,
                    language_name,
                    file_extensions,
                    repo_url,
                    contact_email,
                    message,
                    "pending",
                    row["created_at"],
                ),
            )
            await conn.commit()
        return row

    async def create_expert_knowledge(
        self,
        repo_id: str,
        author_name: str,
        topic: str,
        content: str,
        related_file: str | None = None,
        related_symbol: str | None = None,
    ) -> dict[str, Any]:
        kid = str(uuid.uuid4())
        row = {
            "id": kid,
            "repo_id": repo_id,
            "author_name": author_name,
            "topic": topic,
            "content": content,
            "related_file": related_file,
            "related_symbol": related_symbol,
            "cognee_stored": 0,
            "created_at": _now(),
        }
        async with self._session() as conn:
            await conn.execute(
                """INSERT INTO expert_knowledge
                (id, repo_id, author_name, topic, content, related_file, related_symbol,
                 cognee_stored, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    kid, repo_id, author_name, topic, content,
                    related_file, related_symbol, 0, row["created_at"],
                ),
            )
            await conn.commit()
        return row

    async def update_expert_knowledge(self, knowledge_id: str, **fields: Any) -> None:
        if not fields:
            return
        cols = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [knowledge_id]
        async with self._session() as conn:
            await conn.execute(f"UPDATE expert_knowledge SET {cols} WHERE id = ?", values)
            await conn.commit()

    async def list_expert_knowledge(self, repo_id: str) -> list[dict[str, Any]]:
        async with self._session() as conn:
            cursor = await conn.execute(
                "SELECT * FROM expert_knowledge WHERE repo_id = ? ORDER BY created_at DESC",
                (repo_id,),
            )
            return [dict(r) for r in await cursor.fetchall()]

    async def upsert_memory_node(
        self,
        repo_id: str,
        *,
        node_type: str,
        label: str,
        ref_key: str,
        detail: str | None = None,
    ) -> str:
        async with self._session() as conn:
            cursor = await conn.execute(
                "SELECT id FROM memory_nodes WHERE repo_id = ? AND ref_key = ?",
                (repo_id, ref_key),
            )
            existing = await cursor.fetchone()
            if existing:
                return str(existing["id"])
            node_id = str(uuid.uuid4())
            await conn.execute(
                """INSERT INTO memory_nodes
                (id, repo_id, node_type, label, ref_key, detail, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (node_id, repo_id, node_type, label, ref_key, detail, _now()),
            )
            await conn.commit()
            return node_id

    async def upsert_memory_edge(
        self, repo_id: str, source_id: str, target_id: str, edge_type: str
    ) -> str:
        async with self._session() as conn:
            cursor = await conn.execute(
                """SELECT id FROM memory_edges
                WHERE repo_id = ? AND source_id = ? AND target_id = ? AND edge_type = ?""",
                (repo_id, source_id, target_id, edge_type),
            )
            existing = await cursor.fetchone()
            if existing:
                return str(existing["id"])
            edge_id = str(uuid.uuid4())
            await conn.execute(
                """INSERT INTO memory_edges
                (id, repo_id, source_id, target_id, edge_type, created_at)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (edge_id, repo_id, source_id, target_id, edge_type, _now()),
            )
            await conn.commit()
            return edge_id

    async def list_memory_nodes(self, repo_id: str) -> list[dict[str, Any]]:
        async with self._session() as conn:
            cursor = await conn.execute(
                "SELECT * FROM memory_nodes WHERE repo_id = ? ORDER BY created_at ASC",
                (repo_id,),
            )
            return [dict(r) for r in await cursor.fetchall()]

    async def list_memory_edges(self, repo_id: str) -> list[dict[str, Any]]:
        async with self._session() as conn:
            cursor = await conn.execute(
                "SELECT * FROM memory_edges WHERE repo_id = ?",
                (repo_id,),
            )
            return [dict(r) for r in await cursor.fetchall()]

    async def count_memory_nodes(self, repo_id: str) -> int:
        async with self._session() as conn:
            cursor = await conn.execute(
                "SELECT COUNT(*) AS c FROM memory_nodes WHERE repo_id = ?",
                (repo_id,),
            )
            row = await cursor.fetchone()
            return int(row["c"]) if row else 0

    async def count_expert_knowledge(self, repo_id: str) -> int:
        async with self._session() as conn:
            cursor = await conn.execute(
                "SELECT COUNT(*) AS c FROM expert_knowledge WHERE repo_id = ?",
                (repo_id,),
            )
            row = await cursor.fetchone()
            return int(row["c"]) if row else 0
