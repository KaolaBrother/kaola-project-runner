# Code review — test custody (issue #27)

Frozen candidate: dirty worktree `/Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/bundle-27`  
Spec: `docs/acp-watch/follow.md` (behavior/acceptance unchanged; only status line flipped to 已实现)  
Focus: whether production deleted, weakened, or reinterpreted `tests/contract/test-acp-follow-contract.py` after RED.

## Verdict

**PASS** — 0 custody defects.

The follow contract file is still the tdd-guide RED surface. Production did not edit it. Watch/ACP contract tests were not touched. `follow_flood` / `inbound_frame` still feed the assertions that distinguish NDJSON follow from the one-shot request/response holder.

## How custody was established

- `git status`: `tests/contract/test-acp-follow-contract.py` is **untracked**. `git diff` / `git diff --cached` on that path are empty. Tracked test diffs are only `tests/contract/mock-acp-agent.py` (additions) and `scripts/validate.sh` (one registration line).
- `git diff tests/contract/test-acp-watch-contract.py tests/contract/test-acp-contract.py tests/contract/fixtures/kaola-acp-view-1.sample.json` is empty.
- Mtimes: follow test `2026-09-13 11:22:07`, mock `11:20:12`, RED proof `11:25:37`, CLI/holder `11:46:40` / `11:52:59`. Implementer production files are later than the test; the test is earlier than the RED proof write.
- RED proof (`kaola-workflow/bundle-27/.cache/tdd-red-proof.md`) names the same 11 methods, `FAILED (failures=11)`, CLI `invalid choice: 'follow'`, holder `unknown-op`. Current file still has those 11 `def test_*` names.

## Original RED surface still present

These assertions still fail a request/response holder and still pass only a follow stream:

| Test | What still distinguishes follow |
| --- | --- |
| `test_follow_usage_missing_session_is_exit_2` (463–475) | `follow` must be a real command; combined stdout/stderr must not contain `invalid choice: 'follow'`; missing `--session` is exit 2. |
| `test_follow_prints_snapshot_then_increasing_cursor_deltas` (477–536) | First follow event `kind=snapshot`, schema `kaola-acp-view/1`, then `delta` with non-decreasing then strictly increasing cursors. |
| `test_two_followers_see_the_same_tool_call` (538–564) | Two CLI followers both see `call_7`; payload shape vs `kaola-acp-view-1.sample.json`. |
| `test_follow_fd_prompt_permit_is_error_without_agent_stdin` (566–606) | Raw Unix `{"op":"follow"}` first line is `kind=snapshot` (not `unknown-op`); subsequent `prompt`/`permit`/`cancel`/`stop` on that FD are `kind=error`; `inbound_trace()` equal before/after. |
| `test_third_socket_permit_still_works_with_followers` (608–651) | Followers attached; a **different** CLI `permit` still produces mock `outbound_response`. |
| `test_slow_follower_dropped_without_pausing_agent_stdio` (653–697) | `follow_flood` must finish (`follow_flood_emitted`) while the slow collector is paused; slow path gets `follow-dropped` and disconnects; fast path does not; `view` still has `call_flood`. |
| `test_killing_follow_cli_leaves_holder_and_agent` (699–719) | SIGKILL follow CLI; holder pid and agent pid stay alive; `list`/`view` still work. |
| `test_process_exited_emits_follow_eof` (721–735) | Kill agent → follow stdout `kind=eof`; holder still alive. |
| `test_holder_lost_emits_follow_error_line` (737–747) | Kill holder → `kind=error` with code `holder-lost`. |
| `test_format_text_joins_titles_and_is_not_ndjson_only` (749–788) | `--format text` emits message/tool titles, not NDJSON-only, no OSC/DCS TUI. |
| `test_view_one_object_and_l0_keys_stay_while_follow_attached` (790–805) | `view` remains one object **without** `kind` while follow is attached; L0 send receipt does not grow human keys. |

`validate.sh` only gained the expected mechanical line after the watch contract.

## Mock still supports the assertions

`tests/contract/mock-acp-agent.py` diff is additive only:

- `follow_flood` (414–433, listed in `on_prompt` scenarios 452–455): 280 `agent_message_chunk` updates then `toolCallId=call_flood`, then `follow_flood_emitted`. That is what `test_slow_follower_dropped_without_pausing_agent_stdio` waits on (669–675, 676).
- `inbound_frame` logged at `dispatch` (497–502). `inbound_trace()` (388–403) still includes `inbound_frame`, `prompt`, `outbound_response`, `unparseable_inbound`, `session_cancel`. The follow-FD write test compares that trace (590–603).

No mock path was deleted or narrowed so that extra agent-stdin frames or a short flood would go unseen.

## Findings

None. Production did not delete, weaken, or reinterpret the follow contract assertions to go green.

## Observations (specified behavior left unpinned by the original RED file)

These are gaps in the tdd-guide file, not post-RED meaning changes. They would still have been true on the RED worktree.

1. **Heartbeat interval (and presence) unpinned.** `assert_heartbeat_shape` (442–456) only inspects events that already have `kind=heartbeat`. If the CLI never emits a heartbeat, the helper is a no-op. `test_follow_prints_snapshot_then_increasing_cursor_deltas` calls it (504) but does not `wait_kind("heartbeat")` and does not pin an interval. Spec requires heartbeats to carry full `pending_permissions` and `mutation_status`; payload keys are checked **if** a heartbeat appears; cadence is not.

2. **Snapshot nesting is flexible.** `follow_view_payload` (105–114) accepts top-level `kaola-acp-view/1` **or** nesting under `payload` / `view` / `snapshot` / `delta` / `data`. Spec says each NDJSON line is `{kind:snapshot|delta|heartbeat|eof|error, ...}` with snapshot/delta payload the same schema as `view`. Tests do not require `kind` and view fields to sit at one fixed nesting.

3. **`--since` may still emit snapshot; the late follower need not emit anything.** After `--since` (521–536) the test only requires the process still running and that *if* a snapshot/delta appears, its cursor is `>= since`. It does not forbid a snapshot, does not require a delta, and `wait_for(... events or poll is None ...)` is true while the process lives. Spec: optional snapshot, then cursor deltas; `--since CURSOR` is named but not fully pinned.

4. **Follow CLI exit code after `eof` unpinned.** `test_process_exited_emits_follow_eof` waits for `kind=eof` and holder liveness; it never asserts `collector.proc.poll()` / returncode. Spec: `process_exited` then eof — the `process_exited` kind itself is also unpinned (only eof after SIGKILL agent).

Related original looseness (same class, not a meaning change): `FOLLOW_QUEUE_CAP = 256` is only asserted `> 0` (697), a tautology; the 256 cap is implied only by sending 280 flood lines and expecting `follow-dropped`. Write-op error **code** on the follow FD is unpinned (only `kind=error`).

## Conclusion

PASS. Eleven RED tests remain, still distinguish follow NDJSON from request/response, and still have mock `follow_flood` / `inbound_frame` behind them. Named gaps are untested specified details in the original test file, not production reinterpretation.
