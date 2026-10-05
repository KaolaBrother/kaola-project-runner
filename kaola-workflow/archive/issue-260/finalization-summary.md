# Issue260 finalization summary

## Delivered

Host accepted candidate `e23040ae348652aac61141551bb5a252f4520fb7` for confirmed
items7 and8 on 2026-10-05 and authorized this merge sink, single-run archive,
claim release and own-tree cleanup. The issue must remain OPEN.
Base: `647626dde2ec07b4667ca861161d19c288dd7d6d`, completed262.
Original implementation: `9394bb9e308cbbb2a486af9ff720d35db95d8a71`.

Item7: unset/empty CODEX_PATH resolves CODEX_BIN, then PATH. Explicit CODEX_PATH
remains authoritative and must name an absolute executable. A chosen child is
cached per call so the checked and launched paths agree. Invalid setup gets an
actionable error. Explicit caller-owned command overrides retain their behavior.
Item8: bad Runner flags return structured schema_version 3 invalid-input JSON,
nonzero exit, mutation_status not_started and mutation_performed false. Existing
stderr diagnostics and help remain available.

Delivery and exact receipts: `/tmp/kpr-i260-transport-delivery.md`.
Original focused/full checks: `/tmp/kpr-i260-check-receipts.json`.
Updated checks: `/tmp/kpr-i260-update-check-receipts.json`.
Source/base preservation: `/tmp/kpr-i260-update-receipt.json`.

## Acceptance evidence and limits

Original full validate.sh passed with exit0 on 9394bb9e, no named skips:
`PATH=/Users/ylmacstudio/.local/bin:$PATH /Users/ylmacstudio/.local/bin/bash /Users/ylmacstudio/Workspace/kaola-project-runner/.kw/worktrees/issue-260/scripts/validate.sh`.
Frozen receipt: `/tmp/kpr-i260-validate-accepted-candidate.log`.
That is reused evidence for unchanged source/tests/manifests, not a fresh full
run on e23040ae. Only 262 source guidance, its rendered surfaces and 262 archive
differ. Render --write/--check, generated Skill acceptance and 15 progressive
disclosure tests passed on the updated tree. The original 80-case invalid-flag
matrix and parent simulations were not repeated. All affected checks passed.

One real standalone Codex diagnostic used the repaired original260 client,
CODEX_PATH unset and CODEX_BIN `/Users/ylmacstudio/.local/bin/codex`, in
`/private/tmp/kpr-i260-live-66poltnk/repo`, Workflow off.
Runner name: `codex-KPR-i260-child-smoke`.
ACP/native session id: `01a10b79-b708-7231-a647-9a8f7a8e2945`.
Holder id: `da22c60fcf2a5683045a6bc5238d82eb`.
Native turn id: `01a10b7d-2f67-7f81-8ac5-c4980464654d`.
Requested codex/luna; actual configOptions and native turn_context confirmed
`gpt-6-luna`, effort `max`. Fast off was applied and read back by ACP.
Adapter 2.0.1 was unchanged; requested CLI 0.160.0 is separate from actual child
and native CLI 0.160.0. The legacy models.currentModelId was stale; no original
receipt was rewritten to turn that into a model-verification claim.

The one reply-only prompt returned `KPR_I260_CODEX_LUNA_OK`, end_turn, zero tools,
zero commands and zero files changed. One invalid --text-file send returned
invalid-input with no mutation and retained the prior prompt and event cursor.
Normal exact stop returned stopped true, residual_pids[]; status and exact PID
checks confirmed cleanup. No real seat remains from this diagnostic.
Receipts under `/tmp/kpr-i260-live-`: start.json, observe-before.json, send.json,
capture.json, capture-reply.json, bad-flag.json, bad-flag-preservation.json,
stop.json, status.json, residual-check.json and native-facts.json. Exact argv,
exit codes and elapsed times are in the operation JSON files. No service failure,
credential retry or unknown mutation replay occurred.

## Documentation impact

The accepted API guide, Codex source manifest descriptions and rendered references
explain executable setup and structured input errors. The unreleased changelog
records the behavior. No seats need a restart for these client changes. No holder,
bridge, adapter pin, protocol or grok-golden change was made. All generated output
came from source rendering. No new framework was added.

## Validation

classification: final_validation_stale
green: false
mode: final-validation

recorded validated_candidate_hash "2985606b39687ab9eff4159eb7e174dc24f001f0daf91e8dd3e95587c44e1275" != current code-tree hash "faded7215a3c6289a21e78c8a9a74f8acb95ab8272e1ecc0012f45fe3bcd775a" — a relevant source/test/test-consumed file changed after the recorded validation; re-run the validation command and re-record final-validation.md with a fresh hash

