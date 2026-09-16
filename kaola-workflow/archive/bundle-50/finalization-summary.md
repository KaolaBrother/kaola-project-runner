# Finalization summary — bundle-50 (Issue #50)

Candidate: `8095611` on `workflow/bundle-50`, based on `main` = `origin/main` = `4a705f3`
(Issue #49 sunk; its R3/P3/archive history is an ancestor and untouched). Sink: merge.
Issue set: #50 (single). Closure decision: close (owner acceptance of candidate `8095611` on
2026-09-16 after review round 2; non-blocking notes accepted as recorded).

## Delivered

- `vendor/claude-code-acp/`: pinned MIT fork of harukitosa/claude-code-acp at
  `6c20f2802e390c80b0542247c6b9738e11efdc11` (LICENSE verbatim, UPSTREAM.md with the complete
  modification list and hashed inventory, committed single-file `dist/index.js` whose derivation
  `kaola-dist.py --check` re-verifies offline). Fork behavior: exact absolute Claude binary
  (never PATH), per-session `mode`/`model`/`effort`/`fast` mapped onto every `claude -p`
  subprocess, native `session/list`/`session/resume`, process-group cancel/shutdown, credential
  stripping with everything else inherited, masked logs, per-turn temp cleanup, cancelled
  `--resume` turns reported as cancelled (live finding), atomic session-store writes.
- Runner integration: `platforms/claude-code.yaml` runs
  `node $SKILL_DIR/scripts/vendor/claude-code-acp/dist/index.js`; `scripts/kaola-acp.py`
  resolves the `$SKILL_DIR/scripts/` token (installed Skill, else checkout; escapes and missing
  files → `acp-bridge-missing`), passes the exact `claude` path as `CLAUDE_ACP_CLAUDE_BIN`, and
  reports `bridge`/`runtime_binary` facts; `scripts/render-skills.py` ships the bundle,
  derivation, LICENSE, and UPSTREAM.md into the Claude Code worker only.
- Default transport for Claude Code: `acp` (live subscription gate passed 2026-09-16, re-run on
  the composed candidate); `--transport pty` remains the explicit fallback and login channel.
- Offline harnesses: `tests/contract/test-issue-50-claude-acp-bridge.py` (10 tests, 203 checks)
  and `tests/contract/test-issue-50-runner-integration.py` (6 tests, 107 checks) against
  `tests/contract/fake-claude.py`; `scripts/validate.sh` runs both plus `git diff --check`.
- Docs: README, docs/api.md, docs/architecture.md, design v0.4 decision superseding §12.5,
  CHANGELOG.

## Files Changed

Five content commits `main..8095611`: `e5dd527` (Mission 1), `4a1ea1f` (Mission 2), `8a6ddac`
(Mission 3), `46c7492` and `8095611` (Mission 4 review fixes). `git diff --stat main HEAD`:
74 files, +43397/−111 (the vendored bundle and lock dominate). Six non-Claude workers differ
from main only in their shared `scripts/kaola-acp.py` copy (inert for them). Grok Bot pin files
returned to the content stage as the pin gate requires of a content commit after P3;
`templates/grok-golden/`, orchestrator and worker templates, and adapters unchanged.

## Test Coverage

- Bridge harness: provenance and inventory, self-contained dist, first/second-turn flags and env
  and cwd and log masking, cwd validation, permission round trip, cancel on first and resume
  turns (process group), stop mid-turn cleanup, missing/bare binary fail-closed, concurrent
  session isolation, named continuity + list + resume.
- Runner harness: manifest and generated-Skill inventory, preflight facts in both layouts,
  fail-closed on missing/bare binary and missing bridge (including token escapes),
  start/send/resume/cancel/stop through the generated Skill, `--continue`/`--resume` into one
  native session, explicit PTY fallback and manifest-default dispatch.
- Vendor vitest 130/130 (20 upstream files verbatim, agent-modes updated, kaola-fork added);
  `tsc --noEmit` clean; `kaola-dist.py --check` byte-identical rebuild.
- Live (not automated; recorded in `uat-live-2026-09-16.md`): preflight facts, Fable High
  sentinel with native model `claude-fable-5-1`, tool call, cancel on a resume turn, continue and
  resume into the same conversation, zero residue, Settings size/mtime identical; re-run on the
  composed candidate after the rebase.

## Validation

