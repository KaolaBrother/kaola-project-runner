# Issue259: current source delivery, Host945 prompt correction

The source candidate is clean at `13f0720c9b6fc9b748abbc4f1ee07b0052c24b57`, parent `cefcda13980b888c731a31e4069429412b3a6fba`. The only new source change clarifies node checkpoint accounting and end-of-turn behavior. Four existing binding cases, render, generated and syntax checks pass. The 33 accepted current-state/seat cases and Host945 accepted17-call disposable upgrade proof are reused. Host929/926 scoped native results retain their actual immutable candidates. Host judges this new prompt change. Final affected Opus plus outer review, accepted266 integration and lifecycle remain pending. This is not final issue acceptance.

## Candidate, scope and custody

- Worktree: `/Users/ylmacstudio/Workspace/kaola-project-runner/.kw/worktrees/issue-259`.
- Branch: `workflow/issue-259`. Sole source writer: original f888, same original issue259 run.
- Candidate: `13f0720c9b6fc9b748abbc4f1ee07b0052c24b57`; parent: scoped accepted `cefcda13980b888c731a31e4069429412b3a6fba`. Cefc parent: `1acf4b1263e1345d4df83ef9f63e5371f82c4d06`.
- Behavior commit1acf parent: scoped accepted `badca11e4f3b7b109b1b93c8536d4893208f50d7`. Earlier accepted recovery mechanism: `0553a8dbad2d6e9813075f07e3705a42844eca12`.
- Full patch base: `77d57fc0bae03cbcb70aa0b0b618c76ea7499a33`. Full base-to-candidate diff: 20 authored paths and 42 generated paths. The diff from badca has 10 authored paths and 35 generated paths. The new diff from cefc changes only one authored holder file and ten generated copies.
- Commit1acf implements the owner899 current-state corrections and latest owner913 Delegator report correction. Commitcefc restores the exact existing permission-event/no-additional-full-sweep guidance in the snapshot reference. Commit13f changes only `_node_prompt` instructions and generated copies. Tests, checkpoint engine, state/view code and reporting references remain byte equal to cefc.
- No main, other worktree, installed Skill/configuration, live Host state/index, native history, claim, ledger, archive, forge, release or timer write occurred. No native target, worker or reviewer was started. No lifecycle operation ran. Source custody remains with original259 until Host accepts and exact-stops the writer.

The source uses `/tmp/kpr-i259-899-owner-adoption.md` and the latest authoritative body `/tmp/kpr-i259-913-latest-authoritative-issue.json`, updated2026-10-06T03:46:48Z, body SHA256 `bfc857a3cf9789a762d47bab83e1b05f29df89e2a4bfda9e6a56fd9270a2a526`. The exact latest seat design section is in `docs/dispatch-collect.md`. The earlier BOTH-role relay was superseded before implementation. Requirement2 in candidate AGENTS states the new current-state and Delegator report contract. The other five owner requirements remain byte equal to badca.

Issue266 candidate `95871b8d7c0386a172bf912dbeadc892a87cb50c` remains an unaccepted same-assignment repair under `/tmp/kpr-i266-942-host-review.md`. Request9 fingerprint `e507800b95909dbade73ab53501b94ecf1dca3b18bc9a8ae6f39abe5497971d3` is in progress at original holder `e57ac24a859d36d9cf896cddaf3e755b`. It must repair exact rollback identity, partial-effect child custody and attempt-owned cleanup as Host942 states. It is not integrated. Host must accept and hand over exact bytes before this sole writer changes shared source. No overlapping launch proposal was adopted; no other owner or independent QA was interrupted.

## Current-positive state contract

The Agent judges whether a matter is current or handled from original evidence. The tools validate positive types, role ownership and revision-bound transitions. They do not classify prose or decide business meaning. A handled object leaves its stored applicable collection. All role views and the injected current body derive from those same collections. There is no resolved row, hiding-only policy, tombstone or alternate retrospective text slot. Existing Git and original evidence retain prior facts.

| Current object | Existing operation and resulting state | Preserved duty or refusal |
| --- | --- | --- |
| Handled alert or hold | Owner uses `state retire` with exact record revision and original handled evidence; stored row is removed. | A pending covered recovery input cannot be retired before its exact checkpoint. Newer or unrelated inputs stay current. |
| Host decision | Host updates its existing decision to `settled` with original answer evidence; the operation removes the stored row atomically. Host can also retire a handled pending decision with original settlement evidence. | An absent terminal update is refused. Missing evidence is refused. Sideagent cannot settle the Host judgment. |
| Transcribed Host answer | Sideagent uses the existing host-turn and evidence fields; it remains a positive pending decision with its transcribed marker until Host adoption. | Original answer and Host adoption duty stay visible. |
| Delegator watch | Existing update clears `watch.ID` with null and source effect evidence. A valid normalized adopted/settled transition removes the existing row. | Pending/sent/open/blocked watches remain. Unknown aliases retain original text and the current reconciliation route. Absent terminal rows are not created. |
| Completed task | Existing `state retire` requires Host verdict, closed original dispatch/reclaim links and retrievable outcome citation where required. | Genuine open seats, result links or unfinished side effects remain concrete current duties. |
| Revoked or supported expired Expert grant | Existing authorization normalization removes inapplicable grant rows from effective grant collections. | Effective revocation restrictions still prevent dispatch from restoring a revoked preset through Worker pool defaults. Current stop/reclaim/task duties remain. Unknown expiry is not treated as expired. |
| Known legacy settled decision/watch | Existing migration removes a source-backed terminal row; a transcribed answer becomes pending Host adoption. | Missing owner/effect evidence or an unknown type stays visible as a migration blocker. Repeat migration preserves remaining duties and effective authorization. |

