---
pack_schema: kaola-ddd-pack/1
id: c4-state-retire
status: current
owner: host
context_primary: orchestration-state/C4-state
contexts_touched: orchestration-state/C5-dispatch, session-runtime/C1-lifecycle
baseline_commit: 8b3779c9c9c76e03f6794b5bf5cf6ffb76bd27c0
related_issues: 280, 255, 259, 281, 282
---

# Pilot pack — retire a record (C4 state, crossing C5 dispatch and C1 session lifecycle)

Work unit: the state tool command `state retire` removes one current record (task, hold, alert
or decision) from `.kaola/heartbeat-prompt.json`. This is the cross-component sample required by
design §2.1 (revision 2). Retiring a **task** crosses three boundaries:

- **C4 state**, where the row lives;
- **C5 dispatch index**, whose items must be shown closed;
- **C1 session lifecycle**, whose seats must be shown stopped, or the task uses `--handoff`
  instead.

Context names follow [`../context-map.md`](../context-map.md) as `<candidate grouping>/<component>`.
Q3 found that C4 and C5 share one language (see the map). C5 is still listed as touched, because
it is a separate store, lock and schema, i.e. a separate consistency boundary.

All citations are at `8b3779c9`. That commit changed only the design document relative to
`1a2f577e`, so every `scripts/` and `tests/` line below is identical at both commits. `D` means
`scripts/kaola-dispatch.py`, `RC` means `scripts/kaola-record-contract.py` and `A` means
`scripts/kaola-acp.py`.

## Vocabulary

| Term | Meaning in this unit | Defined at |
|---|---|---|
| record | One current row in `state.<kind>.<id>`, where kind ∈ `tasks`, `holds`, `alerts`, `decisions` | `D:98` `RECORD_KINDS` |
| retire | Delete the current row from the state file, with evidence. This is **not** C1's `retire_record`, which moves a session `record.json` aside (`A:2194-2203`). Same name, different meaning: see the map. | `D:4990`, `D:5077` |
| `rev` | Per-record revision. The caller must name it as `--expect-rev`. | `D:4999-5001` |
| `revision` | Per-file revision. It goes up by 1 on every write. | `D:5096-5098` |
| `host_revision` | Per-file Host business revision. It goes up only on `--writer host` writes. | `D:5133-5137` |
| StateRefusal | A typed refusal: `{"result":"refused","reason","detail",…}`. Exit code 2, or 3 for `conflict`. | `D:3480-3483`, `D:3467`, `D:5141-5143` |
| `retire-unmet` | The duty has not ended: a task without an accepted/cancelled verdict, dispatch or seats not shown closed, a pending decision, an untranscribed decision, or an alert that names the current recovery input | `D:5007`, `D:5013`, `D:5027`, `D:5031`, `D:5034` |
| `schema-unsupported` / `legacy-format` | The file's schema is unknown (`/3` or later), or is v1 and needs `state migrate` | `D:3542-3546` |
| verdict | The Host's judgment on a task: `accepted`, `partial`, `repair` or `cancelled` | `D:102` `VERDICTS` |
| stage | Task stage: `todo`, `doing`, `review`, `closeout` or `done`. Defined twice, as a tuple and as a frozenset. | `D:100`, `RC:156` |
| dispatch (ref) | A task's list of C5 index `item_id`s | `D:4891-4892` |
| index `status` | C5 item coverage: `in-flight`, `returned`, `failed`, `unknown` or `not-run` | `D:83` `COVERAGE` |
| index `acceptance` | C5 row projection of the Host disposition/verdict: `pending`, `undecided`, `accepted`, …; it carries `acceptance_source` | `D:5184-5199` |
| seat | A worker session that a task names (`session`, `sessions[]`, optionally with `holder_instance_id`) | `D:4848` `task_seats` |
| live rows | `{"rows":[…]}` passed with `--live`. Its producer is `kaola-acp.py list` (`kaola-acp-list/1`). | `D:5658-5664`, `A:838`, `A:968` |
| stopped | The C1 holder record `state` value. Retire reads it verbatim from live rows. | `A:842`, `A:2277-2285`, `D:4868-4877` |
| handoff | Retire a task by moving its seats and dispatch, whole, onto another current task | `D:4955-4987`, `D:5016-5022` |
| cite | `{path, commit?, locator?}` naming where an accepted outcome can still be found after the row leaves | `RC:203-217`, `D:5036-5065`, `D:5274` |
| stone | The command result `value`: `{kind,id,outcome,at,…}`. It is **not stored**. Existing `state.retired` stones are only pruned (see I4). | `D:5066-5072`, `D:5078-5092` |

