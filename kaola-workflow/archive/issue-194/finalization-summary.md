# Finalization Summary — issue-194

## Delivered
#194: minimal Host QA guidance distinct from testing, evidenced-redundancy handling, adaptive
verification cadence, and a short Delegator pacing-feedback duty. `templates/orchestrator/SKILL.md.tmpl`
step 3 gets one short pointer to new `templates/orchestrator/references/qa-evidence.md`, which
covers when to assign bounded QA (an in-scope undemonstrated outcome, evidenced verification
redundancy, or an explicit request — at any point in scope, not only issue-literal wording or a
frozen delivery), who (existing profile judgment; visual work prefers an authorized Opus preset or
GPT-6 Sol first, then Kimi; Grok CLI/Cursor CLI default vs Cursor's Opus preset), tools/authority
(ordinary tool/environment failures are the Host's to resolve; `HUMAN_DECISION_REQUIRED` only for a
real gap), brief/return conventions distinguishing a record-only QA observation from an
evidenced-redundancy simplification (implementation-owner work), reading a failure, redundancy and
adaptive cadence at delivery points, and compact CLI/UI/docs-only examples.
`templates/kaola-delegator/SKILL.md.tmpl`'s existing follow-up-cadence sentence now also compares
outcomes, blockers, and repeated testing/QA against prior checks and relays the Host one new pacing
note when warranted, marking stall uncertainty — kept inline (no new reference file, per Host
steer) by tightening existing phrasing to fit the 4096 B budget. `templates/grok-bot/accepted-revision.json`
returns to the content stage (precedent commit 45031bda, #188) since this is the first template
change since the v0.6.5 pin; no release or pin is performed by this issue. README.md and
CHANGELOG.md note both changes. Reviewed against newly-filed #195 (a default-eligible worker-preset
pool, not yet implemented): current wording says only "already authorized" generically and never
asserts a per-seat individual-grant requirement, so it stays compatible once #195 lands; #195's own
list/authorization wording is intentionally not referenced or duplicated here, per the accepting
Host's explicit instruction (its owner will integrate overlapping guidance after this issue merges).
Host reviewed the source candidate at 35ad4937 across two rounds and accepted it.

## Files Changed
`templates/orchestrator/SKILL.md.tmpl`, `templates/orchestrator/references/qa-evidence.md` (new),
`templates/kaola-delegator/SKILL.md.tmpl`, `templates/grok-bot/accepted-revision.json`, `README.md`,
`CHANGELOG.md`, plus normally re-rendered generated output: `skills/kaola-project-runner/SKILL.md`,
`skills/kaola-project-runner/references/qa-evidence.md` (new), `skills/kaola-delegator/SKILL.md`,
every worker's `skills/*/scripts/main-skill-build.json` (main-skill hash moved), and
`hosts/grok-bot/{INSTALL.md,bridge.json,kaola-delegator.md}`. 22 files changed, 326 insertions(+),
79 deletions(-) at commit 35ad4937.

## Test Coverage
No new test files added (this issue changes Skill prose/guidance, not executable behavior); the
existing contract-test suite is the coverage for the generated Skills' exact content and byte
budgets. One regression was introduced and caught during this run: a byte-trimming edit reworded
`templates/kaola-delegator/SKILL.md.tmpl`'s canonical-invariance-probe anchor sentence, which broke
`tests/contract/test-issue-49-grok-bot-host.py`; fixed by reverting that one sentence to its exact
original wording rather than editing the test. Two other trims broke pinned substrings in
`test-issue-187-delegator-any-host.py` and `test-issue-86-delegator-quota.py`; also reverted.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- README.md
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
- skills/kaola-delegator/SKILL.md
- skills/kaola-project-runner/SKILL.md
- skills/kaola-project-runner/references/qa-evidence.md
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/grok-bot/accepted-revision.json
- templates/kaola-delegator/SKILL.md.tmpl
- templates/orchestrator/SKILL.md.tmpl
- templates/orchestrator/references/qa-evidence.md

## Documentation Docking
DOCKED — see `.cache/doc-docking.md` (README.md, CHANGELOG.md, and template sources checked;
docs/grok-bot-host.md and docs/conventions.md checked and unaffected).

## Follow-Up Items
None filed. No run-discovered defect independent of this issue's own edits was found; the one
regression found (canonical-invariance-probe anchor) was self-introduced and self-repaired before
Host acceptance, not a pre-existing defect. Coordination with #195 (default-eligible preset pool)
is intentionally deferred to #195's own implementation, per the accepting Host's explicit
instruction recorded in this run's conversation; not filed as a separate follow-up issue since #195
already exists and already states that ownership.

## Status
READY — merge sink, verified issue closure, archive.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-194/.cache/doc-docking.md
- kaola-workflow/archive/issue-194/.cache/final-validation.md
- kaola-workflow/archive/issue-194/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-194/finalization-summary.md
- kaola-workflow/archive/issue-194/mission-ledger.jsonl
- kaola-workflow/archive/issue-194/workflow-state.md
