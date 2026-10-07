## 5. Post-correction addendum (@4f28f8ac; review only)

Inputs: four docs @4f28f8ac. Checks: `grep -c '^def '` = 208/51/195/68 (matches; all-def 233/209/207/72); ten vendored holder copies md5-identical; render `--check` PASS.

**(1) ADR-1 / §6a.** Converged. One contradiction: §6a says the core "enforces" C4 data access, yet holders keep single-writer rights when the core exits. Pick: holders write via the library under file locks; core never in the write path. ADR-1 anchors still wrong: acp.py:1537-1546 is read_record/socket close, :1680-1693 is socket-candidate probing, :1166/:3556 are dispatch.py.

**(2) Inventory.** Counts verified. But 299/522 rows are UNASSIGNED (dispatch 111, acp 127, record-contract 51, holder 10) under one blanket sentence, not per-row reasons. The holder's 158 class-internal defs (the real event loop, ~:1800-6000) have no rows, exactly the C1/C3 seam B0 cuts. Ten rows sampled, five disagreements: `observed_at` :585 is a UTC timestamp helper, not C3; `caller_dispatcher` :1242 recovers holder identity from env, CORE-identity not C1; `seatbelt_confined` :870 is a process fact, not C1; `_snapshot_file` :1176 is script-digest/skew (C7 or C1), not C4; `compact_module` :1109 is the holder's loader of C6, i.e. C1 code and the missing C1→C6 edge. Agreed: `model_match`, `latest_session`, `quota_module`, `projected_record`, `pid_alive`/`process_alive` (duplication unresolved). New: holder `quota_module` loading C5 code plus `run_runner` (C5) spawning C1 makes C1↔C5 a cycle unless kaola-quota.py is declared C2 catalog data. `run_runner`, `acp_runner` and both `holders_dispatched_by` copies stay UNASSIGNED; §4 DAG still lacks C5→C1, C1→C6, C1→C4.

**(3) Candidate-vs-existing.** Honest. C6 queue: C4 owning record/replay is right, but the holder detects absence (:1109-1124), so C1→C4 must be a declared edge; present behaviour past `_COMPACT=False` unverified by me.

**(4) Fencing.** ADR-5 right in kind, not sufficient: no "machine-local" scope anywhere; no compare-under-lock rule (epoch stored in the artifact, verified on every StateLock write); §6:67 still says "holder_instance_id epoch, newer supersedes", contradicting ADR-5.

**(5) Events.** Absent: no "gap", "dup", "order" or "catch-up" in any doc, only "cursor semantics designed". The P5 gate must name all four plus events.jsonl rotation behaviour.

**(6) Retire.** §5 reader-fallback converges with Q3(ii); Q3(i) implied. Uninstall-time data default still unstated.

**(7) ADR-6.** Verified: guidance at template sideagent-node.md:60, render PASS, accepted checkout 3de9f61a exists. Rendered copy at HEAD is stale (render uncommitted). Event 105633 is consumer-bridge evidence unreadable here: unverified.

**(8) Gates.** P4-parallel beats my waiver; accepted. Gap: §6a's core-down degrade relies on P3's queue contract, so gate P5 on P3 or scope that claim out. P1 "without behavior change" stays false (three duplicate implementations).

**Choices re-checked.** (1) Packaging: open decision 1 still says shared package; evidence (identical vendored copies, beside-me discovery in `acp_runner`) supports vendor-per-skill, render-enforced identical. (2) "Flip" is moot after ADR-1; recast as pre-registered per-axis pass/stop thresholds before P5 starts (nine axes named, no thresholds). (3) Uninstall data retain-frozen still open.

— End addendum.
