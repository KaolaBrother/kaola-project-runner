# Documentation Docking — issue-191

Candidate: 5d9877d39bb04f4be477b6b80340a798552d5354 (workflow/issue-191; code frozen and Host-accepted at caf83ea, plus doc-only 5d9877d)

Checked files:
- docs/api.md — fixed (5d9877d): the `stop --force` reused-PID / dead-holder paragraph no longer says a leaderless agent group or a pre-`agent_started` record is trusted; it states the exact `agent_started` second match, the `pgid_identity: "unverified"` / `pgid_identity_unverified` receipt (`code: pgid-identity-unverified`, `agent_pgid`, `live_members`, `signalled: false`, `retired_record`), seat-record-only retirement (never a newer record), and `status` → `no-session`. The holder-lost stop paragraph qualifies the agent-group SIGKILL.
- CHANGELOG.md — fixed (caf83ea): `## Unreleased` #191 bullet with operator-diff fact (only scripts/kaola-acp.py and scripts/kaola-acp-sweep.py; holder/bridge/quota/adapters/platforms untouched). No release section.
- docs/architecture.md:129, docs/zcode-host.md:110 — no impact: they say holder-lost `stop --force` uses the identity-checked record and reports `swept_pgids`; still true.
- templates/orchestrator/references/host-startup.md.tmpl:127 — no impact and not edited (#190 owns templates this cycle): "gone = `stopped` with `residual_pids: []`, or `no-session`" still holds, since an unverified group retires the record so `status` reads `no-session`.
- README.md — no impact: no force-stop receipt fields described; #190 owns README this cycle.
- AGENTS.md — no impact: commands, constraints, validation policy unchanged.
- skills/, hosts/grok-bot/ — generated; render-skills.py --write, --check PASS; ten skills/*/scripts/kaola-acp.py byte-equal to scripts/kaola-acp.py.
- Historical CHANGELOG sections and dated design docs — no change.

Result: DOCKED
