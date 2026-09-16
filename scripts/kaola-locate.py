#!/usr/bin/env python3
"""Device-local locator and host-target attestation for one kaola-project-runner checkout.

This file lives at ``<checkout>/scripts/kaola-locate.py``. A target (the Mac that runs
Local Computer, or a cloud Agent Computer) registers it once as the command
``kaola-project-runner-locate`` -- a symlink in the same bin directory that
``install-local.sh --bin-links`` uses -- and from then on the thin account bridge asks that
command, on the bound target, where the canonical checkout is. The checkout path is never
written into any Skill: moving the checkout means running ``register`` again from its new
location. There is no service, daemon, registry, or filesystem scan; the link is the whole
locator.

Every receipt is one bounded JSON line: the target kind **as declared by the caller**
(``--target`` is echoed, never inferred: this script cannot prove whether it runs on a Mac or
a cloud computer; what ties a receipt to the bound target is that the locator link is
device-local and that its host fingerprint matches the one recorded at registration), host
kernel and a hashed hostname fingerprint, the resolved repo root, the normalised origin (never
the raw URL, never userinfo), HEAD, clean state, and -- when attesting a dispatch -- the
consumer project identity, the selected worker's script path under the same root, and whether
tmux reports a session of the exact requested name (presence only; ownership is proven by the
worker preflight, not here). ``root.path`` and ``project.path`` are real local paths and may
include the user's home directory: bounded local evidence for the bound target, never to be
stored in any account Skill. ``result`` is ``ok`` or ``refused`` with reasons; nothing here
reads, prints, hashes, or forwards a credential, and Git runs with ``GIT_TERMINAL_PROMPT=0``
so a missing credential can only fail, never prompt. ``register`` validates origin, optional
expected revision, clean state, and the link path before it touches anything; a refused
registration leaves an existing locator link unchanged.
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
from pathlib import Path

SCHEMA = "kaola-project-runner-locator/1"
LOCATOR_COMMAND = "kaola-project-runner-locate"
EXPECTED_ORIGIN = "github.com/KaolaBrother/kaola-project-runner"
ORCHESTRATOR = "kaola-project-runner"
WORKER_IDS = ("claude-code", "codex", "cursor-cli", "devin", "grok", "kimi-cli", "opencode")
TARGETS = ("local", "cloud")
REVISION = re.compile(r"^[0-9a-f]{40}$")
RECEIPT_LIMIT = 4096
GIT_ENV = {"GIT_TERMINAL_PROMPT": "0", "LC_ALL": "C"}


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


def normalise_origin(raw: str) -> str:
    """github.com/Owner/repo from any https/ssh/scp form; userinfo, port and .git are dropped."""
    value = raw.strip()
    if "://" in value:
        authority, _, path = value.split("://", 1)[1].partition("/")
        host = authority.rsplit("@", 1)[-1]
    else:
        scp = re.match(r"^(?:[^@/\s]+@)?([^:/\s]+):(.+)$", value)
        if scp:
            host, path = scp.group(1), scp.group(2)
        else:
            host, _, path = value.partition("/")
    host = host.split(":", 1)[0].lower()
    path = path.strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    return f"{host}/{path}"


def host_facts() -> dict[str, str]:
    node = _platform.node() or "unknown"
    return {
        "kernel": _platform.system() or "unknown",
        "fingerprint": hashlib.sha256(node.encode("utf-8")).hexdigest()[:12],
    }


def this_checkout() -> tuple[Path | None, list[str]]:
    script = Path(__file__).resolve()
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
    if origin is None or origin.lower() != EXPECTED_ORIGIN.lower():
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
    if root is not None:
        facts, more = root_facts(root, args.expect_revision)
        receipt["root"] = facts
        reasons.extend(more)
        if args.worker is not None:
            wf, more = worker_facts(root, args.worker)
            receipt["worker"] = wf
            reasons.extend(more)
    if args.project is not None:
        pf, more = project_facts(args.project)
        receipt["project"] = pf
        reasons.extend(more)
    if args.session is not None:
        receipt["session"] = session_facts(args.session)
    receipt["result"] = "ok" if not reasons else "refused"
    if reasons:
        receipt["reasons"] = reasons
    return emit(receipt)


def register_command(args: argparse.Namespace) -> int:
    """Link the locator to this checkout -- only after every fact has been validated.

    Origin, the optional expected revision, the clean state, and the link path are all
    checked first; any refusal returns before the filesystem is touched, so a foreign,
    dirty, or mismatched checkout can never replace an existing, good locator.
    """
    root, reasons = this_checkout()
    receipt: dict[str, object] = {"schema": SCHEMA, "host": host_facts(), "action": "register"}
    if root is None:
        receipt.update(result="refused", reasons=reasons)
        return emit(receipt)
    if args.expect_revision is not None and not REVISION.match(args.expect_revision):
        reasons.append("expect-revision-not-40-hex")
        args.expect_revision = None
    facts, more = root_facts(root, args.expect_revision)
    reasons.extend(more)
    receipt["root"] = facts
    bin_dir = Path(args.bin_dir).expanduser() if args.bin_dir else Path.home() / ".local" / "bin"
    link = bin_dir / LOCATOR_COMMAND
    source = (root / "scripts" / "kaola-locate.py").resolve()
    previous: str | None = None
    if link.is_symlink():
        previous = os.readlink(link)
        if not previous.endswith("/scripts/kaola-locate.py"):
            reasons.append("foreign-locator-link")
    elif link.exists():
        reasons.append("locator-path-occupied")
    locator: dict[str, object] = {"path": str(link), "command": LOCATOR_COMMAND, "changed": False,
                                  "replaced": False}
    if reasons:
        receipt.update(result="refused", reasons=reasons, locator=locator)
        return emit(receipt)
    bin_dir.mkdir(parents=True, exist_ok=True)
    temp = bin_dir / f".{LOCATOR_COMMAND}.tmp.{os.getpid()}"
    if temp.exists() or temp.is_symlink():
        temp.unlink()
    os.symlink(str(source), temp)
    os.replace(temp, link)
    locator.update(changed=True, replaced=previous is not None)
    receipt.update(result="ok", locator=locator)
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
    register = sub.add_parser("register", help=f"link {LOCATOR_COMMAND} to this checkout (after validating it)")
    register.add_argument("--bin-dir")
    register.add_argument("--expect-revision")
    argv = sys.argv[1:]
    if not argv or argv[0].startswith("-"):
        argv = ["receipt", *argv]
    args = parser.parse_args(argv)
    if args.command == "register":
        return register_command(args)
    return receipt_command(args)


if __name__ == "__main__":
    raise SystemExit(main())
