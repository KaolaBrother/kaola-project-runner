# Finalization summary — issue-315

## Delivered

Fix for #315: a registered Delegator decision wakes; an otherwise-silent
Host turn falls back to all-idle; the skill text requires decision
registration; the compaction-reload dead-wake suspicion is closed.

- `scripts/kaola-acp-holder.py`:
  - Open `state.decisions` rows classify as `needs_decision` and **win
    over all-idle**, including when the episode latch is already set and
    including the turn that follows a compaction reload (the suspected
    dead path — the registered decision at 18:38 that never woke; the
    classifier now sees registered decisions regardless of episode
    state).
  - A Host turn end with no active seat turn and no registered decision
    falls back to the existing `all-idle` wake, once per idle episode
    (#307 latch respected).
- Skill/templates (rendered): the orchestrator `SKILL.md`,
  `references/lifecycle-state.md`, and the Delegator
  `webhook-wake.md` state that any point requiring a Delegator decision
  MUST be a `state.decisions` row — points left only in
  `.kaola/run/*.md` or turn text leave the runner blind (the observed
  16:55–18:40 block).
- Tests: `test-issue-315-decision-wake.py` (6 cases): open registered
  decision rows classify; rendered skills require registration; a
  registered pending decision wakes `needs_decision` (not all-idle); a
  silent turn falls back to all-idle exactly once; a registered
  decision still wakes after a compaction reload; an active seat keeps
  current behavior. The 302 suite adjusted.
- `docs/api.md` (+49); CHANGELOG Unreleased — **Seats: restart
  required** (holder changed, consistent with #314's line).

## Candidate

- Implementation commit `18414637` on `workflow/issue-315` (worktree
  `.kw/worktrees/issue-315`, base `e9475237`). Implemented by the
  `grok/default` seat `grok-KPR-i315-decisions`; reviewed and finalized
  by the Host.

## Evidence

- Host diff review (this run): needs_decision precedence over the latch
  proven including the post-compact-reload scenario; fallback is the
  existing all-idle wake with its episode semantics; skill texts
  rendered within budgets.
- `./scripts/render-skills.py --check` — PASS.
- Affected suites, all exit 0: `test-issue-315-decision-wake.py` (new),
  `test-issue-302-delegator-wake-gate.py`, `test-issue-299-delegator-webhook.py`,
  `test-issue-255-lifecycle-state.py`, `test-progressive-disclosure.py`,
  `test-zcode-heartbeat-contract.py` (logs `/tmp/kpr-i315-*.log`).
- `.cache/final-validation.md`: verdict `pass`, candidate hash
  `6a8f172a71d622fb…`.
- Worker seat exact-stopped after acceptance (`state: stopped`).

## Known failures / unverified scope

- No release (owner releases). Live-end observation happens at the
  owner's install step.

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
- scripts/validate.sh
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-delegator/references/webhook-wake.md
- skills/kaola-project-runner/SKILL.md
- skills/kaola-project-runner/references/lifecycle-state.md
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/kaola-delegator/references/webhook-wake.md
- templates/orchestrator/SKILL.md.tmpl
- templates/orchestrator/references/lifecycle-state.md
- tests/contract/test-issue-302-delegator-wake-gate.py
- tests/contract/test-issue-315-decision-wake.py

## Follow-Up Items

- None.

## Final readiness

Ready: candidate reviewed, affected scope green, validation recorded.
Proceed to sink (merge) and archive.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-315/finalization-summary.md
