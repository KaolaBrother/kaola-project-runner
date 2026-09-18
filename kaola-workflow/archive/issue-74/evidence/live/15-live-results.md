# Issue #74 live ZCode A→B isolation (real app-server)

Isolation project: `/Volumes/WorkspaceA/ylminiserver/workspace/kaola-i74-iso-ab`  
Host session: `zcode-ISO74-orchestrator-ab` only.  
Other sessions (vrpcadcore worker, issue-70, issue-72 naming, desktop `zcode-host-local-1`) were not stopped or renamed.

Original input: `evidence/live/02-original-input.txt` (`KPR74-ORANGE-LANTERN`).

## What the real backend did

1. Direct `KAOLA_ZCODE_ENTRY=/Applications/ZCode.app/Contents/Resources/glm/zcode.cjs` with Homebrew node exits immediately: CLI cannot find bundled provider config (`glm/provider/zcode-builtin.json` vs app `Resources/config/provider/zcode-builtin.json`). Isolation used a project-local shim of that layout (`iso/.zcode-runtime/`). Not a global install change.
2. ZCode.app 3.12.3 `session/create` and `session/resume` reject `runtimeModel` (0.16.5 overlay). Adapter now retries create without that key and keeps the first resume error when overlay is unrecognized.
3. After shim + retry, **start was `state: ready`**, ACP `zcode-1`, and a real native id was emitted: `sess_2499f37a-fbbd-4046-a1c9-2d9aa896966d` (`09-pointer-filled.json`).
4. **Agent B live-attach** (read only `.kaola/delegator-host.json`, then `status`/`capture`, no second `start`): same session, `agent_alive: true` (`10-B-live-status.json`).
5. First handoff reached the app-server and **refused**: `Select a model before continuing` (`08-host-handoff-send.json`). Headless 3.12.3 Provider Registry is empty without `runtimeModel`, so no model reply quoted the token. Old-context confirmation after resume is therefore not available.
6. Exact `stop`: `stopped: true`, `residual_pids: []`, no `zcode-ISO74` leftover (`11-host-stop.json`, `14-leftover-after-final-stop.txt`).
7. `start --resume sess_2499f37a-…` then failed **`Session not found`** (`13-host-resume.json`). Exact stop `session/close` spent the native id. This is cannot-resume, not a cue to start a second Host.

## What is not claimed

- Fake-zcode-app-server is not this path and is not a pass.
- Real start → first prompt → model reply with token → A/B live attach → exact stop → `--resume sess_*` restoring that reply did **not** complete. The live-attach and stop-close facts above are the measured remainder.

## Foreign sessions after isolation

vrpcadcore `zcode-kaola-vrpcadcore-worker`, `claude-code-kaola-issue70-0918`, and `claude-code-KPR-i72-naming` were still running.
