# Issue 243 — Raise execution Opus 5.5 presets from medium to high

## Delivered

Four execution presets now start at high effort. Preset IDs, classes, profiles, counts, permissions, packages, and Fast policy are unchanged.

1. `claude-code/default`: `opus` at `effort=high`. `claude-code/opus-xhigh` stays `opus` at `effort=xhigh` and thinking-only.
2. `devin/opus-fusion`: launch argv `devin acp --model fusion-claude-opus-5-5-high-sidekick-swe-2-medium`. Main component Opus 5.5 is high. The SWE-2 sidekick stays medium. `opus_fusion_model_effort` stays empty, so there is no top-level Fusion effort. The current quirks text states the high default; Issue #190 and Issue #197 medium observations stay historical, including the advertisement-lag sentence.
3. `droid/opus`: `claude-opus-5-5` at `reasoning_effort=high`. `droid/default` and `droid/core` are unchanged.
4. `cursor-cli/opus`: `claude-opus-5-5-high` at effort high. ACP still maps that picker id onto base model `claude-opus-5-5` and sends effort on its own option. The map still includes `claude-opus-5-5-medium`.

New starts use these defaults. An ordinary resume keeps the saved model and effort. An explicit `--effort` or `--model` still wins. Sonnet, Fable, Cursor's default Grok, and Devin default/Fable are unchanged. No new tier or alias. No release, tag, install, or CHANGELOG release section.

## Candidate

c6a0d9036a20fb0c5066758eea4d537ddf0d79b9, workflow/issue-243.
Worktree: /Users/ylmacstudio/Workspace/kaola-project-runner/.kw/worktrees/issue-243
Baseline: 5558d8e8. Diff: 45 files, +207/−103.

## Evidence and acceptance

Host ACCEPTANCE: PASS. The Host verified the four preset changes in the manifests, adapters, generated Skills and references, profile catalog, README, and docs/api.md, and verified the boundaries: opus-xhigh remains xhigh and thinking-only; other presets and Fast are unchanged; medium was not replaced globally; Devin #190/#197 medium observations stay historical. Six new override and variant tests were added and none were removed. The Host re-ran `./scripts/render-skills.py --check` and the eight affected suites under an isolated HOME; every one exited 0.

Those same commands exited 0 in this worktree on the bytes that became `c6a0d903` (the commit did not change them): render-skills --check; test-issue-111-model-tiers; test-issue-218-preset-ids; test-issue-237-model-display; test-progressive-disclosure; test-droid-acp-contract; test-issue-148-quota-packages; test-generated-skills; test-acp-contract.

`run-chains --project issue-243` from this worktree: exit 1, `chains_config_missing` — this repo has no `package.json` `test:kaola-workflow:*` scripts. Consumer finalize evidence is `.cache/final-validation.md` (`verdict: pass`, the command above, hash `ca231c8a4ef2290952cac0ce60ff6186112481e9d27157f90b3fd282c1660ceb`). That receipt is not a `./scripts/validate.sh` receipt.

Mock ACP evidence, not a live native-model probe: Claude default sends `model=opus` and `effort=high`; an explicit `--effort medium` keeps `preset_effort` high. Cursor opus maps `claude-opus-5-5-high` to `claude-opus-5-5` with effort config id `effort` and value high; an explicit medium variant and an explicit `--effort medium` still split model and effort. Droid opus sends `reasoning_effort=high`; a preserved resume does not. Devin opus-fusion launches the high slug through argv; an advertisement of the earlier medium slug stays stale and `model_verified` stays `unknown`.

Protected untracked files `docs/harness-acp-compat-2026-10-01.md` and `docs/harness-acp-reverify-2026-10-01.md` were not staged or deleted. `templates/grok-golden/` was not edited.

## Known failures or unverified scope

No failure on this candidate. Native CLI model selection was not probed; unknown native-model evidence stays unknown. No push, tag, release, grok-bot pin, or install. The Host owns those. This receipt does not claim a full `./scripts/validate.sh` run.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- README.md
- docs/api.md
- platforms/claude-code.yaml
- platforms/cursor-cli.yaml
- platforms/devin.yaml
- platforms/droid.yaml
- scripts/adapters/claude-code.sh
- scripts/adapters/cursor-cli.sh
- scripts/adapters/devin.sh
- scripts/adapters/droid.sh
- skills/claude-code-kaola-project-runner/SKILL.md
- skills/claude-code-kaola-project-runner/references/platform.md
- skills/claude-code-kaola-project-runner/scripts/adapters/claude-code.sh
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/platform.yaml
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/SKILL.md
- skills/cursor-cli-kaola-project-runner/references/platform.md
- skills/cursor-cli-kaola-project-runner/scripts/adapters/cursor-cli.sh
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/platform.yaml
- skills/devin-kaola-project-runner/SKILL.md
- skills/devin-kaola-project-runner/references/acp.md
- skills/devin-kaola-project-runner/references/platform.md
- skills/devin-kaola-project-runner/scripts/adapters/devin.sh
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/platform.yaml
- skills/droid-kaola-project-runner/SKILL.md
- skills/droid-kaola-project-runner/references/platform.md
- skills/droid-kaola-project-runner/scripts/adapters/droid.sh
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/platform.yaml
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/references/profile-catalog.md
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- tests/contract/fake-droid-acp-agent.py
- tests/contract/test-acp-contract.py
- tests/contract/test-droid-acp-contract.py
- tests/contract/test-generated-skills.py
- tests/contract/test-issue-111-model-tiers.py
- tests/contract/test-issue-218-preset-ids.py
- tests/contract/test-issue-237-model-display.py

## Follow-Up Items

None. No run-discovered defect was filed.

## Readiness

Ready to merge locally and close issue #243. Do not push or tag.

## Finalize Findings

### residue_unattributed

The residue mirror did not copy the paths below out of the main checkout: this run's HEAD does not contain them. Presence in main, an untracked status, or a neighboring file this run committed is not evidence they belong to this run. Nothing was copied, staged, committed, deleted, reverted or relocated — they remain in the main checkout. Read them before the sink runs: commit what belongs to the run, leave what does not.

Paths left in the main checkout:

- docs/harness-acp-compat-2026-10-01.md
- docs/harness-acp-reverify-2026-10-01.md

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-243/.cache/final-validation.md
- kaola-workflow/archive/issue-243/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-243/finalization-summary.md
- kaola-workflow/archive/issue-243/mission-ledger.jsonl
- kaola-workflow/archive/issue-243/workflow-state.md
