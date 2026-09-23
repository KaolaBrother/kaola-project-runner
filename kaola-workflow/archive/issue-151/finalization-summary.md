# Finalization Summary: Issue #151

## Delivered

- The three machine-env gaps that made `./scripts/validate.sh` exit 1 on a Studio dev machine
  (Xcode python 3.9, /bin/bash 3.2, no tmux) are version-tolerant: affected rows skip with an
  explicit, counted, named receipt — never silent green — and machines that have the prerequisite
  run the identical rows with unchanged assertions (detection, not weakening).
- `tests/contract/test-issue-51-runner-integration.py`: the two rows that drive a probe-loaded
  adapter child skip with a python >= 3.10 receipt on python 3.9, whose pathlib `_NormalAccessor`
  binds the probe's `os.open` patch as a method ("open() takes at most 3 positional arguments
  (4 given)").
- `tests/contract/test-zcode-heartbeat-contract.py`: the three `tmux has-session` rows (#105
  build-skew, #106 unreadable-root, #108 host-model) skip with a tmux-not-installed receipt
  (`shutil.which` detection, the idiom the #119/#123/#130 rows already use).
- `scripts/validate-watchdog.sh`: bash < 4 (no mapfile/BASHPID) prints one named receipt and runs
  the suite unwatched with its own exit status; the monitor body is unchanged and runs identically
  on bash >= 4. `tests/contract/test-issue-101-validate-watchdog.py` skips its two behavioral rows
  with a bash >= 4 receipt; the static validate.sh-coverage row still runs everywhere.
- One full-contract dev-machine prerequisites line in README.md ("Validation and evidence") and
  one Validation Policy bullet in AGENTS.md (tmux, bash >= 4 mapfile/BASHPID, python >= 3.10).

## Files Changed

- `tests/contract/test-issue-51-runner-integration.py`
- `tests/contract/test-zcode-heartbeat-contract.py`
- `tests/contract/test-issue-101-validate-watchdog.py`
- `scripts/validate-watchdog.sh`
- `README.md`
- `AGENTS.md`

## Test Coverage

- Focused runs on this Studio (python 3.9.6, /bin/bash 3.2.57, tmux missing):
  i51 `4/6 tests, 2 skipped (prerequisite receipts), 80 checks`, exit 0;
  heartbeat `20/23 tests, 3 skipped (prerequisite receipts), 432 checks`, exit 0;
  i101 `Ran 3 tests ... OK (skipped=2)`.
- Watchdog fallback probed directly: receipt on stderr, exit statuses 0 and 3 pass through,
  stdout clean; `bash -n` and `py_compile` clean; the #78 here-document scan stays green.
- Full `./scripts/validate.sh` on this Studio: exit 0 with zero `FAILED:` lines and every skip
  receipt visible and counted in the replayed lane output.

## Validation

classification: consumer-recorded
green: true
mode: final-validation
validation_command: ./scripts/validate.sh (exit 0; render-skills.py --check runs as its first
watched step: PASS)
validated_candidate_hash: 15000e031d67c8c1c26c57d8a041dbc02bcf717d86f7893ba8bd344211ec054f

agent validation recorded and bound to the worktree at commit 908aa10

## Changed Paths

- AGENTS.md
- README.md
- scripts/validate-watchdog.sh
- tests/contract/test-issue-101-validate-watchdog.py
- tests/contract/test-issue-51-runner-integration.py
- tests/contract/test-zcode-heartbeat-contract.py

## Documentation Docking

- `.cache/doc-docking.md`: `DOCKED` — README.md and AGENTS.md updated; CHANGELOG.md excluded by
  issue scope (no version bump, no release entry); docs/api.md, docs/architecture.md,
  docs/conventions.md, and the dated evidence records have no impact (checked, no fix needed).

## Follow-Up Items

- None filed. No run-discovered defect beyond #151 itself. The one receipt this Studio cannot
  produce (a bash >= 4 live watchdog trip) is inherent to the machine, proven by construction
  (the guard is a strictly conditional no-op on bash >= 4; the monitor body is unchanged), and was
  noted and accepted by the Host at acceptance.

## Measured

- `./scripts/validate.sh` from `.kw/worktrees/issue-151` at 908aa10: exit 0 (`VALIDATE_EXIT=0`,
  zero `FAILED:` lines; i51 4/6 tests + 2 receipted skips; heartbeat 20/23 + 3 receipted skips;
  i101 OK (skipped=2); grok-bot verify PASS; final sweep clean).
- `./scripts/render-skills.py --check` at 908aa10: PASS (10 workers + kaola-project-runner +
  kaola-delegator + grok-bot host: 1 bridge skill, 2555 B, budgets OK).

## Hypothesis

- None. The issue's three stated causes were confirmed by direct reproduction before the fix: the
  exact pathlib 3.9 traceback from the probe-patched `os.open`, `FileNotFoundError: 'tmux'`, and
  the monitor death at trip under bash 3.2 (no `mapfile` builtin).

searched: none required — no new defect filed beyond #151; at claim the duplicate probe
(`kaola-workflow-claim.js list-open`) showed issue #151 as the only open issue (1 hit).

final_status: ready

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-151/.cache/doc-docking.md
- kaola-workflow/archive/issue-151/.cache/final-validation.md
- kaola-workflow/archive/issue-151/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-151/finalization-summary.md
- kaola-workflow/archive/issue-151/mission-ledger.jsonl
- kaola-workflow/archive/issue-151/workflow-state.md
