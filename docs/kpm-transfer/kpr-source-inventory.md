# KPR source inventory for the KPM programme mapping

Version: 2026-10-07 (Git-versioned; this file is the single KPR-side input to the
two-repo responsibility/issue/evidence mapping). Owner of this file: the KPR Host
(original-capability owner). Programme lead: the KPM bridge
(`01a11660-1189-77d1-8639-40e896a4a025`, repo `/Users/ylmacstudio/Workspace/kaola-project-manager`),
which creates the new KPM issues with back-links; original tickets keep cross-references
explaining migrated vs retained responsibility. No ticket is blind-closed and no
implementation is copied: KPM reuses KPR/KW from the single original repositories through
versioned interfaces (no repo copy, vendor, or fork).

Facts discipline used below: `main` content ≠ release ≠ installed runtime. Release v0.9.1 =
content R `3de9f61a` + pin P `1112070e`. Everything merged after R is unreleased; the
installed main Skill payload still lacks `scripts/kaola-compact-recovery.py` (tracked as the
`maintenance-returned` batch:118 boundary, resolved only by a root-gated release + install).
Design drafts are separated from runtime evidence rows.

## A line — retained in KPR (original capability)

| Issue | Fixed at / evidence | Status | Target | Real dependencies | Interface contract | Acceptance owner | Next action |
|---|---|---|---|---|---|---|---|
| #269 CAD recurrence | `ab2624b6` + corrected `01f1bebb` (`docs/cad-recurrence-diagnosis-2026-10-07.md`) | diagnosis delivered; semantic cleanup incomplete; OPEN | KPR | consumer bridge facts only | none (observation/diagnosis) | root | complete semantic cleanup per issue |
| #271 dispatch entry coverage | `5cef759a` (D1/D2/S1/S3/S4, with #273); QA chain `1cfe7d51` + cursor correction `aa1c1444` | implementation + corrected evidence complete; OPEN | KPR | #273 fix rides the same commit | `execute`/`collect` plan+index schemas `kaola-dispatch-plan/1`, `kaola-dispatch-index/1`; collect binding needs `dispatch_event_cursor`+`prompt_fingerprint`+item repo | root (ruling pending) | await root ruling |
| #272 self-evolution design | `d584d32e` (docs; F1 bounded, F2–F3 bridge QA) | tracking proposal; OPEN | KPR | none | process docs only | root | await root ruling |
| #273 identity false-positive | `5cef759a` fix; suite `test-issue-273-list-identity.py` (9 tests, real entry); independent review `a4f0664d` | merged main, UNRELEASED; OPEN until release/install | KPR | none | list projection: `agent_alive` only from type-checked holder replies with `holder_identity=="verified"`; four-state identity + `holder_argv_anchor` | KPR Host per issue; release gate = root | release + install, then close per a4f0664d recommendations |
| #274 orchestrator package closure | `93662173`; suite `test-issue-274-package-closure.py` (4 tests); review `a4f0664d` | merged main, UNRELEASED; installed Skill still lacks the helper | KPR | none | `render-skills.py` copies `kaola-compact-recovery.py` into the orchestrator package (`dispatch.py` dynamic load) | KPR Host per issue; release gate = root | release + install; clears maintenance-returned batch:118 |
| #278 TMPDIR-independent ACP records | merge `bd58301b` | merged main, UNRELEASED; OPEN until release/install | KPR | none | session record root independent of caller TMPDIR (status/locate find a live Host) | KPR Host per issue; release gate = root | release + install, then close |
| #287 per-input settlement | candidate `73887f7a` on `workflow/issue-287` (worktree `.kw/worktrees/issue-287`) | Host-verified this beat: 9 suites green under worktree-only content-stage flip (379 tests OK); inherited-failure proof: candidate tests on clean main `0657e37f` fail exactly the 4 new tests, 0 others; CHANGELOG entry + `Seats: restart required` present | KPR | rebase base `0657e37f` (post-#286) already satisfied | `state update --kind alerts` per-input settlement: typed refusals `input-missing`/`input-unproven`/`conflict`/`expect-rev-required`; no tombstone relocation; recovery-only completion cannot claim unsent range | KPR Host | KW finalize (first action next beat), pre-push own-files diff check (protected dirty main files must not publish) |
| #288 preset unknown for start/send seats | none yet (no run) | OPEN, unscheduled | KPR | none | seat projection preset field for direct `start`/`send` seats | KPR Host | schedule fix run |
| #289 dead-holder exact stop | candidate `9735a6e8` on `workflow/issue-289` (worktree `.kw/worktrees/issue-289`) | candidate present, Host verification pending; workers stopped at the 19:15 pause (all stop=true exit0 residual[]) | KPR | rebase after #287 lands (original acceptance) | foreign `--expected-holder-instance-id` on a dead holder refused (`holder_instance_mismatch` S3 event); matching id unchanged; `--force` decision documented (a proposed behavior change is HUMAN_DECISION_REQUIRED) | KPR Host | rebase onto post-#287 main, verify per acceptance, finalize |
| #290 multi-index retire | none yet (no run) | OPEN, unscheduled | KPR | none | `state retire` accepts a dispatch spanning two execute indices (today single `--index`) | KPR Host | schedule fix run; unblocks the `kpr-ddd-component` task retire |

