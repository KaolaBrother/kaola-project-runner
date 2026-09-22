# #133 Runner read side: Host reads kaola-workflow/.ledger/issue-<N>.jsonl only; Mission List hard-retired (Owner override: no legacy transition, absent ledger = unknown; PR delivery, no self-merge)

1. item: rewrite templates (orchestrator SKILL + references, heartbeat skeleton, codex-host compact-recovery, kaola-delegator SKILL + handoff) to ledger-only wording; contract block §3 of #133 governs; replace, never append; render --write within budgets
   status: done
   dispatched: self (worktree .kw/worktrees/issue-133)
   result: 7 templates rewritten + issue-dispatch.md ledger section; rendered SKILL 17383/17408, handoff 8176/8192, skeleton 8189/8192, issue-dispatch 5991; zero Mission List residue in skills/ hosts/
2. item: .gitignore gains `kaola-workflow/.ledger/`; `git check-ignore -q kaola-workflow/.ledger/x` exits 0
   status: done
   dispatched: self
   result: .gitignore line added; check-ignore rc=0
3. item: contract tests — ledger projection read (fixture issue-7 → `1 / 3 [(3, 'blocked')]`), absent file = unknown, rendered surfaces carry no Mission List keeper sentence; repin #72/#74/#75 pins without reducing assertions; wire into validate.sh
   status: done
   dispatched: self
   result: tests/contract/test-issue-133-mission-ledger.py (5 tests OK) wired into validate.sh all+lane b; #72/#74/#75 pins repinned, assertion count unchanged
4. item: docs — README, docs/architecture.md, CHANGELOG Unreleased; frozen historical smoke/decision docs untouched
   status: done
   dispatched: self → README.md, docs/architecture.md, CHANGELOG.md in worktree
   result: README 6 sites + ledger sentence, architecture.md:256, CHANGELOG Unreleased entry; historical docs untouched
5. item: gates — render-skills --check PASS with measured byte sizes; validate.sh rc=0 (foreground)
   status: done
   dispatched: self (foreground validate on worktree)
   result: render --check PASS; validate.sh rc=0 (/tmp/v133.log); committed as b7378ad
6. item: open PR from workflow/issue-133, post PR URL on #133; await Host acceptance, no self-merge
   status: done
   dispatched: self → push workflow/issue-133 + gh pr create
   result: PR https://github.com/KaolaBrother/kaola-project-runner/pull/134 ; URL posted on #133; awaiting Host acceptance (no self-merge)
7. item: Owner revision (issuecomment-5770305093): terminal-state rule — all-terminal + forge OPEN = finalize/archive in progress (wait); all-terminal + CLOSED or run already archived = forgotten archive = stuck (report, name owner; neither unknown nor done); vanished file = archive done. Into issue-dispatch.md ledger section + one test case; re-gate; push to workflow/issue-133 (same PR #134)
   status: done
   dispatched: self → templates/orchestrator/references/issue-dispatch.md + tests/contract/test-issue-133-mission-ledger.py in worktree; push updates PR #134
   result: commit 394caf7 pushed to workflow/issue-133 (PR #134 head); TerminalLedger test OK (6/6); render --check PASS; validate.sh rc=0 (/tmp/v133b.log) before CHANGELOG-only sentence, #24/#49 re-run rc=0 after; awaiting Host final acceptance
