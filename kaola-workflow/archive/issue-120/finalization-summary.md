# Finalization — issue-120

Issue: #120 "A dsh worker cannot start inside a dsh Host (ACP initialize exits 1)"
Branch: workflow/issue-120 at e003029 (cd69ce5 + e003029), rebased onto main 29647b0
Status: READY — accepted by the Host 2026-09-22 (候选 1bc8618 PASS; rebased to e003029 at Host direction and re-validated)

## Delivered

- Root cause: dsh's `acp` bundle confines the model shell tool in macOS Seatbelt. The mode comes from
  `DSH_PERMISSION_MODE`, default `workspace-write`, which allows writes only to the workspace, /tmp and
  $TMPDIR. Every Runner start from that shell inherits the sandbox. As a result, a nested dsh boot write
  to `$DSH_HOME/profiles/acp/cordis.yml` fails with EPERM (exit 1), and the setuid /bin/ps cannot
  exec, so the holder's stop crashed with `holder-closed`.
- cd69ce5: a failed ACP start carries `error.stderr_tail` and `error.seatbelt_confined`. `run_ps` in
  the holder and the CLI falls back to libproc when `ps` cannot exec.
- e003029 (Host ruling Option 1): a dsh start launches with `DSH_PERMISSION_MODE=danger-full-access`.
  Precedence: caller `--mode`, then caller env, then the default. `bypassPermissions` maps to
  danger-full-access, and unknown values are refused before spawn. The receipt records
  `config_application.mode {applied_via: env, value, source}`.
- Corrected the dsh manifest, README and #88 contract claim that outside-workspace writes "run
  unattended with no approval gate to skip". The #98 probe had written to /tmp.

## Files Changed

CHANGELOG.md, README.md, platforms/dsh.yaml, scripts/kaola-acp.py, scripts/kaola-acp-holder.py,
tests/contract/test-issue-88-permission-defaults.py, tests/contract/test-issue-98-dsh-acp.py, plus
generated copies under skills/*/scripts/ (kaola-acp.py and kaola-acp-holder.py for all 10 workers)
and skills/dsh-kaola-project-runner/{references/acp.md, references/platform.md, scripts/platform.yaml}.

## Test Coverage

- test-issue-98-dsh-acp.py: 37/37. New #120 classes:
  - Issue120RunnerUnderAHostSeatbelt: real `sandbox-exec`, 4 cases.
  - Issue120ProcessTableWithoutPs: libproc rows equal ps rows, in both scripts.
  - Issue120DshPermissionModeDefault: 4 cases.
  - Issue120DshPermissionModeThroughTheRunner: 4 cases, where the agent reports the value it received.
- Baseline fd909e1 against the first 5 cases: 4 failed, including the holder-closed stop; the
  unconfined control passed.
- test-issue-88-permission-defaults.py: 42/42. The class is now `DshSkipAllIsTheLaunchVariable`.

## Acceptance legs

- Automated: `./scripts/validate.sh` rc=0 on e003029 (evidence/validate-e003029.log). Earlier runs:
  rc=0 on 1bc8618 and on 6e765a0. `./scripts/render-skills.py --check` PASS, budgets OK.
- Live, in a real dsh Host with DSH_HOME outside every writable root (evidence/):
  - Leg A (dsh default mode): reproduces #119. The receipt now shows seatbelt_confined=true and the
    EPERM stack.
  - Leg B (DSH_PERMISSION_MODE=danger-full-access set by hand): worker ready, clean stop.
  - Leg C (pure Runner default, build 1bc8618): Host shell sandbox_check=0 and ps rc=0; nested dsh
    worker ready; worker and Host stop `stopped: true, residual_pids: []`.
  - The real `~/.dsh` mtimes are unchanged, and the scratch credential copies were deleted.
- Not executed: the live legs were not re-run on e003029. The rebase changed only CHANGELOG context
  (#121/#123 entries); code bytes are identical to 1bc8618 (render --check PASS, same suites green).
- Host acceptance: PASS on 1bc8618 (Host message 2026-09-22).

## Issue statement walk

- "dsh worker start returned state: error (ACP initialize failed), exit_code=1": the cause is
  identified (diagnosis.md). The default now starts it: leg C, and the Issue120DshPermissionMode*
  tests.
- "Host then received the worker's terminated carrier": follows from the exit and is not a separate
  defect. The stop leak found alongside it is fixed (the sandbox stop test).
- "The same dsh Host with a claude-code worker passed": explained. That worker needs no write outside
  the sandbox, but its stop also stuck in `stopping`, which is now fixed.
- Hypothesis "environment inheritance": refuted. A correction comment was posted on #120
  (issuecomment-5764037096).

## Validation

Recorded via `kaola-workflow-validation-runner.js record`. verdict: pass, command:
`./scripts/validate.sh` (rc=0 on e003029) plus `render-skills.py --check` PASS.
validated_candidate_hash c9644b189cbf9359cca5d13e1e3289ae61a152d1908bbbd10d0404c7c7e01945.
run-chains: chains_config_missing (a consumer repo; the recorded final-validation.md gates).

## Changed Paths

Finalize precheck `changed_paths` (source-scoped, 28 paths): platforms/dsh.yaml;
scripts/kaola-acp.py; scripts/kaola-acp-holder.py; skills/<10 workers>/scripts/kaola-acp.py and
kaola-acp-holder.py; skills/dsh-kaola-project-runner/references/{acp.md,platform.md} and
scripts/platform.yaml; tests/contract/test-issue-88-permission-defaults.py;
tests/contract/test-issue-98-dsh-acp.py. The docs it leaves out are README.md and CHANGELOG.md, also
in the candidate.

## Documentation Docking

DOCKED — .cache/doc-docking.md.

## Follow-Up Items

- cc-in-cc (a claude-code worker inside a claude-code Host fails initialize with exit 1) is a different
  cause: sandbox_check=0 in a claude-code worker. Per the Host's instruction, it goes to the Delegator
  through the Host and is not filed from this run.
- None other run-discovered in repo code.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-120/.cache/doc-docking.md
- kaola-workflow/archive/issue-120/.cache/final-validation.md
- kaola-workflow/archive/issue-120/.cache/mirror-digest.json
- kaola-workflow/archive/issue-120/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-120/diagnosis.md
- kaola-workflow/archive/issue-120/evidence/A-host-send.json
- kaola-workflow/archive/issue-120/evidence/A-host-start.json
- kaola-workflow/archive/issue-120/evidence/A-host-stop.json
- kaola-workflow/archive/issue-120/evidence/A-probe.out
- kaola-workflow/archive/issue-120/evidence/B-host-send.json
- kaola-workflow/archive/issue-120/evidence/B-host-start.json
- kaola-workflow/archive/issue-120/evidence/B-host-stop.json
- kaola-workflow/archive/issue-120/evidence/B-probe.out
- kaola-workflow/archive/issue-120/evidence/C-host-send.json
- kaola-workflow/archive/issue-120/evidence/C-host-start.json
- kaola-workflow/archive/issue-120/evidence/C-host-stop.json
- kaola-workflow/archive/issue-120/evidence/C-probe.out
- kaola-workflow/archive/issue-120/evidence/probe.out
- kaola-workflow/archive/issue-120/evidence/probe.sh
- kaola-workflow/archive/issue-120/finalization-summary.md
- kaola-workflow/archive/issue-120/mission-list.md
- kaola-workflow/archive/issue-120/workflow-state.md
