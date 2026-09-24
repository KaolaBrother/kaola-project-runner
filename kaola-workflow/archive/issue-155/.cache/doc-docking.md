# Documentation docking — issue-155

Candidate: 9eb28d0 on workflow/issue-155 (parent 26cee00 == main == origin/main).

Checked files:
- docs/api.md — FIXED (this run's deliverable): the opencode steering note now names `acp_verified_versions` 2.0.15 (record-only since the 2026-09-24 Pink batch) and keeps the dated 1.18.17 `-32601` probe and the 2.0.11 `initialize` observation. That was the only "2.0.11 as the current record" line in docs/api.md (grep for 2.0.11, 2.0.15, 1.18.17).
- platforms/opencode.yaml — NO IMPACT: it is already the source of truth (`cli=2.0.15`; its steering_summary already names 2.0.15 as the un-probed record). Out of scope for this run.
- CHANGELOG.md — NO IMPACT: the #153 Unreleased entry already records the opencode `cli=2.0.15` record and its steering summary. #155 is a docs-consistency sync with no user-visible behavior change.
- README.md, AGENTS.md, docs/architecture — NO IMPACT: no public API, setup, command, or behavior changed.
- skills/, hosts/ (generated) — NO IMPACT: docs/ is not a rendered surface; render-skills.py --check rc=0.

DOCKED
