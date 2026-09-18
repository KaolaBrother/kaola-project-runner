# Issue #79 — Mission 6: frozen final candidate

Candidate: **`55f330fb99a57338c949c953d7c7e98327c603f2`** on `workflow/issue-79`, rebased onto `main` @ `f6cbe27` (5 commits).
Rebase was clean; the branch now inherits #78's here-document fix
(`grep -c` here-docs in `scripts/kaola-tmux.sh`: was 9 at the old base `f6be8a3`, now 0).

## Commits

```
55f330f fix(zcode): commit the model selection only after the backend accepts (Issue #79)
e3477ea fix(zcode): route mid-session model switches through the account path (Issue #79)
3a9b240 fix(zcode): keep the generated Skill free of parent-path references (Issue #79)
396dc99 fix(zcode): live-measured account state and reasoning level (Issue #79)
5ee3388 fix(zcode): ZCode 3.12+ ACP app-server compatibility (Issue #79)
```

## Second live verification, on THIS candidate

Fresh isolated disposable repo `/tmp/kpr-i79-live2-HrScRY/repo` (`git init`, fixture commit `ccd76b7`), real desktop
ZCode **3.12.3**, through the Runner ACP path. Credential read only in the adapter's memory; never
copied, decrypted, or printed.

| step | receipt |
|---|---|
| `start` | `state: ready`, mode **yolo applied: true**, `error: null` |
| `send` | `final_text: "KAOLA79FINAL"`, `stop_reason: end_turn`, `outcome: turn_completed`, 5463 ms, 0 tool calls, 0 files changed |
| `stop` | `stopped: true`, **`residual_pids: []`**, no holder or agent left |

Credential present in the final receipts: **False**. No leftover `zcode-i79-final` process.

This repeats the Mission 5 result (`KAOLA79OK`, 4530 ms) on the post-rebase code that includes the
two review-driven fixes, so the live proof belongs to the candidate being handed over, not to an
earlier tree.

## Test receipts on this candidate

| surface | result |
|---|---|
| `render-skills.py --check` | PASS (budgets OK) |
| `test-generated-skills.py` | PASS |
| `test-issue-79-zcode-312.py` | **19/19 OK** |
| `test-zcode-acp-contract.py` | 34/34 OK |
| `test-zcode-host-contract.py` | exit 0 |
| `test-zcode-heartbeat-contract.py` | exit 0 |
| `test-issue-51-runner-integration.py` | **6/6, 119 checks** — was 4/6 on the old base |
| `test-issue-78-heredoc-deadlock.py` (inherited) | 3/3 OK |
| `test-issue-49-grok-bot-host.py` | **RED** — `[Errno 66] Directory not empty` in `TemporaryDirectory` teardown, 43 tests / 1 error |

## Honest status of the two reds seen during this run

1. **`test-issue-49-grok-bot-host.py` — still RED, not fixed here.** Reproduced identically at the
   original base `f6be8a3` in a throwaway worktree, deterministic across repeats, and it is a
   teardown race rather than an assertion failure. Owned by **#80**. This candidate is NOT claimed
   to make full `validate.sh` green.
2. **`test-issue-51-runner-integration.py` — was RED, now GREEN after the rebase.** Its two failures
   were 60 s timeouts in `install-local.sh` and `kaola-tmux.sh zcode status`, caused by the
   here-document deadlock that #78 fixed on main and that the old base still carried. It was never a
   defect of this candidate, and it is not claimed as a pass on the old base.

`validate.sh` as a whole still exits non-zero because of #49. Note also that a single
`validate.sh` invocation stops early: a lane aborts at the first failing suite, and the log replay
then hits a missing log under `set -e`, so it is not by itself evidence that the other suites ran.
The per-suite receipts above are the real coverage. The last full clean-env sweep on the previous
frozen SHA reached 27 of 33 suites with exactly those two reds and no others; it was not re-run in
full after the final fixes because any code change invalidates it, and the affected surfaces were
re-verified individually instead.

## Review-driven fixes included

- `e3477ea` mid-session model switch routed through the account path (was sending `runtimeModel`
  and no reasoning level on 3.12+).
- `55f330f` model selection committed to local state only after the backend accepts (a refused
  switch previously left configOptions advertising a model that never took effect).

Both were written failure-first; each reproduced its exact symptom before the fix.
