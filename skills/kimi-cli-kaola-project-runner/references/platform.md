# Kimi CLI adapter

- Platform ID: `kimi-cli`
- Default binary: `kimi`
- Binary override: `KIMI_BIN`
- Default tmux session prefix: `kimi-cli-kaola`
- Continue: `--continue`
- Exact resume: `--session <session-id>`

## Preflight

Require workflow-next and kaola-workflow-finalize in project or user Kimi Skill carriers and validate current Kimi configuration health.

Preflight is read-only. Missing or untrusted Kaola runtime surfaces produce a typed refusal and a
repair hint; the Runner never installs, upgrades, adopts, or rewrites runtime configuration.

## Launch

Launch kimi from the canonical repository root.

Use `scripts/runtime-tmux.sh` for every preflight, start, observe, status, capture, send, answer, and
stop operation. Read [transport.md](transport.md) before any action that can change the runtime.
Do not reconstruct ownership checks from process names or fuzzy tmux matches.

## Scheduling carriers

Use the caller-selected one-shot, Codex heartbeat, or live-verified runtime-native carrier described in [scheduling.md](scheduling.md).

This adapter capability does not gate external Codex scheduling. The human or invoking agent chooses
the execution carrier and follows [scheduling.md](scheduling.md) for each firing.

---

# Kimi CLI TUI control

Use `scripts/runtime-tmux.sh` for the CLI control plane. It marks sessions it creates with tmux environment
metadata and refuses mutation when ownership, repository, TUI identity, or idle state is uncertain.

## Preflight

```bash
scripts/runtime-tmux.sh preflight --repo "$REPO" --session "$SESSION"
```

Preflight requires:

- an absolute existing Git repository root;
- available `tmux`, `kimi`, `git`, and `python3` executables;
- the live adapter preflight result discovering both `workflow-next` and `kaola-workflow-finalize`.

The discovered skill may come from commands, a plugin, or another current Kimi CLI source. Do not use
a runtime-native catalog listing alone as the availability test.

## Start or resume

Fresh main conversation:

```bash
scripts/runtime-tmux.sh start --repo "$REPO" --session "$SESSION"
```

Continue the latest Kimi CLI conversation for this repository:

```bash
scripts/runtime-tmux.sh start --repo "$REPO" --session "$SESSION" --continue
```

Resume an exact Kimi CLI conversation:

```bash
scripts/runtime-tmux.sh start --repo "$REPO" --session "$SESSION" --resume "$RUNTIME_SESSION_ID"
```

Launch kimi from the canonical repository root. Preserve terminal evidence so it remains capturable. If the exact session
already exists, start succeeds only when it is already owned by this runner and bound to the same
repository; otherwise it fails closed.

Mutation commands use the schema-v2 snapshot and editor guards in [transport.md](transport.md).

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
ownership marker, and the pane title together instead of assuming the executable name is `kimi`.
Status also reports local Git branch, HEAD, cleanliness, upstream, and locally known ahead/behind
counts. Read [status-monitoring.md](status-monitoring.md) before deciding the project is complete.

## Send literal input

```bash
scripts/runtime-tmux.sh send --repo "$REPO" --session "$SESSION" \
  --if-snapshot "$SNAPSHOT_ID" --require-empty-editor --text "$PROMPT"
```

For a multiline or large prompt, use stdin:

```bash
scripts/runtime-tmux.sh send --repo "$REPO" --session "$SESSION" \
  --if-snapshot "$SNAPSHOT_ID" --require-empty-editor < prompt.txt
```

The helper pastes literal bytes and sends Enter separately. Shell metacharacters in the prompt are
not executed by the tmux pane's shell.

## Stop

```bash
scripts/runtime-tmux.sh stop --repo "$REPO" --session "$SESSION" \
  --if-snapshot "$SNAPSHOT_ID"
```

This only sends `/exit` to an owned idle Kimi CLI session. If it does not exit promptly, report
`quit-pending` and inspect it. `--force` may kill the exact owned session only when the user has
explicitly authorized forced termination. An absent session is already stopped; do not inspect or
affect other sessions.
