#!/usr/bin/env python3
"""Issue #63: exact sweep of one invocation's ACP holder processes.

``scripts/validate.sh`` runs its suites under a validate-owned ``TMPDIR``
root, so every holder those suites spawn carries a ``--record-dir`` and a
``--socket`` under that root. A normal suite teardown already stops each
holder through the admin-socket ``stop`` op, which sweeps the agent process
group and the noted child groups; an interrupted or early-exited run
(``set -e``, SIGINT, SIGTERM) skips that teardown, and the holders — spawned
with ``start_new_session`` — survive re-parented to launchd.

This sweep stops exactly the holders whose ``--record-dir`` or ``--socket``
lies under the given root, using the same admin-socket ``stop`` (force) op
a normal teardown uses. Any residue of this root's holders — a wedged
holder that survives its stop, or a member of an agent group the holder
recorded — is swept with the ``kaola-acp.py stop --force`` machinery:
identity-checked groups through ``recorded_groups``, members through
``live_group_members``, SIGKILL per member. Nothing outside the root is
ever matched or signaled: foreign and concurrent runs hold their own fresh
random roots, and every signaled pid is first matched by its root-scoped
argv. Output is one JSON receipt line; the exit status is nonzero only when
residue remains.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent

# The admin-socket stop op escalates SIGTERM -> SIGKILL inside the agent
# group and sweeps child groups before replying, so one request can take
# TERM_GRACE + EXIT_GRACE + TERM_GRACE seconds; the exit waits are the
# outer bounds for a wedged holder.
STOP_TIMEOUT = 25.0
EXIT_WAIT = 12.0
KILL_WAIT = 5.0


def _load_cli() -> Any:
    """Import ``kaola-acp.py`` (hyphenated module name) to reuse its exact
    stop machinery: the admin-socket protocol, record reads, identity-checked
    group resolution, and group-member resolution."""
    spec = importlib.util.spec_from_file_location("kaola_acp", SCRIPT_DIR / "kaola-acp.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


KAOLA_ACP = _load_cli()


def process_table() -> tuple[dict[int, str], dict[int, str]]:
    """``pid -> state`` and ``pid -> command`` from the same ps source
    kaola-acp.py trusts; a zombie counts as gone for this sweep."""
    table = subprocess.run(["ps", "-axo", "pid=,state=,command="], capture_output=True, text=True)
    states: dict[int, str] = {}
    commands: dict[int, str] = {}
    for line in table.stdout.splitlines():
        fields = line.strip().split(None, 2)
        if len(fields) == 3 and fields[0].isdigit():
            states[int(fields[0])] = fields[1].upper()
            commands[int(fields[0])] = fields[2].strip()
    return states, commands


def flag_value(tokens: list[str], flag: str) -> str | None:
    for index in range(len(tokens) - 1):
        if tokens[index] == flag:
            return tokens[index + 1]
    return None


def matched_holders(root: Path) -> list[dict[str, Any]]:
    """Live holder processes whose ``--record-dir`` or ``--socket`` value lies
    under ``root`` (as given or realpath; macOS canonicalizes /tmp prefixes).
    The root is a fresh random directory owned by one invocation, so no
    foreign or concurrent run can ever match."""
    roots = {str(root), str(root.resolve())}
    states, commands = process_table()
    holders: list[dict[str, Any]] = []
    for pid, command in commands.items():
        if states.get(pid, "").startswith("Z") or "kaola-acp-holder.py" not in command:
            continue
        tokens = command.split()
        record_dir = flag_value(tokens, "--record-dir")
        sock = flag_value(tokens, "--socket")
        values = [value for value in (record_dir, sock) if value]
        if not any(
            value == base or value.startswith(base + os.sep)
            for value in values
            for base in roots
        ):
            continue
        holders.append({"pid": pid, "record_dir": record_dir, "socket": sock})
    return holders


def process_gone(pid: int) -> bool:
    """Zombie-safe liveness: an exited-but-unreaped holder is gone for this
    sweep's purposes (its stop already ran; its parent reaps it)."""
    states, _ = process_table()
    return pid not in states or states[pid].startswith("Z")


