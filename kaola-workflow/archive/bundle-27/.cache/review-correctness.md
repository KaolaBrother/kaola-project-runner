# Correctness review — issue #27 local holder `follow`

Frozen candidate: dirty worktree `/Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/bundle-27` (branch `workflow/bundle-27`).  
Spec: GitHub #27 and `docs/acp-watch/follow.md`.  
Contract: `tests/contract/test-acp-follow-contract.py` (not modified in this review).  
Orchestrator already reported follow 11 OK; this review is against the spec and those tests, not a re-run.

Claim under test: the candidate implements local holder follow as specified.

---

## Finding 1 — drop condition is not “queue > 256”

**Spec:** `docs/acp-watch/follow.md` line 18: a slow consumer whose **queue** exceeds 256 lines gets `follow-dropped` and that path disconnects; agent stdio does not pause. Same sentence in `docs/api.md` and issue #27 (“Queue cap: drop that follower”).

**Code:**

- `scripts/kaola-acp-holder.py:358` `FOLLOW_QUEUE_CAP = 256`
- `scripts/kaola-acp-holder.py:588` `queue.Queue(maxsize=FOLLOW_QUEUE_CAP)` — this part matches the spec (257th `put_nowait` raises `Full`).
- `scripts/kaola-acp-holder.py:593` `self.produced = 0` — lifetime counter of **offer attempts**, not queue depth. Never reset.
- `scripts/kaola-acp-holder.py:591` `self.blocked` — set when a send is not writable for 50ms; **never cleared** (only `blocked.set` at line 720; grep shows no `blocked.clear`).
- `scripts/kaola-acp-holder.py:636-639`:

```python
self.produced += 1
if self.blocked.is_set() and self.produced > FOLLOW_QUEUE_CAP:
    self._drop_locked()
    return False
```

- `scripts/kaola-acp-holder.py:716-723` (inside `_send`): if `select` 0s then 50ms both fail, set `blocked` and drop when `produced > 256`, even if `queue.qsize()` is 1.

**Concrete state that goes wrong:**

1. Follower consumes 256 snapshot/delta/heartbeat lines in real time. Queue is empty. `produced == 256`.
2. At any earlier moment the Unix socket was not writable for 50ms (`FOLLOW_SNDBUF = 4096` at holder line 360; CLI also sets `SO_RCVBUF = 4096` at `scripts/kaola-acp.py:308`). `blocked` stays set for the life of the follower.
3. Event 257 is offered (another `agent_message_chunk`, or a heartbeat at `FOLLOW_HEARTBEAT_SECONDS = 5`). Queue depth is still ~0–few.
4. `_offer_locked` drops the follower with `follow-dropped` / disconnects that path.

That is not “queue > 256”. A caught-up consumer that once stalled 50ms is treated as overflow after 257 lifetime lines.

The flood contract (`test_slow_follower_dropped_without_pausing_agent_stdio`) still passes because a paused reader fills `Queue(maxsize=256)` and hits `queue.Full` — the correct path. It does not pin the incorrect `produced`+sticky-`blocked` path. `assertGreater(FOLLOW_QUEUE_CAP, 0)` (test line 697) does not bind holder behavior to 256.

---

## Finding 2 — `tool_call` / plan / mode / usage never fan out as `delta`

**Spec / issue:** snapshot then **cursor deltas** whose payload is `kaola-acp-view/1`; two followers must see the same `tool_call`. Heartbeats exist so a **dropped** delta cannot hide a permission card (`pending_permissions` + `mutation_status`), not as the only carrier for tools.

**Code:**

- `scripts/kaola-acp-holder.py:362-366` — `FOLLOW_STREAM_UPDATES` is only `agent_message_chunk`, `user_message_chunk`, `agent_thought_chunk`.
- `scripts/kaola-acp-holder.py:1037-1041` — only those variants call `fanout_follow_delta()`. Everything else (`tool_call`, `tool_call_update`, `plan`, `current_mode_update`, `usage_update`, `available_commands_update`, `config_option_update`) sets `self.follow_dirty = True` and returns.
- `follow_dirty` is assigned at lines 774, 993, 1038, 1041, 1067, 1347 and **never read**. Grep of `scripts/kaola-acp-holder.py` shows no consumer. Coalesced flush was not implemented.
- Immediate fanout otherwise only on permission request (993-994), prompt response (1067-1068), permit (1347-1348), and permission cancel (967).
- Heartbeat (`1456-1462`, `1493-1499`) sends `kind=heartbeat` with a full view. Contract `wait_tool` / stream assertions only inspect `kind in {snapshot, delta}` (`test-acp-follow-contract.py:136-145`, `511`).

**Concrete input:**

Agent emits `sessionUpdate: tool_call` (`toolCallId=call_7`) and then stays on that tool (no further message/thought chunk, no `session/request_permission`, turn still active). Followers already have their initial snapshot.

- Projection updates in memory (`projection.apply` at 1035).
- No `offer_delta`. `follow_dirty` is true and ignored.
- Next `kind=delta` does not exist until a later stream chunk, permission, permit, or prompt completion.
- A 5s heartbeat may contain the tool, but `kind=heartbeat`, so a client following the documented snapshot/delta stream (and the contract helper) does not treat it as the tool event.

Why the 11 contract tests still pass: `watch_projection` always `ask_permission` after the tool (`mock-acp-agent.py:348-411`), which fans out; `follow_flood` always `finish_turn` after `call_flood` (`414-432`), and `on_prompt_response` fans out. Those fixtures hide the missing `tool_call` delta.

Same gap: `op_prompt` writes the user line into the projection (`1257`) and does not fan out, so a follow client does not see the local prompt until the agent’s next stream notification.

---

## Suspicion — `--format text` reprints the full timeline on every delta

`scripts/kaola-acp.py:240-268` prints every `messages[].text` and `tools[].title` for each `snapshot` **and** each `delta`. Deltas are full `op_view` objects (`holder.py:1448-1454`), not patches. Spec only requires joining titles and “not a second TUI”. Not admitted as a defect; likely noisy, not a protocol break. `test_format_text_joins_titles_and_is_not_ndjson_only` only checks that some title appears and stdout is not NDJSON-only.

## Suspicion — snapshot vs register race

`start_follow` (`1474-1491`) calls `op_view` **outside** `followers_lock`, then offers the snapshot and appends. A `fanout_follow_delta` in that window does not include the new follower. The first snapshot can be a cursor behind live state; recovery depends on a later fanout (see Finding 2) or a heartbeat. Not demonstrated with a failing input.

## Test custody (observation, not a production defect)

The new contract file covers the issue’s named cases (two followers, follow-FD writes, third-socket permit, kill follow, eof, holder-lost, text format, L0/view while attached). It does not pin queue-depth vs lifetime `produced`, and it does not emit a `tool_call` without a later permission/prompt-complete. Those holes let Findings 1–2 through.

---

## Conclusion: DEFECTS

The command surface is real (`kaola-acp <platform> follow`, holder `op=follow`, NDJSON kinds, read-only FD, third-socket permit, eof / holder-lost, `--format text`, tmux `follow-unsupported`). The 11 contract tests as written can pass.

They do **not** establish the spec. Drop uses a sticky 50ms-block flag plus a lifetime offer counter instead of queue depth 256. `tool_call` (and plan/mode/usage) do not emit cursor deltas; `follow_dirty` is dead. Those are specified follow behaviors, not nits.

Verdict: **DEFECTS** — refute the claim that this candidate implements local holder follow as specified.
