# Finalization Summary: issue-227

## Delivered

Issue #227: verify DSH npm `latest` native ACP compatibility and update the supported-version records.

- Candidate: `a1586168` on `workflow/issue-227` (commits 4e4c0cd7, 9203b691, a1586168). Delegator final review: PASS on a1586168.
- `platforms/dsh.yaml` records conditional compatibility:
  `acp_verified_versions: cli=0.1.7-rc.2;agent=deepseek-harness-acp/0.0.1;protocol=1;condition=operator-declared-opencode-go-route`.
- Limitation (preserved verbatim in meaning): DSH 0.1.7-rc.2 is verified only when the operator declares the `opencode-go` route in the `acp` profile patch (`config.providers.opencode-go`: openai-completions api, baseURL, a models entry, and a static `x-opencode-session` header). Stock 0.1.7-rc.2 fails the default preset: model selection returns `-32602 unknown model option`, and send returns `400 MissingSessionID`. The recovery path lives in `launch_summary` (rendered to `platform.md` §Launch): `start`, check `config_application.model` is applied, check `observe`/`status` `currentValue`, then one `send`.
- KPR fix: `scripts/kaola-acp.py` now launches the `DSH_BIN` binary for dsh (`LAUNCH_BINARY_ENV_PLATFORMS`, `manifest_launch_command`) at both the main and resume paths, so preflight and the launched agent agree. Precedence unchanged: `--command` > `KAOLA_ACP_COMMAND` > manifest/tier command. Regression class `Issue227LaunchUsesDshBin` (4 tests), red before and green after.
- Rendered all Skills; Grok Bot pin at content stage (identical to main after #226); leakage-test exemptions for `x-opencode-session` and `opencode_go_api_key`.

## Evidence

- Evidence file: `kaola-workflow/issue-227/dsh-0.1.7-compat-evidence.md` (archived with this run).
- Live isolated lifecycle (`/tmp/kpr-227`, isolated home, real `~/.dsh` untouched): round trip, cancel, resume (same session id, model preserved, context recalled), default permission tool turn, exact stops with no residuals.
- Live argv proof of the DSH_BIN fix: session `dsh-kaola-i227-binfix`, agent argv `/tmp/kpr-227/npm/node_modules/.bin/dsh --profile acp` while PATH `dsh` was 0.1.5-rc.3.
- Final validation: `./scripts/render-skills.py --check && ./scripts/validate.sh` at a1586168, exit 0 (`.cache/final-validation.md`).

## Unverified Scope

- Workspace-write permission round trip on 0.1.7-rc.2 (only the default permission tool turn was run).
- Steering re-probe on 0.1.7-rc.2.
- `next` channel 0.2.0-rc.1: static inspection only (ACP, settings, pi-ai packages byte-identical to 0.1.7-rc.2; `dsh-base` adds otel/telemetry). Not adopted, not live-tested.
- Stock (undeclared) opencode-go route: known failing on 0.1.7-rc.2; not verified.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- hosts/grok-bot/INSTALL.md
- hosts/grok-bot/bridge.json
- hosts/grok-bot/kaola-delegator.md
- platforms/dsh.yaml
- scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/references/acp.md
- skills/dsh-kaola-project-runner/references/platform.md
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/platform.yaml
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- templates/grok-bot/accepted-revision.json
- tests/contract/test-generated-skills.py
- tests/contract/test-issue-98-dsh-acp.py

## Follow-Up Items

- Stock-route gap: not filed in this repo. It is an upstream DSH packaging gap (the stock `opencode-go` route lacks the model entry and session header), already recorded as the verification condition and the operator recovery path. Revisit when a newer DSH `latest` ships.
- Drift note: main moves after this sink. The #230 worktree was based on the pre-sink main; its owner rebases.

## Readiness

Ready to finalize and sink via merge; closes #227.

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
- kaola-workflow/archive/issue-227/.cache/final-validation.md
- kaola-workflow/archive/issue-227/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-227/dsh-0.1.7-compat-evidence.md
- kaola-workflow/archive/issue-227/finalization-summary.md
- kaola-workflow/archive/issue-227/mission-ledger.jsonl
- kaola-workflow/archive/issue-227/workflow-state.md
