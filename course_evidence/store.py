"""Crash-conscious local JSONL journal and SQLite delivery outbox."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .events import canonical_json, event_content_hash, validate_event


class EventStore:
    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve()
        self.log_dir = self.root / "logs"
        self.spool_dir = self.root / "spool"
        self.db_path = self.root / "outbox.sqlite3"
        self._lock = threading.RLock()
        for path in (self.root, self.log_dir, self.spool_dir):
            path.mkdir(parents=True, exist_ok=True, mode=0o700)
            try:
                path.chmod(0o700)
            except OSError:
                pass
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    @contextmanager
    def _database(self):
        """Commit/rollback like a sqlite connection context and always close it."""
        connection = self._connect()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._database() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    event_json BLOB NOT NULL,
                    digest TEXT NOT NULL,
                    local_only INTEGER NOT NULL DEFAULT 0,
                    acknowledged INTEGER NOT NULL DEFAULT 0,
                    receipt_id TEXT,
                    recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS events_pending ON events(acknowledged, local_only, recorded_at);
                CREATE TABLE IF NOT EXISTS sequences (
                    session_id TEXT PRIMARY KEY,
                    value INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                """
            )
        try:
            self.db_path.chmod(0o600)
        except OSError:
            pass

    def record(self, event: dict[str, Any], *, local_only: bool = False) -> dict[str, Any]:
        return self._store(event, append_log=True, local_only=local_only)

    def import_spooled(self, event: dict[str, Any]) -> dict[str, Any]:
        return self._store(event, append_log=True, local_only=False)

    def _store(self, event: dict[str, Any], *, append_log: bool, local_only: bool) -> dict[str, Any]:
        validate_event(event)
        with self._lock, self._database() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute("SELECT event_json FROM events WHERE event_id=?", (event["event_id"],)).fetchone()
            if existing:
                prior = json.loads(existing["event_json"])
                if self._identity_hash(prior) != self._identity_hash(event):
                    raise ValueError("event_id conflict: the same ID was submitted with different content")
                db.commit()
                return prior

            logged = self._find_in_log(event["session_id"], event["event_id"])
            if logged:
                if self._identity_hash(logged) != self._identity_hash(event):
                    raise ValueError("event_id conflict: local journal has different content")
                event = logged

            session_id = event["session_id"]
            current = db.execute("SELECT value FROM sequences WHERE session_id=?", (session_id,)).fetchone()
            seq = int(current["value"]) if current else 0
            if isinstance(event.get("sequence"), int) and event["sequence"] > seq:
                seq = event["sequence"]
            else:
                seq += 1
            event["sequence"] = seq
            encoded = canonical_json(event)
            if append_log and not logged:
                self._append_jsonl(session_id, encoded)
            db.execute(
                "INSERT INTO events(event_id,session_id,sequence,event_json,digest,local_only,acknowledged) VALUES(?,?,?,?,?,?,0)",
                (event["event_id"], session_id, seq, encoded, self._identity_hash(event), int(local_only)),
            )
            db.execute(
                "INSERT INTO sequences(session_id,value) VALUES(?,?) ON CONFLICT(session_id) DO UPDATE SET value=excluded.value",
                (session_id, seq),
            )
            db.commit()
            return event

    @staticmethod
    def _identity_hash(event: dict[str, Any]) -> str:
        return event_content_hash(event)

    def _append_jsonl(self, session_id: str, encoded: bytes) -> None:
        safe = "".join(ch for ch in session_id if ch.isalnum() or ch in "-_")[:96] or "session"
        path = self.log_dir / f"{safe}.jsonl"
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            remaining = memoryview(encoded + b"\n")
            while remaining:
                written = os.write(descriptor, remaining)
                if written <= 0:
                    raise OSError("short write while appending course event")
                remaining = remaining[written:]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def _find_in_log(self, session_id: str, event_id: str) -> dict[str, Any] | None:
        safe = "".join(ch for ch in session_id if ch.isalnum() or ch in "-_")[:96] or "session"
        path = self.log_dir / f"{safe}.jsonl"
        try:
            with path.open(encoding="utf-8") as stream:
                for line in stream:
                    try:
                        event = json.loads(line)
                        if event.get("event_id") == event_id:
                            return event
                    except (json.JSONDecodeError, AttributeError):
                        continue
        except OSError:
            pass
        return None

    def import_spools(self) -> int:
        imported = 0
        for path in sorted(self.spool_dir.glob("*.jsonl")):
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except OSError:
                continue
            for line in lines:
                try:
                    event = json.loads(line)
                    validate_event(event)
                    self.import_spooled(event)
                    imported += 1
                except (ValueError, json.JSONDecodeError, TypeError):
                    # Keep malformed spool data intact for manual recovery.
                    continue
            # Preserve the original spool until its events have either become
            # durable in the primary journal or remain malformed for review.
            if lines and all(self._event_exists_from_line(line) for line in lines):
                path.unlink(missing_ok=True)
        return imported

    def _event_exists_from_line(self, line: str) -> bool:
        try:
            event = json.loads(line)
            with self._database() as db:
                row = db.execute("SELECT 1 FROM events WHERE event_id=?", (event["event_id"],)).fetchone()
                return bool(row)
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            return False

    def pending(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._database() as db:
            rows = db.execute(
                "SELECT event_json FROM events WHERE acknowledged=0 AND local_only=0 ORDER BY session_id,sequence,event_id LIMIT ?",
                (max(1, min(int(limit), 500)),),
            ).fetchall()
        return [json.loads(row["event_json"]) for row in rows]

    def acknowledge(self, event_ids: list[str], receipt_id: str) -> None:
        if not event_ids:
            return
        with self._database() as db:
            db.executemany(
                "UPDATE events SET acknowledged=1,receipt_id=? WHERE event_id=?",
                [(receipt_id, event_id) for event_id in event_ids],
            )

    def status(self) -> dict[str, Any]:
        with self._database() as db:
            counts = db.execute(
                "SELECT count(*) AS total, sum(CASE WHEN acknowledged=0 AND local_only=0 THEN 1 ELSE 0 END) AS pending, sum(CASE WHEN acknowledged=1 THEN 1 ELSE 0 END) AS acknowledged FROM events"
            ).fetchone()
            last = db.execute("SELECT value FROM metadata WHERE key='last_successful_sync'").fetchone()
            error = db.execute("SELECT value FROM metadata WHERE key='last_sync_error'").fetchone()
        return {
            "recorded_events": int(counts["total"] or 0),
            "pending_events": int(counts["pending"] or 0),
            "acknowledged_events": int(counts["acknowledged"] or 0),
            "last_successful_sync": last["value"] if last else None,
            "last_sync_error": error["value"] if error else None,
        }

    def set_metadata(self, key: str, value: str) -> None:
        with self._database() as db:
            db.execute("INSERT INTO metadata(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))

    def events(self) -> list[dict[str, Any]]:
        with self._database() as db:
            rows = db.execute("SELECT event_json FROM events ORDER BY session_id,sequence").fetchall()
        return [json.loads(row["event_json"]) for row in rows]

    def export_jsonl(self) -> bytes:
        return b"".join(canonical_json(event) + b"\n" for event in self.events())
