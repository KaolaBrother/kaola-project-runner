# Documentation Docking — bundle-146 (issue #146)

candidate: a5a9fa8 (workflow/bundle-146; 0d29728 + a5a9fa8 over f5dc05f)

## Checked files
- docs/api.md — UPDATED: `acp_session_new_timeout` documented beside the other optional manifest transport keys. Covers the range (0, 600], the 15 s default, codex `60` against the measured ~18 s, the 20 s start window and 60 s probe bound widening by the excess over 15 s, and `acp-session-timeout` on no answer. Transcribed from scripts/kaola-acp.py (SESSION_NEW_TIMEOUT, SESSION_NEW_TIMEOUT_MAX, START_WAIT, PROBE_WAIT, session_new_extra) and scripts/render-skills.py validation.
- templates/references/acp.md.tmpl — UPDATED: one sentence on the `start`/`preflight` session/new wait and `acp-session-timeout`. Also updates the 10 rendered skills/*/references/acp.md through render-skills.py --write; --check PASS, budgets OK.
- CHANGELOG.md — UPDATED: Unreleased entry for Issue #146.
- README.md — NO IMPACT: lists no manifest transport fields and no start timeouts (Host accepted this call).
- docs/runner-v2-dual-transport-design-2026-09-11.md — NO IMPACT: a dated historical design record, not a living contract.
- AGENTS.md — NO IMPACT: install/test/lint commands unchanged.
- templates/orchestrator/, templates/kaola-delegator/, hosts/grok-bot/ — NO IMPACT: no control-plane, Delegator, or bridge surface consumes the wait (render --check PASS, bridge unchanged).

DOCKED
