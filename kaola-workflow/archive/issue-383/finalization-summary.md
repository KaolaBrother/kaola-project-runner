# Finalization Summary — Issue #383

## Delivered

Implemented and repaired KPR #383 on `workflow/issue-383`: the client transport
for holder calls now has one monotonic absolute deadline with an explicit stage,
and a wedged holder answers `holder-timeout` instead of blocking indefinitely.

- `socket_request` records one `monotonic + timeout` deadline and recomputes
  `remaining` before `connect`, `sendall` and every `recv`; a nominal 30 s
  bound can no longer accumulate to 3 x 30 s.
- `holder-timeout` carries `stage` (`connect`/`send`/`read`) and `timeout_s`.
  `connect` and `send` report `outcome:not_sent`, `mutation_performed:false`,
  `mutation_status:not_started`; `read` and `holder-closed` report
  `outcome:unknown`, `mutation_performed:null`, `mutation_status:unknown`.
  A read-stage timeout is genuinely uncertain and may be admitted late; the
  `SIGCONT` probe showed the abandoned prompt completing with the exact
  `last_prompt.fingerprint`.
- Default client bounds: a send whose resolved wait is false and a start brief
  whose resolved wait is false (explicit `--no-wait` or the owning-Host default)
  get a 30 s admission bound; native steer 60 s; cancel/key 35 s;
  interrupt `max(cancel_timeout, timeout, 5) + 30 s` selected by the resolved
  holder op (`steer_interrupt`), not the CLI command; `send --wait` and `wait`
  stay unbounded; standalone `start --text` keeps its wait=true unbounded
  transport. `--timeout <= 0` is a typed `invalid-input` refusal.
- A start-brief failure whose brief may have been written keeps the request's
  `prompt_fingerprint` and `verify`; a clean no-write still omits both. The
  verify block names real surfaces: `status`/`last_prompt.fingerprint` for a
  prompt or an interrupt's follow-up prompt; capture's existing
  `steer_sent`/`steer_result` events for a native steer, with a written event
  never treated as consumption.
- The holder force-stop path skips `_cancel_pending_permissions()`, so a
  lock-wedged holder stops in seconds and a blocked send receives
  `acp-write-failed` with `mutation_performed:false`/`not_started`. The
  `op_prompt`/`op_steer` lock scope is unchanged and documented as known
  behavior.
- `scripts/kaola-recovery-routes.py` has a `holder-timeout` self-route;
  `docs/api.md` carries the timeout matrix and the #381 admission-window
  correction; `CHANGELOG.md` records the change.
- `tests/contract/test-issue-383-holder-timeout.py` has 29 cases, including
  real SIGSTOP/SIGCONT and trickle-server probes, real CLI interrupt dispatch,
  a real start-brief 30 s timeout, and the lock-wedge force-stop recovery.
  `tests/contract/test-issue-379-receipt-mutation.py` was updated for the
  send-stage `false` and read-stage `null`; the suite is registered in
  `scripts/validate.sh`.

Candidate: `c4367b114808e1f41435baddad1a699a79e87094` on
`workflow/issue-383`; prior candidate `f519c036906ab25eac397147feda6e7237ea3fdc`;
base `a85d2c0002d700d24e27e23051ef599fcfe23e42`. No tag, release, publish,
install, or KPM-side operation was performed.

## Acceptance Evidence

- Host acceptance of `c4367b11`: F1/F2/F3/P3 independently confirmed; Host
  rerun measured `interrupt_default` 35.2 s with `timeout_s=35.0`, exact
  `send30`/`key35`/`cancel35`/`steer60`, `cancel80` waited the full 110 s,
  and fingerprint/verify were present.
