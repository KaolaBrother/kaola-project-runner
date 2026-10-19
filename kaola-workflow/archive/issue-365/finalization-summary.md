# Finalization Summary — issue-365

## Delivered

`op_rebind_heartbeat_host` in `scripts/kaola-acp-holder.py` now moves the seat's
recorded `dispatcher` quadruple (`platform`, `session`, `repo`,
`holder_instance_id`) to the verified replacement Host in the same locked
mutation as `heartbeat_host`. Before this change the op updated only the
carrier, so a rebound worker's record still named the stopped Host: the new
Host's working-seat scan never counted it, and its turn-end check emitted
`reason: all-idle` wakes while that worker was mid-turn (the reported four
wakes at event_seq 650/1432/3784/3946 inside the worker turn
18:27:06→19:12:42). A rebind call without `host_holder_instance_id` is refused
before any mutation as `missing-host-holder-instance-id`; recovery is to rerun
`rebind-host` from inside the replacement Host session so the verified
dispatcher supplies the ID. The rebind receipt now returns `dispatcher`, and
the `heartbeat_host_rebound` event records both the previous and the new
dispatcher. Existing refusal precedence is unchanged: invalid target, then
`no-heartbeat-host`, then `heartbeat-host-foreign-repo`, then the new missing
holder-ID refusal, then mutation. `docs/api.md` and `docs/conventions.md` now
describe the carrier and the recorded dispatcher moving together; generated
skill copies were rerendered.

## Candidate

Branch `workflow/issue-365`, one commit on main `c84741fe` (the post-release
content-cycle base; the branch was fast-forwarded there before the change, so
its diff carries no routing-line regression):

- `159a9fbd` Move a rebound seat's recorded dispatcher to the replacement Host
  (#365): `scripts/kaola-acp-holder.py` + regenerated `skills/` copies +
  `tests/contract/test-issue-302-delegator-wake-gate.py` (new
  `test_rebound_busy_worker_blocks_all_idle_until_it_stops`) +
  `tests/contract/test-issue-255-lifecycle-state.py` (record `dispatcher`
  assertion on the in-place rebind test) + `CHANGELOG.md` Unreleased +
  `docs/api.md` + `docs/conventions.md`.

## Evidence

- Reproduction before the fix, record shape (`/tmp/repro-365.py`, same tree):
  rebind changed `heartbeat_host` but `record["dispatcher"]` still named the
  old Host; `holders_dispatched_by(new_host_holder_id, working=True)` returned
  `[]`, so the turn-end reason resolved to all-idle while the worker's
  `last_prompt.mutation_status` was `in_progress`.
- Reproduction before the fix, wire level: the new WakeGate test was run once
  against a temporary pre-fix `op_rebind_heartbeat_host`; the record kept
  `dispatcher` on the old Host and the new Host holder POSTed
  `reason: all-idle` (event_seq 8) while the rebound worker was mid-turn —
  the same shape as the reported wakes.
- After the fix, same repro and same test: `record["dispatcher"]` equals the
  replacement Host quadruple, the busy rebound worker is counted as a live
  seat, no all-idle is sent while `mutation_status` is `in_progress`, and the
  all-idle wake is emitted after the worker is stopped — matching the
  reported correct wake at event_seq 4824 (19:15:13, after the worker's
  exact-stop at 19:13:19).
- `./scripts/validate.sh --suite test-issue-302-delegator-wake-gate.py` →
  `Ran 39 tests`, `OK` (author and Host, Host re-run on this candidate).
- `./scripts/validate.sh --suite test-issue-255-lifecycle-state.py` →
  `Ran 166 tests`, `OK` on the author's run.
- `./scripts/render-skills.py --check` → `PASS` (11 workers + orchestrator +
  delegator + grok-bot bridge, content stage, budgets OK); also PASS inside
  each suite run.
- Recorded receipt: `kaola-workflow/issue-365/.cache/final-validation.md`
  (verdict pass, validated_candidate_hash 003a45d58251…).
- Host acceptance: the acceptor re-ran both suites on this candidate —
  302 suite 39/39 OK; 255 suite 164/166 with two `HolderNodeMode` batch
  timeouts that also time out on main `c84741f` under local load (timing
  sensitivity, recorded below, not caused by this diff).

## Known failures or unverified scope

- Host observation on this candidate: `test-issue-255-lifecycle-state.py`
  showed 164/166, the two failures being `HolderNodeMode` batch waits that
  timed out; the same two tests time out on unmodified main `c84741f` on this
  machine under load. Judged load-sensitive timing, not a regression of this
  change; recorded here per the acceptor's instruction. Author-side run of
  the same suite on the same bytes: 166/166 OK.
- The full suite inventory was not run on this candidate; the focused suites
  plus the render check were the agreed scope, and the Host runs the full
  inventory at its own boundary.
- `Seats: restart required` — the diff touches `scripts/kaola-acp-holder.py`
  (the operator restart set), so already-running holders keep the old
  single-field rebind until restarted.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/api.md
- docs/conventions.md
- scripts/kaola-acp-holder.py
- skills/antigravity-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- tests/contract/test-issue-255-lifecycle-state.py
- tests/contract/test-issue-302-delegator-wake-gate.py

## Follow-Up Items

None filed: the run discovered no new defect. The issue body needed no
correction — the fix and tests land exactly the body-stated acceptance
(`dispatcher` rewritten to the new Host; no all-idle while the rebound worker
is busy). The two `HolderNodeMode` timeouts observed by the Host reproduce on
unmodified main and are recorded under Known failures rather than as a
follow-up, per the acceptor's ruling.

## Readiness

Ready for merge-sink close-out. `Seats: restart required` — the diff touches
`scripts/kaola-acp-holder.py`, which is in the operator restart set.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-365/.cache/final-validation.md
- kaola-workflow/archive/issue-365/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-365/finalization-summary.md
- kaola-workflow/archive/issue-365/mission-ledger.jsonl
- kaola-workflow/archive/issue-365/workflow-state.md
