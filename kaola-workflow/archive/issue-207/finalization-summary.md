# Finalization Summary — issue-207

## Delivered

Issue #207 (body + owner comment): minimal confirmed-quota-exhaustion recovery guidance in the
existing Delegator and Host paths, using the #206 Expert/Worker/Elite classes, with no login.

Issue parts → evidence (commit 3720111d):
- Trigger = confirmed exhaustion only; generic 429/auth/timeout/transient/catalog-reset metadata
  is not; unknowns preserved; no probe/retry/detector → quota-packages.md §Confirmed exhaustion
  para 1; host-brick.md §Quota-exhausted Host para 1; README §Quota exhaustion.
- Evidence retained in existing records; shared pool is not fresh quota (error/`quotaPool`/
  `model-package`; unmapped proves neither) → quota-packages.md para 1.
- Host → Delegator replaces with one ZCode Host via existing exact-stop/new-Host handoff, platform
  not re-asked, carries grants/issues/evidence/worker ownership/pending close-out, never two Hosts,
  never resumes a foreign native id as ZCode → host-brick.md steps 1–2.
- Already-ZCode or inoperable fallback → preserve state, ask the user, no recreate loop (owner
  comment) → host-brick.md step 3.
- Expert → preserve task, ask user; no substitute/reuse/downgrade; unrelated work continues →
  quota-packages.md table row Expert.
- Elite → reclaim seat, remove grant/availability from this run's heartbeat snapshot, hand to
  another authorized Elite (not shown on the exhausted pool) within caps; no restart under old
  grant or model switch; user reauthorizes; revocation stays out of later Delegator handoffs /
  KPR-update reconciliation → quota-packages.md row Elite; host-brick.md closing para.
- Worker → another suitable Worker preset under pool permission, exemption kept, real limits
  apply, no cycling an exhausted shared pool → quota-packages.md row Worker.
- No suitable same-class replacement → report and ask; no class crossing, grant creation or
  discarded work; same issue run, single writer, no duplicate claim/redo; revocation scoped to the
  seat in this run → quota-packages.md closing para.
- No-login (attempt/retry/delegate login, logout/login cycling, credential refresh/replacement,
  account switching; no credential/billing/quota purchase change; auth evidence to the user) →
  quota-packages.md "Never log in"; host-brick.md "Never log in"; pointers in both entry Skills.
- Concise entry pointers → kaola-delegator SKILL (`[Bricked or quota-exhausted Host]…; never log
  in.`), kaola-project-runner SKILL quota line, worker-profiles pointer.
- No registry/watcher/retry loop/classifier/quota engine/probe; transport/CLI/permission/model
  surfaces unchanged (no scripts/ or platforms/ diff).

Host acceptance: ZCode Host zcode-KPR-orchestrator-main (holder 626a061e) accepted tip 3720111d
and authorized finalize (merge sink, push, close, archive; no release/tag/install).

## Files Changed

templates/orchestrator/{SKILL.md.tmpl, references/quota-packages.md,
references/worker-profiles.md.tmpl}; templates/kaola-delegator/{SKILL.md.tmpl,
references/host-brick.md}; README.md; CHANGELOG.md; regenerated skills/** (5 rendered docs + 10
main-skill-build.json). Commit 3720111d.

Rendered bytes (budget unchanged) before 61f75a68 → after 3720111d:
- kaola-project-runner/SKILL.md 17404 → 17401 / 17408
- kaola-delegator/SKILL.md 4091 → 4094 / 4096
- kaola-delegator/references/host-brick.md 909 → 2810 / 8192
- kaola-project-runner/references/quota-packages.md 4509 → 7076 / 8192
- kaola-project-runner/references/worker-profiles.md 6497 → 6637 / 8192
- hosts/grok-bot/kaola-delegator.md 2555 → 2555 / 2560 (unchanged)

## Test Coverage

render-skills.py --check PASS (budgets OK) on 3720111d. Full ./scripts/validate.sh on 3720111d
(log /tmp/kpr-i207-validate.log): exit 1 with only test-issue-65-host-contract (2:
test_reference_keeps_turn_end_and_exit_as_equal_triggers,
test_reference_starts_the_worker_from_the_host_with_a_runnable_example) and
test-issue-162-upgrade-safety (1: test_release_note_rule_and_no_rebind_wording); identical names
and assertion text on a clean export of main 61f75a68 (/tmp/kpr-main-validate.log) — pre-existing,
tracked as #209. All other suites PASS. Focused scenario read-through of the diff done by the
implementer and independently by the Host. No live quota-exhaustion or model test (out of scope).

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- README.md
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-delegator/SKILL.md
- skills/kaola-delegator/references/host-brick.md
- skills/kaola-project-runner/SKILL.md
- skills/kaola-project-runner/references/quota-packages.md
- skills/kaola-project-runner/references/worker-profiles.md
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/kaola-delegator/SKILL.md.tmpl
- templates/kaola-delegator/references/host-brick.md
- templates/orchestrator/SKILL.md.tmpl
- templates/orchestrator/references/quota-packages.md
- templates/orchestrator/references/worker-profiles.md.tmpl

## Documentation Docking

DOCKED — see .cache/doc-docking.md.

## Follow-Up Items

- None filed. Pre-existing 65/162 failures already tracked as #209 (open).
- Main Skill trims to stay in budget: removed "ZCode or not", "(already claimed / in flight)" →
  "(claimed or in flight)", dropped "that default is not an extra engine" (Report section still
  forbids a close-out dashboard/ledger). Recorded for the Host's cumulative QA from v0.6.7.

## Readiness

READY — accepted by Host; merge sink; close #207 on verified merge.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-207/.cache/doc-docking.md
- kaola-workflow/archive/issue-207/.cache/final-validation.md
- kaola-workflow/archive/issue-207/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-207/finalization-summary.md
- kaola-workflow/archive/issue-207/mission-ledger.jsonl
- kaola-workflow/archive/issue-207/workflow-state.md
