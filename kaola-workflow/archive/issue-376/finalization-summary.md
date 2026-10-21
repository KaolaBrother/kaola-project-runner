# Finalization Summary — Issue #376

## Delivered

`project` / `execute` now reject a Delegator heartbeat's split grants shape supplied as
`--authorization` instead of normalizing it to an empty grant list and projecting granted
Elite/Expert seats as `host-grant-missing`. The refusal is shape-based: `elite_grants`,
`expert_task_grants`, or `worker_grants` without flat `grants`, or either shape together with
flat `grants`, exits 2 with the Host input and Delegator-view guidance. An empty Delegator
authorization (no split keys) remains an empty Host authorization and is accepted; a test pins
that distinction.

The split-to-flat conversion used by the Delegator seat view is now the shared
`flatten_delegator_grants()` helper with token-level equivalent behavior. `execute` still does
not adopt the Delegator ceiling as Host grants. `docs/dispatch-collect.md`, the orchestrator
reference, and the generated Skill state the contract, including the restored #377 480-char
excerpt sentence and the split-shape exit code. No tag, release, install, or KPM-side change was
made by this run.

## Candidate

Branch `workflow/issue-376` at `259692b36ed02556d729fe7a96e28f262f8e65e9` (`docs: restore
excerpt contract and shape wording (#376)`), on top of `ae289e8e7d0d7f583b1c189ac0fd0f0151a6b24d`
(`fix: reject Delegator heartbeat as --authorization input (#376)`), based on main `4ccdd4c2`.
The tip was accepted after independent review; the prior accepted engineering candidate was
`ae289e8e`, and `259692b3` only corrected the reviewed documentation/template defects.

## Evidence

- Host acceptance in conversation: verdict accepted at `259692b3`; independent review's
  engineering evidence remains valid.
- Mutation evidence reported by the independent review: removing the shape guard turned 10
  issue-376 cases red; deleting the helper's `extra_seats` mapping turned #296 red.
- `tests/contract/test-issue-376-authorization-shape.py` — split rejection, mixed-shape
  rejection, empty-authorization acceptance, Delegator-view equivalence, exclusions/shared
  groups, and documentation assertions (11 tests).
- `./scripts/validate.sh --suite test-issue-376-authorization-shape --suite
  test-issue-244-dispatch --suite test-issue-295-delegator-seats` — 11, 80, and 10 tests,
  all OK at `259692b3`.
- `./scripts/render-skills.py --check` — PASS; template and generated reference are 8190 B.
- Earlier focused runs from the accepted candidate: `test-issue-255-lifecycle-state` 171 tests
  OK; `test-issue-294-expert-ceiling`, `test-issue-296-shared-tier-seats`,
  `test-issue-346-worker-grants` 14 tests OK.
- Post-change split/flat output artifacts: `/tmp/kpr376/after-376/`.

## Known failures or unverified scope

- The focused suites and renderer were run; `KAOLA_FULL_GATE=1 ./scripts/validate.sh` was not run
  by this run, per the Host's final-gate boundary.
- The KT flat authorization still reports the pre-existing `claude-code/opus-xhigh`
  `ceiling-incomplete` caused by Host/Delegator `special_requirements` literal-text mismatch
  (the independent second gap in the #376 research), which is outside this issue's orientation b
  and was not changed.
- No product code change was introduced by `259692b3`; it restores reviewed documentation and
  assertions only.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- docs/dispatch-collect.md
- scripts/kaola-dispatch.py
- scripts/validate.sh
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/references/dispatch-collect.md
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/orchestrator/references/dispatch-collect.md
- tests/contract/test-issue-376-authorization-shape.py

## Follow-Up Items

- None filed by this run. The remaining KT `special_requirements` mismatch is already documented
  in the #376 research as a separate gap; no duplicate issue was created.

Readiness: accepted candidate at `259692b3`, focused suites and renderer green, ready to merge,
archive, and close.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-376/.cache/final-validation.md
- kaola-workflow/archive/issue-376/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-376/finalization-summary.md
- kaola-workflow/archive/issue-376/mission-ledger.jsonl
- kaola-workflow/archive/issue-376/workflow-state.md
