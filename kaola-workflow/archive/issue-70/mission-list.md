# Issue #70 — ZCode Host: expose the worker holder's actual heartbeat binding, add reuse verification and safe missed-binding recovery

Run: issue-70 · branch `workflow/issue-70` · worktree `.kw/worktrees/issue-70`
Boundary: transport/receipt truth + ZCode Host guidance only. No new rebind API, scheduler,
state machine, or global gate; unbound ordinary workers stay legal. No finalize/close/archive/
sink/push without an outer ACCEPT. Do not touch the issue-68 or issue-65/#69 runs.

## 1. Expose the holder's actual notification target through the existing ACP surfaces
- item: Carry the holder's really-adopted heartbeat host (or an explicit null) on `state`,
  `record.json`, and the CLI receipts that report holder facts; keep the `start` input echo
  distinguishable from the running fact; a pre-#70 record/holder reports unknown, never
  "unbound"; existing field shapes stay compatible. Sources only — `skills/` is generated.
- status: done
- dispatched: self, inline in worktree `.kw/worktrees/issue-70`; output lands in
  `scripts/kaola-acp.py` and `scripts/kaola-acp-holder.py` on branch `workflow/issue-70`.
- result: done. Holder `write_record`/`op_state` now carry `heartbeat_host` (the adopted
  target or null); `kaola-acp.py` gained `attach_binding_fact()` used by `start` (success and
  `session-exists`) and `observe`/`status`, `heartbeat_host_requested` records the input, and
  the resolved target is handed to the holder so its answer is the validated one. Absent key
  → `heartbeat_host_known: false`, never a fake null.

## 2. Automated contract evidence for the exposed binding
- item: Contract test proving: unarmed worker still works end to end and reports an explicit
  null; an armed worker's reported target equals the holder's real one; a live holder does not
  report a new target after a later env change or a repeat `start` (session-exists); an old
  record reads as unknown; previously asserted receipt fields still present.
- status: done
- dispatched: self, inline; output lands in `tests/contract/test-issue-70-binding-fact.py`
  plus the updated Issue #66 unarmed-worker assertion in
  `tests/contract/test-zcode-heartbeat-contract.py`.
- result: done. New suite 3/3 tests, 27 checks (running fact vs input, `session-exists` reuse,
  the event reaching only the bound Host, explicit null, pre-#70 record unknown, stop/start
  rebinding); `test-zcode-heartbeat-contract` 9/9, 164 checks. Registered in both
  `validate.sh` suite lists.

## 3. ZCode Host dispatch/recovery guidance
- item: In `templates/orchestrator/references/` only: verify the actual target belongs to the
  current Host on every worker start — new and reused, not just the first round; state that the
  env var applies to that one start without claiming environments never inherit; and give the
  minimal missed/mis-bound recovery along the existing safety boundary (keep in-flight work and
  read its result, rebind at a safe idle point with the existing exact stop/start, resume only
  where supported and evidenced, never auto-cancel/re-send/switch platform/kill the Host).
  Render with `render-skills.py --write`; byte budgets must not rise.
- status: done
- dispatched: self, inline; output lands in
  `templates/orchestrator/references/zcode-host-dispatch.md.tmpl` and `host-startup.md.tmpl`
  plus their rendered `skills/kaola-project-runner/references/` copies.
- result: done. Dispatch reference gained "Verify the binding in force — every worker, new or
  reused" and "A missing or wrong binding" (keep in-flight work, carry the duty, rebind only at
  a safe idle point via exact stop/start with optional `--resume`, never auto-cancel/re-send/
  switch/kill); host-startup took the identity table and the loaded-payload check (a merged
  checkout is not an installed Skill); `docs/zcode-host.md` states the same facts. Rendered
  8184 B / 8192 B and 6544 B / 8192 B — budgets unchanged, `render-skills.py --check` PASS.

