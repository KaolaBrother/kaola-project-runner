# Finalization summary — issue-124

## Delivered
Issue #124: grok sessions record the CLI build they actually ran, and the ACP contract is re-verified on grok 1.0.40.
- `scripts/kaola-acp.py`: `CLI_VERSION_PLATFORMS = {"grok"}` + `cli_version_fact()`; a grok `start` resolves the ACP command's first word on the agent PATH, runs `--version`, and passes `{path, version, verified_versions}` to the holder (`--cli-version`); the start receipt reports it as `transport.cli_version`. `binary_version()` factored out of `bridge_facts()` (behavior unchanged).
- `scripts/kaola-acp-holder.py`: `cli_version` in `record.json` and holder state (`null` for other platforms).
- Fact only: no refusal, warning tier, classifier or gate; a mismatch or unreadable version still starts.
- `platforms/grok.yaml`: `acp_verified_versions` `cli=1.0.40;protocol=1`; `steering_summary` cites cli 1.0.40.
- Host acceptance: PASS (Host verdict 2026-09-21, candidate 970f546, no repair round).

## Files Changed
Commits 14a329f, 970f546 on workflow/issue-124: scripts/kaola-acp.py, scripts/kaola-acp-holder.py, tests/contract/test-acp-contract.py, platforms/grok.yaml, CHANGELOG.md, docs/api.md, and rendered skills/ (10 workers' kaola-acp.py/kaola-acp-holder.py; grok platform.yaml and references/steering.md).

## Test Coverage
- AC1: tests/contract/test-acp-contract.py::test_start_records_launched_cli_version_without_gating — a fake `grok` reporting `grok 9.9.124 (fixture)` (≠ verified) starts; receipt `transport.cli_version` and `record.json` `cli_version` equal `{path, version, verified_versions}`; stop `residual_pids []`. FAIL on baseline 7ccb2af, PASS on 14a329f.
- AC1/AC2 live: evidence/grok-1.0.40-acp-smoke.md (+ raw dir) — grok 1.0.40 (eb1a2256660d) start/send/read/cancel/stop: `cli_version` recorded while verified still read 1.0.25 and the session started; `turn_ended end_turn` (cursor 71), `turn_ended cancelled` (cursor 80), `process_exited code 0` (cursor 84), stop `residual_pids []`, `agent_exit_code 0`. Network: command-prefix HTTP(S)_PROXY only.
- Contract re-check: initialize protocol 1, no agentInfo, `_meta` x.ai/hooks + x.ai/capabilities + x.ai/fs_notify, no steering `_meta`; session/new configOptions model + reasoning_effort; 12 `_x.ai/*` notification methods recorded without malformed lines or handler errors; steering candidates all -32601 (evidence/grok-1.0.40-acp-smoke/steer-probe-grok-1.0.40.json, archived #65 steer_probe.py idle phase).
- AC4: existing grok tests unchanged and green inside validate.sh.

## Validation
- `./scripts/render-skills.py --check && ./scripts/validate.sh` → rc=0 on the 970f546 bytes (evidence/validate.log; test-acp-contract 48 tests OK, baseline 47); recorded in .cache/final-validation.md, verdict pass, validated_candidate_hash e4a5c9017ae4….
- run-chains: not applicable (consumer repo without package.json; gate is the recorded final validation). finalize --check: ok, validation chains_green, no reasons.

## Changed Paths
finalize --check reported changed_paths (26, source-scoped; CHANGELOG.md and docs/api.md are docs and not listed):
- platforms/grok.yaml
- scripts/kaola-acp-holder.py
- scripts/kaola-acp.py
- skills/{claude-code,codex,cursor-cli,devin,droid,dsh,grok,kimi-cli,opencode,zcode}-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/{claude-code,codex,cursor-cli,devin,droid,dsh,grok,kimi-cli,opencode,zcode}-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/references/steering.md
- skills/grok-kaola-project-runner/scripts/platform.yaml
- tests/contract/test-acp-contract.py

## Documentation Docking
DOCKED — .cache/doc-docking.md (CHANGELOG.md, docs/api.md updated; historical 1.0.25 PoC/design measurements intentionally kept).

## Follow-Up Items
- None filed. Known alternative recorded by the Host and deliberately not pursued: grok's `initialize` result carries the version in `result._meta.agentVersion` (observed "1.0.40"); the Runner does not read it.
- Forge note: the dispatch brief cited two issue comments; the forge had zero at claim time, so the issue body was the design and acceptance source.
- Boundary: no change to ~/.grok (auto_update unchanged), ~/.dsh, ~/.claude, persistent proxy settings, or #120–#123.

## Status
Ready: accepted, validated, docked. Issue #124 closes with the merge sink.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-124/.cache/doc-docking.md
- kaola-workflow/archive/issue-124/.cache/final-validation.md
- kaola-workflow/archive/issue-124/.cache/mirror-digest.json
- kaola-workflow/archive/issue-124/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-124/evidence/grok-1.0.40-acp-smoke.md
- kaola-workflow/archive/issue-124/evidence/grok-1.0.40-acp-smoke/01-start.json
- kaola-workflow/archive/issue-124/evidence/grok-1.0.40-acp-smoke/02-send.json
- kaola-workflow/archive/issue-124/evidence/grok-1.0.40-acp-smoke/03-observe.json
- kaola-workflow/archive/issue-124/evidence/grok-1.0.40-acp-smoke/04-send-long.json
- kaola-workflow/archive/issue-124/evidence/grok-1.0.40-acp-smoke/05-cancel.json
- kaola-workflow/archive/issue-124/evidence/grok-1.0.40-acp-smoke/06-stop.json
- kaola-workflow/archive/issue-124/evidence/grok-1.0.40-acp-smoke/events.jsonl
- kaola-workflow/archive/issue-124/evidence/grok-1.0.40-acp-smoke/record.json
- kaola-workflow/archive/issue-124/evidence/grok-1.0.40-acp-smoke/steer-probe-grok-1.0.40.json
- kaola-workflow/archive/issue-124/finalization-summary.md
- kaola-workflow/archive/issue-124/mission-list.md
- kaola-workflow/archive/issue-124/workflow-state.md
