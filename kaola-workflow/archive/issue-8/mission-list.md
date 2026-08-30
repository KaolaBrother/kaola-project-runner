# Establish verified per-run main-model selection for all five runtimes

- item: Measure the current model catalog, launch arguments, resume behavior, and post-launch model evidence surfaces for Grok CLI, Claude Code, OpenCode, Kimi CLI, and Cursor CLI without changing global configuration.
  status: done
  dispatched: investigator (standard-reasoning tier) performs read-only source and real-CLI catalog/help probes for all five runtimes from the Issue #8 worktree, returns exact commands/output and uncertainty to the primary runtime, and the durable synthesis will land in `kaola-workflow-design-issue-8.md`.
  result: PASS — measured installed catalogs, exact argv and new/continue/resume behavior for all five runtimes; identified native evidence surfaces, Claude's expired login boundary, Cursor's exact non-FAST `cursor-grok-4.6-xhigh` selector, and that Cursor `/model` mutates global picker state and therefore is not a read-only probe.

- item: Define baseline-failing behavioral acceptance for user override, Runner default, saved-picker override, unavailable/mismatched/unreadable models, resume behavior, and literal-safe malicious model input across all five runtimes.
  status: done
  dispatched: tdd-guide (standard-reasoning tier) owns only Issue #8 behavioral tests and fixtures in the Issue #8 worktree, proves meaningful RED against baseline 3782d65, and must not edit production scripts, adapters, manifests, templates, generated Skills, or documentation.
  result: PASS — `tests/contract/test-model-policy.sh` failed meaningfully on baseline `3782d65` for all five missing model contracts, then passed against the implementation while retaining custody of the acceptance surface.

- item: Implement the shared model-policy evidence contract and five adapter-specific catalog resolution, argv construction, and post-launch verification while preserving the communication-only Agent/Runner boundary.
  status: done
  dispatched: primary runtime implemented the shared resolver/verifier, exact literal argv and runtime-specific effort plumbing across the five adapters in the Issue #8 worktree after the independent RED contract existed.
  result: PASS — user override wins, otherwise each adapter's declared Runner default is resolved against readable catalog evidence; unavailable pre-session choices create no unspecified session, while post-launch mismatch or unreadable evidence remains a reported fact and never blocks send/observe/stop communication.

- item: Generate and dock the five Skills plus root API, architecture, conventions, changelog, and Issue evidence for user-override-first otherwise Runner-default semantics.
  status: done
  dispatched: primary runtime updated the authoritative templates/manifests/docs and regenerated every supported platform Skill from the shared source without modifying the frozen Grok golden protocol fixture.
  result: PASS — all five generated Skills carry the same model evidence fields and platform-specific defaults; README, API, architecture, conventions, changelog, AGENTS and Issue #8 design evidence document the communication-only boundary and Cursor non-FAST rule.

- item: Prove focused and repository-wide contracts plus exact-tmux live smokes for all five runtimes, including new, continue, and exact resume within each runtime's real capabilities and available accounts.
  status: done
  dispatched: primary runtime is running repository validation and exact owned tmux sessions for all five installed CLIs, will send an Agent-selected read-only workflow-next verification prompt, record model/communication evidence, and stop only those exact sessions; Claude acceptance is limited to command receipt because the installed account is not logged in.
  result: PASS — `scripts/validate.sh` completed with every contract green; exact live sessions proved runtime-owned model and prompt/reply communication for Grok, OpenCode, Kimi and non-FAST Cursor, while Claude proved Opus High selection and full prompt receipt before its truthful expired-login boundary. OpenCode sanitized session export proved variant max. All five exact sessions ended and final status was absent with no `kpr-i8-live-*` tmux residue.
