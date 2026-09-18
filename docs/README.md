# Documentation Index

- [Architecture](architecture.md): golden contract, worker vs main Skill, generated Skills, boundaries, ownership, and canonical-root versus Workflow child worktree guidance
- [API](api.md): renderer, installer, tmux core, status, and adapter contracts
- [Grok Bot host](grok-bot-host.md): one thin bridge Skill, execution-target binding (Local Computer vs cloud), device-local locator and fail-closed attestation, one-write install, read-only Mac UAT boundary, Routine heartbeat, token-cost comparison
- [ZCode Host](zcode-host.md): ZCode as worker platform and as native skill-directory host, the
  generic ACP entry, the event-driven heartbeat carrier and its prompt-file defect receipt, and
  the two startup flows (ordinary worker supervision vs Orchestrator/Host supervision)
- [Conventions](conventions.md): change boundary, source-of-truth, safety, and validation
- [Runner v2 dual-transport design](runner-v2-dual-transport-design.md) (v0.3, implementation
  baseline): ACP transport alongside the existing pty transport, channel defaults, low-token
  receipts, PoC conclusions, and the production acceptance split (A / B / C)
- [ACP Watch Surface](acp-watch/README.md) (design freeze 2026-09-13; **#25 / #26 / #27 implemented**):
  human spectator beside the holder — [#25 permit lock](acp-watch/permit-lock.md),
  [#26 list/view schema](acp-watch/list-view.md), [#27 local follow](acp-watch/follow.md).
  Does not add HTTP/SSE, hydra, or a second agent-stdio client.
- [ACP transport PoC report (2026-09-11)](poc-acp-transport-2026-09-11.md): prototype holder/CLI,
  offline contract suite, Grok + Kimi live receipts, and the measured token drop
- [Five-runtime live smoke (2026-08-29)](live-smoke-2026-08-29.md): real tmux command receipt,
  Workflow startup, authentication boundary, shutdown, and residue evidence
- [Decisions](decisions/): architecture decision records —
  [issue #7 evidence-only interaction](decisions/issue-7-evidence-only-interaction.md),
  [issue #8 per-run main model](decisions/issue-8-per-run-main-model.md)
- [Changelog](../CHANGELOG.md): user-visible changes
