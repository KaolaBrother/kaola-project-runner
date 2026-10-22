# Finalization Summary — Issue #396

## Delivered

Issue #396's Expert admission now reports a conflicting `special_requirements` exactly like Elite.

- `ceiling_block()`'s Expert fast path returned `None` before reading `ceiling["problems"]`, so a
  Host/Delegator literal `special_requirements` conflict that Elite reports as `ceiling-incomplete`
  still admitted the Expert preset; `execute` shared the same path.
- The Expert fast path now returns an already-recorded problem for the preset before admitting the
  choice. `project` withholds the preset, `project --seats` marks it unavailable with
  `idle_available` 0, and `execute` refuses `not-run` / `ceiling-incomplete` with the Host and
  Delegator original text in evidence.
- Conflict-free Experts (identical text, one-sided, or no special requirements) still pass; Elite
  behavior, the #376 grant flattening and unrelated ceiling reasons are untouched.
- `tests/contract/test-issue-396-ceiling-conflict.py` (5 cases) covers the Expert conflict, Elite
  symmetry, the conflict-free Expert paths and both `execute` paths, with the pre-fix silent-pass
  counter-proof. It is registered in `scripts/validate.sh`.
- The generated Skill payload and build stamps are re-rendered; `CHANGELOG.md` carries the
  user-visible entry.

Candidate: `974934d7` on `workflow/issue-396`; base `19254c57`. This run performed no tag,
release, publish, install, or KPM-side operation.

## Acceptance Evidence

- Host acceptance passed, followed by an independent astra lightweight review PASS: 27/27 CLI
  checks, 21 files byte-identical to the baseline, and mutation capture.
- Pre-fix counter-proof on the same tree before the fix, `tests/contract/test-issue-396-ceiling-conflict.py`:
  `FAILED (failures=2, errors=1)` — the Expert conflict was a `project` candidate, had no seat
  `unavailable` row, and `execute` returned `dry-run`; Elite and conflict-free cases passed.
  Log: `/tmp/kpr396-prefix-suite.log`.
- Final focused validation on clean tip `974934d7`, exit 0, 8 suites / 283 tests, all `OK`
  (total wall 141.277 s; no residual pids):
  `./scripts/validate.sh --suite test-issue-396-ceiling-conflict.py --suite test-issue-376-authorization-shape.py --suite test-issue-294-expert-ceiling.py --suite test-issue-295-delegator-seats.py --suite test-issue-296-shared-tier-seats.py --suite test-issue-255-lifecycle-state.py --suite test-issue-264-validate-lane-integrity.py --suite test-issue-259-record-contract.py`
  Log: `/tmp/kpr396-final-focused.log`.
- Additional affected set on the same content, all `OK`: `test-issue-244-dispatch.py`,
  `test-issue-346-worker-grants.py`, `test-issue-345-worker-pool.py`,
  `test-issue-118-seat-cap.py`, `test-issue-111-model-tiers.py`,
  `test-issue-123-shared-refs.py`, `test-generated-skills.py`,
  `test-progressive-disclosure.py`.
- `./scripts/render-skills.py --check`: PASS (11 workers + orchestrator + delegator + Grok Bot
  bridge; content stage; budgets OK). `render-skills.py --write` was run before the check.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
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
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- tests/contract/test-issue-396-ceiling-conflict.py

## Known Failures and Unverified Scope

- No full-inventory `./scripts/validate.sh` run: the selected suites cover the changed admission
  decision, the seat/execute surfaces, the #376 authorization contract, the #255 lifecycle state,
  the #264 lane integrity and the adjacent ceiling/worker suites.
- No live platform ACP UAT was run for this change; the suite exercises the dispatch CLI paths.

## Follow-Up Items

- No follow-up issue was filed by this run.

## Readiness

Ready for the merge sink. The candidate is committed on `workflow/issue-396`, acceptance is
recorded, and there is no tag, release, publish, install or KPM-side operation in this run.
Seats: restart required.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-396/.cache/final-validation.md
- kaola-workflow/archive/issue-396/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-396/finalization-summary.md
- kaola-workflow/archive/issue-396/mission-ledger.jsonl
- kaola-workflow/archive/issue-396/workflow-state.md
