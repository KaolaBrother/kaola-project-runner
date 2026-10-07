# Finalization summary — issue 263

## Delivered

Noninterrupting steer adaptations across supported runtimes on `workflow/issue-263` (tip
`02c45cc0`, fully contained in the cycle candidate `e1ff6d486c16d89c65473ac19ff316811abad3ac` on
`workflow/issue-264`): Grok and OpenCode V2 steer adaptation, exact OpenCode binary binding without
proxy changes, shared steer receipt text free of platform names, supported noninterrupting prompt
and later-turn delivery, DSH native steer exposure and delivery after prompt completion, pending
delivery identity with old-holder guard, plus the compaction-recovery commits co-developed with
264. Owner-facing delivery: `docs/evidence/steer-20261005-all-runtime-delivery.md` in the tree.

## Validation

classification: final_validation_stale
green: false
mode: final-validation

recorded validated_candidate_hash "dc63693539592d99fba1565ef0f1d540dc7cce811d4330f551869604fba4f209" != current code-tree hash "2960e1bcf0c24a33d1b53b49dc70d36c46ee41a4ddf6444f2322a80629fee43c" — a relevant source/test/test-consumed file changed after the recorded validation; re-run the validation command and re-record final-validation.md with a fresh hash

A relevant source/test/test-consumed file changed after validation — or the record was written from a different checkout than this one. Re-run the validation command, then re-record with `kaola-workflow-validation-runner.js record --project <project> --verdict pass --command "<the validation command you ran>"`, invoked from the working tree you validated (the gate hashes the tree its own shell is in, and a linked worktree and main differ until the branch merges); never hand-patch the hash.

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- README.md
- docs/api.md
- docs/zcode-host.md
- platforms/cursor-cli.yaml
- platforms/devin.yaml
- platforms/droid.yaml
- platforms/dsh.yaml
- platforms/grok.yaml
- platforms/kimi-cli.yaml
- platforms/opencode.yaml
- scripts/kaola-acp-holder.py
- scripts/kaola-acp.py
- scripts/kaola-compact-recovery.py
- scripts/kaola-dsh-acp.py
- scripts/kaola-dsh-steer.mjs
- scripts/kaola-opencode-acp.py
- scripts/kaola-opencode-steer.mjs
- scripts/kaola-project-compact-notice.py
- scripts/kaola-zcode-acp.py
- scripts/render-skills.py
- scripts/validate.sh
- skills/claude-code-kaola-project-runner/SKILL.md
- skills/claude-code-kaola-project-runner/references/acp.md
- skills/claude-code-kaola-project-runner/references/steering.md
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-compact-recovery.py
- skills/claude-code-kaola-project-runner/scripts/kaola-project-compact-notice.py
- skills/claude-code-kaola-project-runner/scripts/vendor/claude-code-acp/dist/DERIVATION.json
- skills/claude-code-kaola-project-runner/scripts/vendor/claude-code-acp/dist/index.js
- skills/codex-kaola-project-runner/SKILL.md
- skills/codex-kaola-project-runner/references/acp.md
- skills/codex-kaola-project-runner/references/steering.md
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-compact-recovery.py
- skills/codex-kaola-project-runner/scripts/kaola-project-compact-notice.py
- skills/cursor-cli-kaola-project-runner/SKILL.md
- skills/cursor-cli-kaola-project-runner/references/acp.md
- skills/cursor-cli-kaola-project-runner/references/steering.md
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-compact-recovery.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-project-compact-notice.py
- skills/cursor-cli-kaola-project-runner/scripts/platform.yaml
- skills/devin-kaola-project-runner/SKILL.md
- skills/devin-kaola-project-runner/references/acp.md
- skills/devin-kaola-project-runner/references/steering.md
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-compact-recovery.py
- skills/devin-kaola-project-runner/scripts/kaola-project-compact-notice.py
- skills/devin-kaola-project-runner/scripts/platform.yaml
- skills/droid-kaola-project-runner/SKILL.md
- skills/droid-kaola-project-runner/references/acp.md
- skills/droid-kaola-project-runner/references/steering.md
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-compact-recovery.py
- skills/droid-kaola-project-runner/scripts/kaola-project-compact-notice.py
- skills/droid-kaola-project-runner/scripts/platform.yaml
- skills/dsh-kaola-project-runner/SKILL.md
- skills/dsh-kaola-project-runner/references/acp.md
- skills/dsh-kaola-project-runner/references/platform.md
- skills/dsh-kaola-project-runner/references/steering.md
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-compact-recovery.py
- skills/dsh-kaola-project-runner/scripts/kaola-dsh-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-dsh-steer.mjs
- skills/dsh-kaola-project-runner/scripts/kaola-opencode-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-project-compact-notice.py
- skills/dsh-kaola-project-runner/scripts/platform.yaml
- skills/grok-kaola-project-runner/SKILL.md
- skills/grok-kaola-project-runner/references/acp.md
- skills/grok-kaola-project-runner/references/steering.md
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-compact-recovery.py
- skills/grok-kaola-project-runner/scripts/kaola-project-compact-notice.py
- skills/grok-kaola-project-runner/scripts/platform.yaml
- skills/kimi-cli-kaola-project-runner/SKILL.md
- skills/kimi-cli-kaola-project-runner/references/acp.md
- skills/kimi-cli-kaola-project-runner/references/steering.md
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-compact-recovery.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-project-compact-notice.py
- skills/kimi-cli-kaola-project-runner/scripts/platform.yaml
- skills/opencode-kaola-project-runner/SKILL.md
- skills/opencode-kaola-project-runner/references/acp.md
- skills/opencode-kaola-project-runner/references/steering.md
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-compact-recovery.py
- skills/opencode-kaola-project-runner/scripts/kaola-opencode-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-opencode-steer.mjs
- skills/opencode-kaola-project-runner/scripts/kaola-project-compact-notice.py
- skills/opencode-kaola-project-runner/scripts/platform.yaml
- skills/zcode-kaola-project-runner/SKILL.md
- skills/zcode-kaola-project-runner/references/acp.md
- skills/zcode-kaola-project-runner/references/steering.md
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-compact-recovery.py
- skills/zcode-kaola-project-runner/scripts/kaola-project-compact-notice.py
- skills/zcode-kaola-project-runner/scripts/kaola-zcode-acp.py
- templates/SKILL.md.tmpl
- templates/references/acp.md.tmpl
- templates/references/steering.md.tmpl
- tests/contract/test-issue-24-opencode-no-skip-all.py
- tests/contract/test-issue-263-steer-adaptation.py
- tests/contract/test-issue-264-compact-recovery.py
- tests/contract/test-issue-65-steering.py
- tests/contract/test-issue-88-permission-defaults.py
- tests/contract/test-issue-98-dsh-acp.py
- tests/contract/test-project-compact-notice.py
- tests/contract/test-runner-v2.py
- tests/contract/test-zcode-acp-contract.py
- vendor/claude-code-acp/UPSTREAM.md
- vendor/claude-code-acp/dist/DERIVATION.json
- vendor/claude-code-acp/dist/index.js
- vendor/claude-code-acp/src/agent.ts
- vendor/claude-code-acp/src/claude-runner.ts
- vendor/claude-code-acp/tests/kaola-compact.test.ts

