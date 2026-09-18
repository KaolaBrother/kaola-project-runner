# Finalization summary — Issue #78

Run `issue-78`, branch `workflow/issue-78`, base main `f6be8a3`, sink `merge`.
Owner ACCEPT given on frozen candidate `9b40638`; `c8d9fd9` adds only the
finalization CHANGELOG docking on top.

## Delivered

Issue #78 asked why two Issue #73 refusal cases intermittently burned the whole
60 s `run_cli` budget under load and left an orphaned `kaola-tmux.sh ... start`
with no children that died to a single SIGTERM — and asked for a minimal repair
that neither inflates the timeout nor adds a retry or a new guard.

The cause is a **bash here-document deadlocking against its own pipe**. Bash
writes a heredoc body up to `HEREDOC_PIPESIZE` (4096 bytes) into a pipe from the
forked child *before* `exec`, so one process holds both ends and nothing drains
it. macOS hands out 512-byte pipes under system-wide pipe-KVA pressure, so any
larger body blocks in `write()` forever. `emit_json` (883 bytes) is the last
thing the canonical-root refusal path does, while an accepted start ends at
`die`, a plain `printf` — which is why the cases doing strictly *less* work hung
and the ones doing more passed, in the same run, on a machine that stayed fast.

`scripts/kaola-tmux.sh` now carries no here-document and no here-string at all.
No timeout raised, no retry, no classifier or guard added.

The issue's own stated hypothesis (process and `git` startup cost) was refuted by
its own log, and both correlations it noted — `child_a`, and "first two methods of
the class" — are coincidence. A correction comment recording this was posted to
the issue before closure.

## Files Changed

Hand-written, 5 files:

| file | change |
|---|---|
| `scripts/kaola-tmux.sh` | all 10 here-documents removed: 8 Python programs to `-c`, `usage()` to `printf`, one `read` heredoc to a process substitution; 11-line rationale comment |
| `scripts/validate.sh` | +2 lines registering the new guard in `python_suites_b` and `python_suites_all` |
| `tests/contract/test-issue-78-heredoc-deadlock.py` | new structural contract suite (136 lines) |
| `tests/contract/test-acp-contract.py` | python stub accepts the `-c` calling convention; assertions unchanged |
| `docs/conventions.md` | 7-line rule under *Shell safety* |
| `CHANGELOG.md` | `## Unreleased` entry (finalization docking) |

Generated: the nine `skills/*/scripts/kaola-tmux.sh` copies, via
`./scripts/render-skills.py --write`.

## Test Coverage

- `tests/contract/test-issue-78-heredoc-deadlock.py` — asserts the shared
  entrypoint and all nine generated copies carry no here-document or here-string,
  and that the nine copies are byte-identical to the source. **Failing baseline
  proven**: restoring `f6be8a3` produces `FAILED (failures=10)`, naming every
  offender with its size including `line 41 <<PY (883 bytes)`.
  Detects every tag spelling bash accepts (`<<TAG`, `<<'TAG'`, `<<"TAG"`,
  `<<\TAG`, `<<'T A G'`, `<<2TAG`, `<<-TAG`, `<<<`) while excluding
  `$((1 << n))` and `#` comments.
- `tests/contract/test-issue-73-canonical-root.py` — unchanged, **0 diff lines**.
  The Issue #73 guard assertions and the Issue #77 `addCleanup` holder force-stop
  survive untouched. 29 tests OK in ~22–25 s (the reported failing run was 145 s).

## Validation

Recorded receipt (`.cache/final-validation.md`):

    verdict: pass
    validation_command: ./scripts/render-skills.py --check && python3 tests/contract/test-issue-78-heredoc-deadlock.py && python3 tests/contract/test-issue-73-canonical-root.py
    validated_candidate_hash: 50f05b88d07e906c264c38f6ed542945fdf968f0902a1ff889382ab2ba10a096

Finalize transaction check reported `validation: chains_green`, `dirty_paths: []`.

**Acceptance legs**

| leg | command | outcome |
|---|---|---|
| automated (diff-scoped chain) | as recorded above | exit 0 |
| automated (full suite) | `./scripts/validate.sh` | **exit 1 — known-red, see below** |
| independent review | `code-reviewer` on frozen `9632571` | no defects |
| owner re-verification | 78-guard 3/3, #73 29/29, `render --check` | PASS |
| live tmux smoke per platform | — | **not executed** (see Not Executed) |

