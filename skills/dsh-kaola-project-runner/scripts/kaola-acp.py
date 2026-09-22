#!/usr/bin/env python3
"""Runner v2 ACP transport CLI for the PoC (issue #15).

Thin socket client: every command talks to the per-session holder process
(``kaola-acp-holder.py``) over ``holder.sock`` with newline-delimited JSON.
Receipts are ``schema_version: 3`` JSON on stdout; fact errors ride inside the
receipt as ``error: {code, message}`` while usage errors exit non-zero.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import re
import secrets
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
HOLDER = SCRIPT_DIR / "kaola-acp-holder.py"
MODEL_POLICY_HELPER = SCRIPT_DIR / "kaola-model-policy.py"
FAST_VARIANT_SUFFIXES = ("-fast", "-priority")
SESSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")
PLATFORMS = ("claude-code", "codex", "cursor-cli", "devin", "droid", "dsh", "grok", "kimi-cli", "opencode", "zcode")
START_WAIT = 20.0
SESSION_PREFIX = "kaola"
# Issue #22: default start sets session/set_config_option configId=mode to each
# platform's measured skip-all value. Omitted platforms have no ACP mode skip
# (Grok: agent always-approve; Cursor/OpenCode: no skip-shaped mode value).
# Devin ACP `bypass` is not the PTY argv `dangerous`.
ACP_SKIP_MODE = {
    "claude-code": "bypassPermissions",
    "codex": "agent-full-access",
    "devin": "bypass",
    "droid": "auto-high",
    "kimi-cli": "yolo",
    "zcode": "yolo",
}

# Runner permission-mode names are not Droid autonomy_level values; translate
# them before sending so a caller-permission-mode mapping on ACP stays the
# semantic equivalent of the PTY --permission-mode mapping.
ACP_MODE_VALUE_MAP = {
    "droid": {
        "bypassPermissions": "auto-high",
        "high": "auto-high",
        "medium": "auto-medium",
        "low": "auto-low",
        "manual": "normal",
    },
    "dsh": {"bypassPermissions": "danger-full-access"},
}

# Issue #120: dsh advertises no ACP mode option; its permission mode is the
# launch variable ``DSH_PERMISSION_MODE`` (Seatbelt sandbox + approval policy,
# dsh's own default ``workspace-write``). ``danger-full-access`` is dsh's
# skip-all - no sandbox, approval never - and the Runner default, like every
# other platform's measured bypass. A caller's ``--mode`` or own variable wins.
DSH_PERMISSION_ENV = "DSH_PERMISSION_MODE"
DSH_PERMISSION_MODES = ("read-only", "workspace-write", "danger-full-access")
DSH_SKIP_MODE = "danger-full-access"


def dsh_permission_mode(args: argparse.Namespace) -> tuple[str, str]:
    """The ``DSH_PERMISSION_MODE`` a dsh start launches with, and its source."""
    mode = getattr(args, "mode", None)
    if mode:
        return ACP_MODE_VALUE_MAP["dsh"].get(mode, mode), "caller-mode"
    if os.environ.get(DSH_PERMISSION_ENV):
        return os.environ[DSH_PERMISSION_ENV], "caller-env"
    return DSH_SKIP_MODE, "runner-default"

# A manifest ``acp_command`` may name files shipped inside the Skill with this
# prefix (Issue #50: the vendored Claude Code bridge). It resolves to an
# absolute path before anything is spawned: ``scripts/`` of the installed Skill
# (``SCRIPT_DIR``) first, then the checkout layout whose ``vendor/`` sits one
# level up -- the same two-layout probe ``load_manifest`` uses. A token that
# resolves nowhere is an error, never a PATH lookup.
SKILL_SCRIPTS_TOKEN = "$SKILL_DIR/scripts/"
# Platforms whose ACP agent is a vendored bridge spawning the exact runtime
# binary: the Runner-resolved path of ``binary_env``/``binary_name`` travels to
# the bridge in this variable, so the bridge never looks the binary up itself.
BRIDGE_BINARY_ENV = {
    "claude-code": "CLAUDE_ACP_CLAUDE_BIN",
}
# Issue #124: platforms whose `initialize` returns no `agentInfo`, so a start
# records the launched CLI's own `--version` instead (a fact, never a gate).
CLI_VERSION_PLATFORMS = frozenset({"grok"})
# Issue #112: OpenCode V2 reaches its own server over loopback HTTP, so a
# forward proxy that does not exclude loopback swallows that hop and every ACP
# session method answers ClientError while `initialize` still succeeds.
# Upstream treats loopback bypass as intended (anomalyco/opencode#31096). For
# these platforms only, the child environment gains the missing loopback
# entries; the Runner's own process environment is never modified.
LOOPBACK_NO_PROXY_PLATFORMS = frozenset({"opencode"})
FORWARD_PROXY_ENV = ("HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy")
NO_PROXY_ENV = ("NO_PROXY", "no_proxy")
LOOPBACK_HOSTS = ("127.0.0.1", "localhost")
ZCODE_ENTRY_ENV = "KAOLA_ZCODE_ENTRY"
ZCODE_NODE_ENV = "KAOLA_ZCODE_NODE"
# Issue #62 phase 2: a worker start may declare the ZCode Host session whose
# holder carries worker events back into that host session (the event-driven
# heartbeat carrier). JSON: {"platform": "zcode", "session": ..., "repo": ...}.
# The CLI validates it, resolves the host holder's deterministic socket, and
# hands both to the spawned worker holder; that holder does the notifying from
# its existing agent-exit and turn-end paths. Issue #119: the target platform
# is any platform with a measured Host Skill entry (below); every other
# platform keeps its periodic carrier, and it fails closed.
HEARTBEAT_HOST_ENV = "KAOLA_ACP_HEARTBEAT_HOST"
HEARTBEAT_HOST_SOCKET_ENV = "KAOLA_ACP_HEARTBEAT_HOST_SOCKET"
# Set by a holder for its agent: the JSONL file where an agent that spawns
# detached Runner holders (a ZCode Host turn starting a nested Worker, a
# Claude Code agent doing the same, ...) records each holder's identity so the
# outer holder's exact stop can sweep it even after the outer agent died
# first. Written only by this CLI at holder spawn; read only through the
# identity-checked group resolution in this file and kaola-acp-holder.py.
CHILD_RECORD_ENV = "KAOLA_ACP_CHILD_RECORD"
# Issue #104 (design #99 §a.1): the second holder->agent fact. Every holder
# names itself to the agent it hosts - identity only (holder_instance_id,
# platform, repo, session), no socket, record path, or pid. A `start` run
# inside that agent derives its KAOLA_ACP_HEARTBEAT_HOST binding from it
# (ZCode dispatcher), verifies the named Host holder is live, and refuses
# with a typed receipt when it is not, so a Runner-dispatched worker can
# never open unbound by omission. Absent => standalone start, unchanged.
DISPATCHER_ENV = "KAOLA_ACP_DISPATCHER"
# Issue #119: each platform's measured turn-opening Skill entry line - the
# `host_skill_entry` fact of platforms/<id>.yaml, restated here because an
# installed worker Skill carries only its own manifest while the binding it
# makes names another platform's Host. The contract test holds this table
# equal to the manifests. Empty = no measured entry: that platform is not a
# Host. Issue #122 (owner ruling): it fails closed - a Host-named start, a
# start it dispatches, and a start naming it as the heartbeat target all
# refuse `host-entry-unsupported`; filling the manifest entry with measured
# evidence is the only admission.
HOST_SKILL_ENTRIES = {
    "claude-code": "/kaola-project-runner",
    "codex": "",
    "cursor-cli": "/kaola-project-runner",
    "devin": "/kaola-project-runner",
    "droid": "/kaola-project-runner",
    "dsh": "/kaola-project-runner",
    "grok": "/kaola-project-runner",
    "kimi-cli": "/skill:kaola-project-runner ",
    "opencode": "/kaola-project-runner",
    "zcode": "/kaola-project-runner",
}
# Issue #119: the Skill roots each platform was measured to discover, relative
# to both the consuming repo and the home directory (a pair that does not
# exist on one side is simply skipped). Issue #105 compares worker Skills found
# here against a Host's own build before that Host starts.
HOST_SKILL_DISCOVERY_DIRS = {
    "claude-code": (".claude/skills",),
    "codex": (".codex/skills", ".agents/skills"),
    "cursor-cli": (".cursor/skills", ".claude/skills", ".codex/skills",
                   ".grok/skills", ".agents/skills"),
    "devin": (".config/devin/skills", ".devin/skills", ".claude/skills",
              ".cursor/skills", ".agents/skills"),
    "droid": (".factory/skills", ".agents/skills"),
    "dsh": (".agents/skills",),
    "grok": (".grok/skills", ".agents/skills", ".claude/skills", ".cursor/skills"),
    "kimi-cli": (".agents/skills",),
    "opencode": (".config/opencode/skills", ".config/opencode/skill",
                 ".opencode/skills", ".claude/skills", ".agents/skills"),
    "zcode": (".zcode/skills", ".agents/skills"),
}


def host_capable(platform: Any) -> bool:
    return bool(HOST_SKILL_ENTRIES.get(platform) if isinstance(platform, str) else "")


def host_entry_unsupported(platform: str, role: str) -> dict[str, str]:
    """Issue #122: the typed refusal for an entry-less platform in a Host role."""
    return {"reason": "host-entry-unsupported",
            "detail": (f"{role} platform {platform} has no measured host_skill_entry "
                       f"(platforms/{platform}.yaml is empty), so it cannot run as a Project "
                       "Runner Host: no carrier can open its turn. Use a Host platform with a "
                       "measured entry; admission is measuring the entry and filling the manifest")}


def record_holder_child_spawn(proc: subprocess.Popen) -> dict[str, Any] | None:
    """Append the spawned holder's identity to the parent agent's child record.

    One JSON line ``{pid, pgid, spawned_at ms}``. The holder is spawned with
    ``start_new_session`` so it leads its own process group (``pgid == pid``).
    The append is best effort: the holder's process-tree note already covers
    the outer-agent-alive case, and a lost line never blocks start; the
    recorded identity is only ever trusted while a live pid keeps it.
    """
    path = os.environ.get(CHILD_RECORD_ENV) or ""
    if not path:
        return None
    try:
        pgid = os.getpgid(proc.pid)
    except OSError:
        pgid = proc.pid
    entry = {"pid": proc.pid, "pgid": pgid, "spawned_at": int(time.time() * 1000)}
    recorded = False
    try:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, sort_keys=True) + "\n")
        recorded = True
    except OSError:
        recorded = False
    return {"path": path, "recorded": recorded, "pid": proc.pid, "pgid": pgid}


def zcode_runtime_error() -> str | None:
    """Fail closed unless both ZCode paths are explicit, absolute, and present.

    Never searches PATH and never probes a well-known application bundle.
    """
    entry = os.environ.get(ZCODE_ENTRY_ENV) or ""
    node = os.environ.get(ZCODE_NODE_ENV) or ""
    if not entry:
        return "no explicit ZCode entry: set KAOLA_ZCODE_ENTRY to an absolute path"
    if not node:
        return "no explicit ZCode node runtime: set KAOLA_ZCODE_NODE to an absolute path"
    if not os.path.isabs(entry) or not os.path.isabs(node):
        return "ZCode entry and node runtime must be absolute paths"
    if not os.path.isfile(entry):
        return f"ZCode entry is not a file: {entry}"
    if not os.path.isfile(node):
        return f"ZCode node runtime is not a file: {node}"
    if not os.access(node, os.X_OK):
        return f"ZCode node runtime is not executable: {node}"
    return None


def resolve_agent_command(command: str) -> tuple[str, list[dict[str, Any]]]:
    """Expand ``$SKILL_DIR/scripts/<rel>`` argv words to absolute paths.

    Returns the resolved command plus one fact per token: ``relative``, the
    absolute ``path`` (or ``None``), ``layout`` (``skill`` / ``checkout``),
    ``present``, and ``sha256`` of the resolved file.
    """
    facts: list[dict[str, Any]] = []
    words = shlex.split(command)
    for index, word in enumerate(words):
        if not word.startswith(SKILL_SCRIPTS_TOKEN):
            continue
        relative = word[len(SKILL_SCRIPTS_TOKEN):]
        fact: dict[str, Any] = {"token": SKILL_SCRIPTS_TOKEN, "relative": relative,
                                "path": None, "layout": None, "present": False}
        parts = Path(relative).parts
        if not relative or Path(relative).is_absolute() or ".." in parts:
            # The token names a file inside the Skill; it never escapes it.
            facts.append(fact)
            continue
        for layout, base in (("skill", SCRIPT_DIR), ("checkout", SCRIPT_DIR.parent)):
            candidate = base / relative
            if candidate.is_file():
                fact.update({"path": str(candidate), "layout": layout, "present": True,
                             "sha256": hashlib.sha256(candidate.read_bytes()).hexdigest()})
                words[index] = str(candidate)
                break
        facts.append(fact)
    # A command without the token is passed through untouched.
    return (shlex.join(words) if facts else command), facts


def runtime_binary(manifest: dict[str, str]) -> str:
    """The exact runtime binary the Runner would launch: ``binary_env`` wins,
    else the first PATH match, else the bare name (a fact, not a launch).

    ZCode never searches PATH: only an explicit absolute ``KAOLA_ZCODE_NODE``.
    """
    if manifest.get("id") == "zcode":
        node = os.environ.get(ZCODE_NODE_ENV) or ""
        return node if os.path.isabs(node) else ""
    return (
        os.environ.get(manifest.get("binary_env") or "")
        or shutil.which(manifest.get("binary_name") or "")
        or manifest.get("binary_name")
        or ""
    )


def loopback_no_proxy(env: dict[str, str]) -> dict[str, str]:
    """The NO_PROXY/no_proxy values a loopback-reaching child needs, or {}.

    No-op without a forward proxy. Each non-empty name the operator set is
    extended in place (existing bytes kept, never removed or reordered) with
    only the loopback hosts it lacks; ``*`` already excludes everything. When
    neither name is set, both are set, because clients differ on which one
    they read. ``scripts/adapters/opencode.sh`` applies the same rule to the
    PTY child, and one contract test runs both over the same cases."""
    if not any(env.get(name) for name in FORWARD_PROXY_ENV):
        return {}
    names = [name for name in NO_PROXY_ENV if env.get(name)] or list(NO_PROXY_ENV)
    changes: dict[str, str] = {}
    for name in names:
        current = env.get(name) or ""
        entries = {entry.strip() for entry in current.split(",")}
        if "*" in entries:
            continue
        missing = [host for host in LOOPBACK_HOSTS if host not in entries]
        if not missing:
            continue
        base = current.rstrip()
        if base and not base.endswith(","):
            base += ","
        changes[name] = base + ",".join(missing)
    return changes


def agent_environment(args: argparse.Namespace) -> dict[str, str]:
    """Environment for the holder and its agent process: inherited whole, plus
    the exact binary path for a vendored bridge. A non-absolute value is passed
    as-is so the bridge refuses it (fail closed) instead of searching PATH.
    Loopback-reaching platforms also get the loopback proxy bypass; that lands
    in this copy only, never in ``os.environ``."""
    env = dict(os.environ)
    bridge_env = BRIDGE_BINARY_ENV.get(args.platform)
    if bridge_env:
        env[bridge_env] = runtime_binary(args.manifest)
    if args.platform in LOOPBACK_NO_PROXY_PLATFORMS:
        env.update(loopback_no_proxy(env))
    if args.platform == "dsh":
        env[DSH_PERMISSION_ENV] = dsh_permission_mode(args)[0]
    return env


def bridge_facts(args: argparse.Namespace, with_version: bool = False) -> dict[str, Any]:
    """Transport facts for a vendored bridge platform: the resolved bridge file
    and the exact runtime binary. Never a gate; never an environment value."""
    facts: dict[str, Any] = {}
    tokens = getattr(args, "agent_command_facts", None) or []
    if tokens:
        bridge = dict(tokens[0])
        bridge.pop("token", None)
        bridge["upstream_pin"] = args.manifest.get("acp_wrapper_pin") or None
        bridge["verified_versions"] = args.manifest.get("acp_verified_versions") or None
        facts["bridge"] = bridge
    bridge_env = BRIDGE_BINARY_ENV.get(args.platform)
    if bridge_env:
        path = runtime_binary(args.manifest)
        binary: dict[str, Any] = {
            "env": args.manifest.get("binary_env") or None,
            "path": path or None,
            "absolute": bool(path) and os.path.isabs(path),
            "present": bool(path) and os.path.isabs(path) and os.path.isfile(path)
            and os.access(path, os.X_OK),
            "passed_as": bridge_env,
        }
        if with_version and binary["present"]:
            binary["version"] = binary_version(path)
        facts["runtime_binary"] = binary
    return facts


