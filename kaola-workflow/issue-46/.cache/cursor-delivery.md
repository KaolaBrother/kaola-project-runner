# Issue #46 delivery — workflow/issue-46

- Commit: `8604f2b91b8db1a534d31b5414e00ede1229444c`
- Branch: `workflow/issue-46`
- Worktree: `/Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/issue-46`

## Changed paths

- `scripts/install-local.sh` — omitted `--method` now defaults to `copy`; `--method link` remains explicit; usage text updated. Owned source links (including grok root) already migrate via `copy-over-link`.
- `templates/orchestrator/SKILL.md.tmpl` — consumer-project boundary: checkout, templates, generated files, and installed Skill payload are read-only; store authorization/heartbeat/run facts in the consuming project; Project Runner edits need an explicit human assignment.
- `skills/kaola-project-runner/SKILL.md` — regenerated via `./scripts/render-skills.py --write` (not hand-edited).
- `README.md`, `docs/api.md`, `docs/architecture.md`, `CHANGELOG.md` — install default described as standalone copy.
- `tests/contract/test-installer-migration.sh` — existing symlink-install proofs now pass `--method link` (same meaning).
- `tests/contract/test-installer-runtimes.sh` — existing link assertions pass `--method link`; new focused default-copy, owned-link-to-copy, grok-root-to-copy, foreign/modified protection tests.
- `tests/contract/test-generated-skills.py`, `tests/contract/test-issue-41-orchestrator.py` — generated Skill guidance and installer default pins.

## Tests

- `./scripts/render-skills.py --check` — PASS (`render-skills: PASS (7 workers + kaola-project-runner)`)
- `./scripts/validate.sh` — PASS (exit 0). Includes installer migration PASS, installer runtimes PASS, generated Skill acceptance PASS, Issue #41/46 orchestrator tests OK. Pre-existing ResourceWarning noise from `test-acp-holder-continue.py` is unchanged.

## Known limits

- Live per-platform tmux smoke was not re-run; this change does not alter start/send/read/stop transport.
- This worktree did not migrate a real `~/.codex/skills` install. Operators who still have owned source links get a copy on the next default `install-local.sh`.
- The observed uncommitted consumer authorization paragraph in the main checkout was not modified (out of this worktree).
- PR #45 branch, main checkout, and `templates/grok-golden/` were not touched.
- No merge, issue close, Workflow finalize, or acceptance-test meaning change.
