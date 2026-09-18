# Finalization summary — Issue #84

project: issue-84
issue: #84 (fix: ZCode 3.12+ 原生会话 resume 恢复模型配置)
branch: workflow/issue-84
sink: merge
accepted candidate: fef74d15afcdef3c3bd165abbc121ab3805141e1 (outer ACCEPT)
adapter bytes at acceptance: 6dc12633ddb6e157 (unchanged by rebase and by render --write)

## Delivered

Native `sess_*` resume on ZCode 3.12+ now keeps the session's own Coding Plan model. The Issue
named one defect; the live wire had five, and the last two were found by running, not by reading:

1. `session/read` on 3.12.3 returns a message list with NO top-level `settings`, so
   `hydrate_settings()` never saw a model. It now reads both real transcript shapes — nested
   `info.model` and flat `info.modelId`/`info.providerId` — taking the newest complete pair by
   `info.time.created`, not array position.
2. `_resume_backend_session()` never called `push_account_config()` (only `materialize()` did), so
   the resumed app-server's provider registry was empty. This is the direct cause of #69's
   `Provider Registry 中不存在 Model` receipt, which that run had left as an open question.
3. `reregister_provider()` sent `session/setModel` with a top-level `runtimeModel` key that 3.12
   rejects with a ZodError.
4. It compared the persisted provider against `builtin:bigmodel-coding-plan` where a real
   persisted session names `account:bigmodel-individual-coding-plan`.
5. `session/resume` retried the pre-3.12 overlay after ANY failure, so an unknown or deleted
   session was reported as a `runtimeModel` schema error instead of its real reason.

The repair reuses the fresh-session path (`push_account_config()` + `select_account_model()`). No
new ledger, cache, waiting layer, guessed default, or loosened fallback. Nothing is substituted: an
off-plan model or a foreign account fails the resume closed without reaching `session/setModel`.

Found and fixed during review, same surface: a resumed session reporting its real provider made its
advertised model `currentValue` account-qualified while `on_set_config_option` accepted only
`builtin:*`, so a client echoing back the value it had just been handed was refused. Both ids for
the one enabled Coding Plan now round-trip; any other provider, including another account, is still
refused. `select_account_model()` now records the provider it had accepted, which also confines the
transcript derivation to the resume path.

## Files Changed

| File | Change |
| --- | --- |
| `scripts/kaola-zcode-acp.py` | new pure helper `persisted_model_from_messages()`; `hydrate_settings()` transcript derivation + `session/messages` fallback; `reregister_provider()` 3.12+ account path; `_resume_backend_session()` narrowed overlay retry; `select_account_model()` records the provider; `on_set_config_option()` accepts either enabled-plan id |
| `skills/zcode-kaola-project-runner/scripts/kaola-zcode-acp.py` | generated mirror, byte-identical, via `render-skills.py --write` |
| `tests/contract/test-issue-84-zcode-native-resume.py` | new, 18 tests |
| `tests/contract/fake-zcode-312-app-server.py` | additive `session/resume`/`session/read`/`session/messages` in the measured real shapes; no existing strictness relaxed |
| `scripts/validate.sh` | registers the new suite in `python_suites_all` and lane A |
| `CHANGELOG.md` | Issue #84 entry under Unreleased |
| `docs/zcode-host.md` | new "Resuming a native session's model (3.12+)" subsection |

## Test Coverage

New suite `test-issue-84-zcode-native-resume.py`, 18 tests: recovery from both real transcript
shapes; newest-wins by timestamp; fail-closed with NO `session/setModel` at all on absent,
malformed, off-plan or foreign-account metadata; no `runtimeModel` on the resume selection;
provider registered before selection; unknown session reports its own reason; resumed-session
config-option round trip and its foreign-account refusal; fresh-session path unaffected; credential
absent from ACP output, logs and the record on both success and failure paths.

Baseline proof: on `88042cd` the suite failed 7/13 on the exact defect message. Every guarantee was
mutation-checked, including the two the outer review asked for: reverting the round-trip fix
reproduces the reported refusal verbatim, and a mutation that forwards the persisted value past the
guards is caught where the previous weaker assertion passed.

## Validation

- `./scripts/validate.sh` on the integrated candidate `fef74d1`: **exit 0**, run in the foreground
  so the exit could not be lost. Receipt `evidence/validate-integrated-exit.txt` (exit + HEAD +
  adapter sha256); raw log `evidence/validate-integrated.log` — 24152 bytes, 70 `PASS`, 28
  `Ran N tests`, zero `^FAILED:`, zero `^SKIPPED:`, terminating sweep `residual_pids: []`.
