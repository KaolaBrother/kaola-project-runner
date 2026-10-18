# Finalization Summary — issue-351

## Delivered

Issue #351: one DSH role profile for both tiers, and the verified CLI pin moves to `0.2.1-rc.2`.

- `dsh/default` and `dsh/commandcode` share one profile, 225 characters: a fast, low-cost worker for self-contained tasks with clear goals, boundaries, and acceptance criteria; strong at 3D and frontend; one-pass complete features; iterative validation and self-repair; review each output; split a long chain. The OpenCode profile is unchanged.
- `platforms/dsh.yaml` `acp_verified_versions` is `cli=0.2.1-rc.2;agent=deepseek-harness-acp/0.0.1;protocol=1;condition=operator-declared-opencode-go-route`. A throwaway ACP initialize on CLI `0.2.1-rc.2` returned that agent name, version `0.0.1`, and protocol 1. `docs/api.md` states DSH >= 0.2.1-rc.1 is required for DeepSeek 1017.
- Rendered catalog, README preset rows, and `skills/dsh-kaola-project-runner/scripts/platform.yaml` match the platform file. `skills/kaola-project-runner/references/profile-catalog.md` is 8128 bytes, under the 8192-byte reference budget with room for the #49 rename probe.
- Seats: restart required. `platforms/dsh.yaml` is in the operator restart set. The Grok Bot bridge stays unpinned (`saveable: false`).

## Candidate

Branch `workflow/issue-351`, parent local `main` `77489f00eef49456b341113bc9f4244af9d86f0b`.

- `7306355796b98bf12361fdc9131f01eb15fe266b` — `Update the DSH profile text and verified CLI (#351)`
- `c7f1ab537b9d04262297f61d3f8ecce41a29e879` — `Shorten the DSH profile so the catalog probe fits (#351, #49)`

Acceptance candidate: `c7f1ab537b9d04262297f61d3f8ecce41a29e879`. Worktree clean. Not pushed. This finalize does not add an implementation commit.

Host acceptance: ACCEPTED.

## Evidence

- Full inventory `./scripts/validate.sh` (no `--suite`), worktree clean at `c7f1ab53`: 131 suites, exit 0, wall 1564.08 s. Log: `/tmp/kpr-run/full-validate-351-c7f1ab53.log` (`validate: candidate: c7f1ab53 (clean)`, `VALIDATE_EXIT=0`). The same commit is still the worktree HEAD, so that voucher is reused and the suite is not re-run.
- The first full gate on `73063557` failed `test-issue-49-grok-bot-host.py` because the 257-character profile left the catalog at 8192 bytes and the rename probe reached 8212. `c7f1ab53` shortened the shared profile to 225 characters (catalog 8128 bytes). The re-run above is the accepted gate.
- Mission ledger `kaola-workflow/.ledger/issue-351.jsonl`: two missions `done`. Those lines are not rewritten.

## Known failures and unverified scope

- No known product failure on `c7f1ab53`.
- Host boundary for this finalize: merge into local main only. Do not push. Do not close issue #351. Do not add a GitHub comment. Do not release, tag, install, or open a new issue. Keep-open is that deferral. Offline mode makes no forge call, so the claim label is not released here.
- Post-merge `./scripts/render-skills.py --write` and `--check` run on local main after the sink. No validate suite is re-run; the full gate already passed on this same commit.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- README.md
- docs/api.md
- platforms/dsh.yaml
- scripts/validate.sh
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/platform.yaml
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/references/profile-catalog.md
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- tests/contract/test-issue-345-dsh-commandcode.py
- tests/contract/test-issue-351-dsh-profile.py
- tests/contract/test-issue-98-dsh-acp.py

## Follow-Up Items

- None filed. No run-discovered defect requires a new issue. The #49 budget miss was fixed on this same branch before acceptance.

## Readiness

Host accepted the change. The full-gate voucher on `c7f1ab53` is reused. Local merge-sink and archive proceed. Issue #351 stays open. Publication to the remote waits for the Host.

## Finalize Findings

### claim_release_skipped_offline

This finalize released no claim: KAOLA_WORKFLOW_OFFLINE=1, so the release returned before making any forge call. Nothing local records whether this run was ever claimed online, so this does not assert the artifacts are there — but IF the claim was posted, the `workflow:in-progress` label and the `kw:claim` marker comment are still on the issues below. The marker expires after 24h; the label does not, and either one blocks a later claim of that issue until it is removed.

Issues whose claim release was skipped:

- #351

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-351/.cache/final-validation.md
- kaola-workflow/archive/issue-351/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-351/finalization-summary.md
- kaola-workflow/archive/issue-351/mission-ledger.jsonl
- kaola-workflow/archive/issue-351/workflow-state.md