Current typed validation covers alert and decision values, scalar types and original evidence references. The existing eight closed alert-input fields remain unchanged. No new schema, grant, map, history window, scheduler, cancellation or classifier was added.

For an obsolete EXISTING row, refusal names collection/id, record revision and file revision. It gives an executable existing clear/retire operation and its evidence requirements. For an ABSENT row it says do not create it or move handled text into another field. A genuinely unresolved, unclassified matter retains original evidence through the existing current decision/reconciliation route until the proper type is established. Unknown is not resolved.

These are supported recovery forms. The responsible owner replaces each upper-case value with the exact current row, revision and original source. Run a plan before migration. These commands were exercised in isolated CLI cycles; they are not instructions to write the live Host file from this source session.

```bash
python3 scripts/kaola-dispatch.py state retire --file CURRENT_FILE --writer host \
  --source ORIGINAL_SOURCE --kind alerts --id EXACT_ID --expect-rev RECORD_REV \
  --evidence ORIGINAL_HANDLED_EVIDENCE
python3 scripts/kaola-dispatch.py state update --file CURRENT_FILE --writer host \
  --source ORIGINAL_HOST_ANSWER --kind decisions --id EXACT_ID --expect-rev RECORD_REV \
  --set '{"status":"settled","evidence":"ORIGINAL_ANSWER"}'
python3 scripts/kaola-dispatch.py delegator update --file DELEGATOR_FILE --writer delegator \
  --source ORIGINAL_EFFECT --expect-revision FILE_REV --set '{"watch":{"EXACT_ID":null}}'
python3 scripts/kaola-dispatch.py state migrate --file CURRENT_FILE --repo CONSUMER_ROOT --index INDEX --live LIVE_ROWS
python3 scripts/kaola-dispatch.py state migrate --file CURRENT_FILE --repo CONSUMER_ROOT --index INDEX --live LIVE_ROWS --write
python3 scripts/kaola-dispatch.py delegator migrate --file DELEGATOR_FILE
python3 scripts/kaola-dispatch.py delegator migrate --file DELEGATOR_FILE --write
```

Host reconciles the four old alerts against their original dispositions. Their latest inquiry resurrection is one regression observation, not four new tasks. The earlier already-judged retirement input `host:retired/alerts/maintenance-returned@287` and batch `b-78ac20c3ef65` stay valid original references. The repair does not clear genuinely newer maintenance or rewrite original verdicts.

## Delegator user-facing seat summary

The existing `project --seats` projection now supplies one derived summary. The Delegator current view and generated user-report guidance use it. Host reads the same dispatch facts on demand. No mandatory Host section, injected seat block, new reading cycle or timer change was added. Occupancy is not stored in Delegator JSON or a second seat list.

The report groups permitted tiers by their effective shared grant. It shows exact runtime/tier IDs, authorized count and Expert task or standing lifetime. Shared Claude tiers count as one seat; shared Droid tiers count as two. It never adds tier rows to obtain shared capacity. Current linked tasks and verified turn facts distinguish working, idle but unreclaimed, reserved, held/faulted and unknown. Only proven idle available capacity is assignable. A ready session alone proves neither work nor free capacity. Host, bound Sideagent and Worker pool do not consume Elite/Expert seats. Missing Expert authorization is shown as none.

Each grant retains its limits. Available counts are bounded by the effective general cap, Delegator ceilings, shared limits, holds and current resource constraints. Per-grant free counts cannot authorize exceeding the combined cap. Unknown source/holder/task/turn/availability facts produce explicit unknown capacity. A project-root list cannot establish availability of separately receipt-bound native QA resources. Profiles stay on demand.

The existing source resolves live presets and shared occupancy, then relates original index holders and current tasks. Missing original admissions or task links stay unknown; no row or prompt is reconstructed. Both `state view --role delegator` and `delegator view` use this path. `project --seats` retains its original raw grant/session interface and adds the derived summary.

## Actual read of current sources

`/tmp/kpr-i259-913-current-view-receipt.json` records a real candidate CLI read of the current canonical Host file and existing dispatch index with fresh Runner listing. This is an actual source/tool read, not a native model or compaction result. Exit0,0.855036s. It read revision930. The stored alert/decision/hold/unverified collections were empty after Host repair. State SHA256 before and after was `bded93a25a60ffc0db2ef5943d0d5870c634cebbe408ae0a945550de45657819`.

The output `/tmp/kpr-i259-913-candidate-current-delegator-view.json` SHA256 is `7e919bc6c30135404e2ffbf7d2e1447d5505d9f639bf3afc81982d1c3fb1cb37`. It counts grok1/cursor1/codex1/Droid shared2/Claude shared1 and reports Expert none. That historical revision930 output left original f888 correlation unknown. It did not establish free capacity. Current read-only original-source correlation below establishes occupied/unreclaimed custody; the historical output is not a current seat verdict. The read did not write either live JSON.

The earlier `/tmp/kpr-i259-882-index-inspection.json` remains valid: installed `merge_index_rows` can omit a prior in-flight/unknown/repair row. The candidate already has the small `pending_correlation` fix and its named244 regression. The exact historical deletion write is not established. Host owns correlation from original admission/native/holder/task receipts; no missing row, claim or admitted prompt was fabricated or replayed.


