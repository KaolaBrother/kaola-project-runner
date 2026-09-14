# PR #42 review repair — Issue #41

Owner: Cursor CLI in `/Users/ylpromax5/Workspace/kaola-project-runner-pr42` on `codex/pr-42-review`.
Main Codex owns acceptance, close-out, push, merge, and finalize.
Mission remains in-flight.

## Scope (owner-authorized)

No per-platform live tmux smoke. Main verified the original PR does not change
platform manifests, adapters, or PTY/ACP scripts; worker change is prose pointer
only. This repair does not edit worker templates, `validate-skill.py`, or
transport scripts. No additional workers or heartbeats.

## Finding 1 — invalid YAML description

Cause: orchestrator `DESCRIPTION` contained unquoted colon-space (`Skills: recover`).
`yaml.safe_load` of SKILL.md frontmatter raised `ScannerError`.

Fix: `scripts/render-skills.py` `orchestrator_values()` now sets `DESCRIPTION` with
`json.dumps(...)` (JSON strings are YAML-compatible quoted scalars). Template
`description: {{DESCRIPTION}}` unchanged. Regenerated
`skills/kaola-project-runner/SKILL.md` only for this surface.

Regression: `tests/contract/test-issue-41-orchestrator.py`
`test_orchestrator_description_json_quotes_colon_space_for_yaml` — asserts JSON-quoted
renderer value, generated `description:` scalar `json.loads` to the same string
including `Skills: recover`, and `yaml.safe_load` when PyYAML is present. No new
required dependency.

## Finding 2 — archived credential URL

`kaola-workflow/archive/issue-41/workflow-state.md` `claim_repository_id` used an
HTTPS userinfo URL. Sanitized to canonical
`https://github.com/KaolaBrother/kaola-project-runner`. Historical
`claim_identity_digest` `30a96fc22c57215549e50ece1823a18ab23d9c3a1745d9cb8981f2d2e4528594`
is preserved. No other tracked userinfo URLs remained under `archive/issue-41/`.
Completed mission results were not rewritten.

Tracked-file cleanup does not purge already-published git/GitHub history.

Token metadata (from main, not re-decoded here): `exp` `2026-09-14T08:05:20Z`,
currently expired. Token value was not printed and was not used. No rotation and
no force-push.

## Validation (this worktree)

- `./scripts/render-skills.py --write` → exit 0
  `render-skills: WROTE (7 workers + kaola-project-runner)`
- `./scripts/render-skills.py --check` → exit 0
  `render-skills: PASS (7 workers + kaola-project-runner)`
- `./scripts/validate.sh` → exit 0
  - `render-skills: PASS (7 workers + kaola-project-runner)`
  - `validate-skill: PASS` × 8 (seven workers + orchestrator)
  - installer migration/runtimes PASS
  - `test-issue-9-contract.py` 7 OK
  - `test-direct-transport-contract.py` 5 OK
  - `test-devin-regressions.py` 31 OK
  - `test-acp-contract.py` 44 OK (53.027s)
  - `test-acp-watch-contract.py` 13 OK
  - `test-acp-follow-contract.py` 12 OK (ResourceWarning: unclosed file; same class as prior archive notes)
  - `test-acp-holder-continue.py` 29 OK
  - `test-issue-33-config-meta.py` 9 OK
  - `test-runner-v2.py` 4 OK
  - `test-generated-skills.py` `generated Skill acceptance: PASS`
  - `test-issue-24-opencode-pty-bypass.py` 14 OK
  - `test-issue-41-orchestrator.py` 10 OK (1.252s; includes new YAML description test)
- Local PyYAML `yaml.safe_load` of generated orchestrator frontmatter: mapping
  `name=kaola-project-runner`, `description` is str, equals JSON-decoded scalar,
  contains `Skills: recover`. No `ScannerError`.

Live CLI start/observe/send/capture/stop: not run (authorized no-smoke scope).

## Handback

Fixes and this evidence are in the local commit on `codex/pr-42-review`. Not pushed.
