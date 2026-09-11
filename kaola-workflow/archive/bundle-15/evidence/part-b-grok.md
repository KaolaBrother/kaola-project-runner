# Part B live evidence — Grok (`grok agent stdio`, v1.0.25)

Date: 2026-09-11. Host: macOS arm64. Worktree: `.kw/worktrees/bundle-15`.
Record root: `${TMPDIR}/kaola-501/grok/<session>/<sha256(repo)[:16]>/`.
Grok build: 1.0.25 (f7e67d6988e2). Auth: cached token (`~/.grok/auth.json`) — already logged in.

## preflight

`kaola-acp.py grok preflight` → `protocol_version: 1`, `login_required: false`,
`session_probe: 01a09102-8c80-7181-851b-f92edf7f9ea1` (real session created + closed).
`agent_info: {}` (Grok returns no agentInfo). `auth_methods`: `cached_token`, `grok.com`.
Capabilities: `prompt/cancel/permission/set_config_option/load_session: true`;
`resume/list/close: false`. `_meta.x.ai/capabilities.toolOverrides` present.

## §10.1 scenario results

1. **plain prompt → send --wait** — PASS. "Reply with exactly PONG" →
   `final_text: "PONG"`, `stop_reason: end_turn`, `outcome: turn_completed`,
   `mutation_status: completed`, `duration_ms: 3209`, `event_cursor: 70`,
   `thinking_chars: 129`, `context_usage: null` (no `usage_update` emitted).
2. **permission → pending_permissions → permit** — NOT TRIGGERED by Grok.
   `create file` and `run shell command` prompts both executed immediately
   (`tool_calls: {edit: 1}`, `side_effects.files_changed: 1`; file verified on disk).
   Zero `session/request_permission` events in events.jsonl. Grok TUI shows
   `always-approve` mode; its ACP surface auto-approves tool calls. The
   `permit` path is verified by the offline contract suite (Part A).
3. **long task → wait --timeout → prompt_timeout → cancel → cancelled** — PASS.
   500-line-poem prompt → `wait --timeout 3` → `outcome: prompt_timeout`,
   `mutation_status: accepted`; `cancel` → `turn_canceled`, `stop_reason: cancelled`,
   `mutation_status: completed`.
4. **stop non-force → residual_pids []** — PASS. `stop` → `stopped: true`,
   `residual_pids: []`, `agent_exit_code: 0` (Grok exits on stdin EOF per §7.6 step 4;
   no signals needed). holder exited, socket cleaned.
5. **--resume / --continue** — PASS. `start --resume <id>` → `session/load` →
   `state: ready`, same `acp_session_id` (`01a09102-bcd3-…`), context retained
   ("what was the string" → "PONG"). `start --continue` → `continue-unsupported`
   (agent lacks `session/list`; no auto-create — correct per design).
6. **not logged in → login_required → pty login → acp** — PRECONDITION-NOT-MET.
   Grok was already authenticated; preflight reports `login_required: false`.
   The auth-required branch is covered by the mock `auth_required` scenario and
   `authMethods` are surfaced in the preflight receipt.
7. **acp spawn failure → not_started → resend over pty** — PASS.
   `--command "false --definitely-not-acp"` → `acp-initialize-failed` (agent exited);
   subsequent `send` → `mutation_status: not_started`, `mutation_performed: false`.
   Same prompt over pty (`kaola-tmux.sh grok start/send kpr-poc-pty`) →
   `mutation_performed: true`, "PONG-PTY" visible in frame. (Note: first pty send
   raced TUI init — existing v1 characteristic, resend landed.)
8. **duplicate-prompt-warning** — PASS (acp side). Re-sending the identical prompt
   → `duplicate_warning: {code: duplicate-prompt-warning, previous_transport: acp,
   previous_mutation_status: completed, previous_stop_reason: end_turn,
   previous_written_at: …}`. While the pty session was alive, `start` over acp with
   the same name → `error.code: transport-mismatch{other_transport: pty}`.
   GAP for production: cross-transport fingerprint matching needs the pty path to
   journal `last_prompt` into the shared record — not wired in PoC scope.
9. **second send during active turn → prompt-in-progress** — PASS.
   `error.code: prompt-in-progress`, `outcome: in_progress`; turn unaffected.
10. **holder killed → holder-lost + mutation_status unknown → stop --force** — PASS.
    `kill -9 <holder>` mid-turn → `observe` → `outcome: holder_lost`,
    `mutation_status: unknown`, `mutation_performed: null` (never `not_started`).
    Agent stayed alive orphaned; `stop --force` → `stopped: true`,
    `residual_pids: []` (Grok self-exited on stdin EOF before SIGKILL needed).
11. **--repo not canonical git root** — PASS. `--repo <root>/scripts` →
    `--repo must name the Git root: <root>` — identical refusal text as v1.
12. **same session name, two repos** — PASS. `kpr-poc-grok` in worktree and in
    `/tmp/kpr-repo2` → distinct record dirs (`17afc9a6…`, `c7263734…`), distinct
    `acp_session_id`s, both `ready`; records do not collide.
13. **configOptions ids (Grok)** — CAPTURED in `record.session_meta.configOptions`:
    - `model` (category `model`): `grok-4.6` (current), `grok-4.5`
    - `reasoning_effort` (category `thought_level`): `xhigh` (current), `high`,
      `medium`, `low`
    `_meta.x.ai/sessionConfig.options` carries the same model + mode ids.
    Candidate manifest keys: `acp_model_config_id: "model"`,
    effort via `session/set_config_option {configId: "reasoning_effort"}`.

## Grok-specific notes for the design

- `session_info_update` is a Grok extension variant (title only) — counted by the
  holder's unknown-variant path, not an error.
- `available_commands_update` arrives repeatedly (12×) carrying `_meta.tools`
  (~25 tools incl. `run_terminal_command`, `search_replace`, `enter_plan_mode`).
- `usage_update` was not emitted → `context_usage: null`.
- `agentInfo` absent → `agent_info: {}`; version falls back to `grok --version`.
- Grok answers `session/prompt` with `stopReason` and streams chunks; the whole
  exchange is also mirrored through its leader socket — no issue observed.
