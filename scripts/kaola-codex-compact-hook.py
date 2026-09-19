#!/usr/bin/env python3
"""Merge-safe installer for the Project Runner Codex compact-recovery hook.

Issue #75: a Codex host that uses Project Runner (or Kaola-Delegator) reloads
its installed Skill after context compaction through Codex's verified
``SessionStart(source=compact)`` hook. This script installs, removes, and
reports exactly one Runner-owned entry in the CONSUMING project's
``<project_root>/.codex/hooks.json`` -- id
``kaola-project-runner:compact-context`` -- plus private asset copies under
``<project_root>/.codex/kaola-project-runner/hooks/`` (payload, emitter,
binding).

Why the project layer: Codex officially supports project-level hooks in
``<repo>/.codex/hooks.json`` (loaded only while the directory is trusted and
subject to the ``/hooks`` review flow; ``--dangerously-bypass-hook-trust``
runs enabled hooks without review). A single user-global ``hooks.json``
cannot hold two projects' bindings -- installing project B would overwrite
project A's designated-Host binding, and uninstalling B would strip A. The
project layer keeps each binding inside the repository it describes, so any
number of bound Hosts coexist and removal stays strictly local. The project
actions never write to ``${CODEX_HOME}`` or ``~/.codex``.

User layer (Issue #97): an outer Codex Agent that uses the installed
``kaola-delegator`` may delegate several projects from any repository, so a
per-project hook cannot cover it. ``user-install`` writes ONE Runner-owned
entry -- id ``kaola-project-runner:user-compact-context`` -- into the
official user-level ``${CODEX_HOME:-~/.codex}/hooks.json`` plus private
asset copies under ``<CODEX_HOME>/kaola-project-runner/hooks/`` (payload
``compact-recovery-user.md`` and the emitter copy). Its command runs
``user-emit``, which prints the short CONDITIONAL payload on every
``SessionStart(compact)``: the text itself tells a session that was already
using ``kaola-delegator`` or ``kaola-project-runner`` to re-read that
installed Skill and continue from existing records, and tells every other
session to do nothing. No session filter, binding table, session registry,
cwd-based role guess, or heartbeat exists at the user layer. The one
suppression is coexistence with a legacy project-level entry: when the
session's ``cwd`` holds a Runner project entry whose ``binding.json`` names
this exact ``session_id`` and canonical root -- precisely the predicate the
project ``emit`` fires on -- ``user-emit`` stays silent so one compaction
never injects two Runner blocks. ``user-uninstall`` and ``user-status``
touch or report only that entry and those copies; the Kaola Workflow user
hook and any user-owned entry are preserved and never echoed or copied.
``user-install`` is idempotent, and it does not change the host's trust
review: Codex marks a new or changed non-managed hook for review in
``/hooks`` and loads hooks at session start, so nothing here promises silent
activation. ``--runtime codex`` (or the legacy Codex default) is the only
installer path that reaches this layer; ``--skills-dir`` never does.

Host-only filter: the hook command runs a copy of this script (``emit``)
that reads ``binding.json`` plus the official hook input on stdin --
``session_id``, ``cwd``, ``hook_event_name``, ``source`` -- and prints the
payload ONLY when the event is ``SessionStart(compact)`` AND the session id
and (realpath-normalized) cwd match the binding. An ordinary Worker session,
a session in another repository, a non-compact source, or an untrusted /
unmatched context emits nothing; the entry alone is never sufficient.

Two-phase bootstrap (first-session coverage): hooks load at session start,
so a binding that can only be written after the Host exists must not gate
entry installation. ``prepare`` writes the assets and the hook entry with an
inert ``binding.json`` (``session_id: null`` -- emit always silent) BEFORE
the Host is launched; ``bind`` then writes ONLY ``binding.json`` with the
exact designated session id after the Host starts, leaving the already
loaded/reviewed entry untouched. ``install`` remains the one-shot form
(prepare + bind) for a session id that is already known. Inside the Codex
host's own shell, ``CODEX_SESSION_ID``/``CODEX_THREAD_ID`` carry the session
identity that equals the hook input's ``session_id`` -- verified live. The
session id is bound only by explicit operator choice; nothing auto-claims
the first session and ordinary Workers are never bound.

Merge safety is the contract: the entry is matched by id only and foreign
entries (Workflow-owned, user-owned, or plugin-era leftovers) keep their
JSON content untouched. The document is re-serialized canonically on write,
so byte-level formatting is not preserved and none is claimed; uninstall
removes only our entry and our copies (a hooks.json that held nothing else
is removed, and ``.codex`` is left only while other content remains). The
hook itself performs no dispatch and edits no project state; it prints the
short recovery prompt that becomes the model's ``additionalContext``.

Binding safety: ``prepare`` is deliberately re-runnable but never silently
unbinds -- a ``binding.json`` is preserved byte-for-byte only when it holds
a non-empty ``session_id`` AND this project's canonical ``project_root``
(the exact pair ``emit`` matches on); an id without the matching root, an
empty/whitespace id, or any other unclassifiable shape is refused before
any write. ``install``/``bind`` with an explicit ``--session-id`` always
overwrite the binding by operator choice.

Every action prints one bounded JSON receipt; ``result`` is ``ok`` or
``refused`` with reasons. A malformed existing ``hooks.json`` -- including
JSON-null ``hooks`` or ``hooks.SessionStart`` -- is refused before any write
rather than clobbered or crashed on. No backup copies of the configuration
are ever made: foreign content (which may carry credentials) stays only in
the file it already lived in. The hook command quotes every path with
``shlex.quote`` so a project root containing shell metacharacters cannot
alter what the hook executes. ``--project-root`` must name an existing
directory and explicit global/ancestor danger paths are refused -- the
filesystem root, the user home directory, and the effective CODEX_HOME
layer (so a mistaken ``$HOME`` can never write ``~/.codex/hooks.json``).
Before any read, write, or delete, the real paths of ``.codex`` and the
Runner-owned asset parents are resolved; a symlink that escapes the
canonical project root is refused (a project-local ``.codex`` symlink
remains legal). ``install``/``bind`` refuse a missing or blank
``--session-id``, and ``status`` reports only safe metadata -- it never
echoes a matched entry's command or arbitrary config, which could carry a
credential. Reading the existing ``hooks.json`` -- which may hold a
credential-bearing foreign command -- is required to merge; the boundary
is that nothing prints, copies, or forwards foreign content, and
``status`` never writes.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import sys
import tempfile
from pathlib import Path

ENTRY_ID = "kaola-project-runner:compact-context"
USER_ENTRY_ID = "kaola-project-runner:user-compact-context"
ASSETS_REL = Path(".codex") / "kaola-project-runner" / "hooks"
USER_ASSETS_REL = Path("kaola-project-runner") / "hooks"
PAYLOAD_SOURCE = (
    Path(__file__).resolve().parents[1]
    / "templates"
    / "codex-host"
    / "compact-recovery.md"
)
USER_PAYLOAD_SOURCE = PAYLOAD_SOURCE.with_name("compact-recovery-user.md")
PROJECT_ACTIONS = ("prepare", "install", "bind", "uninstall", "status")
USER_ACTIONS = ("user-install", "user-uninstall", "user-status")
RECEIPT_LIMIT = 4096


def resolve_root(raw: str | None) -> tuple[Path | None, str | None]:
    """Canonicalize --project-root, or return a refusal reason.

    The directory must exist, and explicit global/ancestor danger paths are
    refused: the filesystem root, the user home directory, and the effective
    CODEX_HOME layer (the directory itself or the parent whose ``.codex`` IS
    that layer). Pointing at ``$HOME`` would otherwise write
    ``~/.codex/hooks.json`` — user-global config this tool must never touch.
    """
    if not raw:
        return None, "missing --project-root"
    root = Path(raw).expanduser()
    if not root.is_dir():
        return None, f"--project-root is not a directory: {root}"
    root = Path(os.path.realpath(root))
    dangers = []
    if root == Path(root.anchor):
        dangers.append("the filesystem root")
    home = Path(os.path.realpath(Path.home()))
    if root == home:
        dangers.append("the user home directory")
    codex_env = os.environ.get("CODEX_HOME")
    codex_home = Path(
        os.path.realpath(
            Path(codex_env).expanduser() if codex_env else home / ".codex"
        )
    )
    if root == codex_home or root / ".codex" == codex_home:
        dangers.append("the effective CODEX_HOME layer")
    if dangers:
        return None, (
            "--project-root resolves to " + " and ".join(dangers) + f": {root}"
        )
    return root, None


def hooks_path_for(root: Path) -> Path:
    return root / ".codex" / "hooks.json"


def assets_dir_for(root: Path) -> Path:
    return root / ASSETS_REL


def containment_reason(root: Path) -> str | None:
    """Refuse when a managed path would escape the canonical project root.

    ``os.path.realpath`` resolves every symlink component, so a ``.codex``
    symlinked to the effective CODEX_HOME (or anywhere outside the project)
    is caught before any read, write, or delete -- otherwise prepare would
    append to the user-global hooks.json and uninstall could delete global
    assets. The owned leaves are checked too: writes are atomic-replace,
    but ``read_bytes``/``read_text`` follow a symlink, so a leaf pointing
    outside the project would read foreign content. A symlink that stays
    inside the project remains legal.
    """
    for path in (
        hooks_path_for(root),
        assets_dir_for(root),
        payload_path_for(root),
        emitter_path_for(root),
        binding_path_for(root),
    ):
        real = Path(os.path.realpath(path))
        if real != root and root not in real.parents:
            return f"{path}: resolves outside --project-root ({real})"
    return None


def payload_path_for(root: Path) -> Path:
    return root / ASSETS_REL / "compact-recovery.md"


def emitter_path_for(root: Path) -> Path:
    return payload_path_for(root).with_name("kaola-codex-compact-hook.py")


def binding_path_for(root: Path) -> Path:
    return payload_path_for(root).with_name("binding.json")


def hook_entry(emitter: Path) -> dict:
    command = f"python3 {shlex.quote(str(emitter))} emit"
    return {
        "matcher": "compact",
        "hooks": [
            {
                "type": "command",
                "command": command,
                "timeout": 5,
            }
        ],
        "description": (
            "Inject the Project Runner compact-recovery prompt after context "
            "compaction (bound Host session only)"
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
    if "hooks" in data and not isinstance(data["hooks"], dict):
        raise ValueError(f"{path}: 'hooks' is not an object")
    hooks = data.get("hooks") or {}
    if "SessionStart" in hooks and not isinstance(hooks["SessionStart"], list):
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


def receipt(action: str, result: str, **fields) -> None:
    out = {"schema": "kaola-codex-compact-hook/1", "action": action, "result": result}
    out.update(fields)
    line = json.dumps(out, sort_keys=True)
    sys.stdout.write(line[:RECEIPT_LIMIT] + "\n")


def write_hooks(hooks_path: Path, data: dict) -> None:
    existing_mode = hooks_path.stat().st_mode & 0o777 if hooks_path.exists() else None
    atomic_write(
        hooks_path,
        (json.dumps(data, indent=2) + "\n").encode("utf-8"),
        mode=existing_mode,
    )


def write_binding(root: Path, session_id: str | None) -> bool:
    """Write binding.json (inert when session_id is None); return changed."""
    binding_path = binding_path_for(root)
    binding_bytes = (
        json.dumps(
            {"session_id": session_id, "project_root": str(root)},
            indent=2,
        )
        + "\n"
    ).encode("utf-8")
    changed = (
        not binding_path.exists() or binding_path.read_bytes() != binding_bytes
    )
    if changed:
        atomic_write(binding_path, binding_bytes)
    return changed


def read_binding(binding_path: Path) -> dict | None:
    """Return the existing binding dict, or None when absent."""
    if not binding_path.exists():
        return None
    try:
        data = json.loads(binding_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{binding_path}: unreadable or invalid JSON ({exc})") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{binding_path}: top-level JSON is not an object")
    return data


def _install(root: Path, session_id: str | None, action: str) -> int:
    """Write assets, binding, and the entry; session_id None means inert."""
    if not PAYLOAD_SOURCE.is_file():
        receipt(action, "refused", reasons=[f"missing payload source: {PAYLOAD_SOURCE}"])
        return 1
    payload_path = payload_path_for(root)
    emitter = emitter_path_for(root)
    hooks_path = hooks_path_for(root)
    binding_path = binding_path_for(root)
    try:
        data = load_hooks(hooks_path)
    except ValueError as exc:
        receipt(action, "refused", reasons=[str(exc)])
        return 1

    # prepare (inert install) must never silently unbind a live Host: a
    # current binding that is already bound is preserved byte-for-byte; a
    # binding we cannot classify is refused before any write.
    preserve_binding = False
    bound_session: str | None = None
    if session_id is None and binding_path.exists():
        try:
            existing = read_binding(binding_path)
        except ValueError as exc:
            receipt(action, "refused", reasons=[str(exc)])
            return 1
        existing_id = existing.get("session_id") if existing else None
        existing_root = existing.get("project_root") if existing else None
        bound = isinstance(existing_id, str) and bool(existing_id.strip())
        if bound:
            # A preserved binding must be verifiably bound to THIS project:
            # emit matches session_id AND project_root, so an id without the
            # exact canonical root can never fire -- refuse it as ambiguous
            # rather than reporting binding_preserved on broken recovery.
            if existing_root == str(root):
                preserve_binding = True
                bound_session = existing_id
            else:
                receipt(
                    action,
                    "refused",
                    reasons=[
                        f"{binding_path}: bound session id without the "
                        "canonical project_root of this project"
                    ],
                )
                return 1
        elif existing_id is None and (
            existing_root is None or existing_root == str(root)
        ):
            pass  # inert binding -- rewritten canonically below
        else:
            receipt(
                action,
                "refused",
                reasons=[f"{binding_path}: ambiguous existing binding"],
            )
            return 1

    payload_path.parent.mkdir(parents=True, exist_ok=True)
    payload_bytes = PAYLOAD_SOURCE.read_bytes()
    payload_changed = not payload_path.exists() or payload_path.read_bytes() != payload_bytes
    if payload_changed:
        atomic_write(payload_path, payload_bytes)
    emitter_bytes = Path(__file__).resolve().read_bytes()
    emitter_changed = not emitter.exists() or emitter.read_bytes() != emitter_bytes
    if emitter_changed:
        atomic_write(emitter, emitter_bytes)
    binding_changed = (
        False if preserve_binding else write_binding(root, session_id)
    )

    hooks = data.setdefault("hooks", {})
    session = hooks.setdefault("SessionStart", [])
    foreign = [e for e in session if not (isinstance(e, dict) and e.get("id") == ENTRY_ID)]
    entry = hook_entry(emitter)
    merged = foreign + [entry]
    changed = session != merged
    if changed:
        session[:] = merged
        write_hooks(hooks_path, data)
    receipt(
        action,
        "ok",
        changed=changed or payload_changed or emitter_changed or binding_changed,
        hooks_json=str(hooks_path),
        payload=str(payload_path),
        emitter=str(emitter),
        binding=str(binding_path_for(root)),
        binding_preserved=preserve_binding,
        entry_id=ENTRY_ID,
        session_id=bound_session if preserve_binding else session_id,
        project_root=str(root),
        foreign_session_start=len(foreign),
    )
    return 0


def cmd_prepare(root: Path) -> int:
    """Install the entry + assets with an inert (unbound) binding."""
    return _install(root, None, "prepare")


def cmd_install(root: Path, session_id: str | None) -> int:
    if not session_id or not session_id.strip():
        receipt(
            "install",
            "refused",
            reasons=[
                "missing or blank --session-id",
                "the entry must bind the exact designated Host session identity",
            ],
        )
        return 1
    return _install(root, session_id, "install")


def cmd_bind(root: Path, session_id: str | None) -> int:
    """Rebind the designated session by writing ONLY binding.json.

    The hook entry itself is never touched -- it is already loaded/reviewed
    from the session start, and the emit copy re-reads binding.json on every
    event. Refuses when the project has no prepared Runner entry.
    """
    if not session_id or not session_id.strip():
        receipt(
            "bind",
            "refused",
            reasons=[
                "missing or blank --session-id",
                "the entry must bind the exact designated Host session identity",
            ],
        )
        return 1
    hooks_path = hooks_path_for(root)
    try:
        data = load_hooks(hooks_path)
    except ValueError as exc:
        receipt("bind", "refused", reasons=[str(exc)])
        return 1
    hooks = data.get("hooks") or {}
    session = hooks.get("SessionStart")
    ours = [
        e
        for e in (session if isinstance(session, list) else [])
        if isinstance(e, dict) and e.get("id") == ENTRY_ID
    ]
    emitter = emitter_path_for(root)
    payload_path = payload_path_for(root)
    if not ours or not emitter.is_file() or not payload_path.is_file():
        receipt(
            "bind",
            "refused",
            reasons=[
                "no prepared Runner entry/assets in this project; run prepare first"
            ],
        )
        return 1
    changed = write_binding(root, session_id)
    receipt(
        "bind",
        "ok",
        changed=changed,
        binding=str(binding_path_for(root)),
        hooks_json=str(hooks_path),
        session_id=session_id,
        project_root=str(root),
    )
    return 0


def cmd_emit() -> int:
    """Print the payload only for the bound Host's SessionStart(compact).

    Reads ``binding.json`` next to this script copy and the official hook
    input on stdin (``session_id``, ``cwd``, ``hook_event_name``, ``source``).
    Any other session, repository, or event emits nothing and still exits 0 --
    a hook must never break the host turn. The payload, the binding, and this
    script sit side by side under ``<repo>/.codex/kaola-project-runner/hooks/``.
    """
    here = Path(__file__).resolve().parent
    try:
        binding = json.loads((here / "binding.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0
    if not isinstance(binding, dict):
        return 0
    session_id = binding.get("session_id")
    project_root = binding.get("project_root")
    if not isinstance(session_id, str) or not isinstance(project_root, str):
        return 0
    try:
        event = json.loads(sys.stdin.read() or "null")
    except json.JSONDecodeError:
        return 0
    if not isinstance(event, dict):
        return 0
    if event.get("hook_event_name") != "SessionStart" or event.get("source") != "compact":
        return 0
    if event.get("session_id") != session_id:
        return 0
    cwd = event.get("cwd")
    if not isinstance(cwd, str) or not cwd:
        return 0
    try:
        if os.path.realpath(cwd) != os.path.realpath(project_root):
            return 0
    except OSError:
        return 0
    try:
        sys.stdout.buffer.write((here / "compact-recovery.md").read_bytes())
    except OSError:
        pass
    return 0


def cmd_uninstall(root: Path) -> int:
    payload_path = payload_path_for(root)
    hooks_path = hooks_path_for(root)
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
            if not session:
                del hooks["SessionStart"]
            if not hooks:
                del data["hooks"]
            if not data:
                hooks_path.unlink()
            else:
                write_hooks(hooks_path, data)
    payload_removed = payload_path.is_file()
    emitter_removed = emitter_path_for(root).is_file()
    binding_removed = binding_path_for(root).is_file()
    for path in (payload_path, emitter_path_for(root), binding_path_for(root)):
        if path.is_file():
            path.unlink()
    for parent in (
        payload_path.parent,
        payload_path.parent.parent,
        payload_path.parent.parent.parent,
    ):
        try:
            parent.rmdir()
        except OSError:
            break
    receipt(
        "uninstall",
        "ok",
        changed=bool(removed or payload_removed or emitter_removed or binding_removed),
        removed_entries=removed,
        payload_removed=payload_removed,
        emitter_removed=emitter_removed,
        binding_removed=binding_removed,
        hooks_json=str(hooks_path),
    )
    return 0


def cmd_status(root: Path) -> int:
    hooks_path = hooks_path_for(root)
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
    bound = False
    try:
        binding = json.loads(
            binding_path_for(root).read_text(encoding="utf-8")
        )
        bound = (
            isinstance(binding, dict)
            and isinstance(binding.get("session_id"), str)
            and bool(binding["session_id"].strip())
            and binding.get("project_root") == str(root)
        )
    except (OSError, json.JSONDecodeError):
        pass
    receipt(
        "status",
        "ok",
        installed=bool(ours),
        bound=bound,
        entry_id=ENTRY_ID if ours else None,
        entry_hook_count=(
            len(ours[0].get("hooks") or []) if ours else 0
        ),
        hooks_json=str(hooks_path),
        hooks_json_exists=hooks_path.exists(),
        session_start_entries=len(session) if isinstance(session, list) else 0,
        payload=str(payload_path_for(root)),
        payload_present=payload_path_for(root).is_file(),
    )
    return 0


# --- user layer (Issue #97) -------------------------------------------------


def effective_codex_home(raw: str | None = None) -> Path:
    """The Codex home the user layer targets, unresolved (may not exist)."""
    if raw:
        return Path(raw).expanduser()
    env = os.environ.get("CODEX_HOME")
    return Path(env).expanduser() if env else Path.home() / ".codex"


def resolve_codex_home(raw: str | None) -> tuple[Path | None, str | None]:
    """Canonicalize the user-level target, or return a refusal reason.

    The directory must already exist (Codex creates it on first run; the
    installer creates ``<CODEX_HOME>/skills`` before this runs), and the
    filesystem root or the user home directory itself is refused so a
    mistaken ``CODEX_HOME=$HOME`` can never write ``~/hooks.json``.
    """
    if raw is not None and not raw.strip():
        return None, "--codex-home is empty"
    home = effective_codex_home(raw)
    if not home.is_dir():
        return None, f"Codex home is not a directory: {home}"
    home = Path(os.path.realpath(home))
    if home == Path(home.anchor):
        return None, f"Codex home resolves to the filesystem root: {home}"
    if home == Path(os.path.realpath(Path.home())):
        return None, f"Codex home resolves to the user home directory: {home}"
    return home, None


def user_hooks_path_for(home: Path) -> Path:
    return home / "hooks.json"


def user_assets_dir_for(home: Path) -> Path:
    return home / USER_ASSETS_REL


def user_payload_path_for(home: Path) -> Path:
    return user_assets_dir_for(home) / "compact-recovery-user.md"


def user_emitter_path_for(home: Path) -> Path:
    return user_assets_dir_for(home) / "kaola-codex-compact-hook.py"


def user_containment_reason(home: Path) -> str | None:
    """Refuse when a managed user-layer path would escape CODEX_HOME."""
    for path in (
        user_hooks_path_for(home),
        user_assets_dir_for(home),
        user_assets_dir_for(home).parent,
        user_payload_path_for(home),
        user_emitter_path_for(home),
    ):
        real = Path(os.path.realpath(path))
        if real != home and home not in real.parents:
            return f"{path}: resolves outside the Codex home ({real})"
    return None


def user_install_blockers(home: Path) -> list[str]:
    """Reasons a user-install would fail before or during its writes.

    Reported by ``user-status`` (``install_blockers``) so the installer can
    refuse during planning, before its first Skill write, and re-checked by
    ``user-install`` itself so every failure is a receipt, never a traceback.
    """
    blockers: list[str] = []
    if not USER_PAYLOAD_SOURCE.is_file():
        blockers.append(f"missing payload source: {USER_PAYLOAD_SOURCE}")
    for path in (user_assets_dir_for(home).parent, user_assets_dir_for(home)):
        if path.exists() and not path.is_dir():
            blockers.append(f"{path}: exists and is not a directory")
    for path in (user_payload_path_for(home), user_emitter_path_for(home)):
        if path.exists() and not path.is_file():
            blockers.append(f"{path}: exists and is not a regular file")
    if user_hooks_path_for(home).exists() and not user_hooks_path_for(home).is_file():
        blockers.append(f"{user_hooks_path_for(home)}: exists and is not a regular file")
    if not os.access(home, os.W_OK):
        blockers.append(f"{home}: not writable")
    return blockers


def user_hook_entry(emitter: Path) -> dict:
    command = f"python3 {shlex.quote(str(emitter))} user-emit"
    return {
        "matcher": "compact",
        "hooks": [
            {
                "type": "command",
                "command": command,
                "timeout": 5,
            }
        ],
        "description": (
            "Inject the Project Runner conditional compact-recovery prompt "
            "after context compaction (acted on only by a session already "
            "using kaola-delegator or kaola-project-runner)"
        ),
        "id": USER_ENTRY_ID,
    }


def user_entries(session: object) -> list:
    return [
        e
        for e in (session if isinstance(session, list) else [])
        if isinstance(e, dict) and e.get("id") == USER_ENTRY_ID
    ]


def cmd_user_install(home: Path) -> int:
    """Merge the user-level entry and write its private asset copies."""
    action = "user-install"
    blockers = user_install_blockers(home)
    if blockers:
        receipt(action, "refused", reasons=blockers)
        return 1
    hooks_path = user_hooks_path_for(home)
    payload_path = user_payload_path_for(home)
    emitter = user_emitter_path_for(home)
    try:
        data = load_hooks(hooks_path)
    except ValueError as exc:
        receipt(action, "refused", reasons=[str(exc)])
        return 1

    try:
        payload_path.parent.mkdir(parents=True, exist_ok=True)
        payload_bytes = USER_PAYLOAD_SOURCE.read_bytes()
        payload_changed = (
            not payload_path.exists() or payload_path.read_bytes() != payload_bytes
        )
        if payload_changed:
            atomic_write(payload_path, payload_bytes)
        emitter_bytes = Path(__file__).resolve().read_bytes()
        emitter_changed = not emitter.exists() or emitter.read_bytes() != emitter_bytes
        if emitter_changed:
            atomic_write(emitter, emitter_bytes)

        hooks = data.setdefault("hooks", {})
        session = hooks.setdefault("SessionStart", [])
        foreign = [
            e
            for e in session
            if not (isinstance(e, dict) and e.get("id") == USER_ENTRY_ID)
        ]
        merged = foreign + [user_hook_entry(emitter)]
        changed = session != merged
        if changed:
            session[:] = merged
            write_hooks(hooks_path, data)
    except OSError as exc:
        # Asset writes are atomic-replace and hooks.json is written last, so
        # a failure here leaves at most our own copies behind, never a
        # half-written hooks.json; report it as a receipt, not a traceback.
        receipt(action, "refused", reasons=[f"{exc.filename or home}: {exc.strerror or exc}"])
        return 1
    receipt(
        action,
        "ok",
        changed=changed or payload_changed or emitter_changed,
        codex_home=str(home),
        hooks_json=str(hooks_path),
        payload=str(payload_path),
        emitter=str(emitter),
        entry_id=USER_ENTRY_ID,
        foreign_session_start=len(foreign),
        trust_review_required=True,
    )
    return 0


def cmd_user_uninstall(home: Path) -> int:
    action = "user-uninstall"
    hooks_path = user_hooks_path_for(home)
    payload_path = user_payload_path_for(home)
    emitter = user_emitter_path_for(home)
    try:
        data = load_hooks(hooks_path)
    except ValueError as exc:
        receipt(action, "refused", reasons=[str(exc)])
        return 1
    removed = 0
    hooks = data.get("hooks") or {}
    session = hooks.get("SessionStart")
    if isinstance(session, list):
        kept = [
            e
            for e in session
            if not (isinstance(e, dict) and e.get("id") == USER_ENTRY_ID)
        ]
        removed = len(session) - len(kept)
        if removed:
            session[:] = kept
            if not session:
                del hooks["SessionStart"]
            if not hooks:
                del data["hooks"]
            if not data:
                hooks_path.unlink()
            else:
                write_hooks(hooks_path, data)
    payload_removed = payload_path.is_file()
    emitter_removed = emitter.is_file()
    for path in (payload_path, emitter):
        if path.is_file():
            path.unlink()
    for parent in (payload_path.parent, payload_path.parent.parent):
        try:
            parent.rmdir()
        except OSError:
            break
    receipt(
        action,
        "ok",
        changed=bool(removed or payload_removed or emitter_removed),
        removed_entries=removed,
        payload_removed=payload_removed,
        emitter_removed=emitter_removed,
        codex_home=str(home),
        hooks_json=str(hooks_path),
    )
    return 0


def cmd_user_status(home: Path) -> int:
    hooks_path = user_hooks_path_for(home)
    try:
        data = load_hooks(hooks_path)
    except ValueError as exc:
        receipt("user-status", "refused", reasons=[str(exc)])
        return 1
    hooks = data.get("hooks") or {}
    session = hooks.get("SessionStart")
    ours = user_entries(session)
    blockers = user_install_blockers(home)
    receipt(
        "user-status",
        "ok",
        installed=bool(ours),
        install_blockers=blockers,
        entry_id=USER_ENTRY_ID if ours else None,
        entry_hook_count=(len(ours[0].get("hooks") or []) if ours else 0),
        codex_home=str(home),
        hooks_json=str(hooks_path),
        hooks_json_exists=hooks_path.exists(),
        session_start_entries=len(session) if isinstance(session, list) else 0,
        payload=str(user_payload_path_for(home)),
        payload_present=user_payload_path_for(home).is_file(),
        emitter_present=user_emitter_path_for(home).is_file(),
    )
    return 0


def legacy_project_entry_bound(cwd: object, session_id: object) -> bool:
    """True exactly when the project-level ``emit`` in ``cwd`` would fire.

    Mirrors ``cmd_emit``: the repository at ``cwd`` carries the Runner
    project entry in its ``.codex/hooks.json`` and its ``binding.json`` names
    this ``session_id`` with ``cwd`` as the canonical root. Any unreadable or
    unmatched shape is False -- the user layer then speaks.
    """
    if not isinstance(cwd, str) or not cwd or not isinstance(session_id, str):
        return False
    try:
        root = Path(os.path.realpath(cwd))
        project_hooks = json.loads(
            (root / ".codex" / "hooks.json").read_text(encoding="utf-8")
        )
        binding = json.loads(
            (root / ASSETS_REL / "binding.json").read_text(encoding="utf-8")
        )
    except (OSError, ValueError):
        return False
    if not isinstance(project_hooks, dict) or not isinstance(binding, dict):
        return False
    hooks = project_hooks.get("hooks")
    session = hooks.get("SessionStart") if isinstance(hooks, dict) else None
    if not any(
        isinstance(e, dict) and e.get("id") == ENTRY_ID
        for e in (session if isinstance(session, list) else [])
    ):
        return False
    bound_root = binding.get("project_root")
    if binding.get("session_id") != session_id or not isinstance(bound_root, str):
        return False
    try:
        return Path(os.path.realpath(bound_root)) == root
    except OSError:
        return False


def cmd_user_emit() -> int:
    """Print the conditional payload for every ``SessionStart(compact)``.

    Reads the official hook input on stdin. The payload beside this script
    copy is printed unless a legacy project-level Runner entry in the
    session's ``cwd`` is bound to this exact session -- then that entry
    carries the recovery and this one stays silent. Always exits 0.
    """
    here = Path(__file__).resolve().parent
    try:
        event = json.loads(sys.stdin.read() or "null")
    except json.JSONDecodeError:
        return 0
    if not isinstance(event, dict):
        return 0
    if event.get("hook_event_name") != "SessionStart" or event.get("source") != "compact":
        return 0
    if legacy_project_entry_bound(event.get("cwd"), event.get("session_id")):
        return 0
    try:
        sys.stdout.buffer.write((here / "compact-recovery-user.md").read_bytes())
    except OSError:
        pass
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare, install, bind, remove, or report the Project Runner "
            "Codex SessionStart(compact) recovery entry inside the consuming "
            "project's .codex/hooks.json. Only the "
            f"{ENTRY_ID!r} entry is ever added or removed; foreign hooks are "
            "never modified and user-global config is never touched. "
            "prepare writes the entry + assets with an inert binding before "
            "the Host starts (hooks load at session start); bind later "
            "writes only binding.json with the designated Host session id; "
            "install is prepare+bind in one step. The entry emits the "
            "recovery payload only for the bound session at the canonical "
            "--project-root. user-install/user-uninstall/user-status manage "
            f"the one {USER_ENTRY_ID!r} entry in the user-level "
            "${CODEX_HOME:-~/.codex}/hooks.json whose user-emit prints a short "
            "conditional payload on every SessionStart(compact)."
        )
    )
    parser.add_argument(
        "action",
        choices=PROJECT_ACTIONS + ("emit",) + USER_ACTIONS + ("user-emit",),
    )
    parser.add_argument(
        "--codex-home",
        default=None,
        help=(
            "Codex home holding the user-level hooks.json (user-install, "
            "user-uninstall, user-status; default ${CODEX_HOME:-~/.codex})"
        ),
    )
    parser.add_argument(
        "--project-root",
        default=None,
        help=(
            "canonical project root holding .codex/hooks.json "
            "(required by prepare, install, bind, uninstall, status)"
        ),
    )
    parser.add_argument(
        "--session-id",
        default=None,
        help=(
            "designated Codex Host session id to bind "
            "(required by install and bind)"
        ),
    )
    args = parser.parse_args(argv)
    if args.action in ("emit", "user-emit"):
        # stdout of the emit modes becomes model context, so a stray option
        # is never answered with a receipt: an option that the generated hook
        # command never carries means this is not that command -- stay silent.
        if args.project_root is not None or args.session_id is not None or args.codex_home is not None:
            return 0
        return cmd_emit() if args.action == "emit" else cmd_user_emit()
    if args.action in USER_ACTIONS:
        # The user layer binds nothing and takes no project: refuse the
        # project-only options outright rather than silently ignoring them.
        stray = [
            flag
            for flag, value in (
                ("--project-root", args.project_root),
                ("--session-id", args.session_id),
            )
            if value is not None
        ]
        if stray:
            receipt(
                args.action,
                "refused",
                reasons=[f"{' '.join(stray)}: not applicable to {args.action}"],
            )
            return 1
        home, reason = resolve_codex_home(args.codex_home)
        if home is None:
            receipt(args.action, "refused", reasons=[reason])
            return 1
        reason = user_containment_reason(home)
        if reason:
            receipt(args.action, "refused", reasons=[reason])
            return 1
        if args.action == "user-install":
            return cmd_user_install(home)
        if args.action == "user-uninstall":
            return cmd_user_uninstall(home)
        return cmd_user_status(home)
    if args.codex_home is not None:
        receipt(
            args.action,
            "refused",
            reasons=[f"--codex-home: not applicable to {args.action}"],
        )
        return 1
    root, reason = resolve_root(args.project_root)
    if root is None:
        receipt(args.action, "refused", reasons=[reason])
        return 1
    reason = containment_reason(root)
    if reason:
        receipt(args.action, "refused", reasons=[reason])
        return 1
    if args.action == "prepare":
        return cmd_prepare(root)
    if args.action == "install":
        return cmd_install(root, args.session_id)
    if args.action == "bind":
        return cmd_bind(root, args.session_id)
    if args.action == "uninstall":
        return cmd_uninstall(root)
    return cmd_status(root)


if __name__ == "__main__":
    sys.exit(main())
