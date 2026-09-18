# Issue #74 real A→B path (isolated scratch Git repo)

Freeze candidate: `44a17b97e5d9fee90352efd00d74b72832f1e5c9` on `workflow/issue-74`.
Base: origin/main `c963bade2c73fc0ad8090c43bce0094ec008c3bb` (includes published #79 `b40813f` and sunk #80).
Adapter `scripts/kaola-zcode-acp.py` sha256 `cb029a22a2337e5ff54898e4a315d372ee3f8939d72f0ebbbd3f23210bd63919` equals origin/main.
Not ACCEPT. No finalize/archive/sink/merge/push.

## What this run is

Authentic ZCode.app **3.12.3** ACP via the **candidate** adapter (not the older globally installed Skill copy, no global install). Isolated scratch Git repo `/tmp/kpr-i74-ab-KNdEO4/repo`. Standard Host `zcode-I74AB-orchestrator-main`. One authorized Devin worker `devin-I74AB-i74-receipt` (SWE-2 Max / `swe-2-max`).

This is **not** `tests/contract/test-issue-74-kaola-delegator.py` (fake ACP). Fake receipts stay under `evidence/` and `evidence/post-stop-new-host/`.

## Authorization used (this test only)

Recorded in `00-AUTH.txt` and `05-handoff.txt` **before** `start`:

- objective: validate Delegator lifecycle without production changes
- allowed worker: Devin SWE-2 Max only
- one concurrent, at most one short task
- highest priority
- no user project files
- delivery: test receipts only
- stop all I74AB test sessions at end

A `status` on the standard name returned `no-session` (`01-A-status-before.json`). Start followed that complete authorization. Existing live Hosts were snapshotted (`00-existing-session-names.txt`) and not touched.

## Authentic sequence (measured)

| Step | Receipt | Fact |
|---|---|---|
| A recover | `01-A-status-before.json` | no Host; no second start on ambiguity |
| preflight | `02-preflight.json` | adapter `kaola-zcode-acp` 0.3.3; Coding Plan available; mode current `yolo` |
| A start | `03-A-start.json` | `state=ready`, `error=null`, **mode yolo applied=true**, `acp_session_id=zcode-1`, holder `7efadb013f774648bb5e4c281cc613ea`, bridge path is the worktree adapter |
| A live status | `04-A-status-live.json` | `agent_alive=true`, same session/holder/ACP id |
| A handoff | `06-A-handoff-send.json` | real model turn `turn_completed` / `end_turn` in 43032 ms; 7 tool calls (read/execute/edit), 0 failed; Host loaded Project Runner and dispatched Devin |
| Worker | `08-worker-status.json`, `10-worker-RECEIPT.txt` | session `devin-I74AB-i74-receipt` on the scratch repo; `RECEIPT.txt` is exactly `KAOLA74-AB-TOKEN\n` (17 bytes) |
| Event wake | `12-host-wait-after-worker.json` | Host `wait` completed a **second** real turn: worker idle event, fingerprint-matched dispatch, quoted token, Host stopped the I74AB worker (`stopped=true`, residual none) |
| B attach | `14-B-attach-status.json`, `14-B-identity-delta.json` | **no start**. Same session, same `acp_session_id=zcode-1`, same holder. `agent_alive=true` |
| B follow-up | `16-B-followup-send.json` | real model reply 4764 ms, 0 tools: quotes token, confirms one Host, no second dispatch |
| Exact stop | `17-host-stop.json` | `stopped=true`, `residual_pids=[]` |
| Cleanup | `18-host-status-after-stop.json`, `19-leftover-pgrep.txt`, `20-sessions-after-cleanup.json`, `21-worker-stop-idempotent.json` | Host `state=stopped`; no I74AB leftover processes; worker stop idempotent `residual_pids=[]` |

Foreign sessions: `new_sessions=[]`, `gone_sessions=[]`, `alive_changed=[]` versus the pre-test snapshot. Desktop `zcode-host-local-1`, `zcode-kaola-vrpcadcore-orchestrator`, `grok-KPR-i74-livefinal`, and all `devin-KPR-*` / `claude-code-KPR-*` were left running.

No `.kaola/delegator-host.json`. Inner Project Runner wrote `.kaola/heartbeat-prompt.json` only (`10-heartbeat-prompt.json`).

## Not claimed / untested

- **Grok Bot live UAT** still not executed.
- **Stopped-Host `--resume sess_*`** restoring the same native session is still the previously measured cannot-resume boundary on 3.12.3; latest comments allow a **new** Host after confirmed stop once authorization is complete. This run did not try `--resume`. Native `sess_*` was not on the start receipt (lazy until identity event).
- **Missing-authorization non-start** remains a documentation contract. This test **had** complete authorization before start.
- **Fake ACP** contract tests are not this path (they still PASS separately).
- Globally installed `~/.claude/skills/zcode-kaola-project-runner` was **not** used and **not** overwritten.

## Renderer / contract (same freeze)

See `kaola-workflow/issue-74/evidence/validate-02f37b0/` (HEAD then `02f37b0`) plus the equal-length issue-49 probe commit `44a17b9`:

- `render-skills.py --check` PASS (9 workers + Project Runner + kaola-delegator + grok-bot 2536 B / 2560)
- `kaola-grok-bot-verify.py --repo <worktree> hosts/grok-bot` PASS
- `test-issue-74-kaola-delegator.py` 108 assertions PASS
- `test-issue-79-zcode-312.py` 19/19 PASS
- `test-zcode-acp-contract.py` 34/34 PASS
- `test-issue-49-grok-bot-host.py` first run 42/43: append probe overflowed the 2536 B bridge (room 24 B). Equal-length template probe in `44a17b9`; rerun 43/43 PASS, no Errno 66 (`test-issue-49-grok-bot-host.rerun.log`)

Full `validate.sh` is not re-claimed in this file; #80's fixture knobs are in the candidate.

Waiting outer ACCEPT.
