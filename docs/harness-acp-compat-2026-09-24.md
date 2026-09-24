# Harness ACP compatibility — 2026-09-24 (Pink class 2 admission)

Issue #153. The Pink harness-compat daily check of 2026-09-24 judged class 2 (needs change);
v0.6.0 was already cut (R `2504be21…`), so this admission is queued post-cut: no release is cut,
no local CLI is upgraded, and `~/.dsh` is untouched. Everything below is a record change in this
repository plus read-only upstream checks; no live ACP run backs any of it unless the text says
so. Validation receipts and the `.kaola` receipt pointer are at the end.

## 1. Codex pins: 0.155.1 → 0.156.1, codex-acp 1.13.0 → 1.13.1

`platforms/codex.yaml` now pins the 2026-09-24 Pink class-2 report versions:

- `acp_command`:
  `npx --yes --package @openai/codex@0.156.1 --package @agentclientprotocol/codex-acp@1.13.1 codex-acp`
- `acp_verified_versions`: `cli=0.156.1;adapter=1.13.1;protocol=1`
- `acp_wrapper_pin`: `1.13.1`

Provenance, kept honest:

- This is a **record-only pin**. No local CLI was upgraded, and no live ACP session ran on
  1.13.1 / 0.156.1 for this admission.
- It supersedes the #145 `acp_quirks` note that npm `@openai/codex@0.156.1` could not be
  installed through the 2026-09-23 measuring network, so no 0.156.1 pin was claimed then. The
  quirks now say the pins follow the 2026-09-24 Pink class-2 report. The 0.5.9 CHANGELOG
  section that recorded the failed install stays as dated history.
- The 2026-09-23 live measurements stay dated facts inside the same quirks sentence: adapter
  1.13.0 with `CODEX_PATH=/opt/homebrew/bin/codex` (codex-cli 0.156.0) applying `gpt-6-sol/high`
  with a `medium` discriminator and `gpt-6-astra/high`, and the steering summary's
  "adapters 1.11.0 and 1.13.0" advertisement facts. Nothing here re-measures them.

Hardcoded copies of the old pins moved with the record (same values, same commit):

- `tests/contract/test-runner-v2.py` (the exact `acp_command` string in `PLATFORMS`).
- `tests/contract/test-issue-22-bypass-all-approvals.py` (the manifest pin assertion).
- `tests/contract/test-acp-contract.py` (the Issue #145 comment now cites the measurement on
  1.13.0 / 0.155.1 and the pins at 1.13.1 / 0.156.1).
- `templates/orchestrator/references/host-entry-matrix.md`: the codex row's Version cell now
  reads `codex-acp 1.13.1`, and the codex note states the E2/D3 row was measured on codex-acp
  1.13.0 with the pin moved record-only on 2026-09-24 — the cell never claims a 1.13.1
  measurement.
- `docs/codex-host.md` and the 0.5.9/0.6.0 CHANGELOG sections keep their dated live evidence
  (0.155.1 / 1.13.0) as dated fact; history is not rewritten.

## 2. zcode-acp 0.47.x precheck (usage_update, compaction busy-window)

Question: does william0wang/zcode-acp 0.47.x exist, and what does it do for the `usage_update`
notification and compaction busy-window handling?

What was actually verified (read-only network checks, 2026-09-24, this Mac):

- **0.47.x exists.** GitHub `william0wang/zcode-acp` tags/releases list v0.47.0 (2026-09-22)
  through v0.47.10 (2026-09-23T13:51:07Z, latest at precheck time), read through authenticated
  `gh api repos/william0wang/zcode-acp/{tags,releases}`.
- **Compaction busy-window.** Release notes: v0.47.3 "hold prompts during auto-compact instead
  of rejecting them" (#244, commit `c5cbac1`); v0.47.4 "report the auto-compact window as busy
  so held prompts stay visible" (#247, commit `cb496f7`); v0.47.8 "report the manual /compact
  window as busy so prompts queue instead of erroring" (#255, commit `58fbbe5`). The v0.47.8
  patch was read directly: `compact()` in `src/handlers/extensions.ts` is the single raise
  point for both manual and auto compactions — it sets the in-flight flag, emits a turn-state
  `running:true` to every client, runs the compaction, and settles `running:false`; a prompt
  that arrives in the window is held by the prompt path (`waitForAutoCompactIdle`) and reads as
  queued, never the backend compact-lock error (`-32010`).
