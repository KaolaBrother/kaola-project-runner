# Review: trust boundary (issue #25 permit lock)

## Candidate hash

`a76670cf93a6ee25591ddbeb7371529395e7bc00`
(`fix: settle ACP permit/cancel/stop at most once per request_id`)

Worktree HEAD at review: the hash above. Did not modify `scripts/`, `tests/`,
`templates/`, `skills/`, or docs.

Focus: exclusive agent stdio, at-most-once permission results, no second ACP
client, no prompt shell-eval, no grok-golden change, no new TCP/HTTP bind,
L0 keys unchanged, sitecustomize test-only, generated holders match source.

## Findings

None.

## Checks established

### Exclusive agent stdio — permission results only via holder `send_message`

All permission JSON-RPC **results** go through `_settle_pending_permission_locked`
(`scripts/kaola-acp-holder.py:1104-1120`), which calls `self.agent.send_message`
with `{"jsonrpc":"2.0","id": entry["request_id"], "result": {"outcome": ...}}`.

Callers (all under `Holder.lock`):

- `op_permit` (`1128-1150`) — selected or cancelled option for one id
- `_cancel_pending_permissions` (`1122-1126`) used by `op_cancel` (`1155`) and
  `op_stop` (`1278`)

Other `proc.stdin.write` sites in the holder:

- `AgentConnection.send_message` (`277-285`) — the single live-session writer
- `send_request` (`293-295`) — outbound requests (`session/prompt`, close, …)
- unimplemented-method **error** (`808-810`) — not `session/request_permission`
- `op_cancel` / `op_stop` `session/cancel` **notifications** (`1157-1159`,
  `1281-1283`) — no result id for the permission request
- `op_stop` `stdin.close()` (`1295-1297`)
- `run_probe` (`1510-1547`) — separate short-lived preflight process, not the
  live holder session

`scripts/kaola-acp.py` `permit`/`cancel`/`stop` only `socket_request` the Unix
holder (`256-276`, `339-370`). CLI does not open agent stdio. No second ACP
client was added in this diff (`kaola-acp.py` is not in the commit).

Prompt text still travels as JSON-RPC `session/prompt` params (`1027-1032`),
not `eval` / `shell=True`.

### Two Unix clients cannot both emit a result for one id

`listen(16)` still spawns one daemon thread per connection (`1479-1481`).
Settlement is `get` → `send_message` → `pop` in one `with self.lock` section
(same lock as `op_prompt` admission at `1004`). A second settler sees `None`
and returns `unknown-request` without writing stdin (`1143-1145`).

`send_message` is invoked while still holding `Holder.lock`, so the stdin write
for that id cannot overlap another settle of the same map entry.

Concrete input: two already-connected AF_UNIX clients, `threading.Barrier`,
same `params.request_id` (`tests/contract/test-acp-contract.py`
`test_concurrent_permit_same_request_id_at_most_once`). Mock
`outbound_response` log counts one JSON-RPC result for that id; one receipt has
`permitted`, the other `error.code == unknown-request`. Concurrent `cancel`
(`test_concurrent_cancel_same_pending_id_at_most_once`) likewise yields one
result for the pending id (two `session/cancel` notifications remain possible
and are not permission results).

### Follow / list / view / HTTP not added by this candidate

`git diff --name-only` vs parent `192808655a29ba345459406d630396583132c09d`
is holder + tests + changelog/docs + generated `acp.md` / holders. No
`AF_INET` / HTTP bind in the holder diff. Listener remains `AF_UNIX`
(`1442-1449`). Follow is still unimplemented (changelog). List/view exist on
the parent (#26); this commit did not add them.

### `templates/grok-golden/` unchanged

`git diff --stat templates/grok-golden` empty (working tree and vs parent).

### L0 `send --wait` keys not expanded with watch fields

`kaola-acp.py` / `turn_receipt` were not modified in this commit. Test
`test_l0_send_wait_receipt_keys_unchanged` asserts frozen key set and forbids
`timeline`, `thinking_text`, `plan`, `messages`, `tools`. Ran: PASS.

### sitecustomize is test-only

`tests/contract/hooks/sitecustomize.py` is new and only on `PYTHONPATH` in
`Issue25PermitLockTests.env()` (`test-acp-contract.py:458-459`). `find` over
`skills/`, `templates/`, `scripts/` has no `sitecustomize.py`. Production
holder spawn (`kaola-acp.py:485-488`) does not set `PYTHONPATH`.

### Generated holders match source

`shasum` of `scripts/kaola-acp-holder.py` and all six
`skills/*/scripts/kaola-acp-holder.py`: `602b22ea8c8b2037b1906ec30668c81bcfaa3d90`.
`./scripts/render-skills.py --check`: PASS (6 Skills).

## Commands

```
git checkout a76670cf93a6ee25591ddbeb7371529395e7bc00
git diff --stat templates/grok-golden          # empty
./scripts/render-skills.py --check             # PASS (6 Skills)
python3 tests/contract/test-acp-contract.py -v # 18 tests, OK, 22.159s
```

Issue25PermitLockTests: 4/4 OK (includes concurrent same-id permit/cancel and L0 keys).

## Suspicions (not defects)

- Agent reader still mutates `pending_permissions` without `Holder.lock`
  (`on_agent_request` insert `800`, `$/cancel_request` pop `776-777`,
  `on_agent_exit` pop `890-891`). Those paths do not `send_message` a
  permission result. Could not exhibit two JSON-RPC results for one id from
  that race; Unix-client settlers remain serialized on `Holder.lock`.

## Conclusion

PASS
