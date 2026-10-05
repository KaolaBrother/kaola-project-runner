#!/usr/bin/env python3
"""Shared field contract for Host and Delegator routine state.

Pure standard library. No subprocess and no scheduler. The state tool and the
holder import this module. It checks shapes and projects current fields. It
does not decide that a sentence is finished, and it does not call Git.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
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
    "locator", "at", "summary", "detail", "evidence",
})
ASSIGNMENT_KEYS = frozenset({
    "session", "holder_instance_id", "platform", "preset", "holder", "state", "locator",
    "ref", "candidate", "next", "evidence", "wait", "resume_when",
    "dispatch_event_cursor", "prompt_fingerprint", "authorization_source", "handed_from",
})
TASK_TEXT_KEYS = frozenset({
    "goal", "scope", "acceptance", "source", "wait", "next", "boundary", "duty",
    "owner", "resume_when", "ref",
})
HOLD_TEXT_KEYS = frozenset({
    "scope", "reason", "owner", "resume_when", "next", "preset", "summary", "pool",
})
DELEGATOR_GRANT_KEYS = frozenset({
    "preset_id", "preset_ids", "count", "class", "switch_authorization",
    "lifetime", "special_requirements",
})
DAY_START_KEYS = frozenset({"action", "state", "evidence"})
DAY_END_KEYS = frozenset({"action", "state", "host_ack", "claim_check", "evidence"})
FINAL_STOP_KEYS = frozenset({"action", "state", "evidence", "boundary", "text"})
DELEGATOR_HOST_KEYS = frozenset({
    "platform", "session", "holder_instance_id", "acp_session_id", "native_session_id",
    "preset_id", "state",
})
DELEGATOR_PROJECT_KEYS = frozenset({
    "goal", "code", "issue", "repo", "status", "stop", "user_language",
})
DELEGATOR_CADENCE_KEYS = frozenset({"timezone", "start_local", "end_local", "interval_minutes"})
DELEGATOR_STOP_KEYS = frozenset({"boundary", "state", "evidence"})
DELEGATOR_ENTRY_KEYS = frozenset({"skill", "target", "timer_template"})
DELEGATOR_TIMER_KEYS = frozenset({"platform", "native_timer_id", "state"})
DELEGATOR_SIDEAGENT_KEYS = frozenset({"preset", "scope", "source"})
GRANT_STATES = frozenset({"granted", "paused", "revoked", "excluded"})
TASK_STAGES = frozenset({"todo", "doing", "review", "closeout", "done"})
DELEGATOR_AUTH_KEYS = frozenset({
    "run_state", "dispatch_enabled", "expert_task_grants", "worker_pool", "worker_pool_cap",
    "account_token_quotas", "elite_grants", "elite_cap", "priority", "revoked",
    "known_resource_limits", "retired_pool_grants", "sideagent", "paused", "exclusions",
})
DELEGATOR_TOP_KEYS = frozenset({
    "schema", "revision", "updated_at", "project", "host", "authorization", "watch",
    "stop", "entry", "timer_owner", "cadence", "source", "retired",
    "day_start", "day_end", "final_stop",
})
# Legacy bags need current-duty reconciliation before removal.
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
    """Shape only. This module does not run Git. The state tool checks that the path is a file."""
    if not isinstance(cite, dict):
        return "cite is an object with path"
    if set(cite) - {"commit", "path", "locator"}:
        return "cite allows only commit, path, and locator"
    path = cite.get("path")
    if not isinstance(path, str) or not path or path.startswith("/") or ".." in path.split("/"):
        return "path is a relative path inside the repository"
    commit = cite.get("commit")
    if commit is not None and (not isinstance(commit, str) or COMMIT_RE.fullmatch(commit) is None):
        return "commit is 7 to 40 lowercase hex characters"
    locator = cite.get("locator")
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


def drop_settled_history(state: dict[str, Any]) -> list[str]:
    """Drop settled rows. Keep a stone only when it still names seats or dispatch.

    A clear-time, cite, or outcome is not a current duty. ``keep_open`` and
    prose are not read here.
    """
    removed: list[str] = []
    stones = state.get("retired")
    if not isinstance(stones, list):
        return removed
    kept: list[dict[str, Any]] = []
    for stone in stones:
        if not isinstance(stone, dict):
            removed.append("retired.unreadable")
            continue
        kind, ident = stone.get("kind"), stone.get("id")
        pending = bool(stone.get("seats") or stone.get("dispatch")) and not stone.get("handed_to")
        if pending:
            kept.append({
                key: stone[key]
                for key in ("kind", "id", "at", "host_revision", "seats", "dispatch")
                if key in stone
            })
            continue
        removed.append(f"retired.{kind}/{ident}")
    if kept:
        state["retired"] = kept
    else:
        state.pop("retired", None)
    return removed


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
        typed = record_type_problem(kind, {key: value})
        if typed:
            return typed
    return None


def _text(value: Any) -> bool:
    return isinstance(value, str)


def _string_list_ok(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def record_type_problem(kind: str, record: dict[str, Any]) -> dict[str, str] | None:
    """Refuse nested bags and wrong types. Null is a deletion and is not checked here."""
    if kind == "tasks":
        for key in TASK_TEXT_KEYS:
            if key in record and record[key] is not None and not _text(record[key]):
                return refusal(f"tasks.{key}", "string",
                               "set this field to a string, or null to remove it; the file was not changed")
        if "keep_open" in record and record["keep_open"] is not None and not isinstance(record["keep_open"], bool):
            return refusal("tasks.keep_open", "boolean",
                           "set keep_open to true or false; the file was not changed")
        if "depends" in record and record["depends"] is not None and not _string_list_ok(record["depends"]):
            return refusal("tasks.depends", "array of strings",
                           "set depends to an array of task ids; the file was not changed")
        if "needs" in record and record["needs"] is not None and not (
                _text(record["needs"]) or _string_list_ok(record["needs"])):
            return refusal("tasks.needs", "string or array of strings",
                           "set needs to text or an array of strings; the file was not changed")
        problem = _rows_problem("tasks.sessions", record.get("sessions"))
        if problem:
            return problem
        problem = _rows_problem("tasks.assignments", record.get("assignments"))
        if problem:
            return problem
    elif kind == "holds":
        for key in HOLD_TEXT_KEYS:
            if key in record and record[key] is not None and not _text(record[key]):
                return refusal(f"holds.{key}", "string",
                               "set this field to a string; the file was not changed")
        for key in ("presets", "pools"):
            if key in record and record[key] is not None and not _string_list_ok(record[key]):
                return refusal(f"holds.{key}", "array of strings",
                               "set this field to an array of ids; the file was not changed")
        if "impact" in record and record["impact"] is not None and not _text(record["impact"]):
            return refusal("holds.impact", "string",
                           "set impact to a string; the file was not changed")
    return None


def _rows_problem(path: str, value: Any) -> dict[str, str] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        return refusal(path, "array of session names or seat objects",
                       "replace this value with that array; the file was not changed")
    allowed = ", ".join(sorted(ASSIGNMENT_KEYS))
    for index, item in enumerate(value):
        if isinstance(item, str):
            continue
        if not isinstance(item, dict):
            return refusal(f"{path}[{index}]", "string or object",
                           "replace this item; the file was not changed")
        for key in item:
            if key not in ASSIGNMENT_KEYS:
                return refusal(
                    f"{path}[{index}].{key}", allowed,
                    "remove this key; history and snapshot bags are not seat fields. The file was not changed",
                )
    return None


def _string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def count_ok(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def delegator_authorization_blockers(auth: Any) -> list[dict[str, str]]:
    """One closed shape check for writes, migration, and the dispatch ceiling.

    Owner lifetime and requirement text stays literal. The decision reader
    must resolve it for the affected grant; a shape check grants no authority.
    """
    if auth is None:
        return []
    if not isinstance(auth, dict):
        return [refusal("authorization", "object", "rehome the current grants and limits; the file was not written")]
    found = []

    def bad(path: str, allowed: str, recovery: str = "rehome this fact from its source; the file was not written") -> None:
        found.append(refusal(path, allowed, recovery))

    for key in sorted(auth):
        if key not in DELEGATOR_AUTH_KEYS:
            bad(f"authorization.{key}", ", ".join(sorted(DELEGATOR_AUTH_KEYS)))
    for key in ("worker_pool", "paused", "revoked", "exclusions"):
        if auth.get(key) is not None and not _string_list_ok(auth[key]):
            bad(f"authorization.{key}", "array of preset ids")
    for key in ("worker_pool_cap", "elite_cap"):
        if auth.get(key) is not None and not count_ok(auth[key]):
            bad(f"authorization.{key}", "nonnegative integer, excluding boolean",
                "map the owner's stated limit from original evidence; do not infer an integer from text. "
                "Keep an unresolved condition in watch.detail with its source and next action; the file was not written")
    for key in ("run_state", "priority", "account_token_quotas"):
        if auth.get(key) is not None and not isinstance(auth[key], str):
            bad(f"authorization.{key}", "string")
    if auth.get("dispatch_enabled") is not None and not isinstance(auth["dispatch_enabled"], bool):
        bad("authorization.dispatch_enabled", "boolean")
    limits = auth.get("known_resource_limits")
    if limits is not None and (not isinstance(limits, dict)
                              or any(not isinstance(item, (str, int, float, bool)) for item in limits.values())):
        bad("authorization.known_resource_limits", "object of strings or numbers")
    sideagent = auth.get("sideagent")
    if sideagent is not None:
        found.extend(_closed_strings("authorization.sideagent", sideagent, DELEGATOR_SIDEAGENT_KEYS))
    for key in ("elite_grants", "expert_task_grants"):
        grants = auth.get(key)
        if grants is None:
            continue
        if not isinstance(grants, list):
            bad(f"authorization.{key}", "array of grant objects")
            continue
        for index, grant in enumerate(grants):
            path = f"authorization.{key}[{index}]"
            if not isinstance(grant, dict):
                bad(path, "grant object")
                continue
            for field in sorted(grant):
                if field not in DELEGATOR_GRANT_KEYS:
                    bad(f"{path}.{field}", ", ".join(sorted(DELEGATOR_GRANT_KEYS)))
            if not grant.get("preset_id") and not grant.get("preset_ids"):
                bad(path, "preset_id or nonempty preset_ids, plus count")
            if "preset_id" in grant and (not isinstance(grant["preset_id"], str) or not grant["preset_id"]):
                bad(f"{path}.preset_id", "nonempty preset id string")
            if "preset_ids" in grant and (not _string_list_ok(grant["preset_ids"])
                                           or not grant["preset_ids"] or not all(grant["preset_ids"])):
                bad(f"{path}.preset_ids", "nonempty array of preset ids")
            if not count_ok(grant.get("count")):
                bad(f"{path}.count", "nonnegative integer count, excluding boolean; shared counts may exceed one")
            switch = grant.get("switch_authorization")
            if switch is not None and not isinstance(switch, bool):
                bad(f"{path}.switch_authorization", "boolean",
                    "retain the owner's switch condition in watch.detail with source and next action. "
                    "Map true or false only when original authority supports it; the file was not written")
            for field in ("class", "lifetime"):
                if grant.get(field) is not None and not isinstance(grant[field], str):
                    bad(f"{path}.{field}", "string")
            special = grant.get("special_requirements")
            if special is not None and not isinstance(special, (str, dict)):
                bad(f"{path}.special_requirements", "owner text or object of model, effort, task_scope strings")
            elif isinstance(special, dict):
                found.extend(_closed_strings(f"{path}.special_requirements", special,
                                             frozenset({"model", "effort", "task_scope"})))
    return found


def _closed_strings(path: str, value: Any, allowed: frozenset[str]) -> list[dict[str, str]]:
    if not isinstance(value, dict):
        return [refusal(path, "object", "rehome the current fields; the file was not written")]
    return [refusal(f"{path}.{key}", ", ".join(sorted(allowed)) if key not in allowed else "string",
                    "rehome current text into an allowed field; the file was not written")
            for key, item in value.items() if key not in allowed or not isinstance(item, str)]


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
    classes = auth.get("classes")
    if classes is not None:
        if not isinstance(classes, dict) or any(not isinstance(key, str) or not isinstance(value, str) or not value
                                                for key, value in classes.items()):
            found.append(refusal(f"{prefix}.classes", "object of class name to stored sentence",
                                 "keep each Class sentence as a string; the file was not written"))
    for key in ("paused", "revoked", "exclusions"):
        if key in auth and auth[key] is not None and not _string_list_ok(auth[key]):
            found.append(refusal(f"{prefix}.{key}", "array of preset ids",
                                 "set this field to an array of preset ids; the file was not written"))
    if "elite_cap" in auth and auth["elite_cap"] is not None and not isinstance(auth["elite_cap"], int):
        found.append(refusal(f"{prefix}.elite_cap", "integer",
                             "set elite_cap to an integer; the file was not written"))
    summary = auth.get("capability_summary")
    if summary is not None and (
            not isinstance(summary, dict)
            or not _string_list_ok(summary.get("presets"))
            or ("text" in summary and summary["text"] is not None and not isinstance(summary["text"], str))):
        found.append(refusal(f"{prefix}.capability_summary", "object with presets array",
                             "keep the stored preset list; the file was not written"))
    grants = auth.get("grants") or []
    if "grants" in auth and not isinstance(grants, list):
        found.append(refusal(f"{prefix}.grants", "array of grant objects",
                             "rehome grants into that array; the file was not written"))
        grants = []
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
            if "id" in grant and not isinstance(grant.get("id"), str):
                found.append(refusal(f"{prefix}.grants[{index}].id", "preset id string",
                                     "set id to a preset id; the file was not written"))
            if "state" in grant and grant.get("state") not in GRANT_STATES:
                found.append(refusal(f"{prefix}.grants[{index}].state",
                                     "granted, paused, revoked, or excluded",
                                     "set state to one of those tokens; the file was not written"))
            count = grant.get("count")
            if "count" in grant and not isinstance(count, int):
                found.append(refusal(f"{prefix}.grants[{index}].count", "integer",
                                     "set count to an integer; the file was not written"))
    return found


def project_blockers(project: Any) -> list[dict[str, str]]:
    if project in (None, {}):
        return []
    if not isinstance(project, dict):
        return [refusal("project", "object", "rehome project; the file was not written")]
    found = [refusal(
        f"project.{key}",
        ", ".join(sorted(PROJECT_KEYS)),
        "rehome this project fact; the file was not written",
    ) for key in sorted(project) if key not in PROJECT_KEYS]
    for key in ("code", "goal", "issue", "repo", "requirements_source", "skill_adoption_source", "status", "stop"):
        if key in project and project[key] is not None and not isinstance(project[key], str):
            found.append(refusal(f"project.{key}", "string",
                                 "set this field to a string; the file was not written"))
    rules = project.get("rules")
    if rules is not None and not (isinstance(rules, str) or _string_list_ok(rules)):
        found.append(refusal("project.rules", "string or array of strings",
                             "remove history bags from rules; the file was not written"))
    return found


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
    """Eligible presets. Stored Worker-pool ids stay. Paused, revoked, and excluded ids leave.

    Class sentences stay on ``authorization.classes``. This function does not write them.
    """
    if not isinstance(auth, dict):
        return {"presets": [], "shared_seats": []}
    blocked: set[str] = set()
    for key in ("paused", "revoked", "exclusions"):
        value = auth.get(key)
        if isinstance(value, list):
            blocked.update(item for item in value if isinstance(item, str))
        elif isinstance(value, str) and value:
            blocked.add(value)
    summary = auth.get("capability_summary")
    presets: list[str] = []
    if isinstance(summary, dict) and isinstance(summary.get("presets"), list):
        for item in summary["presets"]:
            if isinstance(item, str) and item not in presets:
                presets.append(item)
    shared: dict[str, dict[str, Any]] = {}
    for grant in auth.get("grants") or []:
        if not isinstance(grant, dict):
            continue
        ident = grant.get("id")
        state = grant.get("state")
        if state in ("paused", "revoked", "excluded"):
            if isinstance(ident, str):
                blocked.add(ident)
            continue
        if state not in (None, "granted"):
            continue
        if isinstance(ident, str) and ident not in presets:
            presets.append(ident)
        seat = grant.get("shared_seat")
        if isinstance(seat, str) and seat and isinstance(ident, str):
            row = shared.setdefault(seat, {"seat": seat, "ids": [], "count": grant.get("count")})
            if ident not in row["ids"]:
                row["ids"].append(ident)
            if grant.get("count") is not None:
                row["count"] = grant.get("count")
    return {
        "presets": [item for item in presets if item not in blocked],
        "shared_seats": [shared[key] for key in sorted(shared)],
    }


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
        elif key == "host" and isinstance((state.get("recovery") or {}).get("host"), dict):
            for nested in state["recovery"]["host"]:
                if nested not in V1_IDENTITY:
                    add(f"state.recovery.host.{nested}")
    auth = state.get("authorization")
    if isinstance(auth, dict):
        for key in auth:
            if key not in AUTH_KEYS:
                add(f"state.authorization.{key}")
    binding = state.get("sideagent")
    if isinstance(binding, dict):
        for key in binding:
            if key not in SIDEAGENT_KEYS:
                add(f"state.sideagent.{key}")
    unverified = state.get("unverified")
    if isinstance(unverified, dict):
        for ident, item in unverified.items():
            if not isinstance(item, dict):
                add(f"state.unverified.{ident}")
                continue
            for key in item:
                if key not in UNVERIFIED_KEYS:
                    add(f"state.unverified.{ident}.{key}")
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
        pending = [
            machine_stone(stone) for stone in state["retired"]
            if isinstance(stone, dict)
            and (stone.get("seats") or stone.get("dispatch"))
            and not stone.get("handed_to")
        ]
        if pending:
            out["retired"] = pending
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


def cleanup_current(state: dict[str, Any]) -> tuple[list[dict[str, str]], dict[str, Any], bool, list[str]]:
    """Drop non-critical bags by field name. Name every removal. A bad protected list stops the write."""
    if not isinstance(state, dict):
        return [refusal("state", "object", "the file was not written")], state, False, []
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
        return blockers, state, False, []
    cleaned = json.loads(json.dumps(state))
    changed = False
    removed: list[str] = []
    rec = cleaned.get("recovery") if isinstance(cleaned.get("recovery"), dict) else None
    if isinstance(rec, dict):
        legacy = rec.get("legacy") if isinstance(rec.get("legacy"), dict) else None
        if isinstance(legacy, dict) and "protected_untracked" in legacy and "protected_untracked" not in rec:
            rec["protected_untracked"] = list(legacy["protected_untracked"])
            changed = True
            removed.append("recovery.legacy.protected_untracked mapped to recovery.protected_untracked")
        for key in ("legacy", "v1_host", "migration"):
            if key not in rec:
                continue
            if key == "legacy" and isinstance(rec.get("legacy"), dict):
                for nested in sorted(rec["legacy"]):
                    if nested != "protected_untracked":
                        removed.append(f"recovery.legacy.{nested}")
            removed.append(f"recovery.{key}")
            rec.pop(key)
            changed = True
    tasks = cleaned.get("tasks") if isinstance(cleaned.get("tasks"), dict) else {}
    for task_id, task in tasks.items():
        if isinstance(task, dict) and "legacy" in task:
            removed.append(f"tasks.{task_id}.legacy")
            task.pop("legacy")
            changed = True
    unverified = cleaned.get("unverified")
    if isinstance(unverified, dict):
        for ident, item in list(unverified.items()):
            if isinstance(item, dict) and "raw" in item:
                removed.append(f"unverified.{ident}.raw")
                item.pop("raw")
                changed = True
        for task_id, task in tasks.items():
            warning = f"{task_id}-stage"
            if (warning in unverified and isinstance(task, dict)
                    and task.get("writer") == "host" and task.get("stage") in TASK_STAGES):
                unverified.pop(warning)
                removed.append(f"unverified.{warning}")
                changed = True
    stones = cleaned.get("retired")
    if isinstance(stones, list):
        narrowed = []
        for stone in stones:
            if not isinstance(stone, dict):
                narrowed.append(stone)
                continue
            for key in stone:
                if key not in STONE_KEYS:
                    removed.append(f"retired.{stone.get('kind')}/{stone.get('id')}.{key}")
            narrowed.append(machine_stone(stone))
        if narrowed != stones:
            cleaned["retired"] = narrowed
            changed = True
    history = drop_settled_history(cleaned)
    if history:
        removed.extend(history)
        changed = True
    return [], cleaned, changed, removed


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


def _watch_status(item: dict[str, Any]) -> tuple[str | None, str | None]:
    """Return (token, path of a non-token status). A sentence is not a status."""
    for key in ("status", "relay_status", "relay", "state"):
        if key not in item or item.get(key) in (None, ""):
            continue
        value = item.get(key)
        if isinstance(value, str) and value in WATCH_STATUS:
            return value, None
        return None, key
    return None, None


def _string_field(value: Any, path: str, allowed: str) -> dict[str, str] | None:
    if value is None or isinstance(value, str):
        return None
    return refusal(path, allowed, "set this field to a string; the file was not written")


def section_shape_problems(section: str, value: Any) -> list[dict[str, str]]:
    """Nested types for recovery, sideagent, and unverified. Unknown keys are refused."""
    found: list[dict[str, str]] = []
    if section == "recovery":
        if value is None:
            return found
        if not isinstance(value, dict):
            return [refusal("recovery", "object", "rehome recovery; the file was not written")]
        host = value.get("host")
        if host is not None:
            if not isinstance(host, dict):
                found.append(refusal("recovery.host", "object of identity fields",
                                     "remove history bags; the file was not written"))
            else:
                for key, item in host.items():
                    if key not in V1_IDENTITY:
                        found.append(refusal(f"recovery.host.{key}", ", ".join(sorted(V1_IDENTITY)),
                                             "remove this key; the file was not written"))
                    elif not isinstance(item, str):
                        found.append(refusal(f"recovery.host.{key}", "string",
                                             "set this field to a string; the file was not written"))
        return found
    if section == "sideagent":
        if value is None:
            return found
        if not isinstance(value, dict):
            return [refusal("sideagent", "binding object", "rehome the binding; the file was not written")]
        for key in value:
            if key not in SIDEAGENT_KEYS:
                found.append(refusal(f"sideagent.{key}", ", ".join(sorted(SIDEAGENT_KEYS)),
                                     "remove this key; the file was not written"))
        recipe = value.get("recipe")
        if recipe is not None:
            if not isinstance(recipe, dict):
                found.append(refusal("sideagent.recipe", "object", "rehome the recipe; the file was not written"))
            else:
                for key in recipe:
                    if key not in RECIPE_KEYS:
                        found.append(refusal(f"sideagent.recipe.{key}", ", ".join(sorted(RECIPE_KEYS)),
                                             "remove this key; the file was not written"))
        return found
    if section == "unverified":
        if not isinstance(value, dict):
            return [refusal("unverified", "object of locator records",
                            "rehome each note as an object; the file was not written")]
        for ident, item in value.items():
            if not isinstance(item, dict):
                found.append(refusal(f"unverified.{ident}", "object with summary and locator",
                                     "replace the bare value with that object; the file was not written"))
                continue
            for key in item:
                if key not in UNVERIFIED_KEYS:
                    found.append(refusal(f"unverified.{ident}.{key}", ", ".join(sorted(UNVERIFIED_KEYS)),
                                         "remove this key; the file was not written"))
            summary = item.get("summary")
            if summary is not None and not isinstance(summary, str):
                found.append(refusal(f"unverified.{ident}.summary", "string",
                                     "set summary to a string; the file was not written"))
            locator = item.get("locator")
            if locator is not None and not (isinstance(locator, str) or _string_list_ok(locator)):
                found.append(refusal(f"unverified.{ident}.locator", "string or array of strings",
                                     "set locator to a path; the file was not written"))
        return found
    return found


def _legacy_bag_problem(path: str, value: Any, status: str | None = None) -> dict[str, str] | None:
    if value in (None, "", [], {}) or status in ("adopted", "settled"):
        return None
    return refusal(path, "current text in watch.summary, watch.detail, or watch.evidence",
                   "reconcile this pending or unadopted text from its source and rehome it in a typed duty. "
                   "Do not infer adoption or discard it; the file was not written")


def _day_problems(path: str, value: Any, allowed: frozenset[str], *, text_ok: bool = False) -> list[dict[str, str]]:
    if value is None:
        return []
    if text_ok and isinstance(value, str):
        return []
    if not isinstance(value, dict):
        return [refusal(path, "object" + (" or string" if text_ok else ""),
                        "keep the owner's duty; the file was not written")]
    found = []
    for key in value:
        if key in LEGACY_BAG_KEYS:
            problem = _legacy_bag_problem(f"{path}.{key}", value[key])
            if problem:
                found.append(problem)
            continue
        if key not in allowed:
            found.append(refusal(f"{path}.{key}", ", ".join(sorted(allowed)),
                                 "rehome this field; the file was not written"))
    state = value.get("state")
    if state is not None and state not in ("pending", "confirmed"):
        found.append(refusal(f"{path}.state", "pending or confirmed",
                             "set state to one token; the file was not written"))
    for key in allowed:
        if key == "state" or key not in value:
            continue
        problem = _string_field(value.get(key), f"{path}.{key}", "string")
        if problem:
            found.append(problem)
    return found


def _delegator_nest_problems(doc: dict[str, Any], dropped: list[str]) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    for key, value in doc.items():
        if key in DELEGATOR_TOP_KEYS or key in ("schema", "revision"):
            continue
        if key in LEGACY_BAG_KEYS:
            status = _watch_status(value)[0] if isinstance(value, dict) else None
            if status == "adopted" and not (isinstance(value.get("evidence") or value.get("locator"), str)
                                             and (value.get("evidence") or value.get("locator"))):
                status = None
            problem = _legacy_bag_problem(key, value, status)
            if problem:
                found.append(problem)
            else:
                dropped.append(key)
        elif value in (None, "", [], {}):
            dropped.append(key)
        else:
            found.append(refusal(key, ", ".join(sorted(DELEGATOR_TOP_KEYS)),
                                 "rehome this duty or name it for removal; the file was not written"))
    found.extend(_day_problems("day_start", doc.get("day_start"), DAY_START_KEYS))
    found.extend(_day_problems("day_end", doc.get("day_end"), DAY_END_KEYS))
    found.extend(_day_problems("final_stop", doc.get("final_stop"), FINAL_STOP_KEYS, text_ok=True))
    for key, allowed in (("entry", DELEGATOR_ENTRY_KEYS), ("timer_owner", DELEGATOR_TIMER_KEYS)):
        if doc.get(key) is not None:
            found.extend(_closed_strings(key, doc[key], allowed))
    for key in ("source", "updated_at"):
        if doc.get(key) is not None and not isinstance(doc[key], str):
            found.append(refusal(key, "string", "keep a source locator; the file was not written"))
    if doc.get("revision") is not None and not count_ok(doc["revision"]):
        found.append(refusal("revision", "nonnegative integer, excluding boolean",
                             "recover the current revision from original evidence; the file was not written"))
    host = doc.get("host")
    if isinstance(host, dict):
        for key in host:
            if key not in DELEGATOR_HOST_KEYS:
                if key in LEGACY_BAG_KEYS:
                    problem = _legacy_bag_problem(f"host.{key}", host[key])
                    if problem:
                        found.append(problem)
                    else:
                        dropped.append(f"host.{key}")
                else:
                    found.append(refusal(f"host.{key}", ", ".join(sorted(DELEGATOR_HOST_KEYS)),
                                         "remove this key; the file was not written"))
            elif not isinstance(host[key], str):
                found.append(refusal(f"host.{key}", "string", "keep the exact identity; the file was not written"))
    elif host is not None:
        found.append(refusal("host", "object", "rehome host identity; the file was not written"))
    project = doc.get("project")
    if project is not None and not isinstance(project, dict):
        found.append(refusal("project", "object", "rehome project fields; the file was not written"))
    if isinstance(project, dict):
        for key in project:
            if key not in DELEGATOR_PROJECT_KEYS:
                found.append(refusal(f"project.{key}", ", ".join(sorted(DELEGATOR_PROJECT_KEYS)),
                                     "do not copy Host task tables here; the file was not written"))
            elif not isinstance(project[key], str):
                found.append(refusal(f"project.{key}", "string",
                                     "set this field to a string; the file was not written"))
    cadence = doc.get("cadence")
    if cadence is not None and not isinstance(cadence, dict):
        found.append(refusal("cadence", "object", "rehome cadence fields; the file was not written"))
    if isinstance(cadence, dict):
        for key, value in cadence.items():
            if key not in DELEGATOR_CADENCE_KEYS:
                found.append(refusal(f"cadence.{key}", ", ".join(sorted(DELEGATOR_CADENCE_KEYS)),
                                     "remove this key; the file was not written"))
            elif key == "interval_minutes" and not count_ok(value):
                found.append(refusal("cadence.interval_minutes", "integer",
                                     "set interval_minutes to an integer; the file was not written"))
            elif key != "interval_minutes" and not isinstance(value, str):
                found.append(refusal(f"cadence.{key}", "string",
                                     "set this field to a string; the file was not written"))
    stop = doc.get("stop")
    if isinstance(stop, dict):
        found.extend(_closed_strings("stop", stop, DELEGATOR_STOP_KEYS))
    elif stop is not None and not isinstance(stop, str):
        found.append(refusal("stop", "string or object", "rehome the stop boundary; the file was not written"))
    if "retired" in doc:
        dropped.append("retired")
    return found


def delegator_blockers(doc: dict[str, Any]) -> tuple[list[dict[str, str]], list[str]]:
    blockers: list[dict[str, str]] = []
    dropped: list[str] = []
    blockers.extend(delegator_authorization_blockers(doc.get("authorization")))
    if isinstance(doc.get("authorization"), dict) and "retired_pool_grants" in doc["authorization"]:
        dropped.append("authorization.retired_pool_grants")
    blockers.extend(_delegator_nest_problems(doc, dropped))
    watch = doc.get("watch")
    if watch is not None and not isinstance(watch, dict):
        blockers.append(refusal("watch", "object keyed by current duty id", "rehome current duties; the file was not written"))
    if isinstance(watch, dict):
        for ident, item in watch.items():
            if ident in LEGACY_BAG_KEYS:
                status = _watch_status(item)[0] if isinstance(item, dict) else None
                if status == "adopted" and not (isinstance(item.get("evidence") or item.get("locator"), str)
                                                 and (item.get("evidence") or item.get("locator"))):
                    status = None
                problem = _legacy_bag_problem(f"watch.{ident}", item, status)
                if problem:
                    blockers.append(problem)
                else:
                    dropped.append(f"watch.{ident}")
                continue
            if not isinstance(item, dict):
                blockers.append(refusal(f"watch.{ident}", "object",
                                        "rehome this duty; the file was not written"))
                continue
            status, bad = _watch_status(item)
            if bad:
                blockers.append(refusal(
                    f"watch.{ident}.{bad}",
                    "pending, sent, adopted, open, settled, or blocked",
                    "set status to one token; the file was not written",
                ))
            kind = item.get("kind")
            if kind is not None and kind not in WATCH_KIND:
                blockers.append(refusal(f"watch.{ident}.kind", ", ".join(sorted(WATCH_KIND)),
                                        "set kind to one of those tokens; the file was not written"))
            if status == "adopted":
                evidence = item.get("evidence") or item.get("locator")
                if not isinstance(evidence, str) or not evidence:
                    blockers.append(refusal(
                        f"watch.{ident}.evidence",
                        "string that names the Host record or path",
                        "adopted needs the Host evidence; sent does not. The file was not written",
                    ))
            for key, value in item.items():
                if key in LEGACY_BAG_KEYS:
                    problem = _legacy_bag_problem(f"watch.{ident}.{key}", value, status)
                    if problem:
                        blockers.append(problem)
                    else:
                        dropped.append(f"watch.{ident}.{key}")
                    continue
                if key not in WATCH_KEYS and key not in {"state", "relay_status", "relay"}:
                    if value not in (None, "", [], {}):
                        blockers.append(refusal(
                            f"watch.{ident}.{key}",
                            ", ".join(sorted(WATCH_KEYS)),
                            "rehome this text onto summary, detail, or evidence; the file was not written",
                        ))
                    else:
                        dropped.append(f"watch.{ident}.{key}")
            for key in ("summary", "detail", "evidence", "source", "next", "locator"):
                problem = _string_field(item.get(key), f"watch.{ident}.{key}", "string")
                if key in item and problem:
                    blockers.append(problem)
            for key in WATCH_KEYS - {"kind", "status", "summary", "detail", "evidence", "source", "next", "locator", "presets"}:
                if key in item and item[key] is not None and not isinstance(item[key], str):
                    blockers.append(refusal(f"watch.{ident}.{key}", "string", "rehome current text; the file was not written"))
            if item.get("presets") is not None and not _string_list_ok(item["presets"]):
                blockers.append(refusal(f"watch.{ident}.presets", "array of preset ids", "keep exact affected ids; the file was not written"))
    return blockers, dropped


def delegator_migrated(doc: dict[str, Any]) -> tuple[dict[str, Any] | None, list[dict[str, str]], list[str]]:
    blockers, dropped = delegator_blockers(doc)
    if blockers:
        return None, blockers, dropped
    out: dict[str, Any] = {"schema": DELEGATOR_SCHEMA, "revision": int(doc.get("revision") or 0)}
    for key in ("updated_at", "project", "host", "authorization", "stop", "entry", "timer_owner", "cadence", "source",
                "day_start", "day_end", "final_stop"):
        if key not in doc:
            continue
        value = doc[key]
        allowed = {
            "day_start": DAY_START_KEYS, "day_end": DAY_END_KEYS, "final_stop": FINAL_STOP_KEYS,
        }.get(key)
        if isinstance(value, dict) and allowed is not None:
            for bag in LEGACY_BAG_KEYS:
                if bag in value:
                    dropped.append(f"{key}.{bag}")
            out[key] = {item: value[item] for item in allowed if item in value}
        elif key == "host" and isinstance(value, dict):
            for bag in LEGACY_BAG_KEYS:
                if bag in value:
                    dropped.append(f"host.{bag}")
            out[key] = {item: value[item] for item in DELEGATOR_HOST_KEYS if item in value}
        elif key == "project" and isinstance(value, dict):
            out[key] = {item: value[item] for item in DELEGATOR_PROJECT_KEYS if item in value}
        else:
            out[key] = value
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
    auth_out = out.get("authorization")
    if isinstance(auth_out, dict) and "retired_pool_grants" in auth_out:
        auth_out.pop("retired_pool_grants")
        dropped.append("authorization.retired_pool_grants")
    if "retired" in doc:
        dropped.append("retired")
    return out, [], sorted(set(dropped))


def host_changes(doc: dict[str, Any], after: int, through: int) -> dict[str, int]:
    """Each Host business change in (after, through], by its input id. A
    record the Host rewrote later shows only its latest change."""
    state = doc["state"]
    found: dict[str, int] = {}

    def take(ident: str, value: Any) -> None:
        if isinstance(value, int) and not isinstance(value, bool) and after < value <= through:
            found[ident] = value

    for kind in RECORD_KEYS:
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
        # Host goal, next, and verdict only. A node process write does not change this row.
        body = {"goal": task.get("goal"), "next": task.get("next"), "verdict": verdict.get("value")}
        text = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        found.append({"kind": "tasks", "id": task_id, "why": "delivery-open",
                      "content": hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]})
    if isinstance(task.get("transcribed"), dict):
        found.append({"kind": "tasks", "id": task_id, "why": "transcribed-check",
                      "host_turn": task["transcribed"].get("host_turn"),
                      "fields": task["transcribed"].get("fields")})
    return found


def _record_root() -> Path:
    """Same root as the Runner: explicit root, else ``XDG_RUNTIME_DIR``, else the process temp dir."""
    root = os.environ.get("KAOLA_ACP_RECORD_ROOT")
    if root:
        return Path(root)
    base = os.environ.get("XDG_RUNTIME_DIR") or tempfile.gettempdir()
    return Path(base) / f"kaola-{os.getuid()}"


def _repo_of_state_file(path: Path) -> Path:
    resolved = path.resolve()
    return resolved.parent.parent if resolved.parent.name == ".kaola" else resolved.parent


def _same_repo(stored: Any, repo: str) -> bool:
    if not isinstance(stored, str) or not stored:
        return False
    if os.path.normpath(stored) == os.path.normpath(repo):
        return True
    try:
        return Path(stored).resolve() == Path(repo).resolve()
    except OSError:
        return False


def _host_of(doc: dict[str, Any]) -> dict[str, str] | None:
    """Host identity already stored on this file's carrier. No new registry."""
    carrier = doc.get("carrier") if isinstance(doc.get("carrier"), dict) else None
    if carrier is None:
        return None
    platform, session, holder = (
        carrier.get("platform"), carrier.get("session"), carrier.get("holder_instance_id"))
    if not all(isinstance(item, str) and item for item in (platform, session, holder)):
        return None
    return {"platform": platform, "session": session, "holder_instance_id": holder}


