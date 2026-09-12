# Code review — correctness (issue #22 / PR #23)

Frozen candidate: `69c87a871a5cae74f97d8f3f3967bd820536f0ab` (`cursor/issue-22-permit-oracle-d35d`)
Base: `origin/main` (`86a583105aaf67df9bd09b0bc3f36a54f365fc05`)
Focus: refute the claim that default `start` (no caller `--permission-mode`) now launches skip-all permission mode on ACP and PTY so `send --wait` does not hang on `session/request_permission` / a tool-approval TUI.

`templates/grok-golden/` is unchanged (empty diff vs `origin/main`). Skills were re-rendered. This review does not implement fixes.

## Claim under test

PR #23 / CHANGELOG: default `start` enables each platform's measured skip-all on **both** ACP and PTY. Issue #22 acceptance: every **working** platform/transport; workspace-trust flags alone do not satisfy; `permit` must not be the default path for ordinary tool use.

## What does work (not findings)

- Claude PTY: no-flag start assigns `permission_mode=bypassPermissions` (`scripts/kaola-tmux.sh:88-91`) and the adapter still forwards `--permission-mode "$permission_mode"`. Fake Claude runtime and `test-adapters.sh` now expect skip-all, not `auto`.
- Devin PTY: no-flag start assigns `dangerous` (not workspace-trust alone). Adapter still passes `--respect-workspace-trust false` in addition.
- Devin ACP: `mode=bypass` is a real agent skip value (`Bypass Permissions` / `auto-approved by bypass mode` in the installed `devin` binary), distinct from PTY `dangerous`.
- Kimi ACP: default start forwards `--mode yolo` and `ACP_SKIP_MODE` sets `session/set_config_option` `mode=yolo`. Mock `permission_unless_yolo` + `test-issue-22-bypass-all-approvals.py` PASS (7 tests, 1.029s).
- Cursor: PTY `--yolo` and `acp_command: cursor-agent --yolo acp` match the global CLI flag (`--yolo` alias for `--force` / Run Everything). `cursor-agent acp --help` has no subcommand `--yolo`; placing it before `acp` is the correct commander shape.
- Grok ACP: still no `configOptions` skip; live PoC recorded agent `always-approve` / zero `request_permission`. Claude ACP initialize remains `probe-eof`; skip `set_config_option` only runs after `state == ready`.

## Findings

### 1. bug — OpenCode default transport is ACP and still has no skip-all

- `platforms/opencode.yaml:21-22` — `default_transport: "acp"`, `acp_command: "opencode acp"`
- `scripts/kaola-acp.py:37-41` — `ACP_SKIP_MODE` omits `opencode`
- `scripts/kaola-tmux.sh:135-139` — default ACP start forwards `--mode` only for kimi/devin/claude
- `scripts/kaola-acp-holder.py:537-555` — `session/request_permission` is queued in `pending_permissions` and **not answered** (wait continues until `permit` / cancel / process exit)

**Concrete input:** `scripts/kaola-tmux.sh opencode start --repo <abs-git-root> --session <name>` with no `--permission-mode` and no `--transport` (manifest default ACP), then `send --text "write a file then run a shell" --wait`.

**What goes wrong:** OpenCode ACP still starts as `opencode acp` with no auto-approve. The installed OpenCode binary (1.x) implements `session/request_permission` (`connection.sendRequest(...session_request_permission...)`) and documents `--auto` as “auto-approve permissions that are not explicitly denied”. Holder still waits on unanswered permission RPCs, which is the original hang.

**How established:**
- Candidate YAML/code as cited; CHANGELOG itself lists “OpenCode PTY `--auto`” and does not claim an OpenCode ACP skip.
- `opencode acp --auto` exits 1 and prints ACP help (same rejection shape as `opencode acp --not-a-real-flag`).
- `opencode --auto acp` does **not** start ACP: it treats `acp` as a project directory (`Failed to change directory to .../acp`).
- Plain `opencode acp` starts (rc=0 on stdin close). So the measured TUI knob cannot be attached to the ACP argv the runner uses.
- `scripts/adapters/opencode.sh:42` adds `--auto` only on the PTY path.

