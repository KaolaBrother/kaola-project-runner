# Finalization Summary — issue-338

## Delivered

Issue #338: a plain `start` of `dsh/default` and `opencode/default` (no `--effort`, tier `default`) applies effort `max`.

- `platforms/dsh.yaml`: `default_model_effort: "max"` and `default_model_parameters: "effort=max via ACP option reasoning_effort"`.
- `platforms/opencode.yaml`: `default_model_effort: "max"` and `default_model_parameters: "effort=max via ACP option effort"`.
- `scripts/adapters/dsh.sh` and `scripts/adapters/opencode.sh`: `ADAPTER_DEFAULT_MODEL_EFFORT="max"`.
- The runner already takes `<tier>_model_effort` in `selection_basis` and sends it through `acp_effort_config_id` (`reasoning_effort` for dsh, `effort` for opencode). No production change to `scripts/kaola-acp.py` was required for this preset.
- `tests/contract/test-issue-338-preset-effort-max.py` asserts both manifest strings, the README rows, and that a plain start sends exactly `reasoning_effort=max` / `effort=max` with `config_application.effort.applied` true and `effective_selection.effective_effort` `max`. Registered in `scripts/validate.sh` `python_suites_all` and `python_suites_b`, immediately after `test-issue-324-wake-fixes.py`.
- `tests/contract/mock-acp-agent.py` keeps a published model `currentValue` when a later effort set arrives, so the OpenCode advertisement proof still holds.
- `tests/contract/test-issue-111-model-tiers.py` and `tests/contract/test-issue-119-host-entry.py` expect the new default effort.
- Generated `skills/` and the README preset rows come from `./scripts/render-skills.py --write`.

## Candidate

Branch `workflow/issue-338`:

