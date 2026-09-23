# Finalization Summary — bundle-148 (Issue #148)

Candidate: workflow/bundle-148 @ ace35ab (frozen; validated_candidate_hash bf1229799411283c16901b60e7906c3a7637c32f9243817e2708a3a1243f51d3)
Run posture: cross-machine continuation — implementation phase on the Mac mini (Mini Host zcode-KPR-orchestrator-dsh-acp), Delivery/validation/acceptance phase on Mac Studio (this Host, zcode-KPR-orchestrator-delivery-148, holder a3e4645a247b2732d5294d514c3f9f95).

## Delivered

Issue #148 "Tool + contract: query model↔quota-package for consumer agents (and Terminal Usage)":

1. Read-only quota catalog queries (10c90a1): `kaola-acp packages [--platform P] [--installed-only]` and `kaola-acp model-package --platform P --model ID` — no agent start, no session, no holder, no record, no quota burn; unknown id resolves `status: unmapped, packageId: null`, never a guessed package.
2. ACP quotaPool stamps (0cd0bbf): `observe`/`status` stamp model leaves on the emitted receipt (`quotaPool` qualified id or `quotaPool: null` + `quotaPoolStatus: "unmapped"`); `view` adds `models.availableModels`/`models.options` from a copy; stored `session_meta`/`record.json` stay native.
3. Contract documentation (a8173a6): docs/api.md §Quota packages, README query lane, Project Runner `references/quota-packages.md`, per-platform acp.md pointers; progressive-disclosure byte budgets respected (render --check PASS).
4. Verified model-id mappings (d229f25, REVIEW_REJECT repair): claude-code default/opus/sonnet/haiku → subscription, fable → scoped-weekly; cursor-cli auto → cursor-models, grok-4.7 / grok-4.7-xhigh / grok-4.7-xhigh-fast, claude-opus-5-5 / claude-opus-5-5-high → other-models; tests expect each mapping.
5. Cursor advertised auto-select binding (ace35ab, Studio repair): live parameterized picker advertises Auto as wire id `default`; rule now binds both `default` and seeded `auto` onto cursor-models (same convention as claude-code's `default`).

## Files Changed

87 paths at ace35ab vs main base d62ab08 (full list in finalize --check receipt): platforms/*.yaml (quota_packages + model_package_rule fields), scripts/{kaola-quota,kaola-acp,kaola-acp-holder,render-skills,validate}.py|sh, docs/api.md, README.md, templates/references/acp.md.tmpl + templates/orchestrator/, hosts/grok-bot/{INSTALL.md,bridge.json,kaola-delegator.md,templates/grok-bot/accepted-revision.json}, generated skills/** copies (10 platforms + orchestrator), tests/contract/{test-issue-148-quota-packages,test-issue-33-config-meta,test-issue-64-receipt-bound}.py.

## Test Coverage

- tests/contract/test-issue-148-quota-packages.py: 14/14 OK at ace35ab (mapping table incl. cursor-cli `default` case added by ace35ab, unmapped cases, dsh provider-prefix forms).
- render-skills.py --check: PASS (10 workers + orchestrator + delegator + grok-bot bridge, budgets OK).
- tests/contract/test-issue-33/64 re-run green post-repair under the validate.sh environment.
- Full `./scripts/validate.sh`: 3 suite failures on this machine, all machine-environment gaps with zero file overlap with this branch's diff — filed: #151 (P3). Not candidate defects.

## Validation

- Automated (recorded receipt, verdict pass): `python3 scripts/render-skills.py --check && python3 tests/contract/test-issue-148-quota-packages.py` at frozen ace35ab; .cache/final-validation.md.
- Manual/live (Studio, worktree build only; installed pin v0.5.9 untouched):
  - packages/model-package queries: all 10 platforms, mapped + unmapped cases correct (droid seat droid-KPR-i148-quota-validate; Host spot-read).
  - Live ACP stamps: cursor-cli 80 model leaves 0 mismatches (post-ace35ab), grok all leaves grok:account, opencode 76 leaves all unmapped (no provider advertised), dsh opencode-go mapped + deepseek-official unmapped (declared gap), droid 168 observe leaves / 56 view rows all unmapped (native billingPool absent — contract-correct). Sessions: one per platform, initialize-only, all exact-stopped, residual_pids [] (droid seat + Host).
- Review: grok-KPR-i148-quota-review-2 over frozen tip ace35ab — REVIEW_PASS, zero blocking findings; verdict read from the holder event log by the Host (the bounded capture window truncated the body; full text extracted from events.jsonl).
- Host acceptance: PASS 2026-09-23 (all issue acceptance-sketch legs satisfied: query tool without agent start; live rows carry quotaPool or explicit unmapped; new upstream id unmapped; contract documented for Host/workers/Terminal).
- Unexecuted: full validate.sh clean pass on Studio (blocked by machine-env gaps, #151); claude-code/codex live stamp checks on Studio (not in this Delivery's authorized platform set; contract tests + claude-code bridge source citations cover the mapping, and claude-code/codex were live-verified in the Mini phase of this run).

## Changed Paths

From the finalize transaction's own receipt (87 paths, base d62ab08 → ace35ab): README.md; docs/api.md; hosts/grok-bot/{INSTALL.md,bridge.json,kaola-delegator.md}; platforms/{claude-code,codex,cursor-cli,devin,droid,dsh,grok,kimi-cli,opencode,zcode}.yaml; scripts/{kaola-acp-holder.py,kaola-acp.py,kaola-quota.py,render-skills.py,validate.sh}; skills/** (all ten platform copies + skills/kaola-project-runner/SKILL.md + references/quota-packages.md); templates/grok-bot/accepted-revision.json; templates/orchestrator/{SKILL.md.tmpl,references/quota-packages.md}; templates/references/acp.md.tmpl; tests/contract/{test-issue-148-quota-packages.py,test-issue-33-config-meta.py,test-issue-64-receipt-bound.py}.

## Documentation Docking

DOCKED — .cache/doc-docking.md. CHANGELOG entry intentionally deferred to the next release cut per Owner ruling (no version bump in this run); all other public-behavior surfaces documented on the branch.

## Follow-Up Items

- filed: #151 (P3) — Studio dev-machine prerequisites for the full contract suite (tmux, bash-4 mapfile/BASHPID, python≥3.10 pathlib).
- CHANGELOG entry + next release (v0.6 intent, not 0.5.x) owned by the release cut after issues 148/150/149 closeout; sync Mini and Studio to the same accepted pin first (Owner ruling, post-closeout intent only).
- Issue 150 sinks behind this run (separate run, not bundled).
- Mini main checkout still holds the implementation-phase ledger/state of this run (machine-local, gitignored); this Studio ledger records the continuation frontier with commit-level locators. No action required.
- Observed, not filed: one transient cursor-cli `acp-session-timeout` on start (live2 attempt); retried clean same run.

## Readiness

READY — validation pass (recorded), review PASS, Host acceptance done, docs docked, follow-up filed. Proceed: finalize transaction (archive) → sink-merge into main (no PR per Owner) → close issue 148 (single-issue set).

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/bundle-148/.cache/doc-docking.md
- kaola-workflow/archive/bundle-148/.cache/final-validation.md
- kaola-workflow/archive/bundle-148/finalization-summary.md
- kaola-workflow/archive/bundle-148/mission-ledger.jsonl
- kaola-workflow/archive/bundle-148/workflow-state.md
