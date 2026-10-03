# Issue #245 finalization summary

## Delivered

Additive `session_role` on the holder record and the public list, status,
observe, view, and follow surfaces. Known values are host, sidekick, expert,
elite, and worker; otherwise the value is null. Host still comes from the
existing host session name. Exact `--role sidekick` is the only sidekick flag.
Expert, elite, and worker still come from the preset that was actually
selected. A dispatch plan role other than exact sidekick stays index metadata
and does not authorize, relabel, or refuse an otherwise valid item. Only exact
sidekick is forwarded as start `--role sidekick`. `scripts/kaola-tmux.sh`
accepts that flag and forwards it to `kaola-acp.py`. Occupancy stays
catalog-Class-based.

Candidate: `ba43915a510218a64c732b501f4b4cdcb808c667`, parent
`7161a3f9f3091032e54ee3b1a59ff1bfe5e72624`, ancestor
`1f282f02365c977c4998c88cabded24a13387228`.
Accepted source commit, unamended: `72196b7d2faaef3a454fe16def130c3afbc8f662`
(parent `bf5656f048044599633990341edb70624fb6e279`).
Acceptance record: `acceptance.md`.

Evidence: Host acceptance of the public identity surfaces and normal dispatch;
direct checkout start `baseline_exempt`; list rows for sidekick, worker, and
host; both trial stops `residual_pids []` and `process_exited` code 0;
`/tmp/kpr-i245-receipts/validate-ba43915a.txt` (`./scripts/validate.sh`,
`EXIT:0`) on this tip, including
`test_unproven_role_stays_metadata_and_only_sidekick_reaches_argv` and
`test_timeout_and_unknown_mutation_are_not_failed_or_returned`.
`run-chains --project issue-245` exited 1 with `chains_config_missing`: this
repo has no `package.json` `test:kaola-workflow:*` scripts. Consumer evidence
is `.cache/final-validation.md`.

The bridge remains content stage, unpinned, and not saveable. No release pin,
release, tag, or installation is part of this issue. A running seat must
restart before it emits `session_role`; this issue does not restart seats.
Terminal UI is unchanged.

## Documentation Impact

`docs/api.md`, `docs/dispatch-collect.md`, `docs/acp-watch/list-view.md`,
`docs/acp-watch/follow.md`, and the Unreleased CHANGELOG entry are the
delivered documentation. This summary, the acceptance record, the measured
validation, and the changed-path report are the normal #245 finalize record.
No separate documentation ledger.

## Known Failures and Unverified Scope

`./scripts/validate.sh` on this tip exited 0. The dispatch timeout assertion
still expects `start-timeout`, and that test passed. The fixture timing in
that test remains as it is on this candidate.

The skills-tree start refusal stays a recorded limitation, not an acceptance
gate. Shared-root Skill installation was not required and was not done.
`/tmp/kpr-i245-receipts/validate.txt` is an earlier receipt and does not bind
`ba43915a`. No per-platform installer rollout was run for this finalize.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/acp-watch/follow.md
- docs/acp-watch/list-view.md
- docs/api.md
- docs/dispatch-collect.md
- scripts/kaola-acp-holder.py
- scripts/kaola-acp.py
- scripts/kaola-dispatch.py
- scripts/kaola-tmux.sh
- scripts/validate.sh
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-tmux.sh
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-tmux.sh
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-tmux.sh
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-tmux.sh
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-tmux.sh
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-tmux.sh
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-tmux.sh
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/references/dispatch-collect.md
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-tmux.sh
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-tmux.sh
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-tmux.sh
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/orchestrator/references/dispatch-collect.md
- tests/contract/fixtures/kaola-acp-view-1.sample.json
- tests/contract/test-acp-contract.py
- tests/contract/test-acp-watch-contract.py
- tests/contract/test-issue-244-dispatch.py
- tests/contract/test-issue-245-session-role.py

## Follow-Up Items

No new follow-up is filed. The owner scope correction is already on the issue:
https://github.com/KaolaBrother/kaola-project-runner/issues/245#issuecomment-5964728868.
The skills-tree start limitation stays in this record.

## Final Readiness

Host acceptance authorizes close, archive, the configured merge sink, and
cleanup for issue #245 only. The implementation candidate is frozen.
`72196b7d` and `ba43915a` are not amended here. Lifecycle results come from
the transaction and sink receipts. No release, tag, package publication, or
install is authorized.

## Finalize Findings

### residue_unattributed

The residue mirror did not copy the paths below out of the main checkout: this run's HEAD does not contain them. Presence in main, an untracked status, or a neighboring file this run committed is not evidence they belong to this run. Nothing was copied, staged, committed, deleted, reverted or relocated — they remain in the main checkout. Read them before the sink runs: commit what belongs to the run, leave what does not.

Paths left in the main checkout:

- docs/harness-acp-codex-160-live-2026-10-03.md
- docs/harness-acp-compat-2026-10-01.md
- docs/harness-acp-compat-2026-10-03.md
- docs/harness-acp-reverify-2026-10-01.md

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-245/.cache/final-validation.md
- kaola-workflow/archive/issue-245/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-245/acceptance.md
- kaola-workflow/archive/issue-245/finalization-summary.md
- kaola-workflow/archive/issue-245/mission-ledger.jsonl
- kaola-workflow/archive/issue-245/workflow-state.md