def binary_version(path: str, env: dict[str, str] | None = None) -> str | None:
    """First line of ``<path> --version``, or ``None`` when it cannot be read."""
    try:
        out = subprocess.run([path, "--version"], capture_output=True, text=True,
                             timeout=15, env=env)
    except (OSError, subprocess.TimeoutExpired):
        return None
    text = (out.stdout or out.stderr).strip()
    return text.splitlines()[0] if text else None


def cli_version_fact(args: argparse.Namespace, env: dict[str, str]) -> dict[str, Any] | None:
    """Issue #124: the CLI build this start actually launches, for a platform
    whose ``initialize`` returns no ``agentInfo``. The first word of the agent
    command is resolved on the agent's own PATH and asked for ``--version``,
    reported beside ``acp_verified_versions``. A record, never a gate: a
    mismatch or an unreadable version still starts the session."""
    if args.platform not in CLI_VERSION_PLATFORMS:
        return None
    words = shlex.split(args.agent_command)
    path = shutil.which(words[0], path=env.get("PATH")) if words else None
    return {
        "path": path,
        "version": binary_version(path, env) if path else None,
        "verified_versions": args.manifest.get("acp_verified_versions") or None,
    }


def die(message: str, code: int = 2) -> None:
    print(f"kaola-acp: {message}", file=sys.stderr)
    raise SystemExit(code)


def canonical_dir(path: str) -> str:
    return os.path.realpath(path)


def load_manifest(platform: str) -> dict[str, str]:
    candidates = (SCRIPT_DIR / "platform.yaml", SCRIPT_DIR.parent / "platforms" / f"{platform}.yaml")
    path = next((candidate for candidate in candidates if candidate.is_file()), None)
    if path is None:
        die(f"manifest not found for platform {platform}")
    result: dict[str, str] = {}
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition(":")
        if not separator:
            die(f"{path}:{number}: expected key: value")
        try:
            parsed = json.loads(value.strip())
        except json.JSONDecodeError:
            die(f"{path}:{number}: values must be JSON strings")
        if not isinstance(parsed, str):
            die(f"{path}:{number}: values must be JSON strings")
        result[key.strip()] = parsed
    if result.get("id") != platform or not result.get("acp_command"):
        die(f"invalid ACP manifest for platform {platform}")
    return result


def resolve_repo(raw: str) -> str:
    if not raw or not raw.startswith("/") or not os.path.isdir(raw):
        die("--repo must be an existing absolute path")
    repo = canonical_dir(raw)
    result = subprocess.run(
        ["git", "-C", repo, "rev-parse", "--show-toplevel"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        die(f"not a Git repository: {repo}")
    git_root = canonical_dir(result.stdout.strip())
    if git_root != repo:
        die(f"--repo must name the Git root: {git_root}")
    return repo


def record_root(args: argparse.Namespace) -> Path:
    if getattr(args, "record_root", None):
        return Path(args.record_root)
    env = os.environ.get("KAOLA_ACP_RECORD_ROOT")
    if env:
        return Path(env)
    base = os.environ.get("XDG_RUNTIME_DIR") or tempfile.gettempdir()
    return Path(base) / f"kaola-{os.getuid()}"


def record_dir(args: argparse.Namespace, repo: str) -> Path:
    digest = hashlib.sha256(repo.encode("utf-8")).hexdigest()[:16]
    return record_root(args) / args.platform / args.session / digest


def spawn_record_dir(args: argparse.Namespace, repo: str) -> Path | None:
    """Record directory whose ``children.jsonl`` a record-based receipt may
    consult, or None when the invocation names no platform/session (a receipt
    built from a bare record has no spawn record to read)."""
    if not all(getattr(args, name, None) for name in ("platform", "session")):
        return None
    return record_dir(args, repo)


def sock_path_for_directory(directory: Path) -> Path:
    """Short deterministic socket path; AF_UNIX sun_path is ~104 bytes on macOS."""
    digest = hashlib.sha256(str(directory).encode("utf-8")).hexdigest()[:24]
    return Path(tempfile.gettempdir()) / f"kaola-{os.getuid()}-acp" / f"{digest}.sock"


def sock_path(args: argparse.Namespace, repo: str) -> Path:
    return sock_path_for_directory(record_dir(args, repo))


LIST_SCHEMA = "kaola-acp-list/1"
VIEW_SCHEMA = "kaola-acp-view/1"
VIEW_RUNTIME_CODES = ("holder-lost", "holder-unreachable", "no-session")
HOLDER_STATES = {
    "starting", "ready", "agent_exited", "stopping", "stopped", "error",
}


def probe_socket_ok(path: Path) -> bool:
    if not path.exists():
        return False
    connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        connection.settimeout(0.5)
        connection.connect(str(path))
        return True
    except OSError:
        return False
    finally:
        connection.close()


def parse_list_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="kaola-acp.py list")
    parser.add_argument("--platform", choices=PLATFORMS)
    parser.add_argument("--repo")
    parser.add_argument("--record-root")
    # Issue #132: the default stays the frozen live-holder view; the repo
    # sweep also needs the records whose holder PID is gone.
    parser.add_argument("--include-dead", action="store_true")
    return parser.parse_args(argv)


def command_list(args: argparse.Namespace) -> dict[str, Any]:
    root = record_root(args)
    repo_filter = resolve_repo(args.repo) if args.repo else None
    rows: list[dict[str, Any]] = []
    if not root.is_dir():
        return {"schema": LIST_SCHEMA, "rows": rows}
    for path in sorted(root.glob("*/*/*/record.json")):
        platform = path.parent.parent.parent.name
        session = path.parent.parent.name
        if platform not in PLATFORMS:
            continue
        if args.platform and platform != args.platform:
            continue
        if not SESSION_PATTERN.match(session):
            continue
        directory = path.parent
        record = read_record(directory)
        if not record:
            continue
        pid = record.get("holder_pid")
        if not pid_alive(pid) and not args.include_dead:
            continue
        repo = record.get("repo")
        if not isinstance(repo, str):
            continue
        if repo_filter is not None and repo != repo_filter:
            continue
        identity, _ = holder_identity(directory, record, LIST_IDENTITY_TIMEOUT)
        pending = record.get("pending_permissions") or []
        last = record.get("last_prompt") or {}
        mutation = last.get("mutation_status") if isinstance(last, dict) else None
        if not isinstance(mutation, str) or not mutation:
            mutation = "not_started"
        cursor = record.get("event_cursor")
        if not isinstance(cursor, int) or isinstance(cursor, bool) or cursor < 0:
            cursor = 0
        state = record.get("state")
        if state not in HOLDER_STATES:
            state = str(state) if state is not None else "error"
        rows.append({
            "platform": record.get("platform") or platform,
            "session": record.get("session") or session,
            "repo": repo,
            "state": state,
            "holder_pid": pid,
            "holder_instance_id": record.get("holder_instance_id"),
            "agent_alive": bool(record.get("agent_alive")),
            "event_cursor": cursor,
            "mutation_status": mutation,
            "pending_count": len(pending) if isinstance(pending, list) else 0,
            "socket_ok": probe_socket_ok(sock_path_for_directory(directory)),
            "transport": "acp",
            # Issue #132: the identity check, the Host-name fact, and the
            # recorded binding the repo sweep classifies a row by.
            "identity": identity,
            "host_class": host_session(record.get("platform") or platform,
                                       record.get("session") or session),
            "dispatcher": record.get("dispatcher"),
        })
        attach_binding_fact(rows[-1], record)
    return {"schema": LIST_SCHEMA, "rows": rows}


def view_error(code: str, message: str) -> dict[str, Any]:
    return {"schema": VIEW_SCHEMA, "error": {"code": code, "message": message}}


# Ordinary receipts are bounded (progressive disclosure): capture through
# bound_capture_receipt, observe/status through bound_state_receipt. The capture limit
# equals ``capture_receipt_bytes`` in templates/budgets.json and the PTY bound in
# kaola-observation.py. ``capture --full`` is the explicit, unbounded request and
# never passes through bound_capture_receipt.
CAPTURE_RECEIPT_BYTES = 65536
BOUNDED_LISTS = ("events", "tool_calls")
# Issue #64: an ordinary observe/status receipt carries whole session state, and a real
# platform's ``session_meta`` (Devin ~70.6 KB) beside the stored ``record`` (~142.5 KB)
# busts the capture budget, which replaced the whole ``session_meta`` with
# ``{omitted, bytes, sha256}`` and left ``configOptions`` ``currentValue`` (the
# configured model) unreachable. The state path keeps its own larger
# ``state_receipt_bytes`` limit in templates/budgets.json: realistic meta and record
# sizes stay whole, and a field over this limit is still summarised exactly as before
# — the omission mechanism, credential hygiene, and ``--full`` are unchanged.
STATE_RECEIPT_BYTES = 262144


def event_stream_bytes(items: list[Any]) -> bytes:
    """The canonical byte form of a captured list: one sorted-key JSON line per item."""
    return "".join(
        json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in items
    ).encode("utf-8")


def line_size(value: Any) -> int:
    """Bytes of the emitted receipt line: the JSON plus the newline ``print`` writes."""
    return len(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")) + 1


def bound_capture_receipt(receipt: dict[str, Any], limit: int = CAPTURE_RECEIPT_BYTES) -> dict[str, Any]:
    """Keep an ordinary capture receipt within ``limit`` bytes, verifiably.

    When the JSON line would exceed the limit, the oldest entries of its list
    (``events`` for L2, ``tool_calls`` for L1) are dropped and ``truncated`` records
    the list name, kept/dropped/total counts, the byte size and sha256 of the
    untruncated stream (``event_stream_bytes`` of the full list), and the hint to
    pass ``--full``. The newest entries are always the ones kept.
    """
    key = next((name for name in BOUNDED_LISTS if isinstance(receipt.get(name), list)), None)
    if key is None or line_size(receipt) <= limit:
        return receipt
    items = list(receipt[key])
    stream = event_stream_bytes(items)
    bounded = dict(receipt)
    sizes = [len(json.dumps(item, ensure_ascii=False, sort_keys=True).encode("utf-8")) + 2 for item in items]
    start = 0
    while True:
        kept = items[start:]
        bounded[key] = kept
        bounded["truncated"] = {
            "list": key,
            "kept": len(kept),
            "dropped": start,
            "total": len(items),
            "stream_bytes": len(stream),
            "stream_sha256": hashlib.sha256(stream).hexdigest(),
            "hint": "newest entries kept; pass --full for the whole record",
        }
        size = line_size(bounded)
        if size <= limit or not kept:
            return bounded
        excess = size - limit
        dropped = 0
        while start < len(items) and (dropped < excess or dropped == 0):
            dropped += sizes[start]
            start += 1


# Ordinary observe/status receipts share the same budget. Scalar facts (state, activity,
# turn outcome, cursors, pids, fingerprints) always stay whole; the large structures below
# are summarised, in this order, until the line fits.
STATE_BOUNDED_FIELDS = ("record", "initial_config_options", "session_meta", "capabilities",
                        "agent_info", "pending_permissions")
STATE_BOUNDED_HINT = ("ordinary observe/status receipts are bounded: summarised structures are "
                      "named with their byte size and sha256; pending_permissions keeps its newest entries")


def bound_state_receipt(receipt: dict[str, Any], limit: int = STATE_RECEIPT_BYTES) -> dict[str, Any]:
    """Keep an ordinary observe/status receipt within ``limit`` bytes, verifiably.

    When the emitted line (JSON plus its newline) would exceed the limit, each field in
    ``STATE_BOUNDED_FIELDS`` is replaced in turn by ``{"omitted": true, "bytes", "sha256"}``
    (``pending_permissions`` first drops its oldest entries and keeps the newest that fit) and
    ``truncated.fields`` records, per bounded field, the byte size and sha256 of the full
    value plus its key list or counts. The summary entry is written before its field is cut,
    so the budget is measured on the line that is actually emitted. A receipt within budget
    passes through unchanged.
    """
    if line_size(receipt) <= limit:
        return receipt
    bounded = dict(receipt)
    fields: dict[str, Any] = {}
    bounded["truncated"] = {"fields": fields, "hint": STATE_BOUNDED_HINT}
    for key in STATE_BOUNDED_FIELDS:
        if line_size(bounded) <= limit:
            break
        value = bounded.get(key)
        if not isinstance(value, (dict, list)) or not value:
            continue
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
        summary: dict[str, Any] = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
        fields[key] = summary
        if key == "pending_permissions" and isinstance(value, list):
            kept = list(value)
            summary.update(kind="list", total=len(value), kept=len(kept), dropped=0)
            while line_size(bounded) > limit and kept:
                kept = kept[1:]
                bounded[key] = kept
                summary.update(kept=len(kept), dropped=len(value) - len(kept))
        elif isinstance(value, list):
            summary.update(kind="list", count=len(value))
            bounded[key] = {"omitted": True, "bytes": len(raw), "sha256": summary["sha256"]}
        else:
            summary.update(kind="object", keys=sorted(str(k) for k in value))
            bounded[key] = {"omitted": True, "bytes": len(raw), "sha256": summary["sha256"]}
    return bounded


def command_view(args: argparse.Namespace, repo: str, directory: Path) -> dict[str, Any]:
    sock = sock_path(args, repo)
    record = read_record(directory)
    if record is None:
        return view_error("no-session", "no ACP session record for this platform/session/repo")
    if not pid_alive(record.get("holder_pid")):
        return view_error("holder-lost", "holder process is not alive")
    if not sock.exists():
        if pid_alive(record.get("holder_pid")):
            return view_error("holder-unreachable", "holder alive but socket path is absent")
        return view_error("holder-lost", "holder process is not alive")
    params: dict[str, Any] = {}
    if args.since is not None:
        params["since"] = args.since
    response = socket_request(sock, "view", params, 15.0)
    err = response.get("error")
    if isinstance(err, dict):
        if not pid_alive(record.get("holder_pid")):
            return view_error("holder-lost", "holder process is not alive")
        code = err.get("code")
        if code in VIEW_RUNTIME_CODES:
            return view_error(str(code), str(err.get("message") or "view failed"))
        return view_error(
            "holder-unreachable",
            str(err.get("message") or "holder socket is unreachable"),
        )
    return response


def follow_error_line(code: str, message: str) -> dict[str, Any]:
    return {"kind": "error", "error": {"code": code, "message": message}}


class FollowTextPrinter:
    """Incremental tty join of message text and tool titles (not a TUI).

    Every snapshot/delta/heartbeat carries the whole ``kaola-acp-view/1``
    projection, so the printer remembers what it already wrote per message
    (keyed by cursor/role/messageId) and per tool, and prints only the new
    suffix or a changed tool status.
    """

    def __init__(self) -> None:
        self.printed: dict[tuple[Any, Any, Any], int] = {}
        self.tools: dict[str, Any] = {}
        self.open_key: tuple[Any, Any, Any] | None = None

    def _end_line(self) -> None:
        if self.open_key is not None:
            sys.stdout.write("\n")
            self.open_key = None

    def feed(self, event: dict[str, Any]) -> None:
        kind = event.get("kind")
        if kind in ("error", "eof"):
            self._end_line()
            print(json.dumps(event, ensure_ascii=False), flush=True)
            return
        if kind not in ("snapshot", "delta", "heartbeat"):
            return
        for message in event.get("messages") or []:
            if not isinstance(message, dict):
                continue
            text = str(message.get("text") or "")
            key = (message.get("cursor"), message.get("role"), message.get("messageId"))
            done = self.printed.get(key, 0)
            if len(text) <= done:
                continue
            if self.open_key != key:
                self._end_line()
                sys.stdout.write(f"{message.get('role') or 'message'}: ")
                self.open_key = key
            sys.stdout.write(text[done:])
            self.printed[key] = len(text)
        for tool in event.get("tools") or []:
            if not isinstance(tool, dict):
                continue
            tool_id = str(tool.get("toolCallId") or "")
            status = tool.get("status")
            if tool_id in self.tools and self.tools[tool_id] == status:
                continue
            self.tools[tool_id] = status
            self._end_line()
            title = tool.get("title") or tool_id
            suffix = f" [{status}]" if status else ""
            sys.stdout.write(f"tool: {title}{suffix}\n")
        sys.stdout.flush()


def emit_follow_line(raw: bytes, printer: FollowTextPrinter | None) -> str | None:
    """Print one holder line; return its ``kind`` when it parses."""
    text = raw.decode("utf-8", "replace")
    try:
        event = json.loads(text)
    except ValueError:
        event = None
    if printer is None or not isinstance(event, dict):
        print(text, flush=True)
    else:
        printer.feed(event)
    return event.get("kind") if isinstance(event, dict) else None


def command_follow(args: argparse.Namespace, repo: str, directory: Path) -> int:
    sock = sock_path(args, repo)
    record = read_record(directory)
    printer = FollowTextPrinter() if getattr(args, "format", "json") == "text" else None

    def emit_error(code: str, message: str) -> int:
        print(json.dumps(follow_error_line(code, message), ensure_ascii=False), flush=True)
        return 0

    if record is None:
        return emit_error("no-session", "no ACP session record for this platform/session/repo")
    if not pid_alive(record.get("holder_pid")):
        return emit_error("holder-lost", "holder process is not alive")
    if not sock.exists():
        if pid_alive(record.get("holder_pid")):
            return emit_error("holder-unreachable", "holder alive but socket path is absent")
        return emit_error("holder-lost", "holder process is not alive")

    connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        try:
            connection.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4096)
        except OSError:
            pass
        connection.connect(str(sock))
        params: dict[str, Any] = {}
        if args.since is not None:
            params["since"] = args.since
        payload = json.dumps({
            "op": "follow",
            "request_id": secrets.token_hex(8),
            "params": params,
        }).encode("utf-8") + b"\n"
        connection.sendall(payload)
        buffer = bytearray()
        while True:
            try:
                data = connection.recv(65536)
            except OSError:
                latest = read_record(directory) or record
                if not pid_alive(latest.get("holder_pid")):
                    emit_error("holder-lost", "holder process is not alive")
                return 0
            if not data:
                latest = read_record(directory) or record
                if not pid_alive(latest.get("holder_pid")):
                    emit_error("holder-lost", "holder process is not alive")
                break
            buffer.extend(data)
            while b"\n" in buffer:
                line, _, rest = buffer.partition(b"\n")
                buffer = bytearray(rest)
                if line.strip() and emit_follow_line(line, printer) == "eof":
                    return 0
    except OSError as exc:
        latest = read_record(directory) or record
        if not pid_alive(latest.get("holder_pid")):
            emit_error("holder-lost", "holder process is not alive")
        else:
            emit_error("holder-unreachable", str(exc))
    finally:
        try:
            connection.close()
        except OSError:
            pass
    return 0


def read_record(directory: Path) -> dict[str, Any] | None:
    path = directory / "record.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def pid_alive(pid: Any) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def socket_request(sock_path: Path, op: str, params: dict[str, Any],
                   timeout: float | None) -> dict[str, Any]:
    connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        connection.settimeout(timeout)
        connection.connect(str(sock_path))
        payload = json.dumps({"op": op, "request_id": secrets.token_hex(8),
                              "params": params}).encode("utf-8") + b"\n"
        connection.sendall(payload)
        buffer = bytearray()
        while True:
            data = connection.recv(65536)
            if not data:
                break
            buffer.extend(data)
            if b"\n" in buffer:
                line, _, _ = buffer.partition(b"\n")
                return json.loads(line.decode("utf-8"))
        if buffer:
            return json.loads(buffer.decode("utf-8"))
        return {"error": {"code": "holder-closed", "message": "holder closed the connection"}}
    except (OSError, ValueError) as exc:
        return {"error": {"code": "holder-unreachable", "message": str(exc)}}
    finally:
        connection.close()


