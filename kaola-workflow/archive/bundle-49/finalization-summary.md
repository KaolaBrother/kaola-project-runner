# Issue #49 finalization

## Delivered

Official Grok Bot is a first-class Project Runner **bridge host**: exactly one thin account Skill named `kaola-project-runner` binds an execution target, asks that target's device-local locator for a verified `KaolaBrother/kaola-project-runner` checkout at the pinned content revision, and loads the canonical main Skill plus one selected worker from that checkout. Progressive disclosure and measured byte budgets are locked. Grok Bot is not an eighth CLI worker, has no `platforms/grok-bot.yaml` / transport adapter / installer destination, and does not use a Cursor-plugin or eight-document private-skill payload. Delivery is the two-commit pair content R3 `bc8592d323864c30010b48ae724f329f8df6753e` + pin P3 `db4b0d5813111ef71afbcf165be0fb91d9a7d976` (P3 differs from R3 by the revision file and three generated host products only). Owner UAT on Grok Bot 0.53.0 is PASS under the rollout-corrected exposure gate.

## Files Changed

84 paths vs `main` (`ba3d14f`): `scripts/` (renderer, locator, verifier, bounded PTY/ACP observation, installer help, validate.sh), `templates/` (orchestrator + grok-bot adapter + budgets + transport/acp references; golden untouched), generated `skills/` and `hosts/grok-bot/` (bridge, `bridge.json`, `INSTALL.md`), focused tests (`test-issue-49-grok-bot-host.py`, `test-progressive-disclosure.py`, installer/tmux/generated-skill suites), and public docs (`README.md`, `docs/{api,architecture,conventions,grok-bot-host,README}.md`, `CHANGELOG.md`, `AGENTS.md`). P3 pin commit touches only `templates/grok-bot/accepted-revision.json` and the three `hosts/grok-bot/` products.

## Test Coverage

Issue #49 host/bridge tests (37) and progressive-disclosure tests (21, including bounding regressions that fail on R2). Installer runtimes/migration, generated-Skill acceptance, validator, and live private-tmux bounding (`test-kaola-tmux.sh`). Pin gate refutations (stray edit, missing commit, release-masquerade label, extra bridge line, self-pin) already recorded in `delivery-report.md` and not re-executed against the production worktree.

## Validation

PASS at P3 `db4b0d5813111ef71afbcf165be0fb91d9a7d976` (R3 `bc8592d323864c30010b48ae724f329f8df6753e`): `python3 scripts/render-skills.py --check --require-pinned && ./scripts/validate.sh && git diff --check main...HEAD && git diff --check`, exit 0. Receipt: `.cache/final-validation.md`, candidate hash `9ca9a19a5b9ca2fee28b3d4f4dffa3da0224e7b64f2928e0146eb5cde53eebdd`. Additional legs: verifier `--require-pinned` PASS; live `tests/contract/test-kaola-tmux.sh` PASS; golden empty vs `main`; no grok-bot platform/adapter. Pre-existing ACP `ResourceWarning: unclosed file` noise is unchanged.

Issue #49 acceptance (owner-corrected; original Cursor-plugin / `--runtime grok-bot` / eight-Skill / Yours-slash gates are void):

- Official Skill write succeeds; exactly one account Skill `kaola-project-runner`; no worker Skills; no publication — UAT 5693161395 + 5693267500.
- Fresh 1:1 conversation native exposure returns R3 revision, repo, target/locator, and security boundary — UAT 5693267500.
- Local Computer register/attest/exact Claude preflight, no session mutation, no credentials/Settings read, cleanup — UAT 5693161395.
- Renderer `--write`/`--check --require-pinned`, `validate.sh`, focused tests, `git diff --check`, golden frozen, seven platforms only — this freeze.
- Docs distinguish Grok Bot host vs Grok CLI worker — `.cache/doc-docking.md` DOCKED, with the Yours/slash prose exception below.

## Changed Paths

Files this branch changed outside the run-state and documentation bands:

