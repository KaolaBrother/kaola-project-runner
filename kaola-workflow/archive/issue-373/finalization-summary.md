# Finalization Summary — issue-373

## Delivered

Adopted #369 tier A for the agent's tool shells. The holder exports
`KAOLA_TOOL_CWD_FILE=<record_dir>/tool-cwd` and, per the new manifest `tool_shell`,
`ZDOTDIR=<record_dir>/shellenv` (zsh) or `BASH_ENV=<record_dir>/shellenv/.bashenv` (bash).
The runner-owned entry writes `$PWD` once per top-level tool shell under the
`KAOLA_TOOL_CWD_TRACED` guard, then restores and sources the user's own `ZDOTDIR`/`BASH_ENV`;
the user's shell init is unchanged. The holder reads the file on execute-kind tool calls, turn
end and the status scan, ignores a file older than the agent start, and leaves a dangling path
for V1 when a spawn fails with ENOENT. `platforms/zcode.yaml` enables `tool_shell: "zsh"`; the
ZCode adapter forwards exactly the tier A names to the app-server only when
`KAOLA_TOOL_CWD_FILE` is present. `/bin/sh` tools without an entry hook stay on tiers B/C, as
documented.

The documented #369 leftovers are fixed: observations order by their own `observed_at` (newer
tier A beats an older tier C sample; C never overwrites a fresher A path); the single
`tool_cwd_repair_error` slot is now the `status.tool_cwd_errors` list; and the pending notice
is one batch, so one steer names every repaired path while the worker event remains per path.

`tests/contract/test-issue-369-holder-cwd-repair.py` un-skips and passes the tier A case
(`/bin/zsh` and `bash` record the cwd; nested shell writes once; missing trace directory is
silent; user init still runs), the Mock-ACP tier A-only removal/repair/cleanup, the batch steer,
the stale-file ignore, and the fact-layer precedence/error-list cases. The test fixtures use a
class-wide serial so a leftover placeholder cannot collide with a later test.

`docs/api.md` and `docs/zcode-host.md` document tier A, the manifest field and the adapter
boundary. `CHANGELOG.md` Unreleased carries the #373 entry with `Seats: restart required`;
`docs/live-smoke-issue-373-tier-a-2026-10-20.md` is the controlled live smoke receipt.

## Candidate

Branch `workflow/issue-373` at `4b25e890`, rebased from the accepted `5b9a991a` onto current
main `454aebad` (which contains merged #374, #375 and #377) as `2b30faf4`, plus the test
isolation commit `4b25e890`. The rebase resolved the `CHANGELOG.md` Unreleased union (#373,
#374, #375, #377) with `Seats: restart required`; `docs/api.md` merged cleanly with the #374
and #375 sections. Generated Skill copies render cleanly (`./scripts/render-skills.py --check`
PASS). The Grok Bot bridge remains at the unpinned content stage on main.

## Evidence

- Host acceptance of `5b9a991a` in conversation, including the fable Expert review verdict
  PASS (all 10 specification items, 23 tier A tests, Mock-ACP contract, live smoke receipt,
  full gate exit 0). The review session was `devin-KPR-i373-expert-review` (dead/stopped).
- Pre-rebase full gate on `5b9a991a`: `/tmp/kpr-373-validate-full3.log`, 140 suites, exit 0,
  total wall 2023.88 s.
- Rebased full gate on `4b25e890`: `/tmp/kpr-373-validate-rebase3.log`, 143 suites, exit 0,
  total wall 1806.85 s.
- Affected holder suite after the fixture-isolation fix:
  `/tmp/kpr-373-suite-holder-rebase2.log`, 23/23 PASS.
- Live ZCode 0.16.9 smoke receipt:
  `docs/live-smoke-issue-373-tier-a-2026-10-20.md`. The independent session recorded the
  fixture worktree as `source: trace`, removed it out of band, repaired it at the next tool
  call with no `spawn /bin/zsh ENOENT` loop, delivered the notice by steer, and removed the
  empty placeholder at exact stop.
- Final validation record: `kaola-workflow/issue-373/.cache/final-validation.md`, verdict
  `pass`, command `./scripts/validate.sh`, candidate hash
  `90b0940ffa2de412ecfa35cb0b2f2a3a66ca0b59cf64c51d27e85cb612b8734f`.
- F1 was filed as issue #378 (non-blocking); F2/F3/F4 are recorded in the #378 body.

## Known failures or unverified scope

- The first rebased full run failed only `test-issue-369-holder-cwd-repair.py` because two
  fixtures shared a worktree number; that is fixed by `4b25e890` and the suite is green.
- Two unrelated timing-sensitive suites (`test-issue-302-delegator-wake-gate.py`,
  `test-issue-341-agent-initiated-turn.py`) timed out once under load; each passed in the
  individual rerun (`/tmp/kpr-373-suite-302-341.log`) and the final full gate is green.
- No release, tag, install, cloud action, or managed worker seat restart was performed. The
  Host's own holder is outside this candidate.
- Issue #378 (F1: cwd-repair notice re-steered every 15 s on a platform whose native steer
  answers `written`) remains open and is intentionally not blocking this merge.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/api.md
- docs/live-smoke-issue-373-tier-a-2026-10-20.md
- docs/zcode-host.md
- platforms/zcode.yaml
- scripts/kaola-acp-holder.py
- scripts/kaola-acp.py
- scripts/kaola-zcode-acp.py
- scripts/render-skills.py
- skills/antigravity-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/antigravity-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-zcode-acp.py
- skills/zcode-kaola-project-runner/scripts/platform.yaml
- tests/contract/mock-acp-agent.py
- tests/contract/test-issue-369-holder-cwd-repair.py

## Follow-Up Items

- #378 — F1 cwd-repair notice re-steer loop; F2/F3/F4 low-risk findings recorded in its body.
  Non-blocking for #373.

## Status

READY — merge to main, close #373, archive, clean up the run worktree and branch tail.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-373/.cache/final-validation.md
- kaola-workflow/archive/issue-373/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-373/finalization-summary.md
- kaola-workflow/archive/issue-373/mission-ledger.jsonl
- kaola-workflow/archive/issue-373/workflow-state.md
