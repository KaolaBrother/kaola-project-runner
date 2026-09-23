# Documentation docking — issue-142

Candidate: workflow/issue-142 @ 0415d2a (base main 992da2c).

| File | Result |
|---|---|
| CHANGELOG.md | Updated — Unreleased codex entry (after the landed #143/#144 entries): default `gpt-6-sol` "GPT-6 Sol", applied via plain ACP `model` option, no effort option under gpt-6-sol (`reasoning_effort` -32602 for high/medium) so no Runner effort override; upgrade/pins/`acp_verified_versions` unchanged. |
| README.md | No impact — grep for `gpt-5.6`, `5.6 Sol`, `Sol`, `gpt-6`, `Astra`, codex tier: no codex-default hits. |
| docs/api.md | No impact — existing rule "a rejection stays a limitation receipt" already covers an explicit `--effort` under gpt-6-sol; no codex default named. |
| docs/architecture.md, docs/codex-host.md | No impact — no codex default model/effort named. |
| docs/droid-live-verification-2026-09-17.md | No impact — historical Droid measurement naming Droid's own `gpt-5.6-sol`, not the codex preset. |
| skills/codex-kaola-project-runner/* | Generated via render-skills.py --write; --check PASS. |
| AGENTS.md | No impact — no platform tier facts. |

Verdict: DOCKED
