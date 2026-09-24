# Doc docking — bundle-153 (Issue #153)

Checked against the AGENTS.md documentation checklist for this record-only admission (no public
API, command, install, architecture, environment, or validation behavior changed):

- CHANGELOG.md — UPDATED: one `## Unreleased` entry covering the Codex pin move (0.156.1 /
  1.13.1 with honest record-only provenance and the #145 supersession), the zcode-acp 0.47.x
  precheck conclusion, and the four optional records. Dated 0.5.9/0.6.0 sections left untouched
  by design (dated fact).
- docs/harness-acp-compat-2026-09-24.md — NEW: the class-2 admission evidence doc (pins and
  provenance, precheck with what was and was not verified, optional records, bridge
  content-stage reset, validation receipts, `.kaola` receipt pointer).
- README.md — NO IMPACT: no install, usage, or architecture change; README pins no CLI versions
  (grep over README for every moved version: zero hits).
- docs/api.md — NO CHANGE THIS RUN; one stale attribution recorded and filed: #155. Line ~450
  still says opencode's `acp_verified_versions` "names 2.0.11" while the record now says
  2.0.15. The surrounding capability claim stays correct (native steering `unknown`, manifest
  declared the single source of truth in the same paragraph) and the #88 test needles
  (`1.18.17`, `2.0.11`, `steer-capability-unknown`) still pass. Fixing it here would mutate the
  Host-accepted frozen candidate 7d8bce7, so it is filed instead of patched.
- docs/architecture.md, docs/conventions.md — NO IMPACT: no architecture or convention change.
- AGENTS.md — NO IMPACT: commands, constraints, and the release-pin note are unchanged (the
  bridge pin note concerns a future release; this run explicitly cuts none).
- Generated surfaces — REGENERATED ONLY: `skills/` and `hosts/grok-bot/` changed exclusively
  through `render-skills.py --write`, never hand-edited; `render-skills.py --check` PASS
  (budgets OK, content stage).

DOCKED