# Issue #132: a live PID is necessary, never sufficient. A holder is "live"
# only when its record exists, its PID is alive, its admin socket answers,
# and the socket reports the record's own holder_instance_id; a record left
# behind by a crashed holder whose PID the kernel handed to another process
# fails the last two checks.
IDENTITY_PROBE_TIMEOUT = 5.0
# The frozen list view pays this per silent row; a holder that is initializing
# its agent answers no op at all, so waiting longer only delays the reading.
LIST_IDENTITY_TIMEOUT = 2.0


def answering_socket(directory: Path, record: dict[str, Any],
                     timeout: float = IDENTITY_PROBE_TIMEOUT) -> tuple[Path | None, dict[str, Any] | None]:
    """The admin socket the live holder of this record answers on, and its
    ``state`` reply, or ``(None, None)``. The path derived from this caller's
    spelling of the record root comes first; when it is absent or silent, the
    ``--socket`` in the holder's own argv is tried, but only once that argv's
    ``--record-dir`` resolves to this record (a holder started under another
    spelling of the same root, e.g. ``/tmp`` vs ``/private/tmp``)."""
    derived = sock_path_for_directory(directory)
    candidates = [derived]
    for index, sock in enumerate(candidates):
        if sock.exists():
            state = socket_request(sock, "state", {}, timeout)
            if "holder_instance_id" in state:
                return sock, state
        if index == 0:
            own = holder_argv_paths(record.get("holder_pid"))
            if (own is not None and own[1]
                    and os.path.realpath(own[0]) == os.path.realpath(str(directory))
                    and os.path.realpath(own[1]) != os.path.realpath(str(derived))):
                candidates.append(Path(own[1]))
    return None, None


def holder_identity(directory: Path, record: dict[str, Any],
                    timeout: float = IDENTITY_PROBE_TIMEOUT) -> tuple[str, dict[str, Any] | None]:
    """``verified``, ``dead`` (PID gone), ``unreachable`` (PID alive, socket
    absent or silent), or ``mismatch`` (socket answers with another or no
    instance id), plus the holder's ``state`` reply when it answered."""
    if not pid_alive(record.get("holder_pid")):
        return "dead", None
    _sock, state = answering_socket(directory, record, timeout)
    if state is None:
        return "unreachable", None
    expected = record.get("holder_instance_id")
    if not isinstance(expected, str) or not expected or state["holder_instance_id"] != expected:
        return "mismatch", state
    return "verified", state


def procargs_command(pid: int) -> str | None:
    """``pid``'s argv from the macOS ``KERN_PROCARGS2`` sysctl, joined by
    spaces, or None. Issue #120: under a Seatbelt profile the setuid ``ps``
    cannot exec, but a process may still read its own user's arguments."""
    if sys.platform != "darwin":
        return None
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        mib = (ctypes.c_int * 3)(1, 49, pid)  # CTL_KERN, KERN_PROCARGS2
        size = ctypes.c_size_t(0)
        if libc.sysctl(mib, 3, None, ctypes.byref(size), None, 0) != 0 or size.value < 4:
            return None
        buffer = ctypes.create_string_buffer(size.value)
        if libc.sysctl(mib, 3, buffer, ctypes.byref(size), None, 0) != 0:
            return None
    except (OSError, AttributeError):
        return None
    raw = buffer.raw[:size.value]
    argc = int.from_bytes(raw[:4], sys.byteorder)
    rest = raw[4:]
    end = rest.find(b"\0")  # the exec path, then NUL padding, then argv
    if end < 0:
        return None
    argv = rest[end:].lstrip(b"\0").split(b"\0")[:argc]
    if len(argv) < argc:
        return None
    return " ".join(value.decode("utf-8", "replace") for value in argv)


def process_command(pid: int) -> str | None:
    """Live ``pid``'s command line from ``ps``, else from ``KERN_PROCARGS2``."""
    try:
        result = subprocess.run(["ps", "-p", str(pid), "-o", "command="],
                                capture_output=True, text=True, env=PS_ENV)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except OSError:
        pass
    return procargs_command(pid)


# The holder argv order command_start spawns: --record-dir, --socket, --repo.
# Both anchors below depend on it; test_t3 runs a real start through them.
HOLDER_RECORD_DIR = re.compile(r" --record-dir (.+?) --socket ")
HOLDER_SOCKET = re.compile(r" --socket (.+?) --repo ")


def holder_argv_paths(pid: Any) -> tuple[str, str | None] | None:
    """``(--record-dir, --socket)`` from live ``pid``'s argv when it is a
    holder, else None (not a holder, or the argv is unreadable)."""
    if not isinstance(pid, int) or pid <= 0:
        return None
    command = process_command(pid)
    if command is None or "kaola-acp-holder" not in command:
        return None
    line = f" {command} "
    record_dir = HOLDER_RECORD_DIR.search(line)
    if record_dir is None:
        return None
    sock = HOLDER_SOCKET.search(line)
    return record_dir.group(1), sock.group(1) if sock else None


def holder_argv_anchor(pid: Any, directory: Path) -> bool | None:
    """Issue #132: whether live ``pid`` is the holder of ``directory`` by its
    own argv (``--record-dir`` names that directory, the anchor
    kaola-acp-sweep matches on), both sides resolved so ``/tmp`` and
    ``/private/tmp`` spellings of one root agree. ``None`` when the argv
    cannot be read, which never licenses a signal and never frees a root."""
    if not isinstance(pid, int) or pid <= 0:
        return False
    command = process_command(pid)
    if command is None:
        return None if pid_alive(pid) else False
    if "kaola-acp-holder" not in command:
        return False
    match = HOLDER_RECORD_DIR.search(f" {command} ")
    if match is None:
        return False
    return os.path.realpath(match.group(1)) == os.path.realpath(str(directory))