Command: `./scripts/validate.sh` from the candidate worktree at `8095611` (consumer repository
without `test:kaola-workflow:*` chains; `run-chains.js` reports `chains_config_missing` as
designed). Result: exit 0 (render-skills PASS; bridge harness 10/10 = 203 checks; Runner harness 6/6 =
107 checks; all contract suites green). Receipt `.cache/final-validation.md`: `verdict: pass`,
`validation_command: ./scripts/validate.sh`,
`validated_candidate_hash: 692ea9720e6e05d6f38524e6aa32f0ad2233a128ae6572be1b9bfa5799b04567`
(recorded by `kaola-workflow-validation-runner.js record --verdict pass` from the candidate
worktree); `finalize --check` afterwards: `ok: true`, `validation: chains_green`, `reasons: []`. Additional evidence on the same
tree: `render-skills.py --check` PASS; `git diff --check main HEAD` clean; `finalize --check`
`ok: true` with `validation: final_validation_unverified` before the receipt was recorded.

## Changed Paths

Reported by `finalize --check` (`changed_paths`, 66 entries): `.gitattributes`;
`hosts/grok-bot/{INSTALL.md,bridge.json,kaola-project-runner.md}`; `platforms/claude-code.yaml`;
`scripts/{kaola-acp.py,render-skills.py,validate.sh}`;
`skills/claude-code-kaola-project-runner/{SKILL.md,references/acp.md,references/platform.md,scripts/kaola-acp.py,scripts/platform.yaml,scripts/vendor/claude-code-acp/{LICENSE,UPSTREAM.md,dist/DERIVATION.json,dist/index.js}}`;
`skills/{codex,cursor-cli,devin,grok,kimi-cli,opencode}-kaola-project-runner/scripts/kaola-acp.py`;
`skills/kaola-project-runner/SKILL.md`; `templates/grok-bot/accepted-revision.json`;
`tests/contract/{fake-claude.py,test-issue-50-claude-acp-bridge.py,test-issue-50-runner-integration.py,test-runner-v2.py}`;
`vendor/claude-code-acp/**` (37 files: attributes, ignore, LICENSE, UPSTREAM.md, bin, dist ×2,
kaola-dist.py, package.json, package-lock.json, src ×7, tests ×21, tsconfig, tsup.config).
`dirty_paths: []`.

## Documentation Docking

`.cache/doc-docking.md`: DOCKED (README, docs/api.md, docs/architecture.md, design doc v0.4,
CHANGELOG, generated Claude Skill surfaces, UPSTREAM.md; AGENTS.md and installer no impact;
historical wrapper record intentionally unchanged).

## Acceptance legs

- Automated: `./scripts/validate.sh` (above) — pass.
- Local: `git diff --check main HEAD`, per-commit `render-skills.py --check`, vendor vitest and
  dist check — pass.
- Manual/UAT: live subscription gate on this Mac (2026-09-16, `uat-live-2026-09-16.md`) — pass
  with the recorded permit fact; owner accepted candidate `8095611` after review round 2.
- Unexecuted: `stop --force` residue path live; a real permission round trip (the CLI emitted no
  permission request); Fast on (`--fast on`) live.
- Issue-statement walk: every acceptance member is mapped to a test, receipt, or prose evidence
  in `delivery-report.md`; the deviations (six workers not byte-identical; permit unexercised)
  are recorded on the issue (evidence comment) as corrections, not footnotes.

## Follow-Up Items

- filed: #53 (P3) — bridge robustness edges from the reviews: `.tmp` leftover on rename failure,
  force-kill residue visibility, stale cancel flag race, one-directional permit. Confirmed to
  exist with a non-empty body (2987 chars) in this finalize transaction.
- Recorded, no action: `acp_env_allowlist` is documentation-only; two pre-existing
  `claude-acp-mcp-*` dirs in the user's TMPDIR and the user's own UAT transcripts/bridge store
  entries were left in place by instruction.
- No user value decision outstanding; no conflicts left; no partial work.

## Readiness

READY for the finalize transaction (archive + commit) and the merge sink of `workflow/bundle-50`
into `main`, closing #50. No release or tag (by instruction). bundle-51 untouched.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/bundle-50/.cache/doc-docking.md
- kaola-workflow/archive/bundle-50/.cache/final-validation.md
- kaola-workflow/archive/bundle-50/.cache/mirror-digest.json
- kaola-workflow/archive/bundle-50/.cache/origin/selection-record.json
- kaola-workflow/archive/bundle-50/delivery-report.md
- kaola-workflow/archive/bundle-50/finalization-summary.md
- kaola-workflow/archive/bundle-50/mission-list.md
- kaola-workflow/archive/bundle-50/review-report.md
- kaola-workflow/archive/bundle-50/uat-live-2026-09-16.md
- kaola-workflow/archive/bundle-50/workflow-state.md
