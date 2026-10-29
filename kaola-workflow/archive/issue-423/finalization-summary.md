# Finalization Summary — issue-423

## Delivered

Root cause, corrected by the run's evidence: the idle self-prompt came from the Issue #264
compact-reload reread, not from the #341 continuation path. Devin 3000.11.92 sends a summary-less
`_cognition.ai/compaction` started/completed pair on ordinary agent steps. The holder treated each
one as a completed compaction and owed a Skill-reread self-prompt, which it delivered at the next
turn end. Devin is not on the list of platforms that run their own compact recovery
(`NATIVE_COMPACT_RECOVERY_PLATFORMS` is empty). This is the KPR i416 zero-work reload turn: reload
delivered at cursor 5144, the turn ended at cursor 5309.

- `scripts/kaola-compact-recovery.py`: a Devin `completed` notification counts as a compaction only
  when `params.summary` is a non-empty string (`DEVIN_SUMMARY_KEY`). A summary-less pair produces
  no `compact_reload_detected`, no Host maintenance registration and no reload prompt. The holder
  code is unchanged, and the change adds no timer and no state.
- Census (`docs/evidence/issue-423-devin-compaction-census.md`):
  - 84/84 summary-bearing completions were real compactions (83 shrank to ≤ 0.6×; 1 had no prior
    `usage_update` reading).
  - Of 688 summary-less completions, 681 showed no drop and 7 coincided with a context-window
    switch (1,000,000 ↔ 262,000).
  - The two committed #264 Devin 3000.11.3 completions also carry `summary`.
- New suite `tests/contract/test-issue-423-devin-compaction-summary.py`, 6 tests, registered in
  `python_suites_all` and `python_suites_b`. The two Devin positive fixtures in
  `tests/contract/test-issue-264-compact-recovery.py` now carry a summary.
- Docs:
  - `docs/api.md` (post-compaction reread section) states the summary rule.
  - `docs/conventions.md` and the `CHANGELOG.md` header add `scripts/kaola-compact-recovery.py` to
    the operator restart test. The holder pins it at startup (`load_sibling_modules`).
- Correction comment on #423 (6483867232). It downgrades the #341 verified-initiation gate to a
  low-priority follow-up for the Owner to authorize separately. The gate was not built (Host ruling C).

## Candidate

`workflow/issue-423` @ `a399a8e6` (one commit on base `6207456f`).

## Acceptance

Host verdict ACCEPTED (a399a8e6). The Host verified independently:

- the rule in code;
- test-issue-423 6/6 and test-issue-341 9/9;
- render --check PASS;
- test-issue-264 49/49;
- the restart-set doc additions;
- golden and `.kaola` untouched;
- the dispatch re-check semantics: a stale summary-less detection is refused as
  `signal-unverified`, and a real compaction still passes.

## Evidence

- Recorded validation: `.cache/final-validation.md` (verdict pass, bound to the candidate tree).
- Lead runs on `a399a8e6` (logs `/tmp/kpr423b-*.log`): render --write/--check PASS;
  test-issue-423 6/6; test-issue-264 (direct) 49/49; test-issue-341 9/9. Against the pre-fix
  classifier, test-issue-423 fails 13 subtests, so it detects the bug.
- Census source: `/tmp/kaola-501/devin/*/*/events.jsonl*` (87 Devin record directories, 48 with
  pairs) and `docs/evidence/host-compaction/edge-devin-20261006-*`.

## Known failures or unverified scope

- **Seats: restart required.** Running seats keep the old classifier until they restart. No release
  or tag in this run.
- **AGENTS.md (noted only, not edited, per Host):** the Release-line operator test omits
  `scripts/kaola-compact-recovery.py`, `scripts/kaola-record-contract.py` and
  `scripts/kaola-acp-paths.py`. `docs/conventions.md` and the CHANGELOG list all three.
- VRPAI seat `devin-vrpai-i2366-s8` logs were not available on this machine. That incident's fit to
  the same mechanism is inferred from its shape, not measured.
- No live seat measurement. Focused suites only; the whole inventory was not run.
- Run custody: at 2026-10-29T08:03:39 an external checkout of `ac11d795` in the main checkout
  removed the linked worktree, the run folder and the uncommitted first pass.
  - The lead's mistaken commit `61fef4a6` captured that state. The Host reset it; it stays in the
    reflog only and was never reused.
  - The candidate was re-applied from the reviewed record.
  - The claim was re-acquired to restore `workflow-state.md`: the old label and marker were removed
    and `startup --target-issue 423` was run again. The new `claim_ts` is 2026-10-29T00:13:38Z. The
    mission ledger was rebuilt from the lead's record.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/api.md
- docs/conventions.md
- docs/evidence/issue-423-devin-compaction-census.md
- scripts/kaola-compact-recovery.py
- scripts/validate.sh
- skills/antigravity-kaola-project-runner/scripts/kaola-compact-recovery.py
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/kaola-compact-recovery.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/kaola-compact-recovery.py
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/kaola-compact-recovery.py
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/kaola-compact-recovery.py
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/kaola-compact-recovery.py
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/kaola-compact-recovery.py
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/kaola-compact-recovery.py
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/hermes-kaola-project-runner/scripts/kaola-compact-recovery.py
- skills/hermes-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/scripts/kaola-compact-recovery.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-compact-recovery.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-compact-recovery.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-compact-recovery.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- tests/contract/test-issue-264-compact-recovery.py
- tests/contract/test-issue-423-devin-compaction-summary.py

## Follow-Up Items

- filed: #424 — `validate.sh` does not run `test-issue-264-compact-recovery.py` (49 classifier
  tests unregistered). P3. Confirmed present: OPEN, body 1,123 chars.
- #341 verified-initiation gate: proposed in the #423 correction comment for separate Owner
  authorization; not filed (Host directive).

## Readiness

Ready to finalize and sink (merge).

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-423/.cache/final-validation.md
- kaola-workflow/archive/issue-423/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-423/finalization-summary.md
- kaola-workflow/archive/issue-423/mission-ledger.jsonl
- kaola-workflow/archive/issue-423/workflow-state.md