def node_is_running(binding: Any, repo: Path | None, host: dict[str, str] | None) -> bool | None:
    """True only for this repo's ready Sideagent record dispatched by this Host.

    The path is ``<record root>/<platform>/<session>/<sha256(repo)[:16]>/record.json``.
    ``repo`` on that record and ``dispatcher`` must match this state file and its
    Host carrier. Another ready record that shares only the platform and session
    name does not count. False means no such live record. None means the record
    could not be read, or this file does not name a repo.
    """
    if not isinstance(binding, dict) or binding.get("mode") != "node":
        return None
    platform, session = binding.get("platform"), binding.get("session")
    if not isinstance(platform, str) or not isinstance(session, str):
        return False
    if repo is None:
        return None
    repo_text = str(repo)
    digest = hashlib.sha256(repo_text.encode("utf-8")).hexdigest()[:16]
    path = _record_root() / platform / session / digest / "record.json"
    try:
        if not path.is_file():
            return False
        record = json.loads(path.read_text(encoding="utf-8"))
    except OSError:
        return None
    except ValueError:
        return False
    if not isinstance(record, dict):
        return False
    if record.get("session_role") not in ("sideagent", "sidekick"):
        return False
    if record.get("platform") != platform or record.get("session") != session:
        return False
    if record.get("state") != "ready":
        return False
    if not _same_repo(record.get("repo"), repo_text):
        return False
    dispatcher = record.get("dispatcher")
    if (not isinstance(host, dict) or not isinstance(dispatcher, dict)
            or dispatcher.get("holder_instance_id") != host.get("holder_instance_id")
            or dispatcher.get("platform") != host.get("platform")
            or dispatcher.get("session") != host.get("session")
            or not _same_repo(dispatcher.get("repo"), repo_text)):
        return False
    pid = record.get("holder_pid")
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def delegator_file_view(doc: dict[str, Any]) -> dict[str, Any]:
    """Field-by-field view of the Delegator file. Unknown keys are locators."""
    unknown: list[dict[str, str]] = []

    def add(path: str) -> None:
        unknown.append({"path": path})

    for key in doc:
        if key not in DELEGATOR_TOP_KEYS:
            add(key)
    auth = doc.get("authorization") if isinstance(doc.get("authorization"), dict) else {}
    for key in auth:
        if key not in DELEGATOR_AUTH_KEYS:
            add(f"authorization.{key}")
    watch = doc.get("watch") if isinstance(doc.get("watch"), dict) else {}
    duties = []
    for ident, item in sorted(watch.items()):
        if ident in LEGACY_BAG_KEYS:
            add(f"watch.{ident}")
            continue
        if not isinstance(item, dict):
            add(f"watch.{ident}")
            continue
        for key in item:
            if key not in WATCH_KEYS and key not in {"state", "relay_status", "relay"}:
                add(f"watch.{ident}.{key}")
        duties.append({"id": ident, **{
            key: item[key] for key in WATCH_KEYS if key in item
            and (isinstance(item[key], str) or (key == "presets" and _string_list_ok(item[key])))
        }})
    host = doc.get("host") if isinstance(doc.get("host"), dict) else {}
    project = doc.get("project") if isinstance(doc.get("project"), dict) else {}
    auth_view = {}
    for key in DELEGATOR_AUTH_KEYS - {"retired_pool_grants"}:
        value = auth.get(key)
        if key in ("elite_grants", "expert_task_grants") and isinstance(value, list):
            auth_view[key] = [{field: item for field, item in grant.items()
                               if field in DELEGATOR_GRANT_KEYS and (
                                   isinstance(item, (str, int, bool))
                                   or (field == "preset_ids" and _string_list_ok(item))
                                   or (field == "special_requirements" and isinstance(item, dict)
                                       and not _closed_strings("special_requirements", item,
                                                               frozenset({"model", "effort", "task_scope"}))))}
                              for grant in value if isinstance(grant, dict)]
        elif key == "sideagent" and isinstance(value, dict):
            auth_view[key] = {field: item for field, item in value.items()
                              if field in DELEGATOR_SIDEAGENT_KEYS and isinstance(item, str)}
        elif key == "known_resource_limits" and isinstance(value, dict):
            auth_view[key] = {field: item for field, item in value.items() if isinstance(item, (str, int, float, bool))}
        elif isinstance(value, (str, int, bool)) or _string_list_ok(value):
            auth_view[key] = value
    problems, _ = delegator_blockers(doc)
    for problem in problems:
        if {"path": problem["path"]} not in unknown:
            add(problem["path"])
    return {
        "view": "delegator-file",
        "schema": doc.get("schema"),
        "revision": doc.get("revision"),
        "project": {key: project[key] for key in DELEGATOR_PROJECT_KEYS if isinstance(project.get(key), str)},
        "host": {key: host[key] for key in DELEGATOR_HOST_KEYS if isinstance(host.get(key), str)},
        "authorization": auth_view,
        "watch": duties,
        **{key: ({field: value[field] for field in allowed if isinstance(value.get(field), str)}
                  if isinstance(value, dict) else value if isinstance(value, str) else None)
           for key, allowed in (("day_start", DAY_START_KEYS), ("day_end", DAY_END_KEYS), ("final_stop", FINAL_STOP_KEYS))
           for value in [doc.get(key)]},
        "unknown": unknown,
    }


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
        if binding.get("mode") == "node":
            repo = _repo_of_state_file(path) if isinstance(path, Path) else None
            running = node_is_running(binding, repo, _host_of(doc))
            if running is True:
                view["sideagent_maintenance"] = "a node is running"
            elif running is False:
                view["sideagent_maintenance"] = (
                    "no node is running; an idle binding is not missing maintenance"
                )
            else:
                view["sideagent_maintenance"] = (
                    "node liveness was not read; a binding is not proof a node is running"
                )
        else:
            view["sideagent_maintenance"] = "binding present"
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


def injection_body(doc: dict[str, Any], path: Path | None = None) -> tuple[str | None, str | None]:
    """Projected Host view for a current state file. None means the caller keeps a legacy body."""
    if not isinstance(doc, dict) or doc.get("schema") != HOST_SCHEMA or not isinstance(doc.get("state"), dict):
        return None, None
    view = host_view(doc, path)
    body = json.dumps(view, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if len(body.encode("utf-8")) > HOST_VIEW_MAX_BYTES:
        return None, (
            f"projected Host view exceeds {HOST_VIEW_MAX_BYTES} bytes; retire finished "
            "records. The stored body was not injected."
        )
    return body, None
