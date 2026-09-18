#!/usr/bin/env python3
"""Runner-owned ACP adapter for the native ZCode stdio app-server.

Speaks ACP (newline-delimited JSON-RPC) to the Kaola Runner on stdin/stdout and
the private ZCode Protocol to an explicitly resolved `app-server --stdio` child.

Issue #51 selection gate, Gate 2: the active community adapter
`william0wang/zcode-acp` could not be reduced to the Runner-required surface
(its quota, task-index, goal-loop and sandbox code is imported *by* the core
handlers), so this is a Runner-owned translation written against that project's
`docs/PROTOCOL.md` as reference. See `third_party/zcode-acp/UPSTREAM.md`.

Model provider bridging (Issue #51 owner correction, 2026-09-16). CLI 0.16.5
resolves its model provider from ``~/.zcode/cli/config.json`` while the desktop
App keeps the logged-in providers under ``~/.zcode/v2/config.json``; a headless
``session/create`` therefore fails with ``Model config is missing``. The desktop
App itself feeds providers to the app-server in memory (``runtimeModel`` /
provider-registry overlays whose ``apiKey`` is ``{source: "inline"}``), and
this adapter does the same, bounded as follows:

* ``~/.zcode/v2/config.json`` (and ``coding-plan-cache.json`` for plan status)
  are opened read-only; nothing under ``~/.zcode`` is ever written, and
  ``~/.zcode/cli/config.json`` is never touched;
* only an ``enabled`` provider whose id ends in ``-coding-plan`` with a
  non-empty plan credential and model list is eligible; ``*-start-plan``
  (headless captcha) and pay-as-you-go providers are refused, never fallen
  back to, and the selected provider is reported in ``agentInfo._meta``;
* the credential travels only inside the ``session/create`` /
  ``session/resume`` / ``session/setModel`` overlay to the child's stdin; it
  is never logged, never placed in an ACP message, never written to disk;
* ``~/.zcode/v2/credentials.json`` and ``~/.config/zcode-acp/config.json``
  are never opened;

Deliberate non-capabilities, enforced here and asserted by the contract suite:

* no auth environment injection - the child env is built from a strict
  allowlist, so ``ANTHROPIC_API_KEY`` and friends are never forwarded;
* no config rewrite, no ``tasks-index.sqlite`` write;
* no network, no quota client, no remote hub, no listener, no daemon, no TUI,
  no sandbox. This module imports no socket, http, urllib or sqlite3.

The ZCode runtime path is explicit and fails closed: there is no PATH search,
no registry install and no filesystem discovery.
"""

from __future__ import annotations

import argparse
import atexit
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from typing import Any

ADAPTER_NAME = "kaola-zcode-acp"
ADAPTER_VERSION = "0.3.3"

# Desktop provider registry (read-only) and plan-status cache, relative to HOME.
DESKTOP_CONFIG_RELPATH = os.path.join(".zcode", "v2", "config.json")
PLAN_CACHE_RELPATH = os.path.join(".zcode", "v2", "coding-plan-cache.json")
CODING_PLAN_PROVIDER_IDS = frozenset(("builtin:bigmodel-coding-plan", "builtin:zai-coding-plan"))
START_PLAN_SUFFIX = "-start-plan"
# Backend `kind` enum and the apiFormat it maps to (desktop converter parity).
API_FORMAT_BY_KIND = {
    "anthropic": "anthropic-messages",
    "openai": "openai-chat-completions",
    "openai-compatible": "openai-chat-completions",
}
PROVIDER_SOURCES = ("builtin", "models-dev", "custom", "user", "workspace", "ephemeral")

# ZCode 3.12+ bundled provider-config resolution (Issue #79).
#
# 3.12.3's own bootstrap probes only two paths from the entry's directory --
# `<entryDir>/provider/zcode-builtin.json` and a five-levels-up
# `config/provider/zcode-builtin.json` that fits the source tree
# (`apps/zcode-cli/packages/cli/dist/zcode.cjs`) but not the shipped .app, where
# the table sits ONE level up at `<Resources>/config/provider/zcode-builtin.json`.
# In the .app layout the probe therefore fails and `app-server` exits 1 before it
# ever serves a request. Setting the two env names below makes the CLI use the
# given paths verbatim instead of probing.
#
# The builtin path is derived from the entry this adapter already verified in
# resolve_runtime(), never inherited from the parent environment: an inherited
# value would be unowned and could point the CLI at an attacker- or
# stale-controlled provider table. Neither name is in ENV_ALLOWLIST, so an
# inherited value cannot reach the child.
BUILTIN_PROVIDER_CONFIG_ENV = "ZCODE_BUILTIN_PROVIDER_CONFIG_FILE"
PERSONAL_PROVIDER_CONFIG_ENV = "ZCODE_PERSONAL_PROVIDER_CONFIG_FILE"
PERSONAL_PROVIDER_CONFIG_RELPATH = os.path.join(".zcode", "v2", "provider_config.json")
# Probed in order, first existing file wins; mirrors the CLI's own candidates
# plus the shipped .app layout it misses.
BUILTIN_PROVIDER_CONFIG_CANDIDATES = (
    ("provider", "zcode-builtin.json"),
    (os.pardir, "config", "provider", "zcode-builtin.json"),
    (os.pardir, os.pardir, os.pardir, os.pardir, os.pardir,
     "config", "provider", "zcode-builtin.json"),
)


def resolve_builtin_provider_config(entry: str) -> str | None:
    """Locate the bundled provider table relative to the verified entry.

    Returns None when no candidate exists; the caller then leaves both env
    names unset and the CLI keeps its own (older, working) behaviour.
    """
    base = os.path.dirname(os.path.abspath(entry))
    for parts in BUILTIN_PROVIDER_CONFIG_CANDIDATES:
        candidate = os.path.normpath(os.path.join(base, *parts))
        if os.path.isfile(candidate):
            return candidate
    return None


def personal_provider_config_path(home: str | None = None) -> str | None:
    """Path of the per-user provider config. Never opened by this adapter."""
    home = home or os.environ.get("HOME") or ""
    if not home:
        return None
    return os.path.join(home, PERSONAL_PROVIDER_CONFIG_RELPATH)


# The app-server's own provider registry is keyed by `account:*` ids, not by the
# desktop registry's `builtin:*` ids. The bundled table's providerRules list the
# individual Coding Plan under these names (Issue #79).
# `states[<id>].availability` enum, from the installed 3.12.3 schema.
PLAN_AVAILABILITY = ("available", "pending", "unavailable", "unknown")

ACCOUNT_PROVIDER_BY_CODING_PLAN = {
    "builtin:bigmodel-coding-plan": "account:bigmodel-individual-coding-plan",
    "builtin:zai-coding-plan": "account:zai-individual-coding-plan",
}


def read_builtin_release(path: str) -> dict[str, Any]:
    """Read the bundled provider table. Rules only; it carries no credential."""
    release = _read_json_readonly(path)
    if not isinstance(release, dict):
        raise RuntimeError_(f"bundled provider table is not an object: {path}")
    if not isinstance(release.get("revision"), int):
        raise RuntimeError_(f"bundled provider table has no integer revision: {path}")
    return release


def builtin_revision_string(release: dict[str, Any], active_path: str) -> str:
    """Reproduce the backend's own builtin revision identity.

    `NodeZCodeBuiltinProviderConfigSource` hashes the RESOLVED PATH STRING of the
    active table -- not its bytes -- and reports
    `zcode-builtin:<revision>:<sha256(path)>`. Node's path.resolve() normalises
    without following symlinks, so abspath is the faithful equivalent.
    """
    digest = hashlib.sha256(os.path.abspath(active_path).encode("utf-8")).hexdigest()
    return f"zcode-builtin:{release['revision']}:{digest}"


def account_model_ids(release: dict[str, Any], account_id: str) -> list[str]:
    """`builtinModelIds` the bundled table lists for one account provider."""
    rules = (((release.get("config") or {}).get("providerConfigRules") or {})
             .get("providerRules") or [])
    for rule in rules:
        if isinstance(rule, dict) and rule.get("providerId") == account_id:
            ids = (rule.get("config") or {}).get("builtinModelIds")
            if isinstance(ids, list):
                return [m for m in ids if isinstance(m, str) and m]
    return []


def account_reasoning_levels(release: dict[str, Any], model_id: str) -> list[str]:
    """Reasoning levels the bundled table allows for one model.

    `modelRules` are regex rules applied in order, later matches overriding
    earlier ones -- the backend tests them as `^(?:<modelMatch>)$`, case
    insensitive. 3.12+ requires an explicit level for the Coding Plan models.
    """
    rules = ((release.get("config") or {}).get("modelConfigRules") or {}).get("modelRules") or []
    levels: list[str] = []
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        pattern = rule.get("modelMatch")
        if not isinstance(pattern, str):
            continue
        try:
            if not re.match(f"^(?:{pattern})$", model_id, re.IGNORECASE):
                continue
        except re.error:
            continue
        values = (((rule.get("config") or {}).get("optionSpecs") or {})
                  .get("reasoningLevel") or {}).get("values")
        if isinstance(values, list) and values:
            levels = [v for v in values if isinstance(v, str) and v]
    return levels


