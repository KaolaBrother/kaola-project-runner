# Trust-boundary review — issue #27 follow

Frozen candidate: uncommitted dirty worktree
`/Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/bundle-27`

Focus: refute “the follow FD is a read-only projection.” Admit a finding only with a shown defect.

Sources read: `scripts/kaola-acp-holder.py` (`serve_connection` follow branch, `Follower._send`/`offer_*`, `handle_request`, `AgentConnection.send_message` call sites), `scripts/kaola-acp.py` `command_follow`, `docs/acp-watch/follow.md`, `tests/contract/test-acp-follow-contract.py`.

Checks run (worktree, unmodified):
`python3 tests/contract/test-acp-follow-contract.py -v` for
`test_follow_fd_prompt_permit_is_error_without_agent_stdin`,
`test_slow_follower_dropped_without_pausing_agent_stdio`,
`test_killing_follow_cli_leaves_holder_and_agent`,
`test_third_socket_permit_still_works_with_followers`,
`test_view_one_object_and_l0_keys_stay_while_follow_attached`
→ 5 OK, 3.759s.

## Attempted refutations (not findings)

Each claim below was the strongest write-through / second-writer / bind / stall attack that still fits the frozen code. None produced a demonstrated defect.

### 1. Prompt/permit/cancel/stop on the follow FD call `op_prompt` / `op_permit` / agent stdin

**Concrete input:** after `{"op":"follow","params":{}}\n`, client sends
`{"op":"prompt","params":{"text":"sneak"}}\n`,
`{"op":"permit","params":{"option":"allow_once"}}\n`,
`{"op":"cancel"}\n`,
`{"op":"stop"}\n`
(same socket; also pipelined in one `recv` buffer).

**Code:** `serve_connection` 1656–1673. Once `follower is not None`, every subsequent decoded line takes the `FOLLOW_WRITE_OPS` / else branch, both of which `offer_error("follow-readonly", …)` and `continue`. They never call `handle_request`. `handle_request` is the only path to `op_prompt` (1616–1617), `op_permit` (1620–1621), `op_cancel` (1622–1623), `op_stop` (1630–1631).

`FOLLOW_WRITE_OPS` (361) is only the error-text denylist. `set_config_option` (the other holder op that writes agent stdin via `send_request` at 1597) is also rejected after follow, as `op not in FOLLOW_WRITE_OPS` still `continue`s without `handle_request`.

Pipelined follow+prompt in one packet is the same `while b"\n" in buffer` loop on one thread: first line `start_follow`, second line sees `follower is not None`.

**Established:** `AgentConnection.send_message` (279–287) is the only runtime writer of `proc.stdin` (plus `op_stop` closing stdin at 1548–1550, and the probe helper which is a different process). Call sites: `send_request` 295; unsupported agent-request reply 998; `_settle_pending_permission_locked` 1314; `op_cancel` 1357; `op_stop` 1534. None are reachable from `Follower` or from the post-follow branch.

Contract test `test_follow_fd_prompt_permit_is_error_without_agent_stdin` compared mock `inbound_frame` traces before vs after those writes: equal; holder still alive.

### 2. Extra JSON after `op=follow` turns follow into a second agent-stdin writer

**Concrete input:** `{"op":"follow"}\n{"jsonrpc":"2.0","method":"session/prompt","params":{…}}\n` (no `op`), or invalid JSON, or a second `{"op":"follow"}`.

**Code:** non-dict / missing `op` still hits `if follower is not None` (1657) and the else `follow-readonly` path. Invalid JSON after follow is `follower.offer_error("bad-request")` (1651–1652), not `handle_request`. A second follow is `op == "follow"` which is not in `FOLLOW_WRITE_OPS`, so also `follow-readonly`, not a second `start_follow` that later upgrades to writes.

`command_follow` (287–352) sends exactly one follow line, then only `recv`s. It never forwards stdin or extra JSON onto the socket.

### 3. Exclusive stdio is not holder-owned; follow is more than a Unix-socket consumer

