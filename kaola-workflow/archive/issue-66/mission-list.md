# Issue #66 — separate ordinary-Worker and ZCode-Orchestrator startup flows, with outer startup acceptance and lifecycle supervision

Run: issue-66 · branch `workflow/issue-66` · worktree
`/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner/.kw/worktrees/issue-66`
Baseline: main `bb6d740` (v0.3.5). Minimalism is an owner hard boundary: reuse existing
start/send/observe/capture/stop + Workflow; no role parameter, launcher, state machine, config
system, scheduler, persistent ledger, or approval gate.
Read-only cross-reference: Issue #65 frozen candidate `b62f957` (branch `workflow/issue-65`,
NOT merged, awaiting outer acceptance). Never modified, merged, or cherry-picked here.

## 1. Scope statement: minimal change surface and reused capabilities
- item: From the #66 body + the owner's minimalism comment, main's real behavior, and a read-only
  look at #65's candidate, state in a few lines which files change and which existing capabilities
  carry the contract; hand it to the outer Agent before implementing.
- status: done
- dispatched: self; landed in this file plus the session report to the outer Agent.
- result: 5 files: `templates/orchestrator/SKILL.md.tmpl` (two short entry points),
  one new on-demand reference `templates/orchestrator/references/host-startup.md`,
  `templates/orchestrator/references/heartbeat-skeleton.txt` (name the `body` field),
  `scripts/kaola-acp-holder.py` (`_heartbeat_payload` error visibility only),
  one new contract test — plus generated `skills/**` from `render-skills.py --write` and docs.
  Reused: `start` + `KAOLA_ACP_HEARTBEAT_HOST` + its `heartbeat_host` start-receipt echo,
  `send --no-wait` (`in_progress`, `prompt_fingerprint`, `dispatch_event_cursor`), staged/delivered/
  confirmed worker events, `observe`/`capture --since`, exact `stop`, Kaola-Workflow Mission List.

## 2. Two entry points in the main Skill, plus one on-demand Orchestrator startup reference
- status: done
- dispatched: self; landed in `templates/orchestrator/SKILL.md.tmpl` and
  `templates/orchestrator/references/host-startup.md.tmpl`, regenerated into `skills/`.
- result: commit 1ec663b. Main Skill gained "## Two entry points" (ordinary worker / Orchestrator)
  linking the new reference, paid for by six redundancy trims in sections #65 does not touch;
  rendered main Skill 17297 B of 17408 (111 B headroom), reference 5833 B of 8192.
  `render-skills.py --check`: PASS, budgets OK.
- item: Main Skill gets two short entry points (ordinary Worker / Orchestrator) that route to the
  right flow and no more; the startup-and-supervision procedure lives in one on-demand reference
  that extends #65's Host-reference idea instead of duplicating its per-beat dispatch mechanics.
  Ordinary Worker keeps zero new obligations. Main Skill must stay inside the 17408 B budget
  (17088 B used on baseline: 320 B headroom) and the reference inside 8192 B, so the entry points
  are paid for by trimming redundancy in sections #65 does not touch.

## 3. Evidenced runtime error visibility for the heartbeat prompt body
- status: done
- dispatched: self; `scripts/kaola-acp-holder.py` plus the skeleton reference, regenerated.
- result: commit 1ec663b. New pure `heartbeat_body_defect()` classifies absent (no defect) vs
  unreadable / invalid JSON / non-object / missing `body` (naming the fields actually present) /
  non-string / empty; `_heartbeat_payload` reports it in the delivered prompt
  ("present but UNUSABLE - <defect>") and in `heartbeat_body_error` on the
  `worker_event_delivered` log entry. Delivery is not blocked. The skeleton now names the `body`
  field. No receipt field was removed or renamed.
- item: `_heartbeat_payload` currently collapses "no file" and "file present but `body` missing /
  wrong type / empty / unparseable" into the same "none maintained" text, which is what let the
  audited Host believe its maintained prompt was in effect while it had written `prompt`. Report the
  actual defect (path, what is wrong, keys present) in the delivered notification and in the
  holder's `worker_event_delivered` log; the skeleton reference names the `body` field. No new gate:
  delivery still happens.

## 4. Minimal contract test for the evidenced failure modes, then full validate
- status: done
- dispatched: self; two tests added to the existing
  `tests/contract/test-zcode-heartbeat-contract.py` harness (no new harness), then
  `./scripts/validate.sh` with raw output in `kaola-workflow/issue-66/evidence/`.
