# Finalization Summary — issue-147

Issue: #147 "Contract: read-only installed-platforms survey (login env, no agent start)"
Branch: workflow/issue-147 — candidate 77c63cb (feat 217f820 + fix 77c63cb)
Delivery: sink-merge to main (no PR, Owner boundary). Host ACCEPTED 77c63cb before finalize.

## Delivered
- `kaola-acp survey [--platform P] [--login-shell SHELL]` → one `kaola-acp-survey/1` object, exit 0: `{schema, login_env, platforms}`; one uniform row per platform (10, Runner order) with `status` present|absent|unknown, `installed`, `path`, `source` (binary_env|process_path|login_binary_env|login_path; ZCode process_env|login_env), `binary`, `binary_env`, `requires_env`, `process_path`, `login_path`.
- Login environment: one non-interactive `SHELL -l -c` from a fresh minimal env (stdin closed, 10 s bound, group-killed, post-kill read bounded), printing `/usr/bin/env -0` after a marker.
- Read-only: no agent, ACP session, holder, record root, or platform binary execution (no `--version`), so no model turn.
- ZCode keeps its existing explicit KAOLA_ZCODE_ENTRY/NODE rule (Host: kept as-is, noted to Owner).

## Acceptance walk (issue #147)
- Codex CLI + OpenCode in login PATH, no live sessions → present: test_login_path_install_without_sessions_is_present; live narrow-PATH receipt survey-narrow-path-77c63cb.json (PATH=/usr/bin:/bin → codex/opencode `source: login_path`); Host independent smoke.
- CLI uninstalled → absent: test_uninstalled_cli_is_absent; unreadable login env → `unknown`, never a false absent: test_unreachable_login_env_is_unknown_not_absent.
- No tmux/ACP holders, no model turns: test_survey_starts_nothing_and_runs_no_platform_binary (record root never created, `list --include-dead` [] before/after, fake codex/opencode/claude/tmux/npx/node never ran); Host smoke: `kaola-acp list` identical before/after.
- Stable machine-readable shape for Mac / peer Mac / iOS: test_output_shape_is_stable; table mirrors manifests: test_runtime_table_mirrors_every_manifest.
- Documented on Runner contract/skill surface: docs/api.md, README.md, worker Skill references/acp.md; test_survey_is_documented_on_the_contract_surfaces.
- Covers the ~10 Usage runtimes incl. Codex CLI and OpenCode; OpenCode Go is a provider route inside the opencode/dsh CLIs (documented), not a separate binary.
- Non-goals respected: no quota fetch; `kaola-acp list` unchanged; no App-side PATH hack.

## Files Changed
scripts/kaola-acp.py; scripts/validate.sh; tests/contract/test-issue-147-installed-survey.py (new); docs/api.md; README.md; CHANGELOG.md; templates/references/acp.md.tmpl; generated skills/*-kaola-project-runner/{scripts/kaola-acp.py,references/acp.md} (10 each).

## Test Coverage
tests/contract/test-issue-147-installed-survey.py — 10 tests, hermetic (fake login shell, empty invoking PATH, private record root), wired into validate.sh (python_suites_all + lane b).

## Validation
- Final (finalize, frozen 77c63cb): `./scripts/render-skills.py --check` rc=0 PASS budgets OK; `./scripts/validate.sh` rc=0, 0 FAILED lines (log validate-finalize-77c63cb.log); `git diff --check 52a5fae..HEAD` clean.
- Recorded: .cache/final-validation.md verdict pass, command `./scripts/render-skills.py --check && ./scripts/validate.sh`, validated_candidate_hash 10c366805a8656b70655b6f976406eb473a781f958ebbab07fb3bafd2d934480.
- Earlier run on same bytes: validate-77c63cb.log rc=0. Host independent: render --check rc=0, validate.sh rc=0 0 FAILED, live narrow-PATH smoke.
- Unexecuted: survey on a peer Mac / iOS consumer and a non-bash/zsh login shell (fish) — not measured.

## Changed Paths
CHANGELOG.md, README.md, docs/api.md, scripts/kaola-acp.py, scripts/validate.sh, templates/references/acp.md.tmpl, tests/contract/test-issue-147-installed-survey.py, and generated skills/{claude-code,codex,cursor-cli,devin,droid,dsh,grok,kimi-cli,opencode,zcode}-kaola-project-runner/{references/acp.md,scripts/kaola-acp.py} (27 paths; finalize --check reported dirty_paths: [], reasons: []).

## Documentation Docking
DOCKED — see .cache/doc-docking.md.

## Follow-Up Items
- None filed. ZCode presence remains env-explicit by existing contract; any app-bundle probe would be an Owner contract change (Host noted to Owner, no change requested).
- Out of scope, untouched: #146, #126, pending release.

## Status
READY — accepted, validated, docked; closes #147 on sink.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-147/.cache/doc-docking.md
- kaola-workflow/archive/issue-147/.cache/final-validation.md
- kaola-workflow/archive/issue-147/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-147/finalization-summary.md
- kaola-workflow/archive/issue-147/mission-ledger.jsonl
- kaola-workflow/archive/issue-147/survey-narrow-path-77c63cb.json
- kaola-workflow/archive/issue-147/workflow-state.md
