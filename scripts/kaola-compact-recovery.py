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

Accepted shapes and their positive source locators:

* Codex adapter 2.0.1, `createCompactionUpdate`, emits ``compaction_update``
  with status exactly ``completed`` only when the client advertises
  ``clientCapabilities.session.compaction``
  (``@agentclientprotocol/codex-acp/dist/index.js``, `clientSupportsCompaction`
  and `createCompactionUpdate`; status union in the ACP schema).
* OpenCode 2.0.22, the located handler, emits through `ji` a
  ``session_info_update`` whose ``_meta["opencode/compaction"]`` marker is
  ``{status, messageId, reason[, error]}``. `session.compaction.ended` emits
  ``status:"completed"`` with the started ``messageId``; the history-replay
  generator `uu` also emits an entry whose status is not ``running``
  (``opencode` binary offset 119677809 region, `mu` and `ji`). The resume
  replay is the reason the holder also needs a ready-state guard.
* Devin 3000.11.3 emits the ACP notification ``_cognition.ai/compaction`` with
  ``params.sessionId`` and ``params.status``; the measured completed value is
  ``completed``.
* Grok 1.0.46 emits ``x.ai/session_notification`` (wire
  ``_x.ai/session_notification``) with ``params.update.sessionUpdate ==
  "auto_compact_completed"``. The installed binary proves the notification is
  matched by session id ("load-race: x.ai/session_notification DROPPED - no
  agent matches session_id"), so a completion must carry that session id.
* ZCode 3.14.3 emits compact completion on the engine stream; the ZCode bridge
  maps it onto ``compaction_update``. This module only reads the ACP side.
* Kimi Code CLI 2.1.1, the built-in ``kimi acp`` server, maps engine
  ``compaction.completed`` onto one local ``agent_message_chunk`` whose text is
  exactly ``Compaction completed.\\n- Messages compacted: <n>\\n- Tokens before:
  <n>\\n- Tokens after: <n>`` (``AcpSession.onCompactionCompleted`` ->
  ``emitLocalChunk`` -> ``formatCompactionCompleted`` in the installed binary).
  Its update union has no ``compaction_update`` variant, ``session_info_update``
  carries a title only, and the engine ``PostCompact`` hook is fire-and-forget,
  so this chunk is the only ACP-side completion carrier. The exact-shape match
  separates the runtime's own marker from assistant prose; a model could still
  emit the identical four lines, and the reload it then triggers is the
  harmless instruction by design. This rule applies only for the ``kimi-cli``
  platform when a platform is supplied.

Every accepted source requires a non-empty session id. A payload without one is
not accepted; the holder cannot prove its transport scope.
"""

from __future__ import annotations

import re
from typing import Any, Mapping, Optional

# ACP ``session/update`` variants that name a compaction.
COMPACTION_UPDATE = "compaction_update"
SESSION_INFO_UPDATE = "session_info_update"
AGENT_MESSAGE_CHUNK = "agent_message_chunk"

# The Kimi acp completed marker is this exact four-line text, no more and no
# less; ``toLocaleString("en-US")`` writes counts with comma groups.
KIMI_PLATFORM = "kimi-cli"
KIMI_COMPLETED_RE = re.compile(
    r"Compaction completed\.\n"
    r"- Messages compacted: [0-9,]+\n"
    r"- Tokens before: [0-9,]+\n"
    r"- Tokens after: [0-9,]+")

# Native notification methods that carry a compact completion.
DEVIN_COMPACTION_METHOD = "_cognition.ai/compaction"
GROK_NOTIFICATION_METHODS = ("_x.ai/session_notification", "x.ai/session_notification")

# The OpenCode marker key inside ``session_info_update._meta``.
OPENCODE_COMPACTION_META = "opencode/compaction"
OPENCODE_CHILD_META = "opencode/child-session"

# Only this exact status is a completed compaction. No aliases: the inspected
# sources use ``completed`` verbatim.
COMPLETED_STATUS = "completed"

# Grok's completed nested update name.
GROK_COMPLETED_UPDATE = "auto_compact_completed"


class CompactSignal:
    """One recognized completed compaction.

    ``source`` names the wire rule that matched. ``session_id`` is the ACP
    session that carried the signal. It is always non-empty for an accepted
    signal. ``occurrence_id`` is a stable per-occurrence token when the runtime
    sends one, else ``None``.
    """

    __slots__ = ("source", "session_id", "occurrence_id")

    def __init__(self, source: str, session_id: str,
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


def _completed(update: Mapping[str, Any]) -> bool:
    """The exact, positively sourced completed status."""
    status = update.get("status")
    return status == COMPLETED_STATUS


def _marker_occurrence(marker: Mapping[str, Any]) -> Optional[str]:
    """The OpenCode per-occurrence id, when the marker carries one."""
    return _text(marker.get("messageId")) or _text(marker.get("id"))


def classify(message: Any, platform: Optional[str] = None) -> Optional[CompactSignal]:
    """Classify one inbound ACP message or one ``events.jsonl`` record.

    Return a :class:`CompactSignal` for a real completed compaction, else
    ``None``. Only a raw JSON-RPC message (``{"method": ..., "params": ...}``)
    or an ``events.jsonl`` record is accepted. A bare payload without a method
    or a record kind has no proven transport scope and is rejected.

    ``platform`` distinguishes a runtime-local rule where one is available. The
    Kimi text marker rule applies only when ``platform`` is ``None`` (an
    offline controller reading a record) or ``"kimi-cli"``. A model could echo
    the identical four lines in another runtime; the platform gate keeps that
    from waking a non-Kimi session.
    """
    if not isinstance(message, Mapping):
        return None

    # An ``events.jsonl`` record wraps the wire message.
    if "kind" in message and "method" not in message and "sessionUpdate" not in message:
        kind = message.get("kind")
        if kind == "session_update":
            return _from_session_update({"sessionId": message.get("sessionId"),
                                         "update": message.get("update") or {}},
                                        platform)
        if kind == "notification":
            return _from_notification({"method": message.get("method"),
                                       "params": message.get("params") or {}})
        return None

    method = message.get("method")
    if method == "session/update":
        params = message.get("params")
        return _from_session_update(params if isinstance(params, Mapping) else {},
                                    platform)
    if isinstance(method, str):
        return _from_notification(message)
    return None


def _from_session_update(params: Mapping[str, Any],
                         platform: Optional[str] = None) -> Optional[CompactSignal]:
    update = params.get("update")
    if not isinstance(update, Mapping):
        return None
    variant = update.get("sessionUpdate")
    # Every accepted source is session-scoped. No session id, no proof.
    session_id = _text(params.get("sessionId"))
    if session_id is None:
        return None

    if variant == COMPACTION_UPDATE:
        if not _completed(update):
            return None
        return CompactSignal("acp-compaction-update", session_id,
                             _text(update.get("compactionId")))

    if variant == SESSION_INFO_UPDATE:
        meta = update.get("_meta")
        if not isinstance(meta, Mapping):
            return None
        # A child-session update is a different session's work even when it
        # names this session id; never let it wake this session.
        if OPENCODE_CHILD_META in meta:
            return None
        marker = meta.get(OPENCODE_COMPACTION_META)
        if not isinstance(marker, Mapping):
            return None
        if not _completed(marker):
            return None
        return CompactSignal("opencode-compaction-meta", session_id,
                             _marker_occurrence(marker))

    if variant == AGENT_MESSAGE_CHUNK:
        if platform is not None and platform != KIMI_PLATFORM:
            return None
        return _from_kimi_chunk(update, session_id)

    return None


def _from_kimi_chunk(update: Mapping[str, Any],
                     session_id: str) -> Optional[CompactSignal]:
    """The kimi acp completed marker: one local text chunk, exact shape.

    ``onCompactionStarted``, ``compaction.cancelled``, and
    ``compaction.blocked`` emit different fixed sentences, so they can never
    match this full match. The wire does not mark the chunk as runtime-local;
    the exact shape and the caller's platform gate are the distinction.
    """
    content = update.get("content")
    if not isinstance(content, Mapping):
        return None
    if content.get("type") != "text":
        return None
    text = content.get("text")
    if not isinstance(text, str) or KIMI_COMPLETED_RE.fullmatch(text) is None:
        return None
    return CompactSignal("kimi-compaction-chunk", session_id, None)



def _from_notification(message: Mapping[str, Any]) -> Optional[CompactSignal]:
    method = message.get("method")
    params = message.get("params")
    if not isinstance(params, Mapping):
        return None
    session_id = _text(params.get("sessionId"))
    if session_id is None:
        return None

    if method == DEVIN_COMPACTION_METHOD:
        if not _completed(params):
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

    ``session_id`` is the holder's own ACP session id. An accepted signal always
    carries a session id, so a holder that has not yet established its session
    must not accept one (this also blocks resume/history replay).
    """
    return session_id is not None and signal.session_id == session_id


def reload_instruction(skill_path: Optional[str] = None) -> str:
    """The one instruction that satisfies the behavior.

    It names no cached body. With ``skill_path`` it names the installed
    platform Skill file. It never asks the model to restart, cancel, or replay.
    """
    if skill_path:
        reopen = (f"completely re-read the current installed Skill(s) that this "
                  f"session is actively using - your role/task Skill (for "
                  f"example Workflow Next when it is active) and the installed "
                  f"platform Skill at {skill_path} - from their installed "
                  f"directories, not from memory or a cached copy. ")
    else:
        reopen = ("completely re-read the current installed Skill(s) that this "
                  "session is actively using - your role/task Skill (for "
                  "example Workflow Next when it is active) and your installed "
                  "platform Skill - from their installed directories, not from "
                  "memory or a cached copy. ")
    return ("The runtime context was compacted. Before you continue, " + reopen
            + "Then continue the in-progress task from the durable project "
            "records, exactly where it stopped. Do not restart completed work.")


def host_reload_prompt(host_entry: str) -> str:
    """Reload prompt for a Host session.

    The first line is the session's own measured native Skill entry, so the
    runtime opens the Skill the same way it does on any other turn.
    """
    entry = (host_entry or "").strip()
    body = reload_instruction()
    if not entry:
        return body
    return f"{entry}\n{body}"


def worker_reload_prompt(skill_path: Optional[str]) -> str:
    """Reload prompt for a non-Host session.

    A worker's applicable Skill is whatever role/task Skill the session is
    actively running (including Workflow Next), plus its installed platform
    Skill. Name the known platform Skill file and require the active role/task
    Skill too. Never open the Host control-plane entry in a worker session, and
    never promote a worker to a Host.
    """
    return reload_instruction(skill_path=skill_path)


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

    def mark_delivered_occurrence(self, occurrence: Optional[str]) -> None:
        """Record one delivery that may race a newer pending signal.

        ``occurrence`` is the id that was actually delivered. If it is still the
        newest pending id, clear the pending flag. If a newer signal arrived
        during admission, keep that newer obligation pending so it gets its own
        later delivery instead of being lost.
        """
        if occurrence is not None:
            self.last_delivered_id = occurrence
        if self.pending_id == occurrence:
            self.pending = False
            self.pending_id = None
