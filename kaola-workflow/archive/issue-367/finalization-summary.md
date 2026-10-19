# Finalization Summary — issue-367

## Delivered

Every Worker grant is now a per-preset row: `authorization.worker_grants`
accepts only rows naming `preset_ids` with `count` a nonnegative integer or
the literal `unlimited`; the `scope: "all-worker-presets"` form is removed
from `delegator update`, the Host state authorization mirror, the delegator
view, and the dispatch ceiling. A stored scope row is expanded exactly once
by `delegator migrate` into one row per covered, non-excluded Worker preset
(count, state, and expiry preserved); afterwards the old form is refused and
no reader interprets it — `delegator view` flags a stored row's
`authorization.worker_grants[N].scope` path as an unknown entry and never
projects it as authorization. Exclusions remain a separate list and win over
grants, including `unlimited`. The Host `authorization.grants` mirror accepts
per-preset `count: "unlimited"`, so a numeric cap such as `dsh/default: 2`
is enforced beside unlimited rows.

## Candidate

Branch `workflow/issue-367`, one commit on `c84741fe` (current main):

- `6c8b3c51` Write every Worker grant as one per-preset row and retire the
  all-worker-presets scope form (#367): `scripts/kaola-record-contract.py`,
  `scripts/kaola-dispatch.py`, `docs/api.md`, `docs/dispatch-collect.md`,
  `tests/contract/test-issue-346-worker-grants.py`,
  `tests/contract/test-issue-350-computer-use-roles.py`, `CHANGELOG.md`
  Unreleased entry, and regenerated `skills/` + `hosts/` output.

Rebased per Host acceptance direction: the earlier cherry-picked
content-cycle commit was dropped as a duplicate of upstream `f37a1b54`; the
merged candidate carries #364's seven recovery-route rows untouched
(`git diff main..HEAD -- scripts/kaola-recovery-routes.py` is empty).

## Evidence

- Reproduction on baseline 72488b3c (in `/tmp/kpr-i367-repro`): (a) `delegator
  update` with a scope row mixed with named rows -> `refused` /
  `invalid-input` "one all-worker-presets row, or named preset rows, not
  both"; (b) a scope-only row was accepted (`"result":"written"`), proving
  the form was legal; (c) `state update --section authorization` with
  `{"id":"devin/default","count":"unlimited"}` -> `refused` `invalid-input`
  "nonnegative integer, excluding boolean".
- Post-fix: scope-only and mixed updates refuse `invalid-input` naming
  `preset_ids` / one row per preset and the `delegator migrate` route;
  `delegator migrate --write` expanded a stored scope row into 5 covered,
  non-excluded per-preset `unlimited` rows; `state update` accepted
  `unlimited` and `2` rows; dry-run ceiling allowed 2× `dsh/default`,
  refused a 3rd (`count`), kept unlimited `devin/default` runnable and
  `codex/luna` `excluded`.
- `./scripts/render-skills.py --check` -> PASS on the rebased candidate.
- `./scripts/validate.sh --suite` on the rebased candidate `6c8b3c51`, all
  OK: test-issue-346-worker-grants (14), test-issue-350-computer-use-roles
  (7), test-issue-309-recovery-routes (8), test-issue-295-delegator-seats
  (10), test-issue-244-dispatch (80), test-issue-218-preset-ids (17),
  test-issue-74-kaola-delegator (231 assertions, 0 failed),
  test-issue-345-worker-pool (2), test-issue-324-wake-fixes (10),
  test-issue-259-record-contract (63), test-issue-296-shared-tier-seats
  (10), test-issue-294-expert-ceiling (9), test-issue-273-list-identity (9),
  test-issue-111-model-tiers (25).
- Recorded receipt: `kaola-workflow/issue-367/.cache/final-validation.md`
  (verdict pass, bound to the candidate tree hash).
- Host acceptance: user verified `count:"unlimited"` writes on a state-file
  copy with this worktree's tools (the path v0.9.21 installs refuse),
  confirmed the 346 suite, and ordered rebase + finalize.

## Known failures or unverified scope

- The 133-suite full inventory was not run on this candidate; per AGENTS.md
  the focused suites plus render check were the agreed scope, and the Host
  runs the full inventory at its own boundary.

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
- skills/antigravity-kaola-project-runner/scripts/kaola-record-contract.py
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
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
- tests/contract/test-issue-346-worker-grants.py
- tests/contract/test-issue-350-computer-use-roles.py

## Follow-Up Items

None filed: the run discovered no new defect. The issue body needed no
correction — both defect faces reproduced as written.

## Readiness

Ready for merge-sink close-out. `Seats: restart required` —
`scripts/kaola-record-contract.py` is in the operator restart set
(`docs/conventions.md`); a running seat keeps the old grant validation until
it restarts. The Grok Bot bridge stays at the unpinned content stage; the
pin returns at the next release commit.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-367/.cache/final-validation.md
- kaola-workflow/archive/issue-367/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-367/finalization-summary.md
- kaola-workflow/archive/issue-367/mission-ledger.jsonl
- kaola-workflow/archive/issue-367/workflow-state.md
