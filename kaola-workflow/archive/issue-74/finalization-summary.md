# Issue #74 — finalization summary

Run: `issue-74` · Issue: **#74** · Branch: `workflow/issue-74` · Sink: merge to `main`
Accepted candidate (outer review): `eb9585208d40da0c9f21add3596278833b0ba3bb`
Base at ACCEPT: origin/main `513e8e1f82172fce3145c893c6db3072759ea457`
Finalized head: the archive commit on this branch (product bytes remain `eb95852`; no product mutation after ACCEPT).

## Delivered

Kaola-Delegator (`kaola-delegator`) is the external delegation Skill for Grok Bot,
generic `--skills-dir`, and Codex. It extracts goal, progress, authorized
platforms, quota (concurrency / account / token kept as separate figures),
priority, and delivery/stop boundary, then starts or resumes **one** ZCode ACP
Host that must load Project Runner. The outer Agent does not dispatch workers,
copy a Mission List, or run the inner heartbeat.

Project Runner consuming entries are Codex, generic, and ZCode. Grok Bot is a
bridge host only (`hosts/grok-bot/kaola-delegator.md`); it is not a Project
Runner host and has no installer destination. Nine platform workers are
unchanged. `templates/grok-golden/` is frozen.

Live Host recovery uses the canonical Git root, the standard Runner session
name `zcode-<PROJECT>-orchestrator-<purpose>`, and existing Runner
`status`/receipts. There is no `.kaola/delegator-host.json`. Three ids stay
separate: Runner `--session`, `acp_session_id`, native `sess_*`. Exact stop
and live attach bind receipt `holder_instance_id` via
`--expected-holder-instance-id`. After exact stop, try attested native
`--resume` first; native resume is backend-dependent. A new Host is allowed
only after proven resume failure and complete authorization. Installer
`--platform` still filters workers; an already-installed Delegator is included
on later filtered Codex/generic reinstall/uninstall.

Budgets: `external_skill_bytes` 4096 (new); existing ceilings unchanged.
Measured on `eb95852`: Skill 3824/4096, handoff 8189/8192, bridge 2536/2560,
Project Runner 16494/17408.

No release, no global install, no account Skill rewrite.

## Files Changed

45 tracked paths (`git diff --name-only origin/main...HEAD` at `eb95852`):

`AGENTS.md`, `CHANGELOG.md`, `README.md`, `docs/README.md`, `docs/api.md`,
`docs/architecture.md`, `docs/conventions.md`, `docs/grok-bot-host.md`,
`hosts/grok-bot/INSTALL.md`, `hosts/grok-bot/bridge.json`,
`hosts/grok-bot/kaola-delegator.md` (renamed from `kaola-project-runner.md`),
`scripts/install-local.sh`, `scripts/kaola-grok-bot-verify.py`,
`scripts/render-skills.py`, `scripts/validate.sh`,
`skills/kaola-delegator/` (generated), `skills/kaola-project-runner/`
(generated; Grok Bot host reference removed), `templates/budgets.json`,
`templates/grok-bot/`, `templates/kaola-delegator/`,
`templates/orchestrator/`, `tests/contract/test-issue-74-kaola-delegator.py`
(new), plus installer/generated-skills/issue-49/progressive-disclosure and
related contract-test updates.

`skills/` and `hosts/grok-bot/` are renderer output.

## Test Coverage

New suite `tests/contract/test-issue-74-kaola-delegator.py` — **151
assertions** on this candidate, including: generated entry matrix / no engine
leak; fake ACP Host/worker/event/live status (labeled fake); adopt
nonstandard live Host without a second start; locator full attestation;
missing-authorization non-start is documentation-only (`measured: false`);
new standard Host after confirmed stop; numeric fixture quotas
(`quota_account=1 job`, `quota_token=10000 tokens`).

Installer runtime/migration tests cover Delegator install on Codex/generic,
skip on other runtimes, `--no-orchestrator`, and filtered reinstall/uninstall
not leaving a stale Delegator. `test-issue-49-grok-bot-host.py` retargeted to
the Delegator bridge. `scripts/validate.sh` registers the suite.

Live authentic A→B is not that suite: `evidence/live-ab-44a17b9/`.

## Validation

Recorded receipt: `verdict: pass`, `validated_candidate_hash`
`64ca6b1f3889f39c4da29d75203f11a2cdb4c3b6aac9163dd5d76591a6042d8a`.
Exact command (from candidate worktree `.kw/worktrees/issue-74` at `eb95852`):

```
./scripts/render-skills.py --check && ./scripts/validate.sh
```

