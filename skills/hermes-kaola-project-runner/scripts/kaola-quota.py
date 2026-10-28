#!/usr/bin/env python3
"""Quota package catalog and model→package resolution (Issue #148).

Platform manifests store two JSON documents as ordinary JSON strings
(``parse_manifest`` accepts only strings):

``quota_packages``
    A JSON array. Each object has ``id`` (``^[a-z][a-z0-9_-]*$``), ``name``
    (non-empty string), optional ``binds_models`` (bool, default true),
    optional ``windows`` (null or an array of non-empty strings), and optional
    ``pool`` (a bare token). ``pool`` names the provider-side quota pool the
    package bills to; packages declared on different runtimes that carry the
    same ``pool`` describe the same shared pool — Issue #368 merges Grok and
    Cursor usage into pool ``cursor-grok``, which each runtime acquires from
    its own source (Cursor reads Cursor usage, Grok reads Grok billing) with
    no cross-mapping, mirroring, or derivation. A package without ``pool`` is
    its own pool, addressed by its qualified id ``<platform>:<token>``.
    Current period values are ``5h``, ``weekly``, and ``monthly``; multiple
    windows may apply to one package. An empty array means the package is
    verified to have no time-based reset window. Null means its period is not
    established. No other keys. ``binds_models: false`` is a balance the Usage
    page can list and that a ``native_field`` rule may name, and that
    ``single`` / ``explicit`` / ``provider_prefix`` must not target.

``model_package_rule``
    One JSON object. ``kind`` is exactly one of:

    * ``single`` — ``{"kind","package"}``. Every non-empty model id maps to
      that package. This is a declared one-pool fact, not a fallback used
      when another rule misses.
    * ``explicit`` — ``{"kind","map"}``. ``map`` is model-id → package token,
      exact string match after stripping. Any other id is unmapped.
    * ``provider_prefix`` — ``{"kind","providers","gaps"?}``. ``providers``
      maps a provider segment to a package token. ``gaps`` (optional) lists
      segments that stay unmapped even though the package catalog may name
      that lane. The segment is the first element of a JSON-array model id,
      else the head before ``\\``, else the head before ``/``. A bare id
      with no segment uses an optional exact ``models`` map, otherwise unmapped.
    * ``native_field`` — ``{"kind","field","values","absent"?}``. ``values``
      maps an upstream field spelling to a package token. A missing, null,
      or empty field uses ``absent`` when that key names a package, and is
      unmapped when ``absent`` is omitted. A present value that is not in
      ``values``, or a list whose members do not all name the same package,
      is unmapped. With no row (the static query), the field is not exposed,
      so ``absent`` applies. An optional exact ``models`` map takes precedence
      over ``absent`` only when the native field is missing, null, or empty.

A match returns the consumer id ``<platform>:<token>``. A miss is
``packageId: null`` and ``status: "unmapped"``. Nothing substitutes another
package. Package tokens and rule targets are checked when the manifest loads.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RULE_KINDS = ("single", "provider_prefix", "native_field", "explicit")
PLATFORM_ORDER = (
    "antigravity", "claude-code", "codex", "cursor-cli", "devin", "droid",
    "dsh", "grok", "hermes", "kimi-cli", "opencode", "zcode",
)
PACKAGE_KEYS = {"id", "name", "binds_models", "windows", "pool"}
TOKEN = re.compile(r"^[a-z][a-z0-9_-]*$")
FIELD_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_MISSING = object()


class QuotaError(ValueError):
    """A manifest quota document does not match the schema."""


def _json_document(raw: str, label: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise QuotaError(f"{label} is not a JSON document") from exc


def _package_token(value: Any, label: str) -> str:
    if not isinstance(value, str) or TOKEN.fullmatch(value) is None:
        raise QuotaError(f"{label} must be a package token")
    return value


def parse_packages(raw: str) -> list[dict[str, Any]]:
    """Normalize ``quota_packages``. Raises ``QuotaError`` on a bad document."""
    document = _json_document(raw, "quota_packages")
    if not isinstance(document, list) or not document:
        raise QuotaError("quota_packages must be a non-empty array")
    packages: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(document):
        if not isinstance(item, dict):
            raise QuotaError(f"quota_packages[{index}] must be an object")
        extra = set(item) - PACKAGE_KEYS
        if extra:
            raise QuotaError(f"quota_packages[{index}] has unknown keys {sorted(extra)}")
        token = _package_token(item.get("id"), f"quota_packages[{index}].id")
        if token in seen:
            raise QuotaError(f"duplicate quota package {token!r}")
        seen.add(token)
        name = item.get("name")
        if not isinstance(name, str) or not name.strip():
            raise QuotaError(f"quota_packages[{index}].name must be a non-empty string")
        binds = item.get("binds_models", True)
        if not isinstance(binds, bool):
            raise QuotaError(f"quota_packages[{index}].binds_models must be a bool")
        windows = item.get("windows", None)
        if windows is not None:
            if not isinstance(windows, list) or not all(
                isinstance(entry, str) and entry.strip() for entry in windows
            ):
                raise QuotaError(
                    f"quota_packages[{index}].windows must be null or an array of strings"
                )
        pool = item.get("pool")
        if pool is not None and (
            not isinstance(pool, str) or TOKEN.fullmatch(pool) is None
        ):
            raise QuotaError(
                f"quota_packages[{index}].pool must be a bare pool token"
            )
        packages.append({
            "id": token,
            "name": name,
            "binds_models": binds,
            "windows": windows,
            "pool": pool,
        })
    return packages


def _binding_token(packages: dict[str, dict[str, Any]], value: Any, label: str) -> str:
    token = _package_token(value, label)
    package = packages.get(token)
    if package is None:
        raise QuotaError(f"{label} names unknown package {token!r}")
    if not package["binds_models"]:
        raise QuotaError(f"{label} names balance package {token!r}")
    return token


def _known_token(packages: dict[str, dict[str, Any]], value: Any, label: str) -> str:
    token = _package_token(value, label)
    if token not in packages:
        raise QuotaError(f"{label} names unknown package {token!r}")
    return token


def parse_rule(raw: str, packages: list[dict[str, Any]]) -> dict[str, Any]:
    """Normalize ``model_package_rule`` against ``packages``."""
    document = _json_document(raw, "model_package_rule")
    if not isinstance(document, dict):
        raise QuotaError("model_package_rule must be an object")
    kind = document.get("kind")
    if kind not in RULE_KINDS:
        raise QuotaError(f"model_package_rule.kind must be one of {', '.join(RULE_KINDS)}")
    by_id = {package["id"]: package for package in packages}
    if kind == "single":
        _exact_keys(document, {"kind", "package"})
        return {"kind": kind, "package": _binding_token(by_id, document.get("package"), "single.package")}
    if kind == "explicit":
        _exact_keys(document, {"kind", "map"})
        mapping = document.get("map")
        if not isinstance(mapping, dict) or not mapping:
            raise QuotaError("explicit.map must be a non-empty object")
        normalized: dict[str, str] = {}
        for model_id, token in mapping.items():
            if not isinstance(model_id, str) or not model_id.strip():
                raise QuotaError("explicit.map keys must be non-empty strings")
            normalized[model_id] = _binding_token(by_id, token, f"explicit.map[{model_id!r}]")
        return {"kind": kind, "map": normalized}
    if kind == "provider_prefix":
        _exact_keys(document, {"kind", "providers", "gaps", "models"})
        providers = document.get("providers")
        gaps = document.get("gaps", [])
        if not isinstance(providers, dict) or not providers:
            raise QuotaError("provider_prefix.providers must be a non-empty object")
        if not isinstance(gaps, list):
            raise QuotaError("provider_prefix.gaps must be an array")
        gap_set: list[str] = []
        for entry in gaps:
            if not isinstance(entry, str) or not entry.strip() or any(ch.isspace() for ch in entry):
                raise QuotaError("provider_prefix.gaps entries must be non-empty tokens")
            gap_set.append(entry)
        if len(set(gap_set)) != len(gap_set):
            raise QuotaError("provider_prefix.gaps has a duplicate")
        normalized_providers: dict[str, str] = {}
        for segment, token in providers.items():
            if not isinstance(segment, str) or not segment.strip() or any(ch.isspace() for ch in segment):
                raise QuotaError("provider_prefix.providers keys must be non-empty segments")
            if segment in gap_set:
                raise QuotaError(f"provider segment {segment!r} is both a route and a gap")
            normalized_providers[segment] = _binding_token(
                by_id, token, f"provider_prefix.providers[{segment!r}]"
            )
        return {"kind": kind, "providers": normalized_providers, "gaps": gap_set,
                "models": _model_bindings(document, packages)}
    _exact_keys(document, {"kind", "field", "values", "absent", "models"})
    field = document.get("field")
    if not isinstance(field, str) or FIELD_NAME.fullmatch(field) is None:
        raise QuotaError("native_field.field must be an identifier")
    values = document.get("values")
    if not isinstance(values, dict) or not values:
        raise QuotaError("native_field.values must be a non-empty object")
    normalized_values: dict[str, str] = {}
    for spelling, token in values.items():
        if not isinstance(spelling, str) or not spelling:
            raise QuotaError("native_field.values keys must be non-empty strings")
        normalized_values[spelling] = _known_token(
            by_id, token, f"native_field.values[{spelling!r}]"
        )
    rule: dict[str, Any] = {"kind": kind, "field": field, "values": normalized_values,
                            "models": _model_bindings(document, packages)}
    if "absent" in document and document.get("absent") is not None:
        rule["absent"] = _binding_token(by_id, document.get("absent"), "native_field.absent")
    return rule


def _model_bindings(document: dict[str, Any], packages: list[dict[str, Any]]) -> dict[str, str]:
    # A present null ``models`` is the same as omitting it, matching ``absent``.
    # The explicit-map reparse validates keys and binds each value to a real
    # model-binding package, so a static entry can never name a balance.
    if document.get("models") is None:
        return {}
    models = document["models"]
    if not isinstance(models, dict) or not models:
        raise QuotaError("model_package_rule.models must be a non-empty object")
    return parse_rule(json.dumps({"kind": "explicit", "map": models}), packages)["map"]


def _exact_keys(document: dict[str, Any], allowed: set[str]) -> None:
    # ``gaps`` and ``absent`` are optional. A present null ``absent`` is the
    # same as omitting it. ``gaps`` may be omitted.
    optional = {"gaps", "absent", "models"}
    unknown = set(document) - allowed
    if unknown:
        raise QuotaError(f"model_package_rule has unknown keys {sorted(unknown)}")
    required = allowed - optional
    missing = [key for key in sorted(required) if key not in document]
    if missing:
        raise QuotaError(f"model_package_rule missing {missing}")


def validate_manifest(fields: dict[str, str]) -> dict[str, Any]:
    """Parse one manifest's quota fields. ``fields`` values are already strings."""
    packages = parse_packages(fields.get("quota_packages", ""))
    rule = parse_rule(fields.get("model_package_rule", ""), packages)
    return {"packages": packages, "rule": rule}


