#!/usr/bin/env python3
"""Shared field contract for Host and Delegator routine state.

Pure standard library. No subprocess and no scheduler. The state tool and the
holder import this module. It checks shapes and projects current fields. It
does not decide that a sentence is finished, and it does not call Git.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


HOST_SCHEMA = "kaola-heartbeat-prompt/2"
DELEGATOR_SCHEMA = "kaola-delegator-heartbeat/1"
HOST_VIEW_MAX_BYTES = 65536
COMMIT_RE = re.compile(r"^[0-9a-f]{7,40}$")
BACKUP_RE = re.compile(r"^(?P<stem>.+)\.v(?P<gen>[0-9]+)-(?P<digest>[0-9a-f]{12})\.json$")

PROJECT_KEYS = frozenset({
    "code", "goal", "issue", "repo", "requirements_source", "rules",
    "skill_adoption_source", "status", "stop",
})
GRANT_KEYS = frozenset({
    "id", "state", "count", "shared_seat", "model_switch", "special_requirements",
    "lifetime", "expires",
})
AUTH_KEYS = frozenset({
    "classes", "grants", "elite_cap", "exclusions", "paused", "revoked",
    "model_switches", "account_token_quotas", "capability_summary",
})
RECOVERY_KEYS = frozenset({"protected_untracked", "host"})
TASK_KEYS = frozenset({
    "stage", "goal", "scope", "acceptance", "needs", "depends", "source", "keep_open",
    "dispositions", "verdict", "prior_verdict", "dispatch", "evidence", "wait", "next",
    "sessions", "assignments", "session", "holder", "holder_instance_id", "platform",
    "preset", "candidate", "resume_when", "boundary", "owner", "duty", "ref",
    "rev", "created_at", "updated_at", "writer", "transcribed", "host_revision",
    "writer_holder", "observed_at",
})
HOLD_KEYS = frozenset({
    "scope", "reason", "owner", "resume_when", "next", "preset", "presets", "pool",
    "pools", "evidence", "impact", "summary", "observed_at", "rev", "created_at",
    "updated_at", "source", "writer", "host_revision", "writer_holder", "count",
    "last_seen", "ack",
})
ALERT_KEYS = frozenset({
    "level", "summary", "impact", "owner", "next", "count", "ack", "evidence", "inputs",
    "observed_at", "rev", "created_at", "updated_at", "source", "writer",
    "host_revision", "writer_holder", "last_seen",
})
DECISION_KEYS = frozenset({
    "owner", "question", "options", "status", "evidence", "next", "answer",
    "transcribed", "rev", "created_at", "updated_at", "source", "writer",
    "host_revision", "writer_holder",
})
RECORD_KEYS = {
    "tasks": TASK_KEYS, "holds": HOLD_KEYS, "alerts": ALERT_KEYS, "decisions": DECISION_KEYS,
}
VERDICT_KEYS = frozenset({"value", "by", "host_turn", "why"})
TRANSCRIBED_KEYS = frozenset({"host_turn", "fields"})
UNVERIFIED_KEYS = frozenset({"summary", "locator", "session", "live", "v1", "unchecked", "source"})
V1_IDENTITY = frozenset({
    "session", "holder_instance_id", "platform", "preset", "authorization_source", "state",
})
STONE_KEYS = frozenset({
    "kind", "id", "outcome", "at", "host_revision", "writer", "writer_holder",
    "handed_to", "seats", "dispatch", "cite",
})
SIDEAGENT_KEYS = frozenset({
    "platform", "session", "preset", "state", "holder_instance_id", "mode", "source",
    "since", "authorization_source", "recipe",
})
RECIPE_KEYS = frozenset({"argv", "runner", "state_tool"})
WATCH_STATUS = frozenset({"pending", "sent", "adopted", "open", "settled", "blocked"})
WATCH_KIND = frozenset({"relay", "observation", "recovery", "decision"})
WATCH_KEYS = frozenset({
    "kind", "status", "source", "next", "scope", "issue", "preset", "presets", "pool",
    "locator", "at",
})
DELEGATOR_GRANT_KEYS = frozenset({"preset_id", "preset_ids", "count", "class", "switch_authorization"})
DELEGATOR_AUTH_KEYS = frozenset({
    "run_state", "dispatch_enabled", "expert_task_grants", "worker_pool", "worker_pool_cap",
    "account_token_quotas", "elite_grants", "elite_cap", "priority", "revoked",
    "known_resource_limits", "retired_pool_grants", "sideagent", "paused", "exclusions",
})
DELEGATOR_TOP_KEYS = frozenset({
    "schema", "revision", "updated_at", "project", "host", "authorization", "watch",
    "stop", "entry", "timer_owner", "cadence", "source", "retired",
})
# Non-critical freeform bags removed by these field names. Not by reading the text.
LEGACY_BAG_KEYS = frozenset({
    "legacy", "v1_host", "migration", "raw", "report", "observation", "latest",
    "latest_owner_change", "archive", "release", "previous_completion",
})
CRITICAL_WATCH_FIELDS = frozenset({"relay_status", "relay"})

OVERWRITE_DETECTION = {
    "alert": "state-overwritten",
    "raised": False,
    "detail": (
        "Migration does not write heartbeat-prompt.vN-<hash>.json or recovery.migration.raw. "
        "state-overwritten is not raised from those copies. An older writer that replaces the "
        "current file is no longer detected that way. Recover from project, Runner, and forge records."
    ),
}

CLEANUP_PROCEDURE = (
    "Do not delete heartbeat-prompt.vN-<hash>.json files from this command. "
    "A backup is not authority. Read it only to see whether it names a pending "
    "grant, hold, task, or relay that the current file and the project's Git, "
    "Runner, and forge records do not. Leave that file in place until the "
    "installation's own authorized migration rehomes that evidence. "
    "Cleanup of one live installation is that migration, not a bulk delete."
)


def refusal(path: str, allowed: str, recovery: str) -> dict[str, str]:
    return {
        "path": path,
        "allowed": allowed,
        "recovery": recovery,
        "detail": f"{path} is not allowed. Allowed: {allowed}. {recovery}",
    }


def cite_problem(cite: Any) -> str | None:
    """Shape only. This module does not run Git or check that the object exists."""
    if not isinstance(cite, dict):
        return "cite is an object with commit and path"
    if set(cite) - {"commit", "path", "locator"}:
        return "cite allows only commit, path, and locator"
    commit = cite.get("commit")
    path = cite.get("path")
    if not isinstance(commit, str) or COMMIT_RE.fullmatch(commit) is None:
        return "commit is 7 to 40 lowercase hex characters"
    if not isinstance(path, str) or not path or path.startswith("/") or ".." in path.split("/"):
        return "path is a relative path inside the repository"
    locator = cite.get("locator", "")
    if locator is not None and not isinstance(locator, str):
        return "locator is a string"
    return None


def machine_stone(stone: dict[str, Any]) -> dict[str, Any]:
    """Fixed machine identity, outcome, time, and revision. No prose."""
    kept = {key: stone[key] for key in STONE_KEYS if key in stone and stone[key] is not None}
    cite = kept.get("cite")
    if cite is not None and cite_problem(cite):
        kept.pop("cite", None)
    return kept


def unknown_record_keys(kind: str, record: dict[str, Any]) -> list[str]:
    allowed = RECORD_KEYS[kind]
    found = [key for key in record if key not in allowed]
    verdict = record.get("verdict")
    if isinstance(verdict, dict):
        found += [f"verdict.{key}" for key in verdict if key not in VERDICT_KEYS]
    prior = record.get("prior_verdict")
    if isinstance(prior, dict):
        found += [f"prior_verdict.{key}" for key in prior if key not in VERDICT_KEYS]
    transcribed = record.get("transcribed")
    if isinstance(transcribed, dict):
        found += [f"transcribed.{key}" for key in transcribed if key not in TRANSCRIBED_KEYS]
    return found


def reject_record_patch(kind: str, patch: dict[str, Any]) -> dict[str, str] | None:
    """Refuse a proposed patch. Null deletes any key; that is the writer's own removal."""
    allowed = RECORD_KEYS[kind]
    for key, value in patch.items():
        if value is None:
            continue
        if key not in allowed:
            return refusal(
                f"{kind}.{key}",
                ", ".join(sorted(allowed)),
                "remove this key from the patch and retry; the file was not changed",
            )
        if key in ("verdict", "prior_verdict") and isinstance(value, dict):
            for nested in value:
                if nested not in VERDICT_KEYS:
                    return refusal(
                        f"{kind}.{key}.{nested}",
                        ", ".join(sorted(VERDICT_KEYS)),
                        "remove this key from the patch and retry; the file was not changed",
                    )
    return None


