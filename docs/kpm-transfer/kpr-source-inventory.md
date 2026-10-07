# KPR source inventory for the KPM programme mapping

Version: 2026-10-07 v3 (supersedes v2 `de26b31c`). Git-versioned; this file is the single
KPR-side input to the two-repo responsibility/issue/evidence mapping. Owner of this file:
the KPR Host. Programme lead: the KPM bridge (`01a11660-1189-77d1-8639-40e896a4a025`,
repo `/Users/ylmacstudio/Workspace/kaola-project-manager`), which will create the KPM issues
with back-links; original tickets keep cross-references marking migrated-out/stopped (never
"implemented"). No ticket is blind-closed and no implementation is copied. The
single-implementation constraint (no repo copy, vendor, or fork) stands; beyond that,
**no final migration mechanism is predetermined here**: KW updates are currently stopped,
how KPR and KW would incorporate any new architecture awaits KPM design confirmation, and
**nothing has actually been migrated yet**. No KPM issue numbers exist yet — reference the
KPM repo and bridge above instead of guessing them.

Scope of this revision (owner direction `Sentinel_64a7198f` / `f8a26d7b` and the final
boundary round): ALL KPR architecture-upgrade implementation is revoked in this repo —
including the earlier allowance for KPR/KW component-interface, lifecycle and
recovery-contract transformation. KPR executes only limited fixes, verification and release
closeout of pre-existing defects. P2/P3 results stay in place solely for KPM
classification; nothing architectural lands in this repo under any classification outcome.
KPR does not modify KW; KW updates are stopped and this inventory sets no future KW-change
path — any question of KW incorporation belongs to the pending KPM design confirmation.
No new KPR issues are created at all (not only architecture ones).

Facts discipline: `main` content ≠ release ≠ installed runtime. Release v0.9.1 = content R
`3de9f61a` + pin P `1112070e`. Everything merged after R is unreleased; the installed main
Skill payload still lacks `scripts/kaola-compact-recovery.py` (the `maintenance-returned`
batch:118 boundary, resolved only by a root-gated release + install). Design drafts are
separated from runtime evidence rows.

## A line — retained in KPR (pre-existing defect fixes, verification, release closeout only)

| Issue | Fixed at / evidence | Status | Real dependencies | Interface contract | Acceptance owner | Next action |
|---|---|---|---|---|---|---|
| #269 CAD recurrence | `ab2624b6` + corrected `01f1bebb` (`docs/cad-recurrence-diagnosis-2026-10-07.md`) | diagnosis delivered; semantic cleanup incomplete; OPEN | consumer bridge facts only | none (observation/diagnosis) | root | complete semantic cleanup per issue |
| #271 dispatch entry coverage | `5cef759a` (D1/D2/S1/S3/S4, with #273); QA chain `1cfe7d51` + cursor correction `aa1c1444` | implementation + corrected evidence complete; OPEN | #273 fix rides the same commit | `execute`/`collect` plan+index schemas `kaola-dispatch-plan/1`, `kaola-dispatch-index/1`; collect binding needs `dispatch_event_cursor`+`prompt_fingerprint`+item repo | root (ruling pending) | await root ruling |
| #272 self-evolution design | `d584d32e` (docs) | design proposal; no KPR implementation (revoked scope); a limited bug-fix scope is NOT claimed unless evidenced by existing acceptance | none | process docs only | root (classification pending) | design-transformation part migrates to KPM or awaits root classification; no new framework, no continued upgrade here on the old ticket |
| #273 identity false-positive | `5cef759a` fix; suite `test-issue-273-list-identity.py` (9 tests, real entry); independent review `a4f0664d` | merged main, UNRELEASED; OPEN until release/install | none | list projection: `agent_alive` only from type-checked holder replies with `holder_identity=="verified"`; four-state identity + `holder_argv_anchor` | KPR Host per issue; release gate = root | release + install, then close per a4f0664d recommendations |
| #274 orchestrator package closure | `93662173`; suite `test-issue-274-package-closure.py` (4 tests); review `a4f0664d` | merged main, UNRELEASED; installed Skill still lacks the helper | none | `render-skills.py` copies `kaola-compact-recovery.py` into the orchestrator package | KPR Host per issue; release gate = root | release + install; clears maintenance-returned batch:118 |
| #278 TMPDIR-independent ACP records | merge `bd58301b` | merged main, UNRELEASED; OPEN until release/install | none | session record root independent of caller TMPDIR | KPR Host per issue; release gate = root | release + install, then close |
| #287 per-input settlement | candidate `73887f7a` on `workflow/issue-287` (worktree `.kw/worktrees/issue-287`) | Host-verified 2026-10-07: 9 suites green under worktree-only content-stage flip (379 tests OK); inherited-failure proof: candidate tests on clean main `0657e37f` fail exactly the 4 new tests, 0 others; CHANGELOG entry + `Seats: restart required` present | rebase base `0657e37f` (post-#286) satisfied | `state update --kind alerts` per-input settlement: typed refusals `input-missing`/`input-unproven`/`conflict`/`expect-rev-required`; no tombstone relocation; recovery-only completion cannot claim unsent range | KPR Host | KW finalize (first action next beat), pre-push own-files diff check |
| #288 preset unknown for start/send seats | none yet (no run) | OPEN, unscheduled | none | seat projection preset field for direct `start`/`send` seats | KPR Host | schedule defect-fix run |
| #289 dead-holder exact stop | candidate `9735a6e8` on `workflow/issue-289` (worktree `.kw/worktrees/issue-289`) | candidate present; Host verification pending; worker stopped at the 19:15 pause (receipt: c9c4ae40 stop=true exit0 residual[]) | rebase after #287 lands (original acceptance) | foreign `--expected-holder-instance-id` on a dead holder refused (`holder_instance_mismatch` S3 event); matching id unchanged; `--force` decision documented (a proposed behavior change is HUMAN_DECISION_REQUIRED) | KPR Host | rebase onto post-#287 main, verify per acceptance, finalize |
| #290 multi-index retire | none yet (no run) | OPEN, unscheduled | none | `state retire` accepts a dispatch spanning two execute indices (today single `--index`) | KPR Host | schedule defect-fix run; unblocks the `kpr-ddd-component` task retire |

