# Documentation Docking — Issue #173

Status: DOCKED

Checked against `AGENTS.md`'s documentation checklist for changed public behavior.

| Surface | Decision | Reason |
|---|---|---|
| `CHANGELOG.md` | **Updated** | Unreleased entry added for the holder behavior change, stating `Seats: restart required` — the operator test `git diff OLD NEW -- scripts/kaola-acp-holder.py scripts/kaola-zcode-acp.py scripts/kaola-quota.py scripts/adapters platforms` is non-empty because `scripts/kaola-acp-holder.py` changed. |
| `docs/api.md` | No change | The fix introduces no new receipt field, schema, error code namespace, or vocabulary. `turn_failed` is a pre-existing `turn_ended` outcome; the receipt `error` object and `status`/`observe`'s `turn_outcome` already existed. `docs/api.md` documents no turn-outcome field, so there is no wording there that this change makes wrong. |
| `docs/zcode-host.md` | No change | Describes ZCode host heartbeat/outcome flow; no ZCode behavior changed (the guard is codex-`threadStatus`-gated and inert elsewhere). |
| `docs/conventions.md` | No change | The seat-restart convention is satisfied by the CHANGELOG entry; the convention text itself did not change. |
| `AGENTS.md` | No change | No command, installation step, validation policy, or constraint changed. |
| `README.md` | No change | No setup, usage, or entry-tier behavior changed. |
| `docs/architecture*.md` | No change | The holder's role is unchanged; this reads one additional existing ACP field within the same turn lifecycle. |

Public behavior documented: the CHANGELOG entry names the observable outcome change
(`turn_completed` → `turn_failed`), the receipt `error.code` (`agent-system-error`), the
unchanged verbatim `stop_reason` (#113), the events-stay-staged/redelivery behavior, and the
no-change boundary for non-codex platforms and healthy codex turns.

No invented fields, signatures, or schema were transcribed.
