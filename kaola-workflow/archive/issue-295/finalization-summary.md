# Finalization summary — issue-295

## Delivered

Fix for #295: the Delegator seat view lists every authorized seat from
both `elite_grants` and `expert_task_grants`, and its totals match
`project --seats`.

- `scripts/kaola-dispatch.py`:
  - `seat_summary` now reads the same admission ceiling as `execute`:
    after the host-grant pass, a second pass adds every Elite/Expert
    preset the ceiling authorizes that the host grants omit (count from
    `ceiling_count`), reported unavailable with the honest reason
    `host-grant-missing` — authorized, not silently dropped. Admissible
    Worker-pool presets are listed in a new `worker_pool` field without
    counting as seats. `expert_authorization` reflects real Expert
    presence.
  - `delegator_seats` (the `kaola-delegator-heartbeat/1` both-keys
    path): a legal elite/expert overlap (an Expert choice named in a
    shared elite row that also has its own expert row) is one grant, not
    a duplicate; `worker_pool` presets are appended as plain granted rows
    so the view and `project --seats` see the same set.
- Tests: `tests/contract/test-issue-295-delegator-seats.py` (5 cases,
  261 lines) — `state view --role delegator` lists Expert grants;
  `project --seats` summary matches the view totals; delegator view host
  and fallback paths; host-omitted Delegator grant is
  `host-grant-missing`; shared Expert choice without its own expert row
  stays out. Registered in `validate.sh`; CHANGELOG entry (dispatch CLI
  only; section restart still reflects the holder changes); one docs
  sentence in `docs/dispatch-collect.md`.

## Candidate

- Implementation commit `396195f9` on `workflow/issue-295` (worktree
  `.kw/worktrees/issue-295`, base `74927063` = current main). Implemented
  by the `devin/opus-fusion` seat `devin-KPR-i295-seats`; reviewed and
  finalized by the Host.

## Evidence

- Host diff review (this run): seat-source and total derivation verified
  path-by-path (see ledger m2).
- `./scripts/render-skills.py --check` — PASS.
- Affected suites, all exit 0: `test-issue-295-delegator-seats.py` (new),
  `test-issue-294-expert-ceiling.py`, `test-issue-271-dispatch-help.py`,
  `test-issue-259-record-contract.py`, `test-issue-244-dispatch.py`,
  `test-issue-273-list-identity.py` (logs `/tmp/kpr-i295-*.log`).
- `.cache/final-validation.md`: verdict `pass`, candidate hash
  `fa1208d2108c078d98cc809436e5f6c8f2035f9d0ed9f05ce2d2733f14474acf`.
- Worker seat exact-stopped after acceptance (`state: stopped`).

## Known failures / unverified scope

- The full `validate.sh` inventory and the per-platform live ACP smoke
  run immediately next, at the release boundary over the integrated
  candidate (#292–#295 together), per the recorded plan.

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
- tests/contract/test-issue-295-delegator-seats.py

## Follow-Up Items

- None. All four issues of this run's fix batch (#292–#295) are closed
  or closing; the release is the remaining run step.

## Final readiness

Ready: candidate reviewed, affected scope green, validation recorded.
Proceed to sink (merge) and archive.
