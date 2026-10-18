"""Bounded authenticated delivery with durable acknowledgement semantics."""

from __future__ import annotations

import json
import os
import random
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

from .events import canonical_json
from .store import EventStore


class SyncError(RuntimeError):
    def __init__(self, message: str, *, status: int | None = None, retryable: bool = True):
        super().__init__(message)
        self.status = status
        self.retryable = retryable


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


class SyncClient:
    def __init__(self, store: EventStore, base_url: str | None, token_path: str, *, timeout: float = 8.0, batch_size: int = 50):
        self.store = store
        self.base_url = (base_url or "").rstrip("/")
        self.token_path = token_path
        self.timeout = timeout
        self.batch_size = min(max(int(batch_size), 1), 100)
        self._sync_lock = threading.Lock()

    def _token(self) -> str | None:
        try:
            from pathlib import Path
            value = json.loads(Path(self.token_path).read_text(encoding="utf-8")).get("submission_token")
            return value if isinstance(value, str) and value else None
        except (OSError, ValueError, AttributeError):
            return None

    def enroll(self, enrollment_code: str, student_id: str, device_id: str) -> dict[str, Any]:
        if not self.base_url:
            raise SyncError("Collector URL is not configured by the instructor", retryable=False)
        payload = {"enrollment_code": enrollment_code, "student_id": student_id, "device_id": device_id}
        response = self._request("POST", "/v1/enroll", payload, bearer=None)
        token = response.get("submission_token")
        if not isinstance(token, str) or len(token) < 32:
            raise SyncError("Collector returned an invalid enrollment response", retryable=False)
        import os
        from pathlib import Path

        path = Path(self.token_path)
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(json.dumps({"submission_token": token, "student_id": response.get("student_id", student_id)}, separators=(",", ":")), encoding="utf-8")
        os.chmod(temp, 0o600)
        temp.replace(path)
        return {"student_id": response.get("student_id", student_id)}

    def sync_once(self) -> dict[str, Any]:
        if not self._sync_lock.acquire(blocking=False):
            raise SyncError("A synchronization request is already in progress", retryable=True)
        try:
            return self._sync_once()
        finally:
            self._sync_lock.release()

    def _sync_once(self) -> dict[str, Any]:
        if not self.base_url:
            raise SyncError("Collector URL is not configured by the instructor", retryable=False)
        token = self._token()
        if not token:
            raise SyncError("Student enrollment is required before synchronization", status=401, retryable=False)
        watermark = self._request("GET", "/v1/submission/status", None, bearer=token)
        if isinstance(watermark.get("last_accepted_sequence"), dict):
            self.store.set_metadata("last_server_watermark", json.dumps(watermark["last_accepted_sequence"], sort_keys=True))
        batch = self.store.pending(self.batch_size)
        if not batch:
            return {"accepted": 0, "pending": 0, "receipt_id": None}
        try:
            result = self._request("POST", "/v1/events/batch", {"events": batch}, bearer=token)
        except SyncError as error:
            self.store.set_metadata("last_sync_error", self._safe_error(error))
            raise
        receipt = result.get("receipt")
        accepted = receipt.get("accepted_event_ids", []) if isinstance(receipt, dict) else []
        receipt_id = receipt.get("batch_id") if isinstance(receipt, dict) else None
        if not receipt_id or not isinstance(accepted, list):
            raise SyncError("Collector response did not include a durable receipt")
        self.store.acknowledge([str(item) for item in accepted], str(receipt_id))
        self.store.set_metadata("last_successful_sync", _now())
        self.store.set_metadata("last_sync_error", "")
        return {"accepted": len(accepted), "pending": self.store.status()["pending_events"], "receipt_id": receipt_id}

    def _request(self, method: str, path: str, payload: dict[str, Any] | None, *, bearer: str | None) -> dict[str, Any]:
        from urllib.parse import urlsplit

        parsed = urlsplit(self.base_url)
        local_http_allowed = os.environ.get("COURSE_COLLECTOR_ALLOW_HTTP", "").lower() in {"1", "true", "yes"}
        loopback_hosts = {"localhost", "127.0.0.1", "::1", "collector"}
        if parsed.scheme != "https" and not (parsed.scheme == "http" and local_http_allowed and parsed.hostname in loopback_hosts):
            raise SyncError("Collector URL must use HTTPS; plain HTTP is permitted only for explicit local staging", retryable=False)
        data = canonical_json(payload) if payload is not None else None
        headers = {"Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        if bearer:
            headers["Authorization"] = f"Bearer {bearer}"
        request = urllib.request.Request(self.base_url + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read(1_000_001)
                if len(body) > 1_000_000:
                    raise SyncError("Collector response exceeds size limit", retryable=False)
                decoded = json.loads(body or b"{}")
                return decoded if isinstance(decoded, dict) else {}
        except urllib.error.HTTPError as error:
            detail = error.read(4096).decode("utf-8", errors="replace")
            retryable = error.code >= 500 or error.code in (408, 429)
            if error.code in (401, 403):
                detail = "Enrollment expired or rejected; ask the instructor for a new enrollment code."
            raise SyncError(f"Collector rejected request ({error.code}): {detail[:500]}", status=error.code, retryable=retryable) from error
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            raise SyncError(f"Collector is unreachable: {type(error).__name__}") from error
        except json.JSONDecodeError as error:
            raise SyncError("Collector returned invalid JSON") from error

    @staticmethod
    def _safe_error(error: Exception) -> str:
        return str(error)[:500]


class SyncWorker:
    def __init__(self, store: EventStore, client: SyncClient, interval: int = 120, on_event=None):
        self.store = store
        self.client = client
        self.interval = max(30, int(interval))
        self.on_event = on_event
        self._stop = False
        self._force = False

    def request_sync(self) -> None:
        self._force = True

    def run(self) -> None:
        # An initial short delay leaves Jupyter startup and normal notebook work
        # independent of collector readiness.
        deadline = time.monotonic() + 15
        backoff = self.interval
        while not self._stop:
            if not self._force and time.monotonic() < deadline:
                time.sleep(min(1, max(0.05, deadline - time.monotonic())))
                continue
            self._force = False
            try:
                self.store.import_spools()
                result = self.client.sync_once()
                if result.get("accepted") and self.on_event and self.client.base_url:
                    self.on_event("sync.receipt", str(result.get("receipt_id") or time.time_ns()), result)
                backoff = self.interval
                deadline = time.monotonic() + self.interval
            except SyncError as error:
                if self.on_event and self.client.base_url:
                    self.on_event("sync.failure", f"attempt:{time.time_ns()}", {"status": error.status, "message": str(error)[:500], "retryable": error.retryable})
                # Configuration/auth errors wait for a manual request or the
                # next interval. Transient errors use capped exponential delay.
                if error.retryable:
                    backoff = min(1800, max(self.interval, int(backoff * 2)))
                    backoff += random.randint(0, min(30, backoff // 4))
                else:
                    backoff = self.interval
                deadline = time.monotonic() + backoff
            except Exception as error:  # Keep background collection non-blocking.
                self.store.set_metadata("last_sync_error", f"Local sync error: {type(error).__name__}")
                backoff = min(1800, max(self.interval, int(backoff * 2)))
                deadline = time.monotonic() + backoff

    def stop(self) -> None:
        self._stop = True
