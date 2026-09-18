# Finalization summary — issue-66

Issue: #66 — 区分 Worker 与 ZCode Orchestrator 启动流程，并建立外层启动验收与生命周期监督契约
Branch: `workflow/issue-66` · sink: merge · baseline: `bb6d740` (v0.3.5)
Accepted candidate (outer Agent, 2026-09-18): `2da5f92dd5838cd7545b2ea13ae8de56abb35e24`
Doc-docking follow-up commit is recorded under Validation below.

## Delivered

- **Two entry points in the main Skill.** `kaola-project-runner` now opens with ordinary worker
  supervision (unchanged: no Host obligation, no event binding, no added gate) and Orchestrator
  (ZCode Host) supervision, which reads roles, authorization and the lifecycle boundary from the
  project's existing Project Plan or already-authorized task plan — no second plan schema.
- **One on-demand reference** `references/host-startup.md`: the ordinary-worker example with
  receipt checks and failure/unknown handling; the outer startup order (recover → start at the
  canonical root → hand over what a Host cannot discover → startup receipt → verify it against the
  plan and produced artifacts → verify the first real event loop → keep, then exact stop); the
  Host's own beat (valid `body` before the first dispatch, bind per `start` and check the receipt,
  `send --no-wait`, ending the turn as the wait); and which record holds roles, progress, current
  state and facts.
- **Error visibility, not a gate.** A `.kaola/heartbeat-prompt.json` that exists but carries no
  usable `body` (wrong field name, wrong type, empty, unparseable, or non-UTF-8 bytes) is reported
  by its real defect in the delivered notification and as `heartbeat_body_error` on the host
  holder's `worker_event_delivered` entry, instead of the old "none maintained" text that let the
  audited Host believe a prompt written under another field name was in effect. One read supplies
  both the verdict and the body, so the checked body is the delivered body. Delivery is never
  blocked; the skeleton reference now names the `body` field.
- No role parameter, launcher, role state machine, config system, scheduler, persistent ledger, or
  approval gate was added; the flows reuse existing `start` / `send --no-wait` / `observe` /
  `capture` / `stop`, the `KAOLA_ACP_HEARTBEAT_HOST` binding receipt, the worker-event carrier, and
  the Kaola-Workflow Mission List.

## Files Changed

Hand-edited (7):
- `scripts/kaola-acp-holder.py` — `heartbeat_prompt_body()` (new, single read → `(body, defect)`)
  and `_heartbeat_payload` reporting the defect.
- `templates/orchestrator/SKILL.md.tmpl` — `## Two entry points`; duplicate-restatement compression
  to stay inside the byte budget (17281 B of 17408).
- `templates/orchestrator/references/host-startup.md.tmpl` — new (6521 B of 8192).
- `templates/orchestrator/references/heartbeat-skeleton.txt` — names the `body` field.
- `tests/contract/test-zcode-heartbeat-contract.py` — two Issue #66 tests in the existing harness.
- `docs/zcode-host.md`, `docs/README.md`, `CHANGELOG.md` — documentation docking.

Generated (never hand-edited): `skills/kaola-project-runner/**` and the ten copies of
`kaola-acp-holder.py` under `skills/*/scripts/`, all from `./scripts/render-skills.py --write`.

Frozen surfaces untouched: `templates/grok-golden` and `templates/budgets.json` are byte-identical
to `bb6d740` (0 diff lines); no byte budget was relaxed.

## Test Coverage

- `tests/contract/test-zcode-heartbeat-contract.py`: 9/9 tests, 164 checks. New:
  - `test_issue_66_defective_prompt_file_reports_its_defect` (21 checks) — the pure helper over
    absent / unparseable / non-object / non-string / empty / wrong-field-name / valid, plus
    non-UTF-8 bytes and an unreadable path reported rather than raised, plus a counted-read proof
    that the file is read exactly once and that read's own body comes back, plus a full live-holder
    round trip proving the notification says `present but UNUSABLE`, names the file and `"body"`,
    no longer claims the file is missing, never passes mis-filed text off as the body, and logs
    `heartbeat_body_error`.
  - `test_issue_66_unarmed_worker_stays_ungated` (5 checks) — an ordinary worker start carries no
    `heartbeat_host`, blocking `send` still reaches `turn_completed`, stop is normal, and its holder
    never runs the carrier.
