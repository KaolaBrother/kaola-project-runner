# Finalization Summary — issue-361

## Delivered

- `launch_backend: auto` degrades to the direct spawn with an explicit, machine-readable
  reason when the outside launcher cannot operate (`job-state-unknown`,
  `launch-backend-unsupported`); explicit `--launch-backend` requests still refuse.
- The start receipt now names the actual backend the broker used (`launch_backend`),
  and a degraded start carries `launch_backend_degraded`,
  `launch_backend_fallback_reason`, and `launch_backend_fallback_detail`.
- `session_role: host` records go through the dispatched-worker identity check on both
  stop paths: a cooperative Host stop (`_terminate_group`) and the dead-holder
  exact-stop (`recorded_groups`) spare verified Runner holders, reported as
  `spared_child_pgids`; unverified child groups are still swept.
- Docs updated (`docs/api.md`, orchestrator `SKILL.md.tmpl`,
  `references/sideagent-node.md`, `references/lifecycle-state.md`); generated
  `skills/` + `hosts/` re-rendered; CHANGELOG Unreleased entry, `Seats: restart
  required` (`scripts/kaola-acp-holder.py` is in the operator restart set).

## Candidate

`33468603` on `workflow/issue-361`, rebased onto `0df26780` (main tip containing
#360 `b463335f` and #368 `0e853582`); content-accepted by the Host at `8a5acbb4`
and re-verified after the #360/#368 rebase.

## Evidence

- Reproduction: dsh `workspace-write` Seatbelt fails `launchctl` write/state calls;
  `auto` refused `job-state-unknown` rather than silently choosing `direct` — the
  incident's direct came from an explicit/inherited selection. Host records were
  excluded from `dispatched_worker_groups` on both stop paths.
- Live check: `sandbox-exec` + `KAOLA_LAUNCH_BACKEND=auto` start returns
  `launch_backend: "direct"`, `launch_backend_degraded: true`,
  `launch_backend_fallback_reason: "job-state-unknown"`.
- Focused suites all pass on this candidate; the recorded command is in
  `.cache/final-validation.md` (`verdict: pass`,
  `validated_candidate_hash: 7cf9e9c2ddc36f4432f075fe21af8a30f08069ae04c47560e2ca022130819b0d`).

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
- skills/antigravity-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/antigravity-kaola-project-runner/scripts/kaola-acp.py
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/SKILL.md
- skills/kaola-project-runner/references/lifecycle-state.md
- skills/kaola-project-runner/references/sideagent-node.md
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/orchestrator/SKILL.md.tmpl
- templates/orchestrator/references/lifecycle-state.md
- templates/orchestrator/references/sideagent-node.md
- tests/contract/test-issue-255-lifecycle-state.py
- tests/contract/test-issue-266-launch-broker-composed.py

## Known failures / unverified scope

- None in the candidate scope. Full-inventory `validate.sh` (all 134 suites) is the
  Host's gate and was not run here by design.
- Observed, not a candidate defect: contract tests run by bare `python3` (outside
  `validate.sh`) inherit a live seat's `KAOLA_*` environment and can fail on
  timeouts; `validate.sh` scrubs those variables. Left to the Host whether a
  follow-up is wanted.

## Follow-Up Items

- None filed; no run-discovered defect remained after the fix.

## Readiness

Candidate frozen at `33468603`; all missions done; ready for the merge sink.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-361/.cache/final-validation.md
- kaola-workflow/archive/issue-361/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-361/finalization-summary.md
- kaola-workflow/archive/issue-361/mission-ledger.jsonl
- kaola-workflow/archive/issue-361/workflow-state.md
