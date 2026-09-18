"""Probe-only: summarize ZCode app-server JSON-RPC lines. Never dump secrets."""

from __future__ import annotations

import atexit
import hashlib
import json
import os
import threading

_DUMP = os.environ.get("KAOLA_ZCODE_UPSTREAM_DUMP")
_MARKER = os.environ.get("KAOLA_PROBE_MARKER", "")
_SENTINEL = os.environ.get("KAOLA_PROBE_SENTINEL", "")
_LOCK = threading.Lock()
_RECORDS: list[dict] = []
_SECRET_SUBSTR = (
    "apikey", "api_key", "token", "secret", "password", "credential",
    "authorization", "bearer",
)
_orig_loads = json.loads


def _secretish(key: str) -> bool:
    k = key.lower().replace("-", "_")
    return any(s in k for s in _SECRET_SUBSTR)


def _rel_or_hash(text: str) -> dict:
    if _MARKER and text == _MARKER:
        return {"kind": "probe_marker"}
    if _SENTINEL and text.startswith(_SENTINEL):
        return {"kind": "sentinel_rel", "rel": text[len(_SENTINEL):].lstrip("/")}
    digest = hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()[:12]
    return {"kind": "opaque", "len": len(text), "sha12": digest}


def _summarize_value(key: str, value):
    if _secretish(key):
        return {"redacted": True, "type": type(value).__name__}
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return _rel_or_hash(value)
    if isinstance(value, dict):
        return {str(k): _summarize_value(str(k), v) for k, v in value.items()}
    if isinstance(value, list):
        return [_summarize_value(key, item) for item in value[:8]]
    return {"type": type(value).__name__}


def _summarize_payload(payload: dict) -> dict:
    out = {"keys": sorted(str(k) for k in payload.keys())}
    for field in ("kind", "toolCallId", "toolName", "status"):
        if field in payload and payload[field] is not None:
            out[field] = payload[field]
    if "input" in payload:
        raw = payload.get("input")
        out["input_present"] = True
        out["input_type"] = type(raw).__name__
        if isinstance(raw, dict):
            out["input_keys"] = sorted(str(k) for k in raw.keys())
            out["input"] = {str(k): _summarize_value(str(k), v) for k, v in raw.items()}
        elif raw is None:
            out["input"] = None
        else:
            out["input"] = _summarize_value("input", raw)
    else:
        out["input_present"] = False
    for field in ("stdoutTail", "stderrTail", "output", "result", "message"):
        if field in payload:
            val = payload.get(field)
            out[field] = {
                "present": True,
                "type": type(val).__name__,
                "len": len(val) if isinstance(val, str) else None,
            }
    if payload.get("kind") == "batch":
        items = payload.get("items") or []
        out["batch_len"] = len(items) if isinstance(items, list) else None
        if isinstance(items, list):
            out["items"] = [_summarize_payload(item) for item in items[:16] if isinstance(item, dict)]
    return out


def _maybe_record(msg: dict) -> None:
    if not isinstance(msg, dict):
        return
    method = msg.get("method")
    if method == "session/event":
        params = msg.get("params") or {}
        etype = params.get("type")
        payload = params.get("payload") or {}
        if not isinstance(payload, dict):
            payload = {}
        interesting = (
            etype in ("model.streaming", "tool.updated")
            or payload.get("kind") == "tool_call"
            or "toolCallId" in payload
            or "input" in payload
        )
        if etype == "model.streaming" and payload.get("kind") not in ("tool_call",):
            if not interesting:
                return
            if payload.get("kind") in ("text_delta", "reasoning_delta"):
                return
        rec = {
            "channel": "session/event",
            "type": etype,
            "payload": _summarize_payload(payload),
        }
        with _LOCK:
            _RECORDS.append(rec)
        return
    if method == "interaction/requestPermission":
        params = msg.get("params") or {}
        rec = {
            "channel": "interaction/requestPermission",
            "toolName": params.get("toolName"),
            "toolCallId": params.get("toolCallId"),
            "input_present": "input" in params,
            "params_keys": sorted(str(k) for k in params.keys()),
        }
        if isinstance(params.get("input"), dict):
            rec["input_keys"] = sorted(str(k) for k in params["input"].keys())
            rec["input"] = {
                str(k): _summarize_value(str(k), v) for k, v in params["input"].items()
            }
        with _LOCK:
            _RECORDS.append(rec)


def loads(s, *args, **kwargs):
    msg = _orig_loads(s, *args, **kwargs)
    try:
        if isinstance(msg, dict):
            _maybe_record(msg)
    except Exception:
        pass
    return msg


def _flush() -> None:
    if not _DUMP:
        return
    try:
        with _LOCK:
            payload = list(_RECORDS)
        with open(_DUMP, "w", encoding="utf-8") as handle:
            json.dump({"n": len(payload), "events": payload}, handle, indent=2)
            handle.write("\n")
    except OSError:
        return


json.loads = loads  # type: ignore[assignment]
atexit.register(_flush)