- Reused rather than rebuilt (same file, unchanged): duplicate `event_id` collapse, bounded queue,
  busy-host staging and turn-boundary flush, `start --resume` redelivery of unconfirmed events, the
  ZCode-Host-only carrier boundary, and the canonical-skeleton/one-set contract.
- Live model-driven lifecycle loop (implementer self-verification, isolated sentinel sessions):
  `kaola-workflow/issue-66/evidence/live-loop-2026-09-18.md` with raw receipts in `evidence/live/`.

## Validation

- `verdict: pass`, command `./scripts/validate.sh`, recorded through
  `kaola-workflow-validation-runner.js record` into `.cache/final-validation.md`.
- Raw outputs: `evidence/validate-final-2.txt` (exit 0, on `2da5f92`) and the re-run after the
  documentation-docking commit (exit 0) — see `.cache/final-validation.md` for the bound hash.
- `./scripts/render-skills.py --check`: PASS, budgets OK, in both runs.
- Acceptance legs: automated (the full contract suite above), local live UAT (the sentinel loop,
  implementer-run and therefore self-verification), and independent outer review of the frozen
  diff, the single-read/Unicode tests and the raw live records (outer ACCEPT of `2da5f92`).
  Not executed: any non-ZCode host, PTY transport, multi-worker concurrency, and a live session with
  a defective heartbeat `body` (covered by contract tests only). No release, tag, or global install
  was performed or authorized.

## Changed Paths

Recorded by the finalize transaction below.

## Documentation Docking

`DOCKED` — `.cache/doc-docking.md`: `docs/zcode-host.md` (new two-flow section and the corrected
payload bullet), `docs/README.md` (the index had no `zcode-host.md` entry at all), `CHANGELOG.md`
(`## Unreleased`); `README.md`, `docs/api.md`, `docs/architecture.md`, `docs/conventions.md` and the
Grok Bot / watch-surface / decision / report docs recorded as no-impact with reasons.

## Issue statement coverage

1. Executable examples with correct installed paths for both flows, including calls, checks and
   failure/unknown handling → `references/host-startup.md` §A (worker) and §B–§C (Orchestrator).
2. A real ZCode Host started only from the generated Skill plus the given plan and identity, with
   the outer Agent checking loading and the role receipt against the plan, and no dispatch without
   authorization → live evidence (`evidence/live/01`–`03`): the Host loaded the candidate payload,
   read the plan, answered with role/authorization/lifecycle/sources/binding-state, and held before
   dispatching. **Corrected in the issue's own thread** (comment `#issuecomment-5726039395`): ZCode
   `tool_call` records carry no paths, so the delivered contract verifies plan-checkable facts and
   produced artifacts instead; the record gap is tracked as #67.
3. Measured bind → non-blocking dispatch → natural `end_turn` → worker completion while the Host is
   busy and while idle → staging/delivery/confirmation → reading the full delivery → rework →
   second delivery → acceptance → close-out → exact stop → live evidence: four real events, two
   delivered while idle and two staged mid-turn and delivered at the boundary, all confirmed; one
   rework round; two exact worker stops; the Host exact-stopped by the outer Agent after close-out.
4. Minimal contract tests for a wrong heartbeat field, binding-absence visibility, duplicate/
   unconfirmed recovery, and the ordinary worker staying ungated, reusing existing tests → see Test
   Coverage.
5. Template change → `render --write`/`--check` → `validate`, grok-golden and byte budgets frozen;
   compatibility for changed public receipts → satisfied: no receipt field was removed or renamed,
   `heartbeat_body_error` is additive, and the pre-existing delivery/confirmation tests pass
   unchanged.
