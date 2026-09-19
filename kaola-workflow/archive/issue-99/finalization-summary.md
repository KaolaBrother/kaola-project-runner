# Finalization summary — issue-99

Issue: #99 — Design: make `KAOLA_ACP_HEARTBEAT_HOST` binding mechanical on the Project Runner dispatch path
Run type: design-only (no implementation authorized; implementation waits for a separate authorization)
Candidate: d300c7a on `workflow/issue-99` (identical to `main`; zero source bytes changed)
Acceptance: design accepted by the Host on 2026-09-20 with the owner's 2026-09-19 rulings recorded in place.

## Delivered

- `evidence/heartbeat-auto-bind-design.md` (≈38 KB), covering the five required sections:
  - (a) enforcement point: holder → agent identity fact `KAOLA_ACP_DISPATCHER` (one ZCode-bridge allowlist entry), `kaola-acp.py start` derives and verifies the binding, refuses before anything is probed or spawned;
  - (b) failure shape: `result: refused`, exit 1, reasons `heartbeat-host-unresolved`, `heartbeat-host-conflict`, `heartbeat-host-pty-unsupported`; receipt fields `heartbeat_host_source`, `dispatcher`;
  - (c) relation to the #70 receipt contract, the `permission_required` → `permit` flow, the Delegator's receipt habit; PTY handling;
  - (d) compatibility for live `heartbeat_host: null` sessions and pre-change Hosts (documented restart residual);
  - (e) acceptance cases N1–N8 (incl. N6b–N6d), P1–P10, one live smoke;
  - (f) per-paragraph prose-reduction inventory across `templates/orchestrator/` and `templates/kaola-delegator/` with the test pins that retire or move.
- Owner rulings recorded 2026-09-19: PTY under a ZCode Host is always refused with `heartbeat-host-pty-unsupported` (allow-with-`pty-no-carrier` rejected); Runner dispatch on the Project Runner path is ACP-only for every Host, not only ZCode.

## Files Changed

None in the repository source. Run records only: `kaola-workflow/issue-99/{workflow-state.md, mission-list.md, finalization-summary.md, evidence/heartbeat-auto-bind-design.md, .cache/*}`.

## Test Coverage

Not applicable — no behaviour changed. The design lists the tests an implementation must add and the existing pins it must move (design §e, §f.8).

## Validation

- Command: `./scripts/render-skills.py --check` in the candidate worktree — PASS (9 workers + kaola-project-runner + kaola-delegator + grok-bot bridge; budgets OK).
- Recorded: `.cache/final-validation.md`, `verdict: pass`, `validated_candidate_hash: 9bda8b0589cf5a4e3a040f1c32f6c741d10558d275a66291f11ca51b00537f55`.
- `./scripts/validate.sh` and live tmux smoke: not run — the candidate has no source diff, so there is no changed behaviour to exercise; recorded here as unexecuted rather than implied.
- Acceptance legs: manual (Host review of the design document) — accepted; automated/local/UAT — not applicable to a design deliverable.

## Changed Paths

(finalize transaction findings land here)

## Documentation Docking

`.cache/doc-docking.md` — DOCKED. No public behaviour changed; the design itself carries the exact docs/template paragraphs the implementation issue must update (§f.7) so they change together with the script behaviour.

## Issue statement walk

- Type/scope (design only, no `~/.dsh/`, no grok-golden): satisfied — no source changes at all.
- Gap statement: restated with line citations (design §1).
- Requested outcome 1 (automatic binding, refuse on failure): design §a–§b.
- Requested outcome 2 (prose reduction, per paragraph): design §f.
- Must-cover a–e: design §a–§e.
- Deliverable path: `kaola-workflow/issue-99/evidence/heartbeat-auto-bind-design.md`.

## Follow-Up Items

- Implementation of the design is a separate, not-yet-authorized issue; none filed by this run (filing it is the owner's call, and the design document is the spec it would cite).
- No run-discovered defects.

## Readiness

READY — all four missions done, validation recorded, docs docked, design accepted. Closure decision: close #99 (design delivered and accepted); sink kind `merge` per `workflow-state.md`.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-99/.cache/doc-docking.md
- kaola-workflow/archive/issue-99/.cache/final-validation.md
- kaola-workflow/archive/issue-99/.cache/mirror-digest.json
- kaola-workflow/archive/issue-99/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-99/evidence/heartbeat-auto-bind-design.md
- kaola-workflow/archive/issue-99/finalization-summary.md
- kaola-workflow/archive/issue-99/mission-list.md
- kaola-workflow/archive/issue-99/workflow-state.md
