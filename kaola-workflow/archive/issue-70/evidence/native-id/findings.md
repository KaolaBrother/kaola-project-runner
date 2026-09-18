# Issue #70 — where the ZCode native `sess_*` really comes from (2026-09-18)

Review comment 5728867190 said the recovery step sourced `--resume <native session id>` from
`session_meta`, which is wrong for ZCode. Checked in the source and then measured, values taken
from the raw event rather than from prose.

## Source of truth

- `scripts/kaola-zcode-acp.py:739` `emit_session_identity()` publishes
  `session/update {"sessionUpdate": "native_session_identity", "acpSessionId": …,
  "nativeSessionId": sess_*}` when the backend session materialises.
- `scripts/kaola-acp-holder.py` logs every `session/update` in its event log; `session_meta` is
  only ever the result of `session/new` (`:1293`), `session/load` (`:1334`) or a resume
  (`:1379`), so nothing copies the native id into it.
- `tests/contract/test-zcode-acp-contract.py:1096` already recorded the timing: "Materialize is
  lazy: the identity update appears on the first prompt."

## Measured on the candidate (deterministic harness, fake app-server)

`evidence/native-id/probe-source-of-native-id.py`, run against the candidate:

```
start session_meta: null
start acp_session_id: zcode-1
identity events: [{"cursor": 3, "kind": "session_update", "sessionId": "zcode-1",
  "update": {"acpSessionId": "zcode-1", "nativeSessionId": "sess_fake1",
             "sessionUpdate": "native_session_identity"}}]
native id: sess_fake1
observe session_meta: {"configOptions": [...]}      # no sess_* anywhere
resume state: ready err: None                       # start --resume sess_fake1
```

A second probe confirmed the operation the guidance names: `capture --since 0` surfaces that
identity update (`has native id in capture: True`), while `status` carries no event-log pointer.

## What changed in the candidate

- `zcode-host-dispatch.md` recovery step 3: `--resume` needs the real native id — ZCode reports
  `sess_…` in that session's `native_session_identity` event (via `capture`), not `session_meta`;
  no verified id means restart without history and say so, never `acp_session_id` or `--continue`.
- `host-startup.md`: the platform sourcing rule, including that the id exists only once the
  session has run a turn, that a fresh session carries the bridge `zcode-N` id in `session_meta`,
  and that other platforms may publish theirs there.
- `docs/zcode-host.md`: the same fact in the mechanism doc.
- `tests/contract/test-issue-70-binding-fact.py`: a new test that reads the id from the raw event,
  proves `session_meta` does not carry it, that `capture` surfaces it, and that the id taken from
  the event actually resumes the session (12 checks).

Codex, by contrast, does publish its native id in `session_meta` — that is what the earlier live
run used successfully — which is why the wording is "the platform's real native id", not a single
hard-coded location.
