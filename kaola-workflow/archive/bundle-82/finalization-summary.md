# Issue #82 — finalization summary

Run: `bundle-82` · Issue: **#82** · Branch: `workflow/bundle-82` · Sink: merge to `main`
Accepted candidate (outer review): `b158e16d8ea9e32e55e33d46b5a520fb16fdc4d8` (includes `5c6af87`)
Finalized head (accepted candidate + documentation docking): `c79d966` (CHANGELOG.md entry only)

## Delivered

Standalone ACP contract fixtures now stop exactly the sessions they start.

- `tests/contract/test-acp-contract.py` — `Issue34ModelSelectionAcpTests.start(platform)`
  launches codex/cursor-cli/devin holders, but the shared `AcpSessionFixture.tearDown`
  called `self.cli("stop")` which defaulted to `platform="grok"`: the stop hit a
  nonexistent grok session, `check=False` swallowed the failure, and each of the 14
  non-grok tests leaked its holder + mock agent (8 codex + 5 cursor-cli + 1 devin —
  matching the measured 14/run). The fixture now records the platform it started and
  `tearDown` stops exactly that platform; base `cli`/`start` accept an optional
  `platform` kwarg with the grok default preserved.
- `tests/contract/test-acp-watch-contract.py` —
  `test_view_accept_then_close_uses_frozen_runtime_code` unlinks the holder socket and
  binds a stub listener, so teardown's `stop --force` gets `holder-unreachable` and
  `kaola-acp.py` correctly does not kill a still-live holder — one holder + mock leaked
  per run. The test now runs the existing `scripts/kaola-acp-sweep.py --root <this
  test's exact record_dir>` in `finally`; the sweep matches the holder by its own
  `--record-dir`/`--socket` argv under that dir (never a bare pid — the outer review
  rejected a direct `os.kill(holder_pid)` as unverified identity), reads `record.json`
  in the same dir for the identity-checked agent group, and the test asserts
  `matched_pids == [started holder_pid]` and `residual_pids == []`.
- Deterministic failing-first cover: `test_teardown_stops_the_started_platform` starts
  codex, runs the real teardown leg, and asserts the holder dies (RED before the fix);
  every fixture class that starts holders gains a `tearDownClass` own-process sweep —
  holders matched by `--record-dir`/`--socket` under the suite's own temp root,
  agents via the suite's `record.json` pids plus command-name checks so a reused pid
  can never accuse a foreign process.

No production Runner lifecycle code changed; no assertion weakened; no sleep,
daemon, or global cleaner added.

## Files Changed

Three tracked files (`git diff --name-only origin/main...HEAD`):
`tests/contract/test-acp-contract.py` (+118/-9),
`tests/contract/test-acp-watch-contract.py` (+95/-1),
`CHANGELOG.md` (Unreleased entry, documentation docking — `c79d966`).

## Test Coverage

- `Issue34ModelSelectionAcpTests.test_teardown_stops_the_started_platform` — real
  codex holder through the real teardown leg; fails on the old fixture with
  "codex holder 10109 survived the fixture teardown".
- `AcpSessionFixture.tearDownClass` / `AcpWatchContractTests.tearDownClass` — assert
  zero live holders under the suite's own record root and zero live recorded mock
  agents; caught {10109+10110} and {10756+10757} RED before the fix.
- The watch accept-then-close test asserts the bounded sweep receipt matched exactly
  the orphaned holder and left zero residual pids.

## Validation

Recorded receipt: `verdict: pass`, `validated_candidate_hash`
`a57d8f9119972d171fa32f53f9138566ae9839a34a2e41f88b10e635df7304fa`. Exact command:

```
./scripts/render-skills.py --check && ./scripts/validate.sh
```