## Inputs and outputs

| Direction | Artifact | Schema / version | Owner of the format |
|---|---|---|---|
| in/out | `.kaola/heartbeat-prompt.json` | `kaola-heartbeat-prompt/2` (`D:92`). `/1` is refused as `legacy-format`; an unknown schema as `schema-unsupported` (`D:3542-3546`) | C4 |
| in | `--kind --id --expect-rev --evidence [--cite --outcome --index --live --handoff]` | argparse `D:6164-6175` | C4 |
| in | `--index` dispatch index | `kaola-dispatch-index/1` from C5 (`D:1605`, `D:1991`). Retire does **not** check the schema or repo (`D:4906`, `D:5171`; see gap G5) | C5 |
| in | `--live` rows | `kaola-acp-list/1` from C1 (`A:838`). Retire reads only `rows` (`D:5661`; see gap G9) | C1 |
| in | `--cite` | Shape `RC:203-217`; retrievability through Git or the file system (`D:5274`) | C4 |
| out | rewritten state file | `revision`+1, `host_revision`+1 for a Host write, row deleted (`D:5077`, `D:5096-5099`, `D:5133-5137`) | C4 |
| out | stdout JSON | `{"result":"written","revision","previous_revision","host_revision"?,"value":<stone>,"index_mirror"?,…}` (`D:5146-5149`) or a StateRefusal | C4 |
| out (task + `--index`) | C5 index rows `acceptance`, `acceptance_source` | written under `IndexLock`, **after** the state write (`D:5139-5140`, `D:5169-5200`) | C5 store, written by C4 code |

## Invariants

- **I1 — One read-modify-write at a time per state file.** Boundary: the state file's directory.
  A directory `flock` is held across read, change and write (`D:3556-3574`, `D:5106-5140`). The
  write replaces the file atomically through a temp file and `os.replace`, and on failure removes
  the temp file (`D:1166-1177`).
- **I2 — Compare-and-set per record.** Boundary: one record. If `--expect-rev` does not equal the
  current `rev`, the result is `conflict`, exit 3, and the file is not changed (`D:4999-5001`,
  `D:5141-5142`).
- **I3 — Monotonic file counters.** Boundary: the state file. `revision` goes up by 1 on every
  write (`D:5097`). `host_revision` goes up only on Host writes (`D:5133-5137`). These are two
  separate counters from the per-record `rev`. The baseline example's "monotonic `rev`" merged
  them.
- **I4 — Current-only storage.** Boundary: the state file. Retire deletes the row (`D:5077`).
  It never appends a stone; the stone is returned to the caller only (`D:5078`, `D:5146-5149`).
  Pre-existing `state.retired` stones are pruned, except those that still name seats or dispatch
  and have no `handed_to`. Such a stone is a pending reclaim, i.e. a current duty, not history
  (`D:5079-5092`; migration does the same: `RC:230-259`). Owner rule:
  AGENTS.md "Project special requirements — lifecycle implementation (#255)", item 2. Design:
  `docs/designs/lifecycle-state-2026-10-04/design.md:172-174`.
- **I5 — A task leaves only on a Host verdict.** Boundary: the task record. A task retires only
  with stage `done` + verdict `accepted`, or verdict `cancelled` (`D:5011-5014`). Design:
  `…/lifecycle-state-2026-10-04/design.md:70-71`.