def _string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def authorization_blockers(auth: Any, prefix: str = "authorization") -> list[dict[str, str]]:
    if auth in (None, {}):
        return []
    if not isinstance(auth, dict):
        return [refusal(prefix, "object of grants, pauses, and caps",
                        "rehome this value into the authorization object; the file was not written")]
    found = []
    for key in sorted(auth):
        if key not in AUTH_KEYS:
            found.append(refusal(
                f"{prefix}.{key}",
                ", ".join(sorted(AUTH_KEYS)),
                "rehome this authorization fact into an allowed field; the file was not written",
            ))
    grants = auth.get("grants") or []
    if isinstance(grants, list):
        for index, grant in enumerate(grants):
            if not isinstance(grant, dict):
                found.append(refusal(f"{prefix}.grants[{index}]", "grant object",
                                     "rehome this grant; the file was not written"))
                continue
            for key in sorted(grant):
                if key not in GRANT_KEYS:
                    found.append(refusal(
                        f"{prefix}.grants[{index}].{key}",
                        ", ".join(sorted(GRANT_KEYS)),
                        "rehome this grant fact; the file was not written",
                    ))
    return found


def project_blockers(project: Any) -> list[dict[str, str]]:
    if project in (None, {}):
        return []
    if not isinstance(project, dict):
        return [refusal("project", "object", "rehome project; the file was not written")]
    return [refusal(
        f"project.{key}",
        ", ".join(sorted(PROJECT_KEYS)),
        "rehome this project fact; the file was not written",
    ) for key in sorted(project) if key not in PROJECT_KEYS]