- Clean-env review probes at `c4367b11` (`REVIEW_TARGET` = the worktree,
  inherited `KAOLA_*` stripped):
  - F1: `interrupt_default` 35.129 s, `interrupt_cancel80` 110.139 s;
    full bounds matrix send30 30.142 s, steer60 60.143 s, cancel35 35.145 s,
    key35 35.144 s. Evidence: `/tmp/kpr383fix/interrupt-fix.json`,
    `/tmp/kpr383fix/bounds-matrix.log`, `/tmp/kpr383fix/f1_interrupt.py`.
  - F2: real `start --stdin --no-wait` returned in 30.938 s with
    `holder-timeout/read/30`, `mutation_performed:null`, `mutation_status:unknown`,
    `brief_delivered:false`, and both `prompt_fingerprint` and `verify`.
    Evidence: `/tmp/kpr383fix/start-brief30.json`,
    `/tmp/kpr383fix/f2_start_brief.py`.
  - F3: successful interrupt has `steer_consumed:true`,
    `steer_fingerprint == new_prompt_fingerprint`, status has no
    `steer_fingerprint` but `last_prompt.fingerprint` equals it, and capture's
    `steer_interrupt` event carries the same fingerprint. Native steer capture
    events (`steer_sent` fingerprint -> `steer_result` request_id/outcome)
    are covered by the suite. Evidence:
    `/tmp/kpr383fix/steer-verification-surfaces.json`,
    `/tmp/kpr383fix/f3_steer_verify.py`.
- Clean-env validation at `c4367b11`, exit 0:
  `python3 /tmp/kpr383rev/clean-env.py /opt/homebrew/bin/bash scripts/validate.sh
  --suite test-issue-383-holder-timeout.py
  --suite test-issue-379-receipt-mutation.py
  --suite test-issue-344-start-brief.py
  --suite test-acp-contract.py`
  - #383 29/29 (72.368 s), #379 19/19 (11.568 s), #344 10/10 (9.932 s),
    acp-contract 87/87 (138.917 s); render check PASS.
  - Separate #380 run: 20/20 (57.293 s).
  - Log: `/tmp/kpr383fix/validation-clean.log`.
- Validation record: `kaola-workflow/issue-383/.cache/final-validation.md`
  (candidate hash `9224e321b443c4cce2c905b444cdec11c9b65f767761ad95d0bcf20f76a2abe6`).

## Known Failures and Unverified Scope

- No full-inventory `validate.sh` run; the selected suites cover the changed
  client transport, holder force-stop, start brief, interrupt/native steer,
  recovery route, receipt contract and adjacent #379/#380/#344 paths.
- No live external platform UAT; all failure, SIGSTOP, SIGCONT, trickle and
  force-stop probes used temporary mock holders/agents.
- Natural kernel `connect` timeout was not induced on this macOS host; the
  connect stage is covered by an injected `socket.timeout` plus real connect
  refusal evidence. Real send/read timeouts and the absolute deadline are
  covered by real servers.
- `wake` without `--timeout` remains unbounded, unchanged by this issue.
- A standalone `start --text` resolves wait=true and remains unbounded; only a
  resolved wait=false brief gets the 30 s admission bound.
- `scripts/kaola-acp-holder.py` is in the operator restart set, so a running
  holder keeps the old force-stop behavior until it restarts.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/api.md
- scripts/kaola-acp-holder.py
- scripts/kaola-acp.py
- scripts/kaola-recovery-routes.py
- scripts/validate.sh
- skills/antigravity-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/antigravity-kaola-project-runner/scripts/kaola-acp.py
- skills/antigravity-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- tests/contract/test-issue-379-receipt-mutation.py
- tests/contract/test-issue-383-holder-timeout.py

## Follow-Up Items

- No new follow-up issue was filed by this run.
- Holder restart remains an operational note.
- No release, tag, publish, install, or KPM-side operation is part of this
  finalization.

Final readiness: ready. Merge sink to `main`, close #383 with the
Host-supplied closing comment after publication is verified, archive under
`kaola-workflow/archive/issue-383/`, and remove the run worktree.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-383/.cache/final-validation.md
- kaola-workflow/archive/issue-383/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-383/finalization-summary.md
- kaola-workflow/archive/issue-383/mission-ledger.jsonl
- kaola-workflow/archive/issue-383/workflow-state.md
