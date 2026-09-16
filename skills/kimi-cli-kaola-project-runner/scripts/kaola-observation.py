#!/usr/bin/env python3
"""Canonical observation and receipt primitives for the tmux control plane."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any


PANE_REVISION_FIELDS = (
    "pane_id",
    "pane_dead",
    "pane_width",
    "pane_height",
    "cursor_x",
    "cursor_y",
    "cursor_flag",
    "alternate_on",
    "history_size",
    "history_bytes",
    "relay_epoch",
    "child_input_offset",
    "child_output_offset",
    "child_output_digest",
    "resize_revision",
)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _digest(prefix: str, value: Any) -> str:
    return prefix + hashlib.sha256(canonical_bytes(value)).hexdigest()


def _fingerprint(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_process_table(text: str) -> list[dict[str, Any]]:
    """Parse the portable ps projection, rejecting ambiguous or duplicate rows."""

    rows: list[dict[str, Any]] = []
    seen: set[int] = set()
    pattern = re.compile(r"^\s*(\d+)\s+(\d+)\s+(\S+)\s+(\S+)(?:\s+(.*))?$")
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        match = pattern.match(line)
        if match is None:
            raise ValueError(f"malformed process row {number}")
        pid, ppid = int(match.group(1)), int(match.group(2))
        if pid <= 0 or ppid < 0 or pid in seen:
            raise ValueError(f"invalid or duplicate process pid at row {number}")
        seen.add(pid)
        command = os.path.basename(match.group(4).rstrip("/"))
        if not command and match.group(5):
            command = os.path.basename(match.group(5).split(None, 1)[0].rstrip("/"))
        if not command or "/" in command or any(ch.isspace() for ch in command):
            raise ValueError(f"invalid process command at row {number}")
        rows.append(
            {"pid": pid, "ppid": ppid, "state": match.group(3), "command": command}
        )
    rows.sort(key=lambda row: row["pid"])
    return rows


def descendants(root_pid: int, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_parent: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        by_parent.setdefault(row["ppid"], []).append(row)
    found: list[dict[str, Any]] = []
    pending = [root_pid]
    visited = {root_pid}
    while pending:
        parent = pending.pop()
        for row in by_parent.get(parent, []):
            pid = row["pid"]
            if pid in visited:
                raise ValueError("cyclic process tree")
            visited.add(pid)
            pending.append(pid)
            if not row["state"].upper().startswith("Z"):
                found.append(dict(row))
    found.sort(key=lambda row: row["pid"])
    return found


def make_pane_revision(facts: dict[str, Any], frame: str) -> str:
    value = {field: facts.get(field) for field in PANE_REVISION_FIELDS}
    value["raw_current_frame"] = frame
    return _digest("kpr-pane-v2:", value)


def make_snapshot_id(observation: dict[str, Any]) -> str:
    hard = dict(observation.get("hard_evidence") or {})
    hard.pop("pane_input_off", None)
    hard.pop("history_size", None)
    hard.pop("history_bytes", None)
    relay = dict(observation.get("relay") or {})
    relay.pop("state", None)
    relay.pop("child_output_offset", None)
    relay.pop("child_output_digest", None)
    value = {
        "schema_version": observation.get("schema_version"),
        "platform": observation.get("platform"),
        "repo": observation.get("repo"),
        "session": observation.get("session"),
        "raw_current_frame": observation.get("raw_current_frame"),
        "hard_evidence": hard,
        "relay": relay,
        "child_processes": observation.get("child_processes"),
        "child_process_count": observation.get("child_process_count"),
        "native_approval": observation.get("native_approval"),
        "later_output_barrier": observation.get("later_output_barrier"),
        "git": observation.get("git"),
        "model": observation.get("model"),
    }
    return _digest("kpr-snapshot-v2:", value)


def make_decision_marker(frame: str) -> dict[str, Any] | None:
    labels = (
        "HUMAN_DECISION_REQUIRED",
        "Decision:",
        "Evidence:",
        "Recommendation:",
        "Safe options:",
        "Paused state:",
    )
    lines = frame.splitlines()
    for start, line in enumerate(lines):
        if line.rstrip() != labels[0]:
            continue
        block = lines[start : start + len(labels)]
        if len(block) != len(labels):
            continue
        if any(
            not candidate.rstrip().startswith(label)
            for candidate, label in zip(block[1:], labels[1:])
        ):
            continue
        exact = "\n".join(candidate.rstrip() for candidate in block) + "\n"
        fingerprint = _fingerprint(exact)
        suffix = fingerprint.split(":", 1)[1]
        return {
            "decision_id": "kpr-decision-v1:" + suffix,
            "fingerprint": fingerprint,
            "current_frame": True,
        }
    # Raw-mode TUIs can emit LF without CR, so a logical marker line may wrap
    # diagonally across physical grid rows. Whitespace-free label matching
    # recovers only the fixed six-field structure; it does not classify prose.
    compact = "".join(line.strip() for line in lines)
    pattern = re.compile(
        r"HUMAN_DECISION_REQUIRED"
        r"Decision:(.+?)Evidence:(.+?)Recommendation:(.+?)"
        r"Safe options:(.+?)Paused state:(.+?)(?:shells:|agents:|[❯›>]|$)"
    )
    match = pattern.search(compact)
    if match and all(value.strip() for value in match.groups()):
        exact = "\n".join(
            (
                labels[0],
                labels[1] + match.group(1).strip(),
                labels[2] + match.group(2).strip(),
                labels[3] + match.group(3).strip(),
                labels[4] + match.group(4).strip(),
                labels[5] + match.group(5).strip(),
            )
        ) + "\n"
        fingerprint = _fingerprint(exact)
        suffix = fingerprint.split(":", 1)[1]
        return {
            "decision_id": "kpr-decision-v1:" + suffix,
            "fingerprint": fingerprint,
            "current_frame": True,
        }
    return None


def make_answer_receipt(fields: dict[str, Any]) -> str:
    keys = (
        "schema_version",
        "platform",
        "session",
        "repo",
        "decision_id",
        "replaced_editor_fingerprint",
        "answer_fingerprint",
        "based_on_snapshot",
        "relay_epoch",
        "child_start_fingerprint",
        "prepared_pane_revision",
        "submitted_output_offset",
        "child_output_digest",
    )
    return _digest("kpr-answer-v2:", {key: fields[key] for key in keys})


def claude_frame_facts(
    frame: str, activity_hint: str = "unknown", pane_facts: dict[str, Any] | None = None
) -> dict[str, Any]:
    stripped = [line.rstrip(" ") for line in frame.splitlines()]
    joined = "\n".join(stripped)
    tool = all(
        phrase in joined
        for phrase in ("This command requires approval", "Do you want to proceed?")
    )
    trust = all(phrase in joined for phrase in ("Trust this folder?", "Enter to confirm"))
    if tool or trust:
        block = "\n".join(
            line for line in stripped if line.strip()
        ) + "\n"
        approval = {
            "state": "present",
            "kind": "tool" if tool else "trust",
            "fingerprint": _fingerprint(block),
        }
        editor_state, editor_fingerprint = "unknown", None
    else:
        prompt: re.Match[str] | None = None
        prompt_index: int | None = None
        for index, line in enumerate(stripped):
            match = re.match(r"^\s*[❯›>] ?(.*)$", line)
            if match:
                prompt = match
                prompt_index = index
        if prompt is None:
            editor_state, editor_fingerprint = "unknown", None
            approval = {"state": "unknown", "kind": None, "fingerprint": None}
        else:
            editor_lines = [prompt.group(1)]
            cursor_y = (pane_facts or {}).get(
                "cursor_logical_y", (pane_facts or {}).get("cursor_y")
            )
            input_origin = prompt.start(1)
            if (
                prompt_index is not None
                and isinstance(cursor_y, int)
                and prompt_index < cursor_y < len(stripped)
            ):
                for continuation in stripped[prompt_index + 1 : cursor_y + 1]:
                    prefix = " " * input_origin
                    if not continuation.startswith(prefix):
                        editor_lines = []
                        break
                    editor_lines.append(continuation[input_origin:])
            if not editor_lines:
                editor_state, editor_fingerprint = "unknown", None
                approval = {"state": "unknown", "kind": None, "fingerprint": None}
            else:
                editor = "\n".join(editor_lines)
                editor_state = "empty" if editor == "" else "nonempty"
                editor_fingerprint = _fingerprint(editor)
                approval = {"state": "absent", "kind": None, "fingerprint": None}

    def counter(name: str) -> int | None:
        matches = re.findall(rf"(?m)^\s*{name}:\s*(\d+)\s*$", joined)
        return int(matches[-1]) if matches else None

    visible_shell_count = counter("shells")
    visible_agent_count = counter("agents")
    if (
        editor_state == "nonempty"
        and re.search(r"Claude Code v\d+\.\d+\.\d+", joined)
        and re.search(r'^\s*❯\s*Try "[^"]+"\s*$', joined, re.MULTILINE)
        and "auto mode on" in joined
        and re.search(r"^\s*Opus \d+ \| ", joined, re.MULTILINE)
    ):
        editor_state = "empty"
        editor_fingerprint = _fingerprint("")
        visible_shell_count = 0
        visible_agent_count = 0

    return {
        "editor_state": editor_state,
        "editor_fingerprint": editor_fingerprint,
        "visible_shell_count": visible_shell_count,
        "visible_agent_count": visible_agent_count,
        "native_approval": approval,
        "structured_decision_marker": make_decision_marker(frame),
        "activity_hint": activity_hint,
    }


def generic_frame_facts(
    frame: str, activity_hint: str = "unknown", pane_facts: dict[str, Any] | None = None
) -> dict[str, Any]:
    lines = [line.rstrip(" ") for line in frame.splitlines()]
    prompt: re.Match[str] | None = None
    prompt_index: int | None = None
    for index, line in enumerate(lines):
        match = re.match(r"^\s*[❯›→>] ?(.*\S)?\s*$", line)
        if match:
            prompt = match
            prompt_index = index
    if prompt is None:
        state, fingerprint = "unknown", None
        approval_state = "unknown"
    else:
        editor_lines = [prompt.group(1) or ""]
        cursor_y = (pane_facts or {}).get(
            "cursor_logical_y", (pane_facts or {}).get("cursor_y")
        )
        input_origin = prompt.start(1)
        if (
            prompt_index is not None
            and isinstance(cursor_y, int)
            and prompt_index < cursor_y < len(lines)
        ):
            for continuation in lines[prompt_index + 1 : cursor_y + 1]:
                prefix = " " * input_origin
                if not continuation.startswith(prefix):
                    editor_lines = []
                    break
                editor_lines.append(continuation[input_origin:])
        if not editor_lines:
            state, fingerprint = "unknown", None
            approval_state = "unknown"
        else:
            editor = "\n".join(editor_lines)
            state = "empty" if not editor else "nonempty"
            fingerprint = _fingerprint(editor)
            approval_state = "absent"
    # These adapters do not expose Claude-style numeric shell/agent counters.
    # A positively recognized prompt therefore establishes that their applicable
    # visible-counter surface is empty; an unrecognized layout remains unknown.
    visible_count = 0 if prompt is not None else None
    return {
        "editor_state": state,
        "editor_fingerprint": fingerprint,
        "visible_shell_count": visible_count,
        "visible_agent_count": visible_count,
        "native_approval": {"state": approval_state, "kind": None, "fingerprint": None},
        "structured_decision_marker": make_decision_marker(frame),
        "activity_hint": activity_hint,
    }


def opencode_frame_facts(
    frame: str, activity_hint: str = "unknown", pane_facts: dict[str, Any] | None = None
) -> dict[str, Any]:
    facts = generic_frame_facts(frame, activity_hint, pane_facts)
    # OpenCode 1.18.x renders an empty editor as a placeholder rather than a
    # prompt glyph. Require the complete live chrome so prose in history cannot
    # fabricate an empty editor.
    if (
        facts["editor_state"] == "unknown"
        and "OpenCode" in frame
        and "Ask anything..." in frame
        and "ctrl+p cmd" in frame
    ):
        facts.update(
            editor_state="empty",
            editor_fingerprint=_fingerprint(""),
            visible_shell_count=0,
            visible_agent_count=0,
            native_approval={"state": "absent", "kind": None, "fingerprint": None},
        )
    return facts


def kimi_frame_facts(
    frame: str, activity_hint: str = "unknown", pane_facts: dict[str, Any] | None = None
) -> dict[str, Any]:
    facts = generic_frame_facts(frame, activity_hint, pane_facts)
    if (
        "Trust this folder?" in frame
        and "Project-level MCP servers are disabled" in frame
        and "Enter select" in frame
        and "Don't trust" in frame
    ):
        facts.update(
            editor_state="unknown",
            editor_fingerprint=None,
            visible_shell_count=0,
            visible_agent_count=0,
            native_approval={
                "state": "present",
                "kind": "workspace-trust",
                "fingerprint": _fingerprint("kimi-workspace-trust"),
            },
        )
    return facts


def cursor_frame_facts(
    frame: str, activity_hint: str = "unknown", pane_facts: dict[str, Any] | None = None
) -> dict[str, Any]:
    facts = generic_frame_facts(frame, activity_hint, pane_facts)
    if (
        facts["editor_state"] == "nonempty"
        and "Cursor Agent" in frame
        and re.search(r"^\s*v\d{4}\.\d{2}\.\d{2}-[0-9a-f]+\s*$", frame, re.MULTILINE)
        and re.search(r"^\s*→ Plan, search, build anything\s*$", frame, re.MULTILINE)
        and "Run Everything" in frame
    ):
        facts.update(
            editor_state="empty",
            editor_fingerprint=_fingerprint(""),
            visible_shell_count=0,
            visible_agent_count=0,
            native_approval={"state": "absent", "kind": None, "fingerprint": None},
        )
    return facts


def _boolean(name: str, default: bool = False) -> bool:
    return os.environ.get(name, "true" if default else "false") == "true"


def _integer(name: str) -> int | None:
    value = os.environ.get(name, "")
    return int(value) if value not in {"", "null"} else None


def _git_facts(repo: str) -> dict[str, Any]:
    def run(*args: str) -> str:
        result = subprocess.run(
            ["git", "-C", repo, *args], text=True, capture_output=True, check=False
        )
        return result.stdout.strip() if result.returncode == 0 else ""

    branch = run("branch", "--show-current") or "DETACHED"
    head = run("rev-parse", "--short=12", "HEAD") or "UNBORN"
    changed_count = len(run("status", "--porcelain=v1").splitlines())
    upstream = run("rev-parse", "--abbrev-ref", "@{u}")
    ahead = behind = -1
    if upstream:
        counts = run("rev-list", "--left-right", "--count", f"HEAD...{upstream}").split()
        if len(counts) == 2:
            ahead, behind = int(counts[0]), int(counts[1])
    return {
        "branch": branch,
        "head": head,
        "clean": changed_count == 0,
        "changed_count": changed_count,
        "upstream": upstream,
        "ahead": ahead,
        "behind": behind,
    }


def build_from_environment() -> dict[str, Any]:
    frame = Path(os.environ["KPR_FRAME_FILE"]).read_text(encoding="utf-8")
    present = _boolean("KPR_PRESENT")
    hard = {
        "present": present,
        "owned": _boolean("KPR_OWNED"),
        "platform_match": _boolean("KPR_PLATFORM_MATCH"),
        "repo_match": _boolean("KPR_REPO_MATCH"),
        "pane_count": _integer("KPR_PANE_COUNT"),
        "pane_id": os.environ.get("KPR_PANE_ID") or None,
        "pane_dead": None if not present else _boolean("KPR_PANE_DEAD"),
        "pane_input_off": _boolean("KPR_PANE_INPUT_OFF"),
        "pane_path": os.environ.get("KPR_PANE_PATH") or None,
        "pane_pid": _integer("KPR_PANE_PID"),
        "pane_command": os.environ.get("KPR_PANE_COMMAND") or None,
        "pane_title": os.environ.get("KPR_PANE_TITLE") or None,
        "pane_process": os.environ.get("KPR_PANE_PROCESS") or None,
        "relay_process_match": _boolean("KPR_RELAY_PROCESS_MATCH"),
        "process_match": _boolean("KPR_PROCESS_MATCH"),
        "tui_detected": _boolean("KPR_TUI"),
        "pane_width": _integer("KPR_PANE_WIDTH"),
        "pane_height": _integer("KPR_PANE_HEIGHT"),
        "cursor_x": _integer("KPR_CURSOR_X"),
        "cursor_y": _integer("KPR_CURSOR_Y"),
        "cursor_flag": None if not present else _boolean("KPR_CURSOR_FLAG"),
        "alternate_on": None if not present else _boolean("KPR_ALTERNATE_ON"),
        "history_size": _integer("KPR_HISTORY_SIZE"),
        "history_bytes": _integer("KPR_HISTORY_BYTES"),
    }
    adapter = json.loads(os.environ.get("KPR_ADAPTER_JSON", "{}"))
    relay = json.loads(os.environ.get("KPR_RELAY_JSON", "null"))
    if not isinstance(relay, dict):
        relay = {
            "managed": False, "protocol_version": None, "epoch": None,
            "pid": None, "start_fingerprint": None, "socket_path": None,
            "socket_owner_uid": None, "socket_mode": None,
            "peer_pid_verified": False, "state": "legacy-direct",
            "child_pid": None, "child_pgid": None,
            "child_start_fingerprint": None, "child_runtime_path": None,
            "child_process": None, "child_process_state": None,
            "child_process_match": False, "process_group_running": False,
            "lease_active": False,
            "child_input_offset": None, "child_output_offset": None,
            "child_output_digest": None, "resize_revision": None,
            "bracketed_paste": None, "terminal_fence": None,
        }
    process_value = os.environ.get("KPR_PROCESS_JSON", "null")
    processes = json.loads(process_value)
    result = os.environ.get("KPR_RESULT", "observed")
    if not present:
        result = "absent"
        processes = None
        adapter = {
            "editor_state": "unknown",
            "editor_fingerprint": None,
            "visible_shell_count": None,
            "visible_agent_count": None,
            "native_approval": {"state": "unknown", "kind": None, "fingerprint": None},
            "structured_decision_marker": None,
            "activity_hint": "unknown",
        }
    elif result == "unstable":
        adapter.update(editor_state="unknown", editor_fingerprint=None)

    pane_facts = {field: hard.get(field) for field in PANE_REVISION_FIELDS}
    pane_facts.update(
        relay_epoch=relay.get("epoch"),
        child_input_offset=relay.get("child_input_offset"),
        child_output_offset=relay.get("child_output_offset"),
        child_output_digest=relay.get("child_output_digest"),
        resize_revision=relay.get("resize_revision"),
    )
    pane_revision = make_pane_revision(pane_facts, frame) if present and relay.get("managed") else None
    barrier = json.loads(os.environ.get("KPR_BARRIER_JSON", "null"))
    observation = {
        "schema_version": 3,
        "result": result,
        "transport": {
            "selected": "pty",
            "default": os.environ.get("KPR_DEFAULT_TRANSPORT", "pty"),
            "alternatives": ["acp"],
            "reason": os.environ.get("KPR_TRANSPORT_REASON", "caller-override"),
        },
        "platform": os.environ["KPR_PLATFORM"],
        "runtime": os.environ["KPR_RUNTIME"],
        "session": os.environ["KPR_SESSION"],
        "repo": os.environ["KPR_REPO"],
        "snapshot_id": "",
        "pane_revision": pane_revision,
        "raw_current_frame": frame if present else "",
        "editor_state": adapter.get("editor_state", "unknown"),
        "editor_fingerprint": adapter.get("editor_fingerprint"),
        "hard_evidence": hard,
        "relay": relay,
        "child_processes": processes,
        "child_process_count": len(processes) if isinstance(processes, list) else None,
        "visible_shell_count": adapter.get("visible_shell_count"),
        "visible_agent_count": adapter.get("visible_agent_count"),
        "native_approval": adapter.get(
            "native_approval", {"state": "unknown", "kind": None, "fingerprint": None}
        ),
        "structured_decision_marker": adapter.get("structured_decision_marker"),
        "later_output_barrier": barrier,
        "activity_hint": adapter.get("activity_hint", "unknown"),
        "runtime_session_id": os.environ.get("KPR_RUNTIME_SESSION_ID", ""),
        "model": json.loads(os.environ.get("KPR_MODEL_JSON", "{}")),
        "git": _git_facts(os.environ["KPR_REPO"]),
        "evidence_flags": [],
    }
    failures: list[str] = []
    checks = (
        (not present, "session-absent"),
        (present and not hard["owned"], "unowned"),
        (present and not hard["platform_match"], "platform-mismatch"),
        (present and not hard["repo_match"], "repo-mismatch"),
        (present and hard["pane_count"] != 1, "unexpected-pane-count"),
        (present and hard["pane_dead"] is True, "pane-dead"),
        (present and hard["pane_input_off"], "pane-input-disabled"),
        (present and not relay.get("managed"), "relay-required"),
        (present and relay.get("managed") and not hard["relay_process_match"], "relay-process-mismatch"),
        (present and relay.get("managed") and not hard["process_match"], "process-mismatch"),
        (present and not hard["tui_detected"], "tui-not-detected"),
        (result == "unstable", "observation-unstable"),
        (observation["editor_state"] == "nonempty", "editor-nonempty"),
        (observation["editor_state"] == "unknown", "editor-unknown"),
        (observation["child_process_count"] is None, "child-processes-unknown"),
        ((observation["child_process_count"] or 0) > 0, "child-processes-active"),
        (observation["visible_shell_count"] is None, "visible-shell-unknown"),
        ((observation["visible_shell_count"] or 0) > 0, "visible-shell-active"),
        (observation["visible_agent_count"] is None, "visible-agent-unknown"),
        ((observation["visible_agent_count"] or 0) > 0, "visible-agent-active"),
        (observation["native_approval"].get("state") == "present", "native-approval-present"),
        (observation["native_approval"].get("state") == "unknown", "native-approval-unknown"),
        (observation["structured_decision_marker"] is not None, "structured-decision-present"),
        (barrier is not None and barrier.get("state") in {"pending", "output-seen"}, "awaiting-later-output"),
    )
    failures.extend(name for condition, name in checks if condition)
    observation["evidence_flags"] = sorted(set(failures))
    observation["snapshot_id"] = make_snapshot_id(observation) if present and relay.get("managed") else None
    return observation


def status_view(observation: dict[str, Any]) -> dict[str, Any]:
    hard = observation["hard_evidence"]
    git = observation["git"]
    result = dict(observation)
    result.update(
        {
            "activity": observation["activity_hint"],
            "present": hard["present"],
            "owned": hard["owned"],
            "platform_match": hard["platform_match"],
            "repo_match": hard["repo_match"],
            "tui_detected": hard["tui_detected"],
            "pane_count": hard["pane_count"],
            "pane_id": hard["pane_id"] or "",
            "pane_path": hard["pane_path"] or "",
            "pane_command": hard["pane_command"] or "",
            "pane_title": hard["pane_title"] or "",
            "pane_pid": "" if hard["pane_pid"] is None else str(hard["pane_pid"]),
            "pane_process": hard["pane_process"] or "",
            "process_match": hard["process_match"],
            "git_branch": git["branch"],
            "git_head": git["head"],
            "git_clean": git["clean"],
            "git_changed_count": git["changed_count"],
            "git_upstream": git["upstream"],
            "git_ahead": git["ahead"],
            "git_behind": git["behind"],
        }
    )
    if observation["platform"] == "grok":
        result["grok_tui"] = hard["tui_detected"]
    return result


# Ordinary receipts are bounded (progressive disclosure): capture through bound_text,
# observe/status through bound_observation; this limit equals ``capture_receipt_bytes``
# in templates/budgets.json. ``capture --full`` bypasses it by explicit request.
CAPTURE_RECEIPT_BYTES = 65536
TRUNCATION_MARKER = "[kaola capture truncated: kept last {kept} of {total} bytes; sha256 of the full capture {digest}; pass --full for the whole capture]\n"


def bound_text(data: bytes, limit: int = CAPTURE_RECEIPT_BYTES) -> bytes:
    """Keep the newest ``limit`` bytes of a capture (whole lines) plus one marker line.

    The marker names the total size and the sha256 of the untruncated stream so the
    truncated receipt stays verifiable; the result never exceeds ``limit`` bytes.
    """
    if len(data) <= limit:
        return data
    digest = hashlib.sha256(data).hexdigest()
    marker = TRUNCATION_MARKER.format(kept=0, total=len(data), digest=digest).encode("utf-8")
    keep = max(limit - len(marker) - 8, 0)
    tail = data[-keep:] if keep else b""
    newline = tail.find(b"\n")
    if 0 <= newline < len(tail) - 1:
        tail = tail[newline + 1:]
    marker = TRUNCATION_MARKER.format(kept=len(tail), total=len(data), digest=digest).encode("utf-8")
    return tail + marker


# The first entries of the process tree kept while the frame is trimmed.
PROCESS_EXCERPT = 32
OBSERVATION_BOUNDED_HINT = (
    "ordinary observe/status receipts are bounded: raw_current_frame keeps its newest whole "
    "lines and child_processes its first entries; snapshot_id and pane_revision were computed "
    "from the full frame; capture --full is the only unbounded request"
)


def _json_size(value: Any) -> int:
    return len(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8"))


def _tail_lines(data: bytes, keep: int) -> bytes:
    tail = data[-keep:] if keep > 0 else b""
    newline = tail.find(b"\n")
    if 0 <= newline < len(tail) - 1:
        tail = tail[newline + 1:]
    return tail


def bound_observation(observation: dict[str, Any], limit: int = CAPTURE_RECEIPT_BYTES) -> dict[str, Any]:
    """Keep an ordinary observe/status receipt within ``limit`` bytes, verifiably.

    Structural facts (identity, hard evidence, relay, counts, Git, model, flags) stay whole.
    When the JSON line would exceed the limit, ``child_processes`` is first cut to a short
    excerpt of its first entries, then ``raw_current_frame`` keeps its newest whole lines,
    and only if that is still not enough is the process excerpt dropped entirely, so the
    most relevant excerpt (the newest visible output) survives. ``truncated.fields``
    records, per bounded field, the kept and total sizes (or counts) and the sha256 of the
    full value, so the receipt stays verifiable. ``snapshot_id`` and ``pane_revision`` are
    computed before bounding, from the full frame, and are unchanged. A receipt already
    bounded once keeps its original totals and digests.
    """
    if _json_size(observation) <= limit:
        return observation
    bounded = dict(observation)
    previous = (observation.get("truncated") or {}).get("fields") or {}
    fields: dict[str, Any] = {}
    bounded["truncated"] = {"fields": fields, "hint": OBSERVATION_BOUNDED_HINT}
    processes = observation.get("child_processes")
    process_entry: dict[str, Any] | None = None
    if isinstance(processes, list) and processes:
        origin = previous.get("child_processes") or {}
        stream = "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in processes
        ).encode("utf-8")
        process_entry = {
            "kind": "list",
            "total": origin.get("total", len(processes)),
            "kept": len(processes),
            "stream_bytes": origin.get("stream_bytes", len(stream)),
            "stream_sha256": origin.get("stream_sha256", hashlib.sha256(stream).hexdigest()),
        }

    def trim_processes(floor: int) -> None:
        assert process_entry is not None
        kept = list(bounded["child_processes"])
        while _json_size(bounded) > limit and len(kept) > floor:
            kept = kept[:max(floor, len(kept) - max(1, len(kept) // 4))]
            bounded["child_processes"] = kept
            process_entry["kept"] = len(kept)
            fields["child_processes"] = process_entry

    if process_entry is not None:
        trim_processes(PROCESS_EXCERPT)
    frame = observation.get("raw_current_frame")
    if _json_size(bounded) > limit and isinstance(frame, str) and frame:
        data = frame.encode("utf-8")
        origin = previous.get("raw_current_frame") or {}
        entry: dict[str, Any] = {
            "kind": "text",
            "total_bytes": origin.get("total_bytes", len(data)),
            "sha256": origin.get("sha256", hashlib.sha256(data).hexdigest()),
            "kept_bytes": len(data),
        }
        fields["raw_current_frame"] = entry
        keep = len(data)
        while _json_size(bounded) > limit and keep > 0:
            keep = max(keep - max(_json_size(bounded) - limit, 512), 0)
            tail = _tail_lines(data, keep)
            keep = min(keep, len(tail))
            bounded["raw_current_frame"] = tail.decode("utf-8", errors="replace")
            entry["kept_bytes"] = len(tail)
    if process_entry is not None and _json_size(bounded) > limit:
        trim_processes(0)
    return bounded


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=(
            "bound-text",
            "build",
            "process-tree",
            "receipt",
            "claude-frame",
            "generic-frame",
            "opencode-frame",
            "kimi-frame",
            "cursor-frame",
            "status-view",
            "signal",
        ),
    )
    parser.add_argument("value", nargs="?")
    args = parser.parse_args()
    if args.command == "signal":
        if args.value is None or ":" not in args.value:
            raise ValueError("signal requires PID:stop or PID:cont")
        pid_text, action = args.value.split(":", 1)
        signum = {"stop": signal.SIGSTOP, "cont": signal.SIGCONT}.get(action)
        if signum is None:
            raise ValueError("unsupported signal action")
        os.kill(int(pid_text), signum)
    elif args.command == "process-tree":
        if args.value is None:
            raise ValueError("process-tree requires a root pid")
        rows = parse_process_table(sys.stdin.read())
        print(json.dumps(descendants(int(args.value), rows), separators=(",", ":")))
    elif args.command == "bound-text":
        limit = int(args.value) if args.value else CAPTURE_RECEIPT_BYTES
        sys.stdout.buffer.write(bound_text(sys.stdin.buffer.read(), limit))
        sys.stdout.buffer.flush()
    elif args.command == "build":
        print(json.dumps(bound_observation(build_from_environment()), ensure_ascii=False, sort_keys=True))
    elif args.command == "receipt":
        print(make_answer_receipt(json.load(sys.stdin)))
    elif args.command in {"claude-frame", "generic-frame", "opencode-frame", "kimi-frame", "cursor-frame"}:
        frame = sys.stdin.read()
        activity = args.value or "unknown"
        function = {
            "claude-frame": claude_frame_facts,
            "generic-frame": generic_frame_facts,
            "opencode-frame": opencode_frame_facts,
            "kimi-frame": kimi_frame_facts,
            "cursor-frame": cursor_frame_facts,
        }[args.command]
        pane_facts = json.loads(os.environ.get("KPR_ADAPTER_PANE_FACTS", "{}"))
        print(json.dumps(function(frame, activity, pane_facts), ensure_ascii=False, sort_keys=True))
    else:
        print(json.dumps(bound_observation(status_view(json.load(sys.stdin))), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"kaola-observation: {exc}", file=sys.stderr)
        raise SystemExit(2)
