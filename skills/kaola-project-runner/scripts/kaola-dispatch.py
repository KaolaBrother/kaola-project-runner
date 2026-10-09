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
import functools
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
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
CEILING_REASONS = frozenset({
    "above-ceiling", "ceiling-incomplete", "ceiling-unreadable",
    "revoked", "paused", "excluded", "expired",
})
CEILING_DUTY = {
    "revoked": "stop",
    "above-ceiling": "stop",
    "expired": "stop",
    "excluded": "stop",
    "paused": "handoff",
    "ceiling-incomplete": "reclaim",
    "ceiling-unreadable": "reclaim",
}
LEGACY_LIVE_STATE = re.compile(r"^\d+\s+live$")
COVERAGE = ("in-flight", "returned", "failed", "unknown", "not-run")
# Issue #286 (G6): the one closed-status vocabulary retire shares with its
# index mirror. Any other value — absent, renamed or unreadable — is a duty.
CLOSED_COVERAGE = ("returned", "failed", "not-run")
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
CHECK_PREFIX = "chk:"
USER_REQUIREMENT_MARKERS = ("<!-- KPR-USER-REQUIREMENTS-START -->",
                            "<!-- KPR-USER-REQUIREMENTS-END -->")
USER_REQUIREMENT_HEADINGS = {
    "project": ("project special requirements", "user requirements", "user special requirements", "用户特殊要求"),
    "delegator": ("delegator special requirements",),
}
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
    limits = RECORD.aggregate_limit_blockers(auth)
    if limits:
        raise ValueError(limits[0]["path"] + ": " + limits[0]["recovery"])
    obsolete = set(auth) & {"model_switches", "paused", "revoked", "classes", "capability_summary"}
    if obsolete:
        raise ValueError("authorization." + sorted(obsolete)[0] + ": legacy duplicate authority; "
                         "plan state migration and reconcile original owner intent before write")
    # `rows` is not a grant list. A catalog-shaped body must not become seats.
    raw = auth.get("grants")
    if raw is None:
        raw = []
    if not isinstance(raw, list):
        raise ValueError("grants must be an array")
    grants = []
    seen: set[str] = set()
    for item in RECORD.expanded_grants(raw):
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
        extra = item.get("extra_seats")
        if isinstance(extra, dict) and extra:
            grant["extra_seats"] = {key: value for key, value in extra.items() if isinstance(key, str)}
        shared_count = item.get("shared_count")
        if isinstance(shared_count, int) and not isinstance(shared_count, bool) and shared_count >= 0:
            grant["shared_count"] = shared_count
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


def current_authorization(auth: dict[str, Any]) -> dict[str, Any]:
    """A sourced authorization write removes ended grants, keeping current stop restrictions."""
    auth = json.loads(json.dumps(auth))
    if not auth.get("grants") and not auth.get("revoked"):
        return auth
    revoked = set(as_id_list(auth.get("revoked")))
    exclusions = set(as_id_list(auth.get("exclusions")))
    catalog = catalog_from_files(platform_paths(Path(__file__), None))
    kept = []
    for grant in auth.get("grants") or []:
        ids = grant.get("preset_ids") or [grant["id"]]
        expiry = parse_expiry(grant["expires"]) if isinstance(grant.get("expires"), str) else None
        current = []
        for ident in ids:
            ended = (grant.get("state") == "revoked" or ident in revoked or (
                catalog.get(ident, {}).get("class") == "Expert" and expiry is not None
                and expiry <= datetime.now(timezone.utc)))
            if ended:
                if catalog.get(ident, {}).get("class") in (None, "Worker"):
                    exclusions.add(ident)
            else:
                current.append(ident)
        if current:
            if "preset_ids" in grant:
                grant["preset_ids"] = current
                special = grant.get("special_requirements")
                if isinstance(special, dict) and set(special) <= set(ids):
                    grant["special_requirements"] = {key: value for key, value in special.items() if key in current}
                RECORD.retain_extra_seats(grant, current)
            kept.append(grant)
    if "grants" in auth:
        auth["grants"] = kept
    exclusions.update(ident for ident in revoked if catalog.get(ident, {}).get("class") in (None, "Worker"))
    auth.pop("revoked", None)
    if exclusions:
        auth["exclusions"] = sorted(exclusions)
    return auth


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


def _positive_extra(extra: Any) -> dict[str, int] | None:
    if not isinstance(extra, dict) or not extra:
        return None
    parsed: dict[str, int] = {}
    for key, value in extra.items():
        if not isinstance(key, str) or not _count_ok(value) or value <= 0:
            return None
        parsed[key] = value
    return parsed


def _runtime_total(grant: dict[str, Any]) -> int | None:
    """Shared pool plus every tier-specific extra. None when this grant has no extra."""
    extra = _positive_extra(grant.get("extra_seats"))
    shared = grant.get("shared_count")
    if extra is None or not _count_ok(shared):
        return None
    return shared + sum(extra.values())


def shared_seat_capacities(grants: list[dict[str, Any]]) -> dict[str, int]:
    """One capacity per shared label, without adding the same pool per grant.

    A grouped grant with extra_seats reports the runtime total, not the
    largest single tier cap. Tiers that share the pool can still be refused
    by that pool even when the total has room.
    """
    capacities: dict[str, int] = {}
    totals: dict[str, int] = {}
    for grant in grants:
        seat = grant.get("shared_seat")
        if grant.get("state") != "granted" or not isinstance(seat, str) or not seat:
            continue
        count = grant.get("count")
        capacity = count if isinstance(count, int) and not isinstance(count, bool) else 1
        capacities[seat] = max(capacities.get(seat, capacity), capacity)
        total = _runtime_total(grant)
        if total is not None:
            totals[seat] = total
    for seat, total in totals.items():
        capacities[seat] = total
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
        if not pool and not _count_ok(grant.get("count")):
            withhold(preset, "count-unreadable")
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
        if grant and grant.get("switch_authorization") is False:
            candidate["switch_authorization"] = False
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


