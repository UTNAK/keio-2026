"""Jupyter Server integration for scoped course recording and sync status."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any

import tornado.web
from jupyter_server.base.handlers import JupyterHandler
from jupyter_server.utils import url_path_join

from .events import COURSE_ID, MAX_SNAPSHOT_CHARS, make_event, redact_text
from .store import EventStore
from .sync import SyncClient, SyncError, SyncWorker

_EXTENSION_STATE: dict[str, Any] = {}
_MODEL_SUFFIX = ".sysml"
_NOTEBOOK_SUFFIX = ".ipynb"
_SCAN_INTERVAL = 12


def _data_dir() -> Path:
    return Path(os.environ.get("COURSE_DATA_DIR", "/home/keio/work/private-course-data")).expanduser().resolve()


def _identity_path() -> Path:
    return _data_dir() / "identity.json"


def _identity() -> dict[str, str]:
    path = _identity_path()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        identity = json.loads(path.read_text(encoding="utf-8"))
        if identity.get("device_id") and identity.get("student_id"):
            return identity
    except (OSError, ValueError, AttributeError):
        pass
    identity = {"student_id": f"student-{uuid.uuid4()}", "device_id": str(uuid.uuid4())}
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(identity, separators=(",", ":")), encoding="utf-8")
    os.chmod(temp, 0o600)
    temp.replace(path)
    return identity


def _store() -> EventStore:
    store = _EXTENSION_STATE.get("store")
    if not store:
        store = EventStore(_data_dir())
        _EXTENSION_STATE["store"] = store
    return store


def _client() -> SyncClient:
    current = _EXTENSION_STATE.get("client")
    if current:
        return current
    return SyncClient(
        _store(),
        os.environ.get("COURSE_COLLECTOR_URL"),
        str(_data_dir() / "credentials.json"),
        timeout=float(os.environ.get("COURSE_SYNC_TIMEOUT", "8")),
        batch_size=int(os.environ.get("COURSE_SYNC_BATCH_SIZE", "50")),
    )


def _record(kind: str, source: str, source_ref: str, session_id: str, payload: dict[str, Any], *, local_only: bool = False) -> dict[str, Any]:
    identity = _identity()
    event = make_event(
        device_id=identity["device_id"], student_id=identity["student_id"],
        session_id=session_id, kind=kind, source=source, source_ref=source_ref, payload=payload,
    )
    return _store().record(event, local_only=local_only)


class StatusHandler(JupyterHandler):
    @tornado.web.authenticated
    def get(self) -> None:
        state = _store().status()
        enrolled = (_data_dir() / "credentials.json").is_file()
        configured = bool(os.environ.get("COURSE_COLLECTOR_URL"))
        error = state.get("last_sync_error") or ""
        if error and ("401" in error or "403" in error or "Enrollment" in error):
            status = "attention"
        elif not configured or not enrolled or state["pending_events"]:
            status = "offline"
        elif state["last_successful_sync"]:
            status = "synced"
        else:
            status = "recording"
        self.finish({
            **state,
            "status": status,
            "configured": configured,
            "enrolled": enrolled,
            "student_id": _identity()["student_id"],
            "sync_interval_seconds": int(os.environ.get("COURSE_SYNC_INTERVAL", "120")),
            "disclosure_url": self.settings.get("base_url", "/") + "api/course-evidence/disclosure",
        })


class IngestHandler(JupyterHandler):
    def check_xsrf_cookie(self) -> None:
        # OpenCode's local ACP subprocess has no browser cookie. The ingest key
        # is generated locally, mode 0600, and is not used by the student UI.
        expected = _ingest_token()
        actual = self.request.headers.get("Authorization", "")
        if not expected or not hmac.compare_digest(actual, f"Bearer {expected}"):
            raise tornado.web.HTTPError(403, "local course recorder authorization failed")

    def post(self) -> None:
        if len(self.request.body) > 128_000:
            raise tornado.web.HTTPError(413, "event exceeds size limit")
        try:
            event = json.loads(self.request.body)
            stored = _store().record(event)
        except (ValueError, json.JSONDecodeError, TypeError) as error:
            raise tornado.web.HTTPError(400, str(error)) from error
        self.finish({"recorded": True, "event_id": stored["event_id"], "sequence": stored["sequence"]})
        if stored.get("kind") == "class.session.ended":
            worker = _EXTENSION_STATE.get("worker")
            if worker:
                worker.request_sync()


def _ingest_token() -> str:
    path = _data_dir() / ".ingest-token"
    try:
        return path.read_text(encoding="ascii").strip()
    except OSError:
        token = uuid.uuid4().hex + uuid.uuid4().hex
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="ascii") as stream:
            stream.write(token + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        return token


class EnrollHandler(JupyterHandler):
    @tornado.web.authenticated
    def post(self) -> None:
        try:
            body = json.loads(self.request.body)
        except json.JSONDecodeError as error:
            raise tornado.web.HTTPError(400, "invalid JSON") from error
        code = body.get("enrollment_code") if isinstance(body, dict) else None
        if not isinstance(code, str) or not code.strip() or len(code) > 200:
            raise tornado.web.HTTPError(400, "enter the one-time enrollment code provided by the instructor")
        identity = _identity()
        try:
            result = _client().enroll(code.strip(), identity["student_id"], identity["device_id"])
        except SyncError as error:
            status = error.status or (400 if not error.retryable else 503)
            raise tornado.web.HTTPError(status, str(error)) from error
        self.set_status(201)
        self.finish(result)


class SyncNowHandler(JupyterHandler):
    @tornado.web.authenticated
    def post(self) -> None:
        try:
            _store().import_spools()
            result = _client().sync_once()
            _record("sync.receipt", "synchronizer", str(result.get("receipt_id") or time.time_ns()), "local-sync", result, local_only=True)
        except SyncError as error:
            _record("sync.failure", "synchronizer", f"failure:{time.time_ns()}", "local-sync", {"status": error.status, "message": str(error)[:500], "retryable": error.retryable}, local_only=True)
            raise tornado.web.HTTPError(error.status or 503, str(error)) from error
        self.finish({**result, **_store().status()})


class ActivityHandler(JupyterHandler):
    @tornado.web.authenticated
    def post(self) -> None:
        if len(self.request.body) > 128_000:
            raise tornado.web.HTTPError(413, "activity event exceeds size limit")
        try:
            body = json.loads(self.request.body)
        except json.JSONDecodeError as error:
            raise tornado.web.HTTPError(400, "invalid JSON") from error
        if not isinstance(body, dict):
            raise tornado.web.HTTPError(400, "activity event must be an object")
        kind = body.get("kind")
        if kind not in {"notebook.cell.changed", "notebook.cell.executed", "notebook.saved", "sysml.validation", "model.checkpoint"}:
            raise tornado.web.HTTPError(400, "unsupported activity kind")
        payload = body.get("payload")
        if not isinstance(payload, dict):
            raise tornado.web.HTTPError(400, "payload must be an object")
        relative = payload.get("relative_path")
        if not isinstance(relative, str) or not (relative.endswith(".ipynb") or relative.endswith(".sysml")) or relative.startswith(("/", "..")):
            raise tornado.web.HTTPError(400, "activity must refer to a course notebook or model path")
        source_ref = str(body.get("source_ref") or f"{kind}:{relative}:{time.time_ns()}")[:250]
        try:
            stored = _record(kind, "jupyter", source_ref, str(body.get("session_id") or "jupyter-local"), payload)
        except ValueError as error:
            raise tornado.web.HTTPError(400, str(error)) from error
        self.finish({"recorded": True, "event_id": stored["event_id"], "sequence": stored["sequence"]})


class ExportHandler(JupyterHandler):
    @tornado.web.authenticated
    def get(self) -> None:
        self.set_header("Content-Type", "application/x-ndjson; charset=utf-8")
        self.set_header("Content-Disposition", 'attachment; filename="course-evidence.jsonl"')
        self.finish(_store().export_jsonl())


class DisclosureHandler(JupyterHandler):
    @tornado.web.authenticated
    def get(self) -> None:
        self.set_header("Content-Type", "text/markdown; charset=utf-8")
        self.finish((Path("/opt/course/docs/classroom-data-and-privacy.md").read_text(encoding="utf-8")))


def _file_hash(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as source:
        for block in iter(lambda: source.read(64 * 1024), b""):
            size += len(block)
            digest.update(block)
    return digest.hexdigest(), size


def _safe_file(path: Path, root: Path) -> bool:
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(root.resolve(strict=True))
        return path.is_file() and not path.is_symlink()
    except (OSError, ValueError):
        return False


def checkpoint_workspace(stop_event: threading.Event) -> None:
    roots = [Path("/home/keio/work/models"), Path("/home/keio/work/notebooks")]
    interval = max(2, int(os.environ.get("COURSE_FILE_SCAN_INTERVAL", str(_SCAN_INTERVAL))))
    observed: dict[str, tuple[int, int, str]] = {}
    while not stop_event.wait(interval):
        for root in roots:
            if not root.is_dir():
                continue
            suffix = _MODEL_SUFFIX if root == roots[0] else _NOTEBOOK_SUFFIX
            for path in root.rglob(f"*{suffix}"):
                if any(part.startswith(".") or part in {".ipynb_checkpoints", "node_modules"} for part in path.parts):
                    continue
                if not _safe_file(path, root):
                    continue
                try:
                    stat = path.stat()
                    digest, size = _file_hash(path)
                    previous = observed.get(str(path))
                    if previous == (stat.st_mtime_ns, size, digest):
                        continue
                    observed[str(path)] = (stat.st_mtime_ns, size, digest)
                    relative = path.relative_to(root).as_posix()
                    payload: dict[str, Any] = {"relative_path": relative, "sha256": digest, "size_bytes": size}
                    if suffix == _MODEL_SUFFIX:
                        try:
                            content = path.read_text(encoding="utf-8")
                            if len(content) <= MAX_SNAPSHOT_CHARS:
                                payload["snapshot"] = redact_text(content, limit=MAX_SNAPSHOT_CHARS)
                            else:
                                payload["snapshot_omitted"] = "model exceeds bounded snapshot size"
                        except (OSError, UnicodeDecodeError):
                            payload["snapshot_omitted"] = "model is not readable UTF-8"
                        _record("model.checkpoint", "filesystem-watcher", f"model:{relative}:{digest}:{stat.st_mtime_ns}", "workspace-models", payload)
                    else:
                        try:
                            notebook = json.loads(path.read_text(encoding="utf-8"))
                            cells = notebook.get("cells", [])
                            payload["cell_count"] = len(cells)
                            payload["cell_ids"] = [str(cell.get("id", "")) for cell in cells[:300] if isinstance(cell, dict)]
                            payload["cell_source_hashes"] = [hashlib.sha256("".join(cell.get("source", [])).encode()).hexdigest() for cell in cells[:300] if isinstance(cell, dict)]
                        except (OSError, UnicodeDecodeError, ValueError, AttributeError):
                            payload["metadata_omitted"] = "notebook metadata unavailable"
                        _record("notebook.saved", "filesystem-watcher", f"notebook:{relative}:{digest}:{stat.st_mtime_ns}", "jupyter-local", payload)
                except OSError:
                    continue


def _load_jupyter_server_extension(serverapp: Any) -> None:
    """Install authenticated REST endpoints and start local evidence workers."""
    _identity()
    _ingest_token()
    store = _store()
    client = _client()
    _EXTENSION_STATE["client"] = client
    worker = SyncWorker(
        store, client,
        interval=int(os.environ.get("COURSE_SYNC_INTERVAL", "120")),
        on_event=lambda kind, ref, payload: _record(kind, "synchronizer", ref, "local-sync", payload, local_only=True),
    )
    stop_event = threading.Event()
    sync_thread = threading.Thread(target=worker.run, name="course-evidence-sync", daemon=True)
    watch_thread = threading.Thread(target=checkpoint_workspace, args=(stop_event,), name="course-evidence-watch", daemon=True)
    sync_thread.start()
    watch_thread.start()
    _EXTENSION_STATE.update({"worker": worker, "stop_event": stop_event})

    def stop_workers(*_args: Any, **_kwargs: Any) -> None:
        worker.stop()
        stop_event.set()

    serverapp.io_loop.add_callback(lambda: None)
    serverapp.web_app.settings.setdefault("course_evidence_stop", stop_workers)
    base_url = serverapp.web_app.settings.get("base_url", "/")
    route = lambda endpoint: url_path_join(base_url, "api/course-evidence", endpoint)
    serverapp.web_app.add_handlers(".*$", [
        (route("status"), StatusHandler),
        (route("ingest"), IngestHandler),
        (route("enroll"), EnrollHandler),
        (route("sync"), SyncNowHandler),
        (route("activity"), ActivityHandler),
        (route("export"), ExportHandler),
        (route("disclosure"), DisclosureHandler),
    ])
    serverapp.log.info("Keio course evidence endpoints enabled; collector URL configured: %s", bool(os.environ.get("COURSE_COLLECTOR_URL")))


load_jupyter_server_extension = _load_jupyter_server_extension
