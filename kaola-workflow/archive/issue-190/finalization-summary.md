# Finalization Summary — issue-190

## Delivered
Issue #190 (concise worker profiles and user-authorized adaptive model selection per seat), accepted by Host on code candidate 2795c27dcaac2f3ec7e8112a77a7221895b418c8 (main base 4e7a958 after #191 sink; diff sha256 4a5935f3dc78a3c82161f9276f42b3f6f339321bb02418f409adfb0a641a6265) plus Host-accepted doc-only f442ae2a8c190f16cc98cefc6f985b525f90599b (docs/api.md +7/-5, diff sha256 5cd8ee21dede9775d639a2263d1601cff7a14e9f42f6b636b6ae1293e7c6dbd6).
- Single source: every platforms/*.yaml preset carries `default_model_profile` / `<w>_model_profile` (render-skills.py REQUIRED + TIER_FIELDS; may be empty; `|` rejected). render-skills.py renders one 20-row table (Runtime, --tier, Model, Parameters, Profile) into skills/kaola-project-runner/references/worker-profiles.md with the seat-binding rule; the orchestrator Other-tiers row, Kaola-Delegator host-platforms.md (reads it from the Project Runner checkout; relays an explicit per-seat grant in the handoff's project_context=), and README reference it.
- Seat rule: seats stay bound; general dispatch authorization is not a switch grant; only an explicit user grant for a particular seat lets the Host select/switch that seat's model/preset within the same agent runtime, at idle via the existing `drain-restart --resume ID`/`--continue` with explicit --tier/--model (no hot switch; a new seat is not a switch); Fable/Fable Fusion/Astra permission limits kept. No registry, router, scoring, state machine, or new flow.
- Owner corrections consumed: final 20 profiles per the forge table (Claude Code default Opus: all-round, especially strong at complex work, preferred for harder tasks, no default-effort clause, Parameters column effort=high; Cursor/Droid opus and Devin opus-fusion share the all-round text; GPT-6 Sol includes computer use; Sonnet/Luna state default effort max; OpenCode blank). Cursor opus `claude-opus-5-5-medium` (acp_model_map onto claude-opus-5-5, effort via option; -high id still mapped), Droid opus reasoning_effort medium, Devin opus-fusion `fusion-claude-opus-5-5-medium-sidekick-swe-2-medium`. Explicit --model/--effort precedence unchanged.

Issue statement walk:
- single source per runtime and tier, OpenCode empty → manifests + render; rendered table 20 rows; render --check.
- reachable by Host/Delegator/README via existing references → SKILL Other-tiers row, host-platforms.md, README section.
- per-seat same-runtime switch semantics, general authorization excluded, no new mechanism → worker-profiles.md seat section; reviewed by Host.
- three Opus presets at medium with native mapping; defaults and other parameters unchanged → manifests/adapters; test-issue-111 and test-acp-contract Cursor opus expectations; README table.
- existing generation/consistency checks only → render-skills.py --check, existing tests; no benchmark or new framework.

## Files Changed
platforms/*.yaml (10), scripts/adapters/{cursor-cli,devin,droid}.sh, scripts/render-skills.py, templates/orchestrator/SKILL.md.tmpl, templates/orchestrator/references/worker-profiles.md.tmpl (new), templates/kaola-delegator/references/host-platforms.md.tmpl, generated skills/ outputs, README.md, CHANGELOG.md, docs/api.md, tests/contract/{test-issue-111-model-tiers,test-acp-contract,test-generated-skills}.py.

## Test Coverage
Existing tests updated only where they pin changed preset values: test-issue-111 (Droid opus medium; Devin opus-fusion name/id/command), test-acp-contract (Cursor opus medium requested id/effort), test-generated-skills (leakage masks for new ids). No new tests.

Acceptance legs:
- automated, code candidate 2795c27: `./scripts/validate.sh` rc=0, foreground on clean tree, 11:47:57–11:57:43 (log /tmp/kpr-190-validate-final2.log, sha256 2d96b737919a87a6ff13e1d3be01dc02109884f2492ab3266b6ca7b8fa246af1); Grok Bot verify PASS; sweep residual_pids [], pgid_identity_unverified []. Named prerequisite skips only: bash 3.2.57 < 4 watchdog (80 unwatched-suite notices; 2 TestValidateWatchdog rows skipped, #151). Earlier background runs (b92a8bflp pre-freeze rc 0; bemc6ghvo, b4fz1sf13 stopped; bjavekk43 harness-killed at session end, Terminated: 15) are superseded and not counted.
- automated, doc-only f442ae2 (Host-ruled diff-scoped sufficiency): `./scripts/render-skills.py --check` PASS; test-issue-147-installed-survey (10), test-issue-168-drift-enumeration (5), test-issue-52-workflow-worktree (9), test-issue-88-permission-defaults (42) OK; no new processes.
- review: independent code-reviewer pass on 3004780 (5 low findings applied); Host reviews of each freeze; Host acceptance of 2795c27 and f442ae2 on 2026-09-27.
- unexecuted: live ACP smoke per platform; no model/capability probes (issue scope). Devin `fusion-claude-opus-5-5-medium-sidekick-swe-2-medium` is not yet spawn-measured (recorded in devin acp_quirks); Cursor opus medium relies on the measured #143 base-id + effort-option route.
- residue: my stopped run's holder pid 46719 (record-proven, holder_instance_id 518e95f2…) was exact-stopped without --force (residual_pids []), its /tmp/kaola-val.5U5QEw removed; /tmp/kaola-validate-home.ChX9kr (11:05, ownership unprovable between #190/#191) left in place.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- README.md
- docs/api.md
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
- scripts/adapters/cursor-cli.sh
- scripts/adapters/devin.sh
- scripts/adapters/droid.sh
- scripts/render-skills.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/platform.yaml
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/platform.yaml
- skills/cursor-cli-kaola-project-runner/SKILL.md
- skills/cursor-cli-kaola-project-runner/references/platform.md
- skills/cursor-cli-kaola-project-runner/scripts/adapters/cursor-cli.sh
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/platform.yaml
- skills/devin-kaola-project-runner/SKILL.md
- skills/devin-kaola-project-runner/references/acp.md
- skills/devin-kaola-project-runner/references/platform.md
- skills/devin-kaola-project-runner/scripts/adapters/devin.sh
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/platform.yaml
- skills/droid-kaola-project-runner/SKILL.md
- skills/droid-kaola-project-runner/references/platform.md
- skills/droid-kaola-project-runner/scripts/adapters/droid.sh
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/platform.yaml
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/platform.yaml
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/platform.yaml
- skills/kaola-delegator/references/host-platforms.md
- skills/kaola-project-runner/SKILL.md
- skills/kaola-project-runner/references/worker-profiles.md
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/kimi-cli-kaola-project-runner/scripts/platform.yaml
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/platform.yaml
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/platform.yaml
- templates/kaola-delegator/references/host-platforms.md.tmpl
- templates/orchestrator/SKILL.md.tmpl
- templates/orchestrator/references/worker-profiles.md.tmpl
- tests/contract/test-acp-contract.py
- tests/contract/test-generated-skills.py
- tests/contract/test-issue-111-model-tiers.py

## Documentation Docking
DOCKED — see .cache/doc-docking.md (README table/profile reference, CHANGELOG two #190 Unreleased bullets, docs/api.md profile keys and Droid medium; architecture/AGENTS no impact).

## Follow-Up Items
None filed. Not a defect: the Devin medium fusion id awaits its first live spawn as ordinary evidence (no gate); a release assessment should note platforms/ and scripts/adapters/ changed (operator-diff).

## Readiness
Ready: Host-accepted code candidate 2795c27 + doc-only f442ae2, validation recorded pass, docs DOCKED. No release in this run, so no Seats line is issued here; the docs/conventions.md operator test is non-empty for this change (platforms/*.yaml and scripts/adapters/{cursor-cli,devin,droid}.sh; holder, ZCode bridge and kaola-quota.py unchanged), and the next release section must state its Seats line from that test.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-190/.cache/doc-docking.md
- kaola-workflow/archive/issue-190/.cache/final-validation.md
- kaola-workflow/archive/issue-190/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-190/finalization-summary.md
- kaola-workflow/archive/issue-190/mission-ledger.jsonl
- kaola-workflow/archive/issue-190/workflow-state.md