def current_candidates(catalog: dict[str, Any], auth: dict[str, Any], grants: list[dict[str, Any]],
                       available: dict[str, str], document: dict[str, Any] | None,
                       repo: str | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Both current views use existing grant, ceiling, hold and availability facts."""
    ceiling, error = delegator_ceiling(repo) if repo else (None, None)
    if ceiling:
        ceiling = admission_ceiling(ceiling)
    effective = apply_ceiling_to_grants(grants, ceiling, catalog) if ceiling else grants
    candidates, withheld = eligibility(catalog, auth, effective, available)
    holds = preset_holds(document)
    kept = []
    for candidate in candidates:
        ident = candidate["id"]
        reason = ("ceiling-unreadable" if error else ceiling_block(
            ceiling, ident, candidate["class"], expert_grants=True) if ceiling else None)
        if ident in holds:
            reason = "on-hold"
        if reason:
            withheld.append({"id": ident, "reason": reason, **({"evidence": error} if error else {})})
        else:
            kept.append(candidate)
    return kept, withheld


def command_project(args: argparse.Namespace) -> int:
    try:
        auth_doc = load_object(Path(args.authorization))
        auth = authorization_object(auth_doc)
        grants = normalize_grants(auth)
        available = availability_map(
            load_object(Path(args.availability)) if args.availability else None
        )
        catalog = catalog_from_files(platform_paths(Path(__file__), args.platforms))
        repo = getattr(args, "repo", None) or ((auth_doc.get("state") or {}).get("project") or {}).get("repo")
        candidates, withheld = current_candidates(catalog, auth, grants, available, auth_doc, repo)
    except ValueError as exc:
        return fail("invalid-input", str(exc))
    if args.seats:
        if not args.repo:
            return fail("invalid-input", "--seats needs --repo")
        return project_seats(args, auth, grants, catalog, bound_sideagent(auth_doc))
    # Derived eligible ids only; no independently maintained capability paragraph.
    return emit({
        "schema": "kaola-dispatch-project/1",
        "capability_summary": capability_summary(candidates),
        "candidates": candidates,
        "withheld": withheld,
    })


def observed_at() -> str:
    return datetime.now(timezone.utc).isoformat()


def seat_projection(args: argparse.Namespace, auth: dict[str, Any],
                  grants: list[dict[str, Any]], catalog: dict[str, dict[str, Any]],
                  binding: dict[str, Any] | None = None,
                  document: dict[str, Any] | None = None) -> dict[str, Any]:
    """Read the existing occupancy facts; report limits without deciding authority."""
    repo = str(Path(args.repo).resolve())
    unknown: list[str] = []
    skills = Path(args.skills_root) if args.skills_root else None
    status_skills = seat_status_skills_root(Path(__file__), skills)
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
        if (row.get("state") == "stopped" or row.get("host_class") is True
                or (row.get("session_role") == "host" and row.get("identity") == "verified")):
            continue
        if isinstance(row.get("repo"), str) and not same_repo(row["repo"], repo):
            continue
        if binding_row(binding, row) or (row.get("session_role") in SIDEAGENT_ROLES and row.get("identity") == "verified"):
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
                                   status_skills,
                                   require_identity=True)
    used, elite, shared, unnamed = live_occupancy(bound, repo, catalog, grants, resolved)
    unknown.extend("preset-unresolved:" + grant["id"] for grant in grants if grant["id"] not in catalog)
    unknown.extend("preset-unknown:" + row["session"] for row in bound
                   if row["session"] not in resolved)
    if state != "known":
        unknown.append("live-source-unavailable")
    listed = None if args.live else acp_runner(Path(__file__), skills)
    projection = {
        "schema": "kaola-dispatch-seats/1", "repo": repo,
        "source": {"authorization": args.authorization, "live": args.live or (str(listed) if listed else None),
                   "index": args.index, "as_of": observed_at()},
        "unknown_reasons": unknown,
        "observed_elite_expert": elite if state == "known" else None,
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
    }
    projection["summary"] = seat_summary(projection, args, auth, grants, catalog, bound, items, document)
    return projection


def project_seats(args: argparse.Namespace, auth: dict[str, Any],
                  grants: list[dict[str, Any]], catalog: dict[str, dict[str, Any]],
                  binding: dict[str, Any] | None = None) -> int:
    return emit(seat_projection(args, auth, grants, catalog, binding))


def seat_summary(projection: dict[str, Any], args: argparse.Namespace, auth: dict[str, Any],
                 grants: list[dict[str, Any]], catalog: dict[str, dict[str, Any]],
                 rows: list[dict[str, Any]], items: dict[str, dict[str, Any]],
                 document: dict[str, Any] | None) -> dict[str, Any]:
    """Current user report, from the same occupancy and admission facts. Never stored."""
    if document is None:
        try:
            document = load_object(Path(args.repo) / ".kaola" / "heartbeat-prompt.json")
        except ValueError:
            document = None
    tasks = ((document or {}).get("state") or {}).get("tasks") or {}
    unknown_sources = list(projection["unknown_reasons"])
    if document is None or document.get("schema") != STATE_SCHEMA:
        unknown_sources.append("current-task-source-unavailable")
    holds = preset_holds(document)
    ceiling, ceiling_error = delegator_ceiling(projection["repo"])
    if ceiling:
        ceiling = admission_ceiling(ceiling)
    effective = apply_ceiling_to_grants(grants, ceiling, catalog) if ceiling else grants
    availability = availability_map(load_object(Path(args.availability))) if getattr(args, "availability", None) else {}
    candidates, withheld = eligibility(catalog, auth, effective, availability)
    reasons = {item["id"]: item["reason"] for item in withheld}
    resolved = {row["session"]: row.get("preset") for row in projection["sessions"]}
    occupied = []
    for row in rows:
        preset = resolved.get(row["session"])
        if catalog.get(preset, {}).get("class") not in ("Elite", "Expert", "Worker"):
            continue
        links = []
        for ident, task in tasks.items():
            if not isinstance(task, dict):
                continue
            exact = (row["session"], row["holder_instance_id"]) in seat_entries(task)
            linked = any(ref in items and items[ref].get("session") == row["session"]
                         and items[ref].get("holder_instance_id") == row["holder_instance_id"]
                         and items[ref].get("task_id") == ident for ref in task.get("dispatch") or [])
            if exact or linked:
                links.append(ident)
        mutation = row.get("mutation_status")
        status = ("held/faulted" if row.get("state") in ("error", "failed") or preset in holds
                  or row.get("agent_alive") is False or row.get("socket_ok") is False
                  or mutation in ("failed", "refused") else
                  "reserved" if mutation == "not_started" else
                  "working" if mutation == "in_progress" and links else
                  "idle-but-unreclaimed" if mutation in ("completed", "accepted") else "unknown")
        occupied.append({"session": row["session"], "holder_instance_id": row["holder_instance_id"],
                         "preset": preset, "tasks": sorted(links), "state": status,
                         **({"links": "unknown"} if not links and mutation != "not_started" else {})})
    groups: dict[str, dict[str, Any]] = {}
    worker_seats: set[str] = set()

    def add_seat(preset: str, klass: str, count: Any, shared_seat: str | None,
                 lifetime: str | None, special: dict[str, Any] | None,
                 reason: str | None, runtime_total: int | None = None) -> None:
        shared_limit = next((group for group in (ceiling or {}).get("groups", []) if preset in group["ids"]), None)
        group = ("grant:" + ",".join(sorted(shared_limit["ids"]))) if shared_limit else shared_seat or preset
        entry = groups.setdefault(group, {"group": group, "presets": [], "authorized_count": None,
                                          "occupied": [], "unavailable": [], "idle_available": None})
        # A tier extra is one per-runtime total. The ceiling total may narrow
        # it. A host grant with no extra stays on the shared pool count, so a
        # ceiling extra the host omitted does not enlarge the summary.
        if runtime_total is not None and _count_ok(runtime_total):
            if entry.get("_runtime") and _count_ok(entry["authorized_count"]):
                entry["authorized_count"] = min(entry["authorized_count"], runtime_total)
            else:
                entry["authorized_count"] = runtime_total
            entry["_runtime"] = True
            ceiling_total = shared_limit.get("total") if shared_limit else None
            if _count_ok(ceiling_total):
                entry["authorized_count"] = min(entry["authorized_count"], ceiling_total)
        elif _count_ok(count) and not entry.get("_runtime"):
            entry["authorized_count"] = max(entry["authorized_count"] or 0, count)
            pool = shared_limit.get("count") if shared_limit else None
            if _count_ok(pool):
                entry["authorized_count"] = min(entry["authorized_count"], pool)
        entry["presets"].append({"id": preset, "class": klass, "count": count,
                                  "default_model": catalog[preset]["selection"].get("model_id"),
                                  "default_effort": catalog[preset]["selection"].get("effort"),
                                  **({"owner_overrides": special} if special else {}),
                                  **({"lifetime": lifetime or "task"} if klass == "Expert" else {})})
        if preset in holds:
            reason = "held:" + ",".join(holds[preset])
        if ceiling_error:
            reason = "ceiling-unreadable"
        if reason:
            entry["unavailable"].append({"id": preset, "reason": reason})

    for grant in effective:
        preset = grant["id"]
        klass = catalog.get(preset, {}).get("class")
        if klass not in ("Elite", "Expert", "Worker") or grant.get("state") == "revoked" or preset in auth.get("revoked", []):
            continue
        if klass == "Worker" and not _count_ok(grant.get("count")):
            # A counted Worker grant is a seat; the uncounted default pool is not.
            continue
        blocked = ceiling_block(ceiling, preset, klass, expert_grants=True) if ceiling else None
        if blocked in ("above-ceiling", "revoked") or (klass == "Worker" and blocked == "ceiling-incomplete"):
            continue
        if klass == "Worker":
            worker_seats.add(preset)
        add_seat(preset, klass, grant.get("count"), grant.get("shared_seat"),
                 grant.get("lifetime"), grant.get("special_requirements"),
                 blocked or reasons.get(preset), _runtime_total(grant))
    if ceiling and not ceiling_error:
        # The Delegator's authorization is the seat source: an Elite/Expert
        # preset it grants but the Host grants omit is still authorized,
        # reported unavailable as host-grant-missing. A counted Worker row is
        # a seat the same way, but the pool needs no Host grant.
        host_ids = {grant["id"] for grant in effective}
        extras = ((ceiling.get("elite_ids") or {}).keys()
                  | (ceiling.get("expert_ids") or {}).keys()) - host_ids
        for preset in sorted(extras):
            klass = catalog.get(preset, {}).get("class")
            if klass not in ("Elite", "Expert", "Worker"):
                continue
            count = ceiling_count(ceiling, preset, klass)
            if klass == "Worker" and not _count_ok(count):
                continue
            blocked = ceiling_block(ceiling, preset, klass, expert_grants=True)
            if blocked in ("above-ceiling", "revoked") or (klass == "Worker" and blocked == "ceiling-incomplete"):
                continue
            if klass == "Worker":
                worker_seats.add(preset)
            fact = (ceiling.get("by_id") or {}).get(preset) or {}
            reason = blocked or reasons.get(preset)
            add_seat(preset, klass, count, None,
                     fact.get("lifetime"), None,
                     reason if klass == "Worker" else reason or "host-grant-missing")
    worker_pool = []
    if not ceiling_error:
        for item in candidates:
            preset = item["id"]
            if item["class"] != "Worker" or preset in holds or preset in worker_seats:
                continue
            if ceiling and ceiling_block(ceiling, preset, "Worker", expert_grants=True):
                continue
            worker_pool.append(preset)
        worker_pool.sort()
    # Occupancy rows were computed for Worker presets too; only counted Worker
    # seat presets stay listed. Uncounted pool rows report nowhere.
    occupied = [row for row in occupied
                if row["preset"] in worker_seats
                or catalog.get(row["preset"], {}).get("class") in ("Elite", "Expert")]
    observed = projection["observed_elite_expert"]
    authorized_total = (sum(group["authorized_count"] for group in groups.values())
                        if all(group["authorized_count"] is not None for group in groups.values()) else None)
    for entry in groups.values():
        entry.pop("_runtime", None)
        ids = {item["id"] for item in entry["presets"]}
        entry["occupied"] = [row for row in occupied if row["preset"] in ids]
        blocked = {item["id"] for item in entry["unavailable"]}
        available_ids = ids - blocked
        availability_unknown = any(
            availability.get(ident, "unknown") == "unknown" for ident in available_ids)
        unknown = bool(unknown_sources) or ceiling_error is not None or any(row["state"] == "unknown" for row in entry["occupied"])
        entry["occupancy_unknown"] = unknown
        entry["availability_unknown"] = availability_unknown
        count = entry["authorized_count"]
        if not available_ids:
            entry["idle_available"] = 0
        elif not unknown and not availability_unknown and count is not None:
            entry["idle_available"] = max(0, count - len(entry["occupied"]))
    return {"groups": list(groups.values()),
            "expert_authorization": "present" if any(item["class"] == "Expert" for group in groups.values()
                                                       for item in group["presets"]) else "none",
            "occupied": occupied, "authorized_total": authorized_total, "occupied_elite_expert": observed,
            "worker_pool": worker_pool,
            "idle_available_total": sum(group["idle_available"] for group in groups.values())
                if all(group["idle_available"] is not None for group in groups.values()) else None,
            "unknown_reasons": unknown_sources,
            "resource_limits": {key: auth[key] for key in ("account_token_quotas", "exclusions") if key in auth},
            "scope": "current project; external target/account capacity requires its original resource receipt",
            "source": projection["source"]}


def delegator_seats(args: argparse.Namespace, document: dict[str, Any], path: Path) -> dict[str, Any]:
    repo = Path(args.repo).resolve() if getattr(args, "repo", None) else repo_of_state_file(path)
    options = argparse.Namespace(repo=str(repo), authorization=str(path),
                                 live=getattr(args, "live", None), index=getattr(args, "index", None),
                                 skills_root=getattr(args, "skills_root", None), availability=getattr(args, "availability", None))
    if options.index is None and (repo / ".kaola" / "dispatch-index.json").is_file():
        options.index = str(repo / ".kaola" / "dispatch-index.json")
    try:
        catalog = catalog_from_files(platform_paths(Path(__file__), getattr(args, "platforms", None)))
        if document.get("schema") == RECORD.DELEGATOR_SCHEMA:
            source = document.get("authorization") or {}
            problems = RECORD.delegator_authorization_blockers(source)
            legal_overlap = (_listed_once(source.get("elite_grants"))
                             & _listed_once(source.get("expert_task_grants")))
            problems = [problem for problem in problems if not (
                problem.get("path", "").startswith("authorization.grants")
                and any(f"duplicate preset {ident}" in (problem.get("recovery") or "")
                        for ident in legal_overlap))]
            if problems:
                raise ValueError(problems[0]["detail"])
            auth = {key: source[key] for key in ("exclusions", "account_token_quotas") if key in source}
            auth["grants"] = []
            # An Expert choice named in an elite_grants row and with its own
            # expert_task_grants row is one legal overlap, not a duplicate
            # grant. The Expert permission is read from the ceiling file.
            elite_listed = {ident for grant in source.get("elite_grants") or []
                            if isinstance(grant, dict) for ident in _grant_ident_list(grant)}
            for key in ("elite_grants", "expert_task_grants"):
                for grant in source.get(key) or []:
                    if key == "expert_task_grants" and isinstance(grant, dict):
                        if isinstance(grant.get("preset_id"), str) and grant["preset_id"] in elite_listed:
                            continue
                        ids = grant.get("preset_ids")
                        if isinstance(ids, list):
                            kept = [ident for ident in ids if ident not in elite_listed]
                            if ids and not kept:
                                continue
                            grant = {**grant, "preset_ids": kept}
                            RECORD.retain_extra_seats(grant, kept)
                    row = {field: grant[field] for field in ("preset_ids", "count", "state", "lifetime", "expires") if field in grant}
                    if isinstance(grant.get("extra_seats"), dict) and grant["extra_seats"]:
                        row["extra_seats"] = grant["extra_seats"]
                    if isinstance(grant.get("special_requirements"), dict):
                        row["special_requirements"] = grant["special_requirements"]
                    if grant.get("preset_id"):
                        row["id"] = grant["preset_id"]
                    row.setdefault("state", "granted")
                    if "switch_authorization" in grant:
                        row["model_switch"] = grant["switch_authorization"]
                    auth["grants"].append(row)
            listed = {ident for row in auth["grants"] for ident in _grant_ident_list(row)}
            listed.update(row["id"] for row in auth["grants"] if isinstance(row.get("id"), str))
            for ident in source.get("worker_pool") or []:
                if isinstance(ident, str) and ident not in listed:
                    listed.add(ident)
                    auth["grants"].append({"id": ident, "state": "granted"})
            document = None
        else:
            auth = authorization_object(document)
        return seat_projection(options, auth, normalize_grants(auth), catalog,
                               bound_sideagent(document), document)["summary"]
    except (OSError, ValueError) as exc:
        return {"unknown_reasons": [str(exc)], "expert_authorization": "unknown",
                "idle_available_total": None, "worker_pool": None}


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
    if grant.get("switch_authorization") is False:
        return False
    if grant.get("model_switch") is True:
        return True
    return False


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


_count_ok = RECORD.count_ok


def _extra_map(grant: dict[str, Any], ids: list[str]) -> dict[str, int]:
    """Tier extras on a shared row. An empty or invalid map leaves count as the pool."""
    extra = grant.get("extra_seats")
    if not isinstance(extra, dict) or not extra or len(ids) <= 1:
        return {}
    parsed: dict[str, int] = {}
    members = set(ids)
    for key, value in extra.items():
        if not isinstance(key, str) or key not in members or not _count_ok(value) or value <= 0:
            return {}
        parsed[key] = value
    return parsed


def _grant_ident_list(grant: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    if isinstance(grant.get("preset_id"), str) and grant["preset_id"]:
        ids.append(grant["preset_id"])
    many = grant.get("preset_ids")
    if isinstance(many, list) and all(isinstance(item, str) for item in many):
        ids.extend(item for item in many if item and item not in ids)
    return ids


def _listed_once(rows: Any) -> set[str]:
    counts: dict[str, int] = {}
    if not isinstance(rows, list):
        return set()
    for grant in rows:
        if not isinstance(grant, dict):
            continue
        for ident in _grant_ident_list(grant):
            counts[ident] = counts.get(ident, 0) + 1
    return {ident for ident, count in counts.items() if count == 1}


def _expiry_state(value: Any) -> str:
    """none, ok, expired, or unreadable. An offset instant; Z is accepted."""
    if value is None:
        return "none"
    if not isinstance(value, str):
        return "unreadable"
    moment = parse_expiry(value)
    if moment is None:
        return "unreadable"
    if moment <= datetime.now(timezone.utc):
        return "expired"
    return "ok"


def _expiry_evidence(ids: list[str], field: str, expires: Any, state: str) -> dict[str, Any]:
    return {
        "expires": expires,
        "presets": list(ids),
        "source": ".kaola/delegator-heartbeat.json",
        "field": field,
        "path": field,
        "allowed": "ISO-8601 instant with an offset",
        "recovery": (
            "Delegator: a past window is expired; keep the ended grant out of new admission"
            if state == "expired"
            else "Delegator: replace expires with an ISO-8601 instant that has an offset; do not infer a window"
        ),
        "role": "host",
    }


def _lifetime_evidence(ids: list[str], field: str, lifetime: Any) -> dict[str, Any]:
    return {
        "lifetime": lifetime,
        "presets": list(ids),
        "source": ".kaola/delegator-heartbeat.json",
        "field": field,
        "path": field,
        "allowed": "task or standing",
        "recovery": (
            "Delegator: Expert permission is task or standing for this choice only; "
            "it does not apply to the group's Elite choices"
        ),
        "role": "host",
    }


def admission_ceiling(ceiling: dict[str, Any]) -> dict[str, Any]:
    """Expert grant facts override the same preset's Elite-row copy for admission."""
    extra = ceiling.get("expert_by_id")
    if not extra:
        return ceiling
    merged = dict(ceiling)
    merged["by_id"] = {**(ceiling.get("by_id") or {}), **extra}
    return merged


def delegator_ceiling(repo: str, observations: list[dict[str, Any]] | None = None) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Read current grants with the writer's shape check. Scope bad grants by id.

    An untyped old file keeps legacy Host authorization. Report its migration
    duty without changing supported transport or already-running assignments.
    """
    path = Path(repo) / ".kaola" / "delegator-heartbeat.json"
    if not path.is_file():
        return None, None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, RECORD.refusal(str(path), "readable JSON object",
                                    "recover this file from its owner and original evidence; in-flight work stays current")
    if not isinstance(doc, dict) or doc.get("schema") != RECORD.DELEGATOR_SCHEMA:
        if observations is not None:
            observations.append({"code": "delegator-migration-needed", "path": str(path),
                                 "allowed": RECORD.DELEGATOR_SCHEMA,
                                 "recovery": "Delegator: run delegator view and migrate without --write; reconcile grants and pending duties before --write. Legacy Host authorization continues."})
        return None, None
    auth = doc.get("authorization")
    if not isinstance(auth, dict):
        return None, RECORD.refusal("authorization", "object of current grants and limits",
                                    "Delegator: recover current authorization from its source; do not create grants")
    errors = RECORD.delegator_authorization_blockers(auth)
    problems: dict[str, str] = {}
    evidence: dict[str, dict[str, Any]] = {}
    expert_problems: dict[str, str] = {}
    expert_evidence: dict[str, dict[str, Any]] = {}
    bad_grants: set[int] = set()
    expert_bad: set[int] = set()
    worker_problem = elite_problem = expert_problem = None
    # One shared group may name an Expert choice that also has its own
    # expert_task_grants row. That overlap is the Expert permission, not a
    # second seat and not a shape failure.
    legal_overlap = _listed_once(auth.get("elite_grants")) & _listed_once(auth.get("expert_task_grants"))
    for error in errors:
        field = error["path"]
        grant_match = re.match(r"authorization\.(elite_grants|expert_task_grants)\[(\d+)\]", field)
        if grant_match and grant_match[1] == "elite_grants":
            index = int(grant_match[2])
            grant = auth["elite_grants"][index]
            bad_grants.add(index)
            ids = _grant_ident_list(grant) if isinstance(grant, dict) else []
            if ids:
                for ident in ids:
                    problems[ident] = "ceiling-unreadable"
                    evidence.setdefault(ident, error)
            else:
                elite_problem = elite_problem or error
        elif grant_match:
            index = int(grant_match[2])
            pool = auth.get("expert_task_grants")
            grant = pool[index] if isinstance(pool, list) and index < len(pool) else None
            expert_bad.add(index)
            ids = _grant_ident_list(grant) if isinstance(grant, dict) else []
            if ids:
                for ident in ids:
                    expert_problems.setdefault(ident, "ceiling-unreadable")
                    expert_evidence.setdefault(ident, error)
            else:
                expert_problem = expert_problem or error
        elif field in ("authorization.worker_pool", "authorization.worker_pool_cap"):
            worker_problem = worker_problem or error
        elif field in ("authorization.elite_cap", "authorization.total_cap", "authorization.elite_grants"):
            elite_problem = elite_problem or error
        elif field == "authorization.expert_task_grants":
            expert_problem = expert_problem or error
        elif field in ("authorization.revoked", "authorization.paused", "authorization.exclusions"):
            return None, error
        elif field.startswith("authorization.grants") and any(
            f"duplicate preset {ident}" in (error.get("recovery") or "") for ident in legal_overlap
        ):
            continue
        # Non-dispatch fields have no new authority. Their shape errors are
        # current migration observations, not an unrelated dispatch stop.
        elif observations is not None:
            observations.append({"code": "delegator-field-invalid", **error})
    blocked: dict[str, str] = {}
    for key, reason in (("revoked", "revoked"), ("paused", "paused"), ("exclusions", "excluded")):
        for ident in auth.get(key) or []:
            blocked.setdefault(ident, reason)
    raw = auth.get("elite_grants")
    for grant in raw or []:
        if isinstance(grant, dict) and grant.get("state") in ("paused", "revoked", "excluded"):
            for ident in grant.get("preset_ids") or [grant.get("preset_id")]:
                blocked.setdefault(ident, grant["state"])
    catalog = catalog_from_files(platform_paths(Path(__file__), None))
    elite = by_id = groups = None
    if isinstance(raw, list):
        elite, by_id, groups, semantic, semantic_evidence = _parse_elite_grants(
            [grant for index, grant in enumerate(raw) if index not in bad_grants],
            [index for index in range(len(raw)) if index not in bad_grants],
            catalog, legal_overlap)
        problems.update({ident: reason for ident, reason in semantic.items() if ident not in problems})
        evidence.update({ident: item for ident, item in semantic_evidence.items() if ident not in evidence})
    raw_expert = auth.get("expert_task_grants")
    expert_ids = expert_by_id = None
    expert_groups: list[dict[str, Any]] = []
    if isinstance(raw_expert, list):
        kept = [grant for index, grant in enumerate(raw_expert) if index not in expert_bad]
        kept_index = [index for index in range(len(raw_expert)) if index not in expert_bad]
        expert_ids, expert_by_id, expert_groups, expert_semantic, expert_semantic_evidence = _parse_expert_grants(
            kept, kept_index)
        for ident, reason in expert_semantic.items():
            expert_problems.setdefault(ident, reason)
        for ident, item in expert_semantic_evidence.items():
            expert_evidence.setdefault(ident, item)
    elif raw_expert is not None:
        expert_problem = expert_problem or RECORD.refusal(
            "authorization.expert_task_grants", "array of grant objects",
            "Delegator: source the original Expert grants before admission")
    return {
        "blocked": blocked,
        "worker_ids": set(auth["worker_pool"]) if isinstance(auth.get("worker_pool"), list) and worker_problem is None else None,
        "elite_ids": elite,
        "expert_ids": expert_ids,
        "by_id": by_id or {}, "expert_by_id": expert_by_id or {},
        "groups": (groups or []) + expert_groups,
        "problems": problems, "problem_evidence": evidence,
        "expert_problems": expert_problems, "expert_problem_evidence": expert_evidence,
        "worker_problem": worker_problem, "elite_problem": elite_problem,
        "expert_problem": expert_problem,
    }, None


def _parse_elite_grants(
    raw_elite: list[dict[str, Any]], source_indices: list[int],
    catalog: dict[str, dict[str, Any]], expert_owned: set[str],
) -> tuple[
    dict[str, int | None], dict[str, dict[str, Any]], list[dict[str, Any]],
    dict[str, str], dict[str, dict[str, Any]],
]:
    """Interpret shape-checked Elite grants. expires is the time window.

    A shared row's Expert lifetime does not withhold the Elite choices.
    An Expert preset that also has expert_task_grants keeps that clock.
    """
    elite: dict[str, int | None] = {}
    by_id: dict[str, dict[str, Any]] = {}
    groups: list[dict[str, Any]] = []
    problems: dict[str, str] = {}
    problem_evidence: dict[str, dict[str, Any]] = {}

    def problem(ident: str, reason: str, evidence: dict[str, Any] | None = None) -> None:
        problems.setdefault(ident, reason)
        if evidence:
            problem_evidence.setdefault(ident, evidence)

    def literal(ident_list: list[str], field: str, key: str, value: Any) -> None:
        evidence = {
            key: value,
            "presets": list(ident_list),
            "source": ".kaola/delegator-heartbeat.json",
            "field": field,
            "path": field,
            "allowed": "typed grant supported by original owner authority",
            "recovery": "Delegator and Host: reconcile this literal condition from its source for the affected grant; keep it current until resolved",
            "role": "host",
        }
        for ident in ident_list:
            problem(ident, "ceiling-incomplete", evidence)

    for index, grant in zip(source_indices, raw_elite):
        ids: list[str] = []
        if isinstance(grant.get("preset_id"), str):
            ids.append(grant["preset_id"])
        many = grant.get("preset_ids")
        if isinstance(many, list) and all(isinstance(item, str) for item in many):
            ids.extend(item for item in many if item not in ids)
        count = grant.get("count")
        stated = count if _count_ok(count) else None
        extra = _extra_map(grant, ids)
        switch = grant.get("switch_authorization")
        lifetime = grant.get("lifetime")
        prose = isinstance(lifetime, str) and lifetime not in GRANT_LIFETIMES
        window = _expiry_state(grant.get("expires"))
        expires_field = f"authorization.elite_grants[{index}].expires"
        shared = len(ids) > 1

        def elite_choice(ident: str) -> bool:
            # Expert permission owns this choice. The Elite window does not.
            if ident in expert_owned:
                return False
            if shared and catalog.get(ident, {}).get("class") == "Expert":
                return False
            return True

        if window == "expired":
            affected = [ident for ident in ids if elite_choice(ident)]
            if affected:
                window_evidence = _expiry_evidence(affected, expires_field, grant.get("expires"), "expired")
                for ident in affected:
                    problem(ident, "expired", window_evidence)
        elif window == "unreadable":
            affected = [ident for ident in ids if elite_choice(ident)]
            if affected:
                window_evidence = _expiry_evidence(affected, expires_field, grant.get("expires"), "unreadable")
                for ident in affected:
                    problem(ident, "expiry-unreadable", window_evidence)
        if prose and shared and window == "none":
            # No Elite window. The prose lifetime is Expert permission only.
            experts = [ident for ident in ids
                       if ident not in expert_owned and catalog.get(ident, {}).get("class") == "Expert"]
            if experts:
                life_evidence = _lifetime_evidence(
                    experts, f"authorization.elite_grants[{index}].lifetime", lifetime)
                for ident in experts:
                    problem(ident, "lifetime-unreadable", life_evidence)
            lifetime = None
        elif prose and window != "ok":
            # A single grant with no readable window still names the literal lifetime.
            # A readable expires is the window, so the same lifetime is not incomplete.
            if window == "none":
                literal(ids, f"authorization.elite_grants[{index}].lifetime", "lifetime", lifetime)
            lifetime = None
        elif prose:
            lifetime = None
        special = grant.get("special_requirements")
        if isinstance(special, str):
            literal(ids, f"authorization.elite_grants[{index}].special_requirements",
                    "special_requirements", special)
            special = None
        if len(ids) > 1:
            if stated is None:
                for ident in ids:
                    problem(ident, "ceiling-incomplete")
            else:
                # count stays the shared pool. extra is the tier-specific addition.
                # total is the per-runtime cap. A row with no extra keeps total == count.
                groups.append({
                    "ids": set(ids),
                    "count": stated,
                    "extra": extra,
                    "total": stated + sum(extra.values()),
                })
        for ident in ids:
            tier = None if stated is None else stated + extra.get(ident, 0)
            if ident in elite and elite[ident] != tier:
                problem(ident, "ceiling-unreadable")
                elite[ident] = None
            else:
                elite[ident] = tier
            fact = by_id.setdefault(ident, {
                "count": elite[ident], "switch": None, "lifetime": None, "special": None,
            })
            fact["count"] = elite[ident]
            choice_special = special.get(ident) if isinstance(special, dict) and special and set(special) <= set(ids) else special
            for key, value in (("switch", switch), ("lifetime", lifetime), ("special", choice_special)):
                # Elite seats are a time window. A task/standing lifetime on the
                # same row is Expert permission and does not attach to Elite choices.
                # A missing Expert lifetime is task, the same default as Host grants.
                if key == "lifetime" and catalog.get(ident, {}).get("class") != "Expert":
                    continue
                if key == "lifetime" and value is None and not prose:
                    value = "task"
                if value is None:
                    continue
                if fact[key] is None:
                    fact[key] = value
                elif fact[key] != value:
                    problem(ident, "ceiling-incomplete")
            if window == "ok" and elite_choice(ident):
                fact["expires"] = grant.get("expires")
    return elite, by_id, groups, problems, problem_evidence


def _parse_expert_grants(raw_expert: list[dict[str, Any]], source_indices: list[int]) -> tuple[
    dict[str, int | None], dict[str, dict[str, Any]], list[dict[str, Any]],
    dict[str, str], dict[str, dict[str, Any]],
]:
    """Expert grants are per-task or standing. Absence of lifetime means task."""
    expert: dict[str, int | None] = {}
    by_id: dict[str, dict[str, Any]] = {}
    groups: list[dict[str, Any]] = []
    problems: dict[str, str] = {}
    problem_evidence: dict[str, dict[str, Any]] = {}

    def problem(ident: str, reason: str, item: dict[str, Any] | None = None) -> None:
        problems.setdefault(ident, reason)
        if item:
            problem_evidence.setdefault(ident, item)

    for index, grant in zip(source_indices, raw_expert):
        if not isinstance(grant, dict):
            continue
        ids = _grant_ident_list(grant)
        if not ids:
            continue
        field = f"authorization.expert_task_grants[{index}]"
        if grant.get("state") in ("paused", "revoked", "excluded"):
            for ident in ids:
                problem(ident, grant["state"])
            continue
        count = grant.get("count")
        stated = count if _count_ok(count) else None
        extra = _extra_map(grant, ids)
        special = grant.get("special_requirements")
        if isinstance(special, str):
            problem_evidence_row = {
                "special_requirements": special,
                "presets": list(ids),
                "source": ".kaola/delegator-heartbeat.json",
                "field": f"{field}.special_requirements",
                "path": f"{field}.special_requirements",
                "allowed": "typed grant supported by original owner authority",
                "recovery": "Delegator and Host: reconcile this literal condition from its source for the affected grant; keep it current until resolved",
                "role": "host",
            }
            for ident in ids:
                problem(ident, "ceiling-incomplete", problem_evidence_row)
            continue
        lifetime = grant.get("lifetime")
        lifetime = "task" if lifetime is None else lifetime.strip() if isinstance(lifetime, str) else ""
        if lifetime not in GRANT_LIFETIMES:
            life_evidence = _lifetime_evidence(ids, f"{field}.lifetime", grant.get("lifetime"))
            for ident in ids:
                problem(ident, "lifetime-unreadable", life_evidence)
            continue
        window = _expiry_state(grant.get("expires"))
        if window in ("expired", "unreadable"):
            reason = "expired" if window == "expired" else "expiry-unreadable"
            window_evidence = _expiry_evidence(ids, f"{field}.expires", grant.get("expires"), window)
            for ident in ids:
                problem(ident, reason, window_evidence)
            continue
        if len(ids) > 1:
            if stated is None:
                for ident in ids:
                    problem(ident, "ceiling-incomplete")
            else:
                groups.append({
                    "ids": set(ids),
                    "count": stated,
                    "extra": extra,
                    "total": stated + sum(extra.values()),
                })
        switch = grant.get("switch_authorization")
        for ident in ids:
            if ident in problems:
                continue
            tier = None if stated is None else stated + extra.get(ident, 0)
            if ident in expert and expert[ident] != tier:
                problem(ident, "ceiling-unreadable")
                expert[ident] = None
            else:
                expert[ident] = tier
            fact = by_id.setdefault(ident, {
                "count": expert[ident], "switch": None, "lifetime": None, "special": None,
            })
            fact["count"] = expert[ident]
            fact["lifetime"] = lifetime
            if window == "ok":
                fact["expires"] = grant.get("expires")
            if isinstance(switch, bool) and fact.get("switch") is None:
                fact["switch"] = switch
            choice_special = special.get(ident) if isinstance(special, dict) and special and set(special) <= set(ids) else special
            if isinstance(choice_special, dict) and fact.get("special") is None:
                fact["special"] = choice_special
    return expert, by_id, groups, problems, problem_evidence


def _shared_ceiling_member(ceiling: dict[str, Any], preset: str) -> bool:
    """True when this preset shares one count with another preset."""
    for group in ceiling.get("groups") or []:
        ids = group.get("ids") or ()
        if preset in ids and len(ids) > 1:
            return True
    return False


def ceiling_group(ceiling: dict[str, Any] | None, preset: str) -> dict[str, Any] | None:
    if not ceiling:
        return None
    for group in ceiling.get("groups") or []:
        if preset in group["ids"]:
            return group
    return None


def ceiling_block(ceiling: dict[str, Any], preset: str, class_name: str,
                  expert_grants: bool = False) -> str | None:
    field_problem = ceiling.get("worker_problem" if class_name == "Worker" else "elite_problem")
    if field_problem:
        return "ceiling-unreadable"
    # An expert_task_grants row is that choice's own permission. It is not an
    # Elite seat, and the group's Elite window does not replace it.
    if expert_grants and class_name == "Expert":
        expert_problems = ceiling.get("expert_problems") or {}
        if preset in expert_problems:
            return expert_problems[preset]
        if preset in (ceiling.get("expert_ids") or {}) and preset not in ceiling["blocked"]:
            return None
        if ceiling.get("expert_problem") is not None and preset not in (ceiling.get("elite_ids") or {}):
            return "ceiling-unreadable"
    if preset in (ceiling.get("problems") or {}):
        return ceiling["problems"][preset]
    if preset in ceiling["blocked"]:
        return ceiling["blocked"][preset]
    if class_name == "Worker":
        if ceiling["worker_ids"] is None:
            return "ceiling-incomplete"
        return None if preset in ceiling["worker_ids"] else "above-ceiling"
    if ceiling["elite_ids"] is None:
        return "ceiling-incomplete"
    if preset in ceiling["elite_ids"]:
        # A shared row may name an Expert choice. That choice is not an Elite
        # seat: it still needs its own expert_task_grants row. A single Elite
        # grant, including one that names an Expert preset, stays a time window.
        if (expert_grants and class_name == "Expert"
                and preset not in (ceiling.get("expert_ids") or {})
                and _shared_ceiling_member(ceiling, preset)):
            return "above-ceiling"
        return None
    return "above-ceiling"


def ceiling_count(ceiling: dict[str, Any], preset: str, class_name: str) -> int | None:
    elite = (ceiling.get("elite_ids") or {}).get(preset)
    if class_name == "Worker":
        return elite if _count_ok(elite) else None
    expert = (ceiling.get("expert_ids") or {}).get(preset)
    if class_name == "Expert" and _count_ok(expert):
        if _count_ok(elite):
            return min(expert, elite)
        return expert
    return elite if _count_ok(elite) else None


def tighten_count(host_count: Any, shared: Any, limit: Any) -> Any:
    """Use a stated Delegator count when the Host omitted one.

    A stated Host count may fall. It does not rise. An omitted count on a
    shared label stays omitted, so the shared pool does not grow.
    """
    if not _count_ok(limit):
        return host_count
    if _count_ok(host_count):
        return min(host_count, limit)
    if isinstance(shared, str) and shared:
        return 0 if limit == 0 else host_count
    return limit


def _narrow_grant_extra(grant: dict[str, Any], ceiling: dict[str, Any],
                        catalog: dict[str, dict[str, Any]] | None) -> None:
    """Host extra seats may fall to the ceiling. They do not rise, and they do not survive a ceiling with no extra.

    The same map is written on every expanded row. An Expert grant count still
    clamps that preset: an elite extra the expert row does not cover is dropped.
    """
    extra = grant.get("extra_seats")
    if not isinstance(extra, dict) or not extra:
        return
    group = ceiling_group(ceiling, grant["id"])
    ceiling_extra = group.get("extra") if isinstance(group, dict) and isinstance(group.get("extra"), dict) else None
    if not ceiling_extra:
        grant.pop("extra_seats", None)
        grant.pop("shared_count", None)
        return
    shared_pool = group.get("count") if _count_ok(group.get("count")) else grant.get("shared_count")
    narrowed: dict[str, int] = {}
    for ident, value in extra.items():
        if not isinstance(ident, str) or not _count_ok(value) or value <= 0:
            continue
        cap = ceiling_extra.get(ident, 0)
        kept = min(value, cap) if _count_ok(cap) else 0
        if catalog is not None and _count_ok(shared_pool):
            klass = catalog.get(ident, {}).get("class")
            tier_cap = ceiling_count(ceiling, ident, klass) if isinstance(klass, str) else None
            if _count_ok(tier_cap):
                kept = min(kept, max(0, tier_cap - shared_pool))
        if kept > 0:
            narrowed[ident] = kept
    if not narrowed:
        grant.pop("extra_seats", None)
        grant.pop("shared_count", None)
        return
    grant["extra_seats"] = narrowed
    if _count_ok(grant.get("shared_count")) and _count_ok(shared_pool):
        grant["shared_count"] = min(grant["shared_count"], shared_pool)
    if _count_ok(grant.get("shared_count")):
        rebuilt = grant["shared_count"] + narrowed.get(grant["id"], 0)
        if _count_ok(grant.get("count")):
            grant["count"] = min(grant["count"], rebuilt)
        else:
            grant["count"] = rebuilt


def apply_ceiling_to_grants(grants: list[dict[str, Any]], ceiling: dict[str, Any],
                            catalog: dict[str, dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Copy current Delegator limits onto the Host grants used for this decision."""
    by_id = ceiling.get("by_id") or {}
    narrowed = []
    for grant in grants:
        grant = dict(grant)
        fact = by_id.get(grant["id"])
        if not fact or grant["id"] in (ceiling.get("problems") or {}):
            _narrow_grant_extra(grant, ceiling, catalog)
            narrowed.append(grant)
            continue
        new_count = tighten_count(grant.get("count"), grant.get("shared_seat"), fact.get("count"))
        if new_count is not None:
            grant["count"] = new_count
        _narrow_grant_extra(grant, ceiling, catalog)
        if fact.get("switch") is False:
            grant["model_switch"] = False
            grant["switch_authorization"] = False
        life = fact.get("lifetime")
        # Callers pass the catalog so an Expert lifetime is not copied onto an
        # Elite choice. The seat summary reads the same admission ceiling.
        if catalog is not None and catalog.get(grant["id"], {}).get("class") != "Expert":
            life = None
        if life in GRANT_LIFETIMES:
            host_life = grant.get("lifetime")
            if life == "task" and host_life in (None, "standing"):
                grant["lifetime"] = "task"
        special = fact.get("special")
        if isinstance(special, dict):
            host_special = grant.get("special_requirements")
            if not isinstance(host_special, dict):
                grant["special_requirements"] = dict(special)
            else:
                merged = dict(host_special)
                conflict = False
                for key, value in special.items():
                    if key in merged and merged[key] != value:
                        conflict = True
                        break
                    merged[key] = value
                if conflict:
                    ceiling.setdefault("problems", {})[grant["id"]] = "ceiling-incomplete"
                    ceiling.setdefault("problem_evidence", {})[grant["id"]] = {
                        "special_requirements": {"host": host_special, "delegator": special},
                    }
                else:
                    grant["special_requirements"] = merged
        narrowed.append(grant)
    return narrowed


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
    if "seat_cap" in plan:
        return fail("invalid-input", "plan.seat_cap is an obsolete independent limit. Host: reconcile its "
                    "original intent with the owner, then remove this key and retain exact grant counts. "
                    "Do not infer new authority or stop active work.")
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
    observations: list[dict[str, Any]] = []
    ceiling, ceiling_error = delegator_ceiling(repo, observations)
    if ceiling is not None:
        ceiling = admission_ceiling(ceiling)
        grants = apply_ceiling_to_grants(grants, ceiling, catalog)
        shared_capacities = shared_seat_capacities(grants)
        candidates, withheld = eligibility(catalog, auth, grants, available)
        kept_candidates = []
        for candidate in candidates:
            class_name = catalog[candidate["id"]]["class"]
            reason = ceiling_block(ceiling, candidate["id"], class_name, expert_grants=True)
            if reason:
                withheld.append({"id": candidate["id"], "reason": reason})
                continue
            limit = ceiling_count(ceiling, candidate["id"], class_name)
            if limit is not None:
                new_count = tighten_count(candidate.get("count"), candidate.get("shared_seat"), limit)
                if new_count != candidate.get("count"):
                    candidate = dict(candidate)
                    if new_count is not None:
                        candidate["count"] = new_count
            kept_candidates.append(candidate)
        candidates = kept_candidates
        by_candidate = {item["id"]: item for item in candidates}
        withheld_reason = {item["id"]: item["reason"] for item in withheld}

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
        if ceiling_error:
            blocked.append(blank_item(item["item_id"], preset, session, "not-run", "ceiling-unreadable",
                                      {"evidence": ceiling_error}))
            continue
        candidate = by_candidate.get(preset)
        if candidate is None:
            reason = "not-authorized"
            auth_grant = grant_index(grants).get(preset)
            if withheld_reason.get(preset) in CEILING_REASONS:
                reason = withheld_reason[preset]
            elif available.get(preset) == "absent":
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
            detail = ((ceiling or {}).get("problem_evidence", {}).get(preset)
                      or (ceiling or {}).get("expert_problem_evidence", {}).get(preset)
                      or (ceiling or {}).get("worker_problem" if row["class"] == "Worker" else "elite_problem"))
            extra = {"evidence": detail} if isinstance(detail, dict) else None
            blocked.append(blank_item(item["item_id"], preset, session, "not-run", reason, extra))
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
            "_owner_lifetime": (
                candidate.get("lifetime")
                if ceiling is not None
                and ((ceiling.get("by_id") or {}).get(preset) or {}).get("lifetime") in GRANT_LIFETIMES
                and isinstance(candidate.get("lifetime"), str)
                else None
            ),
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
    needs_live = any(
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
            reason = held_refusal(item, o_count, o_shared, o_unnamed, grants, catalog)
            if reason:
                if reason == "shared-occupied":
                    blocked.append(occupied_refusal(
                        item, refusal_presets(item, grants), others, resolved, ready, repo, binding))
                else:
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
        policy = tier_extra_policy(grants, item["preset"])
        if policy is not None:
            # The runtime total replaces the blunt shared-seat and ceiling-pool
            # checks. Those counts would refuse a legal extra seat or admit a
            # second shared-pool tier.
            platforms = {
                catalog[ident]["platform"] for ident in policy["ids"]
                if ident in catalog and isinstance(catalog[ident].get("platform"), str)
            }
            if item.get("_platform") in unnamed_platforms or unnamed_platforms & platforms:
                blocked.append(blank_item(
                    item["item_id"], item["preset"], item["session"], "not-run", "occupancy-unknown",
                ))
                continue
            limit_name = policy_blocks(
                policy, item["preset"], reserved_counts(used_count, kept_items, live_sessions))
            if limit_name:
                blocked.append(occupied_refusal(
                    item, set(policy["ids"]), live_rows, resolved, ready, repo, binding, limit_name))
                continue
        else:
            if (isinstance(seat_name, str) and seat_name
                    and occupied_shared.get(seat_name, 0) >= item.get("_shared_capacity", 1)):
                blocked.append(occupied_refusal(
                    item, refusal_presets(item, grants), live_rows, resolved, ready, repo, binding))
                continue
            if isinstance(seat_name, str) and seat_name and shared_seat_unknown(seat_name, grants, catalog, unnamed_platforms):
                blocked.append(blank_item(
                    item["item_id"], item["preset"], item["session"], "not-run", "occupancy-unknown",
                ))
                continue
            group = ceiling_group(ceiling, item["preset"])
            if group is not None:
                platforms = {
                    catalog[ident]["platform"] for ident in group["ids"]
                    if ident in catalog and isinstance(catalog[ident].get("platform"), str)
                }
                if occupancy != "known" or unnamed_platforms & platforms:
                    blocked.append(blank_item(
                        item["item_id"], item["preset"], item["session"], "not-run", "occupancy-unknown",
                    ))
                    continue
                occupied = sum(used_count.get(ident, 0) for ident in group["ids"])
                if occupied >= group["count"]:
                    blocked.append(occupied_refusal(
                        item, set(group["ids"]), live_rows, resolved, ready, repo, binding))
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
        if isinstance(limit, int):
            used_count[item["preset"]] = used_count.get(item["preset"], 0) + 1
        if isinstance(seat_name, str) and seat_name:
            occupied_shared[seat_name] = occupied_shared.get(seat_name, 0) + 1
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
        "items": [],
    }
    if observations:
        index["observations"] = observations
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
                    evidence = dict(chosen.get("evidence") or {})
                    if match:
                        evidence["blocked_attempt"] = {"reason": attempt}
                    if attempt in CEILING_DUTY and prior.get("status") in ("in-flight", "returned"):
                        if prior.get("status") == "returned" and prior.get("acceptance") == "accepted":
                            evidence["pending_duty"] = "finalize"
                        else:
                            evidence["pending_duty"] = CEILING_DUTY[attempt]
                    if evidence:
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


def seat_status_skills_root(script: Path, skills_root: Path | None) -> Path | None:
    """Find sibling platform status runners when a seat view omits --skills-root."""
    if skills_root is not None:
        return skills_root
    runner = acp_runner(script, None)
    roots = []
    if runner is not None:
        roots.append(runner.resolve().parents[2])
    roots.append(script.resolve().parent.parent / "skills")
    for root in roots:
        if root.is_dir() and any(root.glob("*-kaola-project-runner/scripts/runtime-tmux.sh")):
            return root
    return None


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


def tier_extra_policy(grants: list[dict[str, Any]], preset: str) -> dict[str, Any] | None:
    """Shared pool plus tier extras for this preset, or None when the grant has no extra."""
    grant = grant_index(grants).get(preset)
    if not grant or grant.get("state") != "granted":
        return None
    extra = _positive_extra(grant.get("extra_seats"))
    shared = grant.get("shared_count")
    seat = grant.get("shared_seat")
    if extra is None or not _count_ok(shared) or not isinstance(seat, str) or not seat:
        return None
    ids = {row["id"] for row in grants
           if row.get("state") == "granted" and row.get("shared_seat") == seat and isinstance(row.get("id"), str)}
    if not ids or not set(extra) <= ids:
        return None
    return {"ids": ids, "seat": seat, "shared_count": shared, "extra": extra,
            "total": shared + sum(extra.values())}


def reserved_counts(used_count: dict[str, int], kept: list[dict[str, Any]],
                    live_sessions: set[Any]) -> dict[str, int]:
    """Live occupancy plus kept plan rows that are not already a live seat.

    Fresh admits are already in used_count. Counting them again would shrink the pool.
    """
    counts = dict(used_count)
    for item in kept:
        if item.get("_exempt") or not isinstance(item.get("preset"), str):
            continue
        session = item.get("session")
        if isinstance(session, str) and session in live_sessions:
            continue
        preset = item["preset"]
        counts[preset] = counts.get(preset, 0) + 1
    return counts


def policy_blocks(policy: dict[str, Any], preset: str, used_count: dict[str, int]) -> str | None:
    """shared-pool when tier extras cannot cover the mix; runtime-total when the sum exceeds the cap."""
    proposed = {ident: used_count.get(ident, 0) for ident in policy["ids"]}
    proposed[preset] = proposed.get(preset, 0) + 1
    if sum(proposed.values()) > policy["total"]:
        return "runtime-total"
    demand = 0
    for ident, count in proposed.items():
        demand += max(0, count - policy["extra"].get(ident, 0))
    if demand > policy["shared_count"]:
        return "shared-pool"
    return None


def seat_grant_presets(seat: str, grants: list[dict[str, Any]]) -> set[str]:
    return {grant["id"] for grant in grants
            if grant.get("state") == "granted" and grant.get("shared_seat") == seat
            and isinstance(grant.get("id"), str)}


def refusal_presets(item: dict[str, Any], grants: list[dict[str, Any]]) -> set[str]:
    policy = tier_extra_policy(grants, item["preset"]) if isinstance(item.get("preset"), str) else None
    if policy is not None:
        return set(policy["ids"])
    seat = item.get("_shared_seat")
    presets = seat_grant_presets(seat, grants) if isinstance(seat, str) and seat else set()
    if not presets and isinstance(item.get("preset"), str):
        presets = {item["preset"]}
    return presets


def seat_occupants(presets: set[str], live_rows: list[dict[str, Any]], resolved: dict[str, str],
                   admitted: list[dict[str, Any]], repo: str,
                   exempt: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Live seats and already-admitted plan items in this group. holder_instance_id is null when unknown."""
    found: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(session: Any, holder: Any, preset: Any) -> None:
        if not isinstance(session, str) or not session or session in seen:
            return
        seen.add(session)
        found.append({
            "session": session,
            "holder_instance_id": holder if isinstance(holder, str) and holder else None,
            "preset": preset if isinstance(preset, str) and preset else None,
        })

    for row in live_rows:
        if row.get("state") == "stopped" or row.get("host_class") is True or binding_row(exempt, row):
            continue
        row_repo = row.get("repo")
        if isinstance(row_repo, str) and row_repo and not same_repo(row_repo, repo):
            continue
        session = row.get("session") if isinstance(row.get("session"), str) else None
        preset = row.get("preset") if isinstance(row.get("preset"), str) else None
        if preset is None and session:
            resolved_preset = resolved.get(session)
            preset = resolved_preset if isinstance(resolved_preset, str) else None
        if preset not in presets:
            continue
        add(session, row.get("holder_instance_id"), preset)
    for item in admitted:
        if item.get("_exempt") or item.get("preset") not in presets:
            continue
        holder = item.get("holder_instance_id") or item.get("expected_holder_instance_id") or item.get("_holder")
        add(item.get("session"), holder, item.get("preset"))
    return found


def occupied_refusal(item: dict[str, Any], presets: set[str], live_rows: list[dict[str, Any]],
                     resolved: dict[str, str], admitted: list[dict[str, Any]], repo: str,
                     exempt: dict[str, Any] | None = None, limit: str | None = None) -> dict[str, Any]:
    evidence: dict[str, Any] = {
        "occupants": seat_occupants(presets, live_rows, resolved, admitted, repo, exempt),
    }
    if isinstance(limit, str) and limit:
        evidence["limit"] = limit
    return blank_item(item["item_id"], item["preset"], item["session"], "not-run", "shared-occupied",
                      {"evidence": evidence})


def held_refusal(item: dict[str, Any], used_count: dict[str, int],
                 occupied: dict[str, int], unnamed: set[str],
                 grants: list[dict[str, Any]], catalog: dict[str, dict[str, Any]]) -> str | None:
    """The admission checks for a held seat, against every other live row."""
    preset = item.get("preset") if isinstance(item.get("preset"), str) else ""
    policy = tier_extra_policy(grants, preset)
    if policy is not None:
        if item.get("_platform") in unnamed:
            return "occupancy-unknown"
        if policy_blocks(policy, preset, used_count):
            return "shared-occupied"
    else:
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
    extra: dict[str, Any] = {
        "argv": {
            "status": launch_argv(item, repo, "status"),
            "start": launch_argv(item, repo, "start"),
            "send": launch_argv(item, repo, "send"),
        },
        "dry_run": dry_run,
    }
    if isinstance(item.get("_owner_lifetime"), str):
        extra["evidence"] = {"lifetime": item["_owner_lifetime"]}
    return blank_item(item["item_id"], item["preset"], item["session"], "not-run", reason, extra)


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


def host_view(doc: dict[str, Any], path: Path) -> dict[str, Any]:
    """Projected Host view from the shared contract, field by field."""
    view = RECORD.host_view(doc, path)
    try:
        catalog_paths = platform_paths(Path(__file__), None)
        catalog = catalog_from_files(catalog_paths)
        auth = doc["state"].get("authorization") or {}
        grants = normalize_grants(auth)
        availability_path = path.parent / "dispatch-availability.json"
        availability = availability_map(load_object(availability_path)) if availability_path.is_file() else {}
        candidates, withheld = current_candidates(catalog, auth, grants, availability, doc, str(repo_of_state_file(path)))
        view["capability"] = {**capability_summary(candidates),
                              "shared_seats": [{"seat": seat, "count": count} for seat, count in shared_seat_capacities(grants).items()],
                              "withheld": withheld,
                              "catalog_source": os.path.commonpath([str(p.parent) for p in catalog_paths]),
                              "catalog_sha256": hashlib.sha256(b"".join(p.read_bytes() for p in catalog_paths)).hexdigest()}
        unknown = sum(item.get("availability") == "unknown" for item in candidates)
        view["capability"]["text"] = f"availability unknown: {unknown} of {len(candidates)} eligible presets" if unknown else ""
        profiles = Path(__file__).resolve().parent.parent / "references" / "worker-profiles.md"
        if not profiles.is_file():
            profiles = Path(__file__).resolve().parent.parent / "templates" / "orchestrator" / "references" / "worker-profiles.md.tmpl"
        if profiles.is_file():
            definitions = {}
            for line in profiles.read_text().splitlines():
                match = re.match(r"\| \*\*(Elite|Expert|Worker)\*\* \| ([^|]+) \|", line)
                if match:
                    definitions[match[1]] = match[2].strip()
            view["catalog"] = {"source": str(profiles), "sha256": hashlib.sha256(profiles.read_bytes()).hexdigest(),
                               "classes": definitions}
    except (OSError, ValueError) as exc:
        view["capability"] = {"presets": [], "unknown": str(exc),
                              "next": "Host: plan migration and reconcile original grant authority; unknown is not empty authorization"}
    return view


# Write metadata and alert coalescing change on every repeat without
# changing what the Host is asked to judge.
DIGEST_SKIP = (*RECORD_META, "count", "last_seen", "ack")
# Field-set version inside a task's tool-kept `rejection` object.
# Heartbeat schema stays kaola-heartbeat-prompt/2. Do not bump it: a writer
# that sees /3 refuses the whole file. Absent count is unknown, never zero.
REJECTION_VERSION = 1
# Catalog profile effort is the authorization. Strength is only an explicit
# order the loaded platform catalog declares. Current manifests declare none.
# ACP configOptions order is presentation order and is not that declaration.


def judgment_digest(record: dict[str, Any]) -> str:
    """Short digest of what a Host judgment record asks, so the same id with a
    changed question, options, evidence or owner is new attention."""
    text = json.dumps({key: value for key, value in record.items() if key not in DIGEST_SKIP},
                      ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _positive_int(value: Any) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    return None


def _dispatch_ids(task: dict[str, Any] | None) -> set[str]:
    if not isinstance(task, dict):
        return set()
    raw = task.get("dispatch")
    if isinstance(raw, str) and raw:
        return {raw}
    if isinstance(raw, list):
        return {item for item in raw if isinstance(item, str) and item}
    return set()


def _owner_of(task: dict[str, Any]) -> str | None:
    """Responsible owner: preset or recorded owner. A session shell is not an owner."""
    preset = task.get("preset")
    if isinstance(preset, str) and preset.strip():
        return preset.strip()
    owner = task.get("owner")
    if isinstance(owner, str) and owner.strip():
        return owner.strip()
    rows = task.get("assignments")
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict):
                named = row.get("preset")
                if isinstance(named, str) and named.strip():
                    return named.strip()
    return None


def _submission_dispatch(patch: dict[str, Any]) -> str | None:
    dispositions = patch.get("dispositions")
    if not isinstance(dispositions, dict):
        return None
    repaired = [key for key, value in dispositions.items()
                if value == "repair" and isinstance(key, str) and key]
    if len(repaired) == 1:
        return repaired[0]
    return None


def _submission_receipt(patch: dict[str, Any]) -> str | None:
    if "evidence" not in patch:
        return None
    evidence = patch.get("evidence")
    if isinstance(evidence, str) and evidence.strip():
        return evidence.strip()
    if isinstance(evidence, list):
        rows = [item.strip() for item in evidence if isinstance(item, str) and item.strip()]
        if len(rows) == 1:
            return rows[0]
    return None


def _stored_rejection(current: dict[str, Any] | None) -> dict[str, Any]:
    raw = (current or {}).get("rejection")
    return dict(raw) if isinstance(raw, dict) else {}


def _granted_ids(authorization: dict[str, Any] | None) -> set[str]:
    """Preset ids whose grant state is granted. No second permission engine."""
    if not isinstance(authorization, dict) or not isinstance(authorization.get("grants"), list):
        return set()
    found: set[str] = set()
    for grant in authorization["grants"]:
        if not isinstance(grant, dict) or grant.get("state") not in (None, "granted"):
            continue
        ident = grant.get("id")
        if isinstance(ident, str) and ident.strip():
            found.add(ident.strip())
        presets = grant.get("preset_ids")
        if isinstance(presets, list):
            found.update(item.strip() for item in presets if isinstance(item, str) and item.strip())
    return found


def _owner_grant(authorization: dict[str, Any] | None, owner: str | None) -> dict[str, Any] | None:
    """The granted row that names this preset. No second grant lookup."""
    if not owner or not isinstance(authorization, dict) or not isinstance(authorization.get("grants"), list):
        return None
    for grant in authorization["grants"]:
        if not isinstance(grant, dict) or grant.get("state") not in (None, "granted"):
            continue
        ids = []
        if isinstance(grant.get("id"), str):
            ids.append(grant["id"])
        if isinstance(grant.get("preset_ids"), list):
            ids.extend(item for item in grant["preset_ids"] if isinstance(item, str))
        if owner in ids:
            return grant
    return None


def _profile_effort(row: dict[str, Any] | None) -> str | None:
    selection = row.get("selection") if isinstance(row, dict) else None
    effort = selection.get("effort") if isinstance(selection, dict) else None
    if isinstance(effort, str) and effort.strip():
        return effort.strip().lower()
    return None


def _platform_coverage(catalog: dict[str, Any], row: dict[str, Any]) -> set[str]:
    """Efforts the catalog already declares for this platform."""
    platform = row.get("platform")
    found: set[str] = set()
    for item in catalog.values():
        if not isinstance(item, dict) or item.get("platform") != platform:
            continue
        token = _profile_effort(item)
        if token:
            found.add(token)
    return found


def _effort_permitted(authorization: dict[str, Any] | None, owner: str | None, effort: str,
                      catalog: dict[str, Any] | None) -> bool:
    """The catalog profile effort is the authorization.

    ``special_requirements.effort``, when the owner supplied one, only restates
    that same already-covered effort. It does not authorize a token the
    profile does not name, and a seat is not required to carry one.
    """
    if not isinstance(catalog, dict):
        return False
    grant = _owner_grant(authorization, owner)
    row = catalog.get(owner) if isinstance(owner, str) else None
    profile = _profile_effort(row if isinstance(row, dict) else None)
    if grant is None or not isinstance(row, dict) or not profile or effort != profile:
        return False
    if effort not in _platform_coverage(catalog, row):
        return False
    special = grant.get("special_requirements")
    if not isinstance(special, dict) or "effort" not in special:
        return True
    required = special.get("effort")
    if not isinstance(required, str) or not required.strip():
        return False
    return required.strip().lower() == effort


def _applied_effort(requested: str, receipt: Any) -> str | None:
    """The effort token a real application receipt proves."""
    if not isinstance(receipt, dict):
        return None
    block, _source = application_of(receipt)
    slot, state = application_slot(block, "effort")
    verdict, value = effort_applied_verdict(requested, slot, state)
    if verdict != "match" or value is None:
        return None
    applied = str(value).strip().lower()
    if applied != requested.strip().lower():
        return None
    return applied


def _task_holders(task: dict[str, Any]) -> set[str]:
    found: set[str] = set()
    direct = task.get("holder_instance_id")
    if isinstance(direct, str) and direct.strip():
        found.add(direct.strip())
    for key in ("sessions", "assignments"):
        rows = task.get(key)
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            holder = row.get("holder_instance_id")
            if isinstance(holder, str) and holder.strip():
                found.add(holder.strip())
    return found


def _plain(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _holder_agrees(receipt_holder: str | None, other: Any) -> bool:
    """Both sides named a holder and they differ. A missing side is not a contradiction."""
    named = _plain(other)
    return not (receipt_holder and named and receipt_holder != named)


def _task_dispatch_rows(task: dict[str, Any], task_id: str | None,
                        index_items: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Index rows this task already names, by its dispatch ids or by a plan task_id."""
    if not isinstance(index_items, list):
        return []
    ids = _dispatch_ids(task)
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in index_items:
        item_id = _plain(row.get("item_id"))
        named_task = _plain(row.get("task_id"))
        if not ((item_id and item_id in ids) or (named_task and task_id and named_task == task_id)):
            continue
        key = item_id or named_task or ""
        if not key or key in seen:
            continue
        seen.add(key)
        rows.append(row)
    return rows


def _row_matches(row: dict[str, Any], item: str | None, session: str | None,
                 holder: str | None) -> bool:
    """The receipt's item id or session is this row, and a named holder agrees."""
    row_item = _plain(row.get("item_id"))
    row_session = _plain(row.get("session"))
    item_hit = bool(item and row_item == item)
    session_hit = bool(session and row_session == session)
    if not item_hit and not session_hit:
        return False
    if item and row_item and item != row_item:
        return False
    if session and row_session and session != row_session:
        return False
    return _holder_agrees(holder, row.get("holder_instance_id"))


def _receipt_binds(receipt: Any, task_id: str | None, task: dict[str, Any],
                   index_items: list[dict[str, Any]] | None = None) -> bool:
    """The receipt is this task's seat through a locator that already exists.

    A runner receipt carries ``session`` and ``holder_instance_id`` and does
    not carry ``task_id``. A canonical task stores dispatch item ids and does
    not store ``holder_instance_id``, ``sessions``, or ``assignments``. When
    both sides do name a task id or a holder, a different value does not bind.
    Otherwise the join is the dispatch item id on the task, the session the
    task itself names, or the session on a dispatch-index row for that item
    or for this task when the plan row already carries ``task_id``.
    """
    if not isinstance(receipt, dict) or not isinstance(task, dict) or not task_id:
        return False
    named_task = _plain(nested(receipt, "task_id"))
    if named_task and named_task != task_id:
        return False
    holder = _plain(holder_of(receipt))
    stored = _task_holders(task)
    if stored and holder and holder not in stored:
        return False
    if named_task == task_id and holder and holder in stored:
        return True
    item = _plain(nested(receipt, "item_id"))
    session = _plain(nested(receipt, "session"))
    rows = _task_dispatch_rows(task, task_id, index_items)
    if item and item in _dispatch_ids(task):
        linked = [row for row in rows if _plain(row.get("item_id")) == item]
        if not linked:
            return True
        return any(_row_matches(row, item, session, holder) for row in linked)
    for name, recorded in seat_entries(task):
        if session and session == name and _holder_agrees(holder, recorded):
            return True
    return any(_row_matches(row, item, session, holder) for row in rows)


def _declared_effort_order(catalog: dict[str, Any] | None, owner: str | None) -> list[str] | None:
    """The platform's explicit semantic effort order, or None when it declares none.

    ``catalog_from_files`` stores ``selection.effort`` as one token. That token
    is the authorized effort. The other presets on the platform are the coverage
    set, not a sequence. No loaded field is an ordered list of effort tokens.
    A string, including the empty string some manifests store, is not an order
    between two tokens. The receipt's ``configOptions`` sequence is not read.
    """
    if not isinstance(catalog, dict) or not isinstance(owner, str):
        return None
    row = catalog.get(owner)
    if not isinstance(row, dict):
        return None
    selection = row.get("selection")
    raw = selection.get("effort") if isinstance(selection, dict) else None
    # The only effort fact on the row. It does not rank this token against another.
    if isinstance(raw, str) or raw in (None, ""):
        return None
    return None


def _index_items(path: str, repo: str | None) -> list[dict[str, Any]] | None:
    """One read of the dispatch index this update was given. Unreadable is no proof."""
    try:
        index = load_object(Path(path))
    except (OSError, ValueError):
        return None
    if not isinstance(index, dict) or index.get("schema") != "kaola-dispatch-index/1":
        return None
    if isinstance(index.get("repo"), str) and repo and not same_repo(index.get("repo"), repo):
        return None
    rows = index.get("items")
    if not isinstance(rows, list):
        return None
    return [row for row in rows if isinstance(row, dict)]


def _row_is_owner(row: dict[str, Any] | None, task_id: str, owner: str) -> bool:
    return isinstance(row, dict) and row.get("task_id") == task_id and row.get("preset") == owner


def _row_taken_over(row: dict[str, Any] | None, task_id: str, owner: str) -> bool:
    """The new dispatch row is this task, this owner, and a seat that took it."""
    if not isinstance(row, dict):
        return False
    holder = row.get("holder_instance_id")
    session = row.get("session")
    return (row.get("task_id") == task_id and row.get("preset") == owner
            and row.get("status") in ("in-flight", "returned")
            and isinstance(holder, str) and bool(holder.strip())
            and isinstance(session, str) and bool(session.strip()))


def _handoff_resets(current: dict[str, Any] | None, merged: dict[str, Any],
                    authorization: dict[str, Any] | None, task_id: str | None,
                    index_items: list[dict[str, Any]] | None) -> bool:
    """One responsibility transition, proven from the dispatch index.

    ``state update`` does not guarantee an index. Without ``--index``, or when
    that file is not the dispatch index, the disposition, the new id, and the
    preset are three fields and do not reset. With the index, one read must
    show the handed-off item still belonging to the counted owner and the one
    new dispatch id in flight or returned for the new granted owner on this
    same task. Anything missing keeps the count and that owner.
    """
    if not task_id or not isinstance(index_items, list):
        return False
    old = (current or {}).get("dispositions") if isinstance((current or {}).get("dispositions"), dict) else {}
    new = merged.get("dispositions") if isinstance(merged.get("dispositions"), dict) else {}
    handed = [key for key, value in new.items()
              if value == "handed-off" and old.get(key) != "handed-off" and isinstance(key, str) and key]
    added = _dispatch_ids(merged) - _dispatch_ids(current)
    if len(handed) != 1 or len(added) != 1 or handed[0] not in _dispatch_ids(current):
        return False
    owner = _owner_of(merged)
    if not owner or owner not in _granted_ids(authorization):
        return False
    # The count belongs to rejection.owner. A preset rename alone does not
    # move it; the handoff may arrive in a later patch, so compare with the
    # owner the count still names.
    rejection = _stored_rejection(current)
    counted = rejection.get("owner")
    if not isinstance(counted, str) or not counted.strip():
        counted = _owner_of(current) if isinstance(current, dict) else None
    if not isinstance(counted, str) or not counted.strip() or owner == counted.strip():
        return False
    counted = counted.strip()
    rows: dict[str, dict[str, Any]] = {}
    for row in index_items:
        item_id = row.get("item_id")
        if isinstance(item_id, str) and item_id not in rows:
            rows[item_id] = row
    return (_row_is_owner(rows.get(handed[0]), task_id, counted)
            and _row_taken_over(rows.get(next(iter(added))), task_id, owner))


def _effort_action(patch: dict[str, Any], rejection: dict[str, Any], writer: str,
                   authorization: dict[str, Any] | None, task: dict[str, Any],
                   task_id: str | None, catalog: dict[str, Any] | None,
                   index_items: list[dict[str, Any]] | None = None) -> tuple[str | None, str | None]:
    """Record a proven applied effort. Raise only on an explicit higher order.

    A bare string is not a baseline. The receipt has to bind to this task,
    and ``effort_applied_verdict`` has to match. An older stored token without
    ``effort_applied`` is unproven: this receipt becomes the baseline and the
    count stays. A raise also needs the catalog profile effort and any owner
    effort constraint already inside that coverage. The two tokens reset the
    count only when the platform catalog declares an order that ranks the
    applied token strictly above the baseline. Advertised configOptions order
    is not that declaration. Otherwise the count and any pending duty stay.
    """
    if writer != "host" or not isinstance(patch.get("effort"), str):
        return None, None
    requested = patch["effort"].strip().lower()
    if not requested:
        return None, None
    receipt = patch.get("effort_receipt")
    applied = _applied_effort(requested, receipt)
    if applied is None or not _receipt_binds(receipt, task_id, task, index_items):
        return None, None
    previous = rejection.get("effort")
    previous_token = previous.strip().lower() if isinstance(previous, str) and previous.strip() else None
    if rejection.get("effort_applied") is not True or previous_token is None:
        return "record", applied
    if not _effort_permitted(authorization, _owner_of(task), applied, catalog):
        return None, None
    order = _declared_effort_order(catalog, _owner_of(task))
    if not order or previous_token not in order or applied not in order:
        return None, None
    if order.index(applied) <= order.index(previous_token):
        return None, None
    return "raise", applied


def _incoming_binding(task: dict[str, Any], previous: dict[str, Any], patch: dict[str, Any],
                      rejection: dict[str, Any]) -> dict[str, Any]:
    """Dispatch item, delivery receipt, and review cycle, or a missing element.

    One repair disposition names the dispatch item. When the patch names no
    disposition, the task's single existing dispatch id is that item. A review
    number in the patch is the cycle; otherwise the open slot is. A receipt
    has to be in this patch to count as a delivery. The stored receipt is only
    the identity of the same dispatch item when this patch omits evidence but
    still names another element. A repair that names none of the three is not
    a replay of the open slot.
    """
    if not any(key in patch for key in ("review", "evidence", "dispositions")):
        # Naming none of the three is a new repair with no binding. Filling the
        # open slot and the stored receipt here is what let a counted repair
        # replay itself and hide the new one.
        return {"dispatch": None, "receipt": None, "review": None,
                "missing": True, "receipt_from_store": False}
    missing = False
    if "review" in patch:
        review = _positive_int(patch.get("review"))
        missing = review is None
    else:
        review = _positive_int(rejection.get("open_review"))
        missing = review is None
    if "dispositions" in patch:
        dispatch = _submission_dispatch(patch)
        if not dispatch:
            missing = True
    else:
        ids = _dispatch_ids(task)
        dispatch = next(iter(ids)) if len(ids) == 1 else None
        if dispatch is None:
            missing = True
    receipt_from_store = False
    if "evidence" in patch:
        receipt = _submission_receipt(patch)
        if receipt is None:
            missing = True
    else:
        stored = previous.get("receipt")
        if (isinstance(stored, str) and stored.strip() and dispatch
                and dispatch == previous.get("dispatch")):
            receipt = stored.strip()
            receipt_from_store = True
        else:
            receipt = None
            missing = True
    return {"dispatch": dispatch, "receipt": receipt, "review": review,
            "missing": missing, "receipt_from_store": receipt_from_store}


def _submission_relation(rejection: dict[str, Any], incoming: dict[str, Any]) -> str:
    """`new`, `replay`, `late`, `conflict`, or `unknown`.

    `new` needs the dispatch item, the delivery receipt, and the review cycle
    together. The same dispatch and receipt do not increment when only the
    review number changes. A different delivery at an equal or older review is
    a conflict, not a silent late result. Unknown does not increment.
    """
    if incoming.get("missing"):
        return "unknown"
    dispatch, receipt, review = incoming.get("dispatch"), incoming.get("receipt"), incoming.get("review")
    if not dispatch or not receipt or not isinstance(review, int):
        return "unknown"
    stored_review = _positive_int(rejection.get("review"))
    same = (dispatch == rejection.get("dispatch") and receipt == rejection.get("receipt")
            and rejection.get("dispatch") and rejection.get("receipt"))
    if same:
        if stored_review is not None and review < stored_review:
            return "late"
        return "replay"
    if incoming.get("receipt_from_store"):
        return "unknown"
    if stored_review is None or review > stored_review:
        return "new"
    return "conflict"


def _keep_prior_repair(current: dict[str, Any] | None, merged: dict[str, Any]) -> None:
    old = current.get("verdict") if isinstance(current, dict) else None
    if isinstance(old, dict) and old.get("value") == "repair":
        merged["prior_verdict"] = {
            key: old[key] for key in ("value", "by", "host_turn", "why") if old.get(key) is not None
        }


def apply_task_rejection(current: dict[str, Any] | None, merged: dict[str, Any],
                         patch: dict[str, Any], writer: str,
                         authorization: dict[str, Any] | None = None,
                         task_id: str | None = None,
                         index_items: list[dict[str, Any]] | None = None,
                         catalog: dict[str, Any] | None = None) -> None:
    """Keep the current owner's repair count at the verdict transition.

    The binding is the dispatch item, the delivery receipt, and the review
    cycle together. A Host turn id is not that identity. `effort`, `review`,
    and `effort_receipt` are consumed and are not stored as task keys.

    Late and replay keep the stored binding. A new repair whose order cannot
    be determined, after a positive count, stays a pending-binding duty: the
    count and the old binding remain as a lower bound, and the new verdict is
    kept. The projection publishes that duty. A later complete binding of a
    new delivery increments once. An effort pair the platform does not rank,
    or a handoff this update cannot prove, leaves that duty and the count.
    """
    for key in ("review", "effort", "effort_receipt"):
        if key in patch:
            merged.pop(key, None)
    previous = _stored_rejection(current)
    rejection = dict(previous)
    entered = merged.get("stage") == "review" and (not current or current.get("stage") != "review")
    if entered:
        base = _positive_int(rejection.get("open_review")) or _positive_int(rejection.get("review")) or 0
        rejection["open_review"] = base + 1
    verdict = patch.get("verdict") if isinstance(patch.get("verdict"), dict) else None
    is_repair = bool(verdict and verdict.get("value") == "repair")
    effort_action, effort_token = _effort_action(
        patch, previous, writer, authorization, merged, task_id, catalog, index_items)
    resets = (_handoff_resets(current, merged, authorization, task_id, index_items)
              or effort_action == "raise")
    if resets:
        for key in ("count", "dispatch", "receipt", "review", "pending"):
            rejection.pop(key, None)
        if effort_action != "raise":
            rejection.pop("effort", None)
            rejection.pop("effort_applied", None)
        owner = _owner_of(merged)
        if owner:
            rejection["owner"] = owner
        else:
            rejection.pop("owner", None)
    if effort_action in ("record", "raise") and effort_token:
        rejection["effort"] = effort_token
        rejection["effort_applied"] = True
    incoming = _incoming_binding(merged, previous, patch, rejection) if is_repair else None
    # A segment reset drops the old binding first, so this repair is judged
    # against the new segment. Otherwise the comparison is the stored one.
    relation = _submission_relation(rejection if resets else previous, incoming) if incoming else None
    counted = _positive_int(previous.get("count"))
    if is_repair and relation in ("unknown", "conflict") and counted and not resets:
        kept = dict(rejection)
        for key in ("count", "dispatch", "receipt", "review"):
            if previous.get(key) is not None:
                kept[key] = previous[key]
            else:
                kept.pop(key, None)
        kept["pending"] = "binding"
        kept["v"] = REJECTION_VERSION
        merged["rejection"] = kept
        _keep_prior_repair(current, merged)
        return
    # A late older review of the same delivery keeps the current verdict and
    # the current count. A conflict or an unbound new repair does not: those
    # are the pending duty above. A segment reset still falls through.
    if relation == "late":
        if current and isinstance(current.get("verdict"), dict):
            merged["verdict"] = current["verdict"]
        elif "verdict" in patch:
            merged.pop("verdict", None)
        if current and isinstance(current.get("prior_verdict"), dict):
            merged["prior_verdict"] = current["prior_verdict"]
        elif not (current and "prior_verdict" in current):
            merged.pop("prior_verdict", None)
        restored = dict(previous)
        if entered:
            restored["open_review"] = rejection["open_review"]
        if restored:
            restored["v"] = REJECTION_VERSION
            merged["rejection"] = restored
        else:
            merged.pop("rejection", None)
        return
    if is_repair and incoming is not None and _submission_relation(rejection, incoming) == "new":
        count = _positive_int(rejection.get("count"))
        rejection["count"] = 1 if count is None else count + 1
        rejection["dispatch"] = incoming["dispatch"]
        rejection["receipt"] = incoming["receipt"]
        rejection["review"] = incoming["review"]
        rejection.pop("pending", None)
        open_review = _positive_int(rejection.get("open_review")) or 0
        if incoming["review"] > open_review:
            rejection["open_review"] = incoming["review"]
        if not (isinstance(rejection.get("owner"), str) and rejection.get("owner")):
            owner = _owner_of(merged)
            if owner:
                rejection["owner"] = owner
    if any(key in rejection for key in (
            "count", "open_review", "owner", "effort", "review", "dispatch", "receipt", "pending")):
        rejection["v"] = REJECTION_VERSION
        merged["rejection"] = rejection
    elif not previous:
        merged.pop("rejection", None)
    return merged


def maintenance_brief(state: dict[str, Any]) -> dict[str, Any]:
    """The last checkpoint identity and time beside current obligations, so
    a reader can see whether maintenance is progressing. No history."""
    maintenance = state.get("maintenance") if isinstance(state.get("maintenance"), dict) else {}
    brief = {key: maintenance[key] for key in ("last_verified", "acked_host_revision",
                                               "handled_host_revision", "recovery_seq", "recovery_input") if maintenance.get(key) is not None}
    last = maintenance.get("last_checkpoint")
    if isinstance(last, dict) and not last.get("verified"):
        brief["last_checkpoint"] = {key: last.get(key) for key in ("batch", "at", "verified")}
    return brief


def requirement_scope(title: str) -> str | None:
    title = title.strip().lower()
    for scope, names in USER_REQUIREMENT_HEADINGS.items():
        for name in names:
            if title == name or (title.startswith(name) and not title[len(name)].isalnum()):
                return scope
    return None


def requirement_lines(repo: Path) -> dict[str, Any]:
    """Derive both owner scopes from current AGENTS.md; never store them."""
    source = repo / "AGENTS.md"
    result: dict[str, Any] = {"source": str(source), "project": [], "delegator": []}
    try:
        lines = source.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {**result, "missing": "AGENTS.md is unreadable or absent"}
    start_marker, end_marker = USER_REQUIREMENT_MARKERS
    marked = (start_marker in lines and end_marker in lines
              and lines.index(start_marker) < lines.index(end_marker))
    # Unscoped legacy marker content and headings remain project requirements.
    scope = None
    depth = 0
    found = False
    pending_heading = None
    for line in lines:
        if marked and line == start_marker:
            scope, depth, found = "project", 0, True
            pending_heading = None
            continue
        if marked and line == end_marker:
            scope = pending_heading = None
            continue
        match = re.match(r"^(#+)\s+(.*?)\s*$", line)
        if match:
            selected = requirement_scope(match.group(2))
            if selected:
                scope, depth, found = selected, len(match.group(1)), True
                pending_heading = line.strip()
                continue
            elif scope and depth and len(match.group(1)) <= depth:
                scope = pending_heading = None
        if scope and line.strip():
            if pending_heading:
                result[scope].append(pending_heading)
                pending_heading = None
            result[scope].append(line.strip())
    if not found:
        result["missing"] = "no user requirements region in AGENTS.md"
    return result


def delegator_view(doc: dict[str, Any], path: Path, repo: Path) -> dict[str, Any]:
    """The report the Delegator gives at every inquiry, from the closed contract."""
    state = doc["state"]
    projected = RECORD.projected_state(state)
    tasks = projected.get("tasks") or {}

    def brief(task_id: str, task: dict[str, Any]) -> dict[str, Any]:
        shown = {"id": task_id, **{key: short(task.get(key)) for key in
                                   ("stage", "goal", "wait", "next", "resume_when")
                                   if task.get(key) is not None}}
        verdict = task.get("verdict") if isinstance(task.get("verdict"), dict) else None
        if verdict and isinstance(verdict.get("value"), str):
            shown["verdict"] = verdict["value"]
        projected = RECORD.rejection_projection(task, state.get("holds"), task_id)
        if projected:
            shown["rejection"] = projected
        return shown

    def rows(kind: str, fields: tuple[str, ...]) -> list[dict[str, Any]]:
        found = []
        for key, value in sorted((projected.get(kind) or {}).items()):
            if not isinstance(value, dict):
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
        "pending_host_changes": sorted(host_changes(doc, int(maintenance_brief(state).get(
            "handled_host_revision") or 0), int(doc.get("host_revision") or 0))),
    }


def render_state(doc: dict[str, Any], path: Path, *, unchecked_live: bool = False) -> tuple[str, dict[str, int]]:
    """Serialize with the projected Host view as `body`; enforce the carrier
    bounds instead of truncating any responsibility.

    ``unchecked_live`` is a migration that was not given ``--live``. Missing
    live rows are not an old holder, so the current file bound applies.
    ``carrier-limit`` remains when a supplied live holder does not prove
    ``heartbeat-state/2``."""
    blockers = RECORD.maintenance_blockers(doc["state"].get("maintenance"))
    if blockers:
        raise StateRefusal("invalid-maintenance", "repair the current duty from original receipts", blocked=blockers)
    # The injected/stored body is the shared contract projection, the same one a
    # holder recomputes at read time (kaola-acp-holder.read_heartbeat_file ->
    # RECORD.injection_body). The catalog-enriched capability stays on demand via
    # `state view --role host`, so no catalog section is forced into the heartbeat.
    view = RECORD.host_view(doc, path)
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


@functools.lru_cache(maxsize=None)
def record_directory(platform: str, session: str, repo: str) -> Path:
    return RECORD.record_directory(platform, session, repo)


def carrier_replaced_by_older(carrier: dict[str, Any], path: Path) -> bool:
    """Whether the recorded carrier's Host session now runs another holder
    that does not advertise the state capability: that Host reads only the
    legacy bound. Unknown (no platform recorded, no record) keeps the
    recorded carrier; `state check --live` reports it."""
    platform, session = carrier.get("platform"), carrier.get("session")
    if not isinstance(platform, str) or not isinstance(session, str):
        return False
    try:
        record = json.loads(
            (record_directory(platform, session, str(repo_of_state_file(path))) / "record.json")
            .read_text(encoding="utf-8"))
    except (OSError, ValueError, RECORD.acp_paths.RecordRootMismatch):
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
    try:
        record = json.loads(
            (record_directory(caller["platform"], caller["session"], caller["repo"])
             / "record.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, RECORD.acp_paths.RecordRootMismatch):
        return None
    if not isinstance(record, dict) or record.get("holder_instance_id") != caller["holder_instance_id"]:
        return None
    role = record.get("session_role")
    return role if isinstance(role, str) and role else None


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
        if key in record and not (isinstance(record[key], str) or (
                isinstance(record[key], list) and all(isinstance(ref, str) for ref in record[key]))):
            return f"{key} must be a reference string or a list of references"
    return None


def record_recovery(args: argparse.Namespace, doc: dict[str, Any], current: dict[str, Any] | None) -> str:
    """Name the existing operation. The Agent decides whether the duty is handled."""
    target = f"{args.kind}/{args.id}"
    if current is None:
        text = (f"{target} is absent at file revision {doc['revision']}. Do not create a handled or "
                "inapplicable row or move its text to another field. ")
        if args.kind == "decisions":
            # An owner closure that was never written as a decision row has no
            # current record to retire. The Host records that with --absent.
            command = shlex.join([sys.executable, str(Path(__file__).resolve()), "state", "retire",
                                  "--file", str(args.file), "--writer", "host", "--source", "ORIGINAL_SOURCE",
                                  "--kind", "decisions", "--id", args.id, "--absent",
                                  "--evidence", "ORIGINAL_OWNER_EVIDENCE"])
            text += ("An owner closure that never had a decision row is recorded by the Host "
                     f"with: {command}. That returns a receipt and stores no row. ")
        text += ("If the matter is unresolved, retain its original evidence and use the current "
                 "decision/reconciliation route until its proper type is established. "
                 "Unknown is not resolved.")
        return text
    command = shlex.join([sys.executable, str(Path(__file__).resolve()), "state", "retire",
                          "--file", str(args.file), "--writer", args.writer, "--source", "ORIGINAL_SOURCE",
                          "--kind", args.kind, "--id", args.id, "--expect-rev", str(current.get('rev')),
                          "--evidence", "ORIGINAL_HANDLED_EVIDENCE"])
    return (f"{target} exists at record revision {current.get('rev')}, file revision {doc['revision']}. "
            f"If handled, remove it with: {command}. Use original evidence that ends this duty. "
            "Run `state migrate` for known legacy mappings and read its removed list. "
            "Tasks require the Host verdict and closed dispatch/reclaim links; accepted tasks also "
            "require --cite. Decisions require owner settlement. Do not move settled text to another "
            "field. If unresolved, keep the original evidence and use the current decision/reconciliation "
            "route until its proper type is established.")


STOP_DUTIES = ("stop-unconfirmed", "old-node-live")
RETURNED_SUMMARY = re.compile(r"\d+ maintenance input\(s\) not applied by a node")


def input_settlement_problem(state: dict[str, Any], inputs: dict[str, Any], ident: str,
                             evidence: Any) -> str | None:
    """Why the named evidence does not prove one returned input handled.

    The proof is the recorded node checkpoint: it settled this exact input,
    or it is verified, its range reaches the failed batch's Host revision and
    no returned Host change at or below that revision is still open. A
    recovery-only checkpoint selects no new business range, so it cannot
    reach an unsent one. A stop duty is proven by the exact stop, never here."""
    item = inputs.get(ident)
    if isinstance(item, dict) and item.get("why") in STOP_DUTIES:
        return (f"{ident} is a stop duty ({item['why']}); only the exact stop of the original node "
                "holder ends it, not a checkpoint")
    batch = evidence[len("checkpoint:"):] if isinstance(evidence, str) and evidence.startswith("checkpoint:") else ""
    maintenance = state.get("maintenance") if isinstance(state.get("maintenance"), dict) else {}
    last = maintenance.get("last_checkpoint") if isinstance(maintenance.get("last_checkpoint"), dict) else {}
    if not batch:
        return "--evidence must name the recorded node checkpoint as checkpoint:BATCH"
    if last.get("batch") != batch:
        return f"checkpoint:{batch} is not the recorded node checkpoint"
    if ident in (last.get("settled") or []):
        return None
    failed = item.get("host_revision_through") if isinstance(item, dict) else None
    covered = (last.get("host_revision") or {}).get("through")
    if (ident.startswith("batch:") and isinstance(failed, int) and not isinstance(failed, bool)
            and last.get("verified") is True and isinstance(covered, int) and failed <= covered):
        open_changes = sorted(other for other in inputs
                              if (revision_of(other) or failed + 1) <= failed)
        if not open_changes:
            return None
        return (f"returned Host change(s) {', '.join(open_changes)} at or below revision {failed} "
                f"are still open, so checkpoint:{batch} does not prove {ident} handled")
    return (f"checkpoint:{batch} did not settle {ident}"
            + (f" or verify its Host revision range through {failed}" if failed is not None else ""))


def settle_recovery(args: argparse.Namespace, doc: dict[str, Any], current: dict[str, Any],
                    ident: str) -> str:
    """The exact per-input removal, and how to reach its proof."""
    state = doc["state"]
    maintenance = state.get("maintenance") if isinstance(state.get("maintenance"), dict) else {}
    last = maintenance.get("last_checkpoint") if isinstance(maintenance.get("last_checkpoint"), dict) else {}
    span = last.get("host_revision") or {}
    command = shlex.join([sys.executable, str(Path(__file__).resolve()), "state", "update",
                          "--file", str(args.file), "--writer", args.writer, "--source", "ORIGINAL_SOURCE",
                          "--kind", "alerts", "--id", args.id, "--expect-rev", str(current.get("rev")),
                          "--evidence", f"checkpoint:{last.get('batch') or 'BATCH'}",
                          "--set", json.dumps({"inputs": {ident: None}})])
    others = len((current.get("inputs") or {})) - 1
    return (f"alerts/{args.id} is at record revision {current.get('rev')}. Recorded node checkpoint: "
            f"{last.get('batch') or 'none'} (verified {last.get('verified')}, Host revisions "
            f"{span.get('from')}..{span.get('through')}). "
            f"When that checkpoint settled {ident} or verified its failed range, remove only this input with: "
            f"{command}. Otherwise keep it: reconcile the original node and stop receipts, then request a "
            "bounded check with `state recovery-input --kind request`; that batch also carries pending Host "
            "business changes. A stop duty stays until the exact stop is confirmed. Do not retire the whole "
            f"alert while {others} other input(s) remain, rewrite a failed range, or write a fake business change.")


def settle_inputs(args: argparse.Namespace, doc: dict[str, Any], current: dict[str, Any] | None,
                  patch: dict[str, Any], caller: dict[str, str] | None) -> dict[str, Any]:
    """Remove handled returned inputs one by one. Each removal names the
    original proof; unrelated inputs and the alert's other facts stay."""
    removals = [ident for ident, value in patch["inputs"].items() if value is None]
    if set(patch) != {"inputs"} or len(removals) != len(patch["inputs"]):
        raise StateRefusal("invalid-input", "an input removal patch is only {\"inputs\":{\"ID\":null}}; "
                           "send other changes separately. The file was not changed",
                           path=f"alerts.{args.id}.inputs", allowed="inputs with null values", unapplied=patch)
    if current is None:
        raise StateRefusal("record-missing", f"alerts/{args.id} is not current",
                           recovery=record_recovery(args, doc, current), unapplied=patch)
    if args.expect_rev != current.get("rev"):
        raise StateRefusal("expect-rev-required" if args.expect_rev is None else "conflict",
                           f"alerts/{args.id} is at rev {current.get('rev')}, not {args.expect_rev}",
                           recovery=settle_recovery(args, doc, current, removals[0]), unapplied=patch)
    inputs = current.get("inputs") if isinstance(current.get("inputs"), dict) else {}
    for ident in removals:
        if ident not in inputs:
            raise StateRefusal(
                "input-missing", f"alerts.{args.id}.inputs.{ident} is not a current input",
                path=f"alerts.{args.id}.inputs.{ident}", allowed=", ".join(sorted(inputs)) or "none",
                recovery=(f"Current inputs at record revision {current.get('rev')}: "
                          f"{', '.join(sorted(inputs)) or 'none'}. Remove only a current input id, verbatim. "
                          "Do not create a handled row or move its text to another field."),
                unapplied=patch)
        problem = input_settlement_problem(doc["state"], inputs, ident, getattr(args, "evidence", None))
        if problem:
            raise StateRefusal("input-unproven", problem, path=f"alerts.{args.id}.inputs.{ident}",
                               recovery=settle_recovery(args, doc, current, ident), unapplied=patch)
    remaining = {ident: row for ident, row in inputs.items() if ident not in removals}
    records = doc["state"]["alerts"]
    if args.id == "maintenance-returned" and not remaining:
        # The returned alert is its inputs, as when a checkpoint settles the last one.
        del records[args.id]
        return {"kind": "alerts", "id": args.id, "removed": True, "settled_inputs": removals,
                "evidence": args.evidence}
    merged = {key: value for key, value in current.items() if key != "inputs"}
    if remaining:
        merged["inputs"] = remaining
    # Pointers only a removed input named leave with it; no settled copy stays.
    kept = {ref for row in remaining.values() if isinstance(row, dict)
            for ref in (row.get("evidence"), f"checkpoint:{row.get('batch')}") if ref}
    gone = {ref for ident in removals if isinstance(inputs[ident], dict)
            for ref in (inputs[ident].get("evidence"), f"checkpoint:{inputs[ident].get('batch')}") if ref}
    if isinstance(merged.get("evidence"), list):
        merged["evidence"] = [ref for ref in merged["evidence"] if ref not in gone - kept]
        if not merged["evidence"]:
            merged.pop("evidence")
    if isinstance(merged.get("summary"), str) and RETURNED_SUMMARY.match(merged["summary"]):
        merged["summary"] = RETURNED_SUMMARY.sub(f"{len(remaining)} maintenance input(s) not applied by a node",
                                                 merged["summary"], count=1)
    merged["rev"] = int(current.get("rev") or 0) + 1
    merged["updated_at"] = observed_at()
    merged["source"] = args.source
    merged["writer"] = writer_trace(args, caller)
    stamp_writer(doc, merged, args, caller)
    records[args.id] = merged
    return {**merged, "settled_inputs": removals}


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
    records = state.setdefault(kind, {})
    current = records.get(record_id)
    if kind == "decisions" and patch.get("status") == "settled" and current is None:
        raise StateRefusal("record-missing", "settlement removes an existing decision; it creates no row",
                           recovery=record_recovery(args, doc, current), unapplied=patch)
    if (kind == "alerts" and isinstance(patch.get("inputs"), dict)
            and any(value is None for value in patch["inputs"].values())):
        return settle_inputs(args, doc, current, patch, caller)
    rejected = RECORD.reject_record_patch(kind, patch)
    if rejected:
        rejected["path"] = f"{kind}.{record_id}.{rejected['path'].removeprefix(kind + '.')}"
        rejected["recovery"] = record_recovery(args, doc, current)
        raise StateRefusal("invalid-input", rejected["detail"], **{
            key: rejected[key] for key in ("path", "allowed", "recovery")
        }, unapplied=patch)
    stones = [stone for stone in state.get("retired") or []
              if isinstance(stone, dict) and stone.get("kind") == kind and stone.get("id") == record_id
              and (stone.get("seats") or stone.get("dispatch")) and not stone.get("handed_to")]
    if current is None and stones:
        raise StateRefusal(
            "record-retired",
            f"{kind}/{record_id} still has a pending reclaim. A new duty uses a new id. "
            "The file was not changed.",
            unapplied=patch,
        )
    if current is None and args.expect_rev not in (None, 0):
        raise StateRefusal(
            "record-retired",
            f"{kind}/{record_id} is not current. An old revision does not restore it. The file was not changed.",
            recovery=record_recovery(args, doc, current),
            unapplied=patch,
        )
    if "prior_verdict" in patch:
        raise StateRefusal("invalid-input", "prior_verdict is kept by the tool", unapplied=patch)
    if "rejection" in patch:
        raise StateRefusal("invalid-input", "rejection is kept by the tool", unapplied=patch)
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
    if kind == "tasks" and "verdict" in patch and patch["verdict"] is None:
        raise StateRefusal(
            "invalid-input", "verdict must be an authoritative verdict object",
            path=f"tasks.{record_id}.verdict", allowed=", ".join(VERDICTS),
            recovery="keep the verdict or set a valid verdict object. Use `state migrate` for legacy note text. "
                     "The file was not changed.", unapplied=patch,
        )
    merged = merge_patch(current or {}, patch)
    if (kind == "tasks" and isinstance(patch.get("verdict"), dict)
            and patch["verdict"].get("value") != "repair"):
        # An explicit final/terminal verdict replaces the prior review verdict.
        # A repair keeps it: #267 counts rounds of the same obligation and the
        # earlier repair stays its prior. Refuse invalid new verdicts below.
        merged.pop("prior_verdict", None)
    if kind == "tasks" and isinstance(patch.get("dispatch"), list):
        merged["dispatch"] = RECORD.union_dispatch((current or {}).get("dispatch"), patch.get("dispatch"))
    if current is None:
        missing = [key for key in REQUIRED_ON_CREATE[kind] if merged.get(key) in (None, "")]
        if missing:
            raise StateRefusal("invalid-input", f"a new {kind} record needs {', '.join(missing)}")
        merged["created_at"] = observed_at()
    if kind == "tasks":
        # #267 patch-only inputs consumed by apply_task_rejection below:
        # never stored, never refused as unknown record keys.
        merged.pop("effort", None)
        merged.pop("review", None)
        merged.pop("effort_receipt", None)
    unknown = RECORD.unknown_record_keys(kind, merged)
    if unknown:
        raise StateRefusal(
            "invalid-input",
            f"{kind}.{record_id}.{unknown[0]} is not a current field.",
            path=f"{kind}.{record_id}.{unknown[0]}",
            allowed=", ".join(sorted(RECORD.RECORD_KEYS[kind])),
            recovery=record_recovery(args, doc, current),
            unapplied=patch,
        )
    typed = RECORD.record_type_problem(kind, merged)
    if typed:
        raise StateRefusal("invalid-input", typed["detail"], path=typed["path"],
                           allowed=typed["allowed"], recovery=record_recovery(args, doc, current), unapplied=patch)
    problem = validate_record(kind, merged)
    if problem:
        raise StateRefusal("invalid-input", problem, recovery=record_recovery(args, doc, current), unapplied=patch)
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
        # The copied answer is a current Host adoption duty, not a settled row.
        merged["status"] = "pending"
        merged["transcribed"] = {"host_turn": args.host_turn, "fields": ["status"]}
    elif kind == "decisions" and args.writer == "host":
        merged.pop("transcribed", None)
        if patch.get("status") == "settled":
            if current is None or merged.get("evidence") in (None, "", []):
                raise StateRefusal("evidence-required", "settlement removes an existing decision and "
                                   "names the original evidence of its owner's answer",
                                   recovery=record_recovery(args, doc, current), unapplied=patch)
            del records[record_id]
            return {"kind": kind, "id": record_id, "removed": True}
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
    if kind == "tasks":
        catalog = None
        if isinstance(patch.get("effort"), str):
            try:
                catalog = catalog_from_files(platform_paths(Path(__file__), None))
            except (OSError, ValueError):
                catalog = None
        index_items = None
        index_path = getattr(args, "index", None)
        # Handoff proof and an effort receipt both read this one index. An
        # effort patch carries no disposition, so the load cannot be limited
        # to those keys or the receipt can never see the dispatch row.
        if index_path and any(key in patch for key in ("dispositions", "dispatch", "preset", "effort")):
            index_items = _index_items(str(index_path), str(repo_of_state_file(Path(args.file))))
        apply_task_rejection(
            current if isinstance(current, dict) else None, merged, patch, args.writer,
            state.get("authorization") if isinstance(state.get("authorization"), dict) else None,
            record_id, index_items, catalog)
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
            blocked = []
            if patch and all(value is None for value in patch.values()) and set(patch) <= {"elite_cap", "total_cap", "worker_pool_cap"}:
                merged_section, blocked, args._authorization_removed = RECORD.migrate_authorization_limits(merged_section)
                if not blocked:
                    had_revoked = "revoked" in merged_section
                    merged_section = current_authorization(merged_section)
                    if had_revoked:
                        args._authorization_removed.append("authorization.revoked -> current grants/exclusions")
            blocked += RECORD.authorization_blockers(merged_section)
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
    state[section] = merged_section if section in ("project", "authorization", "recovery", "unverified") else merge_patch(state.get(section) or {}, patch)
    if section == "authorization":
        state[section] = current_authorization(state[section])
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


def index_identity_problem(index: dict[str, Any], repo: str) -> str | None:
    """Issue #286 (G5): retire and its index mirror read only this project's
    dispatch index, identified the way every index execute and collect write
    identifies itself: kaola-dispatch-index/1 for this project's repo. A
    missing, wrong, or foreign identity proves no closure."""
    declared = index.get("schema")
    if declared != "kaola-dispatch-index/1":
        if declared is None:
            return "declares no schema, not kaola-dispatch-index/1"
        return f"declares schema {declared!r}, not kaola-dispatch-index/1"
    seen = index.get("repo")
    if not isinstance(seen, str) or not seen:
        return "declares no repo, not this project's index"
    if not same_repo(seen, repo):
        return f"declares repo {seen!r}, not this project"
    return None


def supplied_index_paths(args: argparse.Namespace) -> list[str]:
    """Every --index this command holds, in order (Issue #290).

    A task's items can be dispatched by more than one execute run, each
    writing its own kaola-dispatch-index/1. `state retire` therefore accepts a
    repeatable --index; every other command still supplies at most one.
    """
    raw = getattr(args, "index", None)
    if raw is None:
        return []
    values = raw if isinstance(raw, list) else [raw]
    return [item for item in values if isinstance(item, str) and item]


def open_dispatch(task: dict[str, Any], args: argparse.Namespace) -> list[str]:
    """Why a task's dispatched items are not shown closed: each needs an index
    row that is no longer in flight and stopped seats. A Host can reconcile
    an initial fingerprint against its accepted same-holder continuation;
    this does not change the original unknown collect result.

    Issue #290: the closure proof may span several of this project's index
    files. Every supplied file still identifies itself as this project's
    kaola-dispatch-index/1, and every dispatch ref must be found in exactly
    one of them."""
    refs = task.get("dispatch")
    refs = [refs] if isinstance(refs, str) else [ref for ref in refs or [] if isinstance(ref, str)]
    seats = task_seats(task)
    if not refs and not seats:
        return []
    problems: list[str] = []
    indices = supplied_index_paths(args)
    if refs and (not indices or not getattr(args, "live", None)):
        problems.append(f"dispatch {', '.join(refs)} needs --index and --live to show it closed and stopped")
    if seats and not getattr(args, "live", None):
        problems.append(f"seat {', '.join(sorted(seats))} needs --live to show it stopped, or "
                        "--handoff to the current task that continues it")
    if problems:
        return problems
    live = live_rows_of(args.live) or []
    if refs:
        repo = str(repo_of_state_file(Path(args.file)))
        rows: dict[str, dict[str, Any]] = {}
        row_index: dict[str, str] = {}
        ambiguous: set[str] = set()
        for index_path in indices:
            index = load_object(Path(index_path))
            mismatch = index_identity_problem(index, repo)
            if mismatch:
                raise StateRefusal(
                    "index-unidentified",
                    f"the index at {index_path} {mismatch}; retire proves closure only from this "
                    "project's dispatch index",
                    recovery="pass --index pointing at this project's kaola-dispatch-index/1, the "
                             "file execute and collect write here")
            for index_row in index.get("items") or []:
                if not isinstance(index_row, dict):
                    continue
                item_id = index_row.get("item_id")
                if not isinstance(item_id, str):
                    continue
                if item_id in row_index and row_index[item_id] != index_path:
                    # Issue #290: a ref in two supplied indices is not in
                    # exactly one, so the pair proves no single closure.
                    ambiguous.add(item_id)
                row_index[item_id] = index_path
                rows[item_id] = index_row
        for ref in refs:
            row = rows.get(ref)
            if row is None:
                problems.append(f"{ref} is not in the index")
                continue
            if ref in ambiguous:
                problems.append(f"{ref} is in more than one supplied index; closure needs exactly "
                                "one --index file to show it closed")
                continue
            status = row.get("status")
            if status in CLOSED_COVERAGE:
                continue
            if status not in ("in-flight", "unknown"):
                # Issue #286 (G6): one allow-list shared with the mirror. A
                # status this vocabulary does not know is still a duty; a
                # missing or renamed value never proves closure.
                problems.append(f"{ref} status {status!r} is not a known closed value")
                continue
            evidence_rows = row.get("evidence") if isinstance(row.get("evidence"), dict) else {}
            collected = evidence_rows.get("collect_status")
            collected = collected if isinstance(collected, dict) else {}
            holder, session = row.get("holder_instance_id"), session_name(row.get("session"))
            verdict = task.get("verdict") or {}
            # The Host owns the result judgment. Mechanical proof is limited
            # to this known initial-fingerprint discrepancy and exact reclaim.
            reconciled = (
                args.writer == "host" and task.get("stage") == "done"
                and verdict.get("value") == "accepted"
                and (task.get("dispositions") or {}).get(ref) == "accepted"
                and row.get("task_id") == args.id
                and row.get("status") == "unknown" and row.get("reason") == "fingerprint-differs"
                and isinstance(holder, str) and bool(holder) and session is not None
                and collected.get("holder_instance_id") == holder
                and collected.get("mutation_status") == "completed" and collected.get("outcome") == "stopped"
                and isinstance(collected.get("repo"), str) and bool(collected.get("repo"))
                and isinstance(row.get("repo"), str) and bool(row.get("repo"))
                and same_repo(collected.get("repo"), row.get("repo"))
                and same_repo(row.get("repo"), repo)
                and any(live_row.get("session") == session
                        and live_row.get("holder_instance_id") == holder
                        and live_row.get("platform") == row.get("platform")
                        and isinstance(live_row.get("repo"), str) and bool(live_row.get("repo"))
                        and same_repo(live_row.get("repo"), row.get("repo")) for live_row in live)
                and not open_seats({session: [holder]}, live))
            if reconciled:
                args._reconciled_dispatch = getattr(args, "_reconciled_dispatch", []) + [
                    {"item_id": ref, "session": session, "holder_instance_id": holder,
                     "collect_status": "unknown", "reason": "fingerprint-differs",
                     "disposition": "accepted"}]
            else:
                problems.append(f"{ref} is {row.get('status')}")
        sessions = {rows[ref].get("session") for ref in refs
                    if ref in rows and ref not in ambiguous} - set(seats)
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


def retire_absent_decision(args: argparse.Namespace, doc: dict[str, Any]) -> dict[str, Any]:
    """Host receipt for a decision id that was never a row.

    The file stores no row, stone, or tombstone. ``state_mutation`` has already
    raised ``host_revision`` for this Host write; that revision is the cite.
    """
    kind, record_id = args.kind, args.id
    if kind != "decisions":
        raise StateRefusal("invalid-input", "--absent applies only to decisions",
                           recovery="retire a current hold, alert, or task without --absent")
    if args.writer != "host":
        raise StateRefusal("host-only", "--absent is a Host write",
                           recovery="the Host runs state retire --kind decisions --id ID --absent "
                                    "--evidence ORIGINAL_OWNER_EVIDENCE")
    if not isinstance(record_id, str) or not re.fullmatch(r"[A-Za-z0-9#][A-Za-z0-9_.:#/-]{0,79}", record_id):
        raise StateRefusal("invalid-input", "id must be a stable short identifier")
    current = doc["state"].get(kind, {}).get(record_id)
    if current is not None:
        raise StateRefusal("invalid-input", f"decisions/{record_id} is current; --absent records only an id "
                           "with no decision row", current=current, recovery=record_recovery(args, doc, current))
    extras = [flag for flag, present in (
        ("--expect-rev", args.expect_rev is not None),
        ("--handoff", bool(getattr(args, "handoff", None))),
        ("--cite", bool(getattr(args, "cite", None))),
        ("--index", bool(getattr(args, "index", None))),
        ("--live", bool(getattr(args, "live", None))),
    ) if present]
    if extras:
        raise StateRefusal("invalid-input", "--absent takes --evidence and optional --outcome only",
                           recovery="omit " + ", ".join(extras))
    if not args.evidence:
        raise StateRefusal("evidence-required", "retirement names the evidence that ends the duty",
                           recovery=record_recovery(args, doc, None))
    return {"kind": "decisions", "id": record_id, "outcome": args.outcome or "resolved",
            "absent_at_retire": True, "evidence": args.evidence, "at": observed_at(),
            "host_revision": doc["host_revision"]}


def retire_record(args: argparse.Namespace, doc: dict[str, Any]) -> dict[str, Any]:
    state = doc["state"]
    kind, record_id = args.kind, args.id
    if kind not in RECORD_KINDS:
        raise StateRefusal("invalid-input", f"kind must be one of {', '.join(RECORD_KINDS)}")
    if getattr(args, "absent", False):
        return retire_absent_decision(args, doc)
    current = state.get(kind, {}).get(record_id)
    if current is None:
        raise StateRefusal("record-missing", f"{kind}/{record_id} is not current",
                           recovery=record_recovery(args, doc, current))
    if args.expect_rev is None:
        raise StateRefusal("expect-rev-required", "retire needs --expect-rev of the current record")
    if args.expect_rev != current.get("rev"):
        raise StateRefusal("conflict", f"{kind}/{record_id} is at rev {current.get('rev')}, not "
                           f"{args.expect_rev}", current=current)
    if not args.evidence:
        raise StateRefusal("evidence-required", "retirement names the evidence that ends the duty",
                           recovery=record_recovery(args, doc, current))
    recovery = (state.get("maintenance") or {}).get("recovery_input") or {}
    if kind == "alerts" and f"recovery#{recovery.get('seq')}" in (current.get("inputs") or {}):
        raise StateRefusal("retire-unmet", "this alert still names the current pending recovery input; "
                           "bind and checkpoint that exact input first", current=current,
                           recovery=record_recovery(args, doc, current))
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
    if kind == "decisions" and current.get("status") != "settled" and args.writer != "host":
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
             **({"reconciled_dispatch": args._reconciled_dispatch}
                if getattr(args, "_reconciled_dispatch", None) else {}),
             **({"cite": cite} if cite else {}),
             **({"handed_to": handoff, **handed} if handoff else {})}
    stamp_writer(doc, stone, args, caller_dispatcher())
    if kind == "tasks":
        # Keep the original Host verdict for this operation's index mirror.
        # This is transient command data, never a retired registry.
        args._retired_task = json.loads(json.dumps(current))
    del state[kind][record_id]
    # The command result carries the cite. The file does not keep a settled row.
    # Seats handed to another task stay on that task. A stone stays only when
    # it still names seats or dispatch and names no receiver.
    kept = []
    for old in state.get("retired") or []:
        if not isinstance(old, dict):
            continue
        if old.get("kind") == kind and old.get("id") == record_id:
            continue
        if (old.get("seats") or old.get("dispatch")) and not old.get("handed_to"):
            kept.append(old)
    if kept:
        state["retired"] = kept
    else:
        state.pop("retired", None)
    return stone


def write_state(path: Path, doc: dict[str, Any], *, unchecked_live: bool = False) -> dict[str, int]:
    doc["revision"] = int(doc.get("revision") or 0) + 1
    doc["updated_at"] = observed_at()
    text, sizes = render_state(doc, path, unchecked_live=unchecked_live)
    atomic_write(path, text)
    return sizes


def state_mutation(args: argparse.Namespace, change, limit_removal: dict[str, Any] | None = None) -> int:
    path = Path(args.file)
    try:
        with StateLock(path):
            doc, _ = read_state_file(path)
            if doc and doc.get("schema") in (None, LEGACY_STATE_SCHEMA) and limit_removal:
                # A sourced aggregate removal can precede migration. Keep the
                # schema 1 body and every other original field unchanged.
                body = json.loads(doc.get("body") or "null")
                if not isinstance(body, dict) or not isinstance(body.get("authorization"), dict):
                    raise StateRefusal("legacy-unreadable", "legacy authorization is unreadable; the file was not changed")
                if args.writer != "host":
                    raise StateRefusal("host-only", "the Host removes legacy authorization limits")
                check_writer(args, body)
                before = doc.get("revision", 0)
                if args.expect_revision != before:
                    raise StateRefusal("conflict", f"file is at revision {before}", current_revision=before)
                body["authorization"] = merge_patch(body["authorization"], limit_removal)
                doc["body"] = json.dumps(body, ensure_ascii=False)
                doc["revision"] = before + 1
                doc["updated_at"] = observed_at()
                atomic_write(path, json.dumps(doc, ensure_ascii=False, sort_keys=True, indent=1) + "\n")
                return emit({"result": "written", "revision": doc["revision"], "previous_revision": before,
                             "source": args.source, "value": body["authorization"],
                             "removed": [f"authorization.{key}" for key in limit_removal],
                             "next": "run state migrate with this matching tool; no count was inferred"})
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
                 **({"removed": args._authorization_removed} if hasattr(args, "_authorization_removed") else {}),
                 **({"host_revision": doc["host_revision"]} if doc.get("host_revision") else {}),
                 "value": changed, **({"index_mirror": mirrored} if mirrored else {}), **sizes})


