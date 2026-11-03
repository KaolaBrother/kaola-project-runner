# Hermes Agent 0.22.6 ACP revalidation — 2026-11-03

MacBook leg of the `#1053` compat item (moved from KPR #462). This is the
adapter-path re-check that `owner-acp-must-match-latest-20261031` asks for
before a three-Mac CLI upgrade. No `worker_grants` row, seat count, preset,
grant or hold changed. No `--setup`, `--setup-browser` or `--accept-hooks` ran;
no `~/.hermes/.env` was read, and nothing was written under `$HERMES_HOME` by
the Runner.

Raw receipts stayed on this machine under
`/Users/ylpromax5/.kaola-tmp/kpm-parallel-fill-t1590-20261103/seat-1053/`
(`receipts/`, `wire/`, `logs/`). The probe scripts there are evidence only,
not Runner code.

## Verdict

**GREEN for the Runner/holder ACP path.** Protocol 1 is unchanged,
`initialize` is identical, and model selection/readback, mode, prompt and
cancel behave as on 0.22.5 through the in-repo `kaola-hermes-acp.py`. The
verified pin moves to `cli=0.22.6;agent=hermes-agent/0.22.6;protocol=1` with
the named condition below.

**Condition `native-config-update-unmapped`.** 0.22.6 adds a native
`session/update` variant `config_option_update` whose `configOptions` use the
runtime ids (`edit_approval_policy`, `model`, `reasoning_effort`). The adapter
still replaces the `session/new`/`load` reply list with its synthesized
`model`/`mode`, but forwards the notification unchanged. The holder mirrors it
into `session_meta.configOptions`; `model` keeps its id and value, while mode
appears as `edit_approval_policy` and a new `reasoning_effort` appears. Seat
execution does not read mode from that list, so this is a view/editor follow-up,
not a stop-ship defect. An editor that writes one of the native ids still gets
the adapter's local `-32602`.

## Version and identity

- CLI: `Hermes Agent v0.22.6 (2026.9.24) · stable · local f0d94882e89a`
  (`~/.local/bin/hermes`); commit `f0d94882e89ab8d4098b5bb2f166adfb9ee0a0ab`
  (`v0.22.6`; annotated tag object `49138a6058`).
- `initialize`: `protocolVersion` 1, `agentInfo` `hermes-agent` / `0.22.6`,
  `loadSession: true`, session capabilities `fork`/`list`/`resume`, auth
  methods `deepseek` and terminal `hermes-setup`.
- `hermes acp --check` → `Hermes ACP check OK`.
- Adapter child argv was `hermes --yolo acp`; the adapter stripped `resume`.

## Source diff

The release range has 3482 commits (the release branch merges upstream main);
ten touch `acp_adapter/`. The protocol dependency stays
`agent-client-protocol==0.9.0`.

| Commit | ACP-relevant change |
|---|---|
| `b2f9dee01a` | list gateway editor threads; add `edit_approval_policy`/`model`/`reasoning_effort` config pickers; stop on cancel |
| `8aee8df0ec` | project config options on outside changes; document `prompt.cancel` |
| `d23579a1e5` | refuse cancelling steered rows; drop superseded config projections |
| `04f52d6bed` | equal snapshot no longer cancels a pending picker update |
| `3ae67dc3d6` | stopping a turn no longer kills background subagents |
| `33bce7b26d` | approval prompt redacts hidden display characters |

The 0.22.5 `session/new`/`load` reply had no `configOptions`; `set_config_option`
answered `{configOptions: []}` for every id; `session/cancel` also ended
background delegations.

## Live wire

The probe sent the Runner's sequence against the exact command: `initialize`
(client capabilities `fs` false, `terminal` false), `session/new` in a
throwaway cwd, `session/set_mode dont_ask`, `session/set_model
deepseek:deepseek-flash`, `session/load`, a `pong` prompt, and a `sleep` turn
cancelled after 3 s.

| Run | Receipt | Result |
|---|---|---|
| raw 0.22.6 | `receipts/raw-0.22.6.json` | native `configOptions`; load `deepseek:deepseek-flash` / `dont_ask`; `pong`/`end_turn`; cancel `cancelled` |
| adapter 0.22.6 | `receipts/adapter-0.22.6.json` | `resume` stripped; reply `[model, mode]`; load readback correct; `pong`; cancel `cancelled` |
| adapter 0.22.5 (control) | `receipts/adapter-0.22.5.json` | same adapter contract on the old runtime |

Selected 0.22.6 facts:

- Native `configOptions`: `edit_approval_policy` (`ask` / `workspace_session` /
  `session`), `model` (`auto:anthropic/claude-opus-4.6` before the pick), and
  `reasoning_effort` (`medium`; `none`, `minimal`, `low`, `medium`, `high`,
  `xhigh`, `max`, `ultra`).
- `session/set_config_option` now applies `model` and `reasoning_effort` and
  returns the full list; an unknown id is still accepted silently (the
  adapter's local refusal rationale is unchanged).
- `session/set_model` and `session/set_mode` still return `{}`.
- `session/load` still omits top-level `sessionId`; it reads back
  `currentModelId deepseek:deepseek-flash` and `currentModeId dont_ask`.
- A `pong` prompt: `stopReason end_turn`, final text `pong`. A cancelled
  `sleep` turn: `stopReason cancelled`.
- `config_option_update` appeared after a typed `/reasoning high`; the frame
  carried the native ids above. A `/model` prompt at the same value sent none.

## Fleet

All three Macs were on `bf0203a794` / 0.22.5 with clean trees and no running
Hermes services before the upgrade. After `hermes update --yes` all three are
on `f0d94882e8` / 0.22.6, `hermes --version` names 0.22.6, `hermes acp
--check` is OK, and `install-stamp.json` records `baseVersion` and
`displayVersion` `0.22.6`.

| Mac | Path | Result |
|---|---|---|
| MacBook | `hermes update --yes` (first attempt hit a 60 s `git ls-remote` timeout; retry succeeded) | 0.22.6 |
| Mini | `hermes update --yes` over SSH | 0.22.6 |
| Studio | `hermes update --yes` over SSH | 0.22.6 |

**Tag/stamp step.** On Mini and Studio the updater checked out the release
commit but the clone had no `v0.22.6` tag, so the stamp initially read
`0.22.5+3482.gf0d9488` and `hermes --version` reported that derived string.
`git fetch --tags` plus
`hermes_cli.source_stamp.write_source_stamp(root)` rewrote the stamp to
`0.22.6` on both. The three-Mac routine must read `hermes --version` after an
update: a `vX.Y.Z+N.gsha` result means the tag is missing and the machine is
not aligned yet.

Mini and Studio were verified by version, commit, stamp and `hermes acp
--check`; they were not driven through a live ACP session. The live wire
measurement is MacBook.

## What changed

- `platforms/hermes.yaml`: `acp_verified_versions` → 0.22.6 with
  `condition=macbook-20261103-native-config-update-unmapped`; the 0.22.6
  config-option/effort/cancel facts in `acp_quirks` and `launch_summary`;
  effort text in the preset parameters and Fast summary.
- Regenerated `skills/hermes-kaola-project-runner/` (and the shared profile
  catalog/build manifests) from that manifest.
- `tests/contract/test-issue-416-hermes-acp.py`: the pin/condition assertions.
- No adapter, holder or preset behavior change.

## Limits

- Permission, instruction-walk, login and steering facts stay the 0.22.5
  measurements. The only 0.22.6 `edit_approval.py` change is the displayed
  approval title.
- `reasoning_effort` is a real 0.22.6 ACP option but neither this adapter nor
  the KPM row surfaces it; effort remains a Hermes-config fact.
- `session/list` and `session/fork` were not exercised; their advertised
  capabilities are unchanged.
- `native_steering` stays `unknown`; no steer measurement was added.
