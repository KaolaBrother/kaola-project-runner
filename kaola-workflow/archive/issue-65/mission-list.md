# Goal: Issue #65 — native steering tool coverage across all nine Worker platforms, plus the ZCode Host post-dispatch event-wait contract

Run facts: branch `workflow/issue-65`; worktree
`/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner/.kw/worktrees/issue-65`;
baseline `bb6d74022bd187e86307a00b93ea8c869caf078f` (verified on site).
Runner session `claude-code-kaola-issue65-0918`. Outer Codex holds acceptance; no finalize,
merge, push, issue close, release, or global install before it accepts.
Evidence lands under `kaola-workflow/issue-65/evidence/`.
One authorized implementer (this session): no implementation or review subagents.

## 1. Nine-platform native steering capability investigation
item: Derive the platform list from `platforms/*.yaml` and investigate each platform's NATIVE mid-turn steering entry point — transport, protocol surface, version/pin, negotiation evidence — recording supported / unsupported / unknown separately from what the Runner currently exposes. Distinguish active-turn injection from next-turn queueing and from cancel+new-turn; never report "bridge missing" as "natively unsupported"; missing local environment stays unknown, not unsupported.
status: done
dispatched: self (inline, single authorized implementer); findings land in kaola-workflow/issue-65/evidence/steering-capability-matrix.md
result: DONE. All nine platforms reached and answered on this machine; no row left `unknown`. Matrix: `kaola-workflow/issue-65/evidence/steering-capability-matrix.md`; raw receipts under `evidence/idle/`, `evidence/fallback/`, `evidence/live/`; probe `evidence/probes/steer_probe.py`. SUPPORTED: **codex** (adapter 1.11.0 advertises top-level `_meta.steering.supported=true`, serves `_session/steering`) and **claude-code** (cli 2.1.272 injects a second stream-json stdin user message into the RUNNING turn — one `result` event, `num_turns: 3`, sentinel replaced the remaining tool steps; the vendored bridge 0.1.0 was the gap, not the platform). UNSUPPORTED with versioned evidence: cursor-cli 2026.09.10-fd3934a, devin 3000.10.21, droid 0.220.0, grok 1.0.25, kimi-cli 2.0.0, opencode 1.18.17 — all four candidate entries (`_session/steering`, `session/steering`, `session/steer`, `_session/steer`) answer -32601 and no `initialize` advertises steering. **zcode 0.16.5**: engine-capable (`turn.steerQueued`/`turn.steerDrained`, `steerTurn`) but NOT exposed on the app-server `--stdio` surface — no steer method in the method table, `session/send` schema is `.strict()` with no delivery field, `sendPrompt` throws -32010 while a turn is active; live run confirmed. Second-ordinary-prompt fallback characterised live for all six unsupported ACP platforms: cursor cancels the original; grok queues; kimi never answers the second request; devin/opencode/droid accept it concurrently but settle BOTH request ids together, losing terminal-state attribution — recorded explicitly as not-steering.
## 2. Unified `steer` transport operation with native mappings
item: Implement `steer` alongside send/wait/cancel/stop in the shared routing (`scripts/kaola-tmux.sh`, `scripts/kaola-acp.py`, `scripts/kaola-acp-holder.py`, `scripts/kaola-zcode-acp.py`, platform adapters) for every natively supported platform, reusing exact session/repo/transport routing with no scheduler or second stdin writer. Preserve the original active prompt's output and terminal-state attribution; express injected / not-consumed / unsupported / unknown as distinct receipt facts without a second lifecycle.
status: done
dispatched: self (inline); implementation in the issue-65 worktree on `workflow/issue-65`
result: DONE and live-verified on both supported platforms. `kaola-tmux.sh` routes `steer` to ACP and answers `steer-unsupported-transport` over PTY; `kaola-acp.py` reads the manifest (so a holder started before this release needs no restart) and short-circuits `unsupported`; `kaola-acp-holder.py::op_steer` sends the native request only while a turn is active and maps `injected` / `started_new_turn` / `not_consumed` / `unsupported` / `rejected` / `unknown` onto `steer_outcome` + `steer_consumed`, reporting `turn_request_id`, `turn_request_id_after`, `turn_request_id_preserved`. Claude Code's native channel was opened by rebuilding the vendored bridge: streaming turns now run `claude -p --input-format stream-json` with the prompt on an open stdin and the bridge serves `_session/steering` via the SDK `extMethod` (`vendor/claude-code-acp/src/{claude-runner,agent}.ts`; `kaola-dist.py --check` byte-identical). LIVE through the real Runner: codex `steer_outcome: injected`, turn_request_id 7 preserved, original prompt settled `end_turn` with "Step 1 completed.STEERED-OK-65"; claude-code `injected`, id 7 preserved, `end_turn` with "...Step 3 done...STEERED-OK-65"; both `stop` clean with `residual_pids []`. Receipts in `evidence/live/`. Also fixed a real defect the ZCode probe exposed: `kaola-zcode-acp.py::on_session_prompt` overwrote the active `turn_request_id`, orphaning the original request forever and handing its completion to the newcomer; it now refuses the concurrent prompt with -32010.
## 3. Capability-accurate tool exposure through manifests, templates, and renderer
item: Carry the per-platform native steering fact through `platforms/*.yaml`, the shared Worker template and references, and the renderer, so supported platforms document a callable `steer` tool with its real semantics and unsupported platforms never advertise one while the unified route still answers a clear unsupported-and-unconsumed. Regenerate `skills/` and `hosts/grok-bot/`; keep `templates/grok-golden/` frozen.
status: done
dispatched: self (inline)
result: DONE. Three new manifest keys on all nine platforms — `native_steering`, `acp_steer_method`, `steering_summary` — with renderer validation that a non-`supported` platform cannot carry an entry and every platform must record its evidence. The renderer derives a `{{STEERING_BLOCK}}`: supported platforms get a runnable `steer` command, unsupported ones get an explicit "offers no `steer` tool" statement, and `references/acp.md` gains the full outcome table plus the per-platform verdict. Budgets held without raising any limit (progressive disclosure stayed a locked invariant): `ACP_QUIRKS` moved out of the worker `SKILL.md` into `references/acp.md` where it was already rendered, the Grok Bot walkthrough was compressed into its own reference, and zcode's duplicated provider mechanics were dropped from `acp_quirks` (they are stated verbatim in `launch_summary`). `render-skills.py --write` and `--check` both PASS with `budgets OK`; `templates/grok-golden/` and `hosts/grok-bot/` unchanged.
## 4. ZCode Host post-dispatch event-wait contract
item: Write the ZCode Host event-wait contract into the canonical orchestrator Skill's ZCode Host section and the dispatch references: non-blocking background dispatch with acceptance check, finish this beat's coordination and update the one project heartbeat prompt, then end the turn naturally and wait for Worker turn-end/exit events — no sleep, poll, or blocking wait, no stop/cancel to manufacture waiting, and a Host awaiting in-flight Workers is not a stoppable idle Worker. Keep the shared main Skill and PROJECT_RUNNER_HEARTBEAT_V2 one specification; other Hosts' carriers keep their meaning.
status: done
dispatched: self (inline); includes the owner's 2026-09-18 comment (issuecomment-5723734779) requiring operating instructions, not only mechanism
result: DONE. The main Skill's ZCode Host paragraph now carries the action rules (identity bootstrap, `KAOLA_ACP_HEARTBEAT_HOST` per worker `start` plus the `heartbeat_host` receipt check, `send --no-wait` read as accepted-not-done, update the one `.kaola/heartbeat-prompt.json`, then end the turn normally — never sleep, poll, blocking-`wait`, or stop/cancel to manufacture a wake-up), and step 5 of the execution loop states that a Host awaiting in-flight workers or open close-out is not a stoppable idle worker and gets no "continue". The runnable role-by-role procedure is the new on-demand reference `references/zcode-host-dispatch.md` (6857 B, generated from `templates/orchestrator/references/zcode-host-dispatch.md.tmpl`): three never-interchangeable identities; the outer Agent's start-plus-bootstrap example; the exact `KAOLA_ACP_HEARTBEAT_HOST` JSON and receipt check; non-blocking dispatch with the real failure outcomes; "ending the turn *is* the wait, there is no wait-mode command"; the literal `kaola-host-notify/1` event shape with `event_cursor` and how to read the worker's real reply through that worker's own Skill; and the carrier's staging, dedupe, confirmation and at-least-once resume semantics. Every fact was checked against the real signatures in `kaola-acp.py::heartbeat_host_target` and `kaola-acp-holder.py::{op_prompt,_notify_heartbeat_host_now,_deliver_worker_events,_worker_event_turn_end,_heartbeat_payload}`; no tool or parameter is invented and no second heartbeat skeleton was created. `docs/zcode-host.md` gained the matching section. LIVE-ACCEPTED: a real ZCode Host (0.16.5, GLM Coding Plan) in a scratch workspace install performed the whole loop from the generated Skill alone, given only its own identity and the task — it bound `KAOLA_ACP_HEARTBEAT_HOST`, verified the `heartbeat_host` receipt, dispatched `--no-wait`, wrote `.kaola/heartbeat-prompt.json`, then said "Per the Skill, I now end this reply - ending the turn is the wait; no sleep, polling, or stop is needed" and ended the turn; the worker's `idle` event was staged mid-turn, delivered at the boundary, and woke it; it then said "the notification isn't the reply" and read the worker's real transcript, verifying `WORKER-DONE-65` before accepting and stopping the worker; the `terminated` event woke it once more and it closed out without inventing work. Both events were confirmed after their notification turn completed. Evidence: `kaola-workflow/issue-65/evidence/live-host-acceptance.md` and `evidence/live-host/`. That live run also caught a real defect in my reference — the installed per-platform wrapper takes NO platform argument, but the examples carried one — now fixed and pinned by a contract test.
## 5. Contract tests for steering semantics and Host event waiting
item: Add contract tests covering steer receipt semantics (injected, not-consumed at turn-end race, consecutive steers, cancel interaction, disconnect-unknown, session isolation, no request-id overwrite, unsupported platforms unconsumed), no regression in send/wait/cancel/stop, and the rendered ZCode Host event-wait wording plus non-blocking dispatch and Host-busy event stashing, delivery, dedupe, and resume redelivery.
status: done
dispatched: self (inline); new suites wired into both `scripts/validate.sh` lanes
result: DONE. `tests/contract/test-issue-65-steering.py` — 15 tests, all pass: manifest capability/entry pairing across all nine platforms, unsupported platform never consumes and starts no session, PTY honest-unsupported, injected preserves the running turn's request id and terminal state, consecutive steers get separate receipts sharing one turn id, idle never steered (nothing written), promptRequired/startedNewTurn/rejected/unrecognised/no-reply each mapped distinctly, cancel-then-steer not consumed, session isolation, and no send/wait/cancel/stop regression. `tests/contract/test-issue-65-host-contract.py` — 11 tests, all pass, pinning the generated Host wording, the reference's runnable elements, and that the documented mechanics still match the scripts (it also caught a real defect in my own change: the new reference was not a `.tmpl`, so `{{SKILL_NAME}}` shipped literally). Mock ACP agent gained a `--steering` mode set. `tests/contract/test-zcode-acp-contract.py` gained `test_concurrent_prompt_never_steals_the_active_request_id` (27 tests pass). Three pre-existing suites carried assertions pinning the old `-p <prompt>` argv shape and were updated to the new, stronger fact (the prompt never enters the argument list): `test-issue-50-claude-acp-bridge.py` 11/11, `test-issue-50-runner-integration.py` 7/7, `test-issue-41-orchestrator.py` 23/23 (its two pinned worker-contract sentences were restored verbatim rather than weakened).
## 6. Verification pass and candidate evidence binding
item: Run `render-skills.py --write`, `render-skills.py --check`, and `./scripts/validate.sh`, plus live capability/sentinel probes in isolated exact sessions this run owns, and bind actual results, versions, and the nine-platform matrix to a candidate SHA — recording FAIL and unverified items as such rather than green. Never probe through the supervising channel or touch pre-existing sessions.
status: done
dispatched: self (inline)
result: DONE. Candidate `71d6dd27100a58a52844634b9cafe63c6ed74aec` on `workflow/issue-65` (97 files, +4086/-322 from baseline `bb6d740`); worktree clean. `render-skills.py --write` and `--check` PASS with `budgets OK` and no budget raised; `vendor/claude-code-acp/kaola-dist.py --check` OK, 12 inputs, rebuild byte-identical; `./scripts/validate.sh` **exit 0** with all 26 contract suites green (the two new Issue-65 suites are wired into both lanes). LIVE, through the real Runner, with actual versions: codex-acp 1.11.0 and claude-code cli 2.1.272 both `steer_outcome: injected` with the original request id preserved and the original turn settling `end_turn` having absorbed the steer; real ZCode Host 0.16.5 completed the dispatch/end-turn/event-wake/read-result loop from the generated Skill alone. Isolation held: every probe owned only its own child in its own scratch cwd or an exactly named session this run created and stopped (`residual_pids []` each time); the pre-existing `vrpcadcore` holders, tmux `kaola-9d0873b0`, the neighbouring checkouts, and the supervising runtime were never touched, and the post-validate sweep left zero leaked holders. NOT VERIFIED and left open: per-platform PTY queue/steer semantics (scope decision recorded in the matrix - `steer` is an ACP operation and PTY answers `steer-unsupported-transport`); Devin/OpenCode/Droid mid-turn concurrent-prompt attribution is characterised but deliberately not exposed.

