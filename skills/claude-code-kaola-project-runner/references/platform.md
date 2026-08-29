# Claude Code adapter

- Platform ID: `claude-code`
- Default binary: `claude`
- Binary override: `CLAUDE_BIN`
- Default tmux session prefix: `claude-code-kaola`
- Continue: `--continue`
- Exact resume: `--resume <session-id>`
- Recurring execution: `unsupported`

## Preflight

Require workflow-next and kaola-workflow-finalize in the nearest project or user Claude command carrier; do not install them automatically.

Preflight is read-only. Missing or untrusted Kaola runtime surfaces produce a typed refusal and a
repair hint; the Runner never installs, upgrades, adopts, or rewrites runtime configuration.

## Launch

Launch claude from the canonical repository root.

Use `scripts/runtime-tmux.sh` for every preflight, start, status, capture, send, and stop operation.
Do not reconstruct ownership checks from process names or fuzzy tmux matches.

## Recurring boundary

Do not map goals, background agents, or other Claude features to recurring execution until a same-main-conversation lifecycle is live-proven.

---

# Claude Code TUI control

Use `scripts/runtime-tmux.sh` for the CLI control plane. It marks sessions it creates with tmux environment
metadata and refuses mutation when ownership, repository, TUI identity, or idle state is uncertain.

## Preflight

```bash
scripts/runtime-tmux.sh preflight --repo "$REPO" --session "$SESSION"
```

Preflight requires:

- an absolute existing Git repository root;
- available `tmux`, `claude`, `git`, and `python3` executables;
- the live adapter preflight result discovering both `workflow-next` and `kaola-workflow-finalize`.

The discovered skill may come from commands, a plugin, or another current Claude Code source. Do not use
a runtime-native catalog listing alone as the availability test.

## Start or resume

Fresh main conversation:

```bash
scripts/runtime-tmux.sh start --repo "$REPO" --session "$SESSION"
```

Continue the latest Claude Code conversation for this repository:

```bash
scripts/runtime-tmux.sh start --repo "$REPO" --session "$SESSION" --continue
```

Resume an exact Claude Code conversation:

```bash
scripts/runtime-tmux.sh start --repo "$REPO" --session "$SESSION" --resume "$RUNTIME_SESSION_ID"
```

Launch claude from the canonical repository root. Preserve terminal evidence so it remains capturable. If the exact session
already exists, start succeeds only when it is already owned by this runner and bound to the same
repository; otherwise it fails closed.

## Observe

```bash
scripts/runtime-tmux.sh status --repo "$REPO" --session "$SESSION"
scripts/runtime-tmux.sh capture --repo "$REPO" --session "$SESSION" --lines 120
```

Interpret `activity` conservatively:

- `busy`: wait and observe later; do not inject.
- `idle`: input may be sent if every ownership and identity field is also true.
- `unknown`: inspect the capture and do not inject until the uncertainty is resolved.

`pane_current_command` may name a launcher or runtime process. The helper uses the exact cwd, its tmux
ownership marker, and the pane title together instead of assuming the executable name is `claude`.
Status also reports local Git branch, HEAD, cleanliness, upstream, and locally known ahead/behind
counts. Read [status-monitoring.md](status-monitoring.md) before deciding the project is complete.

## Send literal input

```bash
scripts/runtime-tmux.sh send --repo "$REPO" --session "$SESSION" --text "$PROMPT"
```

For a multiline or large prompt, use stdin:

```bash
scripts/runtime-tmux.sh send --repo "$REPO" --session "$SESSION" < prompt.txt
```

The helper pastes literal bytes and sends Enter separately. Shell metacharacters in the prompt are
not executed by the tmux pane's shell.

## Stop

```bash
scripts/runtime-tmux.sh stop --repo "$REPO" --session "$SESSION"
```

This only sends `/exit` to an owned idle Claude Code session. If it does not exit promptly, report
`quit-pending` and inspect it. `--force` may kill the exact owned session only when the user has
explicitly authorized forced termination. An absent session is already stopped; do not inspect or
affect other sessions.