## B line — migrated to KPM (composition layer); originals and evidence stay here

| Issue / artifact | Fixed at / evidence | Status | Target | Real dependencies | Interface contract | Acceptance owner | Next action |
|---|---|---|---|---|---|---|---|
| #275 core extraction (P1) | slice 1 characterization contracts merged `9c88c0ef` (archive bundle-275); design `docs/designs/modular-core-2026-10-07/migration.md` in set `889f12bb` + tail `85d84525` | slice 1 done; code-motion slices remain; OPEN | KPM (composition); characterization contracts are KPR-owned evidence | was gated on #286/#287; re-plan by KPM | minimal core (identity + process facts + atomic state + contract registry) as an internal package; versioned reuse from the single repo | root, via KPM phase review | KPM maps and re-stages; no KPR dispatch |
| #276 P2 gates / P3 C6 | P2: worktree `workflow/issue-276-p2-gates` @`4751d9aa`, 31 dirty paths (worker `f8c0c922` stopped exactly); P3: worktree `issue-276` @`70892471`, 9 dirty paths (worker `b211fb4c` stopped exactly) | IN PLACE, unmerged, unpushed; preserved verbatim | classification pending: original-capability fix vs KPM composition layer (KPM bridge leads) | none active (workers stopped) | P2: render findings classified per class, pure length as dev advisory, pin/drift/closure/identity/route keep blocking. P3: recovery-input queue-when-absent + deployment-isolation regression | root, via KPM mapping | classify, then either land here as original-capacity fix or KPM adopts; no code moves before classification |
| #277 P4 KW read-only index (P5 remaining) | merged `21ec9a37`; #277 OPEN for P5 | P4 done+archived; P5 (lease/event semantics) remains | P4 evidence KPR; P5 → KPM | KW repo read-only | read-only reader reconciling `computeCodeTreeHash` vs `computeLandableTreeDigest`; writes nothing; typed absent/unsupported | root, via KPM phase review | KPM decides P5 staging; KW-side gaps stay tracked in the KW repo |
| #291 lifecycle contract | design comment `6035861090` (3 open questions: Host-mode route-through vs bypass receipt; lock scope; task-stage table timing) | design only; root six-item revision undelivered; Fable not started | KPM (design); original-capability contract parts may return as KPR issues after mapping | #288/#289 identity semantics (A line) | minimal lifecycle contract for resource/duty-holding components (seat lease, admission boundary, transactional project-scope admission, reconciliation) | root (dot reviews first), then bounded Fable | KPM bridge picks up the design thread; KPR supplies #288/#289 semantics when they land |

## DDD line — closed in KPR; continuation belongs to KPM

| Issue / artifact | Fixed at / evidence | Status | Target | Acceptance owner |
|---|---|---|---|---|
| #279 method + complements | corpus `210b712e` + `9d8de351`; integration `41b12e85` (§6b counterexamples; the standalone duplicate carried by `69c8c539` was dropped at `cdc29e69`); root-accepted baseline `f4accb11` (Fable CHANGES-REQUIRED→PASS preserved) | accepted baseline; issue OPEN pending closure | KPR (doc design); new-design continuation → KPM | root |
| #280–#285 phases | merged+closed; last `0657e37f`; design rev2 `8b3779c9`; runtime evidence `test-ddd-pack.py` (29 tests) | done | optional component `kaola-ddd/1`, KPR-owned, uninstallable, never a B0 precondition | KPR Host (done) |
| #270 research parent | corpus `docs/research/` (14 pinned worker originals + Fable reviews `59b82b39`, `cbfd92dd`) | breadth complete; OPEN | KPR | root (final joint review after root corpus analysis) |

## Runtime / release boundary facts (evidence, not design)

- Release v0.9.1: content R `3de9f61a`, pin P `1112070e`, tag `v0.9.1`. Seats: restart required per CHANGELOG.
- `main` ahead of R and pushed: `5cef759a`, `93662173`, `bd58301b`, DDD merges, archives, `69c8c539` (AGENTS KPM-transfer supersession), `cdc29e69` (duplicate drop). None of this is released or installed.
- Installed main Skill payload (`~/.agents`, `~/.claude`, `~/.codex` copies) lacks `scripts/kaola-compact-recovery.py` → the `maintenance-returned` alert batch:118 stays open until a root-gated release + install; not a KPM dependency.
- Protected owner files dirty on main (`hosts/grok-bot/INSTALL.md`, `bridge.json`, `kaola-delegator.md`, `templates/grok-bot/accepted-revision.json` family): never published by KPR runs; every finalize keeps the pre-push own-files diff check and drops mirrored protected paths pre-push (precedent `774ff7a6`).
- Live seats: zero verified at the 2026-10-07 handover beat (fresh all-platform sweep; the 19:15 pause had exactly stopped Host + 4 workers).
- Supervision: dot's existing hourly heartbeat covers both canonical locators (KPR + KPM); no new or changed timer; no cross-repo global stop-and-wait; bottom-layer gaps are tracked in their original repo.
