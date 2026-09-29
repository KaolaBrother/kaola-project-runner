# Issue 236 — pinned guide budget correction

## Delivered
Compressed only the Grok Bot install guide introduction and regenerated its product. All installation, UAT, recovery and target boundaries remain; budget and tests unchanged.

## Candidate
f22661ac, workflow/issue-236.

## Evidence and acceptance
Outer personally reproduced three failures on 11ebd3b8 in test-issue-49-grok-bot-host.py: pinned INSTALL.md was 8267 B > 8192 B. Content-stage render passed, so the earlier outer review missed the pin-stage expansion. This corrects the earlier broad PASS statement.
On f22661ac: render --check PASS; existing issue49 suite45/45 PASS (including all three pin regressions); progressive-disclosure15/15 PASS; diff --check PASS. Logs /tmp/kpr236-budget-issue49.log and /tmp/kpr236-budget-progressive.log. Renderer measurement: content7965 B, pinned8102 B; fixed ceiling8192 B. Personal source/generated diff review: only introductory prose shortened, operational instructions unchanged. Acceptance PASS for this correction.

## Known failures or unverified scope
No remaining failure in affected checks. Full unrelated transport suite not rerun for this prose-only correction. No release, tag, installation or live account write.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- hosts/grok-bot/INSTALL.md
- templates/grok-bot/INSTALL.md.tmpl

## Follow-Up Items
None. Same issue correction, not a new independent defect.

## Readiness
Ready to merge and close the reopened issue.

## Sink Findings

post_rebase_tests: skipped

Published: f22661ac verified on main; issue closed after merge, worktree/branches removed.
