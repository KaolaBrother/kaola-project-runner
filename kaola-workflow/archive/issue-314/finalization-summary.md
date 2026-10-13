# Finalization summary — issue-314

## Delivered

Fix for #314: the all-idle wake counts only seats with an active turn;
an idle held seat (ready, awaiting acceptance, no turn) no longer
silences an idle Host.

- `scripts/kaola-acp-holder.py`: the all-idle scan
  (`holders_dispatched_by(..., working=True)`) now reads
  `last_prompt.mutation_status` from each dispatched seat's
  `record.json` — `in_progress` and `accepted` block; `completed`,
  `not_started`, a missing turn, and no `last_prompt` do not; an
  unrecognized turn state still blocks (conservative). No new IPC: the
  record's own admission-written field is the source. #307 semantics
  unchanged (episode latch, Delegator-turn rules, stop re-checks).
- Tests: `test-issue-302-delegator-wake-gate.py` (+281 lines, 6 new
  cases): turn-state classification; idle held seat wakes all-idle
  exactly once; completed record → one all-idle in process; active turn
  blocks until it ends; active → completed wakes once at the
  transition; unknown turn state blocks.
- `docs/api.md` (+24) and the Delegator Skill reference via render;
  CHANGELOG Unreleased — **Seats: restart required** (holder changed).

## Candidate

- Implementation commit `05ca53ef` on `workflow/issue-314` (worktree
  `.kw/worktrees/issue-314`, base `6386e4b6`). Implemented by the
  `grok/default` seat `grok-KPR-i314-idle-seat`; reviewed and finalized
  by the Host.

## Evidence

- Host diff review (this run): turn-state source verified
  (admission-written `last_prompt.mutation_status`, no new IPC);
  conservative unknown-blocks proven; #307 cases intact.
- `./scripts/render-skills.py --check` — PASS.
- Affected suites, all exit 0: `test-issue-302-delegator-wake-gate.py`
  (updated), `test-issue-299-delegator-webhook.py`,
  `test-issue-255-lifecycle-state.py`, `test-zcode-heartbeat-contract.py`,
  `test-issue-271-dispatch-help.py` (logs `/tmp/kpr-i314-*.log`).
- `.cache/final-validation.md`: verdict `pass`, candidate hash
  `3b8124971cd45ed0…`.
- Worker seat exact-stopped after acceptance (`state: stopped`).

## Known failures / unverified scope

- #315 (decision registration + fallback) follows as its own run on
  this scan change. No release (owner releases).

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/api.md
- scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kaola-delegator/references/webhook-wake.md
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- templates/kaola-delegator/references/webhook-wake.md
- tests/contract/test-issue-302-delegator-wake-gate.py

## Follow-Up Items

- None.

## Final readiness

Ready: candidate reviewed, affected scope green, validation recorded.
Proceed to sink (merge) and archive.
