# Finalization Summary — issue-366

## Delivered

Issue #366 removes spelled-out predecessor names from tracked archive finalization summaries, archive mission ledgers, and `docs/host-compact-capabilities.md`. A line that existed only for that name is deleted. A line that also carried another fact keeps that fact. Two removed-docs paths are deleted from `kaola-workflow/archive/issue-358/finalization-summary.md`. The one current overview sentence stays once in `AGENTS.md` and once in `README.md`. Hash and base64 substring hits are unchanged.

`CHANGELOG.md` Unreleased gains one bullet for this cleanup. The section line stays `Seats: restart required`. The operator diff `85119632..fb6686a4` is empty for the restart set and for `hosts/grok-bot/accepted-revision.json`.

## Candidate

Branch `workflow/issue-366`, parent `85119632e4db8785372257fd680a6eb5489fb67a`.

- `fb6686a4cb1d43833e95fdcf3334cdfce91ea39c` — `docs: remove upstream project references from archive and evidence`

26 files changed, 30 insertions, 41 deletions. Acceptance candidate: `fb6686a4`. Worktree clean. This finalize adds no implementation commit.

Host acceptance: ACCEPTED in the controlling conversation on 2026-10-19. Boundary: merge into main, push `origin/main`, close the issue with proof, archive the run, and remove the worktree and branch tail. No tag, no release, no `accepted-revision.json` change.

## Evidence

- Tracked-file case-insensitive scan of the abbreviation and the spelled-out predecessor name, over `git ls-files`, on this candidate's bytes: exit 0, 9 lines. Two are the retained overview sentence (`AGENTS.md:11`, `README.md:3`). Seven are hash or base64 lines: `docs/evidence/host-compaction/core-grok-20261006-r1-host-events.jsonl` (cursors 300, 859, 1016, 1109), `kaola-workflow/archive/issue-246/qa/real-admission-receipts.json:3145`, `kaola-workflow/archive/issue-65/evidence/claude-native-steer-events2.json:268`, `vendor/claude-code-acp/package-lock.json:2384`.
- Scan of the four deprecated positioning terms over tracked files: exit 1, zero files.
- `./scripts/render-skills.py --check` PASS.
- `./scripts/validate.sh --suite test-issue-49-grok-bot-host.py --suite test-issue-162-upgrade-safety.py --suite test-issue-349-checkpoint-verb.py` in the worktree (`NO_COLOR=1`; proxies, `KAOLA_ACP_DISPATCHER`, `KAOLA_ZCODE_ENTRY`, and `KAOLA_ZCODE_NODE` unset; `KAOLA_LAUNCH_BACKEND=direct`): exit 0. `test-issue-49-grok-bot-host.py` Ran 45 OK. `test-issue-162-upgrade-safety.py` Ran 27 OK. `test-issue-349-checkpoint-verb.py` Ran 39 OK. Wall 80.18 s. Recorded in `.cache/final-validation.md`.
- Edited mission ledgers parse as JSONL: issue-297, 304, 307, 308, 309, 310, and 345.

## Known failures and unverified scope

- No known product failure on `fb6686a4`.
- No release, tag, or install. `hosts/grok-bot/accepted-revision.json` is unchanged.
- The full inventory was not run. The suites above are the ones that read `CHANGELOG.md` or `docs/`.
- No contract suite reads the edited archive prose. JSONL parse is the check for those files.
- Live ACP smoke was not re-run. This change does not touch the holder, adapters, or platforms.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/host-compact-capabilities.md

## Follow-Up Items

- None filed.
- searched: `gh issue list --repo KaolaBrother/kaola-project-runner --state open --search "stale archive evidence references" --limit 20` → 1 hit, #366, this issue.

## Readiness

Host accepted `fb6686a4`. Merge sink into main, push `origin/main`, close #366 with the proof comment, archive, and remove the worktree and the branch tail. No tag, no release, no accepted-revision change.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-366/.cache/final-validation.md
- kaola-workflow/archive/issue-366/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-366/finalization-summary.md
- kaola-workflow/archive/issue-366/mission-ledger.jsonl
- kaola-workflow/archive/issue-366/workflow-state.md