def mirror_dispositions(args: argparse.Namespace, doc: dict[str, Any], path: Path) -> dict[str, Any] | list[dict[str, Any]] | None:
    """Copy one task's Host-recorded per-assignment dispositions onto the
    existing index rows. A linked row the Host gave no disposition after a
    verdict reads `undecided`, never a misleading `pending`.

    Issue #290: a retire closure proof may span several indices, so the mirror
    writes each supplied file. One supplied file keeps the single-object
    result every existing reader expects; several return one result per file."""
    paths = supplied_index_paths(args)
    if not paths or getattr(args, "kind", None) != "tasks" or getattr(args, "command", "") != "state":
        return None
    task = getattr(args, "_retired_task", None) or doc["state"].get("tasks", {}).get(args.id)
    if not isinstance(task, dict):
        return None
    if len(paths) == 1:
        try:
            return mirror_task(args, task, path, paths[0])
        except (OSError, ValueError) as exc:
            # The state write already landed; the index stays as it was and says so.
            return {"index": paths[0], "error": str(exc), "changed": {}}
    mirrored: list[dict[str, Any]] = []
    for index_path in paths:
        try:
            mirrored.append(mirror_task(args, task, path, index_path))
        except (OSError, ValueError) as exc:
            mirrored.append({"index": index_path, "error": str(exc), "changed": {}})
    return mirrored