- `bca682af28034069415e7652ebbc4373cf8a1b3e` chore(release): open post-v0.9.14 content cycle — grok-bot bridge back to unpinned content stage (cherry-pick of `d8a100ec`)
- `cdadbfdee9f627621953fb7c9d4b43c31034dc58` fix: apply max effort on a plain dsh and opencode default start (#338)
- `baa9a38feb025837e0cd6672c3ee6b691d687f80` Merge origin/main (`c1d302af`, #337/#339/#340) into workflow/issue-338. The only conflict was `scripts/validate.sh`; both registrations were kept (`test-issue-338` then `test-issue-340` then `test-issue-339` in `python_suites_all` and `python_suites_b`). README auto-merged. `./scripts/render-skills.py --write` then `--check` stayed clean.

Host acceptance: ACCEPTED by `zcode-KPR-orchestrator-main` on `cdadbfde`, including a re-run of test-issue-338, test-issue-119, test-issue-98, and test-issue-264 (exit 0). The merge commit above is the sink candidate.

## Evidence

- Recorded validation (`.cache/final-validation.md`, verdict pass, candidate hash `09f9f2e5a9c2c23be16d99ef99cb9e38c276c020af59f005b58c9d3d6d146854`), run from the issue-338 worktree after the merge commit:
  `./scripts/validate.sh --suite test-issue-338-preset-effort-max.py --suite test-issue-119-host-entry.py --suite test-issue-98-dsh-acp.py --suite test-issue-264-validate-lane-integrity.py --suite test-issue-254-opencode-model.py --suite test-issue-339-model-option-rejected.py --suite test-issue-340-devin-argv-model.py --suite test-issue-331-effort-model-id.py --suite test-issue-111-model-tiers.py`
  Exit 0, wall 111.113 s, `residual_pids: []`. Outcomes: test-issue-98 41 OK; test-issue-111 25 OK; test-issue-119 11/11, 169 checks; test-issue-254 5 OK; test-issue-331 9 OK; test-issue-338 3 OK; test-issue-340 5 OK; test-issue-339 4 OK; test-issue-264 4 OK. The same command's render-check passed. A separate `./scripts/render-skills.py --check` exited 0: `11 workers + kaola-project-runner + kaola-delegator + grok-bot host: 1 bridge skill, 2555 B, content stage, unpinned (not saveable); budgets OK`.
- README rows on the candidate: `effort=max via ACP option reasoning_effort` (`dsh/default`) and `effort=max via ACP option effort` (`opencode/default`).
- Live acceptance evidence is the worktree checkout script (`<worktree>/scripts/kaola-acp.py`) against `/tmp/kpr-i338-live-repo`, sessions `dsh-KPR-i338-live` and `opencode-KPR-i338-live`. Receipts: `/tmp/kpr-i338-receipts/*-checkout-*.json`. Live binaries: `dsh` `0.2.0-rc.2`, `opencode` `opencode v2.0.29`.
  - dsh start exit 0, `state` `ready`. `config_application.effort`: `{"advertised": true, "applied": true, "candidates": ["reasoning_effort"], "config_id": "reasoning_effort", "value": "max"}`. `config_application.model`: `{"applied": true, "config_id": "model", "mapped": true, "requested_id": "opencode-go/deepseek-v4.1-flash", "value": "[\"opencode-go\",\"deepseek-v4.1-flash\"]"}`. `effective_selection`: `{"effective_effort": "max", "effective_model": "[\"opencode-go\",\"deepseek-v4.1-flash\"]", "effort_config_id": "reasoning_effort"}`.
  - dsh stop exit 0. The receipt has no `result` field: `{"agent_exit_code": 0, "agent_exit_signal": null, "git": {"branch": "main", "dirty": false}, "mutation_status": "not_started", "platform": "dsh", "repo": "/private/tmp/kpr-i338-live-repo", "residual_pids": [], "schema_version": 3, "session": "dsh-KPR-i338-live", "stopped": true, "swept_child_pgids": [], "transport": {"selected": "acp"}}`.
  - opencode start exit 0, `state` `ready`. `config_application.effort`: `{"advertised": true, "applied": true, "candidates": ["effort"], "config_id": "effort", "value": "max"}`. `config_application.model`: `{"applied": true, "config_id": "model", "value": "opencode-go/deepseek-v4.1-flash"}`. `effective_selection`: `{"effective_effort": "max", "effective_model": "opencode-go/deepseek-v4.1-flash", "effort_config_id": "effort"}`.
  - opencode stop exit 0. The receipt has no `result` field: `{"agent_exit_code": 0, "agent_exit_signal": null, "git": {"branch": "main", "dirty": false}, "mutation_status": "not_started", "platform": "opencode", "repo": "/private/tmp/kpr-i338-live-repo", "residual_pids": [], "schema_version": 3, "session": "opencode-KPR-i338-live", "stopped": true, "swept_child_pgids": [], "transport": {"selected": "acp"}}`.

## Known failures and unverified scope

- The required Skill-path starts (`skills/dsh-kaola-project-runner/scripts/kaola-acp.py` and `skills/opencode-kaola-project-runner/scripts/kaola-acp.py`) refused before spawn, exit 1, `result` `"refused"`, `reason` `"main-skill-build-skew"`, `mutation_status` `"not_started"`. `config_application` and `effective_selection` are absent. Installed `kaola-project-runner` is build `5639e05593d1`; the worktree build is `445879381d61`; the differing file is `references/profile-catalog.md`. dsh named `/Users/ylpromax5/.agents/skills/kaola-project-runner`. opencode named that path plus `/Users/ylpromax5/.config/opencode/skills/kaola-project-runner` and `/Users/ylpromax5/.claude/skills/kaola-project-runner`. Following status and stop exited 0 with `error.code` `"no-session"`. The Host recorded these refusals as the expected limit. No install was run.
- Manifest pins were left unchanged: dsh `acp_verified_versions` `cli=0.1.7-rc.2`, opencode `cli=2.0.22`. The live binaries above are newer. The accepted option value was still `max` on both.
- Whole-inventory `./scripts/validate.sh` was not run. Focused suites cover this change and the merged #339/#340 surfaces that share `scripts/kaola-acp.py` and the mock.
- CHANGELOG was not edited. No release and no tag.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- README.md
- platforms/dsh.yaml
- platforms/opencode.yaml
- scripts/adapters/dsh.sh
- scripts/adapters/opencode.sh
- scripts/validate.sh
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/SKILL.md
- skills/dsh-kaola-project-runner/references/platform.md
- skills/dsh-kaola-project-runner/scripts/adapters/dsh.sh
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/platform.yaml
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/references/profile-catalog.md
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/SKILL.md
- skills/opencode-kaola-project-runner/references/platform.md
- skills/opencode-kaola-project-runner/scripts/adapters/opencode.sh
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/platform.yaml
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- tests/contract/mock-acp-agent.py
- tests/contract/test-issue-111-model-tiers.py
- tests/contract/test-issue-119-host-entry.py
- tests/contract/test-issue-338-preset-effort-max.py

## Follow-Up Items

- None filed. The Skill-path build skew is the expected no-install limit above, and this dispatch does not open a new issue for it.

## Readiness

Ready to finalize and merge-sink. Host accepted the delivery. Validation is recorded pass on the merged worktree. Issue #338 closes on the verified merge.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-338/.cache/final-validation.md
- kaola-workflow/archive/issue-338/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-338/finalization-summary.md
- kaola-workflow/archive/issue-338/mission-ledger.jsonl
- kaola-workflow/archive/issue-338/workflow-state.md