def build_account_config(
    choice: dict[str, Any], release: dict[str, Any], active_path: str,
) -> dict[str, Any] | None:
    """`provider/updateAccountConfig` snapshot for the one enabled Coding Plan.

    Carries no credential: the backend asks for auth per model request through
    `interaction/requestProviderRuntimeHeaders`. Returns None when this plan has
    no account-provider counterpart, so the caller can stay on the old path.
    """
    account_id = ACCOUNT_PROVIDER_BY_CODING_PLAN.get(choice["provider_id"])
    if not account_id:
        return None
    bundled = account_model_ids(release, account_id)
    if not bundled:
        return None
    # Offer only models the desktop plan and the bundled table agree on, in the
    # desktop's order; nothing is substituted or invented.
    model_ids = [m for m in choice["model_ids"] if m in bundled]
    if not model_ids:
        raise RuntimeError_(
            f"{choice['provider_id']} offers {', '.join(choice['model_ids'])} but "
            f"{account_id} lists {', '.join(bundled)}; no shared model"
        )
    # `availability` is reported, not asserted: the desktop plan cache is the
    # only fact we have about the plan, and an unrecognised status stays
    # `unknown` rather than being upgraded to `available`.
    status = choice.get("plan_cache_status")
    availability = status if status in PLAN_AVAILABILITY else "unknown"
    return {
        "account_id": account_id,
        "model_ids": model_ids,
        "release": release,
        "params": {
            "revision": f"{ADAPTER_NAME}:{int(time.time() * 1000)}",
            "basedOnZCodeBuiltinRevision": builtin_revision_string(release, active_path),
            "providers": {
                account_id: {
                    "builtinModelIds": model_ids,
                    "access": {"type": "zhipu-account", "entitled": True},
                },
            },
            # Measured against the installed 3.12.3 schema: `availability` and
            # `entitled` are required here, and `current` is required by the
            # snapshot validator for an entitled zhipu-account provider.
            "states": {
                account_id: {
                    "availability": availability,
                    "entitled": True,
                    "current": True,
                },
            },
        },
    }

# Environment names that must never reach the ZCode child. The child env is
# built from ENV_ALLOWLIST, so these are already excluded by construction;
# DENIED_ENV is the explicit, testable statement of that boundary.
DENIED_ENV = (
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_BASE_URL",
    "OPENAI_API_KEY",
    "ZCODE_API_KEY",
    "ZCODE_BASE_URL",
    "ZCODE_MODEL",
    "ZCODE_PROVIDER",
    "ZCODE_CREDENTIAL_SECRET",
    "ZCODE_BIGMODEL_USAGE_API_KEY",
    "ZCODE_BIGMODEL_USAGE_QUOTA_URL",
    "ZCODE_ACP_REMOTE",
    "ZCODE_ACP_REMOTE_TOKEN",
    "ZCODE_ACP_HUB_HOST",
    "ZCODE_ACP_HUB_PORT",
)

# Only these names are copied from the parent environment. HOME is required so
# the native runtime can find its own login; the adapter itself never reads
# anything under it. The two KAOLA_* names are Runner-internal facts, never
# credentials: the explicit ZCode entry/node paths this adapter was itself
# started with (a nested ZCode ACP worker reuses the same already-verified
# runtime; the nested start re-validates them with the same fail-closed
# checks). The holder's child-record path (KAOLA_ACP_CHILD_RECORD) is
# deliberately NOT forwarded: an external agent child must never gain a write
# handle to another holder's record (Issue #62, trust boundary).
ENV_ALLOWLIST = (
    "HOME",
    "PATH",
    "TMPDIR",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "USER",
    "LOGNAME",
    "SHELL",
    "TZ",
    "TERM",
    "KAOLA_ZCODE_ENTRY",
    "KAOLA_ZCODE_NODE",
)

# Protocol-documented backend modes / thought levels. These are vocabulary,
# not a catalog read from the user's config.
MODE_CHOICES = (
    ("plan", "Plan"),
    ("build", "Build"),
    ("edit", "Edit"),
    ("yolo", "Yolo"),
    ("auto", "Auto"),
)
THOUGHT_CHOICES = (
    ("low", "Low"),
    ("high", "High"),
    ("max", "Max"),
)

STDOUT_LOCK = threading.Lock()

# Credential values that must never leave the process except inside the
# backend overlay. Registered by select_coding_plan_provider; every string that
# reaches stderr or an ACP error message passes through redact().
_SECRET_VALUES: set[str] = set()


def register_secret(value: str) -> None:
    if isinstance(value, str) and len(value) >= 8:
        _SECRET_VALUES.add(value)


def redact(text: Any) -> Any:
    """Replace any registered credential value inside a string (or nested
    dict/list of strings) with a fixed marker."""
    if isinstance(text, str):
        for secret in _SECRET_VALUES:
            if secret in text:
                text = text.replace(secret, "<redacted-credential>")
        return text
    if isinstance(text, dict):
        return {k: redact(v) for k, v in text.items()}
    if isinstance(text, list):
        return [redact(v) for v in text]
    return text


def log(message: str) -> None:
    """Diagnostics go to stderr only; stdout is the ACP channel."""
    sys.stderr.write(f"[{ADAPTER_NAME}] {redact(message)}\n")
    sys.stderr.flush()


# --------------------------------------------------------------------------
# Explicit, fail-closed runtime resolution
# --------------------------------------------------------------------------


class RuntimeError_(Exception):
    """Raised when the explicit ZCode runtime cannot be honoured."""


def resolve_runtime(entry: str | None, node: str | None) -> tuple[str, str]:
    """Resolve the ZCode entry script and its node runtime, or fail closed.

    Both values must be explicit and must already exist. No PATH lookup, no
    glob, no registry install, no download.
    """
    entry = entry or os.environ.get("KAOLA_ZCODE_ENTRY") or ""
    node = node or os.environ.get("KAOLA_ZCODE_NODE") or ""
    if not entry:
        raise RuntimeError_(
            "no explicit ZCode entry: pass --zcode-entry or set KAOLA_ZCODE_ENTRY"
        )
    if not node:
        raise RuntimeError_(
            "no explicit ZCode node runtime: pass --zcode-node or set KAOLA_ZCODE_NODE"
        )
    if not os.path.isabs(entry) or not os.path.isabs(node):
        raise RuntimeError_("ZCode entry and node runtime must be absolute paths")
    if not os.path.isfile(entry):
        raise RuntimeError_(f"ZCode entry is not a file: {entry}")
    if not os.path.isfile(node):
        raise RuntimeError_(f"ZCode node runtime is not a file: {node}")
    if not os.access(node, os.X_OK):
        raise RuntimeError_(f"ZCode node runtime is not executable: {node}")
    return entry, node


def build_child_env(entry: str | None = None) -> dict[str, str]:
    """Build the child environment from a strict allowlist.

    ELECTRON_RUN_AS_NODE is set because the shipped ZCode runtime is the
    Electron binary acting as node; it also keeps the desktop UI from starting.

    When ``entry`` is given and the bundled provider table is found next to it,
    both ZCode 3.12+ provider-config names are set from that verified location
    (Issue #79). The CLI requires both or neither: given only the builtin name
    it re-syncs the table into a version-keyed runtime copy and rewires its
    config revision to that copy, so a half-set pair is worse than none.
    """
    env = {k: os.environ[k] for k in ENV_ALLOWLIST if k in os.environ}
    for name in DENIED_ENV:
        env.pop(name, None)
    env["ELECTRON_RUN_AS_NODE"] = "1"
    leaked = sorted(n for n in DENIED_ENV if n in env)
    if leaked:  # unreachable by construction; kept as an enforced invariant
        raise RuntimeError_(f"denied env leaked into child: {leaked}")
    # Neither provider-config name is in ENV_ALLOWLIST, so anything inherited
    # was already dropped above; these are set only from the verified entry.
    if entry:
        builtin = resolve_builtin_provider_config(entry)
        personal = personal_provider_config_path(env.get("HOME"))
        if builtin and personal:
            env[BUILTIN_PROVIDER_CONFIG_ENV] = builtin
            env[PERSONAL_PROVIDER_CONFIG_ENV] = personal
    return env


# --------------------------------------------------------------------------
# Desktop Coding Plan provider -> in-memory runtimeModel overlay
# --------------------------------------------------------------------------


