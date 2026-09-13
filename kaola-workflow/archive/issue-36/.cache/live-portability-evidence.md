# Live portability evidence — issue-36

FINAL candidate: `workflow/issue-36` @ `d948b90` (bcbd6d8 + merges of
origin/main @3650a28/#34 and @27e277b/#33). The copied payload at
`/tmp/kpr36-live/installed skills/` was updated in place via the installer's
owned-update path (`update:`) so the refreshed leg below ran the NEW
candidate's payload — SKILL.md carries the two-tier presets and the holder
carries #33 `initial_config_options`.
fixtures: `/tmp/kpr36-live/` (paths contain spaces), scratch repos
`/tmp/kpr36-live/scratch-repo`, `/tmp/kpr36-live/scratch-grok`
records: `$TMPDIR/kaola-501/{codex,grok}/kpr36-*/<repo-digest>/record.json`

## Final leg (d948b90) — Devin explicit Skill-read → copied Codex default Sol/high/Fast-off

- Read `/tmp/kpr36-live/installed skills/codex-kaola-project-runner/SKILL.md`
  (explicit loading; neutral `description`, two-tier preset contract, Fast-off
  default confirmed in the copied file).
- `preflight --repo /tmp/kpr36-live/scratch-repo --session kpr36-final-codex`
  → `login_required:false`, `transport:acp`, `advertised_config_options`
  incl. `fast-mode` (current `off`).
- `start` → `state:ready`, `acp_session_id 01a09bfd-0d84-7881-98af-6a0c553f2a30`,
  `holder_pid 32903`; `configured_options`: `model=gpt-5.6-sol`,
  `reasoning_effort=high`, `fast-mode=off` (explicit off applied, not assumed),
  `mode=agent-full-access`; `model_selection`: `source:runner-default`,
  `tier:default`, resolved `gpt-5.6-sol`/`high` (#34 contract live on copy).
- `send` → `final_text:"KPR36_FINAL_OK"`, `stop_reason:end_turn`,
  `mutation_status:completed`.
- `observe` → current `session_meta.configOptions`: `mode=agent-full-access`,
  `model=gpt-5.6-sol`, `reasoning_effort=high`, `fast-mode=off` vs
  `initial_config_options`: `mode=agent`, `model=gpt-5.6-sol`,
  `reasoning_effort=medium`, `fast-mode=off` — #33 current-vs-initial
  reporting proven live on the copied payload.
- `stop` → `stopped:true`, `residual_pids:[]`, `agent_exit_code:0`;
  `status` → `state:stopped`. `tmux ls`/`pgrep`: zero `kpr36` residue.

## Prior legs (bcbd6d8, pre-#34 payload — capability evidence retained)

## Leg A — Devin (non-Codex controller) → Codex ACP target, explicit Skill reading

Loading mode: EXPLICIT Skill reading. Devin does not natively discover Skills
under `/tmp`; the controller read the file
`/tmp/kpr36-live/installed skills/codex-kaola-project-runner/SKILL.md`
(copy-installed via `--skills-dir "/tmp/kpr36-live/installed skills" --method copy`)
and then invoked the copied payload's absolute script path.

- `preflight --repo /tmp/kpr36-live/scratch-repo --session kpr36-devin-codex`
  → `login_required:false`, `transport:acp`, ACP `@agentclientprotocol/codex-acp@1.11.0`.
- `start` → `state:ready`, `acp_session_id 01a09ba3-5f96-7cb2-8b7a-247911a402c7`,
  `holder_pid 36459`, `agent_pid 36460`, configured `gpt-5.6-luna`/`low`/
  `agent-full-access`.
- `send` → `final_text:"KPR36_DEVIN_OK"`, `stop_reason:end_turn`,
  `mutation_status:completed`, `duration_ms 10319`.
- `capture` → full event log readable (`event_cursor:15`, 27,750 bytes).
- `stop` → `stopped:true`, `residual_pids:[]`, `agent_exit_code:0`.
- `status` → `state:stopped`, `outcome:stopped`.
- Record: `$TMPDIR/kaola-501/codex/kpr36-devin-codex/f9f438b0c9245269/record.json`
  `state:stopped`.

Evidence note (#33 domain, recorded not judged): final `status` `session_meta`
reports `model currentValue gpt-5.6-sol` and `mode currentModeId agent` while
`start` `configured_options` applied `gpt-5.6-luna`/`agent-full-access`.

## Leg B — Codex consuming runtime → Grok ACP target

Controller started via the same copied Codex Skill:
`start --session kpr36-codex-ctrl` → `state:ready`,
`acp_session_id 01a09ba9-a64a-7a11-9e70-42fff95a2cbc`,
`holder_pid 44667`, `agent_pid 44681`.

Sent instruction directed Codex to read
`/tmp/kpr36-live/controller skills/grok-kaola-project-runner/SKILL.md`
and follow its loop on `--repo /tmp/kpr36-live/scratch-grok --session kpr36-grok-target`.

- Codex `tool_calls`: `read:1` (the copied SKILL.md) + `execute:6`
  (preflight/start/send/capture/stop/status on the copied script).
- Codex `final_text`: "Observed reply: `KPR36_CODEX_OK` … Final session state:
  `stopped` … Residual processes: none … no files were modified."
- Target record: `$TMPDIR/kaola-501/grok/kpr36-grok-target/8812d927f3bd0aef/record.json`
  `state:stopped`, `holder_pid 48038`, `agent_pid 48039`,
  `acp_session_id 01a09baa-0e6c-7a00-8a93-282235ed537e`.
- Controller stopped: `residual_pids:[]`.

## Native discovery vs explicit Skill reading

- Native discovery evidence: the Codex controller session's `availableCommands`
  listed `$grok-kaola-project-runner` (and the other Kaola Skills) sourced from
  `~/.codex/skills` — Codex's own discovery of installed Skills, observed, not
  used as the drive path.
- Explicit Skill reading evidence: both legs drove the COPIED payload by reading
  `SKILL.md` at its `/tmp/kpr36-live/...` path and invoking
  `"<copied SKILL_DIR>/scripts/runtime-tmux.sh"`. Devin's leg used explicit
  reading exclusively (no `/tmp` discovery exists).

## Copied-payload self-containment (no checkout / no global bin links)

- `scripts/runtime-tmux.sh` line 3:
  `script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"`.
- `scripts/kaola-tmux.sh` line 122 invokes `"$script_dir/kaola-acp.py"`.
- `scripts/kaola-acp.py` lines 27-28:
  `SCRIPT_DIR = Path(__file__).resolve().parent; HOLDER = SCRIPT_DIR / "kaola-acp-holder.py"`;
  line 634-635 spawns `[sys.executable, str(HOLDER), ...]`.
- Grep of the copied `scripts/` tree: no reference to `~/.local/bin`,
  `kaola-acp`/`kaola-acp-holder` bin links, or the source checkout on the
  executed path.
- Ownership/content receipts live outside the payload at
  `/tmp/kpr36-live/{installed skills,controller skills}/.kaola-install-receipts/*.json`.
- The live sessions above ran entirely from the copied payload; the source
  checkout and `~/.local/bin` links were never on the execution path.

## Scope notes

- No PTY legs and no Claude/Cloud authentication legs run (issue scope).
- Post-run `tmux ls`: only pre-existing foreign sessions `kaola-9362e3d5` and
  `kaola-fb9f6f4c`; `pgrep kpr36`: none; unrelated sibling-run test processes
  (`issue6-*`, `model-literal-*`) left untouched.