## Old-member full-inventory failure — diagnosis and association (dot judgment, verified)

The old member tip `02c45cc0` predates the `--suite` parser (added later by issue 265), so a
`--suite` invocation there runs the full old inventory. That run is genuinely RED at this tree
and the failure is preserved, not rewritten: `test-issue-65-steering.py` fails exactly 10
platform subtests of `test_generated_skills_advertise_only_real_tools` (27 tests total) at the
old test's line 440 `assertIn("steers natively", body)`.

Root cause (member-tree documentation-static drift, not a runtime regression): this member chain
made all ten platforms `native_steering: "supported"` and reworded the rendered SKILL steering
prose so no per-platform SKILL.md body carries the literal sentence "steers natively" any more,
while the old test still required that literal for every supported platform. At `dad228e4`
(main) the same assertions pass (three supported platforms carry the literal); at `02c45cc0`
all ten supported platforms lack it — ten subtest failures, exactly the observed set.

Subsequent-fix verification on the integrated candidate `e1ff6d486c16d89c65473ac19ff316811abad3ac`:
the chain's later commits `46901564` and `34e885c2` (not ancestors of the member tip) reworked
the steering test to check the steering reference and the actual runtime `kaola-tmux.sh` steer
command instead of the documentation literal, and the same 27 steering tests run green there —
v8 full inventory `./scripts/validate.sh` EXIT=0, 85 suites all green, steering suite 27/27
elapsed 33.094s (`/tmp/kpr-final-inventory-v8.log`, receipt line `validate: elapsed
test-issue-65-steering.py 33.094 s`, `EXIT=0`).

Preserved receipts: parent bridge `/tmp/kaola-val.W6Tw6d/test-issue-65-steering.py.log` (27
tests/33.247s, 10 failures, all the line-440 literal subtests) and this Host's own full-run
receipt `/tmp/kpr-final-i263-suite.log` (same invocation class at the same tree). The member's
focused own-scope suite receipt recorded below is a separate, real run and does not rewrite the
failed full-inventory attempt.

## Known limitations

Interrupt-steer is outside the safe boundary for ordinary needs (one documented deviation remains
recorded with its boundary verification); unsupported-native-steer runtimes keep waiting/idle-send
behavior. Cross-runtime steer equivalence beyond the delivered adapters stays unverified.

## Follow-Up Items

None filed; residual steer observations ride issue 260's owner disposition.

## Readiness

Accepted within scope; issue closes through the issue-264 merge sink (recorded set
259,263,264,265,266,267,268). No separate sink for this branch.

## Finalize Findings

### residue_unattributed

The `chore: finalize` commit did NOT carry the paths below. Worktree paths whose directories this run never committed are left in the worktree. Main-checkout paths this run's HEAD does not contain were not copied. Nothing was committed, deleted, reverted or relocated. Read them before the sink runs: commit what belongs to the run, leave what does not.

Paths not attributed to this run:

- .cache/final-validation.md

Paths left in the main checkout:

- docs/harness-acp-codex-160-live-2026-10-03.md
- docs/harness-acp-compat-2026-10-01.md
- docs/harness-acp-compat-2026-10-03.md
- docs/harness-acp-compat-2026-10-06.md
- docs/harness-acp-reverify-2026-10-01.md

