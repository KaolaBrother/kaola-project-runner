#!/usr/bin/env python3
"""Opt-in Droid/Cursor project precompact hook. Uses the existing KPR holder socket.

No native Stop hook, completed-compaction claim, prompt replay or service.
The binding is supplied by the owner after the exact session starts.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import socket
import sys


def request(path: str, op: str, params: dict) -> dict:
    attempted = False
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.settimeout(10)
            connection.connect(path)
            attempted = True
            connection.sendall(json.dumps({"op": op, "params": params}).encode() + b"\n")
            data = bytearray()
            while len(data) < 1024 * 1024:
                chunk = connection.recv(65536)
                if not chunk:
                    break
                data.extend(chunk)
                if b"\n" in data:
                    result = json.loads(data.partition(b"\n")[0])
                    if isinstance(result, dict):
                        return result
                    break
    except (OSError, ValueError):
        pass
    # Connect failure is before write. Send failure/lost reply is unknown.
    return {"error": {"code": "holder-response-unavailable"},
            "notice_write": "unknown" if attempted and op == "compact_notice" else "not_attempted"}


def forward(binding: dict, payload: dict) -> dict:
    required = ("socket_path", "holder_instance_id", "acp_session_id", "project_root",
                "platform_skill_path")
    if (any(not isinstance(binding.get(key), str) or not binding[key] for key in required)
            or not Path(binding["socket_path"]).is_absolute()
            or not isinstance(binding.get("task_skill_paths"), list)
            or not binding["task_skill_paths"]):
        return {"notice_write": "not_attempted", "reason": "invalid-binding"}
    event = {"droid": "PreCompact", "cursor-cli": "preCompact"}.get(binding.get("platform"))
    ids = [payload[key] for key in ("session_id", "conversation_id") if key in payload]
    root_matches = (payload.get("cwd") == binding["project_root"]
                    if binding.get("platform") == "droid" else
                    bool(binding.get("hook_project_root")) and
                    payload.get("workspace_roots") == [binding["hook_project_root"]])
    if (event is None or payload.get("hook_event_name") != event
            or not ids or any(value != binding["acp_session_id"] for value in ids)
            or not root_matches):
        return {"notice_write": "not_attempted", "reason": "foreign-or-unsupported-hook"}
    state = request(binding["socket_path"], "state", {})
    if (state.get("holder_instance_id") != binding["holder_instance_id"]
            or state.get("acp_session_id") != binding["acp_session_id"]
            or not state.get("turn_active") or state.get("turn_request_id") is None):
        return {"notice_write": "not_attempted", "reason": "exact-active-holder-required"}
    result = request(binding["socket_path"], "compact_notice", {
        "expected_holder_instance_id": binding["holder_instance_id"],
        "expected_acp_session_id": binding["acp_session_id"],
        "expected_prior_turn_request_id": state["turn_request_id"],
        "hook_event_name": event, "hook_session_id": ids[0],
        "hook_cwd": payload.get("cwd"), "hook_workspace_roots": payload.get("workspace_roots"),
        "project_root": binding["project_root"],
        "platform_skill_path": binding["platform_skill_path"],
        "task_skill_paths": binding["task_skill_paths"]})
    # Never print arbitrary input, auth, headers or vendor response bodies.
    if "error" in result:
        return {"notice_write": result.get("notice_write", "not_admitted"),
                "reason": (result.get("error") or {}).get("code", "holder-error")}
    if "notice_pending" not in result and "notice_write" not in result:
        return {"notice_write": "unknown", "reason": "invalid-notice-reply"}
    return {key: result[key] for key in (
        "notice_pending", "notice_recorded", "acp_mutation_performed",
        "completion", "prior_turn_request_id", "reason",
        "new_notice_accepted", "notice_write") if key in result}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binding", type=Path, required=True)
    args = parser.parse_args()
    try:
        binding = json.loads(args.binding.read_text())
        payload = json.load(sys.stdin)
        if not isinstance(binding, dict) or not isinstance(payload, dict):
            raise ValueError("object required")
        result = forward(binding, payload)
    except (OSError, ValueError):
        result = {"notice_write": "not_attempted", "reason": "invalid-hook-input"}
    print(json.dumps(result), file=sys.stderr)
    # A notice failure must not block the native compaction.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