Current source correlation is in `/tmp/kpr-i259-945-source-seat-correlation.json`. At file revision948, task `i259-impl` revision160 already links session `codex-KPR-i259-host-compact-impl`, holder `f888667b7e6a5071753d218d0cc0484f` and original admitted item `i259-host-compact-implementation`. Original admission `/tmp/kpr-i259-862-compact-implementation-admission.json` and status `/tmp/kpr-i259-929-status.json` bind ACP `01a10ef7-cb78-70c0-8380-ec495356e431`, applied `codex/default`, `gpt-6.1-sol/high/Fast off`. The last original status is an accepted busy turn; Host945 confirms occupied/unreclaimed custody between turns. Applied selection is not a new native payload-model verification. Missing installed index correlation does not free this seat. The current task needs no identity repair. Host/Delegator uses these exact original sources and the existing on-demand `project --seats` with `--platforms` for a partial catalog. Unmatched turn/resource facts remain unknown; no index row or admitted prompt is created or replayed. No live state/index or native status call was made here.

## Focused affected verification

All commands ran from the original worktree with `/Users/ylmacstudio/.local/share/bash-5.3.20/bin` first on the task PATH. Each receipt has exact argv, candidate, clean status, output hash and elapsed time. Test names retain their existing suite identity; older names containing rehome/settled bags do not weaken the new assertion that current handled text is removed.

| Group | Named cases | Actual candidate | Exit | Seconds | Receipt |
| --- | ---: | --- | ---: | ---: | --- |
| 899-current | 13 | 1acf4b12 | 0 | 10.467405 | `/tmp/kpr-i259-compact-final-899-current.json` |
| 913-seats | 2 | 1acf4b12 | 0 | 0.774917 | `/tmp/kpr-i259-compact-final-913-seats.json` |
| 899-255 | 7 | 1acf4b12 | 0 | 2.185513 | `/tmp/kpr-i259-compact-final-899-255.json` |
| 913-244 | 7 | 1acf4b12 | 0 | 0.887519 | `/tmp/kpr-i259-compact-final-913-244.json` |
| 899-injection | 1 | 1acf4b12 | 0 | 2.124487 | `/tmp/kpr-i259-compact-final-899-injection.json` |
| 899-relay | 1 | cefcda13 | 0 | 0.371259 | `/tmp/kpr-i259-compact-final-899-relay.json` |
| 899-inquiry | 2 | cefcda13 | 0 | 2.710022 | `/tmp/kpr-i259-compact-final-899-inquiry.json` |
| 899-render-r2 | build/check | cefcda13 | 0 | 0.050530 | `/tmp/kpr-i259-compact-final-899-render-r2.json` |
| 899-generated-r2 | build/check | cefcda13 | 0 | 2.437172 | `/tmp/kpr-i259-compact-final-899-generated-r2.json` |
| 899-syntax-r2 | build/check | cefcda13 | 0 | 0.100324 | `/tmp/kpr-i259-compact-final-899-syntax-r2.json` |

The 33 behavior/interface cases cover repeated create/update/resolve/retire CLI cycles, stored JSON and all role views, mock ACP injection absence, pending newer maintenance, refusal/CAS, unknown legacy evidence, migration repeat, effective grants, shared-tier counts, linked busy work, unreclaimed/reserved/held/unknown seats, missing Expert, installed Runner projection compatibility, exact checkpoint binding and inquiry recovery without business writes. The injection case uses a real ACP mock transport and exact fixture stop; it does not start a native model.

Behavior receipts on1acf remain valid for the state/view boundaries: state/view code, tests, AGENTS, lifecycle and inquiry guidance remain byte equal. Cefc changed only snapshot wording;13f changes only holder `_node_prompt` and generated copies. Four existing binding cases and final13f render/generated checks cover this changed prompt. Historical native results retain their original scope and labels. Receipt candidate labels were not rewritten. `validate.sh --suite test-generated-skills.py` selected the existing generated suite, one of80 inventory entries; this was not a whole-suite run. The final disposable validation root `/tmp/kaola-val.vFQfjh` was removed; matched/killed/residual PID lists were empty.

Exact selected commands follow. Do not repeat them just for delivery; their matching receipts already establish the results.

```bash
python3 tests/contract/test-issue-259-record-contract.py RecordContract.test_current_exception_resolution_repeated_cli_views_and_newer_recovery RecordContract.test_refusal_names_current_clear_and_absent_terminal_is_not_created RecordContract.test_terminal_migration_repeats_preserve_pending_adoption_and_grants RecordContract.test_ended_eligibility_leaves_grants_without_restoring_pool_or_losing_work RecordContract.test_watch_alias_text_stays_blocked_when_status_is_added RecordContract.test_watch_alias_tokens_keep_pending_data_and_status_precedence RecordContract.test_release_named_typed_duty_is_preserved_with_adoption_guards RecordContract.test_pending_legacy_text_requires_rehome_and_normal_update_removes_settled_bags RecordContract.test_delegator_update_and_view_are_closed RecordContract.test_cleanup_names_removals_and_legacy_refusal_says_how RecordContract.test_closed_task_leaves_and_pending_goal_stays RecordContract.test_settled_task_and_retirement_leave_the_routine_view RecordContract.test_nested_types_are_refused_and_bytes_stay
```

```bash
python3 tests/contract/test-issue-259-record-contract.py RecordContract.test_delegator_seat_summary_groups_live_task_states_cap_and_no_host_cycle RecordContract.test_delegator_missing_expert_and_unknown_sources_do_not_imply_free_seats
```

```bash
python3 tests/contract/test-issue-255-lifecycle-state.py StateTool.test_a_sideagent_settles_a_decision_only_as_transcribed_evidence StateTool.test_a_stable_fault_id_recurs_but_a_stale_event_does_not MaintenanceCheckpoint.test_recovery_checkpoint_binds_sent_input_batch_and_holder_keeps_newer MaintenanceCheckpoint.test_recovery_unavailable_sources_stay_visible_and_scoped_clear_keeps_other_alerts MaintenanceCheckpoint.test_host_retirement_preserves_an_earlier_sent_checkpoint_range RenderedGuidance.test_lifecycle_reference_is_generated_linked_and_bounded RenderedGuidance.test_node_reference_names_the_implemented_contract
```

