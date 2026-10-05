#!/usr/bin/env python3
"""One dispatch/collect entry for an adopted research, QA, or report plan.

The plan is input. The printed index correlates Runner receipts. It is not a
mission ledger, a scheduler, or a permission engine. Kaola-Workflow records
and the existing authorization stay authoritative.

`project` derives a compact capability summary and the eligible-candidate
projection from that authorization plus the platform manifests.
`execute` admits an adopted plan through each platform's existing
runtime-tmux.sh and does not call that admission a result.
`collect` later reads Runner status and capture receipts and correlates
completed results. `snapshot` writes the heartbeat file so its nested body is
one JSON object.
`state` maintains the structured current state in that same heartbeat file
(Issue #255): record updates with revision conflicts, retirement, role views,
consistency checks, the static timer entry check, and legacy-format migration.
It holds current responsibilities and references only, never history.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
import importlib.util
from pathlib import Path
from typing import Any


def _load_record_contract():
    path = Path(__file__).resolve().parent / "kaola-record-contract.py"
    spec = importlib.util.spec_from_file_location("kaola_record_contract", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"missing record contract: {path}")
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


RECORD = _load_record_contract()


SCOPES = frozenset({"research", "qa", "report", "implementation"})
# Only an implementation plan may declare repository mutation; the worker's
# own Workflow owns its claim, worktree, ledger and finalize.
MUTATING_SCOPES = frozenset({"implementation"})
LAUNCH_OVERRIDE_KEYS = frozenset({"model", "effort"})
RECORDED_OVERRIDE_KEYS = LAUNCH_OVERRIDE_KEYS | frozenset({"task_scope"})
SESSION_OK = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")
GRANT_STATES = frozenset({"granted", "paused", "revoked", "excluded"})
GRANT_LIFETIMES = frozenset({"task", "standing"})
EXPERT_WITHHELD_REASONS = frozenset({"lifetime-unreadable", "expiry-unreadable", "expired"})
LEGACY_LIVE_STATE = re.compile(r"^\d+\s+live$")
COVERAGE = ("in-flight", "returned", "failed", "unknown", "not-run")
RUNNER_TIMEOUT = float(os.environ.get("KAOLA_DISPATCH_RUNNER_TIMEOUT", "120"))
INDEX_LOCK = threading.Lock()
SIDEAGENT_ROLES = ("sideagent", "sidekick")
# Issue #255 lifecycle state. The file keeps its path and its `body` string, so
# a holder that predates this format still injects `body` (now the projected
# Host view). A holder that predates it also reads at most 65536 bytes of the
# whole file; a newer holder advertises STATE_CAPABILITY and reads the larger
# file while still injecting at most HOST_VIEW_MAX_BYTES of `body`.
STATE_SCHEMA = "kaola-heartbeat-prompt/2"
LEGACY_STATE_SCHEMA = "kaola-heartbeat-prompt/1"
STATE_CAPABILITY = "heartbeat-state/2"
LEGACY_READER_MAX_BYTES = 65536
STATE_FILE_MAX_BYTES = 1048576
HOST_VIEW_MAX_BYTES = 65536
RECORD_KINDS = ("tasks", "holds", "alerts", "decisions")
SECTIONS = ("project", "authorization", "sideagent", "recovery", "unverified")
TASK_STAGES = ("todo", "doing", "review", "closeout", "done")
ALERT_LEVELS = ("watch", "warn", "severe")
VERDICTS = ("accepted", "partial", "repair", "cancelled")
BINDING_STATES = ("active", "replacing", "failed", "ended")
DECISION_OWNERS = ("host", "delegator", "user")
WRITER_ROLES = ("host", "sideagent")
HOST_OWNED_TASK_FIELDS = ("goal", "scope", "acceptance", "needs", "depends", "source", "keep_open",
                          "dispositions")
DISPOSITIONS = ("accepted", "repair", "cancelled", "superseded", "handed-off")
TOMBSTONE_CAP = 64
CHECK_PREFIX = "chk:"
USER_REQUIREMENT_MARKERS = ("<!-- KPR-USER-REQUIREMENTS-START -->",
                            "<!-- KPR-USER-REQUIREMENTS-END -->")
USER_REQUIREMENT_HEADINGS = ("user requirements", "user special requirements", "用户特殊要求")
# The whole native timer body: the Skill entry line and one locator sentence.
# templates/kaola-delegator/references/snapshot.md quotes the same sentence.
TIMER_LOCATOR = ("Kaola-Delegator inquiry: read {repo}/.kaola/delegator-heartbeat.json "
                 "on target {target} and run the loaded Skill's standard inquiry.")


def emit(payload: dict[str, Any], code: int = 0) -> int:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2))
    sys.stdout.write("\n")
    return code


def fail(reason: str, detail: str | None = None) -> int:
    payload: dict[str, Any] = {"result": "error", "reason": reason}
    if detail:
        payload["detail"] = detail
    return emit(payload, 2)


def load_object(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path}: JSON must be one object")
    return data


def parse_flat_yaml(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw or raw[0] in " \t#" or raw.lstrip().startswith("#"):
            continue
        key, sep, value = raw.partition(":")
        if not sep:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                parsed = value[1:-1]
            value = parsed if isinstance(parsed, str) else value[1:-1]
        data[key.strip()] = value
    return data


def catalog_from_files(paths: list[Path]) -> dict[str, dict[str, Any]]:
    catalog: dict[str, dict[str, Any]] = {}
    for path in paths:
        manifest = parse_flat_yaml(path)
        platform = manifest.get("id") or ""
        if not platform:
            continue
        tiers = ["default"]
        tiers.extend(
            part.strip()
            for part in (manifest.get("named_tiers") or "").split(",")
            if part.strip()
        )
        for tier in tiers:
            prefix = tier.replace("-", "_")
            klass = manifest.get(f"{prefix}_model_class")
            if klass not in {"Expert", "Elite", "Worker"}:
                continue
            preset = f"{platform}/{tier}"
            if preset in catalog:
                raise ValueError(f"duplicate preset {preset}")
            catalog[preset] = {
                "id": preset,
                "platform": platform,
                "tier": tier,
                "class": klass,
                "profile": manifest.get(f"{prefix}_model_profile") or "",
                "selection": {
                    "model_name": manifest.get(f"{prefix}_model_name") or "",
                    "model_id": manifest.get(f"{prefix}_model_id") or "",
                    "parameters": manifest.get(f"{prefix}_model_parameters") or "",
                    "effort": manifest.get(f"{prefix}_model_effort") or "",
                },
            }
    if not catalog:
        raise ValueError("no presets in platform manifests")
    return catalog


def platform_paths(script: Path, explicit: str | None) -> list[Path]:
    if explicit:
        directory = Path(explicit)
        files = sorted(directory.glob("*.yaml"))
        if not files:
            raise ValueError(f"no manifests in {directory}")
        return files
    repo_platforms = script.resolve().parent.parent / "platforms"
    if repo_platforms.is_dir():
        files = sorted(repo_platforms.glob("*.yaml"))
        if files:
            return files
    skills = script.resolve().parent.parent.parent
    files = sorted(skills.glob("*-kaola-project-runner/scripts/platform.yaml"))
    if not files:
        raise ValueError("no platform manifests found")
    return files


def authorization_object(doc: dict[str, Any]) -> dict[str, Any]:
    """Direct authorization, or the heartbeat envelope this entry's snapshot writes.

    The envelope is ``{"body": "<state JSON>"}``. A body that does not parse
    to an object with an ``authorization`` object is an error. A direct
    ``authorization`` string or null is the same error. A document with no
    ``authorization`` key is the authorization itself. Neither path is
    silently read as an empty grant list. A lifecycle-state file (Issue #255)
    is read from its structured ``state``, not from the projected ``body``.
    """
    if doc.get("schema") == STATE_SCHEMA:
        state = doc.get("state")
        nested = state.get("authorization") if isinstance(state, dict) else None
        if not isinstance(nested, dict):
            raise ValueError("heartbeat authorization is missing")
        return nested
    if "body" in doc:
        body = doc.get("body")
        if not isinstance(body, str) or not body.strip():
            raise ValueError("heartbeat body must be a non-empty JSON string")
        try:
            state = json.loads(body)
        except json.JSONDecodeError as exc:
            raise ValueError("heartbeat body is not JSON") from exc
        if not isinstance(state, dict):
            raise ValueError("heartbeat body must be a JSON object")
        nested = state.get("authorization")
        if not isinstance(nested, dict):
            raise ValueError("heartbeat authorization is missing")
        return nested
    if "authorization" in doc:
        nested = doc.get("authorization")
        if not isinstance(nested, dict):
            raise ValueError("authorization must be an object")
        return nested
    return doc


def as_id_list(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError("id lists must be arrays of preset id strings")
    return list(value)


def normalize_grants(auth: dict[str, Any]) -> list[dict[str, Any]]:
    # `rows` is not a grant list. A catalog-shaped body must not become seats.
    raw = auth.get("grants")
    if raw is None:
        raw = []
    if not isinstance(raw, list):
        raise ValueError("grants must be an array")
    grants = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise ValueError("each grant needs a string id")
        preset = item["id"]
        if preset in seen:
            raise ValueError(f"duplicate grant {preset}")
        seen.add(preset)
        if "state" not in item:
            state = "granted"
        else:
            state = item.get("state")
        if not isinstance(state, str):
            raise ValueError(f"{preset}: state must be a string")
        state = state.strip()
        if state not in GRANT_STATES:
            # Older snapshots stored a live count in state ("0 live"). Any other
            # word, including expired, withdrawn, unknown, or prose, is unreadable.
            # The Host judges it. This entry does not treat it as granted.
            state = "granted" if LEGACY_LIVE_STATE.fullmatch(state) else "unreadable"
        switch = item.get("model_switch")
        if switch is not None and not isinstance(switch, bool):
            raise ValueError(f"{preset}: model_switch must be a boolean")
        count = item.get("count")
        if count is not None and (not isinstance(count, int) or isinstance(count, bool) or count < 0):
            raise ValueError(f"{preset}: count must be a non-negative integer")
        shared = item.get("shared_seat")
        if shared is not None and not isinstance(shared, str):
            raise ValueError(f"{preset}: shared_seat must be a string")
        special = item.get("special_requirements")
        if special is not None and not isinstance(special, dict):
            raise ValueError(f"{preset}: special_requirements must be an object")
        lifetime = item.get("lifetime")
        if lifetime is not None and not isinstance(lifetime, str):
            raise ValueError(f"{preset}: lifetime must be a string")
        expires = item.get("expires")
        if expires is not None and not isinstance(expires, str):
            raise ValueError(f"{preset}: expires must be a string")
        grant = {
            "id": preset,
            "state": state,
            "count": count,
            "shared_seat": shared,
            "special_requirements": special,
            "model_switch": switch is True,
        }
        # Carried only when stated, so a grant without them projects as before.
        if lifetime is not None:
            grant["lifetime"] = lifetime
        if expires is not None:
            grant["expires"] = expires
        grants.append(grant)
    return grants


def parse_expiry(value: str) -> datetime | None:
    """An ISO-8601 instant with an offset, else None. `Z` is accepted for 3.10."""
    text = value.strip()
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    try:
        moment = datetime.fromisoformat(text)
    except ValueError:
        return None
    return moment if moment.tzinfo is not None and moment.utcoffset() is not None else None


def availability_map(doc: dict[str, Any] | None) -> dict[str, str]:
    if doc is None:
        return {}
    mapped: dict[str, str] = {}
    for label in ("present", "absent"):
        for preset in as_id_list(doc.get(label)):
            mapped[preset] = label
    unknown = doc.get("unknown")
    if unknown is not None:
        for preset in as_id_list(unknown):
            mapped.setdefault(preset, "unknown")
    return mapped


def grant_index(grants: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in grants}


def shared_seat_capacities(grants: list[dict[str, Any]]) -> dict[str, int]:
    """One capacity per shared label, without adding the same pool per grant."""
    capacities: dict[str, int] = {}
    for grant in grants:
        seat = grant.get("shared_seat")
        if grant.get("state") != "granted" or not isinstance(seat, str) or not seat:
            continue
        count = grant.get("count")
        capacity = count if isinstance(count, int) and not isinstance(count, bool) else 1
        capacities[seat] = max(capacities.get(seat, capacity), capacity)
    return capacities


def eligibility(
    catalog: dict[str, dict[str, Any]],
    auth: dict[str, Any],
    grants: list[dict[str, Any]],
    available: dict[str, str],
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    by_id = grant_index(grants)
    excluded = set(as_id_list(auth.get("exclusions")))
    paused = set(as_id_list(auth.get("paused")))
    revoked = set(as_id_list(auth.get("revoked")))
    candidates = []
    withheld = []
    considered: set[str] = set()

    def withhold(preset: str, reason: str) -> None:
        if preset not in considered:
            considered.add(preset)
            withheld.append({"id": preset, "reason": reason})

    interesting = set(catalog) | set(by_id) | excluded | paused | revoked
    for preset in sorted(interesting):
        row = catalog.get(preset)
        grant = by_id.get(preset)
        if row is None:
            if grant is not None or preset in excluded or preset in paused or preset in revoked:
                withhold(preset, "preset-unresolved")
            continue
        state = grant["state"] if grant else None
        if preset in excluded or state == "excluded":
            withhold(preset, "excluded")
            continue
        if preset in revoked or state == "revoked":
            withhold(preset, "revoked")
            continue
        if preset in paused or state == "paused":
            withhold(preset, "paused")
            continue
        if state not in (None, "granted"):
            withhold(preset, "state-unreadable")
            continue
        pool = row["class"] == "Worker"
        granted = state == "granted"
        if not pool and not granted:
            continue
        presence = available.get(preset, "unknown")
        if presence == "absent":
            withhold(preset, "absent")
            continue
        expert = {}
        if row["class"] == "Expert" and granted:
            # Only the grant's own words make an Expert grant standing. The
            # tool never infers one and never mutates the grant.
            lifetime = grant.get("lifetime")
            lifetime = "task" if lifetime is None else lifetime.strip()
            if lifetime not in GRANT_LIFETIMES:
                withhold(preset, "lifetime-unreadable")
                continue
            expires = grant.get("expires")
            if expires is not None:
                moment = parse_expiry(expires)
                if moment is None:
                    withhold(preset, "expiry-unreadable")
                    continue
                if moment <= datetime.now(timezone.utc):
                    withhold(preset, "expired")
                    continue
                expert["expires"] = expires
            expert["lifetime"] = lifetime
        special = grant.get("special_requirements") if grant else None
        candidate = {
            "id": preset,
            "platform": row["platform"],
            "tier": row["tier"],
            "class": row["class"],
            "profile": row["profile"],
            "selection": dict(row["selection"]),
            "availability": presence,
            "state": "granted" if granted else "default-pool",
            "pool": pool,
            "shared_seat": grant.get("shared_seat") if grant else None,
            "count": grant.get("count") if grant else None,
            "model_switch": bool(grant.get("model_switch")) if grant else False,
            **expert,
        }
        if special:
            candidate["special_requirements"] = special
            candidate["restrictions"] = [special]
        else:
            candidate["restrictions"] = []
        candidates.append(candidate)
    candidates.sort(key=lambda item: item["id"])
    return candidates, withheld


def capability_summary(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """Eligible preset ids. Profiles stay on each candidate row.

    This does not read a capability out of profile wording. The Host writes
    the short capability paragraph and changes it only when a grant, profile,
    or availability fact changes.
    """
    shown: list[str] = []
    unknown: list[str] = []
    for item in candidates:
        preset = item["id"]
        if item.get("availability") == "absent":
            continue
        shown.append(preset)
        if item.get("availability") == "unknown":
            unknown.append(preset)
    text = "availability unknown: " + ", ".join(unknown) if unknown else ""
    return {"presets": shown, "text": text}


def command_project(args: argparse.Namespace) -> int:
    try:
        auth_doc = load_object(Path(args.authorization))
        auth = authorization_object(auth_doc)
        grants = normalize_grants(auth)
        available = availability_map(
            load_object(Path(args.availability)) if args.availability else None
        )
        catalog = catalog_from_files(platform_paths(Path(__file__), args.platforms))
        candidates, withheld = eligibility(catalog, auth, grants, available)
    except ValueError as exc:
        return fail("invalid-input", str(exc))
    if args.seats:
        if not args.repo:
            return fail("invalid-input", "--seats needs --repo")
        return project_seats(args, auth, grants, catalog, bound_sideagent(auth_doc))
    # Eligible ids only. The Host keeps the capability paragraph.
    return emit({
        "schema": "kaola-dispatch-project/1",
        "capability_summary": capability_summary(candidates),
        "candidates": candidates,
        "withheld": withheld,
    })


def observed_at() -> str:
    return datetime.now(timezone.utc).isoformat()


def project_seats(args: argparse.Namespace, auth: dict[str, Any],
                  grants: list[dict[str, Any]], catalog: dict[str, dict[str, Any]],
                  binding: dict[str, Any] | None = None) -> int:
    """Read the existing occupancy facts; report limits without deciding authority."""
    repo = str(Path(args.repo).resolve())
    unknown: list[str] = []
    skills = Path(args.skills_root) if args.skills_root else None
    try:
        rows, state = live_facts(args.live, repo, Path(__file__), skills)
    except ValueError as exc:
        rows, state = [], "unavailable"
        unknown.append(str(exc))
    items = {}
    if args.index:
        try:
            index = load_object(Path(args.index))
            if index.get("schema") != "kaola-dispatch-index/1" or not same_repo(index.get("repo"), repo):
                raise ValueError("index identity/schema differs")
            if not isinstance(index.get("items"), list):
                raise ValueError("index items unavailable")
            items = {item["item_id"]: item for item in index.get("items", [])
                     if isinstance(item, dict) and isinstance(item.get("item_id"), str)}
        except ValueError as exc:
            unknown.append(str(exc))
    bound = []
    sideagent_rows = []
    for row in rows:
        if row.get("state") == "stopped" or row.get("host_class") is True:
            continue
        if isinstance(row.get("repo"), str) and not same_repo(row["repo"], repo):
            continue
        if binding_row(binding, row):
            sideagent_rows.append({"session": row.get("session"), "platform": row.get("platform"),
                                   "holder_instance_id": row.get("holder_instance_id"),
                                   "state": row.get("state"), "seat_exempt": True})
            continue
        if (row.get("identity") != "verified" or not same_repo(row.get("repo"), repo)
                or not row.get("holder_instance_id") or not row.get("session")):
            unknown.append("unbound-live-row:" + str(row.get("session")))
            continue
        bound.append(row)
    resolved = resolve_live_presets(bound, repo, catalog, items,
                                   Path(args.skills_root) if args.skills_root else None,
                                   require_identity=True)
    used, elite, shared, unnamed = live_occupancy(bound, repo, catalog, grants, resolved)
    unknown.extend("preset-unresolved:" + grant["id"] for grant in grants if grant["id"] not in catalog)
    unknown.extend("preset-unknown:" + row["session"] for row in bound
                   if row["session"] not in resolved)
    if state != "known":
        unknown.append("live-source-unavailable")
    listed = None if args.live else acp_runner(Path(__file__), skills)
    return emit({
        "schema": "kaola-dispatch-seats/1", "repo": repo,
        "source": {"authorization": args.authorization, "live": args.live or (str(listed) if listed else None),
                   "index": args.index, "as_of": observed_at()},
        "unknown_reasons": unknown,
        "elite_cap": auth.get("elite_cap"), "observed_elite_expert": elite if state == "known" else None,
        "grants": [{**grant, "observed_live": used.get(grant["id"], 0) if state == "known" else None,
                    "occupancy_unknown": bool(unknown) or catalog.get(grant["id"], {}).get("platform") in unnamed,
                    "shared_occupied": grant.get("shared_seat") in shared if state == "known" else None}
                   for grant in grants],
        "sessions": [{"session": row["session"], "platform": row.get("platform"),
                      "holder_instance_id": row["holder_instance_id"], "state": row.get("state"),
                      "preset": resolved.get(row["session"]),
                      **({"role": row["session_role"]} if row.get("session_role") in SIDEAGENT_ROLES else {})}
                     for row in bound],
        "bound_sideagent": sideagent_rows or None,
    })


def present_value(value: Any) -> Any:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, str) and (not value.strip() or value.strip().lower() == "unknown"):
        return None
    return value


def application_of(receipt: dict[str, Any] | None) -> tuple[dict[str, Any] | None, str | None]:
    """Actual config application, never a resolved or requested value."""
    if not isinstance(receipt, dict):
        return None, None
    direct = receipt.get("config_application")
    if isinstance(direct, dict):
        return direct, "config_application"
    evidence = receipt.get("start_evidence")
    if isinstance(evidence, dict) and isinstance(evidence.get("config_application"), dict):
        return evidence["config_application"], "start_evidence.config_application"
    record = receipt.get("record")
    if isinstance(record, dict):
        saved = record.get("start_evidence")
        if isinstance(saved, dict) and isinstance(saved.get("config_application"), dict):
            return saved["config_application"], "record.start_evidence.config_application"
    return None, None


def advertised_of(receipt: dict[str, Any] | None) -> tuple[dict[str, Any], str | None]:
    if not isinstance(receipt, dict):
        return {}, None
    direct = receipt.get("effective_selection")
    if isinstance(direct, dict):
        return direct, "effective_selection"
    evidence = receipt.get("start_evidence")
    if isinstance(evidence, dict) and isinstance(evidence.get("effective_selection"), dict):
        return evidence["effective_selection"], "start_evidence.effective_selection"
    record = receipt.get("record")
    if isinstance(record, dict):
        saved = record.get("start_evidence")
        if isinstance(saved, dict) and isinstance(saved.get("effective_selection"), dict):
            return saved["effective_selection"], "record.start_evidence.effective_selection"
    return {}, None


def application_slot(block: dict[str, Any] | None, label: str) -> tuple[dict[str, Any] | None, str]:
    if not isinstance(block, dict):
        return None, "absent"
    slot = block.get(label)
    if not isinstance(slot, dict):
        return None, "absent"
    applied = slot.get("applied")
    if applied is True:
        return slot, "applied"
    if applied is False:
        return slot, "unapplied"
    return slot, "unknown"


def switch_authorized(preset: str, model: str, special: dict[str, Any],
                      auth: dict[str, Any], grant: dict[str, Any]) -> bool:
    """An item model override is not a grant. Owner structure is."""
    if isinstance(special, dict) and special.get("model") == model:
        return True
    if grant.get("model_switch") is True:
        return True
    switches = auth.get("model_switches")
    return isinstance(switches, list) and preset in switches


def model_match(requested: Any, actual: Any) -> bool:
    """Exact id, or ZCode's provider-qualified form of that same id.

    A slash inside a catalog id is part of the id. Only a backslash qualifier
    is stripped, so two routes that share a tail stay different.
    """
    if str(actual) == str(requested):
        return True
    if "\\" in str(actual):
        return str(actual).split("\\")[-1] == str(requested)
    return False


def field_verdict(requested: Any, actual: Any, *, model: bool = False) -> str:
    if requested is None:
        return "not-requested"
    if actual is None:
        return "unknown"
    matched = model_match(requested, actual) if model else str(actual) == str(requested)
    return "match" if matched else "mismatch"


def model_applied_verdict(requested: Any, slot: dict[str, Any] | None, state: str) -> tuple[str, Any]:
    """Return the verdict and the value that may be called applied.

    A mapped adapter value matches when its ``requested_id`` is the catalog id.
    An unapplied or refused value is never reported as applied.
    """
    if requested is None:
        return "not-requested", None
    if state == "absent" or slot is None:
        return "unknown", None
    if state == "unapplied":
        return "mismatch", None
    if state != "applied":
        return "unknown", None
    value = present_value(slot.get("value"))
    requested_id = present_value(slot.get("requested_id"))
    if slot.get("mapped") is True and requested_id is not None and model_match(requested, requested_id):
        return "match", requested_id
    if value is not None and model_match(requested, value):
        return "match", value
    if value is None and requested_id is None:
        return "unknown", None
    return "mismatch", value


def effort_applied_verdict(requested: Any, slot: dict[str, Any] | None, state: str) -> tuple[str, Any]:
    if requested is None:
        return "not-requested", None
    if state == "absent" or slot is None:
        return "unknown", None
    if state == "unapplied":
        return "mismatch", None
    if state != "applied":
        return "unknown", None
    value = present_value(slot.get("value"))
    if value is None:
        return "unknown", None
    return ("match" if str(value) == str(requested) else "mismatch"), value


def flag_of(receipt: dict[str, Any] | None, key: str) -> Any:
    if not isinstance(receipt, dict):
        return None
    if key in receipt:
        return receipt.get(key)
    evidence = receipt.get("start_evidence")
    if isinstance(evidence, dict) and key in evidence:
        return evidence.get(key)
    record = receipt.get("record")
    if isinstance(record, dict):
        saved = record.get("start_evidence")
        if isinstance(saved, dict) and key in saved:
            return saved.get(key)
    return None


def advertised_verdict(requested: Any, actual: Any, *, model: bool = False) -> str:
    """A non-string or non-matching advertisement is unknown, not a mismatch.

    List-shaped advertisements are left as the Runner sent them. This does not
    invent a second encoding.
    """
    if requested is None:
        return "not-requested"
    if not isinstance(actual, str) or not actual.strip() or actual.strip().lower() == "unknown":
        return "unknown"
    matched = model_match(requested, actual) if model else actual == str(requested)
    return "match" if matched else "unknown"


def selection_report(requested: dict[str, Any], receipt: dict[str, Any] | None) -> dict[str, Any]:
    block, source = application_of(receipt)
    model_slot, model_state = application_slot(block, "model")
    effort_slot, effort_state = application_slot(block, "effort")
    model_verdict, model_value = model_applied_verdict(requested.get("model_id"), model_slot, model_state)
    effort_verdict, effort_value = effort_applied_verdict(requested.get("effort"), effort_slot, effort_state)
    if flag_of(receipt, "model_verified") is False:
        model_verdict, model_value = "mismatch", None
    advertised_block, advertised_source = advertised_of(receipt)
    advertised = {
        "model_id": advertised_block.get("effective_model"),
        "effort": advertised_block.get("effective_effort"),
    }
    fields = {
        "model_id": {
            "applied": model_verdict,
            "advertised": advertised_verdict(requested.get("model_id"), advertised["model_id"], model=True),
        },
        "effort": {
            "applied": effort_verdict,
            "advertised": advertised_verdict(requested.get("effort"), advertised["effort"]),
        },
    }
    applied_sides = [field["applied"] for field in fields.values() if field["applied"] != "not-requested"]
    if any(side == "mismatch" for side in applied_sides):
        comparison = "mismatch"
    elif any(side == "unknown" for side in applied_sides):
        comparison = "unknown"
    else:
        comparison = "match"
    return {
        "requested": requested,
        "applied": {"model_id": model_value, "effort": effort_value},
        "applied_state": {"model_id": model_state, "effort": effort_state},
        "source": source,
        "advertised": advertised,
        "advertised_source": advertised_source,
        "fields": fields,
        "comparison": comparison,
    }


def applied_mismatch(report: dict[str, Any]) -> bool:
    return any(field["applied"] == "mismatch" for field in report["fields"].values())


def nested(receipt: dict[str, Any] | None, key: str) -> Any:
    if not isinstance(receipt, dict):
        return None
    if key in receipt and receipt.get(key) is not None:
        return receipt.get(key)
    record = receipt.get("record")
    if isinstance(record, dict) and record.get(key) is not None:
        return record.get(key)
    return None


def last_prompt(receipt: dict[str, Any] | None) -> dict[str, Any]:
    value = nested(receipt, "last_prompt")
    return value if isinstance(value, dict) else {}


def finger_norm(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.startswith("sha256:"):
        text = text[7:]
    return text or None


def fingers_equal(left: Any, right: Any) -> bool:
    seen = finger_norm(left)
    expected = finger_norm(right)
    return seen is not None and seen == expected


def fingerprint_of(receipt: dict[str, Any] | None) -> Any:
    direct = nested(receipt, "prompt_fingerprint")
    if isinstance(direct, str) and direct:
        return direct
    finger = last_prompt(receipt).get("fingerprint")
    return finger if isinstance(finger, str) and finger else None


def mutation_of(receipt: dict[str, Any] | None) -> Any:
    direct = nested(receipt, "mutation_status")
    if isinstance(direct, str):
        return direct
    nested_prompt = last_prompt(receipt).get("mutation_status")
    return nested_prompt if isinstance(nested_prompt, str) else None


def holder_of(receipt: dict[str, Any] | None) -> Any:
    value = nested(receipt, "holder_instance_id")
    return value if isinstance(value, str) and value else None


def repo_of(receipt: dict[str, Any] | None) -> Any:
    if not isinstance(receipt, dict):
        return None
    for key in ("canonical_repo", "repo"):
        value = receipt.get(key)
        if isinstance(value, str) and value:
            return value
    record = receipt.get("record")
    if isinstance(record, dict):
        for key in ("canonical_repo", "repo"):
            value = record.get(key)
            if isinstance(value, str) and value:
                return value
    return None


def session_absent(receipt: dict[str, Any] | None) -> bool:
    if not isinstance(receipt, dict):
        return False
    error = receipt.get("error")
    if isinstance(error, dict) and error.get("code") == "no-session":
        return True
    return receipt.get("reason") == "no-session"


def parse_stdout(text: str) -> dict[str, Any] | None:
    for line in reversed(text.splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def run_runner(script: Path, argv: list[str]) -> tuple[int | None, dict[str, Any] | None, str]:
    try:
        proc = subprocess.run(
            [str(script), *argv],
            capture_output=True,
            text=True,
            timeout=RUNNER_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return None, None, "timeout"
    except OSError as exc:
        return None, None, str(exc)
    return proc.returncode, parse_stdout(proc.stdout), (proc.stderr or "")[:240]


def evidence(receipt: dict[str, Any] | None, code: int | None, note: str = "") -> dict[str, Any]:
    body: dict[str, Any] = {
        "exit_code": code,
        "holder_instance_id": holder_of(receipt),
        "repo": repo_of(receipt),
        "prompt_fingerprint": fingerprint_of(receipt),
        "dispatch_event_cursor": nested(receipt, "dispatch_event_cursor"),
        "acp_session_id": nested(receipt, "acp_session_id"),
        "mutation_status": mutation_of(receipt),
        "outcome": receipt.get("outcome") if isinstance(receipt, dict) else None,
        "result": receipt.get("result") if isinstance(receipt, dict) else None,
    }
    if isinstance(receipt, dict) and isinstance(receipt.get("error"), dict):
        body["error_code"] = receipt["error"].get("code")
    if note:
        body["note"] = note
    return body


def receipt_unreadable(code: int | None, receipt: dict[str, Any] | None, note: str = "") -> str | None:
    if note == "timeout" or code is None:
        return "timeout"
    if receipt is None:
        return "unreadable"
    return None


def runner_refused(code: int | None, receipt: dict[str, Any] | None) -> bool:
    if not isinstance(receipt, dict):
        return False
    if receipt.get("result") == "refused":
        return True
    if isinstance(receipt.get("error"), dict):
        return True
    return code not in (None, 0)


def atomic_write(target: Path, text: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".tmp")
    try:
        temporary.write_text(text, encoding="utf-8")
        os.replace(temporary, target)
    except Exception:
        try:
            temporary.unlink()
        except OSError:
            pass
        raise


def prompt_sha(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def same_repo(seen: Any, expected: str) -> bool:
    if not isinstance(seen, str) or not seen:
        return True
    try:
        return Path(seen).resolve() == Path(expected).resolve()
    except OSError:
        return seen.rstrip("/") == expected.rstrip("/")


def string_list(value: Any) -> list[str] | None:
    if value is None:
        return []
    if isinstance(value, str) or not isinstance(value, list):
        return None
    if not all(isinstance(item, str) for item in value):
        return None
    return value


def blank_item(item_id: str, preset: str | None, session: str | None, status: str, reason: str,
               extra: dict[str, Any] | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {
        "item_id": item_id,
        "preset": preset,
        "session": session,
        "status": status,
        "reason": reason,
        "evidence": {},
    }
    if extra:
        body.update(extra)
    return body


def requirement_problem(requires: Any, preset: str, row: dict[str, Any]) -> str | None:
    """A Host-stated requirement of this one item, compared before any effect.

    Only a declared requirement is compared; an item without one is not
    judged here, and no Class is inferred from a platform name.
    """
    if not isinstance(requires, dict) or not requires or set(requires) - {"class", "presets"}:
        return "requirement-unreadable: use {\"class\": ..., \"presets\": [...]}"
    classes = requires.get("class")
    if classes is not None:
        classes = [classes] if isinstance(classes, str) else classes
        if not isinstance(classes, list) or not all(item in ("Expert", "Elite", "Worker") for item in classes):
            return "requirement-unreadable: class must be Expert, Elite, or Worker"
        if row["class"] not in classes:
            return f"preset class {row['class']} is not {'/'.join(classes)}"
    presets = requires.get("presets")
    if presets is not None:
        if not isinstance(presets, list) or not all(isinstance(item, str) for item in presets):
            return "requirement-unreadable: presets must be preset ids"
        if preset not in presets:
            return f"preset {preset} is not among the named presets"
    return None


def caller_dispatcher() -> dict[str, str] | None:
    """Who ran this execute: the holder identity its agent inherited, if any."""
    try:
        value = json.loads(os.environ.get("KAOLA_ACP_DISPATCHER") or "null")
    except ValueError:
        return None
    if not isinstance(value, dict):
        return None
    keys = ("holder_instance_id", "platform", "repo", "session")
    if not all(isinstance(value.get(key), str) and value[key] for key in keys):
        return None
    return {key: value[key] for key in keys}


def dispatch_links(row: dict[str, Any], item: dict[str, Any],
                   mark: dict[str, Any] | None = None) -> dict[str, Any]:
    """Carry the plan's task association, output location and stated
    requirement onto the index row, whatever its admission result."""
    for key in ("task_id", "output", "requires", "prompt_source"):
        if item.get(key) is not None and row.get(key) is None:
            row[key] = item[key]
    item = mark or {}
    if item.get("_helper_counted"):
        evidence = dict(row.get("evidence") or {})
        evidence["seat_note"] = "Sideagent-role helper counted as a worker; one bound Sideagent is exempt"
        row["evidence"] = evidence
    elif item.get("_exempt"):
        row["seat_exempt"] = True
    elif item.get("_held_row") and row.get("status") != "not-run":
        evidence = dict(row.get("evidence") or {})
        evidence["seat_note"] = "already-live unprompted named seat counted as this item's seat"
        row["evidence"] = evidence
    return row


def bound_sideagent(doc: dict[str, Any] | None) -> dict[str, Any] | None:
    """The one active maintenance Sideagent binding of a lifecycle-state file."""
    if not isinstance(doc, dict) or doc.get("schema") != STATE_SCHEMA:
        return None
    state = doc.get("state")
    binding = state.get("sideagent") if isinstance(state, dict) else None
    if (isinstance(binding, dict) and binding.get("state") == "active"
            and isinstance(binding.get("session"), str) and binding["session"]):
        return binding
    return None


def binding_row(binding: dict[str, Any] | None, row: dict[str, Any]) -> bool:
    if binding is None or row.get("session") != binding.get("session"):
        return False
    holder = binding.get("holder_instance_id")
    return not holder or row.get("holder_instance_id") == holder


def command_execute(args: argparse.Namespace) -> int:
    try:
        plan = load_object(Path(args.plan))
        auth_doc = load_object(Path(args.authorization))
        auth = authorization_object(auth_doc)
        binding = bound_sideagent(auth_doc)
        grants = normalize_grants(auth)
        shared_capacities = shared_seat_capacities(grants)
        available = availability_map(
            load_object(Path(args.availability)) if args.availability else None
        )
        catalog = catalog_from_files(platform_paths(Path(__file__), args.platforms))
        candidates, withheld = eligibility(catalog, auth, grants, available)
        prior_path = args.prior_index
        if not prior_path and args.index and Path(args.index).is_file():
            prior_path = args.index
        prior = load_object(Path(prior_path)) if prior_path else None
    except ValueError as exc:
        return fail("invalid-input", str(exc))
    by_candidate = {item["id"]: item for item in candidates}
    withheld_reason = {item["id"]: item["reason"] for item in withheld}
    prior_items = {}
    if prior is not None:
        rows = prior.get("items")
        if not isinstance(rows, list):
            return fail("invalid-input", "prior index items must be an array")
        for row in rows:
            if isinstance(row, dict) and isinstance(row.get("item_id"), str):
                prior_items[row["item_id"]] = row
    scope = plan.get("scope")
    repo = plan.get("repo")
    items = plan.get("items")
    if not isinstance(repo, str) or not Path(repo).is_absolute():
        return fail("invalid-input", "plan repo must be an absolute path")
    repo = str(Path(repo).resolve())
    if not isinstance(items, list):
        return fail("invalid-input", "plan items must be an array")
    seat_cap = plan.get("seat_cap", None)
    if seat_cap is not None and (isinstance(seat_cap, bool) or not isinstance(seat_cap, int) or seat_cap < 0):
        return fail("invalid-input", "seat_cap must be a non-negative integer")
    try:
        elite_cap = authorization_cap(auth.get("elite_cap"))
    except ValueError as exc:
        return fail("invalid-input", str(exc))
    if elite_cap is None:
        effective_cap = seat_cap
    elif seat_cap is None:
        effective_cap = elite_cap
    else:
        effective_cap = min(elite_cap, seat_cap)
    ids = [item.get("item_id") for item in items if isinstance(item, dict)]
    if len(ids) != len(items) or any(not isinstance(item, str) for item in ids) or len(set(ids)) != len(ids):
        return fail("invalid-input", "each item needs a unique item_id")
    session_names = [item.get("session") for item in items if isinstance(item, dict)]
    duplicate_sessions = {
        name for name in session_names
        if isinstance(name, str) and session_names.count(name) > 1
    }

    def refuse_all(reason: str) -> int:
        index = {
            "schema": "kaola-dispatch-index/1",
            "correlation_only": True,
            "repo": repo,
            "scope": scope,
            "items": [
                blank_item(
                    item["item_id"],
                    item.get("preset") if isinstance(item.get("preset"), str) else None,
                    item.get("session") if isinstance(item.get("session"), str) else None,
                    "not-run",
                    reason,
                )
                for item in items
            ],
        }
        # An out-of-scope attempt must not replace known priors.
        return finish_index(index, args.index, write=False)

    if scope not in SCOPES or (scope not in MUTATING_SCOPES and (plan.get("mutation") is True or any(
        isinstance(item, dict) and item.get("mutation") is True for item in items
    ))):
        return refuse_all("scope-outside-bounded")
    try:
        assemble_prompts(plan, items)
        lifecycle = load_object(Path(args.state)) if getattr(args, "state", None) else None
    except ValueError as exc:
        return fail("invalid-input", str(exc))
    holds = preset_holds(lifecycle if lifecycle is not None else auth_doc)
    known_tasks = state_task_ids(lifecycle)

    prepared: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            return fail("invalid-input", "items must be objects")
        preset = item.get("preset")
        session = item.get("session")
        prompt = item.get("prompt")
        if not isinstance(preset, str) or not isinstance(session, str) or not isinstance(prompt, str):
            return fail("invalid-input", f"{item.get('item_id')}: preset, session, and prompt must be strings")
        if not SESSION_OK.fullmatch(session):
            blocked.append(blank_item(item["item_id"], preset, session, "not-run", "session-name"))
            continue
        if preset in holds and not exact_prior(prior_items.get(item["item_id"]), item, repo):
            # A recorded account/service hold is not re-probed: no status,
            # start or send reaches that preset until its hold is retired.
            blocked.append(blank_item(item["item_id"], preset, session, "not-run", "on-hold",
                                      {"holds": holds[preset]}))
            continue
        if session in duplicate_sessions:
            blocked.append(blank_item(item["item_id"], preset, session, "not-run", "duplicate-session"))
            continue
        row = catalog.get(preset)
        if row is None:
            blocked.append(blank_item(item["item_id"], preset, session, "not-run", "preset-unresolved"))
            continue
        candidate = by_candidate.get(preset)
        if candidate is None:
            reason = "not-authorized"
            auth_grant = grant_index(grants).get(preset)
            if available.get(preset) == "absent":
                reason = "absent"
            elif auth_grant and auth_grant["state"] in {"excluded", "revoked", "paused"}:
                reason = auth_grant["state"]
            elif preset in set(as_id_list(auth.get("exclusions"))):
                reason = "excluded"
            elif preset in set(as_id_list(auth.get("revoked"))):
                reason = "revoked"
            elif preset in set(as_id_list(auth.get("paused"))):
                reason = "paused"
            elif auth_grant and auth_grant.get("state") not in {None, "granted"}:
                reason = "state-unreadable"
            elif withheld_reason.get(preset) in EXPERT_WITHHELD_REASONS:
                reason = withheld_reason[preset]
            blocked.append(blank_item(item["item_id"], preset, session, "not-run", reason))
            continue
        if item.get("requires") is not None:
            problem = requirement_problem(item["requires"], preset, row)
            if problem:
                blocked.append(blank_item(
                    item["item_id"], preset, session, "not-run", "requirement-unmet",
                    {"requires": item["requires"], "detail": problem},
                ))
                continue
        overrides = item.get("overrides") or {}
        if not isinstance(overrides, dict):
            blocked.append(blank_item(item["item_id"], preset, session, "not-run", "override-unapplied"))
            continue
        special = candidate.get("special_requirements") or {}
        unknown_keys = [
            key for key in set(overrides) | set(special)
            if key not in RECORDED_OVERRIDE_KEYS
        ]
        if unknown_keys:
            blocked.append(blank_item(
                item["item_id"], preset, session, "not-run", "override-unapplied",
                {"unapplied": sorted(unknown_keys)},
            ))
            continue
        resources = item.get("resources") or {}
        if not isinstance(resources, dict):
            blocked.append(blank_item(item["item_id"], preset, session, "not-run", "resources-unreadable"))
            continue
        writes = string_list(resources.get("writes"))
        ports = string_list(resources.get("ports"))
        account = resources.get("account")
        desktop = resources.get("desktop")
        if writes is None or ports is None or (account is not None and not isinstance(account, str)) or (
            desktop is not None and not isinstance(desktop, bool)
        ):
            detail = "ports must be strings" if ports is None else None
            blocked.append(blank_item(
                item["item_id"], preset, session, "not-run", "resources-unreadable",
                {"detail": detail} if detail else None,
            ))
            continue
        item_seat = item.get("shared_seat")
        grant_seat = candidate.get("shared_seat")
        if item_seat is not None and not isinstance(item_seat, str):
            blocked.append(blank_item(item["item_id"], preset, session, "not-run", "shared-seat-mismatch"))
            continue
        if item_seat and grant_seat and item_seat != grant_seat:
            blocked.append(blank_item(item["item_id"], preset, session, "not-run", "shared-seat-mismatch"))
            continue
        owner_effort = special.get("effort") if isinstance(special.get("effort"), str) else None
        owner_model = special.get("model") if isinstance(special.get("model"), str) else None
        item_effort = overrides.get("effort") if isinstance(overrides.get("effort"), str) else None
        item_model = overrides.get("model") if isinstance(overrides.get("model"), str) else None
        if overrides.get("effort") is not None and not isinstance(overrides.get("effort"), str):
            blocked.append(blank_item(item["item_id"], preset, session, "not-run", "override-unapplied"))
            continue
        if overrides.get("model") is not None and not isinstance(overrides.get("model"), str):
            blocked.append(blank_item(item["item_id"], preset, session, "not-run", "override-unapplied"))
            continue
        owner_scope = special.get("task_scope") if isinstance(special.get("task_scope"), str) else None
        item_scope = overrides.get("task_scope") if isinstance(overrides.get("task_scope"), str) else None
        if ((owner_model and item_model and item_model != owner_model)
                or (owner_effort and item_effort and item_effort != owner_effort)
                or (owner_scope and item_scope and item_scope != owner_scope)):
            blocked.append(blank_item(
                item["item_id"], preset, session, "not-run", "override-conflicts-owner",
            ))
            continue
        effort = owner_effort if owner_effort is not None else item_effort
        model = owner_model if owner_model is not None else item_model
        task_scope = owner_scope or item_scope
        catalog_model = row["selection"]["model_id"] or None
        if model and catalog_model and model != catalog_model and not switch_authorized(
            preset, model, special, auth, candidate
        ):
            blocked.append(blank_item(item["item_id"], preset, session, "not-run", "model-switch-unauthorized"))
            continue
        if model and effort is None:
            requested_effort = None
        elif isinstance(effort, str) and effort:
            requested_effort = effort
        else:
            requested_effort = row["selection"]["effort"] or None
        requested_model = model if isinstance(model, str) and model else (catalog_model or None)
        if requested_effort == "":
            requested_effort = None
        if requested_model == "":
            requested_model = None
        prepared.append({
            **item,
            "resources": {"writes": writes, "ports": ports, "account": account, "desktop": desktop},
            "_shared_seat": item_seat or grant_seat,
            "_shared_capacity": shared_capacities.get(item_seat or grant_seat, 1),
            "_count": candidate.get("count"),
            "_pool": candidate["pool"],
            "_platform": row["platform"],
            "_tier": row["tier"],
            "_model": model if isinstance(model, str) else None,
            "_effort": effort if isinstance(effort, str) else None,
            "_task_scope": task_scope,
            "_prompt_sha256": prompt_sha(prompt),
            "_requested": {
                "preset": preset,
                "tier": row["tier"],
                "model_id": requested_model,
                "effort": requested_effort,
            },
        })

    for item in prepared:
        if (item.get("role") in SIDEAGENT_ROLES and binding is not None
                and item.get("session") == binding.get("session")):
            item["_exempt"] = True
    kept_items = [
        item for item in prepared
        if exact_prior(prior_items.get(item["item_id"]), item, repo)
    ]
    fresh_items = [item for item in prepared if item not in kept_items]
    blocked_ids = conflict_ids(fresh_items)
    conflict_note = {
        item["item_id"]: sorted(
            other["item_id"] for other in fresh_items
            if other["item_id"] != item["item_id"] and other["item_id"] in blocked_ids
            and resource_conflict(item, other)
        )
        for item in fresh_items
    }
    fresh_open = []
    for item in fresh_items:
        if item["item_id"] in blocked_ids:
            blocked.append(blank_item(
                item["item_id"], item["preset"], item["session"], "not-run", "resource-conflict",
                {"conflicts_with": conflict_note[item["item_id"]]},
            ))
            continue
        occupied_by = [
            old["item_id"] for old in kept_items if resource_conflict(item, old)
        ]
        if occupied_by:
            blocked.append(blank_item(
                item["item_id"], item["preset"], item["session"], "not-run", "resource-conflict",
                {"conflicts_with": occupied_by},
            ))
            continue
        fresh_open.append(item)

    skills_root = Path(args.skills_root) if args.skills_root else None
    try:
        live_rows, occupancy = live_facts(getattr(args, "live", None), repo, Path(__file__), skills_root)
    except ValueError as exc:
        return fail("invalid-input", str(exc))
    needs_live = effective_cap is not None or any(
        item.get("_shared_seat") or isinstance(item.get("_count"), int)
        for item in fresh_open
    )
    resolved: dict[str, str] = {}
    if needs_live and occupancy == "known":
        unbound = [row for row in live_rows if not binding_row(binding, row)]
        verified: set[str] = set()
        resolved = resolve_live_presets(unbound, repo, catalog, prior_items, skills_root,
                                        verified=verified)
        for item in fresh_open:
            row = held_seat(item, unbound, repo, resolved, verified)
            if row is not None:
                item["_held_row"] = row
    used_count, used_seats, occupied_shared, unnamed_platforms = live_occupancy(
        live_rows, repo, catalog, grants, resolved, exempt=binding,
    )
    live_sessions = {
        row.get("session") for row in live_rows
        if row.get("state") != "stopped" and row.get("host_class") is not True
        and not binding_row(binding, row)
        and not (isinstance(row.get("repo"), str) and row.get("repo")
                 and not same_repo(row["repo"], repo))
    }
    for item in kept_items:
        seat_name = item.get("_shared_seat")
        if (isinstance(seat_name, str) and seat_name and not item.get("_exempt")
                and item.get("session") not in live_sessions):
            occupied_shared[seat_name] = occupied_shared.get(seat_name, 0) + 1
    # Only the one bound maintenance Sideagent (named in the lifecycle state
    # before its start) is exempt from worker seats; any other Sideagent-role
    # item is a helper and counts as a worker.
    for item in fresh_open:
        if item.get("role") not in SIDEAGENT_ROLES:
            continue
        if binding is not None and item.get("session") == binding.get("session"):
            item["_exempt"] = True
        else:
            item["_helper_counted"] = True
    seat_marks = {item["item_id"]: item for item in fresh_open
                  if item.get("_exempt") or item.get("_helper_counted") or item.get("_held_row")}
    ready = list(kept_items)
    for item in fresh_open:
        if item.get("_exempt"):
            ready.append(item)
            continue
        held = item.get("_held_row")
        if held is not None:
            # This item's own live, unprompted seat is already in the totals
            # every other item is admitted against. Judge it against the other
            # live rows only and do not count it a second time.
            others = [row for row in live_rows if row is not held]
            o_count, o_seats, o_shared, o_unnamed = live_occupancy(
                others, repo, catalog, grants, resolved, exempt=binding)
            reason = held_refusal(item, o_count, o_seats, o_shared, o_unnamed,
                                  effective_cap, grants, catalog)
            if reason:
                blocked.append(blank_item(item["item_id"], item["preset"], item["session"], "not-run", reason))
                continue
            ready.append(item)
            continue
        if occupancy != "known" and needs_live and (not item["_pool"] or item.get("_shared_seat") or isinstance(item.get("_count"), int)):
            blocked.append(blank_item(
                item["item_id"], item["preset"], item["session"], "not-run", "occupancy-unknown",
            ))
            continue
        seat_name = item.get("_shared_seat")
        if (isinstance(seat_name, str) and seat_name
                and occupied_shared.get(seat_name, 0) >= item.get("_shared_capacity", 1)):
            blocked.append(blank_item(item["item_id"], item["preset"], item["session"], "not-run", "shared-occupied"))
            continue
        if isinstance(seat_name, str) and seat_name and shared_seat_unknown(seat_name, grants, catalog, unnamed_platforms):
            blocked.append(blank_item(
                item["item_id"], item["preset"], item["session"], "not-run", "occupancy-unknown",
            ))
            continue
        limit = item.get("_count")
        if isinstance(limit, int) and item.get("_platform") in unnamed_platforms and used_count.get(item["preset"], 0) < limit:
            blocked.append(blank_item(
                item["item_id"], item["preset"], item["session"], "not-run", "occupancy-unknown",
            ))
            continue
        if isinstance(limit, int) and used_count.get(item["preset"], 0) >= limit:
            blocked.append(blank_item(item["item_id"], item["preset"], item["session"], "not-run", "count"))
            continue
        if not item["_pool"] and effective_cap is not None and used_seats >= effective_cap:
            blocked.append(blank_item(item["item_id"], item["preset"], item["session"], "not-run", "seat-cap"))
            continue
        if not item["_pool"] and effective_cap is not None and unnamed_platforms:
            blocked.append(blank_item(
                item["item_id"], item["preset"], item["session"], "not-run", "occupancy-unknown",
            ))
            continue
        if isinstance(limit, int):
            used_count[item["preset"]] = used_count.get(item["preset"], 0) + 1
        if isinstance(seat_name, str) and seat_name:
            occupied_shared[seat_name] = occupied_shared.get(seat_name, 0) + 1
        if not item["_pool"] and effective_cap is not None:
            used_seats += 1
        ready.append(item)

    if ready and (args.dry_run or skills_root is None):
        if args.dry_run:
            for item in ready:
                if item in kept_items:
                    blocked.append(launch_plan(item, repo, dry_run=True, reason="reconciled"))
                else:
                    blocked.append(launch_plan(item, repo, dry_run=True))
            ready = []
        if ready and skills_root is None:
            return fail("invalid-input", "execute needs --skills-root when an item is ready")

    results: dict[str, dict[str, Any]] = {}
    index = {
        "schema": "kaola-dispatch-index/1",
        "correlation_only": True,
        "phase": "admission",
        "repo": repo,
        "scope": scope,
        "occupancy": occupancy,
        "effective_cap": effective_cap,
        "items": [],
    }
    dispatcher = caller_dispatcher()
    if dispatcher is not None:
        index["dispatcher"] = dispatcher
    base = ({"items": json.loads(json.dumps(prior.get("items") or []))}
            if prior is not None and prior_path == args.index else None)

    def publish() -> None:
        ordered = []
        for item in items:
            item_id = item["item_id"]
            if item_id in results:
                ordered.append(dispatch_links(results[item_id], item, seat_marks.get(item_id)))
                continue
            match = [row for row in blocked if row["item_id"] == item_id]
            preset = item.get("preset") if isinstance(item.get("preset"), str) else None
            session = item.get("session") if isinstance(item.get("session"), str) else None
            chosen = match[0] if match else blank_item(item_id, preset, session, "unknown", "missing")
            prior = prior_items.get(item_id)
            if assignment_identity(prior, item, repo):
                attempt = chosen.get("reason")
                chosen = preserve_correlation(dict(chosen), prior)
                if attempt not in ("reconciled", "dry-run") and prior.get("status") in (
                    "unknown", "failed", "in-flight", "returned",
                ):
                    # publish() runs before the executor. An empty match is the
                    # placeholder reason "missing", not a refusal.
                    if match:
                        evidence = dict(chosen.get("evidence") or {})
                        evidence["blocked_attempt"] = {"reason": attempt}
                        chosen["evidence"] = evidence
                    chosen["status"] = prior["status"]
                    if isinstance(prior.get("reason"), str) and prior["reason"]:
                        chosen["reason"] = prior["reason"]
            ordered.append(dispatch_links(chosen, item, seat_marks.get(item_id)))
        index["items"] = ordered
        finish_index(index, args.index, emit_stdout=False, write=not args.dry_run, base=base)

    publish()
    if ready:
        assert skills_root is not None
        with ThreadPoolExecutor(max_workers=len(ready)) as pool:
            futures = {
                pool.submit(execute_one, item, repo, skills_root, prior_items.get(item["item_id"])): item
                for item in ready
            }
            for future in as_completed(futures):
                item = futures[future]
                try:
                    result = future.result()
                except Exception as exc:
                    result = blank_item(
                        item["item_id"], item["preset"], item["session"], "unknown",
                        "admission-error", {"detail": str(exc)},
                    )
                results[result["item_id"]] = result
                publish()
    if known_tasks is not None:
        for row in index["items"]:
            if row.get("task_id") is not None and row["task_id"] not in known_tasks:
                row.setdefault("evidence", {})["task_note"] = (
                    f"task {row['task_id']} is not a current task in {args.state}")
        if not args.dry_run:
            index["task_links"] = link_dispatch_to_tasks(Path(args.state), index, args.index)
    return finish_index(index, args.index, write=not args.dry_run, base=base)


def assemble_prompts(plan: dict[str, Any], items: list[Any]) -> None:
    """Give each item the exact text it will be sent. A full `prompt` is sent
    as written; otherwise the Host's unchanged task `core` at its recorded
    `core_revision` (plan- or item-level) is joined with the item's
    Host-authored `worker_scope`. Nothing here rewrites either part."""
    for item in items:
        if not isinstance(item, dict):
            continue
        if isinstance(item.get("prompt"), str):
            if item.get("worker_scope") is not None:
                raise ValueError(f"{item.get('item_id')}: give either prompt or worker_scope")
            item["prompt_source"] = {"kind": "full", "prompt_sha256": prompt_sha(item["prompt"])}
            continue
        if item.get("worker_scope") is None:
            continue
        core = item.get("core", plan.get("core"))
        revision = item.get("core_revision", plan.get("core_revision"))
        scope_text = item.get("worker_scope")
        if not isinstance(core, str) or not core.strip() or not isinstance(scope_text, str):
            raise ValueError(f"{item.get('item_id')}: worker_scope needs a string core")
        if isinstance(revision, bool) or not isinstance(revision, (str, int)) or revision == "":
            raise ValueError(f"{item.get('item_id')}: core needs its recorded core_revision")
        item["prompt"] = core.rstrip("\n") + "\n\n" + scope_text
        item["prompt_source"] = {"kind": "core+scope", "core_revision": revision,
                                 "core_sha256": prompt_sha(core), "scope_sha256": prompt_sha(scope_text),
                                 "prompt_sha256": prompt_sha(item["prompt"])}


def preset_holds(doc: dict[str, Any] | None) -> dict[str, list[str]]:
    """Current lifecycle holds that name a preset, by preset id."""
    if not isinstance(doc, dict) or doc.get("schema") != STATE_SCHEMA:
        return {}
    state = doc.get("state")
    holds = state.get("holds") if isinstance(state, dict) else None
    found: dict[str, list[str]] = {}
    for hold_id, hold in sorted((holds or {}).items()):
        if not isinstance(hold, dict):
            continue
        named = hold.get("presets", hold.get("preset"))
        named = [named] if isinstance(named, str) else named if isinstance(named, list) else []
        for preset in named:
            if isinstance(preset, str) and preset:
                found.setdefault(preset, []).append(hold_id)
    return found


def state_task_ids(doc: dict[str, Any] | None) -> set[str] | None:
    if not isinstance(doc, dict) or doc.get("schema") != STATE_SCHEMA:
        return None
    state = doc.get("state")
    tasks = state.get("tasks") if isinstance(state, dict) else None
    return set(tasks) if isinstance(tasks, dict) else set()


def link_dispatch_to_tasks(path: Path, index: dict[str, Any], index_path: str | None) -> dict[str, Any]:
    """Tool-only linkage: add each admitted or unknown item to its named
    task's `dispatch` refs. Not a Host business write, so it moves no
    `host_revision` and wakes no maintenance node."""
    wanted: dict[str, list[str]] = {}
    for row in index["items"]:
        if row.get("status") in ("in-flight", "returned", "unknown") and isinstance(row.get("task_id"), str):
            wanted.setdefault(row["task_id"], []).append(row["item_id"])
    if not wanted:
        return {"linked": {}}
    try:
        with StateLock(path):
            doc, _ = read_state_file(path)
            doc = require_current(doc, path)
            tasks = doc["state"].get("tasks") or {}
            linked: dict[str, list[str]] = {}
            for task_id, refs in wanted.items():
                task = tasks.get(task_id)
                if not isinstance(task, dict):
                    continue
                mine = task.get("dispatch")
                mine = [mine] if isinstance(mine, str) else list(mine or [])
                added = [ref for ref in refs if ref not in mine]
                if added:
                    task["dispatch"] = mine + added
                    task["rev"] = int(task.get("rev") or 0) + 1
                    task["updated_at"] = observed_at()
                    task["writer"] = "tool:execute"
                    linked[task_id] = added
            if linked:
                write_state(path, doc)
    except StateRefusal as refusal:
        return {"unlinked": sorted(wanted), "refusal": refusal.payload}
    except (OSError, ValueError) as exc:
        return {"unlinked": sorted(wanted), "error": str(exc)}
    return {"linked": linked, **({"index": index_path} if index_path else {})}


def resource_conflict(left: dict[str, Any], right: dict[str, Any]) -> bool:
    if (left.get("_shared_seat") and left.get("_shared_seat") == right.get("_shared_seat")
            and not left.get("_exempt") and not right.get("_exempt")
            and min(left.get("_shared_capacity", 1), right.get("_shared_capacity", 1)) <= 1):
        # One-slot pools remain exclusive. Larger pools are checked by capacity.
        return True
    left_res = left.get("resources") or {}
    right_res = right.get("resources") or {}
    if set(left_res.get("writes") or []) & set(right_res.get("writes") or []):
        return True
    if left_res.get("desktop") is True and right_res.get("desktop") is True:
        return True
    if left_res.get("account") and left_res.get("account") == right_res.get("account"):
        return True
    if set(left_res.get("ports") or []) & set(right_res.get("ports") or []):
        return True
    return False


def conflict_ids(items: list[dict[str, Any]]) -> set[str]:
    parent = list(range(len(items)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    for i, left in enumerate(items):
        for j in range(i + 1, len(items)):
            if resource_conflict(left, items[j]):
                parent[find(j)] = find(i)
    groups: dict[int, list[int]] = {}
    for index in range(len(items)):
        groups.setdefault(find(index), []).append(index)
    blocked: set[str] = set()
    for members in groups.values():
        if len(members) > 1:
            blocked.update(items[index]["item_id"] for index in members)
    return blocked


def authorization_cap(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("elite_cap must be a non-negative integer")
    return value


def acp_runner(script: Path, skills_root: Path | None) -> Path | None:
    """The Runner entry for a fresh list; an explicit skills root is the only place looked in."""
    if skills_root is not None:
        found = sorted(skills_root.glob("*-kaola-project-runner/scripts/kaola-acp.py"))
        return found[0] if found else None
    beside = script.resolve().parent / "kaola-acp.py"
    if beside.is_file():
        return beside
    found = sorted(script.resolve().parent.parent.parent.glob("*-kaola-project-runner/scripts/kaola-acp.py"))
    return found[0] if found else None


def live_facts(path: str | None, repo: str, script: Path,
               skills_root: Path | None = None) -> tuple[list[dict[str, Any]], str]:
    if path:
        document = load_object(Path(path))
        rows = document.get("rows")
        if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
            raise ValueError("live facts rows must be an array of objects")
        return rows, "known"
    acp = acp_runner(script, skills_root)
    if acp is None:
        return [], "unavailable"
    # Generated copies are not executable; the interpreter runs them.
    code, receipt, note = run_runner(Path(sys.executable), [str(acp), "list", "--repo", repo])
    if receipt_unreadable(code, receipt, note) or not isinstance(receipt, dict):
        return [], "unavailable"
    rows = receipt.get("rows")
    if not isinstance(rows, list):
        return [], "unavailable"
    return [row for row in rows if isinstance(row, dict)], "known"


def assignment_identity(prior: dict[str, Any] | None, item: dict[str, Any], repo: str) -> bool:
    """Same assignment: repo, preset, session, and prompt. Not admission state."""
    if not isinstance(prior, dict):
        return False
    preset = prior.get("preset")
    session = prior.get("session")
    prior_repo = prior.get("repo")
    if not isinstance(preset, str) or not preset or preset != item.get("preset"):
        return False
    if not isinstance(session, str) or not session or session != item.get("session"):
        return False
    if not isinstance(prior_repo, str) or not prior_repo or not same_repo(prior_repo, repo):
        return False
    prompt = item.get("_prompt_sha256")
    if not isinstance(prompt, str):
        raw = item.get("prompt")
        prompt = prompt_sha(raw) if isinstance(raw, str) else item.get("prompt_sha256")
    return fingers_equal(prior.get("prompt_sha256"), prompt)


def exact_prior(prior: dict[str, Any] | None, item: dict[str, Any], repo: str) -> bool:
    """Already admitted: matching assignment, holder present, in-flight or returned."""
    if not isinstance(prior, dict) or prior.get("status") not in ("in-flight", "returned"):
        return False
    holder = prior.get("holder_instance_id")
    if not isinstance(holder, str) or not holder:
        return False
    return assignment_identity(prior, item, repo)


def preserve_correlation(result: dict[str, Any], prior: dict[str, Any] | None) -> dict[str, Any]:
    """Keep the index binding when this pass refuses or cannot reconcile."""
    if not isinstance(prior, dict):
        return result
    for key in (
        "holder_instance_id", "dispatch_event_cursor", "prompt_fingerprint",
        "prompt_sha256", "result", "selection", "platform", "repo",
    ):
        if result.get(key) is None and prior.get(key) is not None:
            result[key] = prior[key]
    prior_evidence = prior.get("evidence")
    if isinstance(prior_evidence, dict):
        merged = dict(prior_evidence)
        current = result.get("evidence")
        if isinstance(current, dict):
            merged.update(current)
        result["evidence"] = merged
    return result


def preset_from_applied(catalog: dict[str, dict[str, Any]], platform: str,
                        receipt: dict[str, Any]) -> str | None:
    """One catalog preset on this platform, from applied model and effort.

    A mapped slot is named by ``requested_id``, the same rule as
    ``model_applied_verdict``. The raw ``value`` is only the provider payload.
    """
    application, _source = application_of(receipt)
    if not isinstance(application, dict):
        return None
    model_slot, model_state = application_slot(application, "model")
    if model_state != "applied" or not isinstance(model_slot, dict):
        return None
    requested_id = present_value(model_slot.get("requested_id"))
    value = present_value(model_slot.get("value"))
    if model_slot.get("mapped") is True and isinstance(requested_id, str):
        observed = requested_id
    elif isinstance(value, str) and value.strip():
        observed = value
    else:
        return None
    effort_slot, effort_state = application_slot(application, "effort")
    effort = None
    if effort_state == "applied" and isinstance(effort_slot, dict) and isinstance(effort_slot.get("value"), str):
        effort = effort_slot["value"]
    matches = []
    for preset, row in catalog.items():
        if row["platform"] != platform:
            continue
        if not model_match(row["selection"].get("model_id") or "", observed):
            continue
        if effort is not None and (row["selection"].get("effort") or "") != effort:
            continue
        matches.append(preset)
    if len(matches) == 1:
        return matches[0]
    return None


def preset_from_bound_index(items: dict[str, dict[str, Any]], row: dict[str, Any], repo: str) -> str | None:
    session = row.get("session")
    holder = row.get("holder_instance_id")
    if not isinstance(session, str) or not isinstance(holder, str) or not holder:
        return None
    found: set[str] = set()
    for item in items.values():
        if not isinstance(item, dict):
            continue
        if item.get("session") != session or item.get("holder_instance_id") != holder:
            continue
        if item.get("status") not in ("in-flight", "returned"):
            continue
        if not same_repo(item.get("repo"), repo):
            continue
        preset = item.get("preset")
        if isinstance(preset, str):
            found.add(preset)
    if len(found) == 1:
        return next(iter(found))
    return None


def resolve_live_presets(rows: list[dict[str, Any]], repo: str, catalog: dict[str, dict[str, Any]],
                         prior_items: dict[str, dict[str, Any]],
                         skills_root: Path | None, *, require_identity: bool = False,
                         verified: set[str] | None = None) -> dict[str, str]:
    """Preset for a list row that does not carry one. Platform name is not a Class.

    ``verified`` collects sessions whose status receipt also named this repo,
    session and the row's holder."""
    resolved: dict[str, str] = {}
    for row in rows:
        if row.get("state") == "stopped" or row.get("host_class") is True:
            continue
        row_repo = row.get("repo")
        if isinstance(row_repo, str) and row_repo and not same_repo(row_repo, repo):
            continue
        session = row.get("session")
        if not isinstance(session, str) or not session:
            continue
        preset = row.get("preset") if isinstance(row.get("preset"), str) else None
        if preset in catalog:
            resolved[session] = preset
            continue
        bound = preset_from_bound_index(prior_items, row, repo)
        if bound in catalog:
            resolved[session] = bound
            continue
        platform = row.get("platform") if isinstance(row.get("platform"), str) else None
        if skills_root is None or not platform:
            continue
        script = skills_root / f"{platform}-kaola-project-runner" / "scripts" / "runtime-tmux.sh"
        if not script.is_file():
            continue
        code, receipt, note = run_runner(script, ["status", "--repo", repo, "--session", session])
        if receipt_unreadable(code, receipt, note) or not isinstance(receipt, dict):
            continue
        same = (same_repo(repo_of(receipt), repo)
                and receipt.get("session") == session
                and holder_of(receipt) == row.get("holder_instance_id"))
        if require_identity and not same:
            continue
        applied = preset_from_applied(catalog, platform, receipt)
        if applied:
            resolved[session] = applied
            if verified is not None and same and isinstance(repo_of(receipt), str):
                verified.add(session)
    return resolved


def shared_seat_unknown(seat: str, grants: list[dict[str, Any]], catalog: dict[str, dict[str, Any]],
                        unnamed: set[str]) -> bool:
    for grant in grants:
        if grant.get("shared_seat") != seat or grant.get("state") != "granted":
            continue
        row = catalog.get(grant["id"])
        if row and row["platform"] in unnamed:
            return True
    return False


def live_occupancy(rows: list[dict[str, Any]], repo: str, catalog: dict[str, dict[str, Any]],
                   grants: list[dict[str, Any]], resolved: dict[str, str] | None = None,
                   exempt: dict[str, Any] | None = None,
                   ) -> tuple[dict[str, int], int, dict[str, int], set[str]]:
    used_count: dict[str, int] = {}
    used_seats = 0
    occupied: dict[str, int] = {}
    unnamed: set[str] = set()
    grants_by_id = grant_index(grants)
    known = resolved or {}
    for row in rows:
        if row.get("state") == "stopped":
            continue
        if binding_row(exempt, row):
            # The bound maintenance Sideagent is independent of worker seats,
            # shared-preset seats included. A real service limit is evidence
            # (availability or a hold), not a seat it takes from workers.
            continue
        row_repo = row.get("repo")
        if isinstance(row_repo, str) and row_repo and not same_repo(row_repo, repo):
            continue
        if row.get("host_class") is True:
            continue
        platform = row.get("platform") if isinstance(row.get("platform"), str) else None
        preset = row.get("preset") if isinstance(row.get("preset"), str) and row.get("preset") in catalog else None
        session = row.get("session")
        if preset is None and isinstance(session, str):
            candidate = known.get(session)
            if candidate in catalog:
                preset = candidate
        seat = row.get("shared_seat") if isinstance(row.get("shared_seat"), str) else None
        grant = grants_by_id.get(preset) if preset else None
        if not seat and grant and isinstance(grant.get("shared_seat"), str):
            seat = grant["shared_seat"]
        if seat:
            occupied[seat] = occupied.get(seat, 0) + 1
        klass = catalog[preset]["class"] if preset else None
        if preset:
            used_count[preset] = used_count.get(preset, 0) + 1
        elif platform:
            unnamed.add(platform)
        if klass in ("Elite", "Expert"):
            used_seats += 1
    return used_count, used_seats, occupied, unnamed


def held_seat(item: dict[str, Any], rows: list[dict[str, Any]], repo: str,
              resolved: dict[str, str], verified: set[str]) -> dict[str, Any] | None:
    """The one verified live row that already is this fresh item's seat.

    Same repo, platform, session and preset, identity verified, nothing sent
    yet. Anything else stays an ordinary occupant counted against the item.
    """
    session = item.get("session")
    if item.get("_exempt") or not isinstance(session, str):
        return None
    mine = [row for row in rows
            if row.get("session") == session and row.get("state") != "stopped"]
    if len(mine) != 1:
        return None
    row = mine[0]
    preset = row.get("preset") if isinstance(row.get("preset"), str) else (
        resolved.get(session) if session in verified else None)
    expected = item.get("expected_holder_instance_id")
    if (row.get("host_class") is True or row.get("identity") != "verified"
            or not isinstance(row.get("repo"), str) or not same_repo(row["repo"], repo)
            or row.get("platform") != item.get("_platform")
            or preset != item.get("preset")
            or row.get("mutation_status") != "not_started"
            or not isinstance(row.get("holder_instance_id"), str) or not row["holder_instance_id"]
            or (isinstance(expected, str) and expected and expected != row["holder_instance_id"])):
        return None
    return row


def held_refusal(item: dict[str, Any], used_count: dict[str, int], used_seats: int,
                 occupied: dict[str, int], unnamed: set[str], cap: int | None,
                 grants: list[dict[str, Any]], catalog: dict[str, dict[str, Any]]) -> str | None:
    """The admission checks for a held seat, against every other live row."""
    seat = item.get("_shared_seat")
    if (isinstance(seat, str) and seat
            and occupied.get(seat, 0) >= item.get("_shared_capacity", 1)):
        return "shared-occupied"
    if isinstance(seat, str) and seat and shared_seat_unknown(seat, grants, catalog, unnamed):
        return "occupancy-unknown"
    limit = item.get("_count")
    if isinstance(limit, int):
        if used_count.get(item["preset"], 0) >= limit:
            return "count"
        if item.get("_platform") in unnamed:
            return "occupancy-unknown"
    if not item["_pool"] and cap is not None:
        if used_seats >= cap:
            return "seat-cap"
        if unnamed:
            return "occupancy-unknown"
    return None


def launch_argv(item: dict[str, Any], repo: str, command: str) -> list[str]:
    argv = [command, "--repo", repo, "--session", item["session"]]
    if command == "start":
        argv.extend(["--tier", item["_tier"]])
        if item.get("_model"):
            argv.extend(["--model", item["_model"]])
        if item.get("_effort"):
            argv.extend(["--effort", item["_effort"]])
        # Sideagent is explicit; retain legacy plan values without rewriting them.
        if item.get("role") in ("sideagent", "sidekick"):
            argv.extend(["--role", item["role"]])
    elif command == "send":
        argv.extend(["--no-wait", "--text", item["prompt"]])
        holder = item.get("_holder") or item.get("holder_instance_id")
        if isinstance(holder, str) and holder:
            argv.extend(["--expected-holder-instance-id", holder])
    elif command == "capture":
        cursor = item.get("dispatch_event_cursor")
        if isinstance(cursor, int) and not isinstance(cursor, bool):
            argv.extend(["--since", str(cursor)])
    return argv


def launch_plan(item: dict[str, Any], repo: str, dry_run: bool, reason: str = "dry-run") -> dict[str, Any]:
    return blank_item(
        item["item_id"], item["preset"], item["session"], "not-run", reason,
        {
            "argv": {
                "status": launch_argv(item, repo, "status"),
                "start": launch_argv(item, repo, "start"),
                "send": launch_argv(item, repo, "send"),
            },
            "dry_run": dry_run,
        },
    )


def remember_holder(item: dict[str, Any], base: dict[str, Any], receipt: dict[str, Any] | None) -> None:
    holder = holder_of(receipt) if isinstance(receipt, dict) else None
    if not holder and isinstance(item.get("expected_holder_instance_id"), str):
        holder = item["expected_holder_instance_id"]
    if isinstance(holder, str) and holder:
        base["holder_instance_id"] = holder
        item["_holder"] = holder


def execute_one(item: dict[str, Any], repo: str, skills_root: Path,
                prior: dict[str, Any] | None) -> dict[str, Any]:
    script = skills_root / f"{item['_platform']}-kaola-project-runner" / "scripts" / "runtime-tmux.sh"
    base = {
        "item_id": item["item_id"],
        "preset": item["preset"],
        "session": item["session"],
        "repo": repo,
        "prompt_sha256": item.get("_prompt_sha256") or prompt_sha(item["prompt"]),
        "platform": item.get("_platform"),
        "evidence": {},
        "acceptance": "pending",
    }
    if isinstance(item.get("role"), str) and item["role"]:
        base["role"] = item["role"]
    if isinstance(item.get("_task_scope"), str) and item["_task_scope"]:
        base["task_scope"] = item["_task_scope"]

    def finish(result: dict[str, Any]) -> dict[str, Any]:
        if result.get("reason") != "admitted" and assignment_identity(prior, item, repo):
            return preserve_correlation(result, prior)
        return result

    if not script.is_file():
        base.update(status="not-run", reason="runner-missing")
        return finish({key: value for key, value in base.items() if value is not None})
    code, receipt, note = run_runner(script, launch_argv(item, repo, "status"))
    base["evidence"]["status"] = evidence(receipt, code, note)
    unread = receipt_unreadable(code, receipt, note)
    if unread:
        base.update(status="unknown", reason="status-" + unread)
        return finish(base)
    if not session_absent(receipt):
        return finish(recover_or_send(item, repo, script, base, receipt, prior))
    if assignment_identity(prior, item, repo) and prior.get("status") in ("in-flight", "returned"):
        base.update(status=prior["status"], reason="session-gone")
        return finish(base)
    if assignment_identity(prior, item, repo) and prior.get("status") == "unknown":
        base.update(status="unknown", reason="reconciliation-needed")
        return finish(base)
    if isinstance(item.get("expected_holder_instance_id"), str) and item["expected_holder_instance_id"]:
        base.update(status="not-run", reason="expected-holder-absent")
        return finish(base)
    code, receipt, note = run_runner(script, launch_argv(item, repo, "start"))
    base["evidence"]["start"] = evidence(receipt, code, note)
    unread = receipt_unreadable(code, receipt, note)
    if unread:
        base.update(status="unknown", reason="start-" + unread)
        return finish(base)
    report = selection_report(item["_requested"], receipt if isinstance(receipt, dict) else None)
    base["selection"] = report
    if runner_refused(code, receipt):
        base.update(status="failed", reason="start-failed")
        return finish(base)
    seen_repo = repo_of(receipt)
    if not same_repo(seen_repo, repo):
        base.update(status="unknown", reason="repo-mismatch")
        return finish(base)
    remember_holder(item, base, receipt)
    if isinstance(receipt, dict):
        # Who dispatched and where its events go are separate facts.
        target = receipt.get("heartbeat_host")
        if isinstance(target, dict):
            base["notify_target"] = {key: target.get(key) for key in ("platform", "session")}
        if isinstance(receipt.get("dispatcher"), dict):
            base["dispatcher"] = {key: receipt["dispatcher"].get(key)
                                  for key in ("platform", "session", "holder_instance_id")}
    expected = item.get("expected_holder_instance_id")
    if isinstance(expected, str) and holder_of(receipt) and holder_of(receipt) != expected:
        base.update(status="unknown", reason="holder-mismatch")
        return finish(base)
    if applied_mismatch(report):
        base.update(status="failed", reason="selection-mismatch")
        return finish(base)
    return finish(send_item(item, repo, script, base))


def assignment_bound(prior: dict[str, Any] | None, item: dict[str, Any],
                     receipt: dict[str, Any], repo: str, prompt_sha: str) -> bool:
    """A prior row is this assignment only when every identity field matches."""
    if not isinstance(prior, dict):
        return False
    holder = holder_of(receipt)
    checks = {
        "repo": repo,
        "session": item.get("session"),
        "preset": item.get("preset"),
        "holder_instance_id": holder,
    }
    for key, want in checks.items():
        have = prior.get(key)
        if key == "repo":
            if not isinstance(have, str) or not isinstance(want, str) or not same_repo(have, want):
                return False
            continue
        if not isinstance(have, str) or not isinstance(want, str) or have != want:
            return False
    recorded = prior.get("prompt_sha256")
    if not fingers_equal(recorded, prompt_sha):
        return False
    return True


def note_persisted_role(item: dict[str, Any], receipt: dict[str, Any],
                        base: dict[str, Any]) -> None:
    """A requested Sideagent absent from the persisted role is a note only.

    Recovery does not start again and does not change the live session's role.
    """
    if item.get("role") not in ("sideagent", "sidekick"):
        return
    persisted = receipt.get("session_role") if isinstance(receipt, dict) else None
    if persisted not in ("host", "sideagent", "sidekick", "expert", "elite", "worker"):
        persisted = None
    if persisted in ("sideagent", "sidekick"):
        return
    evidence = base.get("evidence")
    if not isinstance(evidence, dict):
        evidence = {}
        base["evidence"] = evidence
    shown = "null" if persisted is None else persisted
    evidence["role_note"] = (
        f"persisted session_role is {shown}; requested Sideagent was not applied"
    )


def recover_or_send(item: dict[str, Any], repo: str, script: Path, base: dict[str, Any],
                    receipt: dict[str, Any], prior: dict[str, Any] | None) -> dict[str, Any]:
    note_persisted_role(item, receipt, base)
    seen_repo = repo_of(receipt)
    if not same_repo(seen_repo, repo):
        base.update(status="unknown", reason="repo-mismatch")
        return base
    remember_holder(item, base, receipt)
    holder = holder_of(receipt)
    expected = item.get("expected_holder_instance_id")
    if isinstance(expected, str) and holder and holder != expected:
        base.update(status="unknown", reason="holder-mismatch")
        return base
    finger = fingerprint_of(receipt)
    mutation = mutation_of(receipt)
    outcome = receipt.get("outcome") if isinstance(receipt.get("outcome"), str) else None
    bound = assignment_bound(prior, item, receipt, repo, base["prompt_sha256"])
    # A refused admission row records that nothing was started or sent; it
    # binds no assignment that a first send could replay.
    never_ran = (isinstance(prior, dict) and prior.get("status") == "not-run"
                 and not prior.get("holder_instance_id") and not prior.get("prompt_fingerprint"))
    if isinstance(prior, dict) and not bound and not never_ran:
        base.update(status="unknown", reason="assignment-unbound", prompt_fingerprint=finger,
                    holder_instance_id=holder)
        return base
    if bound and mutation not in (None, "not_started") and finger and not fingers_equal(finger, prior.get("prompt_fingerprint")) and not fingers_equal(finger, prior.get("prompt_sha256")):
        base.update(status="unknown", reason="fingerprint-differs", prompt_fingerprint=finger,
                    holder_instance_id=holder)
        return base
    if bound and mutation not in (None, "not_started") and (mutation == "unknown" or outcome == "unknown"):
        base.update(status="unknown", reason="mutation-ambiguous", prompt_fingerprint=finger,
                    holder_instance_id=holder)
        return base
    if mutation == "not_started":
        report = selection_report(item["_requested"], receipt)
        base["selection"] = report
        if applied_mismatch(report):
            base.update(status="failed", reason="selection-mismatch", holder_instance_id=holder)
            return base
        return send_item(item, repo, script, base)
    if bound:
        kept = prior.get("status") if prior.get("status") in ("returned", "failed", "unknown") else "in-flight"
        reason = "already-collected" if kept == "returned" else "already-admitted"
        base.update(
            status=kept,
            reason=reason,
            prompt_fingerprint=finger or prior.get("prompt_fingerprint"),
            holder_instance_id=holder,
            dispatch_event_cursor=prior.get("dispatch_event_cursor") or nested(receipt, "dispatch_event_cursor"),
            acceptance=prior.get("acceptance") or "pending",
        )
        if prior.get("result") is not None:
            base["result"] = prior["result"]
        return base
    if finger and not bound:
        base.update(status="unknown", reason="existing-session-ambiguous", prompt_fingerprint=finger,
                    holder_instance_id=holder)
        return base
    if mutation == "unknown" or outcome == "unknown":
        base.update(status="unknown", reason="mutation-ambiguous", holder_instance_id=holder)
        return base
    base.update(status="unknown", reason="existing-session-ambiguous", holder_instance_id=holder)
    return base


def send_item(item: dict[str, Any], repo: str, script: Path, base: dict[str, Any]) -> dict[str, Any]:
    code, receipt, note = run_runner(script, launch_argv(item, repo, "send"))
    base["evidence"]["send"] = evidence(receipt, code, note)
    unread = receipt_unreadable(code, receipt, note)
    if unread:
        base.update(status="unknown", reason="send-" + unread)
        return base
    error = receipt.get("error") if isinstance(receipt, dict) else None
    if isinstance(error, dict) and error.get("code") == "holder-instance-mismatch":
        base.update(status="unknown", reason="holder-mismatch")
        return base
    if runner_refused(code, receipt):
        base.update(status="failed", reason="send-failed")
        return base
    mutation = mutation_of(receipt)
    outcome = receipt.get("outcome") if isinstance(receipt, dict) and isinstance(receipt.get("outcome"), str) else None
    holder = holder_of(receipt) or base.get("holder_instance_id")
    finger = fingerprint_of(receipt)
    if mutation == "unknown" or outcome == "unknown":
        base.update(status="unknown", reason="mutation-unknown", holder_instance_id=holder,
                    prompt_fingerprint=finger)
        return base
    base.update(
        status="in-flight",
        reason="admitted",
        acceptance="pending",
        prompt_fingerprint=finger,
        dispatch_event_cursor=nested(receipt, "dispatch_event_cursor"),
        holder_instance_id=holder,
    )
    if base.get("prompt_fingerprint") is None:
        base["prompt_fingerprint_state"] = "unknown"
    return base


def coverage(items: list[dict[str, Any]]) -> dict[str, list[str]]:
    grouped = {label: [] for label in COVERAGE}
    for item in items:
        grouped.setdefault(item.get("status") or "unknown", []).append(item.get("item_id"))
    return grouped


class IndexLock:
    """Exclusive lock on an existing dispatch index for one read-modify-write,
    across threads and processes. The index is replaced by rename, so the
    lock counts only once it is held on the file the path still names."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.fd: int | None = None

    def __enter__(self) -> "IndexLock":
        INDEX_LOCK.acquire()
        try:
            while True:
                try:
                    fd = os.open(self.path, os.O_RDONLY)
                except FileNotFoundError:
                    return self
                fcntl.flock(fd, fcntl.LOCK_EX)
                try:
                    current = os.stat(self.path).st_ino == os.fstat(fd).st_ino
                except FileNotFoundError:
                    current = False
                if current:
                    self.fd = fd
                    return self
                os.close(fd)
        except BaseException:
            INDEX_LOCK.release()
            raise

    def __exit__(self, *exc: Any) -> None:
        if self.fd is not None:
            fcntl.flock(self.fd, fcntl.LOCK_UN)
            os.close(self.fd)
        INDEX_LOCK.release()


_ABSENT = object()


def pending_correlation(row: Any) -> bool:
    """True when omission from this plan must not drop the assignment.

    ``in-flight`` stays, including a disposition already mirrored onto it.
    ``unknown`` stays until a later fact changes that status. A mirrored
    acceptance does not drop it. ``returned`` and ``failed`` stay while
    acceptance is absent, ``pending``, ``undecided``, or ``repair``.
    ``repair`` is an open repair reference, not settlement of the duty.
    ``not-run`` is not an assignment. ``accepted``, ``cancelled``,
    ``superseded``, and ``handed-off`` on ``returned`` or ``failed`` do
    not stay.
    """
    if not isinstance(row, dict):
        return False
    status = row.get("status")
    if status in ("in-flight", "unknown"):
        return True
    if status not in ("returned", "failed"):
        return False
    return row.get("acceptance") in (None, "pending", "undecided", "repair")


def merge_index_rows(disk: list[Any], base: list[Any], mine: list[Any]) -> list[Any]:
    """Three-way merge by item and field.

    A field this writer changed since it read ``base`` is its own. Every
    other field on a row this writer still emits keeps the disk value.
    A row another writer added stays. A row this writer read but did not
    emit stays only when the locked disk row is still pending correlation.
    The older baseline status does not keep a row the lock already settled.
    The kept bytes are the disk row. A ``not-run`` row does not stay. A ``returned`` or
    ``failed`` row stays for an open acceptance or ``repair``, and does not
    stay for ``accepted``, ``cancelled``, ``superseded``, or ``handed-off``.
    A per-result disposition is not settlement of every duty.
    """
    def rows(items: list[Any]) -> dict[str, dict[str, Any]]:
        return {row["item_id"]: row for row in items
                if isinstance(row, dict) and isinstance(row.get("item_id"), str)}
    on_disk, before = rows(disk), rows(base)
    merged: list[Any] = []
    seen: set[Any] = set()
    for row in mine:
        ident = row.get("item_id") if isinstance(row, dict) else None
        seen.add(ident)
        theirs, prior = on_disk.get(ident), before.get(ident)
        if theirs is None or prior is None or theirs == prior:
            merged.append(row)
            continue
        out = dict(theirs)
        for key in set(row) | set(prior):
            if row.get(key, _ABSENT) != prior.get(key, _ABSENT):
                if key in row:
                    out[key] = row[key]
                else:
                    out.pop(key, None)
        merged.append(out)
    for ident, row in on_disk.items():
        if ident in seen:
            continue
        if ident not in before or pending_correlation(row):
            merged.append(row)
    return merged


def finish_index(index: dict[str, Any], path: str | None, emit_stdout: bool = True,
                 write: bool = True, base: dict[str, Any] | None = None) -> int:
    """Write the index. With ``base`` (this writer's rows as it read them,
    then as it last meant them), rows are merged with what is on disk and
    ``base`` takes this write's own rows for the next write."""
    index["coverage"] = coverage(index["items"])
    payload = index
    if path and write:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with IndexLock(target):
            if base is not None:
                intent = json.loads(json.dumps(index["items"]))
                try:
                    disk = load_object(target) if target.exists() else None
                except ValueError:
                    disk = None
                if isinstance(disk, dict) and isinstance(disk.get("items"), list):
                    index["items"] = merge_index_rows(disk["items"], base.get("items") or [], index["items"])
                    index["coverage"] = coverage(index["items"])
                base["items"] = intent
            atomic_write(target, json.dumps(index, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
        payload = dict(index)
        payload["index_path"] = str(target)
    if not emit_stdout:
        return 0
    return emit(payload)


EXCERPT_CHARS = 480


def result_excerpt(receipt: dict[str, Any] | None) -> str | None:
    text = result_text(receipt)
    return None if text is None else text[:EXCERPT_CHARS]


def result_text(receipt: dict[str, Any] | None) -> str | None:
    """The reply text a capture holds, uncut; callers mark any cut."""
    if not isinstance(receipt, dict):
        return None
    events = receipt.get("events")
    if not isinstance(events, list):
        record = receipt.get("record")
        events = record.get("events") if isinstance(record, dict) else None
    chunks: list[str] = []
    lines: list[str] = []
    if isinstance(events, list):
        for event in events:
            if not isinstance(event, dict):
                continue
            update = event.get("update")
            if isinstance(update, dict) and update.get("sessionUpdate") == "agent_message_chunk":
                content = update.get("content")
                piece = content.get("text") if isinstance(content, dict) and content.get("type") == "text" else None
                if isinstance(piece, str) and piece:
                    chunks.append(piece)
                continue
            if event.get("role") not in (None, "assistant"):
                continue
            content = event.get("content") or event.get("text")
            if isinstance(content, str) and content.strip():
                lines.append(content.strip())
    parts: list[str] = []
    if chunks:
        parts.append("".join(chunks))
    parts.extend(lines)
    if not parts and isinstance(receipt.get("text"), str) and receipt["text"].strip():
        parts.append(receipt["text"].strip())
    if not parts:
        return None
    return "\n".join(parts)


OUTPUT_KINDS = ("file", "capture", "remote", "description")


def output_kind(output: Any) -> str:
    """What a declared output names: a local file (checked), the reply
    capture itself, a remote locator, or a description of the deliverable.
    An explicit `kind` wins; a bare string is a file only when it reads as
    a path, so a sentence describing the reply is never reported absent."""
    if isinstance(output, dict):
        if output.get("kind") in OUTPUT_KINDS:
            return output["kind"]
        path = output.get("path")
        if isinstance(path, str) and path.strip():
            return "remote" if "://" in path else "file"
        output = output.get("locator")
    if not isinstance(output, str) or not output.strip():
        return "description"
    text = output.strip()
    if "://" in text:
        return "remote"
    if text.lower() in ("capture", "reply"):
        return "capture"
    if (text.startswith(("/", "~/")) or text.split("/", 1)[0] in (".", "..")
            or not any(char.isspace() for char in text)):
        return "file"
    return "description"


def output_facts(output: Any, repo: str, reply_present: bool | None = None) -> dict[str, Any] | None:
    """A declared output's kind and locator; a local file is checked for
    existence, the capture kind by the reply text. Absence is a gap for the
    Host to judge, never a transport failure."""
    if output is None:
        return None
    kind = output_kind(output)
    if kind == "capture":
        return {"declared": output, "kind": kind, "checked": reply_present is not None,
                **({"present": reply_present} if reply_present is not None else {})}
    if kind != "file":
        return {"declared": output, "kind": kind, "checked": False}
    path = output.get("path") if isinstance(output, dict) else output
    if not isinstance(path, str) or not path.strip():
        return {"declared": output, "kind": kind, "checked": False}
    path = os.path.expanduser(path.strip())
    target = Path(path) if Path(path).is_absolute() else Path(repo) / path
    return {"declared": output, "kind": kind, "path": str(target), "checked": True, "present": target.exists()}


def turn_facts(receipt: dict[str, Any]) -> tuple[Any, Any, Any]:
    turn = receipt.get("turn") if isinstance(receipt.get("turn"), dict) else {}
    active = receipt.get("turn_active")
    if active is None:
        active = turn.get("active")
    outcome = receipt.get("turn_outcome")
    if not isinstance(outcome, str):
        outcome = turn.get("outcome") if isinstance(turn.get("outcome"), str) else None
    if not isinstance(outcome, str) and isinstance(receipt.get("outcome"), str):
        outcome = receipt["outcome"]
    stop = receipt.get("stop_reason") if isinstance(receipt.get("stop_reason"), str) else None
    if stop is None and isinstance(turn.get("stop_reason"), str):
        stop = turn["stop_reason"]
    if stop is None:
        last_stop = last_prompt(receipt).get("stop_reason")
        if isinstance(last_stop, str):
            stop = last_stop
    return active, outcome, stop


def completed_turn(receipt: dict[str, Any]) -> bool:
    active, outcome, stop = turn_facts(receipt)
    if active is True:
        return False
    mutation = mutation_of(receipt)
    done = mutation in ("completed", "accepted") and outcome in ("turn_completed", "accepted")
    return done or (mutation in ("completed", "accepted") and stop == "end_turn" and active is not True)


def collect_one(item: dict[str, Any], repo: str, skills_root: Path) -> dict[str, Any]:
    kept = dict(item)
    if item.get("status") != "in-flight":
        return kept
    platform = item.get("platform")
    if not isinstance(platform, str):
        preset = item.get("preset")
        platform = preset.split("/", 1)[0] if isinstance(preset, str) and "/" in preset else None
    script = None if not platform else skills_root / f"{platform}-kaola-project-runner" / "scripts" / "runtime-tmux.sh"
    if script is None or not script.is_file():
        kept.update(status="unknown", reason="runner-missing")
        return kept
    probe = {"session": item.get("session"), "dispatch_event_cursor": item.get("dispatch_event_cursor")}
    code, receipt, note = run_runner(script, launch_argv(probe, repo, "status"))
    kept.setdefault("evidence", {})
    if not isinstance(kept["evidence"], dict):
        kept["evidence"] = {}
    kept["evidence"]["collect_status"] = evidence(receipt, code, note)
    unread = receipt_unreadable(code, receipt, note)
    if unread or not isinstance(receipt, dict):
        kept.update(status="unknown", reason="collect-" + (unread or "unreadable"))
        return kept
    if not same_repo(repo_of(receipt), repo):
        kept.update(status="unknown", reason="repo-mismatch")
        return kept
    if item.get("session") and receipt.get("session") not in (None, item["session"]):
        kept.update(status="unknown", reason="session-mismatch")
        return kept
    holder = holder_of(receipt)
    if item.get("holder_instance_id") and holder and holder != item["holder_instance_id"]:
        kept.update(status="unknown", reason="holder-mismatch")
        return kept
    finger = fingerprint_of(receipt)
    if finger and not fingers_equal(finger, item.get("prompt_fingerprint")) and not fingers_equal(finger, item.get("prompt_sha256")):
        kept.update(status="unknown", reason="fingerprint-differs", prompt_fingerprint=finger)
        return kept
    active, outcome, stop = turn_facts(receipt)
    kept["turn_active"] = active
    kept["turn_outcome"] = outcome
    kept["stop_reason"] = stop
    if isinstance(item.get("dispatch_event_cursor"), int):
        kept["capture_since"] = item["dispatch_event_cursor"]
    mutation = mutation_of(receipt)
    if mutation == "unknown" or outcome == "unknown":
        kept.update(status="unknown", reason="mutation-unknown")
        return kept
    if outcome in ("turn_failed", "turn_canceled", "process_exited") or receipt.get("result") == "refused":
        kept.update(status="failed", reason="turn-failed", acceptance="pending")
        return kept
    if active is True:
        kept.update(status="in-flight", reason="still-running", acceptance="pending")
        return kept
    if runner_refused(code, receipt):
        kept.update(status="failed", reason="turn-failed", acceptance="pending")
        return kept
    if not completed_turn(receipt):
        kept.update(status="in-flight", reason="no-result", acceptance="pending")
        return kept
    cap_code, capture, cap_note = run_runner(script, launch_argv(probe, repo, "capture"))
    kept["evidence"]["capture"] = evidence(capture, cap_code, cap_note)
    if receipt_unreadable(cap_code, capture, cap_note):
        kept.update(status="unknown", reason="capture-" + (receipt_unreadable(cap_code, capture, cap_note) or "unreadable"))
        return kept
    cursor = item.get("dispatch_event_cursor")
    if isinstance(cursor, bool) or not isinstance(cursor, int):
        cursor = None
    text = result_text(capture)
    gaps = []
    if text is None:
        gaps.append("reply-text-absent")
    if isinstance(capture, dict) and capture.get("truncated"):
        gaps.append("capture-truncated")
    output = output_facts(item.get("output"), repo, reply_present=text is not None)
    if output and output.get("kind") == "file" and output.get("present") is False:
        gaps.append("output-absent")
    # A new return is a new candidate: any earlier disposition answered the
    # earlier result only.
    if item.get("acceptance") not in (None, "pending"):
        kept["prior_acceptance"] = item["acceptance"]
    kept.update(
        status="returned",
        reason="collected",
        acceptance="pending",
        result={"excerpt": None if text is None else text[:EXCERPT_CHARS],
                "excerpt_truncated": text is not None and len(text) > EXCERPT_CHARS,
                "reply_chars": None if text is None else len(text),
                "stop_reason": stop, "cursor": cursor,
                "turn": {"holder_instance_id": holder or item.get("holder_instance_id"),
                         "prompt_fingerprint": item.get("prompt_fingerprint")},
                "locator": {"platform": platform, "session": item.get("session"),
                            "argv": ["capture", "--repo", repo, "--session", str(item.get("session")),
                                     "--full", "--inline"],
                            "since": cursor, "event_log_path": nested(capture, "event_log_path")},
                **({"output": output} if output else {}),
                "gaps": gaps},
    )
    return kept


def command_collect(args: argparse.Namespace) -> int:
    try:
        index = load_object(Path(args.index))
    except ValueError as exc:
        return fail("invalid-input", str(exc))
    if index.get("schema") != "kaola-dispatch-index/1" or not isinstance(index.get("items"), list):
        return fail("invalid-input", "collect needs a dispatch index")
    repo = index.get("repo")
    if not isinstance(repo, str):
        return fail("invalid-input", "index repo is required")
    if args.item:
        matches = [item for item in index["items"]
                   if isinstance(item, dict) and item.get("item_id") == args.item]
        if len(matches) != 1:
            return fail("invalid-input", "--item must name one exact index item")
        return read_turn(matches[0], repo, Path(args.skills_root), args.index)
    skills_root = Path(args.skills_root)
    pending = [item for item in index["items"] if isinstance(item, dict) and item.get("status") == "in-flight"]
    updated: dict[str, dict[str, Any]] = {}
    own = list(index["items"])
    base = {"items": json.loads(json.dumps(own))}

    def rows() -> list[Any]:
        return [updated[item["item_id"]] if isinstance(item, dict) and item.get("item_id") in updated else item
                for item in own]

    def publish() -> None:
        index["items"] = rows()
        index["phase"] = "collection"
        finish_index(index, args.index, emit_stdout=False, base=base)

    if pending:
        with ThreadPoolExecutor(max_workers=len(pending)) as pool:
            futures = {
                pool.submit(collect_one, item, repo, skills_root): item
                for item in pending
            }
            for future in as_completed(futures):
                item = futures[future]
                try:
                    updated[item["item_id"]] = future.result()
                except Exception as exc:
                    failed = dict(item)
                    failed.update(status="unknown", reason="collection-error", detail=str(exc))
                    updated[item["item_id"]] = failed
                publish()
    index["items"] = rows()
    index["phase"] = "collection"
    return finish_index(index, args.index, base=base)


def read_turn(item: dict[str, Any], repo: str, skills_root: Path, index_path: str) -> int:
    """One read-only projection. Full native capture keeps evidence outside the excerpt."""
    platform = item.get("platform") or str(item.get("preset", "")).split("/", 1)[0]
    script = skills_root / f"{platform}-kaola-project-runner" / "scripts" / "runtime-tmux.sh"
    cursor = item.get("dispatch_event_cursor")
    result: dict[str, Any] = {
        "schema": "kaola-dispatch-turn/1", "item_id": item.get("item_id"),
        "repo": repo, "session": item.get("session"),
        "holder_instance_id": item.get("holder_instance_id"),
        "source": {"index": index_path, "runner": str(script), "since": cursor,
                   "as_of": observed_at()},
        "unknown_reasons": [], "outcome": None, "stop_reason": None,
        "permission_evidence": [], "failure_evidence": [], "excerpt": None,
        "range_complete": None,
        "truncation": {"reply": False, "evidence": False},
    }
    unknown = result["unknown_reasons"]

    def compact(payload: dict[str, Any], raw: dict[str, Any]) -> dict[str, Any]:
        text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        size = len(text.encode("utf-8"))
        if size <= 2048:
            return payload
        # Keep identities and cursors even when bodies move to the raw capture.
        fields = ("cursor", "kind", "sessionId", "request_id", "tool_call_id",
                  "toolCallId", "sessionUpdate", "status", "prompt_fingerprint",
                  "outcome", "stop_reason", "code", "threadStatus", "option")
        summary = {key: payload[key] for key in fields if key in payload}
        for key in ("request", "update", "error", "fatal_error"):
            value = payload.get(key)
            if isinstance(value, dict):
                summary[key] = {field: value[field] for field in fields if field in value}
        summary.update(truncated=True, payload_bytes=size,
                       payload_excerpt=text.encode("utf-8")[:480].decode("utf-8", errors="ignore"), raw=raw)
        if len(json.dumps(summary, ensure_ascii=False).encode("utf-8")) > 2048:
            # Oversized identities are bodies too; the raw cursor stays exact.
            summary = {"cursor": raw.get("cursor"), "truncated": True,
                       "payload_bytes": size, "payload_excerpt": text[:240], "raw": raw}
        result["truncation"]["evidence"] = True
        return summary

    def finish() -> int:
        # Counts describe all inspected, retained evidence, including entries
        # omitted from this view. Unknown/unavailable ranges never prove absence.
        for operation, argv_key in (("status", "status_argv"), ("after_status", "status_argv"),
                                    ("capture", "capture_argv")):
            facts = result["source"].get(operation)
            if facts is not None:
                size = len(json.dumps(facts, ensure_ascii=False).encode("utf-8"))
                if size > 1024:
                    result["source"][operation] = {
                        "truncated": True, "payload_bytes": size,
                        "raw": {"source": "source", "argv_key": argv_key}}
                    result["truncation"]["evidence"] = True
        summaries = result["evidence_summary"] = {}
        for key in ("failure_evidence", "permission_evidence", "pending_permissions"):
            entries = result.get(key)
            count = len(entries) if isinstance(entries, list) else None
            if key != "pending_permissions":
                label = key.removesuffix("_evidence")
                result[label + "_count"] = count if result["range_complete"] is True else None
                result["retained_" + label + "_count"] = count
                result[label + "_present"] = (True if count else
                    False if result["range_complete"] is True else None)
            else:
                result["pending_permission_count"] = count
            if not isinstance(entries, list):
                continue
            cursors = [entry["cursor"] for entry in entries
                       if isinstance(entry, dict) and isinstance(entry.get("cursor"), int)]
            summaries[key] = {
                "count": count, "shown_entries": count, "omitted_entries": 0,
                "body_truncated_entries": sum(isinstance(entry, dict) and entry.get("truncated") is True
                                              for entry in entries),
                "first_cursor": min(cursors) if cursors else None,
                "last_cursor": max(cursors) if cursors else None,
                "omitted_first_cursor": None, "omitted_last_cursor": None,
                # One exact raw range locator replaces hundreds of repeated paths.
                "raw": ({"events": {"source": "source", "argv_key": "capture_argv",
                         "since": cursor, "through": result["source"].get("through")},
                         "status": {"source": "source", "argv_key": "status_argv"}}
                        if key != "pending_permissions" else
                        {"source": "source", "argv_key": "status_argv"}),
            }
        result["count_scope"] = ("complete-range totals or null; retained counts are inspected lower bounds; "
                                 "failure entries are observations, recovered ones included; outcome is the turn verdict")
        result["view_limit_bytes"] = 8192
        def text() -> str:
            return json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"

        # Measure the entire returned encoding, including the final newline.
        while len(text().encode("utf-8")) > 8192:
            keys = [key for key in summaries if result[key]]
            if not keys:
                break
            key = max(keys, key=lambda key: len(json.dumps(result[key], ensure_ascii=False).encode("utf-8")))
            entry = result[key].pop()
            summary = summaries[key]
            summary["shown_entries"] -= 1
            summary["omitted_entries"] += 1
            entry_cursor = entry.get("cursor") if isinstance(entry, dict) else None
            if isinstance(entry_cursor, int):
                summary["omitted_first_cursor"] = entry_cursor
                if summary["omitted_last_cursor"] is None:
                    summary["omitted_last_cursor"] = entry_cursor
            result["truncation"]["evidence"] = True
        sys.stdout.write(text())
        return 0

    if not same_repo(item.get("repo"), repo):
        unknown.append("dispatch-repo-mismatch")
        return finish()
    if (not isinstance(item.get("holder_instance_id"), str) or not item["holder_instance_id"]
            or not isinstance(item.get("session"), str) or not SESSION_OK.fullmatch(item["session"])
            or not finger_norm(item.get("prompt_fingerprint") or item.get("prompt_sha256"))
            or isinstance(cursor, bool) or not isinstance(cursor, int) or cursor < 0):
        unknown.append("dispatch-binding-missing")
        return finish()
    if not script.is_file():
        unknown.append("runner-missing")
        return finish()

    def bound(receipt: dict[str, Any] | None) -> bool:
        return (isinstance(receipt, dict) and same_repo(repo_of(receipt), repo)
                and receipt.get("session") == item["session"]
                and holder_of(receipt) == item["holder_instance_id"])

    status_raw = {"runner": str(script), "argv": launch_argv(item, repo, "status")}
    result["source"]["status_argv"] = status_raw["argv"]
    code, status, note = run_runner(script, status_raw["argv"])
    result["source"]["status"] = evidence(status, code, note)
    status_at = observed_at()
    unread = receipt_unreadable(code, status, note)
    if unread or not bound(status):
        unknown.append("status-" + (unread or "identity-unbound"))
        return finish()
    current_turn = fingers_equal(fingerprint_of(status), item.get("prompt_fingerprint") or item.get("prompt_sha256"))
    if current_turn:
        active, outcome, stop = turn_facts(status)
        result.update(turn_active=active, outcome=outcome, stop_reason=stop)
        pending = nested(status, "pending_permissions")
        result["pending_permissions"] = [
            compact(entry, status_raw) if isinstance(entry, dict) else entry
            for entry in pending
        ] if isinstance(pending, list) else pending
        if result["pending_permissions"] is None:
            unknown.append("pending-permissions-unavailable")
        if status.get("truncated"):
            result["truncation"]["status"] = status["truncated"]
            unknown.append("status-truncated")
        for key in ("error", "fatal_error"):
            if status.get(key):
                result["failure_evidence"].append(compact({key: status[key]}, status_raw))
    # --full --inline uses the existing rotated-log reader and bypasses the tail budget.
    argv = ["capture", "--repo", repo, "--session", item["session"], "--full", "--inline"]
    cap_code, capture, cap_note = run_runner(script, argv)
    result["source"]["capture_argv"] = argv
    result["source"]["capture"] = evidence(capture, cap_code, cap_note)
    unread = receipt_unreadable(cap_code, capture, cap_note)
    # Capture has no holder field on current Runners; bracket it with status.
    after_code, after, after_note = run_runner(script, launch_argv(item, repo, "status"))
    result["source"]["after_status"] = evidence(after, after_code, after_note)
    capture_bound = (isinstance(capture, dict) and same_repo(repo_of(capture), repo)
                     and capture.get("session") == item["session"]
                     and holder_of(capture) in (None, item["holder_instance_id"]))
    after_unread = receipt_unreadable(after_code, after, after_note)
    # A readable receipt for another identity clears the verdict, before any retrieval failure.
    if (not unread and not capture_bound) or (not after_unread and not bound(after)):
        result.update(outcome=None, stop_reason=None, turn_active=None)
        unknown.append("capture-identity-unbound")
        return finish()
    if unread or after_unread:
        # The status verdict is identity- and fingerprint-bound; only the capture read failed.
        result["source"]["verdict_as_of"] = status_at
        unknown.append(("capture-" + unread) if unread else ("after-status-" + after_unread))
        return finish()
    result["source"]["event_log_path"] = capture.get("event_log_path")
    end_cursor = nested(status, "event_cursor")
    result["source"]["through"] = end_cursor
    events = capture.get("events")
    if (not isinstance(events, list) or isinstance(end_cursor, bool)
            or not isinstance(end_cursor, int) or end_cursor < cursor):
        unknown.append("event-range-unavailable")
        return finish()
    cursors = [event.get("cursor") for event in events if isinstance(event, dict)
               and isinstance(event.get("cursor"), int) and not isinstance(event.get("cursor"), bool)]
    window = sorted((event for event in events if isinstance(event, dict)
                     and isinstance(event.get("cursor"), int) and not isinstance(event.get("cursor"), bool)
                     and cursor < event["cursor"] <= end_cursor), key=lambda event: event["cursor"])
    terminal = next((event for event in window if event.get("kind") == "turn_ended"), None)
    expected = item.get("prompt_fingerprint") or item.get("prompt_sha256")
    if terminal:
        if not fingers_equal(terminal.get("prompt_fingerprint"), expected):
            result.update(outcome=None, stop_reason=None, turn_active=None)
            unknown.append("turn-fingerprint-differs")
            return finish()
        window = [event for event in window if event["cursor"] <= terminal["cursor"]]
        result.update(turn_active=False, outcome=terminal.get("outcome"), stop_reason=terminal.get("stop_reason"))
        result["source"]["through"] = terminal["cursor"]
    elif not current_turn:
        unknown.append("turn-fingerprint-unknown-or-differs")
        return finish()
    else:
        active, outcome, stop = turn_facts(status)
        result.update(turn_active=active, outcome=outcome, stop_reason=stop)
    if capture.get("truncated"):
        result["truncation"]["capture"] = capture["truncated"]
        result["truncation"]["evidence"] = True
        unknown.append("capture-truncated")
    if (len(window) != result["source"]["through"] - cursor
            or any(event["cursor"] != cursor + offset for offset, event in enumerate(window, 1))):
        result["truncation"]["evidence"] = True
        unknown.append("cursor-range-incomplete")
    result["range_complete"] = not any(reason in unknown for reason in
                                      ("capture-truncated", "cursor-range-incomplete"))
    result["source"]["oldest_available_cursor"] = min(cursors) if cursors else None
    reply_chars = 0
    for event in window:
        kind = event.get("kind")
        update = event.get("update") if isinstance(event.get("update"), dict) else {}
        raw = {"runner": str(script), "argv": argv,
               "event_log_path": capture.get("event_log_path"), "cursor": event["cursor"]}
        if kind in ("request_permission", "permission_answered", "permission_cancelled"):
            result["permission_evidence"].append(compact(event, raw))
        # Codex threadStatus is a transient wire observation, possibly from a
        # child thread. The holder owns identity/recovery and the turn verdict;
        # raw capture retains these signals without inventing event errors.
        if (kind in ("process_exited", "agent_message_error", "malformed_stdout")
                or event.get("error")
                or (kind == "turn_ended" and event.get("outcome") in ("turn_failed", "turn_canceled", "process_exited"))
                or (update.get("sessionUpdate") in ("tool_call", "tool_call_update")
                    and update.get("status") in ("failed", "error"))):
            result["failure_evidence"].append(compact(event, raw))
        if update.get("sessionUpdate") == "agent_message_chunk":
            content = update.get("content")
            if isinstance(content, dict) and isinstance(content.get("text"), str):
                reply_chars += len(content["text"])
    result["excerpt"] = result_excerpt({"events": window})
    result["truncation"]["reply"] = reply_chars > 480
    if result["outcome"] is None:
        unknown.append("turn-outcome-unavailable")
    return finish()


def command_snapshot(args: argparse.Namespace) -> int:
    try:
        state = load_object(Path(args.state))
    except ValueError as exc:
        return fail("invalid-input", str(exc))
    try:
        existing, _ = read_state_file(Path(args.out))
    except ValueError:
        existing = None
    if isinstance(existing, dict) and existing.get("schema") not in (None, LEGACY_STATE_SCHEMA):
        # A whole-body snapshot would drop the structured state it projects
        # (a newer schema included).
        return emit({"result": "refused", "reason": "state-managed",
                     "detail": f"{args.out} is {existing.get('schema')}; change it with `state update`"}, 2)
    body = json.dumps(state, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    parsed = json.loads(body)
    if not isinstance(parsed, dict):
        return fail("invalid-input", "nested body was not one object")
    outer = {"body": body}
    text = json.dumps(outer, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    again = json.loads(text)
    if set(again) != {"body"} or not isinstance(again.get("body"), str) or json.loads(again["body"]) != state:
        return fail("snapshot-unstable", "nested body did not round-trip")
    atomic_write(Path(args.out), text)
    return emit({
        "result": "written",
        "out": str(Path(args.out)),
        "body_is_string": True,
        "body_is_object": True,
    })


# -- lifecycle state (Issue #255) ---------------------------------------------

STATE_EXIT_CONFLICT = 3
REQUIRED_ON_CREATE = {
    "tasks": ("stage", "goal"),
    "holds": ("scope", "reason"),
    "alerts": ("level", "summary"),
    "decisions": ("owner", "question"),
}
HOST_ONLY_SECTIONS = ("project", "authorization", "sideagent")
RECORD_META = ("rev", "created_at", "updated_at", "source", "writer", "transcribed",
               "host_revision", "writer_holder")
ACTIVE_STAGES = ("doing", "review", "closeout")


class StateRefusal(Exception):
    def __init__(self, reason: str, detail: str, **extra: Any) -> None:
        super().__init__(detail)
        self.payload = {"result": "refused", "reason": reason, "detail": detail, **extra}


def json_arg(raw: str) -> Any:
    text = Path(raw[1:]).read_text(encoding="utf-8") if raw.startswith("@") else raw
    try:
        return json.loads(text)
    except ValueError as exc:
        raise ValueError(f"not JSON: {exc}") from exc


def merge_patch(target: Any, patch: Any) -> Any:
    """RFC 7386: objects merge, null deletes, anything else replaces."""
    if not isinstance(patch, dict):
        return patch
    result = dict(target) if isinstance(target, dict) else {}
    for key, value in patch.items():
        if value is None:
            result.pop(key, None)
        else:
            result[key] = merge_patch(result.get(key), value)
    return result


def empty_state() -> dict[str, Any]:
    state: dict[str, Any] = {section: {} for section in SECTIONS}
    state["sideagent"] = None
    for kind in RECORD_KINDS:
        state[kind] = {}
    state["retired"] = []
    state["maintenance"] = {}
    return state


def repo_of_state_file(path: Path) -> Path:
    resolved = path.resolve()
    return resolved.parent.parent if resolved.parent.name == ".kaola" else resolved.parent


def read_state_file(path: Path) -> tuple[dict[str, Any] | None, bytes | None]:
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        return None, None
    except OSError as exc:
        raise ValueError(f"{path}: {exc}") from exc
    if len(raw) > STATE_FILE_MAX_BYTES:
        raise ValueError(f"{path}: {len(raw)} bytes exceeds {STATE_FILE_MAX_BYTES}")
    try:
        doc = json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise ValueError(f"{path}: {exc}") from exc
    if not isinstance(doc, dict):
        raise ValueError(f"{path}: JSON must be one object")
    return doc, raw


def require_current(doc: dict[str, Any] | None, path: Path) -> dict[str, Any]:
    if doc is None:
        raise StateRefusal("state-missing", f"{path} does not exist; run `state init` or `state migrate`")
    if doc.get("schema") not in (None, LEGACY_STATE_SCHEMA, STATE_SCHEMA):
        raise StateRefusal("schema-unsupported", f"{path} declares schema {doc.get('schema')!r}, "
                           "which this Runner does not know; update the Runner")
    if doc.get("schema") != STATE_SCHEMA:
        raise StateRefusal("legacy-format", f"{path} is not {STATE_SCHEMA}; run `state migrate`")
    state = doc.get("state")
    if not isinstance(state, dict):
        raise StateRefusal("state-unreadable", f"{path} has no structured state object")
    for kind in RECORD_KINDS:
        if not isinstance(state.get(kind, {}), dict):
            raise StateRefusal("state-unreadable", f"state.{kind} must be an object keyed by id")
    return doc


class StateLock:
    """Exclusive lock on the state file's directory for one read-modify-write.

    Directory lock, so no lock file is left beside the state."""

    def __init__(self, path: Path) -> None:
        self.directory = path.resolve().parent
        self.fd: int | None = None

    def __enter__(self) -> "StateLock":
        self.directory.mkdir(parents=True, exist_ok=True)
        self.fd = os.open(self.directory, os.O_RDONLY)
        fcntl.flock(self.fd, fcntl.LOCK_EX)
        return self

    def __exit__(self, *exc: Any) -> None:
        if self.fd is not None:
            fcntl.flock(self.fd, fcntl.LOCK_UN)
            os.close(self.fd)


def short(value: Any, limit: int = 240) -> Any:
    """A view's text field, cut with an explicit omission note: the full
    text stays on the record (`state view --role sideagent`)."""
    if isinstance(value, str) and len(value) > limit:
        return value[:limit] + f"… [+{len(value) - limit} chars omitted; full text on the record]"
    return value


# Write metadata and alert coalescing change on every repeat without
# changing what the Host is asked to judge.
DIGEST_SKIP = (*RECORD_META, "count", "last_seen", "ack")


def judgment_digest(record: dict[str, Any]) -> str:
    """Short digest of what a Host judgment record asks, so the same id with a
    changed question, options, evidence or owner is new attention."""
    text = json.dumps({key: value for key, value in record.items() if key not in DIGEST_SKIP},
                      ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def task_attention(task_id: str, task: dict[str, Any]) -> list[dict[str, Any]]:
    found = []
    verdict = task.get("verdict") if isinstance(task.get("verdict"), dict) else None
    if task.get("stage") == "review" and not verdict:
        prior = task.get("prior_verdict") if isinstance(task.get("prior_verdict"), dict) else None
        # A later repair round repeats the same prior value; its new result,
        # evidence and prior Host turn are what make it a new judgment.
        found.append({"kind": "tasks", "id": task_id, "why": "awaiting-verdict",
                      **({"prior_verdict": prior.get("value")} if prior else {}),
                      "content": judgment_digest(task)})
    elif (task.get("stage") in ("closeout", "done")
          and (verdict or {}).get("value") not in ("accepted", "partial", "cancelled")):
        # Moving past review is a stage change, not a judgment: the Host is
        # still asked until it records one.
        found.append({"kind": "tasks", "id": task_id, "why": "verdict-missing", "stage": task["stage"],
                      "content": judgment_digest(task)})
    if isinstance(task.get("transcribed"), dict):
        found.append({"kind": "tasks", "id": task_id, "why": "transcribed-check",
                      "host_turn": task["transcribed"].get("host_turn"),
                      "fields": task["transcribed"].get("fields")})
    return found


def host_view(doc: dict[str, Any], path: Path) -> dict[str, Any]:
    """Projected Host view from the shared contract, field by field."""
    return RECORD.host_view(doc, path)


def maintenance_brief(state: dict[str, Any]) -> dict[str, Any]:
    """The last checkpoint identity and time beside current obligations, so
    a reader can see whether maintenance is progressing. No history."""
    maintenance = state.get("maintenance") or {}
    brief = {key: maintenance[key] for key in ("last_verified", "acked_host_revision",
                                               "handled_host_revision") if maintenance.get(key) is not None}
    last = maintenance.get("last_checkpoint")
    if isinstance(last, dict) and not last.get("verified"):
        brief["last_checkpoint"] = {key: last.get(key) for key in ("batch", "at", "verified")}
    return brief


def requirement_heading(title: str) -> bool:
    title = title.strip().lower()
    for name in USER_REQUIREMENT_HEADINGS:
        if title == name or (title.startswith(name) and not title[len(name)].isalnum()):
            return True
    return False


def requirement_lines(repo: Path) -> dict[str, Any]:
    """User special requirements, read from their one source: AGENTS.md."""
    source = repo / "AGENTS.md"
    try:
        lines = source.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {"source": str(source), "missing": "AGENTS.md is unreadable or absent", "items": []}
    start_marker, end_marker = USER_REQUIREMENT_MARKERS
    picked: list[str] | None = None
    if start_marker in lines and end_marker in lines:
        first, last = lines.index(start_marker), lines.index(end_marker)
        if first < last:
            picked = lines[first + 1:last]
    if picked is None:
        for number, line in enumerate(lines):
            match = re.match(r"^(#+)\s+(.*?)\s*$", line)
            if match and requirement_heading(match.group(2)):
                # A scoped heading such as "User special requirements — X (#N)"
                # counts too; every such section is reported, in file order.
                depth = len(match.group(1))
                picked = picked if picked is not None else []
                picked.append(line.strip())
                for follow in lines[number + 1:]:
                    heading = re.match(r"^(#+)\s", follow)
                    if heading and len(heading.group(1)) <= depth:
                        break
                    picked.append(follow)
    if picked is None:
        return {"source": str(source), "missing": "no user requirements region in AGENTS.md", "items": []}
    items = [line.strip() for line in picked if line.strip()]
    return {"source": str(source), "items": items}


def delegator_view(doc: dict[str, Any], path: Path, repo: Path) -> dict[str, Any]:
    """The report the Delegator gives at every inquiry, from the closed contract."""
    state = doc["state"]
    projected = RECORD.projected_state(state)
    tasks = projected.get("tasks") or {}

    def brief(task_id: str, task: dict[str, Any]) -> dict[str, Any]:
        return {"id": task_id, **{key: short(task.get(key)) for key in ("stage", "goal", "wait", "next")
                                  if task.get(key) is not None}}

    def rows(kind: str, fields: tuple[str, ...]) -> list[dict[str, Any]]:
        found = []
        for key, value in sorted((projected.get(kind) or {}).items()):
            if not isinstance(value, dict):
                continue
            if kind == "decisions" and value.get("status") == "settled" and not isinstance(
                    value.get("transcribed"), dict):
                continue
            found.append({"id": key, **{field: value.get(field) for field in fields if value.get(field) is not None}})
        return found

    return {
        "view": "delegator",
        "revision": doc.get("revision"),
        "as_of": doc.get("updated_at"),
        "user_requirements": requirement_lines(repo),
        "special": {
            "holds": rows("holds", ("scope", "preset", "presets", "pool", "pools", "reason", "owner",
                                    "resume_when", "next")),
            "alerts": rows("alerts", ("level", "summary", "impact", "owner", "next")),
            "decisions": rows("decisions", ("owner", "question", "status", "next")),
            "unverified": projected.get("unverified") or {},
        },
        "doing": [brief(key, value) for key, value in sorted(tasks.items())
                  if value.get("stage") in ACTIVE_STAGES],
        "todo": [brief(key, value) for key, value in sorted(tasks.items()) if value.get("stage") == "todo"],
        "outcomes": [brief(key, value) for key, value in sorted(tasks.items()) if value.get("stage") == "done"],
        "sideagent": projected.get("sideagent"),
        "unknown": RECORD.unknown_paths(state),
        "maintenance": maintenance_brief(state),
    }


def render_state(doc: dict[str, Any], path: Path, *, unchecked_live: bool = False) -> tuple[str, dict[str, int]]:
    """Serialize with the projected Host view as `body`; enforce the carrier
    bounds instead of truncating any responsibility.

    ``unchecked_live`` is a migration that was not given ``--live``. Missing
    live rows are not an old holder, so the current file bound applies.
    ``carrier-limit`` remains when a supplied live holder does not prove
    ``heartbeat-state/2``."""
    view = host_view(doc, path)
    body = json.dumps(view, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    doc["body"] = body
    text = json.dumps(doc, ensure_ascii=False, sort_keys=True, indent=1) + "\n"
    sizes = {"body_bytes": len(body.encode("utf-8")), "file_bytes": len(text.encode("utf-8"))}
    carrier = doc.get("carrier") if isinstance(doc.get("carrier"), dict) else {}
    capable = (carrier.get("capability") == STATE_CAPABILITY
               and not carrier_replaced_by_older(carrier, path))
    file_limit = STATE_FILE_MAX_BYTES if capable or unchecked_live else LEGACY_READER_MAX_BYTES
    sizes["file_limit"] = file_limit
    if sizes["body_bytes"] > HOST_VIEW_MAX_BYTES:
        raise StateRefusal("host-view-too-large",
                           "the projected Host view exceeds the carrier's injection bound; retire "
                           "finished records or move detail into evidence references", sizes=sizes)
    if sizes["file_bytes"] > file_limit:
        stop_recovery = (
            "Record an owner stop with state update --section project --set "
            "{\"stop\":\"...\"}; that write uses the current file bound. "
            "Other writes need a holder that advertises heartbeat-state/2, or retire finished records."
        )
        raise StateRefusal(
            "carrier-limit" if file_limit == LEGACY_READER_MAX_BYTES else "state-too-large",
            "the whole file exceeds what the recorded Host holder can read. " + stop_recovery
            if file_limit == LEGACY_READER_MAX_BYTES else
            "the whole file exceeds the state bound; retire finished records",
            recovery=stop_recovery if file_limit == LEGACY_READER_MAX_BYTES else
            "retire finished records",
            sizes=sizes,
        )
    return text, sizes


def runner_record_root() -> Path:
    root = os.environ.get("KAOLA_ACP_RECORD_ROOT")
    return Path(root) if root else (
        Path(os.environ.get("XDG_RUNTIME_DIR") or tempfile.gettempdir()) / f"kaola-{os.getuid()}")


def carrier_replaced_by_older(carrier: dict[str, Any], path: Path) -> bool:
    """Whether the recorded carrier's Host session now runs another holder
    that does not advertise the state capability: that Host reads only the
    legacy bound. Unknown (no platform recorded, no record) keeps the
    recorded carrier; `state check --live` reports it."""
    platform, session = carrier.get("platform"), carrier.get("session")
    if not isinstance(platform, str) or not isinstance(session, str):
        return False
    digest = hashlib.sha256(str(repo_of_state_file(path)).encode("utf-8")).hexdigest()[:16]
    try:
        record = json.loads((runner_record_root() / platform / session / digest / "record.json")
                            .read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    if not isinstance(record, dict) or record.get("holder_instance_id") == carrier.get("holder_instance_id"):
        return False
    pid = record.get("holder_pid")
    try:
        alive = isinstance(pid, int) and pid > 0 and (os.kill(pid, 0) is None)
    except OSError:
        alive = False
    return alive and STATE_CAPABILITY not in (record.get("holder_features") or [])


def check_writer(args: argparse.Namespace, state: dict[str, Any]) -> dict[str, str] | None:
    if args.writer not in WRITER_ROLES:
        raise StateRefusal("writer-refused", f"writer {args.writer!r} may not change lifecycle state")
    if not isinstance(args.source, str) or not args.source.strip():
        raise StateRefusal("source-required", "every state change names its source")
    caller = caller_dispatcher()
    binding = state.get("sideagent")
    role = caller_role(caller)
    if role is not None and ((args.writer == "host" and role != "host")
                             or (args.writer == "sideagent" and role not in SIDEAGENT_ROLES)):
        # The caller's own holder record names its role; a worker cannot
        # write as the Host or the Sideagent.
        raise StateRefusal("writer-refused", f"caller {caller['session']} runs as {role}, not as "
                           f"{args.writer}")
    if (args.writer == "sideagent" and caller and node_binding(binding)
            and caller["session"] == binding.get("session") and caller_role(caller) in SIDEAGENT_ROLES):
        # Node mode: each batch runs a fresh holder under the bound session
        # name. The session's own live record naming this caller proves the
        # previous node no longer holds it, so there is no competing writer.
        return dict(caller, role=caller_role(caller))
    if (args.writer == "sideagent" and caller and node_binding(binding)
            and caller["session"] == binding.get("session")):
        raise StateRefusal("binding-superseded", f"caller {caller['session']} ({caller['holder_instance_id']}) "
                           "is not the node holder the bound session's record names now")
    if args.writer == "sideagent" and caller:
        if not isinstance(binding, dict) or binding.get("state") not in ("active", "replacing"):
            raise StateRefusal("sideagent-unbound", "no maintenance Sideagent is bound in this state")
        bound_holder = binding.get("holder_instance_id")
        if (caller["session"] != binding.get("session")
                or (bound_holder and caller["holder_instance_id"] != bound_holder)):
            # A replaced Sideagent's late write must not undo its successor.
            raise StateRefusal("binding-superseded",
                               f"caller {caller['session']} ({caller['holder_instance_id']}) is not "
                               f"the bound Sideagent {binding.get('session')} ({bound_holder})")
    if (args.writer == "host" and caller and isinstance(binding, dict)
            and caller["session"] == binding.get("session")):
        raise StateRefusal("writer-mismatch", "the bound Sideagent writes as sideagent, never as host")
    return dict(caller, role=role) if caller else caller


def node_binding(binding: Any) -> bool:
    return (isinstance(binding, dict) and binding.get("mode") == "node"
            and binding.get("state") == "active")


def writer_trace(args: argparse.Namespace, caller: dict[str, Any] | None) -> str:
    """Who wrote, as far as this tool can tell. The writer flag is a trace,
    not an identity proof: a `host` write from a caller whose own record
    names no role says so instead of reading as a verified Host."""
    if not caller:
        return args.writer
    unverified = args.writer == "host" and caller.get("role") is None
    return f"{args.writer}:{caller['session']}" + (" (role unverified)" if unverified else "")


def caller_role(caller: dict[str, str] | None) -> str | None:
    """The session role the caller's own live holder record states, or None
    when it cannot be read (no caller, a legacy record without a role)."""
    if not caller:
        return None
    digest = hashlib.sha256(caller["repo"].encode("utf-8")).hexdigest()[:16]
    try:
        record = json.loads((runner_record_root() / caller["platform"] / caller["session"] / digest
                             / "record.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(record, dict) or record.get("holder_instance_id") != caller["holder_instance_id"]:
        return None
    role = record.get("session_role")
    return role if isinstance(role, str) and role else None


def observed_after(observed: Any, retired: Any) -> bool:
    try:
        return datetime.fromisoformat(str(observed)) > datetime.fromisoformat(str(retired))
    except (TypeError, ValueError):
        return False


def validate_record(kind: str, record: dict[str, Any]) -> str | None:
    unknown = RECORD.unknown_record_keys(kind, record)
    if unknown:
        return "unknown " + ", ".join(unknown)
    if kind == "tasks":
        if record.get("stage") not in TASK_STAGES:
            return f"stage must be one of {', '.join(TASK_STAGES)}"
        verdict = record.get("verdict")
        if verdict is not None and (not isinstance(verdict, dict) or verdict.get("value") not in VERDICTS):
            return f"verdict.value must be one of {', '.join(VERDICTS)}"
        dispositions = record.get("dispositions")
        if dispositions is not None and (not isinstance(dispositions, dict) or any(
                value not in DISPOSITIONS for value in dispositions.values())):
            return f"dispositions maps item ids to one of {', '.join(DISPOSITIONS)}"
    elif kind == "alerts":
        if record.get("level") not in ALERT_LEVELS:
            return f"level must be one of {', '.join(ALERT_LEVELS)}"
    elif kind == "decisions":
        if record.get("owner") not in DECISION_OWNERS:
            return f"owner must be one of {', '.join(DECISION_OWNERS)}"
        if record.get("status") not in (None, "pending", "settled"):
            return "status must be pending or settled"
    for key in ("dispatch", "evidence"):
        if key in record and not isinstance(record[key], (list, str)):
            return f"{key} must be a reference string or a list of references"
    return None


def apply_record_update(args: argparse.Namespace, doc: dict[str, Any], patch: dict[str, Any],
                        caller: dict[str, str] | None) -> dict[str, Any]:
    state = doc["state"]
    kind, record_id = args.kind, args.id
    if kind not in RECORD_KINDS:
        raise StateRefusal("invalid-input", f"kind must be one of {', '.join(RECORD_KINDS)}")
    if not isinstance(record_id, str) or not re.fullmatch(r"[A-Za-z0-9#][A-Za-z0-9_.:#/-]{0,79}", record_id):
        raise StateRefusal("invalid-input", "id must be a stable short identifier")
    if any(key in patch for key in RECORD_META):
        raise StateRefusal("invalid-input", f"{', '.join(RECORD_META)} are kept by the tool")
    rejected = RECORD.reject_record_patch(kind, patch)
    if rejected:
        raise StateRefusal("invalid-input", rejected["detail"], **{
            key: rejected[key] for key in ("path", "allowed", "recovery")
        }, unapplied=patch)
    records = state.setdefault(kind, {})
    current = records.get(record_id)
    stones = [stone for stone in state.get("retired") or []
              if stone.get("kind") == kind and stone.get("id") == record_id]
    if current is None and stones:
        if not (kind in ("holds", "alerts") and observed_after(patch.get("observed_at"), stones[-1].get("at"))):
            raise StateRefusal("record-retired", f"{kind}/{record_id} was retired; a late event does not "
                               "reopen it. A new occurrence of a stable hold or alert id names its "
                               "`observed_at`, later than the retirement; other work uses a new id",
                               retired=stones[-1], unapplied=patch)
    if "prior_verdict" in patch:
        raise StateRefusal("invalid-input", "prior_verdict is kept by the tool", unapplied=patch)
    coalesce = bool(getattr(args, "coalesce", False)) and kind == "alerts" and current is not None
    expected = args.expect_rev
    if not coalesce:
        actual = current.get("rev") if current else 0
        if current is not None and expected is None:
            raise StateRefusal("expect-rev-required", f"{kind}/{record_id} exists; pass --expect-rev",
                               current=current)
        if expected is not None and expected != actual:
            raise StateRefusal("conflict", f"{kind}/{record_id} is at rev {actual}, not {expected}",
                               current=current, unapplied=patch)
    if args.writer == "sideagent" and kind == "tasks":
        owned = [key for key in (*HOST_OWNED_TASK_FIELDS, "verdict") if key in patch]
        if owned and not args.host_turn:
            raise StateRefusal("host-turn-required",
                               f"{', '.join(owned)} are Host decisions; name the Host turn transcribed",
                               unapplied=patch)
    merged = merge_patch(current or {}, patch)
    if kind == "tasks" and isinstance(patch.get("dispatch"), list):
        merged["dispatch"] = RECORD.union_dispatch((current or {}).get("dispatch"), patch.get("dispatch"))
    if current is None:
        missing = [key for key in REQUIRED_ON_CREATE[kind] if merged.get(key) in (None, "")]
        if missing:
            raise StateRefusal("invalid-input", f"a new {kind} record needs {', '.join(missing)}")
        merged["created_at"] = observed_at()
    unknown = RECORD.unknown_record_keys(kind, merged)
    if unknown:
        raise StateRefusal(
            "invalid-input",
            f"{kind}.{unknown[0]} is not a current field. Run `state migrate` and read its removed list, "
            "or set this key to null.",
            path=f"{kind}.{unknown[0]}",
            allowed=", ".join(sorted(RECORD.RECORD_KEYS[kind])),
            recovery="run `state migrate` or set this key to null and retry. The file was not changed.",
            unapplied=patch,
        )
    typed = RECORD.record_type_problem(kind, merged)
    if typed:
        raise StateRefusal("invalid-input", typed["detail"], path=typed["path"],
                           allowed=typed["allowed"], recovery=typed["recovery"], unapplied=patch)
    problem = validate_record(kind, merged)
    if problem:
        raise StateRefusal("invalid-input", problem, unapplied=patch)
    if coalesce:
        merged["count"] = int(current.get("count") or 1) + 1
        merged["last_seen"] = observed_at()
    verdict = (current or {}).get("verdict")
    if (kind == "tasks" and patch.get("stage") == "review" and "verdict" not in patch
            and isinstance(verdict, dict) and verdict.get("value") in ("repair", "partial")):
        # Rework returned for review: the earlier verdict answered the earlier
        # review only, so this one waits for a new verdict.
        merged["prior_verdict"] = verdict
        merged.pop("verdict", None)
    if kind == "decisions" and patch.get("status") == "settled" and args.writer == "sideagent":
        if not args.host_turn or merged.get("evidence") in (None, "", []):
            raise StateRefusal("host-turn-required",
                               "a decision is settled by its owner: name the Host turn that "
                               "transcribed it and the evidence of the answer", unapplied=patch)
        merged["transcribed"] = {"host_turn": args.host_turn, "fields": ["status"]}
    elif kind == "decisions" and args.writer == "host":
        merged.pop("transcribed", None)
    if kind == "tasks" and args.writer == "sideagent" and args.host_turn:
        owned = [key for key in (*HOST_OWNED_TASK_FIELDS, "verdict") if key in patch]
        if owned:
            prior = (current or {}).get("transcribed") or {}
            merged["transcribed"] = {"host_turn": args.host_turn,
                                     "fields": sorted(set(prior.get("fields") or []) | set(owned))}
            if "verdict" in patch:
                merged["verdict"] = {**merged["verdict"], "by": "host", "host_turn": args.host_turn}
    elif kind == "tasks" and args.writer == "host":
        # The Host wrote or saw the record itself; nothing is left to echo back.
        merged.pop("transcribed", None)
        if "verdict" in patch:
            merged["verdict"] = {**merged["verdict"], "by": "host"}
    merged["rev"] = int((current or {}).get("rev") or 0) + 1
    merged["updated_at"] = observed_at()
    merged["source"] = args.source
    merged["writer"] = writer_trace(args, caller)
    stamp_writer(doc, merged, args, caller)
    records[record_id] = merged
    if (kind == "tasks" and "stage" in patch and patch.get("stage") in TASK_STAGES
            and (args.writer == "host" or (args.writer == "sideagent" and args.host_turn))):
        RECORD.clear_stage_warning(state, record_id)
    return merged


def stamp_writer(doc: dict[str, Any], target: dict[str, Any], args: argparse.Namespace,
                 caller: dict[str, str] | None) -> None:
    """A Host write carries the Host business revision it made; any write by
    a known holder carries that holder, so a checkpoint can tell its own
    applied evidence from older or unrelated records."""
    if args.writer == "host":
        target["host_revision"] = doc["host_revision"]
    if caller and caller.get("holder_instance_id"):
        target["writer_holder"] = caller["holder_instance_id"]
    else:
        target.pop("writer_holder", None)


def apply_section_update(args: argparse.Namespace, doc: dict[str, Any], patch: Any,
                         caller: dict[str, str] | None = None) -> Any:
    state = doc["state"]
    section = args.section
    if section not in SECTIONS:
        raise StateRefusal("invalid-input", f"section must be one of {', '.join(SECTIONS)}")
    if args.expect_revision is None or args.expect_revision != doc.get("revision"):
        raise StateRefusal("conflict", f"file is at revision {doc.get('revision')}, not "
                           f"{args.expect_revision}", current=state.get(section), unapplied=patch)
    binding = state.get("sideagent") if isinstance(state.get("sideagent"), dict) else {}
    if (section == "sideagent" and args.writer == "sideagent" and caller
            and patch == {"holder_instance_id": caller["holder_instance_id"]}
            and binding.get("session") == caller["session"] and not binding.get("holder_instance_id")):
        # The started Sideagent records its own holder once; nothing else.
        binding["holder_instance_id"] = caller["holder_instance_id"]
        note_section_source(state, args, section)
        return binding
    if section in HOST_ONLY_SECTIONS and args.writer != "host":
        raise StateRefusal("host-only", f"state.{section} is adopted by the Host", unapplied=patch)
    if section == "sideagent":
        if patch is not None and not isinstance(patch, dict):
            raise StateRefusal("invalid-input", "sideagent is one binding object or null")
        value = merge_patch(state.get("sideagent") or {}, patch) if patch is not None else None
        if value is not None:
            shaped = RECORD.section_shape_problems("sideagent", value)
            if shaped:
                first = shaped[0]
                raise StateRefusal("invalid-input", first["detail"], path=first["path"],
                                   allowed=first["allowed"], recovery=first["recovery"], unapplied=patch)
            if value.get("state") not in BINDING_STATES or not isinstance(value.get("session"), str):
                raise StateRefusal("invalid-input",
                                   f"binding needs session and state in {', '.join(BINDING_STATES)}")
            value["source"] = args.source
            value["since"] = value.get("since") if (state.get("sideagent") or {}).get(
                "session") == value["session"] else observed_at()
        state["sideagent"] = value
        note_section_source(state, args, section)
        return value
    if not isinstance(patch, dict):
        raise StateRefusal("invalid-input", f"state.{section} takes a JSON merge patch object")
    if section in ("project", "authorization", "recovery", "unverified"):
        merged_section = merge_patch(state.get(section) or {}, patch)
        if section == "project":
            blocked = RECORD.project_blockers(merged_section)
        elif section == "authorization":
            blocked = RECORD.authorization_blockers(merged_section)
        elif section == "recovery":
            blocked = []
            if isinstance(merged_section, dict):
                for key, value in merged_section.items():
                    if key not in RECORD.RECOVERY_KEYS:
                        blocked.append(RECORD.refusal(
                            f"recovery.{key}",
                            ", ".join(sorted(RECORD.RECOVERY_KEYS)),
                            "remove this key from the patch and retry; the file was not changed",
                        ))
                    elif key == "protected_untracked":
                        blocked.extend(RECORD.protected_blockers(value, "recovery.protected_untracked"))
            blocked.extend(RECORD.section_shape_problems("recovery", merged_section))
        else:
            blocked = RECORD.section_shape_problems("unverified", merged_section)
        if blocked:
            first = blocked[0]
            raise StateRefusal("invalid-input", first["detail"], path=first["path"],
                               allowed=first["allowed"], recovery=first["recovery"], unapplied=patch)
    if section == "unverified":
        # A resolved unknown leaves a machine tombstone. The source text is not copied.
        for key in sorted(key for key, value in patch.items()
                          if value is None and key in (state.get("unverified") or {})):
            stones = list(state.get("retired") or []) + [RECORD.machine_stone({
                "kind": "unverified", "id": key, "outcome": "resolved",
                "writer": args.writer, "at": observed_at()})]
            state["retired"] = stones[-TOMBSTONE_CAP:]
    state[section] = merge_patch(state.get(section) or {}, patch)
    note_section_source(state, args, section)
    return state[section]


def note_section_source(state: dict[str, Any], args: argparse.Namespace, section: str) -> None:
    """The current source of each section, beside it: who changed it, from what."""
    sources = state.get("section_sources") if isinstance(state.get("section_sources"), dict) else {}
    sources[section] = {"source": args.source, "writer": args.writer, "at": observed_at()}
    if args.writer == "host" and getattr(args, "_host_revision", None) is not None:
        sources[section]["host_revision"] = args._host_revision
    state["section_sources"] = sources


def session_name(value: Any) -> str | None:
    """A Runner session name. Migrated prose in `sessions` is a note, not a seat."""
    return value if isinstance(value, str) and SESSION_OK.fullmatch(value) else None


def seat_entries(task: dict[str, Any]) -> list[tuple[str, str | None]]:
    """Each seat a task itself names, with the holder instance recorded with
    it: migrated `assignments`, `sessions` (names or objects) and a duty's own
    `session` with its `holder_instance_id`. A string that is not a session
    name stays on the task and is not a seat."""
    found: list[tuple[str, str | None]] = []
    rows = [row for row in task.get("assignments") or [] if isinstance(row, dict)]
    rows += [row for row in task.get("sessions") or [] if isinstance(row, dict)]
    rows += [{"session": name} for name in task.get("sessions") or [] if session_name(name)]
    if session_name(task.get("session")):
        rows.append({"session": task.get("session"), "holder_instance_id": task.get("holder_instance_id")})
    for row in rows:
        name = session_name(row.get("session"))
        if not name:
            continue
        holder = row.get("holder_instance_id")
        found.append((name, holder if isinstance(holder, str) and holder else None))
    return found


def task_seats(task: dict[str, Any]) -> dict[str, list[str]]:
    """Seat name to every holder instance recorded for it. A name with no
    recorded holder is the only one a bare stopped row can prove."""
    seats: dict[str, list[str]] = {}
    for session, holder in seat_entries(task):
        holders = seats.setdefault(session, [])
        if holder and holder not in holders:
            holders.append(holder)
    return {session: sorted(holders) for session, holders in seats.items()}


def open_seats(seats: dict[str, list[str]], rows: list[dict[str, Any]]) -> list[str]:
    """A named seat is shown stopped only by a live-row listing that has its
    session stopped, under its recorded holder when one is recorded; a
    missing row, a row of another holder, live or stopped, or two different
    recorded holders leave the association unresolved rather than proving
    cleanup. A holder instance id is unique, so it also fixes platform and
    root."""
    problems = []
    for session, holders in sorted(seats.items()):
        matches = [row for row in rows if row.get("session") == session]
        running = [row for row in matches if row.get("state") != "stopped"]
        own = [row for row in matches if not holders or row.get("holder_instance_id") in holders]
        if len(holders) > 1:
            problems.append(f"{session} has conflicting recorded holders {', '.join(holders)}; the "
                            "association is unresolved")
        elif not matches:
            problems.append(f"{session} is not in the live rows; its stop is not shown")
        elif any(row in own for row in running):
            problems.append(f"{session} is still live")
        elif running or not own:
            other = (running or matches)[0]
            problems.append(f"{session} is {'live' if running else 'stopped'} under holder "
                            f"{other.get('holder_instance_id')}, not the recorded "
                            f"{holders[0] if holders else None}; the association is unresolved")
    return problems


def open_dispatch(task: dict[str, Any], args: argparse.Namespace) -> list[str]:
    """Why a task's dispatched items are not shown closed: each needs an index
    row that is no longer in flight and, when the task names sessions, live
    rows showing none of them still running. A task with no dispatch and no
    named seat has dispatched nothing."""
    refs = task.get("dispatch")
    refs = [refs] if isinstance(refs, str) else [ref for ref in refs or [] if isinstance(ref, str)]
    seats = task_seats(task)
    if not refs and not seats:
        return []
    problems: list[str] = []
    if refs and (not getattr(args, "index", None) or not getattr(args, "live", None)):
        problems.append(f"dispatch {', '.join(refs)} needs --index and --live to show it closed and stopped")
    if seats and not getattr(args, "live", None):
        problems.append(f"seat {', '.join(sorted(seats))} needs --live to show it stopped, or "
                        "--handoff to the current task that continues it")
    if problems:
        return problems
    live = live_rows_of(args.live) or []
    if refs:
        rows = {row.get("item_id"): row for row in load_object(Path(args.index)).get("items") or []
                if isinstance(row, dict)}
        problems = [f"{ref} is {rows[ref].get('status')}" if ref in rows else f"{ref} is not in the index"
                    for ref in refs if ref not in rows or rows[ref].get("status") in ("in-flight", "unknown")]
        sessions = {rows[ref].get("session") for ref in refs if ref in rows} - set(seats)
        for row in live:
            if row.get("state") != "stopped" and row.get("session") in sessions:
                problems.append(f"{row.get('session')} is still live")
    return problems + open_seats(seats, live)


def handoff_seats(receiver: dict[str, Any], task: dict[str, Any], task_id: str,
                  args: argparse.Namespace) -> dict[str, Any]:
    """Move a retiring task's dispatch refs, sessions and assignments onto
    the continuing task, each assignment naming where it came from. Nothing
    is dropped; the receiver's own retirement later needs them closed."""
    refs = task.get("dispatch")
    refs = [refs] if isinstance(refs, str) else [ref for ref in refs or [] if isinstance(ref, str)]
    seats = task_seats(task)
    if refs:
        mine = receiver.get("dispatch")
        mine = [mine] if isinstance(mine, str) else list(mine or [])
        receiver["dispatch"] = mine + [ref for ref in refs if ref not in mine]
    rows = [row for row in task.get("assignments") or [] if isinstance(row, dict)]
    if rows:
        receiver["assignments"] = list(receiver.get("assignments") or []) + [
            {**row, "handed_from": task_id} for row in rows]
    if seats:
        # Every recorded holder and its evidence moves with the seat; a seat
        # known only by name stays a name.
        names = list(receiver.get("sessions") or [])
        moved = [{**row, "handed_from": task_id} for row in task.get("sessions") or []
                 if isinstance(row, dict)]
        if task.get("session") is not None:
            moved.append({"session": task.get("session"), "handed_from": task_id,
                          **({"holder_instance_id": task["holder_instance_id"]}
                             if task.get("holder_instance_id") else {})})
        bare = [name for name in task.get("sessions") or [] if isinstance(name, str)]
        receiver["sessions"] = names + moved + [name for name in bare if name not in names]
    if refs or seats:
        receiver["rev"] = int(receiver.get("rev") or 0) + 1
        receiver["updated_at"] = observed_at()
        receiver["writer"] = args.writer
    return {"seats": sorted(seats), "dispatch": refs}


def retire_record(args: argparse.Namespace, doc: dict[str, Any]) -> dict[str, Any]:
    state = doc["state"]
    kind, record_id = args.kind, args.id
    if kind not in RECORD_KINDS:
        raise StateRefusal("invalid-input", f"kind must be one of {', '.join(RECORD_KINDS)}")
    current = state.get(kind, {}).get(record_id)
    if current is None:
        raise StateRefusal("record-missing", f"{kind}/{record_id} is not current")
    if args.expect_rev != current.get("rev"):
        raise StateRefusal("conflict", f"{kind}/{record_id} is at rev {current.get('rev')}, not "
                           f"{args.expect_rev}", current=current)
    if not args.evidence:
        raise StateRefusal("evidence-required", "retirement names the evidence that ends the duty")
    verdict = current.get("verdict") if isinstance(current.get("verdict"), dict) else {}
    if kind == "tasks" and not (verdict.get("value") == "cancelled"
                                or (current.get("stage") == "done" and verdict.get("value") == "accepted")):
        raise StateRefusal("retire-unmet", "a task leaves the current set only when the Host accepted it "
                           "done or cancelled it", current=current)
    handoff = getattr(args, "handoff", None)
    handed: dict[str, Any] = {}
    if handoff and (kind != "tasks" or handoff == record_id or handoff not in state.get("tasks", {})):
        raise StateRefusal("invalid-input", "--handoff names another current task that continues "
                           "this task's seats and dispatch", current=current)
    if kind == "tasks" and handoff:
        # Design §6: a seat may end with this task or move, whole and with
        # its evidence, to a continuing duty; the receiver owns its stop.
        handed = handoff_seats(state["tasks"][handoff], current, record_id, args)
    elif kind == "tasks":
        open_refs = open_dispatch(current, args)
        if open_refs:
            raise StateRefusal("retire-unmet", "its dispatched work is not shown closed: "
                               + "; ".join(open_refs) + "; or --handoff it to a continuing task",
                               current=current)
    if kind == "decisions" and current.get("status") != "settled":
        raise StateRefusal("retire-unmet", "a pending decision stays until it is settled", current=current)
    if (kind in ("tasks", "decisions") and args.writer == "sideagent"
            and isinstance(current.get("transcribed"), dict)):
        raise StateRefusal("retire-unmet", "the Host has not yet seen this transcribed decision",
                           current=current)
    cite = None
    if kind == "tasks" and verdict.get("value") == "accepted":
        raw_cite = getattr(args, "cite", None)
        try:
            cite = json.loads(raw_cite) if isinstance(raw_cite, str) else raw_cite
        except ValueError as exc:
            raise StateRefusal("invalid-input", f"cite is not JSON: {exc}") from exc
        problem = RECORD.cite_problem(cite)
        if problem:
            raise StateRefusal(
                "cite-required",
                "a completed outcome that must survive names a retrievable path before it leaves: "
                f"{problem}",
                path="cite",
                allowed="{path: relative repository path, commit?: 7-40 lowercase hex, locator?: string}",
                recovery="pass --cite for a file in this repository, or a commit this repository can read. "
                         "Do not invent a commit. Holds, alerts, cancellations, and relays still retire "
                         "with --evidence.",
                current=current,
            )
        missing = cite_retrievable(repo_of_state_file(Path(args.file)), cite)
        if missing:
            raise StateRefusal(
                "cite-required",
                missing,
                path="cite",
                allowed="{path: relative repository path, commit?: retrievable commit, locator?: string}",
                recovery=missing,
                current=current,
            )
    stone = {"kind": kind, "id": record_id, "outcome": args.outcome or current.get("stage") or "resolved",
             "at": observed_at(),
             **({"cite": cite} if cite else {}),
             **({"handed_to": handoff, **handed} if handoff else {})}
    stamp_writer(doc, stone, args, caller_dispatcher())
    del state[kind][record_id]
    stones = list(state.get("retired") or []) + [stone]
    state["retired"] = stones[-TOMBSTONE_CAP:]
    return stone


def write_state(path: Path, doc: dict[str, Any], *, unchecked_live: bool = False) -> dict[str, int]:
    doc["revision"] = int(doc.get("revision") or 0) + 1
    doc["updated_at"] = observed_at()
    text, sizes = render_state(doc, path, unchecked_live=unchecked_live)
    atomic_write(path, text)
    return sizes


def state_mutation(args: argparse.Namespace, change) -> int:
    path = Path(args.file)
    try:
        with StateLock(path):
            doc, _ = read_state_file(path)
            doc = require_current(doc, path)
            before = doc.get("revision")
            caller = check_writer(args, doc["state"])
            if args.writer == "host":
                # Only a Host business write moves the Host revision; tool and
                # Sideagent writes never wake another maintenance node.
                doc["host_revision"] = int(doc.get("host_revision") or 0) + 1
                args._host_revision = doc["host_revision"]
            changed = change(doc, caller)
            sizes = write_state(path, doc, unchecked_live=_owner_stop(args))
            mirrored = mirror_dispositions(args, doc, path)
    except StateRefusal as refusal:
        code = STATE_EXIT_CONFLICT if refusal.payload["reason"] == "conflict" else 2
        return emit(refusal.payload, code)
    except (OSError, ValueError) as exc:
        return fail("invalid-input", str(exc))
    return emit({"result": "written", "revision": doc["revision"], "previous_revision": before,
                 **({"host_revision": doc["host_revision"]} if doc.get("host_revision") else {}),
                 "value": changed, **({"index_mirror": mirrored} if mirrored else {}), **sizes})


def mirror_dispositions(args: argparse.Namespace, doc: dict[str, Any], path: Path) -> dict[str, Any] | None:
    """Copy one task's Host-recorded per-assignment dispositions onto the
    existing index rows. A linked row the Host gave no disposition after a
    verdict reads `undecided`, never a misleading `pending`."""
    index_path = getattr(args, "index", None)
    if not index_path or getattr(args, "kind", None) != "tasks" or getattr(args, "command", "") != "state":
        return None
    task = doc["state"].get("tasks", {}).get(args.id)
    if not isinstance(task, dict):
        return None
    try:
        return mirror_task(args, task, path, index_path)
    except (OSError, ValueError) as exc:
        # The state write already landed; the index stays as it was and says so.
        return {"index": index_path, "error": str(exc), "changed": {}}


def mirror_task(args: argparse.Namespace, task: dict[str, Any], path: Path, index_path: str) -> dict[str, Any]:
    with IndexLock(Path(index_path)):
        index = load_object(Path(index_path))
        refs = task.get("dispatch")
        refs = {refs} if isinstance(refs, str) else {ref for ref in refs or [] if isinstance(ref, str)}
        dispositions = task.get("dispositions") if isinstance(task.get("dispositions"), dict) else {}
        verdict = (task.get("verdict") or {}).get("value") if isinstance(task.get("verdict"), dict) else None
        changed: dict[str, str] = {}
        for row in index.get("items") or []:
            if not isinstance(row, dict) or not (row.get("item_id") in refs or row.get("task_id") == args.id):
                continue
            value = dispositions.get(row.get("item_id"))
            if value is None and verdict is not None and row.get("acceptance") in (None, "pending"):
                value = "undecided"
                row["acceptance_note"] = (f"task verdict {verdict} recorded without a disposition "
                                          "for this item; the Host records one")
            if value is None or row.get("acceptance") == value:
                continue
            row["acceptance"] = value
            row["acceptance_source"] = {"state": str(path), "task_id": args.id, "task_rev": task.get("rev"),
                                        "host_revision": task.get("host_revision")}
            if value != "undecided":
                row.pop("acceptance_note", None)
            changed[row["item_id"]] = value
        if changed:
            atomic_write(Path(index_path), json.dumps(index, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    return {"index": index_path, "changed": changed}


def command_state_init(args: argparse.Namespace) -> int:
    path = Path(args.file)
    try:
        project = json_arg(args.project) if args.project else {}
        authorization = json_arg(args.authorization_json) if args.authorization_json else {}
        if not isinstance(project, dict) or not isinstance(authorization, dict):
            return fail("invalid-input", "project and authorization are JSON objects")
        blocked = RECORD.project_blockers(project) + RECORD.authorization_blockers(authorization)
        if blocked:
            first = blocked[0]
            return emit({"result": "refused", "reason": "invalid-input", **first}, 2)
        with StateLock(path):
            doc, _ = read_state_file(path)
            if doc is not None:
                return emit({"result": "refused", "reason": "state-exists",
                             "detail": "an existing file is migrated or updated, never replaced",
                             "schema": doc.get("schema")}, 2)
            if args.writer != "host":
                return emit({"result": "refused", "reason": "host-only",
                             "detail": "the Host creates the lifecycle state"}, 2)
            state = empty_state()
            state["project"] = project
            state["authorization"] = authorization
            note_section_source(state, args, "project")
            note_section_source(state, args, "authorization")
            doc = {"schema": STATE_SCHEMA, "revision": 0, "host_revision": 1, "state": state,
                   "created_from": args.source}
            for section in ("project", "authorization"):
                state["section_sources"][section]["host_revision"] = 1
            sizes = write_state(path, doc)
    except StateRefusal as refusal:
        return emit(refusal.payload, 2)
    except ValueError as exc:
        return fail("invalid-input", str(exc))
    return emit({"result": "written", "revision": doc["revision"], **sizes})


def command_state_update(args: argparse.Namespace) -> int:
    try:
        patch = json_arg(args.set)
    except (OSError, ValueError) as exc:
        return fail("invalid-input", str(exc))
    if bool(args.kind) == bool(args.section):
        return fail("invalid-input", "pass either --kind/--id or --section")
    if args.kind:
        if not isinstance(patch, dict):
            return fail("invalid-input", "a record update is a JSON merge patch object")
        return state_mutation(args, lambda doc, caller: apply_record_update(args, doc, patch, caller))
    return state_mutation(args, lambda doc, caller: apply_section_update(args, doc, patch, caller))


def command_state_retire(args: argparse.Namespace) -> int:
    return state_mutation(args, lambda doc, caller: retire_record(args, doc))


def _owner_stop(args: argparse.Namespace) -> bool:
    """An owner stop uses the current file bound so carrier-limit does not block it."""
    if getattr(args, "section", None) != "project":
        return False
    try:
        patch = json.loads(getattr(args, "set", "") or "null")
    except ValueError:
        return False
    return isinstance(patch, dict) and isinstance(patch.get("stop"), str) and bool(patch["stop"])


def cite_retrievable(repo: Path, cite: dict[str, Any]) -> str | None:
    """The path is a file, or git can read commit:path. This is not a gate for holds or cancels."""
    path = repo / str(cite.get("path") or "")
    exists = path.is_file()
    commit = cite.get("commit")
    if isinstance(commit, str) and commit:
        try:
            proc = subprocess.run(
                ["git", "-C", str(repo), "cat-file", "-e", f"{commit}:{cite['path']}"],
                capture_output=True, timeout=15, check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            proc = None
        if proc is not None and proc.returncode == 0:
            return None
        if proc is not None:
            return ("this repository cannot read that commit and path. "
                    "Omit commit when the path is a file, or pass a commit this repository can read. "
                    "Do not invent a commit.")
        if not exists:
            return "git did not run and the path is not a file in this repository"
    if exists:
        return None
    return "path is not a file in this repository. Put the original evidence at that relative path."


def host_changes(doc: dict[str, Any], after: int, through: int) -> dict[str, int]:
    """Each Host business change in (after, through], by its input id. A
    record the Host rewrote later shows only its latest change."""
    state = doc["state"]
    found: dict[str, int] = {}

    def take(ident: str, value: Any) -> None:
        if isinstance(value, int) and not isinstance(value, bool) and after < value <= through:
            found[ident] = value

    for kind in RECORD_KINDS:
        for record_id, record in (state.get(kind) or {}).items():
            if isinstance(record, dict):
                take(f"host:{kind}/{record_id}@{record.get('host_revision')}", record.get("host_revision"))
    for section, source in (state.get("section_sources") or {}).items():
        if isinstance(source, dict):
            take(f"host:section/{section}@{source.get('host_revision')}", source.get("host_revision"))
    for stone in state.get("retired") or []:
        if isinstance(stone, dict):
            take(f"host:retired/{stone.get('kind')}/{stone.get('id')}@{stone.get('host_revision')}",
                 stone.get("host_revision"))
    return found


def revision_of(ident: str) -> int | None:
    head, _, tail = ident.rpartition("@")
    return int(tail) if head.startswith("host:") and tail.isdigit() else None


def retirement_stones(state: dict[str, Any], kind: str, record_id: str) -> list[dict[str, Any]]:
    return [stone for stone in state.get("retired") or []
            if isinstance(stone, dict) and stone.get("kind") == kind and stone.get("id") == record_id]


def already_settled_input(state: dict[str, Any], ident: str) -> bool:
    """A Host input that already has a retirement stone. A later node may acknowledge it.

    A cancelled task with a live seat, and a keep_open task, stay open. They are not settled here.
    """
    if not ident.startswith("host:"):
        return False
    body = ident[len("host:"):].rpartition("@")[0]
    if body.startswith("retired/"):
        kind, _, record_id = body[len("retired/"):].partition("/")
        return bool(record_id) and bool(retirement_stones(state, kind, record_id))
    kind, _, record_id = body.partition("/")
    if not record_id or kind not in RECORD_KINDS:
        return False
    return bool(retirement_stones(state, kind, record_id))


def checkpoint_entry(state: dict[str, Any], entry: Any, holder: str) -> tuple[str | None, str | None]:
    """(input id, why it is not settled) for one checkpoint entry. Applied
    evidence must be a current record or tombstone this node wrote; a
    retained duty must be a current record with a responsible next reader."""
    if not isinstance(entry, dict) or not isinstance(entry.get("input"), str) or not entry["input"]:
        return None, "entry-unreadable"
    applied, retained = entry.get("applied"), entry.get("retained")
    if (applied is None) == (retained is None):
        return entry["input"], "entry-needs-applied-or-retained"
    if applied is not None:
        refs = [applied] if isinstance(applied, str) else applied
        if not isinstance(refs, list) or not refs:
            return entry["input"], "applied-empty"
        for ref in refs:
            if not isinstance(ref, str):
                return entry["input"], "applied-unreadable"
            if ref.startswith("retired:"):
                kind, _, record_id = ref[len("retired:"):].partition("/")
                stones = retirement_stones(state, kind, record_id)
                # An existing retirement is already settled. This node may
                # acknowledge it; only a missing stone is unsettled.
                if not stones:
                    return entry["input"], f"{ref} is not a retirement by this node"
                continue
            kind, _, record_id = ref.partition("/")
            record = (state.get(kind) or {}).get(record_id) if kind in RECORD_KINDS else None
            if not isinstance(record, dict) or record.get("writer_holder") != holder:
                return entry["input"], f"{ref} is not a current record this node wrote"
        return entry["input"], None
    kind, _, record_id = retained.partition("/") if isinstance(retained, str) else ("", "", "")
    if kind == "section":
        # A section is a Host-owned current fact the node reads; the Host
        # stays its responsible reader.
        if record_id not in (state.get("section_sources") or {}):
            return entry["input"], f"retained {retained} is not a current section"
        return entry["input"], None
    record = (state.get(kind) or {}).get(record_id) if kind in RECORD_KINDS else None
    if not isinstance(record, dict):
        return entry["input"], f"retained {retained} is not a current record"
    if all(record.get(key) in (None, "", [], {}) for key in ("next", "owner", "wait")):
        return entry["input"], f"retained {retained} names no next reader"
    return entry["input"], None


def apply_checkpoint(args: argparse.Namespace, doc: dict[str, Any],
                     caller: dict[str, str] | None) -> dict[str, Any]:
    state = doc["state"]
    if args.writer != "sideagent" or not caller or not caller.get("holder_instance_id"):
        raise StateRefusal("node-identity-required", "a checkpoint is written by the bound Sideagent "
                           "node from inside its own session, so its holder is known")
    holder = caller["holder_instance_id"]
    try:
        entries = json_arg(args.entries)
        events = json_arg(args.events) if args.events else []
    except (OSError, ValueError) as exc:
        raise StateRefusal("invalid-input", str(exc))
    if not isinstance(entries, list) or not isinstance(events, list) or not all(
            isinstance(event, str) for event in events):
        raise StateRefusal("invalid-input", "--entries is a JSON array; --events a JSON array of ids")
    maintenance = state.setdefault("maintenance", {})
    handled = int(maintenance.get("handled_host_revision") or 0)
    current = int(doc.get("host_revision") or 0)
    through = args.through_host_revision if args.through_host_revision is not None else handled
    if through < handled or through > current:
        raise StateRefusal("invalid-input", f"--through-host-revision must be within {handled}..{current}")
    selected = host_changes(doc, handled, through)
    # A batch input the Host rewrote after this batch was selected shows
    # only its later change, which is past `through` and so in the next
    # batch: superseded, not lost.
    later = {ident.rpartition("@")[0] for ident in host_changes(doc, through, current)}
    settled: list[str] = []
    superseded: list[str] = []
    returned: dict[str, str] = {}
    seen: set[str] = set()
    for entry in entries:
        ident, problem = checkpoint_entry(state, entry, holder)
        if ident is None:
            raise StateRefusal("invalid-input", "each entry names its `input`")
        seen.add(ident)
        revision = revision_of(ident)
        if problem and not already_settled_input(state, ident):
            returned[ident] = problem
        elif ident in selected or ident in events or already_settled_input(state, ident):
            settled.append(ident)
        elif (revision is not None and handled < revision <= through
              and ident.rpartition("@")[0] in later):
            superseded.append(ident)
        else:
            returned[ident] = "not-in-batch"
    for ident in [*selected, *events]:
        if ident not in seen:
            if already_settled_input(state, ident):
                settled.append(ident)
            else:
                returned[ident] = "unaccounted"
    # The acknowledgment never passes an unaccounted Host change: neither
    # one of this batch nor one still in the Host's open returned alert.
    still_returned = ((state.get("alerts") or {}).get("maintenance-returned") or {}).get("inputs") or {}
    open_revisions = [revision for ident, revision in selected.items() if ident not in settled]
    open_revisions += [revision_of(ident) for ident in still_returned if revision_of(ident) is not None]
    new_acked = min([through] + [revision - 1 for revision in open_revisions])
    verified = not returned
    record = {"batch": args.batch, "node": {"session": caller.get("session"), "holder_instance_id": holder},
              "at": observed_at(), "source": args.source, "verified": verified,
              "host_revision": {"from": handled, "through": through, "current": current},
              "settled": sorted(settled), "returned_to_host": dict(sorted(returned.items())),
              **({"superseded": sorted(superseded)} if superseded else {})}
    maintenance["last_checkpoint"] = record
    if verified:
        maintenance["last_verified"] = {key: record[key] for key in ("batch", "node", "at")}
    maintenance["acked_host_revision"] = new_acked
    maintenance["handled_host_revision"] = through
    alerts = state.setdefault("alerts", {})
    alert_id = "maintenance-returned"
    prior = alerts.get(alert_id) if isinstance(alerts.get(alert_id), dict) else {}
    inputs = dict(prior.get("inputs") or {})
    for ident in settled:
        inputs.pop(ident, None)
    if returned:
        # Handed to the Host once, as one durable alert: never re-sent to
        # another node, never counted as applied. Already-settled inputs leave.
        inputs.update({ident: {"why": why, "batch": args.batch} for ident, why in returned.items()})
        alerts[alert_id] = {**prior, "level": "warn", "owner": "host",
                            "summary": f"{len(inputs)} maintenance input(s) not applied by a node; "
                                       "judge or re-dispatch them from their sources",
                            "inputs": inputs, "evidence": [f"checkpoint:{args.batch}"],
                            "rev": int(prior.get("rev") or 0) + 1,
                            "created_at": prior.get("created_at") or observed_at(),
                            "updated_at": observed_at(), "source": args.source,
                            "writer": writer_trace(args, caller), "writer_holder": holder}
    elif alert_id in alerts and not inputs:
        alerts.pop(alert_id, None)
    elif alert_id in alerts and inputs != (prior.get("inputs") or {}):
        alerts[alert_id] = {**prior, "inputs": inputs,
                            "summary": f"{len(inputs)} maintenance input(s) not applied by a node; "
                                       "judge or re-dispatch them from their sources",
                            "rev": int(prior.get("rev") or 0) + 1, "updated_at": observed_at()}
    return record


def command_state_checkpoint(args: argparse.Namespace) -> int:
    return state_mutation(args, lambda doc, caller: apply_checkpoint(args, doc, caller))


def command_state_view(args: argparse.Namespace) -> int:
    path = Path(args.file)
    try:
        doc = require_current(read_state_file(path)[0], path)
    except StateRefusal as refusal:
        return emit(refusal.payload, 2)
    except ValueError as exc:
        return fail("invalid-input", str(exc))
    if args.role == "host":
        return emit(host_view(doc, path))
    if args.role == "delegator":
        repo = Path(args.repo).resolve() if args.repo else repo_of_state_file(path)
        return emit(delegator_view(doc, path, repo))
    maintenance = doc["state"].get("maintenance") or {}
    handled = int(maintenance.get("handled_host_revision") or 0)
    current = int(doc.get("host_revision") or 0)
    return emit({"view": "sideagent", "revision": doc.get("revision"), "as_of": doc.get("updated_at"),
                 "host_revision": current,
                 "pending_host_changes": sorted(host_changes(doc, handled, current)),
                 "carrier": doc.get("carrier"), "state": RECORD.projected_state(doc["state"]),
                 "unknown": RECORD.unknown_paths(doc["state"])})


def live_rows_of(path: str | None) -> list[dict[str, Any]] | None:
    if not path:
        return None
    rows = load_object(Path(path)).get("rows")
    if not isinstance(rows, list):
        raise ValueError("live rows must be an array")
    return [row for row in rows if isinstance(row, dict)]


def live_host_rows(rows: list[dict[str, Any]], repo: Path) -> list[dict[str, Any]]:
    return [row for row in rows if row.get("state") != "stopped"
            and (row.get("host_class") is True or row.get("session_role") == "host")
            and same_repo(row.get("repo"), str(repo))]


def carrier_from_live(rows: list[dict[str, Any]] | None, repo: Path) -> tuple[dict[str, Any] | None, str]:
    if rows is None:
        return None, "no live rows supplied"
    hosts = live_host_rows(rows, repo)
    if len(hosts) != 1:
        return None, f"{len(hosts)} live Host rows in this repo"
    features = hosts[0].get("holder_features")
    if not isinstance(features, list) or STATE_CAPABILITY not in features:
        return None, f"Host holder {hosts[0].get('holder_instance_id')} does not advertise {STATE_CAPABILITY}"
    return {"capability": STATE_CAPABILITY, "holder_instance_id": hosts[0].get("holder_instance_id"),
            "platform": hosts[0].get("platform"), "session": hosts[0].get("session"),
            "observed_at": observed_at()}, "advertised"


def state_problems(doc: dict[str, Any], path: Path, index: dict[str, Any] | None,
                   rows: list[dict[str, Any]] | None, repo: Path) -> list[dict[str, Any]]:
    state = doc["state"]
    problems: list[dict[str, Any]] = []

    def note(code: str, level: str, detail: str, kind: str | None = None, ident: str | None = None) -> None:
        problems.append({"code": code, "level": level, "detail": detail,
                         **({"kind": kind} if kind else {}), **({"id": ident} if ident else {})})

    for kind in RECORD_KINDS:
        for ident, record in (state.get(kind) or {}).items():
            if not isinstance(record, dict):
                note("record-unreadable", "warn", "record is not an object", kind, ident)
                continue
            problem = validate_record(kind, record)
            if problem:
                note("record-invalid", "warn", problem, kind, ident)
            if not record.get("source"):
                note("source-missing", "watch", "no source names where this came from", kind, ident)
    for ident, task in (state.get("tasks") or {}).items():
        if not isinstance(task, dict):
            continue
        if task.get("stage") == "doing" and not task.get("dispatch") and not task.get("wait"):
            note("doing-untraced", "warn", "doing with neither a dispatch reference nor a wait reason",
                 "tasks", ident)
        if task.get("stage") == "done":
            note("done-not-retired", "watch", "done; retire it with its evidence once close-out is "
                 "verified", "tasks", ident)
            seats = task_seats(task)
            if seats and rows is not None:
                for detail in open_seats(seats, rows):
                    note("done-seat-open", "warn", f"done while {detail}", "tasks", ident)
        if isinstance(task.get("transcribed"), dict):
            note("transcription-unechoed", "watch", "a Sideagent-recorded Host decision waits for the "
                 "Host's next view", "tasks", ident)
    retired = {(stone.get("kind"), stone.get("id")) for stone in state.get("retired") or []}
    if index is not None:
        rows_by_id = {row.get("item_id"): row for row in index.get("items") or [] if isinstance(row, dict)}
        for item_id, row in rows_by_id.items():
            if row.get("status") not in ("in-flight", "returned", "unknown"):
                continue
            task_id = row.get("task_id")
            if not task_id:
                note("dispatch-unassociated", "warn", f"index item {item_id} names no task", "index", item_id)
            elif task_id not in (state.get("tasks") or {}) and ("tasks", task_id) not in retired:
                note("dispatch-task-missing", "warn", f"index item {item_id} names unknown task {task_id}",
                     "index", item_id)
        for ident, task in (state.get("tasks") or {}).items():
            refs = task.get("dispatch") if isinstance(task, dict) else None
            for ref in [refs] if isinstance(refs, str) else refs or []:
                if isinstance(ref, str) and ref not in rows_by_id and "/" not in ref:
                    note("dispatch-ref-missing", "watch", f"dispatch {ref} is not in the supplied index",
                         "tasks", ident)
                elif (isinstance(task, dict) and task.get("stage") == "done" and isinstance(ref, str)
                      and (rows_by_id.get(ref) or {}).get("status") in ("in-flight", "unknown")):
                    note("done-dispatch-open", "warn", f"done while dispatch {ref} is still "
                         f"{rows_by_id[ref].get('status')}", "tasks", ident)
    binding = state.get("sideagent")
    if rows is not None:
        live = [row for row in rows if row.get("state") != "stopped" and same_repo(row.get("repo"), str(repo))]
        if isinstance(binding, dict) and binding.get("state") == "active" and not node_binding(binding):
            matched = [row for row in live if binding_row(binding, row)]
            if not matched:
                note("sideagent-not-live", "warn", f"bound Sideagent {binding.get('session')} has no live "
                     "row with its holder", "sideagent", binding.get("session"))
        for row in live:
            if row.get("session_role") in SIDEAGENT_ROLES and not binding_row(binding, row):
                note("sideagent-helper", "watch", f"{row.get('session')} has the Sideagent role but is not "
                     "the bound one; it is counted as a worker", "live", row.get("session"))
        carrier = doc.get("carrier") if isinstance(doc.get("carrier"), dict) else None
        hosts = live_host_rows(rows, repo)
        if carrier and hosts and all(row.get("holder_instance_id") != carrier.get("holder_instance_id")
                                     for row in hosts):
            proven, why = carrier_from_live(rows, repo)
            if proven is None:
                note("carrier-unproven", "severe" if len(json.dumps(doc)) > LEGACY_READER_MAX_BYTES
                     else "warn", f"recorded carrier holder is not the live Host: {why}")
    try:
        _, sizes = render_state(json.loads(json.dumps(doc)), path)
    except StateRefusal as refusal:
        note(refusal.payload["reason"], "severe", refusal.payload["detail"])
    else:
        if sizes["body_bytes"] > HOST_VIEW_MAX_BYTES * 3 // 4:
            note("host-view-near-limit", "watch", f"Host view is {sizes['body_bytes']} bytes")
    return problems


def command_state_check(args: argparse.Namespace) -> int:
    path = Path(args.file)
    try:
        doc = require_current(read_state_file(path)[0], path)
        index = load_object(Path(args.index)) if args.index else None
        rows = live_rows_of(args.live)
    except StateRefusal as refusal:
        return emit(refusal.payload, 2)
    except ValueError as exc:
        return fail("invalid-input", str(exc))
    repo = Path(args.repo).resolve() if args.repo else repo_of_state_file(path)
    problems = state_problems(doc, path, index, rows, repo)
    return emit({"result": "checked", "revision": doc.get("revision"), "ok": not problems,
                 "problems": problems, "read_only": True,
                 "unchecked": [name for name, value in (("index", index), ("live", rows)) if value is None]})


def command_state_timer(args: argparse.Namespace) -> int:
    """Compare a native timer's body with the installed template, exactly."""
    if args.body_file:
        try:
            actual = Path(args.body_file).read_text(encoding="utf-8")
        except OSError as exc:
            return fail("invalid-input", str(exc))
    elif not args.body:
        return emit({
            "result": "unavailable",
            "detail": "no native timer body was read. This is not a mismatch. It does not block an urgent stop.",
        })
    else:
        actual = args.body
    expected = args.entry + "\n" + TIMER_LOCATOR.format(repo=str(Path(args.repo).resolve()), target=args.target)
    match = actual.rstrip("\n") == expected
    return emit({"result": "match" if match else "mismatch", "expected": expected,
                 **({} if match else {"actual": actual})}, 0 if match else 1)


# The v1 skeleton's fields plus those the v1 Host recorded in practice; any
# other nested key is kept in place and listed in `unverified` by locator.
V1_ACTIVE_FIELDS = ("ref", "session", "platform", "preset", "holder", "holder_instance_id",
                    "dispatch_event_cursor", "prompt_fingerprint", "candidate", "next", "evidence",
                    "wait", "resume_when")
V1_PENDING_FIELDS = ("duty", "scope", "owner", "evidence", "boundary", "next", "wait",
                     "resume_when", "holder", "platform", "session", "stage")


def unmapped_fields(state: dict[str, Any], locator: str, entry: dict[str, Any],
                    known: tuple[str, ...]) -> None:
    extra = sorted(key for key in entry if key not in known)
    RECORD.note_unmapped(state, locator, extra)


def legacy_tasks(body: dict[str, Any], state: dict[str, Any]) -> None:
    """v1 `active` rows and `pending` duties as tasks. Every v1 row is kept
    whole (one assignment per active row, every pending field on its task);
    a stage is taken only from the v1 list a row came from or an explicit
    `stage`, never guessed from free text."""
    tasks: dict[str, Any] = {}
    for number, entry in enumerate(body.get("active") or []):
        locator = f"active[{number}]"
        if not isinstance(entry, dict):
            state["unverified"][f"active-{number}"] = {"summary": "unreadable legacy active entry",
                                                       "locator": locator}
            continue
        ref = entry.get("ref")
        ident = ref if isinstance(ref, str) and re.fullmatch(r"[A-Za-z0-9#][A-Za-z0-9_.:#/-]{0,79}", ref) \
            else f"active-{number}"
        # v1 `active` lists work in flight or ready to act on.
        task = tasks.setdefault(ident, {"stage": "doing", "goal": ref or f"legacy active entry {number}",
                                        "sessions": [], "assignments": [], "source": "migrated:active"})
        task["assignments"].append(
            {key: entry[key] for key in V1_ACTIVE_FIELDS if key in entry} | {"locator": locator})
        if entry.get("session") is not None and entry["session"] not in task["sessions"]:
            task["sessions"].append(entry["session"])
        unmapped_fields(state, locator, entry, V1_ACTIVE_FIELDS)
    for task in tasks.values():
        rows = task["assignments"]
        for key in ("next", "wait", "resume_when", "candidate", "evidence"):
            values = [row[key] for row in rows if row.get(key) is not None]
            if values:
                task[key] = values[0] if len(rows) == 1 else values
    for number, duty in enumerate(body.get("pending") or []):
        ident = f"duty-{number + 1}"
        locator = f"pending[{number}]"
        if not isinstance(duty, dict):
            state["unverified"][ident] = {"summary": "unreadable legacy pending entry",
                                          "locator": locator}
            continue
        stage = duty.get("stage") if duty.get("stage") in TASK_STAGES else None
        if stage is None:
            stage = "todo"
            state["unverified"][f"{ident}-stage"] = {
                "summary": f"legacy pending duty {ident} states no stage; it is kept open as todo, "
                           "the Host sets its stage", "locator": locator}
        # A v1 key with no v1 meaning stays inert under `legacy`: one named
        # like a v2 field (`verdict`, `dispatch`, ...) must not take effect.
        tasks[ident] = {**{key: value for key, value in duty.items()
                           if key in V1_PENDING_FIELDS and key != "stage"},
                        "stage": stage, "goal": duty.get("duty") or "legacy pending duty",
                        "source": f"migrated:{locator}"}
        unmapped_fields(state, locator, duty, V1_PENDING_FIELDS)
    for ident, task in tasks.items():
        if isinstance(task.get("evidence"), dict):
            task["evidence"] = [json.dumps(task["evidence"], ensure_ascii=False, sort_keys=True)]
        elif isinstance(task.get("evidence"), list):
            task["evidence"] = [item if isinstance(item, str) else json.dumps(item, ensure_ascii=False,
                                                                              sort_keys=True)
                                for item in task["evidence"]]
        task["rev"] = 1
        task["created_at"] = task["updated_at"] = observed_at()
        task["writer"] = "migration"
        state["tasks"][ident] = task


def migrate_document(doc: dict[str, Any], raw: bytes, path: Path, index: dict[str, Any] | None,
                     rows: list[dict[str, Any]] | None, repo: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    body_text = doc.get("body")
    if not isinstance(body_text, str):
        raise StateRefusal("legacy-unreadable", 'legacy file has no string "body"; it is left unchanged')
    try:
        body = json.loads(body_text)
    except ValueError as exc:
        raise StateRefusal("legacy-unreadable", f"legacy body is not JSON ({exc}); left unchanged")
    if not isinstance(body, dict):
        raise StateRefusal("legacy-unreadable", "legacy body is not one object; left unchanged")
    state = empty_state()
    blockers: list[dict[str, str]] = []
    dropped: list[str] = []
    project = body.get("project") if isinstance(body.get("project"), dict) else {}
    state["project"] = project
    blockers.extend(RECORD.project_blockers(project))
    authorization = body.get("authorization")
    if isinstance(authorization, dict):
        state["authorization"] = authorization
        blockers.extend(RECORD.authorization_blockers(authorization))
    elif authorization is not None:
        blockers.append(RECORD.refusal(
            "authorization", "object of grants, pauses, and caps",
            "rehome authorization; the file was not written"))
    kept, recovery_blockers, recovery_dropped = RECORD.recovery_from_v1(body.get("recovery"))
    blockers.extend(recovery_blockers)
    dropped.extend(recovery_dropped)
    state["recovery"].update(kept)
    if recovery_dropped:
        RECORD.note_unmapped(state, "recovery", [key.removeprefix("recovery.") for key in recovery_dropped])
    if isinstance(body.get("host"), dict):
        dropped.append("host")
        RECORD.note_unmapped(state, "host", sorted(body["host"]))
    legacy_tasks(body, state)
    known = {"project", "authorization", "active", "pending", "recovery", "host", "sideagent"}
    for key in sorted(set(body) - known):
        dropped.append(key)
        state["unverified"][f"legacy-{key}"] = {
            "summary": f"unmapped body field {key}",
            "locator": key}
    if isinstance(state["project"].get("rules"), (list, str, dict)):
        requirements = requirement_lines(repo)
        if requirements.get("missing"):
            state["unverified"]["rules-source"] = {
                "summary": "project.rules is kept as adopted; AGENTS.md holds no user requirements "
                           "region to name as its source", "source": requirements["source"]}
    sessions: dict[str, str] = {}
    for ident, task in state["tasks"].items():
        for session in task.get("sessions") or []:
            if isinstance(session, str):
                sessions[session] = ident
            elif isinstance(session, dict) and isinstance(session.get("session"), str):
                sessions[session["session"]] = ident
    if index is not None:
        for row in index.get("items") or []:
            if not isinstance(row, dict) or row.get("status") not in ("in-flight", "returned", "unknown"):
                continue
            owner = row.get("task_id") if row.get("task_id") in state["tasks"] else sessions.get(row.get("session"))
            if owner:
                refs = state["tasks"][owner].setdefault("dispatch", [])
                if row.get("item_id") not in refs:
                    refs.append(row.get("item_id"))
            else:
                state["unverified"][f"index-{row.get('item_id')}"] = {
                    "summary": f"index item {row.get('item_id')} ({row.get('status')}) matches no "
                               "current task; associate it or retire it with evidence",
                    "session": row.get("session")}
    # A role label on a live row never makes it the maintenance Sideagent. Only
    # the v1 file's own authorized binding, proven by a live row with its exact
    # holder, carries over; anything else stays a candidate for the Host.
    v1_side = body.get("sideagent") if isinstance(body.get("sideagent"), dict) else None
    sideagents = [row for row in rows or [] if row.get("state") != "stopped"
                  and row.get("session_role") in SIDEAGENT_ROLES and same_repo(row.get("repo"), str(repo))]
    proven = [row for row in sideagents if v1_side and v1_side.get("authorization_source")
              and row.get("session") == v1_side.get("session")
              and row.get("holder_instance_id") == v1_side.get("holder_instance_id")]
    if len(proven) == 1:
        row = proven[0]
        state["sideagent"] = {"platform": row.get("platform"), "session": row.get("session"),
                              "holder_instance_id": row.get("holder_instance_id"),
                              "preset": v1_side.get("preset"),
                              "authorization_source": v1_side.get("authorization_source"),
                              "state": "active", "source": "migrated: v1 binding proven by its live holder",
                              "since": observed_at()}
        RECORD.note_unmapped(state, "sideagent", sorted(
            key for key in v1_side
            if key not in ("platform", "session", "holder_instance_id", "preset",
                           "authorization_source", "state")))
    elif v1_side or sideagents:
        state["unverified"]["sideagent-candidate"] = {
            "summary": "no authorized v1 binding is proven by a live holder; the Host binds the "
                       "maintenance Sideagent (a live Sideagent-role row alone is only a candidate)",
            **({"v1": RECORD.identity_only(v1_side)} if RECORD.identity_only(v1_side) else {}),
            "live": [{key: row.get(key) for key in ("platform", "session", "holder_instance_id")}
                     for row in sideagents],
            **({} if rows is not None else {"unchecked": "no live rows supplied"})}
    new_doc: dict[str, Any] | None = None
    carrier, why = carrier_from_live(rows, repo)
    if not blockers:
        new_doc = {"schema": STATE_SCHEMA, "revision": 0, "state": state}
        if carrier:
            new_doc["carrier"] = carrier
    report = {
        "tasks": sorted(state["tasks"]),
        "unverified": sorted(state["unverified"]),
        "sideagent": state["sideagent"],
        "authorization_kept": isinstance(authorization, dict),
        "dropped": dropped,
        "blockers": blockers,
        "overwrite_detection": RECORD.OVERWRITE_DETECTION,
        "carrier": carrier or {"capability": None, "why": why,
                               "file_limit": LEGACY_READER_MAX_BYTES},
    }
    return new_doc, report


def command_state_migrate(args: argparse.Namespace) -> int:
    path = Path(args.file)
    repo = Path(args.repo).resolve() if args.repo else repo_of_state_file(path)
    try:
        index = load_object(Path(args.index)) if args.index else None
        rows = live_rows_of(args.live)
        with StateLock(path):
            doc, raw = read_state_file(path)
            if doc is None:
                return emit({"result": "refused", "reason": "state-missing",
                             "detail": f"{path} does not exist; nothing to migrate"}, 2)
            backups = RECORD.assess_backups(path.parent, raw.decode("utf-8", errors="replace"))
            if doc.get("schema") == STATE_SCHEMA:
                blockers, cleaned, changed, removed = RECORD.cleanup_current(doc["state"])
                report: dict[str, Any] = {
                    "result": "current", "revision": doc.get("revision"),
                    "overwrite_detection": RECORD.OVERWRITE_DETECTION, "backups": backups,
                    "removed": removed,
                }
                if blockers:
                    return emit({"result": "blocked", "writes": False, "blockers": blockers,
                                 "overwrite_detection": RECORD.OVERWRITE_DETECTION,
                                 "backups": backups,
                                 "detail": "unresolved critical mapping; the file was not written"}, 2)
                carrier, why = carrier_from_live(rows, repo)
                if not args.write:
                    report["carrier"] = doc.get("carrier") or {"capability": None, "why": why}
                    if changed:
                        return emit({"result": "planned", "writes": False, "cleanup": True,
                                     "report": report})
                    return emit(report)
                if changed:
                    doc["state"] = cleaned
                if carrier and doc.get("carrier", {}).get("holder_instance_id") != carrier["holder_instance_id"]:
                    doc["carrier"] = carrier
                    report["result"] = "carrier-recorded"
                if changed:
                    report["result"] = "migrated"
                    report["cleanup"] = True
                if changed or report["result"] == "carrier-recorded":
                    report.update(write_state(path, doc, unchecked_live=rows is None))
                report["carrier"] = doc.get("carrier") or {"capability": None, "why": why}
                return emit(report)
            if doc.get("schema") not in (None, LEGACY_STATE_SCHEMA):
                return emit({"result": "refused", "reason": "schema-unsupported",
                             "detail": f"{path} declares schema {doc.get('schema')!r}, which this "
                                       "Runner does not know; it is not read as v1 and is left "
                                       "unchanged (update the Runner)"}, 2)
            new_doc, report = migrate_document(doc, raw, path, index, rows, repo)
            report["backups"] = backups
            unchecked = [name for name, value in (("index", index), ("live", rows)) if value is None]
            if new_doc is None:
                return emit({"result": "blocked", "writes": False, "unchecked": unchecked,
                             "report": report,
                             "detail": "unresolved critical mapping; the file was not written"}, 2)
            preview = json.loads(json.dumps(new_doc))
            preview["revision"] = 1
            _text, sizes = render_state(preview, path, unchecked_live=rows is None)
            report.update(sizes)
            if not args.write:
                return emit({"result": "planned", "writes": False, "unchecked": unchecked,
                             "report": report, "state": new_doc["state"]})
            sizes = write_state(path, new_doc, unchecked_live=rows is None)
    except StateRefusal as refusal:
        return emit(refusal.payload, 2)
    except (OSError, ValueError) as exc:
        return fail("invalid-input", str(exc))
    return emit({"result": "migrated", "revision": new_doc["revision"], "unchecked": unchecked,
                 "report": report, **sizes})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="kaola-dispatch.py")
    commands = parser.add_subparsers(dest="command", required=True)

    project = commands.add_parser("project")
    project.add_argument("--authorization", required=True)
    project.add_argument("--availability")
    project.add_argument("--platforms")
    project.add_argument("--seats", action="store_true", help="read occupancy against supplied grants")
    project.add_argument("--repo")
    project.add_argument("--live")
    project.add_argument("--index")
    project.add_argument("--skills-root")
    project.set_defaults(func=command_project)

    execute = commands.add_parser("execute")
    execute.add_argument("--plan", required=True)
    execute.add_argument("--authorization", required=True)
    execute.add_argument("--availability")
    execute.add_argument("--platforms")
    execute.add_argument("--skills-root")
    execute.add_argument("--prior-index")
    execute.add_argument("--index")
    execute.add_argument("--live")
    execute.add_argument("--dry-run", action="store_true")
    execute.add_argument("--state", help="lifecycle state: preset holds and task links")
    execute.set_defaults(func=command_execute)

    collect = commands.add_parser("collect")
    collect.add_argument("--index", required=True)
    collect.add_argument("--skills-root", required=True)
    collect.add_argument("--item", help="read one exact turn without rewriting the index")
    collect.set_defaults(func=command_collect)

    snapshot = commands.add_parser("snapshot")
    snapshot.add_argument("--state", required=True)
    snapshot.add_argument("--out", required=True)
    snapshot.set_defaults(func=command_snapshot)

    state = commands.add_parser("state", help="lifecycle state in .kaola/heartbeat-prompt.json")
    actions = state.add_subparsers(dest="action", required=True)

    def writer_args(sub: argparse.ArgumentParser) -> None:
        sub.add_argument("--file", required=True)
        sub.add_argument("--writer", required=True, help="host or sideagent; any other role is refused")
        sub.add_argument("--source", required=True, help="the event, receipt or Host turn behind this change")

    init = actions.add_parser("init")
    writer_args(init)
    init.add_argument("--project")
    init.add_argument("--authorization", dest="authorization_json")
    init.set_defaults(func=command_state_init)

    update = actions.add_parser("update")
    writer_args(update)
    update.add_argument("--kind", choices=RECORD_KINDS)
    update.add_argument("--id")
    update.add_argument("--section", choices=SECTIONS)
    update.add_argument("--expect-rev", type=int, help="record revision this change was based on")
    update.add_argument("--expect-revision", type=int, help="file revision, for a section change")
    update.add_argument("--set", required=True, help="JSON merge patch, or @path")
    update.add_argument("--host-turn", help="the Host turn a Sideagent transcribes a decision from")
    update.add_argument("--coalesce", action="store_true", help="repeat of an existing alert")
    update.set_defaults(func=command_state_update)

    retire = actions.add_parser("retire")
    writer_args(retire)
    retire.add_argument("--kind", required=True, choices=RECORD_KINDS)
    retire.add_argument("--id", required=True)
    retire.add_argument("--expect-rev", type=int, required=True)
    retire.add_argument("--evidence", required=True)
    retire.add_argument("--cite", help="JSON {commit, path} for a completed outcome that must survive")
    retire.add_argument("--outcome")
    retire.add_argument("--index", help="dispatch index showing the task's items closed")
    retire.add_argument("--live", help="Runner rows showing its sessions stopped")
    retire.add_argument("--handoff", help="current task that takes over its seats and dispatch")
    retire.set_defaults(func=command_state_retire)

    update.add_argument("--index", help="dispatch index to mirror this task's dispositions onto")

    checkpoint = actions.add_parser("checkpoint", help="a maintenance node's input accounting")
    writer_args(checkpoint)
    checkpoint.add_argument("--batch", required=True, help="the batch id the carrier sent")
    checkpoint.add_argument("--events", help="JSON array of the batch's worker event ids, or @path")
    checkpoint.add_argument("--through-host-revision", type=int,
                            help="the Host revision this batch selected; later changes stay pending")
    checkpoint.add_argument("--entries", required=True,
                            help='JSON array of {"input": ID, "applied": [REF...]} or '
                                 '{"input": ID, "retained": "kind/id"}, or @path')
    checkpoint.set_defaults(func=command_state_checkpoint)

    view = actions.add_parser("view")
    view.add_argument("--file", required=True)
    view.add_argument("--role", required=True, choices=("host", "sideagent", "delegator"))
    view.add_argument("--repo")
    view.set_defaults(func=command_state_view)

    check = actions.add_parser("check")
    check.add_argument("--file", required=True)
    check.add_argument("--index")
    check.add_argument("--live")
    check.add_argument("--repo")
    check.set_defaults(func=command_state_check)

    timer = actions.add_parser("timer")
    timer.add_argument("--repo", required=True)
    timer.add_argument("--target", required=True)
    timer.add_argument("--entry", required=True, help="the outer platform's Skill entry line")
    timer.add_argument("--body")
    timer.add_argument("--body-file")
    timer.set_defaults(func=command_state_timer)

    migrate = actions.add_parser("migrate")
    migrate.add_argument("--file", required=True)
    migrate.add_argument("--repo")
    migrate.add_argument("--index")
    migrate.add_argument("--live")
    migrate.add_argument("--write", action="store_true", help="apply; default is a read-only plan")
    migrate.set_defaults(func=command_state_migrate)

    backups = actions.add_parser("backups", help="list hash-named copies; never deletes them")
    backups.add_argument("--file", required=True)
    backups.set_defaults(func=command_state_backups)

    delegator = commands.add_parser("delegator", help="closed current state in .kaola/delegator-heartbeat.json")
    delegator_actions = delegator.add_subparsers(dest="action", required=True)
    for name, func in (
        ("view", command_delegator_view),
        ("migrate", command_delegator_migrate),
        ("update", command_delegator_update),
    ):
        sub = delegator_actions.add_parser(name)
        sub.add_argument("--file", required=True)
        if name == "migrate":
            sub.add_argument("--write", action="store_true")
        if name == "update":
            sub.add_argument("--writer", required=True)
            sub.add_argument("--source", required=True)
            sub.add_argument("--expect-revision", type=int, required=True)
            sub.add_argument("--set", required=True)
        sub.set_defaults(func=func)
    return parser


def command_state_backups(args: argparse.Namespace) -> int:
    path = Path(args.file)
    try:
        text = path.read_text(encoding="utf-8") if path.exists() else ""
    except OSError as exc:
        return fail("invalid-input", str(exc))
    return emit({"result": "assessed", **RECORD.assess_backups(path.parent, text)})


def _delegator_read(path: Path) -> dict[str, Any]:
    doc = load_object(path) if path.exists() else None
    if not isinstance(doc, dict):
        raise ValueError(f"{path} is missing or not an object")
    return doc


def command_delegator_view(args: argparse.Namespace) -> int:
    try:
        doc = _delegator_read(Path(args.file))
    except (OSError, ValueError) as exc:
        return fail("invalid-input", str(exc))
    return emit(RECORD.delegator_file_view(doc))


def command_delegator_migrate(args: argparse.Namespace) -> int:
    path = Path(args.file)
    try:
        with StateLock(path):
            doc = _delegator_read(path)
            migrated, blockers, dropped = RECORD.delegator_migrated(doc)
            if blockers or migrated is None:
                return emit({"result": "blocked", "writes": False, "blockers": blockers,
                             "dropped": dropped,
                             "detail": "unresolved critical mapping; the file was not written"}, 2)
            if not args.write:
                return emit({"result": "planned", "writes": False, "dropped": dropped,
                             "state": migrated})
            text = json.dumps(migrated, ensure_ascii=False, sort_keys=True, indent=1) + "\n"
            atomic_write(path, text)
    except (OSError, ValueError) as exc:
        return fail("invalid-input", str(exc))
    return emit({"result": "migrated", "writes": True, "dropped": dropped, "revision": migrated["revision"]})


def command_delegator_update(args: argparse.Namespace) -> int:
    if args.writer != "delegator":
        return emit({"result": "refused", "reason": "writer-refused",
                     "detail": "the Delegator writes its own file"}, 2)
    path = Path(args.file)
    try:
        patch = json_arg(args.set)
        if not isinstance(patch, dict):
            return fail("invalid-input", "a delegator update is a JSON object")
        for key, value in patch.items():
            if value is None:
                continue
            if key not in RECORD.DELEGATOR_TOP_KEYS - {"schema", "revision", "updated_at"}:
                refused = RECORD.refusal(
                    key, ", ".join(sorted(RECORD.DELEGATOR_TOP_KEYS)),
                    "remove this key and retry; the file was not changed")
                return emit({"result": "refused", "reason": "invalid-input", **refused}, 2)
        with StateLock(path):
            doc = _delegator_read(path)
            actual = int(doc.get("revision") or 0)
            if args.expect_revision != actual:
                return emit({"result": "refused", "reason": "conflict",
                             "detail": f"file is at revision {actual}", "current_revision": actual}, 3)
            merged = merge_patch(doc, patch)
            merged["schema"] = RECORD.DELEGATOR_SCHEMA
            merged["revision"] = actual + 1
            merged["updated_at"] = observed_at()
            blockers, _dropped = RECORD.delegator_blockers(merged)
            if blockers:
                return emit({"result": "refused", "reason": "invalid-input", "blockers": blockers,
                             "detail": blockers[0]["detail"]}, 2)
            atomic_write(path, json.dumps(merged, ensure_ascii=False, sort_keys=True, indent=1) + "\n")
    except StateRefusal as refusal:
        return emit(refusal.payload, 2)
    except (OSError, ValueError) as exc:
        return fail("invalid-input", str(exc))
    return emit({"result": "written", "revision": merged["revision"]})


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
