# Finalization Summary — issue-202

## Delivered

Issue #202: the Host worker-profiles shared reference and the Kaola-Delegator guidance both now
relay the owner's pool-vs-limited-seat capability policy. Added to
`templates/orchestrator/references/worker-profiles.md.tmpl` (+ generated
`skills/kaola-project-runner/references/worker-profiles.md`): the six-preset pool is cheaper and
generally weaker than the individually authorized limited seats outside it, so it exists for useful
uncapped parallel throughput; for a complex or critical task, prefer a stronger authorized limited
seat when available, then pick the specific worker from the profile rows by task fit; framed as the
owner's heuristic, not a benchmark or a universal-win claim, and not an implication that pool
members (GLM, SWE-2) can only do narrow work. The same policy, framed as something the Delegator
relays rather than judges itself, was added to
`templates/kaola-delegator/references/host-platforms.md.tmpl` (+ generated
`skills/kaola-delegator/references/host-platforms.md`) — `SKILL.md.tmpl` was ruled out as the fit
since the generated `skills/kaola-delegator/SKILL.md` was already at 4085/4096 B. No table
duplication, rankings, scores, routers, or mandatory QA layer; pool membership, the
concurrency-cap exemption, model/effort, seat-binding, permissions, and the Fable/Fable
Fusion/Astra limits are all unchanged. `templates/grok-bot/accepted-revision.json` moved to content
stage in this run's tree, per the existing convention for unreleased main past the v0.6.7 pin; the
v0.6.7 tag and the main checkout's own accepted-revision.json were left untouched (verified).
Wording was written fresh this run; nothing was reused from the abandoned issue-201 run.

Issue parts → evidence:
- "Host worker-profiles shared reference" → `templates/orchestrator/references/worker-profiles.md.tmpl` edit, commit 0aa99ff2.
- "Delegator guidance... relays... only the Host dispatches" → `templates/kaola-delegator/references/host-platforms.md.tmpl` edit (explicit "The Delegator relays this policy; it does not itself judge task fit" line), commit 0aa99ff2.
- "Keep all three wording elements" → present on both surfaces, confirmed by independent review (agent a54185340267ee93b, PASS).
- "No full-table duplication / rankings / routers / QA layers / membership / exemption / model-effort / seat-binding / permission / Fable-Astra changes" → confirmed by diff inspection and independent review; render --check budgets OK.
- "GLM/SWE profiles include substantial/full-cycle tasks" → verified against `platforms/zcode.yaml` (`default_model_profile`: "carry substantial tasks toward completion") and `platforms/devin.yaml` (`default_model_profile`: "capable full-cycle engineering worker").

## Files Changed

templates/orchestrator/references/worker-profiles.md.tmpl; templates/kaola-delegator/references/host-platforms.md.tmpl;
templates/grok-bot/accepted-revision.json; skills/kaola-project-runner/references/worker-profiles.md;
skills/kaola-delegator/references/host-platforms.md; hosts/grok-bot/INSTALL.md; hosts/grok-bot/bridge.json;
hosts/grok-bot/kaola-delegator.md; skills/*/scripts/main-skill-build.json (10 generated, fingerprint-only);
CHANGELOG.md. Commits 0aa99ff2, 61bd3378.

## Test Coverage

Focused: 7 contract suites matched by grepping for worker-profiles/host-platforms/generated-skills
(test-issue-187-delegator-any-host.py 14 ok, test-issue-74-kaola-delegator.py 187 assertions 0
failed, test-issue-65-steering.py 27 ok, test-issue-52-workflow-worktree.py 9 ok, test-runner-v2.py
4 ok, test-issue-111-model-tiers.py 25 ok, test-issue-94-zcode-native-skill-entry.py 30 ok) plus
test-progressive-disclosure.py (budgets.json's own named enforcement suite, 15 ok); all pass on
commit 0aa99ff2 (bytes unchanged by 61bd3378, which only touches CHANGELOG.md). `render-skills.py
--check` PASS, budgets OK. See .cache/final-validation.md.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- hosts/grok-bot/INSTALL.md
- hosts/grok-bot/bridge.json
- hosts/grok-bot/kaola-delegator.md
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-delegator/references/host-platforms.md
- skills/kaola-project-runner/references/worker-profiles.md
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/grok-bot/accepted-revision.json
- templates/kaola-delegator/references/host-platforms.md.tmpl
- templates/orchestrator/references/worker-profiles.md.tmpl

## Documentation Docking

DOCKED — see .cache/doc-docking.md.

## Follow-Up Items

None filed. Host acceptance of commit 0aa99ff2 is recorded in the Host conversation.

## Readiness

Ready: Host-accepted 0aa99ff2, validation pass (reused, bytes unchanged), independent review PASS,
docs docked, tag/pin verified untouched. Sink: merge into local main, close #202.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-202/.cache/doc-docking.md
- kaola-workflow/archive/issue-202/.cache/final-validation.md
- kaola-workflow/archive/issue-202/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-202/finalization-summary.md
- kaola-workflow/archive/issue-202/mission-ledger.jsonl
- kaola-workflow/archive/issue-202/workflow-state.md
