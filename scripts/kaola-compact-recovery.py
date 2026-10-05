#!/usr/bin/env python3
"""Issue #264: recognize a completed context compaction and build one reload.

This module decides two things only:

1. Is this inbound ACP message a real, session-bound, completed compaction
   signal?
2. What is the one harmless instruction that makes the agent re-read the
   current installed Skill and continue the task?

It holds no timer, no queue, no scheduler, and no history store. It does not
start, cancel, or restart any session. The ACP holder imports it. A controller
can also run the same predicate over an ``events.jsonl`` record.

Keep these facts separate. A source event is not ACP exposure. Exposure is not
delivery. Delivery is not a model reread. Only a real completed signal starts
the reload. Never use a start, a failure, a token drop, or assistant prose.

The recognition rules come from the reused original evidence:

* Codex adapter 2.0.1 emits ``compaction_update`` with ``status == "completed"``
  only when the client advertises ``clientCapabilities.session.compaction``.
* OpenCode 2.0.22 emits ``session_info_update`` with the
  ``_meta["opencode/compaction"]`` marker; the completed marker carries the
  per-occurrence ``messageId``.
* Devin 3000.11.3 emits the ACP notification ``_cognition.ai/compaction`` with
  ``status == "completed"``. That payload carries no per-occurrence token.
* Grok 1.0.46 emits the ACP notification ``x.ai/session_notification`` (the wire
  form is ``_x.ai/session_notification``) with the nested update
  ``auto_compact_completed``. That payload carries no per-occurrence token.
* ZCode 3.14.3 emits compact completion on the engine stream; the ZCode bridge
  maps it onto ``compaction_update``. This module only reads the ACP side.

A signal without a per-occurrence token is still a real completed signal. The
reload instruction is harmless and coalesces through the existing holder
cursor, so no exactly-once gate is needed.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional

# ACP ``session/update`` variants that name a compaction.
COMPACTION_UPDATE = "compaction_update"
SESSION_INFO_UPDATE = "session_info_update"

# Native notification methods that carry a compact completion.
DEVIN_COMPACTION_METHOD = "_cognition.ai/compaction"
GROK_NOTIFICATION_METHODS = ("_x.ai/session_notification", "x.ai/session_notification")

# The OpenCode marker key inside ``session_info_update._meta``.
OPENCODE_COMPACTION_META = "opencode/compaction"

# Only these statuses are a completed compaction.
COMPLETED_STATUSES = frozenset({"completed", "complete", "compacted"})

# Grok's completed nested update name.
GROK_COMPLETED_UPDATE = "auto_compact_completed"


class CompactSignal:
    """One recognized completed compaction.

    ``source`` names the wire rule that matched. ``session_id`` is the ACP
    session that carried the signal, or ``None`` when the payload omits it.
    ``occurrence_id`` is a stable per-occurrence token when the runtime sends
    one, else ``None``.
    """

    __slots__ = ("source", "session_id", "occurrence_id")

    def __init__(self, source: str, session_id: Optional[str],
                 occurrence_id: Optional[str]) -> None:
        self.source = source
        self.session_id = session_id
        self.occurrence_id = occurrence_id

    def __repr__(self) -> str:  # pragma: no cover - diagnostic only
        return (f"CompactSignal(source={self.source!r}, "
                f"session_id={self.session_id!r}, "
                f"occurrence_id={self.occurrence_id!r})")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CompactSignal):
            return NotImplemented
        return (self.source, self.session_id, self.occurrence_id) == (
            other.source, other.session_id, other.occurrence_id)


def _text(value: Any) -> Optional[str]:
    """Return a non-empty string, else ``None``. Never invent a value."""
    if isinstance(value, str) and value:
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    return None


def _completed_status(value: Any) -> bool:
    return isinstance(value, str) and value.strip().lower() in COMPLETED_STATUSES


def _marker_occurrence(marker: Mapping[str, Any]) -> Optional[str]:
    """The OpenCode per-occurrence id, when the marker carries one."""
    return _text(marker.get("messageId")) or _text(marker.get("id"))


def classify(message: Any) -> Optional[CompactSignal]:
    """Classify one inbound ACP message or one ``session/update`` payload.

    Accept a raw JSON-RPC message (``{"method": ..., "params": ...}``), a bare
    ``session/update`` params object, or an ``events.jsonl`` record. Return a
    :class:`CompactSignal` for a real completed compaction, else ``None``.
    """
    if not isinstance(message, Mapping):
        return None

    # An ``events.jsonl`` record wraps the wire message.
    if "kind" in message and "method" not in message and "sessionUpdate" not in message:
        kind = message.get("kind")
        if kind == "session_update":
            return _from_session_update({"sessionId": message.get("sessionId"),
                                         "update": message.get("update") or {}})
        if kind == "notification":
            return _from_notification({"method": message.get("method"),
                                       "params": message.get("params") or {}})
        return None

    method = message.get("method")
    if method == "session/update":
        params = message.get("params")
        return _from_session_update(params if isinstance(params, Mapping) else {})
    if isinstance(method, str):
        return _from_notification(message)

    # A bare update payload without a wrapper.
    if "sessionUpdate" in message:
        return _from_session_update({"update": message})
    return None


def _from_session_update(params: Mapping[str, Any]) -> Optional[CompactSignal]:
    update = params.get("update")
    if not isinstance(update, Mapping):
        return None
    variant = update.get("sessionUpdate")
    session_id = _text(params.get("sessionId"))

    if variant == COMPACTION_UPDATE:
        if not _completed_status(update.get("status")):
            return None
        return CompactSignal("acp-compaction-update", session_id,
                             _text(update.get("compactionId")))

    if variant == SESSION_INFO_UPDATE:
        meta = update.get("_meta")
        if not isinstance(meta, Mapping):
            return None
        marker = meta.get(OPENCODE_COMPACTION_META)
        if not isinstance(marker, Mapping):
            return None
        if not _completed_status(marker.get("status")):
            return None
        return CompactSignal("opencode-compaction-meta", session_id,
                             _marker_occurrence(marker))

    return None


def _from_notification(message: Mapping[str, Any]) -> Optional[CompactSignal]:
    method = message.get("method")
    params = message.get("params")
    if not isinstance(params, Mapping):
        return None
    session_id = _text(params.get("sessionId"))

    if method == DEVIN_COMPACTION_METHOD:
        if not _completed_status(params.get("status")):
            return None
        return CompactSignal("devin-compaction", session_id, None)

    if method in GROK_NOTIFICATION_METHODS:
        update = params.get("update")
        if not isinstance(update, Mapping):
            return None
        if update.get("sessionUpdate") != GROK_COMPLETED_UPDATE:
            return None
        return CompactSignal("grok-auto-compact-completed", session_id, None)

    return None


def is_same_session(signal: CompactSignal, session_id: Optional[str]) -> bool:
    """True when the signal belongs to this holder's own session.

    A payload that omits ``sessionId`` is not foreign; the holder already
    scopes such updates to its live session. A payload with a different
    session id is a child thread and must not wake this session.
    """
    return signal.session_id is None or signal.session_id == session_id


def reload_instruction() -> str:
    """The one instruction that satisfies the behavior.

    It names no cached body and relies on the installed directory. It never
    asks the model to restart, cancel, or replay an unknown mutation.
    """
    return (
        "The runtime context was compacted. Before you continue, completely "
        "re-read the current installed Skill for your role from its installed "
        "directory, not from memory or a cached copy. Then continue the "
        "in-progress task from the durable project records, exactly where it "
        "stopped. Do not restart completed work."
    )


def reload_prompt(host_entry: str) -> str:
    """Build the full reload prompt for one holder.

    The first line is the session's own measured native Skill entry, so the
    runtime loads the Skill the same way it does on any other turn. The
    instruction follows.
    """
    entry = (host_entry or "").strip()
    body = reload_instruction()
    if not entry:
        return body
    return f"{entry}\n{body}"


class CompactReloadTracker:
    """The smallest pending-reload state: one flag and one scalar.

    The flag coalesces several completed signals into at most one pending
    reload. The scalar suppresses an adjacent duplicate that carries the same
    occurrence id. It does not keep a set and does not keep history. A signal
    without an occurrence id never suppresses a later real completion.
    """

    def __init__(self) -> None:
        self.pending = False
        self.pending_id: Optional[str] = None
        self.last_delivered_id: Optional[str] = None

    def observe(self, signal: Optional[CompactSignal]) -> bool:
        """Record one recognized signal. Return True when a reload is owed.

        A duplicate occurrence returns False while a reload is still pending
        or already delivered. A new occurrence or an unknown occurrence
        returns True.
        """
        if signal is None:
            return False
        occurrence = signal.occurrence_id
        if occurrence is not None and occurrence == self.last_delivered_id:
            return False
        self.pending = True
        self.pending_id = occurrence
        return True

    def take_pending(self) -> bool:
        """Return and clear the pending flag."""
        pending = self.pending
        self.pending = False
        return pending

    def mark_delivered(self) -> None:
        """Clear the pending flag and remember the delivered occurrence id.

        The scalar is never cleared. An identity-less signal leaves the scalar
        untouched, so it can never suppress a later occurrence.
        """
        if self.pending_id is not None:
            self.last_delivered_id = self.pending_id
        self.pending = False
        self.pending_id = None
