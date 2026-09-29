# Finalization Summary — issue #231

## Delivered

This run follows the current #231 scope: "Guide supported DSH ACP harness installation and version checks."
The issue was closed and withdrawn at 06:48:01, then retitled and rewritten at 06:48:32 and
reopened at 06:48:34. The first candidate, `b24e048d`, provisioned the provider, model, and header
route. The Delegator rejected it for scope, and `eeace4c2` reverts it in full. None of its content
ships.

The delivered change, net against main, touches 5 files (+34/−3). It adds no code, protocol,
install, or release.

- `README.md` Install and begin gains the paragraph "dsh ACP harness". It explains that
  `agentInfo` (`deepseek-harness-acp/0.0.1`) does not name the harness build. It gives a one-line
  `node` check that resolves `@deepseek-ai/dsh`, `dsh-acp-app`, and `dsh-acp` versions from the
  real path of the `${DSH_BIN:-dsh}` launcher. It states that the verified harness is 0.1.7-rc.2
  (ACP protocol 1) and references the #227 evidence once. If the verified harness is already
  loaded, the Agent keeps it with its existing configuration.
- The packaging limit comes from the installed package metadata. The launcher `@deepseek-ai/dsh`
  pins `dsh-acp-app` to its own exact version, and `dsh-acp-app` pins `dsh-acp` the same way. So
  there is no standalone harness upgrade. An older harness means a whole-dsh upgrade, which the
  Agent reports as the required action for the user to decide. An already-installed verified copy
  can be selected with `DSH_BIN`, using #227's launch fix.
- ACP connectivity is checked with preflight, start (`transport.agent_info`), status, and exact
  stop, with no model turn. Model, provider, or credential failures are reported separately and
  never repaired. The Agent does not log in.
- In `platforms/dsh.yaml`, `acp_quirks` carries the same packaging fact. The rendered dsh
  `references/acp.md` and `scripts/platform.yaml` were regenerated.
- `CHANGELOG.md` gains one Unreleased bullet.

## Candidate

- Branch `workflow/issue-231`. Content commit `9578cf89`, merged with main `b0cf2652` as `82d1f02f`.
  The merge applied cleanly, and `render-skills.py --check` passed without re-rendering.
- Reviews: the Delegator rejected `b24e048d` for scope, then gave a personal-review PASS on
  `9578cf89`.

## Evidence

- `.cache/final-validation.md`: verdict pass, bound to hash `34297d7c…`. Checks run: render
  `--check`, plus `test-issue-98-dsh-acp.py`, `test-generated-skills.py`,
  `test-progressive-disclosure.py`, and `test-issue-218-preset-ids.py` at `82d1f02f`.
- The harness check command was run read-only on two layouts. In `/tmp/kpr-227/npm` (flat), all
  three packages are 0.1.7-rc.2. In `~/.local/lib/node_modules` (nested under dsh), all three are
  0.1.5-rc.3.
- Protocol and lifecycle evidence is reused from `kaola-workflow/archive/issue-227/dsh-0.1.7-compat-evidence.md`,
  with no new probes.

## Known failures / unverified scope

- `tests/contract/test-issue-118-seat-cap.py` has 1 failure. It also fails on main `aede714e` and
  `b0cf2652`, and this change does not cause it. It was filed as #233.
- `./scripts/validate.sh` was not run, per the owner's "affected checks only" instruction for a
  documentation and manifest-text change.
- No live dsh start was run in this run.
- A harness copy in a profile-level `node_modules` is not a verified layout. The #227 profile's
  `node_modules` was empty, and the README check resolves from the launcher.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- README.md
- platforms/dsh.yaml
- skills/dsh-kaola-project-runner/references/acp.md
- skills/dsh-kaola-project-runner/scripts/platform.yaml

## Follow-Up Items

- filed: #233 (P3). The test-issue-118 seat-cap contract test fails after the #229 orchestrator
  wording compression. I confirmed the issue is open with a non-empty body (1612 chars).
- README coordination with #232 happens in #232's own correction turn. This run did not touch it.

## Readiness

Ready to sink: this is a merge sink that closes #231 as completed.

## Finalize Findings

### residue_unattributed

The residue mirror did not copy the paths below out of the main checkout: this run's HEAD does not contain them. Presence in main, an untracked status, or a neighboring file this run committed is not evidence they belong to this run. Nothing was copied, staged, committed, deleted, reverted or relocated — they remain in the main checkout. Read them before the sink runs: commit what belongs to the run, leave what does not.

Paths left in the main checkout:

- docs/harness-acp-compat-2026-09-25.md
- docs/harness-acp-compat-2026-09-26.md
- docs/harness-acp-compat-2026-09-29.md

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-231/.cache/final-validation.md
- kaola-workflow/archive/issue-231/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-231/finalization-summary.md
- kaola-workflow/archive/issue-231/mission-ledger.jsonl
- kaola-workflow/archive/issue-231/workflow-state.md
