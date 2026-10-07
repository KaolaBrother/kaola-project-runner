# Source-review pass — inventory-matrix.json (source @7012e4d6)

Reviewed by reading each function at its matrix line range against the design's
component contracts. All four source hashes match `recount.py`. Output:
`/tmp/kpr-matrix-review.json` — 430 rows (223 hold resolutions + 207 keyword
corrections). The root-decided `seat_projection` family stays `C5`.

## Hold walk (223 rows)

- `kaola-dispatch.py` (92): ~70 are dispatch machinery — `eligibility`/ceiling/
  held-seat admission, index write (`IndexLock`, `merge_index_rows`,
  `finish_index`), collect/read_turn → **C5**; ~20 are state-tool machinery
  (judgment/submission/effort-record helpers, `cite_retrievable` git check,
  `requirement_lines` AGENTS.md read, `unmapped_fields` migration,
  `_delegator_read`/`command_delegator_update`) → **C4**; `emit`/`fail` stay
  `keep-in-place` (shared receipt emitters for C4+C5 commands).
- `kaola-acp-holder.py` (20): `EventLog.*` → **C3**; `AgentConnection.*`,
  `_as_text`, `rfc3339_instant` (session-list time parse) → **C2**;
  `StderrPump.*` → **C1**; `_hex_revision` → **C7**; `_import_sibling`/
  `load_sibling_modules` stay `keep-in-place` (bootstrap spanning C2/C4/C7).
- `kaola-acp.py` (77): manifest/tier/model/config/continuity/survey/preflight/
  bridge cluster (~40) → **C2**; holder ops + heartbeat-host resolution →
  **C1**; `resolve_repo`/`record_root`/`repo_problem`/`host_session`/`git_facts`
  → **core-identity**; `probe_socket_ok`/`recorded_groups`/
  `unverified_agent_group` → **core-process**; `file_sha256`/`skew_baseline_dir`/
  `_stored_script_digests`/`owning_runtime` → **C7**; 9 stay `keep-in-place`
  (argparse/die/InputError plumbing).
- `kaola-record-contract.py` (34): all **C4** — the heartbeat-state record
  contract (validators, blockers, projections, migration helpers).

## Spot-check disagreements (207 corrections, ~110 keyword rows sampled)

Systematic draft errors:

- **Holder C4 bucket → C1**: ~70 `Holder.*`/`ViewProjection.*` rows were
  keyworded `C4-state` for touching "state"; source shows holder-internal
  turn/relay/wake/node/carrier machinery — holder lifecycle → **C1**
  (`ViewProjection.*` serves `op_view`; `_quota_models`/`_current_model`/`initialize_agent`/`_list_repo_sessions` → **C2**; `note_agent_children`/`holders_dispatched_by` → **core-process**; `op_worker_event` + two bookkeeping helpers → **C3**).
- **acp.py skill cluster → C7**: 15 rows keyworded `core-process` are installed-
  Skill build/skew/pin machinery (`worker_skill_alignment`, `skill_refresh_route`,
  `*_skew_refusal`, `registration_*`, `seat_freshness`, `capture_script_paths`).
- **`core-registry` was a junk drawer**: refusal builders and record-file ops
  → `C1`/`C2`/`C4`/`core-identity`/`C7` per actual behavior (`pre_spawn_refusal`→C1,
  `tier_refusal`/`zcode_host_refusal`/`codex_child_refusal`→C2, `retire_record`(acp)→core-identity, `retire_record`(dispatch)→C4, skew/file referrers→C7).
- **dispatch.py `C1` rows**: the retire/state-update helpers (`apply_section_update`, `seat_entries`, `task_seats`, `handoff_seats`, `_submission_*`, `carrier_*`, `note_section_source`, `revision_of`, `json_arg`, `maintenance_brief`, `command_state_backups`) → **C4**; execute-side receipt predicates (`session_absent`, `holder_of`, `application_of`, `mutation_of`, `assignment_identity`, `preserve_correlation`, `held_seat`, `IndexLock.__exit__`) → **C5**; `session_name` → **core-identity**; `main`/`build_parser` → keep-in-place.
- Other moves: `socket_request`→C1 (holder IPC), `answering_socket`/`holder_identity`/`holder_argv_*`→core-process (design-named process facts), `command_view`/`view_error`→C1, `bound_state_receipt`→C3, `authorization_view`/`capability_from_grants`→C5 (grant semantics), `EventLog._restore_cursor`/`oldest_cursor`→C3, `Holder.follow_heartbeat_loop`→C3, `Holder.op_steer*`→C1, `dsh_permission_mode`/`loopback_no_proxy`/`session_new_*`/selection-evidence cluster→C2.

## §3b — typed error/refusal surface and I/O (from source)