On the accepted candidate `b158e16` (rebased onto `88042cd`, post-#83 main):

- Focused: both key regressions rc=0 (`focused-test-*-88042cd.log`).
- Standalone: `test-acp-contract.py` 46 tests OK rc=0 (110.1s);
  `test-acp-watch-contract.py` 13 tests OK rc=0 (24.9s).
- `./scripts/render-skills.py --check` rc=0 PASS.
- Plain `./scripts/validate.sh` rc=0 — all suites OK incl. #83's SKIPPED reporting
  and issue-49 on the #80-fixed base; terminal sweep receipt
  `matched_pids=[]/residual_pids=[]` (`validate-plain-88042cd.log`).
- Process snapshots (`ps-*-88042cd.txt`): zero holders/mocks under
  `worktrees/bundle-82` or this run's `kaola-val.jTQP0y` root.
- Post-docking (`c79d966`): `test-issue-49-grok-bot-host.py` 43/43 (the only suite
  that reads CHANGELOG.md), render --check PASS, `git diff --check` clean. Full
  validate not re-run after the docs-only commit: `git diff b158e16..c79d966` is
  CHANGELOG.md only; all code/test bytes identical to the validated tree.
- Outer acceptance: independent review ACCEPTed `b158e16` (merge-base 88042cd,
  two-test-file diff, diff --check/render, both key regressions 1/1, plain validate
  green/zero-residue, standalone 46+13) before this finalization.

## Changed Paths

As reported by the finalize transaction (pending at write time — updated below
after the transaction runs):

```
CHANGELOG.md
tests/contract/test-acp-contract.py
tests/contract/test-acp-watch-contract.py
```

## Documentation Docking

`.cache/doc-docking.md` — **DOCKED**. Fixed: `CHANGELOG.md` (new Unreleased entry,
per house convention — #80's test-only fix has one). No impact: `README.md`,
`docs/conventions.md`, `docs/architecture.md`, `docs/api.md`,
`docs/runner-v2-dual-transport-design.md`, `AGENTS.md` (all mention the test
commands only; no fixture-teardown prose to correct).

## Follow-Up Items

None discovered requiring a new filing. Run-observed defect already fixed by
another run: the `test-issue-49` `TemporaryDirectory`/detached-git-maintenance
race surfaced during this run's first validate was diagnosed here and fixed by
Issue #80 (`maintenance.auto=false` fixtures) before this candidate's rebase;
verified green in the plain validate on this base. Foreign processes observed
but never touched: bundle-75's in-flight validate (`kaola-val.Cqx1xc`) ran the
old unfixed fixtures and showed the same 14+1 leak signature this fix removes —
that residue belongs to bundle-75's own run, not this one; issue-74's
`kaola-val.yjmpLq` run and named `kaola-501` sessions likewise untouched.

## Readiness

Accepted by independent outer review at `b158e16d8ea9e32e55e33d46b5a520fb16fdc4d8`
on merge-base `88042cd`; documentation docking added afterwards as `c79d966`.
Ready to archive and sink to `main` — the sink serializes behind bundle-69's
in-flight close-out per outer instruction; worktree/branch removed after the
sink, other runs untouched.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/bundle-82/.cache/doc-docking.md
- kaola-workflow/archive/bundle-82/.cache/final-validation.md
- kaola-workflow/archive/bundle-82/.cache/mirror-digest.json
- kaola-workflow/archive/bundle-82/.cache/origin/selection-record.json
- kaola-workflow/archive/bundle-82/evidence/diff-b158e16.patch
- kaola-workflow/archive/bundle-82/evidence/diff-ece2d06.patch
- kaola-workflow/archive/bundle-82/evidence/frozen-commits-88042cd.txt
- kaola-workflow/archive/bundle-82/evidence/frozen-commits.txt
- kaola-workflow/archive/bundle-82/evidence/ps-after-standalone-88042cd.txt
- kaola-workflow/archive/bundle-82/evidence/ps-after-standalone-rebase.txt
- kaola-workflow/archive/bundle-82/evidence/ps-after-standalone.txt
- kaola-workflow/archive/bundle-82/evidence/ps-after-validate-88042cd.txt
- kaola-workflow/archive/bundle-82/evidence/ps-after-validate.txt
- kaola-workflow/archive/bundle-82/evidence/ps-before-standalone-88042cd.txt
- kaola-workflow/archive/bundle-82/evidence/ps-before-standalone-rebase.txt
- kaola-workflow/archive/bundle-82/evidence/ps-before-standalone.txt
- kaola-workflow/archive/bundle-82/finalization-summary.md
- kaola-workflow/archive/bundle-82/mission-list.md
- kaola-workflow/archive/bundle-82/workflow-state.md
