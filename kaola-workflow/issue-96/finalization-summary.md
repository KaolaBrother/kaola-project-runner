# Finalization — Issue #96

test: contract suites inherit `KAOLA_PROJECT_RUNNER_CANONICAL_REPO` and are refused against
their own throwaway repos.

Branch `workflow/issue-96`, sink `merge`, baseline `a31fdc9`, synced onto `main` `baf12f0`
after Issue #95 sank. Outer parent ACCEPTed the frozen candidate `b986be7`.

## Delivered

Two contract classes start a worker through `scripts/kaola-tmux.sh` against their own
throwaway repository, but built the child environment from a bare `dict(os.environ)`. An
operator shell bound as a Project Runner control plane leaked
`KAOLA_PROJECT_RUNNER_CANONICAL_REPO` into those starts, so the Issue #73 guard refused them
before the mock ACP agent was spawned. Because a refusal receipt carries `result`/`reason` and
no `error`, each suite's `assertIsNone(receipt.get("error"))` passed and the failure surfaced
one line later as something unrelated.

Both suites now drop the binding — the convention already used by
`test-issue-73-canonical-root.py:116` and `test-issue-88-permission-defaults.py:360` — and each
start asserts the receipt is not `refused` before the existing error assertion, so a refusal
reports its own receipt.

The scope held: **no production file changed**, the Issue #73 guard is untouched and unweakened,
and nothing is unset globally. Production Runner commands still require the binding.

## Files Changed

Source diff vs `main`: **2 files, +13/-0**, both tests.

- `tests/contract/test-acp-contract.py` — `CANONICAL_KEY` constant with an intent comment; one
  `env.pop` in `Issue22KimiDefaultYoloAcpTests.env()`; one refusal assertion.
- `tests/contract/test-issue-22-bypass-all-approvals.py` — same constant; one `env.pop` in
  `Issue22KimiAcpDefaultYolo.env()`; two refusal assertions.
- `CHANGELOG.md` — one `## Unreleased` entry.

## Test Coverage

The core proof is the red/green flip under an **explicitly exported** outer binding — no
`env -u` anywhere, at any step.

| evidence | baseline (bound) | candidate (bound) |
|---|---|---|
| `Issue22KimiDefaultYoloAcpTests` | EXIT 1, `FileNotFoundError: .../mock-events.jsonl` | EXIT 0 |
| `Issue22KimiAcpDefaultYolo` | EXIT 1, `[] is not true` + `no-session` | EXIT 0 |
| `./scripts/validate.sh` | `FAILED: test-acp-contract.py` | `VALIDATE_EXIT=0`, 34 OK, no FAILED/SKIPPED |
| `test-issue-73-canonical-root.py` | — | 29/29 OK, boundary cases unweakened |
| `render-skills.py --check` | PASS | PASS, no generated diff |

Honest limit on the first baseline: `evidence/validate/baseline-env-bound-fail.log` was killed
with its session before the wrapper could write an exit line. It carries **no `VALIDATE_EXIT`
record and none is claimed**. What it does establish at `a31fdc9` under the binding is
`render-skills: PASS`, both installer acceptances PASS, and exactly one suite failure,
`FAILED: test-acp-contract.py`. The precise per-class baseline is
`baseline-targeted-bound-fail.log`; the full baseline was not re-run.

`refusal-receipt-shape.log` measures why the old assertion let the refusal through: the receipt
carries `result=refused`, `reason=canonical-root-mismatch`, `mutation_performed=false`, exit 1,
and **no `error` key**. That is what the added `assertNotEqual(result, "refused")` catches.

## Validation

- verdict: **pass**
- command: `KAOLA_PROJECT_RUNNER_CANONICAL_REPO=/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner ./scripts/validate.sh`
- receipt: `.cache/final-validation.md`, recorded from the candidate worktree.
- Post-freeze mutation: the `CHANGELOG.md` entry changed bytes after `b986be7`. The one suite
  that reads `CHANGELOG.md` was re-run rather than the whole suite —
  `test-issue-49-grok-bot-host.py` 43 OK, plus `test-issue-24-opencode-pty-bypass.py` 14 OK and
  `render-skills.py --check` PASS (`evidence/validate/post-doc-docking-affected.log`).

## Changed Paths

Reported by the finalize transaction (`checks.changed_paths`), source-scoped, so it omits docs
and run records:

- `tests/contract/test-acp-contract.py`
- `tests/contract/test-issue-22-bypass-all-approvals.py`

`dirty_paths` empty; `validation: chains_green`; `staging_guard: ok`. The full branch diff
against `main` is 16 paths: those 2 test files, `CHANGELOG.md`, and 13 run records under
`kaola-workflow/issue-96/`.

## Documentation Docking

`DOCKED` — `.cache/doc-docking.md`. `CHANGELOG.md` updated; `README.md:258`, `docs/api.md:227`,
`docs/architecture.md:231`, and `AGENTS.md` verified no-impact because they describe the
unchanged production guard. No document instructed `env -u`, so no stale workaround needed
retracting.

## Issue statement coverage

- *Measured* section's reproduction — satisfied by `baseline-targeted-bound-fail.log` and
  `fixed-targeted-bound-pass.log`.
- *Hypothesis* — confirmed. `dict(os.environ)` leaks the binding; the guard refuses before the
  mock spawns; `reason` not `error` is why `assertIsNone(error)` passed. All four parts measured.
- *"other contract suites that start against temp repos may share the shape"* — confirmed and
  resolved. The guard fires only when the binding is set **and** (`--repo` omitted **or** command
  is `start`) — `scripts/kaola-tmux.sh:158` — and exists nowhere else; `kaola-acp.py` reads only
  the derived `KPR_CANONICAL_REPO`. Exactly one other class shares the shape,
  `test-issue-22-bypass-all-approvals.py::Issue22KimiAcpDefaultYolo`, which runs under
  `tests/test-issue-1-acceptance.sh` and not `validate.sh` — which is why only one error ever
  surfaced. Every remaining entrypoint-executing suite uses `status`/`view`/`steer` **with**
  `--repo` and is ungated (`test-acp-watch-contract.py:600`, `test-issue-65-steering.py:161`,
  `test-issue-51-runner-integration.py:254`). The suite Issue #95 added,
  `test-issue-95-reader-exception.py`, was re-checked after the merge and drives `kaola-acp.py`
  directly, so it is not gated.
- *Proposed remedy* — followed as written, including "nothing here argues for weakening or
  narrowing the Issue #73 guard".

## Follow-Up Items

None filed. No run-discovered defect: the one adjacent finding — the sibling suite sharing the
defect — was in scope for this issue's own "other suites may share the shape" clause and is
fixed here rather than deferred. The pre-existing fact that
`test-issue-22-bypass-all-approvals.py` is absent from `scripts/validate.sh` is longstanding and
recorded in `kaola-workflow/archive/issue-22/.cache/review-test-custody.md`; this run did not
change the validate lists and does not reopen that decision.

## Readiness

READY. Accepted at `b986be7` by the outer parent; docs docked and affected evidence re-run after
the one post-freeze doc mutation.
