# Part B live evidence — Kimi CLI (`kimi acp`, v0.41.0)

Date: 2026-09-11. Host: macOS arm64. Worktree: `.kw/worktrees/bundle-15`.
Record root: `${TMPDIR}/kaola-501/kimi-cli/<session>/<sha256(repo)[:16]>/`.
Auth: already logged in (interactive account).

## preflight

`kaola-acp.py kimi-cli preflight --command "kimi acp"` → `protocol_version: 1`,
`login_required: false`, `session_probe: session_0ef19d72-…` created + closed.
`agent_info: {name: "Kimi Code CLI", version: "0.41.0"}` (real agentInfo — unlike Grok).
`auth_methods`: one `terminal`-type method (`kimi --login`, device-code flow).
Capabilities: `prompt/cancel/permission/set_config_option/load_session: true`;
`resume/list/close: false` — same shape as Grok.

## §10.1 scenario results

1. **plain prompt → send --wait** — PASS. "Reply with exactly PONG" →
   `final_text: "PONG"`, `stop_reason: end_turn`, `outcome: turn_completed`,
   `mutation_status: completed`, `duration_ms: 9444`, `thinking_chars: 47`,
   `context_usage: {used: 22113, size: 1048576}` — Kimi emits `usage_update`
   (Grok did not).
2. **permission → pending_permissions → permit** — NOT TRIGGERED.
   Prompt `create poc-perm-kimi.txt` + `touch /tmp/kimi-perm-shell.txt` executed
   both actions (`tool_calls: {edit:1, execute:1}`, `files_changed:1`,
   `commands_run:1`) with zero `session/request_permission` events — despite
   `modes.currentModeId: "default"` whose description says "Manual approvals".
   Quirk recorded: Kimi's default mode does not emit ACP permission requests for
   in-workspace file writes or shell commands. `permit` path verified in Part A.
3. **long task → prompt_timeout → cancel → cancelled** — PASS.
   `wait --timeout 3` → `prompt_timeout`; `cancel --timeout 15` →
   `turn_canceled`, `stop_reason: cancelled`, `mutation_status: completed`.
4. **stop non-force → residual_pids []** — PASS. `agent_exit_code: 0`
   (stdin EOF per §7.6); no residual pids.
5. **--resume / --continue** — PASS. `start --resume session_06fbb1b2-…` →
   `session/load` → `ready`, same `acp_session_id`; context retained
   ("what string did I ask earlier" → "PONG"). `--continue` →
   `continue-unsupported` (no `session/list`), no auto-create.
6. **login_required path** — PRECONDITION-NOT-MET (already authenticated);
   preflight reports `login_required: false` and the terminal `login` method.
7. **acp spawn failure → not_started → pty resend** — PASS (transport-agnostic
   code path; the `not_started` receipt is identical to Grok's: `acp-spawn-failed`/
   `agent-not-running` → `mutation_status: not_started`, `mutation_performed:
   false`; pty resend verified live under Grok, same mechanism).
8. **duplicate-prompt-warning / transport-mismatch** — PASS (acp side):
   identical prompt re-sent → `duplicate-prompt-warning` with
   `previous_transport: acp`, `previous_mutation_status: completed`,
   `previous_stop_reason: end_turn`. `transport-mismatch` verified under Grok
   (name-based check, identical code path).
9. **second send during active turn → prompt-in-progress** — PASS:
   `error.code: prompt-in-progress`, `outcome: in_progress`.
10. **holder killed → holder-lost + unknown → stop --force** — PASS.
    `kill -9 <holder>` mid-turn → `observe`: `outcome: holder_lost`,
    `mutation_status: unknown`, `error.code: holder-lost`. `stop --force` →
    `stopped: true`, `holder_lost: true`, `residual_pids: []`; agent pid gone.
11. **--repo not canonical git root** — PASS. `--repo <root>/scripts` →
    `--repo must name the Git root: <root>`, exit 2 — same refusal as v1.
12. **same session name, two repos** — PASS. `kpr-poc-kimi` in worktree and
    `/tmp/kpr-repo3` → distinct record dirs (`17afc9a6…`, `c17db59c…`) and
    session ids; no collision.
13. **configOptions ids (Kimi)** — CAPTURED in `record.session_meta`:
    `configOptions` carries three select options —
    - `model` (category `model`): `kimi-code/kimi-for-coding`,
      `kimi-code/kimi-for-coding-highspeed`, `kimi-code/k3` (current),
      `kimi-code/k3-256k`
    - `thinking` (category `thought_level`): `low`, `high`, `max` (current)
    - `mode` (category `mode`): `default` (current), `plan`, `auto`, `yolo`
    plus `modes.availableModes` / `currentModeId: "default"`.
    Candidate manifest keys: `acp_model_config_id: "model"`, effort via
    `session/set_config_option {configId: "thinking"}`, approval mode via
    `configId: "mode"` or `session/set_mode`.

## Kimi-specific notes for the design

- Kimi answers promptly and emits `usage_update` (context meter) — Grok does not.
- `agentInfo` present → no `--version` fallback needed.
- Permission gating observed: none at `mode=default` for workspace writes /
  shell exec. If a deployment needs ACP permission prompts, `mode` configOptions
  exists but `default` is already the "manual approvals" mode — permission
  prompts appear not to be wired through `session/request_permission` in 0.41.0.
- `session/load` works for resume; `session/list`, `session/resume`,
  `session/close` absent — identical capability shape to Grok.
