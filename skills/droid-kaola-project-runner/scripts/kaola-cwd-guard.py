#!/usr/bin/env python3
"""Issue #369: the shared cwd guard for worktree removals.

One hyphenated module, loaded the way ``kaola-acp-sweep.py`` loads
``kaola-acp.py``, used by the holder, ``kaola-dispatch.py sweep`` and the
``worktree-remove`` / ``worktree-guard`` wrapper.

``occupants(repo, target, trees)`` answers whether any live process cwd, or any
recorded tool cwd, lies inside the worktree ``target``. It never reads or
copies a command line: an occupant names the argv[0] basename only.

A probe that cannot answer reports ``unverifiable``. Issue #389 callers treat
``occupied`` and ``unverifiable`` as recoverable and proceed with a typed
warning; only a live process cwd plus uncommitted changes is a hard block.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

PS_TIMEOUT = 10.0
PROBE_TIMEOUT = 20.0


def _path_value(value: Any) -> Path | None:
    if isinstance(value, Path):
        return value
    if isinstance(value, str) and value:
        return Path(value)
    return None


def same_path(left: Any, right: Any) -> bool:
    """Two path spellings naming one directory."""
    first, second = _path_value(left), _path_value(right)
    if first is None or second is None:
        return False
    try:
        return first.resolve() == second.resolve()
    except OSError:
        return os.path.normpath(str(first)) == os.path.normpath(str(second))


def within(root: Any, candidate: Any) -> bool:
    """``candidate`` is ``root`` itself or below it."""
    path, base = _path_value(candidate), _path_value(root)
    if path is None or base is None or not path.is_absolute():
        return False
    try:
        resolved = path.resolve()
        resolved_base = base.resolve()
        return resolved == resolved_base or resolved_base in resolved.parents
    except OSError:
        return False


def process_table() -> dict[int, dict[str, Any]] | None:
    """One ``ps`` read: pid -> ``{ppid, pgid, uid, exe_basename}``.

    ``None`` when ps cannot answer. ``exe_basename`` is the executable name
    only; no command line is read.
    """
    try:
        run = subprocess.run(["ps", "-axo", "pid=,ppid=,pgid=,uid=,comm="],
                             capture_output=True, text=True, timeout=PS_TIMEOUT)
    except (OSError, subprocess.SubprocessError):
        return None
    if run.returncode != 0:
        return None
    table: dict[int, dict[str, Any]] = {}
    for line in run.stdout.splitlines():
        fields = line.strip().split(None, 4)
        if len(fields) != 5 or not all(field.lstrip("-").isdigit() for field in fields[:4]):
            continue
        table[int(fields[0])] = {
            "ppid": int(fields[1]),
            "pgid": int(fields[2]),
            "uid": int(fields[3]),
            "exe_basename": os.path.basename(fields[4].strip()),
        }
    return table or None


def expand(table: dict[int, dict[str, Any]] | None, roots: list[Any]) -> list[int]:
    """The roots plus every descendant of theirs in one process table."""
    seeds = [pid for pid in roots
             if isinstance(pid, int) and not isinstance(pid, bool) and pid > 0]
    if not table:
        return sorted(set(seeds))
    children: dict[int, list[int]] = {}
    for pid, fact in table.items():
        children.setdefault(fact["ppid"], []).append(pid)
    seen: set[int] = set()
    stack = [pid for pid in seeds if pid in table]
    while stack:
        pid = stack.pop()
        if pid in seen:
            continue
        seen.add(pid)
        stack.extend(children.get(pid, []))
    return sorted(seen)


def read_cwds(pids: list[int]) -> tuple[str, dict[int, dict[str, Any]], bool]:
    """``(probe, pid -> {cwd, cwd_deleted}, unverifiable)``.

    Linux reads ``/proc/<pid>/cwd``; elsewhere one ``lsof -a -d cwd`` call for
    the whole pid list. A live pid the probe does not answer for makes the
    answer unverifiable rather than clear.
    """
    if not pids:
        return ("none", {}, False)
    proc = Path("/proc")
    if proc.is_dir():
        found: dict[int, dict[str, Any]] = {}
        unreadable = False
        for pid in pids:
            try:
                raw = os.readlink(str(proc / str(pid) / "cwd"))
            except FileNotFoundError:
                continue
            except OSError:
                unreadable = True
                continue
            deleted = raw.endswith(" (deleted)")
            found[pid] = {"cwd": raw[: -len(" (deleted)")] if deleted else raw,
                          "cwd_deleted": deleted}
        return ("proc", found, unreadable)
    try:
        run = subprocess.run(["lsof", "-a", "-d", "cwd", "-Fpn", "-p",
                              ",".join(str(pid) for pid in pids)],
                             capture_output=True, text=True, timeout=PROBE_TIMEOUT)
    except (OSError, subprocess.SubprocessError):
        return ("lsof", {}, True)
    found = {}
    current: int | None = None
    for line in run.stdout.splitlines():
        if line.startswith("p") and line[1:].isdigit():
            current = int(line[1:])
        elif line.startswith("n") and current is not None:
            found[current] = {"cwd": line[1:], "cwd_deleted": False}
    missing = [pid for pid in pids if pid not in found]
    if missing:
        # A pid that exited between ps and lsof is not an unreadable probe.
        table = process_table() or {}
        missing = [pid for pid in missing if pid in table]
    return ("lsof", found, bool(missing))


def trees_from_rows(rows: list[dict[str, Any]], repo: Any, target: Any,
                    table: dict[int, dict[str, Any]] | None) -> list[dict[str, Any]]:
    """One tree per verified session row rooted at ``repo`` or at ``target``.

    A row's own recorded tool cwd rides along even when no process holds it:
    that string is the case the incident is in.
    """
    trees: list[dict[str, Any]] = []
    for row in rows or []:
        if not isinstance(row, dict) or row.get("identity") != "verified":
            continue
        seen = row.get("repo")
        if not isinstance(seen, str) or not seen:
            continue
        if not (same_path(seen, repo) or same_path(seen, target)):
            continue
        session = {
            "platform": row.get("platform"),
            "session": row.get("session"),
            "role": row.get("session_role"),
            "holder_instance_id": row.get("holder_instance_id"),
        }
        roots: list[Any] = [row.get("holder_pid"), row.get("agent_pid")]
        groups = set()
        for key in ("agent_pgid",):
            value = row.get(key)
            if isinstance(value, int) and not isinstance(value, bool) and value > 0:
                groups.add(value)
        for value in row.get("agent_child_pgids") or []:
            if isinstance(value, int) and not isinstance(value, bool) and value > 0:
                groups.add(value)
        if table and groups:
            roots.extend(pid for pid, fact in table.items() if fact["pgid"] in groups)
        recorded = row.get("tool_cwd_path")
        trees.append({
            "pids": expand(table, roots),
            "session": session,
            "recorded_cwd": recorded if isinstance(recorded, str) and recorded else None,
        })
    return trees


def _session_of(pid: int, owners: dict[int, dict[str, Any]]) -> dict[str, Any] | None:
    session = owners.get(pid)
    return dict(session) if isinstance(session, dict) else None


def occupants(repo: Any, target: Any, trees: list[dict[str, Any]] | None = None,
              *, all_user_processes: bool = False) -> dict[str, Any]:
    """``{"result", "occupants", "probe"}`` for one target directory.

    ``occupied`` means a live process cwd or a recorded tool cwd is inside
    ``target``. ``unverifiable`` means the probe could not answer. Both are
    recoverable findings under Issue #389; the wrapper decides the action.
    """
    table = process_table()
    if table is None:
        return {"result": "unverifiable", "occupants": [], "probe": "none"}
    owners: dict[int, dict[str, Any]] = {}
    roots: list[Any] = []
    for tree in trees or []:
        pids = expand(table, list(tree.get("pids") or []))
        session = tree.get("session")
        for pid in pids:
            roots.append(pid)
            if isinstance(session, dict):
                owners.setdefault(pid, session)
    if all_user_processes:
        uid = os.getuid()
        roots.extend(pid for pid, fact in table.items() if fact["uid"] == uid)
    pids = sorted(set(expand(table, roots)) | {os.getpid()})
    probe, cwds, unreadable = read_cwds(pids)
    found: list[dict[str, Any]] = []
    for pid, fact in cwds.items():
        cwd = fact["cwd"]
        # A deleted cwd keeps its old path spelling on both probes, so the
        # same match rule names it: the path is what dangles.
        if not within(target, cwd):
            continue
        info = table.get(pid, {})
        found.append({
            "pid": pid,
            "ppid": info.get("ppid"),
            "exe_basename": info.get("exe_basename"),
            "cwd": cwd,
            "cwd_deleted": bool(fact["cwd_deleted"]),
            "source": "process",
            "session": _session_of(pid, owners),
        })
    for tree in trees or []:
        recorded = tree.get("recorded_cwd")
        if isinstance(recorded, str) and recorded and within(target, recorded):
            found.append({
                "pid": None,
                "ppid": None,
                "exe_basename": None,
                "cwd": recorded,
                "cwd_deleted": not os.path.isdir(recorded),
                "source": "recorded",
                "session": dict(tree["session"]) if isinstance(tree.get("session"), dict) else None,
            })
    if found:
        return {"result": "occupied", "occupants": found, "probe": probe}
    if unreadable:
        return {"result": "unverifiable", "occupants": [], "probe": probe}
    return {"result": "clear", "occupants": [], "probe": probe}