## 4. Isolated live ACP evidence
- item: One ZCode Host + one worker in an isolated sentinel repo: bound start, non-blocking
  dispatch, Host turn ending on its own, worker event waking the Host, Host reading the real
  reply; plus reuse verification on a second start and the missed-binding recovery path. Keep
  raw inputs/receipts/outputs and exact-stop proof under
  `kaola-workflow/issue-70/evidence/`. Behavioral proof, not grep of strings.
- status: done
- dispatched: self as the outer controlling Agent, driving a live ZCode Host (`zcode-i70-host`)
  and a Codex worker (`codex-i70-w1`) in the isolated sandbox `/tmp/kw-i70-live/project` with
  candidate Skills copied to `/tmp/kw-i70-live/project/.zcode/skills` (no global install);
  raw receipts, prompts and captures land in `kaola-workflow/issue-70/evidence/live/`.
- result: done — `kaola-workflow/issue-70/evidence/live-2026-09-18.md` with raw evidence
  `evidence/live/00…24`. Live chain on candidate 3be1994: adopted unbound worker verified by
  the Host itself via `observe` (`heartbeat_host: null`, known); repeat `start` with a correct
  env returned `session-exists` with the null fact beside the requested target; the unbound
  worker's finished turn produced zero `worker_event` entries on the Host; after acceptance the
  Host rebound via exact stop/start (+`--resume`), verified the fact, and the next turn end
  woke it through a real `kaola-host-notify/1` (staged 1038 → delivered 1039 → confirmed 1240,
  plus a `terminated` event delivered at the next boundary); exact stops left
  `residual_pids: []`, exit 0, no i70 residue, other sessions untouched.

## 5. Freeze and validate the candidate
- item: On the frozen candidate SHA: `./scripts/render-skills.py --check`, `./scripts/validate.sh`,
  and the Issue #70 contract test; sync latest `main` at a safe point preserving both #68 and #70
  semantics; record exact outcomes and evidence paths for outer review. Nine-platform re-validation
  and PTY are out of scope.
- status: done
- dispatched: self, inline in `.kw/worktrees/issue-70`; outcomes land here and in
  `kaola-workflow/issue-70/evidence/validate-2026-09-18.log`.
