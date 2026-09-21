# Finalization summary — issue-112

Issue: #112 "Upgrade the OpenCode adapter for OpenCode V2 (2.0.11)". Branch `workflow/issue-112`, candidate `9708980` (on top of `34c0e5c`), base main `7fc6fe3`.

## Delivered

- **Root cause.** A forward proxy (`HTTP_PROXY`/`HTTPS_PROXY`, no `NO_PROXY`) swallowed OpenCode V2's loopback HTTP self-connection.
  - Upstream, V2 ACP is an unported legacy shim (anomalyco/opencode#35457), and the V1 loopback-bypass fix (#31096) was lost in the copy.
  - The issue's 401/server-password hypothesis and the "wedged managed service" reading were both refuted by a clean A/B.
- **V2 adapter.**
  - The launch line is now `opencode <repo> --auto`: `--mini` was removed, and top-level `--model`/`--variant` are rejected on V2.
  - `OPENCODE_CONFIG_CONTENT` is written in the V2 shape; 2.0.11 ignores it (#50236).
  - TUI chrome detection is fixed: `ctrl+p commands` vs the V1 `ctrl+p cmd`.
- **Manifest.** Only live-verified V2 values: `acp_verified_versions cli=2.0.11;protocol=1`, and the measured no-skip-all choice set (`allow_once`/`allow_always`/`reject_once`).
- **Child-scoped loopback bypass (Host ruling, round 2).** Applied on both transports: ACP via `kaola-acp.py` `agent_environment()`, PTY via the adapter `-e` channel.
  - Append-only and loopback-only; a no-op without a proxy.
  - The Runner's own environment is untouched.
  - Preflight reports `loopback=direct|excluded|ensured`.

## Files Changed

- Source: `platforms/opencode.yaml`, `scripts/adapters/opencode.sh`, `scripts/kaola-acp.py`.
- Docs: `CHANGELOG.md`, `docs/api.md`.
- Tests: `tests/contract/test-issue-24-opencode-pty-bypass.py`, `tests/contract/test-issue-88-permission-defaults.py`, `tests/contract/test-issue-22-bypass-all-approvals.py`, `tests/contract/test-adapters.sh`.
- Generated (render-skills.py --write): `skills/opencode-kaola-project-runner/**`, plus the vendored `skills/*/scripts/kaola-acp.py` ×10.

## Test Coverage

- **test-issue-24:** 22 tests.
  - Pins `<repo> --auto` and forbids `--mini`/`--model`/`--variant` in the launch argv.
  - `Issue112LoopbackProxyBypass` (7 tests) runs one shared 8-case table through both the Python and bash implementations. It also checks that the Runner env is untouched, that the fix is scoped to opencode, the PTY with and without a model, and the three preflight states.
- **test-issue-88:** 42+ tests, including the measured V2 choice set pinned against `cli=2.0.11`.
- **test-issue-22 and test-adapters.sh:** updated to the V2 launch shape.

## Validation

- Chain runner: `chains_config_missing` (a consumer repo with no `test:kaola-workflow:*` scripts). Finalize therefore gates on the agent-recorded `.cache/final-validation.md`.
- Recorded: verdict **pass**, `validated_candidate_hash 4c0cf32b157b5f4a308e5ba698cb7c312617a7b5b5017bc44ff8e7ee77aebece`, candidate `9708980`.
- Command: `./scripts/render-skills.py --check && env -u KAOLA_ZCODE_ENTRY -u KAOLA_ZCODE_NODE -u KAOLA_ACP_DISPATCHER -u KAOLA_ACP_HEARTBEAT_HOST -u KAOLA_ACP_HEARTBEAT_HOST_SOCKET ./scripts/validate.sh`.
- Outcome: render PASS with budgets OK; validate exit 0, 0 FAIL lines (log `/tmp/kpr112/validate-112-final.log`).

## Acceptance legs

- **Automated:** the render and validate results above, run on the frozen candidate `9708980`.
- **Live, PTY:** session `i112-smoke`.
  - `start` → `observed` → `sent` → reply `I112_PTY_OK` captured → `stopped`.
  - On a fresh private tmux server, the TUI came up with the injection, where without it it hung at "Starting background server...".
- **Live, ACP:** session `opencode-KPR-i112-acpsmoke`, default transport, caller `NO_PROXY` unset.
  - `start` → `observe` → `send` (`turn_completed`/`end_turn`/`I112_ACP_OK`) → `capture` → `stop` (`stopped: true`, exit 0, no residual pids).
  - The first start's turn failed with `provider.no-route` on the account's native default model. This is account-level (#50236), not a transport fault. The restart used `--model zhipuai-coding-plan/glm-5.3 --effort high`.
- **Host acceptance:** all nine ACs, on the Host's own evidence.
- **Independent final review:** Fable PASS (issuecomment-5754696645).
- **Unexecuted:** none. Native steering on 2.0.11 was not probed; it is recorded as `unknown` by design (steering is owned by #65).

## Issue walk (#112 acceptance criteria)

1. **Blocker resolved:** a live ACP round trip through the Runner (evidence above), with the root cause recorded in the issue comments (issuecomment-5754404909, issuecomment-5754600824).
2. **Manifest carries only live-verified V2 values:** `platforms/opencode.yaml`, pinned by test-88 and test-24.
3. **Launches on 2.0.11:** the PTY smoke above plus the `test_opencode_pty_launch_drops_the_v1_only_flags` test.
4. **Measured permission position in `acp_quirks`:** `allow_once`/`allow_always`/`reject_once`, no skip-all.
5. **Contract tests updated:** test-24, test-88, test-22, test-adapters.
6. **Render --check with budgets holding:** PASS.
7. **validate.sh in the foreground:** exit 0.
8. **Live V2 smoke through the Runner:** PTY and ACP (above).
9. **Wedged service:** a misdiagnosis caused by the proxy. The real upstream wedge (#41696) is out of Runner scope.

## Changed Paths

Reported by `finalize --check --json` (ok: true, reasons: [], dirty_paths: []). The list is 22 source-scoped paths:

```
platforms/opencode.yaml
scripts/adapters/opencode.sh
scripts/kaola-acp.py
skills/{claude-code,codex,cursor-cli,devin,droid,dsh,grok,kimi-cli,opencode,zcode}-kaola-project-runner/scripts/kaola-acp.py
skills/opencode-kaola-project-runner/references/{acp,platform,steering}.md
skills/opencode-kaola-project-runner/scripts/adapters/opencode.sh
skills/opencode-kaola-project-runner/scripts/platform.yaml
tests/contract/test-adapters.sh
tests/contract/test-issue-22-bypass-all-approvals.py
tests/contract/test-issue-24-opencode-pty-bypass.py
tests/contract/test-issue-88-permission-defaults.py
```

`CHANGELOG.md` and `docs/api.md` also changed, but the transaction's source-scoped list omits docs; see Documentation Docking.

## Documentation Docking

`.cache/doc-docking.md` → DOCKED.

## Follow-Up Items

- **filed: #114 (P3, bug):** the preflight receipt drops its base fields on every platform. This is a pre-existing defect discovered during the run; the Host ruled it out of scope for v0.5.5. Confirmed open with a non-empty body (1686 chars).
- **Not filed, account-level:** the native ACP default `opencode/deepseek-v4.1-flash` has no route on this account (upstream #50236). It is recorded in the closing comment. Per the Fable review, a manifest caveat is only warranted if it recurs on other accounts.
- **Not filed, documented limit:** the PTY injection is evaluated against the caller env, so a pre-existing tmux server carrying a proxy the caller lacks is not covered. This is stated in the adapter comment (Fable: non-blocking).

## Readiness

READY: all 8 missions done, Host-accepted, Fable PASS, validation recorded, DOCKED.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-112/.cache/doc-docking.md
- kaola-workflow/archive/issue-112/.cache/final-validation.md
- kaola-workflow/archive/issue-112/.cache/mirror-digest.json
- kaola-workflow/archive/issue-112/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-112/finalization-summary.md
- kaola-workflow/archive/issue-112/mission-list.md
- kaola-workflow/archive/issue-112/research-v2-acp.md
- kaola-workflow/archive/issue-112/workflow-state.md
