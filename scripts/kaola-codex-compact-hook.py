#!/usr/bin/env python3
"""Merge-safe installer for the Project Runner Codex compact-recovery hook.

Issue #75: a Codex host that uses Project Runner (or Kaola-Delegator) reloads its
installed Skill after context compaction through Codex's verified
``SessionStart(source=compact)`` hook. This script installs, removes, and reports
exactly one Runner-owned entry in ``${CODEX_HOME}/hooks.json`` -- id
``kaola-project-runner:compact-context`` -- plus one payload copy at
``<codex_home>/kaola-project-runner/hooks/compact-recovery.md``.

Merge safety is the contract: the entry is matched by id only and foreign
entries (Workflow-owned, user-owned, or plugin-era leftovers) keep their JSON
content untouched. The document is re-serialized canonically on write, so
byte-level formatting is not preserved and none is claimed; uninstall removes
only our entry and our payload copy. The hook itself performs no dispatch and
edits no project state; it prints the short recovery prompt that becomes the
model's ``additionalContext``.

Every action prints one bounded JSON receipt; ``result`` is ``ok`` or
``refused`` with reasons. A malformed existing ``hooks.json`` is refused rather
than clobbered. Before rewriting an existing ``hooks.json`` the prior content
is kept once as ``hooks.json.kaola-backup-<sha12>`` (content-addressed, so
repeated installs do not accumulate backups; the backup is written atomically
at mode 0600 since it mirrors config content). The hook command quotes the
payload path with ``shlex.quote`` so a ``CODEX_HOME`` containing shell
metacharacters cannot alter what the hook executes. Nothing here reads,
prints, or forwards a credential, and ``status`` never writes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import sys
import tempfile
from pathlib import Path

ENTRY_ID = "kaola-project-runner:compact-context"
PAYLOAD_REL = Path("kaola-project-runner") / "hooks" / "compact-recovery.md"
PAYLOAD_SOURCE = (
    Path(__file__).resolve().parents[1]
    / "templates"
    / "codex-host"
    / "compact-recovery.md"
)
RECEIPT_LIMIT = 4096


def codex_home(raw: str | None) -> Path:
    if raw:
        return Path(raw).expanduser()
    env = os.environ.get("CODEX_HOME")
    if env:
        return Path(env).expanduser()
    return Path.home() / ".codex"


def hook_entry(payload_path: Path) -> dict:
    return {
        "matcher": "compact",
        "hooks": [
            {
                "type": "command",
                "command": f"cat {shlex.quote(str(payload_path))}",
                "timeout": 5,
            }
        ],
        "description": (
            "Inject the Project Runner compact-recovery prompt after context "
            "compaction"
        ),
        "id": ENTRY_ID,
    }


def load_hooks(path: Path) -> dict:
    """Parse hooks.json or refuse; an absent file means an empty document."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{path}: unreadable or invalid JSON ({exc})") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path}: top-level JSON is not an object")
    hooks = data.get("hooks")
    if hooks is not None and not isinstance(hooks, dict):
        raise ValueError(f"{path}: 'hooks' is not an object")
    session = (hooks or {}).get("SessionStart")
    if session is not None and not isinstance(session, list):
        raise ValueError(f"{path}: 'hooks.SessionStart' is not a list")
    return data


def atomic_write(path: Path, content: bytes, mode: int | None = None) -> None:
    handle, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=str(path.parent)
    )
    try:
        with os.fdopen(handle, "wb") as temp:
            temp.write(content)
        os.chmod(temp_name, mode if mode is not None else 0o600)
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def write_backup(hooks_path: Path) -> None:
    """Keep one content-addressed 0600 backup of the prior hooks.json."""
    digest = hashlib.sha256(hooks_path.read_bytes()).hexdigest()[:12]
    backup = hooks_path.with_name(f"{hooks_path.name}.kaola-backup-{digest}")
    if not backup.exists():
        atomic_write(backup, hooks_path.read_bytes())


def receipt(action: str, result: str, **fields) -> None:
    out = {"schema": "kaola-codex-compact-hook/1", "action": action, "result": result}
    out.update(fields)
    line = json.dumps(out, sort_keys=True)
    sys.stdout.write(line[:RECEIPT_LIMIT] + "\n")


def payload_path_for(home: Path) -> Path:
    return home / PAYLOAD_REL


