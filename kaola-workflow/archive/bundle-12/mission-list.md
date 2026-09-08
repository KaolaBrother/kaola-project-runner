# Add optional Workflow advice to all five Runner Skills (Issue #12)

## 1
item: Deliver concise shared Workflow advice and aligned README for all supported runtimes, preserving the communication-only implementation.
status: done
dispatched: self; implementation in .kw/worktrees/bundle-12/templates/SKILL.md.tmpl, generated skills/*/SKILL.md and README.md.

result: Shared template, five generated Skills and README updated; no runtime scripts or frozen golden files changed. Issue #12 body verified non-empty (2096 characters by initial read; exact count recorded separately if needed).

## 2
item: Establish readiness through generated-surface validation and review against Issue #12 acceptance.
status: done
dispatched: independent code-reviewer; review outcome in kaola-workflow/bundle-12/.cache/review.md; self runs render/check and validate.sh.

result: render --check, validate.sh (five Skills and 12 tests) and diff --check passed; independent final eight-file review passed with zero findings in .cache/review.md. Ready for finalization; no live CLI behavior claimed.

Evidence correction: gh issue view 12 --json body --jq '.body | length' returned 2052. The earlier 2096 count in item 1 was a transcription error; the verified body is non-empty.
