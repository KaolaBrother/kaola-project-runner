#!/usr/bin/env python3
"""Device-local locator and host-target attestation for one kaola-project-runner checkout.

This file lives at ``<checkout>/scripts/kaola-locate.py``. A target (the Mac that runs
Local Computer, or a cloud Agent Computer) registers it once as the command
``kaola-project-runner-locate`` -- a symlink in an owner-chosen bin directory on PATH (the
installer's ``--bin-links`` directory is the default) -- and from then on the thin account
bridge asks that command, on the bound target, where the canonical checkout is. The checkout
path is never written into any Skill: moving the checkout means running ``register`` again
from its new location. There is no service, daemon, registry, or filesystem scan.

``register --target local|cloud --expect-revision R`` validates origin, the required expected
revision, the clean state, and the link path before it touches anything; a refused
registration leaves an existing link and registration receipt unchanged. On success it links the command and
atomically writes a minimal, credential-free **registration receipt** beside the link
(``.kaola-project-runner-locate.json``): schema, resolved repo root, declared target, host
kernel and hashed fingerprint, accepted revision. It stores no hostname field, no username
field, and no account data (the root is a real local path and may include the user's home). Every later call
through the link compares the running host fingerprint, the declared ``--target``, the root
the link resolves to, and HEAD against that receipt and fails closed on any mismatch, so a
fresh conversation needs no memory of the fingerprint. Both files stay device-local.

Every receipt is one bounded JSON line: the target kind **as declared by the caller**
(``--target`` is echoed, never inferred: this script cannot prove whether it runs on a Mac or
a cloud computer; what ties a receipt to the bound target is that the locator link is
device-local and that the running host fingerprint and declared target match the registration
receipt), host kernel and a hashed hostname fingerprint, the resolved repo root, the
normalised origin (only explicit ``https://``, ``ssh://``, or scp ``host:path`` forms are
accepted; a bare ``github.com/...`` or a local path is refused; never the raw URL, never
userinfo), HEAD, clean state, and -- when attesting a dispatch -- the consumer project
identity, the selected worker's script path under the same root, and whether the tmux server
reachable from this environment reports a session of the exact requested name (presence on
that server only: not proof that the session exists elsewhere, and never ownership, which the
worker preflight proves). A ZCode Host runs as an ACP holder with no same-named tmux session,
so for ``--worker zcode`` the receipt also carries ``session.acp_holder_alive``: whether the
holder record that ``kaola-acp status`` reads for that platform, session, and project names a
live holder pid (``null`` when no project checkout is named). For an ACP Host
``session.present`` alone is never aliveness (Issue #102). ``root.path`` and ``project.path``
are real local paths and may include the user's home directory: bounded local evidence for
the bound target, never to be stored in any account Skill. Revision and clean-state facts are what the target's own Git
reports (``rev-parse``, ``status --porcelain``); index tricks such as ``assume-unchanged`` or
``skip-worktree`` and a tampered ``.git`` on the executing host are outside this boundary --
the target host is trusted and no content hashing is attempted. ``result`` is ``ok`` or
``refused`` with reasons; nothing here reads, prints, hashes, or forwards a credential, and
Git runs with ``GIT_TERMINAL_PROMPT=0`` so a missing credential can only fail, never prompt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform as _platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCHEMA = "kaola-project-runner-locator/1"
REGISTRATION_SCHEMA = "kaola-project-runner-locator-registration/1"
LOCATOR_COMMAND = "kaola-project-runner-locate"
REGISTRATION_FILE = f".{LOCATOR_COMMAND}.json"
EXPECTED_ORIGIN = "github.com/KaolaBrother/kaola-project-runner"
ORCHESTRATOR = "kaola-project-runner"
WORKER_IDS = (
    "claude-code", "codex", "cursor-cli", "devin", "droid", "dsh", "grok", "kimi-cli", "opencode", "zcode",
)
TARGETS = ("local", "cloud")
REVISION = re.compile(r"^[0-9a-f]{40}$")
RECEIPT_LIMIT = 4096
GIT_ENV = {"GIT_TERMINAL_PROMPT": "0", "LC_ALL": "C"}
# The path this process was started through: the locator link when invoked as
# ``kaola-project-runner-locate``, the script itself when invoked directly.
INVOKED = Path(__file__)
# Scheme, optional userinfo (dropped), host, optional port, path; the scheme separator is
# spelled `:/{2}` so no credential-looking userinfo literal appears in this source.
URL_FORM = re.compile(r"^(https|ssh):/{2}(?:[^@/\s]+@)?([^/:\s]+)(?::\d+)?/(.+)$")
SCP_FORM = re.compile(r"^(?:[^@/\s]+@)?([^:/\s]+):(?!//)([^\s]+)$")


def git(root: Path, *args: str) -> str | None:
    env = dict(os.environ)
    env.update(GIT_ENV)
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True, text=True, env=env, timeout=30, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def normalise_origin(raw: str) -> str | None:
    """host/Owner/repo from an explicit https://, ssh://, or scp host:path form, else None.

    Userinfo, port, a trailing slash, and ``.git`` are dropped; the raw value is never
    returned. A bare ``github.com/Owner/repo``, ``http://``, ``git://``, ``file://``, or a
    local path is not an accepted form, and neither is a malformed value whose host still
    carries an ``@`` (a second userinfo separator) or whose host or path carries a query
    (``?``) or fragment (``#``): no fragment of such a value is ever echoed.
    """
    value = raw.strip()
    match = URL_FORM.match(value)
    if match:
        host, path = match.group(2), match.group(3)
    else:
        match = SCP_FORM.match(value)
        if not match:
            return None
        host, path = match.group(1), match.group(2)
    if "@" in host or any(mark in host or mark in path for mark in "?#"):
        return None
    host = host.lower()
    path = path.strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    parts = path.split("/")
    if len(parts) != 2 or not all(parts) or "." in (parts[0], parts[1]) or ".." in parts:
        return None
    return f"{host}/{path}"


def host_facts() -> dict[str, str]:
    node = _platform.node() or "unknown"
    return {
        "kernel": _platform.system() or "unknown",
        "fingerprint": hashlib.sha256(node.encode("utf-8")).hexdigest()[:12],
    }


def this_checkout() -> tuple[Path | None, list[str]]:
    script = INVOKED.resolve()
    candidate = script.parent.parent
    top = git(candidate, "rev-parse", "--show-toplevel")
    if top is None:
        return None, ["not-a-checkout"]
    root = Path(top).resolve()
    if (root / "scripts" / "kaola-locate.py").resolve() != script or not (root / "platforms").is_dir():
        return None, ["not-a-checkout"]
    return root, []


def root_facts(root: Path, expect_revision: str | None) -> tuple[dict[str, object], list[str]]:
    reasons: list[str] = []
    origin_raw = git(root, "remote", "get-url", "origin")
    origin = normalise_origin(origin_raw) if origin_raw else None
    if origin_raw and origin is None:
        reasons.append("origin-form-unsupported")
    elif origin is None or origin.lower() != EXPECTED_ORIGIN.lower():
        reasons.append("origin-mismatch")
    head = git(root, "rev-parse", "HEAD")
    if head is None or not REVISION.match(head):
        reasons.append("no-head")
    porcelain = git(root, "status", "--porcelain")
    clean = porcelain == ""
    if not clean:
        reasons.append("dirty")
    revision_match: bool | None = None
    if expect_revision is not None:
        revision_match = head == expect_revision
        if not revision_match:
            reasons.append("revision-mismatch")
    facts = {
        "path": str(root),
        "origin": origin if origin is not None else None,
        "expected_origin": EXPECTED_ORIGIN,
        "head": head,
        "clean": clean,
        "revision_match": revision_match,
    }
    return facts, reasons


def project_facts(project: str) -> tuple[dict[str, object] | None, list[str]]:
    path = Path(project)
    if not path.is_absolute() or not path.is_dir():
        return {"path": project, "on_this_host": False}, ["project-not-on-this-host"]
    resolved = path.resolve()
    top = git(resolved, "rev-parse", "--show-toplevel")
    if top is None:
        return {"path": str(resolved), "on_this_host": True, "toplevel": None}, ["project-not-a-checkout"]
    origin_raw = git(resolved, "remote", "get-url", "origin")
    return {
        "path": str(resolved),
        "on_this_host": True,
        "toplevel": str(Path(top).resolve()),
        "origin": normalise_origin(origin_raw) if origin_raw else None,
    }, []


def worker_facts(root: Path, worker: str) -> tuple[dict[str, object], list[str]]:
    if worker not in WORKER_IDS:
        return {"id": worker}, ["worker-unknown"]
    skill = f"skills/{worker}-{ORCHESTRATOR}"
    script_rel = f"{skill}/scripts/runtime-tmux.sh"
    script = root / script_rel
    facts: dict[str, object] = {"id": worker, "skill": skill, "script": script_rel}
    if not script.is_file():
        return facts, ["script-missing"]
    under_root = script.resolve().is_relative_to(root)
    facts["under_root"] = under_root
    facts["executable"] = os.access(script, os.X_OK)
    reasons = [] if under_root else ["script-outside-root"]
    if not facts["executable"]:
        reasons.append("script-not-executable")
    return facts, reasons


def session_facts(name: str) -> dict[str, object]:
    """Presence of an exact session name on the tmux server reachable from here; nothing more."""
    tmux = shutil.which("tmux")
    present: bool | None = None
    if tmux:
        try:
            present = subprocess.run(
                [tmux, "has-session", "-t", f"={name}"], capture_output=True, timeout=10, check=False,
            ).returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            present = None
    return {"name": name, "present": present}


ACP_RECORD_ROOT_ENV = "KAOLA_ACP_RECORD_ROOT"


def acp_holder_alive(platform: str, session: str, repo: str) -> bool:
    """Issue #102: does the ACP holder record that ``kaola-acp status`` reads for this exact
    platform, session, and repo name a live holder pid? Same record path as kaola-acp.py
    ``record_dir`` (root, ``<platform>/<session>/<sha256(repo)[:16]>/record.json``); one exact
    path, never a scan, and a missing or unreadable record is simply not alive."""
    root = os.environ.get(ACP_RECORD_ROOT_ENV)
    base = Path(root) if root else (
        Path(os.environ.get("XDG_RUNTIME_DIR") or tempfile.gettempdir()) / f"kaola-{os.getuid()}")
    digest = hashlib.sha256(repo.encode("utf-8")).hexdigest()[:16]
    try:
        record = json.loads((base / platform / session / digest / "record.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    pid = record.get("holder_pid") if isinstance(record, dict) else None
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def registration_dir(bin_dir: str | None) -> Path:
    """The directory holding the locator link and its registration receipt."""
    if bin_dir:
        return Path(bin_dir).expanduser()
    if INVOKED.is_symlink():
        return INVOKED.parent
    return Path.home() / ".local" / "bin"


def load_registration(directory: Path) -> tuple[dict[str, object] | None, list[str]]:
    path = directory / REGISTRATION_FILE
    if not path.is_file():
        return None, ["locator-not-registered"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None, ["locator-registration-unreadable"]
    if not isinstance(data, dict) or data.get("schema") != REGISTRATION_SCHEMA:
        return None, ["locator-registration-unreadable"]
    accepted = data.get("accepted_revision")
    if not isinstance(accepted, str) or not REVISION.match(accepted):
        return None, ["locator-registration-unreadable"]
    return data, []


def registration_facts(directory: Path, target: str | None, root: Path | None, head: str | None,
                       required: bool) -> tuple[dict[str, object], list[str]]:
    """Compare this call with the registration receipt beside the link; fail closed on mismatch."""
    path = directory / REGISTRATION_FILE
    facts: dict[str, object] = {"path": str(path), "present": False}
    data, reasons = load_registration(directory)
    if data is None:
        return facts, reasons if (required or path.exists()) else []
    host = host_facts()
    recorded_host = data.get("host") if isinstance(data.get("host"), dict) else {}
    fingerprint_match = (recorded_host.get("fingerprint") == host["fingerprint"]
                         and recorded_host.get("kernel") == host["kernel"])
    target_match = target is None or data.get("target") == target
    root_match = root is not None and data.get("root") == str(root)
    accepted = data.get("accepted_revision")
    revision_current = accepted == head
    facts.update(
        present=True,
        target=data.get("target"),
        accepted_revision=accepted,
        fingerprint_match=fingerprint_match,
        target_match=target_match,
        root_match=root_match,
        revision_current=revision_current,
    )
    mismatches: list[str] = []
    if not fingerprint_match:
        mismatches.append("host-fingerprint-mismatch")
    if not target_match:
        mismatches.append("target-mismatch")
    if not root_match:
        mismatches.append("registration-root-mismatch")
    if not revision_current:
        mismatches.append("registration-stale")
    return facts, mismatches


def emit(receipt: dict[str, object]) -> int:
    line = json.dumps(receipt, ensure_ascii=False, sort_keys=True)
    if len(line.encode("utf-8")) > RECEIPT_LIMIT:
        receipt = {"schema": SCHEMA, "result": "refused", "reasons": ["receipt-too-large"]}
        line = json.dumps(receipt, sort_keys=True)
    print(line)
    return 0 if receipt.get("result") == "ok" else 1


def receipt_command(args: argparse.Namespace) -> int:
    reasons: list[str] = []
    receipt: dict[str, object] = {"schema": SCHEMA, "host": host_facts(), "target": args.target}
    attesting = any([args.project, args.worker, args.session])
    if args.target is None and attesting:
        reasons.append("target-required")
    if args.expect_revision is not None and not REVISION.match(args.expect_revision):
        reasons.append("expect-revision-not-40-hex")
        args.expect_revision = None
    root, root_reasons = this_checkout()
    reasons.extend(root_reasons)
    head: str | None = None
    if root is not None:
        facts, more = root_facts(root, args.expect_revision)
        receipt["root"] = facts
        head = facts["head"] if isinstance(facts["head"], str) else None
        reasons.extend(more)
        if args.worker is not None:
            wf, more = worker_facts(root, args.worker)
            receipt["worker"] = wf
            reasons.extend(more)
    # A declared target is an attestation: the registration receipt is required and every
    # recorded fact must match. A plain discovery call still fails closed on a present,
    # mismatching receipt but tolerates an absent one.
    registration, more = registration_facts(
        registration_dir(args.bin_dir), args.target, root, head, required=args.target is not None,
    )
    receipt["registration"] = registration
    reasons.extend(more)
    if args.project is not None:
        pf, more = project_facts(args.project)
        receipt["project"] = pf
        reasons.extend(more)
    if args.session is not None:
        session = session_facts(args.session)
        if args.worker == "zcode":
            project = receipt.get("project")
            toplevel = project.get("toplevel") if isinstance(project, dict) else None
            session["acp_holder_alive"] = (
                acp_holder_alive("zcode", args.session, toplevel) if isinstance(toplevel, str) else None)
        receipt["session"] = session
    receipt["result"] = "ok" if not reasons else "refused"
    if reasons:
        receipt["reasons"] = reasons
    return emit(receipt)


def register_command(args: argparse.Namespace) -> int:
    """Link the locator and write its registration receipt -- only after every fact is validated.

    Origin, the required expected revision (``--expect-revision``, so a registration can
    always go ``registration-stale``), the clean state, the link path, and the receipt path
    are all checked first; any refusal returns before the filesystem is touched, so a
    foreign, dirty, or mismatched checkout can never replace an existing, good locator or
    its receipt. The link is replaced first and the receipt second, each atomically: a
    failure between the two leaves a receipt that no longer matches the link, which every
    later call refuses (``registration-root-mismatch``) until ``register`` runs again.
    """
    root, reasons = this_checkout()
    receipt: dict[str, object] = {"schema": SCHEMA, "host": host_facts(), "action": "register",
                                  "target": args.target}
    if root is None:
        receipt.update(result="refused", reasons=reasons)
        return emit(receipt)
    if args.expect_revision is None:
        reasons.append("expect-revision-required")
    elif not REVISION.match(args.expect_revision):
        reasons.append("expect-revision-not-40-hex")
        args.expect_revision = None
    facts, more = root_facts(root, args.expect_revision)
    reasons.extend(more)
    receipt["root"] = facts
    bin_dir = registration_dir(args.bin_dir)
    link = bin_dir / LOCATOR_COMMAND
    registration_path = bin_dir / REGISTRATION_FILE
    source = (root / "scripts" / "kaola-locate.py").resolve()
    previous: str | None = None
    if link.is_symlink():
        previous = os.readlink(link)
        if not previous.endswith("/scripts/kaola-locate.py"):
            reasons.append("foreign-locator-link")
    elif link.exists():
        reasons.append("locator-path-occupied")
    registered_before = registration_path.is_file() and not registration_path.is_symlink()
    if (registration_path.exists() or registration_path.is_symlink()) and not registered_before:
        reasons.append("registration-path-occupied")
    locator: dict[str, object] = {"path": str(link), "command": LOCATOR_COMMAND, "changed": False,
                                  "replaced": False}
    registration: dict[str, object] = {"path": str(registration_path), "schema": REGISTRATION_SCHEMA,
                                       "changed": False, "replaced": False}
    if reasons:
        receipt.update(result="refused", reasons=reasons, locator=locator, registration=registration)
        return emit(receipt)
    bin_dir.mkdir(parents=True, exist_ok=True)
    temp = bin_dir / f".{LOCATOR_COMMAND}.tmp.{os.getpid()}"
    if temp.exists() or temp.is_symlink():
        temp.unlink()
    os.symlink(str(source), temp)
    os.replace(temp, link)
    locator.update(changed=True, replaced=previous is not None)
    record = {
        "schema": REGISTRATION_SCHEMA,
        "root": str(root),
        "target": args.target,
        "host": host_facts(),
        "accepted_revision": args.expect_revision,
    }
    temp_record = bin_dir / f"{REGISTRATION_FILE}.tmp.{os.getpid()}"
    temp_record.write_text(json.dumps(record, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp_record, registration_path)
    registration.update(changed=True, replaced=registered_before, target=args.target,
                        accepted_revision=args.expect_revision)
    receipt.update(result="ok", locator=locator, registration=registration)
    return emit(receipt)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command")
    receipt = sub.add_parser("receipt", help="print the locator/attestation receipt (default)")
    receipt.add_argument("--target", choices=TARGETS)
    receipt.add_argument("--expect-revision")
    receipt.add_argument("--project")
    receipt.add_argument("--worker")
    receipt.add_argument("--session")
    receipt.add_argument("--bin-dir", help="directory of the locator link and its registration receipt "
                                           "(default: the link's own directory, else the installer's bin directory)")
    register = sub.add_parser("register", help=f"link {LOCATOR_COMMAND} to this checkout and write its "
                                               "registration receipt (after validating it)")
    register.add_argument("--target", choices=TARGETS, required=True,
                          help="the execution target this registration is declared for")
    register.add_argument("--bin-dir", help="owner-chosen directory on PATH for the link and receipt "
                                            "(default: the installer's bin directory)")
    register.add_argument("--expect-revision", help="the accepted 40-hex revision this registration is for "
                                                    "(required; a later HEAD move is registration-stale)")
    argv = sys.argv[1:]
    if not argv or argv[0].startswith("-"):
        argv = ["receipt", *argv]
    args = parser.parse_args(argv)
    if args.command == "register":
        return register_command(args)
    return receipt_command(args)


if __name__ == "__main__":
    raise SystemExit(main())
