# Finalization Summary — issue 444

## Delivered

Claude Code 2.1.316 adopted as the verified CLI under the owner PRIMARY HARD policy
(owner-harness-latest-adapt-primary-20261101). Candidate `dc8c1d11` (rebased from `21f00ae9` onto
origin/main `7831df6f`; the only base change was #439's droid-only `LAUNCH_BINARY_ENV_PLATFORMS`
entry, so the live receipts stay valid). `platforms/claude-code.yaml` `acp_verified_versions`
`cli=2.1.280;bridge=6c20f28;protocol=1` -> `cli=2.1.316;bridge=6c20f28;protocol=1`, a dated
measured clause appended to `acp_quirks`, generated Claude Code Skill files regenerated, CHANGELOG
entry with **Seats: restart not required**. No bridge, adapter or holder bytes changed; no hybrid
work (#436 Phase B stays research-only); no install, PATH, account or fleet change.

Basis: KPR's ACP path is the vendored `harukitosa/claude-code-acp` fork. Upstream HEAD
`6c20f2802e39` (2026-03-17) equals `acp_wrapper_pin`, with no upstream commits since, so the latest
adapter is already pinned. Upstream declares no Claude CLI range, so compatibility rests on the live
Runner run on the installed 2.1.316 binary, not on version inference. R `3d67cf69`'s 2.1.280 entry
was record-only (#153); this run is a live measurement on the same bridge pin.

Host acceptance: PASS for `dc8c1d11`.

## Evidence

- Receipts comment: https://github.com/KaolaBrother/kaola-project-runner/issues/444#issuecomment-6552894927
- Rebase note: https://github.com/KaolaBrother/kaola-project-runner/issues/444#issuecomment-6552911464
- Raw receipts (gitignored, canonical root): `.kaola/issue-444-claude-2.1.316-evidence/` (28 files:
  preflight, start, observe, capture, send/steer/wait, cancel, stop/status, resume, native JSONL
  summaries, validation logs including baseline `22-validate-baseline-67d60bc7.log`).
- Live path (session `claude-code-kaola-i444-acp316`, checkout Runner, launchd): T1
  `KPR444_T1_OK entrypoint=custom`; T2 `--resume` child + steer joined the running turn
  `KPR444_T2_OK prev=KPR444_T1_OK STEERED`; T3 cancel -> `cancelled`, child group gone; stop 0
  residual; `start --resume 9a826407-db28-4b3f-839b-ba72f8419fe6` -> `KPR444_T4_RESUMED
  first=KPR444_T1_OK`; final stop 0 residual; all 19 native user/assistant rows
  `entrypoint: custom`, `version: 2.1.316`.

## Known Failures and Unverified Scope

- `test-issue-50-runner-integration.py` (`test_manifest_and_generated_skill` package count) and
  `test-progressive-disclosure.py` (missing `lifecycle-recovery.md` link in the main Skill) fail
  identically on unmodified main `67d60bc7`: pre-existing baseline debt, not caused by this change.
  The Host owns reporting them as follow-up debt.
- Only this Mac (Mac17,6, arm64) and the default tier were measured; other machines and tiers are
  not covered.
- The installed worker Skill roots (`~/.claude`, `~/.config/devin`, `~/.cursor`, `~/.agents`) carry
  the pre-#436 bridge dist and refuse starts with `worker-skill-build-skew`; the probe used the
  checkout Runner path. No reinstall was done; the Host reports this to the Delegator separately.
- The probe unset the inherited `KAOLA_ACP_HEARTBEAT_HOST`, `KAOLA_ACP_HEARTBEAT_HOST_SOCKET` and
  `KAOLA_ACP_DISPATCHER` on its own commands only, so it ran as a standalone Runner session.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- platforms/claude-code.yaml
- skills/claude-code-kaola-project-runner/references/acp.md
- skills/claude-code-kaola-project-runner/scripts/platform.yaml

## Follow-Up Items

None filed by this run: the baseline suite debt and the installed-roots reinstall question are
Host/Delegator-owned reports per the Host acceptance message.

## Readiness

Accepted by Host; ready for finalize, merge sink and issue closure.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-444/.cache/final-validation.md
- kaola-workflow/archive/issue-444/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-444/finalization-summary.md
- kaola-workflow/archive/issue-444/mission-ledger.jsonl
- kaola-workflow/archive/issue-444/workflow-state.md
