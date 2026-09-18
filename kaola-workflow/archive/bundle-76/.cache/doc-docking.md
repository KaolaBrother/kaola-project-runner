# Documentation docking — bundle-76 (Issue #76)

verdict: DOCKED
candidate: 1b46b6f (docs commit atop accepted 4f7d83d)

## Checked files

- `CHANGELOG.md` — **fixed**: Unreleased entry added for the permission_required
  mid-turn wake (docs: dock commit `1b46b6f`), matching the Issue #70/#73 docking
  convention.
- `docs/zcode-host.md` — **docked with the candidate** (`4f7d83d`): the Events
  bullet now names the third worker-event source (`permission_required`, once per
  new pending key, `request_id` the only locator, ordinary `idle` still at turn
  end) and the Payload bullet records the optional `request_id` field.
- `docs/api.md` — **no impact**: it documents the public CLI surface and settle
  semantics for `permit`/`cancel`/`stop`; the `worker_event` op is an internal
  holder-to-holder carrier documented in `docs/zcode-host.md`, and the settle
  contract it does state (one answer per `request_id`) is unchanged.
- `README.md` — **no impact**: it delegates ZCode Host mechanics to
  `docs/zcode-host.md` and names no event kinds.
- `docs/architecture.md`, `docs/conventions.md`, `docs/decisions/` — **no
  impact**: no event-kind or permission-pipeline claims exist there; the
  carrier architecture statement in `zcode-host.md` remains the canonical one.
- `templates/orchestrator/references/zcode-host-dispatch.md.tmpl` +
  `heartbeat-skeleton.txt` — **docked with the candidate**: Host-facing
  guidance for the new kind lives in the generated references (rendered copies
  verified by `render-skills.py --check`, 8,183 B < 8,192 B budget).

## Live-verification honesty note (required by ACCEPT)

The real-path evidence (`evidence/20-*`, `21-*`, `22-*`) records a REAL droid
0.220.0 worker (`droid exec --output-format acp`, `--mode manual`) raising a
genuine `session/request_permission`, the real holder/carrier/permit path
delivering `permission_required` and settling it — but the Host-side agent
process was the **fake zcode app-server**: no real zcode binary exists on this
machine, so no real ZCode model reply is claimed anywhere.