- **I6 — Dispatched work is closed or handed off.** Boundary: crosses C4↔C5↔C1. A task's
  dispatch items must be shown not `in-flight`/`unknown` in `--index`. Its seats and the item
  sessions must be shown stopped in `--live`, under the recorded holder. Otherwise the seats and
  dispatch must be handed to another current task (`D:4886-4952`, `D:4859-4883`,
  `D:5016-5028`). A single narrow exception exists: a fingerprint-differs item that the Host
  accepted, with the exact stop recorded (`D:4918-4945`).
- **I7 — An accepted outcome stays findable.** Boundary: task record → repository. An accepted
  task needs a `--cite` that can be retrieved (`D:5036-5065`).
- **I8 — Owner questions stay with their owner.** Boundary: the decision record. A Sideagent
  cannot retire a pending decision, and cannot retire a transcribed task or decision that the
  Host has not yet seen (`D:5030-5035`).
- **I9 — Recovery input is not dropped.** Boundary: the alert ↔ `maintenance.recovery_input`. An
  alert that names the current `recovery#<seq>` stays (`D:5005-5009`).
- **I10 — A late write does not reopen.** Boundary: one record id. After retirement, an update
  with an old `--expect-rev` is refused as `record-retired`. A pending-reclaim stone also refuses
  reuse of its id (`D:4570-4585`).
- **I11 — Writer roles.** Boundary: caller identity (C1 holder env). A worker caller cannot
  write as Host. A replaced Sideagent cannot write (`D:4426-4463`; caller from
  `KAOLA_ACP_DISPATCHER`, `D:1242-1253`).
- **I12 — Two stores, no cross-store transaction.** Boundary: the state file vs the dispatch
  index. The index mirror runs after the state write has landed. On mirror failure the index is
  left as it was, and the error is reported in `index_mirror`; the state write is not rolled back
  (`D:5152-5166`). Retirement never settles an index row that is in-flight, unknown or
  unreadable (`D:5181-5185`).

## Dependency contracts

Each bullet is one seam: provider → consumer, contract version, and the suite or gap. A suite is
named only where I read an assertion that exercises the seam. "Shared path" means that the
assertion goes through another command that reaches the same function.

**C4 internal (state file, CORE atomic access)**

