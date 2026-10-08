# Finalization summary — issue-294

## Delivered

Fix for #294: `delegator_ceiling` reads `expert_task_grants` (per-task or
standing, with `expires`), Elite `expires` is the time window, and the two
owner seat rules from the issue comments are implemented, documented and
tested. Delegator-granted Expert seats now pass admission within their
grant; refusals are honest (`expired`, `lifetime-unreadable`,
`expiry-unreadable`), never `above-ceiling` by accident.

- `scripts/kaola-dispatch.py`: `delegator_ceiling` parses both grant lists
  (shape errors scoped per list); `admission_ceiling` merges expert facts
  for admission; `ceiling_block`/`ceiling_count` handle the Expert class
  through `expert_ids`/`expert_problems`; `_parse_elite_grants` treats
  Elite `expires` as the window (past → `expired`, unparseable →
  `expiry-unreadable`) and no longer reports `ceiling-incomplete` for a
  lifetime outside task/standing when a readable window exists (the
  claude-code/fable case); `_parse_expert_grants` models Expert as
  per-task/standing with optional expiry; a shared group keeps ONE count
  across its tiers and an Expert choice in it still needs its own
  expert row (`above-ceiling` without one); the Expert lifetime/expiry
  never attaches to the group's Elite choices.
- `docs/dispatch-collect.md`: both owner rules stated in the existing
  section style (shared seat = one count; Elite = time-windowed with
  expiry; Expert = per-task/standing; Expert-only presets never Elite).
- Tests: `tests/contract/test-issue-294-expert-ceiling.py` (5 cases, 316
  lines) — admission + view-flag separation, omitted lifetime → task,
  honest refusals, shared-group one-count with separate Expert clock in
  both occupancy directions, Elite window + fable lifetime matrix;
  registered in `validate.sh`. CHANGELOG entry (dispatch CLI only; the
  Unreleased section's restart-required still reflects the #292/#293
  holder changes).
- Scope boundary kept: the delegator VIEW seats/authorized_total is #295
  and was not changed.

## Candidate

- Implementation commit `788ebbb8` on `workflow/issue-294` (worktree
  `.kw/worktrees/issue-294`, base `a60201e0` = current main). Implemented
  by the `grok/default` seat `grok-KPR-i294-ceiling`; reviewed and
  finalized by the Host.

## Evidence

- Host diff review (this run): both owner rules verified against the code
  path-by-path (see ledger m2).
- `./scripts/render-skills.py --check` — PASS.
- Affected suites, all exit 0: `test-issue-294-expert-ceiling.py` (new),
  `test-issue-271-dispatch-help.py`, `test-issue-259-record-contract.py`,
  `test-ddd-pack.py`, `test-issue-244-dispatch.py`,
  `test-issue-273-list-identity.py`, `test-issue-292-state-record-root.py`,
  `test-progressive-disclosure.py` (logs `/tmp/kpr-i294-*.log`).
- `.cache/final-validation.md`: verdict `pass`, candidate hash
  `3a306fcd610363dfc13390e52f447bba4d972f4554e3a7b58e8fb2b3e3c5a612`.
- Worker seat exact-stopped after acceptance (`state: stopped`).

## Known failures / unverified scope

- Full inventory and per-platform live ACP smoke deferred once to the
  release boundary over the integrated candidate, as recorded for #292
  and #293 (evidence reuse policy).

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/dispatch-collect.md
- scripts/kaola-dispatch.py
- scripts/validate.sh
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- tests/contract/test-issue-294-expert-ceiling.py

## Follow-Up Items

- #295 (delegator view seats) remains open by design and is next in this
  run's frontier.

## Final readiness

Ready: candidate reviewed, affected scope green, validation recorded.
Proceed to sink (merge) and archive.
