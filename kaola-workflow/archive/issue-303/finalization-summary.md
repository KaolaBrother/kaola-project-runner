# Finalization summary — issue-303

## Delivered

Fix for #303: the Host's own bound Sideagent node no longer occupies a
shared seat group.

- `scripts/kaola-record-contract.py`: new shared predicate
  `seat_exempt_record` — true when a record's `session_role` is
  `sideagent` or legacy `sidekick` (`_start_node` passes
  `--role sideagent`; the child persists that role; there is no separate
  node flag).
- `scripts/kaola-acp-holder.py` / `scripts/kaola-acp.py`:
  `holders_dispatched_by` skips seat-exempt records, so the node is not
  counted as a live seat (the shared root with #305); dispatch admission
  skips those live rows in shared occupancy, occupant naming, and the
  live-seat session set.
- `scripts/kaola-dispatch.py`: the exemption applied on the admission
  path; a genuine worker record still occupies and a `shared-occupied`
  refusal still names it.
- Tests: `test-issue-255-lifecycle-state.py` (+39) and
  `test-issue-296-shared-tier-seats.py` (+32) — a planted live node
  record (sideagent role, Host as dispatcher) lets admission proceed
  within the shared group; a live worker record still blocks beyond the
  count with the occupant named.
- Docs: `docs/dispatch-collect.md`, `docs/api.md`,
  `templates/orchestrator/references/dispatch-collect.md`; CHANGELOG
  Unreleased — **Seats: restart required** (holder and record contract
  changed).

## Candidate

- Implementation commit `51c87afa` on `workflow/issue-303` (worktree
  `.kw/worktrees/issue-303`, base `24b08d58`). Implemented by the
  `grok/default` seat `grok-KPR-i303-seat-exempt`; reviewed and finalized
  by the Host.

## Evidence

- Host diff review (this run): exemption derived from the record's own
  `session_role`; worker-seat behavior non-regressed; the #305
  `live_seats` half is pre-fixed by the same predicate.
- `./scripts/render-skills.py --check` — PASS.
- Affected suites, all exit 0: `test-issue-296-shared-tier-seats.py`,
  `test-issue-255-lifecycle-state.py`, `test-issue-295-delegator-seats.py`,
  `test-issue-302-delegator-wake-gate.py`,
  `test-issue-299-delegator-webhook.py`, `test-issue-271-dispatch-help.py`
  (logs `/tmp/kpr-i303-*.log`).
- `.cache/final-validation.md`: verdict `pass`, candidate hash
  `c3228d1f84ddd5ac…`.
- Worker seat exact-stopped after acceptance (`state: stopped`).

## Known failures / unverified scope

- The sink rebases onto the #304-advanced main (both issues changed
  `kaola-acp.py` copies); the integrated tree is re-verified after the
  merge. Full inventory at the v0.9.8 release boundary.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/api.md
- docs/dispatch-collect.md
- scripts/kaola-acp-holder.py
- scripts/kaola-acp.py
- scripts/kaola-dispatch.py
- scripts/kaola-record-contract.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-record-contract.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-record-contract.py
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-record-contract.py
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-record-contract.py
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-record-contract.py
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-record-contract.py
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-record-contract.py
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/references/dispatch-collect.md
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kaola-project-runner/scripts/kaola-record-contract.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-record-contract.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-record-contract.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-record-contract.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/orchestrator/references/dispatch-collect.md
- tests/contract/test-issue-255-lifecycle-state.py
- tests/contract/test-issue-296-shared-tier-seats.py

## Follow-Up Items

- #305 (all-idle stop-time re-check) builds on this predicate as its own
  claim, per the run plan.

## Final readiness

Ready: candidate reviewed, affected scope green, validation recorded.
Proceed to sink (merge) and archive.
