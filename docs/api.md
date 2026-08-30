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
scripts/kaola-tmux.sh PLATFORM observe   --repo ABS_PATH --session NAME
scripts/kaola-tmux.sh PLATFORM status    --repo ABS_PATH --session NAME
scripts/kaola-tmux.sh PLATFORM capture   --repo ABS_PATH --session NAME [--lines N]
scripts/kaola-tmux.sh PLATFORM send      --repo ABS_PATH --session NAME \
  --if-snapshot ID --require-empty-editor [--text TEXT]
scripts/kaola-tmux.sh PLATFORM answer    --repo ABS_PATH --session NAME \
  --decision-id ID --if-snapshot ID --replace-editor [--text TEXT]
scripts/kaola-tmux.sh PLATFORM stop      --repo ABS_PATH --session NAME \
  --if-snapshot ID [--force]
```

`--repo` must resolve to the exact Git top-level. Session names match
`[A-Za-z0-9][A-Za-z0-9_.-]{0,79}`. Without `--text`, `send` reads non-empty stdin.

Executable overrides are `GROK_BIN`, `CLAUDE_BIN`, `OPENCODE_BIN`, `KIMI_BIN`, and
`CURSOR_AGENT_BIN`. Test/embedding overrides are `TMUX_BIN`, `PYTHON_BIN`, `PS_BIN`, and
`KAOLA_START_TIMEOUT`; `GROK_START_TIMEOUT` remains a Grok-only compatibility alias.

## Observation schema

`observe` is the only source of mutation tokens. Schema version 2 returns `snapshot_id`,
`pane_revision`, `raw_current_frame`, independent `editor_state`, exact ownership and pane facts,
runtime child/process evidence, visible shell/agent counts, native approval, a structured decision
marker, a later-output barrier, advisory `activity_hint`, Git reporting facts, and typed
`guard_failures`.

The `relay` object attests the relay epoch/process/socket, exact runtime child PID/PGID/path/start
fingerprint, child input/output offsets, streaming output digest, resize revision, bracketed-paste
mode, and `decrqm-nonce-v1` terminal fence. `snapshot_id` is opaque. Any covered input counter,
resize, editor, process, identity, frame, approval, decision, barrier, or Git change makes an old
snapshot stale. Output offset/digest, pane revision, history counters, relay run/quiesce state, and
`activity_hint` remain reporting facts: an equivalent TUI redraw may advance them without invalidating
a semantically equal mutation snapshot.

An absent or legacy-direct session has no mutation-usable snapshot. Legacy direct sessions remain
observable and untouched, with `relay.managed: false` and `relay-required` in `guard_failures`.

## Status compatibility

Commands return neutral JSON keys including `result`, `platform`, `runtime`, `session`, `repo`,
`present`, `owned`, `platform_match`, `repo_match`, `tui_detected`, `activity`,
`runtime_session_id`, pane identity, and Git branch/HEAD/cleanliness/ahead/behind. Grok additionally
returns `grok_tui` as a compatibility alias. Status also reports `process_match` and the observed
`pane_process`; a TUI is not accepted unless the live process matches the exact resolved runtime
binary at argv[0] or interpreter argv[1], except Kimi's exact `kimi-code` plus `node` product identity.
The Grok compatibility wrapper preserves `grok_version`, `project_root`, `grok_tui`, and legacy
ownership aliases. `status.activity` equals `status.activity_hint` for compatibility, but both are
advisory and excluded from action guards.

Preflight reports runtime binary/version, Workflow capability discovery, recurring capability,
project materialization state, and an adapter-specific evidence summary.

## Guarded mutation results

Every mutation reacquires an exact relay lease, disables pane input, stops the attested runtime
child tree (including fingerprint-tracked descendants that escaped the original process group),
drains output, completes a tokenized DECRQM parser fence, rebuilds the full observation, and compares
the caller's snapshot before preparing bytes. The prepared surface is rebuilt and checked again
before submit. Missing tokens return
`snapshot-required`; changed facts return `stale-snapshot`; editor, visible-work, approval,
decision, and barrier facts return their typed refusal. Runtime descendant processes remain exact
snapshot facts, but their semantic meaning belongs to the controlling model because real CLIs may
keep launcher and worker descendants alive at an empty prompt. No branch reads `activity` or
`activity_hint` as authority. The fence accepts only one exact nonce reply; unrelated outer-PTY
bytes refuse the action and are discarded, never replayed after restoration.

`send` additionally requires `--require-empty-editor`. `answer` requires an exact current decision
ID and `--replace-editor`; Claude Code is the only v1 replacement capability, while other adapters
return `answer-unsupported`. Receipts expose fingerprints and revisions, never draft or answer
plaintext. A pending or grid-neutral `output-seen` barrier refuses later mutations until fenced
output changes the visible frame revision to `satisfied`.

Input payloads reject CR, ESC, DEL, every other C0/C1 control except LF/TAB, invalid raw control
bytes, and embedded paste delimiters before any child PTY write. LF/TAB are accepted only when the
relay attests bracketed-paste mode. Send and Claude answer both bind the exact relay-prepared payload
fingerprint to the visible prepared editor before Enter; soft terminal wraps are joined while real
payload newlines remain distinct. Answer also attests clear-editor and rechecks the same decision.

Ordinary and force stop both require a fresh snapshot and exact relay identity. A successful force
stop reports `result: stopped`, `action: force-stop`, and terminal `final_state`; it cannot target a
legacy-direct, unowned, wrong-platform, wrong-repo, or stale session, and it is not emitted until
the original child/group and every exact fingerprint-tracked escaped descendant are absent.

## Adapter interface

Each adapter declares identity, display name, executable, environment override, recurring support,
quit text, and answer capability. It implements `adapter_preflight`, `adapter_build_launch`,
`adapter_detect_tui`, `adapter_activity_hint`, `adapter_observe_frame`, and
`adapter_extract_session_id`. An adapter may additionally implement
`adapter_prepare_launch` for an authority-owned point-of-use transaction. The core calls it only for
a new exact session, after read-only preflight and before creating tmux, so a refusal leaves no
orphan session. Adapters contain platform facts only and must not evaluate runtime- or user-produced
shell text.

Claude, Cursor, and OpenCode painted placeholder suggestions count as an empty editor only on the complete
recognized live surface with the cursor still at that platform's input origin. Identical user-entered
text with an advanced cursor is nonempty or unknown, never a placeholder shortcut.

Structural adapter facts describe editor, approval, visible work, and current structured decision;
they do not decide Workflow completion. Cursor CLI uses the optional launch hook to call the
currently installed Kaola Cursor authority's
`--ensure-target <canonical-repo>` transaction. It verifies the returned project target, scope,
status, file count, and required commands before launch. Before any helper invocation it also proves
that the helper's exact path, bytes, and mode are bound by the authority receipt. Preflight itself
remains read-only, and unmanaged project collisions fail closed.