def mirror_task(args: argparse.Namespace, task: dict[str, Any], path: Path, index_path: str) -> dict[str, Any]:
    with IndexLock(Path(index_path)):
        index = load_object(Path(index_path))
        mismatch = index_identity_problem(index, str(repo_of_state_file(Path(path))))
        if mismatch:
            # Issue #286 (G5): the state write above stays (I12); the mirror
            # leaves a foreign index exactly as it was and reports why.
            raise ValueError(f"index identity differs: it {mismatch}")
        refs = task.get("dispatch")
        refs = {refs} if isinstance(refs, str) else {ref for ref in refs or [] if isinstance(ref, str)}
        dispositions = task.get("dispositions") if isinstance(task.get("dispositions"), dict) else {}
        verdict = (task.get("verdict") or {}).get("value") if isinstance(task.get("verdict"), dict) else None
        changed: dict[str, str] = {}
        for row in index.get("items") or []:
            if not isinstance(row, dict) or not (row.get("item_id") in refs or row.get("task_id") == args.id):
                continue
            value = dispositions.get(row.get("item_id"))
            if getattr(args, "_retired_task", None) is not None:
                # An in-flight, unknown, or unreadable status is still a duty,
                # including after a handoff. Never settle it from retirement.
                if row.get("status") not in CLOSED_COVERAGE:
                    continue
                if value is None and verdict in ("accepted", "cancelled"):
                    value = verdict
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
            state["authorization"] = current_authorization(authorization)
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
    removal = patch if (args.section == "authorization" and isinstance(patch, dict) and patch
                        and set(patch) <= {"elite_cap", "total_cap", "worker_pool_cap"}
                        and all(value is None for value in patch.values())) else None
    return state_mutation(args, lambda doc, caller: apply_section_update(args, doc, patch, caller), removal)


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