- .gitignore
- AGENTS.md
- hosts/grok-bot/.generated-by-kaola-project-runner
- hosts/grok-bot/INSTALL.md
- hosts/grok-bot/bridge.json
- hosts/grok-bot/kaola-project-runner.md
- scripts/install-local.sh
- scripts/kaola-acp.py
- scripts/kaola-grok-bot-verify.py
- scripts/kaola-locate.py
- scripts/kaola-observation.py
- scripts/kaola-tmux.sh
- scripts/render-skills.py
- scripts/validate.sh
- skills/claude-code-kaola-project-runner/SKILL.md
- skills/claude-code-kaola-project-runner/references/acp.md
- skills/claude-code-kaola-project-runner/references/transport.md
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-observation.py
- skills/claude-code-kaola-project-runner/scripts/kaola-tmux.sh
- skills/codex-kaola-project-runner/SKILL.md
- skills/codex-kaola-project-runner/references/acp.md
- skills/codex-kaola-project-runner/references/transport.md
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-observation.py
- skills/codex-kaola-project-runner/scripts/kaola-tmux.sh
- skills/cursor-cli-kaola-project-runner/SKILL.md
- skills/cursor-cli-kaola-project-runner/references/acp.md
- skills/cursor-cli-kaola-project-runner/references/transport.md
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-observation.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-tmux.sh
- skills/devin-kaola-project-runner/SKILL.md
- skills/devin-kaola-project-runner/references/acp.md
- skills/devin-kaola-project-runner/references/transport.md
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-observation.py
- skills/devin-kaola-project-runner/scripts/kaola-tmux.sh
- skills/grok-kaola-project-runner/SKILL.md
- skills/grok-kaola-project-runner/references/acp.md
- skills/grok-kaola-project-runner/references/transport.md
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-observation.py
- skills/grok-kaola-project-runner/scripts/kaola-tmux.sh
- skills/kaola-project-runner/SKILL.md
- skills/kaola-project-runner/references/grok-bot-host.md
- skills/kaola-project-runner/references/heartbeat-skeleton.md
- skills/kimi-cli-kaola-project-runner/SKILL.md
- skills/kimi-cli-kaola-project-runner/references/acp.md
- skills/kimi-cli-kaola-project-runner/references/transport.md
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-observation.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-tmux.sh
- skills/opencode-kaola-project-runner/SKILL.md
- skills/opencode-kaola-project-runner/references/acp.md
- skills/opencode-kaola-project-runner/references/transport.md
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-observation.py
- skills/opencode-kaola-project-runner/scripts/kaola-tmux.sh
- templates/SKILL.md.tmpl
- templates/budgets.json
- templates/grok-bot/INSTALL.md.tmpl
- templates/grok-bot/accepted-revision.json
- templates/grok-bot/bridge.md.tmpl
- templates/orchestrator/SKILL.md.tmpl
- templates/orchestrator/references/grok-bot-host.md
- templates/orchestrator/references/heartbeat-skeleton.txt
- templates/references/acp.md.tmpl
- templates/references/transport.md.tmpl
- tests/contract/test-generated-skills.py
- tests/contract/test-installer-migration.sh
- tests/contract/test-installer-runtimes.sh
- tests/contract/test-issue-41-orchestrator.py
- tests/contract/test-issue-49-grok-bot-host.py
- tests/contract/test-kaola-tmux.sh
- tests/contract/test-progressive-disclosure.py
- tests/lib/issue-1-test-lib.sh

## Documentation Docking

DOCKED in `.cache/doc-docking.md`. Owner acceptance exception: generated UAT guide/docs still mention Plugins → Yours and slash discovery; those surfaces are not gates for this account (5693224801). Owner forbade R4/P4 and candidate-byte mutation; no release/tag, so Unreleased changelog is correct.

## Follow-Up Items

None filed. Owner this turn: do not add R4/P4 or other burden; do not rewrite candidate bytes; do not create a release/tag or publish Marketplace; do not mutate the Grok Bot account. The remaining docs/test wording that still names Yours/`/` is recorded as an accepted exception for this merge, not a new forge issue.

Seven Low notes from the R3/P3 PASS-with-notes review (5692569301) remain documented there and were deliberately not corrected, because none sits in the UAT runtime path and the accepted pair must not be rebased, squashed, or amended.

## Readiness

Ready for Workflow archive, issue closure, and merge sink. Do not open a PR. Do not create a release or tag. Do not publish Marketplace. Do not modify the Grok Bot account. Do not touch bundle-50 or bundle-51. Keep R3 then P3 as two commits; no rebase/squash/amend.

## Issue statement walk

Original #49 asked for a Cursor-plugin host bundle and `--runtime grok-bot` into `~/.cursor/plugins/local`, with live `/` and Plugins UAT as the release gate. Owner UAT and successive `kw:correction` comments replaced that with one thin repo-direct bridge + locator. Closing against the original body without a correction comment would be false; the correction is posted on the issue before close.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/bundle-49/.cache/doc-docking.md
- kaola-workflow/archive/bundle-49/.cache/final-validation.md
- kaola-workflow/archive/bundle-49/.cache/mirror-digest.json
- kaola-workflow/archive/bundle-49/.cache/origin/selection-record.json
- kaola-workflow/archive/bundle-49/delivery-report.md
- kaola-workflow/archive/bundle-49/finalization-summary.md
- kaola-workflow/archive/bundle-49/mission-list.md
- kaola-workflow/archive/bundle-49/review-report.md
- kaola-workflow/archive/bundle-49/workflow-state.md