## Scope correction (owner, 2026-09-18, issuecomment-5724733375 + -5724757035)

Recorded without altering any result above; earlier results stand as what was
true when written, including the round-1 REQUEST_CHANGES and its findings.

1. **ACP only.** The nine-platform investigation, implementation and acceptance
   are limited to the ACP channel. PTY/TUI and separate non-ACP channels are out
   of scope: no investigation, no implementation, no live smoke, and their
   absence cannot block acceptance. The outer round-1 instruction to widen to
   PTY and other native channels is withdrawn. My `opencode serve` and
   `cursor-agent persist` exploration is stopped; the `opencode serve` probe I
   started was killed (pid 49193) and no other session was touched.
2. **Every platform gets a usable steering path.** Marking a platform
   `unsupported` and stopping is no longer acceptable. Native steering is
   preferred; a real pause/resume may be composed where it exists; otherwise the
   Runner offers an explicit composite: cancel the running turn, confirm it
   stopped, send the steering instruction to the SAME ACP session, and let the
   next turn continue with the context. The composite is
   interrupted-then-continued and must never be presented as native `injected`.
3. **The Agent chooses.** The composite is never a silent fallback on failure or
   timeout. The tool states that it interrupts execution and may leave partial
   side effects.
4. The native capability matrix stays honest and ACP-scoped; a separate column
   records each platform's actually usable steering path with version and live
   evidence.

