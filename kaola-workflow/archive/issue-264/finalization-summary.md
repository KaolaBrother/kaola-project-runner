# Finalization summary — issue 264

## Delivered

Final release candidate `e1ff6d486c16d89c65473ac19ff316811abad3ac` on `workflow/issue-264`: the
complete integrated close of this cycle's claimed runs plus issue 259's already-archived run —
post-compaction installed-Skill reread and task recovery across runtimes (the original 264 scope),
noninterrupting steer adaptations (263), bounded `--suite` selection and scoped-validation policy
(265), the outside-caller launchd holder launcher for Grok Bot (266), the tool-kept rejection count
with pending-binding duty (267), and four-fact selection continuity against silent model/effort
drift (268). Branches `workflow/issue-259/263/265/266/267/268` are all ancestors of this candidate;
267 and 268 delivered their product changes through this tree with no commits of their own.

Acceptance on the exact candidate: full inventory `./scripts/validate.sh` EXIT=0 (v8 receipt
`/tmp/kpr-final-inventory-v8.log`, 84 suites, zero failures), root/dot final technical PASS on the
integrated delta, and Fable's same-SHA final personal PASS
(`/tmp/kpr-i264-final-fable-VERDICT-20261007.md`). Intermediate receipts preserved:
v5 `d4de8685` EXIT=0, v6 `ff5a5383` EXIT=0, v7 `7ddfe5d5` EXIT=1 (real D3/D4 regressions, fixed in
`a629c862`). The owner's lifecycle completion report
`docs/lifecycle-completion-report-2026-10-06.md` answers the seven #255 requirements against this
candidate. Renewed verification (mission 6, three diagnostic lanes:
`/tmp/kpr-i264-host-chain-1035/{core,hooks,edge}/delivery.md`) concluded and was reviewed;
publication was then directly authorized by the owner on 2026-10-07, superseding the earlier
publication hold recorded in the history note below.

