# Issue #68 — heartbeat carries only the current effective constraints

Goal: make the heartbeat an explicit current-effective-working-instruction snapshot on every host —
latest quota/priority/constraints only, a user-confirmed change re-planned in the same beat,
per-beat subtraction of obsolete project messages, in-flight locators and unfinished close-out
duties preserved, history left in the existing records. Minimal prompt improvement only: no schema,
no quota ledger, no scheduler, no cleanup script, no retry or auto-cancel mechanism; budgets not
raised; grok-golden frozen; skills/ and hosts/ only via the renderer.

Authority: Issue #68 body + issuecomment-5726132231 (terminology is final and outranks the body).

---

## 1. Freeze scope and conflict surface
- item: Read #68 body and comment 5726132231, the live baseline, the byte headroom, and the #65
  candidate's footprint on the same files, so the change lands where it does not fight #65.
- status: done
- dispatched: self (inline; read-only inspection of main 039c278 and read-only `git show`/`git diff`
  of workflow/issue-65 — no checkout, no merge, no write outside this run)
- result: Baseline main 039c278, clean, in sync with origin/main. Budget headroom is the binding
  constraint: templates/budgets.json main_skill_bytes=17408 and the rendered
  skills/kaola-project-runner/SKILL.md is 17281 bytes (127 free); reference_bytes=8192 and the
  rendered references/heartbeat-skeleton.md is 3324 bytes (~4.8 KB free). #65 (tip 4b8168c) rewrites
  the Hosts paragraph, progressive disclosure, Heartbeat paragraph 2, loop steps 1 and 5, and
  Dispatch notes of templates/orchestrator/SKILL.md.tmpl, appends three suites to the
  scripts/validate.sh arrays, and edits docs/zcode-host.md + docs/api.md — but does NOT touch
  templates/orchestrator/references/heartbeat-skeleton.txt at all, and does not change budgets.json.
  Therefore: carry the operational detail in heartbeat-skeleton.txt (zero overlap with #65) and keep
  the SKILL.md.tmpl edit inside Heartbeat paragraph 1 only (also untouched by #65), within the 127
  free bytes. Note #65 is based on a pre-#66 main, so its rendered sizes (SKILL.md 17289,
  heartbeat-skeleton.md 3117) will move when it integrates 039c278.

## 2. Implement the snapshot / subtraction / terminology change
- item: In templates/orchestrator/references/heartbeat-skeleton.txt and the `## Heartbeat`
  paragraph of templates/orchestrator/SKILL.md.tmpl, state the per-host heartbeat definition,
  the current-snapshot (not change-log) rule, immediate effect of a user-confirmed quota/priority/
  platform/model/concurrency change, the per-beat subtraction keep/drop lists, and the in-flight
  protection; scope the `.kaola/heartbeat-prompt.json` body-field guidance to the ZCode Host carrier
  it belongs to, leaving Codex and Grok Bot on their own existing carriers. Re-render with
  ./scripts/render-skills.py --write. No hand edits under skills/ or hosts/.
- status: done
- dispatched: self (inline, this Claude Code session; no sub-agent). Output lands on branch
  workflow/issue-68 in /Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner/.kw/worktrees/issue-68
  as edits to templates/orchestrator/references/heartbeat-skeleton.txt and
  templates/orchestrator/SKILL.md.tmpl plus the renderer-produced
  skills/kaola-project-runner/{SKILL.md,references/heartbeat-skeleton.md}.
- result: Landed on workflow/issue-68 (uncommitted at this point, 4 files):
  templates/orchestrator/references/heartbeat-skeleton.txt now opens with the per-host heartbeat
  definition (Codex/Grok Bot = delivered by their own timer system, ZCode Host = delivered on each
  worker return or existing worker event, carriers stay host-native, no shared path/schema, no timer
  added to ZCode, no event trigger forced on Codex/Grok Bot) and the current-effective-snapshot rule;
  the constraint header now carries quota beside CLI/model/concurrency with the user's own unit and
  an explicit "do not fuse concurrency, account quota and token budget into one number"; step 1 makes
  a user-confirmed quota/priority/platform/model/concurrency change take effect and re-plan in the
  same beat; step 2 states that platform failure or measured exhaustion is evidence only and that a
  lowered quota does not cancel in-flight work, whose locator and remaining close-out duty are kept;
  step 7 becomes the write-back subtraction rule with explicit drop and keep lists, the
  no-two-contradictory-quotas invariant, "removal from the heartbeat is not deleting evidence and does
  not rewrite a done Mission result", and per-host carriers — the #66 `.kaola/heartbeat-prompt.json`
  `body`-field guidance preserved verbatim but scoped to the ZCode Host carrier it belongs to, Codex
  and Grok Bot on their own existing timer-prompt carriers, and no new schema/ledger/scheduler/cleanup
  script. templates/orchestrator/SKILL.md.tmpl carries the same contract in short form in the first
  `## Heartbeat` paragraph. Rendered with ./scripts/render-skills.py --write (exit 0) and re-checked
  (exit 0, "budgets OK"). Budgets untouched: SKILL.md 17281 -> 17405 B against main_skill_bytes 17408
  (3 B free — flagged for integration), heartbeat-skeleton.md 3324 -> 5153 B against reference_bytes
  8192. Only those two templates and their two rendered products changed; grok-golden untouched, no
  hand edit under skills/ or hosts/.

## 3. Scenario self-verification
- item: Build at least three real before -> compacted-snapshot -> next-action scenarios (quota
  exhausted with user-approved platform substitution; priority/quota raised and lowered; obsolete
  project messages cleared while an in-flight locator and an unfinished close-out duty survive) and
  a contract suite that checks those behavioral invariants on the produced snapshots — including
  negative snapshots it must reject — not only keyword presence in the template. Single-worker
  self-verification; anything not executed is marked as such.
- status: done
- dispatched: self (inline, this Claude Code session; no sub-agent). Output lands as
  tests/contract/test-issue-68-heartbeat-snapshot.py plus its scripts/validate.sh registration on
  branch workflow/issue-68, and the readable scenario walk-through at
  kaola-workflow/issue-68/evidence/heartbeat-snapshot-scenarios.md.
- result: tests/contract/test-issue-68-heartbeat-snapshot.py (10 tests, exit 0), registered in
  scripts/validate.sh next to test-issue-41-orchestrator.py in both the all-list and lane A.
  Three scenarios, each carrying a real `before` prompt, the human event, the compacted `after`
  and the beat's `next_action`: (1) Codex quota exhausted with a user-approved swap to Claude Code
  x1; (2) concurrency raised to 4 last beat and lowered to 2 this beat with three workers live;
  (3) an ordinary beat that clears duplicated merge narration, a transient tmux failure, a
  superseded plan and a thrice-repeated project description. Nine executable invariants run over
  each produced snapshot (superseded values gone, current values present, no contradictory pair,
  in-flight locators kept, unfinished duties kept, inert history gone, recovery pointer kept, acts
  under the new constraint in this beat, no unauthorized platform swap or cancel). Eight wrong
  snapshots must be rejected by those same invariants and two of them exposed real fixture bugs
  while writing them (the correct next action says "不 stop" and "不丢弃", so the forbidden-move
  patterns needed a negation guard to avoid matching their own denial); a third test replays each
  `before` as its own `after` and requires it to fail, so the checks cannot be vacuous. The
  readable walk-through is kaola-workflow/issue-68/evidence/heartbeat-snapshot-scenarios.md, which
  also states what was NOT executed: no live tmux/CLI smoke (prompt text only, no transport or
  script behavior changed) and no real host driven through a real beat.

## 4. Exact validation and frozen candidate
- item: Run ./scripts/render-skills.py --check and ./scripts/validate.sh, record exact exit codes and
  the budget numbers, freeze the candidate SHA on workflow/issue-68, and write the minimal
  meaning-preserving merge plan for the #65/#66 overlap. Stop there: no finalize, merge, push, issue
  close, release, or global install until the outer coordinator accepts.
- status: done
- dispatched: self (inline, this Claude Code session; no sub-agent). Exit codes and log land in
  kaola-workflow/issue-68/evidence/; the conflict plan lands in
  kaola-workflow/issue-68/evidence/integration-with-issue-65.md.
- result: Candidate FROZEN at 54bc864 on branch workflow/issue-68 (single commit on top of main
  039c278; 7 files, +476/-32). ./scripts/render-skills.py --check exit 0 ("budgets OK");
  ./scripts/validate.sh exit 0 (full log: evidence/validate-54bc864.log). Budgets unchanged:
  SKILL.md 17297 B <= 17408, heartbeat-skeleton.md 5153 B <= 8192; templates/grok-golden byte-identical
  to main; skills/ and hosts/ produced only by the renderer.
  Two real failures were found and fixed during this mission rather than worked around:
  (a) test-issue-49-grok-bot-host's bridge-invariance test appends a 59-byte probe to the
  orchestrator template and requires the render to succeed, so the first draft at 17405 B busted
  the budget — resolved by removing the Hosts-section enumeration of what a beat writes into the
  ZCode carrier, which the skeleton's new subtraction rule now owns, not by raising the budget;
  (b) test-zcode-heartbeat-contract asserted the shared skeleton contains no "ZCode" wording, a
  proxy that the user's final terminology makes wrong — replaced by the invariant it was protecting
  (the carrier is specified once: the KAOLA_ACP_HEARTBEAT_HOST mechanism only in the Skill, the
  .kaola/heartbeat-prompt.json path exactly once in the skeleton, scoped to the ZCode Host).
  Integration surface vs the live #65 run, computed read-only with `git merge-tree --write-tree`
  (no ref, branch or worktree touched): exactly one conflicting hunk, the `### Hosts` paragraph of
  templates/orchestrator/SKILL.md.tmpl, plus its generated product. Minimal meaning-preserving
  resolution is to take #65's side of that paragraph verbatim and re-render — #65's own rewrite
  already drops the same enumeration, so nothing of #68 is lost. scripts/validate.sh auto-merges
  clean because the #68 suite was registered mid-array instead of appended. Projected merged
  SKILL.md is 17337 B, which leaves only 12 bytes of slack under the effective 17349 B ceiling that
  the #49 probe imposes — flagged for the integrator in
  evidence/integration-with-issue-65.md. NOT DONE by design: finalize, merge, push, issue close,
  release, global install; and the final integration bytes are re-verified only after the outer
  coordinator has safely synchronized #65 with main.

---

## Record correction (2026-09-18, outer review round 1)

Missions 2 and 3 were finished and their `result` written, but their `status` was left at
`in-flight` while the round-1 report claimed "4 done". The outer coordinator caught it. Only the two
`status` lines were corrected to `done`; both recorded results are unchanged and remain immutable.
The report was wrong about the record, not about the work.

Outer review outcome on candidate 54bc864: prompt diff read, direction and minimalism accepted; the
hand-written `after`/`next_action` constants are not behavioral evidence. Missions 5 and 6 below
carry the correction. Also recorded: #65 has been accepted by the outer and is finalizing, so its
work must not be merged here, and the `### Hosts` integration conflict is not dispatched until the
outer has the user's confirmation.

## 5. Live ACP validation sentinel
- item: Run one small isolated ACP validation session (a validation sentinel, not an implementation
  or review worker) on Claude's default preset — Opus high, Fast off — against an isolated scratch
  repo that touches no real project, account quota or scheduler. Give it the candidate Skill and
  skeleton to read plus the three original `before` heartbeats and their user-change events, and
  ask it for the current effective heartbeat and the immediate next step. Withhold every S*_AFTER
  and S*_NEXT answer. Then check its own raw output: superseded quota and inert history dropped,
  in-flight locators and unfinished close-out kept, no unauthorized platform swap or cancel, and
  Codex/Grok Bot timer delivery distinguished from ZCode worker-event delivery. One session, one
  turn, three scenarios, no new harness; exact-session stop afterwards.
- status: done
- dispatched: self (inline, this Claude Code session; no sub-agent). Transport is the repo's own
  claude-code-kaola-project-runner Skill over ACP. Session name kaola-issue68-heartbeat-sentinel,
  --repo an isolated scratch checkout under /tmp holding only a copy of the candidate
  skills/kaola-project-runner/{SKILL.md,references/heartbeat-skeleton.md} and the scenario input
  file. Full prompt, full raw reply, the session's own read evidence and the exact stop receipt land
  under kaola-workflow/issue-68/evidence/sentinel/.
- result: PASS with two reported divergences. Session kaola-issue68-heartbeat-sentinel over ACP,
  requested Opus High from runner-default and resolved opus/effort high/Fast off, claude 2.1.272,
  bridge pin 6c20f28, --repo /private/tmp/kw68-sentinel (scratch: only the two candidate files and
  the scenario input; files_changed 0, no heartbeat registered, no worker dispatched, no account or
  scheduler action). One turn: mutation_status completed, stop_reason end_turn, 153 s, 4 tool calls
  0 failed; the reply ends with the KW68-SENTINEL-DONE marker. Real read evidence in the ACP event
  log: it cat'd candidate/heartbeat-skeleton.md, candidate/kaola-project-runner-SKILL.md and
  scenarios.md, whose sha256 match the candidate's rendered files byte for byte. Its own 18 048-byte
  output drops every superseded value (Codex x2 + 20% quota, Claude Code 未授权, 并发 4), keeps
  Codex x3 / 并发 2 / token 预算 8M as three separate numbers, drops the 429 retry, the Cursor
  mismatch, plan A, plan B, the tmux reconnect and the triplicated project description, keeps every
  in-flight session/worktree/Issue locator and every unfinished duty, switches platform only where
  the user authorized it, re-plans in the same beat ("本拍立即按并发 2 执行"), and refuses to cancel
  in-flight work to fit a lowered ceiling. Read cold, it also answered the terminology question
  correctly — Codex timer, Grok Bot Routine, ZCode event-driven — and stated "不是同一个文件实现"
  unprompted. Two divergences from my hand-written fixtures are recorded rather than hidden: it kept
  并发上限 2 in scenario 1 where my constant said 并发 1 (the sentinel is right; the user replaced the
  platform, not the concurrency), and it would stop the idle Codex session in scenario 1 after
  verifying the output landed and the close-out duty was handed over, where my constant said keep.
  Exact stop afterwards: stopped true, agent_exit_code 0, residual_pids [], no process or tmux
  session by that name remains. Full input, full raw reply, receipts and event log under
  kaola-workflow/issue-68/evidence/sentinel/ with 00-findings.md. Still single-worker
  self-verification, stated as such in the findings.

## 6. Reduce the hand-written suite to honest scenario evidence
- item: The 418-line tests/contract/test-issue-68-heartbeat-snapshot.py asserts over constants this
  worker wrote, so it cannot stand as behavioral acceptance. Cut it down to the part that really is a
  contract check — the generated Skill and skeleton state the obligation — and move the three
  scenarios to readable evidence, with the live sentinel output as the behavioral record. Do not
  grow test engineering.
- dispatched: self (inline, this Claude Code session; no sub-agent). Output is the reduced
  tests/contract/test-issue-68-heartbeat-snapshot.py on branch workflow/issue-68 and the updated
  scenario evidence under kaola-workflow/issue-68/evidence/.
- status: done
- result: 418 lines -> 98, 10 tests -> 7, commit 230ca83. Everything that asserted over hand-written
  after/next_action constants is gone: the Snapshot class, the nine invariant functions, the three
  scenario constant blocks, the eight wrong variants and the three behavior tests. What remains is
  the contract check proper — the rendered Skill and skeleton state the per-host definition, the
  per-beat drop and keep lists, the same-beat effect of a confirmed change, the in-flight
  protection, the three separate quota kinds, the host-native carriers with no invented mechanism,
  and the unraised budgets. The scenarios moved to kaola-workflow/issue-68/evidence/
  heartbeat-snapshot-scenarios.md, rewritten to present them as design inputs and to point at the
  sentinel output as the behavioral record, with the earlier over-claim withdrawn in its own words.
  Re-validated after the cut: render-skills.py --check exit 0 ("budgets OK"), ./scripts/validate.sh
  exit 0 (evidence/validate-230ca83.log).
  State change recorded mid-mission: main moved from 039c278 to 90842e7 because #65 was accepted and
  finalized while this mission ran. `git diff main..HEAD` is therefore no longer this run's change
  set; measured from the merge base 039c278 it is 7 files, +156/-32. The conflict recomputed against
  the new main is unchanged — the same single `### Hosts` hunk in templates/orchestrator/
  SKILL.md.tmpl plus its generated product, projection still 17337 B — and the branch was
  deliberately NOT updated onto the new main, because the outer coordinator holds that resolution
  until the user confirms it.

## Record correction 2 (2026-09-18, same session)

The mission 2/3 status slip recurred on missions 5 and 6: both results were written while the
`status` line still said `in-flight`, and mission 6 briefly carried two status lines. Corrected to a
single `done` each; no recorded result was altered. The cause is writing `result` and `status` in
separate edits — from here the two are written in one edit.

## 7. Integrate main 68845bd into the candidate
- item: The outer coordinator has confirmed the resolution and authorized it. From this run's own
  worktree, `git merge` the current main `68845bd` (which now contains both #65 and #66) into
  `workflow/issue-68` — a merge, never a rebase, no history rewrite. Resolve the one `### Hosts`
  conflict in templates/orchestrator/SKILL.md.tmpl by taking the accepted #65 Host paragraph, while
  keeping #68's own `## Heartbeat` paragraph and the skeleton's new subtraction rules; keep the
  references layered so #65's and #66's behavior and authorization boundaries survive intact.
  Generated files come only from ./scripts/render-skills.py --write — grok-golden stays frozen and
  templates/budgets.json is not raised; if the #49 probe's effective ceiling binds, compress real
  duplicated wording instead. Then re-run --check and ./scripts/validate.sh, record exact exit
  codes, freeze the integrated SHA, and hand the real integration diff plus evidence to the outer
  coordinator. No finalize, push, or issue close without its acceptance.
- status: done
- dispatched: self (inline, this Claude Code session; no sub-agent — the single authorized
  implementer). Output lands as the merge commit on branch workflow/issue-68 in
  /Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner/.kw/worktrees/issue-68, with the
  exit codes, validate log and integration diff under kaola-workflow/issue-68/evidence/.
- result: Integrated candidate FROZEN at merge commit `19eda62` on branch workflow/issue-68, parents
  230ca83 (the #68 candidate) + 68845bd (main, which already contains #65 and #66). A merge, not a
  rebase: no commit on either side was rewritten, and 230ca83 remains reachable as the first parent.
  Conflicts were exactly the one predicted in mission 4 — the `### Hosts` paragraph of
  templates/orchestrator/SKILL.md.tmpl plus its generated product — and nothing else; scripts/validate.sh
  auto-merged clean as designed. Resolved by taking main's (#65's accepted) `### Hosts` text verbatim,
  2141 B replacing #68's 2048 B, which loses nothing of #68: its only edit there was trimming the
  per-beat enumeration and #65's own rewrite already drops it. #65/#66 behavior and authorization
  boundaries survive intact in that paragraph — the KAOLA_ACP_HEARTBEAT_HOST receipt check,
  `send --no-wait` with the dispatch_event_cursor anchor, "end the turn normally — that is the wait",
  the references/zcode-host-dispatch.md pointer, and the bridge-host locator attestation with its
  per-target isolation. #68's own scope merged clean and is unchanged: the `## Heartbeat` paragraph,
  the Defaults Heartbeat row, and the whole subtraction rule in
  templates/orchestrator/references/heartbeat-skeleton.txt. The generated
  skills/kaola-project-runner/SKILL.md was produced only by ./scripts/render-skills.py --write (exit 0),
  never hand-resolved.
  Measured on the new main, this run's contribution is the same 7 files, +152/−28 (it was +156/−32
  against 039c278; the 4-line delta is precisely the Hosts hunk now coming from #65).
  Exact validation on the integrated tree: ./scripts/render-skills.py --check exit **0**
  ("PASS … budgets OK"); ./scripts/validate.sh exit **0**, 22 suites OK, full log
  evidence/validate-19eda62.log.
  One intermediate failure is recorded rather than hidden: run before the merge was committed,
  validate.sh exited **2** on its final `git diff --check --cached` gate with
  `kaola-workflow/archive/issue-65/mission-list.md:252: new blank line at EOF`, while all 22 suites
  still passed. Cause is the uncommitted merge state — that blank line is pre-existing in #65's
  archive as committed on main, and --cached saw the whole incoming archive as staged additions. It is
  another run's archive, so it was NOT edited; committing the merge cleared the gate and the clean-tree
  re-run is the exit 0 above.
  Budgets: templates/budgets.json unchanged (main_skill_bytes 17408) and templates/grok-golden
  byte-identical to main. Rendered SKILL.md is 17337 B — exactly the mission-4 projection — against the
  17349 B effective ceiling the #49 bridge probe imposes, i.e. 12 B of slack. That slack was verified,
  not assumed: tests/contract/test-issue-49-grok-bot-host.py was run directly on the integrated tree
  (42 tests, exit 0) and again inside the full suite. No wording was compressed because none needed to
  be; the two trim candidates named in evidence/integration-with-issue-65.md stay documented for
  whoever next grows the main Skill.
  Boundaries held: `git diff main -- templates/grok-golden templates/budgets.json hosts/` is empty and
  `git diff --name-only main -- kaola-workflow/` is empty, so no other run's archive, no accepted
  checkout, no sibling worktree and no global config was touched; the worktree is clean at 19eda62.
  Evidence: evidence/integration-diff-19eda62.patch (full diff vs main),
  evidence/merge-commit-19eda62.txt, evidence/validate-19eda62.log, and the "Integration performed"
  section appended to evidence/integration-with-issue-65.md.
  NOT DONE, awaiting the outer coordinator's acceptance: finalize, push, issue close, release, global
  install. Nothing was pushed and no remote was contacted.
