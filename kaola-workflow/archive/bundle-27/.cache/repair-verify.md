# repair-verify — issue #27 queue-depth drop and tool deltas

Worktree: `/Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/bundle-27`

## Repair

- Drop only on `queue.Full` (cap 256). Removed lifetime `produced` and sticky `blocked`.
- Writer waits on `select` for writability; does not drain the queue into the kernel while the client is stopped.
- Every `session/update` applies the projection **before** incrementing `event_cursor`, then fans out a delta (tool_call/plan/mode/usage included).
- `tool_call_only` mock + `test_tool_call_emits_delta_without_permission`.
- Slow-follower test SIGSTOP/SIGCONT so the follow FD itself stalls (pipe buffers no longer hide queue depth).

## Commands

```
python3 tests/contract/test-acp-follow-contract.py -q
```
exit 0 — Ran 12 tests in 7.043s — OK

```
python3 tests/contract/test-acp-watch-contract.py -q
```
exit 0 — Ran 10 tests — OK

```
python3 tests/contract/test-acp-contract.py -q
```
exit 0 — Ran 18 tests — OK

```
./scripts/render-skills.py --write && ./scripts/render-skills.py --check
```
exit 0 — WROTE / PASS (6 Skills)

```
./scripts/validate.sh
```
exit 0 — VALIDATE:0

```
git diff --stat templates/grok-golden
```
empty
