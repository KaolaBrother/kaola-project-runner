# Finalization Summary — Issue #406

## Delivered

A general legacy-tolerant retirement path for versionless rows, closing the
dead end where a settled decision row with no `rev` and no usable evidence
(missing, empty string, `null`, or leafless container) had no working
recovery route.

- `scripts/kaola-dispatch.py`: `closed_shape(kind, record)` generalizes the
  #395 alert exit — a versionless record whose stored shape already ends its
  duty (empty-`inputs` alert, `status: settled` decision, cancelled or
  accepted-done task) retires directly with explicit `--expect-rev 0` and
  operator-supplied `--evidence`; all substantive gates (dispatch closure,
  task cite, transcription) still apply. Every refusal — `state check`
  command, update/retire `record-versionless`, and the `cleanup_current`
  migrate blocker — now names that working route.
- `scripts/kaola-record-contract.py`: the migrate blocker for an unusable-
  evidence settled decision names the concrete retire command at the row's
  own revision (`--expect-rev <recorded rev>` or the explicit `0`) while
  still refusing to write the file — migration never invents the owner
  answer; Unknown is not resolved. The #404 migrate-only tolerance for
  nonempty legacy freeform evidence is unchanged.
- Review repair (`4a34ed60`): a settled decision whose stored evidence is
  unusable retires only by the Host — the supplied evidence attests the
  owner's original answer; other writers are `host-only` and the refusal
  names the exact Host command. Literal `ORIGINAL_*` placeholder evidence
  is refused `invalid-input` on the direct path. The recovery-routes
  catalog, `docs/api.md`, `docs/conventions.md`,
  `templates/orchestrator/references/lifecycle-state.md`, CHANGELOG
  `## Unreleased`, and all generated `skills/` surfaces follow.

Candidate: `4a34ed60414b5402e4eb4a0145b50e3e606e56ec` on
`workflow/issue-406` (implementation `542bd206` + Host review repair
`4a34ed60`). Host verdict on `4a34ed60`: ACCEPTED — Host verification
confirmed blockers name the exact working command per row shape, both
named retires succeed, whole-file `migrate --write` succeeds after them,
the `ORIGINAL_*` placeholder is refused, and the sideagent writer is
refused. Host probes: `/tmp/kpr-406-verify`.

## Evidence

- `kaola-workflow/.ledger/issue-406.jsonl`: three missions done.
- Host repro receipts: `/tmp/kpr-406-repro/` (the dead-end fixture:
  `legacy-seat-plan`, settled, `evidence: ""`, no `rev`).
- Fixture demonstration: `/tmp/kpr-406-demo/01-04` — migrate plan and
  `--write` blocked exit 2 naming the retire command; the named direct
  retire exit 0 removes the row with supplied evidence; post-check clean.
- Focused receipts: `./scripts/validate.sh --suite` ×4 (406/362/395/404)
  exit 0 in 16.97s on `542bd206` and exit 0 in 19.59s on `4a34ed60`;
  `test-issue-406`: 14 tests, 2 documented #397 skips.
- Wider affected set on `4a34ed60`: `--suite` ×10
  (259/397/354/255/286/372/309/349/298/327) — 9/10 green; the one failure,
  `test-issue-255-lifecycle-state.py` (2 `wait_for` batch timeouts under
  parallel load), passed standalone exit 0 (171 tests, 156.7s).
- Full inventory on `542bd206`: `./scripts/validate.sh` exit 1, 162/164
  green; only failures `test-issue-76-permission-wake.py` and
  `test-issue-341-agent-initiated-turn.py` under a concurrent Host
  diagnostic gate — known #405 holder-timing family, both green on
  standalone rerun (both receipts kept).
- `./scripts/render-skills.py --write` + `--check` exit 0; post-commit
  `--check` on `4a34ed60` exit 0 (lifecycle reference exactly 8192 B,
  content stage, budgets OK).
- `kaola-workflow/issue-406/.cache/final-validation.md`: verdict `pass`,
  bound to this candidate tree.

## Known failures or unverified scope

- The full-inventory gate is not all-green under concurrent Host load:
  `test-issue-76` and `test-issue-341` are the separately tracked #405
  holder-timing phenomenon — standalone-green, fix run queued elsewhere;
  not a defect of this change (Host verdict concurs).
- No live ACP seat UAT: the change is state-tool contract behavior
  covered by contract suites and fixture probes.
- #397's v1 `body.alerts` mapping and large-carrier cases remain
  documented out-of-scope (2 skips in the #406 suite).

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/api.md
- docs/conventions.md
- hosts/grok-bot/INSTALL.md
- hosts/grok-bot/bridge.json
- hosts/grok-bot/kaola-delegator.md
- scripts/kaola-dispatch.py
- scripts/kaola-record-contract.py
- scripts/kaola-recovery-routes.py
- scripts/validate.sh
- skills/antigravity-kaola-project-runner/scripts/kaola-record-contract.py
- skills/antigravity-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/kaola-record-contract.py
- skills/claude-code-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/kaola-record-contract.py
- skills/codex-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/kaola-record-contract.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/kaola-record-contract.py
- skills/devin-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/kaola-record-contract.py
- skills/droid-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/kaola-record-contract.py
- skills/dsh-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/kaola-record-contract.py
- skills/grok-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/references/lifecycle-state.md
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kaola-project-runner/scripts/kaola-record-contract.py
- skills/kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-record-contract.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-record-contract.py
- skills/opencode-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-record-contract.py
- skills/zcode-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/grok-bot/accepted-revision.json
- templates/orchestrator/references/lifecycle-state.md
- tests/contract/test-issue-362-versionless-retire.py
- tests/contract/test-issue-406-versionless-decision-retire.py

## Documentation Docking

`docs/api.md`, `docs/conventions.md`,
`templates/orchestrator/references/lifecycle-state.md` (at its 8192-byte
budget), `scripts/kaola-recovery-routes.py`, and CHANGELOG `## Unreleased`
(Seats: restart required — `kaola-record-contract.py` is in the operator
restart set) carry the contract. `templates/grok-bot/accepted-revision.json`
stays at `"stage": "content"` per the post-release convention. All generated
`skills/` copies were re-rendered by `render-skills.py --write`; `--check`
is green. No tag, release, install, or restart is part of this finalization.

## Follow-Up Items

- KPM mirror `KaolaBrother/kaola-project-manager#783`: comment the fix
  and merge commits and close it as done, referencing this evidence.
- No new issue filed: the run found no further defect; the two
  full-gate load failures are already tracked as #405.

Final readiness: ready. Merge sink to `main`, verify publication and
issue closure, archive the run under `kaola-workflow/archive/issue-406/`,
and remove the run worktree and branch per the sink.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-406/.cache/final-validation.md
- kaola-workflow/archive/issue-406/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-406/finalization-summary.md
- kaola-workflow/archive/issue-406/mission-ledger.jsonl
- kaola-workflow/archive/issue-406/workflow-state.md