## B line — revoked in this repo; originals and evidence stay here for KPM

| Issue / artifact | Fixed at / evidence | Status | Real dependencies | Interface contract | Acceptance owner | Next action |
|---|---|---|---|---|---|---|
| #275 core extraction (P1) | slice 1 characterization contracts merged `9c88c0ef` (archive bundle-275); design `docs/designs/modular-core-2026-10-07/migration.md` in set `889f12bb` + tail `85d84525` | slice 1 done and retained as evidence; all further slices revoked here; OPEN, migrated out | none active | minimal core as an internal package — the interface/reuse mechanism itself is PENDING KPM design confirmation; only the single-implementation/no-copy constraint is fixed | root, via KPM | KPM re-stages after its design confirmation; no KPR dispatch; already-merged code is not reverted |
| #276 P2 gates / P3 C6 | P2: worktree `workflow/issue-276-p2-gates` @`4751d9aa`, 31 dirty paths (worker `f8c0c922` stopped, fresh receipt state=stopped); P3: worktree `issue-276` @`70892471`, 9 dirty paths (worker `b211fb4c` stopped, fresh receipt state=stopped) | IN PLACE, unmerged, unpushed, preserved verbatim; for KPM classification ONLY — no classification outcome lands architecture transformation in this repo | none active | P2: render findings classified per class, pure length as dev advisory, pin/drift/closure/identity/route keep blocking. P3: recovery-input queue-when-absent + deployment-isolation regression | root, via KPM | KPM classifies and adopts as it sees fit; KPR moves nothing |
| #277 P4 KW read-only index (P5 remaining) | merged `21ec9a37`; #277 OPEN for P5 | P4 done+archived (evidence); P5 revoked here | KW read-only usage only | read-only reader reconciling `computeCodeTreeHash` vs `computeLandableTreeDigest`; writes nothing; typed absent/unsupported | root, via KPM | P5 → KPM; KPR does not modify KW; KW updates are stopped — KW incorporation, if any, is part of the pending KPM design confirmation, not a path set here |
| #291 lifecycle contract | design comment `6035861090` (3 open questions) | design only; root six-item revision undelivered; Fable not started; revoked here | #288/#289 identity semantics exist as A-line defect fixes; KPR adds nothing further | minimal lifecycle contract for resource/duty-holding components | root (dot first), then bounded Fable — in KPM | all lifecycle-contract design and implementation in KPM; KPR contributes only the existing #288/#289 semantics as they land |

## Research / DDD — originals retained as evidence; continuation revoked here

| Issue / artifact | Fixed at / evidence | Status | Separation | Acceptance owner |
|---|---|---|---|---|
| #270 research parent | corpus `docs/research/` (14 pinned worker originals + Fable reviews `59b82b39`, `cbfd92dd`) | research originals complete (retained evidence); B architecture implementation revoked in this repo (→ KPM); OPEN | research evidence ≠ B implementation | root (final joint review of the corpus) |
| #279 DDD method + complements | corpus `210b712e` + `9d8de351`; integration `41b12e85` §6b (standalone duplicate carried by `69c8c539` dropped at `cdc29e69`); root-accepted baseline `f4accb11` | accepted baseline (evidence); new-design continuation revoked here (→ KPM); OPEN pending closure | doc design ≠ implementation | root |
| #280–#285 DDD phases | merged+closed; last `0657e37f`; design rev2 `8b3779c9`; runtime evidence `test-ddd-pack.py` (29 tests) | done; optional component `kaola-ddd/1` stays as-is (uninstallable, never a B0 precondition) | closed line, no continuation here | KPR Host (done) |

## Runtime / release boundary facts (evidence, not design)

- Release v0.9.1: content R `3de9f61a`, pin P `1112070e`, tag `v0.9.1`. Seats: restart required per CHANGELOG.
- `main` ahead of R and pushed: `5cef759a`, `93662173`, `bd58301b`, DDD merges, archives, `69c8c539` (AGENTS KPM-transfer supersession), `cdc29e69` (duplicate drop). None released or installed.
- Installed main Skill payload (`~/.agents`, `~/.claude`, `~/.codex` copies) lacks `scripts/kaola-compact-recovery.py` → the `maintenance-returned` alert batch:118 stays open until a root-gated release + install; not a KPM dependency.
- Protected owner files dirty on main (`hosts/grok-bot/INSTALL.md`, `bridge.json`, `kaola-delegator.md`, `templates/grok-bot/accepted-revision.json` family): never published by KPR runs; every finalize keeps the pre-push own-files diff check and drops mirrored protected paths pre-push (precedent `774ff7a6`).
- Live workers: zero, verified by a fresh all-platform sweep at the 2026-10-07 handover beat; the stopped architecture workers' fresh status receipts read `state=stopped` (P2 `f8c0c922`, P3 `b211fb4c`, #289 `c9c4ae40`, prior Claude Host `5fe42978`). The only verified live KPR session is the current sole ZCode Host. No stop is repeated against historical PIDs.
- Supervision: dot's existing hourly heartbeat covers both canonical locators (KPR + KPM); no new or changed timer; no cross-repo global stop-and-wait. Cross-repo gaps are reported to the owning bridge/repo; KPR dispatches no work into other repos and expands no scope from this inventory.
