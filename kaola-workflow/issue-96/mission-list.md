# Issue #96 — contract suites inherit KAOLA_PROJECT_RUNNER_CANONICAL_REPO and are refused against their own throwaway repos

Run posture: worktree `.kw/worktrees/issue-96`, branch `workflow/issue-96`,
baseline `a31fdc9`. Scope is test-harness isolation only. The Issue #73
production guard in `scripts/kaola-tmux.sh` is not touched, not narrowed, and
not globally unset; the #73 positive/negative boundary cases keep setting their
binding explicitly. Outer parent review holds ACCEPT; no finalize/archive/sink/
close/push until it lands.

## 1. Record the real baseline under an explicitly bound outer shell
- item: Run `./scripts/validate.sh` with `KAOLA_PROJECT_RUNNER_CANONICAL_REPO` explicitly exported to the outer KPR root, capturing the true exit code and the `Issue22KimiDefaultYoloAcpTests` failure text into this run's evidence. This is the failing baseline the fix must flip, and it proves the reproduction without asking anyone to run `env -u`.
- status: done
- dispatched: self (inline). Output lands at `kaola-workflow/issue-96/evidence/validate/baseline-env-bound-fail.log` with the recorded exit code.
- result: PARTIAL then completed by a narrower measurement, both docked. The full `validate.sh` run was killed with its session before the wrapper could write `VALIDATE_EXIT`, so `baseline-env-bound-fail.log` carries **no exit record** and none is claimed; what it does establish under an explicitly exported outer binding at `a31fdc9` is `render-skills: PASS`, both installer acceptances PASS, and exactly one suite failure, `FAILED: test-acp-contract.py`. The baseline was not re-run whole. `baseline-targeted-bound-fail.log` supplies the precise per-class baseline: `Issue22KimiDefaultYoloAcpTests` EXIT 1 with `FileNotFoundError: .../mock-events.jsonl`, and `test-issue-22-bypass-all-approvals.py::Issue22KimiAcpDefaultYolo` EXIT 1 with two failures (`[] is not true` and `no-session`). Neither failure names the refusal, confirming the issue's hypothesis and showing the misleading-failure symptom is not limited to the reported `FileNotFoundError`.

## 2. Narrow the affected inventory and apply the minimal harness fix
- item: Establish which suites actually reach the guarded entrypoint `scripts/kaola-tmux.sh` against a deliberately throwaway repo (vs. those invoking `scripts/kaola-acp.py` directly, which the guard does not gate), then fix only those by the convention already in the tree — `env.pop(CANONICAL_KEY, None)` plus the suite's own explicit binding where one is intended (#73), or the scrub-on-copy used by #88. Also make a refused `start` fail with the receipt itself rather than a downstream `FileNotFoundError` on the mock log. No new env framework, no production change, no broad rewrite.
- status: done
- dispatched: self (inline). Output lands as the working-tree diff on `workflow/issue-96` plus `evidence/validate/fixed-targeted-bound-pass.log` and `evidence/validate/refusal-receipt-shape.log`.
- result: Inventory narrowed by the guard's own trigger condition (`scripts/kaola-tmux.sh:158`: binding set AND (`--repo` omitted OR command is `start`)); the guard exists nowhere else, and `kaola-acp.py` reads only the derived `KPR_CANONICAL_REPO`. Exactly two classes execute a `start` through the entrypoint against a throwaway repo: `test-acp-contract.py::Issue22KimiDefaultYoloAcpTests` (in `validate.sh`) and `test-issue-22-bypass-all-approvals.py::Issue22KimiAcpDefaultYolo` (in `tests/test-issue-1-acceptance.sh`, not in `validate.sh` — which is why only one error surfaced). Every other entrypoint-executing suite uses `status`/`view`/`steer` **with** `--repo` and is not gated: `test-acp-watch-contract.py:600`, `test-issue-65-steering.py:161`, `test-issue-51-runner-integration.py:254`; `test-issue-88-permission-defaults.py:360` already scrubs the key; `test-issue-73-canonical-root.py` pops it and sets `bound=` explicitly on every case. Fix is additive only — 13 inserted lines, 0 deleted, across the two test files: a `CANONICAL_KEY` constant with a comment naming the standalone-invocation intent, one `env.pop(CANONICAL_KEY, None)` per suite env builder, and one `assertNotEqual(receipt.get("result"), "refused", ...)` before each existing `assertIsNone(error)` start assertion (three sites). No production file changed; the #73 guard is untouched and nothing is globally unset.

## 3. Prove the flip and the preserved boundaries
- item: Re-run `./scripts/validate.sh` under the same explicit outer binding and show it now passes; confirm the #73 canonical-root suite still exercises both the accepted and the refused case explicitly; run `./scripts/render-skills.py --check` and produce no generated diff. Dock the real exit lines as this run's evidence.
- status: in-flight
- dispatched: self (inline). Targeted and boundary evidence already landed under `kaola-workflow/issue-96/evidence/validate/`; the full `validate.sh` leg is held until Issue #95 sinks to `main` so it runs on the synced tree, and lands in the same directory.
- result:

## 4. Freeze the candidate and establish review readiness
- item: Commit claim, mission list, the fix, and the original evidence onto `workflow/issue-96` so the run is not a main-root-only record; freeze the SHA and hand the outer parent a report it can verify. Readiness only — finalization is not this list's to perform.
- status: todo
- dispatched:
- result:
