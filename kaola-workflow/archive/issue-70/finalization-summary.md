# Issue #70 — finalization summary

Run: `issue-70` · branch `workflow/issue-70` · sink `merge` · issue #70
Accepted candidate: `2e00a0f37572df28fc9c13f41951d57a144f4bbb`, rebased unchanged onto main
`3dd7e5e` as `bf9fda3`; documentation docking added `7590e45` on top.

## Delivered

A ZCode Host wakes only through workers actually bound to it, but the `start` receipt echoed the
caller's own `KAOLA_ACP_HEARTBEAT_HOST` input, so a missed or foreign binding was indistinguishable
from a correct one — the condition reported from the VRP AI machine.

- **The binding is now the holder's own fact.** `kaola-acp-holder.py` carries the adopted target in
  its state and record; `kaola-acp.py` reports it on `start`, `observe` and `status` through one
  helper: a target, an explicit `null` for an ordinary unbound worker, or
  `heartbeat_host_known: false` for a holder or record older than the field — unknown is never
  reported as unbound, and a `no-session` receipt stays silent. `start` keeps its input separately
  in `heartbeat_host_requested`, a `session-exists` reuse answers with the binding in force, and
  the CLI hands the holder the target it validated so the answer is the checked one.
- **Reuse verification and internal recovery** in the ZCode Host guidance: verify the fact on every
  worker started, reused or adopted; on a missed binding keep the in-flight work, read its result in
  that beat with the existing bounded `wait --timeout` when the unbound worker is the only wake
  source (a recovery exception, never the ordinary wait and never a poll loop), then rebind by exact
  `stop`/`start` and verify again. Only a recovery that cannot complete goes outward as an exception
  naming the decision needed; a heartbeat note is bookkeeping, not a wake-up.
- **`--resume` needs a real native id**, and for ZCode that `sess_*` is published in the session's
  own `native_session_identity` event, not `session_meta` — never substituted by `acp_session_id`
  or `--continue`.
- No new rebind API, scheduler, timer, poll loop or global gate; unbound ordinary workers stay
  legal; no byte budget raised.

## Files Changed

Source (9 files): `scripts/kaola-acp.py`, `scripts/kaola-acp-holder.py`, `scripts/validate.sh`,
`templates/orchestrator/references/zcode-host-dispatch.md.tmpl`,
`templates/orchestrator/references/host-startup.md.tmpl`, `docs/zcode-host.md`, `docs/api.md`,
`CHANGELOG.md`, plus `tests/contract/test-issue-70-binding-fact.py` (new) and the two updated
contract suites (`test-issue-65-host-contract.py`, `test-zcode-heartbeat-contract.py`).
Generated (renderer only): the nine worker Skills' `kaola-acp*.py` copies and the orchestrator's
two references. `skills/` and `hosts/` were never hand-edited.

## Test Coverage

- `tests/contract/test-issue-70-binding-fact.py` — 6 tests, 54 checks: the fact versus the request
  (including `session-exists` and a post-start `send` under a changed environment), the event
  reaching only the bound Host, explicit `null`, a pre-Issue-#70 record read as unknown, rebinding
  through exact `stop`/`start`, the internal-recovery and exception wording, the native id taken
  from the raw `native_session_identity` event and actually used to resume, and every `--session`
  example in the generated reference matching the issue-scoped naming rule.
- `tests/contract/test-zcode-heartbeat-contract.py` — 9 tests, 164 checks, with the Issue #66
  unarmed-worker assertion updated to the explicit-null contract.
- `tests/contract/test-issue-65-host-contract.py` — 13 tests; two assertions this Issue supersedes
  now pin the new receipt contract, the rest of #65's pinned wording unchanged.
- Registered in both `scripts/validate.sh` suite lists.

## Validation

- Verdict: **pass**. Command: `./scripts/render-skills.py --check && ./scripts/validate.sh`,
  run from the candidate worktree; receipt in `.cache/final-validation.md`
  (`validated_candidate_hash: 2fc419ac…54e2`).