**C1-lifecycle** — holder op `error.code` + receipt `reason`:
`agent-not-running, agent-exited, agent-system-error, no-acp-session, prompt-in-progress, queue-empty, stopping, prior-turn-unsuccessful, duplicate-prompt-warning, holder-instance-mismatch, unknown-op, bad-request, no-pending-permission, request-id-required, unknown-request, cancel-turn-changed, steer-empty/-unsupported/-queued/-prompt-required/-undecided/-unrecognized-outcome/-no-response/-reply-pending/-rejected/-prompt-failed/-send-failed/-turn-changed/-cancel-unconfirmed/-write-only-confirmation, carrier-aborted, host-answered/-closed/-unreachable/-reply-invalid, heartbeat-host-foreign-repo, invalid-heartbeat-host, no-heartbeat-host, invalid-session-role, invalid-start-evidence, start-evidence-too-large, session-role, node-starting/-start-error/-stop-unreachable, native-route-owned, no-compact-module, no-pending-reload, reload-inflight, not-attempted, notice-*(4 codes), coalesced, prior-notice-unresolved, sideagent-receipt-unreadable, sideagent-unreachable, host-entry-absent`; acp.py adds `no-session, holder-lost/-unreachable/-closed/-socket-missing/-instance-mismatch/-start-timeout, session-exists, start-incomplete, host-exists, preserve-unsupported, rebind-host-unresolved, drain-not-idle, drain-restart-mode-required/-selection-unknown, drain-stop-failed, steer-mode-required, steer-capability-unknown, steer-holder-outdated, key-unsupported, answer-unsupported, launch-broker-missing/-failed/-timeout, pgid-identity-unverified, heartbeat-host-conflict/-unresolved, invalid-input`.
I/O: `record.json` read/write/rename under `<record_root>/<platform>/<session>/<repo-sha16>/`; `holder.sock` AF_UNIX (listener + ops `state,view,prompt,steer,steer_interrupt,wait,capture,permit,cancel,stop,set_config_option,record_start_evidence,rebind_heartbeat_host,worker_event,compact_notice,follow`); AF_UNIX sends to host/sideagent/node sockets; agent stdio pipes (spawn boundary C2); reads `.kaola/heartbeat-prompt.json` (carrier) and `events.jsonl` (receipts); env `KAOLA_ACP_DISPATCHER`, `KAOLA_ACP_RECORD_ROOT`, `XDG_RUNTIME_DIR`.

**C3-events** — codes: `worker-event-unsupported, worker-event-invalid, worker-event-queue-full`; follow error lines reuse `no-session, holder-lost, holder-unreachable`; event stream entries use `kind` values, not error codes (unverified: full `kind` vocabulary not enumerated).
I/O: `events.jsonl` + `events.jsonl.N` rotations in record dir (append/read/rotate); follower writes over the same `holder.sock` AF_UNIX stream.

**C4-state** — `StateRefusal`/`fail`/`emit` reasons:
`invalid-input, conflict, host-only, record-missing, record-retired, evidence-required, retire-unmet, cite-required, state-exists, state-managed, state-missing, state-unreadable, snapshot-unstable, legacy-format, legacy-unreadable, schema-unsupported, source-required, writer-refused, writer-mismatch, binding-superseded, sideagent-unbound, expect-rev-required, host-turn-required, fingerprint-differs, host-identity-required, signal-unverified, original-signal-already-settled, scoped-checkpoint-already-settled, node-identity-required, invalid-maintenance, host-view-too-large, identity-unavailable, identity-mismatch, batch-unverified, carrier-limit, delegator-field-invalid, delegator-migration-needed`.
I/O: `.kaola/heartbeat-prompt.json` under `StateLock` (fcntl) + `read_state_file`/`atomic_write`; `.vN-*` backups (read); `AGENTS.md` (read); `--file/--set/@path/--index/--live/--handoff` inputs; `record.json` reads (caller/carrier checks); `events.jsonl` reads (transcription); `git` subprocess (cite_retrievable). No sockets.

**C5-dispatch** — `reason`/`withheld` vocabulary:
`invalid-input`; withheld `preset-unresolved, excluded, revoked, paused, state-unreadable, count-unreadable, absent, lifetime-unreadable, expiry-unreadable, expired`; ceiling `above-ceiling, ceiling-incomplete, ceiling-unreadable, revoked, paused, excluded, expired`, `on-hold`, `held:<ids>`; admission `not-authorized, shared-occupied, occupancy-unknown, count`; item statuses `not-run/unknown/failed/in-flight` with reasons `runner-missing, session-gone, reconciliation-needed, expected-holder-absent, start-*, repo-mismatch, holder-mismatch, selection-mismatch, assignment-unbound, fingerprint-differs, mutation-ambiguous, existing-session-ambiguous, send-*, mutation-unknown, already-collected, already-admitted, admitted, collected, collect-*, collection-error, session-mismatch, capture-*, turn-failed, still-running, no-result, reconciled, status-*` (`*`=dynamic suffix).
I/O: reads `--authorization/--availability/--plan/--prior-index/--live/--state` JSON, `platforms/*.yaml` (flat parse); read+atomic-write dispatch index under `IndexLock` (flock); spawns `kaola-acp.py` subprocesses and parses stdout receipts. No sockets opened directly (unverified: heartbeat carrier sockets are the holder's, surfaced indirectly via subprocess output).
