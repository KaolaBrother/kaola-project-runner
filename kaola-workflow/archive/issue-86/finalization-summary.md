# Finalization Summary — Issue #86

Run: `issue-86` · branch `workflow/issue-86` · sink `merge` · issue #86
Candidate accepted by outer independent review: `c0bcaf58a1ff37ddb55e1b19118125ffcc6febee`
Docked head at finalize: `ec86396` (accepted fix + docs-only changelog docking)

## Delivered

Issue #86: the shared Kaola-Delegator prompt turned Issue #74's "do not fuse quota units"
into "all three quota units are mandatory figures", so an outer Agent that already held
worker platforms, counts, concurrency, an account quota, priority, the stop boundary, and
the canonical project path still refused to `start` for want of a separate token cap.
That was an extra hard start gate, not unit hygiene.

Quota now travels in the units the user actually gave. A unit the user never gave is not a
missing key value: it is carried as `unspecified`, does not block the start, and is
explicitly **not** unlimited. Everything Issue #74 pins survives unchanged — unit
non-fusion, no guessing, no stale-quota reuse, no blank Host, still-ask on a genuinely
missing or ambiguous value, and no re-ask on a live Host A→B attach.

Prompt-only. No new schema, state file, quota engine, or transport gate. No release, no tag.

### Issue acceptance walked, member by member

1. *Account quota + all other key items given, no separate token cap → may start; handoff
   says the token limit is unspecified, does not claim unlimited, does not demand a token
   figure.* — Satisfied. Fixed leg A returns START with `quota_token=unspecified`,
   explicitly not unlimited and not fused into the account figure
   (`evidence/fixed/A.md`); the same leg returned ASK pre-fix (`evidence/baseline/A.md`).
   Pinned by `test-issue-86-delegator-quota.py`.
2. *Explicit token cap given → carried verbatim, never fused with account or concurrency;
   a later change takes the newest value.* — Satisfied. Fixed leg B carries
   `quota_token=200000 tokens` apart from account and concurrency, unchanged from baseline
   (`evidence/fixed/B.md`). The "apply only the user's latest change" rule on a live Host
   is untouched in `SKILL.md.tmpl` and exercised by leg D.
3. *Genuinely missing worker platform/count, or an unclear quota meaning → still ask, do
   not open a blank Host; a live Host B does not re-`start`.* — Satisfied. Leg C1 still
   asks (and no longer demands a token figure); leg C2 still asks on the unclear unit and
   explicitly refuses to default the ambiguous "3" to `unspecified`; leg D attaches in
   place with a delta-only send.
4. *Minimal prompt/test/necessary-doc change; `skills/` and `hosts/grok-bot/` generated
   only by the renderer; `--check` and `validate.sh` pass; finalize only after independent
   review of the frozen SHA.* — Satisfied. The change is 2 templates + their 2 rendered
   outputs + README + one suite registration + one new test; generated files were produced
   by `./scripts/render-skills.py --write`; `--check` and `validate.sh` pass; the outer
   independent review accepted the frozen `c0bcaf5` before this finalize began.

## Files Changed

Accepted fix (`c0bcaf5`):

- `templates/kaola-delegator/SKILL.md.tmpl` — "Extract once" rule
- `templates/kaola-delegator/references/handoff.md.tmpl` — step 3 reflow, step 4,
  handoff-text header, `quota_concurrency` slot
- `skills/kaola-delegator/SKILL.md` — generated
- `skills/kaola-delegator/references/handoff.md` — generated
- `README.md` — A→B paragraph
- `scripts/validate.sh` — register the new suite in `python_suites_all` + `python_suites_b`
- `tests/contract/test-issue-86-delegator-quota.py` — new, 169 lines

Docking (`ec86396`): `CHANGELOG.md` only.

Byte budgets (locked invariant, `templates/budgets.json`): `reference_bytes` had 3 B of
headroom, so the handoff edit is net-negative (8189 → 8186 B rendered), funded by two
lossless rewordings that drop no rule; the fuller statement lives in `SKILL.md`
(3824 → 4010 B of 4096).

