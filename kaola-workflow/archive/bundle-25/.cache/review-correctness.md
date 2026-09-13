# Review: correctness (issue #25 permit lock)

## Candidate hash

`a76670cf93a6ee25591ddbeb7371529395e7bc00` (`fix: settle ACP permit/cancel/stop at most once per request_id`)

Reviewed against GitHub #25 and `docs/acp-watch/permit-lock.md`.
Worktree HEAD at review: the hash above. Did not modify `scripts/`, `tests/`, `templates/`, `skills/`, or docs.

## Findings

None.

Established:

- Permission JSON-RPC results are written only in `_settle_pending_permission_locked` (`scripts/kaola-acp-holder.py:1116-1118`). Other `send_message` sites are `session/prompt` / generic requests, `-32601` for unsupported methods, and `session/cancel` (not a result for the permission `request_id`).
- Lookup + send + pop is one critical section under `Holder.lock` (`1104-1120`, callers `1124-1126` and `1131-1142`). The loser of a named-id settle hits `entry is None` and returns `unknown-request` (`1143-1145`) without a second stdin write.
- `op_cancel` (`1152-1160`) still sends `session/cancel` after `_cancel_pending_permissions()`. Two concurrent cancels can emit two `session/cancel` notifications; they cannot both `_settle` the same pending id because the second lock holder iterates an empty map.
- `op_stop` (`1278`) uses the same `_cancel_pending_permissions()` path.
- `op_prompt` admission and permission settle share `self.lock` (`1004`, `1131`, `1124`).
- Lock order does not deadlock on the examined paths: `_settle` does not re-enter `Holder.lock`; `send_message` does not take `AgentConnection.lock`; `turn_cond` is a separate `Condition()` and is never waited while holding `Holder.lock`; `write_record` takes only `record_lock`.
- Distinct-id concurrent permits remain sequential successes under the same lock (existing `test_multiple_concurrent_permissions`).
- L0 `send --wait` keys unchanged (`Issue25PermitLockTests.test_l0_send_wait_receipt_keys_unchanged`).

Commands:

```
python3 tests/contract/test-acp-contract.py Issue25PermitLockTests -v
# 4 tests, OK, 5.286s

python3 tests/contract/test-acp-contract.py AcpContractTests.test_multiple_concurrent_permissions -v
# 1 test, OK, 1.142s
```

Concrete concurrent same-id permit: two Unix clients, barrier, `permit` with the same `request_id` (`tests/contract/test-acp-contract.py:494-531`). Mock stdin log records one `outbound_response` for that id; winner has `permitted`; loser `error.code == unknown-request`. Slow-stdin hook (`tests/contract/hooks/sitecustomize.py`) widens the write window; lock still yields one result.

## Suspicions (not defects)

- `on_agent_request` (`785-800`), `$/cancel_request` (`770-777`), and `on_agent_exit` (`890-891`) still mutate `pending_permissions` without `Holder.lock`. Under the GIL this can race a settle (e.g. insert of a reused id between get and pop, dropping the new entry). That is a lost pending, not a second JSON-RPC result for one id. Issue #25 only forbids double-write; I could not exhibit two results from this race.

## Conclusion

PASS