```bash
python3 tests/contract/test-issue-244-dispatch.py DispatchEntry.test_seats_view_binds_identity_and_retains_grant_states DispatchEntry.test_seats_missing_source_does_not_claim_zero_occupancy DispatchEntry.test_seats_omitted_live_lists_through_a_non_executable_installed_runner DispatchEntry.test_seats_view_without_the_new_keys_is_unchanged DispatchEntry.test_shared_droid_pool_admits_two_items_and_refuses_a_third DispatchEntry.test_shared_seat_blocks_the_pair_and_an_independent_item_runs DispatchEntry.test_seats_omitted_live_without_an_installed_runner_stays_unknown
```

```bash
python3 tests/contract/test-issue-259-record-contract.py RealAcpInjection.test_start_send_observe_stop_injects_the_projected_view
```

```bash
python3 tests/contract/test-issue-259-record-contract.py RecordContract.test_delegator_relay_tokens_and_a_prose_status_blocks_the_write
```

```bash
python3 tests/contract/test-issue-255-lifecycle-state.py HolderNodeMode.test_recipe_refusal_for_owed_recovery_is_visible_once_in_both_views HolderNodeMode.test_inquiry_request_recovers_recipe_without_business_write
```

```bash
./scripts/render-skills.py --check
```

```bash
bash scripts/validate.sh --suite test-generated-skills.py
```

```bash
python3 -c 'import py_compile,subprocess; [py_compile.compile(p,doraise=True) for p in ['"'"'scripts/kaola-dispatch.py'"'"','"'"'scripts/kaola-record-contract.py'"'"','"'"'tests/contract/test-issue-259-record-contract.py'"'"']]; subprocess.run(['"'"'git'"'"','"'"'diff'"'"','"'"'--check'"'"','"'"'77d57fc0bae03cbcb70aa0b0b618c76ea7499a33'"'"','"'"'HEAD'"'"'],check=True); print('"'"'PASS Python syntax and diff'"'"')'
```

Preserved failures remain evidence: `/tmp/kpr-i259-899-first-check.txt` had a missing test helper; `/tmp/kpr-i259-899-second-check.txt` had invalid fixture recovery kind/evidence types; `/tmp/kpr-i259-913-first-check.txt` had misplaced parser arguments; `/tmp/kpr-i259-913-guidance-precommit.txt` caught a lost exact no-synchronous-roundtrip phrase. These were corrected without weakening original assertions. The clean1acf generated suite failed two existing literal guidance assertions; `/tmp/kpr-i259-compact-final-899-generated.json` retains exit1. Source guidance was restored in cefc and the unchanged generated checks passed. Earlier budget refusals led to reference consolidation; budgets and timeouts were not raised. Original native negatives, immutable055 C7 failure, Bash prerequisite repair and badca test-binding failure remain in their original receipts and accepted archives.

## Accepted native evidence and unchanged boundaries

Host929 independently accepts `/tmp/kpr-i264-882-host-proof.md` against immutable055. Its disposition is `/tmp/kpr-i264-929-host-review.md`; raw verification is `/tmp/kpr-i264-929-host-proof-verification.json`. The consolidated runtime boundary is `/tmp/kpr-i264-native-boundary-limitations-20261006.md`. These are original independent actual native results. No model test was repeated by this writer.

Actual Claude Code2.1.289 sonnet/high/Fast off scratch Host `497f81ce9465878e1000a2540ad3b61c`, ACP `bc89eec216928410bb8c2e6097458c81`, occurrence `3d88c0d0-57e1-44d7-8aa8-fb2a53a9754a`: native events41/42 created typed input43 before reload46 at unchanged business revision5. Full installed Read49/50, byte/end-line checks51 and TASK-B52 prove current installed Project Runner17407B SHA256 `1af732f378a11bd04e4533a3e1fe38cef9b9b48b393360748d0a8030f5524df7` and platform10472B SHA256 `68989e48d2cd3bcd4fd87f78f5f002d8399183b3e0e197704420d6a65bfb9e59` reread and use.

Seven non-overlapping bound node lifetimes have matched stops. Busy input2, newer decision@5, qa-gap-missing and original Host judgments survived. Visible partial and invalid-recipe results led to actual Host binding repair and scoped recovery. Final checkpoint `b-3364a45e5f1b`, holder `ce3718cde5f1b4baf4780c094255f8e8`, recovery4 is verified with unavailable{}. Diagnostic Workflow originals were fixtures; controller request inputs2-4 are not additional native occurrences or a real outer inquiry. Scratch Host and original Devin helper exact-stopped exit0/residual[]. No helper duty remains.

The hash manifest compares14 named functions against immutable055. Thirteen are unchanged, including registration, selection, settlement, node start/stop/reclaim, reload, `command_state_recovery_input`, batch/checkpoint validation and `apply_checkpoint`. Only `_node_prompt` differs, with the instructions described below. Every other holder function AST and the checkpoint engine bytes match cefc. The current prompt was inspected and checked model-free; its actual native use is not claimed. Current state and role-view changes have the affected checks above. This is scoped reuse, not a claim that all current files equal055. Node lifetimes171.647–557.438s are retained as model/source reconciliation cost, not build-suite cost; the seven-node exploration is not repeated.

Host926/929 also accepts immutablebadca finite DSH0.2.0-rc.2 `/compact`: original persisted native summary/end52/53/55 matched completed32; automatic reload35 preceded full current installed platform Read45,165lines/10450B, and changed TASK-B end70. Same-session gauge13255→9815/cap1000000 is scoped measured context, not a universal detector. Original target/helper exact-stopped0[]. The finite candidate adapter route is reused; no global installed adapter activation or background forwarding claim follows. Busy/null/save/cancel remain fixture cases.

