# Finalization Summary — issue-421

## Delivered

The L2 cleanup gate is complete and proven. This issue is the Layer-2 cleanup
home (pair of KPM #893, per `owner-hb-two-layers-issues-do-sync-20261029`);
its KPR deliverable — the fail-closed mechanism every legacy shape clears
through, plus this repository's own cleanup — is merged and verified:

| Named shape | Merged route | Landed by |
|---|---|---|
| Sideagent `failed` binding recovery | `state ensure-sideagent --recover-failed` (dead old node proven from `--live`; no hold/decision may name it) | #421(a) `4671b965` |
| `kpm.dispatch-index/1.x` retire compat | index accepted by `project.canonical_root`; mirror never writes it | #421(b) |
| Reboot `/tmp` record loss | `index-stop-receipt` / `archived-ledger` stop-evidence kinds | #421(c) |
| Direct-dispatch accepted-done | `direct-dispatch` kind | #421(d) |
| Purged seat | `sweep-purge` kind | #421(e) |
| Session-gone unknown collect | `stale-collect-session-gone` | #426 |
| Tool-collected terminal items | `collect-terminal` with `acp_session_id`/holder/repo binding, unlinked rows accepted | #426 + #427 |
| Never-indexed dispatch refs | `refs-unindexed` (issue-number-bound, committed, fence-aware archive citation) | #426 |
| Escalated/closed hand-off items | `superseded` / `handed-off` dispositions settle | #427 |
| `maintenance-returned` bloat | coalescing by construction | #421 `b7caf9c2` |
| Finished rows / finished-work retention | P1 terminal-delete writer (never stores done; cite-bearing delete) | #425 |
| Unbounded duty strings | 512-byte bound, `field-too-large` | #425 |
| Orphan dispositions | `disposition-orphan` merged-relation refusal | #425 |

All of the above verified present on merged main `f5d4c3cb` (coverage grep
matrix; the initial `--recover-failed` miss was a grep-option artifact —
`ensure_sideagent_recover_command` / `recover_failed_sideagent` are in the
merged script).

## Live proof on this repository

- 10 legacy accepted-done rows retired with typed receipts (i369
  stale-collect; i371–i389 collect-terminal; i412 refs-unindexed @
  `e005402b`) — #426 run.
- The #426 and #427 runs' own task rows retired through the new routes
  (superseded dispositions settled; exact-reclaim) — #427 run.
- The #425 run's acceptance used the P1 terminal-delete path itself
  (`removed: true`, cite kept, dispatch refs as `unknown_refs`, rev 912).
- Heartbeat now: zero alerts, zero decisions, one task row
  (`profiles-20261026`).

## Known failures / honest boundary

- `profiles-20261026` stays: no conforming
  `kaola-workflow/archive/*/mission-ledger.jsonl` citation exists (Host-branch
  task; durable outcome in tag v0.9.30 + CHANGELOG). Widening the citation
  kinds is an owner-level design call, deliberately not made.
- Consumer rows (Claire's 15, Selena `i2255-x1`, shared `red-suites-420`)
  are NOT hand-cleared by KPR (per this issue's hardened scope): they clear
  through this gate by their own Hosts, or by Owner authorization. KPM-side
  clearing tracks in KPM #893.
- Live rebind/enable/sweep holds 46642/48182 are untouched by this settle and
  by this close-out.

## Validation

classification: final_validation_unverified
green: false
mode: final-validation

no agent validation evidence at /Users/ylpromax5/Workspace/kaola-project-runner-dev/.kw/worktrees/issue-421/kaola-workflow/issue-421/.cache/final-validation.md — a consumer (non-npm) repo records its validation in .cache/final-validation.md (with a column-0 `verdict: pass`), not a chain receipt

No agent validation evidence at .cache/final-validation.md. In a consumer (non-npm) repo the agent owns verification: record .cache/final-validation.md with the validation result + a column-0 `verdict: pass` before finalize.

## Changed Paths

none outside the kaola-workflow/ run-state band.

## Follow-Up Items

- Consumer cleanup execution: KPM #893 (its own acceptance).
- `profiles-20261026` citation-kind decision: owner call, recorded here.

## Citation

Closed by merge sink `19529c91` on main (issue #421, second finalize of the reopened L2 home; first-run archive preserved at `issue-421.archived-2026-10-29T08-13-23-000Z`). Mechanism landed across sinks `6207456f` (#421 round 1), `94d70828` (#426), `46629e47` (#427), `f5d4c3cb` (#425).

## Final readiness

Ready: KPR-side L2 deliverable complete (mechanism 13/13, live proofs, honest
residual); sink = merge (no code delta on this branch beyond run records),
close #421, archive/sink on -dev.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-421/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-421/finalization-summary.md
- kaola-workflow/archive/issue-421/mission-ledger.jsonl
- kaola-workflow/archive/issue-421/workflow-state.md
