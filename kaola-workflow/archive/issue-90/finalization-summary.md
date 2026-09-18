# Finalization summary — issue-90

Issue: #90 — fix: ZCode Host 快速通知确认竞态与已确认事件去重
Branch: `workflow/issue-90` · Base: `1f01b3c` · Sink: merge
Accepted candidate: `c5155e5668d225eb5dbf209205679af4d9abea51` (outer ACCEPT, 2026-09-19)

## Delivered

Three defects in the ZCode Host worker-event carrier, all in `scripts/kaola-acp-holder.py`:

1. **Fast-response admission/confirmation race (the Issue's P1).** `_deliver_worker_events()` marked
   its staged events and snapped the overflow generation only AFTER `op_prompt(wait=False)` returned.
   `op_prompt` starts the turn's response thread before returning, so a Host answering at once ran
   `_worker_event_turn_end()` against an unmarked turn: it confirmed nothing and delivered the same
   events — and the same full-check generation — a second time. Snapshot, `_heartbeat_payload`,
   admission, marking, and the `worker_event_delivered` append are now ONE hold of the existing
   `worker_events_lock`, which the turn-end callback also takes. Marking follows a successful
   admission, so a refused or unwritten prompt leaves nothing to undo.
2. **Confirmed-`event_id` retry dedup (the Issue's P2).** `op_worker_event()` deduplicated only
   against `pending_worker_events`, from which a confirmed event has been removed, so a retry of the
   same deterministic id re-staged and re-prompted. A retry is now answered
   `{"duplicate": true, "confirmed": true}`.
3. **Retained-log semantics for that answer** (both found by outer review of intermediate
   candidates). The bounded in-memory index is a cache, not truth: each entry carries the event-log
   cursor its confirmation was recorded at, an entry whose record rotation has dropped stops being
   evidence, and any miss falls back to the `worker_event_confirmed` records themselves. The promise
   is therefore exactly as wide as the RETAINED event log — no fixed-id horizon — and the
   confirmation is appended before the events leave the pending list, so nothing observes an event as
   confirmed before the record that proves it exists.

No scheduler, no second queue or ledger, no broad gate, no permission change, no history rewrite.
Busy-host staging, failed-notification restaging, cap-32 overflow, and at-least-once resume of
genuinely unconfirmed events are unchanged.

## Issue statement walk

| Issue acceptance clause | satisfied by |
|---|---|
| Deterministic fake Host responding before `op_prompt(wait=False)` returns is RED on main, then GREEN: one prompt, one confirmation, no second prompt | `test_instant_response_does_not_double_prompt_a_staged_event`, `test_instant_response_confirms_a_full_queue_and_its_overflow_together`; RED on `1f01b3c`, GREEN at `c5155e5` |
| …include overflow generation in this race | `test_instant_response_does_not_double_prompt_the_overflow_full_check` (asserts `overflow_confirmed_generation` and the `worker_event_overflow_confirmed` record) |
| Retry same `event_id` after confirmation is ignored | `test_retry_of_a_confirmed_event_id_does_not_prompt_again`, `test_a_confirmed_retry_is_ignored_past_the_hot_cache_bound` (no 256-id exception), `test_a_cached_confirmation_that_rotated_away_is_deliverable_again` (the exact bound) |
| …but a new turn's distinct event is delivered | `test_a_distinct_later_event_is_still_delivered_after_a_confirmed_retry`, `test_a_new_event_is_still_delivered_past_the_hot_cache_bound` |
| Resume still redelivers unconfirmed and not confirmed | `test_resume_redelivers_unconfirmed_and_never_a_confirmed_event`, `test_resume_rebuilds_the_confirmed_memory_from_the_event_log`, `test_an_unconfirmed_event_past_the_bound_still_resumes` |
| Preserve at-least-once redelivery and cap-32/full-check behavior | `test_a_failed_notification_turn_leaves_the_event_redeliverable`, `test_admission_failure_marks_nothing_and_keeps_the_event_deliverable`, `test-zcode-heartbeat-contract.py` 15/15 (302 checks) unchanged |
| Focused ZCode heartbeat/overflow and adjacent tests | heartbeat, zcode-host, zcode-acp, issue-65 steer-race + host-contract, issue-70, issue-76, issue-68 — all PASS |
| `render-skills.py --check`, full `validate.sh`, `git diff --check`, candidate SHA and raw evidence | all recorded below |
| Work only in this Issue's run/worktree; outer review and ACCEPT before finalize; do not touch #75/#81 or global user settings | single worktree `.kw/worktrees/issue-90`; four review rounds; `#75`/`#81` branches untouched throughout |

## Files Changed

`scripts/kaola-acp-holder.py` (+174/−34 vs base), `scripts/validate.sh` (+2, suite registration),
`tests/contract/test-issue-90-event-confirmation-race.py` (new, 19 tests),
`tests/contract/test-zcode-heartbeat-contract.py` (+2, `bare_holder` fixture init only),
`docs/zcode-host.md`, `CHANGELOG.md`, and the nine generated
`skills/*/scripts/kaola-acp-holder.py` mirrors.

## Test Coverage

New suite `tests/contract/test-issue-90-event-confirmation-race.py` — 19 tests, in-process real
`Holder` with a stub agent, following `test-issue-65-steer-race.py`. Failure-first and **monotone**
across every candidate, one suite run against each:

| SHA | result |
|---|---|
| `1f01b3c` (base) | 16 RED |
| `19c04cc` (rejected: claim-stealing under concurrency) | 5 RED |
| `71173bc` (rejected: 256-id dedup exception) | 3 RED |
| `31fb665` (rejected: cached confirmation outliving its record; confirmation not durable before answerable) | 2 RED |
| **`c5155e5` (accepted)** | **19/19 OK** |

The fast-response and concurrent-admission guards still fail on `19c04cc`, so no earlier guard was
weakened by later work. The concurrency guard is deterministic in both directions (12/12 FAIL against
`19c04cc`, 12/12 PASS here); an earlier no-rendezvous version caught it only 1/15 and was discarded.

## Validation

- `verdict: pass` — `.cache/final-validation.md`, `validated_candidate_hash`
  `b210e0333a329aafa143f0f9d58bf9090da286551d070e7ed85d61c87c56b358`
- Exact command: `./scripts/render-skills.py --check && ./scripts/validate.sh`
- Full `./scripts/validate.sh` → **exit 0**, no FAILED/SKIPPED (`validate-issue-90.log`)
- `./scripts/render-skills.py --check` → PASS; all nine generated mirrors verified byte-identical
- `git diff --check` / `--cached` → clean
- finalize `--check` → `ok: true`, `validation: chains_green`, no reasons, no dirty paths
- Not executed: live tmux smoke per platform and live ZCode Host UAT (AGENTS.md integration
  validation). This change is holder-internal ACP carrier logic with no CLI, transport, or installer
  surface; the run was scoped ACP-only by the owner. Recorded as unexecuted, not as passed.

## Changed Paths

Reported by the finalize transaction (source-scoped; docs and CHANGELOG are outside its scope but
are in the commit):

`scripts/kaola-acp-holder.py`, `scripts/validate.sh`,
`skills/{claude-code,codex,cursor-cli,devin,droid,grok,kimi-cli,opencode,zcode}-kaola-project-runner/scripts/kaola-acp-holder.py`,
`tests/contract/test-issue-90-event-confirmation-race.py`,
`tests/contract/test-zcode-heartbeat-contract.py`

## Documentation Docking

`DOCKED` — `.cache/doc-docking.md`. `docs/zcode-host.md` and `CHANGELOG.md` updated;
`README.md`, `docs/api.md`, `docs/architecture.md` no impact with reasons;
`templates/orchestrator/references/zcode-host-dispatch.md.tmpl` verified consistent and deliberately
left unchanged (pinned by the Issue #65 contract, at its byte budget).

## Follow-Up Items

- **#91** (P3, OPEN) — `event_id` reuse after a worker record dir is lost could be swallowed as a
  confirmed retry. Raised by both independent reviews, not reproduced; filed as Hypothesis with a
  non-binding remedy. Issue #90 widened the dedup window from "pending only" to "retained log", which
  is what the Issue asked for, so this is residual risk rather than a regression.
- A correction comment was posted on #90 before closure recording that the delivered dedup contract
  is bounded by the retained event log, so the closed issue is not read as promising unconditional
  dedup forever.

## Readiness

READY — accepted candidate `c5155e5`, validation pass, docs docked, follow-up filed.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-90/.cache/doc-docking.md
- kaola-workflow/archive/issue-90/.cache/final-validation.md
- kaola-workflow/archive/issue-90/.cache/mirror-digest.json
- kaola-workflow/archive/issue-90/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-90/candidate-c5155e5.diff
- kaola-workflow/archive/issue-90/candidate-c5155e5.stat
- kaola-workflow/archive/issue-90/finalization-summary.md
- kaola-workflow/archive/issue-90/mission-list.md
- kaola-workflow/archive/issue-90/workflow-state.md
