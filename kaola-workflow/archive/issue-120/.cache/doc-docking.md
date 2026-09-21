# Documentation docking — issue-120 (candidate e003029)

Checked against changed public behavior (start-failure receipt fields, ps fallback, dsh default permission mode):

- CHANGELOG.md — two #120 entries added (facts + libproc stop; dsh default mode). Fixed.
- README.md — dsh operator brief and the per-platform permission paragraph corrected (DSH_PERMISSION_MODE default, caller override, /tmp correction). Fixed.
- platforms/dsh.yaml (launch_summary, acp_quirks) → generated skills/dsh-kaola-project-runner/references/acp.md, platform.md, scripts/platform.yaml via render --write; render --check PASS, budgets OK. Fixed.
- templates/ (main Skill, worker template) — no dsh permission or receipt-field claim; no impact.
- docs/runner-v2-dual-transport-design.md — already documents `error: {code, message, stderr_tail}`; the start path now matches it; no change needed.
- API/architecture docs, examples, setup, environment — no other surface names DSH_PERMISSION_MODE, seatbelt_confined, or the ps dependency; no impact.

DOCKED
