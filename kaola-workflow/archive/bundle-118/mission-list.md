# Issue #118: worker seat count is a hard live-process cap; stop-before-start; only idle = awaiting acceptance; new task = new session

- item: Implement the seat-cap rule across Host-read surfaces (main Skill template + render-skills.py placeholders, heartbeat skeleton, zcode-host-dispatch, issue-dispatch), docs one-sentence summaries (architecture, zcode-host, README), amend test-issue-41:444-466, add tests/contract/test-issue-118-seat-cap.py registered in validate.sh, CHANGELOG Unreleased entry; budgets replace-not-append
  status: done
  dispatched: self, in worktree .kw/worktrees/bundle-118 on branch workflow/bundle-118; output lands as commits on that branch
  result: commit c337c86 on workflow/bundle-118 (16 files, +322/-74)
- item: Establish readiness — render --check, validate.sh 0 failed, new suite fails on base 34aaeae and passes on candidate; deliver candidate to Host for acceptance (no self-finalize)
  status: done
  dispatched: self, gates run in .kw/worktrees/bundle-118 against c337c86 content; log /tmp/validate-118.log
  result: render --check PASS budgets OK; test-issue-118 18 tests OK on candidate, 30 subtest failures on base 34aaeae; test-issue-41 amended FAILS on base output, OK on candidate; validate.sh exit 0, no FAILED/SKIPPED (8m07s). Candidate delivered to Host; awaiting acceptance, no self-finalize