- CORE `StateLock` + `atomic_write` → C4 `state_mutation` (retire shares this path, `D:5259-5260`); `kaola-heartbeat-prompt/2`; eight concurrent writers lose nothing (`test_concurrent_writers_never_lose_an_update`; shared path through `update`). suite: test-issue-255-lifecycle-state.py
- CORE `atomic_write` → C4: a failed temp write leaves the original and no temp file (`test_a_failed_write_removes_its_temp_file`). suite: test-issue-259-record-contract.py
- C4 retire CAS: a stale `--expect-rev` gives exit 3 and unchanged bytes (`test_current_exception_resolution_repeated_cli_views_and_newer_recovery`, retire calls at :436-445). suite: test-issue-259-record-contract.py
- C4 schema reader → retire: future `/3` is `schema-unsupported` and the file is unchanged (`test_future_schema_is_refused_unchanged`). This is asserted through `state view`/`migrate`; retire reaches the same `require_current` (`D:5130`). suite: test-issue-255-lifecycle-state.py
- C4 schema reader → retire, v1 file: `state retire` on schema `kaola-heartbeat-prompt/1` is `legacy-format` and the file is unchanged (`test_a_v1_file_is_legacy_format_on_retire`, commit `7815e0b43c3143851631d437e7ce872697c23bb0`). suite: test-issue-255-lifecycle-state.py
- C4 retire refusal codes `record-missing` (`D:4997`) and `evidence-required` (`D:5003`, reachable with `--evidence ""`): both names are asserted, and the file is unchanged (`test_retire_names_record_missing_and_evidence_required`, commit `7815e0b43c3143851631d437e7ce872697c23bb0`). suite: test-issue-255-lifecycle-state.py
- C4 task verdict precondition (I5): not done, done without a verdict, and `partial` are all `retire-unmet`; accepted+cite retires (`test_retire_and_late_event_cannot_reopen`). suite: test-issue-255-lifecycle-state.py
- C4 → Git cite (I7): a fabricated commit is refused with unchanged bytes, and a real path is kept (`test_a_fabricated_cite_is_refused_and_a_real_path_is_kept`; the reason is asserted through `detail` "invent", not by the `cite-required` name). suite: test-issue-259-record-contract.py
- C4 → Git cite with a real commit (`gate` task retired with `{"path","commit": HEAD}`, :430-433). suite: test-issue-267-rejection-count.py
- C4 accepted task **without** `--cite`: `cite-required` and the file is unchanged (`test_an_accepted_task_without_cite_is_cite_required`, commit `7815e0b43c3143851631d437e7ce872697c23bb0`). suite: test-issue-259-record-contract.py
- C4 current-only storage (I4): a handled row leaves no stone, no body text and nothing in the host/sideagent/delegator views (`test_current_exception_resolution_…` :446-460; `test_retire_and_late_event_cannot_reopen` :165-172). suite: test-issue-259-record-contract.py
- C4 migration drops settled stones (`test_cleanup_keeps_pending_duties_and_does_not_delete_hash_copies`). suite: test-issue-259-record-contract.py
- C4 pending-reclaim stones (I4 keep branch `D:5087-5088`, `RC:246-252`; I10 refusal `D:4570-4579`): migrate and retire keep a stone with seats or dispatch and no `handed_to`, and `state update` of that id at `--expect-rev 0` is `record-retired` (`test_a_pending_reclaim_stone_is_kept_and_blocks_its_id`, commit `7815e0b43c3143851631d437e7ce872697c23bb0`). suite: test-issue-259-record-contract.py
- C4 decisions (I8): a Sideagent retire of a pending decision is `retire-unmet`, the Host retire works, and an old rev gives `record-retired` (`test_retire_and_late_event_cannot_reopen`); a transcribed settlement is first seen by the Host (`test_a_sideagent_settles_a_decision_only_as_transcribed_evidence`). suite: test-issue-255-lifecycle-state.py

**C4 ↔ C5 (dispatch index, `kaola-dispatch-index/1`)**

