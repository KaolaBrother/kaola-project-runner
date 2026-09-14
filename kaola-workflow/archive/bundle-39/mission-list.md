# Issue #39 — optionally bind ACP permit/cancel to expected holder instance

Issue: https://github.com/KaolaBrother/kaola-project-runner/issues/39
Branch: workflow/bundle-39
Worktree: .kw/worktrees/bundle-39
Contract: frozen additive protocol in issue body (no comments). Runner owns Runner files only.

## Missions

- item: Mint immutable random `holder_instance_id` per Holder construction; expose on record, op_state, op_view (top-level), list rows, start receipt; enforce optional `expected_holder_instance_id` inside self.lock at permit/cancel mutation point incl. inactive cases; mismatch error `holder-instance-mismatch` + mutation_status not_started + mutation_performed false + both IDs in error object; zero agent writes on mismatch.
  status: done
  dispatched: self (inline)
  result: scripts/kaola-acp-holder.py — mint in __init__ (secrets.token_hex(16)); field added to write_record, op_state, op_view payload; _holder_instance_mismatch helper returns code holder-instance-mismatch, mutation_status/mutation_performed at top level and inside error object, both IDs in error, plus evidence event; op_permit checks expected inside self.lock before pending lookup; op_cancel mutation section moved under self.lock (pending settle, cancel_requested, session/cancel write) with expected check first; turn_cond wait stays outside the lock.
- item: CLI `--expected-holder-instance-id` flag on shared parser; forward exact value (incl. explicit empty) as socket param on permit, cancel, and key escape alias; shell wrapper kaola-tmux.sh accepts/forwards flag with given-tracking so empty string still forwards.
  status: done
  dispatched: self (inline)
  result: scripts/kaola-acp.py — parser flag added; forwarded on permit/cancel/key-escape when `is not None`; list rows carry top-level holder_instance_id from record; start receipt carries holder_instance_id from state. scripts/kaola-tmux.sh — flag parsed with expected_holder_instance_id_given tracker and forwarded verbatim (empty value preserved).
- item: Contract tests — real holder/socket restart same-triplet reused request_id (stale permit AND cancel → mismatch, zero outbound writes on mock log, B pending/turn intact; fresh B expected call succeeds; omitted flag legacy success; explicit empty token not downgraded; native resume mints new ID; identity on list/view/follow/record/status); wrapper forwarding; existing concurrent settlement stays green.
  status: done
  dispatched: self (inline)
  result: tests/contract/test-acp-contract.py Issue39HolderInstanceTests — 6 tests, all pass: restart-same-triplet reused request_id (stale permit+cancel+key-escape → mismatch, zero agent writes proven on mock outbound log, pending/turn intact; correct-B permit succeeds; legacy cancel succeeds; post-settlement stale cancel still mismatches), explicit-empty token not downgraded, identity on start/record/observe/status/view/list/follow-snapshot, native resume mints fresh id with same acp session, concurrent same-id permit with matching expected still at-most-once, shell wrapper forwards flag incl. empty.
- item: Docs — api.md + docs/acp-watch/{list-view,permit-lock}.md fields/compatibility boundary; update view sample fixture with holder_instance_id; CHANGELOG Unreleased entry.
  status: done
  dispatched: self (inline)
  result: docs/api.md transport paragraph extended; list-view.md list+view tables and sample updated; permit-lock.md #39 addendum; fixtures/kaola-acp-view-1.sample.json carries holder_instance_id; CHANGELOG Unreleased entry added (v0.1.0 untouched).
- item: Regenerate seven Skills (render --write/--check), grok-golden untouched, run focused contract tests + validate.sh, exact owned cleanup.
  status: done
  dispatched: self (inline)
  result: render --write WROTE 7 Skills / --check PASS; grok-golden 0 changed files; Issue39+Issue25+AcpContract 27 tests OK; AcpWatch 13 OK; validate.sh exit 0; owned leaked test holders from the run killed by exact PID (foreign devin-kaola-*/vrpai-* sessions untouched).
- item: Commit on workflow/bundle-39, push, open PR; report SHA + test receipts; STOP before merge.
  status: done
  dispatched: self (inline)
  result: b950c0aded4c5f983971809198026023f2f39741 committed on workflow/bundle-39 (30 files, +767/-97), pushed to origin, PR https://github.com/KaolaBrother/kaola-project-runner/pull/40 opened (open, unmerged — supervisor review). Receipts: Issue39+Issue25 10 OK, Issue25+AcpContract 17 OK, AcpWatch 13 OK, render --check 7 Skills PASS, validate.sh exit 0. Final-validation record + doc-docking + finalization-summary written under kaola-workflow/bundle-39/; close/archive/sink deferred per stop-before-merge instruction; v0.1.0 untouched.
