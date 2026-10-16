# Finalization Summary — issue-336

## Delivered

The reported bug reproduced and is fixed: a Sideagent node whose admitted
turn its runtime refuses now moves through the Worker chain instead of
sticking on one runtime and waking the Host per rejection; the dsh fresh
start no longer depends on the `ps` enumeration; a live holder of the carrier's
own is adopted (or exact-stopped) instead of twinned. All work by the Host
`zcode-KPR-orchestrator-main` on `workflow/issue-336` (base main `ac12635d`),
independently reviewed by the Expert seat `devin-KPR-i336-review`
(devin/fable): verdict pass-with-should-fix, every should-fix item repaired.

**Reproduction (before any change).** The ZCode bridge maps a backend
`turn.failed` — the 5-hour limit `[1308] 已达到 5 小时的使用上限…重置` and
provider rejections — to a *completed* prompt with `stopReason: refusal`. In
the Host carrier's `_settle_node_batch` that is "checkpoint missing" →
`host_owned` → one Host turn, no `_node_fallback` (only runner-missing,
batch-unadmitted and start-failed called it) and no `node.failed`, so the
next Host write restarted the same runtime. Local evidence on this MacBook
(KT project, 2026-10-16 16:06:01 and 16:12:09): two refusals settled
`checkpoint: missing`, `host_woken: true`, no `sideagent_node_fallback`, next
batch (same range, through 1575) on zcode again — the vrpai Studio pattern
(24×) by mechanism. The new suite failed on the unfixed holder (5 failures,
1 error) and passes after the fix.

