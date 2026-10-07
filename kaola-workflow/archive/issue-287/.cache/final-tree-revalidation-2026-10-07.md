# #287 final-tree re-validation — post-archive delivery-evidence supplement

Recorded 2026-10-07 ~22:35 +08 by Host `zcode-KPR-orchestrator-main`
(holder `eb9f120438d48c82131ada5bc1e56919`), a fresh session after the prior
holder `c7e8d581e121a5a387f65d1007d78e90` was exact-stopped by the Delegator
(stop=true, exit 0, residual=[]); no native resume is claimed.

## Why this supplement exists

The archived `finalization-summary.md` carries `final_validation_stale`,
`green: false`: recorded `validated_candidate_hash`
`47241a4755cae49e00cc07448060628f0531fc46bdca855f24c58a06409910a8` (worktree
candidate `73887f7a`, worktree-only content-stage flip) != finalize-time
code-tree hash
`454fb9a89f04ff59c7ae5f544b2ee780cfb442cfd03c54d7168a22cabd8e7966`. The
original 379-PASS evidence was therefore never bound to the final landed tree.
That stale finding stands unedited. The Kaola-Workflow validation runner
refuses to amend an archived run's record (`project_folder_missing`;
operator hint: "once the transaction has archived the run its record is closed
evidence and must not be edited retroactively"), so this file is separate
normal-Git evidence: not a re-finalize, not a hand-patched hash, and it does
not report the archived final gate as green.

## Source attribution (code identity)

- Landed fix: `70dc4062` (fix #287); archive/sink: `930236f2` (main HEAD at
  this writing; commit tree `618cd7dd0093e13fcc4d7c3e72fc2a44ba4abef0`,
  fix-commit tree `80bd80b6ccfa342750a9e0572a9573541d027fcd` — they differ only
  by the `kaola-workflow/` archive band).
- `git diff --name-status 73887f7a 70dc4062 -- scripts templates tests skills
  CHANGELOG.md docs/api.md` is **empty**: every relevant
  source/test/test-consumed byte validated at candidate `73887f7a` equals the
  landed code at `70dc4062`.
- `tests/contract/test-issue-255-lifecycle-state.py` at HEAD: 135 tests, last
  changed by `70dc4062`.

## Final-tree re-validation (isolated, exact tree)

Detached worktree `/tmp/kpr-287-final-tree` at `930236f2`
(`930236f2d1f4ffec624f330bcd2db70fb26e3753`), start dirty=0, post-restore
dirty=0. Log `/tmp/kpr-287-final-revalidate.log`; per-suite outputs
`/tmp/kpr-287-suite-*.out` (ephemeral /tmp; this file is the durable record).
Run window 2026-10-07T14:18:16Z–14:21:47Z.

1. `./scripts/render-skills.py --check` on the CLEAN final tree → **exit 1**,
   **214 `pin:` findings** ("P may differ from 3de9f61afbfa only by
   templates/grok-bot/accepted-revision.json and the three generated
   hosts/grok-bot/ products"). Tree-bound figures only: the bridge measured
   207 at clean `7e3998c2`; this run measured 214 at clean `930236f2`.
   Standing pre-release pin state (P commit not yet made), not a #287 defect.
2. Worktree-only content-stage flip
   (`templates/grok-bot/accepted-revision.json` stage=content +
   `./scripts/render-skills.py --write`, exit 0) → `--check` **PASS** (exit 0):
   "content stage, unpinned (not saveable)".
3. Nine affected suites via `./scripts/validate.sh --suite <name>`:

   | suite | unittest summary | exit |
   |---|---|---|
   | test-issue-255-lifecycle-state.py | Ran 135 tests, OK | 0 |
   | test-issue-286-retire-input.py | Ran 13 tests, OK | 0 |
   | test-issue-259-record-contract.py | Ran 63 tests, OK | 0 |
   | test-issue-244-dispatch.py | Ran 79 tests, OK | 0 |
   | test-issue-244-holder-prompt-binding.py | Ran 7 tests, OK | 0 |
   | test-issue-274-package-closure.py | Ran 4 tests, OK | 0 |
   | test-issue-275-core-contracts.py | Ran 20 tests, OK | 0 |
   | test-issue-267-rejection-count.py | Ran 29 tests, OK | 0 |
   | test-ddd-pack.py | Ran 29 tests, OK | 0 |

   **379 tests OK** — per-suite counts identical to the candidate validation
   bound at `73887f7a`.
4. `git checkout -- .` → restored (exit 0, dirty=0).

## Scope and limits

- This binds the 379-PASS evidence to the exact final tree `930236f2` and
  proves candidate/landed code identity on all relevant paths.
- It does not modify the archived `finalization-summary.md` or
  `.cache/final-validation.md`, does not re-run finalize, and the #287 final
  gate is **not** reported green: the archived stale finding remains the
  recorded final-gate state.
- Release/install/restart for AI consumption stays behind the original owner's
  gate (main != release/install). Installed main-Skill payloads still lack the
  compact helper (batch118 lineage) — open duty, unchanged by this supplement.
