# Issue 237 — live model name and current pair

## Delivered

Outer review corrections on the merged #237 delivery. A direct native id that the same manifest already declares gets that declaration's display name, with `preset_id` and `preset_effort` left null and the invocation's own effort unchanged. `view.model.current` reads the live model id and effort from `session_meta.configOptions`; `start_evidence` stays the launch record. The display contract test keeps the changed identities, override acceptance and rejection, known direct selection, preserved resume, and the current-option pair.

## Candidate

80eb58605645ccdc28fb94118d29837529001319, workflow/issue-237.
Worktree: /Users/ylmacstudio/Workspace/kaola-project-runner/.kw/worktrees/issue-237

## Evidence and acceptance

Host ACCEPTANCE: PASS. The Host judged the pre-commit diff (36 files, +1201/−318) against the three review findings and independently reran the checks below. This finalize commits that same tree as 80eb5860.

Host reruns, all green:
- `python3 tests/contract/test-issue-237-model-display.py` — 10 tests OK
- `python3 tests/contract/test-acp-contract.py` — 80 tests OK
- `python3 tests/contract/test-issue-148-quota-packages.py` — OK
- `python3 tests/contract/test-issue-111-model-tiers.py` — OK
- `./scripts/render-skills.py --check` — PASS (content stage, budgets OK)

Finding 1: `declared_display_name` labels an exact `*_model_id`, assigns no preset and no preset effort; unknown ids stay null; a preserved resume start display stays all null. Finding 2: `view.model.current` is the live pair from `session_meta` only, with `name_provenance: catalog-declared`; launch facts stay historical; Devin advertised-model semantics stay. Finding 3: no whole-catalog EXPECTED table and no doc-substring mirrors; 10 focused regressions.

Manifests, presets, Grok bridge/guide surfaces, and protected files were untouched. `test-issue-218` was not rerun; catalog rows were unchanged. No release, tag, install, or CHANGELOG release section.

## Known failures or unverified scope

No remaining failure in the affected checks. No ten-platform model, price, or capability probe. No pin-stage run, because Grok bridge and guide surfaces had zero diff.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- docs/api.md
- scripts/kaola-acp-holder.py
- scripts/kaola-acp.py
- scripts/kaola-quota.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-quota.py
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-quota.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-quota.py
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-quota.py
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-quota.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-quota.py
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-quota.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-quota.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-quota.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-quota.py
- tests/contract/test-acp-contract.py
- tests/contract/test-issue-237-model-display.py

## Follow-Up Items

None. The three findings are the correction of this same issue, not a new defect.

## Readiness

Ready to merge and close the reopened issue.

## Sink Findings

post_rebase_tests: skipped