**Known-red, owner-accepted exception.** `./scripts/validate.sh` exits 1 at the
merged tree on `test-issue-49-grok-bot-host.py` alone. This is **pre-existing and
not caused by this change**: the same
`OSError: [Errno 66] Directory not empty: .../repo/.git` reproduces **2/2 on
untouched `f6be8a3`** and **3/3 on the candidate**. The owner accepted this
explicitly and directed that it be recorded as known-red rather than reported as
green. Filed as **#80**. Receipt: `evidence/verification.md` §5 and
`evidence/validate-final.log`.

**Not executed.** No end-to-end behavioural reproduction of the deadlock was
staged: it requires machine-wide pipe-KVA pressure, which would deadlock other
agents' shell scripts on this shared machine. The owner ruled it out. The causal
chain rests instead on live `sample` stacks of five already-hung processes, the
bounded pipe-capacity measurement, and the measured heredoc sizes. AGENTS.md's
"live tmux smoke per platform" was not run — this change alters no transport
behavior and refusal receipts are byte-identical, but it is recorded as
unexecuted rather than waived silently.

## Changed Paths

Reported by the finalize transaction:

    scripts/kaola-tmux.sh
    scripts/validate.sh
    skills/claude-code-kaola-project-runner/scripts/kaola-tmux.sh
    skills/codex-kaola-project-runner/scripts/kaola-tmux.sh
    skills/cursor-cli-kaola-project-runner/scripts/kaola-tmux.sh
    skills/devin-kaola-project-runner/scripts/kaola-tmux.sh
    skills/droid-kaola-project-runner/scripts/kaola-tmux.sh
    skills/grok-kaola-project-runner/scripts/kaola-tmux.sh
    skills/kimi-cli-kaola-project-runner/scripts/kaola-tmux.sh
    skills/opencode-kaola-project-runner/scripts/kaola-tmux.sh
    skills/zcode-kaola-project-runner/scripts/kaola-tmux.sh
    tests/contract/test-acp-contract.py
    tests/contract/test-issue-78-heredoc-deadlock.py

    dirty_paths: []

## Documentation Docking

`.cache/doc-docking.md` — status **DOCKED**. `CHANGELOG.md`,
`docs/conventions.md` and an in-file comment updated; `README.md`,
`docs/api.md`, `docs/architecture.md`, the dual-transport design record, the host
contracts and the dated live-verification records are all no-impact, because no
public signature, JSON field, help text, exit status, or environment variable
changed (refusal receipts byte-identical, `usage()` output `cmp`-identical).

## Follow-Up Items

- **filed: #80** (P3) — `test-issue-49-grok-bot-host.py` teardown `Errno 66`
  makes `validate.sh` red on main and hides later suites in its lane.
- **owner-owned, not filed by this run** — 63 here-documents repo-wide sit in the
  513..4096-byte deadlock window, including `scripts/install-local.sh` (one body
  2765 bytes) and ten `tests/contract/*.sh` suites. The owner scoped this run to
  the shared entrypoint and said they would open the separate issue themselves.
  Live proof it is real: `install-local.sh` from the issue-71 run was hung for
  over 4 h, and a `status --help` pair for 34 h, during this run.
- **not a defect, noted** — `python3 -c` now carries up to 908 bytes of program
  text in argv, so `ps -ww` output for these children is noisier. Nothing in the
  repo matches on `kaola-tmux.sh` argv, so there is no functional impact.

## Readiness

READY. Owner ACCEPT recorded on `9b40638`; only finalization docking added since.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-78/.cache/doc-docking.md
- kaola-workflow/archive/issue-78/.cache/final-validation.md
- kaola-workflow/archive/issue-78/.cache/mirror-digest.json
- kaola-workflow/archive/issue-78/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-78/evidence/derived-from-archived-log.md
- kaola-workflow/archive/issue-78/evidence/mission1-kill-receipt.txt
- kaola-workflow/archive/issue-78/evidence/residue-receipt.txt
- kaola-workflow/archive/issue-78/evidence/root-cause.md
- kaola-workflow/archive/issue-78/evidence/verification.md
- kaola-workflow/archive/issue-78/finalization-summary.md
- kaola-workflow/archive/issue-78/mission-list.md
- kaola-workflow/archive/issue-78/workflow-state.md
