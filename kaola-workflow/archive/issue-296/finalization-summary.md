# Finalization summary — issue-296

## Delivered

Fix for #296: one grouped grant row can express a shared tier group plus a
tier-specific extra seat, so the owner policy "Claude Code 2 seats total =
1 shared across default/sonnet/fable + 1 default-only" is writable,
admissible, and correctly capped.

- Re-check at current main (`06632a44`, recorded in the suite docstring):
  still reproducing — the policy shape could not be written
  (`one authoritative row per preset`; `count: 2` on the shared group
  over-grants sonnet/fable), `delegator update` refused a preset listed
  once in `elite_grants` and once in `expert_task_grants` (the ceiling
  reader already allowed that overlap), and a `shared seat occupied`
  refusal did not name the occupant. Already fixed by #294/#297 (not
  treated as a bug here): the `default: 2` + shared-pair workaround does
  admit a second default seat, though it totals 3.
- `scripts/kaola-dispatch.py`: `extra_seats` on the one grouped grant row
  adds seats for named member presets only; the seat summary reports the
  per-runtime total (2 here) while sonnet/fable stay at the shared
  contribution of 1; admission counts against that total and admits the
  second seat within it; a `shared-occupied` refusal now carries
  `seat_occupants` naming the occupying session and
  `holder_instance_id`. `delegator update` accepts a preset once in
  `elite_grants` and once in `expert_task_grants` (legal overlap).
- `scripts/kaola-record-contract.py`: `extra_seats` is a typed grant field
  (positive integers, member presets only) with blockers and retention
  across update merges; the holder pins this module, so the CHANGELOG
  entry states **Seats: restart required**.
- Tests: `tests/contract/test-issue-296-shared-tier-seats.py` (8 cases,
  412 lines) — update acceptance/refusal, host-update shape validation,
  total 2 with sonnet/fable at 1, admission against the per-runtime
  total, occupant-named refusal + count-2-stays-pool, the workaround
  still totaling 3, fable expert gating, elite-window scoping.
- Docs: `docs/dispatch-collect.md`, `docs/api.md`; CHANGELOG Unreleased.

## Candidate

- Implementation commit `3246a74a` on `workflow/issue-296` (worktree
  `.kw/worktrees/issue-296`, base `06632a44`). Implemented by the
  `grok/default` seat `grok-KPR-i296-seat-shape`; reviewed and finalized
  by the Host.

## Evidence

- Host diff review (this run): acceptance items 1–3 verified; #294 owner
  rules non-regressed (294/295 suites green).
- `./scripts/render-skills.py --check` — PASS.
- Affected suites, all exit 0: `test-issue-296-shared-tier-seats.py`
  (new), `test-issue-294-expert-ceiling.py`,
  `test-issue-295-delegator-seats.py`, `test-issue-271-dispatch-help.py`,
  `test-issue-259-record-contract.py`, `test-issue-292-state-record-root.py`,
  `test-issue-298-absent-decision-retire.py` (logs `/tmp/kpr-i296-*.log`).
- `.cache/final-validation.md`: verdict `pass`, candidate hash
  `78dc150ae3cbc717…`.
- Worker seat exact-stopped after acceptance (`state: stopped`).

## Known failures / unverified scope

- Full inventory runs after the #299 merge (the run's final gate), per
  the run plan. No release in this run per the owner boundary.

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
- scripts/kaola-dispatch.py
- scripts/kaola-record-contract.py
- scripts/validate.sh
- skills/claude-code-kaola-project-runner/scripts/kaola-record-contract.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/kaola-record-contract.py
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/kaola-record-contract.py
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/kaola-record-contract.py
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/kaola-record-contract.py
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/kaola-record-contract.py
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/kaola-record-contract.py
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kaola-project-runner/scripts/kaola-record-contract.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-record-contract.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-record-contract.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-record-contract.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- tests/contract/test-issue-296-shared-tier-seats.py

## Follow-Up Items

- #299 (webhook wake) remains in flight on its own branch; merged after
  its review.

## Final readiness

Ready: candidate reviewed, affected scope green, validation recorded.
Proceed to sink (merge) and archive.
