# Codex compact-recovery — isolated live verification (Issue #75)

Date: 2026-09-18. Host: codex-cli 0.153.4 (npm install), macOS arm64.
Method: real `CODEX_HOME` (auth + existing user hooks untouched; zero writes to
`~/.codex` by this verification) + scratch project `/tmp/kpr-i75-verify` whose
`.codex/hooks.json` carries exactly one entry — the byte-shape the installer
writes — pointing at `templates/codex-host/compact-recovery.md`. Codex launched
via tmux with `--dangerously-bypass-hook-trust` (automation-vetted invocation;
no persisted trust mutated).

## Sequence (all captures preserved)

1. `codex --dangerously-bypass-hook-trust` in scratch dir; trusted the scratch
   project layer (my own fixture; required for project `.codex/` hooks).
2. Prompt: "Reply with exactly the single word READY" → `READY` (turn 1).
3. `/compact` → pane shows `• Context compacted`; rollout records
   `type:"compacted"` + `item_completed ContextCompaction`
   (2026-09-18T15:47:08Z).
4. Probe: quote the recovery marker in the injected developer context →
   assistant final answer: `KW-COMPACT-RECOVERY-V2\nKPR-COMPACT-RECOVERY-V1`
   (2026-09-18T15:47:53Z).

## Proof points

- `20-transcript-extracts.json` line 19: real `compacted` record — context was
  actually rewritten (not simulated).
- Same file, line 30: `response_item` `role:"developer"` `input_text` containing
  the full `KPR-COMPACT-RECOVERY-START` payload — the hook's stdout became the
  model-visible `additionalContext` between the compaction item and the next
  model turn.
- Lines 35/39: `final_answer` quotes **both** markers —
  `KW-COMPACT-RECOVERY-V2` (foreign `kaola-workflow:compact-context` from
  `~/.codex/hooks.json`) and `KPR-COMPACT-RECOVERY-V1` (ours, project layer).
  This is simultaneously the coexistence proof: foreign hook untouched and
  still firing.
- Session stopped via `/quit`; `residual_pids=[]`.

## What was NOT touched

- `~/.codex/hooks.json` — never written (the project layer carried the test
  entry; Codex merges layers natively).
- `~/.codex/config.toml`, auth, trust store — never written; bypass flag is
  invocation-scoped.
- No credential read, copy, or log anywhere in this evidence.

## Installer receipts (fresh temp CODEX_HOME, not the real one)

- `30-status-before.json` → `installed:false`, no writes.
- `31-install-receipt.json` → `changed:true`, entry + payload copy installed;
  `32-installed-hooks.json` shows the exact entry shape verified live above.
- `33-reinstall-receipt.json` → `changed:false` (idempotent).
- `34-uninstall-receipt.json` → `removed_entries:1`, `payload_removed:true`;
  `35-after-uninstall-hooks.json` shows only the empty structure left.
- Merge safety vs foreign entries is covered by the contract suite
  `tests/contract/test-issue-75-codex-compact-hook.py` (24 cases, all PASS —
  includes two-project coexistence, Host/Worker/other-repo filtering, and
  atomic refusal on null-shaped config).

## Remaining boundary

- The live run proves injection timing and model visibility for the exact entry
  the installer writes. Trust-grant for a non-bypassed install remains a
  deliberate host-owner step (`/hooks` review), documented in
  `docs/codex-host.md`.
- ZCode compact carrier: no live path — see `../capability-matrix.md`
  (SessionStart(compact) cannot fire in 0.16.5; live probing blocked on #79).

## Round 2 — Host-bound emit on the project layer (session 01a0b658)

Second isolated run after the Host-only filter landed, scratch repo
`/tmp/kpr-i75-hostfilter/repo4` carrying `.codex/hooks.json` with the exact
entry shape the installer writes (`python3 <emitter> emit`,
`40-repo4-project-hooks.json`) plus an independent stdin-capture entry, and
`binding.json` bound to the live session id + canonical repo path
(`41-repo4-binding.json`).

- Real `/compact` → rollout line 24 `item_completed ContextCompaction`
  (`43-repo4-rollout-extracts.json`).
- Lines 29–30: TWO developer `additionalContext` messages landed between the
  compaction item and the next turn — the foreign `KW-COMPACT-RECOVERY` block
  (user-global Workflow hook) and our `KPR-COMPACT-RECOVERY` payload. The
  bound emit fired in the real host; coexistence intact.
- Lines 36/39: the model's own answer `Yes. "Recovery marker:
  KPR-COMPACT-RECOVERY-V1."` (`42-repo4-pane.txt`).
- `codex resume` preserved the session id across a quit/resume cycle — the
  binding survives resume by design.
- Hooks are loaded at session start: an entry written mid-session did not
  fire until a new session.
- Trust gate observed directly: `/hooks` showed the project-layer entries
  `Installed 3 / Active 1 / Review 2` — installed but inactive until the
  project dir trust + `--dangerously-bypass-hook-trust` invocation let them
  run. Review-gating, not the filter, explains silence in untrusted contexts.
- The `cat >` stdin-capture entry produced no file (hook writes appear
  sandboxed); stdin shape is instead pinned by the codex binary's embedded
  `session-start.command.input` schema and the contract suite.
- Unbound-session silence (ordinary Worker / other repo / non-compact source)
  is proven by the contract suite; a clean live negative was not separately
  staged after the bound positive landed — recorded as a boundary, not
  claimed.

## Round 3 — two-phase bootstrap, first-session coverage (repo5)

Scratch repo `/tmp/kpr-i75-hostfilter/repo5`; entry prepared with the shipped
`prepare` action (inert `binding.json`, `session_id: null`) BEFORE the Host
launched, so the entry was present at session start — the only way the FIRST
session can be covered. Two real Codex sessions ran in the same repo
(`42`/`52`-series artifacts; session ids masked in prose, preserved in the
rollout extracts).

- Session A, compact #1 (inert): model's marker list =
  `KW-COMPACT-RECOVERY-V2` only — the project hook RAN (foreign Workflow
  hook visible) while our emit emitted nothing (`53-repo5-sessionA-*`
  lines 24/29/40).
- Env identity (requested check): inside the host's own shell,
  `printenv | grep -i codex` shows `CODEX_SESSION_ID` and `CODEX_THREAD_ID`
  both present; offline compare against the rollout `session_meta` —
  `CODEX_SESSION_ID == CODEX_THREAD_ID == session_id`, all equal
  (`54-repo5-env-compare.json`; values masked). The hook-stdin
  `session_id` is that same identity — proven when the bound emit fired.
- `bind --session-id <A>`: receipt `ok`, `changed:true`; hooks.json sha256
  byte-identical before/after — bind touches ONLY `binding.json`
  (`51-repo5-binding.json`).
- Session A, compact #2 — SAME session, no stop/resume: model's marker list =
  `KW-COMPACT-RECOVERY-V2` + `KPR-COMPACT-RECOVERY-V1`; rollout lines 83
  (ContextCompaction), 88–89 (two developer `additionalContext` messages),
  98 (task_complete quoting both). **First-session compact coverage
  achieved via prepare + bind.**
- Session B (second session, same repo, Worker contrast): real compact →
  model's marker list = `KW-COMPACT-RECOVERY-V2` only; ours silent for the
  unbound session (`55-repo5-sessionB-*`).
- Isolation: no writes to `~/.codex` or any user-global config; project dir
  trust + `--dangerously-bypass-hook-trust` are invocation-scoped; both
  scratch sessions exact-stopped (`/quit` + tmux kill-session).