- **`_settle_node_batch` / `_node_turn_refusal`** (`b32a50fd`): a refused
  turn (`turn_failed`, or `turn_completed` with `stopReason refusal`) with no
  checkpoint at all is an unavailable runtime (#324 semantics): the carrier
  moves to the next eligible Worker runtime, restores the batch's selection
  (`sent_through`/`recovery_sent` from `sent_prior`) so that runtime takes the
  same range at the next boundary, exact-stops the refused node under the
  runtime it ran on, and wakes no Host turn for the move. An exhausted chain
  fails once (`host_owned` turn end, `checkpoint-missing` recorded,
  `node.failed`; detail names the tried runtimes and the unhandled range) and
  no node starts until the binding or recipe changes. A completed turn that
  merely wrote no checkpoint, a partial checkpoint, or a cancelled turn stay
  Host-owned as before. The node holder's turn end carries
  `turn_stop_reason`; the Host also reads `stop_reason=` from the reason text
  of an older node holder.
- **Node start without the `ps` enumeration** (`b32a50fd`): `_start_node`
  sets `KAOLA_ACP_RECORD_ROOT` to the carrier's own root (as
  `_maintenance_tool` already did), so the Runner resolves the node's record
  directory directly; the all-roots enumeration refused a fresh dsh node with
  `record-root-mismatch` whenever `ps` failed or exceeded 3 s (the
  Delegator's deterministic `ps`-shim measurement). A root-less start keeps
  that refusal (tests pin both).
- **No twin** (`b32a50fd`, `730ac436`): a Runner that fails after its holder
  came up leaves this carrier's own live node, adopted once its record is
  `ready`; a still-starting one is waited for (bounded, outside the lock); one
  that never becomes ready, or sits alive in an error state, is exact-stopped
  under its own runtime before the chain moves on (`_exact_stop_holder` keeps
  the node phase under the carrier's control). `stop_unconfirmed` remembers
  the platform/session it belongs to, so a later runtime move still confirms
  the stop under the right record; the stop thread reports the batch's own
  range/recovery.
- **dsh 0.2.0-rc.2** (`cb7e07a7`, `a6405400`, Delegator evidence C):
  `platforms/dsh.yaml` `acp_verified_versions` → `cli=0.2.0-rc.2;agent=
  deepseek-harness-acp/0.0.1;protocol=1;condition=operator-declared-opencode-go-route`
  after a live `initialize` (adapter and raw `dsh --profile acp` agree:
  protocol 1, agentInfo deepseek-harness-acp 0.0.1); the quirks sentence and
  `docs/api.md` name the launcher; the measured `reasoning_effort` value set
  is recorded. No harness was upgraded (the newest published launcher equals
  the installed one).
- **Content cycle** (`d8a100ec`): the post-v0.9.14 opening (four grok-bot pin
  paths back to R), per the a6af2d88 convention.

Out of this run by owner direction (Yanlei 22:10): the effort-max default
(#338) and the model-option-rejection refusal (#339) were drafted here, then
handed to their own seats as reference diffs and reverted from this branch;
they landed through their own runs.

## Candidate

Branch `workflow/issue-336`: `d8a100ec`, `b32a50fd`, `cb7e07a7`, `a6405400`,
`730ac436`, merge `b90559ef` (origin/main `c1d302af`: #337, #340, #339; the
only conflict was the adjacent suite registration in `scripts/validate.sh`,
resolved by keeping every suite). Validation record:
`kaola-workflow/issue-336/.cache/final-validation.md` (verdict pass, hash bound
to the candidate worktree).

## Evidence

- Field evidence: this MacBook's Host logs
  (`/tmp/kaola-501/zcode/zcode-KT-orchestrator-main/…/events.jsonl` cursors
  26833–26861, `/tmp/kaola-501/devin/devin-KT-orchestrator-main/…` cursors
  53–62) and the node log
  (`/tmp/kaola-501/zcode/zcode-KT-sideagent-node/…/events.jsonl` lines
  2081/2101: `[zcode turn failed] [1308]…`, `turn_ended` outcome
  `turn_completed` stop `refusal`).
- Suite `tests/contract/test-issue-336-node-turn-refusal.py` (13 cases: the
  three move paths incl. reason-text fallback, exhausted chain fails once and
  a binding change restarts, completed/partial turns stay Host-owned, node
  turn end names its stop reason, carrier root on the node start, explicit
  root under a failing `ps`, adoption of a ready / starting holder, never-ready
  holder stopped before the chain, unconfirmed stop after a move checked under
  the old runtime).
- Merged candidate: `./scripts/validate.sh --suite 336 --suite 324 --suite 293
  --suite 264 --suite 98 --suite 339 --suite 340 --suite 255` — all PASS,
  exit 0 (`/tmp/kpr336-suites-merged.log`); earlier on `b32a50fd`: 13 suites
  PASS (`/tmp/kpr336-suites-wt3.log`); `render-skills.py --check` PASS.
- Expert review report: `devin-KPR-i336-review` event log
  (`/tmp/kaola-501/devin/devin-KPR-i336-review/…/events.jsonl`), text at
  `/tmp/kpr-review-336.md`; its own read-only run of the 336 + 324 suites: OK.

## Known failures and unverified scope

- The fallback choice is in-memory: a restarted carrier tries the bound
  runtime first again (by design, #324); a runtime is never retried within a
  carrier's life until the binding changes (tried list).
- `_settle_node_batch` reads the binding at settle time: a Host rewrite of
  the binding *during* the node's turn would mark the new binding's platform
  tried (review nit 5, pre-existing structure, not changed).
- `_binding_key` includes `platform` while the `failed` fingerprint does
  not (review nit 8, pre-existing in #324).
- A deterministic prompt failure (#173 systemError, any JSON-RPC prompt
  error) now walks the whole chain once (one node start per runtime, no Host
  wake) before failing once — bounded, documented in the docstring.
- `KAOLA_ACP_RECORD_ROOT` is inherited by the node holder and its agent;
  harmless under the default root; a recipe `--record-root` still wins.
- No live dsh/zcode node run in this validation (fake-node fixtures); the
  Delegator's `record-root-mismatch` measurement is taken as given. The full
  inventory was not run (`--suite` subsets only).
- CHANGELOG untouched (release notes are prepared at release time); the
  holder, `platforms/`, and adapters changed, so the next release carries
  `Seats: restart required`. No tag/release/install; KPM mirror #441 exists
  (not touched).

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- docs/api.md
- platforms/dsh.yaml
- scripts/kaola-acp-holder.py
- scripts/validate.sh
- skills/antigravity-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/references/acp.md
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/platform.yaml
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- tests/contract/test-issue-293-node-record-roots.py
- tests/contract/test-issue-336-node-turn-refusal.py
- tests/contract/test-issue-98-dsh-acp.py

## Follow-Up Items

- None filed (owner rule: no new KPR issues). Candidates for the Delegator's
  judgement, from the review nits: binding snapshot at send time (nit 5) and
  the `failed` fingerprint including `platform` (nit 8).

Final readiness: ready — issue #336 closes on the merge sink.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-336/.cache/final-validation.md
- kaola-workflow/archive/issue-336/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-336/finalization-summary.md
- kaola-workflow/archive/issue-336/mission-ledger.jsonl
- kaola-workflow/archive/issue-336/workflow-state.md
