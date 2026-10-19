# Finalization Summary — issue-328

## Delivered

Antigravity worker `antigravity-KPR-i328-midturn-steer` (antigravity/default) made agy mid-turn
steer work end to end. Original commit `5a502d83`; the Host rebased onto main `8c26a705` (which
had gained #331) with a union CHANGELOG resolution, final candidate `3dff38da`.

**Chosen delivery mode: native mid-turn steer over `_session/steering`.**

- **Live experiments (agy 1.3.5, isolated temp repos, `i328-` prefixed sessions)**: stream-json
  `control_request` and leading-slash commands end the session (exit 2); a mid-turn
  `{"event":"user",...}` on stdin is buffered by agy's stream reader and runs on the same process
  right after the in-flight turn; `SIGINT` mid-turn emits `status: "ERROR", error: "interrupted"`
  (exit 1) while persisting the conversation on disk (including on Turn 1), resumable via
  `agy --conversation <id>`.
- **Implementation** (`scripts/kaola-antigravity-acp.py`): `_meta.steering.supported = true` and
  `_session/steering` (`on_session_steering`) — in-turn writes go to the running child's stdin,
  the resulting agy turn is coalesced under the active ACP `session/prompt` request id; leading
  `/` text refused (`-32602`); when no native turn runs (including the holder's settle window)
  it returns `promptRequired`, composing with #326's after-turn queue; `session/cancel` maps the
  interrupted exit to `stopReason: "cancelled"`, records the persisted conversation, and respawns
  the child with `--conversation` (also behind `--steer-mode interrupt`). `step_epoch` tool-id
  namespacing keeps re-launches clean.
- **Manifest** (`platforms/antigravity.yaml`): `acp_steer_method: "_session/steering"`
  (`steering_delivery: "after-turn"` removed), `native_steering: "supported"`, updated
  `acp_quirks`/`steering_summary`, `acp_verified_versions:
  cli=1.3.5;protocol=1;condition=live-one-turn-two-turn-resume-steer-cancel`.
- **Live acceptance evidence**: real receipts — Turn 1 (secret token), Turn 2 (`sleep 12`),
  mid-turn `steer --steer-mode interrupt` (`cancel-confirmed`, resent), capture verified the
  token recall, exact-stop clean; all sessions stopped.
- **Tests**: `mock-agy.py` models the real in-turn stdin buffering and SIGINT exit; new unit +
  end-to-end coverage in `test-issue-323-antigravity-acp.py` (in-turn write + coalescing, slash
  refusal, idle/`expectedTurnId` mismatch `promptRequired`, composition with #326
  `_queue_after_turn`, interrupt+`--conversation` resend). Renders within budget
  (`steering.md` 8164/8192 B). `delegator_turn_wake_reason` ordering and queue handling
  unchanged. CHANGELOG Unreleased (union with #331), `Seats: restart required`.

## Candidate

Branch `workflow/issue-328`, rebased single commit `3dff38da` over main `8c26a705`.
Recorder-bound hash: `6f7f063b1bf227b5…`.

## Evidence

- Dispatch fp `71ee51ed…`; experiment sessions (`i328-live-steer`, `i328-live-verify`) each
  stopped cleanly (terminated exit 0 receipts delivered to this Host).
- Worker runs on pre-rebase `5a502d83`: 323 suite 58 OK; **full inventory 114 suites rc=0**
  (1270.95 s).
- Host runs on the rebased final candidate `3dff38da`: **full inventory rc=0** (1267.9 s,
  proxies and ambient `KAOLA_ACP_DISPATCHER` unset); `render-skills.py --write`/`--check` PASS
  (no re-render delta); suites 323 and 331 green standalone.
- Validation record: `kaola-workflow/issue-328/.cache/final-validation.md` (verdict pass).

## Known failures and unverified scope

- Live verification covered one-turn, two-turn, resume, mid-turn native steer, and
  cancel/interrupt+resume on macOS agy 1.3.5; longer multi-concurrent stress and non-macOS agy
  behavior are not separately tested (declared in the manifest's `acp_quirks`/
  `acp_verified_versions`).
- The worker's final turn ended with a stream `turn_failed` marker after the complete report was
  emitted; no content was lost (capture verified).
- Running Antigravity seats keep the old adapter process until restart (`Seats: restart
  required`); nothing installed.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- platforms/antigravity.yaml
- scripts/kaola-antigravity-acp.py
- skills/antigravity-kaola-project-runner/references/acp.md
- skills/antigravity-kaola-project-runner/references/steering.md
- skills/antigravity-kaola-project-runner/scripts/kaola-antigravity-acp.py
- skills/antigravity-kaola-project-runner/scripts/platform.yaml
- tests/contract/mock-agy.py
- tests/contract/test-issue-323-antigravity-acp.py

## Follow-Up Items

- None filed (no new KPR issues without owner direction).
- searched: duplicate probe not applicable (owner-filed issue).

## Final readiness

Ready: candidate accepted (live evidence + worker full inventory + Host full inventory on the
final rebased candidate), validation recorded pass, no tag/release/install performed.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-328/.cache/final-validation.md
- kaola-workflow/archive/issue-328/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-328/finalization-summary.md
- kaola-workflow/archive/issue-328/mission-ledger.jsonl
- kaola-workflow/archive/issue-328/workflow-state.md
