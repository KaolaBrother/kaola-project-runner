# Droid live verification — 2026-09-17

## Environment

Droid CLI `0.220.0` (`/Users/ylpromax5/.local/bin/droid`; ACP `agentInfo` `@factory/cli` "Factory
Droid" 0.220.0, protocol 1) on macOS, tmux 3.7b, Python 3.13.12, already authenticated. Scratch
repository `/tmp/kaola-droid-live/repo` (one commit `e43ab0a`, clean tree before each gate). All
receipts are schema version 3. Every step ran the real CLI and the real model through the shared
entry point `./scripts/kaola-tmux.sh droid …` from the workflow/bundle-58 worktree, exactly as the
README documents, with no installed Skill. Session names follow the platform prefix
(`droid-kaola-*`).

## Gate 1 — ACP (default transport, real droid)

- `preflight` (session `droid-kaola-live-acp`): `ready`; `login_required: false`; auth methods
  `device-pairing`, `factory-api-key`. The config options are declared in the `session/new` result,
  never `initialize`: `autonomy_level` (current `auto-high`), `model` (current `gpt-5.6-sol`),
  `reasoning_effort` (current `high`). Capabilities: `prompt`, `cancel`, `permission`, `resume`,
  `load_session`, `list`, `set_config_option`. Nothing gated communication.
- `start` with **no `--transport` flag**: `transport {selected: acp, default: acp, reason:
  manifest-default}`; `state: ready`; `acp_session_id:
  37f161c2-3061-4a49-8a8c-7da909d8a1cb`; holder 64812, agent 64813. `config_application`:
  `model {applied: true, config_id: model, value: auto}` — the native default model id is
  `gpt-5.6-sol`, not `auto`, so the Runner applies Auto Model explicitly; `mode {applied: true,
  config_id: autonomy_level, value: auto-high}` — the default ACP session is already auto-high;
  `effort {applied: false, reason: no-resolved-value}` (no invented effort); `fast {applied:
  false, reason: no-advertised-config-option}`. The post-stop `status` record shows
  `session_meta` model `currentValue: auto`.
- `send "Reply with exactly: pong"`: `outcome: turn_completed`, `stop_reason: end_turn`,
  `final_text: "pong"`, `pending_permissions: []`, 0 tool calls, 6713 ms.
- `send "Create a file named live-acp.txt containing the word ok, then reply done."`:
  `outcome: turn_completed`, `stop_reason: end_turn`, `final_text: "done"`,
  **`pending_permissions: []` on a file-writing turn** (bypass evidence), 1 `execute` tool call
  (0 failed), `commands_run: 1`; `/tmp/kaola-droid-live/repo/live-acp.txt` exists containing `ok`.
- `stop`: `stopped: true`, `agent_exit_code: 0`, **`residual_pids: []`**, `swept_child_pgids: []`;
  `status` afterwards: `outcome: stopped`, `agent_alive: false`. `ps` sweeps: pids 64812/64813
  gone, no `droid exec --output-format acp` process left.
- Resume: `start --resume 37f161c2-3061-4a49-8a8c-7da909d8a1cb` returned `state: ready` on the
  **same native session id**, with `model_selection.source: resume-preserved` (saved native
  selection kept; only `autonomy_level: auto-high` re-applied). One history probe ("What is the
  name of the file you created in this session earlier?") answered `live-acp.txt` — the
  pre-stop conversation survived the stop/resume. `stop` again returned `residual_pids: []`.

## Gate 2 — PTY (real droid TUI in tmux)

- `start --transport pty` (session `droid-kaola-live-pty`): `result: started`,
  `transport {selected: pty, reason: caller-override}`, relay `managed: true`, `tui_detected:
  true`, pane title `⛬ Droid`. Launch args in the receipt: child process
  `droid --settings <TMPDIR>/kpr-droid-settings.OmcXUy --skip-permissions-unsafe`
  (`--skip-permissions-unsafe` present as the default bypassPermissions). The overlay file
  contains exactly `{"model": "auto"}` — no `reasoningEffort` key — and lives in the run temp
  area as a process-scoped merge; `~/.factory` is never written by the Runner.
- First launch in the untrusted scratch folder showed the native folder-trust dialog
  (信任此文件夹？). The controlling agent selected option 1 with one `key enter`. The native
  CLI itself then persisted the folder in `~/.factory/settings.json` `trustedFolders` and its
  own `logoAnimation` preference — a native act by droid, identical to a human user accepting the
  dialog; the Runner wrote nothing under `~/.factory`.
- Footer evidence after trust: `Auto (高) · 允许所有命令` (autonomy auto-high, all commands
  allowed — `--skip-permissions-unsafe` in effect) and `Auto Model (动态)` (model auto from the
  overlay). The TUI also prints a one-time informational note about `--skip-permissions-unsafe`;
  it never gated a turn.
- Readiness tuning: with the pre-tune adapter, `observe` on the ready composer reported
  `activity_hint: unknown` — the real composer row is the boxed `│ >` prompt (no bare `❯/›/>`
  row), and the generation spinner reads `(Press ESC to stop)`, not "esc to interrupt".
  `scripts/adapters/droid.sh` `adapter_activity_hint` was tuned from these live facts: busy gains
  `esc to stop`, idle gains `^│[[:space:]]*>` (busy wins first, so the always-present composer
  row reports idle only once the spinner is gone). Re-rendered; `render-skills.py --check` PASS;
  `validate.sh` PASS (exit 0); after the tune, `observe` on the idle composer reports
  `activity_hint: idle`.
- `send "Reply with exactly: pong"`: capture shows `⛬ pong`.
- `send "Create a file named live-pty.txt containing the word ok, then reply done."`: the
  transcript shows the ApplyPatch tool creating `live-pty.txt` (`↳ 成功。文件已创建。 (+1 added)`,
  preview `1 │ ok`), reply `⛬ done`; **no permission prompt appeared**; the file exists in the
  scratch repo containing `ok`.
- `stop` (quit text `/quit`): `result: stopped`; `status` afterwards `absent`; `tmux ls` shows no
  `droid-kaola-*` session; pane/relay/child pids gone; `ps` sweep clean.
- Resume: `start --continue` in fresh session `droid-kaola-live-pty-cont` launched child
  `droid --resume --last --skip-permissions-unsafe` (no overlay — resume preserves the saved
  session selection). The TUI reopened showing the full prior conversation (the pong turn and
  the live-pty.txt turn). One history probe answered `⛬ live-pty.txt` — PTY `--continue` resumed
  the previous conversation with history. `stop` clean again.

## Residue and safety sweep

- Both ACP stop receipts: `residual_pids: []`; both PTY sessions stopped through the Runner's
  own `stop` (`/quit`), and the resume sessions likewise.
- `tmux ls` afterwards lists only the pre-existing foreign sessions (`droid-daemon`, `esc|a|b`,
  `vpn-admin-test`); no `kaola-pane-relay` process for any gate session; no droid process
  referencing the scratch repo or the `kpr-droid-settings` overlay; no
  `droid exec --output-format acp` left.
- The live Factory `droid daemon` tree (`droid daemon` and its `--input-format stream-jsonrpc`
  children) belongs to the user's session; it was never touched and never counted as residue.
- `~/.factory`: the Runner never wrote there — the model overlay is a process-scoped
  `--settings` file under TMPDIR. The only `~/.factory` changes during the gates came from the
  native droid CLI itself (folder-trust acceptance, its own preference and history persistence),
  the same writes a human user driving the same TUI produces.

## Conclusion

- ACP gate **PASS**; PTY gate **PASS** (both against the real droid 0.220.0 with real model
  turns: structured `end_turn` receipts with zero permission requests on ACP, and native-TUI
  turns with bypass active on PTY; clean stop/status/resume and zero residue on both).
- `default_transport: acp` **confirmed**: the native ACP agent completed both probe turns with
  structured receipts and no permission prompts, needs no bridge, and exposes resume; PTY
  remains a fully working explicit fallback whose only observed gap (idle composer detection)
  is fixed by the adapter tuning recorded above.
