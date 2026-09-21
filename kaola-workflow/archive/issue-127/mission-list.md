# #127 Grok 4.6→4.7 adaptation (grok + cursor-cli)

1. item: Live read-only confirmation of Cursor slug/ACP value/footer (cursor-grok-4.7-xhigh / grok-4.7 / Cursor Grok 4.7 Extra High) and Grok CLI advertised grok-4.7; temp-root probes only, no user-config mutation; mismatch → HUMAN_DECISION_REQUIRED
   status: done
   dispatched: self; evidence lands in kaola-workflow/issue-127/live-confirm.md
   result: BLOCKED — HUMAN_DECISION_REQUIRED: ACP grok-4.7 matches on both CLIs; Cursor picker slug is grok-4.7-xhigh (not cursor-grok-4.7-xhigh), name "Grok 4.7  Extra High" (no Cursor prefix); footer unobserved. See live-confirm.md
2. item: [Host ruling 2026-09-22: Option 1, measured names] Isolated-HOME Cursor TUI footer probe, then apply #127 list A–E with measured Cursor names (grok-4.7-xhigh), footer regex without "Cursor" prefix, record Cursor CLI version; post short errata comment on #127 in worktree .kw/worktrees/issue-127, render --write, CHANGELOG Unreleased entry; keep G-section history
   status: done
   dispatched: self; footer evidence → live-confirm.md, code → worktree .kw/worktrees/issue-127 branch workflow/issue-127
   result: candidate af6b45d (17 source files, 51 literal replacements + policy regex/return/fallback + new cursor footer test; 28 generated files via render); footer evidence in live-confirm.md; errata posted issuecomment-5765065615
3. item: Gates: render --check + validate.sh rc=0, residue grep, doc-impact
   status: done
   dispatched: self; validate log → kaola-workflow/issue-127/validate.log
   result: render --check PASS; validate.sh rc=0 (0 RED) on af6b45d tree; test-model-policy.sh (not in validate) 12 RED identical to base 253bbe8, new #127 test green; test-lifecycle-contract.py (not in validate) 9 RED identical to base; residue grep = only kept dated items; doc-impact: AGENTS.md, docs/conventions.md, CHANGELOG updated