- result: done. Merged `main` (b229f84, Issue #68 already landed) into `workflow/issue-70` at
  4c1fd2f — clean, both suite registrations and both sets of heartbeat semantics preserved.
  The first full `validate.sh` after the merge FAILED 7 assertions in
  `test-issue-65-host-contract.py`: my prose compression had dropped sentences that contract
  pins. Fixed by rebuilding the reference from the pre-change template, keeping every pinned
  sentence verbatim and re-fitting the budget by moving the outer-Agent section into
  `host-startup.md`; the two assertions Issue #70 genuinely supersedes (`receipt["heartbeat_host"]
  = heartbeat_host` and "No `heartbeat_host` key means …") were updated to the new contract with
  a comment. Delivered candidate `c96c1c6573969e7acd7c1a8b1e20ed763571a971`:
  `render-skills.py --check` PASS (budgets OK: dispatch 8189 B, host-startup 6254 B of 8192 B),
  `./scripts/validate.sh` EXIT=0 (full log in evidence). The live evidence stays valid: the ACP
  scripts are byte-identical between the live-run SHA 3be1994 and the delivered SHA. Nine-platform
  re-validation and PTY were out of scope; no push, no finalize, no archive.

## 6. Rebase onto latest main, re-freeze, and re-prove the delivered Host guidance
- item: Replace the merge with a rebase onto `main` at the safe point (branch is local-only and
  no one else builds on it), keep Issue #68 semantics and the byte budgets, re-run the affected
  diff/render/validate on the new SHA, and cover the one gap the earlier freeze left: the Host
  guidance the live run read is not byte-identical to the delivered text.
- status: done
- dispatched: self, inline in `.kw/worktrees/issue-70`; the re-freeze lands on branch
  `workflow/issue-70` and the re-proof in `kaola-workflow/issue-70/evidence/live-recheck/` plus
  `evidence/live-recheck-2026-09-18.md`.
- result: done. `git rebase main` replayed both commits with no conflict and produced a
  byte-identical tree to the pre-rebase candidate (`git diff i70-premerge-backup HEAD` empty);
  new frozen SHA `a193d3c12d9080e2b751be6786df753072683656` (`a395eb1` feat + `a193d3c` docs,
  linear on `main` b229f84, merge commit gone). Issue #68 semantics intact (its snapshot suite
  and both suite-list registrations present); `templates/budgets.json` untouched;
  `render-skills.py --check` PASS with dispatch 8189 B and host-startup 6254 B of 8192 B;
  `./scripts/validate.sh` EXIT=0. Minimal live re-proof on the delivered text: a fresh ZCode
  Host, given an adopted unbound worker and a read-only prompt, ran `observe` itself, answered
  "binding not in place" quoting `heartbeat_host_known: true` / `heartbeat_host: null` and
  distinguishing them from `heartbeat_host_requested`, named the exact recovery order, refused
  repeat-`start`/`send` rebinding, and read absent binding information as unknown-treat-as-unbound.
  Exact stops: `stopped: true`, exit 0, `residual_pids: []`, no residue; Issues #67, #71, #72 and
  VRPCadCore sessions untouched. No push, no finalize.

## 7. Close the review's lifecycle gap: hand the wake duty over, or report blocked
- item: The `a193d3c` recovery step 2 told a Host to record the read-back duty in its heartbeat
  body and end the turn; when the unbound worker is the only wake source that write starts
  nothing and the Host waits forever. Fix as guidance only — hand the duty to the existing
  outer Agent before ending the turn, report blocked when there is no outer Agent and no other
  confirmed wake source — with no timer, poll loop or rebind API, nothing cancelled, no field
  or budget change, plus one minimal real-Agent scenario.
- status: done
- dispatched: self, inline in `.kw/worktrees/issue-70`; output lands in the two orchestrator
  reference templates and their rendered copies, `docs/zcode-host.md`,
  `tests/contract/test-issue-70-binding-fact.py`, and
  `kaola-workflow/issue-70/evidence/live-handoff*`.
- result: done, frozen at `15fc467b5eadfd5f3509158886f7a9e36a11382b`. Recovery step 2 now hands
  the read-back and safe-rebind duty to the outer controlling Agent (session + anchor named in
  the reply) and calls the no-wake-source case **blocked** with a resume entry point; the
  carrier bullet hands over an unverified binding instead of only recording it; `host-startup.md`
  gained a numbered step for the receiving side ("Take back what the Host hands you"; a blocked
  Host stays blocked until the outer Agent acts). Bytes freed from non-pinned prose only:
  dispatch reference 8174 B, host-startup 6769 B of an unchanged 8192 B budget;
  `render-skills.py --check` PASS. New suite test pins the wording (4/4 tests, 34 checks) and the
  Issue #65 pinned sentences still pass (13/13); `./scripts/validate.sh` EXIT=0
  (`evidence/validate-handoff.log`). Live scenario (`evidence/live-handoff-2026-09-18.md`): sole
  unbound worker with a task in flight and no other event source — the Host answered "I am
  BLOCKED" with the resume entry point, refused to treat the heartbeat write as a wake-up, kept
  the in-flight work, and its event log recorded zero worker events for that worker's completed
  turn. Exact stops, no residue, other runs untouched. No push, no finalize.

## 8. Put the unbound-worker recovery back inside the Runner (architecture correction)
- item: The confirmed four-layer boundary makes the `15fc467` outward hand-off wrong as the normal
  path: ZCode schedules its own workers through Project Runner, and the delegating Agent must not
  take over read/rebind per worker. Minimal correction: recover internally along existing
  operations — evaluate reusing the bounded `wait`/`observe` to read the in-flight result, then
  safe `stop`/`start` rebinding — as a recovery exception, not the ordinary event wait; no timer,
  no polling layer, no hot rebind API, nothing cancelled; report an exception only when internal
  recovery genuinely cannot complete. Rebase onto `main` 464c4f9 and re-freeze.
- status: done
- dispatched: self, inline in `.kw/worktrees/issue-70`; output lands in the two orchestrator
  reference templates and their rendered copies, `docs/zcode-host.md`,
  `tests/contract/test-issue-70-binding-fact.py`, and `evidence/live-internal*`.
- result: done, frozen at `62a4ef2143efca5afa935ef3e2211a89ced64720` (rebased onto `main`
  464c4f9 first; the rebase replayed all three commits with no conflict and the pre-rebase tree
  was unchanged). Feasibility was checked in the source before writing guidance: `op_wait` is an
  existing bounded operation (condition-variable wait to a deadline, `prompt_timeout` on expiry) —
  no new mechanism needed, so nothing was invented. Recovery step 2 now recovers in-beat (bounded
  `wait --timeout`, or `observe`/`capture` when the turn already ended), step 3 rebinds by exact
  `stop`/`start`, and only an uncompletable recovery is reported as an exception with the decision
  needed; `host-startup.md` says exceptions reach the delegating Agent but per-worker handling does
  not. Budgets unchanged: dispatch reference 8185 B, host-startup 6666 B of 8192 B;
  `render-skills.py --check` PASS; Issue #65 pinned wording 13/13; Issue #70 suite 4/4, 36 checks;
  `./scripts/validate.sh` EXIT=0 (`evidence/validate-internal-recovery.log`). Live proof
  (`evidence/live-internal-2026-09-18.md`): a Host recovered its sole unbound worker itself in both
  legs — turn already ended (anchor read) and genuinely mid-turn (one `wait --timeout 300`,
  fingerprint-confirmed, `capture --since` the dispatch anchor, exact `stop`, `start --resume` with
  the binding, verified on the running holder) — and the restored loop then woke it on real worker
  events (3× staged/delivered/confirmed). Nothing cancelled, no residue, other runs untouched.
  Still unlived and only pinned by contract: the branch where the bounded read or the rebind fails.
  No push, no finalize.

## 9. Correct where the native resume id is read from (review comment 5728867190)
- item: The recovery step said `--resume <native session id>` comes from `session_meta`. For ZCode
  it does not: the translator reports `sess_*` in the session's `native_session_identity` update
  and nothing copies it into `session_meta`. Correct the recovery and startup guidance to source a
  real native id from that event, forbid `acp_session_id`/`--continue` substitutes, and verify
  from the raw event rather than the wording. Keep budgets and the Issue #65 pinned sentences.
- status: done
- dispatched: self, inline in `.kw/worktrees/issue-70`; output lands in the two orchestrator
  reference templates and their rendered copies, `docs/zcode-host.md`,
  `tests/contract/test-issue-70-binding-fact.py`, and `evidence/native-id/`.
- result: done, frozen at `4664f288af4827d36bb73d88b9f18e2eb690f014`. Source confirmed first
  (`kaola-zcode-acp.py:739` emits the update; `kaola-acp-holder.py` builds `session_meta` only
  from `session/new`/`session/load`/resume results) and then measured: a new ZCode session holds
  `acp_session_id zcode-1` with no native id in `session_meta`, the identity event carries
  `sess_fake1`, `capture --since 0` surfaces it, and `start --resume sess_fake1` reaches `ready`
  (`evidence/native-id/findings.md`, probe script kept). Guidance now sources the id from that
  event via `capture`, says no verified id means restart without history and say so, and forbids
  `acp_session_id`/`--continue`; startup carries the platform detail (lazy materialisation, other
  platforms may use `session_meta`). Budgets unchanged: 8189 B and 7218 B of 8192 B;
  `render-skills.py --check` PASS; Issue #65 pinned wording 13/13; Issue #70 suite 5/5, 48 checks;
  `./scripts/validate.sh` EXIT=0 (`evidence/validate-native-id.log`). No push, no finalize; the
  #74 documentation alignment waits for this freeze, and no old naming was propagated.

## 10. Bring the reference's worker examples under the issue-scoped naming rule
- item: Issue #72 (9db4673) fixed the naming contract `<platform>-<CODE>-i<ISSUE>-<purpose>` but
  flagged that `templates/orchestrator/references/zcode-host-dispatch.md.tmpl`, which this run
  owns, still demonstrates `codex-kaola-feature-a` in start/send/observe/capture and in the worker
  event's `session`/`event_id` — names a ZCode Host copies verbatim. Rename only in that reference
  and its rendered copy plus the matching check; the Host example name stays project-level until
  Issue #74 settles it. Budgets and the Issue #65 pinned sentences must hold.
- status: done
- dispatched: self, inline in `.kw/worktrees/issue-70`; output lands in
  `templates/orchestrator/references/zcode-host-dispatch.md.tmpl`, its rendered
  `skills/kaola-project-runner/references/` copy, and `tests/contract/test-issue-70-binding-fact.py`.
- result: done, frozen at `c75a19ac421ea86c15ee91a8b931a8dca00ba28f`. All seven occurrences now
  read `codex-KPR-i77-api` (start, send, observe, capture ×2, the event JSON's `session` and its
  `event_id`), and the rule is stated once beside them so the example reads as a pattern; the Host
  example stays `zcode-kaola-host`, recorded in the test as a deliberate exception pending #74.
  New check `test_worker_examples_use_issue_scoped_names` walks every `--session` example in the
  generated reference against `^[a-z0-9-]+-[A-Z]{2,6}-i\d+-[a-z0-9-]+$`, so a free-form name cannot
  come back. No behaviour, field or budget change: reference 8179 B of 8192 B,
  `render-skills.py --check` PASS, Issue #65 pinned wording 13/13, Issue #70 suite 6/6 with 54
  checks, `./scripts/validate.sh` EXIT=0 (`evidence/validate-issue-scoped-names.log`). Nothing
  outside this reference was renamed; no push, no finalize.

## 11. Rebase onto main 1f87666 and teach one worker example name
- item: The candidate's baseline was `main` 464c4f9; #72 has since landed (1f87666) with its own
  issue-scoped examples in `host-startup.md` and `issue-dispatch.md`. Rebase safely, keep the #70
  holder binding fact, the internal missed-binding recovery and every #72 naming rule, resolve any
  content conflict, and make sure the generated package teaches no stale session example.
- status: done
- dispatched: self, inline in `.kw/worktrees/issue-70`; the re-freeze lands on branch
  `workflow/issue-70`, the log in `evidence/validate-2e00a0f.log`.
- result: done, frozen at `2e00a0f37572df28fc9c13f41951d57a144f4bbb`. `git rebase main` replayed
  all six commits with no conflict; `render-skills.py --check` PASS immediately afterwards, which
  is what proves the generated surface still matches the merged templates. Both sides verified
  present: #72's "Issue-scoped names, one issue per run" section and `references/issue-dispatch.md`
  in the rendered main Skill, and #70's `heartbeat_host_known` / `native_session_identity` /
  bounded-`wait` recovery in the dispatch reference. One real inconsistency the rebase exposed and
  a seventh commit fixed: the package taught two worker examples (#72's `codex-KT-i274-parser` in
  host-startup, my `codex-KPR-i77-api` in the dispatch reference), so the dispatch reference now
  uses `codex-KT-i274-parser` everywhere — the whole orchestrator package has exactly one worker
  example name (10 occurrences) plus the project-level `zcode-kaola-host` awaiting #74. Generated
  docs carry no stale session example (`grep` over `skills/`, `hosts/`, `docs/` finds none).
  Budgets: dispatch reference 8180 B, host-startup 7479 B, main Skill 17292 B — all within
  `templates/budgets.json`, unchanged. Suites on the frozen SHA: Issue #70 6/6 with 54 checks,
  Issue #72 session naming 16/16, Issue #65 host contract 13/13, generated-Skill acceptance PASS,
  `./scripts/validate.sh` EXIT=0. No push, no finalize; no other worktree touched.
