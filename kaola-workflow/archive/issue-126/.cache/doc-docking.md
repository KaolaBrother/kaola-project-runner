# Documentation docking — issue-126 (candidate adcb2e9)

- templates/orchestrator/references/host-entry-matrix.md (+ rendered copy) — FIXED: codex row `$kaola-project-runner` | E2; E2 / E2 | codex-acp 1.13.0; matrix date; codex note (measurement, worker choice, roots provenance, `$` quoting, Host carrier); fail-closed rule kept with "every shipped row has an entry since #126".
- templates/orchestrator/references/heartbeat-skeleton.txt (+ rendered) — FIXED (review F1): the prompt-file carrier is every Host's, the Codex timer carrier a non-Host Codex's. 8190/8192 B.
- docs/api.md — FIXED: `dispatcher-no-carrier` row no longer says "today codex".
- docs/zcode-host.md — FIXED: entry-less example no longer names codex.
- docs/codex-host.md — FIXED: intro names the ACP event-driven codex Host role and points to the matrix.
- CHANGELOG.md Unreleased — FIXED: Issue #126 entry (admission, evidence summary, unchanged #122 rule, skeleton wording, quoting).
- README.md — NO IMPACT: no Host-platform enumeration or codex-cannot-host statement (grep host-entry-matrix / "as a Host" / "measured entry"); the default install already targets ~/.codex/skills.
- templates/orchestrator/SKILL.md.tmpl — NO CHANGE: body byte-identical across the measured builds (anchor evidence depends on it); stale "nine" counts are pre-existing -> filed #150.
- templates/orchestrator/references/host-startup.md.tmpl, templates/kaola-delegator/references/handoff.md.tmpl — NO IMPACT: already say "its platform's host_skill_entry" generically.
- scripts/kaola-acp.py HOST_SKILL_ENTRIES comment — NO IMPACT: the empty-entry rule it describes still holds.

DOCKED
