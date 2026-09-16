# Clarify canonical-root Runner bootstrap and worker-owned Workflow worktree decisions (Issue #52)

Acceptance: https://github.com/KaolaBrother/kaola-project-runner/issues/52
Branch: `workflow/bundle-52`; Workflow worktree: `/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner/.kw/worktrees/bundle-52`.
Owner rule: decision defaults only; no transport gate, no hardcoded `.kw/worktrees` refusal, no Grok Bot host install/UAT (Issue #56). Do not touch other active folders (`issue-53`, `issue-56`) or their worktrees. Do not self-finalize.

1. item: Make shared orchestrator and worker templates, docs, and tests state the same root-start plus in-session Workflow ownership pattern, with Agent-owned exceptions and no transport worktree gate.
   status: done
   dispatched: self, in `.kw/worktrees/bundle-52`. Write failing Issue #52 contract tests first, then change `templates/orchestrator/`, `templates/SKILL.md.tmpl`, shared worker transport reference, README/docs/api/conventions/architecture/AGENTS/CHANGELOG, and `scripts/validate.sh`. Render generated Skills. Avoid `templates/grok-bot/` and Grok Bot host UAT docs. Output lands on `workflow/bundle-52` as reviewed commits plus this Mission result.
   result: PASS. Shared templates, generated Skills, README/docs/AGENTS, and `test-issue-52-workflow-worktree.py` now state root-start plus in-session `workflow-next`. Linked worktrees remain valid `--repo` Git roots on PTY and ACP. No `.kw/worktrees` refusal. Grok Bot host products untouched.

2. item: Freeze the candidate with renderer check, full `validate.sh`, behavioral examples, commit/diff/test evidence; stop before finalize.
   status: done
   dispatched: self, freeze on `workflow/bundle-52` after full validation. Delivery note at `kaola-workflow/bundle-52/delivery.md`. Do not finalize.
   result: PASS at `291feb71bc9c6da8b4779fb8945ebe0e2ac775f7`. `render-skills.py --check` PASS; `test-issue-52-workflow-worktree.py` 9/9; full `validate.sh` exit 0; `git diff --check origin/main...HEAD` clean. Grok Bot host products unchanged. Ready for controlling-Agent acceptance; not finalized.