def wait_for_exit(pid: int, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process_gone(pid):
            return True
        time.sleep(0.05)
    return process_gone(pid)


def recorded_agent_groups(entry: dict[str, Any]) -> list[int]:
    """The holder's agent pgid plus its identity-checked child groups, from
    the record directory under the swept root; empty when no record
    survives (the ``stop --force`` group resolution, unchanged)."""
    record_dir = entry.get("record_dir")
    if not record_dir:
        return []
    directory = Path(record_dir)
    return KAOLA_ACP.recorded_groups(KAOLA_ACP.read_record(directory) or {}, directory)


def kill_group_members(groups: list[int]) -> list[int]:
    killed: list[int] = []
    for member in KAOLA_ACP.live_group_members(groups):
        try:
            os.kill(member, signal.SIGKILL)
            killed.append(member)
        except (ProcessLookupError, PermissionError):
            pass
    return killed


def stop_holder(entry: dict[str, Any]) -> dict[str, Any]:
    """Stop one matched holder. The admin-socket ``stop`` (force) op is the
    normal teardown path: the holder itself sweeps its agent group and child
    groups before exiting. Only when that op cannot run or the holder
    survives it is the holder SIGKILLed; agent-group residue of either path
    is swept once afterwards from the recorded groups."""
    pid = entry["pid"]
    result: dict[str, Any] = {
        "pid": pid,
        "via": "socket",
        "stop_error": None,
        "force_killed": False,
        "stop_residual_pids": [],
        "holder_alive": False,
    }
    sock = entry.get("socket")
    stopped = False
    if sock:
        receipt = KAOLA_ACP.socket_request(Path(sock), "stop", {"force": True}, STOP_TIMEOUT)
        if "error" not in receipt:
            result["stop_residual_pids"] = list(receipt.get("residual_pids") or [])
            stopped = wait_for_exit(pid, EXIT_WAIT)
        else:
            result["stop_error"] = receipt["error"]
    if not stopped:
        result["via"] = "kill"
        result["force_killed"] = True
        try:
            os.kill(pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        stopped = wait_for_exit(pid, KILL_WAIT)
    result["holder_alive"] = not stopped
    return result


def sweep(root: Path) -> dict[str, Any]:
    """Stop every holder matched under ``root`` and verify no residue of
    this root's recorded groups survives; nothing else is ever touched."""
    holders = matched_holders(root)
    results = [stop_holder(entry) for entry in holders]
    # One residue pass over each holder's identity-checked groups — the same
    # verification and escalation ``stop --force`` receipts carry — so a
    # wedged or socketless stop cannot leave an agent group member behind.
    groups = sorted({group for entry in holders for group in recorded_agent_groups(entry)})
    final_killed = kill_group_members(groups)
    leftover: list[int] = []
    if groups:
        time.sleep(0.1)
        leftover = KAOLA_ACP.live_group_members(groups)
    residual: set[int] = set(leftover)
    for result in results:
        if result["holder_alive"]:
            residual.add(result["pid"])
        residual.update(
            pid for pid in result["stop_residual_pids"] if not process_gone(pid)
        )
    return {
        "root": str(root),
        "matched_pids": sorted(entry["pid"] for entry in holders),
        "results": results,
        "swept_groups": groups,
        "killed_group_members": final_killed,
        "residual_pids": sorted(residual),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--root", required=True,
        help="the invocation-owned temp root; only holders whose --record-dir "
             "or --socket lies under it are stopped",
    )
    args = parser.parse_args()
    receipt = sweep(Path(args.root))
    print(json.dumps(receipt, sort_keys=True))
    return 1 if receipt["residual_pids"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
