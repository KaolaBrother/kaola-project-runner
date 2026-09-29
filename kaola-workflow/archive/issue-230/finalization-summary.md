# Finalization Summary — issue #230

## Delivered

Owner-authored Claude Code, Droid, Cursor, and Devin task-selection profiles.
No new seat, no model probe, no install, and no release. The published v0.6.9
tag and release were not edited.

Claude Code, catalog total 21 presets (Elite 13, Worker 5, Expert 3):

- `claude-code/default` — Opus 5.5, native alias `opus`, effort `medium`,
  Elite. Profile: All-round execution worker, especially strong at complex
  execution work and UI and 3D visual implementation. This remains the runtime
  and Host fallback when no tier is chosen, and it implements.
- `claude-code/opus-xhigh` — Opus Extra High, native alias `opus`, effort
  `xhigh`, Elite. Profile: Plans, designs, and reviews difficult, complex work
  and handles deep reasoning tasks, with particular strength in UI and 3D
  visual design and review; does not perform implementation. The preset ID is
  not the alias. Both Opus presets use the existing `opus` subscription map
  entry. A resume or continue that does not name a tier, model, or effort
  still keeps the native selection.
- `claude-code/sonnet` — Sonnet, effort `high`, Elite. Profile: All-round
  execution worker, well suited to well-scoped work, especially UI and 3D
  visual implementation.
- `claude-code/fable` unchanged.

`droid/opus` and `cursor-cli/opus` stay Elite at medium, with the same
implementation profile as `claude-code/default`. `devin/opus-fusion` stays
Elite at medium, with: All-round execution worker, especially strong at
complex execution work. That row has no UI or 3D wording. Devin Fable is
unchanged. Native model IDs and existing grants were not expanded.

The shared Claude seat remains the prior Opus/xhigh configuration plus
Sonnet/high. That Opus side is `claude-code/opus-xhigh`, not the new Medium
default.

## Candidate

Reviewed tree `3d8d576e8ff3815e6e03ae814a70f0b69aa36da2` (Delegator personal
review: PASS). Main had moved to `aede714e` (sinks for #227 and #229). Rebase
onto `origin/main` conflicted only in the ten
`skills/*/scripts/main-skill-build.json` hashes. Those were regenerated with
`python3 scripts/render-skills.py --write` (budgets OK) and the rebase
continued. Rebased commits: `041f48c9`, `f01cb75b`. Follow-up
`0c1558a0a86130d33bd7d3dfd3775ef07e38d0b0` adds `platforms/dsh.yaml` to the
Unreleased operator path list, because that path is in `v0.6.9..HEAD` after
the #227 sink. The tree under validation is `0c1558a0`.

## Evidence

- Delegator personal review of `3d8d576e`: PASS (profile, manifest, adapter,
  catalog, and docs; no extra seat).
- `kaola-workflow/issue-230/.cache/final-validation.md`: `verdict: pass`,
  command `python3 scripts/render-skills.py --check && python3 -m unittest tests.contract.test-issue-218-preset-ids tests.contract.test-issue-111-model-tiers tests.contract.test-issue-148-quota-packages tests.contract.test-generated-skills tests.contract.test-progressive-disclosure`,
  `validated_candidate_hash: b0fd49f42dedaafbc97fd1bb69720c9c21bad59d5154825a002b2eca37f55e25`.
  Observed on `0c1558a0`: render-skills PASS; 72 tests, exit 0.
- `kaola-workflow-run-chains.js --project issue-230`: `chains_config_missing`
  (no `package.json` `test:kaola-workflow:*` scripts). The consumer gate is
  the recorded final-validation file.
- Ledger: `kaola-workflow/.ledger/issue-230.jsonl`. Done lines still name the
  pre-rebase hashes `c500efa6` and `3d8d576e`; those lines are immutable. The
  accepted tree after rebase is `0c1558a0`.

## Known failures / unverified scope

- `./scripts/validate.sh` was not rerun. The Delegator accepted the scoped
  profile checks and this finalize reran those checks on the rebased tree.
- No live model probe and no installation. No live seat was restarted.
- `chains_config_missing` is the expected consumer result, not a failed suite.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- README.md
- docs/api.md
- docs/architecture.md
- platforms/claude-code.yaml
- platforms/cursor-cli.yaml
- platforms/devin.yaml
- platforms/droid.yaml
- scripts/adapters/claude-code.sh
- skills/claude-code-kaola-project-runner/SKILL.md
- skills/claude-code-kaola-project-runner/references/platform.md
- skills/claude-code-kaola-project-runner/scripts/adapters/claude-code.sh
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/platform.yaml
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/platform.yaml
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/platform.yaml
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/platform.yaml
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/references/heartbeat-skeleton.md
- skills/kaola-project-runner/references/profile-catalog.md
- skills/kaola-project-runner/references/worker-profiles.md
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/orchestrator/references/heartbeat-skeleton.txt
- templates/orchestrator/references/profile-catalog.md.tmpl
- templates/orchestrator/references/worker-profiles.md.tmpl
- tests/contract/test-issue-148-quota-packages.py
- tests/contract/test-issue-218-preset-ids.py

## Follow-Up Items

None filed. The live Host heartbeat still has to name the shared Opus/xhigh
grant as `claude-code/opus-xhigh` on its next authorization refresh. That is
the Host's row update, not a new seat and not a separate defect.

## Final readiness

Ready: Delegator PASS on `3d8d576e`, rebased checks PASS on `0c1558a0`;
merge sink, close #230, archive.

## Finalize Findings

### residue_unattributed

The residue mirror did not copy the paths below out of the main checkout: this run's HEAD does not contain them. Presence in main, an untracked status, or a neighboring file this run committed is not evidence they belong to this run. Nothing was copied, staged, committed, deleted, reverted or relocated — they remain in the main checkout. Read them before the sink runs: commit what belongs to the run, leave what does not.

Paths left in the main checkout:

- docs/harness-acp-compat-2026-09-25.md
- docs/harness-acp-compat-2026-09-26.md
- docs/harness-acp-compat-2026-09-29.md

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-230/.cache/final-validation.md
- kaola-workflow/archive/issue-230/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-230/finalization-summary.md
- kaola-workflow/archive/issue-230/mission-ledger.jsonl
- kaola-workflow/archive/issue-230/workflow-state.md