def protected_blockers(value: Any, path: str) -> list[dict[str, str]]:
    if isinstance(value, list) and all(isinstance(item, str) and item for item in value):
        return []
    return [refusal(
        path,
        "array of non-empty strings",
        "rehome protected_untracked from its existing source into that array; the file was not written",
    )]


def recovery_from_v1(recovery: Any) -> tuple[dict[str, Any], list[dict[str, str]], list[str]]:
    """Keep protected_untracked. Every other recovery field name leaves. No copy."""
    dropped: list[str] = []
    if recovery in (None, {}, []):
        return {}, [], dropped
    if not isinstance(recovery, dict):
        return {}, [refusal(
            "recovery",
            "object",
            "rehome recovery from project evidence; the file was not written",
        )], dropped
    blockers = []
    kept: dict[str, Any] = {}
    if "protected_untracked" in recovery:
        blockers = protected_blockers(recovery.get("protected_untracked"), "recovery.protected_untracked")
        if not blockers:
            kept["protected_untracked"] = list(recovery["protected_untracked"])
    for key in sorted(recovery):
        if key == "protected_untracked":
            continue
        dropped.append(f"recovery.{key}")
    return kept, blockers, dropped


def note_unmapped(state: dict[str, Any], locator: str, keys: list[str]) -> None:
    if not keys:
        return
    ident = f"{locator.replace('[', '-').rstrip(']')}-fields"
    state.setdefault("unverified", {})[ident] = {
        "summary": f"unmapped {locator} field names: {', '.join(keys)}",
        "locator": [f"{locator}.{key}" for key in keys],
    }


