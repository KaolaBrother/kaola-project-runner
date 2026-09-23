#!/usr/bin/env python3
"""Quota package catalog and model→package resolution (Issue #148).

Platform manifests store two JSON documents as ordinary JSON strings
(``parse_manifest`` accepts only strings):

``quota_packages``
    A JSON array. Each object has ``id`` (``^[a-z][a-z0-9_-]*$``), ``name``
    (non-empty string), optional ``binds_models`` (bool, default true), and
    optional ``windows`` (null or an array of non-empty strings). No other
    keys. ``binds_models: false`` is a balance the Usage page can list and
    that a ``native_field`` rule may name, and that ``single`` / ``explicit``
    / ``provider_prefix`` must not target. ``windows`` is omitted until a
    window fact is verified; consumers then see null.

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
      with no segment is unmapped.
    * ``native_field`` — ``{"kind","field","values","absent"?}``. ``values``
      maps an upstream field spelling to a package token. A missing, null,
      or empty field uses ``absent`` when that key names a package, and is
      unmapped when ``absent`` is omitted. A present value that is not in
      ``values``, or a list whose members do not all name the same package,
      is unmapped. With no row (the static query), the field is not exposed,
      so ``absent`` applies.

A match returns the consumer id ``<platform>:<token>``. A miss is
``packageId: null`` and ``status: "unmapped"``. Nothing substitutes another
package. Package tokens and rule targets are checked when the manifest loads.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


RULE_KINDS = ("single", "provider_prefix", "native_field", "explicit")
PLATFORM_ORDER = (
    "claude-code", "codex", "cursor-cli", "devin", "droid",
    "dsh", "grok", "kimi-cli", "opencode", "zcode",
)
PACKAGE_KEYS = {"id", "name", "binds_models", "windows"}
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
        packages.append({
            "id": token,
            "name": name,
            "binds_models": binds,
            "windows": windows,
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
        _exact_keys(document, {"kind", "providers", "gaps"})
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
        return {"kind": kind, "providers": normalized_providers, "gaps": gap_set}
    _exact_keys(document, {"kind", "field", "values", "absent"})
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
    rule: dict[str, Any] = {"kind": kind, "field": field, "values": normalized_values}
    if "absent" in document and document.get("absent") is not None:
        rule["absent"] = _binding_token(by_id, document.get("absent"), "native_field.absent")
    return rule


def _exact_keys(document: dict[str, Any], allowed: set[str]) -> None:
    # ``gaps`` and ``absent`` are optional. A present null ``absent`` is the
    # same as omitting it. ``gaps`` may be omitted.
    optional = {"gaps", "absent"}
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
        self.rule = rule
        self.model_config_id = model_config_id

    def qualified(self, token: str) -> str:
        return f"{self.platform}:{token}"

    def public_packages(self) -> list[dict[str, Any]]:
        """Consumer rows. ``id`` is ``<platform>:<token>``; ``windows`` is null when unseeded."""
        return [
            {
                "id": self.qualified(package["id"]),
                "name": package["name"],
                "windows": package["windows"],
                "binds_models": package["binds_models"],
            }
            for package in self.packages
        ]


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
    """``{packageId, status}``. ``packageId`` is ``<platform>:<token>`` or null."""
    text = model_id.strip() if isinstance(model_id, str) else ""
    token = _resolve_token(catalog, text, row if isinstance(row, dict) else None)
    if token is None:
        return {"packageId": None, "status": "unmapped"}
    return {"packageId": catalog.qualified(token), "status": "mapped"}


def _resolve_token(catalog: Catalog, model_id: str, row: dict[str, Any] | None) -> str | None:
    rule = catalog.rule
    kind = rule["kind"]
    if kind == "single":
        return rule["package"] if model_id else None
    if kind == "explicit":
        return rule["map"].get(model_id)
    if kind == "provider_prefix":
        segment = provider_segment(model_id)
        if segment is None or segment in rule["gaps"]:
            return None
        return rule["providers"].get(segment)
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
    row["quotaPool"] = resolved["packageId"]
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
