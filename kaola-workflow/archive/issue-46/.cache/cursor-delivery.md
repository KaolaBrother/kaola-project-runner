# Issue #46 delivery — workflow/issue-46

- Implementation: `8604f2b91b8db1a534d31b5414e00ede1229444c`
- Receipts: `0c50ccf4293cdb6864a548a1df6990bb3b316f97`
- Integrated candidate: `65aa83115416af3384588625a420c59417fbafa7`
- Merged `origin/main` at `bbccd96a3274f33d82a052d00044ccf77dba2f07` (no rebase)
- Branch: `workflow/issue-46`
- Worktree: `/Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/issue-46`

## Changed paths (Issue #46)

- `scripts/install-local.sh` — omitted `--method` now defaults to `copy`; `--method link` remains explicit; usage text updated. Owned source links (including grok root) already migrate via `copy-over-link`.
- `templates/orchestrator/SKILL.md.tmpl` — consumer-project boundary: checkout, templates, generated files, and installed Skill payload are read-only; store authorization/heartbeat/run facts in the consuming project; Project Runner edits need an explicit human assignment. After merge, also carries Issue #44 idle-stop / ending-a-run guidance.
- `skills/kaola-project-runner/SKILL.md` — regenerated via `./scripts/render-skills.py --write` on the integrated candidate (not hand-edited).
- `README.md`, `docs/api.md`, `docs/architecture.md`, `CHANGELOG.md` — install default described as standalone copy; Unreleased keeps both #46 and #44 bullets.
- `tests/contract/test-installer-migration.sh` — existing symlink-install proofs now pass `--method link` (same meaning).
- `tests/contract/test-installer-runtimes.sh` — existing link assertions pass `--method link`; new focused default-copy, owned-link-to-copy, grok-root-to-copy, foreign/modified protection tests.
- `tests/contract/test-generated-skills.py`, `tests/contract/test-issue-41-orchestrator.py` — generated Skill guidance and installer default pins, plus preserved Issue #44 scenario classes.

## Merge resolution

Inspected on-disk conflict after `git merge origin/main` (not rebase). Additive conflicts only in:

- `CHANGELOG.md` — kept both Unreleased bullets (#46 copy-default isolation, then #44 idle-stop/close-out).
- `tests/contract/test-issue-41-orchestrator.py` — kept `Issue44IdleStopOnCompleteMeaning` and `Issue46ConsumerIsolation` (and #44 worker-policy omission tests from main).

README, architecture, conventions, orchestrator template, and generated Skill auto-merged. `kaola-workflow/archive/issue-44/` and `pr-45-review-2` archives arrived from main unchanged.

## Tests (integrated candidate `65aa831`)

- `./scripts/render-skills.py --check` — PASS (`render-skills: PASS (7 workers + kaola-project-runner)`)
- Focused: `test-issue-41-orchestrator.py` 24 tests OK; `test-generated-skills.py` PASS; `test-installer-migration.sh` PASS; `test-installer-runtimes.sh` PASS
- `./scripts/validate.sh` — PASS (exit 0). Pre-existing ResourceWarning noise from `test-acp-holder-continue.py` is unchanged.

## Known limits

- Live per-platform tmux smoke was not re-run; this change does not alter start/send/read/stop transport.
- This worktree did not migrate a real `~/.codex/skills` install. Operators who still have owned source links get a copy on the next default `install-local.sh`.
- Main checkout, PR #45 branch, and the failed Issue #44 archive contents were not edited.
- `templates/grok-golden/` was not touched.
- Stopped before Workflow finalization, merge sink, and issue closure.