- `./scripts/validate.sh` EXIT=0 on the final tree — raw log `evidence/validate-7590e45.log`
  (earlier frozen SHAs: `evidence/validate-bf9fda3.log`, `validate-2e00a0f.log`,
  `validate-issue-scoped-names.log`, `validate-native-id.log`,
  `validate-internal-recovery.log`, `validate-handoff.log`, `validate-a193d3c.log`,
  `validate-2026-09-18.log`).
- `render-skills.py --check` PASS; budgets unchanged and not raised: dispatch reference 8180 B,
  host-startup 7479 B of 8192 B, main Skill 17292 B of 17408 B.
- Finalize precondition check: `ok: true`, no reasons, `dirty_paths: []`.

### Acceptance walk of the Issue statement

| Issue clause | Satisfied by |
|---|---|
| Expose the holder's really-adopted target through existing state/record/observe/status, default explicitly null, old records not impersonating bound | `attach_binding_fact` + holder `write_record`/`op_state`; suite checks 1–4, 6 |
| Distinguish start input from the running fact | `heartbeat_host_requested` versus `heartbeat_host`; checked on both a successful and a `session-exists` start |
| No new binding service, scheduler or state machine | Diff contains none; the recovery reuses `wait`/`observe`/`capture`/`stop`/`start` only |
| ZCode Host verifies every worker, new and reused — not only the first round | Reference section "Verify the binding in force, new worker or reused"; live: the Host verified an **adopted** worker unprompted (`evidence/live-2026-09-18.md` §4) |
| Env var scoped to that one start, without claiming environments never inherit | "Exporting it, or setting it on a later `send`, binds nothing"; proven live by the `session-exists` probe (`evidence/live/09`) |
| Missed/mis-bound not faked by repeat start/send; in-flight preserved; rebind at a safe idle point; resume where evidenced; no auto-cancel/re-send/platform switch/Host kill | Reference "A missing or wrong binding"; live in `evidence/live-internal-2026-09-18.md` (both legs) and `evidence/live-2026-09-18.md` §8 |
| Outer startup supervision verifies the loaded payload and the real first return chain | `host-startup.md` step 4 ("a merged checkout is not an installed Skill"); live: the Host proved its payload by `diff -rq` against the installed release |
| Automated: unbound still works; bound state matches the holder; a live holder does not fake a new target; old record explicitly unknown; existing fields preserved | Issue #70 suite (6/6, 54 checks) plus the unchanged #66/#62 coverage in the heartbeat suite |
| Isolated real ACP: bound start → non-blocking dispatch → Host ends its turn → worker event wakes it → Host reads the result; reuse verification; safe recovery; raw inputs/receipts/outputs and exact-stop evidence | `evidence/live-2026-09-18.md` with raw `evidence/live/00…24`; re-proof on the delivered text in `evidence/live-recheck-2026-09-18.md`; the stall and the internal recovery in `evidence/live-handoff-2026-09-18.md` and `evidence/live-internal-2026-09-18.md` |
| No nine-platform re-validation, no PTY, renderer-only generated files, budgets not raised | Out-of-scope items untouched; `render-skills.py --check` PASS with unchanged `templates/budgets.json` |
| Outer review of the candidate SHA and evidence before finalize | ACCEPT recorded for `2e00a0f`, rebased unchanged to `bf9fda3` |

Not lived, by design and stated: a genuinely pre-Issue-#70 live holder (covered by the suite, since
an old holder cannot be conjured) and the failure branch where the bounded read hits its deadline or
the rebinding `start` refuses (wording pinned by the suite).

## Changed Paths

As reported by the finalize transaction check:

