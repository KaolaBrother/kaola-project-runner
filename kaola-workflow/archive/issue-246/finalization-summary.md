# Issue #246 finalization summary

## Delivered

Host/user accepted candidate `8115c73df48458f79da73037184257f0730c35c9`, whose
parent is exactly `1b6c6f6642349a8838a6f0c0c5bb5bff03d29e82`, and explicitly
instructed finalization, sink, issue closure, archive and cleanup. Neither commit
is amended. Branch: `workflow/issue-246`. Claim digest:
`bca135097e6df14413eda101bd7bfc9e7aeca4eb1a6b53fd149301f64c425533`.
Installed skill: `/Users/ylmacstudio/.agents/skills/kaola-workflow-finalize/SKILL.md`.

The existing Host guidance keeps all worker assignments event-driven, including
ordinary direct Runner/Workflow assignments, with explicit `--no-wait` and a
Host turn boundary after dispatch/current-beat duties. Omitted wait selection is
preserved through direct, shared-shell and runtime entries; explicit flags win
and the last supplied flag wins.

The accepted compatibility correction lets an absent/null `session_role` reuse
`host_session()`, the established derivation defining `host_class`. Exact caller
and record platform, session, repo, holder id, worker dispatcher, heartbeat
binding, and existing live transport must still match. A supplied `host_class`
boolean or nonstandard name grants nothing. Explicit non-Host/unknown roles and
missing/mismatched identity retain blocking `standalone-default` with a detail;
there is no new refusal, fuzzy identity rule, probe, permission decision or gate.
The prompt remains pinned to the exact recorded worker holder. The only behavior
documentation follow-up is the existing change in `docs/api.md`.

## Recovery and ownership

The installed claim script, invoked from this worktree with
`resume --project issue-246 --json`, returned exit 1 and exactly
`{"resumed":false,"reason":"no active workflow project"}`. Receipt:
[.cache/resume-receipt.json](.cache/resume-receipt.json).
This is not recorded as resumed true. Continuation uses the existing main-root
`workflow-state.md` and the accepted worktree, as the owner instructed; no
startup, second claim or claim-digest change. Mission 1 remains done and immutable.
All new run-record writes are this worktree or #246's transaction-owned records.

## Host acceptance and evidence limits

Acceptance is the Host/user's explicit ruling on the compatibility behavior
above, including the exact identity and flag constraints, with finalization
authorized despite the following preserved failure and unverified behavior.
No full model-driven Host behavior PASS is inferred from transport fixtures.

The omitted-wait trial on `1b6c6f66` remains **FAILURE**:
`source: standalone-default`, `wait: true`,
`detail: "caller record does not prove a live Host role and identity"`,
`duration_ms: 763316`, `outcome: turn_completed`.
That send is not rerun. A completed turn did not satisfy the required admission
behavior. No live record was edited to add `session_role`.

The real-record proof uses the exact existing Grok Host and bound #246 worker
records read-only; base reproduces the failure detail and accepted candidate
selects `owning-host-default`, pinning that same worker. The isolated real Grok
CLI transport proof naturally starts a legacy Host from pre-role source without
editing its record. Candidate omitted send returns admission in 93 ms while the
worker remains active; the read-only useful QA task completes and exact-holder
stops report no residual processes. This proves real wait selection/admission,
not model-driven Host assignment choice, turn-boundary permission handling or
completion-event delivery without rescue. That full behavior remains unverified.

Preserved evidence from the accepted candidate's worktree-local
`.kw/qa/issue-246/` now follows this run into its archive:

- [qa/legacy-host-evidence.md](qa/legacy-host-evidence.md)
- [qa/real-record-proof.json](qa/real-record-proof.json)
- [qa/real-admission-summary.json](qa/real-admission-summary.json)
- [qa/real-admission-receipts.json](qa/real-admission-receipts.json)
- [qa/real-admission.log](qa/real-admission.log)

## Checks actually run on the accepted candidate

On the frozen source bytes delivered as `8115c73` (working-tree code unchanged
through commit), the previous continuation actually ran:

- `./scripts/render-skills.py --write` and `--check`: exit 0; budgets and generated
  source equality pass.
- `python3 tests/contract/test-issue-244-holder-prompt-binding.py`: exit 0, 7 tests;
  legacy absent/null roles, exact identity/binding failures, nonstandard and
  worker-marked names, supplied bool rejection, explicit flags and holder pin.