The original compact-behavior scope was accepted earlier at product `291b33b5` with ancestry
integration `4b247a2d`; those receipts and the ten native token/end/exact-stop proofs remain in
`../issue-259/evidence/artifact-bindings.json` after archive.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- AGENTS.md
- CHANGELOG.md
- README.md
- docs/api.md
- docs/conventions.md
- docs/dispatch-collect.md
- docs/evidence/broker-env-allowlist-agent-snapshot-20261006.txt
- docs/evidence/host-compaction/checkpoint-20261006-causal-correction.md
- docs/evidence/host-compaction/checkpoint-20261006-original-entry-verification.json
- docs/evidence/host-compaction/core-20261006-codex-r3-fixture-AGENTS.md
- docs/evidence/host-compaction/core-20261006-codex-r3-host-events.jsonl
- docs/evidence/host-compaction/core-20261006-codex-r3-node-events.jsonl
- docs/evidence/host-compaction/core-20261006-codex-r3-progress.md
- docs/evidence/host-compaction/core-20261006-codex-r3-receipt.json
- docs/evidence/host-compaction/core-20261006-grok-r3-fixture-AGENTS.md
- docs/evidence/host-compaction/core-20261006-grok-r3-host-events.jsonl
- docs/evidence/host-compaction/core-20261006-grok-r3-node-events.jsonl
- docs/evidence/host-compaction/core-20261006-grok-r3-progress.md
- docs/evidence/host-compaction/core-20261006-grok-r3-receipt.json
- docs/evidence/host-compaction/core-20261006-opencode-r3-fixture-AGENTS.md
- docs/evidence/host-compaction/core-20261006-opencode-r3-host-events.jsonl
- docs/evidence/host-compaction/core-20261006-opencode-r3-node-events.jsonl
- docs/evidence/host-compaction/core-20261006-opencode-r3-progress.md
- docs/evidence/host-compaction/core-20261006-opencode-r3-receipt.json
- docs/evidence/host-compaction/core-20261006-opencode-r4-host-events.jsonl
- docs/evidence/host-compaction/core-20261006-opencode-r4-node-events.jsonl
- docs/evidence/host-compaction/core-20261006-opencode-r4-receipt.json
- docs/evidence/host-compaction/core-20261006-r1-continuation-send.json
- docs/evidence/host-compaction/core-20261006-r1-delivery.md
- docs/evidence/host-compaction/core-20261006-r1-host-review.md
- docs/evidence/host-compaction/core-20261006-r1-host-verification.json
- docs/evidence/host-compaction/core-20261006-r2-delivery.md
- docs/evidence/host-compaction/core-20261006-r2-host-review.md
- docs/evidence/host-compaction/core-20261006-r2-host-verification.json
- docs/evidence/host-compaction/core-20261006-r3-delivery.md
- docs/evidence/host-compaction/core-20261006-r3-generation-final-check.txt
- docs/evidence/host-compaction/core-20261006-r3-home-isolation-validation-final.txt
- docs/evidence/host-compaction/core-20261006-r3-host-review.md
- docs/evidence/host-compaction/core-20261006-r3-host-verification.json
- docs/evidence/host-compaction/core-20261006-r3-native-config-footprint.json
- docs/evidence/host-compaction/core-20261006-r4-delivery.md
- docs/evidence/host-compaction/core-20261006-r4-host-review.md
- docs/evidence/host-compaction/core-20261006-r4-host-verification.json
- docs/evidence/host-compaction/core-20261006-r4-selected-env-originals.json
- docs/evidence/host-compaction/core-20261006-repair-affected-node-checks-short-tmp.txt
- docs/evidence/host-compaction/core-20261006-repair-affected-validation-supported-bash.txt
- docs/evidence/host-compaction/core-20261006-repair-affected-validation.txt
- docs/evidence/host-compaction/core-20261006-repair-baseline-failing-checks-corrected.txt
- docs/evidence/host-compaction/core-20261006-repair-final-generation-check.txt
- docs/evidence/host-compaction/core-20261006-repair-notice-corrected-validation.txt
- docs/evidence/host-compaction/core-20261006-repair-targeted-check-summary-corrected.json
- docs/evidence/host-compaction/core-20261006-worker-exact-stop.json
- docs/evidence/host-compaction/core-codex-20261006-r1-host-events.jsonl
- docs/evidence/host-compaction/core-codex-20261006-r1-node-events.jsonl
- docs/evidence/host-compaction/core-codex-20261006-r1-receipt.json
- docs/evidence/host-compaction/core-codex-20261006-r1-start.json
- docs/evidence/host-compaction/core-codex-20261006-r1-stop.json
- docs/evidence/host-compaction/core-codex-20261006-r2-probe-01-initialize.json
- docs/evidence/host-compaction/core-codex-20261006-r2-probe-02-hooks-list-untrusted.json
- docs/evidence/host-compaction/core-codex-20261006-r2-probe-03-hooks-list-trusted.json
- docs/evidence/host-compaction/core-codex-20261006-r2-probe-04-thread-start.json
- docs/evidence/host-compaction/core-codex-20261006-r2-probe-05-compact-start.json
- docs/evidence/host-compaction/core-codex-20261006-r2-probe-06-compact-notifications.json
- docs/evidence/host-compaction/core-codex-20261006-r2-probe-07-hook-notifications.json
- docs/evidence/host-compaction/core-codex-20261006-r2-probe-08-turn-start.json
- docs/evidence/host-compaction/core-codex-20261006-r2-probe-09-turn-notifications.json
- docs/evidence/host-compaction/core-codex-20261006-r2-probe-10-items.json
- docs/evidence/host-compaction/core-codex-20261006-r2-tui-postcompact-fired.json
- docs/evidence/host-compaction/core-codex-20261006-r2-tui-sessionstart-fired.json
- docs/evidence/host-compaction/core-grok-20261006-r1-host-events.jsonl
- docs/evidence/host-compaction/core-grok-20261006-r1-node-events.jsonl
- docs/evidence/host-compaction/core-grok-20261006-r1-receipt.json
- docs/evidence/host-compaction/core-grok-20261006-r1-start.json
- docs/evidence/host-compaction/core-grok-20261006-r1-stop.json
- docs/evidence/host-compaction/core-opencode-20261006-r1-host-events.jsonl
- docs/evidence/host-compaction/core-opencode-20261006-r1-node-events.jsonl
- docs/evidence/host-compaction/core-opencode-20261006-r1-receipt.json
- docs/evidence/host-compaction/core-opencode-20261006-r1-start.json
- docs/evidence/host-compaction/core-opencode-20261006-r1-stop.json
- docs/evidence/host-compaction/core-opencode-20261006-r2-fixture-AGENTS.md
- docs/evidence/host-compaction/core-opencode-20261006-r2-host-events.jsonl
- docs/evidence/host-compaction/core-opencode-20261006-r2-host-stop.json
- docs/evidence/host-compaction/core-opencode-20261006-r2-node-events.jsonl
- docs/evidence/host-compaction/core-opencode-20261006-r2-receipt.json
- docs/evidence/host-compaction/cursor-20261006-host-attempt-events.jsonl
- docs/evidence/host-compaction/cursor-20261006-old-elite-unprompted-events.jsonl
- docs/evidence/host-compaction/droid-20261006-host-attempt-events.jsonl
- docs/evidence/host-compaction/droid-20261006-nested-limit-host-events.jsonl
- docs/evidence/host-compaction/droid-20261006-nested-limit-manifest.yaml
- docs/evidence/host-compaction/droid-20261006-nested-limit-settings.json
- docs/evidence/host-compaction/droid-20261006-original-attempt-manifest.yaml
- docs/evidence/host-compaction/droid-20261006-original-settings.json
- docs/evidence/host-compaction/droid-20261006-probe-manifest.yaml
- docs/evidence/host-compaction/droid-20261006-probe-settings.json
- docs/evidence/host-compaction/droid-20261006-prototype-pins.json
- docs/evidence/host-compaction/dsh-20261006-partial-host-events.jsonl
- docs/evidence/host-compaction/dsh-20261006-partial-host-verification.json
- docs/evidence/host-compaction/dsh-20261006-partial-node-events.jsonl
- docs/evidence/host-compaction/dsh-20261006-partial-receipt.json
- docs/evidence/host-compaction/dsh-20261006-positive-host-events.jsonl
- docs/evidence/host-compaction/dsh-20261006-positive-node-events.jsonl
- docs/evidence/host-compaction/dsh-20261006-positive-receipt.json
- docs/evidence/host-compaction/dsh-20261006-positive-scoped-checkpoint.json
- docs/evidence/host-compaction/edge-20261006-r1-continuation-send.json
- docs/evidence/host-compaction/edge-20261006-r1-correction-steer.json
- docs/evidence/host-compaction/edge-20261006-r1-delivery.md
- docs/evidence/host-compaction/edge-20261006-r1-host-review.md
- docs/evidence/host-compaction/edge-20261006-r1-host-verification.json
- docs/evidence/host-compaction/edge-20261006-r2-delivery.md
- docs/evidence/host-compaction/edge-20261006-r2-host-review.md
- docs/evidence/host-compaction/edge-20261006-r2-host-verification.json
- docs/evidence/host-compaction/edge-20261006-r3-delivery.md
- docs/evidence/host-compaction/edge-20261006-r3-devin3-chain-summary.json
- docs/evidence/host-compaction/edge-20261006-r3-kimi3-chain-summary.json
- docs/evidence/host-compaction/edge-20261006-r3-pins.txt
- docs/evidence/host-compaction/edge-devin-20261006-r1-host-events.jsonl
- docs/evidence/host-compaction/edge-devin-20261006-r1-node-events.jsonl
- docs/evidence/host-compaction/edge-devin-20261006-r1-scoped-checkpoint.json
- docs/evidence/host-compaction/edge-devin-20261006-r1-start.json
- docs/evidence/host-compaction/edge-devin-20261006-r1-stop.json
- docs/evidence/host-compaction/edge-devin-20261006-r1-worker-summary.json
- docs/evidence/host-compaction/edge-devin-20261006-r2-chain3-summary.json
- docs/evidence/host-compaction/edge-devin-20261006-r2-host-events.jsonl
- docs/evidence/host-compaction/edge-devin-20261006-r2-host-start.json
- docs/evidence/host-compaction/edge-devin-20261006-r2-host-stop.json
- docs/evidence/host-compaction/edge-devin-20261006-r2-manual-node-originals.json
- docs/evidence/host-compaction/edge-devin-20261006-r2-node-events.jsonl
- docs/evidence/host-compaction/edge-devin-20261006-r2-scoped-state.json
- docs/evidence/host-compaction/edge-kimi-20261006-r1-host-events.jsonl
- docs/evidence/host-compaction/edge-kimi-20261006-r1-node-events.jsonl
- docs/evidence/host-compaction/edge-kimi-20261006-r1-scoped-checkpoint.json
- docs/evidence/host-compaction/edge-kimi-20261006-r1-start.json
- docs/evidence/host-compaction/edge-kimi-20261006-r1-stop.json
- docs/evidence/host-compaction/edge-kimi-20261006-r1-worker-summary.json
- docs/evidence/host-compaction/edge-kimi-20261006-r2-chain3-summary.json
- docs/evidence/host-compaction/edge-kimi-20261006-r2-host-events.jsonl
- docs/evidence/host-compaction/edge-kimi-20261006-r2-host-start.json
- docs/evidence/host-compaction/edge-kimi-20261006-r2-host-stop.json
- docs/evidence/host-compaction/edge-kimi-20261006-r2-node-events.jsonl
- docs/evidence/host-compaction/edge-kimi-20261006-r2-scoped-state.json
- docs/evidence/host-compaction/edge-kimi-20261006-refused-recipe/host-start.json
- docs/evidence/host-compaction/edge-kimi-20261006-refused-recipe/records/kimi-cli/kimi-cli-KPR103EK-orchestrator-main/ec0c2da05cfe642c/events.jsonl
- docs/evidence/host-compaction/edge-kimi-20261006-refused-recipe/records/kimi-cli/kimi-cli-KPR103EK-orchestrator-main/ec0c2da05cfe642c/record.json
- docs/evidence/host-compaction/edge-zcode-20261006-r1-host-events.jsonl
- docs/evidence/host-compaction/edge-zcode-20261006-r1-host-send-compact.json
- docs/evidence/host-compaction/edge-zcode-20261006-r1-host-send-compact2.json
- docs/evidence/host-compaction/edge-zcode-20261006-r1-host-start-sideagent-chain3.json
- docs/evidence/host-compaction/edge-zcode-20261006-r1-host-start-sideagent-recovery.json
- docs/evidence/host-compaction/edge-zcode-20261006-r1-host-stop-sideagent.json
- docs/evidence/host-compaction/edge-zcode-20261006-r1-node-events.jsonl
- docs/evidence/host-compaction/edge-zcode-20261006-r1-scoped-checkpoint.json
- docs/evidence/host-compaction/edge-zcode-20261006-r1-start.json
- docs/evidence/host-compaction/edge-zcode-20261006-r1-state-reactivate.json
- docs/evidence/host-compaction/edge-zcode-20261006-r1-stop.json
- docs/evidence/host-compaction/edge-zcode-20261006-r1-worker-summary.json
- docs/evidence/host-compaction/hooks-20261006-primary-source-verification.json
- docs/evidence/host-compaction/hooks-20261006-prototype-argv-verification.json
- docs/evidence/host-compaction/hooks-20261006-r2-delivery.md
- docs/evidence/host-compaction/hooks-20261006-r2-host-review.md
- docs/evidence/host-compaction/hooks-20261006-r2-host-verification.json
- docs/evidence/host-compaction/hooks-20261006-r3-delivery.md
- docs/evidence/host-compaction/hooks-20261006-r3-host-review.md
- docs/evidence/host-compaction/hooks-20261006-r3-host-verification.json
- docs/evidence/host-compaction/hooks-20261006-worker-exact-stop.json
- docs/evidence/host-compaction/kpr-heartbeat652-kimi-host-verification.json
- docs/evidence/host-compaction/kpr-heartbeat673-zcode-host-verification.json
- docs/evidence/host-compaction/kpr-heartbeat723-cursor-host-verification.json
- docs/evidence/host-compaction/kpr-heartbeat737-droid-host-verification.json
- docs/evidence/host-compaction/kpr-i264-926-dsh-host-verification.json
- docs/evidence/host-compaction/kpr-i264-929-host-proof-verification.json
- docs/evidence/steer-20261005-all-runtime-delivery.md
- docs/host-compact-capabilities.md
- docs/lifecycle-completion-report-2026-10-06.md
- docs/zcode-host.md
- platforms/codex.yaml
- platforms/cursor-cli.yaml
- platforms/devin.yaml
- platforms/droid.yaml
- platforms/dsh.yaml
- platforms/grok.yaml
- platforms/kimi-cli.yaml
- platforms/opencode.yaml
- scripts/kaola-acp-holder.py
- scripts/kaola-acp.py
- scripts/kaola-compact-recovery.py
- scripts/kaola-dispatch.py
- scripts/kaola-dsh-acp.py
- scripts/kaola-dsh-steer.mjs
- scripts/kaola-launchd-broker.py
- scripts/kaola-opencode-acp.py
- scripts/kaola-opencode-steer.mjs
- scripts/kaola-project-compact-notice.py
- scripts/kaola-record-contract.py
- scripts/kaola-tmux.sh
- scripts/kaola-zcode-acp.py
- scripts/render-skills.py
- scripts/validate-watchdog.sh
- scripts/validate.sh
- skills/claude-code-kaola-project-runner/SKILL.md
- skills/claude-code-kaola-project-runner/references/acp.md
- skills/claude-code-kaola-project-runner/references/steering.md
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-compact-recovery.py
- skills/claude-code-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/claude-code-kaola-project-runner/scripts/kaola-project-compact-notice.py
- skills/claude-code-kaola-project-runner/scripts/kaola-record-contract.py
- skills/claude-code-kaola-project-runner/scripts/kaola-tmux.sh
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/vendor/claude-code-acp/dist/DERIVATION.json
- skills/claude-code-kaola-project-runner/scripts/vendor/claude-code-acp/dist/index.js
- skills/codex-kaola-project-runner/SKILL.md
- skills/codex-kaola-project-runner/references/acp.md
- skills/codex-kaola-project-runner/references/steering.md
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-compact-recovery.py
- skills/codex-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/codex-kaola-project-runner/scripts/kaola-project-compact-notice.py
- skills/codex-kaola-project-runner/scripts/kaola-record-contract.py
- skills/codex-kaola-project-runner/scripts/kaola-tmux.sh
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/platform.yaml
- skills/cursor-cli-kaola-project-runner/SKILL.md
- skills/cursor-cli-kaola-project-runner/references/acp.md
- skills/cursor-cli-kaola-project-runner/references/steering.md
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-compact-recovery.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-project-compact-notice.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-record-contract.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-tmux.sh
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/platform.yaml
- skills/devin-kaola-project-runner/SKILL.md
- skills/devin-kaola-project-runner/references/acp.md
- skills/devin-kaola-project-runner/references/steering.md
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-compact-recovery.py
- skills/devin-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/devin-kaola-project-runner/scripts/kaola-project-compact-notice.py
- skills/devin-kaola-project-runner/scripts/kaola-record-contract.py
- skills/devin-kaola-project-runner/scripts/kaola-tmux.sh
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/platform.yaml
- skills/droid-kaola-project-runner/SKILL.md
- skills/droid-kaola-project-runner/references/acp.md
- skills/droid-kaola-project-runner/references/steering.md
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-compact-recovery.py
- skills/droid-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/droid-kaola-project-runner/scripts/kaola-project-compact-notice.py
- skills/droid-kaola-project-runner/scripts/kaola-record-contract.py
- skills/droid-kaola-project-runner/scripts/kaola-tmux.sh
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/platform.yaml
- skills/dsh-kaola-project-runner/SKILL.md
- skills/dsh-kaola-project-runner/references/acp.md
- skills/dsh-kaola-project-runner/references/platform.md
- skills/dsh-kaola-project-runner/references/steering.md
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-compact-recovery.py
- skills/dsh-kaola-project-runner/scripts/kaola-dsh-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-dsh-steer.mjs
- skills/dsh-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/dsh-kaola-project-runner/scripts/kaola-opencode-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-project-compact-notice.py
- skills/dsh-kaola-project-runner/scripts/kaola-record-contract.py
- skills/dsh-kaola-project-runner/scripts/kaola-tmux.sh
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/platform.yaml
- skills/grok-kaola-project-runner/SKILL.md
- skills/grok-kaola-project-runner/references/acp.md
- skills/grok-kaola-project-runner/references/steering.md
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-compact-recovery.py
- skills/grok-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/grok-kaola-project-runner/scripts/kaola-project-compact-notice.py
- skills/grok-kaola-project-runner/scripts/kaola-record-contract.py
- skills/grok-kaola-project-runner/scripts/kaola-tmux.sh
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/platform.yaml
- skills/kaola-delegator/references/handoff.md
- skills/kaola-delegator/references/host-brick.md
- skills/kaola-delegator/references/host-platforms.md
- skills/kaola-delegator/references/inquiry-report.md
- skills/kaola-delegator/references/snapshot.md
- skills/kaola-project-runner/SKILL.md
- skills/kaola-project-runner/references/dispatch-collect.md
- skills/kaola-project-runner/references/duty-reconcile.md
- skills/kaola-project-runner/references/heartbeat-skeleton.md
- skills/kaola-project-runner/references/host-entry-matrix.md
- skills/kaola-project-runner/references/lifecycle-state.md
- skills/kaola-project-runner/references/qa-evidence.md
- skills/kaola-project-runner/references/quota-packages.md
- skills/kaola-project-runner/references/sideagent-node.md
- skills/kaola-project-runner/references/task-failure.md
- skills/kaola-project-runner/references/worker-profiles.md
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kaola-project-runner/scripts/kaola-record-contract.py
- skills/kimi-cli-kaola-project-runner/SKILL.md
- skills/kimi-cli-kaola-project-runner/references/acp.md
- skills/kimi-cli-kaola-project-runner/references/steering.md
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-compact-recovery.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-project-compact-notice.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-record-contract.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-tmux.sh
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/kimi-cli-kaola-project-runner/scripts/platform.yaml
- skills/opencode-kaola-project-runner/SKILL.md
- skills/opencode-kaola-project-runner/references/acp.md
- skills/opencode-kaola-project-runner/references/steering.md
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-compact-recovery.py
- skills/opencode-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/opencode-kaola-project-runner/scripts/kaola-opencode-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-opencode-steer.mjs
- skills/opencode-kaola-project-runner/scripts/kaola-project-compact-notice.py
- skills/opencode-kaola-project-runner/scripts/kaola-record-contract.py
- skills/opencode-kaola-project-runner/scripts/kaola-tmux.sh
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/platform.yaml
- skills/zcode-kaola-project-runner/SKILL.md
- skills/zcode-kaola-project-runner/references/acp.md
- skills/zcode-kaola-project-runner/references/steering.md
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-compact-recovery.py
- skills/zcode-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/zcode-kaola-project-runner/scripts/kaola-project-compact-notice.py
- skills/zcode-kaola-project-runner/scripts/kaola-record-contract.py
- skills/zcode-kaola-project-runner/scripts/kaola-tmux.sh
- skills/zcode-kaola-project-runner/scripts/kaola-zcode-acp.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/SKILL.md.tmpl
- templates/kaola-delegator/references/handoff.md.tmpl
- templates/kaola-delegator/references/host-brick.md
- templates/kaola-delegator/references/host-platforms.md.tmpl
- templates/kaola-delegator/references/inquiry-report.md
- templates/kaola-delegator/references/snapshot.md
- templates/orchestrator/SKILL.md.tmpl
- templates/orchestrator/references/dispatch-collect.md
- templates/orchestrator/references/duty-reconcile.md
- templates/orchestrator/references/heartbeat-skeleton.txt
- templates/orchestrator/references/host-entry-matrix.md
- templates/orchestrator/references/lifecycle-state.md
- templates/orchestrator/references/qa-evidence.md
- templates/orchestrator/references/quota-packages.md
- templates/orchestrator/references/sideagent-node.md
- templates/orchestrator/references/task-failure.md
- templates/orchestrator/references/worker-profiles.md.tmpl
- templates/references/acp.md.tmpl
- templates/references/steering.md.tmpl
- tests/contract/mock-acp-agent.py
- tests/contract/test-acp-contract.py
- tests/contract/test-acp-follow-contract.py
- tests/contract/test-acp-holder-continue.py
- tests/contract/test-acp-sweep-contract.py
- tests/contract/test-acp-watch-contract.py
- tests/contract/test-droid-acp-contract.py
- tests/contract/test-issue-101-validate-watchdog.py
- tests/contract/test-issue-118-seat-cap.py
- tests/contract/test-issue-119-host-entry.py
- tests/contract/test-issue-123-shared-refs.py
- tests/contract/test-issue-130-pty-retired.py
- tests/contract/test-issue-146-session-new-wait.py
- tests/contract/test-issue-148-quota-packages.py
- tests/contract/test-issue-162-upgrade-safety.py
- tests/contract/test-issue-164-pre-spawn-bridge-facts.py
- tests/contract/test-issue-165-path-drift.py
- tests/contract/test-issue-187-delegator-any-host.py
- tests/contract/test-issue-218-preset-ids.py
- tests/contract/test-issue-22-bypass-all-approvals.py
- tests/contract/test-issue-24-opencode-no-skip-all.py
- tests/contract/test-issue-244-dispatch.py
- tests/contract/test-issue-245-session-role.py
- tests/contract/test-issue-247-codex-child.py
- tests/contract/test-issue-254-opencode-model.py
- tests/contract/test-issue-255-lifecycle-state.py
- tests/contract/test-issue-259-record-contract.py
- tests/contract/test-issue-263-steer-adaptation.py
- tests/contract/test-issue-264-compact-recovery.py
- tests/contract/test-issue-264-validate-lane-integrity.py
- tests/contract/test-issue-266-launch-broker-composed.py
- tests/contract/test-issue-266-launch-broker.py
- tests/contract/test-issue-267-rejection-count.py
- tests/contract/test-issue-268-selection-continuity.py
- tests/contract/test-issue-33-config-meta.py
- tests/contract/test-issue-50-runner-integration.py
- tests/contract/test-issue-64-receipt-bound.py
- tests/contract/test-issue-65-host-contract.py
- tests/contract/test-issue-65-steering.py
- tests/contract/test-issue-73-canonical-root.py
- tests/contract/test-issue-74-kaola-delegator.py
- tests/contract/test-issue-76-permission-wake.py
- tests/contract/test-issue-88-permission-defaults.py
- tests/contract/test-issue-94-zcode-native-skill-entry.py
- tests/contract/test-issue-95-reader-exception.py
- tests/contract/test-issue-98-dsh-acp.py
- tests/contract/test-progressive-disclosure.py
- tests/contract/test-project-compact-notice.py
- tests/contract/test-runner-v2.py
- tests/contract/test-zcode-acp-contract.py
- tests/contract/test-zcode-heartbeat-contract.py
- tests/contract/test-zcode-host-contract.py
- vendor/claude-code-acp/UPSTREAM.md
- vendor/claude-code-acp/dist/DERIVATION.json
- vendor/claude-code-acp/dist/index.js
- vendor/claude-code-acp/src/agent.ts
- vendor/claude-code-acp/src/claude-runner.ts
- vendor/claude-code-acp/tests/kaola-compact.test.ts

