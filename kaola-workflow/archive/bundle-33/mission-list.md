# Issue #33: ACP observation retains initial model metadata after successful configuration

Implement https://github.com/KaolaBrother/kaola-project-runner/issues/33 under the supervisor's
bounded design (Codex owns design/acceptance). Worktree:
`/Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/bundle-33`, branch
`workflow/bundle-33`. `templates/grok-golden/` stays frozen; `skills/` is generated only.
Parallel run: #34 lives in `.kw/worktrees/bundle-34` (PR #35, devin-kaola-model-policy) — do not
touch its worktree, branch, records, or sessions. Main checkout is coordinator only.

Bounded design: holder keeps `session_meta.configOptions` aligned with actual native successful
`session/set_config_option` responses and `config_option_update` notifications, using native
returned `currentValue` (never the requested value) as proof. Failed/timeout updates must not
manufacture new current configuration. new/load/resume keep native response truth; absent/empty
configOptions are handled without inventing values. No new gates, retries, services, classifiers,
or global config writes. Only the selected session's native updates enter its metadata; observed
config persists through the existing record/state path so observe and status report fresh values.

1. item: Extend `tests/contract/mock-acp-agent.py` with env-driven config fixtures (`MOCK_ACP_CONFIG` JSON: `new`/`resume` configOptions, `set_result`, `set_error`, `set_drop`, `notify` config_option_update payload) so contract tests can script native config behavior per case.
   status: done
   dispatched: self (inline) — mock-acp-agent.py `_load_config_fixture` + new/resume/set paths
   result: PASS — `MOCK_ACP_CONFIG` JSON knobs `new`, `resume`, `set_result`, `set_error`, `set_drop`, `set_notify` implemented; existing scenarios unchanged.
2. item: Holder production change in `scripts/kaola-acp-holder.py`: merge usable native `configOptions` into `session_meta` on successful `op_set_config_option` and on `config_option_update` session updates (own-session only); preserve established baseline as `initial_config_options`; surface native `currentValue` in the set receipt; persist via existing record/state path; no fabrication on error/timeout/absent payloads.
   status: done
   dispatched: self (inline) — kaola-acp-holder.py `_apply_config_options`, 3 lifecycle assignment sites, op_set_config_option, on_session_update, write_record, op_state
   result: PASS — `session_meta.configOptions` now mirrors the last native-attested list (successful set result wholesale, own-session `config_option_update` notification); `initial_config_options` records the new/load/resume baseline; receipts carry `current_value` when native returns one; error/timeout/non-list payloads never mutate state; record.json + socket state both persist fresh values.
3. item: New focused regression file `tests/contract/test-issue-33-config-meta.py` (separate from test-acp-contract.py) wired into `scripts/validate.sh`: initial A → native B → observe/status B; notification update; failure keeps prior state; missing result no fabrication; timeout keeps prior state; resume native truth + session identity; absent configOptions not invented.
   status: done
   dispatched: self (inline) — tests/contract/test-issue-33-config-meta.py, validate.sh line added
   result: PASS — 9/9 tests PASS in 20.2s (incl. one real 15s holder timeout path); wired into validate.sh after test-acp-holder-continue.py.
4. item: `./scripts/render-skills.py --check` and `./scripts/validate.sh` pass on the candidate; `templates/grok-golden/` untouched.
   status: done
   dispatched: self (inline)
   result: PASS — render-skills --write WROTE 7 Skills (holder is embedded), --check PASS; validate.sh exit 0 (all suites: issue-9 7, direct-transport 5, devin-regressions 31, acp-contract 19, acp-watch 13, acp-follow 12, holder-continue 29, issue-33 9, runner-v2 4, generated-skills PASS, issue-24 14); grok-golden untouched.
5. item: Real ACP live proof on an authenticated platform (Devin or Codex; no PTY/Claude): start with `--model`, observe/status show native current config after successful set, exact stop, zero residual processes.
   status: done
   dispatched: self (inline) — real `devin acp` (CLI 3000.10.21) on scratch repo /tmp/kpr-33-live, session acp33-devin
   result: PASS — start --model swe-2-max: configured_options current_value swe-2-max/bypass; observe+status session_meta.configOptions model=swe-2-max mode=bypass while initial_config_options shows the issue's stale fusion/accept-edits baseline; events.jsonl shows config_options_applied for set_config_option AND 3 native config_option_update merges; send→"ACP33OK" turn_completed; stop residual_pids=[] agent_exit 0, pids dead. Evidence: kaola-workflow/bundle-33/evidence/acp-live-33.md + 5 receipt JSONs.
6. item: Surgical docs/changelog entry for issue #33 only.
   status: done
   dispatched: self (inline) — CHANGELOG.md Unreleased bullet, docs/api.md one paragraph
   result: PASS — CHANGELOG #33 bullet added; api.md documents current-vs-baseline semantics and current_value evidence.
7. item: Commit, push `workflow/bundle-33`, open PR linked to #33, hand back SHA/PR/tests/evidence/Workflow state; stop before merge (supervisor integrates PR #35 first).
   status: done
   dispatched: self (inline) — commit/push/PR next
   result: PASS — committed 2df269d5d3cb0b10c9017613c0b56e4c68b1e68a (13 files, +642/-3) on workflow/bundle-33; pushed to origin; PR https://github.com/KaolaBrother/kaola-project-runner/pull/37 OPEN (non-draft, base main, "Fixes #33"); worktree + evidence preserved for finalization; stopped before merge. Doc-docking follow-up f4ef35b pushed (design doc record-field line).
8. item: Finalization prep + integration on supervisor main-ready signal: (a) DONE — final-validation receipt (.cache/final-validation.md verdict pass @ tree-hash 4ed916aa), doc-docking DOCKED (.cache/doc-docking.md), finalization-summary.md written; (b) PENDING — once origin/main carries #34 (PR #35), merge fresh main into workflow/bundle-33 preserving Cursor acp_init_meta init metadata AND #33 current-config updates, regenerate skills via render-skills.py --write (never hand-merge generated copies), rerun affected tests + live observe-current-model proof, then resume finalize close/archive/sink.
   status: done
   dispatched: self (inline) — merge origin/main@3650a28 after supervisor main-ready
   result: PASS — merged 527ecba: only CHANGELOG (union both bullets) + mock-acp-agent (combined #34 config_options()/caps-checks with #33 config_fixture, fixture null=omit) conflicted; holder init-meta + config-merge coexist; skills regenerated via render --write (--check PASS); test platform moved to opencode (zero implicit config calls) in 458cdff; merged candidate: issue-33 9/9, acp-contract 38/38, validate.sh exit 0; live devin acp33-devin2 observe/status current swe-2-max/bypass vs baseline fusion/accept-edits, 5 config_options_applied, ACP33MERGED, stop residual []; final-validation receipt re-recorded @ fe0f5627; pushed; PR #37 updated.