- `./scripts/render-skills.py --write` then `--check`: exit 0, PASS, and `--write` left the tree
  unchanged (idempotent).
- Focused: issue-84 18/18, issue-79 19, zcode-acp 34, zcode-heartbeat 9/9 (166 checks), issue-65 27.
  Neighbour check after rebase: `test-issue-74-kaola-delegator.py` 151 assertions, 0 failed.
- Live acceptance, real ZCode.app 3.12.3 / CLI 0.16.5, ACP only, isolated repo, receipts in
  `evidence/live-frozen3/` bound to adapter `6dc12633ddb6e157` on both the start and resume
  receipts: native `sess_a7e56105-3d62-4d15-afc6-3665a513de43`; round 1 real reply; exact stop
  `stopped=true residual_pids=[] agent_exit_code=0`; `--resume` -> `state=ready`; round 2 answered
  on `account:bigmodel-individual-coding-plan\GLM-5.3` and quoted its own first reply back; final
  exact stop clean; deleted-session boundary `-32004 Session not found`.
- Live A/B control (`evidence/live/14-baseline-resume-AB.json`): the same native session resumed
  with the pre-fix adapter `cb029a22` still fails with the Issue #84 error, same machine.
- Honestly recorded negative: an earlier full validate on `249471b` was KILLED mid-run (no exit
  receipt, `[killed]`, 970 bytes, 0 suite executions). No PASS was claimed from it; the partial log
  is kept as `evidence/validate-249471b-KILLED-INCOMPLETE.log` and was superseded by the exit-0 run
  on `fef74d1`.

## Changed Paths

Reported by the finalize transaction; see `## Changed Paths` receipt appended by that run.

## Documentation Docking

`DOCKED` — evidence `.cache/doc-docking.md`. `CHANGELOG.md` and `docs/zcode-host.md` fixed;
`docs/api.md`, `platforms/zcode.yaml`, `README.md`, install/env and examples verified NO IMPACT with
the reason recorded for each. All docked facts transcribed from this run's receipts or the accepted
source; no invented field, method, or error code.

## Issue statement coverage

| Acceptance clause (Issue #84) | Satisfied by |
| --- | --- |
| 1. Isolated real 3.12.3 Coding Plan: create native session, one round, stop holder, exact `--resume sess_*`, second round; record native id, ACP id, model, real reply, exact-stop residual; distinguish the post-`session/close` deletion boundary | `evidence/live-frozen3/` (all ten receipts) + the `-32004 Session not found` boundary probe; A/B control in `evidence/live/` |
| 2. Targeted contract tests for the real `session/read` message-list shape and persisted model metadata; fail closed on error/missing metadata without switching account or model | `tests/contract/test-issue-84-zcode-native-resume.py` (18 tests), fail-closed asserting no `session/setModel` at all; mutation-checked |
| 3. `render-skills.py --check`, focused tests, `validate.sh` all green; outer independent acceptance of the frozen SHA before finalize | render `--check` PASS; focused suites green; `validate.sh` exit 0 on `fef74d1`; outer ACCEPT of `fef74d1` received before this finalization |
| No user global config change, no credential copy/print, no other sessions touched; ACP-only | No global config touched; no credential read, copied, decrypted or printed — credential-absence asserted by test on both paths; #74/#75/#81 untouched; PTY never used |

## Follow-Up Items

- **#85** (filed this run, `bug` + `P3`, verified OPEN with a 1869-char body): a fail-closed ZCode
  resume still advertises the model it just refused. Cosmetic ordering issue; the safety property
  (no substitution, no account switch, no `setModel`) holds and is asserted by test.
- Correction comment posted on #84 before closure (comment 5734812383): the Issue body described
  the symptom correctly but named one defect where the live wire had five; the comment records what
  the Issue turned out to be.
- Judged and deliberately NOT changed, with reasons recorded in `mission-list.md` mission 6:
  non-numeric / `NaN` timestamp degradation in the newest-wins rule (native ZCode timestamps are
  epoch ms throughout the adapter, and `NaN` is not emittable by `JSON.stringify`); "newest
  model-bearing message" versus a post-turn model switch (the measured wire exposes no better
  source); and two redundant-guard test-strength equivalences. Hardening these would be the
  speculative mechanism the project contract warns against.