Codex-specific `clientCapabilities.session.compaction={}` at both initialize paths is preserved. Installed codex-acp2.0.1 supports that interface and finite `/compact`; the actual corrected native initialize request, structured completed event and Codex Host-only chain remain unobserved here. The pre-fix raw initialize packet is missing; original fallback compact77294→completed77303 is real. No-compaction or permanent unsupportedness is not inferred. Other original runtime read/use and steer evidence remains in the consolidated report. Droid/Cursor unreached native boundaries are unverified, not failed. ZCode nested accounting has no proven current-capacity mapping, so no heuristic or new field was added.

Installed bridge emission, independent real outer inquiry and all-runtime Host-only outcome3 remain unverified. Native-owned reload remains independent of maintenance. The session-scoped usage-handler AST and finite DSH seam match accepted badca; no null-last-good policy, token-drop rule or guessed completion was added.

## Prepared pending live step: Host allocation only

This is a prepared command plan, not an executed proof. Owner: original Host. Next: accept the source and exact-stop f888, then allocate only the missing corrected Codex negotiation/signal boundary and independent outer inquiry. Do not rerun accepted Claude seven-node QA or DSH finite read/use.

Exact proposed resources: one disposable `codex/default` diagnostic Host, GPT-6.1 Sol/high/Fast off, and one transient `codex/luna` Sideagent, GPT-6 Luna/max/Fast off, permitted to run concurrently. That is two physical native sessions. Host and Sideagent are worker-seat exempt, but still require exact service/resource authorization and receipt-bound custody. No extra worker or reviewer is needed. If those presets are unavailable, Host must select a supported authorized node and record the actual recipe; a project-root seat list is not that grant. Opus final affected review has its own Host-owned allocation.

Use the existing disposable consumer flow, outside live roots, with an isolated record root and evidence directory. Bind actual owner goal/grants and a real retained duty to retrievable original sources. Label diagnostic Workflow seeds as fixtures. Missing originals must return visible obligations. Use existing tools, not a new harness. Clear inherited dispatcher/Host bindings for disposable start. Set each path placeholder to Host-selected absolute paths.

```bash
K259_CANDIDATE=/Users/ylmacstudio/Workspace/kaola-project-runner/.kw/worktrees/issue-259
K259_BASH=/Users/ylmacstudio/.local/share/bash-5.3.20/bin/bash
K259_PROOF=HOST_SELECTED_ABSOLUTE_DISPOSABLE_ROOT
K259_RECEIPTS=HOST_SELECTED_ABSOLUTE_EVIDENCE_DIRECTORY
export KAOLA_ACP_RECORD_ROOT=HOST_SELECTED_ABSOLUTE_RECORD_ROOT
export PATH="/Users/ylmacstudio/.local/share/bash-5.3.20/bin:$PATH"
unset KAOLA_ACP_DISPATCHER KAOLA_ACP_HEARTBEAT_HOST KAOLA_ACP_HEARTBEAT_HOST_SOCKET KAOLA_ACP_CHILD_RECORD
"$K259_BASH" "$K259_CANDIDATE/scripts/kaola-tmux.sh" codex start --repo "$K259_PROOF" \
  --session codex-K259Proof-orchestrator-main --tier default \
  --model gpt-6.1-sol --effort high --fast off > "$K259_RECEIPTS/host-start.json"
```

Read actual applied model/version/holder/configuration and the original written initialize_request: `request.params.clientCapabilities.session.compaction == {}` and `written == true`. Record the adapter response separately. Load the candidate Skill in this scratch Host. Bind its node with the existing `sideagent.mode=node`, absolute runner and state_tool, and this existing argv:

```json
["codex","start","--repo","HOST_SELECTED_ABSOLUTE_DISPOSABLE_ROOT","--session","codex-K259Proof-sideagent","--role","sideagent","--tier","luna","--model","gpt-6-luna","--effort","max","--fast","off"]
```

End the legitimate setup turn; let its actual initial batch checkpoint and exact-stop. Record business revision equal to handled_host_revision, with original current duty retained. Do not forge a handled revision or business edit. Then send one supported bounded compact:

```bash
"$K259_BASH" "$K259_CANDIDATE/scripts/kaola-tmux.sh" codex send --repo "$K259_PROOF" \
  --session codex-K259Proof-orchestrator-main --text /compact > "$K259_RECEIPTS/compact-send.json"
"$K259_BASH" "$K259_CANDIDATE/scripts/kaola-tmux.sh" codex capture --repo "$K259_PROOF" \
  --session codex-K259Proof-orchestrator-main --full --inline > "$K259_RECEIPTS/host-capture.json"
"$K259_BASH" "$K259_CANDIDATE/scripts/kaola-tmux.sh" codex capture --repo "$K259_PROOF" \
  --session codex-K259Proof-sideagent --full --inline > "$K259_RECEIPTS/node-capture.json"
python3 "$K259_CANDIDATE/scripts/kaola-dispatch.py" state view --role sideagent \
  --file "$K259_PROOF/.kaola/heartbeat-prompt.json" > "$K259_RECEIPTS/state.json"
```

Require genuine current-session structured completed→original detection→registered input before reload can skip maintenance→safe-boundary selected/sent input→real node original goal/grants/duties/decisions/task/result/reclaim reads→exact batch/holder checkpoint→exact reclaim at unchanged business revision. Later/unrelated inputs remain pending. Generic last_verified cannot settle it. Preserve native-owned Skill reload and actual current-file read/use receipts independently. If the completed event remains unobserved after this finite attempt, retain uncertainty and actionable inquiry recovery; do not flood tokens, run a matrix or force PASS.