`scripts/kaola-acp-holder.py`, `scripts/kaola-acp.py`, `scripts/validate.sh`,
`skills/{claude-code,codex,cursor-cli,devin,droid,grok,kimi-cli,opencode,zcode}-kaola-project-runner/scripts/kaola-acp{,-holder}.py`,
`skills/kaola-project-runner/references/host-startup.md`,
`skills/kaola-project-runner/references/zcode-host-dispatch.md`,
`templates/orchestrator/references/host-startup.md.tmpl`,
`templates/orchestrator/references/zcode-host-dispatch.md.tmpl`,
`tests/contract/test-issue-65-host-contract.py`, `tests/contract/test-issue-70-binding-fact.py`,
`tests/contract/test-zcode-heartbeat-contract.py` — `dirty_paths: []`.
The documentation commit `7590e45` additionally carries `docs/api.md` and `CHANGELOG.md`, and
`docs/zcode-host.md` moved in the earlier Issue commits.

## Documentation Docking

`DOCKED` — `.cache/doc-docking.md`. README, architecture, conventions, decisions and AGENTS.md
checked with no impact; `CHANGELOG.md`, `docs/api.md` and `docs/zcode-host.md` fixed; the generated
Skill surface re-rendered from templates with budgets unchanged.

## Follow-Up Items

None filed. No run-discovered defect remained open at close: every review finding in this run
(the lifecycle stall, the outward-hand-off boundary, the native-id source, the naming gap) was
corrected inside this Issue and re-frozen, each with its own mission entry and evidence. The Host
session naming example stays project-level pending Issue #74, which already owns that decision;
no new issue was needed for it.

## Readiness