## Known limitations

Automatic effort-raise reset is not implemented — no catalog field declares an effort order, and a
same-preset effort change never resets a rejection segment today; a preset change that is a real
handoff does reset with index evidence. Codex installed signal emission, independent outer inquiry,
DSH background forwarding, named Droid/Cursor compaction boundaries and long-term consumer behavior
stay unverified. Ten changed-default ACP communication outcomes do not prove all-runtime automatic
compaction, model identity, installed activation, universal recovery or zero defects. Linux and
other OSes, GUI/TCC, logout/reboot and all parent-death combinations remain unverified. Matching
reader precedes incompatible grouped-record migration; the old installed node limitation remains.
The consumer-side Studio install and VRPAI/CAD mechanism migration wait for the actual release and
owner-coordinated cross-project switching. No installation was performed by this run.

## Follow-Up Items

Issue 260 stays open under owner disposition: item6 set aside, cause/ownership unproven; KW1114
ownership unchanged. Not expanded into by this close-out. No new framework or duplicate issue for
the scoped limits above. No consumer mutation.

## Readiness

Accepted and owner-authorized for the full release close-out: this run's merge sink closes the
recorded set `issue_numbers: 259,263,264,265,266,267,268`, then normal release checks
(pin/adapter, operator diff, Seats) and the next unused stable PATCH tag follow. Kimi no-tool
token/end82 and exact-stop1035 exit0/residual[] verified; nine other native replies/stops and all
original worker stops retained.

