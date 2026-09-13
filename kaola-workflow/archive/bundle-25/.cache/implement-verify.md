# Issue #25 implementer verification

## Worktree

- path: `/Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/bundle-25`
- branch: `workflow/bundle-25`
- HEAD: `a76670cf93a6ee25591ddbeb7371529395e7bc00`
- commit: `fix: settle ACP permit/cancel/stop at most once per request_id`

## Files changed (committed)

- `scripts/kaola-acp-holder.py` — `_settle_pending_permission_locked` + `_cancel_pending_permissions`; `op_permit` / `op_cancel` / `op_stop` settle under `self.lock` (same lock as `op_prompt`)
- `tests/contract/test-acp-contract.py` — TDD `Issue25PermitLockTests` (unchanged meaning)
- `tests/contract/hooks/sitecustomize.py` — test-only 50ms stdin-write hook (kept)
- generated Skill copies of holder + `references/acp.md` (via `./scripts/render-skills.py --write`)
- `templates/references/acp.md.tmpl` — one-line at-most-once fact
- `docs/acp-watch/permit-lock.md`, `docs/acp-watch/README.md`, `docs/README.md`, `docs/architecture.md`
- `CHANGELOG.md`

Not committed: `kaola-workflow/bundle-25/` (workflow cache), `__pycache__`.

Mechanical test maintenance: none. `Issue25PermitLockTests` was not deleted, weakened, or reinterpreted.

## Production change

Under `Holder.lock`: lookup pending → send exactly one JSON-RPC result → `pop`.
Already-settled / missing id returns existing `unknown-request` (no `already-answered`).
`op_cancel` still sends `session/cancel` after the at-most-once permission path.
`op_stop` uses the same cancel-pending path.

## Commands and results

### `python3 tests/contract/test-acp-contract.py -v`

```
Ran 18 tests in 22.202s

OK
```

Including:

- 13 `AcpContractTests` OK
- `Issue22KimiDefaultYoloAcpTests.test_public_default_start_sets_mode_yolo` OK
- `Issue25PermitLockTests` 4/4 OK:
  - `test_concurrent_cancel_same_pending_id_at_most_once`
  - `test_concurrent_permit_same_request_id_at_most_once`
  - `test_l0_send_wait_receipt_keys_unchanged`
  - `test_sequential_second_permit_same_id_is_unknown_request`

### `python3 tests/contract/test-acp-watch-contract.py`

```
Ran 10 tests in 6.317s

OK
```

### `./scripts/render-skills.py --write`

```
render-skills: WROTE (6 Skills)
```

### `./scripts/render-skills.py --check`

```
render-skills: PASS (6 Skills)
```

### `./scripts/validate.sh`

```
render-skills: PASS (6 Skills)
Skill is valid!  (×6)
Ran 7 tests in 0.033s   OK   (test-issue-9-contract.py)
Ran 5 tests in 0.001s   OK   (test-direct-transport-contract.py)
Ran 31 tests in 0.411s  OK   (test-devin-regressions.py)
Ran 18 tests in 22.404s OK   (test-acp-contract.py)
Ran 10 tests in 4.388s  OK   (test-acp-watch-contract.py)
Ran 4 tests in 0.002s   OK   (test-runner-v2.py)
generated Skill acceptance: PASS
Ran 14 tests in 0.017s  OK   (test-issue-24-opencode-pty-bypass.py)
```

exit 0.

### `git diff --stat templates/grok-golden`

empty (no output). grok-golden unchanged.

## What was not run

- Live tmux smoke per platform (start/observe/send/capture/stop)
- Live Cursor / Grok / Kimi / Devin / OpenCode / Claude CLI binaries
- `./scripts/install-local.sh`
- No environment or service acceptance against a real ACP agent

## Scope conflict

None.