Follow state is a per-connection `Follower` queue + dedicated `_write_loop` thread. `_send` (709–735) and `_emit_drop` (689–707) write only `self.connection` (the accepted AF_UNIX fd). `start_follow` (1474–1491) registers that object under `followers_lock` and offers a view snapshot. Agent PTY/stdio remains `AgentConnection` (`Popen` stdin/stdout/stderr pipes, reader thread `_read_loop`).

A third AF_UNIX short connection can still `permit` (`test_third_socket_permit_still_works_with_followers` OK). That is holder-mediated stdin, not the follow FD.

### 4. L0 `send --wait` keys changed

`kaola-acp.py` still default `--wait` True (698–699). `send` still `op_or_holder_lost(..., "prompt", {text, wait, timeout, max_final_chars})` (755–766). Follow is a separate `command == "follow"` return (747–750) and does not wrap `send`.

`test_view_one_object_and_l0_keys_stay_while_follow_attached` sent with default wait while a follower was attached: `schema_version` 3, `thinking_chars` int, no `timeline`/`thinking_text`/`plan`/`messages`/`tools`.

### 5. TCP/HTTP bind, or Unix socket not 0600 + peer uid

Listener is `socket.AF_UNIX` (1719), `bind` of `holder.sock` (1724), `os.chmod(..., 0o600)` (1725), `listen(16)` (1726). No `AF_INET` / HTTP server in `kaola-acp-holder.py` / `kaola-acp.py`. Accept path: `verify_peer` then `serve_connection` (1754–1758). Darwin `getpeereid` uid == `getuid()` (1691–1696); else `SO_PEERCRED` (1698–1703). Follow uses this same accept path.

### 6. Slow follower drop pauses or kills agent stdio

Drop path: `queue.put_nowait` Full or `blocked and produced > 256` → `_drop_locked` (647–657) queues `follow-dropped` on that follower only. `_send` backpressure is `select` on the follow socket with SO_SNDBUF 4096; it does not write or flush agent stdin. Fanout (`fanout_follow_delta` 1448–1454) is `put_nowait` under `offer_lock`, invoked from the agent reader, but does not wait on the slow socket.

`test_slow_follower_dropped_without_pausing_agent_stdio`: mock `follow_flood` (280 chunks + `call_flood`) finished (`follow_flood_emitted`), fast follower saw the tool, slow follower got `follow-dropped` and disconnected, other follower was not dropped. View still showed `call_flood`.

### 7. Killing the follow CLI stops holder/agent

`command_follow` close/OSError paths do not send `stop`. Holder `recv` empty → `serve_connection` returns → `follower.close()` (1682–1684) unregisters; no `op_stop`, no `os._exit` (that remains stop’s `_exit_after_reply` on a control connection, 1677–1679).

`test_killing_follow_cli_leaves_holder_and_agent`: SIGKILL follow CLI, holder pid alive, list row present, view OK, agent pid alive.

## Findings

None. No shown path where a follow FD writes ACP JSON-RPC to agent stdin, becomes a second stdio client, binds TCP/HTTP, or killing/slow-dropping a follower stops holder/agent stdio.

## Observations (not defects)

- Enforcement is user-space: the holder keeps `recv` on the follow fd (does not `shutdown(SHUT_RD)`). That matches follow.md (“after the first follow op, read-only; prompt/permit/cancel/stop on that connection are errors”). Kernel-writable bytes are still semantically rejected.
- `self.follow_dirty` is written in session-update/permit paths and never read. Dead flag, not a write-through.
- Contract WRITE_OPS does not include `set_config_option`; the server still refuses it after follow via the catch-all branch.

## Conclusion

**PASS**

The follow FD is a Unix-socket view projection: after `op=follow`, holder-side dispatch cannot reach `handle_request` / `send_message`; exclusive agent stdio stays on the holder; L0 send-wait is unchanged; bind remains AF_UNIX 0600 + peer uid; slow-drop and CLI death are scoped to that follower.
