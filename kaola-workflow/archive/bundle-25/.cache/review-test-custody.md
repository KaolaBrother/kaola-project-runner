# Review: test custody (issue #25 permit/cancel at-most-once)

## Candidate hash

`a76670cf93a6ee25591ddbeb7371529395e7bc00` (`fix: settle ACP permit/cancel/stop at most once per request_id`)

Focus: did the candidate alter acceptance meaning, and can the suite go green while two JSON-RPC results still reach agent stdin?

Worktree HEAD at review: the hash above. Did not modify `scripts/`, `tests/`, `templates/`, `skills/`, or docs.

## Findings

None.

## Established (checklist)

### `wait_for_jsonrpc_results(..., minimum=2)` then `assertEqual(len, 1)`

`tests/contract/test-acp-contract.py:252-260` polls MOCK_ACP_LOG until `len(found) >= minimum` or 1.0s elapses, then returns whatever is present.

Same-id permit (`503`) and cancel (`540`) call it with `minimum=2`, then `assertEqual(len(results), 1)` (`527-529`, `553-555`).

- Two agent-side `outbound_response` results for that id: helper returns as soon as it sees 2; `assertEqual(..., 1)` **fails**.
- One result: helper times out at 1.0s and returns 1; assertion **passes**.
- Zero results: returns `[]`; assertion **fails**.

`jsonrpc_results_for` (`179-192`) keeps only MOCK_ACP_LOG `event == outbound_response` whose JSON-RPC **message has no `method`** (responses, not notifications) and whose `id` matches via `rpc_ids_match`. Duplicate writes with the same permission id are both counted (second mock `on_response` still logs even when `pending` already popped and `method` is `None`; `tests/contract/mock-acp-agent.py:448-455`).

Red-without-lock proof (same tests, parent holder): `kaola-workflow/bundle-25/.cache/tdd-red-proof.md` shows cancel FAIL `2 not less than or equal to 1` with two `outbound_response` rows for id `1001`, and permit FAIL `2 != 1` with two `permitted` receipts. So the suite does not go green on a double write.

### Concurrent permit: agent log + winner/loser + frozen loser code

`test_concurrent_permit_same_request_id_at_most_once` (`494-531`):

- Two already-connected Unix clients, one barrier (`concurrent_holder_ops`, `201-250`), same `request_id`.
- Counts MOCK_ACP_LOG results for that id (not CLI stdout alone).
- Exactly one winner: `error is None` and `"permitted" in receipt`.
- Exactly one loser with `error.code`.
- Loser code frozen: `SETTLED_PERMISSION_ERROR = "unknown-request"` (`45`) asserted at `517-519`. Sequential second permit uses the same code (`466-492`).
- `tagged` filter also requires one permission result (`522-531`).

### Concurrent cancel distinguishes double-cancel

`test_concurrent_cancel_same_pending_id_at_most_once` (`533-556`) fires two `cancel` ops against one pending id, then:

- `assertLessEqual(len(cancelled), 1)` on results whose `result.outcome` is cancelled (string or nested dict).
- `assertEqual(len(results), 1)` on all JSON-RPC **results** for that pending id.

A second cancelled JSON-RPC result for the same id fails both. `session/cancel` notifications are excluded by `jsonrpc_results_for` (`"method" in message`); that is notifications, not permission results. Production still may send two `session/cancel` notifications; the test’s acceptance is at-most-one **result** for the pending permission id.

### Distinct-id test still present; L0 does not replace race tests

- `AcpContractTests.test_multiple_concurrent_permissions` (`396-416`) is unchanged vs parent `192808655a29ba345459406d630396583132c09d` (three pending ids, sequential `permit --request-id` per id). Issue25 docstring points distinct-id concurrency there (`449-452`).
- `test_l0_send_wait_receipt_keys_unchanged` (`558-571`) is an additional key-preservation check, not a substitute for the two race tests. All four Issue25 methods remain.

Existing `AcpContractTests` bodies were not reinterpreted; the class was split to `AcpSessionFixture` + the same 13 tests.

### sitecustomize 50ms sleep is test-only and does not mint GREEN without the lock

`tests/contract/hooks/sitecustomize.py:22-24` sleeps 0.05s on holder→agent stdin writes whose blob contains both `"outcome"` and `"jsonrpc"`. Loaded only when `Path(sys.argv[0]).name == "kaola-acp-holder.py"` (`30`).

PYTHONPATH prepend of `tests/contract/hooks` happens only in `Issue25PermitLockTests.env()` (`455-459`), copied into the CLI subprocess env, inherited by the holder `Popen` (`scripts/kaola-acp.py:485-488` has no env override). `AcpContractTests` does not set that PYTHONPATH.

The sleep sits **inside** `send_message` / `stdin.write`, after `pending.get` and before `pending.pop` on the unlocked parent path. It widens TOCTOU; it is not a mutex. Two holder `serve_connection` threads (`scripts/kaola-acp-holder.py:1479-1481`) can both pass `get`, both sleep, both write. That is the red proof above (2 results / 2 winners). With the candidate lock, the sleep runs while `Holder.lock` is held, so the second settler waits and does not write.

It does not hide a missing lock: without the lock these tests failed; with the lock they pass.

## Commands

```
python3 -m unittest tests.contract.test-acp-contract.Issue25PermitLockTests \
  tests.contract.test-acp-contract.AcpContractTests.test_multiple_concurrent_permissions -v
# Ran 5 tests in 6.310s  OK
```

`scripts/validate.sh` still invokes `tests/contract/test-acp-contract.py` (no suite file swap).

## Suspicions (not defects)

None that would let two JSON-RPC **results** for one permission id pass. Cancel does not pin a loser receipt code (both `op_cancel` calls may return turn receipts); double-cancel is still rejected via the agent log count.

## Conclusion

PASS
