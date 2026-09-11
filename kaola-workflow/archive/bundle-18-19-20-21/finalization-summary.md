# Finalization Summary

## Delivered

- Added manifest-defined ACP/PTY defaults and generated Skill transport, cost, fallback, and ACP reference surfaces.
- Added first-class `--transport acp|pty` dispatch, manifest-driven ACP commands/config IDs, schema-v3 PTY receipts, ACP packaging, and cross-transport identity/duplicate evidence.
- Live-verified Cursor, Devin, OpenCode, Claude wrapper preflight, and Kimi permission behavior.

## Files Changed

Platform manifests, shared templates, renderer, ACP holder/client, tmux/observation/model-policy runtime, generated Skills, contract tests, API/architecture docs, and the live evidence report.

## Test Coverage

- Runner v2 focused contract: 4/4 PASS.
- ACP offline contract: 13/13 PASS.
- Generated Skill acceptance: PASS.
- Live Cursor/Devin/OpenCode scenarios 1/3/4/7: PASS.
- Live Kimi plan permission/permit: PASS.
- Live PTY-to-ACP duplicate detection: PASS.
- Claude wrapper fetched but returned `probe-eof` before initialize; this objective result is recorded rather than claimed as PASS.

## Validation

`./scripts/render-skills.py --check && ./scripts/validate.sh` — PASS, candidate hash `9555806d11b3bd841d70914e8bb78b8dab296c5c35ffb9ca06d7c06761e2da9d`.

`git diff --check` — PASS. `git diff --stat templates/grok-golden` — empty.

## Changed Paths

The finalize transaction records the authoritative changed-path inventory.

## Documentation Docking

DOCKED in `.cache/doc-docking.md`: API, architecture, live evidence, generated references, and examples checked.

## Follow-Up Items

None. Claude ACP remains PTY-default with the measured wrapper `probe-eof` fact recorded in its manifest and report.

## Readiness

READY for all-or-nothing closure and merge sink.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/bundle-18-19-20-21/.cache/doc-docking.md
- kaola-workflow/archive/bundle-18-19-20-21/.cache/final-validation.md
- kaola-workflow/archive/bundle-18-19-20-21/.cache/mirror-digest.json
- kaola-workflow/archive/bundle-18-19-20-21/.cache/origin/selection-record.json
- kaola-workflow/archive/bundle-18-19-20-21/evidence/claude-preflight.json
- kaola-workflow/archive/bundle-18-19-20-21/evidence/cursor-preflight.json
- kaola-workflow/archive/bundle-18-19-20-21/evidence/devin-preflight.json
- kaola-workflow/archive/bundle-18-19-20-21/evidence/kimi-preflight.json
- kaola-workflow/archive/bundle-18-19-20-21/evidence/live-scenarios.json
- kaola-workflow/archive/bundle-18-19-20-21/evidence/opencode-preflight.json
- kaola-workflow/archive/bundle-18-19-20-21/evidence/pty-to-acp-duplicate.json
- kaola-workflow/archive/bundle-18-19-20-21/evidence/scenario-1.json
- kaola-workflow/archive/bundle-18-19-20-21/finalization-summary.md
- kaola-workflow/archive/bundle-18-19-20-21/mission-list.md
- kaola-workflow/archive/bundle-18-19-20-21/workflow-state.md