def cmd_install(home: Path) -> int:
    if not PAYLOAD_SOURCE.is_file():
        receipt("install", "refused", reasons=[f"missing payload source: {PAYLOAD_SOURCE}"])
        return 1
    payload_path = payload_path_for(home)
    hooks_path = home / "hooks.json"
    try:
        data = load_hooks(hooks_path)
    except ValueError as exc:
        receipt("install", "refused", reasons=[str(exc)])
        return 1

    payload_path.parent.mkdir(parents=True, exist_ok=True)
    payload_bytes = PAYLOAD_SOURCE.read_bytes()
    payload_changed = not payload_path.exists() or payload_path.read_bytes() != payload_bytes
    if payload_changed:
        atomic_write(payload_path, payload_bytes)

    hooks = data.setdefault("hooks", {})
    session = hooks.setdefault("SessionStart", [])
    foreign = [e for e in session if not (isinstance(e, dict) and e.get("id") == ENTRY_ID)]
    entry = hook_entry(payload_path)
    merged = foreign + [entry]
    changed = session != merged
    if changed:
        session[:] = merged
        if hooks_path.exists():
            write_backup(hooks_path)
        existing_mode = hooks_path.stat().st_mode & 0o777 if hooks_path.exists() else None
        atomic_write(
            hooks_path,
            (json.dumps(data, indent=2) + "\n").encode("utf-8"),
            mode=existing_mode,
        )
    receipt(
        "install",
        "ok",
        changed=changed or payload_changed,
        hooks_json=str(hooks_path),
        payload=str(payload_path),
        entry_id=ENTRY_ID,
        foreign_session_start=len(foreign),
    )
    return 0


def cmd_uninstall(home: Path) -> int:
    payload_path = payload_path_for(home)
    hooks_path = home / "hooks.json"
    try:
        data = load_hooks(hooks_path)
    except ValueError as exc:
        receipt("uninstall", "refused", reasons=[str(exc)])
        return 1

    removed = 0
    hooks = data.get("hooks") or {}
    session = hooks.get("SessionStart")
    if isinstance(session, list):
        kept = [
            e
            for e in session
            if not (isinstance(e, dict) and e.get("id") == ENTRY_ID)
        ]
        removed = len(session) - len(kept)
        if removed:
            session[:] = kept
            write_backup(hooks_path)
            atomic_write(
                hooks_path,
                (json.dumps(data, indent=2) + "\n").encode("utf-8"),
                mode=hooks_path.stat().st_mode & 0o777,
            )
    payload_removed = False
    if payload_path.is_file():
        payload_path.unlink()
        payload_removed = True
        for parent in (payload_path.parent, payload_path.parent.parent):
            try:
                parent.rmdir()
            except OSError:
                break
    receipt(
        "uninstall",
        "ok",
        changed=bool(removed or payload_removed),
        removed_entries=removed,
        payload_removed=payload_removed,
        hooks_json=str(hooks_path),
    )
    return 0


def cmd_status(home: Path) -> int:
    hooks_path = home / "hooks.json"
    try:
        data = load_hooks(hooks_path)
    except ValueError as exc:
        receipt("status", "refused", reasons=[str(exc)])
        return 1
    hooks = data.get("hooks") or {}
    session = hooks.get("SessionStart")
    ours = [
        e
        for e in (session if isinstance(session, list) else [])
        if isinstance(e, dict) and e.get("id") == ENTRY_ID
    ]
    receipt(
        "status",
        "ok",
        installed=bool(ours),
        entry=ours[0] if ours else None,
        hooks_json=str(hooks_path),
        hooks_json_exists=hooks_path.exists(),
        session_start_entries=len(session) if isinstance(session, list) else 0,
        payload=str(payload_path_for(home)),
        payload_present=payload_path_for(home).is_file(),
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Install, remove, or report the Project Runner Codex "
            "SessionStart(compact) recovery entry. Only the "
            f"{ENTRY_ID!r} entry is ever added or removed; foreign hooks are "
            "never modified."
        )
    )
    parser.add_argument(
        "action", choices=("install", "uninstall", "status")
    )
    parser.add_argument(
        "--codex-home",
        default=None,
        help="Codex home directory (default: $CODEX_HOME or ~/.codex)",
    )
    args = parser.parse_args(argv)
    home = codex_home(args.codex_home)
    if args.action == "install":
        return cmd_install(home)
    if args.action == "uninstall":
        return cmd_uninstall(home)
    return cmd_status(home)


if __name__ == "__main__":
    sys.exit(main())