A relevant source/test/test-consumed file changed after validation — or the record was written from a different checkout than this one. Re-run the validation command, then re-record with `kaola-workflow-validation-runner.js record --project <project> --verdict pass --command "<the validation command you ran>"`, invoked from the working tree you validated (the gate hashes the tree its own shell is in, and a linked worktree and main differ until the branch merges); never hand-patch the hash.

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/api.md
- platforms/codex.yaml
- scripts/kaola-acp.py
- scripts/kaola-tmux.sh
- scripts/validate.sh
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-tmux.sh
- skills/codex-kaola-project-runner/references/acp.md
- skills/codex-kaola-project-runner/references/platform.md
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-tmux.sh
- skills/codex-kaola-project-runner/scripts/platform.yaml
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-tmux.sh
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-tmux.sh
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-tmux.sh
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-tmux.sh
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-tmux.sh
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-tmux.sh
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-tmux.sh
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-tmux.sh
- tests/contract/test-issue-130-pty-retired.py
- tests/contract/test-issue-245-session-role.py
- tests/contract/test-issue-247-codex-child.py
- tests/contract/test-issue-260-transport.py

## Follow-Up Items

Keep issue260 OPEN. Acceptance settles only items7/8. It does not settle these
already-owned reports. No new issue or backlog change is needed.

- Item6: actual matching Grok Bot execution-service exit and its cleanup effects
  on an owned holder/child remain precisely untested, not reproduced. The report
  from KaolaTerminal names 2026-10-02 at 12:58, 15:18 and 19:13; the SIGTERM→SIGKILL
  cleanup cause is an inference. Original remote receipts were unavailable and
  were not read. Local normal-parent-exit and parent-group-SIGTERM simulations
  passed; they do not prove matching service-exit survival. No speculative
  holder-lifetime repair was authorized or made. Evidence:
  `/tmp/kpr-i260-transport-focused.log`, `/tmp/kpr-i260-transport-delivery.md`,
  `/tmp/kpr-i260-local-results.json`, `/tmp/kpr-i260-diagnosis.md` and the original
  issue body at https://github.com/KaolaBrother/kaola-project-runner/issues/260.
- Items4/5: record retire/migrate validation and legacy carrier-limit evidence
  belong to KPR issue259: https://github.com/KaolaBrother/kaola-project-runner/issues/259.
  No duplicate record-validation repair is included in 260.
- Items2/3 belong to Kaola-Workflow issue1114, per Host direction. Original remote
  reports cite KaolaTerminal 518, 522, 560 (repeat archive) and 524 (external advance).
  Local evidence remains `/tmp/kpr-i260-local-results.json` and
  `/tmp/kpr-i260-diagnosis.md`. The local divergence refusal does not prove an
  archive skip. This candidate contains no KW sink/finalize repair or force overwrite.
- Item9 reuses the passed local same-native Droid resume. Native id
  `2e86c675-87b2-426e-a1ac-5cc9d20948a4`; names droid-KPR-i260-resume and
  droid-KPR-i260-resume2; both stopped with residual_pids[]. Receipts:
  `/tmp/kpr-i260-droid-start.json`, -resume.json, -stop.json and -resume-stop.json.
  The pass does not disprove the remote report.

Authority and original evidence corrections remain in owner comments:
https://github.com/KaolaBrother/kaola-project-runner/issues/260#issuecomment-5989655052
https://github.com/KaolaBrother/kaola-project-runner/issues/260#issuecomment-5989658182
https://github.com/KaolaBrother/kaola-project-runner/issues/260#issuecomment-5990030614
The diagnosis-only statement in the original diagnosis file was superseded by
owner authorization; the original file stays intact.

## Readiness

Host accepted the independent repair. Ready to publish with
`issue_action: comment_keep_open` and `--keep-issue-open` through both finalize
and the existing merge sink. Archive only this run and release only its claim.
Preserve main dirty AGENTS, protected untracked documents/archive252 and other
active trees/claims. Preserve the two immutable done ledger lines in the archive.
Publication, keep-open forge state, claim release and cleanup must be verified
before reporting lifecycle completion.

## Finalize Findings

### residue_unattributed

The residue mirror did not copy the paths below out of the main checkout: this run's HEAD does not contain them. Presence in main, an untracked status, or a neighboring file this run committed is not evidence they belong to this run. Nothing was copied, staged, committed, deleted, reverted or relocated — they remain in the main checkout. Read them before the sink runs: commit what belongs to the run, leave what does not.

Paths left in the main checkout:

- docs/harness-acp-codex-160-live-2026-10-03.md
- docs/harness-acp-compat-2026-10-01.md
- docs/harness-acp-compat-2026-10-03.md
- docs/harness-acp-reverify-2026-10-01.md


## Finalization measurement reconciliation

The installed finalize transaction copied main owner AGENTS.md edits into its
automatic commit 358a31c8. This changed the candidate digest and produced the
final_validation_stale finding above. Main owner bytes stayed unchanged. Before
publication, own-branch correction d4d0e830 restored AGENTS.md to the accepted
candidate. All candidate bytes then matched e23040ae; the current code-tree digest
again matched the preserved original validation record. The original stale
measurement remains as evidence of the intermediate finalize state. No archived
validation hash was hand-edited. The immutable mission ledger bytes are preserved.
Receipts: `/tmp/kpr-i260-closeout-finalize.json` and
`/tmp/kpr-i260-closeout-source-reconcile.json`.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-260/.cache/final-validation.md
- kaola-workflow/archive/issue-260/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-260/finalization-summary.md
- kaola-workflow/archive/issue-260/mission-ledger.jsonl
- kaola-workflow/archive/issue-260/workflow-state.md
