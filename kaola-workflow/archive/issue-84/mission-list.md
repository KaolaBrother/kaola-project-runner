# Goal: ZCode 3.12+ native `sess_*` resume restores the session's own Coding Plan model/provider (Issue #84)

Scope lock: only the ZCode adapter's native-resume model/provider recovery path
(`scripts/kaola-zcode-acp.py`), its targeted tests, and necessary docs. Not #81 steering code,
not #74 Delegator, not #69 immutable mission results. ACP-only. No credential copy/print.
Worktree: `.kw/worktrees/issue-84`, branch `workflow/issue-84`.
Baseline `88042cd` -> `93f5a18` -> `5483950` -> `249471b` -> REBASED ONTO `origin/main`
`3a80269` (#74 sunk) -> INTEGRATED FROZEN CANDIDATE
`fef74d15afcdef3c3bd165abbc121ab3805141e1` (adapter bytes UNCHANGED `6dc12633ddb6e157`). Awaiting the outer independent
ACCEPT; no finalize, archive, sink, issue close, or release from me.

## 1. Pin the real gap from #69 original live receipts and the current adapter
- item: Read `.kw/verify-69-legs/legB/evidence/09|10-probe-resume-read*.txt` and the adapter's
  `hydrate_settings` / `reregister_provider` / `_resume_backend_session`; state the exact
  `session/read` shape and every wire-level reason native resume loses the model.
- status: done
- dispatched: self (read-only, main checkout)
- result: Two independent defects, both wire-confirmed on real ZCode 3.12.3.
  (a) `session/read` returns `{"messages":[...]}` with NO top-level `settings`; persisted model
  lives at `messages[*].info.model.{providerId,modelId}` (`session/messages` uses flat
  `info.providerId`/`info.modelId`). `hydrate_settings` only reads `settings.model.current`, so
  `session.model_id`/`provider_id` stay None and `reregister_provider` raises
  "resumed session reports no persisted model".
  (b) `reregister_provider` sends `session/setModel` with a top-level `runtimeModel` key; 3.12.3
  rejects it with -32602 ZodError `Unrecognized key: "runtimeModel"`. The working fresh-session
  path (`select_account_model`) already omits `runtimeModel` and adds `options.reasoningLevel`.
  Live receipt truth: resume itself succeeds only when the client answers
  `session/requestRuntimePreferences` (unanswered -> -32022, session never active: receipt 09).
  Receipt 10's `setModel account+reasoning` -> "Provider Registry 中不存在 Model" was taken with
  `headersApplied:false` (probe refused the credential); whether the real adapter's header answer
  registers the account provider on a resumed session is the open question mission 5 must settle.

## 2. Targeted contract tests for the real shapes (test custody)
- item: Tests pinning: persisted model recovered from the real `session/read` message-list shape
  (and the `session/messages` flat shape); newest-wins when messages disagree; fail closed with no
  account/model substitution when metadata is absent/foreign/malformed; resume `setModel` carries
  no `runtimeModel` on a 3.12+ backend. Must fail on the frozen baseline.
- status: done
- dispatched: tdd-guide (clean context) in worktree `.kw/worktrees/issue-84`, baseline
  `88042cd`; landed `tests/contract/test-issue-84-zcode-native-resume.py` plus additive
  `session/resume`/`session/read`/`session/messages` handlers in
  `tests/contract/fake-zcode-312-app-server.py` and the `scripts/validate.sh` registration.
- result: baseline verdict re-run by me, not taken on trust: `Ran 13 tests ... FAILED
  (failures=7)`, all 7 on `-32000 resumed session reports no persisted model (session/read
  failed)`. The 6 fail-closed/secrecy tests pass on baseline by construction and stand as
  regression guards. #79 suite unchanged and still 19 OK. The agent's mutation probe surfaced the
  FOURTH defect recorded in mission 3. The suite later grew to 16 tests: one for the FIFTH defect
  (mission 5) and two guarding the fresh-session path (mission 6), each mutation-checked by me.

## 3. Minimal adapter repair
- item: Derive the persisted model from the message list when no top-level `settings`; reuse the
  #79 provider/model resolution and the fresh-session `setModel` shape on resume. No new ledger,
  cache, waiting layer, guessed default, or loosened fallback.
- status: done
- dispatched: self (inline; I held the design and the surface is one cohesive adapter path)
- result: `scripts/kaola-zcode-acp.py`, three edits, +97 lines, no new state and no new layer.
  (1) new pure helper `persisted_model_from_messages()` reads BOTH real transcript shapes
  (`info.model.{providerId,modelId}` and flat `info.modelId`/`info.providerId`) and takes the
  newest complete pair by `info.time.created`, falling back to array order only as a tiebreak;
  an incomplete/non-string/absent pair returns None so the caller fails closed.
  (2) `hydrate_settings()` falls back to `session/messages` when `session/read` is unimplemented,
  and derives the model from the transcript when there is no top-level `settings`.
  (3) `reregister_provider()` on the 3.12+ account path now reuses the fresh-session path
  verbatim -- `push_account_config()` then `select_account_model()` -- which fixes defects 2 and 3
  (empty registry; `runtimeModel` key rejected by -32602) and defect 4 below. The pre-3.12 overlay
  branch is untouched and still runs when `legacy_overlay` or no account resolves.
  FOURTH defect (found by the test agent's mutation probe, confirmed against receipt 10):
  `reregister_provider` compared the persisted provider against `choice["provider_id"]`
  (`builtin:bigmodel-coding-plan`), but a real persisted 3.12 session names the ACCOUNT provider
  (`account:bigmodel-individual-coding-plan`), so even a correct hydration would have been refused.
  The account path now compares against `account["account_id"]` and still refuses a foreign
  account or an off-plan model without ever calling setModel.
  Verified: issue-84 suite 13/13 OK; #79 19 OK; zcode-acp 34 OK; zcode-host 3/3 47 checks;
  zcode-heartbeat 9/9 166 checks; issue-65 steering 27 OK; issue-51 integration 4/6 (pre-existing
  shape, to be confirmed against the validate baseline).

## 4. Focused + full gates
- item: `./scripts/render-skills.py --check`, the focused ZCode contract suites, and
  `./scripts/validate.sh` all green on the frozen candidate; record exact outcomes.
- status: done
- dispatched: self; final full `validate.sh` on the frozen tree, into
  `kaola-workflow/issue-84/evidence/validate-final.log`.
- result: on frozen `93f5a18`: `render-skills.py --check` PASS (9 workers + orchestrator +
  grok-bot bridge, budgets OK); `./scripts/validate.sh` **VALIDATE_FINAL_EXIT=0**, 63 PASS lines,
  zero `FAILED:` and zero real `SKIPPED:` (the one "SKIPPED" string in the log is a test docstring
  in the Issue #83 suite, not a skipped suite). The issue-84 suite ran inside validate at its
  registered position (14 dots / `Ran 14 tests in 1.299s` / OK). No `zcode-i84*` process survived
  the run.
- note: first full run was VALIDATE_EXIT=1 -- honestly recorded, and the cause was mine:
  `test-issue-9-contract.py` caught `skills/zcode-kaola-project-runner/scripts/kaola-zcode-acp.py`
  stale because I edited the adapter after `render-skills.py --write`. The background wrapper
  reported "exit code 0" because it ended with an `echo`; the real exit was in the task output.
  Re-rendered; `--check` PASS. Focused suites after the final adapter change: issue-84 14/14 OK,
  issue-79 19 OK, zcode-acp 34 OK.

## 5. Isolated real ZCode 3.12.3 native two-round resume evidence
- item: Isolated ACP only: create native session, complete round 1, exact-stop the holder,
  `--resume sess_*`, complete round 2. Record native id, ACP id, model actually used, real replies,
  exact-stop residual[], and the `session/close`-then-delete boundary that is NOT recoverable.
- status: done
- dispatched: self; isolated repo `/tmp/i84-live-repo`, session `zcode-i84-live`, real
  ZCode.app 3.12.3 / CLI 0.16.5, ACP only. Receipts in
  `kaola-workflow/issue-84/evidence/live/`.
- result: PASS, with a live A/B on the SAME native session.
  Round 1 (fresh): ACP `zcode-1`, native `sess_6fe8bc2d-a913-47cb-82f4-40d95c5a1c9e`
  (`native_session_identity` event, `04-round1-events.jsonl`), model
  `account:bigmodel-individual-coding-plan\GLM-5.3`, real reply
  "I84-ROUND-ONE. I am ZCode, powered by GLM-5.3." Exact stop: `stopped=true`,
  `residual_pids=[]`.
  Resume (fixed adapter `060408e9f3c5`): `state=ready`, `acp_session_id` adopts
  `sess_6fe8bc2d-...`, `model_selection.source=resume-preserved`; `session_meta` after the turn
  still reports `account:bigmodel-individual-coding-plan\GLM-5.3`. Round 2 real reply:
  "I84-ROUND-TWO. I am ZCode, powered by GLM-5.3. In my first reply I sent: I84-ROUND-ONE. I am
  ZCode, powered by GLM-5.3." -- it recalled round 1's exact content, so this is true
  conversation continuity, not a fresh session. Final exact stop: `stopped=true`,
  `residual_pids=[]`, `swept_child_pgids=[]`, `agent_exit_code=0`.
  A/B (`14-baseline-resume-AB.json`): the SAME `sess_6fe8bc2d-...` resumed with the baseline
  adapter `cb029a22a233` gives `state=error`, `resume-failed`, "resumed session reports no
  persisted model (session/read failed); refusing to substitute the provider default". Same
  machine, same session, same ZCode -- the adapter change is the only difference.
  Boundary (`12-resume-deleted-session.json`): a native id that does not exist (the
  `session/close`-then-delete case) is NOT recoverable and now reports its own reason,
  `-32004 Session not found: sess_00000000-...`, with `state=error` and no session adopted.
  Before the guard added in mission 3, this same probe returned a masked
  `-32602 Unrecognized key: "runtimeModel"` -- see the FIFTH defect below.
  FIFTH defect (found by this live run, not by reading): `_resume_backend_session` retried
  `session/resume` with the pre-3.12 `runtimeModel` overlay after ANY failure, so on 3.12+ every
  ordinary resume failure was reported as a schema error about a key that build does not accept.
  It now retries only on the pre-3.12 `Model config is missing` signal -- the same discipline
  `create_backend_session` already used -- and re-raises otherwise. Covered by a new test
  (`test_unknown_session_reports_its_own_reason_not_a_schema_error`) that I mutation-checked:
  removing the guard reproduces the exact masked receipt seen live.
  Cleanup: no `zcode-i84*` process or tmux session survives; other sessions' holders untouched.
- RE-RUN ON THE FROZEN BYTES (closing review finding (b)): the first live run's receipts attested
  `bridge.sha256 6abcd2b3...`, an uncommitted intermediate, so the whole two-round acceptance was
  repeated on frozen `5483950` / adapter `a078052256e5`. Receipts in
  `kaola-workflow/issue-84/evidence/live-frozen/`; every one of them carries
  `bridge.sha256 = a078052256e5e9db`.
  Round 1: native `sess_b21f32e8-a771-4aa2-856b-d27912a82a21`, reply "I84F-ROUND-ONE — 我是由
  GLM-5.3 模型驱动的 ZCode（account:bigmodel-individual-coding-plan/GLM-5.3）。", `end_turn`.
  Exact stop: `stopped=true`, `residual_pids=[]`, `swept_child_pgids=[]`, `agent_exit_code=0`.
  Resume: `state=ready`, `acp_session_id=sess_b21f32e8-...`, `source=resume-preserved`.
  Round 2: "I84F-ROUND-TWO — I am ZCode, powered by GLM-5.3
  (account:bigmodel-individual-coding-plan/GLM-5.3). First reply: I84F-ROUND-ONE" -- it quoted its
  own first reply, so continuity is real. Post-resume `session_meta` model
  `account:bigmodel-individual-coding-plan\GLM-5.3`, mode `yolo`. Final exact stop:
  `stopped=true`, `residual_pids=[]`, `agent_exit_code=0`. Boundary on the same bytes:
  `-32004 Session not found`, `state=error`. No `zcode-i84*` process survived.
  The A/B against baseline `cb029a22` in `evidence/live/14-baseline-resume-AB.json` still stands
  unchanged as the control.
- RE-RUN #2 ON FROZEN `249471b` (adapter bytes `6dc12633ddb6e157`): the round-2 P2 fixes mutated
  the adapter, which invalidates the `a078052256e5` live PASS, so the whole two-round acceptance
  was repeated again. Receipts in `kaola-workflow/issue-84/evidence/live-frozen3/`; `01-start` and
  `06-start-resume` both carry `bridge.sha256 = 6dc12633ddb6e157`.
  Round 1: native `sess_a7e56105-3d62-4d15-afc6-3665a513de43`, reply "I84G-ROUND-ONE. I am ZCode,
  powered by GLM-5.3 (account: bigmodel-individual-coding-plan/GLM-5.3).", `end_turn`.
  Exact stop: `stopped=true`, `residual_pids=[]`, `agent_exit_code=0`.
  Resume: `state=ready`, `acp_session_id=sess_a7e56105-...`.
  Round 2: "I84G-ROUND-TWO. I am ZCode, powered by GLM-5.3. In my first reply I sent:
  I84G-ROUND-ONE." -- quotes its own first reply, so continuity is real.
  Post-resume `session_meta` model `account:bigmodel-individual-coding-plan\GLM-5.3`. Final exact
  stop: `stopped=true`, `residual_pids=[]`, `swept_child_pgids=[]`, `agent_exit_code=0`.
  Boundary on the same bytes: `-32004 Session not found`, `state=error`. No `zcode-i84*` process
  survived.

## 6. Independent review of the exact frozen candidate
- item: Clean-context review of the frozen SHA's real diff: scope creep, fail-closed integrity,
  credential safety, test custody. Findings return to me for the verdict.
- status: done
- dispatched: code-reviewer (clean context) on the exact frozen diff `git diff 88042cd 93f5a18`,
  briefed to attack fail-closed integrity, the newest-wins rule, pre-3.12/fresh-path regression,
  credential safety, and test custody/vacuity.
- result: no correctness defect found in the resume fix; fail-closed verified sound by both
  tracing and mutation (6 of 8 of the reviewer's mutations were caught by the suite), no fake
  strictness relaxed, #79 not weakened, generated mirror byte-identical, credential safety clean,
  no scope drift into #81/#74/grok-golden. I accepted and acted on three findings:
  (a) FRESH-PATH SIDE EFFECT (accepted, fixed): because `select_account_model` set only
  `session.model_id`, my `not (model_id and provider_id)` gate also fired on newly created
  sessions, adding a `session/messages` round trip and, latently, letting the transcript overwrite
  a selection the backend had just accepted. `select_account_model` now records
  `session.provider_id` on acceptance, which confines the transcript derivation to resume. I
  reproduced the reviewer's exact fresh-path call sequence by mutation and added two regression
  tests.
  (b) LIVE-EVIDENCE CUSTODY (accepted, my error): the successful two-round resume receipts carry
  `bridge.sha256 6abcd2b3...`, an uncommitted intermediate, NOT the frozen bytes -- only the
  boundary probe and the baseline A/B were attested. My earlier claim of `060408e9` contradicted
  its own receipt. Re-run on the frozen tree rather than argued away; see mission 5's re-run
  result.
  (c) CHANGELOG "pre-3.12 overlay path is unchanged" overstated: reworded to say the
  `reregister_provider` legacy branch is unchanged while the resume overlay retry now narrows to
  the `Model config is missing` signal.
  Also fixed from the review: the fake answered an unknown session `1404` where real 3.12.3
  returns `-32004 Session not found` (now matches the live receipt), the duplicate
  `session/messages` call when the first read already came from that method, and this file's
  mission 2/6 bookkeeping, which the reviewer correctly flagged as still `todo`.
  Judged and NOT changed: the non-numeric/NaN timestamp degradations (native ZCode timestamps are
  epoch ms everywhere in this file, and `NaN` is not emittable by `JSON.stringify`; hardening
  these would be speculative mechanism); "newest model-bearing message" vs a post-turn model
  switch (the measured wire exposes no better source, and the helper's own docstring is accurate);
  the cosmetic `config_option_update` on a fail-closed resume (pre-existing, and no `setModel` is
  sent); and the two test-strength gaps, which are redundant-guard equivalences today.

## 8. Outer review round 2: two P2 gaps on `5483950` (NOT ACCEPTED)
- item: (1) a resumed session advertises `account:...\GLM-5.3` as its model `currentValue` while
  `on_set_config_option` accepted only `choice['provider_id']` (`builtin:*`), so a client echoing
  that advertised value back is provider-refused; make the enabled account value round-trip
  without permitting a foreign account or changing the billing path, with a focused round-trip
  test on a resumed session. (2) `assert_no_substitution` only forbade attempts whose model id is
  in `PLAN_MODELS`, so a regression forwarding the off-plan/foreign persisted value verbatim would
  be backend-refused while the test still passed; assert no `session/setModel` attempt at all and
  add an adversarial check.
- status: done
- dispatched: self (inline; both land on the surface I already own)
- result: (1) `on_set_config_option` now accepts either id for the ONE enabled Coding Plan --
  `choice['provider_id']` or `account['account_id']` -- and refuses everything else, including
  another account, before any wire call. Related defect found while fixing it and also repaired:
  the trailing `session.provider_id = provider_id` overwrote what `select_account_model` had just
  committed, so after a 3.12+ mid-session switch the session recorded `builtin:*` rather than the
  account it actually runs on; that assignment now belongs to the pre-3.12 branch only. Two new
  tests: `test_advertised_model_value_is_accepted_back` (asserts the advertised value is among its
  own options, round-trips without error, and lands on the account provider with no `runtimeModel`
  and `persistAsWorkspaceLastUsed=false`) and `test_round_trip_still_refuses_a_foreign_account`.
  Mutation-checked: reverting the `enabled` set reproduces the exact refusal the outer review
  described -- "provider account:bigmodel-individual-coding-plan is not the enabled GLM Coding
  Plan provider (builtin:bigmodel-coding-plan); refusing".
  (2) `assert_no_substitution` now asserts `set_model_attempts == []` AND that `session/setModel`
  is absent from the backend's ordered call log, keeping the plan-model check only as a secondary
  guard. Adversarial mutation (guards bypassed, persisted value forwarded verbatim) is now caught
  on `GLM-9-not-in-plan` / `account:someone-else`, exactly the case the old assertion let through.
  Regression caught and fixed honestly rather than by editing someone else's test:
  `test-zcode-acp-contract.py:809` pins the substring "not the enabled GLM Coding Plan provider",
  which my reworded refusal had dropped; the message now carries it and lists both accepted ids.
  Suite is 18 tests. Not exercised live: the ACP-level `session/set_config_option` round trip has
  no Runner CLI surface, so it is covered by the mutation-checked contract test plus the live
  `observe` showing the account-qualified `currentValue`; building a bespoke ACP client for it
  would be the harness the project contract warns against.

## 9. Full validate on `249471b`: KILLED, status UNKNOWN (no PASS claimed)
- item: Determine the exact exit/status of the full `validate.sh` run started on frozen `249471b`,
  without inferring PASS from a partial log.
- status: done
- dispatched: self
- result: the run did NOT complete and its exit status is UNKNOWN. It was killed, not finished.
  Evidence, all four independent: the exit receipt `/tmp/i84-val3.txt` is ABSENT, so the subshell
  never reached its `echo "VALIDATE_EXIT=$?"` and `validate.sh` never returned; the harness task
  output file ends in `[killed]`; the log is 970 bytes and stops right after
  `installer runtimes acceptance: PASS` plus one sweep line; it carries 13 `PASS` markers where a
  complete run of this same tree produced 63, and ZERO `Ran N tests` lines, so not one python
  suite had even reported. I claim NO validate result for `249471b`. The partial log is renamed
  `evidence/validate-249471b-KILLED-INCOMPLETE.log` so it cannot be mistaken for a pass.
  Still valid and unaffected, because they completed and were recorded before the kill:
  `render-skills.py --check` PASS, the focused suites (issue-84 18/18, issue-79 19, zcode-acp 34,
  zcode-heartbeat 9/9, issue-65 27), and the `live-frozen3` receipts bound to adapter bytes
  `6dc12633ddb6e157`.
- next: #74 is running its own accepted-candidate full validate right now (pids under
  `.kw/worktrees/issue-74`), so I am NOT starting a competing full run. Once #74's sink lands I
  rebase this clean branch onto the new `origin/main`, re-render, and run full validation on the
  integrated SHA.

## 10. Rebase onto integrated main and full validation there
- item: Rebase the clean branch onto `origin/main` `3a80269` (#74 sunk), preserve Kaola-Delegator
  and the new docs plus my native-resume change, resolve CHANGELOG semantically, re-render, and
  run the full `validate.sh` on the integrated SHA with an exact captured exit.
- status: done
- dispatched: self
- result: PASS. Rebased cleanly; 3 commits now sit on `3a80269`, HEAD
  `fef74d15afcdef3c3bd165abbc121ab3805141e1`, working tree clean.
  Two conflicts, both expected and both resolved by keeping BOTH sides:
  `scripts/validate.sh` `python_suites_all` now lists `test-issue-74-kaola-delegator.py` AND
  `test-issue-84-zcode-native-resume.py` (verified lane invariant `a | b == all`, 37 suites, no
  suite missing from a lane and none in a lane but not in `all`); `CHANGELOG.md` keeps my #84
  entry followed by #74's whole 74-line block (3 `Issue #84` mentions, 5 `Issue #74`, zero
  conflict markers). #74's own entry already said #84's live proof lands separately, so the two
  are complementary, not competing.
  Nothing of mine touches #74's surface: my net diff vs `3a80269` is exactly my six files
  (+863/-40). `skills/kaola-delegator/` and `hosts/grok-bot/kaola-delegator.md` are present and
  untouched; #81 and #75 untouched.
  ADAPTER BYTES UNCHANGED: `scripts/kaola-zcode-acp.py` is still `6dc12633ddb6e157` after both the
  rebase and `render-skills.py --write`, and the generated mirror matches it. The `live-frozen3`
  two-round native-resume proof therefore still binds to the exact bytes in this integrated tree,
  so no live re-run was required by the outer instruction's own condition.
  `render-skills.py --write` then `--check`: both exit 0, PASS (9 workers + kaola-project-runner +
  kaola-delegator + grok-bot bridge, budgets OK), and `--write` left the tree unchanged, i.e. the
  render is idempotent here.
  FULL VALIDATE, run in the FOREGROUND so the exit could not be lost to a background kill:
  **`VALIDATE_EXIT=0`**, receipt written to `evidence/validate-integrated-exit.txt` alongside HEAD
  and the adapter sha256. Raw log `evidence/validate-integrated.log`: 24152 bytes, 70 `PASS`
  markers, 28 `Ran N tests` executions, ZERO `^FAILED:` and ZERO `^SKIPPED:` lines, terminating in
  the grok-bot verify PASS and a sweep with `matched_pids: []` / `residual_pids: []`. Compare the
  killed run it replaces: 970 bytes, 13 PASS, 0 suite executions.
  Cross-check that I did not break the newly landed neighbour: `test-issue-74-kaola-delegator.py`
  151 assertions / 0 failed, issue-84 18/18 OK, issue-79 19 OK, zcode-acp 34 OK. No `zcode-i84`
  process survived.

## 7. Documentation of real behavior
- item: Record the resume model-recovery behavior and its boundary where the repo already documents
  ZCode host/adapter behavior; no speculative docs.
- status: done
- dispatched: self
- result: `CHANGELOG.md` Unreleased entry for Issue #84, stating the five measured wire defects,
  what is now read and re-registered, the explicit non-substitution guarantee, the unchanged
  pre-3.12 path, and the live 3.12.3 verification including the failing pre-fix A/B. No doc claims
  behavior the diff does not implement; `platforms/zcode.yaml` already described the 3.12+
  account path generically and needed no change.
