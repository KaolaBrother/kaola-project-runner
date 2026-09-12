# Trust-boundary review: PR #23 / Issue #22

- Frozen SHA: `69c87a871a5cae74f97d8f3f3967bd820536f0ab`
- Branch: `cursor/issue-22-permit-oracle-d35d`
- Base: `origin/main` (`86a583105aaf67df9bd09b0bc3f36a54f365fc05`)
- Focus: eval/interpolation, Issue #7 send/stop gates, `--permission-mode` ignore/injection, process-time auto-permit, golden freeze, generated Skills, permit path
- Method: read `origin/main...69c87a8` on the isolated worktree at `.kw/worktrees/issue-22`; compared holder/relay/observation (unchanged); hashed Skill copies vs `scripts/`; ran `./scripts/render-skills.py --check`

## Checklist

### 1. Does the candidate eval or interpolate `permission_mode` / `mode` into a shell?

**No production eval of the value.** `scripts/` has no `eval` and no `shell=True`.

PTY launch still builds `exec …` for the pane with `printf %q` per argv element, then `tmux send-keys -l` (`scripts/kaola-tmux.sh:502`). `permission_mode` is only appended as an argv element after an allowlist (`:167-171`) via `ADAPTER_LAUNCH_ARGS+=(--permission-mode "$permission_mode")` in the Claude/Devin adapters. Defaults assigned at `:88-93` are the literals `bypassPermissions` and `dangerous`.

ACP start forwards `--mode "$permission_mode"` in a bash array and `exec "${acp_args[@]}"` (`:130-144`). `kaola-acp.py` then `json.dumps` the value into a Unix-socket `set_config_option` (`:141-142`, `:427`). Holder spawn of `acp_command` is `shlex.split` + `Popen` without a shell (`kaola-acp-holder.py:189-191`). Cursor’s new command is the static YAML string `cursor-agent --yolo acp`.

Concrete non-eval input: `--permission-mode '$(reboot)'` on PTY dies at the allowlist; on ACP it is one argv string then JSON, not a second shell parse.

### 2. Does skip expand into a send/stop communication gate (Issue #7 non-goal except this start-time bypass)?

**No.** Diff does not touch `kaola-pane-relay.py`, `kaola-observation.py`, send/stop cases, or evidence-flag authorization. `native_approval` remains observe-only (`kaola-tmux.sh:266`). Adapter `activity_hint` classifiers are unchanged. Issue #7 decision doc is unchanged.

The only “no waiting-human” change is the **fake** Claude fixture in `tests/contract/test-claude-code-runtime.sh`, which stops painting a tool-approval TUI when argv contains `bypassPermissions|dontAsk`. Production send/stop still do not branch on approval evidence.

Start-time skip is launch argv / ACP `session/set_config_option` only — the Issue #22 exception, not a process-time gate.

### 3. Caller `--permission-mode` ignored or injected as a terminal control?

**PTY: caller wins; controls cannot pass the allowlist.** `:88-93` assign skip only when `permission_mode_given != true`. Model still has an explicit C0/DEL check (`:161-165`); permission mode is a closed token set (`:167-171`). Tokens in those sets contain no C0/DEL.

**ACP: caller `--mode` is forwarded in the array and JSON-encoded, not written to a PTY.** Default skip is applied only when the caller did not pass the flag (`:130-139`) or, inside Python, when `args.mode` is falsy (`kaola-acp.py:403`). Non-empty `--permission-mode auto` on Claude/Devin ACP is sent as `mode=auto` (caller wins). Cursor/OpenCode/Kimi PTY still die `permission mode is platform-specific` (`:159`) because that check is on the PTY path after ACP `exec`.

**Suspicion (empty string only):** `mode_value = args.mode or ACP_SKIP_MODE.get(args.platform)` (`kaola-acp.py:403`). ACP `start --permission-mode ''` sets `permission_mode_given=true` and `--mode ""`, then Python treats `""` as absent and still sets skip (`bypassPermissions` / `bypass` / `yolo`). PTY empty string fails the allowlist. Established by reading those two sites; not a control-char injection.

ACP still `exec`s before the PTY allowlist (`:144` then `:159-171`). That order is **pre-existing** on `origin/main`. This candidate makes unvalidated `--mode` actually reach `set_config_option` for Claude and Devin (previously only Kimi mapped `mode`; others hit empty `config_id`). The value still never goes through pane `send-keys` / relay PTY write. Not admitted as a PTY terminal-control defect.

Cursor `--yolo` and OpenCode `--auto` are unconditional launch flags with no `--permission-mode` off switch. That matches Issue #22 (those platforms have no permission-mode flag), not ignored caller input.

### 4. Auto-answer `permit` at process time (wrong layer)?

**No.** `scripts/kaola-acp-holder.py` is byte-identical to `origin/main`. `on_agent_request` for `session/request_permission` still queues `pending_permissions` and returns without a client result (`:537-555`). `op_permit` is still the only selected/cancelled reply (`:850-878`). `kaola-acp.py` `permit` still sockets `op=permit` (`:526-529`). Send/wait do not call permit.

Mock `permission_unless_yolo` (`tests/contract/mock-acp-agent.py`) simulates the **agent** omitting `request_permission` after `mode=yolo`. That is the start-time layer Issue #22 asked for, not holder auto-permit.

### 5. `templates/grok-golden/` changed?

**No.** `git diff origin/main...HEAD -- templates/grok-golden` is empty. `platforms/grok.yaml` is also unchanged.

### 6. Hand-edited `skills/` instead of generating?

**No.** `./scripts/render-skills.py --check` → `render-skills: PASS (6 Skills)`. SHA-256 of `scripts/kaola-tmux.sh`, `scripts/kaola-acp.py`, and the touched adapters matches every Skill copy. Cursor `SKILL.md` only inlines the new manifest `acp_command`.

### 7. Permit path weakened so a still-emitted `request_permission` cannot be answered?

**No.** Holder permit/cancel/stop-cancel paths are unmodified. `tests/contract/test-acp-contract.py::test_multiple_concurrent_permissions` still requires `permit --request-id` for three pending requests. Issue #22 tests assert default yolo avoids permit; they do not delete the permit command.

## Observations (not defects)

- OpenCode ACP `acp_command` remains `opencode acp` with no skip flag; the manifest says `configOptions.mode` is agent identity. That is a completeness gap vs “every working ACP transport,” not a trust-boundary regression: holder will still queue `request_permission` and `permit` still answers it.
- Claude ACP skip still runs only after `state == ready` (`kaola-acp.py:399-403`), so `probe-eof` initialize cannot fake a working bypass.

## Conclusion

The candidate keeps prompts on the existing literal/array/JSON paths, does not eval `permission_mode`, does not add send/stop approval gates, does not auto-permit in the holder, leaves golden Grok frozen, and re-renders Skills. Default skip is start-time knobs (PTY argv / ACP `set_config_option` / Cursor `--yolo`). Residual `request_permission` can still be `permit`ed.

**Verdict: pass** (no shown trust-boundary defect).
