# Documentation docking — issue-145

Candidate: workflow/issue-145 @ 9e5199b (commits 5d42700 + 9e5199b; base main a421ec2).

| File | Result |
|---|---|
| CHANGELOG.md | Updated — #142 bullet annotated as superseded; new Unreleased #145 entry: default gpt-6-sol/high on npx @openai/codex@0.155.1 + codex-acp@1.13.0, measured receipts, verified versions/wrapper pin, CODEX_PATH 0.156.0 override measured (Owner ruling option 1), no portable 0.156.1 pin claimed. |
| platforms/codex.yaml | Updated — default tier, acp_command, acp_verified_versions, acp_wrapper_pin, steering_summary, acp_quirks (CODEX_PATH record). |
| skills/codex-kaola-project-runner/* | Generated via render-skills.py --write; --check PASS. |
| README.md | No impact — no codex tier id, adapter pin, or CODEX_PATH text (grep gpt-6 / codex-acp / 0.15x / CODEX_PATH: no codex hits). |
| docs/api.md:507 | No impact — records the historical 1.11.0 idle-steering measurement; still a true past fact. |
| docs/codex-host.md | No impact — describes the interactive Codex Host (codex-cli 0.153.4/0.155.1 hook evidence), not the ACP worker pin. |
| templates/orchestrator/references/host-entry-matrix.md:54 | Out of scope — "codex-acp 1.11.0" is the Codex Host-entry measurement column owned by #126 (explicitly excluded from this run). |
| AGENTS.md | No impact — no platform tier or pin facts. |

Verdict: DOCKED
