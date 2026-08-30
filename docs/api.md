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
scripts/kaola-tmux.sh PLATFORM start     --repo ABS_PATH --session NAME [--continue | --resume ID] \
  [--model ID --effort low|medium|high|xhigh|max]
scripts/kaola-tmux.sh PLATFORM observe   --repo ABS_PATH --session NAME
scripts/kaola-tmux.sh PLATFORM status    --repo ABS_PATH --session NAME
scripts/kaola-tmux.sh PLATFORM capture   --repo ABS_PATH --session NAME [--lines N]
scripts/kaola-tmux.sh PLATFORM send      --repo ABS_PATH --session NAME \
  [--if-snapshot ID] [--text TEXT]
scripts/kaola-tmux.sh PLATFORM key       --repo ABS_PATH --session NAME \
  [--if-snapshot ID] --key NAME
scripts/kaola-tmux.sh PLATFORM answer    --repo ABS_PATH --session NAME \
  [--decision-id ID] [--if-snapshot ID] --replace-editor [--text TEXT]
scripts/kaola-tmux.sh PLATFORM stop      --repo ABS_PATH --session NAME \
  [--if-snapshot ID] [--force]
```

`--repo` must resolve to the exact Git top-level. Session names match
`[A-Za-z0-9][A-Za-z0-9_.-]{0,79}`. Without `--text`, `send` reads non-empty stdin.

Executable overrides are `GROK_BIN`, `CLAUDE_BIN`, `OPENCODE_BIN`, `KIMI_BIN`, and
`CURSOR_AGENT_BIN`. Test/embedding overrides are `TMUX_BIN`, `PYTHON_BIN`, `PS_BIN`, and
`KAOLA_START_TIMEOUT`; `GROK_START_TIMEOUT` remains a Grok-only compatibility alias.

## Observation schema

`observe` returns evidence for the controlling agent. Schema version 2 includes `snapshot_id`,
`pane_revision`, `raw_current_frame`, exact ownership and pane facts, runtime child/process evidence,
relay input/output facts, Git reporting facts, and compatibility editor/activity/approval/decision
signals. Those compatibility fields are advisory evidence for the controlling agent; generic
`send`/`stop` never consume them as semantic authority.

The `relay` object reports relay epoch/process/socket, runtime child PID/PGID/path/start fingerprint,
child input/output offsets, streaming output digest, resize revision, bracketed-paste mode, and terminal
fence facts. `snapshot_id` is opaque correlation evidence. Any changed fact may produce a different
identifier, but that change is reported and never independently blocks an agent-directed action.

An absent or legacy-direct session may have no snapshot. Legacy direct sessions remain observable,
with `relay.managed: false` and `relay-required` in advisory `evidence_flags`; the agent decides how
to proceed from the available transport capabilities.

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

Preflight reports runtime binary/version, optional Workflow capability discovery, recurring evidence,
project materialization evidence, and an adapter-specific summary. Missing Workflow carriers,
configuration health, or materialization does not block the CLI communication channel.

Preflight also resolves the declared Runner default without starting a session. `start` gives an
explicit user model/effort precedence; otherwise it uses that Runner default. A readable catalog
that proves the requested model absent returns typed `model-unavailable` evidence before tmux is
created, rather than launching with ambient client state. After creation, actual mismatch or
unreadable evidence never disables generic communication.

Model evidence under `model` includes `requested_model_source`, `requested_model_name`,
`resolved_runtime_model_id`, `resolved_parameters`, `actual_runtime_model_id`,
`actual_parameters`, tri-state `model_verified`, `model_mismatch_reason`, and structured provenance.

## Agent-directed transport results

Every transport action acquires the relay's mechanical write transaction, captures action-time
evidence, prepares the requested literal bytes, and reports whether submission happened. `send` and
`stop` do not require a snapshot. If legacy `--if-snapshot` is supplied, the receipt returns
`based_on_snapshot`, `action_time_snapshot`, and `observation_changed`; a changed frame does not return
`stale-snapshot`. No generic action branches on editor, activity, approval, decision, worker count,
coordinate, prose, Git, Workflow, or later-output-barrier interpretations.

`send` returns the prepared payload fingerprint plus `mutation_performed:true` after submit.
`key` accepts `up`, `down`, `left`, `right`, `enter`, `escape`, `tab`, `backtab`, or `space`; it sends
only that key's exact bytes, adds no Enter, and returns `result:key-sent` plus `payload_fingerprint`.
The controlling Agent owns the choice and meaning of the key.
`answer --replace-editor` is a capability-specific whole-editor transfer; Claude Code is the only v1
replacement capability, while other adapters report `answer-unsupported`. Decision IDs, revisions,
and later-output barriers are evidence for the agent and do not become generic follow-up gates.

Before a follow-up, the controlling agent reads the raw frame and chooses how to handle any retained
draft, approval, output, login/trust, or decision surface. The Runner does not decide that choice.
After send/key, the agent observes/captures the response and, when applicable, verifies durable
Workflow/Git/forge state.

Input payloads reject CR, ESC, DEL, every other C0/C1 control except LF/TAB, invalid raw control
bytes, and embedded paste delimiters before any child PTY write. LF/TAB are accepted only when the
relay attests bracketed-paste mode. Send and Claude answer attest the exact relay-prepared payload
fingerprint before Enter. Answer also attests clear-editor and rechecks the same decision.

Ordinary and force stop do not require a snapshot. A successful force
stop reports `result: stopped`, `action: force-stop`, and terminal `final_state`; it cannot target a
session that the current transport cannot mechanically reach, and it is not emitted until the original
child/group and every exact fingerprint-tracked escaped descendant are absent.

## Adapter interface

Each adapter declares identity, display name, executable, environment override, recurring support,
quit text, answer capability, and declared default-model facts. It implements `adapter_preflight`,
`adapter_build_launch`, `adapter_prepare_model_environment`,
`adapter_detect_tui`, `adapter_activity_hint`, `adapter_observe_frame`, and
`adapter_extract_session_id`. Adapters contain platform facts only and must not evaluate runtime- or
user-produced shell text. Starting a CLI does not invoke a Workflow materializer.

Claude, Cursor, and OpenCode painted placeholders and cursor coordinates are preserved as visible
evidence but never become input-origin authority.

Structural adapter facts describe visible chrome and compatibility hints for Agent review; they do
not decide input readiness or Workflow completion. Cursor CLI start does not call a Workflow
materializer or mutate `.cursor`; installed/global/project command surfaces are reported only.
