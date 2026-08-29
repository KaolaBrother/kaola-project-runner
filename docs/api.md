# Command and Contract Reference

## Renderer

```text
scripts/render-skills.py --write
scripts/render-skills.py --check
```

`--write` deterministically rebuilds five managed Skill directories. `--check` returns nonzero for
any missing, stale, or unexpected file or Skill directory. Manifest values are JSON strings in a
flat YAML subset parsed without an external dependency.

## Installer

```text
scripts/install-local.sh [--platform ID[,ID...]] [--uninstall]
```

IDs are `grok`, `claude-code`, `opencode`, `kimi-cli`, and `cursor-cli`. Omit `--platform` for all
five. Every selected target is preflighted before mutation. Only exact owned symlinks are created,
migrated, or removed.

## tmux core

```text
scripts/kaola-tmux.sh PLATFORM preflight --repo ABS_PATH --session NAME
scripts/kaola-tmux.sh PLATFORM start     --repo ABS_PATH --session NAME [--continue | --resume ID]
scripts/kaola-tmux.sh PLATFORM status    --repo ABS_PATH --session NAME
scripts/kaola-tmux.sh PLATFORM capture   --repo ABS_PATH --session NAME [--lines N]
scripts/kaola-tmux.sh PLATFORM send      --repo ABS_PATH --session NAME [--text TEXT]
scripts/kaola-tmux.sh PLATFORM stop      --repo ABS_PATH --session NAME [--force]
```

`--repo` must resolve to the exact Git top-level. Session names match
`[A-Za-z0-9][A-Za-z0-9_.-]{0,79}`. Without `--text`, `send` reads non-empty stdin.

Executable overrides are `GROK_BIN`, `CLAUDE_BIN`, `OPENCODE_BIN`, `KIMI_BIN`, and
`CURSOR_AGENT_BIN`. Test/embedding overrides are `TMUX_BIN`, `PYTHON_BIN`, `PS_BIN`, and
`KAOLA_START_TIMEOUT`; `GROK_START_TIMEOUT` remains a Grok-only compatibility alias.

## Status schema

Commands return neutral JSON keys including `result`, `platform`, `runtime`, `session`, `repo`,
`present`, `owned`, `platform_match`, `repo_match`, `tui_detected`, `activity`,
`runtime_session_id`, pane identity, and Git branch/HEAD/cleanliness/ahead/behind. Grok additionally
returns `grok_tui` as a compatibility alias. Status also reports `process_match` and the observed
`pane_process`; a TUI is not accepted unless the live process matches the exact resolved runtime
binary at argv[0] or interpreter argv[1], except Kimi's exact `kimi-code` plus `node` product identity.
The Grok compatibility wrapper preserves `grok_version` and `project_root` in preflight.

Preflight reports runtime binary/version, Workflow capability discovery, recurring capability,
project materialization state, and an adapter-specific evidence summary.

## Adapter interface

Each adapter declares identity, display name, executable, environment override, recurring support,
and quit text. It implements `adapter_preflight`, `adapter_build_launch`, `adapter_detect_tui`,
`adapter_detect_activity`, and `adapter_extract_session_id`. An adapter may additionally implement
`adapter_prepare_launch` for an authority-owned point-of-use transaction. The core calls it only for
a new exact session, after read-only preflight and before creating tmux, so a refusal leaves no
orphan session. Adapters contain platform facts only and must not evaluate runtime- or user-produced
shell text.

Cursor CLI uses that optional hook to call the currently installed Kaola Cursor authority's
`--ensure-target <canonical-repo>` transaction. It verifies the returned project target, scope,
status, file count, and required commands before launch. Before any helper invocation it also proves
that the helper's exact path, bytes, and mode are bound by the authority receipt. Preflight itself
remains read-only, and unmanaged project collisions fail closed.
