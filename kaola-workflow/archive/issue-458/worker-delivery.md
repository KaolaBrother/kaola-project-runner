# Issue #458 worker delivery

Candidate: `e2fa7291dfd6b0a627e6790cc761a3e1c6d44f23` on `workflow/issue-458`; base `b4a56118`. The worktree is clean. Host acceptance passed on 2026-11-02; live acceptance remains outstanding. No installation, Seat operation, KW rebind or live acceptance was performed under the owner hard stops.

The binding keeps its selected preset through recovery; default selection does not replace a configured unavailable preset. The carrier uses one start/admit/stop path for maintenance and sweeps, checks existing exact identities, and retains unresolved failures and stop duties. A Host can reconcile and recover the same preset or clear it with a current disable instruction while retaining pending work. The Sideagent uses the same start path as other roles. Checkpoint validation joins the carrier batch, node, native session, prompt and stream identity; a sweep does not acknowledge maintenance.

## Focused evidence

- `render-skills.py --write`, `--check`, and `git diff --check`: PASS. `validate.sh` selected nine suites: `test-devin-regressions.py` (34), `test-issue-244-dispatch.py` (80), `test-issue-255-lifecycle-state.py` (187), `test-issue-293-node-record-roots.py` (8), `test-issue-324-wake-fixes.py` (9), `test-issue-336-node-turn-refusal.py` (12), `test-issue-348-backstop-sweep.py` (34), `test-issue-350-computer-use-roles.py` (7), and `test-issue-421-retire-recovery.py` (51): 422 tests PASS, 213.599 s; clean exact sweep. See `evidence/focused.log.txt`.
- `test-acp-contract.py`: 89 PASS in 129.948 s in the earlier transport subset. That run also revealed two #244 failures from broadening the definition of an absent session; the candidate restored the prior ordinary-dispatch meaning and both cases and the complete #244 suite passed in the final run. The subsequent edit affected dispatch, not the ACP contract inputs. See `evidence/transport-first-run.log.txt`.
- In an isolated temporary copy, removing `exact_preset=preset` made `RecoverFailedSideagent.test_recovery_uses_recorded_preset_even_with_a_higher_ranked_alternative` fail. Removing the native stream mismatch check made `MaintenanceCheckpoint.test_native_receipt_mismatches_refuse_without_writes` fail because a mismatched checkpoint wrote state. The temporary copy was removed; neither mutation touched the candidate.
- Operator diff from `v0.9.40` includes `scripts/kaola-acp-holder.py`, `scripts/kaola-dispatch.py`, `scripts/kaola-acp-paths.py` and `scripts/kaola-record-contract.py`. **Seats: restart required.** No restart authorized or attempted.

## Design section 6 regression mapping

- Closed-origin issue independence, higher-ranked alternative, unavailable preset, and clear plus next bind: #421 `RecoverFailedSideagent` fixtures.
- Start, admission, turn and sweep failure, no fallback, occupied holder and unconfirmed stop: #255, #293, #324, #336 and #348 fixtures.
- Copied/forged batch, native identity and prompt mismatch, omitted recovery flags, partial checkpoints, newer inputs and old node writes: #255 checkpoint fixtures; the stream check also has the mutation above.
- Common lifecycle and distinct sweep accounting: #348 fixtures, including failure recovery and exact settlement; maintenance and worker return behavior: #255.
- Upgrade/transition: fixture coverage for legacy records and current source-backed recovery exists; no actual installed-runtime upgrade or interrupted consumer migration was exercised.

These are fixture and source results, not a live native start → batch → checkpoint → settlement → exact-stop chain. No claim is made that the KW incident is resolved or that combined runtime acceptance is complete.

## Project six-item scope at this worker delivery

1. Timer template fidelity and unavailable native readback: existing #255 fixture coverage, no new live timer verification.
2. Current typed information: #255 repeated-cycle and source/provenance fixtures pass; repeated consumer operation and bookkeeping recurrence remain unverified here.
3. Host autonomy and Sideagent lifecycle: focused carrier fixtures pass; no live Host/Sideagent activation or appointed integrated review in this worker delivery.
4. Recovery and informed autonomy: scoped fixture paths and the two mutation checks above pass; transient-service retry outcomes and other live combinations remain unverified.
5. Continuous improvement: this candidate removes the competing fallback paths and shares status/start sequencing. End-to-end delivery efficiency and independent public research were not measured in this run.
6. Future upgrade continuity: supported-old-record fixtures pass; actual installed holder/runtime migration and interruption recovery remain unverified.

The Host owns integrated review, authorization and the live disposition. This worker does not close the issue, archive, merge, publish, or claim final acceptance.