- C5 index rows → C4 `open_dispatch` (I6): an `in-flight` row and a live session are `retire-unmet`; `returned` + stopped retires (`test_retirement_needs_dispatched_work_closed_and_stopped`). The fixtures are hand-written rows. suite: test-issue-255-lifecycle-state.py
- C5 index rows → C4 fingerprint-differs reconciliation: the single exception and its 12 negative variants (`test_retire_mirrors_original_verdict_without_hiding_open_dispatch` :1888-1967). suite: test-issue-259-record-contract.py
- C4 retire → C5 index mirror (I12): a returned row gets `acceptance: accepted` + `acceptance_source`, and in-flight/unknown/foreign rows are untouched (same test, :1856-1884). suite: test-issue-259-record-contract.py
- C5 index identity → C4 retire. suite: none (gap: G5 — retire's index read (`D:4906`) and the mirror (`D:5171`) do not check `schema: kaola-dispatch-index/1` or `repo`, unlike the other index readers (`D:605-607`, `D:3143`, `D:3932`). A probe at this commit retired a task against `{"schema":"other/9","repo":"/elsewhere",…}`: `written`. No suite asserts either behaviour)
- C5 `status` vocabulary → C4 `open_dispatch`. suite: none (gap: G6 — `open_dispatch` closes any status except `in-flight`/`unknown` (`D:4913`), while `mirror_task` accepts only `returned`/`failed`/`not-run` (`D:5184`). A probe retired a task whose row had **no** `status`, and one with `"status":"inflight"`: both `written`. No suite has an absent or unrecognized status)
- C5 producer (`execute`/`collect`) → C4 retire consumer: retire reads the index execute created and collect rewrote to `returned`, then mirrors `acceptance: accepted` (`test_retire_reads_the_index_execute_and_collect_wrote`, commit `7815e0b43c3143851631d437e7ce872697c23bb0`). suite: test-issue-255-lifecycle-state.py
- C4 retire → C5 mirror failure after the state write landed (I12 `D:5161-5166`): `index_mirror.error` with `changed: {}`, index bytes unchanged, task already gone (`test_index_mirror_error_is_reported_after_retire_writes`, commit `7815e0b43c3143851631d437e7ce872697c23bb0`). suite: test-issue-259-record-contract.py
- C4 retire `--handoff` → receiving C4 task, carrying C5 dispatch refs and seats (`test_a_live_seat_can_be_handed_to_a_continuing_task_with_its_evidence`; `test_a_known_holder_in_any_seat_shape_survives_a_handoff`). suite: test-issue-255-lifecycle-state.py

**C4 ↔ C1 (session lifecycle, `kaola-acp-list/1`, holder identity)**

- C1 live rows → C4 `open_seats` (I6): a foreign holder, a live session, conflicting recorded holders and a missing row are each `retire-unmet`; the exact holder stopped retires (`test_a_known_holder_in_any_seat_shape_survives_a_handoff`). The fixtures are hand-written `{"rows":[…]}`. suite: test-issue-255-lifecycle-state.py
- C1 `list` default omits dead holders (the C1 side of this seam: `A:891`), asserted by "the default view stays live holders only" (test-acp-contract :1310-1312). suite: test-acp-contract.py
- C1 `kaola-acp.py list` output → C4 retire `--live`. suite: none (gap: G9 — no suite feeds real `list` output into retire, and `live_rows_of` (`D:5658-5664`) does not check `kaola-acp-list/1`. Measured probe at this commit: a cleanly stopped seat (record `state: stopped`, holder gone, as written by `A:2277-2285`) is **absent** from `list --repo`, so retire is `retire-unmet` "not in the live rows". `list --repo --include-dead` shows it `stopped`, and retire is `written`. The orchestrator reference describes `$LIVE` as "`{"rows":[...]}` from `list --repo`" (`templates/orchestrator/references/dispatch-collect.md:60-61`), so following it literally cannot prove a stop for retire)
- C1 caller identity (`KAOLA_ACP_DISPATCHER`) → C4 writer role (I11): a worker caller cannot write as Host, and a replaced Sideagent is `binding-superseded` (`test_a_worker_caller_cannot_write_as_host`, `test_binding_guards_late_writes_of_a_replaced_sideagent`; shared path through `update`, `check_writer` at `D:5132`). suite: test-issue-255-lifecycle-state.py

**C4 ↔ C6 (recovery, same state file)**

- C6 `recovery_input` → C4 alert retire (I9): an alert naming `recovery#9` is `retire-unmet`, with bytes, maintenance, grants and tasks unchanged (test-259 :477-489). suite: test-issue-259-record-contract.py
- C4 retire → C6 Sideagent checkpoint `applied: ["retired:tasks/<id>"]` (`test_host_retirement_preserves_an_earlier_sent_checkpoint_range`). suite: test-issue-255-lifecycle-state.py

## Acceptance

Observable outcomes. Each is asserted by the suite named in the matching contract bullet, unless
it is marked as a gap.

- Retiring a handled hold, alert or decision with `--evidence` gives `written`. The row is absent
  from the file, from `body` and from every role view, and no stone is stored.
- Retiring an accepted task with `--cite` (and with `--index` + `--live` when it has dispatch or
  seats) gives `written`. The stdout `value` carries the cite. Linked returned index rows show
  `acceptance: accepted` with `acceptance_source`.
- `--handoff T` moves the seats, the dispatch and each recorded holder onto current task `T`,
  whose `rev` goes up by 1. `T` must itself later show those seats stopped.
- Refusals, each leaving the file unchanged:
  - `conflict` (exit 3);
  - `retire-unmet` (each I5/I6/I8/I9 cause);
  - `invalid-input` (bad kind, bad `--handoff`, cite not JSON);
  - `cite-required` (accepted task, no `--cite`);
  - `record-missing`;
  - `evidence-required`;
  - `schema-unsupported`;
  - `legacy-format` (v1 file);
  - `writer-refused` / `binding-superseded` / `writer-mismatch`.
- A later update of the retired id with its old rev gives `record-retired` (I10). So does reuse of an id that still has a pending-reclaim stone.

## Expected-change surface

This is planning information only. Legitimate work outside it is coordinated with the owner, and
never refused.

- C4: `retire_record`, `require_current`, `state_mutation`, `write_state` (`D:3539-3553`,
  `D:4990-5099`, `D:5104-5149`); `cite_problem` and `drop_settled_history` (`RC:203-259`).
- C5 store, written by C4 code: `mirror_dispositions` and `mirror_task` (`D:5152-5200`). Unlike
  the baseline example, a C5 write **is** part of this unit when `--index` is passed. A change
  there is coordinated with the C5 index contract (`kaola-dispatch-index/1`).
- C5/C1 readers inside C4: `open_dispatch`, `open_seats`, `task_seats` and `live_rows_of`
  (`D:4848-4952`, `D:5658-5664`).
- C1 producer (read-only for this unit): `A:command_list` (`A:871-968`).
- Suites: test-issue-255-lifecycle-state.py and test-issue-259-record-contract.py. Phase 2
  (#281) added the G1, G2, G3, G4, G7 and G8 fixtures there. G5, G6 and G9 remain for #286.
- Docs: `templates/orchestrator/references/lifecycle-state.md:38-41` and
  `templates/orchestrator/references/dispatch-collect.md:60-61`, if G9's `$LIVE` wording is
  corrected. That correction is a template change, rendered as usual.
- P1 module moves (#275–#277) may relocate these functions. The pack owner then refreshes the
  citations; the pack never blocks the move (design §7).

## Evolution

- **Split signal (C4/C5).** If a C5 term acquired a second meaning in C4 — for example, if C4
  started reading the index `status` with semantics different from C5's `COVERAGE` — that would
  argue for an explicit translation at the seam. Today the two C4 readers already disagree on
  closedness (G6). This is a defect inside one language, not yet a second meaning. Evidence that
  would change that: a reviewed decision that keeps the two readers different on purpose.
- **Merge signal.** None is needed: retire, the mirror and the C5/C1 readers already live in one
  module (`D`).
- **Split signal (C4/C1).** C1 already uses "retire" for a different act (`A:2194`). If
  orchestration code ever needs both meanings in one place, rename one of them rather than share
  the word.
- **Retire this pack** when `state.retired` stones are gone from every supported reader, so that
  I4's keep branch, I10's stone refusal and G4 disappear. Also retire or refresh it when P1 moves
  the state tool. The pack then stays in Git history.

## Evidence

- Commits: `8b3779c9c9c76e03f6794b5bf5cf6ffb76bd27c0`, the design `kaola-ddd/1` revision 2
  followed here. `git diff 1a2f577e 8b3779c9 --stat` touches only
  `kpm/docs/history/kpr/docs/designs/ddd-component-2026-10-07/design.md`, so the `1a2f577e` source reading carries
  over unchanged. `7815e0b43c3143851631d437e7ce872697c23bb0` adds the G1, G2, G3, G4, G7 and
  G8 assertions named above. G5, G6 and G9 are unchanged and belong to #286.
- Source read: `scripts/kaola-dispatch.py` (lines cited above); `scripts/kaola-record-contract.py:156,
  203-259`; `scripts/kaola-acp.py:838-968, 2194-2203, 2268-2285`;
  `docs/designs/lifecycle-state-2026-10-04/design.md:28-37, 50, 62-73, 168-176`;
  `kpm/docs/history/kpr/docs/designs/modular-core-2026-10-07/design.md:26-33, 44-52`;
  `templates/orchestrator/references/lifecycle-state.md:36-46`;
  `templates/orchestrator/references/dispatch-collect.md:58-61`.
- Suites read for seam coverage (all in `./scripts/validate.sh --list`):
  - test-issue-255-lifecycle-state.py
  - test-issue-259-record-contract.py
  - test-issue-267-rejection-count.py
  - test-issue-244-dispatch.py (producer side only; no `state retire` call)
  - test-acp-contract.py (C1 `list` default view)

  The full inventory has 88 entries; the others were grep-checked for `"retire"` and contain
  none.
- Probes: two scratch-directory scripts, run at this commit. They wrote no repository file. They
  strip the caller environment the same way the suites' `CALLER_ENV` fixture does (test-255 :29).
  - G9 (C1 → C4): `list` default `[]`; `--include-dead` `[('codex-KT-i7-a','stopped','owned-1')]`;
    retire with the default rows gives `retire-unmet … not in the live rows`; with the
    include-dead rows it gives `written`.
  - G5/G6 (C5 → C4): `in-flight` gives `retire-unmet`; no `status` gives `written`; `"inflight"`
    gives `written`; foreign schema/repo gives `written`.
- Baseline corrections (from reading this unit against the source; see the README pilot findings):
  - the C5 write exists (I12);
  - three counters, not one `rev` (I3);
  - the stone keep branch is a current duty, not a tombstone (I4).
- Oracle bites (review 1). Each line is one temporary flip of the asserted value, run as `python3 tests/contract/<suite> <Class>.<test>`, then reverted. Nothing was committed while a test file was mutated.
  - `StateTool.test_a_v1_file_is_legacy_format_on_retire`: expected `schema-unsupported` instead of `legacy-format`. FAIL: `AssertionError: Tuples differ: (2, 'legacy-format') != (2, 'schema-unsupported')`. Reverted.
  - `StateTool.test_retire_names_record_missing_and_evidence_required`: expected `not-a-code` instead of `record-missing`. FAIL: `AssertionError: Tuples differ: (2, 'record-missing') != (2, 'not-a-code')`. Reverted.
  - `RecordContract.test_an_accepted_task_without_cite_is_cite_required`: expected `retire-unmet` instead of `cite-required`. FAIL: `AssertionError: Tuples differ: (2, 'cite-required') != (2, 'retire-unmet')`. Reverted.
  - `RecordContract.test_a_pending_reclaim_stone_is_kept_and_blocks_its_id`: expected kept id `settled-old` instead of `reclaim-1`. FAIL: `AssertionError: Lists differ: ['reclaim-1'] != ['settled-old']`. Reverted.
  - `ConsolidatedDispatch.test_retire_reads_the_index_execute_and_collect_wrote`: expected acceptance `pending` instead of `accepted`. FAIL: `AssertionError: 'accepted' != 'pending'`. Reverted.
  - `RecordContract.test_index_mirror_error_is_reported_after_retire_writes`: expected `index_mirror` to lack `error`. FAIL: `AssertionError: 'error' unexpectedly found in {'changed': {}, 'error': '<index>: Expecting property name enclosed in double quotes: line 1 column 2 (char 1)', 'index': '<index>'}`. Reverted. The live line named the temporary index file; the error text is the unreadable JSON.
- `./scripts/validate.sh --suite` for `test-issue-255-lifecycle-state.py` and `test-issue-259-record-contract.py` still stops at the inherited stale pin `3de9f61afbfa` (`render-check` exits 1 before the suite body). Suite results are direct `python3 tests/contract/<suite>` runs.

Mirror citations: `kpm/…` paths = github.com/KaolaBrother/kaola-project-manager at fixed commit a13c6d6f264cf965ca45a07670dbf46cd1eb1e5f, subpath history/kpr/ — duplicate KPR source copies retired 2026-10-07; full mapping in `docs/kpm-transfer/HANDOFF.md`.