def git_facts(repo: str) -> dict[str, Any]:
    branch = subprocess.run(
        ["git", "-C", repo, "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True, text=True,
    )
    dirty = subprocess.run(
        ["git", "-C", repo, "status", "--porcelain"],
        capture_output=True, text=True,
    )
    return {
        "branch": branch.stdout.strip() if branch.returncode == 0 else None,
        "dirty": bool(dirty.stdout.strip()) if dirty.returncode == 0 else None,
    }


def base_receipt(args: argparse.Namespace, repo: str) -> dict[str, Any]:
    receipt: dict[str, Any] = {
        "schema_version": 3,
        "platform": args.platform,
        "session": args.session,
        "repo": repo,
        "transport": {
            "selected": "acp",
            "default": args.manifest["default_transport"],
            "alternatives": ["pty"],
            "reason": args.transport_reason,
        },
        "git": git_facts(repo),
    }
    # Issue #73: set by the shared entrypoint once its canonical-root binding
    # has accepted this dispatch. Its absence simply means the guard did not run.
    canonical = os.environ.get("KPR_CANONICAL_REPO")
    if canonical:
        receipt["canonical_repo"] = canonical
    return receipt


def holder_lost_receipt(args: argparse.Namespace, repo: str,
                        record: dict[str, Any]) -> dict[str, Any]:
    receipt = base_receipt(args, repo)
    receipt["outcome"] = "holder_lost"
    last = record.get("last_prompt") or {}
    if last.get("written_at") and not last.get("stop_reason"):
        receipt["mutation_status"] = "unknown"
        receipt["mutation_performed"] = None
    else:
        receipt["mutation_status"] = last.get("mutation_status")
        receipt["mutation_performed"] = (
            None if receipt["mutation_status"] == "unknown"
            else receipt["mutation_status"] in ("completed", "accepted", "in_progress")
        )
    # A recorded normal shutdown is not an unexpected connection loss. Only
    # status/observe use this terminal receipt; mutations retain their errors.
    ids = [record.get(key) for key in ("holder_pid", "agent_pid", "agent_pgid")]
    if (args.command in ("status", "observe") and record.get("state") == "stopped"
            and all(isinstance(pid, int) and pid > 0 for pid in ids)
            and not any(pid_alive(pid) for pid in ids)):
        members = run_ps(["pid", "pgid", "state"])
        groups = recorded_groups(record, spawn_record_dir(args, repo))
        residual = []
        for line in members.stdout.splitlines():
            fields = line.split()
            if (len(fields) == 3 and fields[0].isdigit() and fields[1].isdigit()
                    and int(fields[1]) in groups
                    and not fields[2].upper().startswith("Z")):
                residual.append(int(fields[0]))
        if members.returncode == 0 and not residual:
            receipt.update(outcome="stopped", state="stopped", stopped=True,
                           residual_pids=[], record=record)
            return receipt
    receipt["error"] = {
        "code": "holder-lost",
        "message": "holder process is not alive",
        "holder_pid": record.get("holder_pid"),
        "agent_pgid": record.get("agent_pgid"),
    }
    receipt["state"] = record.get("state")
    receipt["record"] = record
    return receipt


def op_or_holder_lost(args: argparse.Namespace, repo: str, directory: Path,
                      op: str, params: dict[str, Any],
                      timeout: float | None) -> dict[str, Any]:
    sock = sock_path(args, repo)
    record = read_record(directory)
    if record and not pid_alive(record.get("holder_pid")):
        if op == "stop":
            return force_kill_from_record(args, repo, record)
        return holder_lost_receipt(args, repo, record)
    if not sock.exists():
        if record is None:
            receipt = base_receipt(args, repo)
            receipt["error"] = {"code": "no-session",
                                "message": "no ACP session record for this platform/session/repo"}
            return receipt
        if op == "stop" and params.get("force") and pid_alive(record.get("holder_pid")):
            return force_stop_unreachable(args, repo, directory, record, params)
        if pid_alive(record.get("holder_pid")):
            receipt = base_receipt(args, repo)
            receipt["error"] = {"code": "holder-socket-missing",
                                "message": "holder alive but socket path is absent",
                                "holder_pid": record.get("holder_pid")}
            receipt["record"] = record
            return receipt
        return holder_lost_receipt(args, repo, record)
    response = socket_request(sock, op, params, timeout)
    if response.get("error", {}).get("code") == "holder-unreachable":
        if record and not pid_alive(record.get("holder_pid")):
            if op == "stop":
                return force_kill_from_record(args, repo, record)
            return holder_lost_receipt(args, repo, record)
        if record and op == "stop" and params.get("force"):
            return force_stop_unreachable(args, repo, directory, record, params)
    receipt = base_receipt(args, repo)
    receipt.update(response)
    return receipt


SPAWN_RECORD_TOLERANCE = 5.0
SPAWN_RECORD_SLACK = 1.0
PS_ENV = {**os.environ, "LC_ALL": "C"}


class _BsdInfo(ctypes.Structure):
    """``struct proc_bsdinfo`` (``PROC_PIDTBSDINFO``), 136 bytes on macOS."""
    _fields_ = [("flags", ctypes.c_uint32), ("status", ctypes.c_uint32),
                ("xstatus", ctypes.c_uint32), ("pid", ctypes.c_uint32),
                ("ppid", ctypes.c_uint32), ("ids", ctypes.c_uint32 * 7),
                ("comm", ctypes.c_char * 16), ("name", ctypes.c_char * 32),
                ("nfiles", ctypes.c_uint32), ("pgid", ctypes.c_uint32),
                ("pjobc", ctypes.c_uint32), ("e_tdev", ctypes.c_uint32),
                ("e_tpgid", ctypes.c_uint32), ("nice", ctypes.c_int32),
                ("start_tvsec", ctypes.c_uint64), ("start_tvusec", ctypes.c_uint64)]


def libproc_ps(columns: list[str]) -> str | None:
    """``ps -axo <columns>`` text built from libproc, for the columns pid,
    ppid, pgid, state and lstart; ``None`` off macOS or when libproc is
    unreadable. Only processes this user may inspect are listed."""
    if sys.platform != "darwin":
        return None
    try:
        lib = ctypes.CDLL("/usr/lib/libproc.dylib")
        count = lib.proc_listallpids(None, 0)
        pids = (ctypes.c_int * (max(count, 0) + 256))()
        count = lib.proc_listallpids(pids, ctypes.sizeof(pids))
    except (OSError, AttributeError):
        return None
    if count <= 0:
        return None
    lines = []
    for pid in pids[:count]:
        info = _BsdInfo()
        size = ctypes.sizeof(info)
        if lib.proc_pidinfo(pid, 3, ctypes.c_uint64(0), ctypes.byref(info), size) != size:
            continue
        values = {"pid": str(pid), "ppid": str(info.ppid), "pgid": str(info.pgid),
                  "state": "Z" if info.status == 5 else "S",
                  "lstart": time.strftime("%a %b %e %H:%M:%S %Y",
                                          time.localtime(info.start_tvsec))}
        lines.append(" ".join(values[column] for column in columns))
    return "\n".join(lines) + "\n"


def run_ps(columns: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    """``ps -axo <columns=...>``. Issue #120: under a Seatbelt profile (a dsh
    Host's shell tool) the setuid ``/bin/ps`` cannot exec at all; the same
    columns then come from libproc. A table neither source can read has
    returncode 1, so a caller that requires a readable table still refuses."""
    argv = ["ps", "-axo", ",".join(f"{column}=" for column in columns)]
    try:
        return subprocess.run(argv, capture_output=True, text=True, env=env)
    except OSError as exc:
        text = libproc_ps(columns)
        return subprocess.CompletedProcess(argv, 1 if text is None else 0,
                                           stdout=text or "", stderr=str(exc))


def recorded_groups(record: dict[str, Any], directory: Path | None = None) -> list[int]:
    """The agent's own process group plus the out-of-group child groups the
    holder noted while the agent was alive (detached CLI children), plus the
    children the agent itself recorded at spawn in ``children.jsonl`` under
    the record directory. A child group counts only while a recorded member
    pid is still alive in that group with its recorded start time (holder
    note) or a start time at or before the recorded spawn and within
    SPAWN_RECORD_TOLERANCE of it
    (spawn record), so a reused pid or group id is never touched."""
    groups: list[int] = []
    pgid = record.get("agent_pgid")
    agent_started = record.get("agent_started")
    checked = isinstance(agent_started, str) and bool(agent_started)
    if isinstance(pgid, int) and pgid > 0 and not checked:
        # A record written before Issue #132 names no agent start time: its
        # group is trusted as before.
        groups.append(pgid)
    children = record.get("agent_child_groups") or {}
    spawned: list[dict[str, Any]] = []
    if directory is not None:
        try:
            for line in (directory / "children.jsonl").read_text(encoding="utf-8").splitlines():
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if isinstance(entry, dict):
                    spawned.append(entry)
        except OSError:
            pass
    if not children and not spawned and not (checked and isinstance(pgid, int) and pgid > 0):
        return groups
    # ``lstart`` is rendered in the caller's locale on macOS: pin C so it
    # parses and matches what the holder recorded under the same pin.
    table = run_ps(["pid", "pgid", "state", "lstart"], env=PS_ENV)
    by_pid: dict[int, tuple[int, str]] = {}
    for line in table.stdout.splitlines():
        fields = line.split(None, 3)
        if (len(fields) == 4 and fields[0].isdigit() and fields[1].isdigit()
                and not fields[2].upper().startswith("Z")):
            by_pid[int(fields[0])] = (int(fields[1]), fields[3].strip())
    if checked and isinstance(pgid, int) and pgid > 0:
        # Issue #132: the agent leads its own group (start_new_session). A live
        # leader must be the recorded agent by start time; with the leader gone
        # the id cannot have been reused while members still hold the group.
        leader = by_pid.get(pgid)
        if leader is None or leader == (pgid, agent_started):
            groups.append(pgid)
    for child, members in children.items():
        if not str(child).isdigit() or int(child) in groups:
            continue
        if any(str(pid).isdigit() and by_pid.get(int(pid)) == (int(child), started)
               for pid, started in (members or {}).items()):
            groups.append(int(child))
    for entry in spawned:
        pid, child, spawned_at = entry.get("pid"), entry.get("pgid"), entry.get("spawned_at")
        if not (isinstance(pid, int) and isinstance(child, int) and isinstance(spawned_at, (int, float))):
            continue
        live = by_pid.get(pid)
        if live is None or live[0] != child or child in groups:
            continue
        try:
            started = time.mktime(time.strptime(live[1], "%a %b %d %H:%M:%S %Y"))
        except ValueError:
            continue
        delta = spawned_at / 1000.0 - started
        if -SPAWN_RECORD_SLACK <= delta <= SPAWN_RECORD_TOLERANCE:
            groups.append(child)
    return groups


def live_group_members(groups: list[int]) -> list[int]:
    members = run_ps(["pid", "pgid", "state"])
    found: list[int] = []
    for line in members.stdout.splitlines():
        fields = line.split()
        if (len(fields) == 3 and fields[0].isdigit() and fields[1].isdigit()
                and int(fields[1]) in groups and not fields[2].upper().startswith("Z")):
            found.append(int(fields[0]))
    return found


def force_kill_from_record(args: argparse.Namespace, repo: str,
                           record: dict[str, Any]) -> dict[str, Any]:
    """stop --force path when the holder is already gone."""
    groups = recorded_groups(record, spawn_record_dir(args, repo))
    receipt = base_receipt(args, repo)
    killed: list[int] = []
    for pid in live_group_members(groups):
        try:
            os.kill(pid, signal.SIGKILL)
            killed.append(pid)
        except (ProcessLookupError, PermissionError):
            pass
    leftover: list[int] = []
    if groups:
        time.sleep(0.1)
        leftover = live_group_members(groups)
    receipt.update({
        "stopped": True,
        "holder_lost": True,
        "swept_pgids": groups,
        "force_killed_pids": killed,
        "residual_pids": leftover,
        "mutation_status": "unknown"
        if (record.get("last_prompt") or {}).get("written_at")
        and not (record.get("last_prompt") or {}).get("stop_reason")
        else (record.get("last_prompt") or {}).get("mutation_status"),
    })
    sock = sock_path(args, repo)
    try:
        sock.unlink()
    except OSError:
        pass
    # Issue #132: a dead holder never records its own end. Once nothing of
    # its recorded groups is left, say so in the record so a later `status`
    # proves the session gone (`stopped`, `residual_pids: []`).
    directory = spawn_record_dir(args, repo)
    if directory is not None and not leftover and record.get("state") != "stopped":
        path = directory / "record.json"
        if read_record(directory) == record:
            tmp = path.with_name(f"record.{secrets.token_hex(4)}.tmp")
            try:
                tmp.write_text(json.dumps(dict(record, state="stopped"), sort_keys=True),
                               encoding="utf-8")
                tmp.replace(path)
            except OSError:
                pass
    return receipt


def force_stop_unreachable(args: argparse.Namespace, repo: str, directory: Path,
                           record: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    """Issue #132: ``stop --force`` on a record whose holder PID is alive but
    whose socket is absent or silent. A signal needs an identity anchor: the
    record's instance id must equal any expected one, and the live PID's argv
    must name this record directory. A PID whose argv is provably another
    process is a reused PID: nothing is signalled, the record is retired so
    ``status`` reads ``no-session``. An unreadable argv refuses."""
    receipt = base_receipt(args, repo)
    holder_pid = record.get("holder_pid")
    expected = params.get("expected_holder_instance_id")
    if expected is not None and expected != record.get("holder_instance_id"):
        receipt["error"] = {"code": "holder-instance-mismatch",
                            "expected_holder_instance_id": expected,
                            "holder_instance_id": record.get("holder_instance_id")}
        receipt.update(mutation_status="not_started", mutation_performed=False)
        return receipt
    anchor = holder_argv_anchor(holder_pid, directory)
    if anchor is None:
        receipt["error"] = {"code": "holder-unreachable",
                            "message": "holder PID alive, socket silent, and its argv is "
                                       "unreadable (a sandboxed caller cannot read another "
                                       "user's process): no identity anchor, nothing "
                                       "signalled; stop it from an unsandboxed shell",
                            "holder_pid": holder_pid}
        receipt.update(mutation_status="not_started", mutation_performed=False)
        return receipt
    if anchor is False:
        # The holder is proven gone and its PID belongs to someone else: that
        # PID gets no signal. The holder's identity-checked groups are swept as
        # for any dead holder, and the record is retired only once nothing of
        # them is left, so a survivor stays visible to the next sweep.
        groups = recorded_groups(record, directory)
        killed: list[int] = []
        for pid in live_group_members(groups):
            if pid == holder_pid:
                continue
            try:
                os.kill(pid, signal.SIGKILL)
                killed.append(pid)
            except (ProcessLookupError, PermissionError):
                pass
        leftover: list[int] = []
        if groups:
            time.sleep(0.1)
            leftover = [pid for pid in live_group_members(groups) if pid != holder_pid]
        retired = None
        if not leftover:
            retired = directory / f"record.pid-reused-{int(time.time())}.json"
            try:
                (directory / "record.json").replace(retired)
            except OSError:
                retired = None
        try:
            sock_path(args, repo).unlink()
        except OSError:
            pass
        receipt.update({
            "stopped": not leftover,
            "pid_reused": True,
            "holder_pid": holder_pid,
            "holder_signalled": False,
            "swept_pgids": groups,
            "force_killed_pids": killed,
            "retired_record": str(retired) if retired else None,
            "residual_pids": leftover,
        })
        return receipt
    # The live PID is this record's own holder. One started under another
    # spelling of this record root answers on the socket its argv names: stop
    # it there, exactly as an ordinary stop - never signal a holder that answers.
    sock, state = answering_socket(directory, record)
    if sock is not None:
        receipt.update(socket_request(sock, "stop", params, 30.0))
        receipt["answering_socket"] = str(sock)
        return receipt
    # Silent on every socket it could use: a wedged holder.
    for sig, grace in ((signal.SIGTERM, 2.0), (signal.SIGKILL, 2.0)):
        try:
            os.kill(holder_pid, sig)
        except (ProcessLookupError, PermissionError):
            break
        deadline = time.monotonic() + grace
        while time.monotonic() < deadline and pid_alive(holder_pid):
            time.sleep(0.05)
        if not pid_alive(holder_pid):
            break
    receipt = force_kill_from_record(args, repo, record)
    receipt["holder_force_killed"] = holder_pid
    if pid_alive(holder_pid):
        receipt["residual_pids"] = sorted(set(receipt["residual_pids"]) | {holder_pid})
    return receipt


def tier_prefix(manifest: dict[str, str], tier: str) -> str:
    """The manifest key prefix a `--tier` value selects.

    Issue #111: `default` and `upgrade` are universal; the optional third slot
    answers to the platform's own word, carried by `alt_tier_label`.
    """
    if tier == "upgrade":
        return "upgrade"
    label = (manifest.get("alt_tier_label") or "").strip()
    if label and tier == label:
        return "alt"
    return "default"


def tier_declared(manifest: dict[str, str], tier: str | None) -> bool:
    """Whether this platform declares the requested tier at all."""
    if not tier:
        return True
    label = (manifest.get("alt_tier_label") or "").strip()
    return tier in {"default", "upgrade"} or (bool(label) and tier == label)


def tier_refusal(args: argparse.Namespace, repo: str) -> dict[str, Any]:
    """Issue #111 typed refusal, in the Issue #105 shape: a tier this platform
    does not declare is named and rejected, never resolved to `default`."""
    label = (args.manifest.get("alt_tier_label") or "").strip()
    available = f"default, upgrade, or {label}" if label else "default or upgrade"
    receipt = base_receipt(args, repo)
    receipt.pop("git", None)
    receipt.update({
        "result": "refused",
        "reason": "tier-not-declared",
        "action": args.command,
        "detail": (
            f"{args.platform} declares no --tier {args.tier}; "
            f"this platform's presets are {available}."
        ),
        "requested_tier": args.tier,
        "available_tiers": ["default", "upgrade"] + ([label] if label else []),
        "mutation_performed": False,
        "mutation_status": "not_started",
    })
    return receipt


def resolve_selection(args: argparse.Namespace, repo: str) -> dict[str, Any]:
    """Resolve tier/model/effort/Fast through the shared model-policy helper.

    Explicit --model wins over the selected tier preset; explicit --effort
    wins over the preset effort but only attaches to the model it was given
    with.  A resume/continue without tier/model/effort preserves the saved
    native session selection (no Runner model override).
    """
    manifest = args.manifest
    tier = args.tier or "default"
    preserve = bool(args.resume or args.use_continue) and not (
        args.model or args.effort or args.tier
    )
    if args.model:
        source = "user"
        requested = args.model
        candidate = args.model
        effort = args.effort or ""
    elif preserve:
        source = "resume-preserved"
        requested = "native saved session selection"
        candidate = ""
        effort = ""
    else:
        prefix = tier_prefix(manifest, tier)
        source = f"runner-{tier if prefix == 'alt' else prefix}"
        requested = manifest.get(f"{prefix}_model_name") or ""
        candidate = manifest.get(f"{prefix}_model_id") or ""
        effort = args.effort or manifest.get(f"{prefix}_model_effort") or ""
    runtime_bin = runtime_binary(manifest)
    fast_support = manifest.get("fast_support") or ""
    mechanism = (
        "model-suffix" if "model-variant" in fast_support
        else "config" if "config" in fast_support
        else "none"
    )
    policy: dict[str, Any] | None = None
    if MODEL_POLICY_HELPER.is_file():
        try:
            out = subprocess.run(
                [
                    sys.executable, str(MODEL_POLICY_HELPER), "resolve",
                    "--platform", args.platform, "--runtime-bin", runtime_bin,
                    "--repo", repo, "--source", source,
                    "--requested-name", requested, "--candidate-id", candidate,
                    "--effort", effort,
                    "--fast", "true" if args.fast == "on" else "false",
                    "--tier", tier, "--fast-mechanism", mechanism,
                ],
                capture_output=True, text=True, timeout=45,
            )
            if out.returncode == 0:
                policy = json.loads(out.stdout)
        except (OSError, ValueError, subprocess.TimeoutExpired):
            policy = None
    if not isinstance(policy, dict):
        policy = {
            "requested_model_source": source,
            "requested_model_name": requested,
            "requested_tier": tier,
            "requested_fast": args.fast,
            "resolved_runtime_model_id": candidate,
            "resolved_runtime_model_display": None,
            "resolved_parameters": {"effort": effort} if effort else {},
            "resolved_fast": "unknown",
            "model_evidence_provenance": {
                "requested": {"source": source, "name": requested},
                "selection": {"source": source, "tier": tier},
                "resolution": {
                    "state": "policy-helper-unavailable",
                    "candidate_id": candidate or None,
                    "resolved_id": candidate or None,
                },
            },
        }
    return policy


def merge_policy_evidence(receipt: dict[str, Any], policy: dict[str, Any]) -> None:
    for key in (
        "requested_model_source", "requested_model_name", "requested_tier",
        "requested_fast", "resolved_runtime_model_id",
        "resolved_runtime_model_display", "resolved_parameters", "resolved_fast",
        "actual_runtime_model_id", "actual_parameters", "model_verified",
        "model_mismatch_reason", "model_evidence_provenance",
    ):
        if key in policy:
            receipt[key] = policy[key]
    receipt["model_selection"] = {
        "source": policy.get("requested_model_source"),
        "tier": policy.get("requested_tier"),
        "requested_name": policy.get("requested_model_name"),
        "resolved_model": policy.get("resolved_runtime_model_id") or None,
        "resolved_effort": (policy.get("resolved_parameters") or {}).get("effort"),
        "preserved": policy.get("requested_model_source") == "resume-preserved",
    }


def parse_acp_model_map(raw: str) -> dict[str, str]:
    """Parse a manifest ``acp_model_map`` entry: ``id=value;id=value``.

    Maps resolved runtime model IDs (PTY picker IDs) onto the ACP option
    values the agent actually advertises for the same model — e.g. Cursor's
    ``grok-4.7-xhigh`` onto ``grok-4.7[effort=high,fast=true]``.
    """
    mapping: dict[str, str] = {}
    for pair in (raw or "").split(";"):
        key, separator, value = pair.partition("=")
        if separator and key.strip() and value.strip():
            mapping[key.strip()] = value.strip()
    return mapping


def parse_manifest_meta(raw: str) -> dict[str, Any]:
    """Parse a manifest ``acp_init_meta`` entry: ``key=value;key=value``.

    Values decode as JSON literals (``true``/``false``/numbers) falling back
    to strings; the result is sent as ``clientCapabilities._meta`` during
    ``initialize`` — e.g. Cursor's ``parameterizedModelPicker=true``.
    """
    meta: dict[str, Any] = {}
    for pair in (raw or "").split(";"):
        key, separator, value = pair.partition("=")
        if not separator or not key.strip():
            continue
        try:
            meta[key.strip()] = json.loads(value.strip())
        except json.JSONDecodeError:
            meta[key.strip()] = value.strip()
    return meta


def parse_manifest_value_map(raw: str) -> dict[str, str]:
    """Parse ``key=value,key=value`` manifest lists such as ``acp_fast_values``."""
    mapping: dict[str, str] = {}
    for pair in (raw or "").split(","):
        key, separator, value = pair.partition("=")
        if separator and key.strip() and value.strip():
            mapping[key.strip()] = value.strip()
    return mapping


def picker_effort_suffix(model_id: str) -> str:
    """Extract an effort encoded in a picker-style model ID.

    Picker IDs like ``grok-4.7-xhigh`` or ``...-xhigh-fast`` encode
    effort in the trailing token; parameterized ACP transports carry that
    effort through their own effort config option instead.
    """
    base = model_id or ""
    for suffix in FAST_VARIANT_SUFFIXES:
        if base.endswith(suffix):
            base = base[: -len(suffix)]
            break
    match = re.search(r"-(low|medium|high|xhigh|max)$", base)
    return match.group(1) if match else ""


def acp_value_params(value: str) -> dict[str, str]:
    """Parse a trailing ``[k=v,...]`` descriptor from an ACP option value.

    Cursor-style values carry their declared settings in the value itself
    (``grok-4.7[effort=high,fast=true]``); the bracket is the agent's own
    statement of what selecting that value does.

    A *descriptor* qualifies a base value, so it can never be the whole value.
    dsh's model option values are JSON arrays serialized as strings
    (``["deepseek-official","deepseek-v4-pro"]``), which are bracketed end to
    end; reading one as a descriptor would invent a ``declared`` map out of the
    array's elements. A value that opens with the bracket declares nothing.
    """
    if (value or "").lstrip().startswith("["):
        return {}
    match = re.search(r"\[([^\]]+)\]\s*$", value or "")
    params: dict[str, str] = {}
    if match:
        for item in match.group(1).split(","):
            key, _, val = item.partition("=")
            if key.strip():
                params[key.strip()] = val.strip()
    return params


def fast_report(args: argparse.Namespace, policy: dict[str, Any],
                applied_via: str, applied: bool, detail: str | None = None,
                effective: str | None = None) -> dict[str, Any]:
    provenance_fast = (policy.get("model_evidence_provenance") or {}).get("fast") or {}
    report = {
        "requested": args.fast,
        "support": args.manifest.get("fast_support") or "none",
        # ``effective`` reflects proven native state only: a resolved intent is
        # reported when nothing had to be applied, but a failed or unapplied
        # mechanism reports ``unknown``/``unsupported`` — never a false on/off.
        "effective": effective if effective is not None else (policy.get("resolved_fast") or "unknown"),
        "applied": applied,
        "applied_via": applied_via,
    }
    for key in ("conflict", "detail", "model_support"):
        if provenance_fast.get(key) is not None:
            report[key] = provenance_fast[key]
    if detail:
        report["detail"] = detail
    return report


def command_preflight(args: argparse.Namespace, repo: str) -> dict[str, Any]:
    receipt = base_receipt(args, repo)
    receipt.update(bridge_facts(args, with_version=True))
    if any(not fact["present"] for fact in getattr(args, "agent_command_facts", [])):
        receipt["error"] = {"code": "acp-bridge-missing",
                            "message": "the Skill-relative ACP command did not resolve to a file"}
        return receipt
    if args.platform == "zcode":
        missing = zcode_runtime_error()
        if missing:
            receipt["error"] = {"code": "acp-runtime-missing", "message": missing}
            return receipt
    probe_argv = [
        sys.executable, str(HOLDER), "--probe", "--repo", repo,
        "--platform", args.platform, "--command", args.agent_command,
    ]
    init_meta = parse_manifest_meta(args.manifest.get("acp_init_meta") or "")
    if init_meta:
        probe_argv += ["--init-meta", json.dumps(init_meta)]
    result = subprocess.run(
        probe_argv,
        capture_output=True, text=True, timeout=60, env=agent_environment(args),
    )
    try:
        probe = json.loads(result.stdout)
    except ValueError:
        receipt["error"] = {"code": "probe-failed", "message": result.stderr[-400:]}
        return receipt
    probe.pop("probe", None)
    receipt["transport"]["capabilities"] = probe.pop("capabilities", None)
    receipt["transport"]["protocol_version"] = probe.pop("protocol_version", None)
    receipt["transport"]["agent_info"] = probe.pop("agent_info", None)
    receipt["login_required"] = probe.pop("login_required", None)
    receipt["transport"]["auth_methods"] = probe.pop("auth_methods", [])
    receipt["transport"]["advertised_config_ids"] = probe.pop("config_option_ids", None)
    receipt["transport"]["advertised_config_options"] = probe.pop("config_options", None)
    receipt.update(probe)
    policy = resolve_selection(args, repo)
    merge_policy_evidence(receipt, policy)
    receipt["config_application"] = {
        "applied": False,
        "detail": "preflight is read-only; selection reported but not applied",
    }
    receipt["fast"] = fast_report(args, policy, "none", False)
    return receipt


def holder_predates_steer(method: str, error: dict[str, Any]) -> dict[str, Any]:
    """A holder started before this release has no steer op and cannot gain one:
    the running process does not reload its dispatch table. Nothing was written,
    and the caller needs the real remedy rather than a misleading `unsupported`."""
    return {
        "steer_outcome": "not_consumed",
        "steer_consumed": False,
        "steer_confirmation": "none",
        "steer_method": method,
        "mutation_status": "not_started",
        "mutation_performed": False,
        "error": {
            "code": "steer-holder-outdated",
            "message": ("this session's running holder predates the steer operation and cannot "
                        "gain it without being restarted; nothing was written. Stop and start "
                        "the session to steer it"),
            "detail": error,
        },
    }


def validate_heartbeat_target(target: Any, args: argparse.Namespace, repo: str,
                              origin: str) -> dict[str, Any]:
    """Validate one heartbeat host target (a platform with a measured Host
    Skill entry) and resolve its holder socket. Fails closed: a malformed,
    entry-less, or self-referential target is a usage error, never a silently
    dropped event carrier."""
    if not isinstance(target, dict):
        die(f"{origin} must be a JSON object")
    platform = target.get("platform")
    session = target.get("session")
    host_repo = target.get("repo")
    if not host_capable(platform):
        die(f"{origin} target platform must declare a measured Host Skill entry "
            "(the event-driven heartbeat carrier needs one to open the Host turn), "
            f"got {platform!r}")
    if not isinstance(session, str) or not SESSION_PATTERN.match(session):
        die(f"{origin} target session is missing or invalid")
    if not isinstance(host_repo, str) or not host_repo:
        die(f"{origin} target repo is missing")
    host_repo = resolve_repo(host_repo)
    if session == args.session and host_repo == repo:
        die(f"{origin} names this worker's own session; "
            "a session cannot be its own heartbeat host")
    digest = hashlib.sha256(host_repo.encode("utf-8")).hexdigest()[:16]
    directory = record_root(args) / platform / session / digest
    return {"platform": platform, "session": session, "repo": host_repo,
            "socket": str(sock_path_for_directory(directory))}


def dispatcher_identity() -> tuple[dict[str, Any] | None, str | None]:
    """The holder-set KAOLA_ACP_DISPATCHER fact, or (None, None) when this
    start runs under no holder. A present but unusable value is a problem
    to report, never a reason to fall back to a standalone start."""
    raw = os.environ.get(DISPATCHER_ENV) or ""
    if not raw:
        return None, None
    try:
        value = json.loads(raw)
    except ValueError:
        return None, f"{DISPATCHER_ENV} is not valid JSON"
    if not isinstance(value, dict):
        return None, f"{DISPATCHER_ENV} must be a JSON object"
    for key in ("holder_instance_id", "platform", "repo", "session"):
        if not isinstance(value.get(key), str) or not value.get(key):
            return None, f"{DISPATCHER_ENV} is missing {key}"
    return value, None


def repo_problem(raw: str) -> str | None:
    """Why ``raw`` is not an existing Git root, or None (resolve_repo without die)."""
    if not raw or not raw.startswith("/") or not os.path.isdir(raw):
        return "is not an existing absolute path"
    repo = canonical_dir(raw)
    result = subprocess.run(["git", "-C", repo, "rev-parse", "--show-toplevel"],
                            capture_output=True, text=True)
    if result.returncode != 0:
        return "is not a Git repository"
    if canonical_dir(result.stdout.strip()) != repo:
        return "is not the Git root"
    return None


def verify_dispatcher_host_live(args: argparse.Namespace, dispatcher: dict[str, Any],
                                target: dict[str, Any]) -> str | None:
    """Design #99 §a.3: the four read-only checks that the dispatching Host
    holder is the live one this worker would notify. Returns the failed
    check as text, or None when every check passed."""
    digest = hashlib.sha256(target["repo"].encode("utf-8")).hexdigest()[:16]
    directory = record_root(args) / target["platform"] / target["session"] / digest
    record = read_record(directory)
    if not record:
        return f"host holder record is missing at {directory / 'record.json'}"
    holder_pid = record.get("holder_pid")
    if not pid_alive(holder_pid):
        return f"host holder record present but holder_pid {holder_pid} is not alive"
    if record.get("holder_instance_id") != dispatcher["holder_instance_id"]:
        return ("host holder record names holder_instance_id "
                f"{record.get('holder_instance_id')!r}, not the dispatcher's "
                f"{dispatcher['holder_instance_id']!r}")
    if not Path(target["socket"]).exists():
        return f"host holder admin socket is missing at {target['socket']}"
    return None


def resolve_heartbeat_host(args: argparse.Namespace, repo: str) -> dict[str, Any]:
    """Resolve the notification target of this start (design #99 §a.2).

    Returns ``target`` (validated, socket-resolved, or None), ``source`` (``none``,
    ``explicit``, ``dispatcher``, ``dispatcher-no-carrier``), ``dispatcher`` (the parsed identity fact when
    present), and ``refusal`` ({"reason", "detail"}) when this start must
    refuse before anything exists - Issue #122: ``host-entry-unsupported``
    when the dispatcher or the explicit target has no measured Host entry.
    Other explicit-variable failures keep today's ``die`` (stderr, exit 2)."""
    raw = os.environ.get(HEARTBEAT_HOST_ENV) or ""
    explicit: dict[str, Any] | None = None
    if raw:
        try:
            explicit_value = json.loads(raw)
        except ValueError:
            die(f"{HEARTBEAT_HOST_ENV} is not valid JSON")
        # Issue #122: a known platform with no measured entry is a typed
        # refusal, not a usage error; unknown platforms still fail as usage.
        named = explicit_value.get("platform") if isinstance(explicit_value, dict) else None
        if named in HOST_SKILL_ENTRIES and not host_capable(named):
            dispatcher, _ = dispatcher_identity()
            return {"target": None, "source": "explicit", "dispatcher": dispatcher,
                    "requested": explicit_value,
                    "refusal": host_entry_unsupported(named, HEARTBEAT_HOST_ENV + " target")}
        explicit = validate_heartbeat_target(explicit_value, args, repo, HEARTBEAT_HOST_ENV)
    dispatcher, dispatcher_error = dispatcher_identity()
    if dispatcher_error:
        return {"target": explicit, "source": "explicit" if explicit else "dispatcher",
                "dispatcher": None,
                "refusal": {"reason": "heartbeat-host-unresolved", "detail": dispatcher_error}}
    if dispatcher is None:
        return {"target": explicit, "source": "explicit" if explicit else "none",
                "dispatcher": None, "refusal": None}
    if not host_capable(dispatcher.get("platform")):
        # Row 4, Issue #122: dispatched by a platform with no measured Host
        # Skill entry. Fail closed - never an unbound start, and an explicit
        # target no longer excuses it.
        return {"target": None, "source": "explicit" if explicit else "dispatcher-no-carrier",
                "dispatcher": dispatcher, "requested": explicit,
                "refusal": host_entry_unsupported(str(dispatcher.get("platform")),
                                                  f"{DISPATCHER_ENV} dispatcher")}
    problem = repo_problem(dispatcher["repo"])
    if problem:
        return {"target": None, "source": "explicit" if explicit else "dispatcher",
                "dispatcher": dispatcher, "requested": explicit,
                "refusal": {"reason": "heartbeat-host-unresolved",
                            "detail": f"dispatcher repo {dispatcher['repo']} {problem}"}}
    derived = validate_heartbeat_target(
        {"platform": dispatcher["platform"], "session": dispatcher["session"],
         "repo": dispatcher["repo"]},
        args, repo, DISPATCHER_ENV)
    if explicit is not None:
        if (explicit["platform"] == derived["platform"]
                and explicit["session"] == derived["session"]
                and explicit["repo"] == derived["repo"]):
            return {"target": explicit, "source": "explicit", "dispatcher": dispatcher,
                    "refusal": None}
        return {"target": None, "source": "explicit", "dispatcher": dispatcher,
                "requested": explicit,
                "refusal": {"reason": "heartbeat-host-conflict",
                            "detail": (f"{HEARTBEAT_HOST_ENV} names {explicit['session']} at "
                                       f"{explicit['repo']} but this start is dispatched by "
                                       f"{derived['session']} at {derived['repo']}; a Host "
                                       "may only bind its workers to itself")}}
    failed = verify_dispatcher_host_live(args, dispatcher, derived)
    if failed:
        return {"target": None, "source": "dispatcher", "dispatcher": dispatcher,
                "requested": derived,
                "refusal": {"reason": "heartbeat-host-unresolved", "detail": failed}}
    return {"target": derived, "source": "dispatcher", "dispatcher": dispatcher, "refusal": None}


def heartbeat_host_refusal(args: argparse.Namespace, repo: str,
                           resolution: dict[str, Any]) -> dict[str, Any]:
    """A typed pre-mutation refusal in the shape of the shell's canonical-root
    refusal: nothing was probed, written, or spawned."""
    receipt = base_receipt(args, repo)
    receipt.pop("git", None)
    receipt.update({
        "result": "refused",
        "reason": resolution["refusal"]["reason"],
        "action": "start",
        "detail": resolution["refusal"]["detail"],
        "heartbeat_host_source": resolution["source"],
        "heartbeat_host_requested": resolution.get("requested"),
        "dispatcher": resolution["dispatcher"],
        "mutation_performed": False,
        "mutation_status": "not_started",
    })
    return receipt


# Issue #105: the worker Skill trees a ZCode Host's agent will load. The
# Issue #104 binding lives entirely in the copy a worker `start` executes, so a
# Host running one build while an installed worker Skill is an older copy opens
# an unbound worker and exits 0 - the mechanical guarantee fails silently. A
# Host `start` therefore compares the installed copies against its own build
# before anything is spawned. These are the four ZCode default Skill discovery
# roots (docs/zcode-host.md); ancestor-directory roots and configured
# `skills.roots` / `plugins.dirs` roots are out of scope and documented there.
# A root that exists but cannot be listed is refused by name (Issue #106): the
# comparison cannot prove alignment, so it must never degrade to a traceback.
SKILL_DISCOVERY_DIRS = (".zcode/skills", ".agents/skills")
# Verbatim copies of this checkout's scripts/ in every generated worker Skill,
# so the running tree is the baseline and any byte difference is a build skew.
# The three required names ship in every worker Skill; the ZCode bridge is
# compared only where both sides have it.
WORKER_SKILL_SCRIPTS = ("kaola-acp.py", "kaola-acp-holder.py", "kaola-tmux.sh")
WORKER_SKILL_OPTIONAL_SCRIPTS = ("kaola-zcode-acp.py",)
SKEW_DETAIL_CAP = 12
# Issue #121: the main orchestrator Skill ships no scripts, so #105 never saw
# it. Every worker Skill carries the main Skill's build record instead, and a
# Host start compares each same-named main Skill in its discovery roots.
MAIN_SKILL_NAME = "kaola-project-runner"
MAIN_SKILL_BUILD_FILE = "main-skill-build.json"

# Issue #108: a ZCode Host is the Project Runner control plane, so its model
# is a dispatch requirement, not a preference — GLM 5.3 at effort max. The
# discriminator is the documented standard Host session name
# zcode-<PROJECT_CODE>-orchestrator-<purpose> (templates/kaola-delegator):
# every new Host is started under it, while adopted live nonstandard names are
# attached in place and never `start`ed, so they never reach this check. The
# issue-worker marker -i<digits>- wins over a purpose token that happens to
# contain "orchestrator", so an ordinary worker is never caught. There is no
# host flag by design: an opt-in marker can be forgotten, which is exactly the
# silent wrong-model start this removes.
ZCODE_HOST_MODEL_ID = "GLM-5.3"
ZCODE_HOST_EFFORT = "max"
ZCODE_HOST_SESSION = re.compile(
    r"^zcode-[A-Za-z0-9_.]+-orchestrator-[A-Za-z0-9][A-Za-z0-9_.-]*$")
ZCODE_HOST_WORKER_MARKER = re.compile(r"-i[0-9]+-")


def zcode_host_session(name: Any) -> bool:
    if not isinstance(name, str):
        return False
    return bool(ZCODE_HOST_SESSION.match(name)) and not ZCODE_HOST_WORKER_MARKER.search(name)


def host_session(platform: str, name: Any) -> bool:
    """Issue #119: the standard Host name <platform>-<PROJECT_CODE>-orchestrator-<purpose>
    for any platform, with the same -i<N>- worker exclusion as ZCode."""
    if not isinstance(name, str):
        return False
    pattern = (rf"^{re.escape(platform)}-[A-Za-z0-9_.]+-orchestrator-"
               r"[A-Za-z0-9][A-Za-z0-9_.-]*$")
    return bool(re.match(pattern, name)) and not ZCODE_HOST_WORKER_MARKER.search(name)


def zcode_host_model_match(value: Any) -> bool:
    """An ACP model value names GLM 5.3 exactly — provider-qualified values
    (``account:*\\GLM-5.3``, ``builtin:*\\GLM-5.3``) included; the distinct
    GLM-5.3-Flash never matches."""
    if not isinstance(value, str):
        return False
    tail = value.split("\\")[-1].split("/")[-1].strip()
    return tail.lower() == ZCODE_HOST_MODEL_ID.lower()


def zcode_host_request_problem(args: argparse.Namespace) -> str | None:
    """Why an explicit selection contradicts the Host requirement, else None.

    An absent --model/--effort is not a problem: the pin supplies it after
    the session is ready and verifies it against the holder's advertised
    state. Only an explicit wrong value is refused before anything exists.
    """
    problems = []
    if args.model and not zcode_host_model_match(args.model):
        problems.append(f"--model {args.model} is not {ZCODE_HOST_MODEL_ID}")
    if args.effort and str(args.effort).strip().lower() != ZCODE_HOST_EFFORT:
        problems.append(f"--effort {args.effort} is not {ZCODE_HOST_EFFORT}")
    return "; ".join(problems) if problems else None


def zcode_host_selection_fact(
    args: argparse.Namespace,
    applied_model: Any = None,
    applied_effort: Any = None,
    effective_model: Any = None,
    effective_effort: Any = None,
) -> dict[str, Any]:
    """Receipt evidence for the Host model pin: what is required, what was
    requested, what was sent, and the holder-advertised effective values."""
    fact: dict[str, Any] = {
        "required_model": ZCODE_HOST_MODEL_ID,
        "required_effort": ZCODE_HOST_EFFORT,
        "requested_model": args.model or None,
        "requested_effort": args.effort or None,
    }
    if applied_model is not None or applied_effort is not None:
        fact["applied_model"] = applied_model
        fact["applied_effort"] = applied_effort
    fact["effective_model"] = effective_model
    fact["effective_effort"] = effective_effort
    fact["verified"] = bool(
        zcode_host_model_match(effective_model)
        and isinstance(effective_effort, str)
        and effective_effort.strip().lower() == ZCODE_HOST_EFFORT
    )
    return fact


def zcode_host_config_state(state: dict[str, Any]) -> tuple[Any, Any]:
    """The holder-advertised currentValue for model and thought level — the
    agent's own answer, not the value this client asked for."""
    options = (state.get("session_meta") or {}).get("configOptions")
    model = effort = None
    if isinstance(options, list):
        for option in options:
            if not isinstance(option, dict):
                continue
            option_id = option.get("id")
            if option_id == "model":
                model = option.get("currentValue")
            elif option_id in ("thought", "thoughtLevel", "thought_level"):
                effort = option.get("currentValue")
    return model, effort


# Issue #119 (H2): platforms whose explicit --model/--effort must be proven by
# the agent's own advertised currentValue. OpenCode's ACP default silently
# resolves a configured provider to another one (measured 2.0.11), so an
# explicit request that did not take effect must never run on.
EXPLICIT_SELECTION_VERIFIED = frozenset({"opencode"})


def effective_selection(manifest: dict[str, str], state: Any) -> dict[str, Any]:
    """The agent-advertised currentValue of this platform's model and effort
    config options - the agent's answer, not the value this client sent."""
    options = ((state.get("session_meta") or {}).get("configOptions")
               if isinstance(state, dict) else None)
    wanted = {"model": manifest.get("acp_model_config_id") or "",
              "effort": manifest.get("acp_effort_config_id") or ""}
    found: dict[str, Any] = {"effective_model": None, "effective_effort": None}
    if isinstance(options, list):
        for option in options:
            if not isinstance(option, dict):
                continue
            for label, config_id in wanted.items():
                if config_id and option.get("id") == config_id:
                    found[f"effective_{label}"] = option.get("currentValue")
    return found


def explicit_selection_problem(requested_model: str, requested_effort: str,
                               effective: dict[str, Any]) -> str | None:
    problems = []
    if requested_model and effective.get("effective_model") != requested_model:
        problems.append(f"model {effective.get('effective_model')!r} is not the "
                        f"requested {requested_model!r}")
    if requested_effort and str(effective.get("effective_effort") or "").lower() \
            != requested_effort.lower():
        problems.append(f"effort {effective.get('effective_effort')!r} is not the "
                        f"requested {requested_effort!r}")
    return "; ".join(problems) or None


def stop_started_holder(sock: Path, proc: subprocess.Popen) -> dict[str, Any]:
    """Force-stop the holder this start just spawned and reap it."""
    stop_reply = socket_request(sock, "stop", {"force": True}, 30.0)
    # Reap through proc.wait: an exited holder stays a zombie under
    # pid_alive until its own Popen object collects it.
    try:
        proc.wait(timeout=10.0)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except OSError:
            pass
        try:
            proc.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            pass
    return {
        "host_session_stopped": bool(isinstance(stop_reply, dict) and stop_reply.get("stopped")),
        "residual_pids": stop_reply.get("residual_pids") if isinstance(stop_reply, dict) else None,
        "holder_alive": proc.poll() is None,
    }


def zcode_host_refusal(args: argparse.Namespace, repo: str,
                       problem: str) -> dict[str, Any]:
    """Issue #108 typed refusal — the Issue #105 shape: nothing was probed,
    written, or spawned."""
    receipt = base_receipt(args, repo)
    receipt.pop("git", None)
    receipt.update({
        "result": "refused",
        "reason": "host-model-mismatch",
        "action": "start",
        "detail": (
            f"a ZCode Host session ({args.session}) must run "
            f"{ZCODE_HOST_MODEL_ID} at effort {ZCODE_HOST_EFFORT}: {problem}. "
            "Omit --model/--effort to take the enforced selection, or pass "
            "the required values."
        ),
        "host_selection": zcode_host_selection_fact(args),
        "mutation_performed": False,
        "mutation_status": "not_started",
    })
    return receipt


def file_sha256(path: Path) -> str | None:
    """The file's content digest, or None when it cannot be read (symlinked
    installs resolve to their target's bytes, which is the build that runs)."""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def invoking_skill_tree() -> Path | None:
    """The installed Skill tree this CLI was loaded from, or None when it was
    run from a repository checkout (``scripts/kaola-acp.py`` with no sibling
    ``SKILL.md``). Deterministic layout, never an activity observation: only a
    Skill-mediated start can be compared against installed Skill copies, and a
    checkout invocation is the project's own development and test path."""
    if SCRIPT_DIR.name != "scripts":
        return None
    tree = SCRIPT_DIR.parent
    return tree if (tree / "SKILL.md").is_file() else None


def is_worker_skill(path: Path) -> bool:
    return (path / "scripts" / "kaola-acp.py").is_file()


def skill_frontmatter_name(path: Path) -> str | None:
    """The ``name:`` of a Skill directory's SKILL.md frontmatter, or None. A
    runtime loads a Skill by this name, so a renamed backup copy still counts."""
    try:
        lines = (path / "SKILL.md").read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return None
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        if line.strip() == "---":
            return None
        if line.startswith("name:"):
            return line[len("name:"):].strip().strip("\"'") or None
    return None


def is_main_skill(path: Path) -> bool:
    return skill_frontmatter_name(path) == MAIN_SKILL_NAME


def installed_worker_skills(repo: str, platform: str = "zcode",
                            match: Any = is_worker_skill
                            ) -> tuple[list[tuple[Path, list[Path]]], list[str]]:
    """``(found, unreadable)`` for the default discovery roots that exist.

    ``found`` is ``(root, matching Skill directories)`` in the documented order
    and without duplicates. By default a match is a worker Skill, a Skill
    directory that ships ``scripts/kaola-acp.py``; Issue #121 passes
    ``is_main_skill`` for the main orchestrator Skill, which ships no scripts.
    ``unreadable`` names every existing root that could not be listed, so
    ``start`` refuses it by name instead of dying with a traceback (Issue #106)."""
    found: list[tuple[Path, list[Path]]] = []
    unreadable: list[str] = []
    seen: set[str] = set()
    for base in (Path(repo), Path.home()):
        for relative in HOST_SKILL_DISCOVERY_DIRS.get(platform, SKILL_DISCOVERY_DIRS):
            root = base / relative
            if not root.is_dir():
                continue
            try:
                key = str(root.resolve())
            except OSError:
                unreadable.append(str(root))
                continue
            if key in seen:
                continue
            seen.add(key)
            try:
                skills = sorted(path for path in root.iterdir() if match(path))
            except OSError:
                unreadable.append(str(root))
                continue
            if skills:
                found.append((root, skills))
    return found, unreadable


def worker_skill_alignment(repo: str, platform: str = "zcode") -> dict[str, Any]:
    """Compare every installed worker Skill's shared scripts with this build.

    Returns ``applies`` (False for a checkout invocation, which has no Skill
    build to be the baseline), ``build`` (the baseline ``kaola-acp.py`` digest,
    12 hex), ``roots`` (what was compared, for the receipt), ``skew`` (the
    differing files) and ``unreadable_roots`` (Issue #106: existing default
    roots that could not be listed, so no comparison was possible). Read-only:
    nothing is written, probed, or spawned."""
    tree = invoking_skill_tree()
    if tree is None:
        return {"applies": False, "build": None, "roots": None, "skew": [],
                "unreadable_roots": []}
    baseline_dir = tree / "scripts"
    baseline = {name: file_sha256(baseline_dir / name)
                for name in WORKER_SKILL_SCRIPTS + WORKER_SKILL_OPTIONAL_SCRIPTS}
    roots: list[dict[str, Any]] = []
    skew: list[dict[str, Any]] = []
    installed, unreadable = installed_worker_skills(repo, platform)
    for root, skills in installed:
        roots.append({"root": str(root), "skills": [skill.name for skill in skills]})
        for skill in skills:
            for name in WORKER_SKILL_SCRIPTS + WORKER_SKILL_OPTIONAL_SCRIPTS:
                expected = baseline.get(name)
                if expected is None:
                    continue
                installed_path = skill / "scripts" / name
                if name in WORKER_SKILL_OPTIONAL_SCRIPTS and not installed_path.is_file():
                    continue
                installed = file_sha256(installed_path)
                if installed == expected:
                    continue
                skew.append({
                    "path": str(installed_path),
                    "file": name,
                    "installed": installed[:12] if installed else None,
                    "expected": expected[:12],
                })
    return {"applies": True, "build": (baseline.get("kaola-acp.py") or "")[:12] or None,
            "roots": roots, "skew": skew, "unreadable_roots": unreadable}


def main_skill_build(files: dict[str, Any]) -> str:
    """One build id over a main Skill's per-file digests (render-skills.py
    main_skill_build_record uses the same formula)."""
    return hashlib.sha256(
        json.dumps(files, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:12]


def main_skill_alignment(repo: str, platform: str = "zcode") -> dict[str, Any]:
    """Issue #121: compare every installed main Skill with this build's record.

    Same scope and roots as ``worker_skill_alignment``; ``applies`` is False
    for a checkout invocation or a worker Skill built before the record
    existed. A copy is aligned when every recorded file has the recorded
    digest; extra files are ignored. Read-only."""
    tree = invoking_skill_tree()
    record_path = tree / "scripts" / MAIN_SKILL_BUILD_FILE if tree else None
    try:
        record = json.loads(record_path.read_text(encoding="utf-8")) if record_path else None
    except (OSError, ValueError):
        record = None
    files = record.get("files") if isinstance(record, dict) else None
    if not isinstance(files, dict) or not files:
        return {"applies": False, "build": None, "skills": None, "skew": []}
    build = main_skill_build(files)
    found: list[str] = []
    skew: list[dict[str, Any]] = []
    for _root, skills in installed_worker_skills(repo, platform, is_main_skill)[0]:
        for skill in skills:
            found.append(str(skill))
            installed = {name: file_sha256(skill / name) for name in files}
            if installed == files:
                continue
            skew.append({
                "path": str(skill),
                "installed": main_skill_build(installed),
                "expected": build,
                "files": sorted(name for name in files if installed[name] != files[name]),
            })
    return {"applies": True, "build": build, "skills": found, "skew": skew}


def main_skill_skew_refusal(args: argparse.Namespace, repo: str,
                            alignment: dict[str, Any]) -> dict[str, Any]:
    """Issue #121: an installed main Skill differs from this Host's build, and
    the runtime may load that copy instead. The Issue #105 refusal shape;
    nothing is created and no user root is changed."""
    skew = alignment["skew"]
    shown = skew[:SKEW_DETAIL_CAP]
    listed = ", ".join(f"{entry['path']} ({entry['installed']} != {entry['expected']})"
                       for entry in shown)
    more = "" if len(skew) == len(shown) else f" (+{len(skew) - len(shown)} more)"
    receipt = base_receipt(args, repo)
    receipt.pop("git", None)
    receipt.update({
        "result": "refused",
        "reason": "main-skill-build-skew",
        "action": "start",
        "detail": (f"{len(skew)} installed {MAIN_SKILL_NAME} main Skill(s) do not match "
                   f"this Host build {alignment['build']}: {listed}{more}. Re-run "
                   "install-local.sh from the accepted checkout for that root, or remove "
                   "the stale copy, then start again."),
        "main_skill_build": alignment["build"],
        "main_skill_skew": shown,
        "main_skill_skew_count": len(skew),
        "mutation_performed": False,
        "mutation_status": "not_started",
    })
    return receipt


def worker_skill_root_refusal(args: argparse.Namespace, repo: str,
                              alignment: dict[str, Any]) -> dict[str, Any]:
    """Issue #106: an existing default discovery root could not be listed, so
    the installed worker Skills could not be compared with this build. A typed
    pre-mutation refusal in the Issue #105 shape - the caller gets the root
    names, not a traceback, and nothing is created."""
    roots = alignment["unreadable_roots"]
    receipt = base_receipt(args, repo)
    receipt.pop("git", None)
    receipt.update({
        "result": "refused",
        "reason": "worker-skill-root-unreadable",
        "action": "start",
        "detail": (f"cannot verify installed worker Skills: {args.platform} discovery "
                   f"root(s) not readable: {', '.join(roots)}. Make the root "
                   "readable or remove it, then start again."),
        "worker_skill_build": alignment["build"],
        "worker_skill_unreadable_roots": roots,
        "mutation_performed": False,
        "mutation_status": "not_started",
    })
    return receipt


def worker_skill_skew_refusal(args: argparse.Namespace, repo: str,
                              alignment: dict[str, Any]) -> dict[str, Any]:
    """Issue #105: a typed pre-mutation refusal, the same shape as the
    heartbeat-host refusals - no record directory, no socket, no holder."""
    skew = alignment["skew"]
    shown = skew[:SKEW_DETAIL_CAP]
    listed = ", ".join(f"{entry['path']} ({entry['installed'] or 'missing'} "
                       f"!= {entry['expected']})" for entry in shown)
    more = "" if len(skew) == len(shown) else f" (+{len(skew) - len(shown)} more)"
    receipt = base_receipt(args, repo)
    receipt.pop("git", None)
    receipt.update({
        "result": "refused",
        "reason": "worker-skill-build-skew",
        "action": "start",
        "detail": (f"{len(skew)} installed worker Skill script(s) do not match this "
                   f"Host build {alignment['build']}: {listed}{more}. Re-run "
                   "install-local.sh from the accepted checkout, then start again."),
        "worker_skill_build": alignment["build"],
        "worker_skill_roots": alignment["roots"],
        "worker_skill_skew": shown,
        "worker_skill_skew_count": len(skew),
        "mutation_performed": False,
        "mutation_status": "not_started",
    })
    return receipt


def attach_binding_fact(receipt: dict[str, Any], facts: Any) -> dict[str, Any]:
    """Report the notification target the running holder really adopted.

    ``facts`` is a holder ``state`` response or its stored record - the running
    fact, not this command's input. Three honest answers, never two: a target,
    an explicit ``null`` for an ordinary unbound worker, and
    ``heartbeat_host_known: false`` for a holder or record written before this
    field existed. An unknown binding is never reported as unbound, and a later
    environment change or repeated ``start`` never edits a live holder's answer.
    """
    if isinstance(facts, dict) and "heartbeat_host" in facts:
        receipt["heartbeat_host"] = facts["heartbeat_host"]
        receipt["heartbeat_host_known"] = True
    else:
        receipt["heartbeat_host_known"] = False
    return receipt


def verified_hosts(args: argparse.Namespace, repo: str) -> list[dict[str, Any]]:
    """Issue #132: every other Host-named holder recorded for this canonical
    root, on any platform, that is or may be live: it passes the identity
    check, or its live PID still answers on the record's socket under another
    instance id (``mismatch``), or it is silent but its argv names the record
    (``unreachable``: initializing its agent, or wedged) or cannot be read.
    Fail closed: only a dead PID or a provably reused one leaves the root
    free; the others are attached, or exact-stopped and proven gone first."""
    digest = hashlib.sha256(repo.encode("utf-8")).hexdigest()[:16]
    hosts: list[dict[str, Any]] = []
    for path in sorted(record_root(args).glob(f"*/*/{digest}/record.json")):
        platform, session = path.parent.parent.parent.name, path.parent.parent.name
        if platform not in PLATFORMS or not host_session(platform, session):
            continue
        if (platform, session) == (args.platform, args.session):
            continue
        record = read_record(path.parent)
        if not record or record.get("repo") != repo:
            continue
        identity, state = holder_identity(path.parent, record)
        if identity == "dead":
            continue
        anchor = None
        if identity == "unreachable":
            anchor = holder_argv_anchor(record.get("holder_pid"), path.parent)
            if anchor is False:
                continue
        facts = state if identity == "verified" and state else record
        host = {"platform": platform, "session": session, "identity": identity,
                "holder_pid": facts.get("holder_pid"),
                "holder_instance_id": facts.get("holder_instance_id"),
                "acp_session_id": facts.get("acp_session_id"),
                "state": facts.get("state")}
        if identity == "unreachable" and anchor is None:
            # Fail closed: nothing proves this live PID is not the Host.
            host["argv"] = "unreadable"
        if identity == "mismatch" and state:
            # The record names one instance, the socket answers as another.
            host["answering_holder_instance_id"] = state.get("holder_instance_id")
        hosts.append(host)
    return hosts


def host_exists_refusal(args: argparse.Namespace, repo: str,
                        hosts: list[dict[str, Any]]) -> dict[str, Any]:
    """One live Host per canonical root: attach ``existing_host``, never
    rename and retry. Nothing was written or spawned."""
    receipt = base_receipt(args, repo)
    receipt.pop("git", None)
    receipt.update({
        "result": "refused",
        "reason": "host-exists",
        "action": "start",
        "detail": (f"{hosts[0]['session']} holds this repo's Host "
                   f"(identity {hosts[0]['identity']}): attach it when verified, else "
                   "exact-stop it and prove it gone before any Host start"
                   + ("; its holder PID is alive but its argv is unreadable here (a "
                      "Seatbelt-sandboxed caller cannot read another user's process or a "
                      "zombie), so nothing proves it is not the Host - inspect or stop it "
                      "from an unsandboxed shell" if hosts[0].get("argv") == "unreadable"
                      else "")),
        "existing_host": hosts[0],
        "mutation_performed": False,
        "mutation_status": "not_started",
    })
    if len(hosts) > 1:
        receipt["existing_hosts"] = hosts
    return receipt


def command_start(args: argparse.Namespace, repo: str) -> dict[str, Any]:
    # Issue #122: a Host-named start on a platform with no measured Host
    # Skill entry fails closed before anything exists,
    # the bridge included.
    if not host_capable(args.platform) and host_session(args.platform, args.session):
        return heartbeat_host_refusal(args, repo, {
            "source": "none", "dispatcher": None,
            "refusal": host_entry_unsupported(args.platform, "Host")})
    # Issue #132: at most one live Host per canonical root. Every start path -
    # a Delegator's Host start or resume, and a Host dispatch that names a
    # Host - reaches this one guard before anything exists.
    if host_session(args.platform, args.session):
        hosts = verified_hosts(args, repo)
        if hosts:
            return host_exists_refusal(args, repo, hosts)
    receipt = base_receipt(args, repo)
    receipt.update(bridge_facts(args))
    if any(not fact["present"] for fact in getattr(args, "agent_command_facts", [])):
        receipt["error"] = {"code": "acp-bridge-missing",
                            "message": "the Skill-relative ACP command did not resolve to a file"}
        receipt["mutation_status"] = "not_started"
        receipt["mutation_performed"] = False
        return receipt
    if args.platform == "zcode":
        missing = zcode_runtime_error()
        if missing:
            receipt["error"] = {"code": "acp-runtime-missing", "message": missing}
            receipt["mutation_status"] = "not_started"
            receipt["mutation_performed"] = False
            return receipt
    # Issue #119: every ZCode start as before, plus a Host-named start on any
    # other platform with a measured Host Skill entry.
    if args.platform == "zcode" or (host_capable(args.platform)
                                    and host_session(args.platform, args.session)):
        # Issue #105: this agent dispatches workers by running an installed
        # worker Skill's own `start`, and that copy carries the Issue #104
        # binding. Refuse a Host whose installed worker Skills are a different
        # build before anything exists, rather than letting the binding fail
        # silently one dispatch later.
        alignment = worker_skill_alignment(repo, args.platform)
        # Issue #106: an existing default root that cannot be listed means no
        # comparison was possible at all; refuse it by name, never a traceback.
        if alignment["unreadable_roots"]:
            return worker_skill_root_refusal(args, repo, alignment)
        if alignment["skew"]:
            return worker_skill_skew_refusal(args, repo, alignment)
        # What this Host would load into a dispatched worker. `null` means the
        # CLI was not run from an installed Skill tree, so there was no build
        # to compare - unknown, never reported as aligned.
        receipt["worker_skill_build"] = alignment["build"]
        receipt["worker_skill_roots"] = alignment["roots"]
        # Issue #121: the same comparison for the main Skill this Host's
        # runtime loads, which ships no scripts and so is not in #105's set.
        main_alignment = main_skill_alignment(repo, args.platform)
        if main_alignment["skew"]:
            return main_skill_skew_refusal(args, repo, main_alignment)
        receipt["main_skill_build"] = main_alignment["build"]
        # Issue #108: a Host-shaped session must run GLM 5.3 at effort max.
        # An explicit --model/--effort that contradicts that is refused
        # before anything exists; an absent one is pinned after the session
        # is ready and verified against the holder's advertised state.
        if args.platform == "zcode" and zcode_host_session(args.session):
            problem = zcode_host_request_problem(args)
            if problem is not None:
                return zcode_host_refusal(args, repo, problem)
    resolution = resolve_heartbeat_host(args, repo)
    if resolution["refusal"]:
        return heartbeat_host_refusal(args, repo, resolution)
    heartbeat_host = resolution["target"]
    # What this command asked for, and where that request came from. The fact
    # that decides whether a worker can wake a Host is the holder's own, read
    # back below.
    receipt["heartbeat_host_requested"] = heartbeat_host
    receipt["heartbeat_host_source"] = resolution["source"]
    receipt["dispatcher"] = resolution["dispatcher"]
    directory = record_dir(args, repo)
    tmux = subprocess.run(
        ["tmux", "has-session", "-t", f"={args.session}"], capture_output=True
    )
    if tmux.returncode == 0:
        receipt["error"] = {
            "code": "transport-mismatch",
            "other_transport": "pty",
            "message": "a pty session with this name exists",
        }
        return receipt
    record = read_record(directory)
    if record:
        holder_pid = record.get("holder_pid")
        if pid_alive(holder_pid):
            identity, _ = holder_identity(directory, record)
            # Issue #132: a live PID that fails the identity check and whose
            # argv is provably not this record's holder is a reused PID. It is
            # never signalled; the stale record is replaced by this start. An
            # argv that cannot be read keeps the session occupied.
            if identity == "verified" or holder_argv_anchor(holder_pid, directory) is not False:
                receipt["error"] = {"code": "session-exists",
                                    "message": "a live ACP holder already owns this session",
                                    "holder_pid": holder_pid,
                                    "identity": identity,
                                    "acp_session_id": record.get("acp_session_id")}
                # This start bound nothing: the reused holder keeps the target it
                # was started with, so report that one and let the caller verify it.
                return attach_binding_fact(receipt, record)
            receipt["replaced_record"] = {"holder_pid": holder_pid, "pid_reused": True,
                                          "holder_instance_id": record.get("holder_instance_id")}
            try:
                sock_path(args, repo).unlink()
            except OSError:
                pass
        if pid_alive(record.get("agent_pgid")) or pid_alive(record.get("agent_pid")):
            receipt.update(holder_lost_receipt(args, repo, record))
            return receipt
    directory.mkdir(parents=True, exist_ok=True)
    log_path = directory / "holder.out.log"
    # Issue #132: keep --record-dir, --socket, --repo in this order; the
    # identity anchors (HOLDER_RECORD_DIR, HOLDER_SOCKET) parse it.
    holder_argv = [
        sys.executable, str(HOLDER),
        "--record-dir", str(directory),
        "--socket", str(sock_path(args, repo)),
        "--repo", repo,
        "--platform", args.platform,
        "--session", args.session,
        "--command", args.agent_command,
    ]
    if args.resume:
        holder_argv += ["--resume", args.resume]
    if args.use_continue:
        holder_argv += ["--continue"]
    # Issue #119: the Host turn-opening entry and name come from this platform's
    # own manifest, never from the platform id.
    holder_argv += ["--host-entry", args.manifest.get("host_skill_entry") or "",
                    "--host-name", args.manifest.get("runtime_name") or args.platform]
    init_meta = parse_manifest_meta(args.manifest.get("acp_init_meta") or "")
    if init_meta:
        holder_argv += ["--init-meta", json.dumps(init_meta)]
    holder_env = agent_environment(args)
    cli_version = cli_version_fact(args, holder_env)
    if cli_version is not None:
        holder_argv += ["--cli-version", json.dumps(cli_version, sort_keys=True)]
    with open(log_path, "ab") as log:
        if heartbeat_host is not None:
            # Hand the holder the target this command validated and resolved,
            # so the binding it reports back is the one that was checked here
            # rather than a re-reading of the caller's raw string.
            holder_env[HEARTBEAT_HOST_ENV] = json.dumps(heartbeat_host, sort_keys=True)
            holder_env[HEARTBEAT_HOST_SOCKET_ENV] = heartbeat_host["socket"]
        proc = subprocess.Popen(
            holder_argv, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
            start_new_session=True, env=holder_env,
        )
    # When this start runs inside an outer agent (nested Host/Worker chain),
    # record the holder's identity for the outer holder's exact sweep.
    child_record = record_holder_child_spawn(proc)
    if child_record is not None:
        receipt["child_record"] = child_record
    sock = sock_path(args, repo)
    deadline = time.monotonic() + START_WAIT
    state: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        if sock.exists():
            state = socket_request(sock, "state", {}, 5.0)
            if "error" not in state or state.get("error", {}).get("code") != "holder-unreachable":
                if state.get("state") in ("ready", "error", "agent_exited"):
                    break
        if not pid_alive(proc.pid):
            break
        time.sleep(0.1)
    if state is None:
        record = read_record(directory) or {}
        receipt["error"] = {"code": "holder-start-timeout",
                            "message": "holder did not report within the start window",
                            "holder_pid": proc.pid}
        return receipt
    receipt.update({
        "holder_pid": state.get("holder_pid", proc.pid),
        "holder_instance_id": state.get("holder_instance_id"),
        "agent_pid": state.get("agent_pid"),
        "acp_session_id": state.get("acp_session_id"),
        "state": state.get("state"),
    })
    attach_binding_fact(receipt, state)
    receipt["transport"]["protocol_version"] = state.get("protocol_version")
    receipt["transport"]["agent_info"] = state.get("agent_info")
    if "cli_version" in state:
        receipt["transport"]["cli_version"] = state["cli_version"]
    receipt["transport"]["capabilities"] = state.get("capabilities")
    if state.get("fatal_error"):
        receipt["error"] = state["fatal_error"]
        receipt["mutation_status"] = "not_started"
        receipt["mutation_performed"] = False
    elif state.get("state") != "ready":
        receipt["error"] = {"code": "start-incomplete", "state": state.get("state")}
    else:
        configured = []
        policy = resolve_selection(args, repo)
        merge_policy_evidence(receipt, policy)
        resolved_model = policy.get("resolved_runtime_model_id") or ""
        resolved_effort = (policy.get("resolved_parameters") or {}).get("effort") or ""
        # ACP option values can differ from PTY picker IDs for the same model.
        # ``acp_model_map`` decomposes a resolved picker ID onto the ACP model
        # value for the same model — effort and fast then travel through their
        # own advertised config options, so semantics are never substituted.
        acp_model_map = parse_acp_model_map(args.manifest.get("acp_model_map") or "")
        acp_model_value = acp_model_map.get(resolved_model, resolved_model)
        # A mapped picker ID carries its effort in the ID suffix; when the
        # caller supplied no explicit effort the suffix preserves it through
        # the effort option. A bare unmapped model gets no invented effort.
        effort_value = resolved_effort or (
            picker_effort_suffix(resolved_model) if resolved_model in acp_model_map else ""
        )
        host_required = args.platform == "zcode" and zcode_host_session(args.session)
        if host_required:
            # Issue #108: a Host's selection is a dispatch requirement, so the
            # pin always lands the canonical pair — an absent request takes it
            # and a matching explicit request resolves to the same values; a
            # contradicting explicit request was refused before the spawn.
            acp_model_value = ZCODE_HOST_MODEL_ID
            effort_value = ZCODE_HOST_EFFORT
        application: dict[str, Any] = {}
        mode_value = args.mode or ACP_SKIP_MODE.get(args.platform)
        # A platform whose option values are not the Runner permission-mode
        # names (droid: autonomy_level) translates before sending; unknown
        # values pass through so the agent's rejection stays a limitation.
        if args.platform in ACP_MODE_VALUE_MAP:
            mode_value = ACP_MODE_VALUE_MAP[args.platform].get(mode_value, mode_value)
        # Model first, then effort, then Fast — the ACP config order the
        # upstream adapter expects.
        option_pairs = [
            ("model", acp_model_value, "acp_model_config_id"),
            ("effort", effort_value, "acp_effort_config_id"),
        ]
        for label, value, key in option_pairs:
            if not value:
                application[label] = {"applied": False, "reason": "no-resolved-value"}
                continue
            config_id = args.manifest.get(key or "")
            if not config_id:
                application[label] = {
                    "applied": False,
                    "reason": "no-advertised-config-option",
                    "manifest_key": key,
                    "value": value,
                }
                continue
            result = socket_request(sock, "set_config_option", {"config_id": config_id, "value": value}, 20.0)
            record: dict[str, Any] = {"applied": not result.get("error"),
                                      "config_id": config_id, "value": value}
            if label == "model":
                if resolved_model and value != resolved_model:
                    record["requested_id"] = resolved_model
                    record["mapped"] = True
                declared = acp_value_params(value)
                if declared:
                    record["declared"] = declared
            if result.get("error"):
                # A rejected option is a limitation receipt, not a session
                # failure — the agent stays usable on its own selection.
                record["error"] = result["error"]
                application[label] = record
                continue
            configured.append(result)
            application[label] = record
        # Fast rides the native config option when the agent advertises one;
        # model-variant platforms carry it in the resolved model ID instead.
        fast_id = args.manifest.get("acp_fast_config_id") or ""
        if "error" not in receipt:
            if fast_id:
                # Fast intent follows the resolved selection: an explicit
                # fast-variant model ID asserts on by identity; otherwise the
                # --fast flag decides. Values convert per platform
                # (acp_fast_values: Cursor true/false, Codex on/off).
                resolved_fast_state = policy.get("resolved_fast")
                fast_intent = (
                    resolved_fast_state
                    if resolved_fast_state in ("on", "off")
                    else args.fast
                )
                fast_value = parse_manifest_value_map(
                    args.manifest.get("acp_fast_values") or ""
                ).get(fast_intent, fast_intent)
                result = socket_request(
                    sock, "set_config_option",
                    {"config_id": fast_id, "value": fast_value}, 20.0,
                )
                if result.get("error"):
                    application["fast"] = {"applied": False, "config_id": fast_id,
                                           "value": fast_value, "error": result["error"]}
                    # Rejected: native fast state is unproven — report unknown,
                    # never the resolved intent as if it had taken effect.
                    receipt["fast"] = fast_report(
                        args, policy, "acp-config", False,
                        detail="fast config option rejected",
                        effective="unknown",
                    )
                else:
                    configured.append(result)
                    application["fast"] = {"applied": True, "config_id": fast_id,
                                           "value": fast_value}
                    receipt["fast"] = fast_report(
                        args, policy, "acp-config", True,
                        effective="on" if fast_intent == "on" else "off",
                    )
            else:
                model_applied = application.get("model", {}).get("applied") is True
                declared = acp_value_params(acp_model_value) if model_applied else {}
                declared_fast = declared.get("fast")
                if declared_fast in ("true", "false"):
                    # The applied model value itself declares a fast tier
                    # (Cursor-style [..,fast=true]) — that descriptor is the
                    # native evidence for what is effective.
                    effective = "on" if declared_fast == "true" else "off"
                    application["fast"] = {
                        "applied": declared_fast == "true",
                        "via": "model-id",
                        "declared_fast": declared_fast,
                    }
                    receipt["fast"] = fast_report(
                        args, policy, "model-id", declared_fast == "true",
                        detail=f"applied model value declares fast={declared_fast}",
                        effective=effective,
                    )
                    if args.fast != effective:
                        receipt["fast"]["conflict"] = (
                            f"requested --fast {args.fast}; applied model value "
                            f"declares fast={declared_fast} and ACP exposes no "
                            "separate fast toggle"
                        )
                elif model_applied and any(
                    resolved_model.endswith(suffix) for suffix in FAST_VARIANT_SUFFIXES
                ):
                    application["fast"] = {"applied": True, "via": "model-id"}
                    receipt["fast"] = fast_report(args, policy, "model-id", True)
                elif not model_applied and any(
                    resolved_model.endswith(suffix) for suffix in FAST_VARIANT_SUFFIXES
                ):
                    # A fast-variant ID was resolved but the model option failed
                    # — fast was never applied; native state is unproven.
                    application["fast"] = {
                        "applied": False,
                        "reason": "model-config-not-applied",
                    }
                    receipt["fast"] = fast_report(
                        args, policy, "model-id", False,
                        detail="fast model ID resolved but model option was not applied",
                        effective="unknown",
                    )
                else:
                    application["fast"] = {"applied": False, "reason": "no-advertised-config-option"}
                    receipt["fast"] = fast_report(args, policy, "none", False)
        if args.platform == "dsh":
            value, source = dsh_permission_mode(args)
            application["mode"] = {"applied": True, "applied_via": "env",
                                   "env": DSH_PERMISSION_ENV, "value": value,
                                   "source": source}
            mode_value = None
        if mode_value and "error" not in receipt:
            # The mode/permission option id is a per-platform manifest fact
            # (``acp_mode_config_id``): droid's autonomy option is
            # ``autonomy_level``, the other ACP-mode platforms advertise
            # ``mode``, and an empty value means the agent exposes no ACP
            # mode config option at all.
            config_id = args.manifest.get("acp_mode_config_id") or ""
            if not config_id:
                application["mode"] = {"applied": False, "reason": "no-advertised-config-option"}
                if args.mode:
                    receipt["error"] = {"code": "config-option-unavailable", "manifest_key": None}
            else:
                result = socket_request(sock, "set_config_option", {"config_id": config_id, "value": mode_value}, 20.0)
                if result.get("error"):
                    application["mode"] = {"applied": False, "config_id": config_id,
                                           "value": mode_value, "error": result["error"]}
                    receipt["error"] = result["error"]
                else:
                    configured.append(result)
                    application["mode"] = {"applied": True, "config_id": config_id,
                                           "value": mode_value}
        if configured:
            receipt["configured_options"] = configured
        receipt["config_application"] = application
        receipt.setdefault("fast", fast_report(args, policy, "none", False))
        # Issue #119 (H2): what the agent itself now reports, for every start.
        effective = effective_selection(args.manifest, socket_request(sock, "state", {}, 10.0))
        receipt["effective_selection"] = effective
        explicit_model = acp_model_value if args.model else ""
        explicit_effort = effort_value if args.effort else ""
        problem = (explicit_selection_problem(explicit_model, explicit_effort, effective)
                   if args.platform in EXPLICIT_SELECTION_VERIFIED else None)
        if problem is not None:
            receipt.pop("error", None)
            receipt.update({
                "result": "refused",
                "reason": "explicit-selection-unverified",
                "action": "start",
                "detail": (f"the {args.platform} agent did not report the explicit "
                           f"selection: {problem}; the session was stopped before this "
                           "start returned, and no other model was substituted."),
                **stop_started_holder(sock, proc),
                "mutation_performed": False,
                "mutation_status": "not_started",
            })
            return receipt
        if host_required:
            # Issue #108: the pin is only real once the agent's own advertised
            # state agrees — a rejected or silently ignored set must never
            # leave a wrong-model Host running, so an unverifiable selection
            # stops the just-created session and refuses.
            verified_state = socket_request(sock, "state", {}, 10.0)
            effective_model, effective_effort = zcode_host_config_state(
                verified_state if isinstance(verified_state, dict) else {})
            host_fact = zcode_host_selection_fact(
                args, acp_model_value, effort_value,
                effective_model, effective_effort)
            receipt["host_selection"] = host_fact
            if not host_fact["verified"]:
                stopped = stop_started_holder(sock, proc)
                receipt.pop("error", None)
                receipt.update({
                    "result": "refused",
                    "reason": "host-model-unverified",
                    "action": "start",
                    "detail": (
                        f"a ZCode Host session ({args.session}) must run "
                        f"{ZCODE_HOST_MODEL_ID} at effort {ZCODE_HOST_EFFORT}; "
                        "the applied session did not report it, so it was "
                        "stopped before this start returned."
                    ),
                    **stopped,
                    "mutation_performed": False,
                    "mutation_status": "not_started",
                })
                return receipt
    return receipt


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        payload = command_list(parse_list_args(sys.argv[2:]))
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return 0

    parser = argparse.ArgumentParser(prog="kaola-acp.py")
    parser.add_argument("platform", choices=PLATFORMS)
    parser.add_argument("command", choices=[
        "preflight", "start", "send", "steer", "wait", "observe", "capture",
        "permit", "key", "answer", "cancel", "stop", "status", "view",
        "follow",
    ])
    parser.add_argument("--repo", required=True)
    parser.add_argument("--session")
    parser.add_argument("--command", dest="agent_command")
    parser.add_argument("--record-root")
    parser.add_argument("--resume")
    parser.add_argument("--continue", dest="use_continue", action="store_true")
    parser.add_argument("--text")
    parser.add_argument("--stdin", action="store_true")
    parser.add_argument("--wait", dest="wait", action="store_true", default=True)
    parser.add_argument("--no-wait", dest="wait", action="store_false")
    parser.add_argument("--timeout", type=float)
    parser.add_argument("--max-final-chars", type=int, default=4000)
    parser.add_argument("--request-id")
    parser.add_argument("--option")
    parser.add_argument("--expected-holder-instance-id")
    parser.add_argument("--key")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--lines", type=int)
    parser.add_argument("--tools", action="store_true")
    parser.add_argument("--since", type=int)
    parser.add_argument("--format", choices=("json", "text"), default="json")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--inline", action="store_true")
    parser.add_argument("--model")
    parser.add_argument("--effort")
    # Issue #111: validated against the manifest after it loads, so an
    # undeclared third tier answers a typed refusal instead of argparse exit 2.
    parser.add_argument("--tier")
    parser.add_argument("--fast", choices=("on", "off"), default="off")
    parser.add_argument("--mode")
    parser.add_argument("--steer-mode", choices=("native", "interrupt"))
    parser.add_argument("--cancel-timeout", type=float)
    parser.add_argument("--transport-reason", choices=("manifest-default", "caller-override"), default="manifest-default")
    args = parser.parse_args()

    args.manifest = load_manifest(args.platform)
    repo = resolve_repo(args.repo)
    if not tier_declared(args.manifest, args.tier):
        print(json.dumps(tier_refusal(args, repo), ensure_ascii=False, sort_keys=True))
        return 1
    if args.command != "preflight":
        if not args.session or not SESSION_PATTERN.match(args.session):
            die("invalid or missing --session name")
    if (args.platform == "dsh" and args.command == "start" and args.mode
            and dsh_permission_mode(args)[0] not in DSH_PERMISSION_MODES):
        die(f"--mode for dsh must be one of {', '.join(DSH_PERMISSION_MODES)} "
            "or bypassPermissions")
    args.agent_command = (
        args.agent_command
        or os.environ.get("KAOLA_ACP_COMMAND")
        or args.manifest["acp_command"]
    )
    if not args.agent_command:
        die(f"no ACP command for platform {args.platform} (use --command)")
    args.agent_command, args.agent_command_facts = resolve_agent_command(args.agent_command)

    directory = record_dir(args, repo) if args.session else None

    if args.command == "preflight":
        receipt = command_preflight(args, repo)
        print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
        return 0
    if args.command == "start":
        receipt = command_start(args, repo)
        print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
        # A typed refusal is a pre-mutation decision, exit 1 like the shell's
        # canonical-root refusal; transport errors stay exit-0 receipts.
        return 1 if receipt.get("result") == "refused" else 0
    if args.command == "view":
        if directory is None:
            die("invalid or missing --session name")
        receipt = command_view(args, repo, directory)
        print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
        return 0
    if args.command == "follow":
        if directory is None:
            die("invalid or missing --session name")
        return command_follow(args, repo, directory)

    timeout = args.timeout
    sock_timeout = (timeout + 30.0) if timeout else None

    if args.command == "send":
        text = args.text
        if args.stdin:
            text = sys.stdin.read()
        if not text:
            die("send requires --text or --stdin")
        receipt = op_or_holder_lost(
            args, repo, directory, "prompt",
            {"text": text, "wait": args.wait, "timeout": timeout,
             "max_final_chars": args.max_final_chars},
            sock_timeout,
        )
    elif args.command == "steer":
        text = args.text
        if args.stdin:
            text = sys.stdin.read()
        if not text:
            die("steer requires --text or --stdin")
        # Issue #65: the manifest carries the platform's investigated ACP
        # capability and its entry. `unsupported` and `unknown` are different
        # answers and must not collapse: only a platform investigated to have no
        # entry gets `unsupported`; an undetermined one stays `unknown`.
        method = (args.manifest.get("acp_steer_method") or "").strip()
        native_steering = args.manifest.get("native_steering") or "unknown"
        # Issue #88: the codes and outcomes already separate `unknown` from
        # `unsupported`; the human-readable text must too. An unverified surface
        # is not a proven absence, so it never reads as one.
        unverified = native_steering == "unknown"
        # Each call site keeps its own `unsupported` wording byte-for-byte; only
        # the `unknown` case is reworded.
        exposes_no_entry = ("has no verified native mid-turn steering entry" if unverified
                            else "exposes no native mid-turn steering entry")
        has_no_entry = ("has no verified native mid-turn steering entry" if unverified
                        else "has no native mid-turn steering entry")
        unverified_note = (
            " No probe has settled this version, so absence is not established."
            if unverified else ""
        )
        mode = args.steer_mode or ("native" if method else None)

        if mode == "interrupt":
            # Composite: cancel the running turn, confirm it stopped, then send
            # the text once as the next turn on the SAME session. The Agent asked
            # for this by name; the Runner never selects it on its own.
            receipt = op_or_holder_lost(
                args, repo, directory, "steer_interrupt",
                {"text": text, "timeout": timeout, "cancel_timeout": args.cancel_timeout},
                sock_timeout,
            )
            receipt.setdefault("native_steering", native_steering)
            receipt.setdefault("steer_mode", "interrupt")
            error = receipt.get("error") or {}
            if error.get("code") == "unknown-op":
                receipt.update(holder_predates_steer(method or "cancel+prompt", error))
        elif mode is None:
            # No native entry here, and no explicit choice: refuse rather than
            # degrade. Nothing is written; the Agent picks the semantics.
            receipt = base_receipt(args, repo)
            receipt.update({
                "steer_outcome": "unknown" if native_steering == "unknown" else "unsupported",
                "steer_consumed": False,
                "steer_confirmation": "none",
                "steer_method": None,
                "steer_mode": None,
                "native_steering": native_steering,
                "available_steer_modes": ["interrupt"],
                "mutation_status": "not_started",
                "mutation_performed": False,
                "error": {
                    "code": "steer-mode-required",
                    "message": (
                        f"{args.platform} {exposes_no_entry} on its ACP "
                        f"surface (native_steering={native_steering}); nothing was written."
                        f"{unverified_note} "
                        "The available path is the composite `--steer-mode interrupt`: it "
                        "CANCELS the running turn, confirms it stopped, then sends this text as "
                        "the next turn on the same session, keeping the conversation's context. "
                        "That interrupts work in progress and can leave partial side effects, so "
                        "the Runner will not choose it for you"
                    ),
                },
            })
        elif not method:
            # `--steer-mode native` on a platform that has no native entry.
            receipt = base_receipt(args, repo)
            receipt.update({
                "steer_outcome": "unknown" if native_steering == "unknown" else "unsupported",
                "steer_consumed": False,
                "steer_confirmation": "none",
                "steer_method": None,
                "steer_mode": "native",
                "native_steering": native_steering,
                "available_steer_modes": ["interrupt"],
                "mutation_status": "not_started",
                "mutation_performed": False,
                "error": {
                    "code": "steer-capability-unknown" if native_steering == "unknown"
                    else "steer-unsupported",
                    "message": (
                        f"{args.platform} {has_no_entry} on the ACP "
                        f"channel (native_steering={native_steering}); nothing was written."
                        f"{unverified_note} "
                        "Use `--steer-mode interrupt` for the composite path"
                    ),
                },
            })
        else:
            receipt = op_or_holder_lost(
                args, repo, directory, "steer",
                {"text": text, "method": method, "timeout": timeout},
                sock_timeout,
            )
            receipt.setdefault("native_steering", native_steering)
            receipt.setdefault("steer_mode", "native")
            error = receipt.get("error") or {}
            if error.get("code") == "unknown-op":
                receipt.update(holder_predates_steer(method, error))
    elif args.command == "wait":
        receipt = op_or_holder_lost(
            args, repo, directory, "wait", {"timeout": timeout}, sock_timeout
        )
    elif args.command in ("observe", "status"):
        receipt = op_or_holder_lost(args, repo, directory, "state", {}, 10.0)
        record = read_record(directory)
        if record:
            receipt.setdefault("record", record)
        # Only a session that exists has a binding to report; ``no-session``
        # stays silent rather than answering "unknown" about nothing.
        if record is not None or "heartbeat_host" in receipt:
            attach_binding_fact(
                receipt, receipt if "heartbeat_host" in receipt else record
            )
        receipt = bound_state_receipt(receipt)
    elif args.command == "capture":
        receipt = op_or_holder_lost(
            args, repo, directory, "capture",
            {"tools": args.tools, "since": args.since, "full": args.full,
             "lines": args.lines, "inline": args.inline},
            15.0,
        )
        if not args.full:
            receipt = bound_capture_receipt(receipt)
    elif args.command == "permit":
        params: dict[str, Any] = {"request_id": args.request_id, "option": args.option}
        if args.expected_holder_instance_id is not None:
            params["expected_holder_instance_id"] = args.expected_holder_instance_id
        receipt = op_or_holder_lost(
            args, repo, directory, "permit", params, 10.0,
        )
    elif args.command == "cancel":
        params = {"timeout": timeout}
        if args.expected_holder_instance_id is not None:
            params["expected_holder_instance_id"] = args.expected_holder_instance_id
        receipt = op_or_holder_lost(
            args, repo, directory, "cancel", params, sock_timeout
        )
    elif args.command == "key":
        if args.key != "escape":
            receipt = base_receipt(args, repo)
            receipt["error"] = {"code": "key-unsupported",
                                "message": "acp transport supports only escape→cancel"}
        else:
            params = {"timeout": timeout}
            if args.expected_holder_instance_id is not None:
                params["expected_holder_instance_id"] = args.expected_holder_instance_id
            receipt = op_or_holder_lost(
                args, repo, directory, "cancel", params, sock_timeout
            )
    elif args.command == "answer":
        receipt = base_receipt(args, repo)
        receipt["error"] = {"code": "answer-unsupported",
                            "message": "use send; --decision-id maps to permit --request-id"}
    elif args.command == "stop":
        # Issue #73: a stop is bound to the exact holder instance the Agent
        # verified, so a same-named session rebuilt by a later instance is
        # refused instead of stopped.
        params = {"force": args.force}
        if args.expected_holder_instance_id is not None:
            params["expected_holder_instance_id"] = args.expected_holder_instance_id
        receipt = op_or_holder_lost(
            args, repo, directory, "stop", params, 30.0
        )
    else:
        die(f"unhandled command {args.command}")
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