Independent outer inquiry stays separate from controller admission. The current Delegator must observe the actual visible recipe/checkpoint duty and request the same Host to run the existing bounded operation below. A controller request alone is not independent inquiry proof. The accepted recipe-refusal and Host binding repair need no native repetition unless this current affected boundary requires it.

```bash
python3 "$K259_CANDIDATE/scripts/kaola-dispatch.py" state recovery-input \
  --file "$K259_PROOF/.kaola/heartbeat-prompt.json" --kind request \
  --source ORIGINAL_OUTER_INQUIRY --evidence ORIGINAL_CURRENT_FAILURE
"$K259_BASH" "$K259_CANDIDATE/scripts/kaola-tmux.sh" codex stop --repo "$K259_PROOF" \
  --session codex-K259Proof-orchestrator-main --expected-holder-instance-id ACTUAL_HOST_HOLDER \
  > "$K259_RECEIPTS/host-exact-stop.json"
python3 "$K259_CANDIDATE/scripts/kaola-acp.py" list --repo "$K259_PROOF" \
  --record-root "$KAOLA_ACP_RECORD_ROOT" --include-dead > "$K259_RECEIPTS/after-stop.json"
```

The recovery-input command runs inside the owned scratch Host. It does not require a fake business write. Match final Host/node receipts to actual holders; require exit0/residual[]. Reconcile unknown effects before safe retries. Initial plus three safe transient retries apply before a persistent service-failure claim; authentication/quota/rate-limit refusals retain their existing handling. No polling loop, timeout raise or blind replay is prepared.

## Host945 returned-maintenance correction

The original batch `b-c847c4805ffe`, holder `7d9d5566441ce872822562a96edd29a8`, input `host:tasks/i266-grok-bot-entry@710` was returned because the node used `applied` for an unchanged Host-written task. The original checkpoint remains `verified:false`, settled empty, ack709/handled710. The correct accounting is `retained` with the task's current next reader. The visible partial result is valid evidence. Host945 owns its one-alert disposition; it does not require replay, another checkpoint, another node or another stop. This source session made no live disposition write. Original final and Host disposition are `/tmp/kpr-945-original-node-final.txt` and `/tmp/kpr-945-maintenance-returned-disposition.md`.

The candidate `_node_prompt` now states that `applied` refers only to this node holder's authorized write or `retired:<kind>/<id>` removal. `retained` refers to an unchanged Host record with `next`, `owner` or `wait`; do not rewrite it for accounting. The example uses `retained`. The prompt says checkpoint once, return any partial result in the final reply and end. Do not write a second empty or replayed checkpoint or prolong script-source investigation. These are existing reference semantics from `templates/orchestrator/references/sideagent-node.md`82–89. The reference and checkpoint engine are unchanged. There is no automatic retry, gate, timer, state store or permanent prose test.

`python3 /tmp/kpr-i259-945-prompt-inspection.py` constructed the actual candidate business709→710 and recovery-only710→710 prompts in a temporary root. Receipt: `/tmp/kpr-i259-945-constructed-prompts-20261006/receipt.json`. The recovery request is a diagnostic fixture, not a genuine native event. The temporary root was removed. This establishes the sent-prompt construction boundary, not model adoption.

| Actual constructed prompt | Bytes | SHA256 |
| --- | ---: | --- |
| `/tmp/kpr-i259-945-constructed-prompts-20261006/standard.txt` | 2612 | `86d64a77289d3b52a23319827bbbb0b53d4a73265d74744cdeb75f02fa7464b6` |
| `/tmp/kpr-i259-945-constructed-prompts-20261006/recovery.txt` | 3727 | `28f37c0896889a8163362e8c811effc10ae04668e64d6b225981dc8d4835166b` |

The following existing checks ran on exact clean13f. Their receipts bind argv, output SHA256 and elapsed time. No new test was added.

| Check | Exit | Seconds | Receipt |
| --- | ---: | ---: | --- |
| 945-checkpoint-binding | 0 | 2.967599 | `/tmp/kpr-i259-compact-final-945-checkpoint-binding.json` |
| 945-render | 0 | 0.048750 | `/tmp/kpr-i259-compact-final-945-render.json` |
| 945-generated | 0 | 2.494332 | `/tmp/kpr-i259-compact-final-945-generated.json` |
| 945-syntax | 0 | 0.064345 | `/tmp/kpr-i259-compact-final-945-syntax.json` |

```bash
python3 tests/contract/test-issue-255-lifecycle-state.py MaintenanceCheckpoint.test_two_consecutive_nodes_account_for_their_fixed_inputs MaintenanceCheckpoint.test_a_checkpoint_needs_the_nodes_own_identity_and_a_valid_range HolderNodeMode.test_a_partial_checkpoint_returns_its_batch_to_the_host_once HolderNodeMode.test_sent_recovery_checkpoint_keeps_later_signal_and_exact_reclaims_first_node
./scripts/render-skills.py --check
bash scripts/validate.sh --suite test-generated-skills.py
```

The syntax receipt gives its exact Python argv and `git diff --check cefc HEAD`. Render `--write` produced all ten holder copies. Generated validation selected one existing suite; `/tmp/kaola-val.khQXnL` was removed, matched/killed/residual lists empty. Accepted33 state/seat cases,17 upgrade calls,055 native chain and finite DSH results were not repeated. No native node, reviewer, model or live installation was started.

## Six current owner answers

1. **Template fidelity.** Generated Host and Delegator entries retain canonical native timer text. Delegator generated inquiry/report guidance makes the user-facing seat summary mandatory. Host remains on-demand for seat facts. Existing timer drift/readback handling and role guidance are preserved; Final13f render and generated checks pass; the accepted cefc timer/report boundaries are unchanged. No live installed timer readback or live consumer migration write was done here. The disposable migration proof remains labeled cefc. Missing readback remains unknown with the existing verification route.