This-finalize evidence `kaola-workflow/issue-74/evidence/finalize-eb95852/`:

- `render-skills.py --check`: **RENDER:0** (9 workers + Project Runner +
  kaola-delegator + grok-bot host 2536 B, content stage, unpinned).
- `./scripts/validate.sh`: **VALIDATE:0**, `failed_or_skipped []`.
- issue-74 checks: **151 assertions, 0 failed tests**.
- `kaola-grok-bot-verify: PASS`.
- HEAD remained `eb9585208d40da0c9f21add3596278833b0ba3bb`; dirty 0.

Prior freeze evidence (same product lineage): `validate-quota-figures/`
(focused 151 + full validate exit 0), `validate-resume-wording/`,
`validate-holder-fix/`, `live-ab-44a17b9/`.

Acceptance legs:

- Automated: render `--check` + full `validate.sh` on exact accepted bytes.
- Local isolation: authentic ZCode 3.12.3 A→B at `live-ab-44a17b9/`
  (Host `zcode-I74AB-orchestrator-main`, Devin `devin-I74AB-i74-receipt`,
  token `KAOLA74-AB-TOKEN`, B live attach, exact stop `residual_pids=[]`).
- Manual/outer: independent review of the diff (four prior fixes, conditional
  native resume wording, numeric quota fixture, AGENTS/README layering,
  installer filtered update), render `--check`, 151 focused assertions,
  full validate receipt, authentic A→B raw evidence, and a fresh Agent
  missing-token-quota non-start sentinel
  (https://github.com/KaolaBrother/kaola-project-runner/issues/74#issuecomment-5734458075).
- UAT: **Grok Bot account UAT remains explicitly unexecuted, not claimed.**
  User-owned acceptance exception under criterion 4. No follow-up filed.

## Changed Paths

Files this branch changed outside the run-state and documentation bands
(finalize `--check` measurement at `eb95852`):

- AGENTS.md
- hosts/grok-bot/INSTALL.md
- hosts/grok-bot/bridge.json
- hosts/grok-bot/kaola-delegator.md
- scripts/install-local.sh
- scripts/kaola-grok-bot-verify.py
- scripts/render-skills.py
- scripts/validate.sh
- skills/kaola-delegator/.generated-by-kaola-project-runner
- skills/kaola-delegator/SKILL.md
- skills/kaola-delegator/agents/openai.yaml
- skills/kaola-delegator/references/handoff.md
- skills/kaola-project-runner/SKILL.md
- skills/kaola-project-runner/references/grok-bot-host.md
- skills/kaola-project-runner/references/heartbeat-skeleton.md
- skills/kaola-project-runner/references/host-startup.md
- skills/kaola-project-runner/references/zcode-host-dispatch.md
- templates/budgets.json
- templates/grok-bot/INSTALL.md.tmpl
- templates/grok-bot/bridge.md.tmpl
- templates/kaola-delegator/SKILL.md.tmpl
- templates/kaola-delegator/agents/openai.yaml.tmpl
- templates/kaola-delegator/references/handoff.md.tmpl
- templates/orchestrator/SKILL.md.tmpl
- templates/orchestrator/references/grok-bot-host.md
- templates/orchestrator/references/heartbeat-skeleton.txt
- templates/orchestrator/references/host-startup.md.tmpl
- templates/orchestrator/references/zcode-host-dispatch.md.tmpl
- tests/contract/test-generated-skills.py
- tests/contract/test-installer-migration.sh
- tests/contract/test-installer-runtimes.sh
- tests/contract/test-issue-49-grok-bot-host.py
- tests/contract/test-issue-50-runner-integration.py
- tests/contract/test-issue-52-workflow-worktree.py
- tests/contract/test-issue-68-heartbeat-snapshot.py
- tests/contract/test-issue-74-kaola-delegator.py
- tests/contract/test-progressive-disclosure.py
- tests/contract/test-zcode-heartbeat-contract.py

## Documentation Docking

`.cache/doc-docking.md` — **DOCKED**. No product mutation after ACCEPT.
README / AGENTS / CHANGELOG / docs already describe Kaola-Delegator on
`eb95852`. Issue-body name correction (Zcode Orchestrator → Kaola-Delegator)
is a comment on #74 before close, not a follow-up issue.

## Follow-Up Items

None filed. Run-discovered items that are **not** this issue:

- Grok Bot account UAT: user-owned unexecuted exception; criterion 4 allows
  it. Do not file unless asked.
- Native resume after `session/close` on ZCode 3.12.3: owned by **#84**, not
  merged here. This candidate uses capability-dependent wording.
- ZCode 3.12+ adapter/runtimeModel compatibility: owned by **#79** (already
  on main). This candidate did not modify that adapter.

