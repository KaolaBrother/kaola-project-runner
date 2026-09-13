# Issue #25 TDD red proof

## Worktree

- path: `/Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/bundle-25`
- HEAD: `192808655a29ba345459406d630396583132c09d`

## Frozen loser error code

`unknown-request`

Sequential second `permit --request-id` on a still-pending *other* id already returns this code. Concurrent same-id loser is pinned to the same fact. `already-answered` is not introduced.

## Production custody

Did **not** edit:

- `scripts/kaola-acp-holder.py`
- `scripts/kaola-acp.py`
- adapters, templates, generated skills

`scripts/validate.sh` already runs `tests/contract/test-acp-contract.py`; no new suite file.

## Files changed

- `tests/contract/test-acp-contract.py` — issue #25 tests + shared fixture helpers
- `tests/contract/hooks/sitecustomize.py` — test-only PYTHONPATH hook; wraps holder `Popen` stdin so a permission-result write sleeps 50ms (GIL released between `pending.get` and `pending.pop`). Not production.

## Baseline existing suite (green)

Command:

```
python3 tests/contract/test-acp-contract.py
```

Before adding tests: 14 tests, 17.194s, OK.

After adding tests, the original 13 `AcpContractTests` + issue #22 still PASS. New concurrent same-id tests FAIL.

## New / extended suite (RED)

Command:

```
python3 tests/contract/test-acp-contract.py -v
```

Exact FAIL output (full file: 18 tests, 19.973s, FAILED (failures=2)):

```
test_multiple_concurrent_permissions (__main__.AcpContractTests.test_multiple_concurrent_permissions) ... ok
...
test_concurrent_cancel_same_pending_id_at_most_once (__main__.Issue25PermitLockTests.test_concurrent_cancel_same_pending_id_at_most_once) ... FAIL
test_concurrent_permit_same_request_id_at_most_once (__main__.Issue25PermitLockTests.test_concurrent_permit_same_request_id_at_most_once) ... FAIL
test_l0_send_wait_receipt_keys_unchanged (__main__.Issue25PermitLockTests.test_l0_send_wait_receipt_keys_unchanged) ... ok
test_sequential_second_permit_same_id_is_unknown_request (__main__.Issue25PermitLockTests.test_sequential_second_permit_same_id_is_unknown_request) ... ok

======================================================================
FAIL: test_concurrent_cancel_same_pending_id_at_most_once (__main__.Issue25PermitLockTests.test_concurrent_cancel_same_pending_id_at_most_once)
----------------------------------------------------------------------
AssertionError: 2 not less than or equal to 1 : op_cancel must not double-cancel 1001; events=[
  {'event': 'outbound_response', 'id': 1001, 'message': {'id': 1001, 'jsonrpc': '2.0', 'result': {'outcome': {'outcome': 'cancelled'}}}, 'method': 'session/request_permission', ...},
  {'event': 'outbound_response', 'id': 1001, 'message': {'id': 1001, 'jsonrpc': '2.0', 'result': {'outcome': {'outcome': 'cancelled'}}}, 'method': None, ...}
]

======================================================================
FAIL: test_concurrent_permit_same_request_id_at_most_once (__main__.Issue25PermitLockTests.test_concurrent_permit_same_request_id_at_most_once)
----------------------------------------------------------------------
AssertionError: 2 != 1 : exactly one concurrent permit may succeed; receipts=[
  {'option': 'allow', ..., 'permitted': 1001},
  {'option': 'allow', ..., 'permitted': 1001}
]
```

Focused re-run of the new class:

```
python3 tests/contract/test-acp-contract.py Issue25PermitLockTests -v
```

same two FAILs, sequential + L0 OK.

## Table

| Test | Baseline result |
|---|---|
| `AcpContractTests.test_multiple_concurrent_permissions` (3 distinct ids + `request-id-required`) | PASS |
| `Issue25PermitLockTests.test_sequential_second_permit_same_id_is_unknown_request` | PASS (pins frozen `unknown-request`) |
| `Issue25PermitLockTests.test_concurrent_permit_same_request_id_at_most_once` | FAIL (two successes; two agent JSON-RPC results) |
| `Issue25PermitLockTests.test_concurrent_cancel_same_pending_id_at_most_once` | FAIL (two cancelled JSON-RPC results for id 1001) |
| `Issue25PermitLockTests.test_l0_send_wait_receipt_keys_unchanged` | PASS |
| Issue #22 yolo default | PASS |

## How concurrent permit is driven

Two already-connected AF_UNIX clients send the same `op=permit` payload as `kaola-acp.py grok permit` after a barrier (CLI process startup serializes the race on this host). Mock log counts `outbound_response` JSON-RPC responses whose message `id` matches the permission `request_id`.