2. **Current, inspectable information.** Handled rows now leave stored applicable collections. Typed owner writes, CAS, source-backed migration, original retire/checkpoint references and all derived views preserve genuinely pending work and authorization. Repeated CLI cycles and actual mock ACP injection prove removed rows stay absent; a read-only current-source receipt confirms stored/view absence after Host repair. Delegator summary uses one derived projection and explicit unknowns; no seat JSON duplication exists. Current cap/shared/held cases pass. Useful VRPAI/VRPCAD advancement remains original accepted evidence, not a new claim from JSON validity. Original f888 is occupied/unreclaimed from exact admission/status/current task links, despite the installed index omission. This does not establish global free diagnostic resources. Final owner judgment that bookkeeping does not displace useful work remains pending.

3. **Host autonomy and Sideagent lifecycle.** Accepted independent055 native Claude chain proves compaction recovery input before reload, no fake business revision, original-source node reconciliation, preservation of newer duties, scoped checkpoint and exact reclaim. Thirteen of14 named carrier/recovery functions match055. Only the current node prompt changes. Existing own-writer/retained semantics are now explicit, with one checkpoint and a final partial return before ending. Four binding cases and actual constructed prompts pass model-free inspection. Native use of this changed prompt is unmeasured; no repeated native chain is claimed. Nodes do not make Host judgments or invent tasks. Native-owned reload remains independent. Actual corrected Codex structured negotiation, independent outer inquiry, installed emission and all-runtime Host3 stay pending with Host as owner.

4. **Recovery and informed autonomy.** Current refusal names existing row/revision/clear command/evidence; absent handled rows are not recreated. Unknown original evidence remains visible. Tests cover newer inputs, binding/checkpoint mismatch, missing sources, recipe refusal, typed migration and inquiry at unchanged business revision. Accepted native partial/recipe failure and actual Host binding repair are reused. Safe retry and exact identity rules are preserved. No permanent unsupportedness, universal fault-freedom or fixture-as-live PASS is claimed.

5. **Continuous improvement.** Existing state resolution, seat projection and suites were reused. Guidance was consolidated within unchanged byte budgets. The current prompt correction reused33 accepted state/seat cases and ran only four existing binding cases plus render/generated checks. It reuses the correct reference semantics and removes the misleading applied-task example. No full113/101 inventory or native matrix was repeated. Final module checks are short; earlier whole-module42.79/65.65s and native172–557s costs remain evidence. The existing Host improvement path still locates coupling, defines the preserved outcome and affected boundary, compares minimal reuse/removal, resolves material scope choices, then verifies integrated interfaces. No new recurring optimization phase, ledger or framework was added. Broader Rust/Swift/Workflow research remains its existing owner scope.

6. **Upgrade continuity.** Existing versioned readers and plan-first migrations remove proven handled rows, preserve unknown blockers and repeat safely. The actual disposable managed-copy upgrade selected the changed generated Delegator report and executed its sibling candidate tool. Original supported real-shape inputs retain19 pending watches,13 tasks, grants, instructions, stop/cadence/entry/timer owner and Chinese user_language; three source-backed settled decisions leave stored state. Business revision602 stays602. Repeat migrations and managed-copy refresh leave bytes unchanged; repeated current facts match except fresh observation time. Preserved timer text returns match, absent readback returns unavailable.17 model-free calls took1.662225s total. A filtered Codex-only root leaves other preset classes unresolved; the existing --platforms exact candidate catalog route produces the five correct groups with capacity unknown. Exact mapping/tool/reference and receipts are in /tmp/kpr-i259-939-report-upgrade-continuity-20261006.md. This proves disposable installed-template selection and current tool-view continuity, not native model adoption, live installation, complete runtime-root upgrade or native timer API readback. Installed bridge emission, native use of the changed Delegator report and final integrated adoption remain Host-owned. Host945 accepts this17-call evidence at immutablecefc. The changed reporting reference, tool, catalog and migration/view code match current13f. The copied holder was not invoked by these calls; its prompt now differs. This does not claim a full current-tree installed copy or native adoption. Accepted33 checks and native055/DSH outcomes are reused; only current prompt binding/render checks ran.

## Current report and upgrade frontier

Host939 scoped source acceptance and Host945 scoped upgrade/report acceptance are adopted. The current six-answer file is reconciled at `/tmp/kpr-i259-six-requirement-answers-20261006.md`; its answer bodies match this delivery exactly. The old bbf view is retained as historical evidence, not a current verdict. Accepted cefc artifact bytes read by Host939 remain under their `accepted-cefcda13-host939` names.

The smallest changed report boundary now has actual disposable managed-copy selection/migration/current-view/repeat evidence in `/tmp/kpr-i259-939-report-upgrade-continuity-20261006.md`. It uses original supported real-shape inputs, preserves pending duties/grants/language and native timer text, and returns the precise filtered-catalog recovery route. The upgrade proof needed no source change. It remains labeled cefc. The current13f source return changes only node-prompt instructions and generated holder copies. Host945 accepted cefc bytes remain under `accepted-cefcda13-host945` names. This result does not authorize diagnostics or live installation. Final affected review and lifecycle remain pending.

## Hashes, generation and unchanged run integrity

Full binary patch: `/tmp/kpr-i259-host-compact-implementation.patch`,822254bytes, SHA256 `c8ce920ccad55a99ffb668c8f5129b97f8b6c7935b981f004a440953aecce28e`.
Authored patch: `/tmp/kpr-i259-host-compact-implementation-authored.patch`, SHA256 `4364b8c1825eaff9c53e48d7b9ae48424562b1795b3af1850e36e269e8fecccc`.
Full source/generated/receipt hash manifest: `/tmp/kpr-i259-host-compact-implementation-hashes-20261006.json`. It binds all62 changed paths to base and candidate hashes, original claims/ledger, protected files, test AST changes, render reference sizes, exact commands, failures, cleanup, accepted native sources and unchanged function ASTs.

