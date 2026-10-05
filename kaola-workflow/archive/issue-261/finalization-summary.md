# Finalization Summary — Issue #261

## Delivered

Issue 261 repairs shared Droid admission. The accepted candidate is `892de2bc77c046f2dda77b6975a8dc962a07b2e5`. It uses base `86514ddb2a8d80cd3dcee6f4979765a67c21f49a`. Code commit: `ef17915c150489d1e7eb5a638306f008c290f9a2`.

The shared Droid pool remains two. A live seat uses one place. Two default/opus/core admissions fit. A third admission refuses. Elite cap 4, Worker exemptions, other resource conflicts, unknown occupancy, grants, and profiles remain unchanged.

## Acceptance and Evidence

Host accepted the frozen candidate. The acceptance record is `/tmp/kpr-i261-host-acceptance-20261005.md`. Host confirmed the dispatcher source, tests, and guidance match reviewed candidate `99b24a6f916a8fb450340816c48d5bd335535d52`. A source equality diff from `99b24a6f` to `892de2bc` returned exit 0 for the dispatcher, its focused tests, source and generated guidance, and generated dispatcher script.

Host used installed Droid sessions for real admission. Default and opus both started, read the full current Skill, returned their exact nonce replies, and remained alive while Host tested a third core assignment. The third assignment refused as `shared-occupied` with known occupancy. Host did not start or send to core. Both diagnostic sessions stopped with exit 0 and no residual process. The shared grant remains 2 and Elite cap remains 4. See the acceptance record and `/tmp/kpr-i261-live-*.json` receipts. No actual Droid admission was run by this owner.

Current focused validation passed on the frozen candidate:

- `render-skills.py --check`: PASS; budgets OK.
- The three shared-seat tests: 3 passed in 1.287 seconds.
- `git diff --check` and `git show --check`: exit 0.

Host also recorded renderer/write and renderer/check exit 0, and the same three tests passed in native receipts `5668`, `5795`, and `5821`. The original reviewed candidate `99b24a6f` had 76 dispatcher tests pass in 37.912 seconds and `validate.sh` exit 0, including 105 lifecycle-state tests. Those full receipts apply to unchanged dispatcher bytes. No fresh full-suite PASS is claimed for `892de2bc`.

The integrated validation log `/tmp/kpr-i261-validate-integrated.txt` exited 1 because the initial Unreleased note lacked the required Seats line. The note was corrected. Focused correction event `4779` passed. The earlier long issue 162 mock run showed error and failure markers and stopped after more than ten minutes. It is not a PASS. The initial capacity failure recovered on retry 1; it is not a current persistent fault.

## Documentation Impact

`CHANGELOG.md` adds one Unreleased note for the user-visible repair and keeps `Seats: restart not required`. The dispatch guide and its source template explain shared capacity. The renderer updated generated outputs. Both #260 Unreleased notes and #262 writing guidance remain present. `templates/grok-golden/` is unchanged.

## Validation

classification: final_validation_stale
green: false
mode: final-validation

recorded validated_candidate_hash "6833903bd0bcc69dea6d682dc57a98d19d9504c52c18ef98b76f2d10a441371f" != current code-tree hash "ab0f0c5d12a9d7c11ac4a2231a41f341a953509c8314a5a5e1cb0071566027f6" — a relevant source/test/test-consumed file changed after the recorded validation; re-run the validation command and re-record final-validation.md with a fresh hash

A relevant source/test/test-consumed file changed after validation — or the record was written from a different checkout than this one. Re-run the validation command, then re-record with `kaola-workflow-validation-runner.js record --project <project> --verdict pass --command "<the validation command you ran>"`, invoked from the working tree you validated (the gate hashes the tree its own shell is in, and a linked worktree and main differ until the branch merges); never hand-patch the hash.

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/dispatch-collect.md
- scripts/kaola-dispatch.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/references/dispatch-collect.md
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/orchestrator/references/dispatch-collect.md
- tests/contract/test-issue-244-dispatch.py

## Follow-Up Items

None. The accepted live proof covers two real Droid admissions and a third refusal. Core itself was not started or smoke-tested.

## Readiness

Host accepted this independent issue 261 candidate. The authorized merge sink will publish it, close only #261 after verified merge, archive this run and its ledger, release this claim, and remove only the issue261 worktree and branch. This closeout does not finalize #259 or establish combined #259 acceptance. No release, tag, install, login, or consumer operation is authorized.

## Finalize Findings

### residue_unattributed

The residue mirror did not copy the paths below out of the main checkout: this run's HEAD does not contain them. Presence in main, an untracked status, or a neighboring file this run committed is not evidence they belong to this run. Nothing was copied, staged, committed, deleted, reverted or relocated — they remain in the main checkout. Read them before the sink runs: commit what belongs to the run, leave what does not.

Paths left in the main checkout:

- docs/harness-acp-codex-160-live-2026-10-03.md
- docs/harness-acp-compat-2026-10-01.md
- docs/harness-acp-compat-2026-10-03.md
- docs/harness-acp-reverify-2026-10-01.md


## Validation Reconciliation

The first finalization transaction reported `final_validation_stale`. The main-to-worktree mirror had copied main's owner `AGENTS.md` edit into the issue261 worktree after the focused check. The transaction did not commit that edit. I restored only the issue261 worktree copy to the committed candidate version. The candidate copy hash is `4afe36587d8dbc71dd923c009849995a215ed9cab4f30bc00accf73ead498233`. Main owner `AGENTS.md` remains unchanged at `770aec796db0089bb044d4860631fa6bbb37f3aeed0f51e3f6d6d4a771f4628f`.

The candidate code-tree hash is again `6833903bd0bcc69dea6d682dc57a98d19d9504c52c18ef98b76f2d10a441371f`, which matches the archived `final-validation.md` record. A later read-only `finalize --check` exited 0 and reported `validation: chains_green`. The dispatcher, tests, templates, generated files, and focused validation command did not change. The first stale measurement remains above as the exact result observed during that transaction.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-261/.cache/final-validation.md
- kaola-workflow/archive/issue-261/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-261/finalization-summary.md
- kaola-workflow/archive/issue-261/mission-ledger.jsonl
- kaola-workflow/archive/issue-261/workflow-state.md
