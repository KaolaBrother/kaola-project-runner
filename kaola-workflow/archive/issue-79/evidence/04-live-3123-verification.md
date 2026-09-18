# Issue #79 — Mission 5: live verification against the real installed ZCode 3.12.3

Date: 2026-09-18/19. Machine: this Mac. Desktop ZCode **3.12.3** (build 3.12.3.7463), bundled CLI
reporting 0.16.5. Entry `/Applications/ZCode.app/Contents/Resources/glm/zcode.cjs`,
node `/opt/homebrew/bin/node`.

Isolated disposable Git repo: `/tmp/kpr-i79-live-08jK6H/repo` (`git init`, one fixture commit `d362a6d`).
Not this repository, not any user project. No global ZCode config was modified, no existing ZCode
session was touched, and no credential was copied, decrypted, or printed.

All transport went through the Runner ACP path
(`scripts/kaola-tmux.sh zcode {preflight,start,send,stop}`), not a hand-rolled client.

## Sequence actually run, in order

| # | step | result |
|---|---|---|
| 1 | `preflight` | ACP selected; desktop registry read; only `builtin:bigmodel-coding-plan` eligible, others refused |
| 2 | `start` (attempt 1) | app-server **started** (env injection works) but `provider/updateAccountConfig` rejected the snapshot |
| 3 | `stop` | `stopped: true`, `residual_pids: []` |
| 4 | `start` (attempt 2) | `updateAccountConfig` accepted; `session/setModel` rejected |
| 5 | `stop` | `stopped: true`, `residual_pids: []` |
| 6 | `start` (attempt 3) | `state: ready`, **mode yolo applied: true**, no error |
| 7 | `send` | **live model reply** |
| 8 | `stop` | `stopped: true`, `residual_pids: []` |

## What the live run corrected in the static reading

Two facts could not be established statically and were settled here. Both had been carried into
this mission as explicit unknowns rather than guessed.

**1. `states[<id>]` is richer than the snapshot validator implied.** `G6n` only reads
`states[id].current`, but the wire schema also requires `availability` and `entitled`. Raw error
from attempt 1:

```
Invalid params — states.account:bigmodel-individual-coding-plan.availability:
  Invalid option: expected one of "available"|"pending"|"unavailable"|"unknown";
states.account:bigmodel-individual-coding-plan.entitled:
  Invalid input: expected boolean, received undefined
```

Fixed by sending all three. `availability` is reported from the desktop plan cache and falls back
to `unknown` for an unrecognised status — it is never upgraded to `available`.

**2. A reasoning level is mandatory for the Coding Plan models.** Raw error from attempt 2:

```
ModelProtocolError: Reasoning level is required for account:bigmodel-individual-coding-plan/GLM-5.3
  at createRegistrySelectionProtocolError (…/glm/zcode.cjs:3199:2630)
  at resolveRegistryOwnedModelSelection (…/glm/zcode.cjs:3199:2160)
  at Object.setModel (…/glm/zcode.cjs:3199:10789)
```

Fixed by resolving the allowed levels from the bundled table's `modelConfigRules` (regex rules in
order, later overriding, matched as `^(?:<modelMatch>)$` case-insensitively) and sending
`options.reasoningLevel`. Resolved values on this machine: `GLM-5.3` and `GLM-5.3-Flash` →
`["low","high","max"]`; an unmatched model → `["disabled","enabled"]`.

**3. `basedOnZCodeBuiltinRevision` was the highest-risk open item and needed no guess.** Computing
it as `zcode-builtin:<revision>:<sha256 of the resolved path>` over the injected `.app` bundled
table was accepted by the live app-server; attempts 2 and 3 got past `updateAccountConfig` with it.

## Final successful run — raw receipts (sanitized)

`start`:
```json
{
 "state": "ready",
 "acp_session_id": "zcode-1",
 "mode_applied": true,
 "mode_value": "yolo",
 "error": null
}
```

`send` (prompt: `Reply with exactly the word: KAOLA79OK`):
```json
{
 "acp_session_id": "zcode-1",
 "outcome": "turn_completed",
 "stop_reason": "end_turn",
 "final_text": "KAOLA79OK",
 "duration_ms": 4530,
 "tool_calls": {
  "count": 0,
  "failed": 0,
  "kinds": {}
 },
 "failed_tools": [],
 "pending_permissions": [],
 "mutation_status": "completed",
 "side_effects": {
  "commands_run": 0,
  "files_changed": 0
 }
}
```

`stop`:
```json
{
 "session": "zcode-i79-live",
 "stopped": true,
 "residual_pids": [],
 "holder_pid": null,
 "agent_pid": null,
 "error": null
}
```

## Acceptance against the issue's Mission 5 wording

- start with yolo applied — **yes**, `state: ready`, `mode applied: true`, value `yolo`.
- explicit correct model selection — **yes**, `session/setModel` on
  `account:bigmodel-individual-coding-plan` / `GLM-5.3` with an explicit reasoning level and
  `persistAsWorkspaceLastUsed: false`.
- simple live model reply — **yes**, `final_text: "KAOLA79OK"`, `stop_reason: end_turn`,
  `outcome: turn_completed`, 4530 ms, 0 tool calls, 0 files changed.
- exact stop with `residual[]` — **yes**, `stopped: true`, `residual_pids: []` on every one of the
  three stops.

This is a real model turn against the real provider, not a fake backend. The hermetic suite is
separate and never stands in for it.

## Secret handling

- The plan credential was read from `~/.zcode/v2/config.json` in memory by the adapter only.
- `~/.zcode/v2/credentials.json`, `setting.json` and `~/.zcode/v2/provider_config.json` were never
  opened; the personal config is referenced by path only.
- Leak check over every receipt above plus the event log: credential present = **False**.
- No key material appears in this file, in any receipt, or in any commit.
- Nothing was written under `~/.zcode`; `persistAsWorkspaceLastUsed: false` keeps the user's
  workspace defaults untouched.

## Cleanup

All three sessions stopped exactly, each reporting `residual_pids: []`. No leftover
`zcode-i79-live` process and no Issue #79 holder remained. Pre-existing orphans belonging to the
#74 / #67 runs were observed but deliberately left alone; the one hung process this run created
(a bare `kaola-tmux.sh` invocation waiting on stdin) was killed by exact PID after confirming
ownership.
