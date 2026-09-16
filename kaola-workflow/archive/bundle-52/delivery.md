# Issue #52 delivery (not finalized)

Candidate branch: `workflow/bundle-52`
Candidate commit: `291feb71bc9c6da8b4779fb8945ebe0e2ac775f7`
Worktree: `/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner/.kw/worktrees/bundle-52`
This note is evidence for the controlling Agent. Do not treat it as acceptance or a finalize instruction.

## Behavioral examples

### Normal path (this run)

Cursor App Agent started at the canonical project root
`/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner` and invoked installed
`workflow-next` for exactly GitHub Issue #52. Workflow claimed the issue
(`claim: acquired`, `selected_project: bundle-52`) and created this child worktree and
branch. Runner session identity stayed the canonical-root conversation; the child
worktree is Workflow's working location.

### Evidence-backed exception (documented)

README and `references/workflow-worktree.md` record the Issues #50/#51 correction:
an Agent chose to stop in-worktree Claude Code sessions and restart at the canonical
root. That remains an Agent decision. Contract tests prove both PTY (`kaola-tmux.sh`
`--repo` Git-root check) and ACP (`kaola-acp.py resolve_repo`) accept a linked
worktree under `.kw/worktrees/` as a Git top-level and still reject a non-root
subdirectory. Adapters contain no `.kw/worktrees` refusal.

## Validation

- `./scripts/render-skills.py --write` then `--check`: PASS (budgets OK; Grok Bot host
  products unchanged)
- Focused: `tests/contract/test-issue-52-workflow-worktree.py` 9/9
- Full `./scripts/validate.sh`: exit 0
- `git diff --check`: clean
- Out of scope: `templates/grok-bot/`, `docs/grok-bot-host.md`, Issue #56 host UAT;
  did not touch `workflow/issue-53` or `workflow/issue-56`

## Close-out

Do not self-finalize, sink, close #52, merge, publish, or tag until the controlling
Agent accepts this delivery.