No release, no global install, no account Skill change.

## Readiness

Outer ACCEPT of exact `eb9585208d40da0c9f21add3596278833b0ba3bb` on base
`513e8e1`. All 30 Mission List items done. Documentation docked without
changing accepted bytes. Ready to archive, serial sink to `main`, push,
CLOSE #74, closure-audit, and exact-owned branch/worktree cleanup.
Preserve `#75` / `#81` / `#84` and all other sessions.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-74/.cache/doc-docking.md
- kaola-workflow/archive/issue-74/.cache/final-validation.md
- kaola-workflow/archive/issue-74/.cache/mirror-digest.json
- kaola-workflow/archive/issue-74/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-74/delivery.md
- kaola-workflow/archive/issue-74/evidence/00-external-skill.txt
- kaola-workflow/archive/issue-74/evidence/01-host-start.json
- kaola-workflow/archive/issue-74/evidence/01b-continuation.json
- kaola-workflow/archive/issue-74/evidence/01c-live-attach-before-prompt.json
- kaola-workflow/archive/issue-74/evidence/01d-continuation-after-handoff.json
- kaola-workflow/archive/issue-74/evidence/02-handoff.txt
- kaola-workflow/archive/issue-74/evidence/03-host-handoff-send.json
- kaola-workflow/archive/issue-74/evidence/04-host-rpc-prompts.json
- kaola-workflow/archive/issue-74/evidence/05-inner-runner-loaded.txt
- kaola-workflow/archive/issue-74/evidence/06-worker-start.json
- kaola-workflow/archive/issue-74/evidence/07-worker-send.json
- kaola-workflow/archive/issue-74/evidence/08-host-worker-events.json
- kaola-workflow/archive/issue-74/evidence/09-worker-rpc-prompts.json
- kaola-workflow/archive/issue-74/evidence/10-host-status.json
- kaola-workflow/archive/issue-74/evidence/11-sessions.json
- kaola-workflow/archive/issue-74/evidence/12-resume-boundary.txt
- kaola-workflow/archive/issue-74/evidence/13-old-host-pointer.json
- kaola-workflow/archive/issue-74/evidence/14-old-host-status.json
- kaola-workflow/archive/issue-74/evidence/15-old-host-sessions.json
- kaola-workflow/archive/issue-74/evidence/16-cannot-resume-after-stop.txt
- kaola-workflow/archive/issue-74/evidence/docs-freeze-sha.txt
- kaola-workflow/archive/issue-74/evidence/finalize-eb95852/exit.txt
- kaola-workflow/archive/issue-74/evidence/grok-bot-colocation/00-external-skill.txt
- kaola-workflow/archive/issue-74/evidence/grok-bot-colocation/01-host-start.json
- kaola-workflow/archive/issue-74/evidence/grok-bot-colocation/01b-start-receipt-ids.json
- kaola-workflow/archive/issue-74/evidence/grok-bot-colocation/01c-live-attach-before-prompt.json
- kaola-workflow/archive/issue-74/evidence/grok-bot-colocation/01d-ids-after-handoff.json
- kaola-workflow/archive/issue-74/evidence/grok-bot-colocation/02-handoff.txt
- kaola-workflow/archive/issue-74/evidence/grok-bot-colocation/03-host-handoff-send.json
- kaola-workflow/archive/issue-74/evidence/grok-bot-colocation/04-host-rpc-prompts.json
- kaola-workflow/archive/issue-74/evidence/grok-bot-colocation/05-inner-runner-loaded.txt
- kaola-workflow/archive/issue-74/evidence/grok-bot-colocation/06-worker-start.json
- kaola-workflow/archive/issue-74/evidence/grok-bot-colocation/07-worker-send.json
- kaola-workflow/archive/issue-74/evidence/grok-bot-colocation/08-host-worker-events.json
- kaola-workflow/archive/issue-74/evidence/grok-bot-colocation/09-worker-rpc-prompts.json
- kaola-workflow/archive/issue-74/evidence/grok-bot-colocation/10-host-status.json
- kaola-workflow/archive/issue-74/evidence/grok-bot-colocation/11-sessions.json
- kaola-workflow/archive/issue-74/evidence/grok-bot-colocation/12-resume-boundary.txt
- kaola-workflow/archive/issue-74/evidence/grok-bot-colocation/13-old-host-receipt.json
- kaola-workflow/archive/issue-74/evidence/grok-bot-colocation/14-old-host-status.json
- kaola-workflow/archive/issue-74/evidence/grok-bot-colocation/15-old-host-sessions.json
- kaola-workflow/archive/issue-74/evidence/grok-bot-colocation/16-stopped-new-host-boundary.txt
- kaola-workflow/archive/issue-74/evidence/grok-bot-colocation/20-first-host.json
- kaola-workflow/archive/issue-74/evidence/grok-bot-colocation/21-first-stop.json
- kaola-workflow/archive/issue-74/evidence/grok-bot-colocation/22-status-after-stop.json
- kaola-workflow/archive/issue-74/evidence/grok-bot-colocation/23-second-host.json
- kaola-workflow/archive/issue-74/evidence/grok-bot-colocation/23b-identity-delta.json
- kaola-workflow/archive/issue-74/evidence/grok-bot-colocation/24-second-status.json
- kaola-workflow/archive/issue-74/evidence/grok-bot-colocation/25-orchestrator-names.json
- kaola-workflow/archive/issue-74/evidence/grok-bot-colocation/26-new-host-handoff.json
- kaola-workflow/archive/issue-74/evidence/grok-bot-colocation/27-missing-auth-untested.json
- kaola-workflow/archive/issue-74/evidence/grok-bot-colocation/30-locator-zcode-host.json
- kaola-workflow/archive/issue-74/evidence/grok-bot-colocation/31-locator-bogus-worker.json
- kaola-workflow/archive/issue-74/evidence/grok-bot-colocation/32-locator-adopted-session.json
- kaola-workflow/archive/issue-74/evidence/grok-bot-colocation/33-locator-not-agent.txt
- kaola-workflow/archive/issue-74/evidence/live-ab-44a17b9/00-AUTH.txt
- kaola-workflow/archive/issue-74/evidence/live-ab-44a17b9/00-existing-session-names.txt
- kaola-workflow/archive/issue-74/evidence/live-ab-44a17b9/00-existing-sessions.err
- kaola-workflow/archive/issue-74/evidence/live-ab-44a17b9/00-existing-sessions.json
- kaola-workflow/archive/issue-74/evidence/live-ab-44a17b9/00-meta.txt
- kaola-workflow/archive/issue-74/evidence/live-ab-44a17b9/00-scratch-repo.txt
- kaola-workflow/archive/issue-74/evidence/live-ab-44a17b9/01-A-status-before.err
- kaola-workflow/archive/issue-74/evidence/live-ab-44a17b9/01-A-status-before.json
- kaola-workflow/archive/issue-74/evidence/live-ab-44a17b9/02-preflight.err
- kaola-workflow/archive/issue-74/evidence/live-ab-44a17b9/02-preflight.json
- kaola-workflow/archive/issue-74/evidence/live-ab-44a17b9/03-A-start.err
- kaola-workflow/archive/issue-74/evidence/live-ab-44a17b9/03-A-start.json
- kaola-workflow/archive/issue-74/evidence/live-ab-44a17b9/04-A-status-live.err
- kaola-workflow/archive/issue-74/evidence/live-ab-44a17b9/04-A-status-live.json
- kaola-workflow/archive/issue-74/evidence/live-ab-44a17b9/05-handoff.txt
- kaola-workflow/archive/issue-74/evidence/live-ab-44a17b9/06-A-handoff-send.err
- kaola-workflow/archive/issue-74/evidence/live-ab-44a17b9/06-A-handoff-send.json
- kaola-workflow/archive/issue-74/evidence/live-ab-44a17b9/07-sessions-after-dispatch.err
- kaola-workflow/archive/issue-74/evidence/live-ab-44a17b9/07-sessions-after-dispatch.json
- kaola-workflow/archive/issue-74/evidence/live-ab-44a17b9/08-worker-status.err
- kaola-workflow/archive/issue-74/evidence/live-ab-44a17b9/08-worker-status.json
- kaola-workflow/archive/issue-74/evidence/live-ab-44a17b9/09-B-status-live.err
- kaola-workflow/archive/issue-74/evidence/live-ab-44a17b9/09-B-status-live.json
- kaola-workflow/archive/issue-74/evidence/live-ab-44a17b9/10-heartbeat-prompt.json
- kaola-workflow/archive/issue-74/evidence/live-ab-44a17b9/10-worker-RECEIPT.txt
- kaola-workflow/archive/issue-74/evidence/live-ab-44a17b9/11-worker-capture.err
- kaola-workflow/archive/issue-74/evidence/live-ab-44a17b9/11-worker-capture.json
- kaola-workflow/archive/issue-74/evidence/live-ab-44a17b9/12-host-wait-after-worker.err
- kaola-workflow/archive/issue-74/evidence/live-ab-44a17b9/12-host-wait-after-worker.json
- kaola-workflow/archive/issue-74/evidence/live-ab-44a17b9/13-host-capture.err
- kaola-workflow/archive/issue-74/evidence/live-ab-44a17b9/13-host-capture.json
- kaola-workflow/archive/issue-74/evidence/live-ab-44a17b9/14-B-attach-status.err
- kaola-workflow/archive/issue-74/evidence/live-ab-44a17b9/14-B-attach-status.json
- kaola-workflow/archive/issue-74/evidence/live-ab-44a17b9/14-B-identity-delta.json
- kaola-workflow/archive/issue-74/evidence/live-ab-44a17b9/15-worker-status-after-host-closeout.err
- kaola-workflow/archive/issue-74/evidence/live-ab-44a17b9/15-worker-status-after-host-closeout.json
- kaola-workflow/archive/issue-74/evidence/live-ab-44a17b9/16-B-followup-send.err
- kaola-workflow/archive/issue-74/evidence/live-ab-44a17b9/16-B-followup-send.json
- kaola-workflow/archive/issue-74/evidence/live-ab-44a17b9/17-host-stop.err
- kaola-workflow/archive/issue-74/evidence/live-ab-44a17b9/17-host-stop.json
- kaola-workflow/archive/issue-74/evidence/live-ab-44a17b9/18-host-status-after-stop.err
- kaola-workflow/archive/issue-74/evidence/live-ab-44a17b9/18-host-status-after-stop.json
- kaola-workflow/archive/issue-74/evidence/live-ab-44a17b9/19-leftover-pgrep.txt
- kaola-workflow/archive/issue-74/evidence/live-ab-44a17b9/20-sessions-after-cleanup.err
- kaola-workflow/archive/issue-74/evidence/live-ab-44a17b9/20-sessions-after-cleanup.json
- kaola-workflow/archive/issue-74/evidence/live-ab-44a17b9/21-worker-stop-idempotent.err
- kaola-workflow/archive/issue-74/evidence/live-ab-44a17b9/21-worker-stop-idempotent.json
- kaola-workflow/archive/issue-74/evidence/live-ab-44a17b9/RESULTS.md
- kaola-workflow/archive/issue-74/evidence/live/00-no-iso-session-before.txt
- kaola-workflow/archive/issue-74/evidence/live/00-preflight.err
- kaola-workflow/archive/issue-74/evidence/live/00-preflight.json
- kaola-workflow/archive/issue-74/evidence/live/00-preflight.txt
- kaola-workflow/archive/issue-74/evidence/live/01-host-start.err
- kaola-workflow/archive/issue-74/evidence/live/01-host-start.json
- kaola-workflow/archive/issue-74/evidence/live/01-host-status.json
- kaola-workflow/archive/issue-74/evidence/live/01b-provisional-pointer.json
- kaola-workflow/archive/issue-74/evidence/live/02-handoff.txt
- kaola-workflow/archive/issue-74/evidence/live/02-original-input.txt
- kaola-workflow/archive/issue-74/evidence/live/03-host-handoff-send.err
- kaola-workflow/archive/issue-74/evidence/live/03-host-handoff-send.json
- kaola-workflow/archive/issue-74/evidence/live/03-status-after-failed-send.json
- kaola-workflow/archive/issue-74/evidence/live/03b-appserver-probe.err
- kaola-workflow/archive/issue-74/evidence/live/03b-appserver-probe.out
- kaola-workflow/archive/issue-74/evidence/live/03c-appserver-adapterenv.err
- kaola-workflow/archive/issue-74/evidence/live/03d-appserver-electron-node.err
- kaola-workflow/archive/issue-74/evidence/live/03d-appserver-electron-node.out
- kaola-workflow/archive/issue-74/evidence/live/03e-appserver-shim.err
- kaola-workflow/archive/issue-74/evidence/live/03e-appserver-shim.out
- kaola-workflow/archive/issue-74/evidence/live/03f-stop-broken-first-start.err
- kaola-workflow/archive/issue-74/evidence/live/03f-stop-broken-first-start.json
- kaola-workflow/archive/issue-74/evidence/live/04-host-start-shim.err
- kaola-workflow/archive/issue-74/evidence/live/04-host-start-shim.json
- kaola-workflow/archive/issue-74/evidence/live/04b-create-no-overlay.err
- kaola-workflow/archive/issue-74/evidence/live/04b-create-no-overlay.out
- kaola-workflow/archive/issue-74/evidence/live/04c-stop-before-retry.json
- kaola-workflow/archive/issue-74/evidence/live/05-host-start.err
- kaola-workflow/archive/issue-74/evidence/live/05-host-start.json
- kaola-workflow/archive/issue-74/evidence/live/05b-provisional-pointer.json
- kaola-workflow/archive/issue-74/evidence/live/05c-status-before-prompt.json
- kaola-workflow/archive/issue-74/evidence/live/06-host-handoff-send.err
- kaola-workflow/archive/issue-74/evidence/live/06-host-handoff-send.json
- kaola-workflow/archive/issue-74/evidence/live/06b-stop-nomodel.json
- kaola-workflow/archive/issue-74/evidence/live/07-host-start.err
- kaola-workflow/archive/issue-74/evidence/live/07-host-start.json
- kaola-workflow/archive/issue-74/evidence/live/07b-provisional-pointer.json
- kaola-workflow/archive/issue-74/evidence/live/08-host-handoff-send.err
- kaola-workflow/archive/issue-74/evidence/live/08-host-handoff-send.json
- kaola-workflow/archive/issue-74/evidence/live/09-native-ids.txt
- kaola-workflow/archive/issue-74/evidence/live/09-pointer-filled.json
- kaola-workflow/archive/issue-74/evidence/live/10-B-live-capture.json
- kaola-workflow/archive/issue-74/evidence/live/10-B-live-status.json
- kaola-workflow/archive/issue-74/evidence/live/11-host-stop.json
- kaola-workflow/archive/issue-74/evidence/live/11-leftover-pgrep.txt
- kaola-workflow/archive/issue-74/evidence/live/12-host-resume.err
- kaola-workflow/archive/issue-74/evidence/live/12-host-resume.json
- kaola-workflow/archive/issue-74/evidence/live/12b-stop-failed-resume.json
- kaola-workflow/archive/issue-74/evidence/live/13-host-resume.err
- kaola-workflow/archive/issue-74/evidence/live/13-host-resume.json
- kaola-workflow/archive/issue-74/evidence/live/13b-stop-resume-error-holder.json
- kaola-workflow/archive/issue-74/evidence/live/14-leftover-after-final-stop.txt
- kaola-workflow/archive/issue-74/evidence/live/14-status-after-stop.json
- kaola-workflow/archive/issue-74/evidence/live/15-live-results.md
- kaola-workflow/archive/issue-74/evidence/live/probe-list/00-events-first-process.json
- kaola-workflow/archive/issue-74/evidence/live/probe-list/00-summary.json
- kaola-workflow/archive/issue-74/evidence/live/probe-list/01-create.json
- kaola-workflow/archive/issue-74/evidence/live/probe-list/02-list-after-create-before-prompt.json
- kaola-workflow/archive/issue-74/evidence/live/probe-list/03-send.json
- kaola-workflow/archive/issue-74/evidence/live/probe-list/04-list-after-prompt.json
- kaola-workflow/archive/issue-74/evidence/live/probe-list/05-close.json
- kaola-workflow/archive/issue-74/evidence/live/probe-list/06-list-after-close-same-process.json
- kaola-workflow/archive/issue-74/evidence/live/probe-list/07-list-after-close-fresh-process.json
- kaola-workflow/archive/issue-74/evidence/live/probe-list/appserver.err
- kaola-workflow/archive/issue-74/evidence/live/probe-list/run-list-probe.py
- kaola-workflow/archive/issue-74/evidence/live/probe-sea/00-locate.txt
- kaola-workflow/archive/issue-74/evidence/live/probe-sea/01-doctor.err
- kaola-workflow/archive/issue-74/evidence/live/probe-sea/01-doctor.out
- kaola-workflow/archive/issue-74/evidence/live/probe-sea/02-appserver-help.err
- kaola-workflow/archive/issue-74/evidence/live/probe-sea/02-appserver-help.out
- kaola-workflow/archive/issue-74/evidence/live/probe-sea/03-appserver.err
- kaola-workflow/archive/issue-74/evidence/live/probe-sea/03-summary.json
- kaola-workflow/archive/issue-74/evidence/live/probe-sea/04-resume-appserver.err
- kaola-workflow/archive/issue-74/evidence/live/probe-stop-resume/00-summary.json
- kaola-workflow/archive/issue-74/evidence/live/probe-stop-resume/a-01-create.json
- kaola-workflow/archive/issue-74/evidence/live/probe-stop-resume/a-02-list-before-close.json
- kaola-workflow/archive/issue-74/evidence/live/probe-stop-resume/a-03-close.json
- kaola-workflow/archive/issue-74/evidence/live/probe-stop-resume/a-04-list-fresh-after-close.json
- kaola-workflow/archive/issue-74/evidence/live/probe-stop-resume/a-05-resume.json
- kaola-workflow/archive/issue-74/evidence/live/probe-stop-resume/appserver-a.err
- kaola-workflow/archive/issue-74/evidence/live/probe-stop-resume/appserver-a2.err
- kaola-workflow/archive/issue-74/evidence/live/probe-stop-resume/appserver-b.err
- kaola-workflow/archive/issue-74/evidence/live/probe-stop-resume/appserver-b2.err
- kaola-workflow/archive/issue-74/evidence/live/probe-stop-resume/b-01-create.json
- kaola-workflow/archive/issue-74/evidence/live/probe-stop-resume/b-02-list-before-kill.json
- kaola-workflow/archive/issue-74/evidence/live/probe-stop-resume/b-03-list-fresh-after-kill-no-close.json
- kaola-workflow/archive/issue-74/evidence/live/probe-stop-resume/b-04-resume.json
- kaola-workflow/archive/issue-74/evidence/live/probe-stop-resume/run-ab-probe.py
- kaola-workflow/archive/issue-74/evidence/post-stop-new-host/00-external-skill.txt
- kaola-workflow/archive/issue-74/evidence/post-stop-new-host/01-host-start.json
- kaola-workflow/archive/issue-74/evidence/post-stop-new-host/01b-start-receipt-ids.json
- kaola-workflow/archive/issue-74/evidence/post-stop-new-host/01c-live-attach-before-prompt.json
- kaola-workflow/archive/issue-74/evidence/post-stop-new-host/01d-ids-after-handoff.json
- kaola-workflow/archive/issue-74/evidence/post-stop-new-host/02-handoff.txt
- kaola-workflow/archive/issue-74/evidence/post-stop-new-host/03-host-handoff-send.json
- kaola-workflow/archive/issue-74/evidence/post-stop-new-host/04-host-rpc-prompts.json
- kaola-workflow/archive/issue-74/evidence/post-stop-new-host/05-inner-runner-loaded.txt
- kaola-workflow/archive/issue-74/evidence/post-stop-new-host/06-worker-start.json
- kaola-workflow/archive/issue-74/evidence/post-stop-new-host/07-worker-send.json
- kaola-workflow/archive/issue-74/evidence/post-stop-new-host/08-host-worker-events.json
- kaola-workflow/archive/issue-74/evidence/post-stop-new-host/09-worker-rpc-prompts.json
- kaola-workflow/archive/issue-74/evidence/post-stop-new-host/10-host-status.json
- kaola-workflow/archive/issue-74/evidence/post-stop-new-host/11-sessions.json
- kaola-workflow/archive/issue-74/evidence/post-stop-new-host/12-resume-boundary.txt
- kaola-workflow/archive/issue-74/evidence/post-stop-new-host/13-old-host-receipt.json
- kaola-workflow/archive/issue-74/evidence/post-stop-new-host/14-old-host-status.json
- kaola-workflow/archive/issue-74/evidence/post-stop-new-host/15-old-host-sessions.json
- kaola-workflow/archive/issue-74/evidence/post-stop-new-host/16-stopped-new-host-boundary.txt
- kaola-workflow/archive/issue-74/evidence/post-stop-new-host/20-first-host.json
- kaola-workflow/archive/issue-74/evidence/post-stop-new-host/21-first-stop.json
- kaola-workflow/archive/issue-74/evidence/post-stop-new-host/22-status-after-stop.json
- kaola-workflow/archive/issue-74/evidence/post-stop-new-host/23-second-host.json
- kaola-workflow/archive/issue-74/evidence/post-stop-new-host/23b-identity-delta.json
- kaola-workflow/archive/issue-74/evidence/post-stop-new-host/24-second-status.json
- kaola-workflow/archive/issue-74/evidence/post-stop-new-host/25-orchestrator-names.json
- kaola-workflow/archive/issue-74/evidence/post-stop-new-host/26-new-host-handoff.json
- kaola-workflow/archive/issue-74/evidence/post-stop-new-host/27-missing-auth-untested.json
- kaola-workflow/archive/issue-74/evidence/shas.txt
- kaola-workflow/archive/issue-74/evidence/validate-02f37b0/meta.txt
- kaola-workflow/archive/issue-74/evidence/validate-02f37b0/overall.txt
- kaola-workflow/archive/issue-74/evidence/validate-0b49e6a/SUMMARY.txt
- kaola-workflow/archive/issue-74/evidence/validate-0b49e6a/exit.txt
- kaola-workflow/archive/issue-74/evidence/validate-0b49e6a/failed-lines.txt
- kaola-workflow/archive/issue-74/evidence/validate-0b49e6a/meta.txt
- kaola-workflow/archive/issue-74/evidence/validate-0b49e6a/rerun-exit.txt
- kaola-workflow/archive/issue-74/evidence/validate-0b49e6a/rerun-failed-lines.txt
- kaola-workflow/archive/issue-74/evidence/validate-0b49e6a/rerun-highlights.txt
- kaola-workflow/archive/issue-74/evidence/validate-0b49e6a/rerun-meta.txt
- kaola-workflow/archive/issue-74/evidence/validate-holder-fix/SUMMARY.txt
- kaola-workflow/archive/issue-74/evidence/validate-holder-fix/candidate-stat.txt
- kaola-workflow/archive/issue-74/evidence/validate-holder-fix/candidate.diff
- kaola-workflow/archive/issue-74/evidence/validate-holder-fix/commits-oneline.txt
- kaola-workflow/archive/issue-74/evidence/validate-holder-fix/exit.txt
- kaola-workflow/archive/issue-74/evidence/validate-holder-fix/git-diff-check.txt
- kaola-workflow/archive/issue-74/evidence/validate-holder-fix/meta-pre.txt
- kaola-workflow/archive/issue-74/evidence/validate-holder-fix/meta.txt
- kaola-workflow/archive/issue-74/evidence/validate-quota-figures/SUMMARY.txt
- kaola-workflow/archive/issue-74/evidence/validate-quota-figures/candidate-stat.txt
- kaola-workflow/archive/issue-74/evidence/validate-quota-figures/candidate.diff
- kaola-workflow/archive/issue-74/evidence/validate-quota-figures/commits-oneline.txt
- kaola-workflow/archive/issue-74/evidence/validate-quota-figures/exit.txt
- kaola-workflow/archive/issue-74/evidence/validate-quota-figures/git-diff-check.txt
- kaola-workflow/archive/issue-74/evidence/validate-quota-figures/meta.txt
- kaola-workflow/archive/issue-74/evidence/validate-rebase-88042cd/SUMMARY.txt
- kaola-workflow/archive/issue-74/evidence/validate-rebase-88042cd/candidate-stat.txt
- kaola-workflow/archive/issue-74/evidence/validate-rebase-88042cd/candidate.diff
- kaola-workflow/archive/issue-74/evidence/validate-rebase-88042cd/commits-oneline.txt
- kaola-workflow/archive/issue-74/evidence/validate-rebase-88042cd/exit.txt
- kaola-workflow/archive/issue-74/evidence/validate-rebase-88042cd/git-diff-check.txt
- kaola-workflow/archive/issue-74/evidence/validate-rebase-88042cd/meta.txt
- kaola-workflow/archive/issue-74/evidence/validate-rebase-94d6792/SUMMARY.txt
- kaola-workflow/archive/issue-74/evidence/validate-rebase-94d6792/candidate-stat.txt
- kaola-workflow/archive/issue-74/evidence/validate-rebase-94d6792/candidate.diff
- kaola-workflow/archive/issue-74/evidence/validate-rebase-94d6792/commits-oneline.txt
- kaola-workflow/archive/issue-74/evidence/validate-rebase-94d6792/exit.txt
- kaola-workflow/archive/issue-74/evidence/validate-rebase-94d6792/git-diff-check.txt
- kaola-workflow/archive/issue-74/evidence/validate-rebase-94d6792/meta.txt
- kaola-workflow/archive/issue-74/evidence/validate-resume-wording/SUMMARY.txt
- kaola-workflow/archive/issue-74/evidence/validate-resume-wording/candidate-stat.txt
- kaola-workflow/archive/issue-74/evidence/validate-resume-wording/candidate.diff
- kaola-workflow/archive/issue-74/evidence/validate-resume-wording/commits-oneline.txt
- kaola-workflow/archive/issue-74/evidence/validate-resume-wording/exit.txt
- kaola-workflow/archive/issue-74/evidence/validate-resume-wording/git-diff-check.txt
- kaola-workflow/archive/issue-74/evidence/validate-resume-wording/meta.txt
- kaola-workflow/archive/issue-74/finalization-summary.md
- kaola-workflow/archive/issue-74/mission-list.md
- kaola-workflow/archive/issue-74/workflow-state.md