- result: PASS. `test-zcode-heartbeat-contract` 9/9 tests, 160 checks
  (`evidence/heartbeat-contract-2.txt`), including the two new ones:
  `test_issue_66_defective_prompt_file_reports_its_defect` (17 checks: the pure predicate over
  absent / invalid JSON / non-object / non-string / empty / wrong-field-name / valid, plus a full
  live-holder round trip proving the notification says "present but UNUSABLE", names the file and
  `"body"`, no longer claims the file is missing, never passes the mis-filed text off as the body,
  and logs `heartbeat_body_error`) and `test_issue_66_unarmed_worker_stays_ungated` (5 checks: no
  `heartbeat_host` key, blocking send still `turn_completed`, normal stop, no carrier event).
  Duplicate-event collapse, resume redelivery of unconfirmed events and the busy/idle staging paths
  are cited from the existing tests in the same file, not rebuilt. Full `./scripts/validate.sh`
  exit 0 twice: `evidence/validate-1.txt` (pre-doc-correction) and
  `evidence/validate-final.txt` on the frozen candidate e0586e4.
  `templates/grok-golden` and `templates/budgets.json` are byte-identical to the baseline.
- item: Reuse the existing `tests/contract/test-zcode-heartbeat-contract.py` harness style for the
  new failure modes (present-but-defective body is reported, not silently "not found"; an unarmed
  ordinary worker start carries no `heartbeat_host` and stays ungated) and cite the existing tests
  that already cover duplicate-event collapse and unconfirmed redelivery instead of rebuilding them.
  Then `render-skills.py --check` and `./scripts/validate.sh`; grok-golden and byte budgets frozen.

## 5. One real model-driven lifecycle closed loop on isolated sentinel sessions
- status: done
- dispatched: self; live sentinel sessions `zcode-i66-host` (ZCode/GLM-5.3) and `codex-i66-w1`
  (Codex) on the ignored sandbox project `.kw/issue-66-live/project`, candidate scripts only, no
  global install. Output in `kaola-workflow/issue-66/evidence/live/` + `live-loop-2026-09-18.md`.
- result: PASS, full closed loop. Recover (`no-session` both names) -> Host start ready at the
  canonical root -> non-blocking handover -> real startup receipt that held before dispatch ->
  heartbeat `body` written before the first dispatch -> bound start with the echoed
  `heartbeat_host` -> `send --no-wait` -> natural `end_turn` -> four real worker events, two
  delivered while idle and two staged while the Host turn was active and delivered at the
  boundary, all `heartbeat_maintained: true` and each confirmed by the notification turn
  completing -> Host read the real delivery through the worker's own Skill and ran the plan's test
  command itself (5 passed) -> accepted -> plan criterion 7 added -> rework dispatch on a
  re-bound `--resume` start -> second delivery re-checked (7 passed) -> accepted -> worker
  exact-stopped twice (exit 0, no residue) -> outer Agent exact-stopped the Host after close-out
  (`stopped: true`, `residual_pids: []`, no `i66` process left). Two live findings were folded
  back into the reference in commit e0586e4.
- item: With short-lived, isolated owned sessions only (never VRPCadCore, no global install): start a
  named ZCode Host at a sandbox project root, hand it identity + plan + authorization, read its
  startup receipt and verify actual main-Skill loading from tool evidence, bind
  `KAOLA_ACP_HEARTBEAT_HOST` per worker start and check the receipt, dispatch `--no-wait`, let the
  Host end its turn naturally, have the worker finish while the Host is busy and while idle, read the
  real delivery through the worker's own Skill, send one rework round, accept, then exact-stop.
  Record raw outputs under `kaola-workflow/issue-66/evidence/`.

## 6. Documentation truth, candidate freeze, READY_FOR_REVIEW handback
- status: done
- dispatched: self; `docs/zcode-host.md` + `CHANGELOG.md` in commit e0586e4, final
  `./scripts/validate.sh` raw output at `kaola-workflow/issue-66/evidence/validate-final.txt`,
  handback in the session report.
- result: READY_FOR_REVIEW. Frozen candidate e0586e4 on `workflow/issue-66` (local only; no push,
  no merge, no finalize, no Issue closure, no release, no global install). 19 files, +1097/-175,
  of which 5 are hand-edited sources; the rest are generated `skills/**` plus docs.
  #65 integration points named in the handback.
- review round 1 (outer Agent, 2026-09-18, same mission, no new mission): two local corrections
  applied and the candidate re-frozen at 2da5f92 - the main Skill's dropped authorization
  sentences restored verbatim (17281 B of 17408) and the heartbeat prompt file read exactly once
  into `(body, defect)` with `OSError`/`UnicodeError`/JSON errors caught, closing the
  check-then-reread window. Focused regressions added to the same test
  (`test-zcode-heartbeat-contract` 9/9, 164 checks); the startup reference now prefers
  `dispatch_event_cursor` with the pre-dispatch `observe` cursor as the fallback; the live report
  now states which steps were explicitly prompted. Re-validation:
  `evidence/validate-final-2.txt`. Prior PASS evidence for the changed bytes is superseded by it.
- item: `docs/zcode-host.md` (and CHANGELOG/README where user-visible) state the real two-flow
  behavior and the new error receipt; freeze the candidate SHA; report minimal diff, raw test
  output locations, #65 integration points (`templates/orchestrator/SKILL.md.tmpl` and the Host
  reference are the shared surfaces), and anything unverified. No finalize/merge/push/close/release.
