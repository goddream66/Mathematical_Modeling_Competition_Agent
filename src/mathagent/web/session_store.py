from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class WebSessionStore:
    db_path: Path

    def __post_init__(self) -> None:
        object.__setattr__(self, "db_path", Path(self.db_path))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        object.__setattr__(self, "json_path", self.db_path.with_suffix(".json"))
        object.__setattr__(self, "backend", "sqlite")
        try:
            self._initialize()
        except sqlite3.OperationalError:
            object.__setattr__(self, "backend", "json")
            if not self.json_path.exists():
                self.json_path.write_text("{}", encoding="utf-8")

    def save_session(self, payload: dict[str, Any]) -> None:
        if self.backend == "json":
            data = self._load_json_store()
            data[str(payload["session_id"])] = payload
            self._save_json_store(data)
            return
        session_id = str(payload["session_id"])
        created_at = str(payload.get("created_at") or "")
        updated_at = str(payload.get("updated_at") or created_at)
        body = json.dumps(payload, ensure_ascii=False)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO web_sessions(session_id, payload, created_at, updated_at)
                VALUES(?,?,?,?)
                ON CONFLICT(session_id)
                DO UPDATE SET payload=excluded.payload, updated_at=excluded.updated_at
                """,
                (session_id, body, created_at, updated_at),
            )

    def load_session(self, session_id: str) -> dict[str, Any] | None:
        if self.backend == "json":
            return self._load_json_store().get(session_id)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload FROM web_sessions WHERE session_id=?",
                (session_id,),
            ).fetchone()
        if row is None:
            return None
        return json.loads(str(row[0]))

    def list_sessions(self) -> list[dict[str, Any]]:
        if self.backend == "json":
            items = list(self._load_json_store().values())
            items.sort(
                key=lambda item: (str(item.get("updated_at") or ""), str(item.get("created_at") or "")),
                reverse=True,
            )
            return items
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT payload FROM web_sessions ORDER BY updated_at DESC, created_at DESC"
            ).fetchall()
        return [json.loads(str(row[0])) for row in rows]

    def delete_session(self, session_id: str) -> None:
        if self.backend == "json":
            data = self._load_json_store()
            data.pop(session_id, None)
            self._save_json_store(data)
            return
        with self._connect() as conn:
            conn.execute("DELETE FROM web_sessions WHERE session_id=?", (session_id,))

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path.resolve()), timeout=30)
        try:
            conn.execute("PRAGMA journal_mode=DELETE;")
            conn.execute("PRAGMA synchronous=NORMAL;")
        except sqlite3.OperationalError:
            pass
        return conn

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS web_sessions (
                    session_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def _load_json_store(self) -> dict[str, dict[str, Any]]:
        if not self.json_path.exists():
            return {}
        return json.loads(self.json_path.read_text(encoding="utf-8"))

    def _save_json_store(self, payload: dict[str, Any]) -> None:
        self.json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
