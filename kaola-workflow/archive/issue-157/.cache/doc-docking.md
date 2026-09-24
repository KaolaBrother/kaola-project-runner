# Documentation docking — issue-157 (candidate f3351e9)

Checked against the frozen candidate's real behavior:

- CHANGELOG.md — FIXED: Unreleased entry for the #156/#157 Skill-prompt landing added (f3351e9); the codex narrative move entry (W4) kept.
- README.md — FIXED: Host entry evidence pointer now names docs/host-entry-evidence.md (the loaded matrix keeps entries/roots only).
- docs/api.md — FIXED: required manifest keys login_summary / permission_summary (W-A10/W-A11) documented; `references/host-entry-matrix.md` host_skill_entry table reference still true.
- docs/README.md — FIXED in 15ad5c5: indexes docs/host-entry-evidence.md and docs/issue-dispatch-display.md.
- docs/zcode-host.md — FIXED in 063cb42: S3 pre-binding recovery text kept verbatim.
- docs/host-entry-evidence.md, docs/issue-dispatch-display.md — NEW (15ad5c5), moved text verbatim from the loaded references.
- docs/architecture.md, docs/conventions.md — no impact: no statement about the edited prompt wording, Host roster, or manifest key list.
- AGENTS.md — no impact: its Layered entry and Runner contract remain true; no new verified project fact requires recording.
- docs/runner-v2-dual-transport-design-2026-09-11.md — no impact: historical design record (mentions self_hosting_risk as a 2026-09-11 design field; left as history).
- templates/grok-golden/, hosts/grok-bot/ — untouched by design (frozen / out of scope).

Status: DOCKED