6. Evidence bound to the final candidate SHA, with implementer self-verification and independent
   outer review distinguished → this summary, `2da5f92`.

## Follow-Up Items

- **#67 (P3, filed by this run, verified OPEN with a non-empty body)** — ZCode ACP `tool_call`
  updates carry no paths, so an outer Agent cannot verify which files a session actually read.
- **Issue #65 integration, owned by the outer Agent after #65 is accepted** (this run must not merge
  or cherry-pick it): shared surfaces are `templates/orchestrator/SKILL.md.tmpl` (both candidates
  edit it; the merged file must be re-measured against the 17408 B budget), the two Host references
  (#65's `zcode-host-dispatch.md` per-beat mechanics next to this run's `host-startup.md`), the
  user-approved resolution of keeping both features with #65's cursor unified and duplicate prose
  compressed before regenerating and re-validating, and `scripts/kaola-acp-holder.py` where the two
  runs touch different functions.
- v0.3.5 release remains pending and unauthorized here; the `## Unreleased` changelog block is
  deliberately left for whoever cuts the next version.

## Readiness

READY — accepted candidate validated, documentation docked, follow-up filed, correction posted on
#66 before closure. Proceeding to closure, archive, merge sink, remote sync and this run's own
worktree/branch cleanup only.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-66/.cache/doc-docking.md
- kaola-workflow/archive/issue-66/.cache/final-validation.md
- kaola-workflow/archive/issue-66/.cache/mirror-digest.json
- kaola-workflow/archive/issue-66/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-66/evidence/heartbeat-contract-1.txt
- kaola-workflow/archive/issue-66/evidence/heartbeat-contract-2.txt
- kaola-workflow/archive/issue-66/evidence/live-loop-2026-09-18.md
- kaola-workflow/archive/issue-66/evidence/live/01-host-start.json
- kaola-workflow/archive/issue-66/evidence/live/02-handover-receipt.json
- kaola-workflow/archive/issue-66/evidence/live/02-handover.txt
- kaola-workflow/archive/issue-66/evidence/live/03-host-startup-capture.json
- kaola-workflow/archive/issue-66/evidence/live/04-confirm-receipt.json
- kaola-workflow/archive/issue-66/evidence/live/04-confirm.txt
- kaola-workflow/archive/issue-66/evidence/live/05-host-dispatch-capture.json
- kaola-workflow/archive/issue-66/evidence/live/06-host-notify-beat.json
- kaola-workflow/archive/issue-66/evidence/live/07-rework-receipt.json
- kaola-workflow/archive/issue-66/evidence/live/07-rework.txt
- kaola-workflow/archive/issue-66/evidence/live/08-host-rework-dispatch.json
- kaola-workflow/archive/issue-66/evidence/live/09-host-accept-beat.json
- kaola-workflow/archive/issue-66/evidence/live/10-event-chain.txt
- kaola-workflow/archive/issue-66/evidence/live/11-host-stop.json
- kaola-workflow/archive/issue-66/evidence/live/12-host-heartbeat-prompt.json
- kaola-workflow/archive/issue-66/evidence/live/13-sentinel-delivery.diff
- kaola-workflow/archive/issue-66/evidence/live/14-src-text.py
- kaola-workflow/archive/issue-66/evidence/live/15-tests-test_text.py
- kaola-workflow/archive/issue-66/evidence/validate-1.txt
- kaola-workflow/archive/issue-66/evidence/validate-final-2.txt
- kaola-workflow/archive/issue-66/evidence/validate-final.txt
- kaola-workflow/archive/issue-66/evidence/validate-finalize.txt
- kaola-workflow/archive/issue-66/finalization-summary.md
- kaola-workflow/archive/issue-66/mission-list.md
- kaola-workflow/archive/issue-66/workflow-state.md
