verdict: DOCKED

Checked files:
- `README.md` — Worker-classes example sentence now names the exact preset
  IDs (`claude-code/default|sonnet|fable`); the Preset-catalog lead-in
  documents the Preset ID column, its grant/snapshot/relay use, and the
  configured-not-running caveat; the generated catalog region was regenerated
  by `render-skills.py --write` (`--check` PASS).
- `CHANGELOG.md` — Unreleased #218 entry with `Seats: restart not required`.
- `AGENTS.md` — project snapshot, constraints and release notes policy
  unaffected: the change adds notation on already-generated rows, not a new
  surface (no registry, validator, dispatch engine, seat, or timer).
- `docs/conventions.md`, `docs/architecture.md`, `docs/host-entry-evidence.md`,
  `docs/issue-dispatch-display.md` — describe layers this change does not
  alter — no impact.
- Generated `skills/` and `hosts/` output regenerated from templates only
  (never hand-edited); `templates/grok-golden/` frozen and untouched;
  operator-test paths (`scripts/kaola-acp-holder.py`,
  `scripts/kaola-zcode-acp.py`, `scripts/kaola-quota.py`,
  `scripts/adapters`, `platforms`) untouched.

No API, CLI, transport, setup, environment, or example change beyond the
documented notation rows and their focused suite.
