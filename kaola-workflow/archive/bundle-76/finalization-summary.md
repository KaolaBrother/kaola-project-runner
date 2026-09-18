# Finalization summary — bundle-76 (Issue #76)

Issue: "ZCode Host：ACP Worker 待审批时立即事件唤醒，避免 turn 未结束造成死等"
Accepted candidate: `4f7d83dc907fc844d1422302b890612ea1ab07d5` (outer reviewer
ACCEPT in conversation); docs dock `1b46b6f` adds the CHANGELOG entry only.
Base: `249fc20` (post-#73 main; rebased at the safe point, both sides' semantics
verified co-present, full validate re-run PASS).

## Delivered

- `permission_required` joins `terminated`/`idle` in `WORKER_EVENT_KINDS`.
- `session/request_permission` on a bound worker emits one carrier event per
  NEW `pending_permissions` key — mid-turn, while `turn_active` stays true —
  delivered immediately to an idle Host or staged at a busy Host's existing
  turn boundary. A retransmitted request id sends no second wake; a settled
  request is idempotent on the Host side.
- Event payload carries only the normalized `request_id` locator (string/int
  accepted, bool/nested rejected); title, options, tool input, and credentials
  never travel. `idle`/`terminated` payloads are byte-identical to before.
- Host guidance (dispatch reference + heartbeat skeleton): the event is a
  wake, not an idle and not a decision — read the worker's own
  `pending_permissions` receipt, `permit` only inside existing authorization,
  escalate anything else; the turn-end `idle` still arrives after settlement.
- No auto-approve, no scheduler, no second queue, no mid-turn prompt
  injection; unbound/standalone/non-ZCode workers unchanged; Droid/Cursor
  native authorization semantics untouched.

## Files Changed

## Changed Paths

- `scripts/kaola-acp-holder.py` — kind tuple, `is_new` dedup, `extra` carrier
  param, `request_id` validation/serialization.
- `scripts/validate.sh` — focused suite registered in lanes A and all.
- `templates/orchestrator/references/zcode-host-dispatch.md.tmpl` — new kind
  documented beside the pinned `idle`/`terminated` sentence (8,177 B tmpl /
  8,183 B rendered, under the 8,192 B cap; only unpinned prose trimmed).
- `templates/orchestrator/references/heartbeat-skeleton.txt` — one step-2
  clause covering receipt-read, idempotence, authorized permit, escalation.
- `docs/zcode-host.md` — third event source + optional `request_id` payload.
- `CHANGELOG.md` — Unreleased entry (dock commit).
- `tests/contract/test-issue-76-permission-wake.py` — new, 5 tests / 77 checks.
- `tests/contract/test-issue-65-host-contract.py` — kind-tuple assertion.
- `skills/*/scripts/kaola-acp-holder.py` (9), `skills/kaola-project-runner/
  references/{heartbeat-skeleton.md,zcode-host-dispatch.md}` — regenerated.

## Test Coverage

- Focused: `tests/contract/test-issue-76-permission-wake.py` — 5/5, 77 checks
  (idle-Host immediate wake with `turn_active`, busy-Host stage+flush,
  Droid-like metadata-only idempotent wake, unbound unchanged, kind
  validation).
- Baseline: same suite on the unmodified base failed exactly at the missing
  wake (`permission_required event reaches the idle host and delivers`).
- Regressions: `test-zcode-heartbeat-contract` 9/9 (incl. canonical-drift),
  `test-issue-65-host-contract` 13/13, `test-issue-70-binding-fact` 6/6,
  `test-issue-73-canonical-root` 29/29.

## Validation

- `./scripts/render-skills.py --check` — PASS, budgets OK.
- `./scripts/validate.sh` — PASS on `4f7d83d` post-rebase (all lanes, clean
  residue sweep); recorded via `kaola-workflow-validation-runner.js record`
  (`verdict: pass`, command `./scripts/render-skills.py --check &&
  ./scripts/validate.sh`, receipt `.cache/final-validation.md`).
- Real ACP path (isolated probe): REAL `droid` 0.220.0 in `--mode manual`
  raised a genuine `session/request_permission` (`request_id: 0`, real
  options); the bound Host received a confirmed `permission_required`
  delivery while `turn_active=True`, the prompt carried only the locator,
  `permit` settled it, `idle`/`terminated` followed; both sessions stopped
  with `residual_pids: []`. **Honest boundary: the Host-side agent process
  was the fake zcode app-server — no real zcode binary exists on this
  machine, so no real ZCode model reply is claimed.** Every holder,
  carrier, staging, delivery, confirm, and permit path was real code.
- Outer review: user independently reviewed the production diff and re-ran
  the 5 focused tests + `render --check` on the frozen SHA — all PASS —
  then formally ACCEPTed `4f7d83d`.

## Documentation Docking

DOCKED — `.cache/doc-docking.md`: CHANGELOG entry added; `docs/zcode-host.md`
and the two Host templates docked with the candidate; `docs/api.md`/`README.md`
verified no-impact.

## Follow-Up Items

- None discovered in this run. No new defects, no deferred work; the only
  limitation is environmental (no real zcode binary), recorded above and in
  the evidence, not a product defect.

## Readiness

All four missions done with recorded results; candidate accepted by the outer
reviewer; validation green post-rebase onto `249fc20`; docs docked. Ready for
close → archive → merge-sink → closure audit → exact #76-scoped cleanup.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/bundle-76/.cache/doc-docking.md
- kaola-workflow/archive/bundle-76/.cache/final-validation.md
- kaola-workflow/archive/bundle-76/.cache/mirror-digest.json
- kaola-workflow/archive/bundle-76/.cache/origin/selection-record.json
- kaola-workflow/archive/bundle-76/evidence/20-real-droid-probe.py
- kaola-workflow/archive/bundle-76/evidence/21-real-probe-host-rpc.jsonl
- kaola-workflow/archive/bundle-76/evidence/22-real-probe-events-droid-droid-i76-probe-worker.jsonl
- kaola-workflow/archive/bundle-76/evidence/22-real-probe-events-zcode-zcode-i76-probe-host.jsonl
- kaola-workflow/archive/bundle-76/evidence/50-candidate-diff.patch
- kaola-workflow/archive/bundle-76/finalization-summary.md
- kaola-workflow/archive/bundle-76/mission-list.md
- kaola-workflow/archive/bundle-76/workflow-state.md
