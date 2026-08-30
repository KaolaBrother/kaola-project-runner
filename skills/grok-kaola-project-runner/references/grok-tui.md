# Grok TUI control

Use `scripts/grok-tmux.sh` for the CLI control plane. It marks sessions it creates with tmux environment
metadata and refuses mutation when ownership, repository, TUI identity, or idle state is uncertain.

## Preflight

```bash
scripts/grok-tmux.sh preflight --repo "$REPO" --session "$SESSION"
```

Preflight requires:

- an absolute existing Git repository root;
- available `tmux`, `grok`, `git`, and `python3` executables;
- `grok inspect --json` discovering both `workflow-next` and `kaola-workflow-finalize`.

The discovered skill may come from commands, a plugin, or another current Grok source. Do not use
`grok plugin list` alone as the availability test.

## Start or resume

Fresh main conversation:

```bash
scripts/grok-tmux.sh start --repo "$REPO" --session "$SESSION"
```

Continue the latest Grok conversation for this repository:

```bash
scripts/grok-tmux.sh start --repo "$REPO" --session "$SESSION" --continue
```

Resume an exact Grok conversation:

```bash
scripts/grok-tmux.sh start --repo "$REPO" --session "$SESSION" --resume "$GROK_SESSION_ID"
```

The helper starts Grok with `--minimal` so terminal evidence remains capturable. If the exact session
already exists, start succeeds only when it is already owned by this runner and bound to the same
repository; otherwise it fails closed.

Mutation commands use the schema-v2 snapshot and editor guards in [transport.md](transport.md).

## Observe

```bash
scripts/grok-tmux.sh status --repo "$REPO" --session "$SESSION"
scripts/grok-tmux.sh capture --repo "$REPO" --session "$SESSION" --lines 120
```

Interpret `activity` conservatively:

- `busy`: wait and observe later; do not inject.
- `idle`: input may be sent if every ownership and identity field is also true.
- `unknown`: inspect the capture and do not inject until the uncertainty is resolved.

`pane_current_command` may be `node` for the Grok launcher. The helper uses the exact cwd, its tmux
ownership marker, and the pane title together instead of assuming the executable name is `grok`.
Status also reports local Git branch, HEAD, cleanliness, upstream, and locally known ahead/behind
counts. Read [status-monitoring.md](status-monitoring.md) before deciding the project is complete.

## Send literal input

```bash
scripts/grok-tmux.sh send --repo "$REPO" --session "$SESSION" \
  --if-snapshot "$SNAPSHOT_ID" --require-empty-editor --text "$PROMPT"
```

For a multiline or large prompt, use stdin:

```bash
scripts/grok-tmux.sh send --repo "$REPO" --session "$SESSION" \
  --if-snapshot "$SNAPSHOT_ID" --require-empty-editor < prompt.txt
```

The helper pastes literal bytes and sends Enter separately. Shell metacharacters in the prompt are
not executed by the tmux pane's shell.

## Stop

```bash
scripts/grok-tmux.sh stop --repo "$REPO" --session "$SESSION" \
  --if-snapshot "$SNAPSHOT_ID"
```

This only sends `/quit` to an owned idle Grok session. If it does not exit promptly, report
`quit-pending` and inspect it. `--force` may kill the exact owned session only when the user has
explicitly authorized forced termination. An absent session is already stopped; do not inspect or
affect other sessions.
