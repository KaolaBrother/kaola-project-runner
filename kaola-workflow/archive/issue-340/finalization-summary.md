# Finalization Summary — issue-340

## Delivered

Issue #340: an `acp_command_<tier>` (argv-launched) model is presented as the effective model on
every Runner receipt surface that names one, so reports stop claiming `devin/default` "switches to
high".

- `scripts/kaola-acp.py`: `apply_argv_model()` is the shared Issue #140 override (start receipt and
  the recorded `start_evidence`), now also stamping `applied_via: "argv"` on `effective_selection`.
  `annotate_argv_effective_selection()` gives `status`/`observe` of an argv-applied start a top-level
  `effective_selection`: the argv id as `effective_model`, `effective_model_source: "launch-argv"`,
  `applied_via: "argv"`, and the ACP `currentValue` only as `advertised_model` (`advertised_source`
  `live-config-option` while the holder runs, `start-evidence` after it stops). Raw `session_meta`
  and `model_verified` are untouched; no verification is invented (`model_verified` stays `unknown`
  for Devin).
- `docs/api.md` and `platforms/devin.yaml` `acp_quirks`: Devin ACP cannot report the argv model, so
  the argv id is authoritative. `acp_verified_versions` unchanged (#337 owns it).
- New suite `tests/contract/test-issue-340-devin-argv-model.py` (live mock start/status/observe with
  ACP `currentValue` `swe-2-high` vs argv `swe-2-max`, plus stopped-holder fallback and non-argv
  units), registered in `scripts/validate.sh` `python_suites_all` and `python_suites_b`.
- Generated `skills/` regenerated via `./scripts/render-skills.py --write`.

## Candidate

Branch `workflow/issue-340`:

- `d23c258a` chore(release): open post-v0.9.14 content cycle (cherry-pick of `d8a100ec`; identical
  content already on main via #337)
- `5073e1d9` fix(#340): status/observe present an acp_command_<tier> argv model as effective

Host acceptance: ACCEPTED by `zcode-KPR-orchestrator-main` (re-ran test-issue-340, devin-regressions,
237-model-display, 264-lane-integrity: exit 0).

## Evidence

- Recorded validation (`.cache/final-validation.md`, verdict pass, candidate hash
  `b522694c5c2047fb23a0e90a325bff8d24c23098bd8e6b073b4968efaec9ec90`):
  `./scripts/validate.sh --suite test-devin-regressions.py --suite test-issue-340-devin-argv-model.py --suite test-issue-316-resume-model-evidence.py --suite test-issue-308-resume-reconcile.py --suite test-issue-264-validate-lane-integrity.py && ./scripts/render-skills.py --check`
  — exit 0: 28 / 5 / 14 / 8 / 4 tests OK; render PASS. Log `/tmp/kpr-i340-validate.log`.
- Adjacent suites: test-acp-contract.py 87 OK, test-droid-acp-contract.py 20 OK,
  test-issue-237-model-display.py 11 OK, test-issue-268-selection-continuity.py 26 OK. Log
  `/tmp/kpr-i340-validate-adjacent.log`.
- New suite fails on the pre-change code (1 failure, 4 errors) and passes on the candidate.
- Pre-change live reproduction (status/observe had no top-level effective model; only
  `session_meta.configOptions[model].currentValue` = `swe-2-high`): `/tmp/kpr-i340-pre-*.json`.
- Live check, devin 3000.11.92, session `devin-KPR-i340-live`, repo `/tmp/kpr-i340-live`
  (`/tmp/kpr-i340-live-*.json`):
  - start: `effective_selection {"advertised_model": "swe-2-high", "applied_via": "argv", "effective_model": "swe-2-max", "effective_model_source": "launch-argv"}`, `config_application.model {"applied": true, "applied_via": "argv", "value": "swe-2-max"}`, `model_verified "unknown"`, `start_evidence_recorded true`
  - status / observe: same `effective_selection` with `advertised_source "live-config-option"`;
    `start_evidence.effective_selection` carries `applied_via "argv"`; `session_meta` currentValue
    `swe-2-high` left raw
  - stop: `stopped true`, `residual_pids []`
  - status after stop: same `effective_selection` with `advertised_source "start-evidence"`

## Known failures and unverified scope

- No known failures.
- `view`/follow `model.current` keeps the live advertised value (`swe-2-high` for Devin). Host
  decision: the #237 contract is unchanged and `kaola-acp-holder.py` is not modified; that surface is
  the advertised option and #340 acceptance is met without it.
- The live check ran the checkout `scripts/kaola-acp.py` (identical code): the Skill copy under
  `skills/devin-kaola-project-runner/` refused with `worker-skill-build-skew` because the installed
  worker Skills on this Mac differ from the candidate build; no install was authorized.
- The scratch live session was started without the worker's Host heartbeat env, so it was not bound
  to the Host.
- A Devin resume launched without `--tier` (no argv `--model`) is not an `acp_command_<tier>` launch
  and is unchanged.
- Release note input: `platforms/devin.yaml` changed (doc-only `acp_quirks`) and is inside the
  operator seat-restart diff; the release preparer decides the `Seats:` line. CHANGELOG not edited.
- Whole-inventory `./scripts/validate.sh` not run (focused suites per project policy).

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- docs/api.md
- hosts/grok-bot/INSTALL.md
- hosts/grok-bot/bridge.json
- hosts/grok-bot/kaola-delegator.md
- platforms/devin.yaml
- scripts/kaola-acp.py
- scripts/validate.sh
- skills/antigravity-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/references/acp.md
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/platform.yaml
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- templates/grok-bot/accepted-revision.json
- tests/contract/test-issue-340-devin-argv-model.py

## Follow-Up Items

- None filed. No run-discovered defect requires a new issue.

## Readiness

Ready to finalize and merge-sink: Host-accepted candidate, validation recorded pass, issue #340
closes on the verified merge.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-340/.cache/final-validation.md
- kaola-workflow/archive/issue-340/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-340/finalization-summary.md
- kaola-workflow/archive/issue-340/mission-ledger.jsonl
- kaola-workflow/archive/issue-340/workflow-state.md
