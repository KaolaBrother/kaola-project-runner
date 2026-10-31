#!/usr/bin/env python3
"""Runner v2 ACP transport CLI for the PoC (issue #15).

Thin socket client: every command talks to the per-session holder process
(``kaola-acp-holder.py``) over ``holder.sock`` with newline-delimited JSON.
Receipts are ``schema_version: 3`` JSON on stdout; fact errors ride inside the
receipt as ``error: {code, message}``; usage errors also return JSON and exit non-zero.
"""

from __future__ import annotations

import argparse
import calendar
import contextlib
import ctypes
import getpass
import hashlib
import importlib.util
import json
import os
import pwd
import re
import secrets
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, NamedTuple

# Issue #278: shared paths also ship beside every generated worker Runner.
_paths_spec = importlib.util.spec_from_file_location(
    "kaola_acp_paths", Path(__file__).resolve().with_name("kaola-acp-paths.py"))
acp_paths = importlib.util.module_from_spec(_paths_spec)
_paths_bytecode = sys.dont_write_bytecode
sys.dont_write_bytecode = True
try:
    _paths_spec.loader.exec_module(acp_paths)
finally:
    sys.dont_write_bytecode = _paths_bytecode


def _load_recovery_routes():
    """Issue #309. A partial script copy without the table still returns the old receipt."""
    cached = getattr(_load_recovery_routes, "module", None)
    if cached is not None:
        return cached or None
    path = Path(__file__).resolve().with_name("kaola-recovery-routes.py")
    if not path.is_file():
        _load_recovery_routes.module = False
        return None
    spec = importlib.util.spec_from_file_location("kaola_recovery_routes", path)
    if spec is None or spec.loader is None:
        _load_recovery_routes.module = False
        return None
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    _load_recovery_routes.module = module
    return module


def _stamp_recovery(payload: dict[str, Any]) -> dict[str, Any]:
    module = _load_recovery_routes()
    if module is None or not isinstance(payload, dict):
        return payload
    return module.stamp(payload)


def _emit_receipt(payload: dict[str, Any]) -> None:
    """Print one receipt. Stamp a copy so a stored object stays unchanged."""
    if isinstance(payload, dict):
        payload = certify_test_lane_receipt(payload)
    printed = payload
    module = _load_recovery_routes()
    if module is not None and isinstance(payload, dict):
        printed = dict(payload)
        lost = printed.get("holder_lost")
        if isinstance(lost, dict):
            printed["holder_lost"] = dict(lost)
        printed = module.stamp(printed)
    print(json.dumps(printed, ensure_ascii=False, sort_keys=True))


# Issue #422. sha256 of the empty byte string. The noop receipts that certified
# pass had this digest on both stdout and stderr: the test binary never ran.
EMPTY_OUTPUT_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
# Observed noop receipts were 7–9 ms. A one-test unittest on this machine
# measured about 28–44 ms and ``python3 -c "print('ok')"`` about 15 ms, both
# with real output. Any floor that sits above 7–9 ms also sits inside that
# fast-lane band, so the floor refuses only when stdout and stderr are both
# empty. A lane that produced output still certifies. 50 ms is above the
# noop band with margin for timer granularity and is recorded on the refusal.
TEST_LANE_MIN_DURATION_MS = 50
_PASS_OUTCOMES = frozenset({"pass", "passed", "ok"})


def _declared_test_lane(receipt: dict[str, Any]) -> str | None:
    """The lane name when this receipt is a declared test lane, else None."""
    lane = receipt.get("test_lane")
    if isinstance(lane, str) and lane.strip():
        return lane.strip()
    if receipt.get("kind") == "test-lane":
        named = receipt.get("lane")
        if isinstance(named, str) and named.strip():
            return named.strip()
        return "test-lane"
    return None


def _parse_sha256(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip().lower()
    if text.startswith("sha256:"):
        text = text[7:]
    if len(text) == 64 and all(char in "0123456789abcdef" for char in text):
        return text
    return None


def _stream_sha256(receipt: dict[str, Any], raw_key: str, sha_key: str) -> str:
    """Sha256 of one stream. Missing output is the empty digest."""
    if raw_key in receipt and receipt[raw_key] is not None:
        raw = receipt[raw_key]
        if isinstance(raw, str):
            return hashlib.sha256(raw.encode("utf-8")).hexdigest()
        return EMPTY_OUTPUT_SHA256
    for key in (sha_key, raw_key + "_sha"):
        parsed = _parse_sha256(receipt.get(key))
        if parsed is not None:
            return parsed
    return EMPTY_OUTPUT_SHA256


def _exit_code(receipt: dict[str, Any]) -> int | None:
    for key in ("exit_code", "exit"):
        if key not in receipt or receipt[key] is None:
            continue
        value = receipt[key]
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            return value
        if isinstance(value, float) and value.is_integer():
            return int(value)
        if isinstance(value, str) and value.strip().lstrip("-").isdigit():
            return int(value.strip())
    return None


def _duration_ms(receipt: dict[str, Any]) -> int | float | None:
    """Milliseconds from ``duration_ms`` or ``duration``. Both are milliseconds."""
    for key in ("duration_ms", "duration"):
        if key not in receipt or receipt[key] is None:
            continue
        value = receipt[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        if isinstance(value, float) and value.is_integer():
            return int(value)
        return value
    return None


def _claims_pass(receipt: dict[str, Any]) -> bool:
    outcome = receipt.get("outcome")
    if isinstance(outcome, str) and outcome.lower() in _PASS_OUTCOMES:
        return True
    return outcome in (None, "") and _exit_code(receipt) == 0


def certify_test_lane_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    """Certify a declared test lane, or refuse it closed.

    A receipt declares a lane with ``test_lane`` or ``kind`` ``test-lane``.
    Any other receipt is returned unchanged. Exit 0 is never proof the suite
    ran. Empty stdout and empty stderr refuse certification. A duration under
    ``TEST_LANE_MIN_DURATION_MS`` refuses only together with that empty output,
    and the refusal records the sha and the duration that were seen. The
    error code is ``noop-test-lane``. The caller's object is left unchanged.
    """
    if not isinstance(receipt, dict):
        return receipt
    lane = _declared_test_lane(receipt)
    if lane is None or not _claims_pass(receipt):
        return receipt
    stdout_sha = _stream_sha256(receipt, "stdout", "stdout_sha256")
    stderr_sha = _stream_sha256(receipt, "stderr", "stderr_sha256")
    duration = _duration_ms(receipt)
    exit_code = _exit_code(receipt)
    empty = stdout_sha == EMPTY_OUTPUT_SHA256 and stderr_sha == EMPTY_OUTPUT_SHA256
    checks: list[str] = []
    if empty:
        checks.append("empty-output")
    if empty and duration is not None and duration < TEST_LANE_MIN_DURATION_MS:
        checks.append("sub-floor-duration")
    certified = dict(receipt)
    certified["test_lane"] = lane
    certified["stdout_sha256"] = stdout_sha
    certified["stderr_sha256"] = stderr_sha
    certified["exit_code"] = exit_code
    if duration is not None:
        certified["duration_ms"] = duration
    if not checks:
        certified["outcome"] = "pass"
        certified["result"] = "pass"
        certified.pop("error", None)
        return certified
    evidence = {
        "test_lane": lane,
        "exit_code": exit_code,
        "stdout_sha256": stdout_sha,
        "stderr_sha256": stderr_sha,
        "duration_ms": duration,
        "min_duration_ms": TEST_LANE_MIN_DURATION_MS,
        "checks": checks,
    }
    certified["outcome"] = "refused"
    certified["result"] = "refused"
    certified["reason"] = "noop-test-lane"
    certified["error"] = {
        "code": "noop-test-lane",
        "message": (
            f"test lane {lane} was not certified ({', '.join(checks)}); "
            f"stdout_sha256={stdout_sha} stderr_sha256={stderr_sha} "
            f"duration_ms={duration} exit_code={exit_code}. "
            "Exit 0 is not proof the suite ran."
        ),
        "evidence": evidence,
    }
    return certified


def _load_session_names():
    """Issue #313. A copy without the helper still starts; the advisory is absent."""
    cached = getattr(_load_session_names, "module", None)
    if cached is not None:
        return cached or None
    path = Path(__file__).resolve().with_name("kaola-session-names.py")
    if not path.is_file():
        _load_session_names.module = False
        return None
    spec = importlib.util.spec_from_file_location("kaola_session_names", path)
    if spec is None or spec.loader is None:
        _load_session_names.module = False
        return None
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.dont_write_bytecode = previous
        _load_session_names.module = False
        return None
    sys.dont_write_bytecode = previous
    _load_session_names.module = module
    return module


def stamp_issue_name_receipt(receipt: dict[str, Any], platform: str, session: str,
                             repo: str) -> dict[str, Any]:
    """Add the Issue #313 advisory. Never changes the start result.

    Issue-named workers get ``issue_name`` (ok, malformed,
    platform-token-mismatch, or no-active-run) and ``name_role`` worker.
    A host, sideagent, seat, or general name omits ``issue_name`` and sets
    ``name_role`` to that role. A missing helper or a lookup error leaves
    the receipt unchanged. The list schema stays ``kaola-acp-list/1``.
    A null ``agent_alive`` stays unknown.
    """
    module = _load_session_names()
    if module is None or not isinstance(receipt, dict):
        return receipt
    if not isinstance(platform, str) or not isinstance(session, str) or not isinstance(repo, str):
        return receipt
    try:
        advice = module.advise(session, platform, repo)
    except Exception:
        return receipt
    role = advice.get("name_role")
    if role in module.NAME_ROLES:
        receipt["name_role"] = role
    issue_name = advice.get("issue_name")
    if issue_name in module.ISSUE_NAME_VALUES:
        receipt["issue_name"] = issue_name
    return receipt


SCRIPT_DIR = Path(__file__).resolve().parent
HOLDER = SCRIPT_DIR / "kaola-acp-holder.py"
LAUNCH_BROKER = SCRIPT_DIR / "kaola-launchd-broker.py"
MODEL_POLICY_HELPER = SCRIPT_DIR / "kaola-model-policy.py"
FAST_VARIANT_SUFFIXES = ("-fast", "-priority")
SESSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")
# Session identity: sidekick is the legacy Sideagent value; never rewrite live records.
SESSION_ROLES = frozenset({"host", "sideagent", "sidekick", "expert", "elite", "worker"})
PLATFORMS = (
    "antigravity", "claude-code", "codex", "cursor-cli", "devin", "droid", "dsh", "grok", "hermes",
    "kimi-cli", "opencode", "zcode",
)
START_WAIT = 20.0
# Issue #146: the holder's shared session/new wait. A manifest
# `acp_session_new_timeout` raises it per platform, and the start window and
# preflight probe bound grow by the same amount so they still enclose it.
SESSION_NEW_TIMEOUT = 15.0
SESSION_NEW_TIMEOUT_MAX = 600.0
# Issue #308: resume/load wait. An explicit KAOLA_RESUME_TIMEOUT wins. Otherwise
# the session/new wait grows by KAOLA_RESUME_TOKENS/10000, capped here. The
# client keeps polling RESUME_RECOVERY_GRACE seconds after that wait so a late
# load success can clear a resume-failed record.
RESUME_TIMEOUT_MAX = 600.0
RESUME_RECOVERY_GRACE = 20.0
PROBE_WAIT = 60.0
SESSION_PREFIX = "kaola"
# Issue #22: default start sets session/set_config_option configId=mode to each
# platform's measured skip-all value. Omitted platforms have no ACP mode skip
# (Grok: agent always-approve; Cursor/OpenCode: no skip-shaped mode value).
# Devin ACP `bypass` is not the PTY argv `dangerous`.
ACP_SKIP_MODE = {
    # Headless agy has no approval prompt and soft-denies shell commands, so the
    # skip-all default is the one --dangerously-skip-permissions flag (#323).
    "antigravity": "bypassPermissions",
    "claude-code": "bypassPermissions",
    "codex": "agent-full-access",
    "devin": "bypass",
    "droid": "auto-high",
    # Issue #416: Hermes `acp_adapter/modes.py` (source-read) offers
    # default=ask, accept_edits=workspace_session, dont_ask=session; dont_ask
    # is the most permissive edit approval (sensitive paths still ask) and
    # matches the `--yolo` launch. #417 confirms live.
    "hermes": "dont_ask",
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


def _dsh_safe_unit(ch: str) -> bool:
    return ch != "~" and ch.isascii() and (ch.isalnum() or ch in "._-")


def dsh_project_key(cwd: str) -> str:
    """The dsh session-store project directory name for a workspace path.

    Mirrors ``projectKey`` in ``@deepseek-ai/dsh-session-persistence-jsonl``:
    runs of ``/``, ``\\`` and ``:`` collapse to one dash, safe units stay
    literal, every other code unit becomes ``~XXXX``, leading dashes are
    dropped and the result is wrapped in ``--…--`` (truncated to 251).
    """
    readable = ""
    separator_run = False
    for ch in cwd:
        if ch in "/\\:":
            if not separator_run:
                readable += "-"
            separator_run = True
        elif _dsh_safe_unit(ch):
            readable += ch
            separator_run = False
        else:
            readable += f"~{ord(ch):04X}"
            separator_run = False
    return "--" + (readable.lstrip("-") or "root")[:251] + "--"


def dsh_path_segment(raw: str) -> str:
    """``encodeSegment`` from the same module: ``.``/``..`` and unsafe units
    become ``~XXXX`` escapes; everything safe stays literal."""
    if raw == ".":
        return "~002E"
    if raw == "..":
        return "~002E~002E"
    return "".join(ch if _dsh_safe_unit(ch) else f"~{ord(ch):04X}" for ch in raw)


def _dsh_log_version(path: Path) -> int | None:
    match = re.fullmatch(r"session(?:\.v(\d+))?\.jsonl(?:\.zstd)?", path.name)
    return int(match.group(1) or 0) if match else None


def _dsh_zstd_stdlib(data: bytes) -> str | None:
    try:
        from compression import zstd  # Python >= 3.14
        return zstd.decompress(data).decode("utf-8", "replace")
    except Exception:
        return None


def _dsh_zstd_module(data: bytes) -> str | None:
    try:
        import io
        import zstandard
        reader = zstandard.ZstdDecompressor().stream_reader(io.BytesIO(data))
        try:
            return reader.read().decode("utf-8", "replace")
        finally:
            reader.close()
    except Exception:
        return None


def _dsh_zstd_cli(path: Path) -> str | None:
    binary = shutil.which("zstd")
    if binary is None:
        return None
    try:
        out = subprocess.run([binary, "-dc", "--", str(path)],
                             capture_output=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.decode("utf-8", "replace")


def _dsh_log_text(path: Path) -> str | None:
    """The decoded text of one dsh session log, or None when unreadable.

    dsh writes size-less streaming zstd frames, so each decoder that exists
    but fails falls through to the next; none of them fabricating text is
    what keeps an unreadable log honest.
    """
    if path.suffix != ".zstd":
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None
    try:
        data = path.read_bytes()
    except OSError:
        return None
    for decode in (_dsh_zstd_stdlib, _dsh_zstd_module):
        text = decode(data)
        if text is not None:
            return text
    return _dsh_zstd_cli(path)


def dsh_session_permission(repo: str, session_id: Any) -> dict[str, Any] | None:
    """The permission facts a resumed dsh session actually keeps (Issue #363).

    dsh pins ``permission/preset``, ``sandbox/mode`` and ``approval/policy``
    into the session log at creation, and ``pinInitialPermission`` keeps the
    recorded values on resume, so the last occurrence of each is the
    effective one. ``None`` when the log is absent or unreadable — an
    unreadable log never fabricates a value.
    """
    if not isinstance(session_id, str) or not session_id:
        return None
    home = os.environ.get("DSH_HOME") or str(Path.home() / ".dsh")
    # dsh records the resolved cwd (a /tmp birth lands under --private-tmp-…).
    directory = Path(home) / "sessions" / dsh_project_key(os.path.realpath(repo)) / dsh_path_segment(session_id)
    try:
        candidates = sorted(
            (path for path in directory.iterdir() if _dsh_log_version(path) is not None),
            key=lambda path: _dsh_log_version(path) or 0, reverse=True)
    except OSError:
        return None
    for path in candidates:
        text = _dsh_log_text(path)
        if text is None:
            continue
        found: dict[str, Any] = {"session_log": str(path)}
        for line in text.splitlines():
            try:
                event = json.loads(line)
            except ValueError:
                continue
            data = event.get("data") if isinstance(event, dict) else None
            if not isinstance(data, dict):
                continue
            if event.get("type") == "permission/preset" \
                    and isinstance(data.get("preset"), str):
                found["preset"] = data["preset"]
            elif event.get("type") == "sandbox/mode" \
                    and isinstance(data.get("mode"), str):
                found["sandbox"] = data["mode"]
            elif event.get("type") == "approval/policy" \
                    and isinstance(data.get("policy"), str):
                found["approval"] = data["policy"]
        if "preset" in found or "sandbox" in found or "approval" in found:
            return found
    return None

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
    "antigravity": "AGY_BIN",
    "claude-code": "CLAUDE_ACP_CLAUDE_BIN",
    "opencode": "OPENCODE_BIN",
    "dsh": "DSH_BIN",
    "hermes": "HERMES_BIN",
}
# Issue #124: platforms whose `initialize` returns no `agentInfo`, so a start
# records the launched CLI's own `--version` instead (a fact, never a gate).
CLI_VERSION_PLATFORMS = frozenset({"grok"})
# Issue #227: platforms whose manifest ACP command starts with ``binary_name``
# and must launch the same ``binary_env`` binary that preflight reports;
# otherwise a PATH ``dsh`` ran while preflight named ``$DSH_BIN``'s version.
LAUNCH_BINARY_ENV_PLATFORMS = frozenset({"dsh"})
# Issue #112: OpenCode V2 reaches its own server over loopback HTTP, so a
# forward proxy that does not exclude loopback swallows that hop and every ACP
# session method answers ClientError while `initialize` still succeeds.
# Upstream treats loopback bypass as intended (anomalyco/opencode#31096). For
# these platforms only, the child environment gains the missing loopback
# entries; the Runner's own process environment is never modified.
LOOPBACK_NO_PROXY_PLATFORMS = frozenset({"opencode"})
# Issue #435: forward proxies are omitted unless the platform opts in.
FORWARD_PROXY_ENV = ("HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy")
NO_PROXY_ENV = ("NO_PROXY", "no_proxy")
LOOPBACK_HOSTS = ("127.0.0.1", "localhost")
ZCODE_ENTRY_ENV = "KAOLA_ZCODE_ENTRY"
ZCODE_NODE_ENV = "KAOLA_ZCODE_NODE"
LOCATOR_REGISTRATION_NAME = ".kaola-project-runner-locate.json"
REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
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
    # Issue #323: no measured Host entry yet (empty fails closed, Issue #122).
    "antigravity": "",
    "claude-code": "/kaola-project-runner",
    "codex": "$kaola-project-runner",
    "cursor-cli": "/kaola-project-runner",
    "devin": "/kaola-project-runner",
    "droid": "/kaola-project-runner",
    "dsh": "/kaola-project-runner",
    "grok": "/kaola-project-runner",
    # Issue #416: Hermes is a worker platform, not a Host (empty fails closed).
    "hermes": "",
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
    "kimi-cli": (".agents/skills", ".kimi-code/skills"),
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


def zcode_path_state(path: str, *, executable: bool) -> str:
    """Why ``path`` cannot launch ZCode, or ``ok``. Never searches PATH."""
    if not path:
        return "missing"
    if not os.path.isabs(path):
        return "not-absolute"
    if not os.path.isfile(path):
        return "not-a-file"
    if executable and not os.access(path, os.X_OK):
        return "not-executable"
    return "ok"


def zcode_runtime_error() -> str | None:
    """Fail closed unless both ZCode paths are explicit, absolute, and present.

    Never searches PATH and never probes a well-known application bundle.
    """
    entry = os.environ.get(ZCODE_ENTRY_ENV) or ""
    node = os.environ.get(ZCODE_NODE_ENV) or ""
    entry_state = zcode_path_state(entry, executable=False)
    node_state = zcode_path_state(node, executable=True)
    if entry_state == "missing":
        return "no explicit ZCode entry: set KAOLA_ZCODE_ENTRY to an absolute path"
    if node_state == "missing":
        return "no explicit ZCode node runtime: set KAOLA_ZCODE_NODE to an absolute path"
    if entry_state == "not-absolute" or node_state == "not-absolute":
        return "ZCode entry and node runtime must be absolute paths"
    if entry_state == "not-a-file":
        return f"ZCode entry is not a file: {entry}"
    if node_state == "not-a-file":
        return f"ZCode node runtime is not a file: {node}"
    if node_state == "not-executable":
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


def manifest_launch_command(args: argparse.Namespace, command: str) -> str:
    """A manifest ACP command whose first word is ``binary_name``, with that
    word replaced by a set ``binary_env`` (Issue #227). --command and
    KAOLA_ACP_COMMAND never reach here; an unset ``binary_env`` keeps PATH."""
    if args.platform not in LAUNCH_BINARY_ENV_PLATFORMS or not command:
        return command
    binary = os.environ.get(args.manifest.get("binary_env") or "")
    words = shlex.split(command)
    if not binary or not words or words[0] != args.manifest.get("binary_name"):
        return command
    words[0] = binary
    return shlex.join(words)


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
    PTY child, and one contract test runs both over the same cases.

    #112's host set is exactly 127.0.0.1/localhost — the same list the shell
    adapter carries and test-issue-24 asserts. #299's IPv6 ``::1`` belongs to
    the webhook's own loopback URL classification (LOOPBACK_HOSTS), not to
    this contract."""
    hosts = ("127.0.0.1", "localhost")
    if not any(env.get(name) for name in FORWARD_PROXY_ENV):
        return {}
    names = [name for name in NO_PROXY_ENV if env.get(name)] or list(NO_PROXY_ENV)
    changes: dict[str, str] = {}
    for name in names:
        current = env.get(name) or ""
        entries = {entry.strip() for entry in current.split(",")}
        if "*" in entries:
            continue
        missing = [host for host in hosts if host not in entries]
        if not missing:
            continue
        base = current.rstrip()
        if base and not base.endswith(","):
            base += ","
        changes[name] = base + ",".join(missing)
    return changes


def codex_manifest_launch(args: argparse.Namespace) -> bool:
    """True when this Codex start uses the manifest ``acp_command``.

    ``--command`` and ``KAOLA_ACP_COMMAND`` stay caller-owned and do not gain
    the CODEX_PATH requirement. Issue #247.
    """
    if getattr(args, "platform", None) != "codex":
        return False
    if getattr(args, "agent_command_given", False):
        return False
    if os.environ.get("KAOLA_ACP_COMMAND"):
        return False
    return True


def absolute_codex_path(env: dict[str, str]) -> str:
    """An absolute ``CODEX_PATH``, or empty. A relative value is not a path."""
    path = env.get("CODEX_PATH") or ""
    return path if os.path.isabs(path) else ""


def codex_child_path(args: argparse.Namespace) -> str:
    """Keep an explicit child path; otherwise resolve the Runner runtime once."""
    if hasattr(args, "resolved_codex_child_path"):
        return args.resolved_codex_child_path
    if os.environ.get("CODEX_PATH"):
        path = os.environ["CODEX_PATH"]
    else:
        binary = runtime_binary(args.manifest)
        resolved = shutil.which(binary)
        path = os.path.abspath(resolved) if resolved else ""
    args.resolved_codex_child_path = path
    return path


def codex_child_error(args: argparse.Namespace) -> dict[str, str] | None:
    """Why a manifest Codex launch must not start, or None.

    codex-acp runs its nested ``@openai/codex`` when ``CODEX_PATH`` is unset.
    A ``codex`` entry on PATH does not change that child. The supported child
    is the explicit absolute ``CODEX_PATH`` binary, or the resolved Runner
    runtime (CODEX_BIN, then PATH). This does not read the binary's version.
    """
    if not codex_manifest_launch(args):
        return None
    path = codex_child_path(args)
    requested = (getattr(args, "manifest", None) or {}).get("acp_requested_cli") or ""
    if not path or not os.path.isabs(path):
        return {
            "code": "codex-child-path",
            "message": (
                "Cannot resolve an absolute Codex child executable "
                f"(requested Codex CLI {requested}). Set CODEX_PATH to the absolute "
                "path of an executable Codex CLI, or unset CODEX_PATH and use "
                "CODEX_BIN or PATH. For example: CODEX_PATH=/absolute/path/to/codex. "
                "The adapter's nested @openai/codex package is not used"
            ),
        }
    if not os.path.isfile(path):
        return {"code": "codex-child-path", "message": f"CODEX_PATH is not a file: {path}"}
    if not os.access(path, os.X_OK):
        return {"code": "codex-child-path",
                "message": f"CODEX_PATH is not executable: {path}"}
    return None


def codex_child_refusal(args: argparse.Namespace, repo: str) -> dict[str, Any] | None:
    """Pre-spawn receipt when the Codex child path cannot launch, or None."""
    error = codex_child_error(args)
    if error is None:
        return None
    receipt = base_receipt(args, repo)
    receipt.update(bridge_facts(args))
    receipt["error"] = error
    receipt["mutation_status"] = "not_started"
    receipt["mutation_performed"] = False
    return receipt


def codex_package_at(binary: str) -> tuple[str, str] | None:
    """``(name, version)`` of the ``@openai/codex`` package that owns ``binary``.

    Walks parents of the real path and stops at the first package whose name
    starts with ``@openai/codex``. Never spawns the binary.
    """
    try:
        directory = os.path.dirname(os.path.realpath(binary))
    except OSError:
        return None
    for _ in range(8):
        candidate = os.path.join(directory, "package.json")
        try:
            data = json.loads(Path(candidate).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = None
        if isinstance(data, dict):
            name = data.get("name")
            version = data.get("version")
            if (isinstance(name, str) and name.startswith("@openai/codex")
                    and isinstance(version, str)):
                return name, version
        parent = os.path.dirname(directory)
        if parent == directory:
            break
        directory = parent
    return None


def codex_binary_from_table(rows: dict[int, tuple[int, str]], agent_pid: int) -> str | None:
    """Absolute Codex binary among ``agent_pid``'s descendants running ``app-server``.

    Prefers a path whose package name is ``@openai/codex``. Does not search PATH.
    """
    children: dict[int, list[int]] = {}
    for pid, (ppid, _command) in rows.items():
        children.setdefault(ppid, []).append(pid)
    stack = list(children.get(agent_pid, []))
    seen: set[int] = set()
    paths: list[str] = []
    while stack:
        pid = stack.pop()
        if pid in seen or pid not in rows:
            continue
        seen.add(pid)
        _ppid, command = rows[pid]
        try:
            tokens = shlex.split(command)
        except ValueError:
            tokens = command.split()
        if "app-server" in tokens:
            for token in tokens:
                if token.startswith("/") and os.path.basename(token) not in {"node", "env"}:
                    paths.append(token)
        stack.extend(children.get(pid, []))
    for token in paths:
        package = codex_package_at(token)
        if package and package[0] == "@openai/codex":
            return token
    return paths[0] if paths else None


def codex_child_from_process(agent_pid: Any) -> dict[str, str | None]:
    """Package name and version of the Codex ``app-server`` this seat spawned."""
    empty: dict[str, str | None] = {
        "child_path": None, "child_package": None, "child_version": None}
    if not isinstance(agent_pid, int) or isinstance(agent_pid, bool) or agent_pid <= 0:
        return empty
    table = run_ps(["pid", "ppid", "command"])
    rows: dict[int, tuple[int, str]] = {}
    for line in table.stdout.splitlines():
        parts = line.split(None, 2)
        if len(parts) == 3 and parts[0].isdigit() and parts[1].isdigit():
            rows[int(parts[0])] = (int(parts[1]), parts[2])
    binary = codex_binary_from_table(rows, agent_pid)
    if not binary:
        return empty
    package = codex_package_at(binary)
    return {
        "child_path": binary,
        "child_package": package[0] if package else None,
        "child_version": package[1] if package else None,
    }


def codex_version_fact(args: argparse.Namespace, agent_pid: Any,
                       agent_info: Any) -> dict[str, Any] | None:
    """Adapter version, requested CLI, and launched child package as separate facts.

    Adapter version is ``agentInfo.version`` from this launch. Requested CLI is
    the manifest. The child package is read from the ``app-server`` process.
    A missing read stays null. Never a gate and never a version probe of PATH.
    """
    if not codex_manifest_launch(args):
        return None
    adapter = None
    if isinstance(agent_info, dict) and isinstance(agent_info.get("version"), str):
        adapter = agent_info["version"]
    fact: dict[str, Any] = {
        "adapter": adapter,
        "requested_cli": (args.manifest.get("acp_requested_cli") or None),
        "child_path": None,
        "child_package": None,
        "child_version": None,
    }
    try:
        fact.update(codex_child_from_process(agent_pid))
    except (OSError, ValueError):
        pass
    return fact


def agent_environment(args: argparse.Namespace) -> dict[str, str]:
    """Environment for the holder and its agent process: inherited except for
    forward proxies unless the platform opts in, plus the exact binary path for
    a vendored bridge. A non-absolute value is passed
    as-is so the bridge refuses it (fail closed) instead of searching PATH.
    Loopback-reaching platforms also get the loopback proxy bypass; that lands
    in this copy only, never in ``os.environ``.

    A Codex manifest launch supplies the same absolute child path checked
    before spawn. An invalid explicit path is refused before this is used.
    """
    env = dict(os.environ)
    if args.manifest.get("acp_forward_proxy") != "true":
        for name in FORWARD_PROXY_ENV:
            env.pop(name, None)
    bridge_env = BRIDGE_BINARY_ENV.get(args.platform)
    if bridge_env:
        env[bridge_env] = runtime_binary(args.manifest)
    if args.platform in LOOPBACK_NO_PROXY_PLATFORMS:
        env.update(loopback_no_proxy(env))
    if args.platform == "dsh":
        env[DSH_PERMISSION_ENV] = dsh_permission_mode(args)[0]
    if codex_manifest_launch(args):
        path = codex_child_path(args)
        if os.path.isabs(path):
            env["CODEX_PATH"] = path
        else:
            env.pop("CODEX_PATH", None)
    return env


def opencode_launch_policy(args: argparse.Namespace, repo: str, directory: Path,
                           env: dict[str, str]) -> dict[str, Any]:
    """Issue #256: native V2 build default, only in this launch environment.

    Do not parse or merge operator configuration. Even a non-permission config
    source defers the default: agent rules rank after root rules, and the native
    explicit-file slot ranks above global config. Presence is enough to leave
    all those policies and native config diagnostics authoritative.
    """
    fact: dict[str, Any] = {"selected": False, "agent": "build"}
    if args.mode is not None or args.resume or args.use_continue or args.agent_command_given:
        return {**fact, "reason": "explicit-mode-resume-or-command"}
    if any(key in env for key in ("OPENCODE_CONFIG", "OPENCODE_CONFIG_CONTENT")):
        return {**fact, "reason": "native-config-supplied"}
    home = Path(env.get("HOME") or str(Path.home()))
    config = Path(env.get("OPENCODE_CONFIG_DIR") or
                  str(Path(env.get("XDG_CONFIG_HOME") or str(home / ".config")) / "opencode"))
    # Global legacy agent sources also contribute native policies. Directory
    # presence conservatively covers markdown, JSONC and unreadable sources.
    legacy_home = Path(env.get("OPENCODE_TEST_HOME") or str(home))
    names = ("opencode.json", "opencode.jsonc", "agent", "agents", "mode", "modes")
    roots = [(root, names) for root in (config, legacy_home / ".claude", legacy_home / ".agents")]
    project = Path(repo).resolve()
    if (env.get("OPENCODE_CONFIG_PROJECT_DISABLE") or
            env.get("OPENCODE_DISABLE_PROJECT_CONFIG") or "").lower() not in ("1", "true"):
        for parent in (project, *project.parents):
            roots.extend(((parent, names[:2]), (parent / ".opencode", names)))
    try:
        for root, candidates in roots:
            for name in candidates:
                source = root / name
                # lstat also preserves broken links; don't treat an unreadable
                # or invalid operator source as authorization to replace it.
                try:
                    source.lstat()
                except FileNotFoundError:
                    continue
                return {**fact, "reason": "existing-config-source", "source": str(source)}
    except OSError:
        return {**fact, "reason": "config-source-unreadable"}
    policy = {"agents": {"build": {"permissions": [
        {"action": "*", "resource": "*", "effect": "allow"},
    ]}}}
    path = directory / "opencode-build-default.json"
    path.write_text(json.dumps(policy) + "\n", encoding="utf-8")
    env["OPENCODE_CONFIG"] = str(path)
    return {**fact, "selected": True, "reason": "managed-build-default",
            "via": "OPENCODE_CONFIG", "path": str(path), "policy": policy}


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
            binary["version"] = binary_version(path, agent_environment(args))
        facts["runtime_binary"] = binary
    return facts


def bridge_runtime_error(args: argparse.Namespace) -> dict[str, str] | None:
    """Why the bridge file or the ZCode runtime is not usable, or None.

    The one presence decision for preflight and for the pre-spawn refusals
    ``start`` and ``drain-restart`` share. It reads ``agent_command_facts``
    already produced by ``resolve_agent_command`` and ``zcode_runtime_error``.
    It does not spawn, write, or search PATH. A command with no Skill-relative
    token is not a missing bridge.
    """
    facts = getattr(args, "agent_command_facts", None) or []
    if any(not fact["present"] for fact in facts):
        return {
            "code": "acp-bridge-missing",
            "message": "the Skill-relative ACP command did not resolve to a file",
        }
    if args.platform == "zcode":
        missing = zcode_runtime_error()
        if missing:
            return {"code": "acp-runtime-missing", "message": missing}
    return None


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


def session_new_timeout(args: argparse.Namespace) -> float:
    """Issue #146: this platform's session/new wait in seconds. Absent or
    unparsable keeps the shared default (render-skills rejects a bad value)."""
    try:
        seconds = float(args.manifest.get("acp_session_new_timeout") or SESSION_NEW_TIMEOUT)
    except ValueError:
        return SESSION_NEW_TIMEOUT
    return seconds if 0 < seconds <= SESSION_NEW_TIMEOUT_MAX else SESSION_NEW_TIMEOUT


def session_new_extra(args: argparse.Namespace) -> float:
    """Seconds this platform's session/new wait exceeds the shared default."""
    return max(0.0, session_new_timeout(args) - SESSION_NEW_TIMEOUT)


def bounded_seconds(raw: object, cap: float) -> float | None:
    """A finite wait in (0, cap], or None when the value is absent or unusable."""
    if raw is None or raw == "":
        return None
    try:
        seconds = float(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if seconds != seconds or seconds == float("inf") or seconds == float("-inf"):
        return None
    if 0 < seconds <= cap:
        return seconds
    return None


def resume_wait_seconds(args: argparse.Namespace) -> float:
    """Issue #308: how long session/resume may take before it is pending.

    ``KAOLA_RESUME_TIMEOUT`` (seconds, finite, in (0, 600]) wins, including
    over the token hint. Otherwise the platform session/new wait is the base
    and ``KAOLA_RESUME_TOKENS`` adds one second per 10_000 tokens. The runner
    does not know a session's token count; the environment is the size hook.
    """
    explicit = bounded_seconds(os.environ.get("KAOLA_RESUME_TIMEOUT"), RESUME_TIMEOUT_MAX)
    if explicit is not None:
        return explicit
    base = session_new_timeout(args)
    raw_tokens = os.environ.get("KAOLA_RESUME_TOKENS")
    tokens = 0
    if raw_tokens:
        try:
            tokens = int(raw_tokens)
        except ValueError:
            tokens = 0
    if tokens > 0:
        base += tokens / 10000.0
    if base > RESUME_TIMEOUT_MAX:
        return RESUME_TIMEOUT_MAX
    if base <= 0:
        return SESSION_NEW_TIMEOUT
    return base


def resume_window_extra(args: argparse.Namespace) -> float:
    """Extra start-window seconds for a resume, including the late-success grace.

    Zero unless this start is a resume or continue. A resume that answers
    inside the shared session/new wait adds only the grace, and the poll
    returns as soon as the holder is ready, so a fast resume stays fast.
    """
    if not (getattr(args, "resume", None) or getattr(args, "use_continue", False)):
        return 0.0
    return max(0.0, resume_wait_seconds(args) - SESSION_NEW_TIMEOUT) + RESUME_RECOVERY_GRACE


class InputError(SystemExit):
    def __init__(self, message: str, code: int = 2):
        super().__init__(message)
        self.message = message
        self.code = code

    def __str__(self) -> str:
        return self.message


class ReceiptArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        # argparse can echo prompt text or a secret in an invalid value.
        reason = "Invalid arguments (invalid choice)" if "invalid choice:" in message else "Invalid arguments"
        die(f"{reason}. Use --help for the accepted arguments.")


def input_error_receipt(message: str, platform: str | None = None,
                        action: str | None = None, repo: str | None = None,
                        session: str | None = None) -> dict[str, Any]:
    """Input failed before any transport mutation; no holder was contacted."""
    return _stamp_recovery({"schema_version": 3, "platform": platform, "action": action,
            "repo": repo, "session": session, "transport": {"selected": "acp"},
            "error": {"code": "invalid-input", "message": message},
            "mutation_status": "not_started", "mutation_performed": False})


def die(message: str, code: int = 2) -> None:
    print(f"kaola-acp: {message}", file=sys.stderr)
    raise InputError(message, code)


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
    return acp_paths.record_root(getattr(args, "record_root", None))


def session_directory(args: argparse.Namespace, platform: str, session: str, repo: str) -> Path:
    return acp_paths.find_directory(platform, session, repo, getattr(args, "record_root", None))


def record_dir(args: argparse.Namespace, repo: str) -> Path:
    return session_directory(args, args.platform, args.session, repo)


def spawn_record_dir(args: argparse.Namespace, repo: str) -> Path | None:
    """Record directory whose ``children.jsonl`` a record-based receipt may
    consult, or None when the invocation names no platform/session (a receipt
    built from a bare record has no spawn record to read)."""
    if not all(getattr(args, name, None) for name in ("platform", "session")):
        return None
    return record_dir(args, repo)


def sock_path_for_directory(directory: Path) -> Path:
    """Applied legacy socket, or the short fixed per-UID socket for a new record."""
    return acp_paths.socket_path(directory)


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
    parser = ReceiptArgumentParser(prog="kaola-acp.py list")
    parser.add_argument("--platform", choices=PLATFORMS)
    parser.add_argument("--repo")
    parser.add_argument("--record-root")
    # Issue #132: the default stays the frozen live-holder view; the repo
    # sweep also needs the records whose holder PID is gone.
    parser.add_argument("--include-dead", action="store_true")
    return parser.parse_args(argv)


def command_list(args: argparse.Namespace) -> dict[str, Any]:
    repo_filter = resolve_repo(args.repo) if args.repo else None
    rows: list[dict[str, Any]] = []
    # Issue #359: (platform, session) pairs that still have a record.json,
    # with the record's repo: a registry row without one is a lost record.
    present: dict[tuple[str, str], list[Path]] = {}
    for path in acp_paths.record_paths("*/*/*/record.json", getattr(args, "record_root", None)):
        platform = path.parent.parent.parent.name
        session = path.parent.parent.name
        present.setdefault((platform, session), []).append(path.parent)
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
        identity, state_reply = holder_identity(directory, record, LIST_IDENTITY_TIMEOUT)
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
        row_platform = record.get("platform") or platform
        row_session = record.get("session") or session
        host = host_session(row_platform, row_session)
        persisted_role = record.get("session_role")
        if persisted_role not in SESSION_ROLES:
            persisted_role = None
        # Issue #273: persisted agent_alive is a receipt-time fact, never a
        # current-liveness claim, and no record field proves its receipt
        # time. Project a current claim ONLY from the verified holder's own
        # type-checked state reply; every other identity (including a PID
        # later held by an unrelated program) yields null — unknown, never
        # dead — and nothing here releases or stops any process.
        if identity == "verified":
            agent_alive: bool | None = bool(state_reply.get("agent_alive")) \
                if isinstance(state_reply, dict) and isinstance(
                    state_reply.get("agent_alive"), bool) else None
        else:
            if identity == "unreachable" and holder_argv_anchor(
                    pid, directory) is False:
                identity = "mismatch"
            agent_alive = None
        rows.append({
            "platform": row_platform,
            "session": row_session,
            "repo": repo,
            "state": state,
            "holder_pid": pid,
            "holder_instance_id": record.get("holder_instance_id"),
            "agent_alive": agent_alive,
            # Issue #369: the cwd guard's tree roots and the recorded tool cwd.
            # Additive row fields; an older record leaves them null.
            "agent_pid": record.get("agent_pid"),
            "agent_pgid": record.get("agent_pgid"),
            "agent_child_pgids": record.get("agent_child_pgids") or [],
            "tool_cwd_path": ((record.get("tool_cwd") or {}).get("last_known")
                              if isinstance(record.get("tool_cwd"), dict) else None),
            "tool_cwd_exists": ((record.get("tool_cwd") or {}).get("exists")
                                if isinstance(record.get("tool_cwd"), dict) else None),
            "event_cursor": cursor,
            "mutation_status": mutation,
            "pending_count": len(pending) if isinstance(pending, list) else 0,
            "socket_ok": probe_socket_ok(sock_path_for_directory(directory)),
            "transport": "acp",
            # Issue #132: the identity check, the Host-name fact, and the
            # recorded binding the repo sweep classifies a row by.
            "identity": identity,
            "host_class": host,
            # Issue #245: host_class stays the name-pattern bool. session_role
            # mirrors it when that bool is true; otherwise the persisted value.
            "session_role": "host" if host else persisted_role,
            "dispatcher": record.get("dispatcher"),
        })
        fresh = seat_freshness(record)
        rows[-1].update({
            "runner_build": fresh["runner_build"],
            "accepted_revision": fresh["accepted_revision"],
            "stale": fresh["stale"],
            "stale_reasons": fresh["stale_reasons"],
            "reported_drift": fresh["reported_drift"],
            "missing_files": fresh["missing_files"],
            "baseline_exempt": fresh["baseline_exempt"],
        })
        if isinstance(record.get("holder_features"), list):
            # Issue #255: what this holder build can read and relay. Absent on
            # older holders, which is unknown, never support.
            rows[-1]["holder_features"] = record["holder_features"]
        attach_binding_fact(rows[-1], record)
        # Issue #313: the same non-blocking name advisory as start. A host,
        # sideagent, or seat row has name_role and no issue_name.
        stamp_issue_name_receipt(rows[-1], str(row_platform), str(row_session), repo)
    result: dict[str, Any] = {"schema": LIST_SCHEMA, "rows": rows}
    if repo_filter is not None:
        lost = _record_loss_list(repo_filter, present)
        if lost:
            result["records_lost"] = lost
    return result



# Issue #147: the read-only installed-platforms survey. A host-wide fact like
# ``list``, but about installs, not sessions: which platform CLIs resolve on
# this host. It runs no platform binary (not even ``--version``), opens no ACP
# session, spawns no holder, and reads no record root; its only child is one
# non-interactive login shell that prints its environment, so a client with a
# narrow PATH (a GUI app subprocess) still sees login-shell installs. The
# table mirrors each manifest's runtime_name/binary_name/binary_env (a
# contract test pins it), because an installed worker Skill ships only its
# own platform.yaml. ZCode keeps its launch rule: installed only when both
# explicit ZCode paths are set, never by PATH or an application bundle.
SURVEY_SCHEMA = "kaola-acp-survey/1"
SURVEY_RUNTIMES = {
    "antigravity": ("Antigravity", "agy", "AGY_BIN"),
    "claude-code": ("Claude Code", "claude", "CLAUDE_BIN"),
    "codex": ("Codex CLI", "codex", "CODEX_BIN"),
    "cursor-cli": ("Cursor CLI", "cursor-agent", "CURSOR_AGENT_BIN"),
    "devin": ("Devin CLI", "devin", "DEVIN_BIN"),
    "droid": ("Droid", "droid", "DROID_BIN"),
    "dsh": ("dsh", "dsh", "DSH_BIN"),
    "grok": ("Grok CLI", "grok", "GROK_BIN"),
    "hermes": ("Hermes Agent", "hermes", "HERMES_BIN"),
    "kimi-cli": ("Kimi CLI", "kimi", "KIMI_BIN"),
    "opencode": ("OpenCode", "opencode", "OPENCODE_BIN"),
    "zcode": ("ZCode", "zcode", "ZCODE_BIN"),
}
SURVEY_ZCODE_ENV = (ZCODE_ENTRY_ENV, ZCODE_NODE_ENV)
SURVEY_LOGIN_TIMEOUT = 10.0
SURVEY_LOGIN_MARKER = "__KAOLA_ACP_SURVEY_LOGIN_ENV__"
SURVEY_BASE_PATH = "/usr/bin:/bin:/usr/sbin:/sbin"


def parse_survey_args(argv: list[str]) -> argparse.Namespace:
    parser = ReceiptArgumentParser(prog="kaola-acp.py survey")
    parser.add_argument("--platform", choices=PLATFORMS)
    parser.add_argument("--login-shell")
    return parser.parse_args(argv)


def survey_login_shell(explicit: str | None) -> tuple[str, str]:
    """The login shell to ask, and where that choice came from."""
    if explicit:
        return explicit, "argument"
    try:
        account = pwd.getpwuid(os.getuid()).pw_shell
    except (KeyError, OSError):
        account = ""
    if account:
        return account, "account"
    if os.environ.get("SHELL"):
        return os.environ["SHELL"], "SHELL"
    return "/bin/zsh", "default"


def survey_login_env(shell: str, source: str) -> tuple[dict[str, Any], dict[str, str] | None]:
    """Run ``<shell> -l -c`` from a fresh minimal environment and return its
    environment, as a new login would see it. Never interactive, stdin closed,
    bounded, and killed as a group on timeout."""
    fact: dict[str, Any] = {"shell": shell, "shell_source": source,
                            "status": "unavailable", "detail": None, "path": None}
    try:
        home = pwd.getpwuid(os.getuid()).pw_dir
    except (KeyError, OSError):
        home = os.environ.get("HOME") or "/"
    env = {"HOME": home, "SHELL": shell, "PATH": SURVEY_BASE_PATH, "TERM": "dumb"}
    for name in ("USER", "LOGNAME", "TMPDIR", "LANG"):
        if os.environ.get(name):
            env[name] = os.environ[name]
    try:
        proc = subprocess.Popen(
            [shell, "-l", "-c", f"echo {SURVEY_LOGIN_MARKER}; exec /usr/bin/env -0"],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            env=env, cwd=home if os.path.isdir(home) else "/", start_new_session=True,
        )
    except OSError as error:
        fact["detail"] = f"login shell could not run: {error}"
        return fact, None
    try:
        out, _ = proc.communicate(timeout=SURVEY_LOGIN_TIMEOUT)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except OSError:
            pass
        try:
            proc.communicate(timeout=2.0)
        except subprocess.TimeoutExpired:
            # A profile daemon outside the group still holds stdout open.
            proc.kill()
            if proc.stdout is not None:
                proc.stdout.close()
        fact["detail"] = f"login shell did not answer within {SURVEY_LOGIN_TIMEOUT:g} s"
        return fact, None
    marker = (SURVEY_LOGIN_MARKER + "\n").encode()
    if marker not in out:
        fact["detail"] = f"login shell exited {proc.returncode} without printing its environment"
        return fact, None
    login: dict[str, str] = {}
    for item in out.rsplit(marker, 1)[1].split(b"\0"):
        key, separator, value = item.decode("utf-8", "replace").partition("=")
        if separator and key:
            login[key] = value
    fact.update(status="ok", path=login.get("PATH"))
    return fact, login


def survey_resolve(value: str | None, path: str | None) -> str | None:
    """An executable file for ``value`` on ``path`` (absolute values as-is), or None."""
    if not value:
        return None
    if os.path.isabs(value):
        return value if os.path.isfile(value) and os.access(value, os.X_OK) else None
    if path is None:
        return None
    found = shutil.which(value, path=path)
    return os.path.abspath(found) if found else None


def survey_zcode_row(row: dict[str, Any], login: dict[str, str] | None) -> None:
    problem: str | None = None
    for source, env in (("process_env", dict(os.environ)), ("login_env", login)):
        if env is None:
            continue
        entry, node = (env.get(name) or "" for name in SURVEY_ZCODE_ENV)
        if not entry and not node:
            continue
        entry_state = zcode_path_state(entry, executable=False)
        node_state = zcode_path_state(node, executable=True)
        if entry_state == "ok" and node_state == "ok":
            row.update(status="present", installed=True, path=entry, source=source)
            return
        # A copied path that is not a file on this host is not "not installed".
        problem = problem or (
            f"{ZCODE_ENTRY_ENV} is {entry_state}; {ZCODE_NODE_ENV} is {node_state}"
        )
    if problem and row["status"] == "absent":
        row["detail"] = problem


def command_survey(args: argparse.Namespace) -> dict[str, Any]:
    shell, source = survey_login_shell(args.login_shell)
    login_fact, login = survey_login_env(shell, source)
    login_path = login.get("PATH") if login is not None else None
    rows: list[dict[str, Any]] = []
    for platform in PLATFORMS:
        if args.platform and platform != args.platform:
            continue
        runtime_name, binary, binary_env = SURVEY_RUNTIMES[platform]
        zcode = platform == "zcode"
        row: dict[str, Any] = {
            "platform": platform,
            "runtime_name": runtime_name,
            "status": "absent",
            "installed": False,
            "path": None,
            "source": None,
            "binary": None if zcode else binary,
            "binary_env": None if zcode else binary_env,
            "requires_env": list(SURVEY_ZCODE_ENV) if zcode else [],
            "process_path": None if zcode else survey_resolve(binary, os.environ.get("PATH")),
            "login_path": None if zcode else survey_resolve(binary, login_path),
        }
        if zcode:
            survey_zcode_row(row, login)
        else:
            # The Runner's own launch order (runtime_binary): the override
            # first, then PATH; the invoking process before the login shell.
            for found, where in (
                (survey_resolve(os.environ.get(binary_env), os.environ.get("PATH")), "binary_env"),
                (row["process_path"], "process_path"),
                (survey_resolve((login or {}).get(binary_env), login_path), "login_binary_env"),
                (row["login_path"], "login_path"),
            ):
                if found:
                    row.update(status="present", installed=True, path=found, source=where)
                    break
        if row["status"] == "absent" and login is None:
            row["status"] = "unknown"
        rows.append(row)
    return {"schema": SURVEY_SCHEMA, "login_env": login_fact, "platforms": rows}


# Issue #148: read-only quota catalog. No agent, no holder, no record, no
# platform binary. ``--installed-only`` reuses the survey and keeps platforms
# whose install status is ``present``.
PACKAGES_SCHEMA = "kaola-acp-packages/1"
MODEL_PACKAGE_SCHEMA = "kaola-acp-model-package/1"
_QUOTA = None


def quota_module():
    """Sibling ``kaola-quota.py``. A Skill copy and the checkout both ship it."""
    global _QUOTA
    if _QUOTA is None:
        path = SCRIPT_DIR / "kaola-quota.py"
        spec = importlib.util.spec_from_file_location("kaola_quota", path)
        if spec is None or spec.loader is None:
            die(f"quota catalog checker missing: {path}")
        module = importlib.util.module_from_spec(spec)
        # A generated Skill must stay byte-identical to the render. Importing the
        # sibling catalog must not drop a __pycache__ next to it.
        previous = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        try:
            spec.loader.exec_module(module)
        finally:
            sys.dont_write_bytecode = previous
        _QUOTA = module
    return _QUOTA


def parse_packages_args(argv: list[str]) -> argparse.Namespace:
    parser = ReceiptArgumentParser(prog="kaola-acp.py packages")
    parser.add_argument("--platform", choices=PLATFORMS)
    parser.add_argument("--installed-only", action="store_true")
    parser.add_argument("--login-shell")
    return parser.parse_args(argv)


def parse_model_package_args(argv: list[str]) -> argparse.Namespace:
    parser = ReceiptArgumentParser(prog="kaola-acp.py model-package")
    parser.add_argument("--platform", required=True, choices=PLATFORMS)
    parser.add_argument("--model", required=True)
    return parser.parse_args(argv)


def command_packages(args: argparse.Namespace) -> dict[str, Any]:
    quota = quota_module()
    present = None
    login_env = None
    if args.installed_only:
        survey = command_survey(argparse.Namespace(
            platform=args.platform, login_shell=args.login_shell))
        login_env = survey["login_env"]
        present = {row["platform"] for row in survey["platforms"] if row["status"] == "present"}
    rows: list[dict[str, Any]] = []
    for platform in quota.available_platforms(SCRIPT_DIR):
        if args.platform and platform != args.platform:
            continue
        if present is not None and platform not in present:
            continue
        catalog = quota.load_catalog(platform, SCRIPT_DIR)
        rows.append({"platform": platform, "packages": catalog.public_packages()})
    payload: dict[str, Any] = {
        "schema": PACKAGES_SCHEMA,
        "installed_only": bool(args.installed_only),
        "platforms": rows,
    }
    if args.installed_only:
        payload["login_env"] = login_env
    return payload


def stamp_quota_emission(receipt: dict[str, Any], platform: str) -> None:
    """Stamp model rows on an observe/status receipt. ``record`` is not walked."""
    if not isinstance(receipt, dict) or not (SCRIPT_DIR / "kaola-quota.py").is_file():
        return
    quota = quota_module()
    try:
        catalog = quota.load_catalog(platform, SCRIPT_DIR)
    except quota.QuotaError:
        return
    quota.annotate_observe(receipt, catalog)


def command_model_package(args: argparse.Namespace) -> dict[str, Any]:
    quota = quota_module()
    try:
        catalog = quota.load_catalog(args.platform, SCRIPT_DIR)
    except quota.QuotaError as exc:
        die(str(exc))
    resolved = quota.resolve_model(catalog, args.model)
    result: dict[str, Any] = {
        "schema": MODEL_PACKAGE_SCHEMA,
        "platform": args.platform,
        "model": args.model,
        "packageId": resolved["packageId"],
        "status": resolved["status"],
    }
    if resolved.get("pool") is not None:
        result["pool"] = resolved["pool"]
    return result


def view_error(code: str, message: str) -> dict[str, Any]:
    return _stamp_recovery({"schema": VIEW_SCHEMA, "error": {"code": code, "message": message}})


# Ordinary receipts are bounded (progressive disclosure): capture through
# bound_capture_receipt, observe/status through bound_state_receipt. The capture limit
# equals ``capture_receipt_bytes`` in templates/budgets.json. ``capture --full`` is
# the explicit, unbounded request and
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
                        "agent_info", "start_evidence", "pending_permissions")
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
    return _stamp_recovery({"kind": "error", "error": {"code": code, "message": message}})


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
    if isinstance(event, dict) and event.get("kind") == "error":
        event = _stamp_recovery(event)
        text = json.dumps(event, ensure_ascii=False)
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


# Issue #383: client transport bounds. ``--timeout`` is the holder's wait, not
# the client's socket deadline; ``REPLY_GRACE`` covers the holder's record write
# and reply serialization. A no-wait send/start brief only waits for admission,
# so an omitted ``--timeout`` still gets a bound; ``send --wait`` and ``wait``
# keep the unbounded socket because a real turn or a long poll may run for
# minutes. The stage facts are what decide whether a failure proves nothing was
# written.
REPLY_GRACE = 30.0
ADMISSION_BOUND = 30.0
STEER_ADMISSION_BOUND = 30.0
CANCEL_GRACE = 5.0


def client_socket_timeout(args: argparse.Namespace, wait: bool | None = None,
                          op: str | None = None) -> float | None:
    """The client-side transport bound for one holder call (Issue #383).

    ``op`` is the **resolved holder operation**, not the CLI command. The
    interrupt path is still ``steer`` at the CLI layer, so dispatching on
    ``args.command`` would select the 60 s native formula and ignore
    ``--cancel-timeout``. Call sites pass ``op="prompt"``, ``"steer"``,
    ``"steer_interrupt"``, ``"wait"``, ``"cancel"`` or ``"wake_delegator"``.
    The command fallback exists only for a caller that has no resolved op.

    An explicit ``--timeout`` keeps the historical ``timeout + 30`` reply
    window. Without it, a no-wait prompt admission is bounded at 30 s, while a
    turn-waiting prompt and ``wait`` remain unbounded. Native ``steer`` uses
    the holder's own 30 s wait plus the grace; ``cancel`` uses its 5 s grace;
    ``steer_interrupt`` uses the largest cancel wait it may pass to the holder.
    """
    resolved = op or args.command
    if resolved in ("send", "start"):
        resolved = "prompt"
    elif resolved == "key":
        resolved = "cancel"
    elif resolved == "wake":
        resolved = "wake_delegator"
    timeout = args.timeout
    if resolved == "prompt":
        if timeout is not None:
            return timeout + REPLY_GRACE
        return ADMISSION_BOUND if wait is False else None
    if resolved == "steer":
        return ((timeout if timeout is not None else STEER_ADMISSION_BOUND)
                + REPLY_GRACE)
    if resolved == "steer_interrupt":
        base = max(getattr(args, "cancel_timeout", None) or 0.0,
                   timeout or 0.0, CANCEL_GRACE)
        return base + REPLY_GRACE
    if resolved == "cancel":
        return ((timeout if timeout is not None else CANCEL_GRACE)
                + REPLY_GRACE)
    if resolved == "wait":
        return None if timeout is None else timeout + REPLY_GRACE
    if resolved == "wake_delegator":
        return None if timeout is None else timeout + REPLY_GRACE
    raise ValueError(f"no client socket bound for {resolved}")


def socket_failure(code: str, stage: str, message: str,
                   timeout: float | None = None) -> dict[str, Any]:
    """Issue #383: one transport failure with the stage that decided it.

    Only connect and send prove the complete request line was not written: the
    newline is the last byte, so a ``sendall`` failure cannot leave a frame the
    holder can parse. A read failure means the request was written and may have
    been admitted, so ``mutation_performed`` is ``null`` rather than ``false``.
    """
    error: dict[str, Any] = {"code": code, "stage": stage, "message": message}
    if timeout is not None:
        error["timeout_s"] = timeout
    if stage in ("connect", "send"):
        return {"error": error, "outcome": "not_sent",
                "mutation_performed": False, "mutation_status": "not_started"}
    return {"error": error, "outcome": "unknown",
            "mutation_performed": None, "mutation_status": "unknown"}


def socket_request(sock_path: Path, op: str, params: dict[str, Any],
                   timeout: float | None,
                   directory: Path | None = None) -> dict[str, Any]:
    connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    stage = "connect"
    # One absolute deadline, not one allowance per syscall. Without this,
    # connect + sendall + recv could each consume the full timeout and a
    # nominal 30 s bound could take 90 s.
    deadline = None if timeout is None else time.monotonic() + timeout

    def remaining() -> float | None:
        if deadline is None:
            return None
        left = deadline - time.monotonic()
        if left <= 0:
            raise TimeoutError("timed out")
        return left

    # Issue #408: a bound seat proves this caller holds the dispatcher
    # capability — the holder-minted ``auth.token`` inside its record dir.
    # ``directory`` is that seat's own record dir. An unbound seat ignores the
    # field, so attaching it whenever a readable token exists is harmless.
    if directory is not None and "auth_token" not in params:
        auth_token = acp_paths.read_auth_token(directory)
        if auth_token:
            params = dict(params, auth_token=auth_token)

    try:
        connection.settimeout(remaining())
        connection.connect(str(sock_path))
        stage = "send"
        payload = json.dumps({"op": op, "request_id": secrets.token_hex(8),
                              "params": params}).encode("utf-8") + b"\n"
        connection.settimeout(remaining())
        connection.sendall(payload)
        stage = "read"
        buffer = bytearray()
        while True:
            connection.settimeout(remaining())
            data = connection.recv(65536)
            if not data:
                break
            buffer.extend(data)
            if b"\n" in buffer:
                line, _, _ = buffer.partition(b"\n")
                return json.loads(line.decode("utf-8"))
        if buffer:
            return json.loads(buffer.decode("utf-8"))
        return socket_failure("holder-closed", "read",
                              "holder closed the connection")
    except (TimeoutError, socket.timeout) as exc:
        return socket_failure("holder-timeout", stage,
                              str(exc) or "timed out", timeout)
    except (OSError, ValueError) as exc:
        return socket_failure("holder-unreachable", stage, str(exc), timeout)
    finally:
        connection.close()


# Issue #254, measured on OpenCode 2.0.22. session/new returns before provider
# discovery finishes: the first model list is only opencode/* (current value
# opencode/fledge-alpha-free). About two seconds later config_option_update
# advertises opencode-go/deepseek-v4.1-flash. session/set_config_option of that
# id before the advertisement returns JSON-RPC -32602 "model not found" with
# providerId opencode-go and modelId equal to the full requested string. The
# same call after the advertisement applies it. The bound covers that delay.
# A value that never appears is still sent once, and the agent's rejection
# stays the receipt. No other model is substituted.
OPENCODE_MODEL_ADVERTISE_WAIT = 8.0


def advertised_config_values(state: Any, config_id: str) -> set[str]:
    """Selectable values of one config option on a holder state reply."""
    if not isinstance(state, dict) or state.get("error"):
        return set()
    meta = state.get("session_meta")
    options = meta.get("configOptions") if isinstance(meta, dict) else None
    found: set[str] = set()
    if not isinstance(options, list):
        return found
    for option in options:
        if not isinstance(option, dict) or option.get("id") != config_id:
            continue
        for entry in option.get("options") or []:
            if not isinstance(entry, dict):
                continue
            nested = entry.get("options")
            if isinstance(nested, list):
                for member in nested:
                    if isinstance(member, dict) and isinstance(member.get("value"), str):
                        found.add(member["value"])
            elif isinstance(entry.get("value"), str):
                found.add(entry["value"])
    return found


def opencode_model_not_found(result: Any) -> bool:
    """OpenCode's -32602 for an id its catalog has not published yet."""
    if not isinstance(result, dict):
        return False
    error = result.get("error")
    if not isinstance(error, dict):
        return False
    detail = error.get("detail")
    if not isinstance(detail, dict):
        return False
    message = str(detail.get("message") or "")
    return detail.get("code") == -32602 and "model not found" in message


def set_opencode_model_when_advertised(sock_path: Path, config_id: str,
                                       value: str,
                                       directory: Path | None = None,
                                       expected_holder: str | None = None
                                       ) -> dict[str, Any]:
    """Set the OpenCode model once the live option list contains ``value``."""
    deadline = time.monotonic() + OPENCODE_MODEL_ADVERTISE_WAIT
    while True:
        state = socket_request(sock_path, "state", {}, 5.0)
        advertised = value in advertised_config_values(state, config_id)
        if advertised or time.monotonic() >= deadline:
            params: dict[str, Any] = {"config_id": config_id, "value": value}
            if expected_holder is not None:
                params["expected_holder_instance_id"] = expected_holder
            result = socket_request(
                sock_path, "set_config_option",
                params, 20.0, directory,
            )
            if (advertised or not opencode_model_not_found(result)
                    or time.monotonic() >= deadline):
                return result
        time.sleep(0.05)


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


# Issue #386: high-frequency receipts (send --no-wait, steer, permit) omit Git
# evidence by default. It costs two subprocesses per call (`rev-parse` and
# `status --porcelain`) and no contract consumes it there. A waiting `send`,
# `status` and every other schema-3 receipt keep the pre-existing shape.
# Explicit --git-facts / --no-git-facts always win over the command default.
def git_facts_requested(args: argparse.Namespace) -> bool:
    explicit = getattr(args, "git_facts", None)
    if explicit is not None:
        return explicit
    command = getattr(args, "command", None)
    if command in ("steer", "permit"):
        return False
    if command == "send":
        wait = getattr(args, "resolved_wait", None)
        if wait is None:
            wait = getattr(args, "wait", None)
        return wait is True
    return True


def base_receipt(args: argparse.Namespace, repo: str,
                 include_git: bool | None = None) -> dict[str, Any]:
    receipt: dict[str, Any] = {
        "schema_version": 3,
        "platform": args.platform,
        "session": args.session,
        "repo": repo,
        "transport": {"selected": "acp"},
    }
    if include_git is None:
        include_git = git_facts_requested(args)
    if include_git:
        receipt["git"] = git_facts(repo)
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
    return _stamp_recovery(receipt)


PROMPT_STEER_OPS = frozenset({"prompt", "steer", "steer_interrupt"})
# Issue #383: these calls can mutate the session. A transport timeout keeps its
# stage fact on them; read-only calls (state/capture/wait) never grow a
# mutation claim from a failed read.
MUTATING_OPS = frozenset({
    "prompt", "steer", "steer_interrupt", "cancel", "permit", "stop",
    "wake_delegator",
})
# Issue #408: the ops a heartbeat-bound seat gates on the holder-issued
# auth.token plus expected_holder_instance_id — the same set the holder
# enforces server-side.
BOUND_WRITE_OPS = frozenset({
    "prompt", "steer", "steer_interrupt", "cancel", "permit", "stop",
    "wake_delegator", "worker_event", "compact_notice", "set_config_option",
    "record_start_evidence", "rebind_heartbeat_host",
})
# Issue #380: the client-supplied message id is accepted only by send/steer,
# and only while the live holder advertises the admission ledger.
CLIENT_MESSAGE_ID_FEATURE = "client-message-id/1"
# Issue #379: these answers prove this request wrote nothing. ``holder-lost`` is
# in this set only when it carries no stage, the connect stage, or the send
# stage; a read loss may have happened after the frame was written.
UNSENT_RECEIPT_CODES = frozenset({
    "no-session", "record-lost", "holder-socket-missing", "holder-lost",
})
UNCERTAIN_ERROR_STAGES = frozenset({"read"})


def _stamp_request_mutation(receipt: dict[str, Any], op: str) -> dict[str, Any]:
    """Issue #379: state mutation for THIS request on a prompt/steer error.

    ``holder_lost_receipt`` describes the previous prompt because ``status``
    and ``observe`` need that historical fact. A send or steer must not inherit
    it. A connect or send failure proves nothing was written: the request line
    ends with a newline, and a failed ``sendall`` cannot have delivered the
    complete line the holder parses. ``holder-closed``, a read failure, and a
    ``holder-unreachable`` without a stage may have happened after the frame
    was written, so ``null``/``unknown`` is the only honest claim. Issue #383
    adds ``error.stage``; when it is present this classification uses it, and
    when it is absent the conservative answer is kept. A ``holder-lost``
    produced after a wire attempt carries an internal source marker: its
    no-stage form is still uncertain, unlike the pre-check that proved the
    holder was already dead before this request.
    """
    if not isinstance(receipt, dict):
        return receipt
    wire_attempted = bool(receipt.pop("_wire_attempted", False))
    if op not in PROMPT_STEER_OPS:
        return receipt
    error = receipt.get("error")
    if not isinstance(error, dict):
        return receipt
    code = error.get("code")
    stage = error.get("stage")
    holder_lost = code == "holder-lost"
    if code == "holder-closed":
        uncertain = True
    elif code in ("holder-unreachable", "holder-timeout"):
        # No stage predates #383 and cannot prove the connect step failed.
        uncertain = stage not in ("connect", "send")
    elif holder_lost:
        # A missing stage predates #383. The pre-check proved the holder dead
        # before this request; a post-wire death may have lost a written
        # frame, so that source stays uncertain until #383 adds the stage.
        uncertain = (stage == "read"
                     or (stage is None and wire_attempted))
    else:
        uncertain = False
    unsent = (
        code in UNSENT_RECEIPT_CODES
        or (code in ("holder-unreachable", "holder-timeout")
            and stage in ("connect", "send"))
    )
    # A holder that answers with its own mutation fact owns it. holder-lost is
    # the exception: its value came from the previous prompt.
    explicit = not holder_lost and (
        "mutation_performed" in receipt or "mutation_status" in receipt)
    if uncertain and not explicit:
        receipt["mutation_performed"] = None
        receipt["mutation_status"] = "unknown"
    elif unsent and not explicit:
        receipt["mutation_performed"] = False
        receipt["mutation_status"] = "not_started"
        if holder_lost:
            last = (receipt.get("record") or {}).get("last_prompt")
            if isinstance(last, dict) and last:
                receipt.setdefault("previous_prompt", last)
    if op in ("steer", "steer_interrupt"):
        performed = receipt.get("mutation_performed")
        if performed is False:
            receipt.setdefault("steer_outcome", "not_consumed")
            receipt.setdefault("steer_consumed", False)
            receipt.setdefault("steer_confirmation", "none")
        elif performed is None and "mutation_performed" in receipt:
            receipt.setdefault("steer_outcome", "unknown")
            receipt.setdefault("steer_consumed", None)
            receipt.setdefault("steer_confirmation", "none")
    return receipt


def _holder_event_log(path: Path):
    """The holder's ``EventLog``, so a refused stop writes its event."""
    module = getattr(_holder_event_log, "module", None)
    if module is None:
        spec = importlib.util.spec_from_file_location(
            "kaola_acp_holder_stop_event", HOLDER)
        module = importlib.util.module_from_spec(spec)
        previous = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        try:
            spec.loader.exec_module(module)
        finally:
            sys.dont_write_bytecode = previous
        _holder_event_log.module = module
    return module.EventLog(path)


def append_holder_instance_mismatch(directory: Path | None, op: str,
                                    expected: Any) -> None:
    """One ``holder_instance_mismatch`` line, the object a live holder appends."""
    if directory is None:
        return
    try:
        _holder_event_log(directory / "events.jsonl").append({
            "kind": "holder_instance_mismatch",
            "op": op,
            "expected_holder_instance_id": expected,
        })
    except OSError:
        pass


def recover_host_death_wake(directory: Path | None,
                            record: dict[str, Any]) -> dict[str, Any] | None:
    """Issue #299: one durable ``error``/``holder_lost`` Delegator wake for a
    Host holder that died without signalling (SIGKILL, crash).

    Called from ``command_start`` on a dead or pid-reused holder, from the
    dead-holder ``stop`` paths, and from ``delegator-webhook status`` (#311).
    Start and stop are about to replace or retire the record. Status leaves
    the record in place. A clean ``op_stop`` writes ``stopped`` (with its own
    inline wake) before the record can look dead, so the state check plus the
    exactly-once ``delegator_death_wake`` event guard keep this to genuinely
    unsignalled deaths. The event cursor doubles as ``event_seq``:
    ``EventLog`` seeds a fresh instance's cursor from the max over live and
    rotated files in this record dir, so it is strictly newer than anything
    the dead holder sent.
    """
    holder_instance_id = record.get("holder_instance_id")
    if (directory is None or record.get("session_role") != "host"
            or not isinstance(holder_instance_id, str)
            or not holder_instance_id
            or record.get("state") == "stopped"):
        return None
    import fcntl
    try:
        with open(directory / "delegator-death-wake.lock", "a+b") as lock_file:
            fcntl.flock(lock_file, fcntl.LOCK_EX)
            log = _holder_event_log(directory / "events.jsonl")
            for entry in log._iter_entries():
                if (entry.get("kind") == "delegator_death_wake"
                        and entry.get("holder_instance_id") == holder_instance_id):
                    return {"sent": False, "reason": "already-recovered",
                            "event_seq": entry.get("cursor")}
            event_seq = log.append({
                "kind": "delegator_death_wake",
                "holder_instance_id": holder_instance_id,
                "state": "error",
                "state_detail": "holder_lost",
            })
    except OSError:
        # Issue #320: omitting the key left the lock/log failure with no reader.
        return {"sent": False, "reason": "death-wake-unrecorded"}
    payload = {
        "schema": "kaola-delegator-wake/1",
        "project": record.get("repo"),
        "session": record.get("session"),
        "holder_instance_id": holder_instance_id,
        "event_seq": event_seq,
        "state": "error",
        "state_detail": "holder_lost",
        "reason": "holder_lost",
        "ts": _utc_stamp(),
    }
    try:
        # The parent returns without waiting. Stderr stays discarded here; the
        # child appends a diagnostic line to this record's event log when the
        # env var is set. The live holder captures stderr itself (#320).
        child_env = os.environ.copy()
        child_env[WAKE_DIAG_EVENT_ENV] = str(directory / "events.jsonl")
        proc = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()),
             "delegator-webhook", "deliver"],
            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, start_new_session=True,
            close_fds=True, cwd=record.get("repo") or None,
            env=child_env)
        assert proc.stdin is not None
        proc.stdin.write(json.dumps(payload).encode("utf-8"))
        proc.stdin.close()
    except Exception as exc:
        return {"sent": False, "reason": "spawn-failed",
                "error": type(exc).__name__}
    return {"sent": True, "holder_instance_id": holder_instance_id,
            "event_seq": event_seq}


def holder_instance_mismatch_receipt(args: argparse.Namespace, repo: str,
                                     directory: Path | None,
                                     record: dict[str, Any], params: dict[str, Any],
                                     op: str) -> dict[str, Any] | None:
    """Refuse a stop that names a holder instance other than the record's.

    Same typed mismatch as a live holder whose socket is silent: code
    ``holder-instance-mismatch``, both ids, ``mutation_status``
    ``not_started``, and ``mutation_performed`` false. One
    ``holder_instance_mismatch`` event is written. The record and every
    process stay as they were. An omitted expected id is not a mismatch.
    """
    expected = params.get("expected_holder_instance_id")
    actual = record.get("holder_instance_id")
    if expected is None or expected == actual:
        return None
    append_holder_instance_mismatch(directory, op, expected)
    receipt = base_receipt(args, repo)
    receipt["error"] = {
        "code": "holder-instance-mismatch",
        "expected_holder_instance_id": expected,
        "holder_instance_id": actual,
    }
    receipt.update(mutation_status="not_started", mutation_performed=False)
    return receipt


# Issue #359: a record dir under a temp root can vanish - an OS tmp reaper or
# a sibling run - while its holder lives or dies unnoticed. Every dead-holder
# wake derives identity and dedupe from record.json in that dir, so nothing
# survived the wipe to report it. The host registry is the liveness
# cross-check that survives: ``start`` registers the row and a recorded clean
# ``stop`` removes it, so a row whose record is gone everywhere is an
# unrecovered loss; the next ``delegator-webhook status`` scan emits the same
# one ``error``/``holder_lost`` wake (``state_detail`` ``record_lost``).
HOST_REGISTRY_SCHEMA = "kaola-host-registry/1"
# The record-loss wake uses event_seq 0 once per holder_instance_id. A
# holder's own event_seq starts at 1, so the claim key never collides with a
# turn wake, and a restarted instance registers a fresh holder_instance_id.
RECORD_LOSS_WAKE_SEQ = 0
HOST_REGISTRY_ROW_KEYS = frozenset({
    "platform", "session", "repo", "record_dir", "socket_path",
    "holder_pid", "holder_instance_id", "acp_session_id",
    "agent_pid", "agent_pgid", "registered_at", "record_lost_wake",
})


def host_registry_path(project_root: str) -> Path:
    return Path(project_root) / ".kaola" / "host-registry.json"


def _host_registry_doc(project_root: str) -> dict[str, Any]:
    """The registry document, or ``{}`` when missing or not this schema."""
    try:
        doc = json.loads(host_registry_path(project_root).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if (not isinstance(doc, dict) or doc.get("schema") != HOST_REGISTRY_SCHEMA
            or not isinstance(doc.get("hosts"), dict)):
        return {}
    return doc


def _host_registry_update(project_root: str, fn: Any) -> Any:
    """``fn(hosts) -> (changed, result)`` under the registry flock; a changed
    hosts map is stored atomically (0600) before the lock releases."""
    import fcntl
    kaola_dir = Path(project_root) / ".kaola"
    kaola_dir.mkdir(exist_ok=True)
    lock_path = kaola_dir / "host-registry.lock"
    with open(lock_path, "a+b") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        doc = _host_registry_doc(project_root)
        hosts = {key: value for key, value in doc.get("hosts", {}).items()
                 if isinstance(value, dict)}
        changed, result = fn(hosts)
        if changed:
            _webhook_atomic_json(host_registry_path(project_root),
                                 {"schema": HOST_REGISTRY_SCHEMA, "hosts": hosts})
        return result


def host_registry_register(project_root: str, row: dict[str, Any]) -> bool:
    """Insert or replace the row for ``platform/session``. Best effort: a
    registry that cannot be written returns False and the receipt notes the
    gap; the start itself already went out."""
    key = f"{row.get('platform')}/{row.get('session')}"
    row = {k: v for k, v in row.items()
           if k in HOST_REGISTRY_ROW_KEYS and v is not None}
    row["repo"] = os.path.realpath(row.get("repo") or project_root)
    row["registered_at"] = _utc_stamp()

    def op(hosts: dict[str, Any]) -> tuple[bool, None]:
        hosts[key] = row
        return True, None

    try:
        _host_registry_update(project_root, op)
    except OSError:
        return False
    return True


def _registry_row_project(row: dict[str, Any], project_root: str) -> bool:
    try:
        return os.path.realpath(row.get("repo") or "") == os.path.realpath(project_root)
    except (OSError, TypeError):
        return False


def host_registry_row(project_root: str, platform: Any,
                      session: Any) -> dict[str, Any] | None:
    """This session's row, or None. A row naming another project is not ours."""
    row = _host_registry_doc(project_root).get("hosts", {}).get(
        f"{platform}/{session}")
    if (not isinstance(row, dict) or row.get("platform") != platform
            or row.get("session") != session
            or not _registry_row_project(row, project_root)):
        return None
    return row


def host_registry_deregister(project_root: str, platform: Any, session: Any,
                             holder_instance_id: Any = None) -> bool:
    """Drop the row a recorded clean stop retires. ``holder_instance_id``
    guards against removing a newer start's row; None removes it outright."""
    if not isinstance(platform, str) or not isinstance(session, str):
        return False
    key = f"{platform}/{session}"

    def op(hosts: dict[str, Any]) -> tuple[bool, bool]:
        row = hosts.get(key)
        if not isinstance(row, dict):
            return False, True
        if (holder_instance_id is not None
                and isinstance(row.get("holder_instance_id"), str)
                and row["holder_instance_id"] != holder_instance_id):
            return False, False
        del hosts[key]
        return True, True

    try:
        return _host_registry_update(project_root, op)
    except OSError:
        return False


def _record_loss_recovery(row: dict[str, Any], holder_alive: bool) -> dict[str, Any]:
    """The executable recovery path for a lost record: an argv-verified
    ``stop --force`` sweeps the orphan holder, then ``start --resume`` on the
    recorded native session id starts a clean one."""
    platform = row.get("platform")
    session = row.get("session")
    repo = row.get("repo")
    acp_session_id = row.get("acp_session_id")
    resume = f"kaola-acp.py {platform} start --repo {repo} --session {session}"
    if isinstance(acp_session_id, str) and acp_session_id:
        resume += f" --resume {acp_session_id}"
    recovery: dict[str, Any] = {
        "resume": resume,
        "acp_session_id": acp_session_id if isinstance(acp_session_id, str) else None,
        "record_dir": row.get("record_dir"),
        "socket_path": row.get("socket_path"),
        "holder_pid": row.get("holder_pid"),
        "holder_pid_alive": holder_alive,
        "agent_pid": row.get("agent_pid"),
        "agent_pgid": row.get("agent_pgid"),
        "registered_at": row.get("registered_at"),
    }
    if holder_alive:
        recovery["orphan_sweep"] = (
            f"kaola-acp.py {platform} stop --repo {repo} --session {session} --force"
            "  (sweeps the argv-verified orphan; run it before the resume)")
    return recovery


def _record_loss_wake(project_root: str, row: dict[str, Any]) -> dict[str, Any]:
    """Spawn the deliver child for this row's ``record_lost`` wake. The caller
    already marked the row under the registry lock, and the webhook claims
    file independently refuses a repeat POST of this (id, seq) pair."""
    holder_instance_id = row.get("holder_instance_id")
    if (not isinstance(holder_instance_id, str) or not holder_instance_id
            or not isinstance(row.get("session"), str)):
        return {"sent": False, "reason": "registry-row-incomplete"}
    payload = {
        "schema": DELEGATOR_WEBHOOK_PAYLOAD_SCHEMA,
        "project": row.get("repo") or project_root,
        "session": row["session"],
        "holder_instance_id": holder_instance_id,
        "event_seq": RECORD_LOSS_WAKE_SEQ,
        "state": "error",
        "state_detail": "record_lost",
        "reason": "holder_lost",
        "ts": _utc_stamp(),
    }
    try:
        proc = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()),
             "delegator-webhook", "deliver"],
            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, start_new_session=True,
            close_fds=True, cwd=project_root)
        assert proc.stdin is not None
        proc.stdin.write(json.dumps(payload).encode("utf-8"))
        proc.stdin.close()
    except Exception as exc:
        return {"sent": False, "reason": "spawn-failed",
                "error": type(exc).__name__}
    return {"sent": True, "holder_instance_id": holder_instance_id,
            "event_seq": RECORD_LOSS_WAKE_SEQ, "state_detail": "record_lost"}


def _record_loss_wake_marked(project_root: str, row: dict[str, Any]) -> dict[str, Any]:
    """Emit the one record-loss wake for this row. The registry mark and the
    webhook claims file keep it exactly once per holder_instance_id; a row
    already marked reports ``already-recovered``."""
    key = f"{row.get('platform')}/{row.get('session')}"

    def op(hosts: dict[str, Any]) -> tuple[bool, Any]:
        current = hosts.get(key)
        if not isinstance(current, dict):
            return False, {"sent": False, "reason": "registry-row-gone"}
        prior = current.get("record_lost_wake")
        if isinstance(prior, dict):
            return False, {"sent": False, "reason": "already-recovered",
                           "event_seq": prior.get("event_seq")}
        current["record_lost_wake"] = {
            "event_seq": RECORD_LOSS_WAKE_SEQ, "at": _utc_stamp()}
        return True, None

    try:
        marked = _host_registry_update(project_root, op)
    except OSError:
        # Mirror recover_host_death_wake: an unrecorded wake is not sent; the
        # next scan retries the mark.
        return {"sent": False, "reason": "death-wake-unrecorded"}
    if marked is not None:
        return marked
    return _record_loss_wake(project_root, row)


def _record_loss_refresh(row: dict[str, Any], record: dict[str, Any]) -> bool:
    """Reconcile a registry row with a live record for the same session. A
    different holder_instance_id is a newer start: refresh the identity facts
    and reset the wake allowance, which is per holder_instance_id."""
    changed = False
    holder_instance_id = record.get("holder_instance_id")
    if (isinstance(holder_instance_id, str) and holder_instance_id
            and holder_instance_id != row.get("holder_instance_id")):
        row.pop("record_lost_wake", None)
        row["holder_instance_id"] = holder_instance_id
        changed = True
    for key in ("holder_pid", "agent_pid", "agent_pgid", "acp_session_id",
                "socket_path"):
        value = record.get(key)
        if value is not None and row.get(key) != value:
            row[key] = value
            changed = True
    return changed


def stop_record_lost(args: argparse.Namespace, repo: str,
                     row: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    """``stop`` on a session whose record dir is gone but whose registry row
    survives (Issue #359). The holder pid is signalled only under ``--force``
    and only when its argv still anchors to the lost record dir; a PID reuse
    is never signalled. The owed holder_lost wake is emitted once either way.
    """
    receipt = base_receipt(args, repo)
    expected = params.get("expected_holder_instance_id")
    actual = row.get("holder_instance_id")
    if expected is not None and actual is not None and expected != actual:
        receipt["error"] = {
            "code": "holder-instance-mismatch",
            "expected_holder_instance_id": expected,
            "holder_instance_id": actual,
        }
        receipt.update(mutation_status="not_started", mutation_performed=False)
        return receipt
    pid = row.get("holder_pid")
    alive = pid_alive(pid)
    receipt["record_lost"] = _record_loss_recovery(row, alive)
    if alive and not params.get("force"):
        receipt["error"] = {
            "code": "record-lost",
            "message": "the session record is gone and the registered holder "
                       "pid is a live orphan; rerun stop with --force to sweep it",
            "holder_pid": pid,
            "holder_instance_id": actual,
        }
        receipt.update(mutation_status="not_started", mutation_performed=False)
        return receipt
    anchor = holder_argv_anchor(pid, Path(row["record_dir"])) \
        if alive and isinstance(row.get("record_dir"), str) else False
    if alive and anchor is None:
        receipt["error"] = {
            "code": "holder-unreachable",
            "message": "holder pid alive but its argv is unreadable; no "
                       "identity anchor, nothing signalled; stop it from an "
                       "unsandboxed shell",
            "holder_pid": pid,
        }
        receipt.update(mutation_status="not_started", mutation_performed=False)
        return receipt
    killed: list[int] = []
    if anchor is True:
        try:
            os.kill(pid, signal.SIGKILL)
            killed.append(pid)
        except (ProcessLookupError, PermissionError):
            pass
        deadline = time.monotonic() + 5.0
        while killed and pid_alive(pid) and time.monotonic() < deadline:
            time.sleep(0.05)
    death_wake = _record_loss_wake_marked(repo, row)
    if death_wake is not None:
        receipt["delegator_death_wake"] = death_wake
    host_registry_deregister(repo, args.platform, args.session,
                             holder_instance_id=actual)
    stopped = not alive or anchor is False or not pid_alive(pid)
    receipt.update(stopped=stopped, holder_lost=True, record_lost=True,
                   holder_pid=pid,
                   force_killed_pids=killed,
                   residual_pids=[pid] if alive and anchor is True and not stopped else [])
    if alive and anchor is False:
        receipt["pid_reused"] = True
    return receipt


def _record_loss_present_record(row: dict[str, Any], project_root: str,
                                dirs: list[Path] | None) -> dict[str, Any] | None:
    """This row's surviving record among ``dirs``, or None. A record for the
    same (platform, session) but another repo does not count (Issue #359)."""
    if not dirs:
        return None
    for directory in dirs:
        try:
            record = read_record(directory)
        except OSError:
            continue
        if isinstance(record, dict) and _webhook_same_project(record, project_root):
            return record
    return None


def _record_loss_list(project_root: str,
                      present: dict[tuple[str, str], list[Path]]) -> list[dict[str, Any]]:
    """This repo's registry rows whose session has no record.json under any
    record root (Issue #359). Read-only: no prune and no wake."""
    lost = []
    for row in _host_registry_doc(project_root).get("hosts", {}).values():
        platform = row.get("platform")
        session = row.get("session")
        if (not isinstance(platform, str) or not isinstance(session, str)
                or not _registry_row_project(row, project_root)):
            continue
        if _record_loss_present_record(
                row, project_root, present.get((platform, session))) is not None:
            continue
        lost.append({
            "platform": platform, "session": session,
            "repo": row.get("repo"),
            "record_lost": True,
            "holder_pid": row.get("holder_pid"),
            "holder_pid_alive": pid_alive(row.get("holder_pid")),
            "holder_instance_id": row.get("holder_instance_id"),
            "acp_session_id": row.get("acp_session_id"),
            "wake_reported": isinstance(row.get("record_lost_wake"), dict),
            "transport": "acp",
        })
    return sorted(lost, key=lambda r: (r["platform"], r["session"]))


def _record_loss_scan(project_root: str,
                      present: dict[tuple[str, str], list[Path]]) -> dict[str, Any]:
    """Registry cross-check for ``delegator-webhook status`` (Issue #359).

    A row whose (platform, session) has no record.json under any record root
    is a host whose record was lost since registration; it gets its one
    ``record_lost``/``holder_lost`` wake. A row with a ``stopped`` record
    retires; a newer holder_instance_id refreshes its facts."""
    def evaluate(hosts: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        changed = False
        send: list[tuple[dict[str, Any], dict[str, Any]]] = []
        lost: list[dict[str, Any]] = []
        for key in sorted(hosts):
            row = hosts[key]
            platform = row.get("platform")
            session = row.get("session")
            if (not isinstance(platform, str) or not isinstance(session, str)
                    or not _registry_row_project(row, project_root)):
                continue
            record = _record_loss_present_record(
                row, project_root, present.get((platform, session)))
            if record is not None:
                if record.get("state") == "stopped":
                    del hosts[key]
                    changed = True
                    continue
                if _record_loss_refresh(row, record):
                    changed = True
                continue
            alive = pid_alive(row.get("holder_pid"))
            finding = {
                "session": session,
                "platform": platform,
                "holder_instance_id": row.get("holder_instance_id"),
                "record_lost": True,
                "holder_pid_alive": alive,
                "registered_at": row.get("registered_at"),
                "recovery": _record_loss_recovery(row, alive),
            }
            prior = row.get("record_lost_wake")
            if isinstance(prior, dict):
                finding["delegator_death_wake"] = {
                    "sent": False, "reason": "already-recovered",
                    "event_seq": prior.get("event_seq")}
            else:
                row["record_lost_wake"] = {
                    "event_seq": RECORD_LOSS_WAKE_SEQ, "at": _utc_stamp()}
                changed = True
                send.append((row, finding))
            lost.append(finding)
        return changed, {"send": send, "lost": lost}

    try:
        result = _host_registry_update(project_root, evaluate)
    except OSError:
        return {"scan": "registry-unavailable", "lost": []}
    for row, finding in result["send"]:
        # The deliver child spawns outside the registry lock; the row mark is
        # already durable, so a spawn failure stays exactly-once recorded.
        finding["delegator_death_wake"] = _record_loss_wake(project_root, row)
    return {"scan": "complete", "lost": result["lost"]}


def _op_or_holder_lost(args: argparse.Namespace, repo: str, directory: Path,
                       op: str, params: dict[str, Any],
                       timeout: float | None) -> dict[str, Any]:
    sock = sock_path(args, repo)
    record = read_record(directory)
    if record and not pid_alive(record.get("holder_pid")):
        if op == "stop":
            refused = holder_instance_mismatch_receipt(
                args, repo, directory, record, params, op)
            if refused is not None:
                return refused
            return force_kill_from_record(args, repo, record)
        return holder_lost_receipt(args, repo, record)
    if not sock.exists():
        if record is None:
            # Issue #359: a record dir can be wiped while its holder lives.
            # A surviving registry row proves a Host ran here: report
            # record-lost with the recovery path instead of a bare no-session;
            # a stop is the orphan sweep.
            row = host_registry_row(repo, args.platform, args.session)
            if row is not None:
                if op == "stop":
                    return stop_record_lost(args, repo, row, params)
                receipt = base_receipt(args, repo)
                receipt["error"] = {
                    "code": "record-lost",
                    "message": "the ACP session record registered for this "
                               "platform/session/repo is gone; the holder may "
                               "still run as an orphan",
                    "holder_pid": row.get("holder_pid"),
                    "holder_instance_id": row.get("holder_instance_id"),
                }
                receipt["record_lost"] = _record_loss_recovery(
                    row, pid_alive(row.get("holder_pid")))
                return receipt
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
    # Issue #408: a heartbeat-bound seat refuses a mutating op whose caller
    # did not name this holder instance. The record says whether the seat is
    # bound; when it is, the CLI fills the still-optional field from the same
    # record the caller verified, so an omitted flag no longer skips the
    # binding while an explicit flag still wins. Unbound records keep the
    # documented caller-asserted behavior.
    if (op in BOUND_WRITE_OPS and record is not None
            and isinstance(record.get("heartbeat_host"), dict)
            and "expected_holder_instance_id" not in params
            and isinstance(record.get("holder_instance_id"), str)):
        params = dict(params, expected_holder_instance_id=record["holder_instance_id"])
    response = socket_request(sock, op, params, timeout, directory=directory)
    wire_error = response.get("error")
    wire_code = (wire_error.get("code")
                 if isinstance(wire_error, dict) else None)
    if (wire_code == "unauthenticated" and op == "stop"
            and params.get("force") and record is not None
            and acp_paths.read_auth_token(directory) is None):
        # Issue #408: a deleted auth.token must not lock out stop --force.
        # This caller cannot present the capability at all, and a same-UID
        # caller can already SIGKILL — the argv-verified path inside still
        # proves the live PID is this record's holder before it is
        # signalled. A presented-but-wrong token stays the honest refusal.
        return force_stop_unreachable(args, repo, directory, record, params)
    if wire_code in ("holder-unreachable", "holder-timeout"):
        if record and not pid_alive(record.get("holder_pid")):
            if op == "stop":
                refused = holder_instance_mismatch_receipt(
                    args, repo, directory, record, params, op)
                if refused is not None:
                    return refused
                return force_kill_from_record(args, repo, record)
            if wire_code == "holder-timeout":
                # Issue #383: a timeout is this request's transport fact, not
                # the previous prompt's mutation. Keep the stage and add the
                # death fact; converting to holder-lost would borrow a
                # historical mutation claim (#379).
                receipt = base_receipt(args, repo)
                receipt.update(response)
                receipt["holder_alive"] = False
                _stamp_timeout_verification(receipt, args, repo, op, params)
                return _scope_transport_mutation(receipt, op)
            lost = holder_lost_receipt(args, repo, record)
            # This death was discovered after the wire attempt, so the
            # pre-check's "definitely unsent" no longer applies.
            if op in PROMPT_STEER_OPS:
                lost["_wire_attempted"] = True
            # Issue #383 puts connect/send/read on the wire error; keep it so
            # a read-stage holder death is not misread as definitely unsent.
            stage = (response.get("error") or {}).get("stage")
            error = lost.get("error")
            if isinstance(error, dict) and isinstance(stage, str) and stage:
                error["stage"] = stage
            return lost
        if record and op == "stop" and params.get("force"):
            # Issue #383: a wedged holder must remain force-stoppable. The
            # timeout is the same unreachable answer for this recovery branch;
            # the probe inside still refuses to signal an answering instance.
            return force_stop_unreachable(args, repo, directory, record, params)
    receipt = base_receipt(args, repo)
    receipt.update(response)
    _stamp_timeout_verification(receipt, args, repo, op, params)
    _scope_transport_mutation(receipt, op)
    if record is None:
        # Issue #359: the socket answers (or is stale) while the record dir is
        # gone. Attach the loss fact so status stays honest about bookkeeping.
        row = host_registry_row(repo, args.platform, args.session)
        if row is not None:
            receipt["record_lost"] = _record_loss_recovery(
                row, pid_alive(row.get("holder_pid")))
    return receipt


def _scope_transport_mutation(receipt: dict[str, Any], op: str) -> dict[str, Any]:
    """Keep a transport mutation claim only on a call that can mutate.

    ``status``, ``observe``, ``capture`` and ``wait`` must not grow a
    ``mutation_performed`` key from a failed read; ``cancel``, ``permit``,
    ``stop``, ``wake_delegator`` and the prompt/steer family do (Issue #383).
    """
    if op in MUTATING_OPS:
        return receipt
    # A successful ``wait``/``status``/``capture`` reply may legitimately carry
    # the turn's own ``mutation_status``; only a transport failure would grow a
    # claim about a write this read-only call never made.
    if not isinstance(receipt.get("error"), dict):
        return receipt
    receipt.pop("mutation_performed", None)
    receipt.pop("mutation_status", None)
    return receipt


def _stamp_timeout_verification(receipt: dict[str, Any],
                                args: argparse.Namespace, repo: str,
                                op: str, params: dict[str, Any]
                                ) -> dict[str, Any]:
    """Issue #383: give a read-stage timeout an actionable, text-free check.

    The request text is never copied into the receipt; only its fingerprint and
    the command that can prove a late admission are added. ``status`` can still
    show the previous (or empty) turn while an admission is in progress: the
    holder publishes a turn only after the agent frame is written (#381), so
    ``turn_active: false`` is not proof that this request was not delivered.
    """
    error = receipt.get("error")
    if not isinstance(error, dict) or error.get("code") != "holder-timeout":
        return receipt
    if op not in PROMPT_STEER_OPS:
        return receipt
    text = params.get("text")
    if isinstance(text, str):
        fingerprint = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
        key = ("steer_fingerprint" if op in ("steer", "steer_interrupt")
               else "prompt_fingerprint")
        receipt.setdefault(key, fingerprint)
    if error.get("stage") != "read":
        # Connect/send already prove nothing was written; only a read timeout
        # can be admitted late and needs a verify route.
        return receipt
    if op == "steer":
        # A native steer is not a prompt turn: status has no steer field. The
        # existing event log has the write (steer_sent: request_id +
        # fingerprint) and the answer (steer_result: request_id, outcome,
        # consumed, confirmation). Match those, never a bare "sent".
        receipt.setdefault("verify", {
            "command": (f"kaola-acp {args.platform} capture --repo {repo} "
                        f"--session {args.session} --since 0"),
            "match": ("events[]: steer_sent.fingerprint == steer_fingerprint, "
                      "then steer_result for that request_id "
                      "(steer_outcome/steer_consumed/steer_confirmation)"),
            "note": ("A read-stage steer timeout may still have been written. "
                     "Find the steer_sent event by fingerprint, then its "
                     "steer_result: an accepted write is not proof of "
                     "consumption. Do not resend before reading capture."),
            "do_not": ("resend, or treat steer_sent/written as consumed, "
                       "before reading the event"),
        })
        return receipt
    note = ("A read-stage timeout may still be admitted. Check status and "
            "capture before deciding; turn_active:false while admission is "
            "in progress is not proof of non-delivery.")
    if op == "steer_interrupt":
        note = ("An interrupt is a cancel followed by a prompt carrying this "
                "steer text, so the follow-up prompt's fingerprint is this "
                "steer's fingerprint. If no follow-up prompt appears, read "
                "capture's steer_interrupt event; do not resend blindly.")
    receipt.setdefault("verify", {
        "command": (f"kaola-acp {args.platform} status --repo {repo} "
                    f"--session {args.session}"),
        "match": "last_prompt.fingerprint",
        "note": note,
        "do_not": "resend before checking status/capture",
    })
    return receipt


def op_or_holder_lost(args: argparse.Namespace, repo: str, directory: Path,
                      op: str, params: dict[str, Any],
                      timeout: float | None) -> dict[str, Any]:
    """Issue #379: only prompt/steer answers are stamped for this request."""
    return _stamp_request_mutation(
        _op_or_holder_lost(args, repo, directory, op, params, timeout), op)


SPAWN_RECORD_TOLERANCE = 5.0
PRESERVE_FEATURE = "preserve-dispatched/1"
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


def recorded_groups(record: dict[str, Any], directory: Path | None = None,
                    verified_only: bool = False, preserve_dispatched: bool = False) -> list[int]:
    """The agent's own process group plus the out-of-group child groups the
    holder noted while the agent was alive (detached CLI children), plus the
    children the agent itself recorded at spawn in ``children.jsonl`` under
    the record directory. A child group counts only while a recorded member
    pid is still alive in that group with its recorded start time (holder
    note) or a start time at or before the recorded spawn and within
    SPAWN_RECORD_TOLERANCE of it
    (spawn record), so a reused pid or group id is never touched.

    Issue #191: ``verified_only`` is for callers that signal. The agent group
    then counts only while its live leader is the recorded agent by start
    time, exactly: the holder recorded ``agent_started`` from the same
    second-resolution ``lstart``. A record without ``agent_started`` or a
    leaderless group proves no identity (macOS reuses a pgid once its group
    empties)."""
    groups: list[int] = []
    pgid = record.get("agent_pgid")
    agent_started = record.get("agent_started")
    checked = (isinstance(agent_started, (int, float)) and not isinstance(agent_started, bool)
               and agent_started > 0)
    if isinstance(pgid, int) and pgid > 0 and not checked and not verified_only:
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
        if leader is None:
            if not verified_only:
                groups.append(pgid)
        elif leader[0] == pgid:
            try:
                leader_started = time.mktime(time.strptime(leader[1], "%a %b %d %H:%M:%S %Y"))
            except ValueError:
                leader_started = None
            # Both sides are epochs in their own process's time zone, so a
            # caller under another TZ than the holder still matches.
            slack = 0.0 if verified_only else 1.0
            if leader_started is not None and abs(leader_started - agent_started) <= slack:
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
    if (record.get("session_role") in ("sideagent", "sidekick", "host") or preserve_dispatched) and groups:
        # Issue #255/#361: workers a Sideagent dispatched and seats a Host
        # opened keep running when it is stopped or replaced; each has its own
        # exact stop. Only this script's `start` appends to the spawn record,
        # so a verified entry is a Runner holder this agent started; a live
        # holder whose own record names this agent's holder as dispatcher is
        # one too. Its whole process tree is kept.
        kept = dispatched_worker_groups(spawned, record.get("holder_instance_id"))
        groups = [group for group in groups if group not in kept]
    return groups


_RECORD_CONTRACT: Any = None


def _record_contract() -> Any:
    """Sibling record contract, or None when this copy does not ship it."""
    global _RECORD_CONTRACT
    if _RECORD_CONTRACT is False:
        return None
    if _RECORD_CONTRACT is None:
        path = SCRIPT_DIR / "kaola-record-contract.py"
        spec = importlib.util.spec_from_file_location("kaola_record_contract_acp", path)
        if not path.is_file() or spec is None or spec.loader is None:
            _RECORD_CONTRACT = False
            return None
        module = importlib.util.module_from_spec(spec)
        previous = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        try:
            spec.loader.exec_module(module)
        finally:
            sys.dont_write_bytecode = previous
        _RECORD_CONTRACT = module
    return _RECORD_CONTRACT


def _seat_exempt_record(record: Any) -> bool:
    """Issue #303 predicate. False when the sibling contract is absent."""
    module = _record_contract()
    predicate = getattr(module, "seat_exempt_record", None) if module is not None else None
    return bool(predicate(record)) if predicate is not None else False


def holders_dispatched_by(holder_instance_id: Any) -> list[int]:
    """Live Runner holders whose own record (under their own argv
    ``--record-dir``, naming them as ``holder_pid``) names this holder
    instance as ``dispatcher``. ``KAOLA_ACP_DISPATCHER`` reaches a worker
    start where the spawn-record variable does not (the ZCode bridge
    forwards only its allowlist), so this needs no spawn line.

    A seat-exempt record (``session_role`` ``sideagent`` or legacy
    ``sidekick``) is not a live seat. A worker record (``expert``,
    ``elite``, ``worker``, or no role) stays in the set.
    """
    if not isinstance(holder_instance_id, str) or not holder_instance_id:
        return []
    found = []
    for line in run_ps(["pid", "command"], env=PS_ENV).stdout.splitlines():
        fields = line.strip().split(None, 1)
        if len(fields) != 2 or not fields[0].isdigit() or "kaola-acp-holder" not in fields[1]:
            continue
        match = HOLDER_RECORD_DIR.search(f" {fields[1]} ")
        if match is None:
            continue
        try:
            worker = json.loads((Path(match.group(1)) / "record.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(worker, dict) or _seat_exempt_record(worker):
            continue
        dispatcher = worker.get("dispatcher")
        if (worker.get("holder_pid") == int(fields[0]) and isinstance(dispatcher, dict)
                and dispatcher.get("holder_instance_id") == holder_instance_id):
            found.append(int(fields[0]))
    return found


def dispatched_worker_groups(spawned: list[dict[str, Any]], holder_instance_id: Any = None) -> set[int]:
    """Issue #255: every process group of each Runner worker in ``spawned``
    whose spawn identity (pid, pgid, spawn time) still holds, or whose own
    live record names ``holder_instance_id`` as dispatcher: the holder's
    group, each group a live descendant runs in (the native agent leads its
    own session, its tools may too), and the agent and child groups that
    worker's own record attests while a recorded member identity holds."""
    rows: list[tuple[int, int, int, str]] = []
    for line in run_ps(["pid", "ppid", "pgid", "state", "lstart"], env=PS_ENV).stdout.splitlines():
        fields = line.split(None, 4)
        if (len(fields) == 5 and all(field.isdigit() for field in fields[:3])
                and not fields[3].upper().startswith("Z")):
            rows.append((int(fields[0]), int(fields[1]), int(fields[2]), fields[4].strip()))
    by_pid = {pid: (pgid, started) for pid, _, pgid, started in rows}
    children: dict[int, list[tuple[int, int]]] = {}
    for pid, ppid, pgid, _ in rows:
        children.setdefault(ppid, []).append((pid, pgid))

    def epoch(text: str) -> float | None:
        try:
            return time.mktime(time.strptime(text, "%a %b %d %H:%M:%S %Y"))
        except ValueError:
            return None

    roots: dict[int, int] = {}
    for entry in spawned:
        pid, pgid, spawned_at = entry.get("pid"), entry.get("pgid"), entry.get("spawned_at")
        if not (isinstance(pid, int) and isinstance(pgid, int) and isinstance(spawned_at, (int, float))):
            continue
        live = by_pid.get(pid)
        started = epoch(live[1]) if live and live[0] == pgid else None
        if started is None or not -SPAWN_RECORD_SLACK <= spawned_at / 1000.0 - started <= SPAWN_RECORD_TOLERANCE:
            continue
        roots[pid] = pgid
    for pid in holders_dispatched_by(holder_instance_id):
        if pid in by_pid:
            roots.setdefault(pid, by_pid[pid][0])
    kept: set[int] = set()
    for pid, pgid in roots.items():
        kept.add(pgid)
        stack, seen = [pid], {pid}
        while stack:
            for child, group in children.get(stack.pop(), []):
                if child not in seen:
                    seen.add(child)
                    stack.append(child)
                    kept.add(group)
        paths = holder_argv_paths(pid)
        try:
            worker = json.loads((Path(paths[0]) / "record.json").read_text(encoding="utf-8")) if paths else None
        except (OSError, ValueError):
            worker = None
        if not isinstance(worker, dict) or worker.get("holder_pid") != pid:
            continue
        agent_pgid, agent_started = worker.get("agent_pgid"), worker.get("agent_started")
        leader = by_pid.get(agent_pgid) if isinstance(agent_pgid, int) else None
        if (leader is not None and leader[0] == agent_pgid
                and isinstance(agent_started, (int, float)) and not isinstance(agent_started, bool)):
            leader_started = epoch(leader[1])
            if leader_started is not None and abs(leader_started - agent_started) <= SPAWN_RECORD_SLACK:
                kept.add(agent_pgid)
        for child, members in (worker.get("agent_child_groups") or {}).items():
            if str(child).isdigit() and any(
                    str(member).isdigit() and by_pid.get(int(member)) == (int(child), started_text)
                    for member, started_text in (members or {}).items()):
                kept.add(int(child))
    return kept


def live_group_members(groups: list[int]) -> list[int]:
    members = run_ps(["pid", "pgid", "state"])
    found: list[int] = []
    for line in members.stdout.splitlines():
        fields = line.split()
        if (len(fields) == 3 and fields[0].isdigit() and fields[1].isdigit()
                and int(fields[1]) in groups and not fields[2].upper().startswith("Z")):
            found.append(int(fields[0]))
    return found


def unverified_agent_group(record: dict[str, Any], groups: list[int]) -> dict[str, Any] | None:
    """Issue #191: the recorded agent pgid when it still has live members but
    is not among the identity-verified ``groups``: never signalled."""
    pgid = record.get("agent_pgid")
    if not isinstance(pgid, int) or isinstance(pgid, bool) or pgid <= 0 or pgid in groups:
        return None
    members = live_group_members([pgid])
    if not members:
        return None
    return {"code": "pgid-identity-unverified", "agent_pgid": pgid,
            "agent_started": record.get("agent_started"), "live_members": members,
            "signalled": False,
            "message": "the recorded agent pgid has live members whose identity as this "
                       "session's agent group cannot be proven (no live leader with the "
                       "recorded start time): not signalled; the seat record is cleared"}


def retire_record(directory: Path, record: dict[str, Any], reason: str) -> Path | None:
    """Move ``record.json`` aside when it still is ``record``."""
    if read_record(directory) != record:
        return None
    retired = directory / f"record.{reason}-{int(time.time())}.json"
    try:
        (directory / "record.json").replace(retired)
    except OSError:
        return None
    return retired


def preserving(args: argparse.Namespace) -> bool:
    return bool(getattr(args, "preserve_dispatched_workers", False))


def preserve_refusal(args: argparse.Namespace, repo: str, directory: Path) -> dict[str, Any] | None:
    """Issue #255: a live holder that predates the preserve intent would
    ignore it and sweep the workers it dispatched, so the request is refused
    before anything is signalled. A dead holder is swept by this script, which
    honours the intent itself."""
    if not preserving(args):
        return None
    record = read_record(directory) or {}
    if not pid_alive(record.get("holder_pid")):
        return None
    if PRESERVE_FEATURE in (record.get("holder_features") or []):
        return None
    receipt = base_receipt(args, repo)
    receipt.update({"result": "refused", "reason": "preserve-unsupported",
                    "detail": f"the live holder does not advertise {PRESERVE_FEATURE}; "
                              "a stop now would end the workers it dispatched",
                    "mutation_status": "not_started", "mutation_performed": False})
    return receipt


def force_kill_from_record(args: argparse.Namespace, repo: str,
                           record: dict[str, Any]) -> dict[str, Any]:
    """Sweep a dead holder's identity-verified recorded groups.

    ``stop`` reaches this when the record's holder pid is already dead,
    with or without ``--force``. A foreign ``expected_holder_instance_id``
    is refused before this runs. Live members of the verified groups are
    SIGKILLed. ``--force`` is not required for that sweep.
    """
    groups = recorded_groups(record, spawn_record_dir(args, repo), verified_only=True,
                             preserve_dispatched=preserving(args))
    unverified = unverified_agent_group(record, groups)
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
    # Issue #299: before this record is retired or rewritten to `stopped`, a
    # dead Host holder that never signalled gets its one holder_lost wake.
    death_wake = recover_host_death_wake(directory, record)
    if death_wake is not None:
        receipt["delegator_death_wake"] = death_wake
    if unverified is not None:
        # Issue #191: a group this record cannot prove its own is someone
        # else's to stop. Only this seat's record is cleared.
        retired = retire_record(directory, record, "pgid-unverified") \
            if directory is not None and not leftover else None
        receipt["pgid_identity"] = "unverified"
        receipt["pgid_identity_unverified"] = unverified
        receipt["retired_record"] = str(retired) if retired else None
        return receipt
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
    refused = holder_instance_mismatch_receipt(
        args, repo, directory, record, params, "stop")
    if refused is not None:
        return refused
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
        groups = recorded_groups(record, directory, verified_only=True,
                                 preserve_dispatched=preserving(args))
        unverified = unverified_agent_group(record, groups)
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
        # Issue #299: the reused PID proves the holder died unsignalled; emit
        # its holder_lost wake before the record is retired.
        death_wake = recover_host_death_wake(directory, record)
        if death_wake is not None:
            receipt["delegator_death_wake"] = death_wake
        retired = retire_record(directory, record, "pid-reused") if not leftover else None
        try:
            sock_path(args, repo).unlink()
        except OSError:
            pass
        if unverified is not None:
            receipt["pgid_identity"] = "unverified"
            receipt["pgid_identity_unverified"] = unverified
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
    unauthenticated_refusal = False
    if sock is not None:
        if (state or {}).get("holder_instance_id") != record.get("holder_instance_id"):
            # Something answers there as another instance: never stop it on
            # this record's behalf, and never signal a holder that answers.
            receipt["error"] = {"code": "holder-instance-mismatch",
                                "expected_holder_instance_id": record.get("holder_instance_id"),
                                "holder_instance_id": (state or {}).get("holder_instance_id"),
                                "answering_socket": str(sock)}
            receipt.update(mutation_status="not_started", mutation_performed=False)
            return receipt
        # Issue #408: a bound seat gates this stop on its minted token and an
        # explicit instance id. The state reply already proved this socket's
        # holder is the recorded one, so fill the id from the record.
        stop_params = dict(params)
        if (isinstance(record.get("heartbeat_host"), dict)
                and "expected_holder_instance_id" not in stop_params
                and isinstance(record.get("holder_instance_id"), str)):
            stop_params["expected_holder_instance_id"] = record["holder_instance_id"]
        reply = socket_request(sock, "stop", stop_params, 30.0, directory)
        reply_error = reply.get("error")
        reply_code = (reply_error.get("code")
                      if isinstance(reply_error, dict) else None)
        if (reply_code != "unauthenticated"
                or acp_paths.read_auth_token(directory) is not None):
            receipt.update(reply)
            receipt["answering_socket"] = str(sock)
            return receipt
        # Issue #408: this bound seat refused a stop its caller could not
        # authenticate — no readable auth.token to present. The refusal
        # cannot lock out --force: the argv anchor already proved this live
        # PID is the record's holder and a same-UID caller can signal it
        # regardless, so fall to the verified kill. A presented-but-wrong
        # token would have returned the honest refusal above.
        unauthenticated_refusal = True
    # Silent on every socket it could use — a wedged holder — or answering
    # only to refuse a stop this caller cannot authenticate.
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
    if unauthenticated_refusal:
        receipt["unauthenticated_stop_fallback"] = True
        receipt["answering_socket"] = str(sock)
    receipt["holder_force_killed"] = holder_pid
    if pid_alive(holder_pid):
        receipt["residual_pids"] = sorted(set(receipt["residual_pids"]) | {holder_pid})
    return receipt


def declared_tiers(manifest: dict[str, str]) -> list[str]:
    """Issue #188: `default` plus this runtime's own named preset words."""
    words = [word.strip() for word in (manifest.get("named_tiers") or "").split(",")]
    return ["default"] + [word for word in words if word]


def tier_prefix(manifest: dict[str, str], tier: str) -> str:
    """The manifest key prefix a declared `--tier` value selects (`-` as `_`).

    Callers refuse an undeclared tier first (``tier_declared``)."""
    return tier.replace("-", "_") if tier in declared_tiers(manifest) else "default"


def tier_agent_command(args: argparse.Namespace) -> str:
    """Issue #140: the manifest ``acp_command_<prefix>`` of the selected tier.

    A preset the agent's ACP ``model`` option does not offer rides the spawn
    argv instead (devin ``--model``). Only when the tier preset is what
    selects the model (``resolve_selection``): an explicit ``--model`` or a
    preserved resume keeps the base ``acp_command``. Platforms that declare no
    such key fall through unchanged.
    """
    preserve = bool(args.resume or args.use_continue) and not (
        args.model or args.effort or args.tier
    )
    if args.model or preserve:
        return ""
    prefix = tier_prefix(args.manifest, args.tier or "default")
    return args.manifest.get(f"acp_command_{prefix}") or ""


def argv_model(command: str) -> str:
    """The model id the spawn argv itself passes as ``--model``, if any."""
    try:
        words = shlex.split(command)
    except ValueError:
        return ""
    for index, word in enumerate(words):
        if word == "--model" and index + 1 < len(words):
            return words[index + 1]
        if word.startswith("--model="):
            return word.split("=", 1)[1]
    return ""


def tier_declared(manifest: dict[str, str], tier: str | None) -> bool:
    """Whether this platform declares the requested tier at all."""
    return not tier or tier in declared_tiers(manifest)


def tier_refusal(args: argparse.Namespace, repo: str) -> dict[str, Any]:
    """Issue #111 typed refusal, in the Issue #105 shape: a tier this platform
    does not declare is named and rejected, never resolved to `default`."""
    tiers = declared_tiers(args.manifest)
    available = ", ".join(tiers[:-1]) + f", or {tiers[-1]}" if len(tiers) > 1 else "default only"
    receipt = base_receipt(args, repo, include_git=False)
    receipt.update({
        "result": "refused",
        "reason": "tier-not-declared",
        "action": args.command,
        "detail": (
            f"{args.platform} declares no --tier {args.tier}; "
            f"this platform's presets are {available}."
        ),
        "requested_tier": args.tier,
        "available_tiers": tiers,
        "mutation_performed": False,
        "mutation_status": "not_started",
    })
    return receipt


def fast_intent(args: argparse.Namespace) -> str:
    """The Fast state this invocation asked for: ``on`` or ``off``.

    Issue #181: ``--fast`` defaults to ``None`` so absence is distinguishable
    from an explicit ``off``, but "not passed" still means Fast off for every
    intent consumer and receipt.
    """
    return args.fast or "off"


def parse_model_components(raw: str) -> list[dict[str, Any]] | None:
    """Decode a manifest ``*_model_components`` string.

    Invalid or absent input is ``None``. This does not read native model IDs
    and does not strip suffixes to guess a name or an effort.
    """
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, list) or not parsed:
        return None
    components: list[dict[str, Any]] = []
    roles: list[str] = []
    for item in parsed:
        if not isinstance(item, dict):
            return None
        role = item.get("role")
        name = item.get("name")
        effort = item.get("effort")
        if role not in ("main", "sidekick") or not isinstance(name, str) or not name:
            return None
        if not isinstance(effort, str) or not effort:
            return None
        components.append({"role": role, "name": name, "effort": effort})
        roles.append(role)
    if roles.count("main") != 1 or len(roles) != len(set(roles)):
        return None
    return components


def resume_without_requested_tier(args: argparse.Namespace) -> bool:
    """A resume or continue that named no model, effort, or tier.

    That invocation keeps the saved native selection. The null tier is then
    the fact ``resume-without-tier``, not the fresh-start word ``default``.
    """
    return bool(args.resume or args.use_continue) and not (
        args.model or args.effort or args.tier
    )


def selection_basis(args: argparse.Namespace) -> dict[str, Any]:
    """What this invocation asked to launch, plus the preset display facts.

    Explicit ``--model`` wins over the tier preset. Explicit ``--effort`` wins
    over the preset's launch effort and attaches only to the model selected
    with it. A known ``--model`` may take its display name from an exact
    ``*_model_id`` match; that label does not assign the preset or its effort.
    A resume/continue without tier/model/effort preserves the native session
    and carries no display: a current name is a live option read, not inherited
    launch metadata. That path records no tier (``tier`` is null). It does not
    fill ``default``. Omitting those flags does not by itself claim that a prior
    applied model or effort is still effective; ``selection_continuity`` is that
    claim. Component metadata never becomes the launch effort.
    """
    manifest = args.manifest
    tier = args.tier or "default"
    preserve = resume_without_requested_tier(args)
    if args.model:
        return {
            "source": "user",
            "requested": args.model,
            "candidate": args.model,
            "effort": args.effort or "",
            "tier": tier,
            "display_name": quota_module().declared_display_name(manifest, args.model),
            "preset_id": None,
            "preset_effort": None,
            "components_raw": "",
        }
    if preserve:
        return {
            "source": "resume-preserved",
            "requested": "native saved session selection",
            "candidate": "",
            "effort": "",
            # No tier was requested. ``None`` stays null in the receipt; it is
            # not the fresh-start ``default`` fill above.
            "tier": None,
            "display_name": None,
            "preset_id": None,
            "preset_effort": None,
            "components_raw": "",
        }
    prefix = tier_prefix(manifest, tier)
    preset_effort = manifest.get(f"{prefix}_model_effort") or ""
    return {
        "source": f"runner-{tier}",
        "requested": manifest.get(f"{prefix}_model_name") or "",
        "candidate": manifest.get(f"{prefix}_model_id") or "",
        "effort": args.effort or preset_effort,
        "tier": tier,
        "display_name": manifest.get(f"{prefix}_model_name") or None,
        "preset_id": f"{args.platform}/{tier}",
        "preset_effort": preset_effort or None,
        "components_raw": manifest.get(f"{prefix}_model_components") or "",
    }


def model_display_fact(basis: dict[str, Any]) -> dict[str, Any]:
    """Consumer display for one invocation. Preset effort stays the declaration.

    ``name`` is the preset's display name, or the catalog label of an explicit
    native id when every matching ``*_model_id`` agrees. It stays null for an
    unknown id and for a preserved resume. ``preset_id`` and ``preset_effort``
    are set only when this invocation selected a preset. ``components`` is null
    when that preset declares none, when the declaration is unreadable, or when
    no preset was selected.
    """
    return {
        "name": basis.get("display_name"),
        "preset_id": basis.get("preset_id"),
        "preset_effort": basis.get("preset_effort"),
        "components": parse_model_components(str(basis.get("components_raw") or "")),
    }


def resolve_selection(args: argparse.Namespace, repo: str) -> dict[str, Any]:
    """Resolve tier/model/effort/Fast through the shared model-policy helper.

    Explicit --model wins over the selected tier preset; explicit --effort
    wins over the preset effort but only attaches to the model it was given
    with.  A resume/continue without tier/model/effort preserves the saved
    native session selection (no Runner model override).
    """
    basis = selection_basis(args)
    # A preserved resume has no tier. Pass an empty flag so the policy helper
    # records null, not the fresh-start word ``default``.
    tier = basis["tier"] if isinstance(basis["tier"], str) else ""
    source = basis["source"]
    requested = basis["requested"]
    candidate = basis["candidate"]
    effort = basis["effort"]
    manifest = args.manifest
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
                    "--fast", "true" if fast_intent(args) == "on" else "false",
                    "--tier", tier, "--fast-mechanism", mechanism,
                ],
                capture_output=True, text=True, timeout=45,
                env=agent_environment(args),
            )
            if out.returncode == 0:
                policy = json.loads(out.stdout)
        except (OSError, ValueError, subprocess.TimeoutExpired):
            policy = None
    if not isinstance(policy, dict):
        policy = {
            "requested_model_source": source,
            "requested_model_name": requested,
            "requested_tier": tier or None,
            "requested_fast": fast_intent(args),
            "resolved_runtime_model_id": candidate,
            "resolved_runtime_model_display": None,
            "resolved_parameters": {"effort": effort} if effort else {},
            "resolved_fast": "unknown",
            "model_evidence_provenance": {
                "requested": {"source": source, "name": requested},
                "selection": {"source": source, "tier": tier or None},
                "resolution": {
                    "state": "policy-helper-unavailable",
                    "candidate_id": candidate or None,
                    "resolved_id": candidate or None,
                },
            },
        }
    policy["model_display"] = model_display_fact(basis)
    policy["requested_effort"] = args.effort or None
    return policy


def merge_policy_evidence(receipt: dict[str, Any], policy: dict[str, Any]) -> None:
    for key in (
        "requested_model_source", "requested_model_name", "requested_tier",
        "requested_fast", "requested_effort", "resolved_runtime_model_id",
        "resolved_runtime_model_display", "resolved_parameters", "resolved_fast",
        "actual_runtime_model_id", "actual_parameters", "model_verified",
        "model_mismatch_reason", "model_evidence_provenance", "model_display",
    ):
        if key in policy:
            receipt[key] = policy[key]
    receipt["model_selection"] = {
        "source": policy.get("requested_model_source"),
        "tier": policy.get("requested_tier"),
        "requested_name": policy.get("requested_model_name"),
        "resolved_model": policy.get("resolved_runtime_model_id") or None,
        "resolved_effort": (policy.get("resolved_parameters") or {}).get("effort"),
        # ``preserved`` is not the bare-continuation branch. It stays false
        # until ``start`` proves the fresh readback equals the prior applied
        # selection (Issue #268). No prior applied selection, or an unreadable
        # readback, is not a silent true. ``override_omitted`` stays that
        # branch fact on its own, so a later resume can still find the last
        # applied selection.
        "preserved": False,
        "override_omitted": policy.get("requested_model_source") == "resume-preserved",
    }
    # Issue #316: a preserved resume omitted --tier. Say so. A silent null is
    # not a record that nobody requested a tier.
    if receipt["model_selection"]["override_omitted"]:
        receipt["model_selection"]["tier_reason"] = "resume-without-tier"


def parse_acp_model_map(raw: str) -> dict[str, str]:
    """Parse a manifest ``acp_model_map`` entry: ``id=value;id=value``.

    Maps resolved runtime model IDs (PTY picker IDs) onto the ACP option
    values the agent actually advertises for the same model — e.g. Cursor's
    ``grok-4.7-high`` onto ``grok-4.7[effort=high,fast=true]``.
    """
    return quota_module().parse_acp_model_map(raw)


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


def parse_config_id_candidates(raw: str) -> list[str]:
    """Parse an ordered ``a;b`` config-id candidate list (Issue #135)."""
    return [part.strip() for part in (raw or "").split(";") if part.strip()]


def resolve_config_id(candidates: list[str], state: Any) -> tuple[str, bool]:
    """The first candidate the agent advertises, else the first literally.

    Cursor's effort option id follows the selected model (grok-4.7
    ``reasoning_effort``, claude-fable-5-1 ``effort``), so the id is read
    from the options advertised after the model apply (Issue #135).
    """
    options = ((state.get("session_meta") or {}).get("configOptions")
               if isinstance(state, dict) else None)
    advertised = {option.get("id") for option in options or []
                  if isinstance(option, dict)} if isinstance(options, list) else set()
    for candidate in candidates:
        if candidate in advertised:
            return candidate, True
    return (candidates[0] if candidates else ""), False


def picker_effort_suffix(model_id: str) -> str:
    """Extract an effort encoded in a picker-style model ID.

    Picker IDs like ``grok-4.7-high`` or ``...-high-fast`` encode
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


def effort_applied_by_model_id(model_record: Any, applied_model: str, effort: str) -> bool:
    """Issue #331: an effort the accepted model ID already carries is applied.

    A platform with no effort config option (antigravity bakes effort into
    ``gemini-4-argon-{low,medium,high}``) applies the requested effort exactly
    when the model the agent accepted encodes that same effort as its suffix.
    An unapplied model, or a suffix that disagrees, proves nothing.
    """
    if not isinstance(model_record, dict) or model_record.get("applied") is not True:
        return False
    return bool(effort) and picker_effort_suffix(applied_model) == effort


def _effort_carried_by_model(application: Any) -> bool:
    entry = application.get("effort") if isinstance(application, dict) else None
    return isinstance(entry, dict) and entry.get("applied_via") == "model-id"


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
        "requested": fast_intent(args),
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
    error = bridge_runtime_error(args)
    if error is not None:
        receipt["error"] = error
        return receipt
    refused = codex_child_refusal(args, repo)
    if refused is not None:
        return refused
    probe_argv = [
        sys.executable, str(HOLDER), "--probe", "--repo", repo,
        "--platform", args.platform, "--command", args.agent_command,
        "--session-new-timeout", repr(session_new_timeout(args)),
    ]
    init_meta = parse_manifest_meta(args.manifest.get("acp_init_meta") or "")
    if init_meta:
        probe_argv += ["--init-meta", json.dumps(init_meta)]
    result = subprocess.run(
        probe_argv,
        capture_output=True, text=True, timeout=PROBE_WAIT + session_new_extra(args),
        env=agent_environment(args),
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


def steer_after_turn_refusal(args: argparse.Namespace, directory: Path) -> dict[str, Any] | None:
    """An older holder ignores delivery and would write a concurrent prompt.

    Apply only to this new delivery route, never to accepted native entries.
    This is a missing operation, not a version or ordinary drift restriction.
    """
    delivery = getattr(args, "delivery", None) or args.manifest.get("steering_delivery")
    if delivery != "after-turn":
        return None
    record = read_record(directory) or {}
    if not pid_alive(record.get("holder_pid")):
        return None
    if "steer-after-turn/1" in (record.get("holder_features") or []):
        return None
    return {"outcome": "steer_delivery_unavailable", "steer_outcome": "not_consumed",
            "steer_consumed": False, "steer_confirmation": "none",
            "mutation_status": (record.get("last_prompt") or {}).get("mutation_status"),
            "mutation_performed": False,
            "error": {"code": "steer-holder-outdated",
                      "message": "this live holder has no delivery-after-turn operation; it would "
                                 "write a concurrent prompt. Nothing was written. Keep ongoing work; "
                                 "adopt a new holder only at a safe restart boundary"}}


def client_message_id_unsupported(
    args: argparse.Namespace, repo: str, directory: Path | None,
) -> dict[str, Any] | None:
    """Issue #380: refuse an id a live pre-#380 holder cannot deduplicate.

    A dead holder is left to the ordinary transport path. The refusal is a
    pre-mutation fact for this request; the recovery route is an idle
    drain-restart, not a second holder.
    """
    if directory is None:
        return None
    record = read_record(directory) or {}
    if not pid_alive(record.get("holder_pid")):
        return None
    if CLIENT_MESSAGE_ID_FEATURE in (record.get("holder_features") or []):
        return None
    receipt = base_receipt(args, repo)
    receipt.update({
        "outcome": "client_message_id_unsupported",
        "mutation_status": "not_started",
        "mutation_performed": False,
        "client_message_id": getattr(args, "client_message_id", None),
        "holder_instance_id": record.get("holder_instance_id"),
        "error": {
            "code": "client-message-id-unsupported",
            "message": ("this live holder does not advertise client-message-id/1, so it "
                        "cannot deduplicate a supplied id; nothing was written. Wait "
                        "until this seat is idle, then drain-restart it. Do not start a "
                        "second holder"),
            "holder_instance_id": record.get("holder_instance_id"),
        },
    })
    return receipt


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
    directory = session_directory(args, platform, session, host_repo)
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
    directory = session_directory(args, target["platform"], target["session"], target["repo"])
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


def resolve_send_wait(args: argparse.Namespace, repo: str,
                      directory: Path) -> tuple[dict[str, Any], str | None]:
    """Resolve omission from existing records only; uncertainty stays blocking.

    No Host op/probe or heartbeat-file read. The worker's recorded dispatcher
    and carrier must name this exact live Host instance in this same repo.
    Return the worker holder id too, so admission keeps the existing exact-
    holder guard across a replacement between this read and the prompt.
    """
    if args.wait is not None:
        return {"wait": args.wait, "source": "explicit"}, None

    def blocking(detail: str) -> tuple[dict[str, Any], None]:
        return {"wait": True, "source": "standalone-default", "detail": detail}, None

    dispatcher, problem = dispatcher_identity()
    if problem or dispatcher is None:
        return blocking(problem or "no caller dispatcher identity")
    if (not host_capable(dispatcher["platform"])
            or dispatcher["repo"] != repo
            or not SESSION_PATTERN.fullmatch(dispatcher["session"])):
        return blocking("caller is not a Host candidate in the target repo")
    worker = read_record(directory)
    if not isinstance(worker, dict):
        return blocking("target record is missing or unusable")
    if any(worker.get(k) != v for k, v in
           {"platform": args.platform, "session": args.session, "repo": repo}.items()):
        return blocking("target record identity is missing or mismatched")
    owner = worker.get("dispatcher")
    if not isinstance(owner, dict) or any(owner.get(k) != dispatcher[k] for k in
                                         ("platform", "session", "repo", "holder_instance_id")):
        return blocking("target dispatcher does not prove this caller owns it")
    host_dir = session_directory(args, dispatcher["platform"], dispatcher["session"], dispatcher["repo"])
    target = {k: dispatcher[k] for k in ("platform", "session", "repo")}
    target["socket"] = str(sock_path_for_directory(host_dir))
    binding = worker.get("heartbeat_host")
    if not isinstance(binding, dict) or any(binding.get(k) != v for k, v in target.items()):
        return blocking("target heartbeat binding does not match this caller")
    host = read_record(host_dir)
    if not isinstance(host, dict):
        return blocking("caller record is missing or unusable")
    role = host.get("session_role")
    # Legacy records predate session_role. Reuse list/start's Host-class fact;
    # the exact dispatcher/record/binding checks still establish ownership.
    if role is None and host_session(dispatcher["platform"], host.get("session")):
        role = "host"
    if (any(host.get(k) != dispatcher[k] for k in
            ("platform", "session", "repo", "holder_instance_id"))
            or role != "host" or host.get("agent_alive") is not True):
        return blocking("caller record does not prove a live Host role and identity")
    problem = verify_dispatcher_host_live(args, dispatcher, target)
    if problem:
        return blocking(problem)
    holder_id = worker.get("holder_instance_id")
    if (not isinstance(holder_id, str) or not holder_id
            or not pid_alive(worker.get("holder_pid"))
            or not sock_path_for_directory(directory).exists()):
        return blocking("target holder identity or live transport is missing")
    return {"wait": False, "source": "owning-host-default"}, holder_id


def sideagent_host_anchor(args: argparse.Namespace, repo: str, dispatcher: dict[str, Any]
                          ) -> tuple[dict[str, Any] | None, str | None] | None:
    """Issue #255: where a Sideagent-dispatched worker sends its events.

    None when the dispatcher is not a Sideagent-role session. Otherwise the
    Host that Sideagent is itself bound to, so who dispatched (the Sideagent)
    and who receives events (the existing Host holder) stay separate facts,
    and a Sideagent replacement leaves its workers' carrier unchanged.
    Returns ``(target, None)`` or ``(None, failed check)``."""
    record = read_record(session_directory(args, dispatcher["platform"], dispatcher["session"], dispatcher["repo"]))
    if not isinstance(record, dict) or record.get("session_role") not in ("sideagent", "sidekick"):
        return None
    if (record.get("holder_instance_id") != dispatcher["holder_instance_id"]
            or not pid_alive(record.get("holder_pid"))):
        return None, "the dispatching Sideagent's own record is not its live holder"
    bound = record.get("heartbeat_host")
    if not isinstance(bound, dict) or not all(isinstance(bound.get(key), str) and bound[key]
                                              for key in ("platform", "session", "repo")):
        # An unbound Sideagent dispatches like any other session.
        return None
    if not host_capable(bound["platform"]):
        return None, f"the Sideagent's Host platform {bound['platform']} has no measured Host entry"
    target = validate_heartbeat_target(
        {key: bound[key] for key in ("platform", "session", "repo")}, args, repo, DISPATCHER_ENV)
    host = read_record(session_directory(args, target["platform"], target["session"], target["repo"]))
    role = host.get("session_role") if isinstance(host, dict) else None
    if role is None and isinstance(host, dict) and host_session(target["platform"], host.get("session")):
        role = "host"
    if not isinstance(host, dict) or role != "host" or not pid_alive(host.get("holder_pid")):
        return None, f"the Sideagent's Host {target['session']} has no live Host holder record"
    if not Path(target["socket"]).exists():
        return None, f"the Sideagent's Host admin socket is missing at {target['socket']}"
    return target, None


def command_rebind_host(args: argparse.Namespace, repo: str, directory: Path) -> dict[str, Any]:
    """Issue #255: a replacement Host takes an existing seat's carrier in place.

    Run from inside the live Host session: the target is that Host itself,
    proven by the same checks a dispatched start uses, so a Host can only
    re-anchor a seat to itself. The seat's agent and holder are unchanged."""
    def refused(detail: str) -> dict[str, Any]:
        receipt = base_receipt(args, repo, include_git=False)
        receipt.update({"result": "refused", "reason": "rebind-host-unresolved",
                        "action": "rebind-host", "detail": detail,
                        "mutation_performed": False, "mutation_status": "not_started"})
        return receipt

    dispatcher, problem = dispatcher_identity()
    if problem:
        return refused(problem)
    if dispatcher is None:
        return refused(f"run rebind-host inside the Host session; {DISPATCHER_ENV} is not set")
    if not host_capable(dispatcher.get("platform")):
        return refused(f"{dispatcher.get('platform')} has no measured Host entry")
    problem = repo_problem(dispatcher["repo"])
    if problem:
        return refused(f"dispatcher repo {dispatcher['repo']} {problem}")
    target = validate_heartbeat_target(
        {key: dispatcher[key] for key in ("platform", "session", "repo")}, args, repo, DISPATCHER_ENV)
    host = read_record(session_directory(args, target["platform"], target["session"], target["repo"])) or {}
    role = host.get("session_role")
    if role is None and host_session(target["platform"], host.get("session")):
        role = "host"
    if role != "host":
        return refused(f"{target['session']} is a {role or 'worker'} session, not a Host")
    failed = verify_dispatcher_host_live(args, dispatcher, target)
    if failed:
        return refused(failed)
    params: dict[str, Any] = {"target": target,
                              "host_holder_instance_id": dispatcher["holder_instance_id"]}
    if args.expected_holder_instance_id is not None:
        params["expected_holder_instance_id"] = args.expected_holder_instance_id
    receipt = op_or_holder_lost(args, repo, directory, "rebind_heartbeat_host", params, 10.0)
    receipt["action"] = "rebind-host"
    return receipt


def resolve_heartbeat_host(args: argparse.Namespace, repo: str) -> dict[str, Any]:
    """Resolve the notification target of this start (design #99 §a.2).

    Returns ``target`` (validated, socket-resolved, or None), ``source`` (``none``,
    ``explicit``, ``dispatcher``, ``dispatcher-no-carrier``, ``sideagent-host``,
    ``dispatcher-not-host``), ``dispatcher`` (the parsed identity fact when
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
    anchor = sideagent_host_anchor(args, repo, dispatcher)
    if anchor is not None:
        target, failed = anchor
        if failed:
            return {"target": None, "source": "sideagent-host", "dispatcher": dispatcher,
                    "requested": explicit,
                    "refusal": {"reason": "heartbeat-host-unresolved", "detail": failed}}
        if explicit is not None and any(explicit[key] != target[key]
                                        for key in ("platform", "session", "repo")):
            return {"target": None, "source": "explicit", "dispatcher": dispatcher,
                    "requested": explicit,
                    "refusal": {"reason": "heartbeat-host-conflict",
                                "detail": (f"{HEARTBEAT_HOST_ENV} names {explicit['session']} but "
                                           f"the dispatching Sideagent is bound to Host "
                                           f"{target['session']}")}}
        return {"target": target, "source": "sideagent-host", "dispatcher": dispatcher,
                "refusal": None}
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
    if explicit is None:
        record = read_record(session_directory(args, dispatcher["platform"], dispatcher["session"], dispatcher["repo"]))
        role = record.get("session_role") if isinstance(record, dict) else None
        if role in SESSION_ROLES - {"host"}:
            # Issue #255: a worker's own sessions are its business. Deriving
            # the worker as their carrier sent it full Host heartbeat passes,
            # and it acted as a second Host. It supervises them by waiting.
            return {"target": None, "source": "dispatcher-not-host", "dispatcher": dispatcher,
                    "refusal": None}
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
    receipt = base_receipt(args, repo, include_git=False)
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
# Version-specific: absent on pre-278 worker packages; compare it when shipped.
WORKER_SKILL_OPTIONAL_SCRIPTS = ("kaola-acp-paths.py", "kaola-zcode-acp.py", "kaola-opencode-acp.py", "kaola-opencode-steer.mjs", "kaola-dsh-acp.py", "kaola-dsh-steer.mjs")
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
    effort_id, _ = resolve_config_id(
        parse_config_id_candidates(manifest.get("acp_effort_config_id") or ""), state)
    wanted = {"model": manifest.get("acp_model_config_id") or "",
              "effort": effort_id}
    found: dict[str, Any] = {"effective_model": None, "effective_effort": None,
                             "effort_config_id": effort_id or None}
    if isinstance(options, list):
        for option in options:
            if not isinstance(option, dict):
                continue
            for label, config_id in wanted.items():
                if config_id and option.get("id") == config_id:
                    found[f"effective_{label}"] = option.get("currentValue")
    return found


def apply_argv_model(effective: dict[str, Any], application: Any) -> dict[str, Any]:
    """An ``acp_command_<tier>`` argv model is the effective model (#140, #340).

    Devin's advertised model option cannot report the argv id, so its
    currentValue stays evidence as ``advertised_model``. A thought_level
    readback beside this overlay is ``argv_thought_verification``.
    """
    model = application.get("model") if isinstance(application, dict) else None
    if not isinstance(model, dict) or model.get("applied_via") != "argv" \
            or not model.get("value"):
        return effective
    effective["advertised_model"] = effective.get("effective_model")
    effective["effective_model"] = model["value"]
    effective["effective_model_source"] = "launch-argv"
    effective["applied_via"] = "argv"
    return effective


def annotate_argv_effective_selection(receipt: dict[str, Any],
                                      manifest: dict[str, str]) -> None:
    """Issue #340: status/observe name an argv-launched model as effective.

    Only a start whose ``config_application.model`` was applied via argv. The
    live advertised currentValue, else the start's, stays ``advertised_model``.
    """
    evidence = receipt.get("start_evidence") if isinstance(receipt, dict) else None
    if not isinstance(evidence, dict):
        return
    application = evidence.get("config_application")
    model = application.get("model") if isinstance(application, dict) else None
    if not isinstance(model, dict) or model.get("applied_via") != "argv":
        return
    if isinstance(receipt.get("session_meta"), dict):
        current = effective_selection(manifest, receipt)
        current["advertised_source"] = "live-config-option"
    else:
        started = evidence.get("effective_selection")
        current = dict(started) if isinstance(started, dict) else {}
        current["effective_model"] = current.get("advertised_model")
        current["advertised_source"] = "start-evidence"
    receipt["effective_selection"] = apply_argv_model(current, application)


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


# Issue #185: platforms whose selected model is verified from the agent's own
# current-model echo (`session_meta.configOptions[model].currentValue`). Droid
# only: its catalog is unreadable and its `models.currentModelId` is frozen.
ECHO_VERIFIED_PLATFORMS = frozenset({"droid"})


def echo_model_verification(
    platform: str, policy: dict[str, Any], effective: dict[str, Any]
) -> dict[str, Any] | None:
    """A ``true``/``false``/``unknown`` model verdict from the agent's own echo.

    ``None`` for a platform whose advertised value is not a reliable authority.
    Reported evidence only; it never gates a start. ``effective`` must be the
    raw ``effective_selection`` echo, before the Issue #140 argv override.
    """
    if platform not in ECHO_VERIFIED_PLATFORMS:
        return None
    actual_id = effective.get("effective_model")
    actual_parameters: dict[str, Any] = {}
    if effective.get("effective_effort"):
        actual_parameters["effort"] = effective["effective_effort"]
    result: dict[str, Any] = {
        "actual_runtime_model_id": actual_id,
        "actual_parameters": actual_parameters,
        "model_verified": "unknown",
        "model_mismatch_reason": None,
    }
    if not actual_id:
        result["model_mismatch_reason"] = "actual-model-evidence-unreadable"
        return result
    expected_id = policy.get("resolved_runtime_model_id")
    if not expected_id:
        # On droid an empty target is only the preserved-resume path.
        result["model_mismatch_reason"] = "resume-preserved-actual-not-comparable"
        return result
    if actual_id != expected_id:
        result["model_verified"] = False
        result["model_mismatch_reason"] = f"actual-model-mismatch:{actual_id}"
        return result
    for key, expected in (policy.get("resolved_parameters") or {}).items():
        if key not in actual_parameters:
            result["model_mismatch_reason"] = f"actual-{key}-evidence-unreadable"
            return result
        if actual_parameters[key] != expected:
            result["model_verified"] = False
            result["model_mismatch_reason"] = f"actual-{key}-mismatch:{actual_parameters[key]}"
            return result
    result["model_verified"] = True
    return result


def argv_thought_verification(
    policy: dict[str, Any], effective: dict[str, Any], application: Any,
) -> dict[str, Any] | None:
    """Issue #342. A thought_level readback beside an argv model.

    ``None`` unless the model was applied via argv, the effort option is
    ``thought_level``, one expected effort is resolved, the model id is not a
    fusion (``-sidekick-``), and ``thought_level`` currentValue is a non-empty
    string. ``true`` only when ``effective_model`` equals the resolved model
    and that thought level equals the resolved effort. The ACP model
    currentValue (``advertised_model``) is not compared: it is not the running
    model (Issue #197, #340). A missing thought level stays unverified.
    Reported evidence only; it never gates a start.
    """
    model = application.get("model") if isinstance(application, dict) else None
    if not isinstance(model, dict) or model.get("applied_via") != "argv":
        return None
    if effective.get("effort_config_id") != "thought_level":
        return None
    expected_id = policy.get("resolved_runtime_model_id") or ""
    if not isinstance(expected_id, str) or not expected_id or "-sidekick-" in expected_id:
        return None
    parameters = policy.get("resolved_parameters") or {}
    expected_effort = parameters.get("effort") if isinstance(parameters, dict) else ""
    if not isinstance(expected_effort, str) or not expected_effort:
        return None
    thought = effective.get("effective_effort")
    if not isinstance(thought, str) or not thought:
        return None
    actual_id = effective.get("effective_model")
    result: dict[str, Any] = {
        "actual_runtime_model_id": actual_id,
        "actual_parameters": {"effort": thought},
        "model_verified": "unknown",
        "model_mismatch_reason": None,
    }
    if actual_id != expected_id:
        result["model_verified"] = False
        result["model_mismatch_reason"] = f"actual-model-mismatch:{actual_id}"
        return result
    if thought != expected_effort:
        result["model_verified"] = False
        result["model_mismatch_reason"] = f"actual-effort-mismatch:{thought}"
        return result
    result["model_verified"] = True
    return result


# Issue #316: a later status/observe reads an actual model the session already
# exposed. The holder record is not rewritten. A platform with nothing readable
# keeps ``actual-model-evidence-not-yet-read``.
_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,200}$")
_CLAUDE_TRANSCRIPT_TAIL = 2_000_000
_EVENT_EVIDENCE_TAIL = 1_500_000
_SESSION_EVIDENCE_SCALARS = (
    "model_verified", "model_mismatch_reason",
    "actual_runtime_model_id", "actual_parameters",
)


def session_model_verdict(
    evidence: dict[str, Any], actual_id: str, actual_parameters: dict[str, Any],
) -> dict[str, Any]:
    """Compare one observed model to the selection this start recorded.

    The target is ``model_selection.resolved_model`` and, when that selection
    pinned one, ``resolved_effort``. No alias is applied: Claude's preset id
    ``opus`` is not the transcript id ``claude-opus-5-5``. An empty target on
    a preserved resume stays unknown and names the actual id
    (``resume-preserved-actual-not-comparable``).
    """
    selection = evidence.get("model_selection")
    selection = selection if isinstance(selection, dict) else {}
    expected_id = selection.get("resolved_model") or ""
    if not isinstance(expected_id, str):
        expected_id = ""
    expected_effort = selection.get("resolved_effort")
    parameters = dict(actual_parameters) if isinstance(actual_parameters, dict) else {}
    result: dict[str, Any] = {
        "actual_runtime_model_id": actual_id or None,
        "actual_parameters": parameters,
        "model_verified": "unknown",
        "model_mismatch_reason": None,
    }
    if not actual_id:
        result["actual_runtime_model_id"] = None
        result["actual_parameters"] = None
        result["model_mismatch_reason"] = "actual-model-evidence-unreadable"
        return result
    if not expected_id:
        result["model_mismatch_reason"] = (
            "resume-preserved-actual-not-comparable"
            if selection.get("source") == "resume-preserved"
            else "native-default-model-not-comparable"
        )
        return result
    if actual_id != expected_id:
        result["model_verified"] = False
        result["model_mismatch_reason"] = f"actual-model-mismatch:{actual_id}"
        return result
    if isinstance(expected_effort, str) and expected_effort:
        if "effort" not in parameters:
            result["model_mismatch_reason"] = "actual-effort-evidence-unreadable"
            return result
        if parameters["effort"] != expected_effort:
            result["model_verified"] = False
            result["model_mismatch_reason"] = f"actual-effort-mismatch:{parameters['effort']}"
            return result
    result["model_verified"] = True
    return result


def claude_project_slug(repo: str) -> str:
    """Claude project-directory name for this cwd.

    Claude encodes the session cwd by writing each separator as ``-``. The
    runner repo is already a realpath; ``abspath`` keeps that spelling.
    """
    return os.path.abspath(repo).replace(os.sep, "-")


def claude_transcript_path(
    repo: str, session_id: Any, config_dir: str | None = None,
) -> Path | None:
    """``<config>/projects/<slug>/<session-id>.jsonl``, or None when unsafe.

    ``config_dir`` wins. Otherwise ``CLAUDE_CONFIG_DIR``, otherwise ``~/.claude``.
    The session id is a single path segment. It is never joined raw.
    """
    if not isinstance(session_id, str) or not _SESSION_ID_RE.fullmatch(session_id):
        return None
    if ".." in session_id:
        return None
    if config_dir:
        root = Path(config_dir)
    else:
        env_dir = os.environ.get("CLAUDE_CONFIG_DIR")
        root = Path(env_dir) if env_dir else Path.home() / ".claude"
    return root / "projects" / claude_project_slug(repo) / f"{session_id}.jsonl"


def _tail_text(path: Path, limit: int) -> str | None:
    """The file's tail as text. A seek drops the partial first line.

    None when the file is missing or unreadable. The caller keeps model id
    and effort only.
    """
    try:
        size = path.stat().st_size
    except OSError:
        return None
    try:
        with open(path, "rb") as handle:
            if size > limit:
                handle.seek(size - limit)
                raw = handle.read(limit)
                newline = raw.find(b"\n")
                raw = raw[newline + 1:] if newline >= 0 else b""
            else:
                raw = handle.read()
    except OSError:
        return None
    return raw.decode("utf-8", errors="replace")


def _claude_assistant_model(entry: Any) -> tuple[str, dict[str, Any]] | None:
    if not isinstance(entry, dict) or entry.get("type") != "assistant":
        return None
    message = entry.get("message")
    if not isinstance(message, dict):
        return None
    model = message.get("model")
    if not isinstance(model, str) or not model or model == "<synthetic>":
        return None
    parameters: dict[str, Any] = {}
    effort = entry.get("effort")
    if isinstance(effort, str) and effort:
        parameters["effort"] = effort
    return model, parameters


def claude_transcript_model(path: Path) -> dict[str, Any] | None:
    """Last non-synthetic assistant model in the transcript tail.

    None when the file cannot be read. ``id`` is empty when the file was read
    and named no model. Only ``id`` and top-level ``effort`` are kept.
    """
    text = _tail_text(path, _CLAUDE_TRANSCRIPT_TAIL)
    if text is None:
        return None
    found_id = ""
    found_parameters: dict[str, Any] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        parsed = _claude_assistant_model(entry)
        if parsed is None:
            continue
        found_id, found_parameters = parsed
    return {"id": found_id, "parameters": found_parameters}


def _runtime_model_from_update(update: Any) -> tuple[str, dict[str, Any]] | None:
    """A closed model object on a session update, or None.

    ``_meta.runtime_model`` is ``{id|model, effort?}``. A Claude-shaped
    ``message.model`` plus top-level ``effort`` is accepted when a runtime
    puts that object on an update the holder already stored. Prose,
    ``currentValue``, and ``<synthetic>`` are not evidence.
    """
    if not isinstance(update, dict):
        return None
    meta = update.get("_meta")
    runtime = meta.get("runtime_model") if isinstance(meta, dict) else None
    if isinstance(runtime, dict):
        model = runtime.get("id") if isinstance(runtime.get("id"), str) else runtime.get("model")
        if not isinstance(model, str) or not model or model == "<synthetic>":
            return None
        parameters: dict[str, Any] = {}
        effort = runtime.get("effort")
        if isinstance(effort, str) and effort:
            parameters["effort"] = effort
        return model, parameters
    message = update.get("message")
    if isinstance(message, dict):
        model = message.get("model")
        if isinstance(model, str) and model and model != "<synthetic>":
            parameters = {}
            effort = update.get("effort")
            if isinstance(effort, str) and effort:
                parameters["effort"] = effort
            return model, parameters
    return None


def read_holder_session_evidence(
    directory: Path,
) -> tuple[tuple[str, dict[str, Any]] | None, str | None]:
    """Last runtime model and last ``nativeSessionId`` in the event tail.

    ``events.jsonl.1`` is read before the live file, so a newer line wins.
    Older rotations are not scanned.
    """
    model: tuple[str, dict[str, Any]] | None = None
    native: str | None = None
    for path in (directory / "events.jsonl.1", directory / "events.jsonl"):
        text = _tail_text(path, _EVENT_EVIDENCE_TAIL)
        if text is None:
            continue
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if not isinstance(entry, dict) or entry.get("kind") != "session_update":
                continue
            update = entry.get("update")
            if not isinstance(update, dict):
                continue
            found = _runtime_model_from_update(update)
            if found is not None:
                model = found
            if update.get("sessionUpdate") == "native_session_identity":
                native_id = update.get("nativeSessionId")
                if (isinstance(native_id, str) and _SESSION_ID_RE.fullmatch(native_id)
                        and ".." not in native_id):
                    native = native_id
    return model, native


def _apply_session_verdict(
    receipt: dict[str, Any], evidence: dict[str, Any], verdict: dict[str, Any],
    actual: dict[str, Any],
) -> None:
    """Replace the receipt's evidence copy. The holder record object stays."""
    copied = dict(evidence)
    for key in _SESSION_EVIDENCE_SCALARS:
        copied[key] = verdict[key]
    provenance = copied.get("model_evidence_provenance")
    provenance = dict(provenance) if isinstance(provenance, dict) else {}
    provenance["actual"] = actual
    copied["model_evidence_provenance"] = provenance
    receipt["start_evidence"] = copied
    for key in _SESSION_EVIDENCE_SCALARS:
        receipt[key] = verdict[key]


def _unreadable_model_verdict() -> dict[str, Any]:
    return {
        "actual_runtime_model_id": None,
        "actual_parameters": None,
        "model_verified": "unknown",
        "model_mismatch_reason": "actual-model-evidence-unreadable",
    }


def annotate_session_model_evidence(
    receipt: dict[str, Any], platform: str, repo: str, directory: Path | None,
) -> None:
    """Overlay a live model verdict onto this status or observe receipt.

    A runtime model the holder already recorded wins. Claude Code, and only
    Claude Code, then reads its session JSONL. No evidence leaves the start
    snapshot as it was, including a Droid echo, a Devin thought_level verdict,
    and ``actual-model-evidence-not-yet-read``. This does not write ``record.json``.
    """
    if directory is None or not isinstance(receipt, dict):
        return
    evidence = receipt.get("start_evidence")
    if not isinstance(evidence, dict):
        return
    found, native_id = read_holder_session_evidence(directory)
    if found is not None:
        actual_id, actual_parameters = found
        verdict = session_model_verdict(evidence, actual_id, actual_parameters)
        _apply_session_verdict(receipt, evidence, verdict, {
            "source": "acp-session-update",
            "model_id": verdict["actual_runtime_model_id"],
            "parameters": verdict["actual_parameters"],
        })
        return
    if platform != "claude-code" or not isinstance(repo, str) or not repo:
        return
    session_ids: list[str] = []
    if native_id:
        session_ids.append(native_id)
    acp_id = evidence.get("acp_session_id")
    if not isinstance(acp_id, str) or not acp_id:
        acp_id = receipt.get("acp_session_id")
    if isinstance(acp_id, str) and acp_id and acp_id not in session_ids:
        session_ids.append(acp_id)
    chosen: Path | None = None
    for session_id in session_ids:
        path = claude_transcript_path(repo, session_id)
        if path is not None and path.is_file():
            chosen = path
            break
    if chosen is None:
        return
    loaded = claude_transcript_model(chosen)
    if not isinstance(loaded, dict) or not loaded.get("id"):
        verdict = _unreadable_model_verdict()
        _apply_session_verdict(receipt, evidence, verdict, {
            "source": "claude-session-jsonl",
            "model_id": None,
            "parameters": None,
        })
        return
    verdict = session_model_verdict(
        evidence, str(loaded["id"]), loaded.get("parameters") or {},
    )
    _apply_session_verdict(receipt, evidence, verdict, {
        "source": "claude-session-jsonl",
        "model_id": verdict["actual_runtime_model_id"],
        "parameters": verdict["actual_parameters"],
    })


# Issue #268: authority order for a continuation. The chosen tier is
# ``selection_continuity.precedence``. ``unresolved`` means neither stale
# holder metadata nor an unconfirmed load was treated as the winner.
CONTINUITY_PRECEDENCE = (
    "explicit-current",
    "saved-session-selection",
    "prior-applied",
    "fresh-start-default",
)
_DIFFERS_RECOVERY = (
    "The fresh effective readback differs from the prior successfully applied "
    "selection. This continuation sent no model or effort override and does not "
    "claim the prior settings were preserved. Why the loaded values differ is "
    "unproven. To choose a selection, continue again with explicit --model, "
    "--effort, or --tier. A bare continuation does not re-apply the fresh-start preset."
)
_CONTRADICTORY_RECOVERY = (
    "The prior applied configuration and the prior live readback disagree, and "
    "the fresh readback does not confirm a single selection. Stale holder "
    "metadata is not the current selection. Continue with explicit --model, "
    "--effort, or --tier to choose."
)
_UNVERIFIABLE_RECOVERY = (
    "The fresh effective readback is missing for a model or effort the prior "
    "start applied. Those prior values remain historical and are not claimed "
    "preserved. Inspect status configOptions, or continue with explicit "
    "--model, --effort, or --tier to re-apply a chosen selection."
)
_EXPLICIT_RECOVERY = (
    "The explicit selection was not confirmed by the fresh readback. "
    "config_application records the attempt. This reconciliation applied no "
    "substitute model."
)
_SAVED_SESSION_DETAIL = (
    "The fresh readback matches the prior live readback, which already differed "
    "from the prior applied value. That saved-session selection is left unchanged."
)


def _continuity_text(value: Any) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


def _applied_config_value(application: Any, label: str) -> str | None:
    if not isinstance(application, dict):
        return None
    entry = application.get(label)
    if not isinstance(entry, dict) or entry.get("applied") is not True:
        return None
    return _continuity_text(entry.get("value"))


def _application_fact(application: Any, label: str) -> dict[str, Any]:
    """This start's application for one axis, without agent error bodies."""
    entry = application.get(label) if isinstance(application, dict) else None
    if not isinstance(entry, dict):
        return {"applied": False, "value": None, "reason": "absent"}
    fact: dict[str, Any] = {
        "applied": entry.get("applied") is True,
        "value": _continuity_text(entry.get("value")),
    }
    if isinstance(entry.get("reason"), str) and entry.get("reason"):
        fact["reason"] = entry["reason"]
    if isinstance(entry.get("applied_via"), str) and entry.get("applied_via"):
        fact["applied_via"] = entry["applied_via"]
    error = entry.get("error")
    if isinstance(error, dict) and isinstance(error.get("code"), str) and error.get("code"):
        fact["error_code"] = error["code"]
    return fact


def _readback_value(effective: Any, label: str) -> tuple[str | None, bool, str | None]:
    """Native currentValue for one axis.

    A launch-argv model is the Runner's substitute, not a native readback
    (Issue #140). The advertised option stays out of this comparison.
    """
    if not isinstance(effective, dict):
        return None, False, None
    if label == "model" and effective.get("effective_model_source") == "launch-argv":
        return None, False, "launch-argv-not-a-native-readback"
    key = "effective_model" if label == "model" else "effective_effort"
    value = _continuity_text(effective.get(key))
    if value is None:
        return None, False, None
    return value, True, None


def _native_readback(effective: Any) -> dict[str, Any] | None:
    """Per-axis sourced native currentValue.

    A launch-argv model is unavailable and does not discard a genuine native
    effort on the same object. ``None`` only when neither axis is a native
    readback. The copy keeps a launch-argv model source so the comparison can
    name that axis unavailable, and clears any other unread model so it cannot
    be taken as native.
    """
    if not isinstance(effective, dict):
        return None
    _model, model_readable, _model_note = _readback_value(effective, "model")
    _effort, effort_readable, _effort_note = _readback_value(effective, "effort")
    if not model_readable and not effort_readable:
        return None
    kept = dict(effective)
    if not model_readable and kept.get("effective_model_source") != "launch-argv":
        kept["effective_model"] = None
    if not effort_readable:
        kept["effective_effort"] = None
    return kept


def _stamp_live_readback(effective: Any, *, holder_instance_id: Any,
                         recorded_at: Any) -> dict[str, Any] | None:
    """Preceding holder's native readback, with that holder's own source.

    The holder and time belong to this value. They are not taken from an
    older start whose echo is a different value.
    """
    native = _native_readback(effective)
    if native is None:
        return None
    live = dict(native)
    live["holder_instance_id"] = holder_instance_id
    live["recorded_at"] = recorded_at
    return live


def _most_recent_live(inherited: Any) -> tuple[Any, Any, Any]:
    """``(effective, holder_instance_id, recorded_at)`` used as prior_live.

    ``most_recent_live`` on a carried object is the live slot, separate from
    the historical echo. ``None`` is unknown: the older ``effective_selection``
    is not that slot. When the key is absent, this object is the preceding
    holder's own record, so its ``effective_selection`` is the live readback
    and the object's holder and time are its source.
    """
    if not isinstance(inherited, dict):
        return None, None, None
    if "most_recent_live" in inherited:
        slot = inherited.get("most_recent_live")
        if not isinstance(slot, dict):
            return None, None, None
        return slot, slot.get("holder_instance_id"), slot.get("recorded_at")
    return (
        inherited.get("effective_selection"),
        inherited.get("holder_instance_id"),
        inherited.get("recorded_at"),
    )


def _applied_baseline_source(inherited: Any) -> tuple[Any, Any]:
    """Holder and time of the historical applied configuration."""
    if not isinstance(inherited, dict):
        return None, None
    if "config_baseline_holder_instance_id" in inherited:
        holder = inherited.get("config_baseline_holder_instance_id")
    else:
        holder = inherited.get("holder_instance_id")
    if "config_baseline_recorded_at" in inherited:
        recorded = inherited.get("config_baseline_recorded_at")
    else:
        recorded = inherited.get("recorded_at")
    return holder, recorded


def _unverified_explicit_baseline(saved: dict[str, Any]) -> dict[str, Any] | None:
    """Earlier applied baseline when this explicit change was not verified.

    ``None`` when this start's own application stands: there is no earlier
    baseline, or the explicit change's readback matched what the Runner
    applied. A bare continuation does not call this.
    """
    continuity = saved.get("selection_continuity")
    if not isinstance(continuity, dict) or continuity.get("outcome") != "explicit-current":
        return None
    if continuity.get("explicit_readback_matches") is True:
        return None
    previous = saved.get("inherited")
    if isinstance(previous, dict) and isinstance(previous.get("config_application"), dict):
        return previous
    return None


def _continuity_equal(label: str, left: str, right: str) -> bool:
    if label == "effort":
        return left.lower() == right.lower()
    return left == right


def _axis_status(label: str, *, explicit: bool, prior_applied: str | None,
                 prior_live: str | None, prior_live_readable: bool,
                 fresh: str | None, fresh_readable: bool) -> str:
    if explicit:
        return "explicit"
    if prior_applied is None:
        return "not-applicable"
    if not fresh_readable or fresh is None:
        return "unverifiable"
    if prior_live_readable and prior_live is not None and not _continuity_equal(
            label, prior_live, prior_applied):
        # A live value that differs from the historical applied value stays
        # unproven, including when this readback repeats it. Repetition is
        # not evidence that someone intended the change.
        if _continuity_equal(label, fresh, prior_live):
            return "differs-from-prior-applied"
        return "contradictory-evidence"
    if _continuity_equal(label, fresh, prior_applied):
        return "matches-prior-applied"
    return "differs-from-prior-applied"


def _continuity_outcome(statuses: list[str], *, resumed: bool, explicit: bool,
                        had_prior: bool) -> str:
    if explicit:
        return "explicit-current"
    if not resumed:
        return "fresh-start-default"
    applicable = [status for status in statuses if status not in ("not-applicable", "explicit")]
    if not had_prior or not applicable:
        return "resume-without-prior-applied"
    if "contradictory-evidence" in applicable:
        return "contradictory-evidence"
    if "differs-from-prior-applied" in applicable:
        return "differs-from-prior-applied"
    if "unverifiable" in applicable:
        return "unverifiable"
    if "saved-session-change" in applicable:
        return "saved-session-change"
    if all(status == "matches-prior-applied" for status in applicable):
        return "matches-prior-applied"
    return "unverifiable"


def _explicit_readback_matches(axes: dict[str, dict[str, Any]]) -> bool | None:
    """Whether this start's own applied values match the fresh readback."""
    saw_unknown = False
    saw_applied = False
    for axis in axes.values():
        if axis.get("applied") is not True:
            if axis.get("recorded"):
                return False
            continue
        saw_applied = True
        if not axis.get("fresh_readable"):
            saw_unknown = True
            continue
        fresh = axis.get("fresh_effective")
        applied = axis.get("applied_this_start")
        label = axis["label"]
        if not isinstance(fresh, str) or not isinstance(applied, str):
            return False
        if not _continuity_equal(label, fresh, applied):
            return False
    if not saw_applied:
        return None
    if saw_unknown:
        return None
    return True


def reconcile_selection_continuity(
    *,
    resumed: bool,
    explicit: bool,
    recorded_source: Any,
    recorded_model: Any,
    recorded_effort: Any,
    application: Any,
    fresh: Any,
    inherited: Any,
) -> dict[str, Any]:
    """Compare recorded, applied, and fresh values for one start (Issue #268).

    Precedence is explicit current selection, then a loaded session when no
    prior applied selection exists, then the prior successfully applied
    selection, then a fresh-start default. Explicit flags replace that applied
    baseline only when the fresh readback verifies the change. A bare
    continuation does not re-apply the preset and does not overwrite the
    loaded session. Stale applied metadata alone never counts as the current
    selection. A match is claimed only when the fresh readback equals the
    prior applied value and the prior live readback does not contradict it.
    A difference from the historical applied value stays unproven, including
    when a later readback repeats it. A missing most-recent live echo is
    unknown and is not filled from an older echo.
    """
    recorded = {
        "source": recorded_source if isinstance(recorded_source, str) else None,
        "model": _continuity_text(recorded_model),
        "effort": _continuity_text(recorded_effort),
    }
    prior_application = inherited.get("config_application") if isinstance(inherited, dict) else None
    prior_effective, live_holder, live_recorded = _most_recent_live(inherited)
    baseline_holder, baseline_recorded = _applied_baseline_source(inherited)
    axes: dict[str, dict[str, Any]] = {}
    statuses: list[str] = []
    prior_model = _applied_config_value(prior_application, "model")
    prior_effort = _applied_config_value(prior_application, "effort")
    for label, recorded_value, prior_applied in (
        ("model", recorded["model"], prior_model),
        ("effort", recorded["effort"], prior_effort),
    ):
        prior_live, prior_live_readable, prior_note = _readback_value(prior_effective, label)
        fresh_value, fresh_readable, fresh_note = _readback_value(fresh, label)
        status = _axis_status(
            label, explicit=explicit, prior_applied=prior_applied,
            prior_live=prior_live, prior_live_readable=prior_live_readable,
            fresh=fresh_value, fresh_readable=fresh_readable,
        )
        if label == "effort" and _effort_carried_by_model(prior_application):
            # Issue #331: an effort the model ID carries has no readback of its
            # own (no effort option), so it stands or falls with the model axis.
            status = statuses[0]
        statuses.append(status)
        axis = {
            "label": label,
            "recorded": recorded_value,
            "applied_this_start": _applied_config_value(application, label),
            "applied": _applied_config_value(application, label) is not None,
            "fresh_effective": fresh_value,
            "fresh_readable": fresh_readable,
            "prior_applied": prior_applied,
            "prior_live": prior_live,
            "prior_live_readable": prior_live_readable,
            "status": status,
        }
        if fresh_note:
            axis["fresh_note"] = fresh_note
        if prior_note:
            axis["prior_live_note"] = prior_note
        if prior_live_readable and isinstance(live_holder, str) and live_holder:
            axis["prior_live_holder_instance_id"] = live_holder
        if prior_live_readable and live_recorded is not None:
            axis["prior_live_recorded_at"] = live_recorded
        axes[label] = axis
    had_prior = prior_model is not None or prior_effort is not None
    outcome = _continuity_outcome(
        statuses, resumed=resumed, explicit=explicit, had_prior=had_prior)
    if outcome == "matches-prior-applied":
        prior_settings_preserved: bool | None = True
    elif outcome in (
        "differs-from-prior-applied", "contradictory-evidence", "saved-session-change",
    ):
        prior_settings_preserved = False
    elif outcome == "explicit-current" and resumed and had_prior:
        prior_settings_preserved = False
    else:
        prior_settings_preserved = None
    precedence = {
        "explicit-current": "explicit-current",
        "saved-session-change": "saved-session-selection",
        "resume-without-prior-applied": "saved-session-selection",
        "matches-prior-applied": "prior-applied",
        "fresh-start-default": "fresh-start-default",
    }.get(outcome, "unresolved")
    readback_matches = _explicit_readback_matches(axes) if explicit else None
    for axis in axes.values():
        axis.pop("label", None)
    prior_applied_selection: dict[str, Any] | None = None
    if had_prior:
        prior_applied_selection = {
            "model": prior_model,
            "effort": prior_effort,
            "source": "prior-holder-record",
            "historical": True,
        }
        if isinstance(baseline_holder, str) and baseline_holder:
            prior_applied_selection["holder_instance_id"] = baseline_holder
        if baseline_recorded is not None:
            prior_applied_selection["recorded_at"] = baseline_recorded
    result: dict[str, Any] = {
        "precedence_order": list(CONTINUITY_PRECEDENCE),
        "precedence": precedence,
        "outcome": outcome,
        "prior_settings_preserved": prior_settings_preserved,
        "had_prior_applied": had_prior,
        "recorded_selection": recorded,
        "applied_configuration": {
            "model": _application_fact(application, "model"),
            "effort": _application_fact(application, "effort"),
        },
        "fresh_effective_readback": {
            "model": axes["model"]["fresh_effective"],
            "effort": axes["effort"]["fresh_effective"],
            "model_readable": axes["model"]["fresh_readable"],
            "effort_readable": axes["effort"]["fresh_readable"],
            "source": "acp-config-echo",
        },
        "prior_applied_selection": prior_applied_selection,
        "axes": {"model": axes["model"], "effort": axes["effort"]},
        "explicit_readback_matches": readback_matches,
    }
    if outcome == "differs-from-prior-applied":
        result["cause"] = "unproven"
        result["recovery"] = _DIFFERS_RECOVERY
    elif outcome == "contradictory-evidence":
        result["cause"] = "unproven"
        result["recovery"] = _CONTRADICTORY_RECOVERY
    elif outcome == "unverifiable":
        result["recovery"] = _UNVERIFIABLE_RECOVERY
    elif outcome == "explicit-current" and readback_matches is False:
        result["recovery"] = _EXPLICIT_RECOVERY
    elif outcome == "saved-session-change":
        result["detail"] = _SAVED_SESSION_DETAIL
    return result


# Issue #203: the start receipt facts the holder keeps as `start_evidence`, by
# their existing names. `model_evidence_provenance` drops only its bulky
# `catalog_probe` output.
START_EVIDENCE_KEYS = (
    "model_selection", "model_display", "requested_effort",
    "config_application", "effective_selection", "fast",
    "host_selection", "model_verified", "model_mismatch_reason",
    "actual_runtime_model_id", "actual_parameters",
    "selection_continuity",
)


def start_evidence_facts(source: dict[str, Any]) -> dict[str, Any]:
    facts = {key: source[key] for key in START_EVIDENCE_KEYS if key in source}
    provenance = source.get("model_evidence_provenance")
    if isinstance(provenance, dict):
        facts["model_evidence_provenance"] = {
            key: value for key, value in provenance.items() if key != "catalog_probe"}
    return facts


def inherited_start_evidence(prior: Any, args: argparse.Namespace, repo: str,
                             acp_session_id: Any) -> dict[str, Any] | None:
    """Evidence an earlier start recorded for this same native session.

    Only a resume/continue whose adopted ``acp_session_id`` equals the one the
    prior record, for this platform/session/repo, both ran and recorded its
    evidence under. A Runner name alone never matches. Historical, never a
    fresh observation: a no-override resume carries the last applied
    configuration forward flat rather than nesting it. The older start's own
    readback stays ``effective_selection`` with that start's holder and time.
    ``most_recent_live`` is only the immediately preceding holder's native
    readback, per axis, with that holder's holder and time. A launch-argv
    model does not drop a native effort. No native readback on that holder
    leaves the live slot missing, so the older echo is not prior_live.
    """
    if not (args.resume or args.use_continue) or not acp_session_id:
        return None
    if not isinstance(prior, dict) or prior.get("acp_session_id") != acp_session_id:
        return None
    if (prior.get("platform"), prior.get("repo"), prior.get("session")) != (
            args.platform, repo, args.session):
        return None
    saved = prior.get("start_evidence")
    if not isinstance(saved, dict) or saved.get("acp_session_id") != acp_session_id:
        return None
    older = saved.get("inherited")
    selection = saved.get("model_selection") if isinstance(saved.get("model_selection"), dict) else {}
    # A no-override resume carries the last applied evidence forward. Old
    # records say that with ``preserved``; current records say it with
    # ``override_omitted``, including when the fresh readback did not confirm
    # the prior values (Issue #268).
    passthrough = selection.get("override_omitted") is True or (
        "override_omitted" not in selection
        and selection.get("preserved") is True
        and selection.get("source") == "resume-preserved"
    )
    if passthrough and isinstance(older, dict):
        carried = dict(older)
        preceding = _stamp_live_readback(
            saved.get("effective_selection"),
            holder_instance_id=prior.get("holder_instance_id"),
            recorded_at=saved.get("recorded_at"),
        )
        if preceding is not None:
            carried["most_recent_live"] = preceding
        elif (_native_readback(carried.get("effective_selection")) is not None
              or "most_recent_live" in carried):
            # A readable older echo, or a live slot copied from a still older
            # hop, is not this holder's readback.
            carried["most_recent_live"] = None
        return carried
    inherited = start_evidence_facts(saved)
    inherited.update({
        "source": "prior-holder-record",
        "holder_instance_id": prior.get("holder_instance_id"),
        "acp_session_id": acp_session_id,
        "recorded_at": saved.get("recorded_at"),
    })
    previous = _unverified_explicit_baseline(saved)
    if previous is not None:
        inherited["config_application"] = previous["config_application"]
        if "config_baseline_holder_instance_id" in previous:
            inherited["config_baseline_holder_instance_id"] = previous.get(
                "config_baseline_holder_instance_id")
        else:
            inherited["config_baseline_holder_instance_id"] = previous.get(
                "holder_instance_id")
        if "config_baseline_recorded_at" in previous:
            inherited["config_baseline_recorded_at"] = previous.get(
                "config_baseline_recorded_at")
        else:
            inherited["config_baseline_recorded_at"] = previous.get("recorded_at")
    return inherited


def preset_class_role(args: argparse.Namespace, basis: dict[str, Any]) -> str | None:
    """Lowercased manifest Class for the preset this start actually selected.

    ``preset_id`` is the only evidence. An undeclared tier, a foreign
    platform, or a class outside Expert/Elite/Worker is null — never Worker.
    """
    preset_id = basis.get("preset_id")
    if not isinstance(preset_id, str):
        return None
    platform, separator, tier = preset_id.partition("/")
    if not separator or platform != getattr(args, "platform", None) or not tier:
        return None
    manifest = getattr(args, "manifest", None) or {}
    if tier not in declared_tiers(manifest):
        return None
    raw = manifest.get(f"{tier.replace('-', '_')}_model_class") or ""
    if not isinstance(raw, str):
        return None
    lowered = raw.strip().lower()
    if lowered in ("expert", "elite", "worker"):
        return lowered
    return None


def inherited_session_role(prior: Any, args: argparse.Namespace, repo: str,
                           acp_session_id: Any) -> str | None:
    """The prior role when this resume is the same native session, else null."""
    if inherited_start_evidence(prior, args, repo, acp_session_id) is None:
        return None
    role = prior.get("session_role") if isinstance(prior, dict) else None
    if role in SESSION_ROLES:
        return role
    return None


def session_role_value(args: argparse.Namespace, basis: dict[str, Any],
                       prior: Any = None, repo: str | None = None,
                       acp_session_id: Any = None) -> str | None:
    """Issue #245 session identity for this start.

    Host name derivation is authoritative. ``--role sideagent`` sets this role;
    ``sidekick`` remains accepted for legacy callers and recovery. Expert, elite,
    and worker come only from the selected preset id and its manifest class. Custom ``--model``, a
    resume-preserved start that is not the same native session, an unknown
    class, and missing evidence stay null.
    """
    if host_session(getattr(args, "platform", ""), getattr(args, "session", None)):
        return "host"
    if getattr(args, "role", None) in ("sideagent", "sidekick"):
        inherited = inherited_session_role(prior, args, repo, acp_session_id)
        # A new spelling is not a new identity on the same native session.
        return inherited if inherited in ("sideagent", "sidekick") else args.role
    if basis.get("preset_id"):
        return preset_class_role(args, basis)
    if basis.get("source") == "resume-preserved" and isinstance(repo, str):
        return inherited_session_role(prior, args, repo, acp_session_id)
    return None


def record_start_evidence(sock: Path, receipt: dict[str, Any], args: argparse.Namespace,
                          repo: str, prior: Any) -> None:
    """Hand this start's selection/application evidence to its holder (Issue #203).

    Evidence only: a holder that cannot keep it is reported, never a refusal.
    """
    evidence = start_evidence_facts(receipt)
    evidence.update({
        "acp_session_id": receipt.get("acp_session_id"),
        "resumed": bool(args.resume or args.use_continue),
        "recorded_at": round(time.time(), 3),
    })
    inherited = inherited_start_evidence(prior, args, repo, receipt.get("acp_session_id"))
    if inherited is not None:
        evidence["inherited"] = inherited
        receipt["inherited_start_evidence"] = inherited
    # Resume identity is knowable only after the native session id comes back.
    # The spawn value stays until the holder accepts this final one.
    role = session_role_value(args, selection_basis(args), prior, repo,
                              receipt.get("acp_session_id"))
    # Issue #408: this op mutates a bound seat, so present the token from the
    # record dir plus the holder instance id the fresh state reply named.
    params: dict[str, Any] = {"evidence": evidence, "session_role": role}
    if receipt.get("holder_instance_id") is not None:
        params["expected_holder_instance_id"] = receipt["holder_instance_id"]
    reply = socket_request(
        sock, "record_start_evidence", params, 10.0,
        record_dir(args, repo),
    )
    receipt["start_evidence_recorded"] = reply.get("recorded") is True
    if receipt["start_evidence_recorded"]:
        receipt["session_role"] = role
    if reply.get("error"):
        receipt["start_evidence_error"] = reply["error"]


def stop_started_holder(sock: Path, proc: subprocess.Popen | None,
                        holder_pid: int | None = None,
                        expected_instance: str | None = None,
                        directory: Path | None = None) -> dict[str, Any]:
    """Force-stop the holder this start just created and report its truth.

    The direct path reaps its own Popen child. The outside-launch path (#266)
    has no local child: it stops through the socket and reports the reply's
    residual facts. The holder answers stop before it exits
    (``_exit_after_reply``), so the outside path settles on the recorded pid
    inside the same bound the direct path's ``proc.wait`` uses; a single
    liveness sample would race the dying holder and misreport a reclaimed
    session as alive.
    """
    params: dict[str, Any] = {"force": True}
    if expected_instance:
        params["expected_holder_instance_id"] = expected_instance
    stop_reply = socket_request(sock, "stop", params, 30.0, directory)
    reply = stop_reply if isinstance(stop_reply, dict) else {}
    stopped = reply.get("stopped") is True
    residual = reply.get("residual_pids")
    if proc is not None:
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
        holder_alive = proc.poll() is None
    elif holder_pid is not None:
        # Local import: the composed broker proof execs this function's source
        # standalone, with only the globals it injects.
        import time as _time
        deadline = _time.monotonic() + 10.0
        while _time.monotonic() < deadline and pid_alive(holder_pid):
            _time.sleep(0.05)
        holder_alive = pid_alive(holder_pid)
    else:
        holder_alive = None
    # The holder validates the expected instance before it mutates and does not
    # echo it back. Clean is a bound request plus a positive stop, an actual
    # empty residual list, and a gone holder; anything else stays unknown.
    reclaimed = (stopped and isinstance(residual, list) and residual == []
                 and holder_alive is False)
    return {
        "host_session_stopped": stopped,
        "residual_pids": residual,
        "holder_alive": holder_alive,
        "holder_reclaimed": reclaimed,
        "holder_identity": {"holder_pid": holder_pid},
    }


def zcode_host_refusal(args: argparse.Namespace, repo: str,
                       problem: str) -> dict[str, Any]:
    """Issue #108 typed refusal — the Issue #105 shape: nothing was probed,
    written, or spawned."""
    receipt = base_receipt(args, repo, include_git=False)
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


def invoked_via_local_bin() -> bool:
    """True when this process was started through ``~/.local/bin``.

    ``install-local --bin-links`` points those names at this checkout's
    ``scripts/``. ``Path.resolve`` on ``__file__`` follows the link, so the
    invocation path is ``sys.argv[0]``, not ``SCRIPT_DIR``.
    """
    raw = sys.argv[0] if sys.argv else ""
    if not raw:
        return False
    path = Path(raw)
    if not path.is_absolute():
        path = Path.cwd() / path
    local_bin = Path.home() / ".local" / "bin"
    try:
        return path.parent.resolve() == local_bin.resolve()
    except OSError:
        return False


def skew_baseline_dir() -> Path | None:
    """Directory whose scripts are the build this start is running, or None.

    An installed Skill tree is the baseline. A ``~/.local/bin`` start is too:
    the link resolves to the checkout scripts, which are what the operator
    just accepted. A direct checkout invocation stays the development path
    and is not a baseline (``applies`` false).
    """
    tree = invoking_skill_tree()
    if tree is not None:
        return tree / "scripts"
    if invoked_via_local_bin():
        return SCRIPT_DIR
    return None


def main_skill_record_file(baseline: Path) -> Path | None:
    """The main-skill build record for this baseline.

    Worker Skills ship it beside their scripts. A ``~/.local/bin`` baseline
    is the checkout ``scripts/`` directory, which does not; the rendered
    record lives in each generated worker Skill of that checkout.
    """
    direct = baseline / MAIN_SKILL_BUILD_FILE
    if direct.is_file():
        return direct
    skills = baseline.parent / "skills"
    if not skills.is_dir():
        return None
    for child in sorted(skills.glob("*-kaola-project-runner")):
        candidate = child / "scripts" / MAIN_SKILL_BUILD_FILE
        if candidate.is_file():
            return candidate
    return None


def is_worker_skill(path: Path) -> bool:
    return (path / "scripts" / "kaola-acp.py").is_file()


# Issue #375: the installer's hidden set-aside names. A runtime does not load a
# dot-directory, so none of these is an installed Skill; they are reported apart
# so stale leftovers can be quarantined without ever blocking a start.
INSTALL_BACKUP_NAME = re.compile(r"^\..+\.(?:drift|old|tmp)\.[0-9]+$")


def is_install_backup(path: Path) -> bool:
    return bool(INSTALL_BACKUP_NAME.match(path.name))


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
                skills = sorted(path for path in root.iterdir()
                                if not is_install_backup(path) and match(path))
            except OSError:
                unreadable.append(str(root))
                continue
            if skills:
                found.append((root, skills))
    return found, unreadable


def stale_install_backups(repo: str, platform: str = "zcode") -> list[str]:
    """Hidden installer backups in the discovery roots (Issue #375).

    They are not installed Skills and never make the build-skew check refuse.
    The list is reported separately with the command that quarantines them."""
    found: list[str] = []
    seen: set[str] = set()
    for base in (Path(repo), Path.home()):
        for relative in HOST_SKILL_DISCOVERY_DIRS.get(platform, SKILL_DISCOVERY_DIRS):
            root = base / relative
            if not root.is_dir():
                continue
            try:
                key = str(root.resolve())
            except OSError:
                continue
            if key in seen:
                continue
            seen.add(key)
            try:
                entries = sorted(root.iterdir())
            except OSError:
                continue
            for path in entries:
                if not is_install_backup(path):
                    continue
                if not (path.is_dir() or path.is_symlink()):
                    continue
                if str(path) not in found:
                    found.append(str(path))
    return found


def worker_skill_alignment(repo: str, platform: str = "zcode") -> dict[str, Any]:
    """Compare every installed worker Skill's shared scripts with this build.

    Returns ``applies`` (False for a direct checkout invocation, which has no
    Skill build to be the baseline; a ``~/.local/bin`` start does apply),
    ``build`` (the baseline ``kaola-acp.py`` digest,
    12 hex), ``roots`` (what was compared, for the receipt), ``skew`` (the
    differing files), ``unreadable_roots`` (Issue #106: existing default
    roots that could not be listed, so no comparison was possible) and
    ``stale_install_backups`` (Issue #375: hidden installer leftovers in the
    same roots, reported but never counted as installed Skills). Read-only:
    nothing is written, probed, or spawned."""
    baseline_dir = skew_baseline_dir()
    if baseline_dir is None:
        return {"applies": False, "build": None, "roots": None, "skew": [],
                "unreadable_roots": [], "stale_install_backups": []}
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
            "roots": roots, "skew": skew, "unreadable_roots": unreadable,
            "stale_install_backups": stale_install_backups(repo, platform)}


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
    baseline_dir = skew_baseline_dir()
    record_path = main_skill_record_file(baseline_dir) if baseline_dir else None
    try:
        record = json.loads(record_path.read_text(encoding="utf-8")) if record_path else None
    except (OSError, ValueError):
        record = None
    files = record.get("files") if isinstance(record, dict) else None
    if not isinstance(files, dict) or not files:
        return {"applies": False, "build": None, "skills": None, "skew": [],
                "stale_install_backups": []}
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
    return {"applies": True, "build": build, "skills": found, "skew": skew,
            "stale_install_backups": stale_install_backups(repo, platform)}


def _pin_file(directory: Path) -> str | None:
    path = directory / LOCATOR_REGISTRATION_NAME
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    accepted = data.get("accepted_revision") if isinstance(data, dict) else None
    if isinstance(accepted, str) and REVISION_RE.fullmatch(accepted):
        return accepted
    return None


def registration_directories() -> list[Path]:
    """Bin directories that may hold the locator link and its registration.

    The owner-chosen directory is the one on ``PATH`` (``hosts/grok-bot/INSTALL.md``).
    ``~/.local/bin`` remains the installer's default when the link is not on PATH.
    """
    found: list[Path] = []
    seen: set[str] = set()

    def add(directory: Path) -> None:
        try:
            key = str(directory.resolve())
        except OSError:
            key = str(directory)
        if key in seen:
            return
        seen.add(key)
        found.append(directory)

    located = shutil.which("kaola-project-runner-locate")
    if located:
        add(Path(located).parent)
    add(Path.home() / ".local" / "bin")
    return found


def registration_pin() -> str | None:
    """The locator registration's accepted revision, the pin a seat is measured against."""
    for directory in registration_directories():
        pin = _pin_file(directory)
        if pin:
            return pin
    return None


def current_accepted_revision() -> str | None:
    """What a new holder should record: the pin when one is registered, else
    this checkout's HEAD when the CLI itself lives in the runner checkout."""
    pin = registration_pin()
    if pin:
        return pin
    root = SCRIPT_DIR.parent
    if not (root / "platforms").is_dir() or not (root / "scripts" / "kaola-locate.py").is_file():
        return None
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        capture_output=True, text=True,
    )
    head = (result.stdout or "").strip()
    if result.returncode == 0 and REVISION_RE.fullmatch(head):
        return head
    return None


def _stored_script_digests(facts: dict[str, Any]) -> dict[str, str]:
    paths = facts.get("script_paths")
    found: dict[str, str] = {}
    if not isinstance(paths, dict):
        return found
    for name, entry in paths.items():
        if isinstance(entry, dict) and isinstance(entry.get("sha256"), str):
            found[str(name)] = entry["sha256"]
    return found


# Issue #179: the one place the emitted ``reported_drift`` vocabulary lives.
# Every value ``seat_freshness`` appends is a member, and the prose surfaces
# (``docs/api.md``, the reference templates) name the field instead of listing
# values, so a value cannot be described in two places that drift apart.
REPORTED_DRIFT_VALUES = (
    "build-unrecorded",
    "revision-unrecorded",
    "pin-drift",
    "cli-drift",
    "recorded-path-missing",
    "checkout-drift",
)


def _restart_required_name(name: str) -> bool:
    """Files the release-note operator test treats as a seat restart.

    ``git diff OLD NEW -- scripts/kaola-acp-holder.py scripts/kaola-zcode-acp.py
    scripts/kaola-quota.py scripts/kaola-record-contract.py scripts/adapters
    platforms``. The holder pins ``kaola-quota.py`` and
    ``kaola-record-contract.py`` at startup, so a running seat picks up those
    bytes only by restarting: the CLI re-imports them per call, so one live
    seat would otherwise stamp ``view`` with the old code and ``observe``/
    ``status`` with the new. ``kaola-acp.py`` and ``kaola-tmux.sh`` are per-call
    CLI files. A pin bump is not in the set.
    """
    return (
        name in ("kaola-acp-holder.py", "kaola-zcode-acp.py", "kaola-quota.py",
                 "kaola-record-contract.py", "kaola-acp-paths.py",
                 "kaola-opencode-acp.py", "kaola-opencode-steer.mjs",
                 "kaola-dsh-acp.py", "kaola-dsh-steer.mjs",
                 "platform.yaml")
        or name.startswith("adapters/")
        or name.startswith("platforms/")
    )


def _seat_from_checkout(facts: dict[str, Any]) -> bool:
    """True when this seat's holder was started from a repository checkout.

    That is the development path ``start`` does not compare to installed
    Skills. An installed Skill tree has ``SKILL.md`` beside ``scripts/``.
    """
    holder = (_stored_script_digests(facts) and
              (facts.get("script_paths") or {}).get("kaola-acp-holder.py"))
    if not isinstance(holder, dict) or not holder.get("path"):
        return False
    tree = Path(str(holder["path"])).parent.parent
    return not (tree / "SKILL.md").is_file()


def _changed_recorded_files(stored_paths: dict[str, Any], wanted) -> list[str]:
    """Recorded names whose bytes at the recorded path differ now."""
    changed: list[str] = []
    if not isinstance(stored_paths, dict):
        return changed
    for name, entry in stored_paths.items():
        if not wanted(str(name)) or not isinstance(entry, dict):
            continue
        recorded = entry.get("sha256")
        path = entry.get("path")
        if not isinstance(recorded, str) or not isinstance(path, str):
            continue
        current = file_sha256(Path(path))
        if current is not None and current != recorded:
            changed.append(str(name))
    return changed


def _unresolved_recorded_files(stored_paths: dict[str, Any]) -> list[str]:
    """Recorded names whose recorded path no longer resolves to a file now.

    Issue #165: a checkout that moved or was deleted leaves the record naming
    bytes that are no longer there. ``_changed_recorded_files`` cannot see
    this - an unreadable path yields no digest, so a missing path is neither
    "changed" nor "unchanged" and goes unreported. This names it. An unreadable
    but present file is not "missing": only a path that is no longer a file
    counts, so the condition is exactly the moved/deleted case.
    """
    missing: list[str] = []
    if not isinstance(stored_paths, dict):
        return missing
    for name, entry in stored_paths.items():
        if not isinstance(entry, dict):
            continue
        path = entry.get("path")
        if not isinstance(path, str) or not path:
            continue
        if not Path(path).is_file():
            missing.append(str(name))
    return missing


def seat_freshness(facts: dict[str, Any]) -> dict[str, Any]:
    """Report build drift. ``stale`` is true only for the restart-required set.

    ``baseline_exempt`` is the start-side fact: a direct checkout invocation
    reports drift and does not block. A ``~/.local/bin`` start is not exempt,
    even though its link resolves into the checkout. The comparison is the
    seat's own recorded paths, which is where a later install replaces the
    bytes. Every value appended to ``reported_drift`` is a member of
    ``REPORTED_DRIFT_VALUES`` (Issue #179); the prose surfaces name the field
    rather than listing them.

    Issue #165 adds a reported-only condition. ``recorded-path-missing``
    names a recorded runner path that no longer resolves to a file (the
    checkout moved or was deleted), with the names in ``missing_files``. It is
    evidence: it never sets ``stale`` and never gates transport.
    """
    build = facts.get("runner_build")
    known = isinstance(build, str) and len(build) == 12
    revision = facts.get("accepted_revision")
    if not isinstance(revision, str) or not REVISION_RE.fullmatch(revision):
        revision = None
    paths = facts.get("script_paths") if isinstance(facts.get("script_paths"), dict) else {}
    blocking: list[str] = []
    reported: list[str] = []
    if not known:
        reported.append("build-unrecorded")
    restart_changed = _changed_recorded_files(paths, _restart_required_name)
    cli_changed = _changed_recorded_files(
        paths, lambda name: name in ("kaola-acp.py", "kaola-tmux.sh"))
    if cli_changed:
        reported.append("cli-drift")
    # Issue #165: a recorded path that no longer resolves is neither changed nor
    # unchanged, so it is named here instead of passing unreported.
    missing = _unresolved_recorded_files(paths)
    if missing:
        reported.append("recorded-path-missing")
    # The start-side fact, not the resolved holder path. ~/.local/bin links
    # resolve into the checkout and still have a baseline.
    exempt = facts.get("baseline_exempt")
    if not isinstance(exempt, bool):
        exempt = _seat_from_checkout(facts)
    if exempt:
        if restart_changed:
            reported.append("checkout-drift")
    elif restart_changed:
        blocking.append("restart-required")
    pin = registration_pin()
    if pin and revision != pin:
        reported.append("pin-drift" if revision else "revision-unrecorded")
    return {
        "runner_build": build if known else None,
        "accepted_revision": revision,
        "stale": bool(blocking),
        "stale_reasons": blocking,
        "restart_files": restart_changed,
        "missing_files": missing,
        "reported_drift": reported,
        "baseline_exempt": exempt,
        "pin": pin,
    }


# Issue #215: the installer's runtime-name -> Skill-root map (mirrors
# install-local.sh runtime_skills_dir, honoring the same env overrides), so a
# skew refusal can name the OWNING runtime's own refresh route for a reported
# root instead of a generic --skills-dir path. Retired roots (droid's
# ~/.factory/skills) are deliberately absent -- they have no owner route.
INSTALLER_RUNTIME_ROOTS: dict[str, tuple[str | None, str]] = {
    "codex": ("CODEX_HOME", ".codex"),
    "claude-code": ("CLAUDE_CONFIG_DIR", ".claude"),
    "cursor": (None, ".cursor"),
    "devin": ("DEVIN_CONFIG_DIR", ".config/devin"),
    "zcode": (None, ".zcode"),
    "grok-cli": (None, ".grok"),
    "opencode": (None, ".config/opencode"),
    "kimi-cli": (None, ".agents"),
    "dsh": (None, ".agents"),
    "droid": (None, ".agents"),
}
INSTALLER_RUNTIME_EXTRA_ROOTS = {"kimi-cli": ("KIMI_CODE_HOME", ".kimi-code")}


def installer_runtime_roots() -> dict[str, list[str]]:
    """Runtime name -> its install destination roots under the current env."""
    home = str(Path.home())
    roots: dict[str, list[str]] = {}
    for runtime, (envvar, base) in INSTALLER_RUNTIME_ROOTS.items():
        override = os.environ.get(envvar) if envvar else None
        directory = override or os.path.join(home, base)
        roots[runtime] = [os.path.join(directory, "skills")]
    envvar, base = INSTALLER_RUNTIME_EXTRA_ROOTS["kimi-cli"]
    override = os.environ.get(envvar) if envvar else None
    directory = override or os.path.join(home, base)
    roots["kimi-cli"].append(os.path.join(directory, "skills"))
    return roots


def root_recorded_referrers(root: Path) -> list[str]:
    """Every referrer the root's install receipts record (Issue #215)."""
    found: set[str] = set()
    receipts = root / ".kaola-install-receipts"
    try:
        paths = sorted(receipts.glob("*.json"))
    except OSError:
        return []
    for path in paths:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        if data.get("receipt") != "kaola-project-runner-install/1":
            continue
        refs = data.get("referrers")
        if isinstance(refs, list):
            found.update(str(ref) for ref in refs)
    return sorted(found)


def owning_runtime(root: Path) -> str | None:
    """The runtime whose own install destination ``root`` is, or None.

    A recorded referrer that maps to this root wins (the ledger's own word on
    who owns the copies). With no such evidence a single candidate runtime is
    its own destination's owner; a shared root (``~/.agents/skills`` is droid,
    dsh and kimi-cli) prefers a single-destination runtime so the emitted route
    does not silently refresh kimi-cli's second root too."""
    real = os.path.realpath(root)
    candidates = [runtime for runtime, dirs in installer_runtime_roots().items()
                  if any(os.path.realpath(directory) == real for directory in dirs)]
    if not candidates:
        return None
    referrers = root_recorded_referrers(root)
    for runtime in sorted(candidates):
        if runtime in referrers:
            return runtime
    single = [runtime for runtime in sorted(candidates)
              if runtime != "kimi-cli" or len(candidates) == 1]
    return single[0] if single else sorted(candidates)[0]


def skill_refresh_route(roots: dict[str, list[str]], unmanaged: list[str],
                        workers_only: bool) -> str:
    """Issue #198, extended by #215: the existing installer route for each
    root a skew refusal reports, ``root -> --platform`` values, plus the
    matching ``--verify-install`` check. The emitted command is the root's
    OWNER route: ``--runtime NAME`` when the root is that runtime's own Skill
    directory (a recorded referrer wins the choice), ``--skills-dir`` only for
    a root no runtime owns -- the generic referrer, never claimed as the owner.
    A root whose other Skills also differ gets the complete-root refresh, not
    repeated single-platform installs. The installer, not this text, decides
    ownership; a copy under another name has no installer route."""
    text = ""
    if roots:
        scope = " --no-orchestrator" if workers_only else ""
        commands = []
        verifies = []
        ownership = []
        for root, platforms in roots.items():
            owner = owning_runtime(Path(root))
            complete = len(platforms) > 1
            platform_arg = "" if complete else f" --platform {','.join(platforms)}"
            if owner:
                commands.append(f"./scripts/install-local.sh --runtime {owner}"
                                f"{platform_arg}{scope}")
                ownership.append(f"{root} is the {owner} runtime's own Skill root")
            else:
                commands.append(f"./scripts/install-local.sh --skills-dir "
                                f"{shlex.quote(root)}{platform_arg}{scope}")
                ownership.append(f"{root} has no recorded runtime owner "
                                 f"(referrers: {', '.join(root_recorded_referrers(Path(root))) or 'none'})")
            if complete:
                verifies.append(
                    f"./scripts/render-skills.py --verify-install {shlex.quote(root)}")
            else:
                expect = list(platforms) + ([] if workers_only
                                            else [MAIN_SKILL_NAME])
                verifies.append(
                    f"./scripts/render-skills.py --verify-install {shlex.quote(root)}"
                    f" --expect {','.join(expect)}")
        text += (" From the accepted checkout, refresh each affected root with the "
                 f"existing installer ({'; '.join(ownership)}): {'; '.join(commands)}. "
                 f"Then verify the affected installed set: {'; '.join(verifies)}. "
                 "The installer replaces only a copy its receipt "
                 "(<root>/.kaola-install-receipts/<skill>.json) owns, keeps every other "
                 "referrer, and never replaces a foreign path. A --skills-dir install is "
                 "the generic referrer"
                 + ("" if workers_only else " and also plans kaola-delegator there")
                 + "; where a receipt lists a runtime referrer or the root is a "
                 "runtime's own Skills directory, that runtime's own --runtime NAME "
                 "install is the owner route -- the generic --skills-dir route is never "
                 "presented as the runtime owner. A root with other stale Skills gets "
                 "the complete-root refresh above (no --platform), not repeated "
                 "single-platform installs. An obsolete duplicate you own is withdrawn "
                 "with the same route plus --uninstall, which removes a copy only when "
                 "no referrer remains; never delete it by hand. If this Host cannot run "
                 "the authorized install itself, it reports this exact route to the "
                 "Delegator or operator and keeps its task and seat -- it never just "
                 "asks for a refresh.")
    if unmanaged:
        shown = unmanaged[:SKEW_DETAIL_CAP]
        more = "" if len(unmanaged) == len(shown) else f" (+{len(unmanaged) - len(shown)} more)"
        text += (f" {', '.join(shown)}{more}: renamed copy no installer manages; confirm "
                 "it is yours before moving it out of the Skill root.")
    return text


def stale_install_backup_recovery(paths: list[str]) -> str:
    """The quarantine command for the roots of the named hidden backups (#375)."""
    roots: list[str] = []
    for raw in paths:
        root = str(Path(raw).parent)
        if root not in roots:
            roots.append(root)
    module = _load_recovery_routes()
    text = ""
    if module is not None:
        _kind, text = module.lookup("stale-install-backup")
    if not text:
        text = ("Run ./scripts/install-local.sh --quarantine-stale-backups "
                "--skills-dir ROOT for each named root; it moves installer backups "
                "into the runner-owned quarantine and deletes nothing.")
    commands = [
        f"./scripts/install-local.sh --quarantine-stale-backups "
        f"--skills-dir {shlex.quote(root)}" for root in roots
    ]
    if commands:
        text += " Commands: " + "; ".join(commands) + "."
    return text


def attach_stale_install_backups(receipt: dict[str, Any],
                                 alignment: dict[str, Any]) -> dict[str, Any]:
    """Report hidden installer backups without making them a start blocker."""
    paths = alignment.get("stale_install_backups") if isinstance(alignment, dict) else None
    if not paths:
        return receipt
    receipt["stale_install_backups"] = paths
    receipt["stale_install_backup_count"] = len(paths)
    receipt["stale_install_backup_roots"] = sorted({str(Path(raw).parent) for raw in paths})
    receipt["stale_install_backup_recovery"] = stale_install_backup_recovery(paths)
    return receipt


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
    # Issue #198: the recovery names each reported root, never a guessed one.
    roots: dict[str, list[str]] = {}
    unmanaged: list[str] = []
    for entry in skew:
        path = Path(entry["path"])
        if path.name == MAIN_SKILL_NAME:
            roots.setdefault(str(path.parent), [args.platform])
        else:
            unmanaged.append(entry["path"])
    receipt = base_receipt(args, repo, include_git=False)
    receipt.update({
        "result": "refused",
        "reason": "main-skill-build-skew",
        "action": "start",
        "detail": (f"{len(skew)} installed {MAIN_SKILL_NAME} main Skill(s) do not match "
                   f"this Host build {alignment['build']}: {listed}{more}. Nothing was "
                   "started." + skill_refresh_route(roots, unmanaged, False)
                   + " The refusal is pre-mutation (mutation_status=not_started), so "
                   "after the refresh verifies, run the same start again."),
        "main_skill_build": alignment["build"],
        "main_skill_skew": shown,
        "main_skill_skew_count": len(skew),
        "mutation_performed": False,
        "mutation_status": "not_started",
    })
    return attach_stale_install_backups(receipt, alignment)


def worker_skill_root_refusal(args: argparse.Namespace, repo: str,
                              alignment: dict[str, Any]) -> dict[str, Any]:
    """Issue #106: an existing default discovery root could not be listed, so
    the installed worker Skills could not be compared with this build. A typed
    pre-mutation refusal in the Issue #105 shape - the caller gets the root
    names, not a traceback, and nothing is created."""
    roots = alignment["unreadable_roots"]
    receipt = base_receipt(args, repo, include_git=False)
    receipt.update({
        "result": "refused",
        "reason": "worker-skill-root-unreadable",
        "action": "start",
        "detail": (f"cannot verify installed worker Skills: {args.platform} discovery "
                   f"root(s) not readable: {', '.join(roots)}. Nothing was started. "
                   "Restore read access to that root through its owner (never delete a "
                   "Skill root to pass this check), then start again."),
        "worker_skill_build": alignment["build"],
        "worker_skill_unreadable_roots": roots,
        "mutation_performed": False,
        "mutation_status": "not_started",
    })
    return attach_stale_install_backups(receipt, alignment)


def worker_skill_skew_refusal(args: argparse.Namespace, repo: str,
                              alignment: dict[str, Any]) -> dict[str, Any]:
    """Issue #105: a typed pre-mutation refusal, the same shape as the
    heartbeat-host refusals - no record directory, no socket, no holder."""
    skew = alignment["skew"]
    shown = skew[:SKEW_DETAIL_CAP]
    listed = ", ".join(f"{entry['path']} ({entry['installed'] or 'missing'} "
                       f"!= {entry['expected']})" for entry in shown)
    more = "" if len(skew) == len(shown) else f" (+{len(skew) - len(shown)} more)"
    # Issue #198: each reported copy's root and platform, from its own path.
    roots: dict[str, list[str]] = {}
    unmanaged: list[str] = []
    for entry in skew:
        skill = Path(entry["path"]).parents[1]
        platform = skill.name.removesuffix(f"-{MAIN_SKILL_NAME}")
        if skill.name == f"{platform}-{MAIN_SKILL_NAME}" and platform in PLATFORMS:
            platforms = roots.setdefault(str(skill.parent), [])
            if platform not in platforms:
                platforms.append(platform)
        elif str(skill) not in unmanaged:
            unmanaged.append(str(skill))
    receipt = base_receipt(args, repo, include_git=False)
    receipt.update({
        "result": "refused",
        "reason": "worker-skill-build-skew",
        "action": "start",
        "detail": (f"{len(skew)} installed worker Skill script(s) do not match this "
                   f"Host build {alignment['build']}: {listed}{more}. Nothing was started."
                   + skill_refresh_route(roots, unmanaged, True)
                   + " The refusal is pre-mutation (mutation_status=not_started), so "
                   "after the refresh verifies, run the same start again."),
        "worker_skill_build": alignment["build"],
        "worker_skill_roots": alignment["roots"],
        "worker_skill_skew": shown,
        "worker_skill_skew_count": len(skew),
        "mutation_performed": False,
        "mutation_status": "not_started",
    })
    return attach_stale_install_backups(receipt, alignment)


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
    own_directory = record_dir(args, repo)
    for path in acp_paths.record_paths(f"*/*/{digest}/record.json",
                                      getattr(args, "record_root", None), all_roots=True):
        platform, session = path.parent.parent.parent.name, path.parent.parent.name
        if platform not in PLATFORMS or not host_session(platform, session):
            continue
        if ((platform, session) == (args.platform, args.session)
                and os.path.realpath(path.parent) == os.path.realpath(own_directory)):
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
    receipt = base_receipt(args, repo, include_git=False)
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


def pre_spawn_refusal(args: argparse.Namespace,
                      repo: str) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """The start refusals decided before any holder is stopped or spawned.
    Returns ``(refusal, facts)``: the refusal is ``None`` when the start may
    proceed, and ``facts`` then carries the worker Skill alignment, the main
    alignment (``None`` unless the worker alignment applies), ``hostish``,
    and the heartbeat resolution for ``command_start`` to reuse.
    ``drain-restart`` runs this first; a refusal leaves the live seat up.
    """
    if not host_capable(args.platform) and host_session(args.platform, args.session):
        return heartbeat_host_refusal(args, repo, {
            "source": "none", "dispatcher": None,
            "refusal": host_entry_unsupported(args.platform, "Host")}), {}
    if host_session(args.platform, args.session):
        hosts = verified_hosts(args, repo)
        if hosts:
            return host_exists_refusal(args, repo, hosts), {}
    error = bridge_runtime_error(args)
    if error is not None:
        receipt = base_receipt(args, repo)
        # Bridge and runtime-binary facts, no ``--version`` probe (#171):
        # the refusal returns without waiting on the runtime binary, and
        # never spawns the bridge or the holder.
        receipt.update(bridge_facts(args))
        receipt["error"] = error
        receipt["mutation_status"] = "not_started"
        receipt["mutation_performed"] = False
        return receipt, {}
    refused_child = codex_child_refusal(args, repo)
    if refused_child is not None:
        return refused_child, {}
    hostish = args.platform == "zcode" or (
        host_capable(args.platform) and host_session(args.platform, args.session))
    alignment = worker_skill_alignment(repo, args.platform)
    main_alignment = None
    if alignment["applies"]:
        if alignment["unreadable_roots"]:
            return worker_skill_root_refusal(args, repo, alignment), {}
        if alignment["skew"]:
            return worker_skill_skew_refusal(args, repo, alignment), {}
        main_alignment = main_skill_alignment(repo, args.platform)
        if main_alignment["skew"]:
            return main_skill_skew_refusal(args, repo, main_alignment), {}
    if hostish and args.platform == "zcode" and zcode_host_session(args.session):
        problem = zcode_host_request_problem(args)
        if problem is not None:
            return zcode_host_refusal(args, repo, problem), {}
    resolution = resolve_heartbeat_host(args, repo)
    if resolution["refusal"]:
        return heartbeat_host_refusal(args, repo, resolution), {}
    return None, {"alignment": alignment, "main_alignment": main_alignment,
                  "hostish": hostish, "resolution": resolution}


LAUNCH_BACKENDS = ("direct", "launchd", "auto", "systemd-user")


def resolved_launch_backend(args: argparse.Namespace) -> str:
    """Issue #266: explicit flag, else the inherited backend, else auto.

    ``auto`` uses the shared outside-caller launcher when it is available (the
    normal macOS path) and only degrades to direct when it is not. A Host started
    outside exports KAOLA_LAUNCH_BACKEND to its agent, so the seats it dispatches
    use the same path.
    """
    explicit = getattr(args, "launch_backend", None)
    if explicit:
        return explicit
    return os.environ.get("KAOLA_LAUNCH_BACKEND") or "auto"


def outside_launch_requested(args: argparse.Namespace) -> bool:
    return resolved_launch_backend(args) != "direct"


def attach_broker_reconcile(receipt: dict[str, Any], args: argparse.Namespace,
                            repo: str, directory: Path) -> None:
    """Issue #308: exact-stop reaps a stale exited one-shot for this session.

    An absent job adds nothing. A missing broker or an unsupported backend
    does not fail the stop. A reap, or a job that is still live or unreadable,
    is a short ``broker_job`` fact. The long recovery command stays on the
    broker refusal; this receipt only flags it.
    """
    broker = LAUNCH_BROKER
    if not broker.is_file() or not args.platform or not args.session or not repo:
        return
    run_base = directory / "launch"
    cmd = [sys.executable, str(broker), "reconcile",
           "--platform", args.platform, "--session", args.session, "--repo", repo,
           "--record-dir", str(directory), "--run-base", str(run_base),
           "--backend", "auto"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        out = json.loads(result.stdout)
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return
    if not isinstance(out, dict) or out.get("reason") == "launch-backend-unsupported":
        return
    if out.get("result") == "reconciled" and out.get("reaped") is True:
        receipt["broker_job"] = {"reaped": True, "label": out.get("label"),
                                 "result": "reconciled"}
    elif out.get("reason") in ("job-occupied", "job-state-unknown"):
        # Issue #371: an unreadable manager carries the read's own facts, so a
        # stop receipt says the caller was confined instead of implying a job.
        fact = {"reaped": False, "label": out.get("label"),
                "reason": out.get("reason"), "result": "refused"}
        if out.get("os_state"):
            fact["os_state"] = out["os_state"]
        if out.get("caller_confined") is not None:
            fact["caller_confined"] = bool(out["caller_confined"])
        receipt["broker_job"] = fact


def spawn_holder_outside(args: argparse.Namespace, repo: str, directory: Path,
                         holder_argv: list[str], holder_env: dict[str, str],
                         log_path: Path, sock: Path) -> dict[str, Any]:
    """Launch the holder as a one-shot per-user job; never through the caller.

    The broker receives only ``holder_env`` and filters it; the literal holder
    argv travels through a mode-600 exclusive file that is removed here.
    """
    broker = LAUNCH_BROKER
    requested = resolved_launch_backend(args)
    if not broker.is_file():
        if requested == "auto":
            return {"degraded": True, "detail": "the outside launcher is not installed"}
        return {"error": {"code": "launch-broker-missing",
                          "message": f"outside-caller launch requested but {broker} is not installed"}}
    run_base = directory / "launch"
    run_base.mkdir(parents=True, exist_ok=True)
    os.chmod(run_base, 0o700)
    argv_file = run_base / ("argv-" + secrets.token_hex(6) + ".json")
    fd = os.open(argv_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, json.dumps(holder_argv).encode("utf-8"))
    finally:
        os.close(fd)
    cmd = [sys.executable, str(broker), "submit",
           "--platform", args.platform, "--session", args.session, "--repo", repo,
           "--record-dir", str(directory), "--socket", str(sock), "--log", str(log_path),
           "--cwd", repo, "--run-base", str(run_base),
           "--backend", resolved_launch_backend(args), "--argv-json", str(argv_file)]
    # A resume's ready window has to cover the holder's wait plus the grace in
    # which a late load success corrects the record. The broker kills the holder
    # when that window ends. A fresh session keeps the broker default.
    if args.resume or args.use_continue:
        cmd += ["--ready-timeout", repr(resume_wait_seconds(args) + RESUME_RECOVERY_GRACE)]
    child_record = holder_env.get("KAOLA_ACP_CHILD_RECORD")
    if child_record:
        cmd += ["--child-record", child_record]
    for key in (args.manifest.get("acp_env_allowlist") or "").split(","):
        if key:
            cmd += ["--env-allow", key]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=START_WAIT + session_new_extra(args) + resume_window_extra(args) + 60,
            env={**holder_env})
    except subprocess.TimeoutExpired:
        return {"error": {"code": "launch-broker-timeout",
                          "message": "the outside launcher did not answer inside the window"},
                "holder_may_exist": True}
    finally:
        try:
            argv_file.unlink()
        except OSError:
            pass
    try:
        out = json.loads(result.stdout)
    except ValueError:
        return {"error": {"code": "launch-broker-failed",
                          "message": (result.stderr or result.stdout or "no broker receipt")[-300:]},
                "holder_may_exist": True}
    if out.get("result") not in ("ready", "existing"):
        # Issue #361: job-state-unknown under auto is the same class as
        # launch-backend-unsupported — the outside launcher cannot operate
        # (a sandboxed Host shell cannot read launchd state), so the seat
        # degrades to the direct path rather than refusing outright.
        if requested == "auto" and out.get("reason") in ("launch-backend-unsupported", "job-state-unknown"):
            return {"degraded": True, "detail": out.get("detail"), "reason": out.get("reason")}
        error = {"code": out.get("reason") or "launch-broker-failed",
                 "message": out.get("detail") or "outside launch refused"}
        if out.get("recovery"):
            error["recovery"] = out["recovery"]
        return {"error": error, "holder_may_exist": bool(out.get("holder_may_exist"))}
    return {"launch": out}


_BRIEF_ADMITTED = frozenset({"in_progress", "accepted", "completed"})


def read_start_brief(args: argparse.Namespace) -> str | None:
    """Text this start was asked to deliver, or None when no brief was requested.

    ``--stdin`` wins over ``--text``, matching ``send``. Whitespace is a brief.
    An empty string means the caller asked for a brief and supplied none.
    """
    if not getattr(args, "stdin", False) and getattr(args, "text", None) is None:
        return None
    if getattr(args, "stdin", False):
        return sys.stdin.read()
    text = getattr(args, "text", None)
    return text if isinstance(text, str) else ""


def brief_empty_receipt(args: argparse.Namespace, repo: str) -> dict[str, Any]:
    receipt = base_receipt(args, repo)
    receipt.update({
        "result": "refused",
        "reason": "brief-empty",
        "action": "start",
        "brief_delivered": False,
        "mutation_status": "not_started",
        "mutation_performed": False,
        "detail": "start with --stdin or --text received no brief text; nothing was started",
    })
    return receipt


def stamp_brief_undelivered(receipt: dict[str, Any], reason: str, *,
                            detail: str | None = None, admitted: bool = False,
                            turn_id: Any = None,
                            request_mutation: dict[str, Any] | None = None,
                            request_fingerprint: str | None = None,
                            request_verify: dict[str, Any] | None = None
                            ) -> dict[str, Any]:
    """A requested brief was not verified as a dispatch.

    Drop ``ready`` and, for a proven no-write, ``prompt_fingerprint`` so neither
    can be read as a dispatch. A turn that was admitted keeps its id and
    mutation. When the prompt request itself returned a mutation fact, that fact
    wins: a frame that may have been written stays ``null``/``unknown`` instead
    of being flattened to unsent. That uncertain case keeps the request's
    fingerprint and ``verify`` block: they are the only way a start consumer can
    locate a late admission, and neither claims the brief was delivered.
    """
    uncertain = bool(
        request_mutation
        and "mutation_performed" in request_mutation
        and request_mutation.get("mutation_performed") is None)
    if uncertain and request_fingerprint:
        receipt["prompt_fingerprint"] = request_fingerprint
    else:
        receipt.pop("prompt_fingerprint", None)
    if uncertain and isinstance(request_verify, dict) and request_verify:
        receipt["verify"] = request_verify
    else:
        receipt.pop("verify", None)
    if admitted and turn_id is not None:
        receipt["turn_request_id"] = turn_id
    else:
        receipt.pop("turn_request_id", None)
    if receipt.get("state") == "ready":
        receipt.pop("state", None)
    receipt["brief_delivered"] = False
    if receipt.get("result") != "refused":
        receipt["result"] = "refused"
        receipt["reason"] = reason
        receipt.setdefault("action", "start")
    elif not receipt.get("reason"):
        receipt["reason"] = reason
    if request_mutation:
        for key in ("mutation_performed", "mutation_status"):
            if key in request_mutation:
                receipt[key] = request_mutation[key]
    if (not admitted and not request_mutation
            and receipt.get("mutation_status")
            in (None, "in_progress", "accepted", "completed")):
        receipt["mutation_status"] = "not_started"
        receipt["mutation_performed"] = False
    if detail and "detail" not in receipt:
        receipt["detail"] = detail
    return receipt


def _brief_failure_reason(reply: dict[str, Any], probed: dict[str, Any] | None,
                          seen_fingerprint: str | None, expected: str) -> str:
    if seen_fingerprint and seen_fingerprint != expected:
        return "brief-fingerprint-mismatch"
    error = reply.get("error")
    if isinstance(error, dict) and isinstance(error.get("code"), str) and error["code"]:
        return error["code"]
    if isinstance(probed, dict):
        probe_error = probed.get("error")
        if isinstance(probe_error, dict) and isinstance(probe_error.get("code"), str):
            return probe_error["code"]
    outcome = reply.get("outcome")
    if outcome in ("turn_failed", "process_exited", "no_session", "stopping"):
        return str(outcome)
    return "brief-turn-unverified"


def deliver_start_brief(args: argparse.Namespace, repo: str, receipt: dict[str, Any],
                        text: str) -> dict[str, Any]:
    """Send ``text`` as this session's first prompt and require admission.

    Wait resolution matches ``send``. ``--no-wait`` returns at admission and
    does not wait for the turn to end. ``ready`` is a dispatch only when the
    turn id, the real fingerprint, and an admitted mutation are all present.
    """
    directory = record_dir(args, repo)
    wait_selection, bound_holder_id = resolve_send_wait(args, repo, directory)
    timeout = args.timeout
    sock_timeout = client_socket_timeout(args, wait_selection["wait"],
                                         op="prompt")
    prompt_params: dict[str, Any] = {
        "text": text,
        "wait": wait_selection["wait"],
        "timeout": timeout,
        "max_final_chars": args.max_final_chars,
    }
    if args.expected_holder_instance_id is not None:
        prompt_params["expected_holder_instance_id"] = args.expected_holder_instance_id
    elif bound_holder_id is not None:
        prompt_params["expected_holder_instance_id"] = bound_holder_id
    reply = op_or_holder_lost(args, repo, directory, "prompt", prompt_params, sock_timeout)
    expected = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
    probed: dict[str, Any] | None = None
    sock = sock_path(args, repo)
    if sock.exists():
        probed = socket_request(sock, "state", {}, 5.0)
    probe_ok = isinstance(probed, dict) and bool(probed.get("state")) and "error" not in probed
    last: dict[str, Any] = {}
    turn_id = reply.get("turn_request_id")
    seen_fp = reply.get("prompt_fingerprint")
    if probe_ok and isinstance(probed, dict):
        raw_last = probed.get("last_prompt")
        if isinstance(raw_last, dict):
            last = raw_last
        if turn_id is None:
            turn_id = probed.get("turn_request_id")
        if not isinstance(seen_fp, str) or not seen_fp:
            seen_fp = last.get("fingerprint")
    reply_mutation = reply.get("mutation_status")
    last_mutation = last.get("mutation_status")
    admitted_mutation = reply_mutation if reply_mutation in _BRIEF_ADMITTED else last_mutation
    verified = (
        probe_ok
        and turn_id is not None
        and admitted_mutation in _BRIEF_ADMITTED
        and last_mutation in _BRIEF_ADMITTED
        and seen_fp == expected
        and last.get("fingerprint") == expected
    )
    if verified and isinstance(probed, dict):
        receipt["brief_delivered"] = True
        receipt["turn_request_id"] = turn_id
        receipt["prompt_fingerprint"] = expected
        receipt["mutation_status"] = admitted_mutation
        receipt["mutation_performed"] = True
        receipt["outcome"] = reply.get("outcome")
        if reply.get("dispatch_event_cursor") is not None:
            receipt["dispatch_event_cursor"] = reply["dispatch_event_cursor"]
        if reply.get("stop_reason") is not None:
            receipt["stop_reason"] = reply["stop_reason"]
        receipt["wait_selection"] = wait_selection
        holder_state = probed.get("state")
        if isinstance(holder_state, str) and holder_state:
            receipt["state"] = holder_state
        return receipt
    reason = _brief_failure_reason(
        reply, probed if isinstance(probed, dict) else None,
        seen_fp if isinstance(seen_fp, str) else None, expected)
    admitted = admitted_mutation in _BRIEF_ADMITTED and turn_id is not None
    detail = None
    if receipt.get("acp_session_id") or receipt.get("holder_pid"):
        detail = ("the seat is up but this start did not verify the brief turn; "
                  "this receipt is not a dispatch")
    request_mutation = {
        key: reply[key] for key in ("mutation_performed", "mutation_status")
        if key in reply
    }
    request_fingerprint = reply.get("prompt_fingerprint")
    request_verify = reply.get("verify")
    stamp_brief_undelivered(
        receipt, reason, detail=detail, admitted=admitted, turn_id=turn_id,
        request_mutation=request_mutation,
        request_fingerprint=(request_fingerprint
                             if isinstance(request_fingerprint, str) else None),
        request_verify=(request_verify
                        if isinstance(request_verify, dict) else None))
    reply_error = reply.get("error")
    if isinstance(reply_error, dict) and "error" not in receipt:
        receipt["error"] = reply_error
    return receipt


def apply_start_brief(args: argparse.Namespace, repo: str, receipt: dict[str, Any],
                      text: str) -> dict[str, Any]:
    if (receipt.get("state") == "ready" and receipt.get("result") != "refused"
            and "error" not in receipt and receipt.get("acp_session_id")):
        return deliver_start_brief(args, repo, receipt, text)
    reason = receipt.get("reason")
    if not isinstance(reason, str) or not reason:
        error = receipt.get("error")
        code = error.get("code") if isinstance(error, dict) else None
        reason = code if isinstance(code, str) and code else "brief-not-started"
    detail = None
    if receipt.get("state") == "ready" or receipt.get("acp_session_id"):
        detail = ("the seat is up but this start did not deliver the brief; "
                  "this receipt is not a dispatch")
    return stamp_brief_undelivered(receipt, reason, detail=detail)


def command_start(args: argparse.Namespace, repo: str,
                  decided: tuple[dict[str, Any] | None, dict[str, Any]] | None = None
                  ) -> dict[str, Any]:
    # Issue #344: a brief is the first prompt turn. No brief leaves this start
    # exactly as it was (ready, no turn).
    brief = read_start_brief(args)
    if brief == "":
        return brief_empty_receipt(args, repo)
    receipt = _command_start_seat(args, repo, decided)
    if brief is None:
        return receipt
    return apply_start_brief(args, repo, receipt, brief)


def _command_start_seat(args: argparse.Namespace, repo: str,
                        decided: tuple[dict[str, Any] | None, dict[str, Any]] | None = None
                        ) -> dict[str, Any]:
    # A caller that already ran the pre-spawn decision, like drain-restart
    # before it stops anything, hands its result in so the installed Skill
    # roots are scanned once, not twice.
    directory = record_dir(args, repo)
    acp_paths.check_record_root(directory.parent.parent.parent)
    refused, facts = decided if decided is not None else pre_spawn_refusal(args, repo)
    if refused is not None:
        return refused
    # Every pre-spawn refusal (#122/#132, bridge/runtime, #105/#106/#121,
    # #108, heartbeat) already returned; the facts computed there ride along.
    receipt = base_receipt(args, repo)
    receipt.update(bridge_facts(args))
    # Issue #162: every platform's worker start, not only ZCode and Host-named
    # sessions. A direct checkout invocation still has no baseline. A
    # ~/.local/bin start does: the link's target is the accepted checkout.
    alignment = facts["alignment"]
    main_alignment = facts["main_alignment"]
    if alignment["applies"] or facts["hostish"]:
        # Issue #121: the main Skill ships no scripts, so it is not in #105's
        # set; an unaligned checkout start has no main-Skill record either.
        receipt["worker_skill_build"] = alignment["build"]
        receipt["worker_skill_roots"] = alignment["roots"]
        receipt["main_skill_build"] = (main_alignment or {}).get("build")
        attach_stale_install_backups(receipt, alignment)
    resolution = facts["resolution"]
    heartbeat_host = resolution["target"]
    # What this command asked for, and where that request came from. The fact
    # that decides whether a worker can wake a Host is the holder's own, read
    # back below.
    receipt["heartbeat_host_requested"] = heartbeat_host
    receipt["heartbeat_host_source"] = resolution["source"]
    receipt["dispatcher"] = resolution["dispatcher"]
    # Issue #181: the one default-fill site. The effective permission mode is
    # resolved here and used both for the recorded start_selection and for the
    # ACP config option below, so a recorded mode is never a raw None that a
    # later command has to re-derive.
    mode_value = args.mode or ACP_SKIP_MODE.get(args.platform)
    record = read_record(directory)
    # Issue #203: read before the new holder replaces it; the only source of
    # evidence a resume of the same native session may inherit.
    prior_record = record
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
        # Issue #299/#319: wake eligibility is this dead or proven
        # pid-reused holder. A live agent does not suppress the wake.
        # It only blocks replacement: the record stays until the caller
        # exact-stops that orphan. The receipt carries the agent pids
        # and the holder-lost route; the wake payload does not.
        death_wake = recover_host_death_wake(directory, record)
        if death_wake is not None:
            receipt["delegator_death_wake"] = death_wake
        if pid_alive(record.get("agent_pgid")) or pid_alive(record.get("agent_pid")):
            receipt.update(holder_lost_receipt(args, repo, record))
            return receipt
    else:
        # Issue #359: no record, but a surviving registry row proves a Host
        # ran here. Emit the owed record-loss wake once; a live argv-verified
        # orphan refuses this start (sweep it with `stop --force` first), a
        # dead or pid-reused one is replaced.
        lost_row = host_registry_row(repo, args.platform, args.session)
        if lost_row is not None:
            receipt["record_lost"] = _record_loss_recovery(
                lost_row, pid_alive(lost_row.get("holder_pid")))
            death_wake = _record_loss_wake_marked(repo, lost_row)
            if death_wake is not None:
                receipt["delegator_death_wake"] = death_wake
            lost_pid = lost_row.get("holder_pid")
            if pid_alive(lost_pid):
                lost_directory = Path(lost_row["record_dir"]) \
                    if isinstance(lost_row.get("record_dir"), str) else None
                anchor = holder_argv_anchor(lost_pid, lost_directory) \
                    if lost_directory is not None else None
                if anchor is not False:
                    receipt.update({
                        "result": "refused",
                        "reason": "record-lost-orphan",
                        "detail": "the session's record directory is gone and "
                                  "its registered holder pid is still alive; "
                                  "run `stop --force` to sweep the orphan, "
                                  "then start --resume with the recorded "
                                  "acp_session_id",
                        "holder_pid": lost_pid,
                        "holder_instance_id": lost_row.get("holder_instance_id"),
                        "mutation_status": "not_started",
                        "mutation_performed": False,
                    })
                    return receipt
                receipt["replaced_record"] = {
                    "holder_pid": lost_pid, "pid_reused": True,
                    "record_lost": True,
                    "holder_instance_id": lost_row.get("holder_instance_id")}
            else:
                receipt["replaced_record"] = {
                    "holder_pid": lost_pid, "record_lost": True,
                    "holder_instance_id": lost_row.get("holder_instance_id")}
    acp_paths.prepare_record_directory(directory, directory.parent.parent.parent)
    if receipt.get("replaced_record"):
        try:
            sock_path(args, repo).unlink()
        except OSError:
            pass
    log_path = directory / "holder.out.log"
    # Issue #388: the seat's own role decides whether it may carry the Host
    # heartbeat prompt. Only a Host holder gets the platform's measured entry;
    # every other role is started without --host-entry (the holder parser's
    # empty default), so a worker/Expert holder cannot open Project Runner as
    # its self-prompt. A resume whose same-native-session role is not yet
    # provable stays null here and records the inherited role afterwards.
    role = session_role_value(args, selection_basis(args), prior_record, repo)
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
    if args.resume or args.use_continue:
        # The holder does not read KAOLA_RESUME_* itself: the broker drops
        # unlisted environment names, and the client is the one place that
        # computes the wait.
        holder_argv += ["--resume-timeout", repr(resume_wait_seconds(args))]
    # Issue #119: the Host turn-opening entry and name come from this platform's
    # own manifest, never from the platform id. Issue #388: only a Host holder
    # is given the entry; omitting the flag leaves the holder's explicit empty
    # default in force (a direct ZCode holder with no --session-role keeps its
    # legacy fallback).
    if role == "host":
        holder_argv += ["--host-entry", args.manifest.get("host_skill_entry") or ""]
    holder_argv += ["--host-name", args.manifest.get("runtime_name") or args.platform]
    holder_argv += ["--session-new-timeout", repr(session_new_timeout(args))]
    # Issue #369: the platform's measured tool-cwd facts, and the native
    # steering entry the holder's own cwd notice may use.
    holder_argv += ["--tool-cwd-note-regex", str(args.manifest.get("tool_cwd_note_regex") or ""),
                    "--shell-cwd-persistence", str(args.manifest.get("shell_cwd_persistence") or ""),
                    "--tool-shell", str(args.manifest.get("tool_shell") or ""),
                    "--steer-method", (args.manifest.get("acp_steer_method") or "").strip(),
                    "--native-steering", (args.manifest.get("native_steering") or "").strip()]
    init_meta = parse_manifest_meta(args.manifest.get("acp_init_meta") or "")
    if init_meta:
        holder_argv += ["--init-meta", json.dumps(init_meta)]
    holder_env = agent_environment(args)
    if args.platform == "opencode":
        receipt["native_permission_policy"] = opencode_launch_policy(args, repo, directory, holder_env)
    # Issue #162: the accepted revision is holder argv, never an agent
    # environment variable, so nothing carries it into the holder's env.
    accepted = current_accepted_revision()
    holder_argv += ["--accepted-revision", accepted or ""]
    holder_argv += ["--baseline-exempt", "1" if skew_baseline_dir() is None else "0"]
    # Issue #245: role was computed before spawn, where it also decides the
    # Host carrier (#388). A resume-preserved role stays null until the native
    # session id proves the same session, below.
    receipt["session_role"] = role
    holder_argv += ["--session-role", role or ""]
    # Issue #181: effective values, not raw flags. Absent --fast means the
    # seat runs with Fast off, and an omitted --mode means the platform
    # default resolved above; recording either as None would make
    # drain-restart lose a state this start really applied.
    start_selection = {
        "model": args.model,
        "effort": args.effort,
        "tier": args.tier,
        "fast": fast_intent(args),
        "mode": mode_value,
        "session_role": role,
        "launch_backend": resolved_launch_backend(args),
    }
    # Issue #316: a preserved resume omitted --tier. Record that. A resume
    # that passed --tier keeps the tier word and does not get this reason.
    if resume_without_requested_tier(args):
        start_selection["tier_reason"] = "resume-without-tier"
    holder_argv += ["--start-selection", json.dumps(start_selection, sort_keys=True)]
    cli_version = cli_version_fact(args, holder_env)
    if cli_version is not None:
        holder_argv += ["--cli-version", json.dumps(cli_version, sort_keys=True)]
    sock = sock_path(args, repo)
    if heartbeat_host is not None:
        # Hand the holder the target this command validated and resolved,
        # so the binding it reports back is the one that was checked here
        # rather than a re-reading of the caller's raw string.
        holder_env[HEARTBEAT_HOST_ENV] = json.dumps(heartbeat_host, sort_keys=True)
        holder_env[HEARTBEAT_HOST_SOCKET_ENV] = heartbeat_host["socket"]
    proc: subprocess.Popen | None = None
    holder_pid_hint: int | None = None
    request = resolved_launch_backend(args)
    if request != "direct":
        # Issue #266: name the backend to the holder so its seats inherit it.
        holder_env["KAOLA_LAUNCH_BACKEND"] = request
    launched = None
    if request != "direct":
        launched = spawn_holder_outside(args, repo, directory, holder_argv, holder_env, log_path, sock)
        if launched.get("degraded"):
            # auto: the outside launcher is unavailable; fall back to the
            # explicit direct path and say so in the receipt.
            receipt["launch_backend_degraded"] = True
            if launched.get("reason"):
                receipt["launch_backend_fallback_reason"] = launched["reason"]
            if launched.get("detail"):
                receipt["launch_backend_fallback_detail"] = launched["detail"]
            launched = None
        elif "error" in launched:
            receipt["error"] = launched["error"]
            # A holder may already exist; report that truth instead of not_started.
            if launched.get("holder_may_exist"):
                receipt["mutation_status"] = "unknown"
                receipt["mutation_performed"] = None
            else:
                receipt["mutation_status"] = "not_started"
                receipt["mutation_performed"] = False
            return receipt
    if launched is None:
        receipt.setdefault("launch_backend", "direct")
        with open(log_path, "ab") as log:
            proc = subprocess.Popen(
                holder_argv, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                start_new_session=True, env=holder_env,
            )
        holder_pid_hint = proc.pid
        # When this start runs inside an outer agent (nested Host/Worker chain),
        # record the holder's identity for the outer holder's exact sweep.
        child_record = record_holder_child_spawn(proc)
        if child_record is not None:
            receipt["child_record"] = child_record
    else:
        # Issue #361: report the actual backend the broker used so the receipt
        # proves whether auto resolved to launchd, systemd-user, or an
        # explained fallback.
        if launched["launch"].get("backend"):
            receipt["launch_backend"] = launched["launch"]["backend"]
        holder_pid_hint = launched["launch"].get("holder_pid")
        if launched["launch"].get("child_record") is not None:
            receipt["child_record"] = launched["launch"]["child_record"]
    deadline = time.monotonic() + START_WAIT + session_new_extra(args) + resume_window_extra(args)
    state: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        if sock.exists():
            state = socket_request(sock, "state", {}, 5.0)
            if "error" not in state or state.get("error", {}).get("code") != "holder-unreachable":
                # A resume that is still pending is not terminal: the load may
                # answer inside the grace and clear the failure.
                if state.get("state") in ("ready", "agent_exited"):
                    break
                if state.get("state") == "error" and not state.get("resume_pending"):
                    break
        if not pid_alive(holder_pid_hint):
            break
        time.sleep(0.1)
    if state is None:
        record = read_record(directory) or {}
        receipt["error"] = {"code": "holder-start-timeout",
                            "message": "holder did not report within the start window",
                            "holder_pid": holder_pid_hint}
        return receipt
    receipt.update({
        "holder_pid": state.get("holder_pid", holder_pid_hint),
        "holder_instance_id": state.get("holder_instance_id"),
        "agent_pid": state.get("agent_pid"),
        "acp_session_id": state.get("acp_session_id"),
        "state": state.get("state"),
        "baseline_exempt": state.get("baseline_exempt"),
    })
    attach_binding_fact(receipt, state)
    # Issue #359: durable registration outside the record root. The row makes
    # a wiped record directory detectable by the status/list scans; a clean
    # stop removes it. A registry write failure must not fail the start.
    if (role == "host"
            and isinstance(state.get("holder_instance_id"), str)
            and state["holder_instance_id"]):
        registered = host_registry_register(repo, {
            "platform": args.platform,
            "session": args.session,
            "repo": repo,
            "record_dir": str(directory),
            "socket_path": str(sock),
            "holder_pid": state.get("holder_pid", holder_pid_hint),
            "holder_instance_id": state["holder_instance_id"],
            "acp_session_id": state.get("acp_session_id"),
            "agent_pid": state.get("agent_pid"),
            "agent_pgid": state.get("agent_pgid"),
        })
        if not registered:
            receipt["host_registry"] = "unrecorded"
    receipt["transport"]["protocol_version"] = state.get("protocol_version")
    receipt["transport"]["agent_info"] = state.get("agent_info")
    versions = codex_version_fact(args, state.get("agent_pid"), state.get("agent_info"))
    if versions is not None:
        receipt["codex_versions"] = versions
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
            if label == "model" and value == argv_model(args.agent_command):
                # Issue #140: the spawn argv already set this model; a
                # redundant option apply is rejected by an agent that does not
                # offer the id on its ACP option, without reverting it.
                application[label] = {"applied": True, "applied_via": "argv",
                                      "value": value}
                continue
            config_id = args.manifest.get(key or "")
            candidates: list[str] = []
            advertised = False
            if label == "effort" and config_id:
                # The effort id follows the model just applied: resolve it
                # against the options the agent now advertises (Issue #135).
                candidates = parse_config_id_candidates(config_id)
                config_id, advertised = resolve_config_id(
                    candidates, socket_request(sock, "state", {}, 10.0))
            if not config_id and label == "effort" and effort_applied_by_model_id(
                    application.get("model"), acp_model_value, value):
                # Issue #331: no effort option is advertised, and the accepted
                # model ID already carries this effort — it is applied.
                application[label] = {"applied": True, "applied_via": "model-id",
                                      "value": value}
                continue
            if not config_id:
                application[label] = {
                    "applied": False,
                    "reason": "no-advertised-config-option",
                    "manifest_key": key,
                    "value": value,
                }
                continue
            if args.platform == "opencode" and label == "model":
                result = set_opencode_model_when_advertised(
                    sock, config_id, value, directory,
                    receipt.get("holder_instance_id"))
            else:
                # Issue #408: a bound seat requires the token (from this
                # seat's own record dir) plus the instance id its state
                # reply already named.
                params: dict[str, Any] = {"config_id": config_id, "value": value}
                if receipt.get("holder_instance_id") is not None:
                    params["expected_holder_instance_id"] = receipt["holder_instance_id"]
                result = socket_request(sock, "set_config_option", params, 20.0, directory)
            record: dict[str, Any] = {"applied": not result.get("error"),
                                      "config_id": config_id, "value": value}
            if label == "model":
                if resolved_model and value != resolved_model:
                    record["requested_id"] = resolved_model
                    record["mapped"] = True
                declared = acp_value_params(value)
                if declared:
                    record["declared"] = declared
            if label == "effort":
                record["candidates"] = candidates
                record["advertised"] = advertised
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
                fast_state = (
                    resolved_fast_state
                    if resolved_fast_state in ("on", "off")
                    else fast_intent(args)
                )
                fast_value = parse_manifest_value_map(
                    args.manifest.get("acp_fast_values") or ""
                ).get(fast_state, fast_state)
                params = {"config_id": fast_id, "value": fast_value}
                if receipt.get("holder_instance_id") is not None:
                    params["expected_holder_instance_id"] = receipt["holder_instance_id"]
                result = socket_request(
                    sock, "set_config_option", params, 20.0, directory,
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
                        effective="on" if fast_state == "on" else "off",
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
                    if fast_intent(args) != effective:
                        receipt["fast"]["conflict"] = (
                            f"requested --fast {fast_intent(args)}; applied model value "
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
            if args.resume or args.use_continue:
                # Issue #363: dsh pins the permission preset into the session
                # log at creation and keeps the recorded value on resume, so
                # the launch variable travels but never applies to a resumed
                # session. Report the request separately from the session's
                # own effective facts, read back from that log.
                entry: dict[str, Any] = {"applied": False, "requested_via": "env",
                                         "env": DSH_PERMISSION_ENV, "value": value,
                                         "source": source, "reason": "resumed-session-permission"}
                effective_mode = dsh_session_permission(repo, receipt.get("acp_session_id"))
                if effective_mode is not None:
                    entry["effective"] = effective_mode
                    entry["effective_via"] = "session-log"
            else:
                # Issue #360: ``applied`` follows the environment the holder
                # was actually launched with, not the intent. A direct spawn
                # gets ``holder_env`` verbatim; the broker receipt names the
                # keys its filter passed (``env_keys``). A reconciled
                # "existing" holder was spawned by an earlier start, so this
                # one delivered no environment — its own start record carries
                # that evidence.
                launch = (launched or {}).get("launch") or {}
                env_keys = launch.get("env_keys")
                if launched is None:
                    delivered = holder_env.get(DSH_PERMISSION_ENV)
                    reason = "holder-env-missing"
                elif isinstance(env_keys, list):
                    delivered = (value if DSH_PERMISSION_ENV in env_keys else None)
                    reason = "dropped-by-launch-env-filter"
                else:
                    delivered = None
                    reason = ("existing-holder-env-not-redelivered"
                              if launch.get("result") == "existing"
                              else "env-census-absent")
                entry = {"applied": delivered is not None,
                         "applied_via": "env", "env": DSH_PERMISSION_ENV,
                         "value": delivered or value, "source": source}
                if delivered is None:
                    entry["reason"] = reason
            application["mode"] = entry
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
                params = {"config_id": config_id, "value": mode_value}
                if receipt.get("holder_instance_id") is not None:
                    params["expected_holder_instance_id"] = receipt["holder_instance_id"]
                result = socket_request(sock, "set_config_option", params, 20.0, directory)
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
        # Issue #185: droid's verdict reads the agent's raw echo here, before
        # the Issue #140 block below replaces the display value with the argv.
        echo_verdict = echo_model_verification(args.platform, policy, effective)
        # Issue #140: devin's advertised currentValue stays the stale
        # initial value when the argv set the model; keep it as evidence.
        apply_argv_model(effective, application)
        receipt["effective_selection"] = effective
        # Issue #342: Devin's thought_level currentValue is the effort readback.
        # It runs after the argv overlay, so effective_model is the argv id and
        # the stale ACP model currentValue is not the compared model.
        thought_verdict = argv_thought_verification(policy, effective, application)
        verdict = echo_verdict if echo_verdict is not None else thought_verdict
        if verdict is not None:
            receipt.update(verdict)
            provenance = policy.setdefault("model_evidence_provenance", {})
            provenance["actual"] = {
                "source": ("acp-config-echo" if echo_verdict is not None
                           else "acp-thought-level"),
                "model_id": verdict["actual_runtime_model_id"],
                "parameters": verdict["actual_parameters"],
            }
            receipt["model_evidence_provenance"] = provenance
        continuity = reconcile_selection_continuity(
            resumed=bool(args.resume or args.use_continue),
            explicit=bool(args.model or args.effort or args.tier),
            recorded_source=policy.get("requested_model_source"),
            recorded_model=policy.get("resolved_runtime_model_id") or None,
            recorded_effort=(policy.get("resolved_parameters") or {}).get("effort") or None,
            application=application,
            fresh=effective,
            inherited=inherited_start_evidence(
                prior_record, args, repo, receipt.get("acp_session_id")),
        )
        receipt["selection_continuity"] = continuity
        selection = receipt.get("model_selection")
        if isinstance(selection, dict) and selection.get("override_omitted") is True:
            # True only when the fresh readback proved continuity with the
            # prior applied selection. No prior, an unreadable readback, and
            # a difference all stay false.
            selection["preserved"] = continuity.get("prior_settings_preserved") is True
        explicit_model = acp_model_value if args.model else ""
        explicit_effort = effort_value if args.effort else ""
        rejected = application.get("model") or {}
        if (rejected.get("applied") is False and isinstance(rejected.get("error"), dict)
                and not getattr(args, "allow_unapplied_model", False)):
            # Issue #339: the agent answered the resolved model option with an
            # error, so this session would run the agent's own model, not the
            # selected one (a dsh seat advertised as opencode-go/deepseek-v4.1-
            # flash ran deepseek-official/deepseek-v4-flash behind a ``ready``
            # receipt). An option the agent never advertises is still a
            # limitation receipt (``no-advertised-config-option``): no set was
            # attempted and nothing is refused.
            stopped = stop_started_holder(sock, proc, holder_pid_hint,
                                          receipt.get("holder_instance_id"),
                                          directory)
            reclaimed = stopped.get("holder_reclaimed") is True
            failure = rejected["error"]
            receipt.update({
                "result": "refused",
                "reason": "model-config-option-rejected",
                "action": "start",
                "error": failure,
                "detail": (f"the {args.platform} agent rejected the resolved model option "
                           f"{rejected.get('config_id')}={rejected.get('value')!r} "
                           f"({(failure.get('detail') or {}).get('message') or failure.get('code')}); "
                           "the session was stopped before this start returned, and no other model "
                           "was substituted; pass --allow-unapplied-model to accept the agent's own "
                           "selection instead."),
                **stopped,
                "mutation_performed": False if reclaimed else None,
                "mutation_status": "not_started" if reclaimed else "unknown",
            })
            return receipt
        problem = (explicit_selection_problem(explicit_model, explicit_effort, effective)
                   if args.platform in EXPLICIT_SELECTION_VERIFIED else None)
        if problem is not None:
            stopped = stop_started_holder(sock, proc, holder_pid_hint,
                                          receipt.get("holder_instance_id"),
                                          directory)
            reclaimed = stopped.get("holder_reclaimed") is True
            receipt.pop("error", None)
            receipt.update({
                "result": "refused",
                "reason": "explicit-selection-unverified",
                "action": "start",
                "detail": (f"the {args.platform} agent did not report the explicit "
                           f"selection: {problem}; the session was stopped before this "
                           "start returned, and no other model was substituted."),
                **stopped,
                "mutation_performed": False if reclaimed else None,
                "mutation_status": "not_started" if reclaimed else "unknown",
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
                stopped = stop_started_holder(sock, proc, holder_pid_hint,
                                              receipt.get("holder_instance_id"),
                                              directory)
                reclaimed = stopped.get("holder_reclaimed") is True
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
                    "mutation_performed": False if reclaimed else None,
                    "mutation_status": "not_started" if reclaimed else "unknown",
                })
                return receipt
        record_start_evidence(sock, receipt, args, repo, prior_record)
    return receipt


def _seat_idle(state: dict[str, Any]) -> bool:
    if state.get("turn_active"):
        return False
    pending = state.get("pending_permissions") or []
    if isinstance(pending, list) and pending:
        return False
    holder_state = state.get("state")
    if holder_state == "agent_exited":
        return True
    return holder_state == "ready" and state.get("activity_hint") in (None, "idle")


def _selection_explicit(args: argparse.Namespace) -> dict[str, bool]:
    """Which selection flags this invocation actually passed.

    Every selection flag defaults to ``None`` (Issue #181), so absence is a
    ``None`` value: argparse handles prefix abbreviations, ``--flag=value``,
    and every other spelling the parser accepts, which a ``sys.argv`` re-read
    could not.
    """
    return {
        "model": args.model is not None,
        "effort": args.effort is not None,
        "tier": args.tier is not None,
        "fast": args.fast is not None,
        "mode": args.mode is not None,
        "command": args.agent_command_given,
        "launch_backend": args.launch_backend is not None,
    }


def apply_recorded_selection(args: argparse.Namespace, record: dict[str, Any]) -> dict[str, Any] | None:
    """Fill omitted model/effort/tier/fast/mode from the seat's recorded start.

    Returns None when the record has no selection and the caller passed none
    of model, effort, tier, fast, or mode, so drain-restart can refuse before
    it stops the seat. An explicit flag wins over the record. The recorded
    mode is the effective mode the previous start applied (Issue #181), so
    there is no default to re-derive here: a platform with no default recorded
    ``null`` and the restart stays unset. The agent command is re-resolved when
    the caller did not pass ``--command``, because a tier can change it.
    """
    saved = record.get("start_selection")
    saved = saved if isinstance(saved, dict) else None
    explicit = _selection_explicit(args)
    if saved is None and not any(explicit[key] for key in ("model", "effort", "tier", "fast", "mode")):
        return None
    if saved:
        if not explicit["model"] and isinstance(saved.get("model"), str):
            args.model = saved["model"]
        if not explicit["effort"] and isinstance(saved.get("effort"), str):
            args.effort = saved["effort"]
        if not explicit["tier"] and isinstance(saved.get("tier"), str):
            args.tier = saved["tier"]
        if not explicit["fast"] and saved.get("fast") in ("on", "off"):
            args.fast = saved["fast"]
        if not explicit["mode"] and isinstance(saved.get("mode"), str):
            args.mode = saved["mode"]
        if not explicit["launch_backend"] and isinstance(saved.get("launch_backend"), str):
            args.launch_backend = saved["launch_backend"]
    if not explicit["command"] and not os.environ.get("KAOLA_ACP_COMMAND"):
        args.agent_command = manifest_launch_command(
            args, tier_agent_command(args) or args.manifest.get("acp_command") or ""
        ) or args.agent_command
        args.agent_command, args.agent_command_facts = resolve_agent_command(args.agent_command)
    selection = {
        "source": "caller" if any(explicit.values()) else "record",
        "model": args.model,
        "effort": args.effort,
        "tier": args.tier,
        "fast": args.fast,
        "mode": args.mode,
    }
    if resume_without_requested_tier(args):
        selection["tier_reason"] = "resume-without-tier"
    return selection


def _note_post_stop_result(started: dict[str, Any], old_id: Any,
                           stop: dict[str, Any] | None) -> None:
    """A start refusal after the exact-stop must not claim that nothing changed."""
    failed = started.get("result") == "refused" or isinstance(started.get("error"), dict)
    if not failed:
        return
    started["mutation_performed"] = True
    if started.get("mutation_status") in (None, "not_started"):
        started["mutation_status"] = "completed"
    started["drain_stopped"] = {
        "stopped": True,
        "previous_holder_instance_id": old_id,
        "residual_pids": (stop or {}).get("residual_pids") or [],
    }
    note = "The previous holder was exact-stopped before this result."
    detail = started.get("detail")
    if isinstance(detail, str) and detail:
        started["detail"] = f"{detail} {note}"
    else:
        started["detail"] = note


def command_drain_restart(args: argparse.Namespace, repo: str) -> dict[str, Any]:
    """Exact-stop an idle seat, then start --resume/--continue with its selection.

    Not a rebind and not a hot replace. Refusals that ``start`` can decide
    without spawning are run first, so a skewed install does not take the seat
    down. That same decision is handed to the start below, so the installed
    Skill roots are scanned once. A seat that is not idle is refused
    immediately with ``drain-not-idle`` and left running; the Agent owns retry
    timing. If a refusal still happens after the stop, the receipt says the
    stop happened. The recorded model/effort/tier/fast/mode are carried unless
    this argv names them; the recorded mode is already the effective one the
    previous start applied, so nothing re-derives a platform default here
    (Issue #181). A restart whose selection leaves mode unset reports the
    effective mode the new start applied, exactly as that start's own receipt
    does. Adoption is the new start's own dispatcher, read directly.
    """
    if not args.resume and not args.use_continue:
        receipt = base_receipt(args, repo)
        receipt.update({
            "result": "refused",
            "reason": "drain-restart-mode-required",
            "action": "drain-restart",
            "detail": (
                "pass --resume ID or --continue. A fresh start would be a new "
                "session, and a live holder is never hot-replaced."
            ),
            "mutation_performed": False,
            "mutation_status": "not_started",
        })
        return receipt
    directory = record_dir(args, repo)
    acp_paths.check_record_root(directory.parent.parent.parent)
    record = read_record(directory)
    if not record or (not pid_alive(record.get("holder_pid")) and record.get("state") != "stopped"):
        receipt = base_receipt(args, repo)
        receipt.update({
            "result": "refused",
            "reason": "no-session",
            "action": "drain-restart",
            "detail": "no live holder to drain",
            "mutation_performed": False,
            "mutation_status": "not_started",
        })
        return receipt
    selection = apply_recorded_selection(args, record)
    if selection is None:
        receipt = base_receipt(args, repo)
        receipt.update({
            "result": "refused",
            "reason": "drain-restart-selection-unknown",
            "action": "drain-restart",
            "detail": (
                "this seat recorded no model, effort, tier, or fast, and this "
                "command did not pass them. Nothing was stopped. Pass "
                "--model/--effort/--tier/--fast to name the restart, or restart "
                "a seat that stored its start selection."
            ),
            "mutation_performed": False,
            "mutation_status": "not_started",
        })
        return receipt
    # Issue #188: a recorded tier this manifest no longer declares (a retired
    # `upgrade`) is refused before the stop, never resolved to `default`.
    if not tier_declared(args.manifest, args.tier):
        refused = tier_refusal(args, repo)
        refused["start_selection"] = selection
        return refused
    refused, decision_facts = pre_spawn_refusal(args, repo)
    if refused is not None:
        refused["action"] = "drain-restart"
        refused["mutation_performed"] = False
        refused["mutation_status"] = "not_started"
        refused["start_selection"] = selection
        return refused
    # Issue #181: one idle read, no poll; only a live holder can answer it.
    if pid_alive(record.get("holder_pid")):
        state = op_or_holder_lost(args, repo, directory, "state", {}, 10.0)
        if not _seat_idle(state):
            receipt = base_receipt(args, repo)
            receipt.update({
                "result": "refused",
                "reason": "drain-not-idle",
                "action": "drain-restart",
                "detail": "the seat is not idle; nothing was stopped",
                "state": state.get("state"),
                "activity_hint": state.get("activity_hint"),
                "turn_active": state.get("turn_active"),
                "mutation_performed": False,
                "mutation_status": "not_started",
            })
            return receipt
    old = read_record(directory) or {}
    old_id = old.get("holder_instance_id")
    old_pid = old.get("holder_pid")
    old_dispatcher = old.get("dispatcher")
    stop: dict[str, Any] | None = None
    did_stop = False
    if pid_alive(old_pid):
        refused = preserve_refusal(args, repo, directory)
        if refused is not None:
            refused["action"] = "drain-restart"
            return refused
        stop = op_or_holder_lost(
            args, repo, directory, "stop",
            {"expected_holder_instance_id": old_id, "require_idle": True,
             **({"preserve_dispatched_workers": True} if preserving(args) else {})}, 30.0,
        )
        if stop.get("idle") is False or stop.get("stopped") is False:
            receipt = base_receipt(args, repo)
            receipt.update({
                "result": "refused",
                "reason": "drain-not-idle",
                "action": "drain-restart",
                "detail": (
                    "exact stop refused because the seat was not idle; the holder "
                    "was not replaced"
                ),
                "mutation_performed": False,
                "mutation_status": "not_started",
            })
            return receipt
        error = stop.get("error") if isinstance(stop.get("error"), dict) else None
        if error:
            receipt = base_receipt(args, repo)
            receipt.update({
                "result": "refused",
                "reason": "drain-stop-failed",
                "action": "drain-restart",
                "detail": error.get("message") or "exact stop failed; the new holder was not started",
                "mutation_performed": False,
                "mutation_status": "not_started",
            })
            return receipt
        did_stop = True
        wait_deadline = time.monotonic() + 10.0
        while pid_alive(old_pid) and time.monotonic() < wait_deadline:
            time.sleep(0.1)
        if pid_alive(old_pid) or (stop.get("residual_pids") or []):
            receipt = base_receipt(args, repo)
            receipt.update({
                "result": "refused",
                "reason": "drain-stop-failed",
                "action": "drain-restart",
                "detail": ("the old holder is not fully gone; the new holder was not "
                           "started. The exact stop was already sent: inspect `status` and "
                           "residual_pids and prove the old holder gone before any "
                           "drain-restart again."),
                "residual_pids": stop.get("residual_pids") or [],
                "mutation_performed": True,
                "mutation_status": "completed",
                "drain_stopped": {
                    "stopped": False,
                    "previous_holder_instance_id": old_id,
                    "residual_pids": stop.get("residual_pids") or [],
                },
            })
            return receipt
    started = command_start(args, repo, (None, decision_facts))
    started["action"] = "drain-restart"
    started["previous_holder_instance_id"] = old_id
    # Issue #181: echo the mode the new start actually applied, not a bare None.
    if selection.get("mode") is None:
        applied_mode = ((started.get("config_application") or {}).get("mode") or {})
        # Issue #363: a resumed session can keep a recorded permission that
        # differs from the requested one; its effective value is the echo.
        effective_mode = applied_mode.get("effective")
        effective_preset = effective_mode.get("preset") if isinstance(effective_mode, dict) else None
        for candidate in (effective_preset, applied_mode.get("value")):
            if isinstance(candidate, str):
                selection["mode"] = candidate
                break
    started["start_selection"] = selection
    if did_stop:
        _note_post_stop_result(started, old_id, stop)
    # Issue #181: adoption is a direct read of the new start's own dispatcher,
    # never a second scan over command_list. The restart runs from the Host
    # that should own the seat, so that is the binding the new start records.
    new_dispatcher = started.get("dispatcher")
    old_instance = old_dispatcher.get("holder_instance_id") if isinstance(old_dispatcher, dict) else None
    new_instance = new_dispatcher.get("holder_instance_id") if isinstance(new_dispatcher, dict) else None
    started["adoption"] = {
        "previous_holder_instance_id": old_id,
        "previous_dispatcher": old_dispatcher if isinstance(old_dispatcher, dict) else None,
        "dispatcher": new_dispatcher if isinstance(new_dispatcher, dict) else None,
        "adopted_on_restart": bool(new_instance) and old_instance != new_instance,
    }
    return started


# ---------------------------------------------------------------------------
# Issue #299 / #302 / #304 / #311 / #325: Delegator webhook wake. A Host holder
# spawns the ``deliver`` subcommand detached only when the Delegator must act;
# this CLI owns the config, validation, POST, retries, dedupe and receipts. No
# receipt ever carries the URL, the sender key, or an exception message (urllib
# errors can embed the URL); only the classified error code travels. An HTTP
# error stores a truncated redacted body and an allowlisted header set (#311).
# ``deliver`` is a new process per wake, so it accepts a payload from a holder
# that is still running the previous shape (#304). ``status`` is the holder-lost
# detector the cron inquiry runs; it does not schedule itself. A run of final
# failed deliveries is one fact (#325): one Host alert, then the heartbeat path
# once that run's window passes. This does not add a wake reason.
# ---------------------------------------------------------------------------

DELEGATOR_WEBHOOK_CONFIG_ENV = "KAOLA_DELEGATOR_WEBHOOK_CONFIG"
DELEGATOR_WEBHOOK_SCHEMA = "kaola-delegator-webhook/1"
DELEGATOR_WEBHOOK_RECEIPTS_SCHEMA = "kaola-delegator-webhook-receipts/1"
DELEGATOR_WEBHOOK_RECEIPTS_LIMIT = 32
# Issue #325. Final failed rows are kept apart from the 32-attempt ring, so the
# next 32 deliveries cannot erase a 101-minute outage. 256 is the cap.
DELEGATOR_WEBHOOK_FAILED_RECEIPTS_LIMIT = 256
DELEGATOR_WEBHOOK_REPEATED_FAILURE_SCHEMA = "kaola-delegator-webhook-repeated-failure/1"
# More than one final failed event. One event's retries are not a run.
DELEGATOR_WEBHOOK_REPEATED_FAILURE_MIN = 2
# Shorter than the 101-minute outage. When the span from the first final
# failure reaches this, the heartbeat path applies. The sender does not sleep
# for it and does not start a timer.
DELEGATOR_WEBHOOK_FAILURE_WINDOW_S = 15 * 60
# The cadence example in webhook-wake.md (120 minutes). The heartbeat's own
# bound. Not a second wake channel and not a tighter poll.
DELEGATOR_WEBHOOK_HEARTBEAT_BOUND_S = 120 * 60
# Network failures only. Config, payload, and spawn failures are not this run,
# and a skip neither joins it nor ends it.
DELEGATOR_WEBHOOK_RUN_ERRORS = frozenset({"http-status", "connection", "timeout"})
DELEGATOR_WEBHOOK_FALLBACKS = ("retry", "receipt-route", "host-notice", "heartbeat")
DELEGATOR_WEBHOOK_CLAIMS_SCHEMA = "kaola-delegator-webhook-claims/1"
# Bound of remembered (holder_instance_id, event_seq) pairs. A pair is claimed
# before the first network attempt and kept after success or final failure, so
# a retry of that same event does not POST again. Oldest pairs fall off only
# after this many later events. A death-recovery wake uses a new event_seq, so
# it is not one of those pairs.
DELEGATOR_WEBHOOK_CLAIMS_LIMIT = 256
# 12 s: one attempt, inside the required 10–15 s range. The old 3 s timeout
# was shorter than a cold listener accept, so the client timed out after the
# server had already taken the POST and then retried it. 12 s covers that
# accept and still fails a dead endpoint once, with no timeout retry.
DELEGATOR_WEBHOOK_TIMEOUT = 12.0
DELEGATOR_WEBHOOK_BACKOFF = (1.0, 2.0, 4.0)
DELEGATOR_WEBHOOK_MAX_ATTEMPTS = 1 + len(DELEGATOR_WEBHOOK_BACKOFF)
# Issue #311 supersedes the #302 rule that HTTP 400 was final. A 400 beside
# sibling 200s of the same shape has been transient. 401, 403 and 404 stay
# final on attempt 1, and so does every other 4xx that is not listed here.
DELEGATOR_WEBHOOK_RETRY_STATUS = frozenset({400, 408, 429})
# Issue #309: deliver and status refusal codes. stamp() reads this tuple.
DELEGATOR_WEBHOOK_ERROR_CODES = (
    "timeout",
    "connection",
    "http-status",
    "redirect-refused",
    "config-mode",
    "invalid-config",
    "invalid-payload",
    "not-enabled",
    "not-configured",
    "duplicate",
)
# Read cap, then the stored cap. Redaction runs on the read window before the
# stored cut, so a secret that begins inside the stored prefix is removed whole
# when it fits in the read window. The stored body is at most 512 characters.
DELEGATOR_WEBHOOK_RESPONSE_READ_CAP = 8192
DELEGATOR_WEBHOOK_RESPONSE_BODY_LIMIT = 512
DELEGATOR_WEBHOOK_RESPONSE_HEADER_LIMIT = 200
DELEGATOR_WEBHOOK_RESPONSE_HEADER_NAMES = (
    "content-type",
    "retry-after",
    "www-authenticate",
    "x-request-id",
    "x-correlation-id",
)
DELEGATOR_WEBHOOK_USER_AGENT = "kaola-delegator-wake/1"
# Issue #320. One stderr line, no exception text and no secret. The holder
# copies it into the event log. A death-recovery parent does not wait, so it
# sets KAOLA_DELEGATOR_WAKE_EVENT_LOG and the child appends the same line.
RECEIPT_WRITE_FAILED_LINE = (
    "delegator-webhook: receipt-write-failed. "
    "Self-route: the POST may have succeeded and this receipt was not stored. "
    "Run delegator-webhook status and test. If test delivers, continue the inquiry now. "
    "Do not treat a stale last_receipt as this wake."
)
PROJECT_UNRESOLVED_LINE = (
    "delegator-webhook: project-unresolved. "
    "Self-route: the project directory is gone, so no receipts file was written. "
    "Read the holder event log. Run delegator-webhook test in the project's current "
    "directory. If test delivers, continue the inquiry now. Do not start a second Host "
    "for the missing directory."
)
WAKE_DIAG_EVENT_ENV = "KAOLA_DELEGATOR_WAKE_EVENT_LOG"
WAKE_DIAG_TEXT_CAP = 1024
DELEGATOR_WEBHOOK_PAYLOAD_SCHEMA = "kaola-delegator-wake/1"
# Keys every shipped wake shape carried: the first #299 sender, v0.9.5/v0.9.6
# (which added state_detail), and v0.9.7 (which added reason).
DELEGATOR_WEBHOOK_PAYLOAD_CORE_KEYS = frozenset(
    {"schema", "project", "session", "holder_instance_id", "event_seq",
     "state", "ts"})
# Current holder shape (v0.9.7+). ``reason`` is optional on the two previous
# shapes; ``state_detail`` is optional only on the shape that predates it.
DELEGATOR_WEBHOOK_PAYLOAD_KEYS = frozenset(
    DELEGATOR_WEBHOOK_PAYLOAD_CORE_KEYS | {"state_detail", "reason"})
# Closed reason vocabulary. Keep in lockstep with DELEGATOR_WAKE_REASONS
# in kaola-acp-holder.py. ``holder_lost`` is sent by death recovery here;
# ``test`` is the CLI test payload.
DELEGATOR_WEBHOOK_REASONS = frozenset({
    "host_stopped_pending",
    "permission_required",
    "needs_decision",
    "question_waiting",
    "delivery_review",
    "turn_failed",
    "agent_exited",
    "boot_failure",
    "holder_lost",
    "exact_stop",
    "all-idle",
    "host_turn_done",
    "test",
})
# Issue #317. The Host's explicit wake. Same three tokens as
# HOST_INITIATED_WAKE_REASONS in kaola-acp-holder.py. Not a new vocabulary.
HOST_INITIATED_WAKE_REASONS = frozenset({
    "needs_decision",
    "question_waiting",
    "delivery_review",
})
DELEGATOR_WEBHOOK_DETAIL_RE = re.compile(r"[A-Za-z0-9_.:-]{1,64}")
DELEGATOR_WEBHOOK_PAYLOAD_STATES = frozenset(
    {"end_turn", "blocked", "error", "stopped", "test"})
DELEGATOR_WEBHOOK_HEADER_NAME = re.compile(r"^[!#$%&'*+.^_`|~0-9A-Za-z-]+$")
DELEGATOR_WEBHOOK_FORBIDDEN_HEADERS = frozenset(
    {"host", "content-type", "content-length", "connection", "transfer-encoding"})
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})


def _utc_stamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def delegator_webhook_config_path() -> Path:
    override = os.environ.get(DELEGATOR_WEBHOOK_CONFIG_ENV)
    if override:
        return Path(override)
    return Path.home() / ".config" / "kaola" / "delegator-webhook.json"


def delegator_webhook_receipts_path(project_root: str) -> Path:
    return Path(project_root) / ".kaola" / "delegator-webhook-receipts.json"


def _webhook_read_config(path: Path) -> tuple[dict[str, Any] | None, str | None, str | None]:
    """(config, error, config_mode). error is None, ``config-mode`` or
    ``invalid-config``; config_mode is the octal string or None."""
    try:
        stat_result = path.stat()
    except FileNotFoundError:
        return None, None, None
    except OSError:
        return None, "invalid-config", None
    config_mode = oct(stat_result.st_mode & 0o777)[2:].zfill(4)
    if stat_result.st_uid != os.getuid() or (stat_result.st_mode & 0o077):
        return None, "config-mode", config_mode
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None, "invalid-config", config_mode
    if (not isinstance(doc, dict) or doc.get("schema") != DELEGATOR_WEBHOOK_SCHEMA
            or not isinstance(doc.get("projects"), dict)):
        return None, "invalid-config", config_mode
    return doc, None, config_mode


@contextlib.contextmanager
def _webhook_config_lock(path: Path):
    """Exclusive flock on ``<path>.lock``. configure/remove hold it across the
    whole read -> ownership check -> modify -> write so concurrent configures
    of different projects cannot lose each other's entries."""
    import fcntl
    lock_path = path.with_name(path.name + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with open(lock_path, "a+b") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        yield lock_file


def _webhook_atomic_write(path: Path, doc: dict[str, Any]) -> None:
    """Atomic 0600 temp+fsync+replace. Callers hold ``_webhook_config_lock``."""
    data = (json.dumps(doc, ensure_ascii=False, sort_keys=True, indent=1) + "\n").encode("utf-8")
    temp_name = str(path.with_name(f"{path.name}.{os.getpid()}.{secrets.token_hex(4)}.tmp"))
    fd = os.open(temp_name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as temp:
            temp.write(data)
            temp.flush()
            os.fsync(temp.fileno())
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def _webhook_url_error(url: Any) -> str | None:
    """None when the URL is deliverable, else a short validation detail."""
    if not isinstance(url, str) or not url:
        return "url is required"
    if any(ch in url for ch in ("\r", "\n", " ")):
        return "url must not contain CR, LF or space"
    try:
        parts = urllib.parse.urlsplit(url)
    except ValueError:
        return "url does not parse"
    if parts.scheme == "https":
        pass
    elif parts.scheme == "http" and (parts.hostname or "") in LOOPBACK_HOSTS:
        pass
    else:
        return "url must be https (http only for a loopback test endpoint)"
    return None


def _webhook_sender_key_error(sender_key: Any) -> str | None:
    if not isinstance(sender_key, str) or not sender_key:
        return "sender_key is required for a header attachment"
    if any(ch in sender_key for ch in ("\r", "\n", "\x00")):
        return "sender_key must not contain CR, LF or NUL"
    return None


def _webhook_attachment_error(attachment: Any, sender_key: Any) -> str | None:
    if not isinstance(attachment, dict):
        return "sender_key_attachment is required"
    style = attachment.get("style")
    if style == "header":
        name = attachment.get("name")
        if not isinstance(name, str) or not DELEGATOR_WEBHOOK_HEADER_NAME.match(name):
            return "header name is not an RFC7230 token"
        if name.lower() in DELEGATOR_WEBHOOK_FORBIDDEN_HEADERS:
            return f"header {name} is reserved for the transport"
        prefix = attachment.get("prefix", "")
        if not isinstance(prefix, str) or any(ord(ch) < 0x20 or ord(ch) > 0x7e for ch in prefix):
            return "header prefix must be printable ASCII without CR/LF"
        return _webhook_sender_key_error(sender_key)
    if style == "url":
        if sender_key not in (None, ""):
            return "sender_key must be absent when the key is already in the url"
        extra = set(attachment) - {"style"}
        if extra:
            return f"url attachment takes no {sorted(extra)}"
        return None
    return 'sender_key_attachment.style must be "header" or "url"'


def _webhook_entry_error(entry: Any) -> str | None:
    if not isinstance(entry, dict):
        return "entry is not an object"
    error = _webhook_url_error(entry.get("url"))
    if error:
        return error
    error = _webhook_attachment_error(
        entry.get("sender_key_attachment"), entry.get("sender_key"))
    if error:
        return error
    if not isinstance(entry.get("enabled"), bool):
        return "enabled must be boolean"
    if not isinstance(entry.get("owner_agent"), str) or not entry["owner_agent"]:
        return "owner_agent is required"
    return None


class _WebhookRedirectRefused(Exception):
    def __init__(self, status: int):
        super().__init__()
        self.status = status


class _WebhookNoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise _WebhookRedirectRefused(code)


_WEBHOOK_OPENER = urllib.request.build_opener(_WebhookNoRedirect)


class _WebhookHttpResult(NamedTuple):
    http_status: int | None
    error: str | None
    response_body: str | None
    response_body_truncated: bool
    response_headers: dict[str, str] | None


def _webhook_secret_values(url: str, sender_key: str | None) -> tuple[str, ...]:
    values = [url]
    if isinstance(sender_key, str) and sender_key:
        values.append(sender_key)
    return tuple(values)


def _webhook_redact(text: str, secrets: tuple[str, ...]) -> str:
    """Replace the configured URL and sender key, longest first.

    Also replaces each secret's percent-encoded form. The replacement is the
    fixed token ``[redacted]``. Exception text is never passed in.
    """
    ordered = sorted({item for item in secrets if item}, key=len, reverse=True)
    for secret in ordered:
        text = text.replace(secret, "[redacted]")
        quoted = urllib.parse.quote(secret, safe="")
        if quoted and quoted != secret:
            text = text.replace(quoted, "[redacted]")
    return text


def _webhook_response_view(raw: bytes, headers: Any, secrets: tuple[str, ...],
                           hit_read_cap: bool) -> tuple[str | None, bool, dict[str, str] | None]:
    """Truncated redacted body plus the allowlisted response headers."""
    text = _webhook_redact(raw.decode("utf-8", errors="replace"), secrets)
    truncated = hit_read_cap or len(text) > DELEGATOR_WEBHOOK_RESPONSE_BODY_LIMIT
    if len(text) > DELEGATOR_WEBHOOK_RESPONSE_BODY_LIMIT:
        text = text[:DELEGATOR_WEBHOOK_RESPONSE_BODY_LIMIT]
    body = text if text else None
    picked: dict[str, str] = {}
    if headers is not None:
        for name in DELEGATOR_WEBHOOK_RESPONSE_HEADER_NAMES:
            try:
                value = headers.get(name)
            except Exception:
                value = None
            if value is None:
                continue
            redacted = _webhook_redact(str(value), secrets)
            if len(redacted) > DELEGATOR_WEBHOOK_RESPONSE_HEADER_LIMIT:
                redacted = redacted[:DELEGATOR_WEBHOOK_RESPONSE_HEADER_LIMIT]
            picked[name] = redacted
    return body, truncated, picked or None


def _webhook_http_error_view(exc: urllib.error.HTTPError,
                             secrets: tuple[str, ...]) -> tuple[str | None, bool, dict[str, str] | None]:
    raw = b""
    hit_read_cap = False
    try:
        chunk = exc.read(DELEGATOR_WEBHOOK_RESPONSE_READ_CAP + 1)
        if isinstance(chunk, str):
            chunk = chunk.encode("utf-8", errors="replace")
        raw = chunk or b""
        hit_read_cap = len(raw) > DELEGATOR_WEBHOOK_RESPONSE_READ_CAP
        if hit_read_cap:
            raw = raw[:DELEGATOR_WEBHOOK_RESPONSE_READ_CAP]
    except Exception:
        raw = b""
        hit_read_cap = False
    finally:
        try:
            exc.close()
        except Exception:
            pass
    return _webhook_response_view(raw, getattr(exc, "headers", None), secrets, hit_read_cap)


def _webhook_post(url: str, attachment: dict[str, Any], sender_key: str | None,
                  body: bytes) -> _WebhookHttpResult:
    """One POST attempt. ``error`` is None on 2xx.

    An HTTP error response contributes a truncated redacted body and the
    allowlisted headers. A timeout, a connection error, a redirect refusal
    and a 2xx do not: success bodies are not stored, and a redirect is refused
    before its body is a delivery.
    """
    secrets = _webhook_secret_values(url, sender_key)
    headers = {"Content-Type": "application/json", "User-Agent": DELEGATOR_WEBHOOK_USER_AGENT}
    if attachment.get("style") == "header":
        headers[attachment["name"]] = attachment.get("prefix", "") + (sender_key or "")
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with _WEBHOOK_OPENER.open(request, timeout=DELEGATOR_WEBHOOK_TIMEOUT) as response:
            status = response.getcode() or 0
    except _WebhookRedirectRefused as exc:
        return _WebhookHttpResult(exc.status, "redirect-refused", None, False, None)
    except urllib.error.HTTPError as exc:
        response_body, truncated, response_headers = _webhook_http_error_view(exc, secrets)
        return _WebhookHttpResult(exc.code, "http-status", response_body, truncated, response_headers)
    except urllib.error.URLError as exc:
        reason = exc.reason
        if isinstance(reason, (socket.timeout, TimeoutError)):
            return _WebhookHttpResult(None, "timeout", None, False, None)
        return _WebhookHttpResult(None, "connection", None, False, None)
    except (socket.timeout, TimeoutError):
        return _WebhookHttpResult(None, "timeout", None, False, None)
    except OSError:
        return _WebhookHttpResult(None, "connection", None, False, None)
    if 200 <= status < 300:
        return _WebhookHttpResult(status, None, None, False, None)
    return _WebhookHttpResult(status, "http-status", None, False, None)


def _webhook_retryable(http_status: int | None, error: str | None) -> bool:
    """Retry connection errors, HTTP 400, 408, 429 and 5xx. Never a client timeout.

    A timeout means this attempt may already have been accepted. Retrying it
    is how the same event was delivered twice. 400, 408 and 429 are server
    responses that are retried with the same backoff. 401, 403 and 404, and
    every other 4xx, are final on attempt 1 (#311; 400 is no longer final).
    """
    if error == "connection":
        return True
    if error == "timeout":
        return False
    if error == "http-status" and isinstance(http_status, int):
        return http_status >= 500 or http_status in DELEGATOR_WEBHOOK_RETRY_STATUS
    return False


def _webhook_attempt_receipt(payload: dict[str, Any], attempt: int, result: str,
                             http_status: int | None, error: str | None,
                             skip_reason: str | None, elapsed_ms: int,
                             final: bool, response_body: str | None = None,
                             response_body_truncated: bool = False,
                             response_headers: dict[str, str] | None = None) -> dict[str, Any]:
    """One attempt row.

    ``delivered`` and ``failed`` always include ``reason``: the payload's
    string wake reason, or null when the payload had none (an accepted
    pre-v0.9.7 shape, or a refused payload with no string reason). The sender
    does not invent a wake token. ``skipped`` includes ``skip_reason``
    (``not-configured`` or ``duplicate``) and no ``reason`` key.
    ``skip_reason`` is ignored unless ``result`` is ``skipped``.
    """
    receipt: dict[str, Any] = {
        "ts": _utc_stamp(),
        "state": payload.get("state"),
        "state_detail": payload.get("state_detail"),
        "session": payload.get("session"),
        "holder_instance_id": payload.get("holder_instance_id"),
        "event_seq": payload.get("event_seq"),
        "result": result,
        "attempt": attempt,
        "max_attempts": DELEGATOR_WEBHOOK_MAX_ATTEMPTS,
        "http_status": http_status,
        "error": error,
        "response_body": response_body,
        "response_body_truncated": bool(response_body_truncated),
        "response_headers": response_headers,
        "elapsed_ms": elapsed_ms,
        "final": final,
    }
    if result == "skipped":
        receipt["skip_reason"] = skip_reason
    else:
        raw_reason = payload.get("reason")
        receipt["reason"] = raw_reason if isinstance(raw_reason, str) else None
    if result == "failed":
        # #318: final rows split by class. A non-final row is still retrying
        # and is not stamped, so it does not carry the lost-wake route.
        receipt = _stamp_webhook_failure(receipt, error, http_status, final)
    return receipt


def _stamp_webhook_failure(receipt: dict[str, Any], error: str | None,
                           http_status: int | None, final: bool) -> dict[str, Any]:
    """Attach the #318 class route, or leave a retrying row unstamped.

    ``None`` from the routes module means the error-code table, including the
    lost-wake text on a final connection, timeout, or other final HTTP status.
    ``""`` means do not stamp. A non-empty string is that route.
    """
    module = _load_recovery_routes()
    chosen = None
    if module is not None:
        choose = getattr(module, "webhook_delivery_route", None)
        if choose is not None:
            chosen = choose(error, http_status, final)
    if chosen is None:
        return _stamp_recovery(receipt)
    if chosen:
        receipt["route"] = chosen
    return receipt


def _webhook_under_lock(project_root: str, fn: Any) -> Any:
    """Run ``fn`` while holding the receipts flock. Not re-entrant."""
    import fcntl
    kaola_dir = Path(project_root) / ".kaola"
    kaola_dir.mkdir(exist_ok=True)
    lock_path = kaola_dir / "delegator-webhook-receipts.lock"
    with open(lock_path, "a+b") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        return fn()


def _webhook_atomic_json(path: Path, doc: dict[str, Any]) -> None:
    """Atomic 0600 replace. Caller holds the receipts flock."""
    data = json.dumps(doc, ensure_ascii=False, sort_keys=True, indent=1).encode("utf-8") + b"\n"
    temp_name = str(path.with_name(f"{path.name}.{os.getpid()}.{secrets.token_hex(4)}.tmp"))
    fd = os.open(temp_name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as temp:
            temp.write(data)
            temp.flush()
            os.fsync(temp.fileno())
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def _webhook_load_receipt_doc(project_root: str) -> dict[str, Any]:
    """The receipts document, or ``{}`` when it is missing or not this schema.

    A read does not rewrite the file. Callers that append hold the flock.
    """
    path = delegator_webhook_receipts_path(project_root)
    try:
        existing = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if (not isinstance(existing, dict)
            or existing.get("schema") != DELEGATOR_WEBHOOK_RECEIPTS_SCHEMA):
        return {}
    return existing


def _webhook_dict_list(doc: dict[str, Any], key: str) -> list[dict[str, Any]]:
    raw = doc.get(key)
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def _webhook_parse_ts(ts: Any) -> int | None:
    if not isinstance(ts, str) or not ts:
        return None
    try:
        return calendar.timegm(time.strptime(ts, "%Y-%m-%dT%H:%M:%SZ"))
    except (ValueError, OverflowError):
        return None


def _webhook_keeps_failed(receipt: dict[str, Any]) -> bool:
    """A final network failure. One row per event, not each retry."""
    return (receipt.get("result") == "failed"
            and receipt.get("final") is True
            and receipt.get("error") in DELEGATOR_WEBHOOK_RUN_ERRORS)


def _webhook_event_key(receipt: dict[str, Any]) -> tuple[Any, Any]:
    return (receipt.get("holder_instance_id"), receipt.get("event_seq"))


def _webhook_heartbeat(applies: bool) -> dict[str, Any]:
    return {
        "path": "heartbeat",
        "bound_seconds": DELEGATOR_WEBHOOK_HEARTBEAT_BOUND_S,
        "applies": applies,
    }


def _webhook_run_open(current: Any) -> bool:
    if not isinstance(current, dict):
        return False
    count = current.get("count")
    return (current.get("schema") == DELEGATOR_WEBHOOK_REPEATED_FAILURE_SCHEMA
            and not current.get("ended_at")
            and isinstance(count, int)
            and not isinstance(count, bool)
            and count >= 1)


def _webhook_copy_run(current: dict[str, Any]) -> dict[str, Any]:
    copied = dict(current)
    for key in ("heartbeat", "host_notice", "last_event"):
        nested = copied.get(key)
        if isinstance(nested, dict):
            copied[key] = dict(nested)
    return copied


def _webhook_open_run(receipt: dict[str, Any]) -> dict[str, Any]:
    ts = receipt.get("ts") if isinstance(receipt.get("ts"), str) else _utc_stamp()
    return {
        "schema": DELEGATOR_WEBHOOK_REPEATED_FAILURE_SCHEMA,
        "active": False,
        "window_start": ts,
        "window_end": ts,
        "count": 1,
        "min_count": DELEGATOR_WEBHOOK_REPEATED_FAILURE_MIN,
        "window_seconds": DELEGATOR_WEBHOOK_FAILURE_WINDOW_S,
        "window_passed": False,
        "last_http_status": receipt.get("http_status"),
        "last_error": receipt.get("error"),
        "last_event": {
            "holder_instance_id": receipt.get("holder_instance_id"),
            "event_seq": receipt.get("event_seq"),
        },
        "host_notice": None,
        "user_notice": None,
        "heartbeat": _webhook_heartbeat(False),
        "fallbacks": list(DELEGATOR_WEBHOOK_FALLBACKS),
        "ended_at": None,
    }


def _webhook_mark_window(cond: dict[str, Any]) -> None:
    """The window has passed when the span reaches the failure bound.

    A shorter span leaves ``heartbeat.applies`` false. The sender does not
    wait out the window in this process.
    """
    start = _webhook_parse_ts(cond.get("window_start"))
    end = _webhook_parse_ts(cond.get("window_end"))
    if start is None or end is None or (end - start) < DELEGATOR_WEBHOOK_FAILURE_WINDOW_S:
        return
    cond["window_passed"] = True
    heartbeat = cond.get("heartbeat")
    if not isinstance(heartbeat, dict):
        cond["heartbeat"] = _webhook_heartbeat(True)
        return
    heartbeat["path"] = "heartbeat"
    heartbeat["bound_seconds"] = DELEGATOR_WEBHOOK_HEARTBEAT_BOUND_S
    heartbeat["applies"] = True


def _webhook_repeated_failure_line(cond: dict[str, Any]) -> str:
    """One stderr line. No URL, key, body, or exception text."""
    heartbeat = cond.get("heartbeat") if isinstance(cond.get("heartbeat"), dict) else {}
    applies = "true" if heartbeat.get("applies") is True else "false"
    return (
        "delegator-webhook: repeated-failure "
        f"window={cond.get('window_start')}..{cond.get('window_end')} "
        f"count={cond.get('count')} host-notice=once "
        f"heartbeat-bound={DELEGATOR_WEBHOOK_HEARTBEAT_BOUND_S}s "
        f"heartbeat-applies={applies}"
    )


def _webhook_arm_host_notice(cond: dict[str, Any]) -> str | None:
    """One Host alert per open run. Later events update the count only.

    The line is the alert the holder already copies from child stderr. The
    stored object is what ``status`` shows the heartbeat. Empty means this
    event is not the first notice.
    """
    count = cond.get("count")
    if (not isinstance(count, int) or isinstance(count, bool)
            or count < DELEGATOR_WEBHOOK_REPEATED_FAILURE_MIN):
        return None
    cond["active"] = True
    cond["user_notice"] = "once"
    notice = cond.get("host_notice")
    if isinstance(notice, dict):
        notice["window_end"] = cond.get("window_end")
        notice["count"] = count
        return None
    cond["host_notice"] = {
        "kind": "alert",
        "once": True,
        "level": "warn",
        "summary": "delegator webhook repeated failure",
        "window_start": cond.get("window_start"),
        "window_end": cond.get("window_end"),
        "count": count,
        "emitted_at": cond.get("window_end"),
    }
    return _webhook_repeated_failure_line(cond)


def _webhook_advance_repeated_failure(
    current: Any, previous: Any, receipt: dict[str, Any],
) -> tuple[Any, Any, str | None]:
    """Fold one attempt row into the run. Returns ``(run, previous, notice)``.

    A non-final row changes nothing. A delivered row ends the open run and
    does not emit a notice. A final network failure extends the open run, or
    starts one. The notice line is returned only on the event that first
    reaches ``min_count``.
    """
    if receipt.get("final") is not True:
        return current, previous, None
    if receipt.get("result") == "delivered":
        if _webhook_run_open(current):
            current = _webhook_copy_run(current)
            current["active"] = False
            ts = receipt.get("ts")
            current["ended_at"] = ts if isinstance(ts, str) else _utc_stamp()
            heartbeat = current.get("heartbeat")
            if isinstance(heartbeat, dict):
                heartbeat["applies"] = False
        return current, previous, None
    if not _webhook_keeps_failed(receipt):
        return current, previous, None
    key = _webhook_event_key(receipt)
    if _webhook_run_open(current):
        last = current.get("last_event")
        if (isinstance(last, dict)
                and (last.get("holder_instance_id"), last.get("event_seq")) == key):
            return current, previous, None
        current = _webhook_copy_run(current)
        ts = receipt.get("ts") if isinstance(receipt.get("ts"), str) else _utc_stamp()
        count = current.get("count")
        current["count"] = (count if isinstance(count, int) and not isinstance(count, bool) else 0) + 1
        current["window_end"] = ts
        current["last_http_status"] = receipt.get("http_status")
        current["last_error"] = receipt.get("error")
        current["last_event"] = {
            "holder_instance_id": receipt.get("holder_instance_id"),
            "event_seq": receipt.get("event_seq"),
        }
        _webhook_mark_window(current)
        return current, previous, _webhook_arm_host_notice(current)
    if isinstance(current, dict) and isinstance(current.get("host_notice"), dict):
        previous = current
    return _webhook_open_run(receipt), previous, None


def _webhook_remember_failed(failed: list[dict[str, Any]],
                             receipts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep each event's final failure apart from the attempt ring."""
    kept = list(failed)
    for item in receipts:
        if not _webhook_keeps_failed(item):
            continue
        key = _webhook_event_key(item)
        kept = [old for old in kept if _webhook_event_key(old) != key]
        kept.append(item)
    return kept[-DELEGATOR_WEBHOOK_FAILED_RECEIPTS_LIMIT:]


def _webhook_append_receipts_unlocked(project_root: str,
                                     receipts: list[dict[str, Any]]) -> str | None:
    """Write the attempt ring, the failed archive, and the run. Return the notice.

    The notice is empty when this batch did not open the Host alert. The
    caller prints it after the flock drops, and only when the write landed.
    """
    path = delegator_webhook_receipts_path(project_root)
    doc = _webhook_load_receipt_doc(project_root)
    old = _webhook_dict_list(doc, "receipts")
    failed = _webhook_remember_failed(_webhook_dict_list(doc, "failed_receipts"), receipts)
    run = doc.get("repeated_failure")
    previous = doc.get("previous_repeated_failure")
    if not isinstance(previous, dict):
        previous = None
    notice: str | None = None
    for item in receipts:
        run, previous, line = _webhook_advance_repeated_failure(run, previous, item)
        if line:
            notice = line
    merged = (old + receipts)[-DELEGATOR_WEBHOOK_RECEIPTS_LIMIT:]
    out: dict[str, Any] = {
        "schema": DELEGATOR_WEBHOOK_RECEIPTS_SCHEMA,
        "limit": DELEGATOR_WEBHOOK_RECEIPTS_LIMIT,
        "failed_limit": DELEGATOR_WEBHOOK_FAILED_RECEIPTS_LIMIT,
        "receipts": merged,
        "failed_receipts": failed,
    }
    if isinstance(run, dict):
        out["repeated_failure"] = run
    if isinstance(previous, dict):
        out["previous_repeated_failure"] = previous
    _webhook_atomic_json(path, out)
    return notice


def _webhook_diag(line: str) -> None:
    """One bounded diagnostic. Stderr always; the event log when the parent set it.

    The line is a fixed sentence. It carries no exception text, URL, or key.
    """
    text = " ".join(line.split())
    if len(text) > WAKE_DIAG_TEXT_CAP:
        text = text[:WAKE_DIAG_TEXT_CAP]
    try:
        print(text, file=sys.stderr, flush=True)
    except Exception:
        pass
    raw = os.environ.get(WAKE_DIAG_EVENT_ENV)
    if not isinstance(raw, str) or not raw:
        return
    marker = "Self-route:"
    entry: dict[str, Any] = {
        "kind": "delegator_wake_child_stderr",
        "text": text,
        "ts": round(time.time(), 3),
    }
    if marker in text:
        entry["self_route"] = text.split(marker, 1)[1].strip()
    blob = (json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    try:
        fd = os.open(raw, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
    except OSError:
        return
    try:
        os.write(fd, blob)
    except OSError:
        pass
    finally:
        os.close(fd)


def _webhook_append_receipts(project_root: str, receipts: list[dict[str, Any]],
                             announce: bool = True) -> bool:
    """Append to the bounded receipts file. A write failure prints one stderr line.

    Deliver must not crash the detached child over bookkeeping. False means the
    row was not stored. The line is the self-route for that case (#320).
    ``announce`` is false when the caller is the holder recording a spawn
    failure: the POST never started, so the receipt-write sentence would be
    the wrong instruction. That caller puts the spawn sentence on its event.
    """
    notice: str | None = None

    def write() -> None:
        nonlocal notice
        notice = _webhook_append_receipts_unlocked(project_root, receipts)

    try:
        _webhook_under_lock(project_root, write)
    except Exception:
        if announce:
            _webhook_diag(RECEIPT_WRITE_FAILED_LINE)
        return False
    # The row is stored. The Host alert is one line, once per run (#325).
    # A write failure took the receipt-write path above and does not also
    # claim the alert.
    if announce and notice:
        _webhook_diag(notice)
    return True


def _webhook_claims_path(project_root: str) -> Path:
    return Path(project_root) / ".kaola" / "delegator-webhook-claims.json"


def _webhook_claim_event(project_root: str, holder_instance_id: str, event_seq: int) -> bool:
    """True when this call owns ``holder_instance_id`` + ``event_seq``.

    False when that pair was already claimed. A claim-file failure returns
    True so the event is still delivered once. Caller holds the receipts flock.
    The claim stays after success and after final network failure. Config and
    invalid-payload skips do not call this, so they do not consume the event.
    """
    path = _webhook_claims_path(project_root)
    try:
        claims: list[dict[str, Any]] = []
        if path.is_file():
            doc = json.loads(path.read_text(encoding="utf-8"))
            if (isinstance(doc, dict)
                    and doc.get("schema") == DELEGATOR_WEBHOOK_CLAIMS_SCHEMA
                    and isinstance(doc.get("claims"), list)):
                claims = [item for item in doc["claims"] if isinstance(item, dict)]
        for item in claims:
            if (item.get("holder_instance_id") == holder_instance_id
                    and item.get("event_seq") == event_seq):
                return False
        claims.append({"holder_instance_id": holder_instance_id, "event_seq": event_seq})
        claims = claims[-DELEGATOR_WEBHOOK_CLAIMS_LIMIT:]
        _webhook_atomic_json(path, {"schema": DELEGATOR_WEBHOOK_CLAIMS_SCHEMA, "claims": claims})
        return True
    except Exception:
        return True


def _webhook_read_receipts(project_root: str) -> list[dict[str, Any]]:
    return _webhook_dict_list(_webhook_load_receipt_doc(project_root), "receipts")


def _webhook_repeated_view(value: Any) -> dict[str, Any] | None:
    if (isinstance(value, dict)
            and value.get("schema") == DELEGATOR_WEBHOOK_REPEATED_FAILURE_SCHEMA):
        return value
    return None


def _webhook_state_detail_ok(detail: Any) -> bool:
    return detail is None or (
        isinstance(detail, str)
        and DELEGATOR_WEBHOOK_DETAIL_RE.fullmatch(detail) is not None)


def _webhook_payload_ok(payload: Any) -> bool:
    """True for the current wake shape or a previous holder's shape.

    A running holder keeps the payload builder it was started with, and the
    next wake spawns this CLI as a new process. Refusing the previous shape
    drops that wake (#304, v0.9.6 holder against a v0.9.7 deliver).

    Accepted key sets, exact (no extra keys):

    - v0.9.7+: core + ``state_detail`` + ``reason``. ``reason`` is in the
      closed vocabulary. ``state_detail`` is null or a token.
    - v0.9.5 / v0.9.6: core + ``state_detail``, no ``reason``. ``reason`` is
      optional and defaults to absent. ``state_detail`` is null or a token.
    - First #299 sender, before ``state_detail`` (``843902e2``): core only.
      ``state_detail`` is optional only for that shape.

    Core keys are ``schema``, ``project``, ``session``, ``holder_instance_id``,
    ``event_seq``, ``state`` and ``ts``. A ``reason`` key without
    ``state_detail`` is not a shipped shape. A wrong schema, a missing core
    key, an extra key, or a present ``reason`` outside the vocabulary is
    refused. The POST body stays the payload as received.
    """
    if not isinstance(payload, dict):
        return False
    keys = set(payload)
    if not DELEGATOR_WEBHOOK_PAYLOAD_CORE_KEYS <= keys:
        return False
    if keys - DELEGATOR_WEBHOOK_PAYLOAD_KEYS:
        return False
    has_reason = "reason" in keys
    has_detail = "state_detail" in keys
    if has_reason and not has_detail:
        return False
    event_seq = payload.get("event_seq")
    if payload.get("schema") != DELEGATOR_WEBHOOK_PAYLOAD_SCHEMA:
        return False
    if payload.get("state") not in DELEGATOR_WEBHOOK_PAYLOAD_STATES:
        return False
    if not isinstance(event_seq, int) or isinstance(event_seq, bool):
        return False
    if has_reason:
        reason = payload.get("reason")
        if not isinstance(reason, str) or reason not in DELEGATOR_WEBHOOK_REASONS:
            return False
    if has_detail and not _webhook_state_detail_ok(payload.get("state_detail")):
        return False
    return True


def _webhook_deliver(project_root: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    """The whole delivery policy for one payload: config lookup, the skipped /
    invalid-config short receipts, and the attempt loop. Writes the receipts
    file best-effort and returns the attempt receipts of this call."""
    config_path = delegator_webhook_config_path()
    doc, config_error, _mode = _webhook_read_config(config_path)
    started = time.monotonic()

    def one(result: str, error: str | None, skip_reason: str | None) -> list[dict[str, Any]]:
        receipt = _webhook_attempt_receipt(
            payload, 0, result, None, error, skip_reason,
            int(round((time.monotonic() - started) * 1000)), True)
        _webhook_append_receipts(project_root, [receipt])
        return [receipt]

    if config_error is not None:
        return one("failed", config_error, None)
    entry = (doc or {}).get("projects", {}).get(project_root)
    if not isinstance(entry, dict) or entry.get("enabled") is not True:
        return one("skipped", None, "not-configured")
    if _webhook_entry_error(entry) is not None:
        return one("failed", "invalid-config", None)

    # Claim before any network attempt. A duplicate of this holder event is a
    # skipped receipt and no POST. Retries of a retryable error stay inside
    # this call, which already owns the claim. Not-configured and invalid
    # config returned above and did not claim.
    holder_instance_id = payload.get("holder_instance_id")
    event_seq = payload.get("event_seq")
    try:
        owned = _webhook_under_lock(
            project_root,
            lambda: _webhook_claim_event(project_root, holder_instance_id, event_seq))
    except Exception:
        owned = True
    if not owned:
        receipt = _webhook_attempt_receipt(
            payload, 0, "skipped", None, None, "duplicate",
            int(round((time.monotonic() - started) * 1000)), True)
        _webhook_append_receipts(project_root, [receipt])
        return [receipt]

    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    receipts: list[dict[str, Any]] = []
    for attempt in range(1, DELEGATOR_WEBHOOK_MAX_ATTEMPTS + 1):
        attempt_started = time.monotonic()
        posted = _webhook_post(
            entry["url"], entry["sender_key_attachment"], entry.get("sender_key"), body)
        result = "delivered" if posted.error is None else "failed"
        final = posted.error is None or not _webhook_retryable(posted.http_status, posted.error) \
            or attempt == DELEGATOR_WEBHOOK_MAX_ATTEMPTS
        # Each attempt's receipt lands before its backoff sleep, so a slow or
        # dead endpoint leaves evidence immediately and a killed child still
        # records every attempt it made. skip_reason stays None: this row is
        # delivered or failed, so the receipt copies the payload wake reason.
        receipts.append(_webhook_attempt_receipt(
            payload, attempt, result, posted.http_status, posted.error, None,
            int(round((time.monotonic() - attempt_started) * 1000)), final,
            posted.response_body, posted.response_body_truncated, posted.response_headers))
        _webhook_append_receipts(project_root, receipts[-1:])
        if final:
            break
        time.sleep(DELEGATOR_WEBHOOK_BACKOFF[attempt - 1])
    return receipts


def _webhook_fingerprint(url: str, sender_key: str | None) -> str:
    return hashlib.sha256((url + "\n" + (sender_key or "")).encode("utf-8")).hexdigest()[:12]


def _webhook_same_project(record: dict[str, Any], project_root: str) -> bool:
    repo = record.get("repo")
    if not isinstance(repo, str) or not repo:
        return False
    try:
        return os.path.realpath(repo) == project_root
    except OSError:
        return False


def _webhook_death_eligible(project_root: str, record: dict[str, Any]) -> bool:
    """Host holder death for ``delegator-webhook status`` (#311, #319).

    Host role, not ``stopped``, this project, and the holder pid dead.
    A live ``agent_pid`` or ``agent_pgid`` still wakes. That liveness only
    blocks ``command_start`` from replacing the record. A live holder pid,
    including one reused by another process, is not this scan: ``status``
    does not probe argv, so that case stays with the next ``start`` or
    dead-holder ``stop``.
    """
    holder_instance_id = record.get("holder_instance_id")
    if (not _webhook_same_project(record, project_root)
            or record.get("session_role") != "host"
            or record.get("state") == "stopped"
            or not isinstance(holder_instance_id, str)
            or not holder_instance_id):
        return False
    return not pid_alive(record.get("holder_pid"))


def _webhook_scan_holder_lost(project_root: str) -> dict[str, Any]:
    """One pass over record files. Does not schedule a later pass.

    The Delegator cron inquiry is what calls ``status``. This function only
    runs when that command runs, and only for an enabled project entry.
    """
    leg = "delegator-webhook status"
    try:
        paths = acp_paths.record_paths("*/*/*/record.json")
    except acp_paths.RecordRootMismatch:
        # Issue #320: ``reason`` lets stamp attach the record-root-mismatch route.
        return {"scan": "incomplete", "leg": leg,
                "reason": "record-root-mismatch", "wakes": []}
    wakes: list[dict[str, Any]] = []
    # Issue #359: (platform, session) pairs with a record.json anywhere. A
    # registry row missing from this map is a record the wipe took.
    present: dict[tuple[str, str], list[Path]] = {}
    for path in paths:
        directory = path.parent
        present.setdefault((path.parent.parent.parent.name,
                            path.parent.parent.name), []).append(directory)
        try:
            record = read_record(directory)
        except OSError:
            continue
        if not isinstance(record, dict) or not _webhook_death_eligible(project_root, record):
            continue
        wake = recover_host_death_wake(directory, record)
        wakes.append({
            "session": record.get("session"),
            "holder_instance_id": record.get("holder_instance_id"),
            "delegator_death_wake": wake,
        })
    result: dict[str, Any] = {"scan": "complete", "leg": leg, "wakes": wakes}
    # Issue #359: the registry cross-check - rows whose records are gone get
    # their one record-lost wake; stale rows are reconciled.
    result["record_lost"] = _record_loss_scan(project_root, present)
    return result


def _webhook_attach_holder_lost(project_root: str, receipt: dict[str, Any]) -> None:
    """Scan only an enabled, valid entry. A skipped scan writes no death event."""
    if receipt.get("error"):
        receipt["holder_lost"] = {
            "scan": "skipped", "leg": "delegator-webhook status",
            "reason": receipt["error"], "wakes": [],
        }
        return
    if receipt.get("enabled") is not True:
        receipt["holder_lost"] = {
            "scan": "skipped", "leg": "delegator-webhook status",
            "reason": "not-enabled", "wakes": [],
        }
        return
    receipt["holder_lost"] = _webhook_scan_holder_lost(project_root)


def _webhook_status_receipt(project_root: str) -> dict[str, Any]:
    config_path = delegator_webhook_config_path()
    doc, config_error, config_mode = _webhook_read_config(config_path)
    entry = (doc or {}).get("projects", {}).get(project_root)
    attachment = entry.get("sender_key_attachment") if isinstance(entry, dict) else None
    attachment_view = None
    if isinstance(attachment, dict):
        attachment_view = {"style": attachment.get("style")}
        if attachment.get("style") == "header":
            attachment_view["name"] = attachment.get("name")
            attachment_view["prefix"] = attachment.get("prefix", "")
            attachment_view["prefix_set"] = bool(attachment.get("prefix"))
    store = _webhook_load_receipt_doc(project_root)
    receipts = _webhook_dict_list(store, "receipts")
    last_test = next((item for item in reversed(receipts) if item.get("state") == "test"), None)
    valid = isinstance(entry, dict) and _webhook_entry_error(entry) is None
    sender_key = entry.get("sender_key") if isinstance(entry, dict) else None
    url = entry.get("url") if isinstance(entry, dict) else None
    receipt: dict[str, Any] = {
        "schema": "kaola-delegator-webhook-status/1",
        "project": project_root,
        "config_path": str(config_path),
        "config_mode": config_mode,
        "configured": bool(valid and entry.get("enabled") is not None),
        "enabled": entry.get("enabled") if valid else None,
        "owner_agent": entry.get("owner_agent") if isinstance(entry, dict) else None,
        "sender_key_attachment": attachment_view if valid else None,
        "sender_key_present": isinstance(sender_key, str) and bool(sender_key) if valid else False,
        "fingerprint": (_webhook_fingerprint(url, sender_key)
                        if valid and isinstance(url, str) else None),
        "last_receipt": receipts[-1] if receipts else None,
        "last_test": last_test,
        "receipts_path": str(delegator_webhook_receipts_path(project_root)),
        "repeated_failure": _webhook_repeated_view(store.get("repeated_failure")),
        "previous_repeated_failure": _webhook_repeated_view(
            store.get("previous_repeated_failure")),
        "failed_receipts_kept": len(_webhook_dict_list(store, "failed_receipts")),
    }
    if config_error is not None:
        receipt["error"] = config_error
    return receipt


def _webhook_refusal(reason: str, detail: str, **extra: Any) -> tuple[int, dict[str, Any]]:
    receipt = _stamp_recovery({"result": "refused", "reason": reason, "detail": detail, **extra})
    _emit_receipt(receipt)
    return 2, receipt


def _webhook_realpath_project(raw: Any) -> str | None:
    if not isinstance(raw, str) or not raw:
        return None
    path = Path(raw)
    if not path.is_dir():
        return None
    return os.path.realpath(str(path))


def command_delegator_webhook(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="kaola-acp.py delegator-webhook")
    sub = parser.add_subparsers(dest="action", required=True)
    for name in ("configure", "status", "test", "remove"):
        p = sub.add_parser(name)
        p.add_argument("--project", required=True)
        if name == "configure":
            p.add_argument("--owner-agent", required=True)
            p.add_argument("--url-env")
            p.add_argument("--key-env")
            p.add_argument("--stdin", action="store_true")
            p.add_argument("--input-file")
            p.add_argument("--key-header")
            p.add_argument("--key-prefix")
            p.add_argument("--key-in-url", action="store_true")
            p.add_argument("--replace-owner")
        if name == "remove":
            p.add_argument("--owner-agent", required=True)
    sub.add_parser("deliver")
    args = parser.parse_args(argv)

    if args.action == "deliver":
        try:
            payload = json.loads(sys.stdin.read())
        except ValueError:
            payload = None
        # Signal-only enforcement at the sender: a payload that is not exactly
        # the wake shape records an invalid-payload receipt (when its project
        # resolves) and is never POSTed.
        if not _webhook_payload_ok(payload):
            project_root = _webhook_realpath_project(
                payload.get("project") if isinstance(payload, dict) else None)
            if project_root is not None:
                given = payload if isinstance(payload, dict) else {}
                _webhook_append_receipts(project_root, [_webhook_attempt_receipt(
                    given, 0, "failed", None, "invalid-payload", None, 0, True)])
            else:
                # No project directory, so the receipts file has nowhere to go.
                _webhook_diag(PROJECT_UNRESOLVED_LINE)
            return 1
        project_root = _webhook_realpath_project(payload["project"])
        if project_root is None:
            _webhook_diag(PROJECT_UNRESOLVED_LINE)
            return 1
        receipts = _webhook_deliver(project_root, payload)
        return 0 if receipts[-1]["result"] in ("delivered", "skipped") else 1

    project_root = _webhook_realpath_project(args.project)
    if project_root is None:
        return _webhook_refusal("invalid-input",
                                "--project must be an existing directory")[0]

    config_path = delegator_webhook_config_path()

    if args.action == "status":
        receipt = _webhook_status_receipt(project_root)
        # Issue #311: the cron fallback's inquiry runs this command. It is the
        # holder-lost detector that does not need a new Host start. ``test``
        # stays a delivery probe and does not scan.
        _webhook_attach_holder_lost(project_root, receipt)
        _emit_receipt(receipt)
        return 0

    if args.action == "test":
        payload = {
            "schema": "kaola-delegator-wake/1",
            "project": project_root,
            "session": None,
            "holder_instance_id": "test-" + secrets.token_hex(8),
            "event_seq": 0,
            "state": "test",
            "state_detail": "test",
            "reason": "test",
            "ts": _utc_stamp(),
        }
        receipts = _webhook_deliver(project_root, payload)
        print(json.dumps({"schema": "kaola-delegator-webhook-test/1",
                          "project": project_root,
                          "result": receipts[-1]["result"],
                          "receipts": receipts},
                         ensure_ascii=False, sort_keys=True))
        return 0 if receipts[-1]["result"] == "delivered" else 1

    if args.action == "remove":
        with _webhook_config_lock(config_path):
            doc, config_error, _mode = _webhook_read_config(config_path)
            if config_error is not None:
                return _webhook_refusal(
                    config_error, f"webhook config at {config_path} is unusable")[0]
            projects = (doc or {}).get("projects", {})
            existing = projects.get(project_root)
            if existing is None:
                print(json.dumps({"result": "absent", "project": project_root},
                                 ensure_ascii=False, sort_keys=True))
                return 0
            if existing.get("owner_agent") != args.owner_agent:
                return _webhook_refusal(
                    "entry-owned-by-other-agent",
                    "the configured entry belongs to another agent label",
                    owner_agent=existing.get("owner_agent"))[0]
            del projects[project_root]
            assert doc is not None
            _webhook_atomic_write(config_path, doc)
        print(json.dumps({"result": "removed", "project": project_root},
                         ensure_ascii=False, sort_keys=True))
        return 0

    # configure
    sources = sum(1 for given in (args.url_env, args.stdin, args.input_file) if given)
    if sources > 1:
        return _webhook_refusal("invalid-input",
                                "give exactly one of --url-env, --stdin or --input-file")[0]
    attachments = sum(1 for given in (args.key_header, args.key_in_url) if given)
    if attachments != 1:
        return _webhook_refusal(
            "invalid-input", "give exactly one of --key-header NAME or --key-in-url")[0]
    if args.key_prefix is not None and not args.key_header:
        return _webhook_refusal("invalid-input", "--key-prefix needs --key-header")[0]
    if args.key_env and not args.url_env:
        return _webhook_refusal("invalid-input", "--key-env needs --url-env")[0]

    url: str | None = None
    sender_key: str | None = None
    if args.url_env:
        url = os.environ.get(args.url_env)
        sender_key = os.environ.get(args.key_env) if args.key_env else None
        if url is None or (args.key_env and sender_key is None):
            return _webhook_refusal("input-required",
                                    "a named environment variable is unset")[0]
    elif args.stdin or args.input_file:
        if args.stdin:
            try:
                given = json.loads(sys.stdin.read())
            except ValueError:
                given = None
        else:
            input_path = Path(args.input_file)
            try:
                stat_result = input_path.stat()
            except OSError:
                stat_result = None
            if (stat_result is None or not input_path.is_file()
                    or stat_result.st_uid != os.getuid()
                    or (stat_result.st_mode & 0o077)):
                return _webhook_refusal(
                    "invalid-input",
                    "--input-file must be a regular file owned by you with mode 0600")[0]
            try:
                given = json.loads(input_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                given = None
        if not isinstance(given, dict):
            return _webhook_refusal("invalid-input",
                                    "the input must be one JSON object")[0]
        url = given.get("url")
        sender_key = given.get("sender_key")
    else:
        if not sys.stdin.isatty():
            return _webhook_refusal(
                "input-required",
                "no input source: use --url-env, --stdin, --input-file, or a terminal")[0]
        url = getpass.getpass("webhook URL: ")
        sender_key = getpass.getpass("sender key (empty when the key is in the URL): ")
        sender_key = sender_key or None

    url_error = _webhook_url_error(url)
    if url_error:
        return _webhook_refusal("invalid-input", url_error)[0]
    if args.key_header:
        attachment = {"style": "header", "name": args.key_header,
                      "prefix": args.key_prefix or ""}
    else:
        attachment = {"style": "url"}
    attach_error = _webhook_attachment_error(attachment, sender_key)
    if attach_error:
        return _webhook_refusal("invalid-input", attach_error)[0]

    with _webhook_config_lock(config_path):
        # Re-read inside the flock: the ownership decision and the merged
        # projects map must come from the state under the lock, otherwise two
        # concurrent configures can read the same old file and one entry is
        # lost on write.
        doc, config_error, _mode = _webhook_read_config(config_path)
        if config_error is not None:
            return _webhook_refusal(
                config_error, f"webhook config at {config_path} is unusable")[0]
        projects = (doc or {}).setdefault("projects", {})
        existing = projects.get(project_root)
        if isinstance(existing, dict) and existing.get("owner_agent") != args.owner_agent:
            if args.replace_owner != existing.get("owner_agent"):
                return _webhook_refusal(
                    "entry-owned-by-other-agent",
                    "the configured entry belongs to another agent label; pass "
                    "--replace-owner with that exact label after its routines retired",
                    owner_agent=existing.get("owner_agent"))[0]

        projects[project_root] = {
            "url": url,
            "sender_key": sender_key,
            "sender_key_attachment": attachment,
            "enabled": True,
            "owner_agent": args.owner_agent,
            "updated_at": _utc_stamp(),
        }
        doc = doc or {"schema": DELEGATOR_WEBHOOK_SCHEMA, "projects": projects}
        doc["schema"] = DELEGATOR_WEBHOOK_SCHEMA
        try:
            _webhook_atomic_write(config_path, doc)
        except OSError as exc:
            return _webhook_refusal("invalid-input",
                                    f"config write failed: {type(exc).__name__}")[0]
    receipt = _webhook_status_receipt(project_root)
    receipt["result"] = "configured"
    _emit_receipt(receipt)
    return 0


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        payload = command_list(parse_list_args(sys.argv[2:]))
        _emit_receipt(payload)
        return 0
    if len(sys.argv) > 1 and sys.argv[1] == "survey":
        payload = command_survey(parse_survey_args(sys.argv[2:]))
        _emit_receipt(payload)
        return 0
    if len(sys.argv) > 1 and sys.argv[1] == "packages":
        payload = command_packages(parse_packages_args(sys.argv[2:]))
        _emit_receipt(payload)
        return 0
    if len(sys.argv) > 1 and sys.argv[1] == "model-package":
        payload = command_model_package(parse_model_package_args(sys.argv[2:]))
        _emit_receipt(payload)
        return 0
    if len(sys.argv) > 1 and sys.argv[1] == "delegator-webhook":
        return command_delegator_webhook(sys.argv[2:])

    parser = ReceiptArgumentParser(prog="kaola-acp.py")
    parser.add_argument("platform", choices=PLATFORMS)
    parser.add_argument("command", choices=[
        "preflight", "start", "send", "steer", "wait", "observe", "capture",
        "permit", "key", "answer", "cancel", "stop", "status", "view",
        "follow", "drain-restart", "rebind-host", "wake",
    ])
    parser.add_argument("--repo", required=True)
    parser.add_argument("--session")
    parser.add_argument("--command", dest="agent_command")
    parser.add_argument("--record-root")
    parser.add_argument("--resume")
    parser.add_argument("--continue", dest="use_continue", action="store_true")
    parser.add_argument("--text")
    parser.add_argument("--reason")
    parser.add_argument("--stdin", action="store_true")
    parser.add_argument("--wait", dest="wait", action="store_true", default=None)
    parser.add_argument("--no-wait", dest="wait", action="store_false")
    # Issue #386: explicit receipt Git evidence. Omitted keeps the command's
    # default: off for send --no-wait, steer and permit; on everywhere else.
    parser.add_argument("--git-facts", dest="git_facts", action="store_true",
                        default=None,
                        help="include Git facts in this receipt")
    parser.add_argument("--no-git-facts", dest="git_facts", action="store_false",
                        default=None,
                        help="omit Git facts from this receipt")
    parser.add_argument("--timeout", type=float)
    parser.add_argument("--max-final-chars", type=int, default=4000)
    parser.add_argument("--request-id")
    parser.add_argument("--option")
    parser.add_argument("--expected-holder-instance-id")
    # Issue #380: accepted only by send/steer; other commands refuse it as
    # invalid-input before any transport work.
    parser.add_argument("--client-message-id")
    parser.add_argument("--launch-backend", choices=LAUNCH_BACKENDS, default=None,
                        help="holder launch backend: auto (default), direct, launchd or systemd-user")
    parser.add_argument("--key")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--preserve-dispatched-workers", action="store_true",
                        help="stop or drain-restart this holder but keep each worker it dispatched")
    parser.add_argument("--lines", type=int)
    parser.add_argument("--tools", action="store_true")
    parser.add_argument("--since", type=int)
    parser.add_argument("--format", choices=("json", "text"), default="json")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--inline", action="store_true")
    parser.add_argument("--model")
    parser.add_argument("--effort")
    # Issue #111/#188: validated against the manifest's declared presets after
    # it loads, so an undeclared name answers a typed refusal, not exit 2.
    parser.add_argument("--tier", metavar="default|PLATFORM_TIER")
    # Issue #245: the only start flag that sets a session role. Host, expert,
    # elite, and worker are derived, never accepted as this flag.
    parser.add_argument("--role", choices=("sideagent", "sidekick"),
                        help="Sideagent session identity (sidekick: legacy compatibility)")
    # Issue #181: None means "not passed", so explicit detection is None-ness.
    # Every consumer that relied on the old "off" default treats None as off.
    parser.add_argument("--fast", choices=("on", "off"))
    # Issue #339: a start whose resolved model option the agent rejects is
    # refused; this flag is the caller's explicit acceptance of the agent's
    # own model selection instead.
    parser.add_argument("--allow-unapplied-model", action="store_true",
                        help="accept a start whose model config option the agent rejected")
    parser.add_argument("--mode")
    parser.add_argument("--steer-mode", choices=("native", "interrupt"))
    parser.add_argument("--delivery", choices=("native", "after-turn"))
    parser.add_argument("--cancel-timeout", type=float)
    args = parser.parse_args()
    # Issue #181: ``--command`` is resolved below, so its raw presence must be
    # captured now — None-ness is what makes it explicit.
    args.agent_command_given = args.agent_command is not None

    args.manifest = load_manifest(args.platform)
    repo = resolve_repo(args.repo)
    # Issue #383: 0 used to mean "unbounded" and a negative value reached
    # socket.settimeout as an error. Neither is a usable bound; refuse before
    # any record or transport work so the caller gets one typed answer.
    if args.timeout is not None and args.timeout <= 0:
        receipt = base_receipt(args, repo)
        receipt.update({
            "result": "refused",
            "reason": "invalid-input",
            "outcome": "invalid_input",
            "mutation_status": "not_started",
            "mutation_performed": False,
            "error": {
                "code": "invalid-input",
                "message": "--timeout must be greater than 0 seconds; omit it "
                           "for the command's default bound",
            },
        })
        _emit_receipt(receipt)
        return 1
    if not tier_declared(args.manifest, args.tier):
        _emit_receipt(tier_refusal(args, repo))
        return 1
    if args.command != "preflight":
        if not args.session or not SESSION_PATTERN.match(args.session):
            die("invalid or missing --session name")
    if (args.platform == "dsh" and args.command == "start" and args.mode
            and dsh_permission_mode(args)[0] not in DSH_PERMISSION_MODES):
        # Issue #158: name the Agent-facing wrapper flag, not the internal one.
        die(f"--permission-mode for dsh must be one of {', '.join(DSH_PERMISSION_MODES)} "
            "or bypassPermissions")
    args.agent_command = (
        args.agent_command
        or os.environ.get("KAOLA_ACP_COMMAND")
        or manifest_launch_command(args, tier_agent_command(args) or args.manifest["acp_command"])
    )
    if not args.agent_command:
        die(f"no ACP command for platform {args.platform} (use --command)")
    args.agent_command, args.agent_command_facts = resolve_agent_command(args.agent_command)

    # Issue #380: only send/steer may name one message. Any other command is a
    # usage refusal before any transport work (preflight included).
    if args.client_message_id is not None and args.command not in ("send", "steer"):
        receipt = base_receipt(args, repo)
        receipt.update({
            "result": "refused", "reason": "invalid-input",
            "outcome": "invalid_input",
            "mutation_status": "not_started", "mutation_performed": False,
            "client_message_id": args.client_message_id,
            "error": {
                "code": "invalid-input",
                "message": "--client-message-id is accepted only by send and steer",
            },
        })
        _emit_receipt(receipt)
        return 1

    if args.command == "preflight":
        receipt = command_preflight(args, repo)
        _emit_receipt(receipt)
        return 0
    directory = record_dir(args, repo) if args.session else None
    if args.client_message_id is not None:
        # A live holder that predates the feature refuses the id rather than
        # silently opening a duplicate turn. A dead holder keeps its ordinary
        # transport answer.
        refused = client_message_id_unsupported(args, repo, directory)
        if refused is not None:
            _emit_receipt(refused)
            return 0
    if args.command == "start":
        receipt = command_start(args, repo)
        # Issue #313: advisory only. Every issue_name value still returns the
        # start result this command already decided.
        stamp_issue_name_receipt(receipt, args.platform, args.session, repo)
        _emit_receipt(receipt)
        # A typed refusal is a pre-mutation decision, exit 1 like the shell's
        # canonical-root refusal; transport errors stay exit-0 receipts.
        return 1 if receipt.get("result") == "refused" else 0
    if args.command == "drain-restart":
        receipt = command_drain_restart(args, repo)
        _emit_receipt(receipt)
        return 1 if receipt.get("result") == "refused" else 0
    if args.command == "rebind-host":
        receipt = command_rebind_host(args, repo, directory)
        _emit_receipt(receipt)
        return 1 if receipt.get("result") == "refused" else 0
    if args.command == "view":
        if directory is None:
            die("invalid or missing --session name")
        receipt = command_view(args, repo, directory)
        _emit_receipt(receipt)
        return 0
    if args.command == "follow":
        if directory is None:
            die("invalid or missing --session name")
        return command_follow(args, repo, directory)

    timeout = args.timeout

    if args.command == "send":
        text = args.text
        if args.stdin:
            text = sys.stdin.read()
        if not text:
            die("send requires --text or --stdin")
        wait_selection, bound_holder_id = resolve_send_wait(args, repo, directory)
        # Issue #386: base_receipt follows the resolved wait mode, so an
        # omitted selection that resolves to blocking keeps the L0 Git facts.
        args.resolved_wait = wait_selection["wait"]
        sock_timeout = client_socket_timeout(args, wait_selection["wait"],
                                             op="prompt")
        prompt_params = {"text": text, "wait": wait_selection["wait"], "timeout": timeout,
                         "max_final_chars": args.max_final_chars}
        if args.client_message_id is not None:
            prompt_params["client_message_id"] = args.client_message_id
        if args.expected_holder_instance_id is not None:
            prompt_params["expected_holder_instance_id"] = args.expected_holder_instance_id
        elif bound_holder_id is not None:
            prompt_params["expected_holder_instance_id"] = bound_holder_id
        receipt = op_or_holder_lost(
            args, repo, directory, "prompt",
            prompt_params,
            sock_timeout,
        )
        receipt["wait_selection"] = wait_selection
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
            interrupt_params: dict[str, Any] = {
                "text": text, "timeout": timeout,
                "cancel_timeout": args.cancel_timeout,
            }
            if args.client_message_id is not None:
                interrupt_params["client_message_id"] = args.client_message_id
            if args.expected_holder_instance_id is not None:
                interrupt_params["expected_holder_instance_id"] = (
                    args.expected_holder_instance_id)
            receipt = op_or_holder_lost(
                args, repo, directory, "steer_interrupt",
                interrupt_params,
                client_socket_timeout(args, op="steer_interrupt"),
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
            if args.client_message_id is not None:
                receipt["client_message_id"] = args.client_message_id
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
            if args.client_message_id is not None:
                receipt["client_message_id"] = args.client_message_id
        else:
            delivery = args.delivery or args.manifest.get("steering_delivery", "native")
            refusal = steer_after_turn_refusal(args, directory)
            if refusal is not None and args.client_message_id is not None:
                refusal["client_message_id"] = args.client_message_id
            steer_params: dict[str, Any] = {
                "text": text, "method": method, "timeout": timeout,
                "delivery": delivery,
            }
            if args.client_message_id is not None:
                steer_params["client_message_id"] = args.client_message_id
            if args.expected_holder_instance_id is not None:
                # Issue #380: only an explicitly supplied binding is forwarded;
                # a normal steer remains unbound.
                steer_params["expected_holder_instance_id"] = (
                    args.expected_holder_instance_id)
            receipt = refusal if refusal is not None else op_or_holder_lost(
                args, repo, directory, "steer",
                steer_params,
                client_socket_timeout(args, op="steer"),
            )
            receipt.setdefault("native_steering", native_steering)
            receipt.setdefault("steer_mode", "native")
            error = receipt.get("error") or {}
            if error.get("code") == "unknown-op":
                receipt.update(holder_predates_steer(method, error))
    elif args.command == "wait":
        receipt = op_or_holder_lost(
            args, repo, directory, "wait", {"timeout": timeout},
            client_socket_timeout(args, op="wait")
        )
    elif args.command in ("observe", "status"):
        receipt = op_or_holder_lost(args, repo, directory, "state", {}, 10.0)
        record = read_record(directory)
        if record:
            receipt.setdefault("record", record)
            # Issue #203: a stopped or lost holder still has its saved start
            # evidence; an old record without it stays without it.
            if "start_evidence" not in receipt and "start_evidence" in record:
                receipt["start_evidence"] = record["start_evidence"]
            # Issue #245: same lift as start evidence. A live state reply
            # already carries the field; a stopped or legacy record fills it.
            if "session_role" not in receipt:
                persisted_role = record.get("session_role")
                receipt["session_role"] = (
                    persisted_role if persisted_role in SESSION_ROLES else None
                )
        # Only a session that exists has a binding to report; ``no-session``
        # stays silent rather than answering "unknown" about nothing.
        if record is not None or "heartbeat_host" in receipt:
            attach_binding_fact(
                receipt, receipt if "heartbeat_host" in receipt else record
            )
        merged = dict(record or {})
        for key in ("runner_build", "accepted_revision", "script_paths", "baseline_exempt"):
            if key in receipt:
                merged[key] = receipt[key]
        if merged:
            receipt.update(seat_freshness(merged))
        # Emission copy only. The holder object and receipt["record"] stay native.
        stamp_quota_emission(receipt, args.platform)
        # Issue #316: read a model the session already exposed. The on-disk
        # start snapshot is left as the start wrote it.
        evidence_repo = repo
        if isinstance(record, dict) and isinstance(record.get("repo"), str) and record["repo"]:
            evidence_repo = record["repo"]
        annotate_session_model_evidence(receipt, args.platform, evidence_repo, directory)
        annotate_argv_effective_selection(receipt, args.manifest)
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
            args, repo, directory, "cancel", params,
            client_socket_timeout(args, op="cancel")
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
                args, repo, directory, "cancel", params,
                client_socket_timeout(args, op="cancel")
            )
    elif args.command == "answer":
        receipt = base_receipt(args, repo)
        receipt["error"] = {"code": "answer-unsupported",
                            "message": "use send; --decision-id maps to permit --request-id"}
    elif args.command == "wake":
        # Issue #317: explicit Host wake. The holder mints event_seq and
        # sends now. Seats may still be working. This is not all-idle.
        if args.reason not in HOST_INITIATED_WAKE_REASONS:
            die("wake requires --reason needs_decision, question_waiting, "
                "or delivery_review")
        record = read_record(directory)
        params = {"reason": args.reason}
        if args.expected_holder_instance_id is not None:
            params["expected_holder_instance_id"] = args.expected_holder_instance_id
        elif isinstance((record or {}).get("holder_instance_id"), str):
            params["expected_holder_instance_id"] = record["holder_instance_id"]
        receipt = op_or_holder_lost(
            args, repo, directory, "wake_delegator", params,
            client_socket_timeout(args, op="wake_delegator"))
    elif args.command == "stop":
        # Issue #73: a stop is bound to the exact holder instance the Agent
        # verified, so a same-named session rebuilt by a later instance is
        # refused instead of stopped.
        params = {"force": args.force}
        if args.expected_holder_instance_id is not None:
            params["expected_holder_instance_id"] = args.expected_holder_instance_id
        refused = preserve_refusal(args, repo, directory)
        if refused is not None:
            receipt = refused
        else:
            if preserving(args):
                params["preserve_dispatched_workers"] = True
            prior = read_record(directory) if directory is not None else None
            receipt = op_or_holder_lost(
                args, repo, directory, "stop", params, 30.0
            )
            # Issue #359: a recorded clean stop retires this host's registry
            # row. The holder already deregisters itself on a socket-answered
            # stop; this also covers dead-record sweeps and older holders.
            if (receipt.get("stopped") is True and directory is not None
                    and isinstance((prior or {}).get("holder_instance_id"), str)):
                host_registry_deregister(
                    repo, args.platform, args.session,
                    holder_instance_id=prior["holder_instance_id"])
            if directory is not None:
                attach_broker_reconcile(receipt, args, repo, directory)
    else:
        die(f"unhandled command {args.command}")
    _emit_receipt(receipt)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except acp_paths.RecordRootUnsafe as exc:
        _emit_receipt({"result": "refused", "reason": "record-root-unsafe",
                       "error": {"code": "record-root-unsafe", "message": str(exc)},
                       "mutation_performed": False, "mutation_status": "not_started"})
        raise SystemExit(1)
    except acp_paths.RecordRootMismatch as exc:
        _emit_receipt({"result": "refused", "reason": "record-root-mismatch",
                       "error": {"code": "record-root-mismatch", "message": str(exc)},
                       "mutation_performed": False, "mutation_status": "not_started"})
        raise SystemExit(1)
    except InputError as exc:
        argv = sys.argv[1:]
        def argument_value(flag: str) -> str | None:
            for index, word in enumerate(argv):
                if word == flag and index + 1 < len(argv):
                    return argv[index + 1]
                if word.startswith(flag + "="):
                    return word[len(flag) + 1:]
            return None
        receipt = input_error_receipt(
            str(exc), argv[0] if argv else None,
            argv[1] if len(argv) > 1 and argv[0] in PLATFORMS else None,
            argument_value("--repo"), argument_value("--session"))
        _emit_receipt(receipt)
        raise SystemExit(exc.code)
