# Issue 409 — finalization summary

## What changed

- `platforms/kimi-cli.yaml`: `default` preset retargets to **Kimi K2.8** (`kimi-code/kimi-for-coding`, thinking=max, Elite; profile "All-round implementation worker for every kind of hands-on development and implementation task."); named tier `kimi-k2-8` deleted (folded into `default` — same model id, same effort); new named tier `kimi-k3-1-pro` = **Kimi K3.1 Pro** (`kimi-code/k3.1-pro`, thinking=max, Elite) with the owner-approved verbatim profile "Strong all round worker. Strong at visual design and visual inspection, with good UI and design taste."; `launch_summary` rewritten for the new default/escalation story; `acp_verified_versions` = cli=2.2.0;protocol=1 from today's live session.
- `scripts/adapters/kimi-cli.sh`: same preset facts on the adapter declaration (kept in agreement by test #111).
- `tests/contract/test-issue-111-model-tiers.py`: kimi-cli pins re-measured live 2026-10-24 (kimi cli 2.2.0). `tests/contract/test-issue-218-preset-ids.py`: Elite row order `kimi-cli/default`, `kimi-cli/kimi-k3-1-pro`.
- `docs/architecture.md`: named-tier example updated. Generated output re-rendered (`skills/kimi-cli-kaola-project-runner/**`, `skills/kaola-project-runner/references/profile-catalog.md`, `README.md`).
- `templates/grok-bot/accepted-revision.json` reset to `content` stage (post-v0.9.28 content cycle opened); bridge re-rendered unpinned.
- `CHANGELOG.md`: Unreleased bullet documenting the fold/disposition.

## Live evidence (kimi cli 2.2.0, this machine, 2026-10-24)

- Native catalog (`kimi provider list --json`, `evidence/kimi-provider-list-2.2.0.json`): `kimi-code/k3.1-pro` (displayName "K3.1 Pro", efforts low/high/max), `kimi-code/kimi-for-coding` (displayName "K2.8 Preview", default effort max). The id was read from the live catalog, not invented.
- ACP start receipts: `evidence/start-default.json` (preset `kimi-cli/default`, effective `kimi-code/kimi-for-coding`, thinking=max applied, session_role=elite) and `evidence/start-k31pro.json` (preset `kimi-cli/kimi-k3-1-pro`, effective `kimi-code/k3.1-pro`, thinking=max applied, session_role=elite). Both seats stopped with zero residual (`evidence/stop-*.json`).

## Validation

- `./scripts/render-skills.py --write` + `--check`: PASS (budgets OK, content-stage bridge).
- Focused suites, all exit 0 (logs in `evidence/suite-*.log`): test-issue-111-model-tiers, test-issue-218-preset-ids, test-issue-148-quota-packages, test-progressive-disclosure, test-generated-skills, test-acp-contract.

## Acceptance vs issue

- [x] `kimi-cli/default` starts Kimi K2.8 at thinking=max (live receipt).
- [x] `kimi-k3-1-pro` starts Kimi K3.1 Pro at thinking=max (live receipt); class=Elite in catalog and dispatch (session_role=elite), not Expert.
- [x] Profile catalog row carries the owner text verbatim; old K3/duplicate disposition in CHANGELOG.
- [x] Gate green (focused suites + render checks); release note (v0.9.29) names the retarget + new higher tier.

## Limitations / notes

- `model_verified` stays `unknown` in both start receipts because no prompt turn ran (start-time ACP config echo is the evidence; no quota spent on a full send/observe smoke).
- No worker seat was dispatched (Host self-executed per owner instruction; catalog-only change with verbatim text).
- No KPM mirror (per issue scope). Seats must restart at v0.9.29 (platforms + adapters changed — operator diff non-empty).
