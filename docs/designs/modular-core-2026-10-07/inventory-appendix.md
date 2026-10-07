# Function-level responsibility matrix — 721 rows (THIS-round output)

Source revision `7012e4d6` (bridge read-only original `/tmp/kpr-source-inventory-bridge-20261007.json`: 4 file sha256s, 721 qualified-name rows with line/end_line/top_level; syntactic calls intentionally excluded from ownership). Corrected AST arithmetic: **top 522 / nested 199 / all 721** (the earlier 1243 double-counted top-level defs into nested; `recount.py` in this directory is the machine-runnable check — it validates per-file top/nested/all AND sha256, exiting 1 on any mismatch).

Assignment status, stated honestly: rows with a component are a KEYWORD-ASSIGNED DRAFT (first-match on qualified name); **223 rows carry an explicit per-file keep-in-place hold** (dispatch 92, acp 77, record-contract 34, holder event-loop 20) — these are NOT silently unowned; they are the P1 step-1 source-review set, each hold naming its file. `quota_module` → C2 with a REAL code contract (`scripts/kaola-quota.py` contains parse/resolution code — catalog + deterministic resolution, never "pure data"; the holder's load edge C1→C2-code stays in the DAG). Zero rows are blank.

**P1 residual (issue #275, slice 1) note:** `inventory-matrix.json` remains the authoritative assignment. The 18 explicit keep-in-place rows plus the two recorded arguable calls (`parse_flat_yaml`, `line_size`) are decided in the section at the end of this file and are marked in place below; every other row in this table is the pre-source-review draft.

| file | qualified_name | line | top | primary |
|---|---|---|---|---|
| kaola-dispatch.py | `_load_record_contract` | 41 | Y | core-atomic |
| kaola-dispatch.py | `emit` | 122 | Y | keep-in-place (P1 adopted keep-in-place: shared stdout JSON receipt emitter for C4/C5 commands; no single owner and not minimal-core identity/process/atomic) |
| kaola-dispatch.py | `fail` | 128 | Y | keep-in-place (P1 adopted keep-in-place: shared stdout failure emitter for all dispatch commands; file-local CLI plumbing) |
| kaola-dispatch.py | `load_object` | 135 | Y | core-atomic |
| kaola-dispatch.py | `parse_flat_yaml` | 145 | Y | C2-acp-adapters (P1 resolved C2-acp-adapters: sole consumer catalog_from_files (already C2) reads C2-owned platforms/*.yaml; the generic reader carries no C5 admission policy; the recorded C5 alternative is closed) |
| kaola-dispatch.py | `catalog_from_files` | 164 | Y | C2-acp-adapters |
| kaola-dispatch.py | `platform_paths` | 203 | Y | C2-acp-adapters |
| kaola-dispatch.py | `authorization_object` | 222 | Y | C1-lifecycle |
| kaola-dispatch.py | `as_id_list` | 260 | Y | C5-dispatch |
| kaola-dispatch.py | `normalize_grants` | 268 | Y | C5-dispatch |
| kaola-dispatch.py | `parse_expiry` | 338 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `current_authorization` | 350 | Y | C5-dispatch |
| kaola-dispatch.py | `availability_map` | 388 | Y | C5-dispatch |
| kaola-dispatch.py | `grant_index` | 402 | Y | C5-dispatch |
| kaola-dispatch.py | `shared_seat_capacities` | 406 | Y | C1-lifecycle |
| kaola-dispatch.py | `eligibility` | 419 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `eligibility.withhold` | 433 | n | C4-state |
| kaola-dispatch.py | `capability_summary` | 518 | Y | C2-acp-adapters |
| kaola-dispatch.py | `current_candidates` | 538 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `command_project` | 559 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `observed_at` | 585 | Y | core-identity |
| kaola-dispatch.py | `seat_projection` | 589 | Y | C1-lifecycle |
| kaola-dispatch.py | `project_seats` | 663 | Y | C1-lifecycle |
| kaola-dispatch.py | `seat_summary` | 669 | Y | C1-lifecycle |
| kaola-dispatch.py | `delegator_seats` | 776 | Y | C1-lifecycle |
| kaola-dispatch.py | `present_value` | 812 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `application_of` | 820 | Y | C1-lifecycle |
| kaola-dispatch.py | `advertised_of` | 838 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `application_slot` | 855 | Y | C1-lifecycle |
| kaola-dispatch.py | `switch_authorized` | 869 | Y | C5-dispatch |
| kaola-dispatch.py | `model_match` | 881 | Y | C2-acp-adapters |
| kaola-dispatch.py | `field_verdict` | 894 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `model_applied_verdict` | 903 | Y | C5-dispatch |
| kaola-dispatch.py | `effort_applied_verdict` | 928 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `flag_of` | 943 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `advertised_verdict` | 959 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `selection_report` | 973 | Y | C1-lifecycle |
| kaola-dispatch.py | `applied_mismatch` | 1015 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `nested` | 1019 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `last_prompt` | 1030 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `finger_norm` | 1035 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `fingers_equal` | 1044 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `fingerprint_of` | 1050 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `mutation_of` | 1058 | Y | C1-lifecycle |
| kaola-dispatch.py | `holder_of` | 1066 | Y | core-identity |
| kaola-dispatch.py | `repo_of` | 1071 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `session_absent` | 1087 | Y | C1-lifecycle |
| kaola-dispatch.py | `parse_stdout` | 1096 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `run_runner` | 1114 | Y | C5-dispatch |
| kaola-dispatch.py | `evidence` | 1129 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `receipt_unreadable` | 1148 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `runner_refused` | 1156 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `atomic_write` | 1166 | Y | core-atomic |
| kaola-dispatch.py | `prompt_sha` | 1180 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `same_repo` | 1184 | Y | core-identity |
| kaola-dispatch.py | `string_list` | 1193 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `blank_item` | 1203 | Y | C5-dispatch |
| kaola-dispatch.py | `requirement_problem` | 1218 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `caller_dispatcher` | 1242 | Y | core-identity |
| kaola-dispatch.py | `dispatch_links` | 1256 | Y | C5-dispatch |
| kaola-dispatch.py | `bound_sideagent` | 1277 | Y | C4-state |
| kaola-dispatch.py | `binding_row` | 1289 | Y | C4-state |
| kaola-dispatch.py | `delegator_ceiling` | 1299 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `_parse_elite_grants` | 1383 | Y | C5-dispatch |
| kaola-dispatch.py | `_parse_elite_grants.problem` | 1394 | n | C5-dispatch |
| kaola-dispatch.py | `_parse_elite_grants.literal` | 1399 | n | C5-dispatch |
| kaola-dispatch.py | `ceiling_group` | 1459 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `ceiling_block` | 1468 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `ceiling_count` | 1485 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `tighten_count` | 1493 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `apply_ceiling_to_grants` | 1508 | Y | C4-state |
| kaola-dispatch.py | `command_execute` | 1553 | Y | C5-dispatch |
| kaola-dispatch.py | `command_execute.refuse_all` | 1603 | n | C5-dispatch |
| kaola-dispatch.py | `command_execute.publish` | 2007 | n | C5-dispatch |
| kaola-dispatch.py | `assemble_prompts` | 2073 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `preset_holds` | 2101 | Y | C4-state |
| kaola-dispatch.py | `state_task_ids` | 2119 | Y | C4-state |
| kaola-dispatch.py | `link_dispatch_to_tasks` | 2127 | Y | C4-state |
| kaola-dispatch.py | `resource_conflict` | 2165 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `conflict_ids` | 2184 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `conflict_ids.find` | 2187 | n | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `acp_runner` | 2207 | Y | C5-dispatch |
| kaola-dispatch.py | `live_facts` | 2219 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `assignment_identity` | 2240 | Y | core-identity |
| kaola-dispatch.py | `exact_prior` | 2260 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `preserve_correlation` | 2270 | Y | C1-lifecycle |
| kaola-dispatch.py | `preset_from_applied` | 2290 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `preset_from_bound_index` | 2329 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `resolve_live_presets` | 2352 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `shared_seat_unknown` | 2400 | Y | C1-lifecycle |
| kaola-dispatch.py | `live_occupancy` | 2411 | Y | C5-dispatch |
| kaola-dispatch.py | `held_seat` | 2457 | Y | C1-lifecycle |
| kaola-dispatch.py | `held_refusal` | 2486 | Y | core-registry |
| kaola-dispatch.py | `launch_argv` | 2505 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `launch_plan` | 2528 | Y | C5-dispatch |
| kaola-dispatch.py | `remember_holder` | 2542 | Y | C4-state |
| kaola-dispatch.py | `execute_one` | 2551 | Y | C5-dispatch |
| kaola-dispatch.py | `execute_one.finish` | 2569 | n | C5-dispatch |
| kaola-dispatch.py | `assignment_bound` | 2628 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `note_persisted_role` | 2654 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `recover_or_send` | 2677 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `send_item` | 2742 | Y | C5-dispatch |
| kaola-dispatch.py | `coverage` | 2777 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `IndexLock.__init__` | 2789 | n | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `IndexLock.__enter__` | 2793 | n | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `IndexLock.__exit__` | 2814 | n | C1-lifecycle |
| kaola-dispatch.py | `pending_correlation` | 2824 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `merge_index_rows` | 2846 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `merge_index_rows.rows` | 2859 | n | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `finish_index` | 2888 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `result_excerpt` | 2920 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `result_text` | 2925 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `output_kind` | 2965 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `output_facts` | 2990 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `turn_facts` | 3010 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `completed_turn` | 3030 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `collect_one` | 3039 | Y | C5-dispatch |
| kaola-dispatch.py | `command_collect` | 3138 | Y | C5-dispatch |
| kaola-dispatch.py | `command_collect.rows` | 3160 | n | C5-dispatch |
| kaola-dispatch.py | `command_collect.publish` | 3164 | n | C5-dispatch |
| kaola-dispatch.py | `read_turn` | 3189 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `read_turn.compact` | 3207 | n | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `read_turn.finish` | 3230 | n | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `read_turn.finish.text` | 3276 | n | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `read_turn.bound` | 3311 | n | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `command_snapshot` | 3433 | Y | C4-state |
| kaola-dispatch.py | `StateRefusal.__init__` | 3481 | n | core-registry |
| kaola-dispatch.py | `json_arg` | 3486 | Y | C1-lifecycle |
| kaola-dispatch.py | `merge_patch` | 3494 | Y | C4-state |
| kaola-dispatch.py | `empty_state` | 3507 | Y | C4-state |
| kaola-dispatch.py | `repo_of_state_file` | 3516 | Y | core-identity |
| kaola-dispatch.py | `read_state_file` | 3521 | Y | core-atomic |
| kaola-dispatch.py | `require_current` | 3539 | Y | core-atomic |
| kaola-dispatch.py | `StateLock.__init__` | 3561 | n | core-atomic |
| kaola-dispatch.py | `StateLock.__enter__` | 3565 | n | core-atomic |
| kaola-dispatch.py | `StateLock.__exit__` | 3571 | n | core-atomic |
| kaola-dispatch.py | `short` | 3577 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `host_view` | 3585 | Y | C4-state |
| kaola-dispatch.py | `judgment_digest` | 3632 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `_positive_int` | 3640 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `_dispatch_ids` | 3646 | Y | C5-dispatch |
| kaola-dispatch.py | `_owner_of` | 3657 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `_submission_dispatch` | 3675 | Y | C1-lifecycle |
| kaola-dispatch.py | `_submission_receipt` | 3686 | Y | C1-lifecycle |
| kaola-dispatch.py | `_stored_rejection` | 3699 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `_granted_ids` | 3704 | Y | C5-dispatch |
| kaola-dispatch.py | `_owner_grant` | 3721 | Y | C5-dispatch |
| kaola-dispatch.py | `_profile_effort` | 3738 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `_platform_coverage` | 3746 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `_effort_permitted` | 3759 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `_applied_effort` | 3785 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `_task_holders` | 3800 | Y | C4-state |
| kaola-dispatch.py | `_plain` | 3818 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `_holder_agrees` | 3824 | Y | C4-state |
| kaola-dispatch.py | `_task_dispatch_rows` | 3830 | Y | C4-state |
| kaola-dispatch.py | `_row_matches` | 3851 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `_receipt_binds` | 3867 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `_declared_effort_order` | 3904 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `_index_items` | 3926 | Y | C5-dispatch |
| kaola-dispatch.py | `_row_is_owner` | 3942 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `_row_taken_over` | 3946 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `_handoff_resets` | 3958 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `_effort_action` | 4001 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `_incoming_binding` | 4039 | Y | C4-state |
| kaola-dispatch.py | `_submission_relation` | 4091 | Y | C1-lifecycle |
| kaola-dispatch.py | `_keep_prior_repair` | 4118 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `apply_task_rejection` | 4126 | Y | C4-state |
| kaola-dispatch.py | `maintenance_brief` | 4235 | Y | C1-lifecycle |
| kaola-dispatch.py | `requirement_scope` | 4247 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `requirement_lines` | 4256 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `delegator_view` | 4299 | Y | C4-state |
| kaola-dispatch.py | `delegator_view.brief` | 4305 | n | C4-state |
| kaola-dispatch.py | `delegator_view.rows` | 4317 | n | C4-state |
| kaola-dispatch.py | `render_state` | 4349 | Y | C4-state |
| kaola-dispatch.py | `runner_record_root` | 4396 | Y | core-identity |
| kaola-dispatch.py | `carrier_replaced_by_older` | 4402 | Y | C1-lifecycle |
| kaola-dispatch.py | `check_writer` | 4426 | Y | C4-state |
| kaola-dispatch.py | `node_binding` | 4466 | Y | C4-state |
| kaola-dispatch.py | `writer_trace` | 4471 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `caller_role` | 4481 | Y | core-identity |
| kaola-dispatch.py | `validate_record` | 4498 | Y | core-registry |
| kaola-dispatch.py | `record_recovery` | 4527 | Y | C4-state |
| kaola-dispatch.py | `apply_record_update` | 4548 | Y | core-registry |
| kaola-dispatch.py | `stamp_writer` | 4721 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `apply_section_update` | 4734 | Y | C1-lifecycle |
| kaola-dispatch.py | `note_section_source` | 4814 | Y | C1-lifecycle |
| kaola-dispatch.py | `session_name` | 4823 | Y | C1-lifecycle |
| kaola-dispatch.py | `seat_entries` | 4828 | Y | C1-lifecycle |
| kaola-dispatch.py | `task_seats` | 4848 | Y | C1-lifecycle |
| kaola-dispatch.py | `open_seats` | 4859 | Y | C1-lifecycle |
| kaola-dispatch.py | `open_dispatch` | 4886 | Y | C4-state |
| kaola-dispatch.py | `handoff_seats` | 4955 | Y | C1-lifecycle |
| kaola-dispatch.py | `retire_record` | 4990 | Y | core-registry |
| kaola-dispatch.py | `write_state` | 5096 | Y | core-atomic |
| kaola-dispatch.py | `state_mutation` | 5104 | Y | C4-state |
| kaola-dispatch.py | `mirror_dispositions` | 5152 | Y | C4-state |
| kaola-dispatch.py | `mirror_task` | 5169 | Y | C4-state |
| kaola-dispatch.py | `command_state_init` | 5205 | Y | C4-state |
| kaola-dispatch.py | `command_state_update` | 5242 | Y | C4-state |
| kaola-dispatch.py | `command_state_retire` | 5259 | Y | C4-state |
| kaola-dispatch.py | `_owner_stop` | 5263 | Y | C1-lifecycle |
| kaola-dispatch.py | `cite_retrievable` | 5274 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `revision_of` | 5303 | Y | C1-lifecycle |
| kaola-dispatch.py | `retirement_stones` | 5308 | Y | C4-state |
| kaola-dispatch.py | `already_settled_input` | 5313 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `caller_record` | 5332 | Y | core-identity |
| kaola-dispatch.py | `original_events` | 5344 | Y | C3-events |
| kaola-dispatch.py | `command_state_recovery_input` | 5359 | Y | C4-state |
| kaola-dispatch.py | `recovery_batch` | 5433 | Y | C4-state |
| kaola-dispatch.py | `checkpoint_entry` | 5449 | Y | C4-state |
| kaola-dispatch.py | `apply_checkpoint` | 5511 | Y | C4-state |
| kaola-dispatch.py | `command_state_checkpoint` | 5628 | Y | C4-state |
| kaola-dispatch.py | `command_state_view` | 5632 | Y | C4-state |
| kaola-dispatch.py | `live_rows_of` | 5658 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `live_host_rows` | 5667 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `carrier_from_live` | 5673 | Y | C1-lifecycle |
| kaola-dispatch.py | `state_problems` | 5687 | Y | C4-state |
| kaola-dispatch.py | `state_problems.note` | 5692 | n | C4-state |
| kaola-dispatch.py | `command_state_check` | 5781 | Y | C4-state |
| kaola-dispatch.py | `command_state_timer` | 5798 | Y | C4-state |
| kaola-dispatch.py | `unmapped_fields` | 5827 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `legacy_tasks` | 5833 | Y | C4-state |
| kaola-dispatch.py | `migrate_document` | 5895 | Y | C4-state |
| kaola-dispatch.py | `command_state_migrate` | 6013 | Y | C4-state |
| kaola-dispatch.py | `build_parser` | 6099 | Y | keep-in-place (P1 adopted keep-in-place: argparse wiring spanning C4/C5 command groups; splitting adds a CLI contract without removing coupling) |
| kaola-dispatch.py | `build_parser.writer_args` | 6141 | n | keep-in-place (P1 adopted keep-in-place: shared writer-args plumbing nested in build_parser; moves with its parent) |
| kaola-dispatch.py | `command_state_backups` | 6261 | Y | core-atomic |
| kaola-dispatch.py | `_delegator_read` | 6270 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `command_delegator_view` | 6277 | Y | C4-state |
| kaola-dispatch.py | `delegator_recovery` | 6295 | Y | C4-state |
| kaola-dispatch.py | `command_delegator_migrate` | 6321 | Y | C4-state |
| kaola-dispatch.py | `command_delegator_update` | 6342 | Y | keep-in-place:kaola-dispatch.py (source review pending P1 walk) |
| kaola-dispatch.py | `main` | 6401 | Y | keep-in-place (P1 adopted keep-in-place: argv->command entrypoint for the whole dispatch tool; not a component surface) |
| kaola-acp-holder.py | `canonical` | 57 | Y | core-identity |
| kaola-acp-holder.py | `normalize_id` | 61 | Y | core-identity |
| kaola-acp-holder.py | `worker_event_id` | 65 | Y | core-identity |
| kaola-acp-holder.py | `process_alive` | 76 | Y | core-process |
| kaola-acp-holder.py | `libproc_ps` | 103 | Y | core-process |
| kaola-acp-holder.py | `run_ps` | 132 | Y | core-process |
| kaola-acp-holder.py | `process_table` | 146 | Y | core-process |
| kaola-acp-holder.py | `child_groups` | 163 | Y | core-process |
| kaola-acp-holder.py | `parse_dispatcher` | 279 | Y | C1-lifecycle |
| kaola-acp-holder.py | `parse_heartbeat_host` | 293 | Y | C1-lifecycle |
| kaola-acp-holder.py | `heartbeat_prompt_body` | 317 | Y | C1-lifecycle |
| kaola-acp-holder.py | `attention_fingerprint` | 323 | Y | C1-lifecycle |
| kaola-acp-holder.py | `read_heartbeat_file` | 336 | Y | C1-lifecycle |
| kaola-acp-holder.py | `spawn_time_matches` | 417 | Y | core-process |
| kaola-acp-holder.py | `start_epoch` | 424 | Y | core-process |
| kaola-acp-holder.py | `live_spawn_entries` | 432 | Y | core-process |
| kaola-acp-holder.py | `spawn_recorded_groups` | 467 | Y | core-process |
| kaola-acp-holder.py | `compact_spawn_record` | 477 | Y | core-process |
| kaola-acp-holder.py | `own_holder_record` | 495 | Y | core-process |
| kaola-acp-holder.py | `worker_tree_groups` | 517 | Y | core-process |
| kaola-acp-holder.py | `is_turn_end` | 544 | Y | C3-events |
| kaola-acp-holder.py | `holders_dispatched_by` | 550 | Y | C4-state |
| kaola-acp-holder.py | `dispatched_worker_groups` | 584 | Y | core-process |
| kaola-acp-holder.py | `live_child_groups` | 604 | Y | core-process |
| kaola-acp-holder.py | `group_members` | 617 | Y | core-process |
| kaola-acp-holder.py | `scrub` | 629 | Y | core-process |
| kaola-acp-holder.py | `config_option_choices` | 643 | Y | C1-lifecycle |
| kaola-acp-holder.py | `config_option_values` | 670 | Y | C1-lifecycle |
| kaola-acp-holder.py | `capability_supported` | 675 | Y | C2-acp-adapters |
| kaola-acp-holder.py | `rfc3339_instant` | 682 | Y | keep-in-place:holder (event-loop interior; P1 step-1 C1/C3 boundary walk) |
| kaola-acp-holder.py | `latest_session` | 702 | Y | C2-acp-adapters |
| kaola-acp-holder.py | `EventLog.__init__` | 740 | n | keep-in-place:holder (event-loop interior; P1 step-1 C1/C3 boundary walk) |
| kaola-acp-holder.py | `EventLog._rotated_paths` | 747 | n | keep-in-place:holder (event-loop interior; P1 step-1 C1/C3 boundary walk) |
| kaola-acp-holder.py | `EventLog._iter_entries` | 757 | n | keep-in-place:holder (event-loop interior; P1 step-1 C1/C3 boundary walk) |
| kaola-acp-holder.py | `EventLog._restore_cursor` | 771 | n | C2-acp-adapters |
| kaola-acp-holder.py | `EventLog.oldest_cursor` | 785 | n | C2-acp-adapters |
| kaola-acp-holder.py | `EventLog.append` | 789 | n | keep-in-place:holder (event-loop interior; P1 step-1 C1/C3 boundary walk) |
| kaola-acp-holder.py | `EventLog._rotate` | 807 | n | keep-in-place:holder (event-loop interior; P1 step-1 C1/C3 boundary walk) |
| kaola-acp-holder.py | `EventLog.read_since` | 823 | n | C3-events |
| kaola-acp-holder.py | `StderrPump.__init__` | 836 | n | keep-in-place:holder (event-loop interior; P1 step-1 C1/C3 boundary walk) |
| kaola-acp-holder.py | `StderrPump.start` | 843 | n | C1-lifecycle |
| kaola-acp-holder.py | `StderrPump._run` | 846 | n | keep-in-place:holder (event-loop interior; P1 step-1 C1/C3 boundary walk) |
| kaola-acp-holder.py | `StderrPump.tail` | 864 | n | keep-in-place:holder (event-loop interior; P1 step-1 C1/C3 boundary walk) |
| kaola-acp-holder.py | `seatbelt_confined` | 870 | Y | core-process |
| kaola-acp-holder.py | `AgentConnection.__init__` | 891 | n | keep-in-place:holder (event-loop interior; P1 step-1 C1/C3 boundary walk) |
| kaola-acp-holder.py | `AgentConnection.spawn` | 911 | n | keep-in-place:holder (event-loop interior; P1 step-1 C1/C3 boundary walk) |
| kaola-acp-holder.py | `AgentConnection._wait_loop` | 946 | n | C1-lifecycle |
| kaola-acp-holder.py | `AgentConnection._read_loop` | 953 | n | C1-lifecycle |
| kaola-acp-holder.py | `AgentConnection.send_message` | 988 | n | keep-in-place:holder (event-loop interior; P1 step-1 C1/C3 boundary walk) |
| kaola-acp-holder.py | `AgentConnection.send_request` | 998 | n | keep-in-place:holder (event-loop interior; P1 step-1 C1/C3 boundary walk) |
| kaola-acp-holder.py | `AgentConnection.wait_response` | 1020 | n | keep-in-place:holder (event-loop interior; P1 step-1 C1/C3 boundary walk) |
| kaola-acp-holder.py | `AgentConnection.resolve_response` | 1031 | n | keep-in-place:holder (event-loop interior; P1 step-1 C1/C3 boundary walk) |
| kaola-acp-holder.py | `AgentConnection.cancel_outbound` | 1041 | n | keep-in-place:holder (event-loop interior; P1 step-1 C1/C3 boundary walk) |
| kaola-acp-holder.py | `quota_module` | 1077 | Y | C2-acp-adapters |
| kaola-acp-holder.py | `compact_module` | 1109 | Y | C6-recovery-helper |
| kaola-acp-holder.py | `_hex_revision` | 1170 | Y | keep-in-place:holder (event-loop interior; P1 step-1 C1/C3 boundary walk) |
| kaola-acp-holder.py | `_snapshot_file` | 1176 | Y | C4-state |
| kaola-acp-holder.py | `capture_script_paths` | 1184 | Y | C3-events |
| kaola-acp-holder.py | `_import_sibling` | 1206 | Y | keep-in-place (P1 adopted keep-in-place: generic sibling-module importer used by holder bootstrap; no domain owner) |
| kaola-acp-holder.py | `load_sibling_modules` | 1227 | Y | keep-in-place (P1 adopted keep-in-place: holder bootstrap wiring quota/record/compact siblings + byte snapshot; loader plumbing, not core identity/process) |
| kaola-acp-holder.py | `runner_identity` | 1253 | Y | core-identity |
| kaola-acp-holder.py | `_as_text` | 1273 | Y | keep-in-place:holder (event-loop interior; P1 step-1 C1/C3 boundary walk) |
| kaola-acp-holder.py | `_normalize_content_items` | 1283 | Y | C3-events |
| kaola-acp-holder.py | `_cap_content_items` | 1308 | Y | C3-events |
| kaola-acp-holder.py | `_normalize_locations` | 1332 | Y | C3-events |
| kaola-acp-holder.py | `permission_options_view` | 1347 | Y | C1-lifecycle |
| kaola-acp-holder.py | `answered_permission_view` | 1354 | Y | C1-lifecycle |
| kaola-acp-holder.py | `ViewProjection.__init__` | 1389 | n | C4-state |
| kaola-acp-holder.py | `ViewProjection.add_user_from_prompt` | 1411 | n | C4-state |
| kaola-acp-holder.py | `ViewProjection.end_turn` | 1429 | n | C4-state |
| kaola-acp-holder.py | `ViewProjection.add_answered_permission` | 1440 | n | C4-state |
| kaola-acp-holder.py | `ViewProjection.close_message` | 1447 | n | C4-state |
| kaola-acp-holder.py | `ViewProjection.apply` | 1451 | n | C4-state |
| kaola-acp-holder.py | `ViewProjection._add_message_locked` | 1532 | n | C4-state |
| kaola-acp-holder.py | `ViewProjection._upsert_tool_locked` | 1565 | n | C4-state |
| kaola-acp-holder.py | `ViewProjection.snapshot` | 1594 | n | C4-state |
| kaola-acp-holder.py | `follow_error_event` | 1614 | Y | C3-events |
| kaola-acp-holder.py | `Follower.__init__` | 1621 | n | C3-events |
| kaola-acp-holder.py | `Follower.start` | 1632 | n | C1-lifecycle |
| kaola-acp-holder.py | `Follower.offer_snapshot` | 1635 | n | C3-events |
| kaola-acp-holder.py | `Follower.offer_delta` | 1644 | n | C3-events |
| kaola-acp-holder.py | `Follower.offer_heartbeat` | 1656 | n | C3-events |
| kaola-acp-holder.py | `Follower.offer_eof` | 1660 | n | C3-events |
| kaola-acp-holder.py | `Follower.offer_error` | 1664 | n | C3-events |
| kaola-acp-holder.py | `Follower._offer_locked` | 1668 | n | C3-events |
| kaola-acp-holder.py | `Follower._drop_locked` | 1678 | n | C3-events |
| kaola-acp-holder.py | `Follower._write_loop` | 1690 | n | C1-lifecycle |
| kaola-acp-holder.py | `Follower._emit_drop` | 1722 | n | C3-events |
| kaola-acp-holder.py | `Follower._send` | 1742 | n | C3-events |
| kaola-acp-holder.py | `Follower.close` | 1760 | n | C3-events |
| kaola-acp-holder.py | `parse_init_meta` | 1773 | Y | C2-acp-adapters |
| kaola-acp-holder.py | `normalize_session_role` | 1793 | Y | core-identity |
| kaola-acp-holder.py | `Holder.__init__` | 1808 | n | C4-state |
| kaola-acp-holder.py | `Holder._empty_turn` | 1962 | n | C4-state |
| kaola-acp-holder.py | `Holder.dispatcher_identity` | 1986 | n | core-identity |
| kaola-acp-holder.py | `Holder.write_record` | 1995 | n | core-registry |
| kaola-acp-holder.py | `Holder._apply_config_options` | 2053 | n | C2-acp-adapters |
| kaola-acp-holder.py | `Holder.initialize_agent` | 2069 | n | C4-state |
| kaola-acp-holder.py | `Holder._list_repo_sessions` | 2181 | n | C4-state |
| kaola-acp-holder.py | `Holder.initialize_agent_resume` | 2206 | n | core-identity |
| kaola-acp-holder.py | `Holder.on_agent_message` | 2228 | n | C1-lifecycle |
| kaola-acp-holder.py | `Holder.note_agent_message_error` | 2238 | n | C4-state |
| kaola-acp-holder.py | `Holder.on_agent_notification` | 2265 | n | C1-lifecycle |
| kaola-acp-holder.py | `Holder.on_agent_request` | 2289 | n | C1-lifecycle |
| kaola-acp-holder.py | `Holder.on_session_update` | 2331 | n | C1-lifecycle |
| kaola-acp-holder.py | `Holder.on_prompt_response` | 2392 | n | C1-lifecycle |
| kaola-acp-holder.py | `Holder.on_agent_exit` | 2461 | n | C1-lifecycle |
| kaola-acp-holder.py | `Holder.op_state` | 2516 | n | C4-state |
| kaola-acp-holder.py | `Holder.turn_receipt` | 2570 | n | C4-state |
| kaola-acp-holder.py | `Holder._no_acp_session` | 2631 | n | core-identity |
| kaola-acp-holder.py | `Holder.op_prompt` | 2650 | n | C4-state |
| kaola-acp-holder.py | `Holder._await_prompt` | 2786 | n | C4-state |
| kaola-acp-holder.py | `Holder._notify_heartbeat_host_now` | 2792 | n | C4-state |
| kaola-acp-holder.py | `Holder._carrier_send` | 2824 | n | C1-lifecycle |
| kaola-acp-holder.py | `Holder._carrier_error_code` | 2899 | n | C1-lifecycle |
| kaola-acp-holder.py | `Holder._retain_undelivered_wake` | 2904 | n | C4-state |
| kaola-acp-holder.py | `Holder._wake_stale_reason` | 2928 | n | C4-state |
| kaola-acp-holder.py | `Holder._wake_still_owed` | 2947 | n | C4-state |
| kaola-acp-holder.py | `Holder._undelivered_wake_facts` | 2954 | n | C4-state |
| kaola-acp-holder.py | `Holder._flush_undelivered_wakes` | 2964 | n | C4-state |
| kaola-acp-holder.py | `Holder._record_overflow_full_check` | 3055 | n | core-registry |
| kaola-acp-holder.py | `Holder._heartbeat_payload` | 3069 | n | C4-state |
| kaola-acp-holder.py | `Holder._established_non_host` | 3155 | n | C1-lifecycle |
| kaola-acp-holder.py | `Holder._sideagent_relay_target` | 3162 | n | C4-state |
| kaola-acp-holder.py | `Holder._relay_prompt` | 3200 | n | C4-state |
| kaola-acp-holder.py | `Holder._relay_send` | 3217 | n | C4-state |
| kaola-acp-holder.py | `Holder._relay_send.remaining` | 3220 | n | C1-lifecycle |
| kaola-acp-holder.py | `Holder._confirm_events` | 3250 | n | C3-events |
| kaola-acp-holder.py | `Holder._settle_relays` | 3261 | n | C4-state |
| kaola-acp-holder.py | `Holder._settle_relays.turn_of` | 3281 | n | C4-state |
| kaola-acp-holder.py | `Holder._settle_relays.end_missing` | 3285 | n | C4-state |
| kaola-acp-holder.py | `Holder._relay_pass` | 3306 | n | C4-state |
| kaola-acp-holder.py | `Holder._lifecycle_state` | 3392 | n | C4-state |
| kaola-acp-holder.py | `Holder._node_binding` | 3398 | n | C4-state |
| kaola-acp-holder.py | `Holder._node_host_pending` | 3437 | n | C4-state |
| kaola-acp-holder.py | `Holder._node_recovery_pending` | 3461 | n | C4-state |
| kaola-acp-holder.py | `Holder._maintenance_tool` | 3476 | n | C1-lifecycle |
| kaola-acp-holder.py | `Holder._register_compact_maintenance` | 3499 | n | C1-lifecycle |
| kaola-acp-holder.py | `Holder._register_compact_maintenance.register` | 3506 | n | C1-lifecycle |
| kaola-acp-holder.py | `Holder._maintenance_failure` | 3528 | n | C1-lifecycle |
| kaola-acp-holder.py | `Holder._maintenance_failure.record_failure` | 3547 | n | C1-lifecycle |
| kaola-acp-holder.py | `Holder._node_relay_pass` | 3557 | n | C4-state |
| kaola-acp-holder.py | `Holder._unhandled` | 3683 | n | C4-state |
| kaola-acp-holder.py | `Holder._node_to_host` | 3691 | n | C4-state |
| kaola-acp-holder.py | `Holder._node_prompt` | 3706 | n | C4-state |
| kaola-acp-holder.py | `Holder._state_tool` | 3758 | n | C4-state |
| kaola-acp-holder.py | `Holder._settle_node_batch` | 3771 | n | C4-state |
| kaola-acp-holder.py | `Holder._node_wrote_attention` | 3834 | n | C4-state |
| kaola-acp-holder.py | `Holder._node_record` | 3850 | n | core-registry |
| kaola-acp-holder.py | `Holder._node_holder_alive` | 3858 | n | C4-state |
| kaola-acp-holder.py | `Holder._start_node` | 3865 | n | C1-lifecycle |
| kaola-acp-holder.py | `Holder._stop_node` | 3907 | n | C1-lifecycle |
| kaola-acp-holder.py | `Holder._reclaim_node` | 3958 | n | C4-state |
| kaola-acp-holder.py | `Holder.op_compact_notice` | 3981 | n | C4-state |
| kaola-acp-holder.py | `Holder.op_compact_notice.refuse` | 3988 | n | C4-state |
| kaola-acp-holder.py | `Holder._attempt_compact_notice` | 4053 | n | C4-state |
| kaola-acp-holder.py | `Holder._observe_compact_signal` | 4097 | n | core-process |
| kaola-acp-holder.py | `Holder._deliver_compact_reload` | 4141 | n | C4-state |
| kaola-acp-holder.py | `Holder._attempt_compact_reload` | 4190 | n | C4-state |
| kaola-acp-holder.py | `Holder._kick_worker_events` | 4232 | n | C3-events |
| kaola-acp-holder.py | `Holder._deliver_worker_events` | 4247 | n | C3-events |
| kaola-acp-holder.py | `Holder._remember_confirmed_worker_events` | 4310 | n | C3-events |
| kaola-acp-holder.py | `Holder._was_worker_event_confirmed` | 4323 | n | C4-state |
| kaola-acp-holder.py | `Holder._worker_event_turn_end` | 4357 | n | C4-state |
| kaola-acp-holder.py | `Holder.op_worker_event` | 4411 | n | C4-state |
| kaola-acp-holder.py | `Holder._overflow_generation_of` | 4501 | n | C1-lifecycle |
| kaola-acp-holder.py | `Holder._restore_worker_events` | 4507 | n | C3-events |
| kaola-acp-holder.py | `Holder.op_wait` | 4594 | n | C4-state |
| kaola-acp-holder.py | `Holder._settle_pending_permission_locked` | 4605 | n | C1-lifecycle |
| kaola-acp-holder.py | `Holder._cancel_pending_permissions` | 4629 | n | C4-state |
| kaola-acp-holder.py | `Holder._holder_instance_mismatch` | 4635 | n | C4-state |
| kaola-acp-holder.py | `Holder.op_permit` | 4651 | n | C4-state |
| kaola-acp-holder.py | `Holder.op_steer` | 4679 | n | C2-acp-adapters |
| kaola-acp-holder.py | `Holder.op_steer.after_turn` | 4742 | n | C2-acp-adapters |
| kaola-acp-holder.py | `Holder.op_steer.await_reply` | 4816 | n | C2-acp-adapters |
| kaola-acp-holder.py | `Holder.op_steer_interrupt` | 4966 | n | C2-acp-adapters |
| kaola-acp-holder.py | `Holder.cancel_turn` | 5184 | n | C4-state |
| kaola-acp-holder.py | `Holder._turn_snapshot_locked` | 5241 | n | C4-state |
| kaola-acp-holder.py | `Holder.op_cancel` | 5252 | n | C4-state |
| kaola-acp-holder.py | `Holder.op_view` | 5278 | n | C4-state |
| kaola-acp-holder.py | `Holder._view_model` | 5352 | n | C4-state |
| kaola-acp-holder.py | `Holder._option_current` | 5382 | n | C1-lifecycle |
| kaola-acp-holder.py | `Holder._current_model` | 5399 | n | C4-state |
| kaola-acp-holder.py | `Holder._quota_models` | 5422 | n | C4-state |
| kaola-acp-holder.py | `Holder._fit_view` | 5434 | n | C4-state |
| kaola-acp-holder.py | `Holder.fanout_follow_delta` | 5451 | n | C3-events |
| kaola-acp-holder.py | `Holder.fanout_follow_heartbeat` | 5459 | n | C3-events |
| kaola-acp-holder.py | `Holder.fanout_follow_eof` | 5467 | n | C3-events |
| kaola-acp-holder.py | `Holder.unregister_follower` | 5473 | n | C3-events |
| kaola-acp-holder.py | `Holder.start_follow` | 5477 | n | C1-lifecycle |
| kaola-acp-holder.py | `Holder.follow_heartbeat_loop` | 5499 | n | C1-lifecycle |
| kaola-acp-holder.py | `Holder.op_capture` | 5507 | n | C3-events |
| kaola-acp-holder.py | `Holder.op_stop` | 5532 | n | C1-lifecycle |
| kaola-acp-holder.py | `Holder.note_agent_children` | 5599 | n | C4-state |
| kaola-acp-holder.py | `Holder._terminate_group` | 5627 | n | core-process |
| kaola-acp-holder.py | `Holder.op_set_config_option` | 5694 | n | C2-acp-adapters |
| kaola-acp-holder.py | `Holder.op_record_start_evidence` | 5733 | n | core-registry |
| kaola-acp-holder.py | `Holder.op_rebind_heartbeat_host` | 5762 | n | C1-lifecycle |
| kaola-acp-holder.py | `Holder.handle_request` | 5801 | n | C1-lifecycle |
| kaola-acp-holder.py | `Holder.serve_connection` | 5836 | n | C1-lifecycle |
| kaola-acp-holder.py | `Holder.verify_peer` | 5900 | n | C4-state |
| kaola-acp-holder.py | `Holder.idle_watcher` | 5918 | n | C4-state |
| kaola-acp-holder.py | `Holder.start_failure_facts` | 5947 | n | C1-lifecycle |
| kaola-acp-holder.py | `Holder.run` | 5974 | n | C4-state |
| kaola-acp-holder.py | `run_probe` | 6024 | Y | C1-lifecycle |
| kaola-acp-holder.py | `run_probe.send` | 6043 | n | C1-lifecycle |
| kaola-acp-holder.py | `run_probe.wait` | 6060 | n | C1-lifecycle |
| kaola-acp-holder.py | `run_probe.reader` | 6065 | n | C1-lifecycle |
| kaola-acp-holder.py | `main` | 6195 | Y | C1-lifecycle |
| kaola-acp.py | `dsh_permission_mode` | 86 | Y | C1-lifecycle |
| kaola-acp.py | `host_capable` | 198 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `host_entry_unsupported` | 202 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `record_holder_child_spawn` | 211 | Y | C4-state |
| kaola-acp.py | `zcode_path_state` | 238 | Y | C2-acp-adapters |
| kaola-acp.py | `zcode_runtime_error` | 251 | Y | C2-acp-adapters |
| kaola-acp.py | `resolve_agent_command` | 275 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `manifest_launch_command` | 307 | Y | C2-acp-adapters |
| kaola-acp.py | `runtime_binary` | 321 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `loopback_no_proxy` | 338 | Y | C1-lifecycle |
| kaola-acp.py | `codex_manifest_launch` | 366 | Y | C2-acp-adapters |
| kaola-acp.py | `absolute_codex_path` | 381 | Y | C2-acp-adapters |
| kaola-acp.py | `codex_child_path` | 387 | Y | C2-acp-adapters |
| kaola-acp.py | `codex_child_error` | 401 | Y | C2-acp-adapters |
| kaola-acp.py | `codex_child_refusal` | 432 | Y | core-registry |
| kaola-acp.py | `codex_package_at` | 445 | Y | C2-acp-adapters |
| kaola-acp.py | `codex_binary_from_table` | 474 | Y | C2-acp-adapters |
| kaola-acp.py | `codex_child_from_process` | 507 | Y | core-process |
| kaola-acp.py | `codex_version_fact` | 530 | Y | C1-lifecycle |
| kaola-acp.py | `agent_environment` | 557 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `opencode_launch_policy` | 584 | Y | C2-acp-adapters |
| kaola-acp.py | `bridge_facts` | 634 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `bridge_runtime_error` | 662 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `binary_version` | 684 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `cli_version_fact` | 695 | Y | C1-lifecycle |
| kaola-acp.py | `session_new_timeout` | 712 | Y | C1-lifecycle |
| kaola-acp.py | `session_new_extra` | 722 | Y | C1-lifecycle |
| kaola-acp.py | `InputError.__init__` | 728 | n | keep-in-place (P1 adopted keep-in-place: typed CLI input-error construction shared by all acp commands; CLI surface, not minimal core) |
| kaola-acp.py | `InputError.__str__` | 733 | n | keep-in-place (P1 adopted keep-in-place: input-error formatting shared by all acp commands) |
| kaola-acp.py | `ReceiptArgumentParser.error` | 738 | n | keep-in-place (P1 adopted keep-in-place: argparse error->receipt adapter shared by all acp subcommands) |
| kaola-acp.py | `input_error_receipt` | 744 | Y | keep-in-place (P1 adopted keep-in-place: pre-transport input-failure receipt shared by all acp commands) |
| kaola-acp.py | `die` | 754 | Y | keep-in-place (P1 adopted keep-in-place: fatal stderr exit helper shared by all acp commands) |
| kaola-acp.py | `canonical_dir` | 759 | Y | core-identity |
| kaola-acp.py | `load_manifest` | 763 | Y | C2-acp-adapters |
| kaola-acp.py | `resolve_repo` | 788 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `record_root` | 804 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `record_dir` | 814 | Y | core-identity |
| kaola-acp.py | `spawn_record_dir` | 819 | Y | core-identity |
| kaola-acp.py | `sock_path_for_directory` | 828 | Y | core-identity |
| kaola-acp.py | `sock_path` | 834 | Y | core-identity |
| kaola-acp.py | `probe_socket_ok` | 846 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `parse_list_args` | 860 | Y | keep-in-place (P1 adopted keep-in-place: argparse plumbing for the list command; list semantics stay in command_list (C1)) |
| kaola-acp.py | `command_list` | 871 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `parse_survey_args` | 1001 | Y | keep-in-place (P1 adopted keep-in-place: argparse plumbing for survey; survey semantics stay in command_survey (C2)) |
| kaola-acp.py | `survey_login_shell` | 1008 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `survey_login_env` | 1023 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `survey_resolve` | 1075 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `survey_zcode_row` | 1087 | Y | C2-acp-adapters |
| kaola-acp.py | `command_survey` | 1108 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `quota_module` | 1159 | Y | C2-acp-adapters |
| kaola-acp.py | `parse_packages_args` | 1180 | Y | keep-in-place (P1 adopted keep-in-place: argparse plumbing for packages; catalog semantics stay in command_packages (C2)) |
| kaola-acp.py | `parse_model_package_args` | 1188 | Y | keep-in-place (P1 adopted keep-in-place: argparse plumbing for model-package; semantics stay in command_model_package (C2)) |
| kaola-acp.py | `command_packages` | 1195 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `stamp_quota_emission` | 1222 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `command_model_package` | 1234 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `view_error` | 1250 | Y | C4-state |
| kaola-acp.py | `event_stream_bytes` | 1272 | Y | C3-events |
| kaola-acp.py | `line_size` | 1279 | Y | C3-events (P1 resolved C3-events: only the C3 bounded-receipt helpers (event_stream_bytes/bound_capture_receipt/bound_state_receipt) call it; generic byte measure with no C1/C4 policy; the recorded ambiguity is closed) |
| kaola-acp.py | `bound_capture_receipt` | 1284 | Y | C3-events |
| kaola-acp.py | `bound_state_receipt` | 1332 | Y | C4-state |
| kaola-acp.py | `command_view` | 1373 | Y | C4-state |
| kaola-acp.py | `follow_error_line` | 1402 | Y | C3-events |
| kaola-acp.py | `FollowTextPrinter.__init__` | 1415 | n | C3-events |
| kaola-acp.py | `FollowTextPrinter._end_line` | 1420 | n | C3-events |
| kaola-acp.py | `FollowTextPrinter.feed` | 1425 | n | C3-events |
| kaola-acp.py | `emit_follow_line` | 1462 | Y | C3-events |
| kaola-acp.py | `command_follow` | 1476 | Y | C3-events |
| kaola-acp.py | `command_follow.emit_error` | 1481 | n | C3-events |
| kaola-acp.py | `read_record` | 1544 | Y | core-registry |
| kaola-acp.py | `pid_alive` | 1552 | Y | core-process |
| kaola-acp.py | `socket_request` | 1564 | Y | core-identity |
| kaola-acp.py | `advertised_config_values` | 1603 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `opencode_model_not_found` | 1628 | Y | C2-acp-adapters |
| kaola-acp.py | `set_opencode_model_when_advertised` | 1642 | Y | C2-acp-adapters |
| kaola-acp.py | `answering_socket` | 1671 | Y | core-identity |
| kaola-acp.py | `holder_identity` | 1695 | Y | core-identity |
| kaola-acp.py | `procargs_command` | 1711 | Y | core-process |
| kaola-acp.py | `process_command` | 1740 | Y | core-process |
| kaola-acp.py | `holder_argv_paths` | 1758 | Y | core-identity |
| kaola-acp.py | `holder_argv_anchor` | 1774 | Y | core-identity |
| kaola-acp.py | `git_facts` | 1793 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `base_receipt` | 1808 | Y | C1-lifecycle |
| kaola-acp.py | `holder_lost_receipt` | 1825 | Y | C4-state |
| kaola-acp.py | `op_or_holder_lost` | 1869 | Y | C1-lifecycle |
| kaola-acp.py | `libproc_ps` | 1925 | Y | core-process |
| kaola-acp.py | `run_ps` | 1954 | Y | core-process |
| kaola-acp.py | `recorded_groups` | 1968 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `holders_dispatched_by` | 2068 | Y | C4-state |
| kaola-acp.py | `dispatched_worker_groups` | 2097 | Y | core-process |
| kaola-acp.py | `dispatched_worker_groups.epoch` | 2115 | n | core-process |
| kaola-acp.py | `live_group_members` | 2166 | Y | core-process |
| kaola-acp.py | `unverified_agent_group` | 2177 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `retire_record` | 2194 | Y | core-registry |
| kaola-acp.py | `preserving` | 2206 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `preserve_refusal` | 2210 | Y | core-registry |
| kaola-acp.py | `force_kill_from_record` | 2230 | Y | core-process |
| kaola-acp.py | `force_stop_unreachable` | 2290 | Y | C1-lifecycle |
| kaola-acp.py | `declared_tiers` | 2392 | Y | C2-acp-adapters |
| kaola-acp.py | `tier_prefix` | 2398 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `tier_agent_command` | 2405 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `argv_model` | 2423 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `tier_declared` | 2437 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `tier_refusal` | 2442 | Y | core-registry |
| kaola-acp.py | `fast_intent` | 2465 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `parse_model_components` | 2475 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `selection_basis` | 2508 | Y | C1-lifecycle |
| kaola-acp.py | `model_display_fact` | 2565 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `resolve_selection` | 2583 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `merge_policy_evidence` | 2649 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `parse_acp_model_map` | 2676 | Y | C2-acp-adapters |
| kaola-acp.py | `parse_manifest_meta` | 2686 | Y | C2-acp-adapters |
| kaola-acp.py | `parse_manifest_value_map` | 2705 | Y | C2-acp-adapters |
| kaola-acp.py | `parse_config_id_candidates` | 2715 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `resolve_config_id` | 2720 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `picker_effort_suffix` | 2737 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `acp_value_params` | 2753 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `fast_report` | 2778 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `command_preflight` | 2800 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `holder_predates_steer` | 2847 | Y | C2-acp-adapters |
| kaola-acp.py | `steer_after_turn_refusal` | 2868 | Y | core-registry |
| kaola-acp.py | `validate_heartbeat_target` | 2891 | Y | core-registry |
| kaola-acp.py | `dispatcher_identity` | 2920 | Y | core-identity |
| kaola-acp.py | `repo_problem` | 2939 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `verify_dispatcher_host_live` | 2953 | Y | C5-dispatch |
| kaola-acp.py | `resolve_send_wait` | 2975 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `resolve_send_wait.blocking` | 2987 | n | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `sideagent_host_anchor` | 3037 | Y | C4-state |
| kaola-acp.py | `command_rebind_host` | 3074 | Y | C1-lifecycle |
| kaola-acp.py | `command_rebind_host.refused` | 3080 | n | C1-lifecycle |
| kaola-acp.py | `resolve_heartbeat_host` | 3119 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `heartbeat_host_refusal` | 3219 | Y | core-registry |
| kaola-acp.py | `zcode_host_session` | 3280 | Y | C2-acp-adapters |
| kaola-acp.py | `host_session` | 3286 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `zcode_host_model_match` | 3296 | Y | C2-acp-adapters |
| kaola-acp.py | `zcode_host_request_problem` | 3306 | Y | C2-acp-adapters |
| kaola-acp.py | `zcode_host_selection_fact` | 3321 | Y | C1-lifecycle |
| kaola-acp.py | `zcode_host_config_state` | 3349 | Y | C2-acp-adapters |
| kaola-acp.py | `effective_selection` | 3373 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `explicit_selection_problem` | 3394 | Y | C1-lifecycle |
| kaola-acp.py | `echo_model_verification` | 3413 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `_continuity_text` | 3497 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `_applied_config_value` | 3503 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `_application_fact` | 3512 | Y | C1-lifecycle |
| kaola-acp.py | `_readback_value` | 3531 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `_native_readback` | 3548 | Y | core-identity |
| kaola-acp.py | `_stamp_live_readback` | 3571 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `_most_recent_live` | 3587 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `_applied_baseline_source` | 3610 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `_unverified_explicit_baseline` | 3625 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `_continuity_equal` | 3643 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `_axis_status` | 3649 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `_continuity_outcome` | 3671 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `_explicit_readback_matches` | 3693 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `reconcile_selection_continuity` | 3720 | Y | C1-lifecycle |
| kaola-acp.py | `start_evidence_facts` | 3874 | Y | C1-lifecycle |
| kaola-acp.py | `inherited_start_evidence` | 3883 | Y | C1-lifecycle |
| kaola-acp.py | `preset_class_role` | 3958 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `inherited_session_role` | 3982 | Y | C1-lifecycle |
| kaola-acp.py | `session_role_value` | 3993 | Y | C1-lifecycle |
| kaola-acp.py | `record_start_evidence` | 4017 | Y | C1-lifecycle |
| kaola-acp.py | `stop_started_holder` | 4048 | Y | C1-lifecycle |
| kaola-acp.py | `zcode_host_refusal` | 4107 | Y | core-registry |
| kaola-acp.py | `file_sha256` | 4130 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `invoking_skill_tree` | 4139 | Y | core-process |
| kaola-acp.py | `invoked_via_local_bin` | 4151 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `skew_baseline_dir` | 4171 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `main_skill_record_file` | 4187 | Y | core-process |
| kaola-acp.py | `is_worker_skill` | 4207 | Y | core-process |
| kaola-acp.py | `skill_frontmatter_name` | 4211 | Y | core-process |
| kaola-acp.py | `is_main_skill` | 4228 | Y | core-process |
| kaola-acp.py | `installed_worker_skills` | 4232 | Y | core-process |
| kaola-acp.py | `worker_skill_alignment` | 4269 | Y | core-process |
| kaola-acp.py | `main_skill_build` | 4311 | Y | core-process |
| kaola-acp.py | `main_skill_alignment` | 4319 | Y | core-process |
| kaola-acp.py | `_pin_file` | 4353 | Y | C7-render-install |
| kaola-acp.py | `registration_directories` | 4365 | Y | C1-lifecycle |
| kaola-acp.py | `registration_directories.add` | 4374 | n | C1-lifecycle |
| kaola-acp.py | `registration_pin` | 4391 | Y | C1-lifecycle |
| kaola-acp.py | `current_accepted_revision` | 4400 | Y | C7-render-install |
| kaola-acp.py | `_stored_script_digests` | 4419 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `_restart_required_name` | 4444 | Y | C1-lifecycle |
| kaola-acp.py | `_seat_from_checkout` | 4467 | Y | C1-lifecycle |
| kaola-acp.py | `_changed_recorded_files` | 4481 | Y | core-registry |
| kaola-acp.py | `_unresolved_recorded_files` | 4499 | Y | core-registry |
| kaola-acp.py | `seat_freshness` | 4523 | Y | C1-lifecycle |
| kaola-acp.py | `installer_runtime_roots` | 4605 | Y | C7-render-install |
| kaola-acp.py | `root_recorded_referrers` | 4620 | Y | core-registry |
| kaola-acp.py | `owning_runtime` | 4643 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `skill_refresh_route` | 4665 | Y | core-process |
| kaola-acp.py | `main_skill_skew_refusal` | 4731 | Y | core-process |
| kaola-acp.py | `worker_skill_root_refusal` | 4770 | Y | core-process |
| kaola-acp.py | `worker_skill_skew_refusal` | 4795 | Y | core-process |
| kaola-acp.py | `attach_binding_fact` | 4837 | Y | C4-state |
| kaola-acp.py | `verified_hosts` | 4855 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `host_exists_refusal` | 4898 | Y | core-registry |
| kaola-acp.py | `pre_spawn_refusal` | 4925 | Y | core-registry |
| kaola-acp.py | `resolved_launch_backend` | 4982 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `outside_launch_requested` | 4996 | Y | keep-in-place:kaola-acp.py (source review pending P1 walk) |
| kaola-acp.py | `spawn_holder_outside` | 5000 | Y | C4-state |
| kaola-acp.py | `command_start` | 5063 | Y | C1-lifecycle |
| kaola-acp.py | `_seat_idle` | 5577 | Y | C1-lifecycle |
| kaola-acp.py | `_selection_explicit` | 5589 | Y | C1-lifecycle |
| kaola-acp.py | `apply_recorded_selection` | 5608 | Y | core-registry |
| kaola-acp.py | `_note_post_stop_result` | 5652 | Y | C1-lifecycle |
| kaola-acp.py | `command_drain_restart` | 5674 | Y | C1-lifecycle |
| kaola-acp.py | `main` | 5856 | Y | keep-in-place (P1 adopted keep-in-place: argv->command entrypoint for the whole acp tool; not a component surface) |
| kaola-acp.py | `argument_value` | 6211 | Y | keep-in-place (P1 adopted keep-in-place: argv flag-value helper for the CLI entrypoint; pure CLI plumbing) |
| kaola-record-contract.py | `maintenance_blockers` | 93 | Y | C1-lifecycle |
| kaola-record-contract.py | `refusal` | 194 | Y | core-registry |
| kaola-record-contract.py | `cite_problem` | 203 | Y | keep-in-place:kaola-record-contract.py (source review pending P1 walk) |
| kaola-record-contract.py | `machine_stone` | 221 | Y | keep-in-place:kaola-record-contract.py (source review pending P1 walk) |
| kaola-record-contract.py | `drop_settled_history` | 230 | Y | keep-in-place:kaola-record-contract.py (source review pending P1 walk) |
| kaola-record-contract.py | `unknown_record_keys` | 262 | Y | core-registry |
| kaola-record-contract.py | `reject_record_patch` | 280 | Y | core-registry |
| kaola-record-contract.py | `_text` | 310 | Y | keep-in-place:kaola-record-contract.py (source review pending P1 walk) |
| kaola-record-contract.py | `_string_list_ok` | 314 | Y | keep-in-place:kaola-record-contract.py (source review pending P1 walk) |
| kaola-record-contract.py | `record_type_problem` | 318 | Y | keep-in-place:kaola-record-contract.py (source review pending P1 walk) |
| kaola-record-contract.py | `_rows_problem` | 377 | Y | keep-in-place:kaola-record-contract.py (source review pending P1 walk) |
| kaola-record-contract.py | `count_ok` | 399 | Y | keep-in-place:kaola-record-contract.py (source review pending P1 walk) |
| kaola-record-contract.py | `aggregate_limit_blockers` | 403 | Y | keep-in-place:kaola-record-contract.py (source review pending P1 walk) |
| kaola-record-contract.py | `migrate_authorization_limits` | 420 | Y | C1-lifecycle |
| kaola-record-contract.py | `duplicate_preset_blockers` | 638 | Y | keep-in-place:kaola-record-contract.py (source review pending P1 walk) |
| kaola-record-contract.py | `expanded_grants` | 657 | Y | C5-dispatch |
| kaola-record-contract.py | `delegator_authorization_blockers` | 683 | Y | C1-lifecycle |
| kaola-record-contract.py | `delegator_authorization_blockers.bad` | 698 | n | C1-lifecycle |
| kaola-record-contract.py | `_closed_strings` | 773 | Y | keep-in-place:kaola-record-contract.py (source review pending P1 walk) |
| kaola-record-contract.py | `authorization_blockers` | 781 | Y | C1-lifecycle |
| kaola-record-contract.py | `project_blockers` | 856 | Y | keep-in-place:kaola-record-contract.py (source review pending P1 walk) |
| kaola-record-contract.py | `protected_blockers` | 873 | Y | keep-in-place:kaola-record-contract.py (source review pending P1 walk) |
| kaola-record-contract.py | `recovery_from_v1` | 883 | Y | C4-state |
| kaola-record-contract.py | `note_unmapped` | 907 | Y | keep-in-place:kaola-record-contract.py (source review pending P1 walk) |
| kaola-record-contract.py | `identity_only` | 917 | Y | core-identity |
| kaola-record-contract.py | `pick` | 924 | Y | keep-in-place:kaola-record-contract.py (source review pending P1 walk) |
| kaola-record-contract.py | `authorization_view` | 930 | Y | C1-lifecycle |
| kaola-record-contract.py | `capability_from_grants` | 944 | Y | C2-acp-adapters |
| kaola-record-contract.py | `project_view` | 986 | Y | C4-state |
| kaola-record-contract.py | `recovery_view` | 990 | Y | C4-state |
| kaola-record-contract.py | `unknown_paths` | 994 | Y | core-registry |
| kaola-record-contract.py | `unknown_paths.add` | 1000 | n | core-registry |
| kaola-record-contract.py | `projected_record` | 1063 | Y | core-registry |
| kaola-record-contract.py | `projected_state` | 1067 | Y | core-registry |
| kaola-record-contract.py | `union_dispatch` | 1112 | Y | C1-lifecycle |
| kaola-record-contract.py | `clear_stage_warning` | 1123 | Y | keep-in-place:kaola-record-contract.py (source review pending P1 walk) |
| kaola-record-contract.py | `cleanup_current` | 1129 | Y | C1-lifecycle |
| kaola-record-contract.py | `assess_backups` | 1248 | Y | core-atomic |
| kaola-record-contract.py | `_watch_status` | 1264 | Y | keep-in-place:kaola-record-contract.py (source review pending P1 walk) |
| kaola-record-contract.py | `_watch_duty_shape` | 1280 | Y | keep-in-place:kaola-record-contract.py (source review pending P1 walk) |
| kaola-record-contract.py | `_string_field` | 1286 | Y | keep-in-place:kaola-record-contract.py (source review pending P1 walk) |
| kaola-record-contract.py | `section_shape_problems` | 1292 | Y | C1-lifecycle |
| kaola-record-contract.py | `_legacy_bag_problem` | 1358 | Y | keep-in-place:kaola-record-contract.py (source review pending P1 walk) |
| kaola-record-contract.py | `_day_problems` | 1367 | Y | keep-in-place:kaola-record-contract.py (source review pending P1 walk) |
| kaola-record-contract.py | `_delegator_nest_problems` | 1398 | Y | keep-in-place:kaola-record-contract.py (source review pending P1 walk) |
| kaola-record-contract.py | `delegator_blockers` | 1482 | Y | keep-in-place:kaola-record-contract.py (source review pending P1 walk) |
| kaola-record-contract.py | `delegator_migrated` | 1560 | Y | C4-state |
| kaola-record-contract.py | `host_changes` | 1634 | Y | C4-state |
| kaola-record-contract.py | `host_changes.take` | 1640 | n | C4-state |
| kaola-record-contract.py | `short` | 1658 | Y | keep-in-place:kaola-record-contract.py (source review pending P1 walk) |
| kaola-record-contract.py | `judgment_digest` | 1664 | Y | keep-in-place:kaola-record-contract.py (source review pending P1 walk) |
| kaola-record-contract.py | `_positive_count` | 1672 | Y | keep-in-place:kaola-record-contract.py (source review pending P1 walk) |
| kaola-record-contract.py | `_verdict_value` | 1679 | Y | keep-in-place:kaola-record-contract.py (source review pending P1 walk) |
| kaola-record-contract.py | `_has_original_evidence` | 1686 | Y | keep-in-place:kaola-record-contract.py (source review pending P1 walk) |
| kaola-record-contract.py | `_evidence_locator` | 1693 | Y | keep-in-place:kaola-record-contract.py (source review pending P1 walk) |
| kaola-record-contract.py | `_pending_unbound_submission` | 1704 | Y | keep-in-place:kaola-record-contract.py (source review pending P1 walk) |
| kaola-record-contract.py | `_unbound_marker` | 1717 | Y | keep-in-place:kaola-record-contract.py (source review pending P1 walk) |
| kaola-record-contract.py | `_submission_binding` | 1725 | Y | C1-lifecycle |
| kaola-record-contract.py | `_escalation_held` | 1730 | Y | C1-lifecycle |
| kaola-record-contract.py | `_repair_still_open` | 1741 | Y | keep-in-place:kaola-record-contract.py (source review pending P1 walk) |
| kaola-record-contract.py | `_duty_fields` | 1750 | Y | keep-in-place:kaola-record-contract.py (source review pending P1 walk) |
| kaola-record-contract.py | `rejection_projection` | 1758 | Y | C1-lifecycle |
| kaola-record-contract.py | `task_attention` | 1810 | Y | C4-state |
| kaola-record-contract.py | `_record_root` | 1859 | Y | core-registry |
| kaola-record-contract.py | `_repo_of_state_file` | 1868 | Y | core-identity |
| kaola-record-contract.py | `_same_repo` | 1873 | Y | core-identity |
| kaola-record-contract.py | `_host_of` | 1884 | Y | keep-in-place:kaola-record-contract.py (source review pending P1 walk) |
| kaola-record-contract.py | `node_is_running` | 1896 | Y | C4-state |
| kaola-record-contract.py | `delegator_file_view` | 1950 | Y | C4-state |
| kaola-record-contract.py | `delegator_file_view.add` | 1954 | n | C4-state |
| kaola-record-contract.py | `host_view` | 2036 | Y | C4-state |
| kaola-record-contract.py | `injection_body` | 2167 | Y | C1-lifecycle |

## P1 residual decisions — issue #275, slice 1 (2026-10-07)

The 18 rows the source review left explicit `keep-in-place` are ADOPTED keep-in-place: they are shared CLI receipt/argparse/bootstrap plumbing with no single component owner, and none is minimal-core identity/process/atomic. The two recorded arguable calls are resolved: `parse_flat_yaml` -> C2-acp-adapters (it joins its only consumer `catalog_from_files`, already C2) and `line_size` stays C3-events (only the C3 bounded-receipt helpers call it). No other row is reassigned.

| file | qualified_name | line | final primary | decision (one line) |
|---|---|---|---|---|
| kaola-dispatch.py | `emit` | 122 | keep-in-place | adopted keep-in-place: shared stdout JSON receipt emitter for C4/C5 commands; no single owner and not minimal-core identity/process/atomic |
| kaola-dispatch.py | `fail` | 128 | keep-in-place | adopted keep-in-place: shared stdout failure emitter for all dispatch commands; file-local CLI plumbing |
| kaola-dispatch.py | `build_parser` | 6099 | keep-in-place | adopted keep-in-place: argparse wiring spanning C4/C5 command groups; splitting adds a CLI contract without removing coupling |
| kaola-dispatch.py | `build_parser.writer_args` | 6141 | keep-in-place | adopted keep-in-place: shared writer-args plumbing nested in build_parser; moves with its parent |
| kaola-dispatch.py | `main` | 6401 | keep-in-place | adopted keep-in-place: argv->command entrypoint for the whole dispatch tool; not a component surface |
| kaola-acp-holder.py | `_import_sibling` | 1206 | keep-in-place | adopted keep-in-place: generic sibling-module importer used by holder bootstrap; no domain owner |
| kaola-acp-holder.py | `load_sibling_modules` | 1227 | keep-in-place | adopted keep-in-place: holder bootstrap wiring quota/record/compact siblings + byte snapshot; loader plumbing, not core identity/process |
| kaola-acp.py | `InputError.__init__` | 728 | keep-in-place | adopted keep-in-place: typed CLI input-error construction shared by all acp commands; CLI surface, not minimal core |
| kaola-acp.py | `InputError.__str__` | 733 | keep-in-place | adopted keep-in-place: input-error formatting shared by all acp commands |
| kaola-acp.py | `ReceiptArgumentParser.error` | 738 | keep-in-place | adopted keep-in-place: argparse error->receipt adapter shared by all acp subcommands |
| kaola-acp.py | `input_error_receipt` | 744 | keep-in-place | adopted keep-in-place: pre-transport input-failure receipt shared by all acp commands |
| kaola-acp.py | `die` | 754 | keep-in-place | adopted keep-in-place: fatal stderr exit helper shared by all acp commands |
| kaola-acp.py | `parse_list_args` | 860 | keep-in-place | adopted keep-in-place: argparse plumbing for the list command; list semantics stay in command_list (C1) |
| kaola-acp.py | `parse_survey_args` | 1001 | keep-in-place | adopted keep-in-place: argparse plumbing for survey; survey semantics stay in command_survey (C2) |
| kaola-acp.py | `parse_packages_args` | 1180 | keep-in-place | adopted keep-in-place: argparse plumbing for packages; catalog semantics stay in command_packages (C2) |
| kaola-acp.py | `parse_model_package_args` | 1188 | keep-in-place | adopted keep-in-place: argparse plumbing for model-package; semantics stay in command_model_package (C2) |
| kaola-acp.py | `main` | 5856 | keep-in-place | adopted keep-in-place: argv->command entrypoint for the whole acp tool; not a component surface |
| kaola-acp.py | `argument_value` | 6211 | keep-in-place | adopted keep-in-place: argv flag-value helper for the CLI entrypoint; pure CLI plumbing |
| kaola-dispatch.py | `parse_flat_yaml` | 145 | C2-acp-adapters | resolved C2-acp-adapters: sole consumer catalog_from_files (already C2) reads C2-owned platforms/*.yaml; the generic reader carries no C5 admission policy; the recorded C5 alternative is closed |
| kaola-acp.py | `line_size` | 1279 | C3-events | resolved C3-events: only the C3 bounded-receipt helpers (event_stream_bytes/bound_capture_receipt/bound_state_receipt) call it; generic byte measure with no C1/C4 policy; the recorded ambiguity is closed |