- Not exercised live: the ACP-level `session/set_config_option` round trip has no Runner CLI
  surface, so it is covered by the mutation-checked contract test plus the live `observe` showing
  the account-qualified `currentValue`.

## Readiness

READY. Outer ACCEPT received for `fef74d15afcdef3c3bd165abbc121ab3805141e1`; docs docked and the
candidate re-validated after docking; all 10 missions done; no blocker outstanding.
No release, no global install, no other-run edits.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-84/.cache/doc-docking.md
- kaola-workflow/archive/issue-84/.cache/final-validation.md
- kaola-workflow/archive/issue-84/.cache/mirror-digest.json
- kaola-workflow/archive/issue-84/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-84/evidence/live-frozen/01-start.json
- kaola-workflow/archive/issue-84/evidence/live-frozen/02-round1-send.json
- kaola-workflow/archive/issue-84/evidence/live-frozen/03-round1-events.jsonl
- kaola-workflow/archive/issue-84/evidence/live-frozen/04-native-session-id.txt
- kaola-workflow/archive/issue-84/evidence/live-frozen/05-stop-exact.json
- kaola-workflow/archive/issue-84/evidence/live-frozen/06-start-resume.json
- kaola-workflow/archive/issue-84/evidence/live-frozen/07-round2-send.json
- kaola-workflow/archive/issue-84/evidence/live-frozen/08-observe-round2.json
- kaola-workflow/archive/issue-84/evidence/live-frozen/09-stop-final.json
- kaola-workflow/archive/issue-84/evidence/live-frozen/10-resume-deleted.json
- kaola-workflow/archive/issue-84/evidence/live-frozen/11-stop-gone.json
- kaola-workflow/archive/issue-84/evidence/live-frozen3/01-start.json
- kaola-workflow/archive/issue-84/evidence/live-frozen3/02-round1-send.json
- kaola-workflow/archive/issue-84/evidence/live-frozen3/03-round1-events.jsonl
- kaola-workflow/archive/issue-84/evidence/live-frozen3/04-native-session-id.txt
- kaola-workflow/archive/issue-84/evidence/live-frozen3/05-stop-exact.json
- kaola-workflow/archive/issue-84/evidence/live-frozen3/06-start-resume.json
- kaola-workflow/archive/issue-84/evidence/live-frozen3/07-round2-send.json
- kaola-workflow/archive/issue-84/evidence/live-frozen3/08-observe.json
- kaola-workflow/archive/issue-84/evidence/live-frozen3/09-stop-final.json
- kaola-workflow/archive/issue-84/evidence/live-frozen3/10-boundary.json
- kaola-workflow/archive/issue-84/evidence/live-frozen3/11-boundary-stop.json
- kaola-workflow/archive/issue-84/evidence/live/00-preflight.json
- kaola-workflow/archive/issue-84/evidence/live/01-start.json
- kaola-workflow/archive/issue-84/evidence/live/02-round1-send.json
- kaola-workflow/archive/issue-84/evidence/live/03-observe-round1.json
- kaola-workflow/archive/issue-84/evidence/live/04-native-session-id.txt
- kaola-workflow/archive/issue-84/evidence/live/04-round1-events.jsonl
- kaola-workflow/archive/issue-84/evidence/live/05-stop-exact-round1.json
- kaola-workflow/archive/issue-84/evidence/live/07-start-resume.json
- kaola-workflow/archive/issue-84/evidence/live/08-round2-send.json
- kaola-workflow/archive/issue-84/evidence/live/09-observe-round2.json
- kaola-workflow/archive/issue-84/evidence/live/09-round2-events.jsonl
- kaola-workflow/archive/issue-84/evidence/live/10-stop-final.json
- kaola-workflow/archive/issue-84/evidence/live/12-resume-deleted-session.json
- kaola-workflow/archive/issue-84/evidence/live/13-stop-gone.json
- kaola-workflow/archive/issue-84/evidence/live/14-baseline-resume-AB.json
- kaola-workflow/archive/issue-84/evidence/live/15-baseline-stop.json
- kaola-workflow/archive/issue-84/evidence/validate-final-docked-exit.txt
- kaola-workflow/archive/issue-84/evidence/validate-integrated-exit.txt
- kaola-workflow/archive/issue-84/finalization-summary.md
- kaola-workflow/archive/issue-84/live-resume-probe.sh
- kaola-workflow/archive/issue-84/mission-list.md
- kaola-workflow/archive/issue-84/workflow-state.md
