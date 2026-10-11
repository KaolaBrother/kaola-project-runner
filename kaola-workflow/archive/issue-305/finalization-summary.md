# Finalization summary — issue-305

## Delivered

Fix for #305: the all-idle wake is now sent when nothing is left running
— including the case where the Sideagent node or the last dispatched seat
stops after the Host's final turn.

- `scripts/kaola-acp-holder.py`: a confirmed `sideagent_node_stopped`
  and a dispatched worker `terminated` event re-check the all-idle
  condition after the Host's last turn end. The all-idle scan
  (`holders_dispatched_by(..., working=True)`) additionally skips a
  just-terminated worker whose record still says `ready` (its
  `terminated` event precedes the `agent_exited` record write). One idle
  episode sends exactly one wake (`_all_idle_woken` episode latch under
  a lock — a latch, not a timer); the wake payload is `state end_turn`,
  `state_detail end_turn`, `reason all-idle`, through the existing gated
  path with `holder_instance_id + event_seq` dedupe. Exact stop still
  sends only `exact_stop`.
- The turn-end case (node alive but exempt via #303's predicate) is
  covered by a dedicated test and passes.
- Tests: `test-issue-302-delegator-wake-gate.py` extended with 8 cases:
  turn-end all-idle while the node stays alive; node stop after an idle
  turn sends exactly one; node-stop skip when the Host is not idle; last
  worker stop after the turn wakes all-idle once; a live worker blocks
  all-idle until it stops; node-stop skip while a worker seat works;
  same event posts once and the episode latch holds; exact stop does not
  also send all-idle.
- `docs/api.md` (+41) and the Delegator Skill reference via render;
  CHANGELOG Unreleased bullet (holder changed — restart required,
  consistent with the batch's line).

## Candidate

- Implementation commit `6d73daae` on `workflow/issue-305` (worktree
  `.kw/worktrees/issue-305`, base `9c544984`; message amended from
  `d8fef2a9` to drop accidental pasted shell text — tree identical).
  Implemented by the `grok/default` seat `grok-KPR-i305-allidle`;
  reviewed and finalized by the Host.

## Evidence

- Host diff review (this run): all six assignment acceptance cases plus
  two skip-cases verified present and green; the episode latch is not a
  time throttle; dedupe intact.
- `./scripts/render-skills.py --check` — PASS.
- Affected suites, all exit 0: `test-issue-302-delegator-wake-gate.py`
  (updated), `test-issue-299-delegator-webhook.py`,
  `test-issue-255-lifecycle-state.py`,
  `test-issue-296-shared-tier-seats.py`, `test-issue-271-dispatch-help.py`,
  `test-issue-289-dead-holder-stop.py` (logs `/tmp/kpr-i305-*.log`).
- `.cache/final-validation.md`: verdict `pass`, candidate hash
  `54d3c8099b667964…`.
- Worker seat exact-stopped after acceptance (`state: stopped`).

## Known failures / unverified scope

- Full inventory runs immediately after this merge as the v0.9.8 release
  gate, per the run plan.

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
- scripts/kaola-record-contract.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/kaola-record-contract.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/kaola-record-contract.py
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-record-contract.py
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/kaola-record-contract.py
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/kaola-record-contract.py
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/kaola-record-contract.py
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/kaola-record-contract.py
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-delegator/references/webhook-wake.md
- skills/kaola-project-runner/scripts/kaola-record-contract.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-record-contract.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/kaola-record-contract.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/kaola-record-contract.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/kaola-delegator/references/webhook-wake.md
- tests/contract/test-issue-302-delegator-wake-gate.py

## Follow-Up Items

- None. With #303, #304 and #306 already merged, this completes the
  owner's four-issue batch.

## Final readiness

Ready: candidate reviewed, affected scope green, validation recorded.
Proceed to sink (merge) and archive.
