# Documentation update — issue-7

verdict: PASS

- `AGENTS.md` now records the communication-driver boundary and forbids semantic evidence gates.
- `README.md` documents the five-platform start/observe/capture/send/key/stop loop and no implicit Workflow or heartbeat behavior.
- `docs/architecture.md` separates evidence collection, exact transport integrity, and Agent-owned judgment.
- `docs/api.md` documents the `key` API, advisory preflight evidence, optional snapshot correlation, and truthful restoration fields.
- `docs/conventions.md` records the shared-template and evidence-first maintenance rules.
- `CHANGELOG.md` records the user-visible communication-only behavior and migration boundary.
- `docs/live-smoke-evidence-first-2026-08-30.md` records the real five-platform evidence and the Claude account limitation.
- `AGENTS.md` and `docs/conventions.md` require formal Cursor experiments to select non-FAST Cursor
  Grok 4.6 through the native UI before prompt verification; this is explicitly not Runner policy.
- No environment-variable example changed; `.env.example` has no impact.

All structured fields and command examples were transcribed from the implemented scripts, generated Skills, test fixtures, or real tmux receipts.