host_changes = RECORD.host_changes


def revision_of(ident: str) -> int | None:
    head, _, tail = ident.rpartition("@")
    return int(tail) if head.startswith("host:") and tail.isdigit() else None


def retirement_stones(state: dict[str, Any], kind: str, record_id: str) -> list[dict[str, Any]]:
    return [stone for stone in state.get("retired") or []
            if isinstance(stone, dict) and stone.get("kind") == kind and stone.get("id") == record_id]


def already_settled_input(state: dict[str, Any], ident: str) -> bool:
    """A Host input whose record has left the current set.

    A current record stays open. ``keep_open`` and prose do not settle it.
    """
    if not ident.startswith("host:"):
        return False
    body = ident[len("host:"):].rpartition("@")[0]
    if body.startswith("retired/"):
        kind, _, record_id = body[len("retired/"):].partition("/")
    else:
        kind, _, record_id = body.partition("/")
    if not record_id or kind not in RECORD_KINDS:
        return False
    if retirement_stones(state, kind, record_id):
        return True
    return (state.get(kind) or {}).get(record_id) is None


def caller_record(caller: dict[str, str]) -> tuple[Path, dict[str, Any]]:
    try:
        directory = record_directory(caller["platform"], caller["session"], caller["repo"])
        record = json.loads((directory / "record.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, RECORD.acp_paths.RecordRootMismatch) as exc:
        raise StateRefusal("identity-unavailable", f"read original holder record: {exc}")
    if record.get("holder_instance_id") != caller["holder_instance_id"]:
        raise StateRefusal("identity-mismatch", "original holder record names another holder")
    return directory, record


def original_events(directory: Path):
    # Use the existing bounded rotations. No state copy or second event store.
    for path in [*sorted(directory.glob("events.jsonl.*")), directory / "events.jsonl"]:
        if not path.is_file():
            continue
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                if isinstance(event, dict):
                    yield event


def command_state_recovery_input(args: argparse.Namespace) -> int:
    path = Path(args.file)
    try:
        caller = caller_dispatcher()
        if not caller or caller_role(caller) != "host" or not same_repo(caller["repo"], str(repo_of_state_file(path))):
            raise StateRefusal("host-identity-required", "use the exact verified Host holder in this project")
        directory, record = caller_record(caller)
        evidence = args.evidence or args.source
        occurrence = None
        if args.kind == "host-compaction" and not args.fail:
            event = next((row for row in original_events(directory) if row.get("cursor") == args.signal_cursor), None)
            if not event or event.get("kind") != "compact_reload_detected" or not isinstance(event.get("holder"), str):
                raise StateRefusal("signal-unverified", "read the original completed Host signal receipt")
            spec = importlib.util.spec_from_file_location("kpr_recovery_signal", Path(__file__).with_name("kaola-compact-recovery.py"))
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            signal = module.classify(event.get("signal") or {}, caller["platform"])
            if (signal is None or event.get("role") != "host"
                    or not module.is_same_session(signal, record.get("acp_session_id"))):
                raise StateRefusal("signal-unverified", "kind alone does not attest a completed Host compaction")
            occurrence = signal.occurrence_id
            evidence = f"{directory / 'events.jsonl'}#{args.signal_cursor}"
        with StateLock(path):
            doc = require_current(read_state_file(path)[0], path)
            maintenance = doc["state"].setdefault("maintenance", {})
            prior = maintenance.get("recovery_input") or {}
            if args.fail:
                ident = args.input
                if args.through_host_revision is not None and not 0 <= args.through_host_revision <= int(doc.get("host_revision") or 0):
                    raise StateRefusal("invalid-input", "failure range must be an actual current Host revision")
                if not ident:
                    raise StateRefusal("invalid-input", "a failure names its actual input or batch")
                last = maintenance.get("last_checkpoint") or {}
                if args.fail not in ("stop-unconfirmed", "old-node-live") and last.get("verified") and ident in (last.get("settled") or []):
                    return emit({"result": "unchanged", "value": prior, "reason": "scoped-checkpoint-already-settled"})
                alerts = doc["state"].setdefault("alerts", {})
                alert = alerts.get("maintenance-returned") or {}
                inputs = dict(alert.get("inputs") or {})
                row = {"why": args.fail, "evidence": evidence,
                       "next": "Host: reconcile the original node and stop receipts; repair the binding; request a bounded check",
                       **({"host_revision_through": args.through_host_revision}
                          if args.through_host_revision is not None else {})}
                if inputs.get(ident) == row:
                    return emit({"result": "unchanged", "value": prior})
                inputs[ident] = row
                alerts["maintenance-returned"] = {**alert, "level": "warn", "owner": "host", "inputs": inputs,
                    "summary": "maintenance needs Host recovery from original receipts", "next": row["next"],
                    "source": args.source, "writer": "tool:carrier", "writer_holder": caller["holder_instance_id"],
                    "rev": int(alert.get("rev") or 0) + 1, "updated_at": observed_at(),
                    "evidence": list(dict.fromkeys([*(alert.get("evidence") or []), evidence]))}
                value = row
            else:
                last = maintenance.get("last_checkpoint") or {}
                previous = (last.get("recovery") or {}).get("input") or {}
                if (args.kind == "host-compaction" and previous.get("evidence") == evidence
                        and f"recovery#{previous.get('seq')}" in (last.get("settled") or [])):
                    return emit({"result": "unchanged", "value": previous, "reason": "original-signal-already-settled"})
                if (args.kind == prior.get("kind") and
                    ((occurrence is not None and occurrence == prior.get("occurrence_id")) or evidence == prior.get("evidence"))):
                    return emit({"result": "unchanged", "value": prior})
                seq = int(maintenance.get("recovery_seq") or 0) + 1
                value = {"seq": seq, "kind": args.kind, "occurrence_id": occurrence, "source": args.source,
                         "holder": caller["holder_instance_id"], "at": observed_at(), "evidence": evidence}
                maintenance.update(recovery_seq=seq, recovery_input=value)
            write_state(path, doc)
        return emit({"result": "written", "value": value, "host_revision": doc.get("host_revision", 0),
                     "carrier_supported": "host-compact-maintenance/1" in (record.get("holder_features") or [])})
    except StateRefusal as exc:
        return emit(exc.payload, 2)
    except (OSError, ValueError) as exc:
        return fail("invalid-input", str(exc))


def recovery_batch(caller: dict[str, str], batch: str, through: int) -> dict[str, Any]:
    _, node = caller_record(caller)
    carrier = node.get("dispatcher")
    if not isinstance(carrier, dict) or caller_role(carrier) != "host" or not same_repo(carrier["repo"], caller["repo"]):
        raise StateRefusal("batch-unverified", "node has no original bound Host carrier")
    directory, _ = caller_record(carrier)
    event = next((row for row in original_events(directory)
                  if row.get("kind") == "sideagent_node_batch" and row.get("batch") == batch
                  and row.get("target_holder") == caller["holder_instance_id"]
                  and row.get("host_holder") == carrier["holder_instance_id"]
                  and row.get("host_revision_through") == through), None)
    if event is None or not isinstance(event.get("recovery_input"), dict):
        raise StateRefusal("batch-unverified", "no original sent recovery input for this batch and node holder")
    return event


def checkpoint_entry(state: dict[str, Any], entry: Any, holder: str) -> tuple[str | None, str | None]:
    """(input id, why it is not settled) for one checkpoint entry. Applied
    evidence names a record this node wrote or a current retirement; a
    retained duty must be a current record with a responsible next reader."""
    if not isinstance(entry, dict) or not isinstance(entry.get("input"), str) or not entry["input"]:
        return None, "entry-unreadable"
    if entry["input"].startswith("recovery#"):
        if entry.keys() - {"input", "checked", "unavailable", "applied"}:
            return entry["input"], "recovery-entry-unknown"
        checked, unavailable = entry.get("checked") or {}, entry.get("unavailable") or {}
        if not isinstance(checked, dict) or not isinstance(unavailable, dict) or (checked.keys() | unavailable.keys()) != RECORD.RECOVERY_SCOPES:
            return entry["input"], "recovery-scopes-missing"
        if checked.keys() & unavailable.keys():
            return entry["input"], "recovery-scope-conflict"
        if any(not isinstance(refs, list) or not refs or not all(isinstance(ref, str) and ref for ref in refs)
               for refs in checked.values()):
            return entry["input"], "recovery-sources-empty"
        if any(not isinstance(reason, str) or not reason for reason in unavailable.values()):
            return entry["input"], "recovery-unavailable-unreadable"
        if unavailable:
            return entry["input"], "recovery-originals-unavailable"
        if "applied" not in entry:
            return entry["input"], None
        # Optional applied facts still require this node's own records.
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
                record = (state.get(kind) or {}).get(record_id) if kind in RECORD_KINDS else None
                if kind in RECORD_KINDS and record is None:
                    continue
                if not retirement_stones(state, kind, record_id):
                    return entry["input"], f"{ref} is not a current retirement"
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
    recovery = None
    recovery_ids = set()
    if getattr(args, "recovery_seq", None) is not None or any(
            isinstance(entry, dict) and str(entry.get("input", "")).startswith("recovery#") for entry in entries):
        receipt = recovery_batch(caller, args.batch, through)
        recovery = receipt["recovery_input"]
        if args.recovery_seq != recovery["seq"]:
            raise StateRefusal("batch-unverified", "checkpoint must name the actual selected recovery sequence")
        recovery_ids.add(f"recovery#{recovery['seq']}")
        current_alerts = ((state.get("alerts") or {}).get("maintenance-returned") or {}).get("inputs") or {}
        recovery_ids.update(ident for ident, value in (receipt.get("recovery_alerts") or {}).items()
                            if ident.startswith("recovery#") and current_alerts.get(ident) == value)
    selected = host_changes(doc, handled, through)
    # A batch input the Host rewrote after this batch was selected shows
    # only its later change, which is past `through` and so in the next
    # batch: superseded, not lost.
    later = {ident.rpartition("@")[0] for ident in host_changes(doc, through, current)}
    still_returned = ((state.get("alerts") or {}).get("maintenance-returned") or {}).get("inputs") or {}
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
        if ident.startswith("recovery#") and ident not in recovery_ids:
            raise StateRefusal("batch-unverified", "recovery entry is not in the original selected batch")
        elif problem and not already_settled_input(state, ident):
            returned[ident] = problem
        elif (ident in selected or ident in recovery_ids or already_settled_input(state, ident)
              or (ident in events and ident not in still_returned)):
            # A returned input was handed to the Host; only a batch that
            # actually carried it settles it, never a self-named event.
            settled.append(ident)
        elif (revision is not None and handled < revision <= through
              and ident.rpartition("@")[0] in later):
            superseded.append(ident)
        else:
            returned[ident] = "not-in-batch"
    for ident in [*selected, *events, *([f"recovery#{recovery['seq']}"] if recovery else [])]:
        if ident not in seen:
            if already_settled_input(state, ident):
                settled.append(ident)
            else:
                returned[ident] = "unaccounted"
    # The acknowledgment never passes an unaccounted Host change: neither
    # one of this batch nor one still in the Host's open returned alert.
    open_revisions = [revision for ident, revision in selected.items() if ident not in settled]
    open_revisions += [revision_of(ident) for ident in still_returned if revision_of(ident) is not None]
    new_acked = min([through] + [revision - 1 for revision in open_revisions])
    verified = not returned
    record = {"batch": args.batch, "node": {"session": caller.get("session"), "holder_instance_id": holder},
              "at": observed_at(), "source": args.source, "verified": verified,
              "host_revision": {"from": handled, "through": through, "current": current},
              "settled": sorted(settled), "returned_to_host": dict(sorted(returned.items())),
              **({"superseded": sorted(superseded)} if superseded else {})}
    if recovery:
        ident = f"recovery#{recovery['seq']}"
        entry = next((item for item in entries if item.get("input") == ident), {})
        record["recovery"] = {"seq": recovery["seq"], "input": recovery,
                              "checked": entry.get("checked") or {}, "unavailable": entry.get("unavailable") or {}}
        if ident in settled and (maintenance.get("recovery_input") or {}).get("seq") == recovery["seq"]:
            maintenance.pop("recovery_input", None)
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
        # A current input this batch did not carry keeps its original facts.
        inputs.update({ident: {"why": why, "batch": args.batch} for ident, why in returned.items()
                       if ident not in inputs or ident in selected or ident in recovery_ids})
        alerts[alert_id] = {**prior, "level": "warn", "owner": "host",
                            "summary": f"{len(inputs)} maintenance input(s) not applied by a node; "
                                       "judge or re-dispatch them from their sources",
                            "inputs": inputs, "evidence": list(dict.fromkeys([*(prior.get("evidence") or []), f"checkpoint:{args.batch}"])),
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
        view = delegator_view(doc, path, repo)
        view["seats"] = delegator_seats(args, doc, path)
        return emit(view)
    maintenance = doc["state"].get("maintenance")
    maintenance = maintenance if isinstance(maintenance, dict) else {}
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
    rows_document = load_object(Path(path))
    declared = rows_document.get("schema")
    # Issue #286 (G9): identify the --live input. `kaola-acp.py list` output
    # declares kaola-acp-list/1; a file that declares another schema, or no
    # schema at all, is not live rows and proves no seat state.
    if declared != "kaola-acp-list/1":
        what = "no schema" if declared is None else f"schema {declared!r}"
        raise StateRefusal("live-unidentified", f"the live rows at {path} declare {what}, "
                           "not kaola-acp-list/1; pass `kaola-acp.py list` output for this repo")
    rows = rows_document.get("rows")
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
            verdict = task.get("verdict") if isinstance(task.get("verdict"), dict) else {}
            seats = task_seats(task)
            close_open = not (
                verdict.get("value") in ("accepted", "cancelled") and not seats and not task.get("dispatch")
            )
            if close_open:
                note("done-not-retired", "watch", "done; retire it with its evidence once close-out is "
                     "verified", "tasks", ident)
            if seats and rows is not None:
                for detail in open_seats(seats, rows):
                    note("done-seat-open", "warn", f"done while {detail}", "tasks", ident)
        if isinstance(task.get("transcribed"), dict):
            note("transcription-unechoed", "watch", "a Sideagent-recorded Host decision waits for the "
                 "Host's next view", "tasks", ident)
    if index is not None:
        rows_by_id = {row.get("item_id"): row for row in index.get("items") or [] if isinstance(row, dict)}
        for item_id, row in rows_by_id.items():
            if row.get("status") not in ("in-flight", "returned", "unknown"):
                continue
            if (row.get("status") == "returned"
                    and row.get("acceptance") in ("accepted", "cancelled", "superseded", "handed-off")):
                continue
            task_id = row.get("task_id")
            if not task_id:
                note("dispatch-unassociated", "warn", f"index item {item_id} names no task", "index", item_id)
            elif task_id not in (state.get("tasks") or {}):
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
        state["authorization"], limit_blockers, limit_removed = RECORD.migrate_authorization_limits(authorization)
        blockers.extend(limit_blockers)
        dropped.extend(limit_removed)
        if not limit_blockers:
            state["authorization"] = current_authorization(state["authorization"])
        blockers.extend(item for item in RECORD.authorization_blockers(state["authorization"]) if item not in blockers)
    elif authorization is not None:
        blockers.append(RECORD.refusal(
            "authorization", "object of grants and pauses",
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
        state["authorization"] = current_authorization(state["authorization"])
        if state.get("retired") == []:
            state.pop("retired")
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
                original_state = doc["state"]
                prepared = json.loads(json.dumps(original_state))
                auth, auth_blockers, auth_removed = RECORD.migrate_authorization_limits(prepared.get("authorization"))
                if auth_blockers:
                    return emit({"result": "blocked", "writes": False, "blockers": auth_blockers,
                                 "detail": "unresolved original authorization; active work stays current"}, 2)
                prepared["authorization"] = current_authorization(auth or {})
                blockers, cleaned, changed, removed = RECORD.cleanup_current(prepared)
                removed = auth_removed + removed
                changed = changed or cleaned != original_state
                if not blockers:
                    auth = current_authorization(cleaned.get("authorization") or {})
                    if auth != cleaned.get("authorization"):
                        removed.append("authorization.grants/capability_summary ended eligibility")
                        cleaned["authorization"] = auth
                        changed = True
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
    project.add_argument("--authorization", required=True, help="JSON file path")
    project.add_argument("--availability", help="JSON file path")
    project.add_argument("--platforms")
    project.add_argument("--seats", action="store_true", help="read occupancy against supplied grants")
    project.add_argument("--repo")
    project.add_argument("--live", help="JSON file path")
    project.add_argument("--index", help="JSON file path")
    project.add_argument("--skills-root")
    project.set_defaults(func=command_project)

    execute = commands.add_parser("execute")
    execute.add_argument("--plan", required=True, help="JSON file path")
    execute.add_argument("--authorization", required=True, help="JSON file path")
    execute.add_argument("--availability", help="JSON file path")
    execute.add_argument("--platforms")
    execute.add_argument("--skills-root")
    execute.add_argument("--prior-index", help="JSON file path")
    execute.add_argument("--index", help="JSON file path")
    execute.add_argument("--live", help="JSON file path")
    execute.add_argument("--dry-run", action="store_true")
    execute.add_argument("--state", help="lifecycle state: preset holds and task links")
    execute.set_defaults(func=command_execute)

    collect = commands.add_parser("collect")
    collect.add_argument("--index", required=True, help="JSON file path")
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
    update.add_argument("--evidence", help="checkpoint:BATCH that proves a removed alert input handled")
    update.set_defaults(func=command_state_update)

    retire = actions.add_parser("retire")
    writer_args(retire)
    retire.add_argument("--kind", required=True, choices=RECORD_KINDS)
    retire.add_argument("--id", required=True)
    retire.add_argument("--expect-rev", type=int,
                        help="record revision of the current row; required unless --absent")
    retire.add_argument("--absent", action="store_true",
                        help="Host only: a decision id with no current row; return a receipt and store nothing")
    retire.add_argument("--evidence", required=True)
    retire.add_argument("--cite", help="JSON {commit, path} for a completed outcome that must survive")
    retire.add_argument("--outcome")
    retire.add_argument("--index", action="append",
                        help="JSON file path: this project's kaola-dispatch-index/1 showing the task's "
                             "items closed; repeatable when separate execute runs wrote separate indices")
    retire.add_argument("--live", help="JSON file path: kaola-acp.py list --repo --include-dead rows "
                        "(kaola-acp-list/1) showing its sessions stopped")
    retire.add_argument("--handoff", help="current task that takes over its seats and dispatch")
    retire.set_defaults(func=command_state_retire)

    update.add_argument("--index", help="JSON file path: dispatch index: mirror dispositions, and the only handoff locator this update reads")

    recovery = actions.add_parser("recovery-input", help="register a bounded Host recovery duty without a business write")
    recovery.add_argument("--file", required=True)
    recovery.add_argument("--kind", choices=("host-compaction", "request"), default="request")
    recovery.add_argument("--source", required=True)
    recovery.add_argument("--evidence")
    recovery.add_argument("--signal-cursor", type=int)
    recovery.add_argument("--fail")
    recovery.add_argument("--input")
    recovery.add_argument("--through-host-revision", type=int)
    recovery.set_defaults(func=command_state_recovery_input)

    checkpoint = actions.add_parser("checkpoint", help="a maintenance node's input accounting")
    writer_args(checkpoint)
    checkpoint.add_argument("--batch", required=True, help="the batch id the carrier sent")
    checkpoint.add_argument("--recovery-seq", type=int, help="the recovery sequence the carrier actually sent")
    checkpoint.add_argument("--events", help="JSON array of the batch's worker event ids, or @path")
    checkpoint.add_argument("--through-host-revision", type=int,
                            help="the Host revision this batch selected; later changes stay pending")
    checkpoint.add_argument("--entries", required=True,
                            help='JSON array or @path: ordinary inputs use applied or retained; '
                                 'recovery#N uses only input, checked, unavailable, optional applied '
                                 '(never retained); each scope is checked or unavailable, not both')
    checkpoint.set_defaults(func=command_state_checkpoint)

    view = actions.add_parser("view")
    view.add_argument("--file", required=True)
    view.add_argument("--role", required=True, choices=("host", "sideagent", "delegator"))
    view.add_argument("--repo")
    for flag in ("live", "index", "skills-root", "availability", "platforms"):
        view.add_argument("--" + flag)
    view.set_defaults(func=command_state_view)

    check = actions.add_parser("check")
    check.add_argument("--file", required=True)
    check.add_argument("--index", help="JSON file path")
    check.add_argument("--live", help="JSON file path")
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
    migrate.add_argument("--index", help="JSON file path")
    migrate.add_argument("--live", help="JSON file path")
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
        if name == "view":
            for flag in ("repo", "live", "index", "skills-root", "availability", "platforms"):
                sub.add_argument("--" + flag)
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
    view = RECORD.delegator_file_view(doc)
    path = Path(args.file)
    repo = Path(args.repo).resolve() if getattr(args, "repo", None) else repo_of_state_file(path)
    try:
        host_path = repo / ".kaola" / "heartbeat-prompt.json"
        host = require_current(read_state_file(host_path)[0], host_path)
    except (StateRefusal, OSError, ValueError):
        view["seats"] = delegator_seats(args, doc, path)
    else:
        view["seats"] = delegator_seats(args, host, host_path)
    return emit(view)


def delegator_recovery(args: argparse.Namespace, doc: dict[str, Any], blockers: list[dict[str, str]]) -> None:
    """Attach a scoped clear operation to watch refusals, without judging currentness."""
    watch = doc.get("watch") or {}
    revision = int(doc.get("revision") or 0)
    for problem in blockers:
        path = problem["path"]
        if not path.startswith("watch."):
            continue
        ident = next((ident for ident in sorted(watch, key=len, reverse=True)
                      if path == f"watch.{ident}" or path.startswith(f"watch.{ident}.")), None)
        if ident is None:
            problem["recovery"] = (f"{path} has no current row at revision {revision}. Do not create a handled "
                                   "or inapplicable row or move its text to another field. Retain original "
                                   "unresolved evidence through the current decision/reconciliation route.")
        else:
            command = shlex.join([sys.executable, str(Path(__file__).resolve()), "delegator", "update",
                                  "--file", str(args.file), "--writer", "delegator", "--source",
                                  "ORIGINAL_HANDLED_EVIDENCE", "--expect-revision", str(revision),
                                  "--set", json.dumps({"watch": {ident: None}}, separators=(",", ":"))])
            problem["recovery"] = (f"watch/{ident} exists at revision {revision}. If handled, clear it with: "
                                   f"{command}. Source must name the original effect evidence. Do not move "
                                   "handled text to another field. If unresolved, retain original evidence "
                                   "through the current decision/reconciliation route until its proper type "
                                   "is established. Unknown is not resolved.")


def command_delegator_migrate(args: argparse.Namespace) -> int:
    path = Path(args.file)
    try:
        with StateLock(path):
            doc = _delegator_read(path)
            migrated, blockers, dropped = RECORD.delegator_migrated(doc, frozenset(ident for ident, row in catalog_from_files(platform_paths(Path(__file__), None)).items() if row["class"] == "Expert"))
            if blockers or migrated is None:
                delegator_recovery(args, doc, blockers)
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
        auth_patch = patch.get("authorization")
        if isinstance(auth_patch, dict):
            limits = RECORD.aggregate_limit_blockers({key: value for key, value in auth_patch.items() if value is not None}, delegator=True)
            if limits:
                return emit({"result": "refused", "reason": "invalid-input", **limits[0], "blockers": limits}, 2)
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
            merged.pop("retired", None)
            if isinstance(merged.get("authorization"), dict):
                merged["authorization"].pop("retired_pool_grants", None)
            merged["schema"] = RECORD.DELEGATOR_SCHEMA
            merged["revision"] = actual + 1
            merged["updated_at"] = observed_at()
            if isinstance(auth_patch, dict):
                invalid = [RECORD.refusal(f"authorization.{key}", ", ".join(sorted(RECORD.DELEGATOR_AUTH_KEYS)),
                                         "Do not create duplicate authority or move it to prose. Use the original owner source and existing grant/watch recovery route; null removes a legacy key.")
                           for key, value in auth_patch.items() if value is not None and key not in RECORD.DELEGATOR_AUTH_KEYS]
                if invalid:
                    return emit({"result": "refused", "reason": "invalid-input", "blockers": invalid, **invalid[0]}, 2)
            normalized, blockers, _dropped = RECORD.delegator_migrated(merged, frozenset(ident for ident, row in catalog_from_files(platform_paths(Path(__file__), None)).items() if row["class"] == "Expert"))
            for ident, item in (patch.get("watch") or {}).items() if isinstance(patch.get("watch"), dict) else []:
                if (isinstance(item, dict) and item.get("status") in ("adopted", "settled")
                        and ident not in (doc.get("watch") or {})):
                    blockers.append(RECORD.refusal(f"watch.{ident}.status", "existing current duty",
                                                  "do not create a handled row"))
            if blockers or normalized is None:
                delegator_recovery(args, doc, blockers)
                return emit({"result": "refused", "reason": "invalid-input", "blockers": blockers,
                             "detail": blockers[0]["detail"]}, 2)
            atomic_write(path, json.dumps(normalized, ensure_ascii=False, sort_keys=True, indent=1) + "\n")
    except StateRefusal as refusal:
        return emit(refusal.payload, 2)
    except (OSError, ValueError) as exc:
        return fail("invalid-input", str(exc))
    return emit({"result": "written", "revision": merged["revision"], "removed": _dropped})


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
