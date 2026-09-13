# Documentation docking — issue #25

Candidate: `e2b5b1c4f1a4bf082f4166d5e999124c1e6d9181`

Transcribed from `scripts/kaola-acp-holder.py` `_settle_pending_permission_locked` / `op_permit` (loser `error.code` `unknown-request`), `python3 scripts/kaola-acp.py grok permit --help` (command surface unchanged: `permit` / `--request-id` / `--option`), and `Issue25PermitLockTests` on that commit.

## Checked

- `README.md` — `permit` still available when an agent emits `request_permission`; same `request_id` at most one JSON-RPC result; second settler is `unknown-request`.
- `CHANGELOG.md` — Unreleased issue #25 bullet: permit/cancel/stop at-most-once under the prompt-admission lock; loser `unknown-request`; `session/cancel` unchanged; L0 keys unchanged. Watch freeze bullet now says #25 and #26 implemented, #27 not.
- `docs/api.md` — ACP command list still includes `permit`/`cancel`/`stop`; at-most-once settlement and `error.code` `unknown-request` transcribed next to that list.
- `docs/architecture.md` — permit lock (#25) and list/view (#26) implemented; follow (#27) not.
- `docs/acp-watch/README.md` and `permit-lock.md` — #25 no longer “未实现”; loser fact frozen as `unknown-request`.
- `docs/README.md` — index line: #25 permit lock and #26 list/view implemented, #27 not.
- Generated Skill `references/acp.md` (via `templates/references/acp.md.tmpl`) — `permit` / `cancel` / `stop` settle each permission `request_id` at most once; second settler is `unknown-request`. `./scripts/render-skills.py --check` PASS; no hand-edits of `skills/`.
- `templates/grok-golden/` — empty diff.
- `docs/runner-v2-dual-transport-design.md` — historical v0.3 PoC record; `permit --request-id` required when several pending remains true; not rewritten as if the PoC had the lock.
- `AGENTS.md` documentation map — README + CHANGELOG + `docs/` cover the public permit settlement fact.

## Verdict

DOCKED
