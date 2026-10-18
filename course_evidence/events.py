"""Versioned, privacy-filtered classroom evidence events."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any

SCHEMA_VERSION = "1.0"
COURSE_ID = "keio-2026"
MAX_TEXT_CHARS = 20_000
MAX_SNAPSHOT_CHARS = 50_000
MAX_EVENT_BYTES = 128_000

_SECRET_PATTERNS = (
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{12,}"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)
_SENSITIVE_PATH = re.compile(r"(?i)(?:^|[/\\])(?:\.env(?:\.[^/\\]+)?|[^/\\]*credentials?[^/\\]*|id_rsa|id_ed25519)(?:$|[/\\])")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def redact_text(value: str, *, limit: int = MAX_TEXT_CHARS) -> str:
    text = value[:limit]
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text


def redact_value(value: Any, *, key: str = "") -> Any:
    if _SENSITIVE_PATH.search(key):
        return "[REDACTED]"
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, list):
        return [redact_value(item, key=key) for item in value[:100]]
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for child_key, child in value.items():
            if re.search(r"(?i)(?:api.?key|access.?token|secret|password|credential|authorization)", child_key):
                cleaned[child_key] = "[REDACTED]"
            else:
                cleaned[child_key] = redact_value(child, key=child_key)
        return cleaned
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return redact_text(str(value))


def stable_event_id(device_id: str, source: str, source_ref: str) -> str:
    raw = f"{COURSE_ID}\0{device_id}\0{source}\0{source_ref}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def content_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def event_content_hash(event: dict[str, Any]) -> str:
    """Hash substantive event bytes while ignoring retry/sequence metadata."""
    stable = {key: value for key, value in event.items() if key not in {"sequence", "timestamp_utc"}}
    return content_hash(stable)


def validate_event(event: Any, *, max_bytes: int = MAX_EVENT_BYTES) -> dict[str, Any]:
    if not isinstance(event, dict):
        raise ValueError("event must be an object")
    if len(canonical_json(event)) > max_bytes:
        raise ValueError("event exceeds size limit")
    required = ("schema_version", "event_id", "course_id", "device_id", "session_id", "timestamp_utc", "kind", "source", "payload")
    missing = [key for key in required if key not in event]
    if missing:
        raise ValueError("missing required event fields: " + ", ".join(missing))
    if event["schema_version"] != SCHEMA_VERSION:
        raise ValueError("unsupported schema_version")
    for key in ("event_id", "device_id", "session_id", "kind", "source"):
        if not isinstance(event[key], str) or not event[key] or len(event[key]) > 200:
            raise ValueError(f"invalid {key}")
    if event["course_id"] != COURSE_ID:
        raise ValueError("unsupported course_id")
    if not isinstance(event["payload"], dict):
        raise ValueError("payload must be an object")
    return event


def make_event(
    *, device_id: str, session_id: str, kind: str, source: str,
    source_ref: str, payload: dict[str, Any], student_id: str | None = None,
    agent: str | None = None, skill: str | None = None,
    message_id: str | None = None, related_question_id: str | None = None,
) -> dict[str, Any]:
    event: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "event_id": stable_event_id(device_id, source, source_ref),
        "course_id": COURSE_ID,
        "device_id": device_id,
        "session_id": session_id,
        "timestamp_utc": utc_now(),
        "kind": kind,
        "source": source,
        "payload": redact_value(payload),
    }
    if student_id:
        event["student_id"] = student_id
    if agent:
        event["agent"] = agent
    if skill:
        event["skill"] = skill
    if message_id:
        event["message_id"] = message_id
    if related_question_id:
        event["related_question_id"] = related_question_id
    return event


def new_device_id() -> str:
    return str(uuid.uuid4())