- `python3 tests/contract/test-zcode-heartbeat-contract.py`: exit 0, 24 tests,
  654 checks, no prerequisite skips; #246 direct/shared/runtime wait-selection
  contract included. [qa/heartbeat-legacy.log](qa/heartbeat-legacy.log).
- `python3 tests/contract/test-acp-contract.py`: exit 0, 84 tests.
  [qa/acp-legacy.log](qa/acp-legacy.log).
- `python3 tests/contract/test-issue-76-permission-wake.py`: exit 0, 5 tests,
  78 checks. [qa/permission-legacy.log](qa/permission-legacy.log).
- `python3 tests/contract/test-issue-245-session-role.py`: exit 0, 11 tests.
  [qa/role-legacy.log](qa/role-legacy.log).
- `git diff --check`, unchanged protected-source comparison and real proofs above:
  pass. No protected assertion or budget was weakened.

The prior `qa/candidate-evidence.md` and referenced frozen validate log apply to
`1b6c6f66` only. They are historical evidence, **not full validation of 8115c73**.
The current finalize invocation runs the measured repository command
`env -u FORCE_COLOR -u CLICOLOR_FORCE NO_COLOR=1 CLICOLOR=0 ./scripts/validate.sh`
on `8115c73` and exited **0**. This is a new measured validation of the accepted
candidate, not reuse of the older frozen log. All listed contract suites execute;
the named limitation is Bash 3.2 without `mapfile`/`BASHPID`, so the watchdog
wrapper skips while the suites run unwatched. No contract-suite prerequisite skip
is reported. Log: [qa/validate-8115c73.log](qa/validate-8115c73.log); command receipt:
[.cache/validation-command-result.json](.cache/validation-command-result.json).

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- docs/api.md
- docs/zcode-host.md
- scripts/kaola-acp.py
- scripts/kaola-tmux.sh
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-tmux.sh
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-tmux.sh
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-tmux.sh
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-tmux.sh
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-tmux.sh
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-tmux.sh
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-tmux.sh
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/SKILL.md
- skills/kaola-project-runner/references/host-startup.md
- skills/kaola-project-runner/references/zcode-host-dispatch.md
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-tmux.sh
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-tmux.sh
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-tmux.sh
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/orchestrator/SKILL.md.tmpl
- templates/orchestrator/references/host-startup.md.tmpl
- templates/orchestrator/references/zcode-host-dispatch.md.tmpl
- tests/contract/test-issue-244-holder-prompt-binding.py
- tests/contract/test-issue-76-permission-wake.py
- tests/contract/test-zcode-heartbeat-contract.py

## Follow-Up Items

No new defect or forge reorganization was discovered in finalization; no new
follow-up is filed. The known model-driven Host behavior gap stays explicitly
unverified above under the owner's acceptance boundary, rather than being
reported as a pass. Issue #251 is outside this run and remains untouched.

## Readiness

Host accepted the specified candidate and authorized finalization. The measured
repository validation on `8115c73` passes (exit 0); implementation bytes remain
unchanged. Ready for the authorized finalize and merge-sink transaction. The
transaction receipts own publication, closure, archive and cleanup truth; this
pre-transaction readiness is not a claim that those operations already succeeded.

No installation, release or tag is authorized. Preserve live Runner records,
heartbeat files, Delegator files and harness docs. Budgets stay 17408/8192, and
`tests/contract/test-issue-244-dispatch.py` keeps hang reason `start-timeout`.

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
- kaola-workflow/archive/issue-246/.cache/final-validation.md
- kaola-workflow/archive/issue-246/.cache/finalization-intake.json
- kaola-workflow/archive/issue-246/.cache/finalize-result.json
- kaola-workflow/archive/issue-246/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-246/.cache/resume-receipt.json
- kaola-workflow/archive/issue-246/.cache/validation-command-result.json
- kaola-workflow/archive/issue-246/finalization-summary.md
- kaola-workflow/archive/issue-246/mission-ledger.jsonl
- kaola-workflow/archive/issue-246/qa/acceptance-correction-comment.md
- kaola-workflow/archive/issue-246/qa/candidate-evidence.md
- kaola-workflow/archive/issue-246/qa/legacy-host-evidence.md
- kaola-workflow/archive/issue-246/qa/real-admission-receipts.json
- kaola-workflow/archive/issue-246/qa/real-admission-summary.json
- kaola-workflow/archive/issue-246/qa/real-record-proof.json
- kaola-workflow/archive/issue-246/workflow-state.md