Ready to close and sink: acceptance received from the outer review, validation green on the frozen
tree, documentation docked, mission list 11/11 done with immutable results, and no open follow-up.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-70/.cache/doc-docking.md
- kaola-workflow/archive/issue-70/.cache/final-validation.md
- kaola-workflow/archive/issue-70/.cache/mirror-digest.json
- kaola-workflow/archive/issue-70/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-70/evidence/live-2026-09-18.md
- kaola-workflow/archive/issue-70/evidence/live-handoff-2026-09-18.md
- kaola-workflow/archive/issue-70/evidence/live-handoff/01-worker-start-unbound.json
- kaola-workflow/archive/issue-70/evidence/live-handoff/02-worker-dispatch.json
- kaola-workflow/archive/issue-70/evidence/live-handoff/03-host-start.json
- kaola-workflow/archive/issue-70/evidence/live-handoff/04-prompt.txt
- kaola-workflow/archive/issue-70/evidence/live-handoff/05-host-reply.json
- kaola-workflow/archive/issue-70/evidence/live-handoff/06-host-reply-full.txt
- kaola-workflow/archive/issue-70/evidence/live-handoff/07-worker-wait.json
- kaola-workflow/archive/issue-70/evidence/live-handoff/08-worker-stop.json
- kaola-workflow/archive/issue-70/evidence/live-handoff/09-host-stop.json
- kaola-workflow/archive/issue-70/evidence/live-internal-2026-09-18.md
- kaola-workflow/archive/issue-70/evidence/live-internal/01-worker-start-unbound.json
- kaola-workflow/archive/issue-70/evidence/live-internal/02-dispatch-taskA.json
- kaola-workflow/archive/issue-70/evidence/live-internal/03-host-start.json
- kaola-workflow/archive/issue-70/evidence/live-internal/04-prompt.txt
- kaola-workflow/archive/issue-70/evidence/live-internal/05-host-beat1.json
- kaola-workflow/archive/issue-70/evidence/live-internal/06-host-event-beat.json
- kaola-workflow/archive/issue-70/evidence/live-internal/07-worker2-start-unbound.json
- kaola-workflow/archive/issue-70/evidence/live-internal/08-dispatch-long.json
- kaola-workflow/archive/issue-70/evidence/live-internal/09-worker2-observe-busy.json
- kaola-workflow/archive/issue-70/evidence/live-internal/10-prompt-busy.txt
- kaola-workflow/archive/issue-70/evidence/live-internal/11-host-bounded-wait-beat.json
- kaola-workflow/archive/issue-70/evidence/live-internal/11a-host-settle.json
- kaola-workflow/archive/issue-70/evidence/live-internal/11b-worker2-observe.json
- kaola-workflow/archive/issue-70/evidence/live-internal/12-host-all-replies.txt
- kaola-workflow/archive/issue-70/evidence/live-internal/13-worker2-bound-observe.json
- kaola-workflow/archive/issue-70/evidence/live-internal/14-worker2-stop.json
- kaola-workflow/archive/issue-70/evidence/live-internal/15-host-final-settle.json
- kaola-workflow/archive/issue-70/evidence/live-internal/16-host-stop.json
- kaola-workflow/archive/issue-70/evidence/live-recheck-2026-09-18.md
- kaola-workflow/archive/issue-70/evidence/live-recheck/00-candidate.txt
- kaola-workflow/archive/issue-70/evidence/live-recheck/01-worker-start-unbound.json
- kaola-workflow/archive/issue-70/evidence/live-recheck/02-host-start.json
- kaola-workflow/archive/issue-70/evidence/live-recheck/03-prompt.txt
- kaola-workflow/archive/issue-70/evidence/live-recheck/04-host-reply.json
- kaola-workflow/archive/issue-70/evidence/live-recheck/05-host-reply-full.txt
- kaola-workflow/archive/issue-70/evidence/live-recheck/06-worker-stop.json
- kaola-workflow/archive/issue-70/evidence/live-recheck/07-host-stop.json
- kaola-workflow/archive/issue-70/evidence/live/00-candidate.txt
- kaola-workflow/archive/issue-70/evidence/live/01-recover.json
- kaola-workflow/archive/issue-70/evidence/live/01b-nosession-status.json
- kaola-workflow/archive/issue-70/evidence/live/02-host-start.json
- kaola-workflow/archive/issue-70/evidence/live/03-worker-start-unbound.json
- kaola-workflow/archive/issue-70/evidence/live/04-handover.txt
- kaola-workflow/archive/issue-70/evidence/live/05-host-startup-receipt.json
- kaola-workflow/archive/issue-70/evidence/live/06-host-startup-capture.json
- kaola-workflow/archive/issue-70/evidence/live/06-host-startup-reply.txt
- kaola-workflow/archive/issue-70/evidence/live/07-beat1.txt
- kaola-workflow/archive/issue-70/evidence/live/08-beat1-receipt.json
- kaola-workflow/archive/issue-70/evidence/live/09-repeat-start-probe.json
- kaola-workflow/archive/issue-70/evidence/live/10-worker-observe.json
- kaola-workflow/archive/issue-70/evidence/live/11-worker-wait-taskA.json
- kaola-workflow/archive/issue-70/evidence/live/12-beat2.txt
- kaola-workflow/archive/issue-70/evidence/live/13-beat2-receipt.json
- kaola-workflow/archive/issue-70/evidence/live/14-worker-wait-taskB.json
- kaola-workflow/archive/issue-70/evidence/live/15-host-wait-notify.json
- kaola-workflow/archive/issue-70/evidence/live/16-host-wait-terminated-event.json
- kaola-workflow/archive/issue-70/evidence/live/17-worker-final-status.json
- kaola-workflow/archive/issue-70/evidence/live/18-host-stop.json
- kaola-workflow/archive/issue-70/evidence/live/19-host-event-chain.jsonl
- kaola-workflow/archive/issue-70/evidence/live/20-worker-carrier-sends.jsonl
- kaola-workflow/archive/issue-70/evidence/live/21-worker-record.json
- kaola-workflow/archive/issue-70/evidence/live/22-heartbeat-prompt.json
- kaola-workflow/archive/issue-70/evidence/live/23-host-all-replies.txt
- kaola-workflow/archive/issue-70/evidence/live/24-delivered-notification-head.txt
- kaola-workflow/archive/issue-70/evidence/live/24-event-chain-full.json
- kaola-workflow/archive/issue-70/evidence/native-id/findings.md
- kaola-workflow/archive/issue-70/evidence/native-id/probe-source-of-native-id.py
- kaola-workflow/archive/issue-70/finalization-summary.md
- kaola-workflow/archive/issue-70/mission-list.md
- kaola-workflow/archive/issue-70/workflow-state.md
