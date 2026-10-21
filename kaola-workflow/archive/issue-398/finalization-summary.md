# Finalization Summary — Issue #398

## Delivered

Restored the #309 recovery-route contract on `workflow/issue-398`: every code
documented by the recently merged #381/#384 work has an executable route again,
without weakening extraction or changing any existing entry.

- `agent-exited-after-write` is now a route: exact-stop the session
  (`stop --repo REPO --session SESSION --expected-holder-instance-id ID`),
  attest, `start --resume NATIVE_ID`, read `view` for the resumed session
  before sending again, never resend the recorded prompt unchanged, and use a
  new `--client-message-id` if the first prompt carried one.
- `event-log` and `since-below-oldest-event` are routes: re-read
  `view` without `--since`, or from
  `truncation.event_log.oldest_cursor`, and continue from that snapshot;
  events below the retained cursor are never replayed.
- `projection-rows-missing`, `timeline-cap`, `view-bytes` and `holder-restart`
  are self-routes naming the real disclosure fields: `messages_dropped`,
  `truncation.rows.messages`/`.tools`/`.turns`/`.answered_permissions`, and
  `truncation.rows.messages.restart` with its honest `null` dropped count when
  the process began against a positive historical cursor. They say to treat
  the returned payload as the current compacted snapshot, not to infer or
  restart for the dropped rows.
- `tests/contract/test-issue-309-recovery-routes.py` passes again with its
  extraction unchanged; existing entries, including `holder-timeout`, are
  byte-identical.
- The shared script is rendered into the twelve Skill copies and their
  `main-skill-build.json` manifests; `CHANGELOG.md` records the change.

Candidate: `09045ab0352f8a697f7c7d236bb80f0980004d92` on
`workflow/issue-398`; base `ef0a8c23c99c208ace08c4bcf1e23183504ca826`. This
run performed no tag, release, publish, install, or KPM-side operation.
`scripts/kaola-recovery-routes.py` is a per-call file outside the operator
restart set, so this change itself needs no seat restart; the `Unreleased`
section's `Seats: restart required` comes from the #383 holder change.

## Acceptance Evidence

- Host acceptance of candidate `09045ab0` (recorded before this finalize seat
  took over). The previous finalize seat stopped on a provider quota refusal
  (429 `GoUsageLimitError`) with zero side effects: `main` stayed at
  `ef0a8c23`, #398 stayed OPEN, and no archive or finalize commit was made.
- Final validation run by this seat at `09045ab0` (clean worktree), exit 0:
  - Command: `/opt/homebrew/bin/bash scripts/validate.sh --suite
    test-issue-309-recovery-routes.py --suite test-issue-381-view-snapshot.py
    --suite test-issue-384-view-disclosure.py --suite
    test-issue-286-retire-input.py --suite
    test-issue-372-stale-collect-retire.py --suite
    test-issue-362-versionless-retire.py --suite
    test-issue-395-alert-direct-retire.py`
  - `test-issue-309-recovery-routes.py` 8/8; `test-issue-381-view-snapshot.py`
    18/18; `test-issue-384-view-disclosure.py` 9/9;
    `test-issue-286-retire-input.py` 29/29;
    `test-issue-372-stale-collect-retire.py` 13/13;
    `test-issue-362-versionless-retire.py` 4/4;
    `test-issue-395-alert-direct-retire.py` 11 tests, 2 skipped
    (`validate.sh` reported `SUBSET RUN (7 of 156 suites)`).
  - `render-skills.py` PASS (11 workers, Project Runner, Kaola-Delegator,
    Grok Bot bridge; budgets OK) and every Skill validation PASS.
  - Log: `/tmp/kpr398-final-validation.log`.
- Validation record:
  `kaola-workflow/issue-398/.cache/final-validation.md`
  (candidate hash `344aedb16d7e00190d4ec07c10c3366d5febe8ae205b2b216996201e3733d577`).

## Known Failures and Unverified Scope

- No full-inventory `validate.sh` run: the selected seven suites cover the
  route catalog, the #381/#384 disclosure producers it names, and the adjacent
  retire/view contracts. A pure route-table change touches no transport.
- `test-issue-309-recovery-routes.py` proves every extracted code has a
  route/self-route body; it does not execute each route's command text against
  a live Host. That prose guidance remains operator-facing and is not a
  runtime-tested behavior.
- No live external-platform UAT was run for this change; none of the changed
  bytes are on a platform transport path.
- The current `CHANGELOG.md` `Unreleased` section still says
  `Seats: restart required` because of the #383 holder change carried in the
  same unreleased window; the #398 route file itself is per-call.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- scripts/kaola-recovery-routes.py
- skills/antigravity-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json

## Documentation Docking

DOCKED — `CHANGELOG.md` `Unreleased` records the new routes and the per-call
restart boundary. No `docs/api.md` change was needed: the disclosed fields are
already documented by #381/#384, and this run only restores their entries in
the operator route catalog; no template or budget changed.

## Follow-Up Items

- No new follow-up issue was filed by this run.
- No release, tag, publish, install, or KPM-side operation is part of this
  finalization.

Final readiness: ready. Merge sink to `main`, verify publication, close #398
with the Host-supplied closing comment, archive under
`kaola-workflow/archive/issue-398/`, and remove the run worktree and branch.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-398/.cache/final-validation.md
- kaola-workflow/archive/issue-398/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-398/finalization-summary.md
- kaola-workflow/archive/issue-398/mission-ledger.jsonl
- kaola-workflow/archive/issue-398/workflow-state.md