Generated payload was produced by `./scripts/render-skills.py --write`, never by hand. Final `--check` and selected generated suite pass. Lifecycle reference8167B, snapshot8114B and inquiry6361B remain within unchanged8192B limits. Frozen grok-golden, native reload helper/hook/text, Bash prerequisite repair, accepted265 selection/cleanup/improvement guidance and original263/264 tests remain preserved. The current owner-driven255/259 assertion changes are listed in the manifest; no false claim that every test body is unchanged is made.

Original claim digest `5ea624f9b9c061bd8c53dc4e20b20ac5a7c35ce95f4d1f244b17fd164f9a29d5`; canonical state SHA256 `610d647040b2ad4c948e36ee9480f14d92e96ade95aa3449210808fd7ef9cb75`; immutable4DONE ledger SHA256 `2efb63f6fb7c9da77f74d12abb4754d3e1b4de558599057bd9a2b59a133ab53b`. No line or claim was rewritten. Finalization was reread for original recovery only. Existing finalization receipts remain in place.

Current source SHA256 values follow. Generated hashes are in the same manifest.

| Authored path | Candidate SHA256 |
| --- | --- |
| `AGENTS.md` | `a803cfdbbbb1494a399b146bfb7f55d535ba7372bd62ca1f199714e3522cd8f5` |
| `docs/api.md` | `e2a77e2346ca06f9df9874f8f49f4968544361aed290805db6f25c78e178820c` |
| `docs/dispatch-collect.md` | `234f6211f3eb12e63d4ee8beb45e60b4b560f632be4aedc2269bc2fc20fd8abc` |
| `platforms/codex.yaml` | `feccec4c41f9c57a4d2a912b6062a6f54de990c46f9e3a0f63a77c2c544a0d09` |
| `platforms/dsh.yaml` | `c7769d9ae67903d5fcbf1e22f085bb4ed89f781b90998310a8c4b8a106b45092` |
| `scripts/kaola-acp-holder.py` | `d8cc9dc147f69db50dc5be5c7cf1f7efced677c19813155792a191aedb72f280` |
| `scripts/kaola-dispatch.py` | `0633a186ff2b7c68eaf5040c07c9458001ae258f24e0970189a89b79f6ace78c` |
| `scripts/kaola-dsh-acp.py` | `b1879fca1791845608ce00fa162c122f0729cdb105516d0d4f27dbe69c506e6a` |
| `scripts/kaola-dsh-steer.mjs` | `f19a3beea03899dfae883ef84de5ede36e0503ed7be9df8b2f5d9de4f9b82da2` |
| `scripts/kaola-record-contract.py` | `703df5d0dcfbdd8405d3fdc8d88203b2cac0c7fc423ec334c743c5a0c47f3f90` |
| `templates/kaola-delegator/references/inquiry-report.md` | `ea468ca05d80351ba63a0e02f89ff318d7902451ccc160ccc874e3b847c9befc` |
| `templates/kaola-delegator/references/snapshot.md` | `efdbc531a7999cd6928495c3597329434dec0a9fd71db6a7bbffa22c141480f6` |
| `templates/orchestrator/references/duty-reconcile.md` | `ab59435d13dcf29f462eeb7813a8d3248265aa48f2364c10acd3090d1c834c4d` |
| `templates/orchestrator/references/lifecycle-state.md` | `a9c2243b491cd5efe4772d0bb90a0a5065185bddb43ae6ae3261d42fa8eb90b9` |
| `templates/orchestrator/references/sideagent-node.md` | `884fc413fdc01c5f094692b00109fb7ba824efe8236d760fb2a89b820a3f3eae` |
| `tests/contract/test-acp-contract.py` | `fd292ecf8cb9d51bbfd3511b8515cf5d0d27efa7d48fba05aa840e0da6cf6128` |
| `tests/contract/test-issue-255-lifecycle-state.py` | `b02573f96567f128f40714cc42a7de6015f16b886b07fdc981f283554069fd87` |
| `tests/contract/test-issue-259-record-contract.py` | `4d6c843ec4dca8aab610068d5904891329c101ac8ce4c8f12a6a3710d750a731` |
| `tests/contract/test-issue-264-compact-recovery.py` | `d2b6e6917a77921f621cbdfdcd50b3b3568c4018659ec5d8840eef1bea8a879a` |
| `tests/contract/test-project-compact-notice.py` | `9f64dad5d7f6f7e8111970e3e7b8f426b83b92b4fbdb38de45f92e1e4e0bdc42` |

Original accepted badca delivery/patch/manifest are retained under their `accepted-badca11e` names. Accepted055 artifacts remain under their original archived names. They retain their actual candidate labels and original outcomes. This report replaces the current delivery view, not the accepted evidence.

Host owns final integrated affected Opus Extra High and outer personal verdict, exact resource grants, pins/Seats restart disposition, original259/263/264/265 lifecycle and any conditional unused stable PATCH. New266 remains unaccepted repair. No finalize, sink, install or publication occurred. Host939 accepted cefc source in scope; Host945 accepted its disposable upgrade/report proof. Current13f prompt correction awaits Host. Original26695871b8d request9/e507800b remains unaccepted. Corrected Codex negotiation and independent outer inquiry remain unverified and Host-owned; a prepared plan is not allocation authority. Optional unmeasured boundaries are not new blanket prerequisites. Final integrated acceptance remains pending.