- **usage_update.** v0.47.9 "report context occupancy only in usage_update, never cumulative
  tokens" (#257, commit `11c3688`, closes upstream #228).
- **npm is not the channel.** The npm package named `zcode-acp` is unrelated (version 0.1.0,
  repository `leezhian/zcode-acp`); william0wang/zcode-acp is not published under any
  `@william0wang/*` scope (E404). This matches the platform record's "never vendored and never
  npm".

What was NOT verified: no live ACP run against any 0.47.x build, and no check of whether the
installed ZCode.app 3.14.1 / CLI 0.16.9 backend already surfaces the same busy-window or usage
semantics. Those stay live-run questions.

Conclusion recorded: upstream 0.47.x (through v0.47.10) adds hold-and-report-busy semantics for
both auto and manual compaction and corrects `usage_update` to context occupancy only. The
Runner's own zcode adapter (`scripts/kaola-zcode-acp.py`, Gate 2, wrapper pin `80aa4e2`
unchanged) is unaffected by this admission; the upstream facts are protocol-reference knowledge
for the next live ZCode run, which should confirm what the installed backend emits during its
compaction windows.

ZCode CLI stays `0.16.9` (`acp_verified_versions` unchanged). The precheck outcome does not
land in `platforms/zcode.yaml`: the generated zcode ACP reference (`references/acp.md`) sits at
8179 of its 8192-byte budget (13 bytes headroom), so the platform record's 2026-09-22 phrasing
stays as-is and this document plus the CHANGELOG entry are the precheck record.

## 3. Optional same-commit records (Pink 2026-09-24 batch, no separate verification)

`acp_verified_versions` only, all record-only, no local CLI upgraded:

- kimi-cli: `cli=2.0.2` → `cli=2.1.0`.
- opencode: `cli=2.0.11` → `cli=2.0.15`. Its `steering_summary` now names 2.0.15 as the
  un-probed record while keeping the 2.0.11 `initialize` observation and the 1.18.17 history
  (the #88 record/measurement calibration), and
  `tests/contract/test-issue-88-permission-defaults.py` pins the new record value.
- claude-code: `cli=2.1.278` → `cli=2.1.280` (bridge pin `6c20f28` unchanged).
- droid: `cli=0.223.0` → `cli=0.225.1`. Pink says 0.225.x; `droid --version` on this dev
  machine printed `0.225.1` (rc 0) on 2026-09-24, matching the live session's `@factory/cli`
  agentInfo. No upgrade was performed — the machine already ran it.

Dated measurements and the fixtures that model them keep the versions they were measured on
(Droid 0.220.0 steering/launch facts, Kimi 2.0.2 steering probe, Claude 2.1.272 permission
fact, OpenCode 1.18.17/2.0.11 probes).

## 4. Validation receipts

Because this is the first content commit after the v0.6.0 pin (P `bf718f7` pinning R
`2504be21`), `templates/grok-bot/accepted-revision.json` returns to the `content` stage — the
same reset the first post-pin content commit of the previous cycle made (`a74119a`) — so
`render --check` accepts work after the pin. The bridge renders its unpinned placeholder line
and `bridge.json` reports `saveable: false`; no release is cut and no new pin is claimed.

Run from the worktree `.kw/worktrees/bundle-153` (branch `workflow/bundle-153`) after all edits,
with `./scripts/render-skills.py --write` first to regenerate `skills/` and `hosts/grok-bot/`
from the changed manifests and the host-entry-matrix template:

- `./scripts/render-skills.py --check`: rc=0 — `PASS (10 workers + kaola-project-runner +
  kaola-delegator + grok-bot host: 1 bridge skill, 2555 B, content stage, unpinned (not
  saveable); budgets OK)`.
- `./scripts/validate.sh`: rc=0 — every lane OK, zero FAILED/ERROR, 281 test rows ok; this
  machine lacks three dev-machine prerequisites and its affected rows skipped with printed,
  named receipts per the #151 policy (python ≥ 3.10 ×2 rows, tmux ×3 rows, bash ≥ 4 watchdog —
  detected bash 3.2.57 / Python 3.9.6 / no tmux). Assertions were not weakened.

## 5. .kaola receipt pointer

The local admission receipt is `.kaola/harness-compat-2026-09-24.md` at the canonical root
(`/Users/ylmacstudio/Workspace/kaola-project-runner/.kaola/`), gitignored by design, carrying
the same facts plus the exact validation commands and rc values.