def _read_json_readonly(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _model_element(model_id: str, entry: Any) -> dict[str, Any]:
    """config.json model entry -> protocol model element (schema `mEt`)."""
    entry = entry if isinstance(entry, dict) else {}
    element: dict[str, Any] = {"modelId": model_id}
    name = entry.get("name")
    if isinstance(name, str) and name:
        element["label"] = name
    limit = entry.get("limit") if isinstance(entry.get("limit"), dict) else {}
    if isinstance(limit.get("context"), int) and limit["context"] > 0:
        element["contextWindow"] = limit["context"]
    if isinstance(limit.get("output"), int) and limit["output"] > 0:
        element["maxOutputTokens"] = limit["output"]
    reasoning = entry.get("reasoning") if isinstance(entry.get("reasoning"), dict) else {}
    variants = [v for v in (reasoning.get("variants") or []) if isinstance(v, str) and v]
    if reasoning.get("enabled") is True and variants:
        block: dict[str, Any] = {
            "enabled": True,
            "levels": [{"value": v, "label": v} for v in variants],
        }
        default = reasoning.get("defaultVariant")
        if isinstance(default, str) and default in variants:
            block["defaultLevel"] = default
        element["reasoning"] = block
    modalities = entry.get("modalities") if isinstance(entry.get("modalities"), dict) else {}
    inputs = modalities.get("input") if isinstance(modalities.get("input"), list) else []
    if "image" in inputs:
        element["supportsImages"] = True
    if "video" in inputs:
        element["supportsVideo"] = True
    return element


def select_coding_plan_provider(home: str | None = None) -> dict[str, Any]:
    """Pick the desktop's enabled GLM Coding Plan provider, or fail closed.

    Read-only. Eligible: a known built-in Coding Plan id, ``enabled`` is true,
    the plan credential is non-empty and at least one model is listed.
    ``*-start-plan`` needs the desktop captcha flow headlessly and is refused;
    every other provider (pay-as-you-go API keys included) is refused so no
    turn can silently bill outside the plan. Nothing here logs the credential.
    """
    home = home or os.environ.get("HOME") or ""
    if not home:
        raise RuntimeError_("no HOME: cannot locate the desktop provider registry")
    config_path = os.path.join(home, DESKTOP_CONFIG_RELPATH)
    if not os.path.isfile(config_path):
        raise RuntimeError_(
            f"desktop provider registry not found: {config_path} "
            "(log in through the ZCode desktop App first)"
        )
    try:
        config = _read_json_readonly(config_path)
    except (OSError, ValueError) as exc:
        raise RuntimeError_(f"desktop provider registry unreadable: {exc.__class__.__name__}")
    providers = config.get("provider") if isinstance(config, dict) else None
    if not isinstance(providers, dict) or not providers:
        raise RuntimeError_("desktop provider registry lists no providers")

    rejected: dict[str, str] = {}
    chosen: dict[str, Any] | None = None
    for provider_id, raw in providers.items():
        if not isinstance(provider_id, str) or not isinstance(raw, dict):
            continue
        options = raw.get("options") if isinstance(raw.get("options"), dict) else {}
        models = raw.get("models") if isinstance(raw.get("models"), dict) else {}
        if provider_id.endswith(START_PLAN_SUFFIX):
            rejected[provider_id] = "start-plan (headless captcha flow, refused)"
            continue
        if provider_id not in CODING_PLAN_PROVIDER_IDS:
            rejected[provider_id] = "not a coding-plan provider (refused: no pay-as-you-go billing)"
            continue
        if raw.get("enabled") is not True:
            reason = raw.get("systemDisabledReason")
            rejected[provider_id] = f"not enabled ({reason})" if isinstance(reason, str) else "not enabled"
            continue
        key = options.get("apiKey")
        if not isinstance(key, str) or not key:
            rejected[provider_id] = "no plan credential in desktop registry"
            continue
        if not models:
            rejected[provider_id] = "no models listed"
            continue
        kind = raw.get("kind") if isinstance(raw.get("kind"), str) else "anthropic"
        if kind not in API_FORMAT_BY_KIND:
            rejected[provider_id] = f"unsupported provider kind {kind}"
            continue
        base_url = options.get("baseURL")
        if not isinstance(base_url, str) or not base_url:
            rejected[provider_id] = "no baseURL"
            continue
        if chosen is not None:
            # Two enabled Coding Plans contradict the owner's one-plan premise;
            # dict order is not a decision. Fail closed instead of guessing.
            raise RuntimeError_(
                "more than one enabled GLM Coding Plan provider in the desktop registry "
                f"({chosen['provider_id']}, {provider_id}); HUMAN_DECISION_REQUIRED: enable "
                "exactly one Coding Plan in the ZCode App"
            )
        model_ids = [m for m in models if isinstance(m, str) and m]
        register_secret(key)
        source = raw.get("source") if raw.get("source") in PROVIDER_SOURCES else "custom"
        chosen = {
            "provider_id": provider_id,
            "label": raw.get("name") if isinstance(raw.get("name"), str) else provider_id,
            "kind": kind,
            "api_format": API_FORMAT_BY_KIND[kind],
            "base_url": base_url,
            "source": source,
            "api_key_required": options.get("apiKeyRequired")
            if isinstance(options.get("apiKeyRequired"), bool) else None,
            "model_ids": model_ids,
            "default_model_id": model_ids[0],
            "models": [_model_element(m, models[m]) for m in model_ids],
            "_secret": key,  # never logged, never serialized into ACP output
            "plan_cache_status": None,
            "rejected": rejected,
        }
    if chosen is None:
        detail = "; ".join(f"{pid}: {why}" for pid, why in sorted(rejected.items())) or "none listed"
        raise RuntimeError_(
            "no enabled GLM Coding Plan provider in the desktop registry "
            f"(HUMAN_DECISION_REQUIRED: enable a Coding Plan in the ZCode App) [{detail}]"
        )
    cache_path = os.path.join(home, PLAN_CACHE_RELPATH)
    if os.path.isfile(cache_path):
        try:
            cache = _read_json_readonly(cache_path)
            items = ((cache.get("entryStatus") or {}).get("items") or {}) if isinstance(cache, dict) else {}
            status = items.get(chosen["provider_id"]) if isinstance(items, dict) else None
            if isinstance(status, dict) and isinstance(status.get("status"), str):
                chosen["plan_cache_status"] = status["status"]
        except (OSError, ValueError):
            chosen["plan_cache_status"] = None
    return chosen


def rfc3339_from_epoch_ms(value: Any) -> str | None:
    """Epoch milliseconds (native ZCode) -> RFC 3339 UTC instant, else None."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        moment = datetime.fromtimestamp(value / 1000.0, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None
    return moment.strftime("%Y-%m-%dT%H:%M:%S.") + f"{moment.microsecond // 1000:03d}Z"


def provider_facts(choice: dict[str, Any]) -> dict[str, Any]:
    """Secret-free provider facts for receipts (agentInfo._meta.zcode)."""
    return {
        "plan": "coding-plan",
        "providerId": choice["provider_id"],
        "providerLabel": choice["label"],
        "kind": choice["kind"],
        "baseURL": choice["base_url"],
        "credential": "desktop-registry-inline-memory",
        "modelIds": list(choice["model_ids"]),
        "defaultModelId": choice["default_model_id"],
        "planCacheStatus": choice.get("plan_cache_status"),
        "rejectedProviders": dict(choice.get("rejected") or {}),
    }


def build_runtime_model(choice: dict[str, Any], model_id: str) -> dict[str, Any]:
    """Protocol `runtimeModel` overlay (schema `$f`) for the chosen provider."""
    if model_id not in choice["model_ids"]:
        raise RuntimeError_(
            f"model {model_id} is not offered by {choice['provider_id']} "
            f"(available: {', '.join(choice['model_ids'])})"
        )
    digest = hashlib.sha256(
        "|".join([choice["provider_id"], choice["kind"], choice["base_url"],
                  ",".join(sorted(choice["model_ids"]))]).encode("utf-8")
    ).hexdigest()[:12]
    provider: dict[str, Any] = {
        "providerId": choice["provider_id"],
        "kind": choice["kind"],
        "apiFormat": choice["api_format"],
        "label": choice["label"],
        "source": choice["source"],
        "baseURL": choice["base_url"],
        "apiKey": {"source": "inline", "value": choice["_secret"]},
        "models": [dict(m) for m in choice["models"]],
    }
    if choice.get("api_key_required") is not None:
        provider["apiKeyRequired"] = choice["api_key_required"]
    return {
        "revision": f"{ADAPTER_NAME}:{digest}",
        "generatedAt": int(time.time() * 1000),
        "model": {"providerId": choice["provider_id"], "modelId": model_id},
        "provider": provider,
    }


# --------------------------------------------------------------------------
# ZCode Protocol client
# --------------------------------------------------------------------------


class ZCodeBackend:
    """Talks the private ZCode Protocol to an `app-server --stdio` child."""

    def __init__(self, entry: str, node: str, cwd: str, on_event, on_request):
        self.entry = entry
        self.node = node
        self.cwd = cwd
        self.on_event = on_event
        self.on_request = on_request
        self.proc: subprocess.Popen | None = None
        self._next_id = 0
        self._pending: dict[int, dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._writer_lock = threading.Lock()

    def start(self) -> None:
        self.proc = subprocess.Popen(
            [self.node, self.entry, "app-server", "--stdio"],
            cwd=self.cwd,
            env=build_child_env(self.entry),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            close_fds=True,
        )
        atexit.register(self.stop)
        threading.Thread(target=self._read_loop, daemon=True).start()

    def _read_loop(self) -> None:
        assert self.proc is not None and self.proc.stdout is not None
        for raw in self.proc.stdout:
            line = raw.decode("utf-8", "replace").strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except ValueError:
                continue
            self._dispatch(msg)
        # Backend died: fail every in-flight call rather than hang.
        with self._lock:
            pending = list(self._pending.values())
            self._pending.clear()
        for slot in pending:
            slot["error"] = {"code": -32000, "message": "zcode app-server exited"}
            slot["event"].set()

    def _dispatch(self, msg: dict[str, Any]) -> None:
        if "method" in msg and "id" in msg:
            self.on_request(msg)
            return
        if "method" in msg:
            self.on_event(msg)
            return
        rid = msg.get("id")
        with self._lock:
            slot = self._pending.pop(rid, None)
        if slot is None:
            return
        slot["result"] = msg.get("result")
        slot["error"] = msg.get("error")
        slot["event"].set()

    def _write(self, msg: dict[str, Any]) -> None:
        if self.proc is None or self.proc.stdin is None:
            raise RuntimeError_("zcode app-server is not running")
        data = json.dumps(msg).encode("utf-8") + b"\n"
        with self._writer_lock:
            self.proc.stdin.write(data)
            self.proc.stdin.flush()

    def call(self, method: str, params: dict[str, Any], timeout: float = 120.0) -> Any:
        with self._lock:
            self._next_id += 1
            rid = self._next_id
            slot: dict[str, Any] = {"event": threading.Event()}
            self._pending[rid] = slot
        self._write({"id": rid, "method": method, "params": params})
        if not slot["event"].wait(timeout):
            with self._lock:
                self._pending.pop(rid, None)
            raise RuntimeError_(f"zcode call timed out: {method}")
        if slot.get("error"):
            raise RuntimeError_(f"zcode error for {method}: {slot['error']}")
        return slot.get("result")

    def notify(self, method: str, params: dict[str, Any]) -> None:
        self._write({"method": method, "params": params})

    def respond(self, request_id: Any, result: Any) -> None:
        self._write({"id": request_id, "result": result})

    def stop(self) -> None:
        """Terminate the child process group and leave no stray process."""
        proc = self.proc
        self.proc = None
        if proc is None:
            return
        try:
            if proc.stdin:
                proc.stdin.close()
        except OSError:
            pass
        if proc.poll() is not None:
            return
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except (OSError, ProcessLookupError):
            try:
                proc.terminate()
            except OSError:
                pass
        try:
            proc.wait(timeout=5)
            return
        except (OSError, subprocess.TimeoutExpired):
            pass
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (OSError, ProcessLookupError):
            try:
                proc.kill()
            except OSError:
                pass
        try:
            proc.wait(timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            pass


# --------------------------------------------------------------------------
# Tool-kind mapping
# --------------------------------------------------------------------------

TOOL_KINDS = {
    "Bash": "execute",
    "BashOutput": "execute",
    "Read": "read",
    "Write": "edit",
    "Edit": "edit",
    "MultiEdit": "edit",
    "NotebookEdit": "edit",
    "Glob": "search",
    "Grep": "search",
    "WebFetch": "fetch",
    "WebSearch": "fetch",
}


def tool_kind(name: str) -> str:
    return TOOL_KINDS.get(name, "other")


TOOL_STATUS = {
    "scheduled": "pending",
    "started": "in_progress",
    "progress": "in_progress",
    "result": "completed",
    "error": "failed",
}

# Path-like keys actually observed on ZCode tool `input` (live 0.16.5 Read:
# `file_path`) plus the same names sibling file tools use. `command` is never
# copied: an execute card keeps kind/title/status only.
TOOL_INPUT_PATH_KEYS = (
    "file_path",
    "filePath",
    "path",
    "file",
    "notebook_path",
    "glob",
)
TOOL_INPUT_LINE_KEYS = ("line", "offset")
RAW_INPUT_PATH_CAP = 1024
RAW_INPUT_MAX_BYTES = 1536
RAW_INPUT_MAX_DEPTH = 1


def _cap_str(text: str, cap: int) -> str:
    return text if len(text) <= cap else text[:cap] + "…"


def extract_tool_evidence(source: Any) -> dict[str, Any] | None:
    """Copy only top-level path and line evidence.

    `command` and every other key are dropped. Depth is 1: a path buried in a
    nested dict is not lifted. Registered adapter secrets in a copied path
    string are still redacted.
    """
    if not isinstance(source, dict):
        return None
    # RAW_INPUT_MAX_DEPTH is 1: never walk nested dicts to find a path.
    evidence: dict[str, Any] = {}
    for key in TOOL_INPUT_PATH_KEYS:
        val = source.get(key)
        if isinstance(val, str) and val:
            evidence[key] = _cap_str(redact(val), RAW_INPUT_PATH_CAP)
    for key in TOOL_INPUT_LINE_KEYS:
        val = source.get(key)
        if isinstance(val, int) and not isinstance(val, bool):
            evidence[key] = val
            break
    if not evidence:
        return None
    encoded = json.dumps(evidence, ensure_ascii=False).encode("utf-8")
    if len(encoded) > RAW_INPUT_MAX_BYTES:
        for key in list(evidence):
            if key in TOOL_INPUT_PATH_KEYS and isinstance(evidence[key], str):
                evidence[key] = _cap_str(evidence[key], 96)
        encoded = json.dumps(evidence, ensure_ascii=False).encode("utf-8")
    if len(encoded) > RAW_INPUT_MAX_BYTES:
        return None
    return evidence


def locations_from_input(raw: Any) -> list[dict[str, Any]]:
    """Copy path fields that are already present. Never invent a path."""
    if not isinstance(raw, dict):
        return []
    line = None
    for key in TOOL_INPUT_LINE_KEYS:
        val = raw.get(key)
        if isinstance(val, int) and not isinstance(val, bool):
            line = val
            break
    locations: list[dict[str, Any]] = []
    for key in TOOL_INPUT_PATH_KEYS:
        val = raw.get(key)
        if isinstance(val, str) and val:
            locations.append({"path": val, "line": line})
    return locations


def attach_tool_input(
    update: dict[str, Any], payload: dict[str, Any], cached: dict[str, Any]
) -> None:
    source = payload.get("input")
    if source is None:
        source = cached.get("input")
    if source is None:
        return
    raw = extract_tool_evidence(source)
    if not raw:
        return
    update["rawInput"] = raw
    locations = locations_from_input(raw)
    if locations:
        update["locations"] = locations


# --------------------------------------------------------------------------
# ACP agent
# --------------------------------------------------------------------------


class Session:
    def __init__(self, acp_id: str, cwd: str, mode: str):
        self.acp_id = acp_id
        self.cwd = cwd
        self.mode = mode
        self.model_id: str | None = None
        self.provider_id: str | None = None
        self.thought: str | None = None
        self.backend_id: str | None = None
        self.subscribed = False
        self.hydrated = False
        self.turn_request_id: Any = None
        self.cancelled = False
        self.tools: dict[str, dict[str, Any]] = {}


class ZCodeAcpAgent:
    def __init__(self, entry: str, node: str, default_cwd: str, default_mode: str):
        self.provider: dict[str, Any] | None = None
        self.provider_error: str | None = None
        self.entry = entry
        self.node = node
        self.default_cwd = default_cwd
        self.default_mode = default_mode
        self.sessions: dict[str, Session] = {}
        self.by_backend: dict[str, Session] = {}
        self.backend: ZCodeBackend | None = None
        self.lock = threading.Lock()
        self._next_out_id = 0
        self._out_pending: dict[Any, dict[str, Any]] = {}
        self._session_seq = 0
        # ZCode 3.12+ account-provider registry state (Issue #79). `None` until
        # the first backend session decides which protocol the child speaks.
        self.account: dict[str, Any] | None = None
        self.account_pushed = False
        self.legacy_overlay = False

    # -- ACP wire ---------------------------------------------------------

    def send(self, msg: dict[str, Any]) -> None:
        # Single outbound boundary: results, errors, session/update
        # notifications and client requests all pass here. Backend event
        # payloads (model.streaming text, tool output, turn.failed messages)
        # are untrusted and may echo the inline credential, so the whole
        # message is redacted before it reaches the ACP channel.
        data = json.dumps(redact(msg)).encode("utf-8") + b"\n"
        with STDOUT_LOCK:
            sys.stdout.buffer.write(data)
            sys.stdout.buffer.flush()

    def respond(self, rid: Any, result: Any = None, error: Any = None) -> None:
        msg: dict[str, Any] = {"jsonrpc": "2.0", "id": rid}
        if error is not None:
            msg["error"] = error  # redacted with the whole message in send()
        else:
            msg["result"] = result
        self.send(msg)

    def notify(self, method: str, params: dict[str, Any]) -> None:
        self.send({"jsonrpc": "2.0", "method": method, "params": params})

    def update(self, session: Session, update: dict[str, Any]) -> None:
        self.notify("session/update", {"sessionId": session.acp_id, "update": update})

    def request_client(self, method: str, params: dict[str, Any], timeout: float = 600.0):
        """Send an ACP request to the client and block for its response."""
        with self.lock:
            self._next_out_id += 1
            rid = f"zc-{self._next_out_id}"
            slot: dict[str, Any] = {"event": threading.Event()}
            self._out_pending[rid] = slot
        self.send({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
        if not slot["event"].wait(timeout):
            with self.lock:
                self._out_pending.pop(rid, None)
            return None
        return slot.get("result")

    # -- backend plumbing -------------------------------------------------

    def ensure_backend(self) -> ZCodeBackend:
        if self.backend is None:
            self.backend = ZCodeBackend(
                self.entry, self.node, self.default_cwd, self.on_backend_event,
                self.on_backend_request,
            )
            self.backend.start()
        return self.backend

    def resolve_account(self) -> dict[str, Any] | None:
        """Account-provider snapshot for this plan, or None on the old path."""
        if self.account is None:
            builtin = resolve_builtin_provider_config(self.entry)
            if not builtin:
                return None
            try:
                release = read_builtin_release(builtin)
            except (RuntimeError_, OSError, ValueError) as exc:
                log(f"bundled provider table unusable ({exc.__class__.__name__}); "
                    "staying on the pre-3.12 path")
                return None
            self.account = build_account_config(
                self.resolve_provider(), release, builtin) or {}
        return self.account or None

    def push_account_config(self, backend: ZCodeBackend) -> None:
        """Register the Coding Plan with the backend's provider registry.

        Without this the 3.12+ registry is empty and the first turn fails with
        `Select a model before continuing`. A pre-3.12 backend does not know the
        method and answers -32601; that is a benign no-op, not an error.
        """
        if self.account_pushed:
            return
        account = self.resolve_account()
        if account is None:
            self.account_pushed = True
            return
        try:
            backend.call("provider/updateAccountConfig", account["params"])
        except RuntimeError_ as exc:
            if "-32601" in str(exc) or "not found" in str(exc).lower():
                log("backend has no provider/updateAccountConfig (pre-3.12); continuing")
            else:
                raise
        self.account_pushed = True

    def resolve_provider(self) -> dict[str, Any]:
        """Read-only desktop registry lookup, cached; raises when ineligible."""
        if self.provider is not None:
            return self.provider
        if self.provider_error is not None:
            raise RuntimeError_(self.provider_error)
        try:
            self.provider = select_coding_plan_provider()
        except RuntimeError_ as exc:
            self.provider_error = str(exc)
            raise
        return self.provider

    def overlay_for(self, session: Session, model_id: str | None = None) -> dict[str, Any]:
        choice = self.resolve_provider()
        wanted = model_id or session.model_id or choice["default_model_id"]
        # build_runtime_model fails closed on a model the provider does not
        # offer; nothing is substituted here.
        return build_runtime_model(choice, wanted)

    def materialize(self, session: Session) -> str:
        """Create and subscribe the backend session on first real use."""
        # Fail closed before spawning anything when no Coding Plan is eligible.
        self.resolve_provider()
        backend = self.ensure_backend()
        if session.backend_id is None:
            workspace = {"workspacePath": session.cwd, "workspaceKey": session.cwd}
            self.push_account_config(backend)
            result = self.create_backend_session(session, backend, workspace)
            backend_id = (result.get("session") or {}).get("sessionId")
            if not backend_id:
                raise RuntimeError_("zcode session/create returned no sessionId")
            session.backend_id = backend_id
            with self.lock:
                self.by_backend[backend_id] = session
            account = self.resolve_account()
            if account is not None and not self.legacy_overlay:
                self.select_account_model(session, backend, account)
        if not session.subscribed:
            backend.call(
                "session/subscribe",
                {
                    "sessionId": session.backend_id,
                    "deliveryKind": "desktop-continuous",
                    "includeSnapshot": False,
                    "afterSeq": 0,
                },
            )
            session.subscribed = True
            self.emit_session_identity(session)
        self.hydrate_settings(session)
        return session.backend_id

    def create_backend_session(
        self, session: Session, backend: ZCodeBackend, workspace: dict[str, Any],
    ) -> dict[str, Any]:
        """Create the backend session under whichever protocol the child speaks.

        3.12+ takes no model on `session/create` (`runtimeModel` is gone from the
        build entirely) and selects afterwards through `session/setModel`. A
        pre-3.12 backend instead refuses a create that carries no model config,
        which is what selects the legacy overlay -- the CLI version string cannot
        tell the two apart, so the protocol is decided by that error, not a gate.
        """
        params = {"workspace": workspace, "mode": session.mode}
        if self.resolve_account() is not None and not self.legacy_overlay:
            try:
                return backend.call("session/create", params) or {}
            except RuntimeError_ as exc:
                if "Model config is missing" not in str(exc):
                    raise
                log("backend requires the pre-3.12 model overlay on session/create")
                self.legacy_overlay = True
        overlay = self.overlay_for(session)
        return backend.call(
            "session/create", {**params, "runtimeModel": overlay}) or {}

    def select_account_model(
        self, session: Session, backend: ZCodeBackend, account: dict[str, Any],
    ) -> None:
        """Select the plan model on the 3.12+ account provider.

        `persistAsWorkspaceLastUsed` stays false so a Runner turn never edits the
        user's workspace defaults.
        """
        model_id = session.model_id or account["model_ids"][0]
        if model_id not in account["model_ids"]:
            raise RuntimeError_(
                f"model {model_id} is not offered by {account['account_id']} "
                f"(available: {', '.join(account['model_ids'])})"
            )
        model: dict[str, Any] = {
            "providerId": account["account_id"], "modelId": model_id,
        }
        # 3.12+ refuses a Coding Plan selection with no explicit reasoning level
        # ("Reasoning level is required for <provider>/<model>"). Honour the
        # session's thought level when the model actually offers it.
        levels = account_reasoning_levels(account.get("release") or {}, model_id)
        if levels:
            wanted = session.thought if session.thought in levels else levels[0]
            model["options"] = {"reasoningLevel": wanted}
        backend.call("session/setModel", {
            "sessionId": session.backend_id,
            "model": model,
            "persistAsWorkspaceLastUsed": False,
        })
        session.model_id = model_id

    def runtime_headers_answer(self, params: dict[str, Any]) -> dict[str, Any]:
        """Answer the per-model-request provider auth callback (3.12+).

        The plan credential is handed to the backend in memory only: it is never
        logged, never echoed into ACP output and never written to disk. The
        response union is strict and has no not-implemented branch, so a wrong
        shape fails the turn with -32031.
        """
        account = self.resolve_account()
        wanted = (params.get("providerId")
                  or (params.get("modelSelection") or {}).get("providerId"))
        if account is None or wanted != account["account_id"]:
            return {
                "headersApplied": False,
                "errorMessage": f"no authorized Coding Plan provider for {wanted}",
            }
        try:
            choice = self.resolve_provider()
        except RuntimeError_ as exc:
            return {"headersApplied": False, "errorMessage": redact(str(exc))}
        return {"headersApplied": True, "requestAuth": {"apiKey": choice["_secret"]}}

    def emit_session_identity(self, session: Session) -> None:
        """Report the two wire-level identities once the backend session exists:
        the ACP session id this client holds and the native ZCode session id
        (``sess_*``) the backend created for it (Issue #62). The Runner session
        name is already on every Runner receipt, so the three layers stay
        separately trackable. Credential-free structured facts; the holder
        records the update in its event log and every ACP client sees it.
        """
        if session.backend_id is None:
            return
        self.update(session, {
            "sessionUpdate": "native_session_identity",
            "acpSessionId": session.acp_id,
            "nativeSessionId": session.backend_id,
        })

    def reregister_provider(self, session: Session) -> None:
        """After a faithful resume the fresh app-server has no provider
        catalog, so the persisted model reports ZCODE_RUNTIME_MODEL_UNAVAILABLE
        on the next send. Re-register the same Coding Plan provider through
        session/setModel with the session's own persisted model. A persisted
        model outside that provider fails closed; nothing is substituted.
        """
        if self.backend is None or session.backend_id is None:
            return
        choice = self.resolve_provider()
        if not session.model_id or not session.provider_id:
            raise RuntimeError_(
                "resumed session reports no persisted model (session/read failed); "
                "refusing to substitute the provider default"
            )
        provider_id = session.provider_id
        model_id = session.model_id
        if provider_id != choice["provider_id"] or model_id not in choice["model_ids"]:
            raise RuntimeError_(
                f"persisted session model {provider_id}\\{model_id} is not offered by the "
                f"enabled GLM Coding Plan provider {choice['provider_id']}; refusing to "
                "substitute (select a model explicitly)"
            )
        self.backend.call("session/setModel", {
            "sessionId": session.backend_id,
            "model": {"providerId": provider_id, "modelId": model_id},
            "runtimeModel": build_runtime_model(choice, model_id),
            "persistAsWorkspaceLastUsed": False,
        })
        session.provider_id = provider_id
        session.model_id = model_id

    def hydrate_settings(self, session: Session) -> None:
        """Read native mode/model/thought. Never invent a substitute model."""
        if session.hydrated or session.backend_id is None or self.backend is None:
            return
        try:
            state = self.backend.call("session/read", {"sessionId": session.backend_id}) or {}
        except RuntimeError_:
            session.hydrated = True
            return
        settings = state.get("settings") or {}
        mode = (settings.get("mode") or {}).get("current")
        if isinstance(mode, str) and mode:
            session.mode = mode
        model = (settings.get("model") or {}).get("current") or {}
        if isinstance(model, dict):
            model_id = model.get("modelId")
            if isinstance(model_id, str) and model_id:
                session.model_id = model_id
            provider_id = model.get("providerId")
            if isinstance(provider_id, str) and provider_id:
                session.provider_id = provider_id
        thought = (settings.get("thoughtLevel") or {}).get("current")
        if isinstance(thought, str) and thought:
            session.thought = thought
        session.hydrated = True
        self.update(session, {
            "sessionUpdate": "config_option_update",
            "configOptions": self.config_options(session),
        })
        self.update(session, {
            "sessionUpdate": "current_mode_update",
            "currentModeId": session.mode,
        })

    def config_options(self, session: Session) -> list[dict[str, Any]]:
        mode_option: dict[str, Any] = {
            "id": "mode",
            "name": "Mode",
            "type": "select",
            "currentValue": session.mode,
            "options": [{"value": value, "name": name} for value, name in MODE_CHOICES],
        }
        thought_option: dict[str, Any] = {
            "id": "thoughtLevel",
            "name": "Thought level",
            "type": "select",
            "options": [{"value": value, "name": name} for value, name in THOUGHT_CHOICES],
        }
        if session.thought:
            thought_option["currentValue"] = session.thought
        model_option: dict[str, Any] = {
            "id": "model",
            "name": "Model",
            "type": "select",
            "options": [],
        }
        if self.provider is not None:
            model_option["options"] = [
                {"value": f"{self.provider['provider_id']}\\{model_id}",
                 "name": f"{model_id} ({self.provider['label']})"}
                for model_id in self.provider["model_ids"]
            ]
        if session.model_id:
            model_value = (
                f"{session.provider_id}\\{session.model_id}"
                if session.provider_id else session.model_id
            )
            model_option["currentValue"] = model_value
            if not any(o["value"] == model_value for o in model_option["options"]):
                model_option["options"].append({"value": model_value, "name": session.model_id})
        return [mode_option, model_option, thought_option]

    @staticmethod
    def parse_model_value(value: str) -> dict[str, str]:
        """ACP config value -> backend model ref. No config.json lookup."""
        if "\\" in value:
            provider_id, model_id = value.split("\\", 1)
            if provider_id and model_id:
                return {"providerId": provider_id, "modelId": model_id}
        return {"modelId": value}

    # -- backend -> ACP ---------------------------------------------------

    def on_backend_event(self, msg: dict[str, Any]) -> None:
        if msg.get("method") != "session/event":
            return
        params = msg.get("params") or {}
        with self.lock:
            session = self.by_backend.get(params.get("sessionId"))
        if session is None:
            return
        etype = params.get("type")
        payload = params.get("payload") or {}
        try:
            self.translate_event(session, etype, payload)
        except Exception as exc:  # never let one event kill the stream
            log(f"event translation failed ({etype}): {exc}")

    def translate_event(self, session: Session, etype: str, payload: dict[str, Any]) -> None:
        if etype == "model.streaming":
            kind = payload.get("kind")
            delta = payload.get("delta") or ""
            if kind == "text_delta" and delta:
                self.update(session, {
                    "sessionUpdate": "agent_message_chunk",
                    "content": {"type": "text", "text": delta},
                })
            elif kind == "reasoning_delta" and delta:
                self.update(session, {
                    "sessionUpdate": "agent_thought_chunk",
                    "content": {"type": "text", "text": delta},
                })
            elif kind == "tool_call":
                call_id = payload.get("toolCallId")
                if call_id:
                    cached = session.tools.setdefault(call_id, {})
                    name = payload.get("toolName") or ""
                    if name:
                        cached["toolName"] = name
                    if "input" in payload:
                        cached["input"] = payload.get("input")
            return

        if etype == "tool.updated":
            self.translate_tool(session, payload)
            return

        if etype == "session.updated":
            usage = payload.get("usage")
            if usage:
                self.update(session, {"sessionUpdate": "usage_update", "usage": usage})
            return

        if etype == "turn.completed":
            usage = payload.get("usage")
            if usage:
                self.update(session, {"sessionUpdate": "usage_update", "usage": usage})
            stop = "cancelled" if session.cancelled else "end_turn"
            self.finish_turn(session, stop, usage)
            return

        if etype == "turn.failed":
            error = payload.get("error") or {}
            self.update(session, {
                "sessionUpdate": "agent_message_chunk",
                "content": {
                    "type": "text",
                    "text": f"[zcode turn failed] {error.get('message', 'unknown error')}",
                },
            })
            self.finish_turn(session, "cancelled" if session.cancelled else "refusal", None)
            return

        if etype == "turn.terminal":
            self.finish_turn(session, "cancelled" if session.cancelled else "end_turn", None)
            return

    def translate_tool(self, session: Session, payload: dict[str, Any]) -> None:
        kind = payload.get("kind")
        if kind == "batch":
            for item in payload.get("items") or []:
                self.translate_tool(session, item)
            return
        call_id = payload.get("toolCallId")
        if not call_id:
            return
        cached = session.tools.setdefault(call_id, {})
        name = payload.get("toolName") or cached.get("toolName") or ""
        if name:
            cached["toolName"] = name
        if "input" in payload:
            cached["input"] = payload.get("input")
        update: dict[str, Any] = {
            "sessionUpdate": "tool_call",
            "toolCallId": call_id,
            "title": name or call_id,
            "kind": tool_kind(name),
            "status": TOOL_STATUS.get(kind, "in_progress"),
        }
        content = []
        for field in ("stdoutTail", "stderrTail", "output", "result"):
            value = payload.get(field)
            if isinstance(value, str) and value:
                content.append({"type": "text", "text": value})
        if kind == "error":
            message = payload.get("message") or (payload.get("error") or {}).get("message")
            if message:
                content.append({"type": "text", "text": str(message)})
        if content:
            update["content"] = content
        attach_tool_input(update, payload, cached)
        self.update(session, update)

    def finish_turn(self, session: Session, stop: str, usage: Any) -> None:
        with self.lock:
            rid = session.turn_request_id
            session.turn_request_id = None
        if rid is None:
            return
        result: dict[str, Any] = {"stopReason": stop}
        if usage:
            result["usage"] = usage
        session.cancelled = False
        self.respond(rid, result)

    def on_backend_request(self, msg: dict[str, Any]) -> None:
        """Backend asks us something: bridge it to the ACP client."""
        threading.Thread(target=self._handle_backend_request, args=(msg,), daemon=True).start()

    def _handle_backend_request(self, msg: dict[str, Any]) -> None:
        method = msg.get("method")
        params = msg.get("params") or {}
        rid = msg.get("id")
        backend = self.backend
        if backend is None:
            return
        # CLI 0.16.5 asks this during session/create, before the backend id
        # is registered. Answer with protocol defaults; never read Settings.
        if method == "session/requestRuntimePreferences":
            backend.respond(rid, {
                "nativeSearchEnhancementsEnabled": True,
                "memoryEnabled": False,
                "askUserQuestionAutoResolutionEnabled": True,
                "modelContextBudgetStrategy": "preflight-v1",
            })
            return
        # Never supply MCP credential/header values. Native login owns that auth.
        if method == "interaction/requestOfficialMcpAuthHeaders":
            backend.respond(rid, {})
            return
        # 3.12+ asks for provider auth before EVERY model request on an account
        # provider, and `{}` does not satisfy the strict response union.
        if method == "interaction/requestProviderRuntimeHeaders":
            backend.respond(rid, self.runtime_headers_answer(params))
            return
        with self.lock:
            session = self.by_backend.get(params.get("sessionId"))
        if session is None:
            if method == "interaction/requestPermission":
                backend.respond(rid, {"optionId": "deny"})
            else:
                backend.respond(rid, {})
            return

        if method == "interaction/requestPermission":
            options = params.get("options") or [
                {"optionId": "allow", "kind": "allow_once", "name": "Allow once"},
                {"optionId": "deny", "kind": "deny_once", "name": "Deny"},
            ]
            tool_call: dict[str, Any] = {
                "toolCallId": params.get("toolCallId"),
                "title": params.get("toolName") or "tool",
                "kind": tool_kind(params.get("toolName") or ""),
                "status": "pending",
            }
            attach_tool_input(tool_call, params, {})
            answer = self.request_client("session/request_permission", {
                "sessionId": session.acp_id,
                "toolCall": tool_call,
                "options": options,
            })
            backend.respond(rid, self._permission_answer(answer, options))
            return

        if method == "interaction/requestUserInput":
            schema = params.get("schema") or {}
            if schema.get("interaction") == "plan_approval":
                plan_text = (params.get("input") or {}).get("plan") or ""
                self.update(session, {
                    "sessionUpdate": "plan",
                    "entries": [{"content": plan_text, "priority": "medium", "status": "pending"}],
                })
                options = [
                    {"optionId": "approve", "kind": "allow_once", "name": "Approve plan"},
                    {"optionId": "reject", "kind": "reject_once", "name": "Reject plan"},
                ]
                answer = self.request_client("session/request_permission", {
                    "sessionId": session.acp_id,
                    "toolCall": {
                        "toolCallId": params.get("toolCallId"),
                        "title": "Plan approval",
                        "kind": "other",
                        "status": "pending",
                    },
                    "options": options,
                })
                chosen = self._permission_answer(answer, options).get("optionId")
                backend.respond(rid, {"approved": chosen == "approve"})
                return
            # AskUserQuestion: surface the questions, let the client choose.
            questions = params.get("questions") or []
            options = []
            for question in questions:
                for opt in question.get("options") or []:
                    options.append({
                        "optionId": str(opt.get("value")),
                        "kind": "allow_once",
                        "name": str(opt.get("label")),
                    })
            if not options:
                backend.respond(rid, {"cancelled": True})
                return
            answer = self.request_client("session/request_permission", {
                "sessionId": session.acp_id,
                "toolCall": {
                    "toolCallId": params.get("toolCallId"),
                    "title": (questions[0].get("question") if questions else "Question") or "Question",
                    "kind": "other",
                    "status": "pending",
                },
                "options": options,
            })
            chosen = self._permission_answer(answer, options).get("optionId")
            backend.respond(rid, {"answers": [chosen]} if chosen else {"cancelled": True})
            return

        backend.respond(rid, {})

    @staticmethod
    def _permission_answer(answer: Any, options: list[dict[str, Any]]) -> dict[str, Any]:
        """Normalise an ACP permission reply; anything unclear denies."""
        deny = {"optionId": next(
            (o["optionId"] for o in options if str(o.get("kind", "")).startswith(("deny", "reject"))),
            "deny",
        )}
        if not isinstance(answer, dict):
            return deny
        outcome = answer.get("outcome")
        if isinstance(outcome, dict):
            if outcome.get("outcome") == "selected" and outcome.get("optionId"):
                return {"optionId": outcome["optionId"]}
            return deny
        if answer.get("optionId"):
            return {"optionId": answer["optionId"]}
        return deny

    # -- ACP method handlers ---------------------------------------------

    def on_initialize(self, rid: Any, params: dict[str, Any]) -> None:
        self.respond(rid, {
            "protocolVersion": 1,
            "agentCapabilities": {
                "loadSession": True,
                "sessionCapabilities": {"list": True, "resume": True, "close": True},
                "promptCapabilities": {"embeddedContext": True},
            },
            "authMethods": [],
            "agentInfo": {
                "name": ADAPTER_NAME,
                "version": ADAPTER_VERSION,
                "_meta": {"zcode": self.provider_meta()},
            },
        })

    def provider_meta(self) -> dict[str, Any]:
        """Secret-free provider/billing facts; read-only registry lookup."""
        try:
            return provider_facts(self.resolve_provider())
        except RuntimeError_ as exc:
            return {"plan": "unavailable", "reason": str(exc)}

    def on_session_new(self, rid: Any, params: dict[str, Any]) -> None:
        cwd = params.get("cwd") or self.default_cwd
        with self.lock:
            self._session_seq += 1
            acp_id = f"zcode-{self._session_seq}"
            session = Session(acp_id, cwd, self.default_mode)
            self.sessions[acp_id] = session
        self.respond(rid, {
            "sessionId": acp_id,
            "configOptions": self.config_options(session),
        })

    def on_session_load(self, rid: Any, params: dict[str, Any]) -> None:
        """Adopt an existing backend session id (ACP load/resume)."""
        acp_id = params.get("sessionId") or ""
        cwd = params.get("cwd") or self.default_cwd
        with self.lock:
            session = self.sessions.get(acp_id)
        if session is None:
            session = Session(acp_id, cwd, self.default_mode)
            if acp_id.startswith("sess_"):
                try:
                    self._resume_backend_session(session)
                except RuntimeError_:
                    # A failed load must not leave a half-registered session
                    # that a later prompt would silently re-create.
                    with self.lock:
                        self.sessions.pop(acp_id, None)
                        self.by_backend.pop(acp_id, None)
                    raise
            with self.lock:
                self.sessions[acp_id] = session
        # The load result carries the adopted identity (``sessionId``) so the
        # holder's record and every receipt track which session was loaded;
        # for a native ``sess_*`` load this ties the Runner session to the
        # resumable native id (Issue #62).
        self.respond(rid, {
            "sessionId": session.acp_id,
            "configOptions": self.config_options(session),
        })

    def _resume_backend_session(self, session: Session) -> None:
        acp_id = session.acp_id
        cwd = session.cwd
        # Fail closed before spawning when no Coding Plan is eligible.
        overlay = self.overlay_for(session)
        backend = self.ensure_backend()
        workspace = {"workspacePath": cwd, "workspaceKey": cwd}
        try:
            # Faithful resume keeps the session's own persisted model.
            backend.call("session/resume", {"sessionId": acp_id, "workspace": workspace})
        except RuntimeError_:
            # The overlay supplies the same Coding Plan provider in memory for
            # a backend that refuses to resume without a provider catalog.
            backend.call("session/resume", {
                "sessionId": acp_id, "workspace": workspace, "runtimeModel": overlay,
            })
        session.backend_id = acp_id
        with self.lock:
            self.sessions[acp_id] = session
            self.by_backend[acp_id] = session
        backend.call("session/subscribe", {
            "sessionId": acp_id,
            "deliveryKind": "desktop-continuous",
            "includeSnapshot": False,
            "afterSeq": 0,
        })
        session.subscribed = True
        self.emit_session_identity(session)
        self.hydrate_settings(session)
        self.reregister_provider(session)

    def on_session_list(self, rid: Any, params: dict[str, Any]) -> None:
        backend = self.ensure_backend()
        workspace = {"workspacePath": self.default_cwd, "workspaceKey": self.default_cwd}
        result = backend.call("session/list", {"workspace": workspace}) or {}
        sessions = []
        for item in result.get("sessions") or []:
            entry: dict[str, Any] = {
                "sessionId": item.get("sessionId"),
                "title": item.get("title") or "",
            }
            # Native timestamps are epoch milliseconds; ACP clients (and the
            # Runner's --continue picker) expect RFC 3339 instants.
            for key in ("updatedAt", "createdAt"):
                instant = rfc3339_from_epoch_ms(item.get(key))
                if instant is not None:
                    entry[key] = instant
            for key in ("status", "mode"):
                if item.get(key) is not None:
                    entry[key] = item[key]
            sessions.append(entry)
        self.respond(rid, {"sessions": sessions})

    def on_session_prompt(self, rid: Any, params: dict[str, Any]) -> None:
        acp_id = params.get("sessionId") or ""
        with self.lock:
            session = self.sessions.get(acp_id)
        if session is None:
            self.respond(rid, error={"code": -32602, "message": f"unknown session {acp_id}"})
            return
        text = self._prompt_text(params.get("prompt"))
        try:
            backend_id = self.materialize(session)
        except RuntimeError_ as exc:
            self.respond(rid, error={"code": -32000, "message": str(exc)})
            return
        with self.lock:
            # Issue #65: one turn owns one request id. A second prompt that
            # landed while a turn is running used to overwrite this field, which
            # orphaned the original request forever and handed its completion to
            # the newcomer. ZCode 0.16.5 rejects a concurrent `session/send`
            # itself (-32010); refuse here too, so the original turn keeps its
            # response attribution no matter which client wrote.
            if session.turn_request_id is not None:
                active = session.turn_request_id
                self.respond(rid, error={
                    "code": -32010,
                    "message": "a prompt is already running for this session",
                    "data": {"activeRequestId": active},
                })
                return
            session.turn_request_id = rid
            session.cancelled = False
        try:
            self.ensure_backend().call(
                "session/send", {"sessionId": backend_id, "content": text}
            )
        except RuntimeError_ as exc:
            with self.lock:
                session.turn_request_id = None
            self.respond(rid, error={"code": -32000, "message": str(exc)})

    @staticmethod
    def _prompt_text(prompt: Any) -> str:
        if isinstance(prompt, str):
            return prompt
        parts = []
        for block in prompt or []:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text") or "")
        return "\n".join(p for p in parts if p)

    def on_session_cancel(self, rid: Any, params: dict[str, Any]) -> None:
        acp_id = params.get("sessionId") or ""
        with self.lock:
            session = self.sessions.get(acp_id)
        if session is not None and session.backend_id:
            session.cancelled = True
            try:
                # A request (with id) bypasses the app-server's processing
                # queue (CLI 0.16.5 fast-paths session/stop only when it has
                # an id); a bare notification waits behind the running turn.
                # The acknowledgement is immediate, but the native runtime
                # aborts at the turn boundary: an in-flight model response
                # streams to completion before the turn reports cancelled.
                self.ensure_backend().call(
                    "session/stop", {"sessionId": session.backend_id}, timeout=15.0
                )
            except RuntimeError_ as exc:
                log(f"cancel failed: {exc}")
        if rid is not None:
            self.respond(rid, {})

    def on_session_close(self, rid: Any, params: dict[str, Any]) -> None:
        acp_id = params.get("sessionId") or ""
        with self.lock:
            session = self.sessions.pop(acp_id, None)
            if session is not None and session.backend_id:
                self.by_backend.pop(session.backend_id, None)
        if session is not None and session.backend_id:
            try:
                self.ensure_backend().call("session/close", {"sessionId": session.backend_id})
            except RuntimeError_ as exc:
                log(f"close failed: {exc}")
        self.respond(rid, {})

    def on_set_mode(self, rid: Any, params: dict[str, Any]) -> None:
        acp_id = params.get("sessionId") or ""
        mode = params.get("modeId") or params.get("mode") or ""
        with self.lock:
            session = self.sessions.get(acp_id)
        if session is None:
            self.respond(rid, error={"code": -32602, "message": f"unknown session {acp_id}"})
            return
        session.mode = mode or session.mode
        if session.backend_id or mode:
            backend_id = self.materialize(session)
            self.ensure_backend().call(
                "session/setMode", {"sessionId": backend_id, "mode": session.mode}
            )
        self.update(session, {"sessionUpdate": "current_mode_update", "currentModeId": session.mode})
        self.update(session, {
            "sessionUpdate": "config_option_update",
            "configOptions": self.config_options(session),
        })
        self.respond(rid, {"configOptions": self.config_options(session)})

    def on_set_config_option(self, rid: Any, params: dict[str, Any]) -> None:
        acp_id = params.get("sessionId") or ""
        config_id = params.get("configId") or params.get("config_id") or ""
        value = params.get("value")
        with self.lock:
            session = self.sessions.get(acp_id)
        if session is None:
            self.respond(rid, error={"code": -32602, "message": f"unknown session {acp_id}"})
            return
        if value is None or not isinstance(value, (str, int, float, bool)):
            self.respond(rid, error={"code": -32602, "message": f"invalid value for {config_id}"})
            return
        text = str(value)
        try:
            backend_id = self.materialize(session)
            if config_id == "mode":
                session.mode = text
                self.ensure_backend().call(
                    "session/setMode", {"sessionId": backend_id, "mode": session.mode}
                )
                self.update(session, {
                    "sessionUpdate": "current_mode_update",
                    "currentModeId": session.mode,
                })
            elif config_id == "model":
                model = self.parse_model_value(text)
                choice = self.resolve_provider()
                provider_id = model.get("providerId") or choice["provider_id"]
                if provider_id != choice["provider_id"]:
                    # Never switch billing paths silently: only the eligible
                    # Coding Plan provider may be selected.
                    self.respond(rid, error={
                        "code": -32602,
                        "message": (
                            f"provider {provider_id} is not the enabled GLM Coding Plan "
                            f"provider {choice['provider_id']}; refusing"
                        ),
                    })
                    return
                model_id = model.get("modelId") or ""
                if model_id not in choice["model_ids"]:
                    self.respond(rid, error={
                        "code": -32602,
                        "message": (
                            f"model {model_id} is not offered by {provider_id} "
                            f"(available: {', '.join(choice['model_ids'])})"
                        ),
                    })
                    return
                account = self.resolve_account()
                if account is not None and not self.legacy_overlay:
                    # 3.12+ has no `runtimeModel` key and requires an explicit
                    # reasoning level, so a mid-session switch takes the same
                    # account path as the initial selection (Issue #79).
                    if model_id not in account["model_ids"]:
                        self.respond(rid, error={
                            "code": -32602,
                            "message": (
                                f"model {model_id} is not offered by "
                                f"{account['account_id']} "
                                f"(available: {', '.join(account['model_ids'])})"
                            ),
                        })
                        return
                    session.model_id = model_id
                    self.select_account_model(session, self.ensure_backend(), account)
                else:
                    # The overlay re-registers the same provider in the backend's
                    # workspace catalog (desktop parity); runtime-only, not persisted.
                    self.ensure_backend().call(
                        "session/setModel",
                        {
                            "sessionId": backend_id,
                            "model": {"providerId": provider_id, "modelId": model_id},
                            "runtimeModel": build_runtime_model(choice, model_id),
                            "persistAsWorkspaceLastUsed": False,
                        },
                    )
                    session.model_id = model_id
                session.provider_id = provider_id
            elif config_id in ("thought", "thoughtLevel", "thought_level"):
                session.thought = text
                self.ensure_backend().call(
                    "session/setThoughtLevel",
                    {"sessionId": backend_id, "thoughtLevel": session.thought},
                )
            else:
                self.respond(
                    rid,
                    error={"code": -32602, "message": f"unsupported config option {config_id}"},
                )
                return
        except RuntimeError_ as exc:
            self.respond(rid, error={"code": -32000, "message": str(exc)})
            return
        options = self.config_options(session)
        self.update(session, {"sessionUpdate": "config_option_update", "configOptions": options})
        self.respond(rid, {"configOptions": options})

    # -- main loop --------------------------------------------------------

    def handle(self, msg: dict[str, Any]) -> None:
        method = msg.get("method")
        rid = msg.get("id")

        if method is None and rid is not None:
            with self.lock:
                slot = self._out_pending.pop(rid, None)
            if slot is not None:
                slot["result"] = msg.get("result")
                slot["event"].set()
            return

        handlers = {
            "initialize": self.on_initialize,
            "session/new": self.on_session_new,
            "session/load": self.on_session_load,
            "session/resume": self.on_session_load,
            "session/list": self.on_session_list,
            "session/prompt": self.on_session_prompt,
            "session/cancel": self.on_session_cancel,
            "session/close": self.on_session_close,
            "session/set_mode": self.on_set_mode,
            "session/setMode": self.on_set_mode,
            "session/set_config_option": self.on_set_config_option,
        }
        if method == "authenticate":
            # The native runtime owns its own login; nothing to do here.
            self.respond(rid, {})
            return
        handler = handlers.get(method or "")
        if handler is None:
            if rid is not None:
                self.respond(rid, error={"code": -32601, "message": f"method not found: {method}"})
            return
        try:
            handler(rid, msg.get("params") or {})
        except RuntimeError_ as exc:
            if rid is not None:
                self.respond(rid, error={"code": -32000, "message": str(exc)})
        except Exception as exc:  # pragma: no cover - defensive
            if rid is not None:
                self.respond(rid, error={"code": -32603, "message": f"internal error: {exc}"})

    def run(self) -> int:
        for raw in sys.stdin.buffer:
            line = raw.decode("utf-8", "replace").strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except ValueError:
                continue
            if isinstance(msg, dict):
                self.handle(msg)
        if self.backend is not None:
            self.backend.stop()
        return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="ACP adapter for the native ZCode app-server")
    parser.add_argument("--zcode-entry", default=None, help="absolute path to zcode.cjs")
    parser.add_argument("--zcode-node", default=None, help="absolute path to the node/Electron runtime")
    parser.add_argument("--cwd", default=None, help="workspace path for ZCode sessions")
    parser.add_argument("--mode", default="yolo", help="ZCode permission mode")
    args = parser.parse_args(argv)

    try:
        entry, node = resolve_runtime(args.zcode_entry, args.zcode_node)
    except RuntimeError_ as exc:
        log(f"fail-closed: {exc}")
        return 2

    cwd = args.cwd or os.getcwd()
    if not os.path.isdir(cwd):
        log(f"fail-closed: workspace is not a directory: {cwd}")
        return 2

    agent = ZCodeAcpAgent(entry, node, cwd, args.mode)
    try:
        return agent.run()
    except KeyboardInterrupt:
        if agent.backend is not None:
            agent.backend.stop()
        return 130


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
