# Issue #27 TDD RED proof

Worktree: `/Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/bundle-27`  
HEAD: current main without `follow` (request/response holder only).  
Recorded: 2026-09-13.

## Commands

```bash
python3 tests/contract/test-acp-follow-contract.py -v
```

- exit code: **1**
- result: `FAILED (failures=11)` in 76.601s

```bash
python3 tests/contract/test-acp-watch-contract.py -q
```

- exit code: **0**
- result: `Ran 10 tests ... OK` (issue #26 suite still green)

`scripts/validate.sh` now also runs `tests/contract/test-acp-follow-contract.py` after the watch contract.

## Failing tests (all 11)

1. `test_follow_usage_missing_session_is_exit_2` — argparse `invalid choice: 'follow'`; command is not registered, so missing `--session` cannot be a follow usage error.
2. `test_follow_prints_snapshot_then_increasing_cursor_deltas` — CLI `follow` is not a command; stdout empty, no `kind=snapshot` then increasing-cursor deltas.
3. `test_two_followers_see_the_same_tool_call` — neither CLI follower attaches; no shared `call_7` stream.
4. `test_follow_fd_prompt_permit_is_error_without_agent_stdin` — holder `op follow` is `unknown-op` (one JSON reply), not a snapshot stream, so the FD is still a request/response writer.
5. `test_third_socket_permit_still_works_with_followers` — followers never emit snapshot, so the attached-follow + third-socket permit path is unproven/unimplemented.
6. `test_slow_follower_dropped_without_pausing_agent_stdio` — no follow stream, so the 256-line `follow-dropped` path never appears.
7. `test_killing_follow_cli_leaves_holder_and_agent` — follow CLI exits 2 at argparse before a live follow process exists to kill.
8. `test_process_exited_emits_follow_eof` — no follow snapshot, so agent death cannot emit `kind=eof`.
9. `test_holder_lost_emits_follow_error_line` — no follow snapshot, so holder death cannot emit `kind=error` / `holder-lost`.
10. `test_format_text_joins_titles_and_is_not_ndjson_only` — `--format text` never runs; stdout has no message/tool titles.
11. `test_view_one_object_and_l0_keys_stay_while_follow_attached` — cannot attach follow, so the “view stays one object while following” gate never starts.

## Representative stderr (CLI)

```
kaola-acp.py: error: argument command: invalid choice: 'follow'
(choose from preflight, start, send, wait, observe, capture, permit,
key, answer, cancel, stop, status, view)
```

## Representative holder reply (raw Unix `{"op":"follow"}`)

```
{'error': {'code': 'unknown-op', 'message': 'unsupported op follow'}}
```

That is today's one-shot request/response holder, not NDJSON `{kind:snapshot|delta|heartbeat|eof|error}`.

## Mock scenario added

`follow_flood` in `tests/contract/mock-acp-agent.py`: 280 `agent_message_chunk` updates then `toolCallId=call_flood`, logged as `follow_flood_emitted`. Also logs every ACP `inbound_frame` so follow-FD writes can be shown not to add agent-stdin frames.

`watch_projection` / `call_7` reused for dual-follower + third-socket permit.