def manifest_file(platform: str, script_dir: Path | None = None) -> Path | None:
    """Checkout ``platforms/<id>.yaml`` wins. A Skill-local ``platform.yaml`` is the fallback."""
    base = script_dir or Path(__file__).resolve().parent
    named = base.parent / "platforms" / f"{platform}.yaml"
    if named.is_file():
        return named
    local = base / "platform.yaml"
    return local if local.is_file() else None


def available_platforms(script_dir: Path | None = None) -> list[str]:
    """Platforms whose manifests this script directory can read, in Runner order."""
    base = script_dir or Path(__file__).resolve().parent
    checkout = base.parent / "platforms"
    if checkout.is_dir() and (checkout / "claude-code.yaml").is_file():
        return [platform for platform in PLATFORM_ORDER if (checkout / f"{platform}.yaml").is_file()]
    local = base / "platform.yaml"
    if not local.is_file():
        return []
    try:
        fields = _read_manifest_file(local)
    except QuotaError:
        return []
    platform = fields.get("id") or ""
    return [platform] if platform in PLATFORM_ORDER else []


def read_manifest(platform: str, script_dir: Path | None = None) -> dict[str, str]:
    """The flat manifest map for one platform."""
    path = manifest_file(platform, script_dir)
    if path is None:
        raise QuotaError(f"manifest not found for platform {platform}")
    result = _read_manifest_file(path)
    if result.get("id") != platform:
        raise QuotaError(f"{path}: id is {result.get('id')!r}, not {platform!r}")
    return result


def parse_acp_model_map(raw: str) -> dict[str, str]:
    """Declared native ID to ACP option value mappings."""
    mapping = {}
    for pair in (raw or "").split(";"):
        key, separator, value = pair.partition("=")
        if separator and key.strip() and value.strip():
            mapping[key.strip()] = value.strip()
    return mapping


def declared_display_name(fields: dict[str, Any], native_id: Any) -> str | None:
    """Label one exact declared native model id, or None.

    Scans ``*_model_id`` and their declared ACP wire mappings. When every
    match has the same non-empty ``*_model_name``, that name is the label. The lookup does not choose a
    preset, copy that preset's effort, or prove a request was applied. An
    unknown id, an empty id, or disagreeing names return None.
    """
    if not isinstance(fields, dict) or not isinstance(native_id, str) or not native_id:
        return None
    mapping = parse_acp_model_map(fields.get("acp_model_map", ""))
    # ZCode's provider qualification is not part of its model identity.
    lookup_id = native_id
    if fields.get("id") == "zcode":
        lookup_id = native_id.split("\\")[-1].split("/")[-1].strip()
    names: list[str] = []
    for key, value in fields.items():
        if not isinstance(key, str) or not key.endswith("_model_id"):
            continue
        if value != lookup_id and mapping.get(value) != native_id:
            continue
        name = fields.get(key[: -len("_model_id")] + "_model_name")
        if not isinstance(name, str) or not name:
            return None
        if name not in names:
            names.append(name)
    if len(names) == 1:
        return names[0]
    return None