## Test Coverage

- `tests/contract/test-issue-86-delegator-quota.py` — 46 checks over both templates and
  both rendered outputs: the three removed sentences asserted absent, the replacement rule
  asserted present, and the four surviving properties (unit non-fusion, no invented
  unlimited quota, still-ask on missing/ambiguous, no re-ask on a live Host) asserted too.
  Proven to FAIL on the pre-fix candidate — first assertion, recorded at
  `evidence/baseline/contract-test-on-baseline.txt`.
- `tests/contract/test-issue-74-kaola-delegator.py` — 151 assertions, unchanged and
  passing; the Issue #74 README sentence it pins verbatim was deliberately not touched.
- Behavioral evidence: five scenarios × two frozen prompt versions = ten isolated
  clean-context Opus legs, each given only its two staged files and its own scenario, at a
  neutral path. Exactly one decision flipped and it is the one Issue #86 names; the four
  guard legs are unchanged. `evidence/COMPARISON.md` plus unedited raw verdicts in
  `evidence/baseline/` and `evidence/fixed/`.

## Validation

- verdict: **pass**
- command: `./scripts/validate.sh`
- exit code: 0, executed in the foreground in the candidate worktree at the docked head
  `ec86396`; raw 348-line log at `evidence/validate-final-docked.txt`, exit at
  `evidence/validate-final-docked.exit`.
- Zero `^FAILED: ` and zero `^SKIPPED: ` lane lines. `render-skills: PASS ... budgets OK`
  (line 1); `issue-74 checks: 151 assertions, 0 failed tests` (line 335);
  `PASS test-issue-86-delegator-quota.py (46 checks)` (line 346);
  `kaola-grok-bot-verify: PASS` (line 347).
- This run is byte-identical to the accepted-candidate run at `c0bcaf5`
  (`evidence/validate-postfix.txt`, exit 0) except for per-suite elapsed times, so the
  docs-only commit is proven not to have moved any verdict.
- Receipt: `.cache/final-validation.md`, `verdict: pass`,
  `validated_candidate_hash: ee5fb668bf531e1a34d723970b28c66d9cd3638652b8b09430e3b2f66d786583`.
- Acceptance legs: automated (above) and local isolated behavioral A/B (above).
  **Not executed:** live tmux smoke and live Grok Bot UAT. The change is prompt text in a
  Skill that no transport reads; no adapter, relay, locator, or session path was touched,
  and the offline grok-bot bridge verify passes. The Grok Bot bridge remains unpinned and
  not `saveable` — unchanged by this run and out of its scope, since no release is created.

## Changed Paths

Reported by the finalize transaction (`changed_paths`):

- `scripts/validate.sh`
- `skills/kaola-delegator/SKILL.md`
- `skills/kaola-delegator/references/handoff.md`
- `templates/kaola-delegator/SKILL.md.tmpl`
- `templates/kaola-delegator/references/handoff.md.tmpl`
- `tests/contract/test-issue-86-delegator-quota.py`

The transaction's list is source-scoped and omits the two documentation files this run also
changed: `README.md` (in the accepted `c0bcaf5`) and `CHANGELOG.md` (in the docking commit
`ec86396`). The complete branch diff against main `18db64b` is those six paths plus those
two — eight files, no others.

Transaction record: `mirror: mirrored`, `ledger_compare: pass`,
`impl_commit: not_applicable`, `archive_commit: deferred_to_sink`,
`closure_invariants: ok` with no violations, `validation: chains_green` bound to this tree.

## Documentation Docking

`DOCKED` — `.cache/doc-docking.md`.

- `README.md` — fixed in the accepted candidate (the A→B quota-units paragraph).
- `CHANGELOG.md` — fixed at docking; Issue #86 entry under `## Unreleased`, matching the
  per-issue convention used by Issues #84 and #85.
