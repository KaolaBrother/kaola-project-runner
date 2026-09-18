# Finalization Summary — Issue #71

主 Skill 的实际字节上限比 budgets.json 低 59 B，且无人声明

- run: issue-71 · branch `workflow/issue-71` · sink `merge` · issue #71
- candidate accepted by the outer coordinator: `c19cdde4113792bfd8ac68881c740dd1d37296f8`
- missions: 4, all `done`; no `BLOCKED`, no open in-flight item
- exclusive mainline sink: this run only; other co-active runs (`issue-67`, `issue-70`, `issue-72`) not merged here

## Delivered

The #49 pin/host invariance probe no longer appends 59 B to canonical templates. It applies
equal-length substitutions of unique existing spans so `templates/budgets.json`
`main_skill_bytes` **17408** is the ceiling `render-skills.py --check` already reports.

The edit still lands (rendered main Skill bytes change, unique markers appear in the matching
products) and host products stay byte-identical. A real host-template edit is a live counterexample
that the comparison has teeth. Padding to the declared ceiling still renders; one extra byte is
refused and not written. No second budget system, no raised budgets, no edit to Issue #72
surfaces, no generated-file hand-edit.

## Files Changed

4 files, +92/−10 against main `b229f84`.

| File | What |
|---|---|
| `tests/contract/test-issue-49-grok-bot-host.py` | equal-length `CANONICAL_INVARIANCE_EDITS`; size/content assertions; host-template counterexample; near-ceiling + over-by-1 B test |
| `docs/architecture.md` | one sentence: equal-length probe, `budgets.json` is the only ceiling |
| `docs/conventions.md` | one sentence under progressive-disclosure budgets |
| `CHANGELOG.md` | Unreleased bullet |

`templates/budgets.json` unchanged (`main_skill_bytes` 17408). `templates/grok-golden/`
byte-identical. Nothing under `skills/` or `hosts/` was hand-edited. Rendered main Skill remains
**17337 B** (71 B headroom against the declared ceiling).

## Test Coverage

- `Issue49BridgeInvariance` — 3 tests: pin/host invariance with equal-length edits, declared-ceiling
  probe that does not spend budget, over-budget bridge/revision refusals unchanged.
- Full `tests/contract/test-issue-49-grok-bot-host.py` — 43 tests.
- `RendererEnforcesBudgets` still fails a true over-budget product.

Not a new budget engine. The old 59 B append remains a failing contrast in
`kaola-workflow/issue-71/evidence/postfix-near-budget.txt`.

## Validation

Recorded by `kaola-workflow-validation-runner.js` from the candidate worktree (see
`.cache/final-validation.md`). This project has no `test:kaola-workflow:*` chains, so
`run-chains.js` does not apply.

| Check | Result | Artifact |
|---|---|---|
| Baseline trap (pre-fix, temp copy, HEAD untouched) | pad to 17405 `--check` 0; +59 B append `--write` 1, `17464 B > 17408 B` | `evidence/baseline-repro.txt` |
| Post-fix near-budget | 17405 + equal-length: size 17405, `--check` 0, host unchanged; old append still 17464 | `evidence/postfix-near-budget.txt` |
| `Issue49BridgeInvariance` at `c19cdde` | 3/3 OK, 3.494s | `evidence/invariance-at-c19cdde.txt` |
| full `test-issue-49-grok-bot-host.py` | 43/43 OK, 27.620s | `evidence/test-issue-49.txt` |
| `./scripts/render-skills.py --check` at `c19cdde` | PASS, budgets OK | `evidence/render-check-at-c19cdde.txt` and finalize re-run |
| `./scripts/validate.sh` | exit 0 on the candidate bytes (second run 181.52s; first-run flake on unrelated `test-issue-51` isolated 6/6) | `evidence/validate.sh-2.log`, `evidence/test-issue-51-isolated.txt`, finalize re-run |
| Outer ACCEPT | independent `Issue49BridgeInvariance` 3/3 exit 0 and `render --check` 0; real test diff reviewed | this conversation |