def _read_manifest_file(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition(":")
        if not separator:
            raise QuotaError(f"{path}:{number}: expected key: value")
        try:
            parsed = json.loads(value.strip())
        except json.JSONDecodeError as exc:
            raise QuotaError(f"{path}:{number}: values must be JSON strings") from exc
        if not isinstance(parsed, str):
            raise QuotaError(f"{path}:{number}: values must be JSON strings")
        result[key.strip()] = parsed
    return result


class Catalog:
    """One platform's packages and rule, ready to resolve."""

    def __init__(self, platform: str, packages: list[dict[str, Any]], rule: dict[str, Any],
                 model_config_id: str) -> None:
        self.platform = platform
        self.packages = packages
        self.packages_by_id = {package["id"]: package for package in packages}
        self.rule = rule
        self.model_config_id = model_config_id

    def qualified(self, token: str) -> str:
        return f"{self.platform}:{token}"

    def package_for(self, token: str) -> dict[str, Any]:
        return self.packages_by_id[token]

    def public_packages(self) -> list[dict[str, Any]]:
        """Consumer rows. ``id`` is ``<platform>:<token>``; null windows mean unknown."""
        rows: list[dict[str, Any]] = []
        for package in self.packages:
            row = {
                "id": self.qualified(package["id"]),
                "name": package["name"],
                "windows": package["windows"],
                "binds_models": package["binds_models"],
            }
            if package["pool"] is not None:
                row["pool"] = package["pool"]
            rows.append(row)
        return rows


def load_catalog(platform: str, script_dir: Path | None = None) -> Catalog:
    fields = read_manifest(platform, script_dir)
    parsed = validate_manifest(fields)
    return Catalog(
        platform,
        parsed["packages"],
        parsed["rule"],
        fields.get("acp_model_config_id") or "",
    )


def provider_segment(model_id: str) -> str | None:
    """The provider segment of a model id, or None when the id has none."""
    text = model_id.strip()
    if text.startswith("["):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return None
        if isinstance(parsed, list) and parsed and isinstance(parsed[0], str) and parsed[0]:
            return parsed[0]
        return None
    if "\\" in text:
        head, _, _tail = text.partition("\\")
        return head or None
    if "/" in text:
        head, _, _tail = text.partition("/")
        return head or None
    return None


def resolve_model(catalog: Catalog, model_id: Any, row: dict[str, Any] | None = None) -> dict[str, Any]:
    """``{packageId, pool?, status}``. ``packageId`` is ``<platform>:<token>`` or null."""
    text = model_id.strip() if isinstance(model_id, str) else ""
    token = _resolve_token(catalog, text, row if isinstance(row, dict) else None)
    if token is None:
        return {"packageId": None, "status": "unmapped"}
    result: dict[str, Any] = {"packageId": catalog.qualified(token), "status": "mapped"}
    pool = catalog.package_for(token).get("pool")
    if pool is not None:
        result["pool"] = pool
    return result


def _resolve_token(catalog: Catalog, model_id: str, row: dict[str, Any] | None) -> str | None:
    rule = catalog.rule
    kind = rule["kind"]
    if kind == "single":
        return rule["package"] if model_id else None
    if kind == "explicit":
        return rule["map"].get(model_id)
    if kind == "provider_prefix":
        segment = provider_segment(model_id)
        if segment is None:
            return rule.get("models", {}).get(model_id)
        if segment in rule["gaps"]:
            return None
        return rule["providers"].get(segment)
    if row is None or row.get(rule["field"]) in (None, "", []):
        return rule.get("models", {}).get(model_id, rule.get("absent"))
    return _native_token(catalog, row)


def _native_token(catalog: Catalog, row: dict[str, Any] | None) -> str | None:
    rule = catalog.rule
    if row is None or rule["field"] not in row:
        return rule.get("absent")
    raw = row.get(rule["field"])
    if raw is None or raw == "":
        return rule.get("absent")
    values: dict[str, str] = rule["values"]
    if isinstance(raw, str):
        return values.get(raw)
    if isinstance(raw, list):
        if not raw:
            return rule.get("absent")
        tokens: list[str] = []
        for item in raw:
            if not isinstance(item, str) or item not in values:
                return None
            tokens.append(values[item])
        if len(set(tokens)) != 1:
            return None
        return tokens[0]
    return None


def _stamp(row: dict[str, Any], catalog: Catalog, model_id: str, evidence: dict[str, Any]) -> None:
    resolved = resolve_model(catalog, model_id, evidence)
    # ``quotaPool`` names the billed pool: the shared ``pool`` id when the
    # package declares one (several runtimes may share it), else the
    # package's qualified id.
    row["quotaPool"] = resolved.get("pool") or resolved["packageId"]
    if resolved["status"] == "unmapped":
        row["quotaPoolStatus"] = "unmapped"
    else:
        row.pop("quotaPoolStatus", None)


def annotate_config_options(options: Any, catalog: Catalog) -> None:
    """Stamp model-option leaves in place. Other options are left untouched."""
    if not catalog.model_config_id or not isinstance(options, list):
        return
    for option in options:
        if not isinstance(option, dict) or option.get("id") != catalog.model_config_id:
            continue
        for entry in option.get("options") or []:
            if not isinstance(entry, dict):
                continue
            nested = entry.get("options")
            if isinstance(nested, list):
                for leaf in nested:
                    if isinstance(leaf, dict):
                        value = leaf.get("value")
                        _stamp(leaf, catalog, value if isinstance(value, str) else "", leaf)
            else:
                value = entry.get("value")
                _stamp(entry, catalog, value if isinstance(value, str) else "", entry)


def annotate_model_rows(rows: Any, catalog: Catalog) -> None:
    """Stamp ``availableModels`` rows in place. The id is ``id``, else ``modelId``, else ``value``."""
    if not isinstance(rows, list):
        return
    for row in rows:
        if not isinstance(row, dict):
            continue
        model_id = row.get("id")
        if not isinstance(model_id, str) or not model_id:
            model_id = row.get("modelId")
        if not isinstance(model_id, str) or not model_id:
            model_id = row.get("value")
        _stamp(row, catalog, model_id if isinstance(model_id, str) else "", row)


def annotate_observe(receipt: dict[str, Any], catalog: Catalog) -> None:
    """Stamp an observe/status receipt's model rows. The caller's object is the copy."""
    meta = receipt.get("session_meta")
    if isinstance(meta, dict):
        annotate_config_options(meta.get("configOptions"), catalog)
        models = meta.get("models")
        if isinstance(models, dict):
            annotate_model_rows(models.get("availableModels"), catalog)
        annotate_model_rows(meta.get("availableModels"), catalog)
    annotate_config_options(receipt.get("initial_config_options"), catalog)


def view_models(session_meta: Any, catalog: Catalog) -> dict[str, Any]:
    """Model rows for a view payload. The caller's ``session_meta`` is not modified."""
    meta = copy.deepcopy(session_meta) if isinstance(session_meta, dict) else {}
    annotate_observe({"session_meta": meta}, catalog)
    nested = meta.get("models") if isinstance(meta.get("models"), dict) else {}
    available = nested.get("availableModels")
    if not isinstance(available, list):
        available = meta.get("availableModels") if isinstance(meta.get("availableModels"), list) else []
    options = meta.get("configOptions") if isinstance(meta.get("configOptions"), list) else []
    model_options = [
        option for option in options
        if isinstance(option, dict) and option.get("id") == catalog.model_config_id
    ]
    return {"availableModels": available, "options": model_options}


ANTIGRAVITY_USAGE_ARGS: tuple[str, ...] = ("-p", "/usage", "--output-format", "json")
ANTIGRAVITY_GEMINI_GROUP = "Gemini Models"
ANTIGRAVITY_3P_GROUP = "Claude and GPT models"
ANTIGRAVITY_WINDOW_PRIORITY: tuple[str, ...] = ("weekly", "5h")
_ANTIGRAVITY_BUCKET_WINDOWS: dict[str, str] = {
    "gemini-weekly": "weekly",
    "gemini-5h": "5h",
    "3p-weekly": "weekly",
    "3p-5h": "5h",
}


def antigravity_group_for_model(model_id: str | None) -> str:
    """Return the Antigravity ``/usage`` group name that governs ``model_id``.

    Verified live on ``agy 1.3.5`` (Issue #329): ``agy -p /usage --output-format json``
    reports two quota groups under ``antigravity:account``:
    ``Gemini Models`` (``gemini-weekly``, ``gemini-5h``) for both verified presets
    ``antigravity/default`` (``gemini-4-argon-medium``) and ``antigravity/xhigh``
    (``gemini-4-argon-high``) plus ``gemini-3-flash-agent``, and
    ``Claude and GPT models`` (``3p-weekly``, ``3p-5h``) for third-party
    Anthropic/OpenAI models (``claude-*``, ``gpt-*``).
    """
    text = (model_id or "").strip().lower()
    if text.startswith(("claude-", "gpt-", "o1-", "o3-", "o4-")):
        return ANTIGRAVITY_3P_GROUP
    return ANTIGRAVITY_GEMINI_GROUP


def _antigravity_bucket_window(bucket_id: str, label: str) -> str | None:
    if bucket_id in _ANTIGRAVITY_BUCKET_WINDOWS:
        return _ANTIGRAVITY_BUCKET_WINDOWS[bucket_id]
    lowered = f"{bucket_id} {label}".lower()
    if "weekly" in lowered or "week" in lowered or "7d" in lowered:
        return "weekly"
    if "5h" in lowered or "5-hour" in lowered or "5 hour" in lowered:
        return "5h"
    if "monthly" in lowered or "month" in lowered:
        return "monthly"
    return None


def _normalize_antigravity_bucket(bucket: dict[str, Any], group_name: str) -> dict[str, Any] | None:
    bucket_id = bucket.get("id")
    if not isinstance(bucket_id, str) or not bucket_id.strip():
        return None
    raw_name = bucket.get("name") if isinstance(bucket.get("name"), str) and bucket.get("name").strip() else None
    raw_label = bucket.get("label") if isinstance(bucket.get("label"), str) and bucket.get("label").strip() else None
    label = raw_name or raw_label or bucket_id.strip()
    explicit_window = bucket.get("window")
    if isinstance(explicit_window, str) and explicit_window.strip() in ("5h", "weekly", "monthly"):
        window: str | None = explicit_window.strip()
    else:
        window = _antigravity_bucket_window(bucket_id.strip(), label)
    if window is None:
        return None
    raw_rem = bucket.get("remaining_fraction")
    if not isinstance(raw_rem, (int, float)) or isinstance(raw_rem, bool):
        return None
    rem_fraction = max(0.0, min(1.0, float(raw_rem)))
    used_fraction = max(0.0, min(1.0, 1.0 - rem_fraction))
    rem_pct = round(rem_fraction * 100.0, 2)
    used_pct = round(used_fraction * 100.0, 2)
    reset_time = bucket.get("reset_time")
    reset_at = reset_time.strip() if isinstance(reset_time, str) and reset_time.strip() else None
    return {
        "bucket_id": bucket_id.strip(),
        "label": label,
        "group": group_name,
        "window": window,
        "used": used_pct,
        "limit": 100.0,
        "used_percent": used_pct,
        "remaining_percent": rem_pct,
        "remaining_fraction": rem_fraction,
        "used_fraction": used_fraction,
        "reset_at": reset_at,
    }


def _select_primary_window(windows: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    for period in ANTIGRAVITY_WINDOW_PRIORITY:
        if period in windows:
            return dict(windows[period])
    for entry in windows.values():
        return dict(entry)
    return None


def parse_antigravity_usage(
    raw: str,
    model: str | None = None,
    stderr: str = "",
) -> dict[str, Any]:
    """Parse ``agy -p /usage --output-format json`` output into standard quota shape.

    Returns a dictionary with:
    - ``platform``: ``"antigravity"``
    - ``packageId``: ``"antigravity:account"``
    - ``status``: ``"ok"`` | ``"login_required"`` | ``"unavailable"`` | ``"error"``
    - ``model``: requested model id (or None)
    - ``selected_group``: group name used for top-level ``quota`` and ``windows``
    - ``quota``: primary window dict (``used``, ``limit``, ``used_percent``,
      ``remaining_percent``, ``remaining_fraction``, ``reset_at``, ``window``)
      selecting ``weekly`` when both ``weekly`` and ``5h`` exist, or ``None``
    - ``windows``: ``{"5h": {...}, "weekly": {...}}`` for ``selected_group``
    - ``groups``: ``{"Gemini Models": {"windows": {...}, "quota": {...}}, ...}``
    """
    selected_group = antigravity_group_for_model(model)
    base: dict[str, Any] = {
        "platform": "antigravity",
        "packageId": "antigravity:account",
        "model": model,
        "selected_group": selected_group,
        "status": "error",
        "quota": None,
        "windows": {},
        "groups": {},
    }
    stderr_text = (stderr or "").strip()
    raw_text = (raw or "").strip()
    payload: dict[str, Any] | None = None
    if raw_text:
        for line in reversed(raw_text.splitlines()):
            candidate = line.strip()
            if candidate.startswith("{") and candidate.endswith("}"):
                try:
                    parsed = json.loads(candidate)
                except json.JSONDecodeError:
                    continue
                if isinstance(parsed, dict):
                    payload = parsed
                    break
        if payload is None:
            try:
                parsed = json.loads(raw_text)
                if isinstance(parsed, dict):
                    payload = parsed
            except json.JSONDecodeError:
                payload = None

    if payload is None:
        if "Authentication required" in stderr_text or "Please visit the URL to log in" in stderr_text:
            base["status"] = "login_required"
            base["error"] = "authentication required"
            return base
        base["status"] = "error"
        base["error"] = stderr_text or "invalid JSON output from agy -p /usage"
        return base

    error_field = payload.get("error")
    error_text = error_field.strip() if isinstance(error_field, str) else ""
    if payload.get("status") != "SUCCESS" or error_text:
        combined = f"{error_text} {stderr_text}".lower()
        if "authentication" in combined or "log in" in combined or "not logged in" in combined:
            base["status"] = "login_required"
        elif "quota data is not available" in combined or "not eligible" in combined:
            base["status"] = "unavailable"
        else:
            base["status"] = "error"
        base["error"] = error_text or stderr_text or "agy /usage returned non-success status"
        return base

    inner: dict[str, Any] | None = None
    command_obj = payload.get("command")
    if isinstance(command_obj, dict) and isinstance(command_obj.get("data"), dict):
        inner = command_obj["data"]
    else:
        response_raw = payload.get("response")
        if isinstance(response_raw, str) and response_raw.strip():
            try:
                parsed_inner = json.loads(response_raw)
                if isinstance(parsed_inner, dict):
                    inner = parsed_inner
            except json.JSONDecodeError as exc:
                base["status"] = "error"
                base["error"] = f"invalid inner response JSON: {exc}"
                return base

    if not isinstance(inner, dict):
        base["status"] = "unavailable"
        base["error"] = "missing command.data or JSON response in agy /usage payload"
        return base

    inner_error = inner.get("error")
    if isinstance(inner_error, str) and inner_error.strip():
        lowered = inner_error.lower()
        if "not logged in" in lowered or "authentication" in lowered:
            base["status"] = "login_required"
        else:
            base["status"] = "unavailable"
        base["error"] = inner_error.strip()
        return base

    raw_groups = inner.get("groups")
    if not isinstance(raw_groups, list) or not raw_groups:
        base["status"] = "unavailable"
        base["error"] = "no quota groups in agy /usage response"
        return base

    groups: dict[str, dict[str, Any]] = {}
    for item in raw_groups:
        if not isinstance(item, dict):
            continue
        group_name = item.get("name") if isinstance(item.get("name"), str) and item.get("name").strip() else item.get("group")
        if not isinstance(group_name, str) or not group_name.strip():
            continue
        raw_buckets = item.get("buckets")
        if not isinstance(raw_buckets, list):
            continue
        group_windows: dict[str, dict[str, Any]] = {}
        buckets_list: list[dict[str, Any]] = []
        for bucket in raw_buckets:
            if not isinstance(bucket, dict):
                continue
            normalized = _normalize_antigravity_bucket(bucket, group_name.strip())
            if normalized is None:
                continue
            buckets_list.append(normalized)
            group_windows[normalized["window"]] = normalized
        if group_windows:
            groups[group_name.strip()] = {
                "group": group_name.strip(),
                "windows": group_windows,
                "quota": _select_primary_window(group_windows),
                "buckets": buckets_list,
            }

    if not groups:
        base["status"] = "unavailable"
        base["error"] = "no usable quota buckets in agy /usage response"
        return base

    chosen = groups.get(selected_group) or next(iter(groups.values()))
    base["status"] = "ok"
    base["selected_group"] = chosen["group"]
    base["groups"] = groups
    base["windows"] = dict(chosen["windows"])
    base["quota"] = dict(chosen["quota"]) if isinstance(chosen.get("quota"), dict) else None
    return base


def probe_antigravity_usage(
    binary: str | None = None,
    model: str | None = None,
    timeout: float = 20.0,
    cwd: str | Path | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Run ``agy -p /usage --output-format json`` and return parsed quota facts.

    Handles ``agy``'s unsigned-account OAuth prompt on stderr by interrupting
    the child with ``SIGINT`` immediately instead of waiting for its 60s
    browser-login timeout, and reads stdout line-by-line so background child
    file descriptors do not block after the JSON line is emitted.
    """
    exe = binary or shutil.which("agy") or "agy"
    cmd = [exe, *ANTIGRAVITY_USAGE_ARGS]
    if isinstance(model, str) and model.strip():
        cmd.extend(["--model", model.strip()])
    run_env = dict(os.environ if env is None else env)
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(cwd) if cwd is not None else None,
            env=run_env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except OSError as exc:
        return {
            "platform": "antigravity",
            "packageId": "antigravity:account",
            "model": model,
            "selected_group": antigravity_group_for_model(model),
            "status": "error",
            "quota": None,
            "windows": {},
            "groups": {},
            "error": str(exc),
            "command": cmd,
        }

    stdout_lines: list[str] = []
    stderr_lines: list[str] = []
    got_json_event = threading.Event()
    auth_prompt_event = threading.Event()

    def _read_stdout() -> None:
        assert proc.stdout is not None
        for line in proc.stdout:
            stdout_lines.append(line)
            stripped = line.strip()
            if stripped.startswith("{") and stripped.endswith("}"):
                got_json_event.set()
                break

    def _read_stderr() -> None:
        assert proc.stderr is not None
        for line in proc.stderr:
            stderr_lines.append(line)
            if "Authentication required" in line or "Please visit the URL to log in" in line:
                auth_prompt_event.set()
                try:
                    proc.send_signal(signal.SIGINT)
                except OSError:
                    pass
                break

    t_out = threading.Thread(target=_read_stdout, daemon=True)
    t_err = threading.Thread(target=_read_stderr, daemon=True)
    t_out.start()
    t_err.start()

    deadline = time.monotonic() + max(0.5, float(timeout))
    while time.monotonic() < deadline:
        if got_json_event.is_set():
            break
        if auth_prompt_event.is_set() and proc.poll() is not None:
            break
        if proc.poll() is not None and not t_out.is_alive():
            break
        time.sleep(0.05)

    timed_out = not got_json_event.is_set() and not auth_prompt_event.is_set() and proc.poll() is None
    if proc.poll() is None:
        try:
            proc.terminate()
            proc.wait(timeout=1.0)
        except Exception:
            try:
                proc.kill()
                proc.wait(timeout=1.0)
            except Exception:
                pass
    else:
        try:
            proc.wait(timeout=1.0)
        except Exception:
            pass

    t_out.join(timeout=0.5)
    t_err.join(timeout=0.5)
    for pipe in (proc.stdout, proc.stderr):
        if pipe is not None:
            try:
                pipe.close()
            except Exception:
                pass
    raw_stdout = "".join(stdout_lines)
    raw_stderr = "".join(stderr_lines)
    if timed_out and not raw_stdout.strip():
        return {
            "platform": "antigravity",
            "packageId": "antigravity:account",
            "model": model,
            "selected_group": antigravity_group_for_model(model),
            "status": "error",
            "quota": None,
            "windows": {},
            "groups": {},
            "error": f"timed out after {timeout}s waiting for agy -p /usage",
            "command": cmd,
        }
    result = parse_antigravity_usage(raw_stdout, model=model, stderr=raw_stderr)
    result["command"] = cmd
    return result


CURSOR_API_BASE = "https://api2.cursor.sh"
CURSOR_KEY_NAME = "CURSOR_API_KEY"
CURSOR_USAGE_PATH = "/auth/usage"
CURSOR_PACKAGE = "cursor-cli:account"
GROK_BILLING_BASE = "https://code.grok.com"
GROK_KEY_NAME = "GROK_API_KEY"
GROK_BILLING_PATH = "/billing?format=credits"
GROK_PACKAGE = "grok:account"
# Issue #368: the Grok+Cursor shared pool. Both manifests declare this pool
# token; each runtime acquires it from its own source with no cross-mapping.
CURSOR_GROK_POOL = "cursor-grok"


def _cursor_home(env: Mapping[str, str]) -> Path:
    raw = env.get("CURSOR_HOME")
    if isinstance(raw, str) and raw.strip():
        return Path(raw).expanduser()
    home = env.get("HOME")
    base = Path(home).expanduser() if isinstance(home, str) and home.strip() else Path.home()
    return base / ".cursor"


def read_cursor_api_key(env: Mapping[str, str] | None = None) -> str | None:
    """``CURSOR_API_KEY`` from the process env, then ``~/.cursor/.env``, then ``refs:``.

    A non-empty ``CURSOR_HOME`` replaces ``~/.cursor`` and does not fall back
    to it. The returned string is for the request header only. Callers must
    not log it.
    """
    source: Mapping[str, str] = os.environ if env is None else env
    direct = source.get(CURSOR_KEY_NAME)
    if isinstance(direct, str) and direct.strip():
        return direct.strip()
    home = _cursor_home(source)
    dotenv = _read_limited(home / ".env")
    if dotenv:
        found = _dotenv_named(dotenv, CURSOR_KEY_NAME)
        if found:
            return found
    credentials = _read_limited(home / ".credentials.yaml")
    if credentials:
        found = _credentials_ref(credentials, CURSOR_KEY_NAME)
        if found and found.strip():
            return found.strip()
    return None


def _grok_home(env: Mapping[str, str]) -> Path:
    raw = env.get("GROK_HOME")
    if isinstance(raw, str) and raw.strip():
        return Path(raw).expanduser()
    home = env.get("HOME")
    base = Path(home).expanduser() if isinstance(home, str) and home.strip() else Path.home()
    return base / ".grok"


def _grok_expiry_seconds(value: Any) -> float | None:
    """Parse an ``expires_at`` field (epoch s/ms or ISO text) to epoch seconds."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        raw = float(value)
        return raw / 1000.0 if raw > 1e12 else raw
    if isinstance(value, str) and value.strip():
        text = value.strip().replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(text).timestamp()
        except ValueError:
            return None
    return None


def read_grok_api_key(env: Mapping[str, str] | None = None) -> str | None:
    """A Grok billing bearer: ``GROK_API_KEY`` env, ``~/.grok/.env``, then
    the ``grok login`` session key in ``~/.grok/auth.json``.

    A non-empty ``GROK_HOME`` replaces ``~/.grok`` and does not fall back to
    it. The returned string is for the request header only. Callers must not
    log it.
    """
    source: Mapping[str, str] = os.environ if env is None else env
    direct = source.get(GROK_KEY_NAME)
    if isinstance(direct, str) and direct.strip():
        return direct.strip()
    home = _grok_home(source)
    dotenv = _read_limited(home / ".env")
    if dotenv:
        found = _dotenv_named(dotenv, GROK_KEY_NAME)
        if found:
            return found
    auth = _read_limited(home / "auth.json")
    if not auth:
        return None
    try:
        parsed = json.loads(auth)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    now = time.time()
    fallback: str | None = None
    for entry in parsed.values():
        if not isinstance(entry, dict):
            continue
        key = entry.get("key")
        if not isinstance(key, str) or not key.strip():
            continue
        expiry = _grok_expiry_seconds(entry.get("expires_at"))
        if expiry is None or expiry > now:
            return key.strip()
        if fallback is None:
            fallback = key.strip()
    return fallback


def _usage_get(url: str, headers: dict[str, str], timeout: float) -> tuple[int | None, bytes | str]:
    request = urllib.request.Request(url, headers=headers, method="GET")
    opener = urllib.request.build_opener(_CommandCodeNoRedirect)
    try:
        with opener.open(request, timeout=timeout) as response:
            status = getattr(response, "status", None) or response.getcode()
            return int(status), response.read(1_000_000)
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read(64_000)
        except Exception:
            body = b""
        return int(exc.code), body
    except urllib.error.URLError as exc:
        reason = exc.reason
        text = str(reason).lower()
        if isinstance(reason, (TimeoutError, socket.timeout)) or "timed out" in text:
            return None, "timeout"
        return None, "network"
    except (TimeoutError, socket.timeout):
        return None, "timeout"
    except OSError:
        return None, "network"


def _cursor_envelope(model: str | None, status: str, reason: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "platform": "cursor-cli",
        "packageId": CURSOR_PACKAGE,
        "pool": CURSOR_GROK_POOL,
        "status": status,
        "model": model,
        "quota": None,
        "windows": {},
    }
    if reason is not None:
        result["reason"] = reason
    return result


def _grok_envelope(model: str | None, status: str, reason: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "platform": "grok",
        "packageId": GROK_PACKAGE,
        "pool": CURSOR_GROK_POOL,
        "status": status,
        "model": model,
        "quota": None,
        "windows": {},
    }
    if reason is not None:
        result["reason"] = reason
    return result


def _monthly_metrics(
    used: int | float | None,
    limit: int | float | None,
    used_percent: int | float | None,
    reset_at: str | None,
) -> dict[str, Any]:
    rem_pct = None
    used_pct = used_percent
    rem_fraction = None
    used_fraction = None
    if isinstance(used_pct, (int, float)) and not isinstance(used_pct, bool):
        used_pct = max(0.0, min(100.0, round(float(used_pct), 2)))
        rem_pct = round(100.0 - used_pct, 2)
        used_fraction = round(used_pct / 100.0, 4)
        rem_fraction = round(1.0 - used_fraction, 4)
    elif isinstance(limit, (int, float)) and not isinstance(limit, bool) and limit > 0 and isinstance(used, (int, float)) and not isinstance(used, bool):
        rem_fraction = max(0.0, min(1.0, (float(limit) - float(used)) / float(limit)))
        used_fraction = round(1.0 - rem_fraction, 4)
        used_pct = round(used_fraction * 100.0, 2)
        rem_pct = round(rem_fraction * 100.0, 2)
    return {
        "window": "monthly",
        "used": used,
        "limit": limit,
        "used_percent": used_pct,
        "remaining_percent": rem_pct,
        "remaining_fraction": rem_fraction,
        "used_fraction": used_fraction,
        "reset_at": reset_at,
    }


def _next_month_reset(start_of_month: str | None) -> str | None:
    """The monthly reset: one calendar month after ``startOfMonth``."""
    if not isinstance(start_of_month, str) or not start_of_month.strip():
        return None
    text = start_of_month.strip().replace("Z", "+00:00")
    try:
        start = datetime.fromisoformat(text)
    except ValueError:
        return None
    year = start.year + (1 if start.month == 12 else 0)
    month = 1 if start.month == 12 else start.month + 1
    try:
        end = start.replace(year=year, month=month)
    except ValueError:
        return None
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    return end.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_cursor_usage(
    raw: str,
    model: str | None = None,
    stderr: str = "",
) -> dict[str, Any]:
    """Parse ``GET {CURSOR_API_ENDPOINT|api2.cursor.sh}/auth/usage`` output.

    The response is per-model-bucket request counters plus ``startOfMonth``;
    the unified account reads one shared pool, so buckets aggregate into a
    single monthly window. Returns the standard usage envelope for pool
    ``cursor-grok`` with ``status`` ``ok`` | ``login_required`` |
    ``unavailable`` | ``error``.
    """
    base = _cursor_envelope(model, "error")
    stderr_text = (stderr or "").strip()
    raw_text = (raw or "").strip()
    payload: Any = None
    if raw_text:
        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError:
            payload = None
    if not isinstance(payload, dict):
        lowered = stderr_text.lower()
        if "auth" in lowered or "log in" in lowered or "401" in lowered:
            base["status"] = "login_required"
            base["error"] = stderr_text or "authentication required"
        else:
            base["error"] = stderr_text or "invalid JSON from cursor /auth/usage"
        return base
    error_text = payload.get("error")
    if isinstance(error_text, str) and error_text.strip():
        lowered = error_text.lower()
        base["status"] = "login_required" if "auth" in lowered or "log in" in lowered else "unavailable"
        base["error"] = error_text.strip()
        return base
    buckets = {
        key: value
        for key, value in payload.items()
        if isinstance(value, dict) and isinstance(value.get("numRequests"), (int, float))
    }
    if not buckets:
        base["status"] = "unavailable"
        base["error"] = "no usage buckets in cursor /auth/usage response"
        return base
    used = 0.0
    limit = 0.0
    saw_limit = False
    for value in buckets.values():
        used += float(value.get("numRequests") or 0)
        cap = value.get("maxRequestUsage")
        if isinstance(cap, (int, float)) and not isinstance(cap, bool) and cap > 0:
            limit += float(cap)
            saw_limit = True
    start_of_month = payload.get("startOfMonth")
    start_text = start_of_month.strip() if isinstance(start_of_month, str) else None
    window = _monthly_metrics(
        used,
        limit if saw_limit else None,
        None,
        _next_month_reset(start_text),
    )
    base["status"] = "ok"
    base["windows"] = {"monthly": window}
    base["quota"] = dict(window)
    if start_text:
        base["start_of_month"] = start_text
    return base


def probe_cursor_usage(
    model: str | None = None,
    timeout: float = 20.0,
    env: Mapping[str, str] | None = None,
    base_url: str | None = None,
) -> dict[str, Any]:
    """Read-only Cursor usage for the shared ``cursor-grok`` pool.

    One GET, no retry. The base is ``base_url``, else the runtime's own
    ``CURSOR_API_ENDPOINT`` env, else ``https://api2.cursor.sh``. The key and
    every field other than the named usage fields are dropped before the
    result is returned. This function does not write a file, does not spawn
    a binary, and does not raise.
    """
    model_text = model.strip() if isinstance(model, str) else None
    try:
        return _probe_cursor_usage(model_text, timeout, env, base_url)
    except Exception:
        return _cursor_envelope(model_text, "error", "probe failed")


def _probe_cursor_usage(
    model: str | None,
    timeout: float,
    env: Mapping[str, str] | None,
    base_url: str | None,
) -> dict[str, Any]:
    source: Mapping[str, str] = os.environ if env is None else env
    key = read_cursor_api_key(source)
    if not key:
        return _cursor_envelope(model, "key_missing", "CURSOR_API_KEY is not set")
    override = source.get("CURSOR_API_ENDPOINT")
    root = (base_url or (override.strip() if isinstance(override, str) else "") or CURSOR_API_BASE).rstrip("/")
    status, body = _usage_get(
        root + CURSOR_USAGE_PATH,
        {"Authorization": "Bearer " + key, "Accept": "application/json",
         "User-Agent": "kaola-quota"},
        max(0.1, float(timeout)),
    )
    if status is None:
        reason = "timeout" if body == "timeout" else "network failure"
        return _cursor_envelope(model, "unavailable", reason)
    if status == 401 or status == 403:
        return _cursor_envelope(model, "login_required", _http_reason(status, body))
    if status != 200:
        return _cursor_envelope(model, "unavailable", _http_reason(status, body))
    text = body.decode("utf-8") if isinstance(body, (bytes, bytearray)) else ""
    return parse_cursor_usage(text, model=model)


def parse_grok_usage(
    raw: str,
    model: str | None = None,
    stderr: str = "",
) -> dict[str, Any]:
    """Parse ``GET {GROK_WEB_BASE_URL|code.grok.com}/billing?format=credits``.

    The response is ``{"config": BillingConfig, ...}``; the unified account's
    shared pool normalizes to one monthly window from ``includedUsed`` /
    ``monthlyLimit`` / ``creditUsagePercent`` / ``currentPeriod.end``.
    Returns the standard usage envelope for pool ``cursor-grok``.
    """
    base = _grok_envelope(model, "error")
    stderr_text = (stderr or "").strip()
    raw_text = (raw or "").strip()
    payload: Any = None
    if raw_text:
        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError:
            payload = None
    if not isinstance(payload, dict):
        lowered = stderr_text.lower()
        if "auth" in lowered or "log in" in lowered or "401" in lowered:
            base["status"] = "login_required"
            base["error"] = stderr_text or "authentication required"
        else:
            base["error"] = stderr_text or "invalid JSON from grok /billing"
        return base
    config = payload.get("config") if isinstance(payload.get("config"), dict) else payload
    used = _commandcode_number(config.get("includedUsed"))
    if used is None:
        used = _commandcode_number(config.get("totalUsed"))
    limit = _commandcode_number(config.get("monthlyLimit"))
    percent = _commandcode_number(config.get("creditUsagePercent"))
    if used is None and limit is None and percent is None:
        base["status"] = "unavailable"
        base["error"] = "no billing counters in grok /billing response"
        return base
    period = config.get("currentPeriod")
    reset_at = None
    if isinstance(period, dict):
        reset_at = _commandcode_reset_at(period.get("end"))
    if reset_at is None:
        reset_at = _commandcode_reset_at(config.get("currentPeriodEnd"))
    window = _monthly_metrics(used, limit, percent, reset_at)
    base["status"] = "ok"
    base["windows"] = {"monthly": window}
    base["quota"] = dict(window)
    return base


def probe_grok_usage(
    model: str | None = None,
    timeout: float = 20.0,
    env: Mapping[str, str] | None = None,
    base_url: str | None = None,
) -> dict[str, Any]:
    """Read-only Grok billing usage for the shared ``cursor-grok`` pool.

    One GET, no retry. The base is ``base_url``, else the runtime's own
    ``GROK_WEB_BASE_URL`` env, else ``https://code.grok.com``. The bearer is
    ``GROK_API_KEY`` or the ``grok login`` session key in ``~/.grok/auth.json``.
    This function does not write a file, does not spawn a binary, and does
    not raise.
    """
    model_text = model.strip() if isinstance(model, str) else None
    try:
        return _probe_grok_usage(model_text, timeout, env, base_url)
    except Exception:
        return _grok_envelope(model_text, "error", "probe failed")


def _probe_grok_usage(
    model: str | None,
    timeout: float,
    env: Mapping[str, str] | None,
    base_url: str | None,
) -> dict[str, Any]:
    source: Mapping[str, str] = os.environ if env is None else env
    key = read_grok_api_key(source)
    if not key:
        return _grok_envelope(model, "key_missing", "GROK_API_KEY is not set and no grok login key is stored")
    override = source.get("GROK_WEB_BASE_URL")
    root = (base_url or (override.strip() if isinstance(override, str) else "") or GROK_BILLING_BASE).rstrip("/")
    status, body = _usage_get(
        root + GROK_BILLING_PATH,
        {"Authorization": "Bearer " + key, "Accept": "application/json",
         "x-grok-client-mode": "billing", "User-Agent": "kaola-quota"},
        max(0.1, float(timeout)),
    )
    if status is None:
        reason = "timeout" if body == "timeout" else "network failure"
        return _grok_envelope(model, "unavailable", reason)
    if status == 401 or status == 403:
        return _grok_envelope(model, "login_required", _http_reason(status, body))
    if status != 200:
        return _grok_envelope(model, "unavailable", _http_reason(status, body))
    text = body.decode("utf-8") if isinstance(body, (bytes, bytearray)) else ""
    return parse_grok_usage(text, model=model)


COMMANDCODE_API_BASE = "https://api.commandcode.ai"
COMMANDCODE_KEY_NAME = "COMMANDCODE_API_KEY"
COMMANDCODE_PACKAGE = "dsh:commandcode"
COMMANDCODE_CREDITS_PATH = "/alpha/billing/credits"
COMMANDCODE_SUBSCRIPTIONS_PATH = "/alpha/billing/subscriptions"
COMMANDCODE_SUMMARY_PATH = "/alpha/usage/summary"
# Published monthly grants for planId values the subscriptions route returns.
# Amounts are the Command Code usage-limits table (Go 10, GOAT 70, Pro 80,
# Max 10x 150, Max 20x 300, Team Pro 40). Any other id leaves the monthly
# limit unknown. The remaining balance is never turned into a limit.
COMMANDCODE_PLAN_GRANTS: dict[str, int] = {
    "individual-go": 10,
    "individual-goat": 70,
    "individual-pro-v1": 80,
    "individual-max": 150,
    "individual-ultra": 300,
    "teams-pro": 40,
}
_COMMANDCODE_GRANT_FIELDS = ("grant", "creditGrant", "includedCredits", "monthlyGrant", "planCredits")
_COMMANDCODE_WINDOW_ORDER = ("5h", "weekly", "monthly")
_PLAN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,80}$")


class _CommandCodeNoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


def _commandcode_number(value: Any) -> int | float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def _commandcode_home(env: Mapping[str, str]) -> Path:
    raw = env.get("DSH_HOME")
    if isinstance(raw, str) and raw.strip():
        return Path(raw).expanduser()
    home = env.get("HOME")
    base = Path(home).expanduser() if isinstance(home, str) and home.strip() else Path.home()
    return base / ".dsh"


def _read_limited(path: Path, limit: int = 65536) -> str | None:
    try:
        return path.read_bytes()[:limit].decode("utf-8", errors="replace")
    except OSError:
        return None


def _dotenv_named(text: str, name: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("export "):
            stripped = stripped[len("export "):].strip()
        key, separator, raw = stripped.partition("=")
        if not separator or key.strip() != name:
            continue
        value = raw.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        value = value.strip()
        return value or None
    return None


def _yaml_scalar(raw: str) -> str | None:
    if raw == "" or raw in {"~", "null", "Null", "NULL"}:
        return None
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "'\"":
        raw = raw[1:-1]
    elif " #" in raw:
        raw = raw.split(" #", 1)[0].rstrip()
    raw = raw.strip()
    return raw or None


def _credentials_ref(text: str, name: str) -> str | None:
    in_refs = False
    refs_indent = -1
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()
        if not in_refs:
            if stripped == "refs:" or stripped.startswith("refs:"):
                in_refs = True
                refs_indent = indent
            continue
        if indent <= refs_indent:
            in_refs = False
            continue
        key, separator, raw = stripped.partition(":")
        if separator and key.strip() == name:
            return _yaml_scalar(raw.strip())
    return None


def read_commandcode_api_key(env: Mapping[str, str] | None = None) -> str | None:
    """``COMMANDCODE_API_KEY`` from the process env, then dsh ``.env``, then ``refs:``.

    A non-empty ``DSH_HOME`` replaces ``~/.dsh`` and does not fall back to it.
    The returned string is for the request header only. Callers must not log it.
    """
    source: Mapping[str, str] = os.environ if env is None else env
    direct = source.get(COMMANDCODE_KEY_NAME)
    if isinstance(direct, str) and direct.strip():
        return direct.strip()
    home = _commandcode_home(source)
    dotenv = _read_limited(home / ".env")
    if dotenv:
        found = _dotenv_named(dotenv, COMMANDCODE_KEY_NAME)
        if found:
            return found
    credentials = _read_limited(home / ".credentials.yaml")
    if credentials:
        found = _credentials_ref(credentials, COMMANDCODE_KEY_NAME)
        if found and found.strip():
            return found.strip()
    return None


def _commandcode_reset_at(value: Any) -> str | None:
    """Epoch milliseconds, or an ISO timestamp, as ``YYYY-MM-DDTHH:MM:SSZ``.

    Zero and missing values are null. This is the Antigravity ``reset_at`` form.
    """
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        if value <= 0 or value < 1e11:
            return None
        try:
            stamp = datetime.fromtimestamp(float(value) / 1000.0, timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
        return stamp.strftime("%Y-%m-%dT%H:%M:%SZ")
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        stamp = datetime.fromisoformat(text)
    except ValueError:
        return None
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return stamp.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _commandcode_metrics(
    name: str,
    used: int | float,
    cap: int | float,
    exceeded: bool,
    reset_at: str | None,
) -> dict[str, Any]:
    rem_fraction = None
    used_fraction = None
    rem_pct = None
    used_pct = None
    if isinstance(cap, (int, float)) and not isinstance(cap, bool) and cap > 0:
        rem_fraction = max(0.0, min(1.0, (float(cap) - float(used)) / float(cap)))
        used_fraction = max(0.0, min(1.0, 1.0 - rem_fraction))
        rem_pct = round(rem_fraction * 100.0, 2)
        used_pct = round(used_fraction * 100.0, 2)
    if exceeded and rem_fraction is not None:
        rem_fraction = 0.0
        used_fraction = 1.0
        rem_pct = 0.0
        used_pct = 100.0
    return {
        "window": name,
        "used": used,
        "limit": cap,
        "used_percent": used_pct,
        "remaining_percent": rem_pct,
        "remaining_fraction": rem_fraction,
        "used_fraction": used_fraction,
        "reset_at": reset_at,
        "exceeded": exceeded,
    }


def _commandcode_limit_window(name: str, raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    used = _commandcode_number(raw.get("used"))
    cap = _commandcode_number(raw.get("cap"))
    if used is None or cap is None:
        return None
    return _commandcode_metrics(
        name,
        used,
        cap,
        raw.get("exceeded") is True,
        _commandcode_reset_at(raw.get("resetAt")),
    )


def _commandcode_plan_id(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text or "@" in text or _PLAN_ID.fullmatch(text) is None:
        return None
    return text


def _commandcode_subscription(payload: dict[str, Any] | None) -> tuple[str | None, str | None, int | float | None]:
    if not isinstance(payload, dict):
        return None, None, None
    data = payload.get("data")
    source = data if isinstance(data, dict) else payload
    plan_id = _commandcode_plan_id(source.get("planId"))
    if plan_id is None:
        plan_id = _commandcode_plan_id(source.get("plan_id"))
    period_end = _commandcode_reset_at(source.get("currentPeriodEnd"))
    if period_end is None:
        period_end = _commandcode_reset_at(source.get("current_period_end"))
    grant = None
    for field in _COMMANDCODE_GRANT_FIELDS:
        number = _commandcode_number(source.get(field))
        if number is not None and number >= 0:
            grant = number
            break
    return plan_id, period_end, grant


def _commandcode_monthly_limit(plan_id: str | None, grant: int | float | None) -> int | float | None:
    if grant is not None:
        return grant
    if not plan_id:
        return None
    return COMMANDCODE_PLAN_GRANTS.get(plan_id.lower())


def _commandcode_monthly_window(
    remaining: int | float | None,
    limit: int | float | None,
    reset_at: str | None,
) -> dict[str, Any]:
    if remaining is None or limit is None or limit <= 0:
        return {
            "window": "monthly",
            "used": None,
            "limit": limit,
            "used_percent": None,
            "remaining_percent": None,
            "remaining_fraction": None,
            "used_fraction": None,
            "reset_at": reset_at,
            "exceeded": False,
        }
    used = limit - remaining
    if used < 0:
        used = 0
    return _commandcode_metrics("monthly", used, limit, remaining <= 0, reset_at)


def _commandcode_period(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    data = payload.get("data")
    source = data if isinstance(data, dict) else payload
    period: dict[str, Any] = {}
    spend = _commandcode_number(source.get("totalCost"))
    requests = _commandcode_number(source.get("totalCount"))
    tokens = _commandcode_number(source.get("totalTokens"))
    if spend is not None:
        period["spend"] = spend
    if requests is not None:
        period["requests"] = requests
    if tokens is not None:
        period["tokens"] = tokens
    return period or None


def _most_constrained_window(windows: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    ranked: list[tuple[float, int, dict[str, Any]]] = []
    for index, name in enumerate(_COMMANDCODE_WINDOW_ORDER):
        window = windows.get(name)
        if not isinstance(window, dict):
            continue
        fraction = window.get("remaining_fraction")
        if isinstance(fraction, bool) or not isinstance(fraction, (int, float)):
            continue
        ranked.append((float(fraction), index, window))
    if not ranked:
        return None
    ranked.sort(key=lambda item: (item[0], item[1]))
    return dict(ranked[0][2])


def _commandcode_envelope(model: str | None, status: str, reason: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "platform": "dsh",
        "packageId": COMMANDCODE_PACKAGE,
        "provider": "commandcode",
        "status": status,
        "model": model,
        "quota": None,
        "windows": {},
    }
    if reason is not None:
        result["reason"] = reason
    return result


def _commandcode_get(url: str, key: str, timeout: float) -> tuple[int | None, bytes | str]:
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": "Bearer " + key,
            "Accept": "application/json",
            "User-Agent": "kaola-quota",
        },
        method="GET",
    )
    opener = urllib.request.build_opener(_CommandCodeNoRedirect)
    try:
        with opener.open(request, timeout=timeout) as response:
            status = getattr(response, "status", None) or response.getcode()
            return int(status), response.read(1_000_000)
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read(64_000)
        except Exception:
            body = b""
        return int(exc.code), body
    except urllib.error.URLError as exc:
        reason = exc.reason
        text = str(reason).lower()
        if isinstance(reason, (TimeoutError, socket.timeout)) or "timed out" in text:
            return None, "timeout"
        return None, "network"
    except (TimeoutError, socket.timeout):
        return None, "timeout"
    except OSError:
        return None, "network"


def _commandcode_json(body: bytes | str) -> dict[str, Any] | None:
    if not isinstance(body, (bytes, bytearray)):
        return None
    try:
        payload = json.loads(bytes(body).decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _upgrade_required(body: bytes | str) -> bool:
    payload = _commandcode_json(body)
    if not isinstance(payload, dict):
        return False

    def token(value: Any, depth: int = 0) -> bool:
        if depth > 3:
            return False
        if value == "upgrade_required":
            return True
        if isinstance(value, dict):
            return any(token(value.get(key), depth + 1) for key in ("error", "code", "type", "reason", "message"))
        return False

    return token(payload)


def _http_reason(status: int, body: bytes | str) -> str:
    if status == 403 and _upgrade_required(body):
        return "upgrade_required"
    return f"http {status}"


def _commandcode_selected(catalog: Catalog, model: str | None) -> bool:
    if catalog.platform != "dsh" or not isinstance(model, str) or not model.strip():
        return False
    return resolve_model(catalog, model).get("packageId") == COMMANDCODE_PACKAGE


def probe_commandcode_usage(
    model: str | None = None,
    timeout: float = 20.0,
    env: Mapping[str, str] | None = None,
    base_url: str = COMMANDCODE_API_BASE,
) -> dict[str, Any]:
    """Read-only Command Code usage for package ``dsh:commandcode``.

    One attempt per route, no retry. Optional subscription and summary failures
    omit ``plan`` and ``period``. The key and every field other than the named
    billing fields are dropped before the result is returned. This function
    does not write a file and does not raise.
    """
    model_text = model.strip() if isinstance(model, str) else None
    try:
        return _probe_commandcode_usage(model_text, timeout, env, base_url)
    except Exception:
        return _commandcode_envelope(model_text, "error", "probe failed")


def _probe_commandcode_usage(
    model: str | None,
    timeout: float,
    env: Mapping[str, str] | None,
    base_url: str,
) -> dict[str, Any]:
    key = read_commandcode_api_key(env)
    if not key:
        return _commandcode_envelope(model, "key_missing", "COMMANDCODE_API_KEY is not set")
    limit = max(0.1, float(timeout))
    root = (base_url or COMMANDCODE_API_BASE).rstrip("/")
    status, body = _commandcode_get(root + COMMANDCODE_CREDITS_PATH, key, limit)
    if status is None:
        reason = body if body in {"timeout", "network"} else "network"
        if reason == "network":
            reason = "network failure"
        return _commandcode_envelope(model, "unavailable", str(reason))
    if status != 200:
        return _commandcode_envelope(model, "unavailable", _http_reason(status, body))
    payload = _commandcode_json(body)
    windows_raw = payload.get("windowLimits") if isinstance(payload, dict) else None
    if not isinstance(windows_raw, dict):
        return _commandcode_envelope(model, "unavailable", "response shape changed")
    five = _commandcode_limit_window("5h", windows_raw.get("fiveHour"))
    weekly = _commandcode_limit_window("weekly", windows_raw.get("weekly"))
    if five is None and weekly is None:
        return _commandcode_envelope(model, "unavailable", "response shape changed")
    credits_raw = payload.get("credits") if isinstance(payload, dict) else None
    credits_raw = credits_raw if isinstance(credits_raw, dict) else {}
    monthly_remaining = _commandcode_number(credits_raw.get("monthlyCredits"))
    purchased = _commandcode_number(credits_raw.get("purchasedCredits"))
    free = _commandcode_number(credits_raw.get("freeCredits"))

    plan_id = None
    period_end = None
    grant = None
    sub_status, sub_body = _commandcode_get(root + COMMANDCODE_SUBSCRIPTIONS_PATH, key, limit)
    if sub_status == 200:
        plan_id, period_end, grant = _commandcode_subscription(_commandcode_json(sub_body))
    period = None
    sum_status, sum_body = _commandcode_get(root + COMMANDCODE_SUMMARY_PATH, key, limit)
    if sum_status == 200:
        period = _commandcode_period(_commandcode_json(sum_body))

    monthly_limit = _commandcode_monthly_limit(plan_id, grant)
    windows: dict[str, dict[str, Any]] = {}
    if five is not None:
        windows["5h"] = five
    if weekly is not None:
        windows["weekly"] = weekly
    windows["monthly"] = _commandcode_monthly_window(monthly_remaining, monthly_limit, period_end)
    result = _commandcode_envelope(model, "ok")
    result["windows"] = windows
    result["quota"] = _most_constrained_window(windows)
    result["credits"] = {"monthly": monthly_remaining, "purchased": purchased, "free": free}
    plan: dict[str, Any] = {}
    if plan_id:
        plan["id"] = plan_id
    if period_end:
        plan["period_end"] = period_end
    if plan:
        result["plan"] = plan
    if period:
        result["period"] = period
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Quota package catalog, model->package resolution, and live usage probe."
    )
    parser.add_argument("--platform", default="antigravity", choices=PLATFORM_ORDER)
    parser.add_argument("--model", default=None, help="Optional model id to resolve or select usage group")
    parser.add_argument("--probe", action="store_true", help="Probe live runtime usage when supported")
    parser.add_argument("--binary", default=None, help="Override CLI binary path for --probe")
    parser.add_argument("--timeout", type=float, default=20.0, help="Timeout in seconds for --probe")
    args = parser.parse_args(argv)

    catalog = load_catalog(args.platform)
    output: dict[str, Any] = {
        "platform": args.platform,
        "packages": catalog.public_packages(),
    }
    if args.model is not None:
        output["resolved"] = resolve_model(catalog, args.model)
    if args.probe:
        if args.platform == "antigravity":
            output["usage"] = probe_antigravity_usage(
                binary=args.binary,
                model=args.model,
                timeout=args.timeout,
            )
        elif args.platform == "cursor-cli":
            output["usage"] = probe_cursor_usage(
                model=args.model,
                timeout=args.timeout,
            )
        elif args.platform == "grok":
            output["usage"] = probe_grok_usage(
                model=args.model,
                timeout=args.timeout,
            )
        elif _commandcode_selected(catalog, args.model):
            output["usage"] = probe_commandcode_usage(
                model=args.model,
                timeout=args.timeout,
            )
        else:
            output["usage"] = {
                "platform": args.platform,
                "status": "unsupported",
                "error": f"live CLI probe in kaola-quota.py is only implemented for antigravity (got {args.platform})",
            }
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
