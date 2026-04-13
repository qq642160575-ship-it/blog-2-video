from __future__ import annotations

import pickle
import sqlite3
from pathlib import Path
from threading import RLock
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver


class PersistentInMemorySaver(InMemorySaver):
    """A drop-in InMemorySaver backed by a local SQLite snapshot."""

    def __init__(self, storage_path: str | Path) -> None:
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        super().__init__()
        self._init_db()
        self._load_from_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.storage_path)

    def _init_db(self) -> None:
        conn = self._connect()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS checkpoint_snapshots (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    payload BLOB NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        finally:
            conn.close()

    def _load_from_db(self) -> None:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT payload FROM checkpoint_snapshots WHERE id = 1"
            ).fetchone()
        finally:
            conn.close()

        if row is None:
            return

        payload = pickle.loads(row[0])

        self.storage.clear()
        for thread_id, ns_map in payload.get("storage", {}).items():
            thread_storage = self.storage[thread_id]
            for checkpoint_ns, checkpoints in ns_map.items():
                thread_storage[checkpoint_ns].update(checkpoints)

        self.writes.clear()
        self.writes.update(payload.get("writes", {}))

        self.blobs.clear()
        self.blobs.update(payload.get("blobs", {}))

    def _serialize_state(self) -> dict[str, Any]:
        storage_payload: dict[str, dict[str, dict[str, Any]]] = {}
        for thread_id, ns_map in self.storage.items():
            storage_payload[thread_id] = {
                checkpoint_ns: dict(checkpoints)
                for checkpoint_ns, checkpoints in ns_map.items()
            }

        return {
            "storage": storage_payload,
            "writes": dict(self.writes),
            "blobs": dict(self.blobs),
        }

    def _flush_to_db(self) -> None:
        payload = sqlite3.Binary(
            pickle.dumps(self._serialize_state(), protocol=pickle.HIGHEST_PROTOCOL)
        )
        conn = self._connect()
        try:
            conn.execute(
                """
                INSERT INTO checkpoint_snapshots (id, payload, updated_at)
                VALUES (1, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET
                    payload = excluded.payload,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (payload,),
            )
            conn.commit()
        finally:
            conn.close()

    def put(self, config, checkpoint, metadata, new_versions):
        with self._lock:
            result = super().put(config, checkpoint, metadata, new_versions)
            self._flush_to_db()
            return result

    def put_writes(self, config, writes, task_id, task_path=""):
        with self._lock:
            super().put_writes(config, writes, task_id, task_path)
            self._flush_to_db()

    def delete_thread(self, thread_id: str) -> None:
        with self._lock:
            super().delete_thread(thread_id)
            self._flush_to_db()