## Changed Paths

(filled by the finalize transaction)

## Acceptance

- **Automated / local.** `./scripts/render-skills.py --check` exit 0 and `./scripts/validate.sh`
  exit 0 on the frozen candidate. Exact command recorded in `.cache/final-validation.md`.
- **Outer coordinator review.** Formal ACCEPT of `c19cdde4113792bfd8ac68881c740dd1d37296f8`:
  real test diff reviewed; equal-length replacement lands in products and host products stay
  identical; full-budget pass and +1 B reject covered; independent `Issue49BridgeInvariance`
  3/3 exit 0 and `render --check` 0.
- **Not executed.** No live tmux/CLI smoke (no transport byte changed), no release, no global
  install, no personal memory.

## Issue statement walk

| Issue #71 clause | Satisfied by |
|---|---|
| undeclared 59 B deduction from `main_skill_bytes` 17408 | baseline: 17405 `--check` green, +59 B probe red at 17464; `evidence/baseline-repro.txt` |
| probe is for #49 pin invariance, append is a side-effect | equal-length substitutions in `test_pin_changes_exactly_one_line_and_canonical_or_manifest_edits_change_nothing` |
| any of: `--check` prints effective ceiling; probe that does not spend budget; or document 17349 | chose the second: probe no longer spends budget, so 17349 is not a live ceiling and is not introduced as a new number |
| next run must not hit an unpublished red line the way #68 did | declared 17408 is the only ceiling; near-ceiling still passes; +1 B still fails |
| worker templates likely same class of gap | same four-file equal-length helper covers worker template, transport reference, and grok-bot-host reference |

No clause unsatisfied. **Issue correction** (comment before close): the body's 17349 figure
described the pre-fix append side-effect; after `c19cdde` it is not a live limit.

## Follow-Up Items

None filed. #73 is a user-authorized next task for a **new** session after exact-stop; this
session does not claim it. The first `validate.sh` flake on `test-issue-51-runner-integration.py`
passed in isolation (6/6) and on the successful full re-run; not a product defect of this run.

## Documentation Docking

`DOCKED` — `.cache/doc-docking.md`. Candidate already carries CHANGELOG / architecture /
conventions. README, api, grok-bot-host, AGENTS, setup/install: no-impact reasons recorded.
No extra production docs at finalize.

## Final readiness

Ready to archive, merge-sink, close #71, publish main, audit, and remove only this run's
worktree and `workflow/issue-71` branch. Other runs, accepted checkouts, and credentials
untouched.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-71/.cache/doc-docking.md
- kaola-workflow/archive/issue-71/.cache/final-validation.md
- kaola-workflow/archive/issue-71/.cache/mirror-digest.json
- kaola-workflow/archive/issue-71/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-71/evidence/baseline-repro.txt
- kaola-workflow/archive/issue-71/evidence/budgets-at-c19cdde.txt
- kaola-workflow/archive/issue-71/evidence/commit.txt
- kaola-workflow/archive/issue-71/evidence/delivery.md
- kaola-workflow/archive/issue-71/evidence/diff-vs-main.patch
- kaola-workflow/archive/issue-71/evidence/finalize-render-check.txt
- kaola-workflow/archive/issue-71/evidence/invariance-at-c19cdde.txt
- kaola-workflow/archive/issue-71/evidence/postfix-near-budget.txt
- kaola-workflow/archive/issue-71/evidence/render-check-at-c19cdde.txt
- kaola-workflow/archive/issue-71/evidence/render-check.txt
- kaola-workflow/archive/issue-71/evidence/shas.txt
- kaola-workflow/archive/issue-71/evidence/test-issue-49.txt
- kaola-workflow/archive/issue-71/evidence/test-issue-51-isolated.txt
- kaola-workflow/archive/issue-71/evidence/test-progressive-budget.txt
- kaola-workflow/archive/issue-71/finalization-summary.md
- kaola-workflow/archive/issue-71/mission-list.md
- kaola-workflow/archive/issue-71/workflow-state.md