def identity_only(entry: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(entry, dict):
        return None
    kept = {key: entry[key] for key in V1_IDENTITY if entry.get(key) is not None}
    return kept or None


def pick(allowed: frozenset[str], value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {key: value[key] for key in allowed if key in value}


def authorization_view(auth: Any) -> dict[str, Any]:
    """Grants, pauses, and the Class sentences stored on the grant. Nothing here rewrites them."""
    if not isinstance(auth, dict):
        return {}
    view = pick(AUTH_KEYS - {"capability_summary"}, auth)
    grants = []
    for grant in auth.get("grants") or []:
        if isinstance(grant, dict):
            grants.append(pick(GRANT_KEYS, grant))
    if "grants" in auth:
        view["grants"] = grants
    return view


def capability_from_grants(auth: Any) -> dict[str, Any]:
    """Compact preset and shared-seat summary from the stored grants. Class text stays on the grant."""
    grants = []
    if isinstance(auth, dict):
        for grant in auth.get("grants") or []:
            if isinstance(grant, dict):
                grants.append(grant)
    presets = []
    shared: dict[str, dict[str, Any]] = {}
    for grant in grants:
        if grant.get("state") not in (None, "granted", "paused"):
            continue
        ident = grant.get("id")
        if isinstance(ident, str):
            presets.append(ident)
        seat = grant.get("shared_seat")
        if isinstance(seat, str) and seat:
            row = shared.setdefault(seat, {"seat": seat, "ids": [], "count": grant.get("count")})
            if isinstance(ident, str) and ident not in row["ids"]:
                row["ids"].append(ident)
            if grant.get("count") is not None:
                row["count"] = grant.get("count")
    return {"presets": presets, "shared_seats": [shared[key] for key in sorted(shared)]}


def project_view(project: Any) -> dict[str, Any]:
    return pick(PROJECT_KEYS, project)


def recovery_view(recovery: Any) -> dict[str, Any]:
    return pick(RECOVERY_KEYS, recovery)


def unknown_paths(state: dict[str, Any]) -> list[dict[str, str]]:
    """Locators only. Values are not copied into the view."""
    found: list[dict[str, str]] = []
    if not isinstance(state, dict):
        return found

    def add(path: str) -> None:
        found.append({"path": path})

    for key in state:
        if key not in {
            "project", "authorization", "sideagent", "recovery", "unverified",
            "tasks", "holds", "alerts", "decisions", "retired", "maintenance",
            "section_sources",
        }:
            add(f"state.{key}")
    for key in (state.get("project") or {}) if isinstance(state.get("project"), dict) else {}:
        if key not in PROJECT_KEYS:
            add(f"state.project.{key}")
    for key in (state.get("recovery") or {}) if isinstance(state.get("recovery"), dict) else {}:
        if key not in RECOVERY_KEYS:
            add(f"state.recovery.{key}")
    for kind, allowed in RECORD_KEYS.items():
        records = state.get(kind) or {}
        if not isinstance(records, dict):
            continue
        for ident, record in records.items():
            if not isinstance(record, dict):
                continue
            for key in record:
                if key not in allowed:
                    add(f"state.{kind}.{ident}.{key}")
    for stone in state.get("retired") or []:
        if isinstance(stone, dict):
            for key in stone:
                if key not in STONE_KEYS:
                    add(f"state.retired.{stone.get('kind')}/{stone.get('id')}.{key}")
    return found[:32]


def projected_record(kind: str, record: dict[str, Any]) -> dict[str, Any]:
    return {key: record[key] for key in RECORD_KEYS[kind] if key in record}


def projected_state(state: dict[str, Any]) -> dict[str, Any]:
    """Role-readable current fields. Legacy bags and prose stones stay out."""
    if not isinstance(state, dict):
        return {}
    out: dict[str, Any] = {}
    for key in ("project", "authorization"):
        if isinstance(state.get(key), dict):
            out[key] = pick(PROJECT_KEYS if key == "project" else AUTH_KEYS, state[key])
    if "sideagent" in state:
        binding = state.get("sideagent")
        out["sideagent"] = pick(SIDEAGENT_KEYS, binding) if isinstance(binding, dict) else binding
    if isinstance(state.get("recovery"), dict):
        out["recovery"] = recovery_view(state["recovery"])
    if isinstance(state.get("unverified"), dict):
        out["unverified"] = {
            ident: pick(UNVERIFIED_KEYS, item) if isinstance(item, dict) else {"summary": "unreadable"}
            for ident, item in state["unverified"].items()
        }
    for kind in RECORD_KEYS:
        records = state.get(kind) or {}
        if isinstance(records, dict):
            out[kind] = {
                ident: projected_record(kind, record)
                for ident, record in records.items() if isinstance(record, dict)
            }
    if isinstance(state.get("retired"), list):
        out["retired"] = [machine_stone(stone) for stone in state["retired"] if isinstance(stone, dict)]
    if isinstance(state.get("maintenance"), dict):
        out["maintenance"] = {
            key: state["maintenance"][key]
            for key in ("last_verified", "acked_host_revision", "handled_host_revision", "last_checkpoint")
            if key in state["maintenance"]
        }
    if isinstance(state.get("section_sources"), dict):
        out["section_sources"] = state["section_sources"]
    return out


def union_dispatch(current: Any, patch: Any) -> Any:
    if not isinstance(patch, list):
        return patch
    previous = current if isinstance(current, list) else []
    merged: list[Any] = []
    for item in [*previous, *patch]:
        if item not in merged:
            merged.append(item)
    return merged


def clear_stage_warning(state: dict[str, Any], task_id: str) -> None:
    unverified = state.get("unverified")
    if isinstance(unverified, dict):
        unverified.pop(f"{task_id}-stage", None)


def cleanup_current(state: dict[str, Any]) -> tuple[list[dict[str, str]], dict[str, Any], bool]:
    """Drop non-critical bags by field name. A bad protected_untracked stops the write."""
    if not isinstance(state, dict):
        return [refusal("state", "object", "the file was not written")], state, False
    blockers: list[dict[str, str]] = []
    recovery = state.get("recovery") if isinstance(state.get("recovery"), dict) else {}
    if "protected_untracked" in recovery:
        blockers.extend(protected_blockers(recovery.get("protected_untracked"), "recovery.protected_untracked"))
    legacy = recovery.get("legacy") if isinstance(recovery.get("legacy"), dict) else None
    if isinstance(legacy, dict) and "protected_untracked" in legacy:
        blockers.extend(protected_blockers(
            legacy.get("protected_untracked"), "recovery.legacy.protected_untracked"))
    blockers.extend(authorization_blockers(state.get("authorization")))
    blockers.extend(project_blockers(state.get("project")))
    if blockers:
        return blockers, state, False
    cleaned = json.loads(json.dumps(state))
    changed = False
    rec = cleaned.get("recovery") if isinstance(cleaned.get("recovery"), dict) else None
    if isinstance(rec, dict):
        legacy = rec.get("legacy") if isinstance(rec.get("legacy"), dict) else None
        if isinstance(legacy, dict) and "protected_untracked" in legacy and "protected_untracked" not in rec:
            rec["protected_untracked"] = list(legacy["protected_untracked"])
            changed = True
        for key in ("legacy", "v1_host", "migration"):
            if key in rec:
                rec.pop(key)
                changed = True
    for task in (cleaned.get("tasks") or {}).values():
        if isinstance(task, dict) and "legacy" in task:
            task.pop("legacy")
            changed = True
    unverified = cleaned.get("unverified")
    if isinstance(unverified, dict):
        for item in unverified.values():
            if isinstance(item, dict) and "raw" in item:
                item.pop("raw")
                changed = True
    stones = cleaned.get("retired")
    if isinstance(stones, list):
        narrowed = [machine_stone(stone) if isinstance(stone, dict) else stone for stone in stones]
        if narrowed != stones:
            cleaned["retired"] = narrowed
            changed = True
    return [], cleaned, changed


def assess_backups(directory: Path, current_text: str) -> dict[str, Any]:
    """Name hash-named copies and whether the current file points at them. Never delete."""
    found = []
    if directory.is_dir():
        for path in sorted(directory.iterdir()):
            if path.is_file() and BACKUP_RE.match(path.name):
                found.append({
                    "name": path.name,
                    "bytes": path.stat().st_size,
                    "referenced": path.name in current_text or str(path) in current_text,
                    "trusted": False,
                    "deleted": False,
                })
    return {"backups": found, "deleted": False, "procedure": CLEANUP_PROCEDURE}


def _watch_status(item: dict[str, Any]) -> tuple[str | None, bool]:
    """Exact token only. A sentence in relay_status is a critical blocker, not a guess."""
    for key in ("status", "relay_status", "relay"):
        value = item.get(key)
        if isinstance(value, str) and value in WATCH_STATUS:
            return value, False
        if key in CRITICAL_WATCH_FIELDS and value not in (None, ""):
            return None, True
    state = item.get("state")
    if isinstance(state, str) and state in WATCH_STATUS:
        return state, False
    return None, False


def delegator_blockers(doc: dict[str, Any]) -> tuple[list[dict[str, str]], list[str]]:
    blockers: list[dict[str, str]] = []
    dropped: list[str] = []
    auth = doc.get("authorization")
    if isinstance(auth, dict):
        for key in sorted(auth):
            if key not in DELEGATOR_AUTH_KEYS:
                blockers.append(refusal(
                    f"authorization.{key}",
                    ", ".join(sorted(DELEGATOR_AUTH_KEYS)),
                    "rehome this grant or limit; the file was not written",
                ))
        for index, grant in enumerate(auth.get("elite_grants") or []):
            if not isinstance(grant, dict):
                blockers.append(refusal(f"authorization.elite_grants[{index}]", "grant object",
                                        "rehome this grant; the file was not written"))
                continue
            if "preset_id" not in grant and "preset_ids" not in grant:
                blockers.append(refusal(
                    f"authorization.elite_grants[{index}]",
                    "preset_id or preset_ids, plus count",
                    "rehome this grant; the file was not written",
                ))
            if not isinstance(grant.get("count"), int):
                blockers.append(refusal(
                    f"authorization.elite_grants[{index}].count",
                    "integer count, including a shared count above one",
                    "rehome this grant; the file was not written",
                ))
            for key in grant:
                if key not in DELEGATOR_GRANT_KEYS:
                    blockers.append(refusal(
                        f"authorization.elite_grants[{index}].{key}",
                        ", ".join(sorted(DELEGATOR_GRANT_KEYS)),
                        "rehome this grant fact; the file was not written",
                    ))
    watch = doc.get("watch")
    if isinstance(watch, dict):
        for ident, item in watch.items():
            if not isinstance(item, dict):
                blockers.append(refusal(f"watch.{ident}", "object",
                                        "rehome this duty; the file was not written"))
                continue
            _status, critical = _watch_status(item)
            if critical:
                blockers.append(refusal(
                    f"watch.{ident}.relay_status",
                    "pending, sent, or adopted",
                    "rehome this relay to status pending, sent, or adopted; the file was not written",
                ))
            for key in item:
                if key not in WATCH_KEYS and key not in {"state", "relay_status", "relay", "kind"} | LEGACY_BAG_KEYS:
                    if key not in LEGACY_BAG_KEYS:
                        dropped.append(f"watch.{ident}.{key}")
    return blockers, dropped


def delegator_migrated(doc: dict[str, Any]) -> tuple[dict[str, Any] | None, list[dict[str, str]], list[str]]:
    blockers, dropped = delegator_blockers(doc)
    if blockers:
        return None, blockers, dropped
    out: dict[str, Any] = {"schema": DELEGATOR_SCHEMA, "revision": int(doc.get("revision") or 0)}
    for key in ("project", "host", "authorization", "stop", "entry", "timer_owner", "cadence", "source"):
        if key in doc:
            out[key] = doc[key]
    watch_out: dict[str, Any] = {}
    for ident, item in (doc.get("watch") or {}).items() if isinstance(doc.get("watch"), dict) else []:
        if not isinstance(item, dict) or ident in LEGACY_BAG_KEYS:
            if ident in LEGACY_BAG_KEYS:
                dropped.append(f"watch.{ident}")
            continue
        status, _critical = _watch_status(item)
        kind = item.get("kind") if item.get("kind") in WATCH_KIND else None
        if kind is None and ("relay_status" in item or "relay" in item):
            kind = "relay"
        kept = {key: item[key] for key in WATCH_KEYS if key in item and key not in {"kind", "status"}}
        if kind:
            kept["kind"] = kind
        if status:
            kept["status"] = status
        for bag in LEGACY_BAG_KEYS:
            if bag in item:
                dropped.append(f"watch.{ident}.{bag}")
        if "state" in item and item.get("state") not in WATCH_STATUS:
            dropped.append(f"watch.{ident}.state")
        if kept:
            watch_out[ident] = kept
        else:
            dropped.append(f"watch.{ident}")
    out["watch"] = watch_out
    if isinstance(doc.get("retired"), list):
        out["retired"] = [machine_stone(stone) for stone in doc["retired"] if isinstance(stone, dict)]
    return out, [], sorted(set(dropped))


def short(value: Any, limit: int = 240) -> Any:
    if isinstance(value, str) and len(value) > limit:
        return value[:limit] + f"… [+{len(value) - limit} chars omitted; full text on the record]"
    return value


def judgment_digest(record: dict[str, Any]) -> str:
    skip = {"rev", "created_at", "updated_at", "source", "writer", "transcribed",
            "host_revision", "writer_holder", "count", "last_seen", "ack"}
    text = json.dumps({key: value for key, value in record.items() if key not in skip},
                      ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def task_attention(task_id: str, task: dict[str, Any]) -> list[dict[str, Any]]:
    found = []
    verdict = task.get("verdict") if isinstance(task.get("verdict"), dict) else None
    if task.get("stage") == "review" and not verdict:
        prior = task.get("prior_verdict") if isinstance(task.get("prior_verdict"), dict) else None
        found.append({"kind": "tasks", "id": task_id, "why": "awaiting-verdict",
                      **({"prior_verdict": prior.get("value")} if prior else {}),
                      "content": judgment_digest(task)})
    elif (task.get("stage") in ("closeout", "done")
          and (verdict or {}).get("value") not in ("accepted", "partial", "cancelled")):
        found.append({"kind": "tasks", "id": task_id, "why": "verdict-missing", "stage": task["stage"],
                      "content": judgment_digest(task)})
    if isinstance(verdict, dict) and verdict.get("value") == "repair" and task.get("goal"):
        found.append({"kind": "tasks", "id": task_id, "why": "delivery-open",
                      "content": judgment_digest(task)})
    if isinstance(task.get("transcribed"), dict):
        found.append({"kind": "tasks", "id": task_id, "why": "transcribed-check",
                      "host_turn": task["transcribed"].get("host_turn"),
                      "fields": task["transcribed"].get("fields")})
    return found


def host_view(doc: dict[str, Any], path: Path | None) -> dict[str, Any]:
    """Field-by-field Host view. Unknown values are locators, not prompt text."""
    state = doc.get("state") if isinstance(doc.get("state"), dict) else {}
    name = path.name if isinstance(path, Path) else "heartbeat-prompt.json"
    attention: list[dict[str, Any]] = []
    tasks = []
    for task_id, task in sorted((state.get("tasks") or {}).items()):
        if not isinstance(task, dict):
            continue
        entry = {"id": task_id, "stage": task.get("stage")}
        for key in ("goal", "acceptance", "depends", "wait", "next", "keep_open", "dispositions"):
            if task.get(key) not in (None, "", [], {}):
                entry[key] = short(task[key]) if key == "goal" else task[key]
        for key in ("verdict", "prior_verdict"):
            if isinstance(task.get(key), dict):
                entry[key] = {field: task[key].get(field) for field in ("value", "by", "host_turn")
                              if task[key].get(field) is not None}
        if task.get("dispatch"):
            entry["dispatch_count"] = len(task["dispatch"]) if isinstance(task["dispatch"], list) else 1
        attention.extend(task_attention(task_id, task))
        tasks.append(entry)
    holds = []
    for hold_id, hold in sorted((state.get("holds") or {}).items()):
        if not isinstance(hold, dict):
            continue
        shown = {"id": hold_id}
        for key in ("scope", "preset", "presets", "pool", "pools", "reason", "owner", "resume_when", "next"):
            if hold.get(key) is not None:
                shown[key] = hold.get(key) if key in ("scope", "preset", "presets", "pool", "pools") else short(hold.get(key))
        holds.append(shown)
        if hold.get("owner") == "host":
            attention.append({"kind": "holds", "id": hold_id, "why": "host-owned",
                              "content": judgment_digest(hold)})
    alerts = []
    for alert_id, alert in sorted((state.get("alerts") or {}).items()):
        if not isinstance(alert, dict):
            continue
        alerts.append({"id": alert_id, **{key: short(alert.get(key)) for key in
                                          ("level", "summary", "impact", "owner", "next", "count", "ack")
                                          if alert.get(key) is not None}})
        if alert.get("level") == "severe" or alert.get("owner") == "host":
            attention.append({"kind": "alerts", "id": alert_id, "why": alert.get("level"),
                              "content": judgment_digest(alert)})
    decisions = []
    for decision_id, decision in sorted((state.get("decisions") or {}).items()):
        if not isinstance(decision, dict):
            continue
        if decision.get("status") == "settled":
            if isinstance(decision.get("transcribed"), dict):
                attention.append({"kind": "decisions", "id": decision_id, "why": "transcribed-check",
                                  "host_turn": decision["transcribed"].get("host_turn"),
                                  "content": judgment_digest(decision)})
            continue
        decisions.append({"id": decision_id, **{key: decision.get(key) if key in ("question", "options")
                                                else short(decision.get(key)) for key in
                                                ("owner", "question", "options", "next")
                                                if decision.get(key) is not None}})
        if decision.get("owner") == "host":
            attention.append({"kind": "decisions", "id": decision_id, "why": "host-decision",
                              "content": judgment_digest(decision)})
    binding = state.get("sideagent")
    if isinstance(binding, dict) and binding.get("state") in ("replacing", "failed"):
        attention.append({"kind": "sideagent", "id": binding.get("session"), "why": binding["state"]})
    unverified = []
    for key, value in sorted((state.get("unverified") or {}).items()):
        if isinstance(value, dict):
            unverified.append({"id": key, "summary": short(value.get("summary")),
                               **({"locator": value.get("locator")} if value.get("locator") is not None else {})})
        else:
            unverified.append({"id": key, "summary": "unreadable"})
    maintenance = state.get("maintenance") or {}
    brief = {key: maintenance[key] for key in ("last_verified", "acked_host_revision", "handled_host_revision")
             if isinstance(maintenance, dict) and maintenance.get(key) is not None}
    last = maintenance.get("last_checkpoint") if isinstance(maintenance, dict) else None
    if isinstance(last, dict) and not last.get("verified"):
        brief["last_checkpoint"] = {key: last.get(key) for key in ("batch", "at", "verified")}
    view: dict[str, Any] = {
        "view": "host",
        "revision": doc.get("revision"),
        "host_revision": doc.get("host_revision"),
        "as_of": doc.get("updated_at"),
        "detail": f"{name} state; `state view --role sideagent` for evidence and dispatch rows",
        "project": project_view(state.get("project") or {}),
        "authorization": authorization_view(state.get("authorization") or {}),
        "capability": capability_from_grants(state.get("authorization") or {}),
        "sideagent": ({key: binding.get(key) for key in ("platform", "session", "preset", "state", "mode")
                       if binding.get(key) is not None} if isinstance(binding, dict) else None),
        "attention": attention,
        "tasks": tasks,
    }
    if isinstance(binding, dict):
        view["sideagent_maintenance"] = (
            "no node is running; an idle binding is not missing maintenance"
            if binding.get("mode") == "node" else "binding present"
        )
    elif binding is None:
        view["sideagent_maintenance"] = "no binding; that is not evidence maintenance ran"
    for key, value in (("holds", holds), ("alerts", alerts), ("decisions", decisions),
                       ("unverified", unverified), ("recovery", recovery_view(state.get("recovery") or {})),
                       ("maintenance", brief)):
        if value:
            view[key] = value
    unknown = unknown_paths(state)
    if unknown:
        view["unknown"] = unknown
    return view


def injection_body(doc: dict[str, Any]) -> tuple[str | None, str | None]:
    """Projected Host view for a current state file. None means the caller keeps a legacy body."""
    if not isinstance(doc, dict) or doc.get("schema") != HOST_SCHEMA or not isinstance(doc.get("state"), dict):
        return None, None
    view = host_view(doc, None)
    body = json.dumps(view, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if len(body.encode("utf-8")) > HOST_VIEW_MAX_BYTES:
        return None, (
            f"projected Host view exceeds {HOST_VIEW_MAX_BYTES} bytes; retire finished "
            "records. The stored body was not injected."
        )
    return body, None
