# KPR release candidate 2026-10-08 — Fable read-only final review

Reviewer: Claude Code Fable 5.1 (thinking/review scope). Method: read-only inspection of the
candidate worktree, Git history, the merged contract sources, and the QA logs named in
`/tmp/kpr-fable-final-review-brief.md`. No repo writes, no publish, no install, no mutation.
The only commands executed beyond reads were `render-skills.py --check` (read-only verifier) in
the candidate and in the clean `48d023a4` QA worktree; neither changed any tracked file
(`git status --short` empty afterwards in both).

## Tree identity (verified)

- `/tmp/kpr-release-candidate` HEAD = `57550098` (detached), clean working tree.
- Lineage confirmed: `48d023a4` (origin/main) → R1 `a6af2d88` → R2 `6ca79623` → P2 `57550098`;
  `git rev-parse 57550098^` = `6ca79623`.
- R1 vs main: exactly the four grok-bot files (`git diff --stat 48d023a4 a6af2d88`); the four
  dirty files in the MAIN checkout are byte-identical to R1's committed content (sha256 prefixes
  `218b2e0f…`, `27866e52…`, `54fbdf39…`, `b9509fd1…` match on both sides).
- R2 vs R1: exactly the three contract tests, +13/−5 lines.
- P2 vs R2: exactly the four pin paths (`hosts/grok-bot/INSTALL.md`, `hosts/grok-bot/bridge.json`,
  `hosts/grok-bot/kaola-delegator.md`, `templates/grok-bot/accepted-revision.json`).
- Whole candidate vs main: `git diff --name-only 48d023a4 57550098` = those 7 files, nothing else.

## Item 1 — three R2 test corrections (`6ca79623`)

### 1a `tests/contract/test-progressive-disclosure.py` — CONFIRMED

