#!/usr/bin/env python3
"""Issue #81 live-evidence tee: sits where the adapter expects `node`, spawns
the real `node zcode.cjs app-server --stdio`, and records a STRICT WHITELIST
summary of backend stdio traffic to an NDJSON log.

Persisted record kinds — nothing else is ever written:
  out  v4/command.sendText -> commandId_sha256, expectedTurnId_sha256,
                              requestedDelivery (finite enum), text_sha256
  in   turn.steerQueued    -> kind, targetTurnId_sha256, commandId_sha256,
                              sourceCommandIds_sha256[], queryIds_sha256[],
                              pendingInputId_sha256, pendingInputIds_sha256[],
                              injectedMessageIds_sha256[], delivery/admittedDelivery
                              (finite enum), text_sha256s[]
  in   turn.steerDrained   -> same whitelist
  any  other JSON line     -> {kind:"other",   bytes}   (count-only)
  any  non-JSON line       -> {kind:"nonjson", bytes}   (count-only)

Hard rules: every ID is persisted only as a stable SHA-256 fingerprint for
correlation (arrays capped at 32 items, scalars at 4096 chars). No raw line,
raw message, raw ID, free-form scalar, text, stderr, token, or credential
can ever reach the log — backend stderr goes to DEVNULL and raw stdio
forwarding is in-memory only. `summarize()` is pure so the fixture test can
feed fake secrets through every would-be field and prove they cannot land.

Config is read from `backend-tee-config.json` next to this file:
    {"real_node": "/opt/homebrew/bin/node", "log": "/path/backend-tee.jsonl"}
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import threading

MAX_SCALAR_CHARS = 4096
MAX_ARRAY_ITEMS = 32
DELIVERY_ENUM = frozenset(("guide", "queue"))


def sha256_text(value) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    return hashlib.sha256(
        value[:MAX_SCALAR_CHARS].encode("utf-8")).hexdigest()[:16]


def _hash_array(values) -> list[str] | None:
    if not isinstance(values, list):
        return None
    return [h for h in (sha256_text(v) for v in values[:MAX_ARRAY_ITEMS]) if h]


def _enum(value) -> str | None:
    return value if value in DELIVERY_ENUM else None


def _event_text_hashes(payload: dict) -> list[str]:
    intent = payload.get("intent") or {}
    texts = [payload.get("input"), payload.get("inputPreview"),
             intent.get("text")]
    for item in payload.get("drainedInputs") or []:
        if isinstance(item, dict):
            texts.append(item.get("text"))
            inner = item.get("intent") or {}
            texts.append(inner.get("text"))
    return sorted({h for h in (sha256_text(t) for t in texts) if h})


def _byte_count(raw_line: str) -> int:
    return len(raw_line.encode("utf-8", "replace"))


def summarize(direction: str, raw_line: str) -> dict:
    """Strict-whitelist summary of one backend stdio line. Any content not on
    the finite field list reduces to {dir, kind, bytes} — raw lines, raw IDs,
    free-form scalars, text, stderr, and credentials can never appear."""
    try:
        msg = json.loads(raw_line)
    except (ValueError, TypeError):
        return {"dir": direction, "kind": "nonjson",
                "bytes": _byte_count(raw_line)}
    if not isinstance(msg, dict):
        return {"dir": direction, "kind": "nonjson",
                "bytes": _byte_count(raw_line)}
    method = msg.get("method")
    params = msg.get("params") or {}
    if not isinstance(params, dict):
        params = {}
    if method == "v4/command" and params.get("type") == "sendText":
        payload = params.get("payload") or {}
        if not isinstance(payload, dict):
            payload = {}
        return {"dir": direction, "kind": "v4/command.sendText",
                "commandId_sha256": sha256_text(params.get("commandId")),
                "expectedTurnId_sha256": sha256_text(
                    payload.get("expectedTurnId")),
                "requestedDelivery": _enum(payload.get("requestedDelivery")),
                "text_sha256": sha256_text(payload.get("text"))}
    if params.get("type") in ("turn.steerQueued", "turn.steerDrained"):
        payload = params.get("payload") or {}
        if not isinstance(payload, dict):
            payload = {}
        intent = payload.get("intent") or {}
        source_ids = [
            (item.get("intent") or {}).get("sourceCommandId")
            for item in (payload.get("drainedInputs") or [])[:MAX_ARRAY_ITEMS]
            if isinstance(item, dict)]
        source_ids += [intent.get("sourceCommandId")]
        return {"dir": direction, "kind": params.get("type"),
                "targetTurnId_sha256": sha256_text(
                    payload.get("targetTurnId")),
                "commandId_sha256": sha256_text(
                    intent.get("sourceCommandId")
                    or payload.get("inputId")
                    or payload.get("queryId")),
                "sourceCommandIds_sha256": _hash_array(source_ids) or [],
                "queryIds_sha256": _hash_array(payload.get("queryIds")),
                "pendingInputId_sha256": sha256_text(
                    payload.get("pendingInputId")),
                "pendingInputIds_sha256": _hash_array(
                    payload.get("pendingInputIds")),
                "injectedMessageIds_sha256": _hash_array(
                    payload.get("injectedMessageIds")),
                "delivery": _enum(payload.get("delivery")),
                "admittedDelivery": _enum(intent.get("admittedDelivery")),
                "text_sha256s": _event_text_hashes(payload)}
    return {"dir": direction, "kind": "other", "bytes": _byte_count(raw_line)}


def main() -> int:
    conf_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "backend-tee-config.json")
    with open(conf_path, "r", encoding="utf-8") as fh:
        conf = json.load(fh)
    real_node = conf["real_node"]
    log = open(conf["log"], "w", encoding="utf-8", buffering=1)
    lock = threading.Lock()

    def record(direction: str, line: str) -> None:
        rec = summarize(direction, line.strip())
        with lock:
            log.write(json.dumps(rec, ensure_ascii=False) + "\n")

    child = subprocess.Popen(
        [real_node, *sys.argv[1:]],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,  # backend stderr is never read or persisted
        text=True, bufsize=1)

    def pump_out() -> None:  # adapter stdin -> backend stdin
        assert child.stdin is not None
        try:
            for line in sys.stdin:
                child.stdin.write(line)
                child.stdin.flush()
                record("out", line)
        except (BrokenPipeError, ValueError):
            pass
        try:
            child.stdin.close()
        except (BrokenPipeError, ValueError):
            pass

    threading.Thread(target=pump_out, daemon=True).start()
    assert child.stdout is not None
    for line in child.stdout:  # backend stdout -> adapter stdout
        sys.stdout.write(line)
        sys.stdout.flush()
        record("in", line)
    return child.wait()


if __name__ == "__main__":
    raise SystemExit(main())