- `AGENTS.md`, `docs/architecture.md`, `docs/api.md`, `docs/conventions.md`,
  `docs/README.md`, `docs/grok-bot-host.md`, `docs/decisions/` — checked, no impact, with
  reasons recorded: they describe the Kaola-Delegator render topology and the handoff
  contract at a level that never enumerated the three quota units.
- Install/setup/validation docs and examples — no impact; no command or flag changed.

## Follow-Up Items

None filed. No run-discovered defect surfaced that this change does not itself resolve.

Recorded for the record, not as defects:

- `skills/kaola-delegator/references/handoff.md` now sits at 8186 of 8192 `reference_bytes`
  — 6 B of headroom. The budget is a locked progressive-disclosure invariant working as
  designed; any future handoff edit must again be net-neutral or net-negative, or move its
  text into `SKILL.md` (86 B of headroom) or a new reference.
- The pending user decision recorded at the end of Mission 6 — whether a token cap is
  mandatory — has since been answered: unspecified (not unlimited) is correct, which is
  what Issue #86 specifies and what this candidate implements. Nothing is left open.

## Readiness

READY. Candidate accepted by outer independent review, docked, validated at exit 0,
documentation `DOCKED`, acceptance walked member by member with no blocker.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-86/.cache/doc-docking.md
- kaola-workflow/archive/issue-86/.cache/final-validation.md
- kaola-workflow/archive/issue-86/.cache/mirror-digest.json
- kaola-workflow/archive/issue-86/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-86/evidence/COMPARISON.md
- kaola-workflow/archive/issue-86/evidence/baseline/A.md
- kaola-workflow/archive/issue-86/evidence/baseline/B.md
- kaola-workflow/archive/issue-86/evidence/baseline/C1.md
- kaola-workflow/archive/issue-86/evidence/baseline/C2.md
- kaola-workflow/archive/issue-86/evidence/baseline/D.md
- kaola-workflow/archive/issue-86/evidence/baseline/RESULTS.md
- kaola-workflow/archive/issue-86/evidence/baseline/SKILL.md
- kaola-workflow/archive/issue-86/evidence/baseline/base-commit.txt
- kaola-workflow/archive/issue-86/evidence/baseline/contract-test-on-baseline.txt
- kaola-workflow/archive/issue-86/evidence/baseline/handoff.md
- kaola-workflow/archive/issue-86/evidence/baseline/sha256.txt
- kaola-workflow/archive/issue-86/evidence/fixed/A.md
- kaola-workflow/archive/issue-86/evidence/fixed/B.md
- kaola-workflow/archive/issue-86/evidence/fixed/C1.md
- kaola-workflow/archive/issue-86/evidence/fixed/C2.md
- kaola-workflow/archive/issue-86/evidence/fixed/D.md
- kaola-workflow/archive/issue-86/evidence/fixed/SKILL.md
- kaola-workflow/archive/issue-86/evidence/fixed/handoff.md
- kaola-workflow/archive/issue-86/evidence/fixed/sha256.txt
- kaola-workflow/archive/issue-86/evidence/scenarios/A-account-quota-no-token-cap.txt
- kaola-workflow/archive/issue-86/evidence/scenarios/B-explicit-token-cap.txt
- kaola-workflow/archive/issue-86/evidence/scenarios/C1-missing-platform-count.txt
- kaola-workflow/archive/issue-86/evidence/scenarios/C2-ambiguous-quota-unit.txt
- kaola-workflow/archive/issue-86/evidence/scenarios/D-live-host-attach.txt
- kaola-workflow/archive/issue-86/evidence/validate-final-docked.exit
- kaola-workflow/archive/issue-86/evidence/validate-final-docked.txt
- kaola-workflow/archive/issue-86/evidence/validate-postfix.exit
- kaola-workflow/archive/issue-86/evidence/validate-postfix.txt
- kaola-workflow/archive/issue-86/finalization-summary.md
- kaola-workflow/archive/issue-86/mission-list.md
- kaola-workflow/archive/issue-86/workflow-state.md
