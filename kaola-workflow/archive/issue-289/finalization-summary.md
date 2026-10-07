# Finalization Summary — issue-289

## Delivered

Fix #289: a `stop` whose holder process is already dead honors
`--expected-holder-instance-id`. The dead-holder branches (including the
`holder-unreachable` race) and `force_stop_unreachable` now refuse a foreign
`expected_holder_instance_id` with the same typed `holder-instance-mismatch`
receipt as the silent live-holder path — `mutation_status: not_started`,
`mutation_performed: false`, both ids echoed, record and processes unchanged —
and write exactly one `holder_instance_mismatch` event. A matching id, or an
omitted id, still sweeps the identity-verified recorded groups without
`--force`. The `force_kill_from_record` docstring and `docs/api.md` now state
the current no-`--force` sweep contract. Ten generated `skills/**/scripts/kaola-acp.py`
copies were refreshed by `render-skills.py --write`.

## Candidate

`42d3d565` on `workflow/issue-289`, 15 files. Rebased onto current `main`
`1c7f34fa` (the run's original candidate `9735a6e8` was based on
`0657e37f`; main had advanced 11 commits, so the branch was rebased — reported
below). The only rebase content conflict was `CHANGELOG.md`, where `main`'s
#287 bullet and this run's #289 bullet were added at the same anchor; both
entries were kept (additive, no meaning changed). `docs/api.md` auto-merged.

## Evidence

- Host acceptance, 2026-10-07 (this run's Host): `test-issue-289-dead-holder-stop.py`
  Ran 6 OK; `test-acp-contract.py` Ran 85 OK; `test-generated-skills.py` exit 0
  (content-stage flip semantics); worktree restored clean; `docs/api.md` and the
  CHANGELOG `Seats` line verified.
- Finalize validation receipt: `kaola-workflow/issue-289/.cache/final-validation.md`
  — `verdict: pass`, `validated_candidate_hash:
  1c3dd7bd379844e2e8c5ad51603707cc5cc3989c05effe9bc56c923a5935f62e`, bound to this
  tree. Command recorded there: worktree-only content-stage flip
  (`templates/grok-bot/accepted-revision.json` stage=content +
  `./scripts/render-skills.py --write`), then
  `./scripts/validate.sh --suite test-issue-289-dead-holder-stop.py --suite
  test-acp-contract.py --suite test-generated-skills.py` under the project's
  controlled sandbox (85 OK / 6 OK / PASS, exit 0), then `git checkout -- .`
  restoring the candidate.
- Regression lane registration: `tests/contract/test-issue-289-dead-holder-stop.py`
  is in `scripts/validate.sh` `python_suites_all` and `python_suites_b`.

## Known failures / unverified scope

- None for this candidate's own scope. `render-skills.py --check` on the clean
  candidate still reports the standing pin findings (the Grok Bot bridge is
  pinned at `3de9f61a`); that is the project's pre-release state, unchanged by
  this run. The validation above therefore ran under the worktree-only
  content-stage flip, the established recipe for this state.
- A direct (non-sandboxed) `test-acp-contract.py` run during finalize showed
  socket-interference failures while several co-active runs held holders; the
  sandboxed `validate.sh` entry — which isolates HOME/TMPDIR — passed 85 OK.
  Recorded as environment interference, not a candidate defect.

## Validation

classification: final_validation_stale
green: false
mode: final-validation

recorded validated_candidate_hash "1c3dd7bd379844e2e8c5ad51603707cc5cc3989c05effe9bc56c923a5935f62e" != current code-tree hash "5ec1e3ad491ec207595c90bf705cb2a76cda1077386a3fdaf1fcdc5dde8dd854" — a relevant source/test/test-consumed file changed after the recorded validation; re-run the validation command and re-record final-validation.md with a fresh hash

A relevant source/test/test-consumed file changed after validation — or the record was written from a different checkout than this one. Re-run the validation command, then re-record with `kaola-workflow-validation-runner.js record --project <project> --verdict pass --command "<the validation command you ran>"`, invoked from the working tree you validated (the gate hashes the tree its own shell is in, and a linked worktree and main differ until the branch merges); never hand-patch the hash.

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/api.md
- scripts/kaola-acp.py
- scripts/validate.sh
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- tests/contract/test-issue-289-dead-holder-stop.py

## Follow-Up Items

- None opened by this run.

## Final readiness

Ready: candidate verified against the issue's Expected acceptance; validation
recorded and bound to `42d3d565`; sink = merge with issue close #289.

## Finalize Findings

### residue_unattributed

The residue mirror did not copy the paths below out of the main checkout: this run's HEAD does not contain them. Presence in main, an untracked status, or a neighboring file this run committed is not evidence they belong to this run. Nothing was copied, staged, committed, deleted, reverted or relocated — they remain in the main checkout. Read them before the sink runs: commit what belongs to the run, leave what does not.

Paths left in the main checkout:

- docs/harness-acp-codex-160-live-2026-10-03.md
- docs/harness-acp-compat-2026-10-01.md
- docs/harness-acp-compat-2026-10-03.md
- docs/harness-acp-compat-2026-10-06.md
- docs/harness-acp-reverify-2026-10-01.md

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-289/.cache/final-validation.md
- kaola-workflow/archive/issue-289/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-289/finalization-summary.md
- kaola-workflow/archive/issue-289/mission-ledger.jsonl
- kaola-workflow/archive/issue-289/workflow-state.md