Issue #22 required skip-all on the **working** default transport. OpenCode ACP initialize is live-verified PASS. Leaving ACP without a skip, while documenting “ACP command has no permission flag”, does not satisfy the claim that default `start` no longer hangs on `request_permission`.

### 2. bug — Kimi PTY start still has no skip-all argv

- `scripts/adapters/kimi-cli.sh:39-46` — launch argv is resume/continue + `--model` only
- `platforms/kimi-cli.yaml:14` — “PTY has no measured skip-all argv”

**Concrete input:** `scripts/kaola-tmux.sh kimi-cli start --transport pty --repo <abs-git-root> --session <name>` (no `--permission-mode`), then a tool-using `send`.

**What goes wrong:** Installed `kimi --help` documents `--auto`: “Start in Never Ask mode: never interrupts you; everything runs and is decided automatically.” `--yolo` is weaker (“Ask When Needed”). Neither flag is passed. Issue #22 listed Kimi PTY as not bypass-all and required both transports. The candidate’s “no measured skip-all argv” sentence is false against the current CLI.

**How established:** read adapter + manifest at the frozen SHA; ran `kimi --help` on the local binary (`kimi acp` has no `--auto`; the TTY command does). ACP `mode=yolo` does not apply to this PTY argv path (`kaola-tmux.sh` ACP exec is skipped when `--transport pty`).

### 3. bug — Grok PTY start still has no skip-all argv

- `scripts/adapters/grok.sh:51-59` — launch remains `--cwd <repo> --minimal` + model/effort
- `platforms/grok.yaml:14` — launch summary unchanged; no `--always-approve`

**Concrete input:** `scripts/kaola-tmux.sh grok start --transport pty --repo <abs-git-root> --session <name>` (no `--permission-mode`).

**What goes wrong:** Installed `grok --help` (default TUI command) documents `--always-approve` (“Auto-approve all tool executions”) and `--permission-mode` including `bypassPermissions`. Neither is on the PTY launch. Default Grok transport is ACP (already always-approve in the PoC), but issue #22 explicitly includes `--transport pty` as a working surface.

**How established:** adapter/manifest at frozen SHA; `grok --help` on the local binary. Grok adapter never reads `permission_mode` (core only rewrites that variable for claude-code/devin).

### 4. suspicion — Grok ACP skip flag exists and is unused

- `platforms/grok.yaml:22` — `acp_command: "grok agent stdio"`
- `grok agent --help` lists `--always-approve`

PoC live evidence was zero `request_permission` without the flag, so `send --wait` may still complete today. Issue #22 asked to set a skip option if one appears. Not admitted as a hang bug.

## Tests vs the claim

`tests/contract/test-issue-22-bypass-all-approvals.py` (and the duplicate class in `test-acp-contract.py`) only assert:
- Devin/Claude PTY source tokens
- Kimi ACP `mode=yolo` + mock send without permit

The file’s own docstring says Cursor/Devin/OpenCode ACP mode values are unmeasured and are not asserted. That matches the **implementation gap** on OpenCode ACP: the contract was narrowed so default OpenCode `start` can stay `opencode acp` and still go green. `./scripts/validate.sh` was not re-run in this review; the issue-22 unit file PASS does not cover findings 1–3.

## Conclusion

The claim is **not** true for every working platform/transport. Claude/Devin PTY, Kimi ACP, Cursor `--yolo`, and Devin ACP `bypass` are real skip knobs. Default OpenCode `start` (ACP) still has no skip-all, so `send --wait` can still sit on unanswered `session/request_permission`. Explicit Kimi and Grok PTY starts also omit measured skip-all argv (`kimi --auto`, `grok --always-approve`).