## Superseded history note

The earlier "Latest owner264 scope — publication held" block (owner comment 6012954294: all ten
runtimes need version-bound actual Host compaction detection, full current Skill reread/use and
automatic scoped Sideagent checkpoint/reclaim; no sink/tag/PATCH until that renewed verification
concluded and was reviewed) is superseded by that verification's conclusion — mission 6 closed
done, lifecycle completion report delivered, root and Fable final PASS on the same candidate — and
the owner's direct release authorization of 2026-10-07. Kept only as the record of why publication
waited.

## Finalize Findings

### residue_unattributed

The residue mirror did not copy the paths below out of the main checkout: this run's HEAD does not contain them. Presence in main, an untracked status, or a neighboring file this run committed is not evidence they belong to this run. Nothing was copied, staged, committed, deleted, reverted or relocated — they remain in the main checkout. Read them before the sink runs: commit what belongs to the run, leave what does not.

Paths left in the main checkout:

- docs/harness-acp-codex-160-live-2026-10-03.md
- docs/harness-acp-compat-2026-10-01.md
- docs/harness-acp-compat-2026-10-03.md
- docs/harness-acp-compat-2026-10-06.md
- docs/harness-acp-reverify-2026-10-01.md

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-264/.cache/final-validation.md
- kaola-workflow/archive/issue-264/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-264/finalization-summary.md
- kaola-workflow/archive/issue-264/mission-ledger.jsonl
- kaola-workflow/archive/issue-264/workflow-state.md