## 7. Composite ACP steering for platforms with no native entry
item: Give all nine platforms a usable ACP steering path. Keep the native tool where the ACP surface really has one (claude-code, codex); everywhere else expose an explicitly Agent-selected composite that reuses the existing cancel and send operations on the same ACP session - cancel the running turn, confirm it ended, send the steering instruction exactly once, and let the next turn continue with the conversation's context. No second scheduler or lifecycle, no silent degradation, no blind retry. The original turn keeps its own terminal attribution; a cancelled turn's possible partial side effects are reported; an uncertain cancel or send stays `unknown` and sends nothing. Verify native and composite success paths, the turn-end race, cancel failure/timeout, and repeated invocation, then prove the actually-usable path live on each of the nine platforms.
status: done
dispatched: self (inline, single authorized implementer) on 2026-09-18 after the owner scope correction above; implementation in the issue-65 worktree on `workflow/issue-65` (holder `op_steer_interrupt`, `--steer-mode`, renderer/templates, `references/steering.md`); contract evidence in `tests/contract/test-issue-65-steering.py`; live per-platform receipts land in `kaola-workflow/issue-65/evidence/live-matrix/` and the rewritten `evidence/steering-capability-matrix.md`
result: DONE, with one platform unverified-live and documented. Candidate `cd98e2da1ebf26ed04a274dfe0d1b80b798f9c1a` on `workflow/issue-65` (109 files, +8235/-343 from baseline `bb6d740`). `kaola-acp-holder.py::op_steer_interrupt` implements the composite over the existing `op_cancel` + `op_prompt` - snapshot the turn, cancel, confirm it settled, then exactly one prompt on the SAME ACP session - and `op_steer` keeps the native path. `kaola-acp.py` gained `--steer-mode {native,interrupt}` and `--cancel-timeout`; with no mode a non-native platform refuses `steer-mode-required` (`available_steer_modes: ["interrupt"]`) having written nothing, so the Runner never interrupts on its own and never degrades silently. Receipts separate the claims: `interrupted_and_resent` / `resent_without_interrupt` with `steer_confirmation` `cancel-confirmed` / `no-turn-to-interrupt`, `cancelled_turn_request_id` + `cancelled_turn_stop_reason` beside a distinct `new_turn_request_id`, and `side_effects_possible` because interrupting is not undoing. An unconfirmed cancel returns `unknown` + `steer-cancel-unconfirmed` and sends NOTHING; nothing is ever retried. LIVE through the generated Skill's own script (`evidence/probes/live-steer-matrix.sh`, receipts `evidence/live-matrix/`), each run planting codeword `TOPAZ-65` in the first prompt and requiring it back after the steer: **codex** `injected`/agent-confirmed id 7 preserved; **claude-code** `written`/write-only id 7 preserved, steer obeyed inside the same turn; **cursor-cli** 6→7, **devin** 5→6, **droid** 5→6, **grok** 5→6, **kimi-cli**, **zcode** 4→5 all `interrupted_and_resent` with the codeword returned - eight of nine proven end to end, every session stopped with `residual_pids []`. **zcode** needed `--cancel-timeout 180`: 0.16.5 accepts the cancel at once but the turn settles only after ~70-100 s, and at 30 s the composite correctly sent nothing and returned `unknown` - the latency is now recorded in its manifest. **opencode** is BLOCKED and NOT proven live: `opencode acp` fails `session/new` with `-32603 {service: "directory"}` for every directory, reproduced with no Runner in the path, while `opencode run` on the same binary works - full reproduction and the recommended fix (reinstall/upgrade the CLI, a global change not made unilaterally) in `evidence/opencode-acp-blocker.md`; the composite code path there is identical to the six proven ones. Matrix rewritten ACP-scoped with a usable-path column: `evidence/steering-capability-matrix.md`; the Devin/OpenCode/Droid attribution claim was softened - close settlement times are consistent with lost attribution but do not prove it. Docs updated (`docs/api.md`, `README.md`, `CHANGELOG.md`) and a new on-demand worker reference `references/steering.md` carries both modes. Tests: `test-issue-65-steering.py` 23/23 (15 native + 8 composite), `test-issue-65-host-contract.py` 13/13, `kaola-steer.test.ts` 10/10, `./scripts/validate.sh` **exit 0**, `render-skills.py --check` PASS with budgets OK, `kaola-dist.py --check` byte-identical. `test-generated-skills.py`'s worker-reference allowlist was extended with the new communication reference `steering.md` (the assertion's intent, excluding orchestration references, is unchanged). LIVE HOST RE-ACCEPTED on the corrected Skill (`evidence/live-host2-acceptance.md`): a real ZCode Host 0.16.5 bound `KAOLA_ACP_HEARTBEAT_HOST`, dispatched `--no-wait`, recorded `dispatch_event_cursor: 6` as its anchor, ended its turn ("that ending **is** the wait"), was woken by the worker `idle` event, said "the event's cursor 35 marks the turn's *end*, so the reply sits below it", read `capture --since 6` and verified all three lines `OPAL-65-ALPHA/BRAVO/CHARLIE` - the round-2 cursor fix proven by a live Host, not only by a test - then stopped the worker and closed out; both events staged, delivered at turn boundaries and confirmed.

## Scope continuation (owner, 2026-09-18, after the OpenCode install push)

The owner authorized the outer to install OpenCode themselves and told this run
not to stop at the OpenCode blocker. Outer facts, recorded as given: a standalone
1.18.17 binary at `/opt/homebrew/bin/opencode` was shadowing the Homebrew
install; it was moved aside recoverably to
`/opt/homebrew/var/opencode-backup-MB6kDM/opencode-1.18.17`, `brew link`
succeeded, `opencode --version` is now 1.18.31, and the outer's own Runner start
of an exact check session succeeded and was stopped. Configuration, auth,
database and user sessions were untouched. The owner also required a fix for the
false success signal seen earlier: a failed `start` followed by `send`/`steer`
reporting `steer_consumed: true`.

## 8. OpenCode live verification and the null-session false success
item: Re-run the OpenCode ACP composite steering live through the final candidate's generated Skill, confirming the same session kept its context, the old turn ended and the new instruction ran; record the real version and receipts and update the blocker record as resolved without erasing its history. Separately, fix the defect that false-signalled success: with no valid `acp_session_id`, `send` and `steer` must state plainly that nothing was sent, never `in_progress` or `steer_consumed: true`, and the refusal must be covered by tests.
status: done
dispatched: self (inline, single authorized implementer); live receipts to kaola-workflow/issue-65/evidence/live-matrix/, correction to evidence/opencode-acp-blocker.md and evidence/steering-capability-matrix.md, code+tests in the issue-65 worktree
result: DONE. Candidate `b62f957f199241dd9978616fb5905ee76943bcf4` on `workflow/issue-65` (109 files, +8644/-343 from baseline `bb6d740`), superseding cd98e2d. **OpenCode now PASSES live**, so all nine platforms are proven: OpenCode 1.18.31, `start` → `state: ready`, `acp_session_id: ses_f4d1faf4dffeqyXDck0FxZTSBa`; `steer --steer-mode interrupt` → `interrupted_and_resent`, `steer_confirmation: cancel-confirmed`, cancelled turn 3 → new turn 4, `side_effects_possible: true`; the steered turn ended `end_turn` with exactly `TOPAZ-65-OK` — the codeword planted in the first prompt, so the same ACP session kept its context — and `stop` was clean with `residual_pids []`. **The blocker's earlier cause was wrong and is corrected, not erased**: it was never the OpenCode installation. On 1.18.31 the failure still reproduced for me through the Runner at the canonical root, the Runner at the worktree, the **pre-change baseline Runner from the main checkout** (so the Runner was never implicated), and a raw JSON-RPC probe four times running. The difference is the environment: this shell exports `HTTP_PROXY`/`HTTPS_PROXY`, OpenCode's session bootstrap makes a network call, `curl https://models.dev/api.json` timed out at 12 s through that proxy, and OpenCode reports the failure as `-32603 {service: "directory"}`; with the proxy unset the same binary in the same cwd answered `session/new` with a real `sessionId`. Both 1.18.17 and 1.18.31 fail with the proxy set and succeed without it, so the upgrade was not what fixed it — the earlier "reinstall the CLI" conclusion was a misattribution and the dismissed `Failed to fetch models.dev cause=TimeoutError` log line was the missed clue. **Runner defect fixed**: `kaola-acp-holder.py::_no_acp_session()` now refuses `op_prompt`, `op_steer` and `op_steer_interrupt` before writing anything when `acp_session_id` is null — `error.code no-acp-session`, `outcome: no_session`, `mutation_status: not_started`, `mutation_performed: false`, and on the steer paths `steer_outcome: not_consumed`, `steer_consumed: false`, `steer_confirmation: none`, no `interrupted`, no `new_turn_request_id`. Previously the prompt frame went out with `"sessionId": null`, so `send` read `in_progress` and the composite read `steer_consumed: true` for text no session ever received. Covered by three new contract tests (`test_send_without_an_acp_session_writes_nothing`, `test_composite_steer_without_an_acp_session_is_not_consumed`, `test_native_steer_without_an_acp_session_is_not_consumed`) driven by a new mock scenario `session_new_fails` that keeps the process alive while `session/new` returns OpenCode's exact error shape; all three were proven RED against the unguarded holder and are green with it. Tests: `test-issue-65-steering.py` **26/26**, `./scripts/validate.sh` **exit 0**, `render-skills.py --check` PASS with budgets OK, `kaola-dist.py --check` byte-identical. Docs updated (`docs/api.md`, `CHANGELOG.md`). Isolation held: only the exact sessions this run created (`opencode-kaola-i65m`, `opencode-kaola-i65root`, `opencode-kaola-i65base`, `opencode-kaola-i65probe`) were started and stopped; the `vrpcadcore` holders and every other session were untouched, and the owner's `opencode-kaola-i65-installcheck` session was already stopped by the outer.

## 9. Turn-attribution race in the composite steer (outer review of b62f957)
item: The outer's substantive review of b62f957 found a remaining blocker: `op_steer_interrupt` reads the running turn's request id under `self.lock`, releases the lock, and then calls an `op_cancel` that validates no turn identity; `serve_connection` is multi-threaded and a Host `worker_event` starts prompts, so after the old turn A ends naturally a new turn B can enter the gap, and the composite actually cancels B while labelling the cancel receipt A. `op_cancel`'s wait on the current `self.turn` can likewise span into a new turn, and reading `new_request_id` from `self.turn` after `op_prompt` returns can mis-attribute the same way. Fix locally with the existing locks and explicit request-id ownership - no queue, no state machine, no retry layer: confirm the old turn's identity before cancelling; scope the wait and the receipt to the target turn; on a turn change neither cancel nor impersonate it and do not blindly resend; take the new send's request id from its own atomic admission receipt. Add a deterministic barrier/mock race regression proving the old implementation RED and the new one neither cancels the new turn nor misreports the cancel/new-turn ids. Separately correct `steering.md`'s blanket claim that a turn ending in the same instant returns `not_consumed`, which does not match the real unknown/started_new_turn branches.
status: done
dispatched: self (inline, single authorized implementer); code in scripts/kaola-acp-holder.py, regression in tests/contract/test-issue-65-steering.py, wording in templates/references/steering.md.tmpl
result: DONE. Candidate `36e6f516dcd3c213b4f7d5cb5245507c3c1983ba` on `workflow/issue-65` (109 files, +9924/-353 from baseline `bb6d740`), superseding b62f957. The finding was real and is fixed with the existing locks plus explicit request-id ownership; no queue, state machine, or retry layer was introduced. (1) `op_cancel` now takes `expected_request_id`: under `self.lock` it verifies the running turn IS that turn before sending `session/cancel`, and its wait returns `turn-changed` (code `cancel-turn-changed`, `mutation_performed: false`) the moment the id changes underneath, so a receipt is never returned for a turn other than the one it cancelled. (2) `op_steer_interrupt` passes the id it snapshotted; on `turn-changed` nothing is cancelled and nothing is sent - `steer_outcome: unknown`, `steer_consumed: null`, `steer_confirmation: none`, `outcome: steer_turn_changed`, error `steer-turn-changed` telling the Agent to observe and decide again rather than resend. A turn admitted between the confirmed cancel and the send is caught the same way: `op_prompt`'s `prompt-in-progress` refusal now reports `mutation_performed: false` with `active_turn_request_id`, and the composite maps it to `not_consumed` with `steer-turn-changed`, nothing written. (3) `op_prompt` reports `turn_request_id` from its own admission under the lock, and the composite takes `new_turn_request_id` from that receipt instead of re-reading `self.turn`. The native `op_steer` needed no change: its active-turn check and its write already happen inside one `self.lock` hold. REGRESSION, deterministic: a new `test_barrier()` helper (inert unless `KAOLA_ACP_TEST_BARRIER` names a directory) pauses the composite exactly in the snapshot-to-cancel window; `test_composite_steer_never_cancels_a_turn_it_did_not_target` uses it to end turn A and admit turn B before releasing, then asserts `steer-turn-changed`, `unknown`, no `new_turn_request_id`, no interrupt, and that B is still the running turn (a stale cancel bound to A reports `turn-changed` naming B). Against the OLD implementation that same receipt reads `steer_outcome: interrupted_and_resent`, `steer_confirmation: cancel-confirmed`, `interrupted: true`, `cancelled_turn_request_id: 5` while turn 6 is what actually died - RED captured verbatim. `test_cancel_bound_to_a_finished_turn_reports_turn_changed` drives the bound cancel directly over the holder socket. `references/steering.md` no longer claims a same-instant turn end always returns `not_consumed`; it now names the real branches (`not_consumed` when the holder refused before writing, `started_new_turn` when the agent says it opened one, `unknown` when nothing or something unrecognised comes back, or the turn settles mid-write) and documents the turn-changed refusal. Tests re-run: `test-issue-65-steering.py` **28/28**, `./scripts/validate.sh` **exit 0**, `render-skills.py --check` PASS with budgets OK, `kaola-dist.py --check` byte-identical. All nine platforms' existing live evidence is preserved untouched, and the changed composite/native paths were re-verified live after the fix: grok `interrupted_and_resent` 5 -> 6 with `TOPAZ-65-OK`, codex native `injected`/agent-confirmed id 7 preserved with `TOPAZ-65-OK`, both stopped with `residual_pids []`.

### Mission 9 review revision (outer re-review of 36e6f51, 2026-09-18)

Recorded against the existing Mission 9; no new mission was opened and the nine
results above stand as written. The outer accepted the snapshot-to-cancel RED
proof and the fix for it, but found the claim "a receipt never describes a
different turn" still false in two places, plus one dishonest branch:
`op_cancel` returned `self.turn_receipt()` after leaving `turn_cond`;
`op_steer_interrupt` re-read `still_active`/`stop_reason`/`mutation_after` from
`self.turn` after the cancel returned; and the wait-branch `turn-changed` carried
`cancel_sent: true` while the composite still said "nothing was cancelled" with
`side_effects_possible: false`. It also required the production
`KAOLA_ACP_TEST_BARRIER` polling hook out of the shipped Skills, with the
interleavings arranged in-process against the real `Holder` instead.

Revised candidate `fd37a4fbb65ff0f6e477df0ee75347b87d3afff1` (110 files,
+10520/-473 from `bb6d740`), superseding 36e6f51. Because `self.turn` is replaced
on admission and never reset in place, the turn OBJECT is now the handle:
`cancel_turn(target, timeout)` binds the admission check, the outbound
`session/cancel`, the wait (on `target["active"]`) and the receipt to that one
turn, builds the receipt while holding the lock, and returns
`(receipt, cancel_sent, snapshot)`; `turn_receipt(turn=...)` describes a given
turn. `op_steer_interrupt` reports only that snapshot and never re-reads
`self.turn`; it separates "replaced before we cancelled" (`cancel_sent: false`,
nothing cancelled) from "the target stopped but another turn owns the session"
and from "the cancel went out and its outcome is unconfirmed"
(`cancel_sent: true`), and `side_effects_possible` is derived from the target's
own mutation status rather than hardcoded. `on_prompt_response` now ignores an
answer whose request id is not the running turn's, so a late reply cannot settle
somebody else's turn. No queue, ledger, state machine or retry layer was added.

Evidence: `tests/contract/test-issue-65-steer-race.py` imports the real `Holder`
with a stubbed agent connection and arranges each interleaving directly - A ends
and B takes over after the cancel was sent, before it was sent, and after our own
send - in 0.012 s with no sleeps and no production hook. 5 of its 6 cases fail
against 36e6f51 ("B must still be running", "None is not True" for `cancel_sent`,
"None != 'cancelled'" for the cancelled turn's stop reason, and `cancel_turn`
missing entirely); all 6 pass now. The `KAOLA_ACP_TEST_BARRIER` hook and its
subprocess test were deleted and confirmed absent from all nine generated
Skills. `templates/references/steering.md.tmpl` and `docs/api.md` now state the
`cancel_sent` distinction instead of a blanket "nothing was cancelled".
Re-run: `test-issue-65-steer-race.py` 6/6, `test-issue-65-steering.py` 27/27,
`./scripts/validate.sh` exit 0 (the new suite is wired into both lanes),
`render-skills.py --check` PASS with budgets OK, `kaola-dist.py --check`
byte-identical. All nine platforms' live evidence is preserved untouched, and
grok's composite was re-run live after this change: `interrupted_and_resent`
5 -> 6, `TOPAZ-65-OK`, `residual_pids []`.

### Mission 9 review revision 2 (outer re-review of fd37a4f, 2026-09-18)

Still one revision of Mission 9, not a new mission. The outer accepted the
turn-object snapshot implementation and named one remaining edge plus two
corrections to how I had described my own evidence.

Candidate `4b8168c3912f538a41d568da53618d65bc1e61be` (branch `workflow/issue-65`),
superseding fd37a4f.

1. **The edge.** When the targeted turn finished naturally between the
   composite's snapshot and the cancel - still the current turn, so not a
   turn-change - `cancel_turn` correctly sent nothing and returned
   `no-active-turn` with `cancel_sent: false`, but `op_steer_interrupt` fell
   through to `interrupted: true` / `cancel-confirmed` and reported
   `interrupted_and_resent`. It now reports `resent_without_interrupt`,
   `steer_confirmation: no-turn-to-interrupt`, `interrupted: false`,
   `cancel_sent: false` and no partial-side-effect warning, while the targeted
   turn's real request id and stop reason stay on the receipt.
   `test_composite_does_not_claim_an_interruption_it_never_made` drives exactly
   that window and is the ONE genuine RED against fd37a4f
   (`'interrupted_and_resent' != 'resent_without_interrupt'`).

2. **Correction to revision 1's evidence claim.** I wrote that 5 of 6 race cases
   failed against 36e6f51. Re-measured honestly: 3 were real behavioural
   failures ("B must still be running"; `cancel_sent` absent; the cancelled
   turn's stop reason read from the wrong turn) and 3 errored with
   `AttributeError: 'Holder' object has no attribute 'cancel_turn'` - a test
   harness incompatibility with the older code, NOT evidence of its behaviour.
   The earlier sentence overstated the proof; this record is the correction and
   revision 1 is left as written.

3. **Correction to a test's own claim.** `test_composite_new_turn_id_is_its_own_send`
   was described as covering a takeover after our send but only exercised the
   plain success path. It now wraps the real `op_prompt`: the admission runs for
   real, then the new turn is settled and B is admitted before the original
   receipt is returned, so `self.turn` is B by the time the composite builds its
   receipt and the reported id is still our own send's. This case PASSES against
   fd37a4f as well - it is added coverage, not a regression proof.

Re-run on 4b8168c: `test-issue-65-steer-race.py` 7/7 (0.022 s, in-process, no
production hook), `test-issue-65-steering.py` 27/27, `./scripts/validate.sh`
exit 0, `render-skills.py --check` PASS with budgets OK, `kaola-dist.py --check`
byte-identical, vendored `kaola-steer.test.ts` 10/10. The nine platforms' live
evidence is preserved untouched.

### Issue #66 integration: not started, blocked on the other run's sink

Checked on 2026-09-18 at the end of this revision: `main` is still
`bb6d740` and does NOT contain `2da5f92`; that commit exists only as an ancestor
of `workflow/issue-66` (tip `3e84948`), whose worktree is still live. Per the
owner's instruction I did not touch that run's main, did not merge, and am not
polling. The approved integration - keep #66's two entry points, startup
acceptance and single heartbeat read alongside #65's steering and event cursor;
separate Host startup from dispatch references by pointing rather than copying;
no budget raised; generated files only through the renderer - is ready to run the
moment the outer dispatches it.

### Issue #66 integration (owner-approved, 2026-09-18)

`main` reached `039c278` with Issue #66 closed and archived, and the outer
ACCEPTed the independent #65 candidate `4b8168c`. Integration merge
`bc720e38722e67a860149f8a931287b9f000ee5a` on `workflow/issue-65`:
`git merge main` - no rebase, no history rewritten, both parents intact.

Three conflicts, all resolved keeping both runs' function:

1. `templates/orchestrator/SKILL.md.tmpl` (Dispatch notes): wording/wrap only -
   took main's sentence verbatim.
2. `CHANGELOG.md`: kept both, #66's two entries above #65's.
3. `skills/kaola-project-runner/SKILL.md`: generated - resolved only by
   `render-skills.py --write`, never edited by hand.

Integration edits beyond the mechanical merge, per the approved plan:

- **One dispatch cursor.** The main Skill's Host paragraph still told a Host to
  read the reply "with the event's session, repo, and `event_cursor`" - the
  round-2 defect. It now keeps the dispatch receipt's `dispatch_event_cursor` as
  the anchor and says the event's own cursor sits after the reply. #66's
  `host-startup.md` hedge ("where a Runner build does not return one, take the
  cursor from an `observe` before the dispatch") is gone: this release always
  returns it.
- **Layered, not duplicated.** `host-startup.md` (#66) keeps the entry points,
  startup order, startup receipt, record separation and keep-versus-stop, and
  its per-beat paragraph is replaced by a pointer to
  `zcode-host-dispatch.md` (#65), which owns the beat, the event shape and the
  carrier. That reference in turn points back for startup, and its duplicated
  "outer Agent starts the Host" section became a pointer. Nothing was copied in
  either direction.
- **No budget raised.** `templates/budgets.json` is untouched. Both files were
  over after the merge (SKILL.md 17791 B, zcode-host-dispatch.md 8380 B) and
  were brought back by removing duplicated explanation only: the main Skill is
  now **17262 B** of 17408 (more headroom than main's own 17281), and the
  reference fits. Two pinned clauses I had compressed too far were restored
  verbatim after `test-issue-49-grok-bot-host.py` caught them ("not a tenth
  platform"; "never reaches the other's files, CLIs, tmux, or sessions"), and
  the main Skill's steer sentence was corrected - `steer` is no longer listed
  only on some platforms, so "Where a platform Skill lists `steer`" became
  "Steering a running turn is an Agent choice, never a Runner policy".

Integrated verification: `./scripts/validate.sh` **exit 0** (all suites,
including #66's `test-zcode-heartbeat-contract.py` and #49's 42-test bridge
invariance), `render-skills.py --check` PASS with budgets OK,
`kaola-dist.py --check` byte-identical, vendored `kaola-steer.test.ts` 10/10,
`test-issue-65-steering.py` 27/27, `test-issue-65-steer-race.py` 7/7,
`test-issue-65-host-contract.py` 13/13, `test-issue-41-orchestrator.py` 23/23.
Working tree clean. Nothing in `kaola-workflow/archive/issue-66/` was modified.

