# Documentation docking — Issue #95

status: DOCKED

Checklist walked from `AGENTS.md` "Documentation Map" and the changed public behavior: the ACP
holder's reader loop now scopes a handler exception to one message, and `status` / `record.json`
carry a new `agent_message_errors` counter.

| file | checked | outcome |
|---|---|---|
| `CHANGELOG.md` | yes | FIXED. Unreleased entry added for Issue #95, then corrected in round 2 to describe the trigger as a malformed ACP `session/update` rather than "legal JSON-RPC by-position params". |
| `docs/runner-v2-dual-transport-design.md` | yes | FIXED. §7.3's inbound-message table enumerates how each inbound class is handled and had no row for "a handler raised". One row added, transcribed from the code: the counter name `agent_message_errors`, the event shape `agent_message_error{method, id, error_type, at}`, the withholding of the raw message and `str(exc)`, the not-answered/not-retried/not-approved semantics, and the best-effort recording (`EventLog.append` absorbs `OSError`; the counter is incremented first). |
| `docs/api.md` | yes | NO IMPACT. "Status compatibility" documents the tmux/PTY status keys and the ACP receipt bounding; it does not enumerate the holder's own counters — the existing siblings `malformed_stdout_lines` and `unknown_update_variants` are absent from it too (`grep` returns nothing). Adding a third sibling there would document one counter and not its two peers. |
| `docs/architecture.md` | yes | NO IMPACT. Describes the holder's place in the transport, not the reader loop's failure semantics. |
| `README.md` | yes | NO IMPACT. Four-tier entry and usage; no reader-loop or status-field surface. |
| `docs/acp-watch/*` | yes | NO IMPACT. Projection/permit-lock/list-view surfaces; unchanged by this diff. |
| `skills/`, `hosts/grok-bot/` | yes | GENERATED, never hand-edited. `render-skills.py --write` then `--check` => PASS; the holder change is propagated into the nine `skills/*/scripts/kaola-acp-holder.py` copies. |

No invented fields: every name above was transcribed from `scripts/kaola-acp-holder.py` at this
candidate, and the event shape was additionally observed live
(`{"kind":"agent_message_error","method":"session/update","id":null,"error_type":"AttributeError","at":"kaola-acp-holder.py:1578"}`).