- Old oracle (two scripts) last touched at `848e2804`; `git merge-base --is-ancestor 848e2804
  93662173` → true. `93662173` (#274, merged; ancestor of `48d023a4`) adds
  `skills/kaola-project-runner/scripts/kaola-compact-recovery.py` (411 lines) to the orchestrator
  package and `scripts/render-skills.py:591-597` now refuses to render without it ("missing
  compaction recovery helper").
- The #274 closure suite `tests/contract/test-issue-274-package-closure.py:29-34` asserts the
  helper is in the package; `:117-125` removes it from an isolated copy and requires a failure that
  names the dependency. So the old enumeration contradicted a merged, test-enforced contract; the
  working-tree run shows exactly that mismatch (`/tmp/rqa-working-validate-full.log:167-190`).
- Helper is not a transport script: `scripts/kaola-compact-recovery.py:2-12` is a pure
  compaction-signal classifier that "does not start, cancel, or restart any session"; transport
  scripts (`kaola-acp.py`, `kaola-acp-holder.py`, `kaola-tmux.sh`, adapters) remain absent from
  `skills/kaola-project-runner/scripts/` (listing at P2: exactly the three files). Exclusion
  semantics ("no transport scripts") kept in the assertion message at
  `tests/contract/test-progressive-disclosure.py:131-134`; no other assertion changed.

### 1b `tests/contract/test-issue-162-upgrade-safety.py` — CONFIRMED

- Contract: `scripts/kaola-acp-paths.py:27-37` `check_record_root` (introduced `b81f2734`, inside
  the #278 merge `bd58301b`, ancestor of main) refuses a root that is not a caller-owned,
  non-symlink directory. `scripts/kaola-acp.py:5776-5777` `command_drain_restart` calls it on
  `record_dir(...).parent.parent.parent`, i.e. the real `<root>/<platform>/<session>/<instance>`
  layout.
- Old fixture stubbed `record_dir` to the test's shallow `self.root`
  (`tempfile.TemporaryDirectory`, test `:57-58`); under the validate harness TMPDIR
  (`/tmp/kaola-val.X/tmpY`) parent^3 is `/`, and the working run's traceback shows precisely
  `RecordRootUnsafe: record root / must be a non-symlink directory owned by the caller`
  (`/tmp/rqa-working-validate-full.log:1632-1646`). The test was last touched at `848e2804`,
  before `b81f2734`. Stale fixture, not a product defect.
- New fixture (`:625-631`) nests `self.root/rec-root/codex/i198/h1`, so parent^3 is a private
  caller-owned directory; the test still asserts the #198 behaviour it existed for
  (`refused`/`drain-stop-failed`, `mutation_performed` True, `completed`, inspect-status hint at
  `:640-644`). No assertion removed or weakened.

### 1c `tests/contract/test-issue-187-delegator-any-host.py` — CONFIRMED

- Contract: `6967afd2` (#278, under merge `bd58301b`) changed `scripts/kaola-locate.py` so that for
  ANY worker in `WORKER_IDS` with a project the session dict is initialised with
  `"acp_holder_alive": None` and filled from the ACP record (`scripts/kaola-locate.py:407-416`);
  its docstring diff explicitly drops the "zcode only" wording. `CHANGELOG.md:14-15`
  (Unreleased, #278): "Locator worker session presence now reads ACP records for all ten
  platforms." Old assertion (key absence) last touched `24adb9c9`, an ancestor of `6967afd2`.
- Working failure shows the actual value: `{'acp_holder_alive': False, 'present': False}`
  (`/tmp/rqa-working-validate-full.log:1688-1692`), i.e. the locator never claimed alive.
- New oracle `assertIsNot(session.get("acp_holder_alive"), True)` (`:394`) preserves the
  invariant "never claim alive without a live record"; all surrounding assertions (session name,
  no worker-unknown/script-missing reasons, `zcode_runtime.required is False`, no zcode-runtime
  reasons, zcode branch) are unchanged. No real assertion deleted; no threshold loosened — the old
  assertion encoded a superseded contract, not a stricter version of the current one.
- Non-blocking observation: `assertIs(..., False)` would be strictly tighter in this fixture
  (no record → `live(None)` is `False` per `scripts/kaola-acp-paths.py:86-88`); `assertIsNot(..., True)`
  also tolerates `None`. Acceptable as written because it matches the stated invariant.

## Item 2 — QA receipt chain — CONFIRMED (one attribution qualified)

| Receipt | Verified |
|---|---|
| `/tmp/rqa-working-validate-full.log` | `FAILED:` exactly the three suites (lines 20-22); final line `working validate exit: 1` (line 2440). |
| `/tmp/rqa-clean-render.log` | 207 `pin:` findings against pin `3de9f61a`; re-executed read-only in `/tmp/kpr-qa-clean-48d023a4` (clean at `48d023a4`): exit 1, 207 findings — matches. |
| `/tmp/rqa-P-validate-full.log` | candidate `65531ff4 (clean)`; `FAILED:` the three suites + `test-issue-244-dispatch.py`; the 244 failure is subTest `label='foreign capture'`, `'capture-identity-unbound' not found in ['status-timeout']` (lines 1811-1821); `P candidate validate exit: 1` (line 2450). |
| `/tmp/rqa-P-244-recheck.log` | `SUBSET RUN (1 of 94 suites)` at `65531ff4 (clean)`, `Ran 80 tests` … `OK`, 80 `... ok` lines. |
| `/tmp/rqa-P2-validate-full.log` | `FULL INVENTORY (94 suites)` at `57550098 (clean)`; 0 `FAIL:`/`ERROR:`/`FAILED` lines; 74 `Ran N tests` lines summing to 1539; `P2 candidate validate exit: 0` (line 2396). The three corrected suites report `Ran 15/27/14 tests … OK` (lines 164-166, 1139-1141, 1428-1430); `test-issue-244-dispatch.py` elapsed 39.8 s, ok. |
| `/tmp/rqa-P2-suite-map.txt` | 94 lines: 92 `ok <suite>.py` + `ok(acceptance PASS)` for `test-installer-migration.sh` and `test-installer-runtimes.sh`; the three corrected suites and 244 listed `ok`. |
| `/tmp/rqa-P2-require-pinned.log` | `render-skills: PASS … 2510 B, pinned at 6ca79623d9ca, pin verified`; re-executed read-only in the candidate now: same line, exit 0. |

Qualification on the P1 244 failure: "proven concurrent-run contamination" is stronger than the
logs support. What the evidence does show: the failing subTest runs with
`KAOLA_DISPATCH_RUNNER_TIMEOUT=1` (`tests/contract/test-issue-244-dispatch.py:2875`), so a
status call over one second yields `status-timeout` before the identity conflict is classified —
a load-sensitive race; `validate.sh` runs two suite lanes concurrently
(`scripts/validate.sh:586-591`); the working full run (ended 02:20:50, 905 s) overlapped the P1
run (started ≈02:17:50) for about three minutes; it did not reproduce in the sequential 80/80
recheck or in the P2 full run; and no file in the candidate diff is an input to the 244 suite
(the suite does not reference the grok-bot paths; `kaola-dispatch.py` is unchanged). Conclusion:
not a candidate defect; attribution to concurrent load is plausible and consistent, not proven.
Non-blocking.

## Item 3 — release boundary integrity — CONFIRMED, with one ref-hygiene gap

- Pre-release label, no version claim: `templates/grok-bot/accepted-revision.json` at P2 =
  `stage pinned`, `commit 6ca79623…`, `label "candidate awaiting root and Fable final review"`;
  `hosts/grok-bot/bridge.json` `release: null`, `saveable: true`, `skill.bytes 2510`,
  `file_sha256 6e0cf6e8…` — both match the actual file (`wc -c` 2510, sha256 `6e0cf6e8…`).
  `CHANGELOG.md:7-9` still `## Unreleased` with `Seats: restart required`; no new version section.
- Not published/tagged: `git tag --contains 57550098` empty; newest tag `v0.9.1` at `b5c87902`
  (2026-10-07); `gh release list` newest `v0.9.1`. No install evidence in the candidate.
- Protected originals untouched in main: main HEAD `48d023a4`; the four files still dirty and
  byte-identical to R1 (hashes above); `git status -- tests/ scripts/ templates/orchestrator
  templates/kaola-delegator` empty in main (the R2 test edits live only in the candidate).
- No KW changes: the candidate diff touches no `kaola-workflow/` path; main shows no tracked
  `kaola-workflow/` modification (only pre-existing untracked archive/issue dirs). Scope of this
  check is the KPR repository; the separate KW repository was not inspected.
- No new issues: newest issue is #291, created 2026-10-07T10:15Z; none on 2026-10-08.
- No architecture change: the seven-file diff is render products of the owner-staged bridge
  content, the pin, and three test oracles/fixtures; no `scripts/`, `templates/orchestrator/`,
  `templates/kaola-delegator/`, `platforms/` or `docs/` change.

GAP (must be corrected before publish; not a content defect): the branch
`release-candidate-2026-10-08` still points at the superseded P1 `65531ff4`
(`git branch -v`), and P2 `57550098` is not contained by any branch or tag
(`git branch -a --contains 57550098` → only the detached worktree HEAD). The brief describes P2
as the branch HEAD; in fact P2 survives only through the worktree's detached HEAD and reflog
(`HEAD@{0}`). Removing or re-pointing that worktree would orphan the reviewed pin chain. The
owner/root should fast-forward the branch to `57550098` (or record the exact hash in the
release record) before any publish step; this review's verdict binds to the commit hash, not to
the branch name.

## Summary of gaps

1. Branch ref `release-candidate-2026-10-08` is stale at P1; P2 unreachable from any ref
   (blocking for publish bookkeeping, not for candidate content).
2. "Proven" concurrent-run contamination of the P1 244 failure is plausible but not strictly
   proven by the logs; it is not reproduced and the candidate does not touch 244 inputs
   (non-blocking).
3. 1c oracle could be `assertIs(..., False)` for this fixture (non-blocking).

FINAL: PASS
