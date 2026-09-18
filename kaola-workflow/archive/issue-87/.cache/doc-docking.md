# Documentation docking — Issue #87

status: DOCKED
candidate: 06091ca176cc2a9e68d99933cf36098176801767
changed public behavior: ZCode Host heartbeat overflow full-check (32-cap,
monotonic generation, remind-only, resume/rotation seed, idle-full delivery)
and 64KiB bounded heartbeat-prompt.json read. Holder/event-log only. No CLI
flag, schema, second queue, scheduler, or adapter change.

## Files checked

- `docs/zcode-host.md` — FIXED in the candidate. States the 32 detailed-event
  cap, overflow full-check generation, remind-only approvals, idle-full
  immediate delivery, restore max + seed-at-least-confirmed (rotation),
  65536-byte prompt-file bound, and drops the old no-event-loss claim.
- `CHANGELOG.md` — FIXED in the candidate. Unreleased Issue #87 bullet matches
  the holder. Rebase onto `db7939e` kept the Issue #86 unspecified-quota
  bullet immediately below it.
- `docs/README.md` — no impact. Index already links `zcode-host.md` for the
  event-driven heartbeat carrier and prompt-file defect receipt.
- `README.md` — no impact. Four-tier entry does not describe the 32-event
  staging list.
- `AGENTS.md` — no impact. Documentation map and validation commands
  unchanged (`render-skills.py --check`, `validate.sh`).
- `docs/api.md`, `docs/architecture.md`, `docs/conventions.md`,
  `docs/grok-bot-host.md` — no impact. No file claimed unbounded
  heartbeat-prompt injection or lossless 33rd-event replay. Holder socket op
  `worker_event` is documented in `docs/zcode-host.md`.
- `docs/decisions/` — no impact. No new architectural decision (no second
  queue, scheduler, or quota system).
- `templates/grok-golden/` — frozen; `git diff --quiet HEAD -- templates/grok-golden`.
- Generated `skills/*/scripts/kaola-acp-holder.py` — renderer copies of
  `scripts/kaola-acp-holder.py`; `./scripts/render-skills.py --check` PASS.

DOCKED
