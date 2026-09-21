# Finalization summary — issue-119

## Delivered
Issue #119: non-ZCode ACP runtimes can run Project Runner as an event-driven Host.
- Measured `host_skill_entry` per platform: `/kaola-project-runner` (zcode, claude-code, cursor-cli, grok, devin, droid, dsh, opencode), `/skill:kaola-project-runner ` (kimi-cli, trailing space), codex empty.
- Holder carrier opens with the Host's entry and names `(<runtime_name> Host)`; ZCode carrier byte-identical to 5122468.
- Worker binding (#104), carrier target validation, `worker_event`, and #105 build skew follow the entry; entry-less dispatchers keep pre-#119 behavior.
- H1: Host start resolves exactly like a worker start; no new Host model constants or manifest model fields.
- H2: `effective_selection` on every ACP start; opencode explicit-selection-unverified refusal + stop.
- Installer runtimes grok-cli, droid, opencode, kimi-cli, dsh; host-entry-matrix.md reference.
- Host acceptance: PASS (Host verdict 2026-09-21, after one repair round).

## Files Changed
Commits 70d448d, 7f4b794, 2d4936c, 7183b2f on workflow/issue-119: platforms/*.yaml, scripts/kaola-acp.py, scripts/kaola-acp-holder.py, scripts/render-skills.py, scripts/install-local.sh, scripts/validate.sh, templates/orchestrator/{SKILL.md.tmpl, references/host-entry-matrix.md, references/host-startup.md.tmpl, references/heartbeat-skeleton.txt}, templates/kaola-delegator/references/handoff.md.tmpl, CHANGELOG.md, README.md, docs/api.md, tests/contract/{test-issue-119-host-entry.py (new), test-installer-runtimes.sh, test-zcode-heartbeat-contract.py, test-issue-33-config-meta.py, test-issue-90-event-confirmation-race.py, test-issue-94-zcode-native-skill-entry.py}, and rendered skills/.

## Test Coverage
- AC1/AC2/AC3/AC9/H2: tests/contract/test-issue-119-host-entry.py 8/8, 114 checks.
- AC7: tests/contract/test-installer-runtimes.sh (install + uninstall per new runtime).
- AC4/AC5/AC6 (live): evidence/kpr119-h2-*.json, evidence/m0-trigger/, evidence/d3-all/ (analysis.json, uat.json, sweep-positive-control.json, sweep-final.json).
- Codex: contract/simulation evidence only (Delegator ruling): entry-less dispatcher and carrier-op refusal tests.

## Validation
- `./scripts/render-skills.py --check && ./scripts/validate.sh` → rc=0 on 7183b2f (evidence/validate-7183b2f.log); recorded in .cache/final-validation.md, verdict pass, validated_candidate_hash 7970f62a1262….
- Earlier: rc=0 on 70d448d, 7f4b794, 2d4936c (Host re-ran rc=0 on 2d4936c).
- run-chains: chains_config_missing (consumer repo; gate is the recorded final validation).

## Changed Paths
finalize --check reported changed_paths (61, source-scoped):
- platforms/claude-code.yaml
- platforms/codex.yaml
- platforms/cursor-cli.yaml
- platforms/devin.yaml
- platforms/droid.yaml
- platforms/dsh.yaml
- platforms/grok.yaml
- platforms/kimi-cli.yaml
- platforms/opencode.yaml
- platforms/zcode.yaml
- scripts/install-local.sh
- scripts/kaola-acp-holder.py
- scripts/kaola-acp.py
- scripts/render-skills.py
- scripts/validate.sh
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/platform.yaml
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/platform.yaml
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/platform.yaml
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/platform.yaml
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/platform.yaml
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/platform.yaml
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/platform.yaml
- skills/kaola-delegator/references/handoff.md
- skills/kaola-project-runner/SKILL.md
- skills/kaola-project-runner/references/heartbeat-skeleton.md
- skills/kaola-project-runner/references/host-entry-matrix.md
- skills/kaola-project-runner/references/host-startup.md
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/platform.yaml
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/platform.yaml
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/platform.yaml
- templates/kaola-delegator/references/handoff.md.tmpl
- templates/orchestrator/SKILL.md.tmpl
- templates/orchestrator/references/heartbeat-skeleton.txt
- templates/orchestrator/references/host-entry-matrix.md
- templates/orchestrator/references/host-startup.md.tmpl
- tests/contract/test-installer-runtimes.sh
- tests/contract/test-issue-119-host-entry.py
- tests/contract/test-issue-33-config-meta.py
- tests/contract/test-issue-90-event-confirmation-race.py
- tests/contract/test-issue-94-zcode-native-skill-entry.py
- tests/contract/test-zcode-heartbeat-contract.py

Also changed, outside the transaction's source scope: CHANGELOG.md, README.md, docs/api.md.

## Documentation Docking
DOCKED — see .cache/doc-docking.md.

## Follow-Up Items
- filed: #122 (P2) Codex Host entry measurement + HUMAN_DECISION on entry-less Host behavior — confirmed OPEN, body 1468 chars.
- filed: #120 (P3) dsh worker cannot start inside a dsh Host — confirmed OPEN, body 1034 chars.
- filed: #121 (P3) stale user-root main Skill shadows the Host build; #105 does not report it — confirmed OPEN, body 1130 chars.
- Correction comment posted on #119 (issuecomment-5761002040): probe hypotheses corrected, AC4 receipts.

## Readiness
READY — Host acceptance PASS; validation pass recorded; docs docked; follow-ups filed. Close #119 via merge sink.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-119/.cache/doc-docking.md
- kaola-workflow/archive/issue-119/.cache/final-validation.md
- kaola-workflow/archive/issue-119/.cache/mirror-digest.json
- kaola-workflow/archive/issue-119/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-119/evidence/d3-all/analysis.json
- kaola-workflow/archive/issue-119/evidence/d3-all/analyze.py
- kaola-workflow/archive/issue-119/evidence/d3-all/claude-code/1-host-start.json
- kaola-workflow/archive/issue-119/evidence/d3-all/claude-code/2-handoff-send.json
- kaola-workflow/archive/issue-119/evidence/d3-all/claude-code/5-worker-status.json
- kaola-workflow/archive/issue-119/evidence/d3-all/claude-code/6-host-stop.json
- kaola-workflow/archive/issue-119/evidence/d3-all/claude-code/carrier-rebuilt.txt
- kaola-workflow/archive/issue-119/evidence/d3-all/claude-code/host-events.jsonl
- kaola-workflow/archive/issue-119/evidence/d3-all/claude-code/summary.json
- kaola-workflow/archive/issue-119/evidence/d3-all/cursor-cli/1-host-start.json
- kaola-workflow/archive/issue-119/evidence/d3-all/cursor-cli/2-handoff-send.json
- kaola-workflow/archive/issue-119/evidence/d3-all/cursor-cli/5-worker-status.json
- kaola-workflow/archive/issue-119/evidence/d3-all/cursor-cli/6-host-stop.json
- kaola-workflow/archive/issue-119/evidence/d3-all/cursor-cli/carrier-rebuilt.txt
- kaola-workflow/archive/issue-119/evidence/d3-all/cursor-cli/host-events.jsonl
- kaola-workflow/archive/issue-119/evidence/d3-all/cursor-cli/summary.json
- kaola-workflow/archive/issue-119/evidence/d3-all/d3.py
- kaola-workflow/archive/issue-119/evidence/d3-all/devin/1-host-start.json
- kaola-workflow/archive/issue-119/evidence/d3-all/devin/2-handoff-send.json
- kaola-workflow/archive/issue-119/evidence/d3-all/devin/5-worker-status.json
- kaola-workflow/archive/issue-119/evidence/d3-all/devin/6-host-stop.json
- kaola-workflow/archive/issue-119/evidence/d3-all/devin/carrier-rebuilt.txt
- kaola-workflow/archive/issue-119/evidence/d3-all/devin/host-events.jsonl
- kaola-workflow/archive/issue-119/evidence/d3-all/devin/summary.json
- kaola-workflow/archive/issue-119/evidence/d3-all/droid-attempt1-quota/1-host-start.json
- kaola-workflow/archive/issue-119/evidence/d3-all/droid-attempt1-quota/2-handoff-send.json
- kaola-workflow/archive/issue-119/evidence/d3-all/droid-attempt1-quota/host-events.jsonl
- kaola-workflow/archive/issue-119/evidence/d3-all/droid/1-host-start.json
- kaola-workflow/archive/issue-119/evidence/d3-all/droid/2-handoff-send.json
- kaola-workflow/archive/issue-119/evidence/d3-all/droid/5-worker-status.json
- kaola-workflow/archive/issue-119/evidence/d3-all/droid/6-host-stop.json
- kaola-workflow/archive/issue-119/evidence/d3-all/droid/carrier-rebuilt.txt
- kaola-workflow/archive/issue-119/evidence/d3-all/droid/host-events.jsonl
- kaola-workflow/archive/issue-119/evidence/d3-all/droid/summary.json
- kaola-workflow/archive/issue-119/evidence/d3-all/dsh-attempt1-dshworker/1-host-start.json
- kaola-workflow/archive/issue-119/evidence/d3-all/dsh-attempt1-dshworker/2-handoff-send.json
- kaola-workflow/archive/issue-119/evidence/d3-all/dsh-attempt1-dshworker/5-worker-status.json
- kaola-workflow/archive/issue-119/evidence/d3-all/dsh-attempt1-dshworker/6-host-stop.json
- kaola-workflow/archive/issue-119/evidence/d3-all/dsh-attempt1-dshworker/carrier-rebuilt.txt
- kaola-workflow/archive/issue-119/evidence/d3-all/dsh-attempt1-dshworker/host-events.jsonl
- kaola-workflow/archive/issue-119/evidence/d3-all/dsh-attempt1-dshworker/summary.json
- kaola-workflow/archive/issue-119/evidence/d3-all/dsh/1-host-start.json
- kaola-workflow/archive/issue-119/evidence/d3-all/dsh/2-handoff-send.json
- kaola-workflow/archive/issue-119/evidence/d3-all/dsh/5-worker-status.json
- kaola-workflow/archive/issue-119/evidence/d3-all/dsh/6-host-stop.json
- kaola-workflow/archive/issue-119/evidence/d3-all/dsh/carrier-rebuilt.txt
- kaola-workflow/archive/issue-119/evidence/d3-all/dsh/host-events.jsonl
- kaola-workflow/archive/issue-119/evidence/d3-all/dsh/summary.json
- kaola-workflow/archive/issue-119/evidence/d3-all/grok/1-host-start.json
- kaola-workflow/archive/issue-119/evidence/d3-all/grok/2-handoff-send.json
- kaola-workflow/archive/issue-119/evidence/d3-all/grok/5-worker-status.json
- kaola-workflow/archive/issue-119/evidence/d3-all/grok/6-host-stop.json
- kaola-workflow/archive/issue-119/evidence/d3-all/grok/carrier-rebuilt.txt
- kaola-workflow/archive/issue-119/evidence/d3-all/grok/host-events.jsonl
- kaola-workflow/archive/issue-119/evidence/d3-all/grok/summary.json
- kaola-workflow/archive/issue-119/evidence/d3-all/kimi-cli/1-host-start.json
- kaola-workflow/archive/issue-119/evidence/d3-all/kimi-cli/2-handoff-send.json
- kaola-workflow/archive/issue-119/evidence/d3-all/kimi-cli/5-worker-status.json
- kaola-workflow/archive/issue-119/evidence/d3-all/kimi-cli/6-host-stop.json
- kaola-workflow/archive/issue-119/evidence/d3-all/kimi-cli/carrier-rebuilt.txt
- kaola-workflow/archive/issue-119/evidence/d3-all/kimi-cli/host-events.jsonl
- kaola-workflow/archive/issue-119/evidence/d3-all/kimi-cli/summary.json
- kaola-workflow/archive/issue-119/evidence/d3-all/kpr119-run2.sh
- kaola-workflow/archive/issue-119/evidence/d3-all/opencode/1-host-start.json
- kaola-workflow/archive/issue-119/evidence/d3-all/opencode/2-handoff-send.json
- kaola-workflow/archive/issue-119/evidence/d3-all/opencode/5-worker-status.json
- kaola-workflow/archive/issue-119/evidence/d3-all/opencode/6-host-stop.json
- kaola-workflow/archive/issue-119/evidence/d3-all/opencode/carrier-rebuilt.txt
- kaola-workflow/archive/issue-119/evidence/d3-all/opencode/host-events.jsonl
- kaola-workflow/archive/issue-119/evidence/d3-all/opencode/summary.json
- kaola-workflow/archive/issue-119/evidence/d3-all/sweep-final.json
- kaola-workflow/archive/issue-119/evidence/d3-all/sweep-positive-control.json
- kaola-workflow/archive/issue-119/evidence/d3-all/sweep-receipt.json
- kaola-workflow/archive/issue-119/evidence/d3-all/uat.json
- kaola-workflow/archive/issue-119/evidence/d3-all/uat.py
- kaola-workflow/archive/issue-119/evidence/d3/1-host-start.json
- kaola-workflow/archive/issue-119/evidence/d3/2-handoff-send.json
- kaola-workflow/archive/issue-119/evidence/d3/3-host-capture-full.json
- kaola-workflow/archive/issue-119/evidence/d3/3-host-capture.json
- kaola-workflow/archive/issue-119/evidence/d3/4-carrier-rebuilt.txt
- kaola-workflow/archive/issue-119/evidence/d3/5-worker-status-after-stop.json
- kaola-workflow/archive/issue-119/evidence/d3/6-host-stop.json
- kaola-workflow/archive/issue-119/evidence/d3/host-events.jsonl
- kaola-workflow/archive/issue-119/evidence/kpr119-h2-default-send.json
- kaola-workflow/archive/issue-119/evidence/kpr119-h2-default-status.json
- kaola-workflow/archive/issue-119/evidence/kpr119-h2-default.json
- kaola-workflow/archive/issue-119/evidence/kpr119-h2-explicit-capture.json
- kaola-workflow/archive/issue-119/evidence/kpr119-h2-explicit-send.json
- kaola-workflow/archive/issue-119/evidence/kpr119-h2-explicit-status.json
- kaola-workflow/archive/issue-119/evidence/kpr119-h2-explicit.json
- kaola-workflow/archive/issue-119/evidence/m0-trigger/A-claude-code.json
- kaola-workflow/archive/issue-119/evidence/m0-trigger/A-codex.json
- kaola-workflow/archive/issue-119/evidence/m0-trigger/A-cursor-cli.json
- kaola-workflow/archive/issue-119/evidence/m0-trigger/A-devin.json
- kaola-workflow/archive/issue-119/evidence/m0-trigger/A-droid.json
- kaola-workflow/archive/issue-119/evidence/m0-trigger/A-dsh.json
- kaola-workflow/archive/issue-119/evidence/m0-trigger/A-grok.json
- kaola-workflow/archive/issue-119/evidence/m0-trigger/A-kimi-cli.json
- kaola-workflow/archive/issue-119/evidence/m0-trigger/A-opencode.json
- kaola-workflow/archive/issue-119/evidence/m0-trigger/B1-claude-code.json
- kaola-workflow/archive/issue-119/evidence/m0-trigger/B1-cursor-cli.json
- kaola-workflow/archive/issue-119/evidence/m0-trigger/B1-devin.json
- kaola-workflow/archive/issue-119/evidence/m0-trigger/B1-droid.json
- kaola-workflow/archive/issue-119/evidence/m0-trigger/B1-dsh.json
- kaola-workflow/archive/issue-119/evidence/m0-trigger/B1-grok.json
- kaola-workflow/archive/issue-119/evidence/m0-trigger/B1-kimi-cli.json
- kaola-workflow/archive/issue-119/evidence/m0-trigger/B1-opencode.json
- kaola-workflow/archive/issue-119/evidence/m0-trigger/B2-kimi-inline.json
- kaola-workflow/archive/issue-119/evidence/m0-trigger/B2-kimi-slash.json
- kaola-workflow/archive/issue-119/evidence/m0-trigger/B2-kimi-space.json
- kaola-workflow/archive/issue-119/evidence/m0-trigger/C-claude-code.json
- kaola-workflow/archive/issue-119/evidence/m0-trigger/C-cursor-cli.json
- kaola-workflow/archive/issue-119/evidence/m0-trigger/C-devin.json
- kaola-workflow/archive/issue-119/evidence/m0-trigger/C-droid.json
- kaola-workflow/archive/issue-119/evidence/m0-trigger/C-dsh.json
- kaola-workflow/archive/issue-119/evidence/m0-trigger/C-grok.json
- kaola-workflow/archive/issue-119/evidence/m0-trigger/C-kimi-cli.json
- kaola-workflow/archive/issue-119/evidence/m0-trigger/C-opencode.json
- kaola-workflow/archive/issue-119/evidence/m0-trigger/N-claude-code.json
- kaola-workflow/archive/issue-119/evidence/m0-trigger/N-cursor-cli.json
- kaola-workflow/archive/issue-119/evidence/m0-trigger/N-devin.json
- kaola-workflow/archive/issue-119/evidence/m0-trigger/N-droid.json
- kaola-workflow/archive/issue-119/evidence/m0-trigger/N-dsh.json
- kaola-workflow/archive/issue-119/evidence/m0-trigger/N-grok.json
- kaola-workflow/archive/issue-119/evidence/m0-trigger/N-kimi-cli.json
- kaola-workflow/archive/issue-119/evidence/m0-trigger/N-opencode.json
- kaola-workflow/archive/issue-119/evidence/m0-trigger/manifest.json
- kaola-workflow/archive/issue-119/evidence/m0-trigger/probe.py
- kaola-workflow/archive/issue-119/finalization-summary.md
- kaola-workflow/archive/issue-119/mission-list.md
- kaola-workflow/archive/issue-119/workflow-state.md
