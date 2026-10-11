# Finalization summary — issue-306

## Delivered

Fix for #306: a clean checkout installs; git-ignored bytecode no longer
fails the payload gate.

- `scripts/render-skills.py`: `--check` and `--verify-install` (and the
  grok-bot bundle verifier, `scripts/kaola-grok-bot-verify.py`) skip
  `__pycache__/` directories and `*.pyc`/`*.pyo` files, matching what
  `install-local.sh`'s `tree_digest`/`stage_copy` already did. A real
  unexpected file — including a regular file merely named `__pycache__` —
  is still reported and still fails the gate.
- Bytecode prevention: worker entry wrappers, `kaola-tmux.sh` and
  `runtime-tmux.sh` export `PYTHONDONTWRITEBYTECODE=1`; the dispatch
  recovery import of `kaola-compact-recovery.py` (the exact repro path —
  a Host runs that file with python directly) sets
  `sys.dont_write_bytecode` around `exec_module`.
- Tests: `tests/contract/test-issue-306-bytecode-payload.py` (4 cases,
  248 lines) — entry points suppress bytecode writes; check + install
  ignore bytecode and reject a real extra file; the host bundle verifier
  ignores bytecode only; the recovery import writes no bytecode.
  Registered in `validate.sh`.
- `docs/api.md`; CHANGELOG Unreleased entry (Seats: restart not required
  — the gate fix is per-call; the wrappers only affect new sessions).

## Candidate

- Implementation commit `8b363b4a` on `workflow/issue-306` (worktree
  `.kw/worktrees/issue-306`, base `826a1ead`). Implemented by the
  `grok/default` seat `grok-KPR-i306-pycache`; reviewed and finalized by
  the Host.

## Evidence

- Host diff review (this run): every payload walk covered; gate strictness
  preserved (real extras fail); the issue's exact repro path guarded.
- `./scripts/render-skills.py --check` — PASS.
- Affected suites, all exit 0: `test-issue-306-bytecode-payload.py` (new),
  `test-progressive-disclosure.py`, `test-issue-274-package-closure.py`,
  `test-ddd-pack.py`, `test-issue-49-grok-bot-host.py`,
  `test-issue-130-pty-retired.py` (logs `/tmp/kpr-i306-*.log`).
- `.cache/final-validation.md`: verdict `pass`, candidate hash
  `ceea41734b8acab4…`.
- Worker seat exact-stopped after acceptance (`state: stopped`).

## Known failures / unverified scope

- The sink rebases onto the #303/#304-advanced main (CHANGELOG union
  expected); the integrated tree is re-verified. Full inventory at the
  v0.9.8 release boundary. The owner-required end-to-end proof — the
  MacBook install of v0.9.8 succeeding with bytecode present — happens at
  the owner's install step (this run installs nothing per boundary).

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/api.md
- scripts/kaola-dispatch.py
- scripts/kaola-grok-bot-verify.py
- scripts/kaola-tmux.sh
- scripts/render-skills.py
- scripts/validate.sh
- skills/claude-code-kaola-project-runner/scripts/kaola-tmux.sh
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/runtime-tmux.sh
- skills/codex-kaola-project-runner/scripts/kaola-tmux.sh
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/runtime-tmux.sh
- skills/cursor-cli-kaola-project-runner/scripts/kaola-tmux.sh
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/runtime-tmux.sh
- skills/devin-kaola-project-runner/scripts/kaola-tmux.sh
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/runtime-tmux.sh
- skills/droid-kaola-project-runner/scripts/kaola-tmux.sh
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/runtime-tmux.sh
- skills/dsh-kaola-project-runner/scripts/kaola-tmux.sh
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/runtime-tmux.sh
- skills/grok-kaola-project-runner/scripts/grok-tmux.sh
- skills/grok-kaola-project-runner/scripts/kaola-tmux.sh
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/runtime-tmux.sh
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-tmux.sh
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/kimi-cli-kaola-project-runner/scripts/runtime-tmux.sh
- skills/opencode-kaola-project-runner/scripts/kaola-tmux.sh
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/runtime-tmux.sh
- skills/zcode-kaola-project-runner/scripts/kaola-tmux.sh
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/runtime-tmux.sh
- tests/contract/test-issue-306-bytecode-payload.py

## Follow-Up Items

- None.

## Final readiness

Ready: candidate reviewed, affected scope green, validation recorded.
Proceed to sink (merge) and archive.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-306/finalization-summary.md
