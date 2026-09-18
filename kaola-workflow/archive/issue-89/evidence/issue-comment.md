## Evidence correction (no product defect)

The issue body's stale-defect hypothesis is **falsified**. OpenCode `acp_verified_versions: "cli=1.18.29;protocol=1"` is a real live ACP PASS, not a source-audit leftover and not wrong because a later session also passed.

### What 1.18.29 actually is

Written in `ed61666` (ACP productionization) after live scenarios 1 / 3 / 4 / 7:

- `docs/acp-live-verification-2026-09-11.md` — CLI/agent `1.18.29`; initialize PASS; scenarios 1, 3, 4, and 7 PASS.
- `kaola-workflow/archive/bundle-18-19-20-21/evidence/opencode-preflight.json` — `agent_info.version=1.18.29`, `protocol_version=1`.

Issue #24 later measured skip-all against that same 1.18.29 and did **not** introduce the stamp.

### What the field is (and is not)

Existing contract: a **verified** CLI version plus negotiated `protocolVersion` (`docs/runner-v2-dual-transport-design.md` §7.5). Runtime copies it onto `bridge.verified_versions` as a fact. There is no implemented last-live duty, no `verified_version_match` gate, and no test that the stamp equal the most recent live CLI.

Later live does not obligate a restamp. Same repo already keeps Kimi at `cli=0.41.0` after Issue #65 live-passed `agent_info.version=2.0.0`.

### What 1.18.31 is

Additional live evidence from Issue #65 (`live-matrix/opencode-1-start.json`: `transport.agent_info.version=1.18.31`, `state=ready`, `acp_session_id=ses_f4d1faf4dffeqyXDck0FxZTSBa`, protocol 1; composite interrupt PASS). Issue #88 already recorded that composite on 1.18.31 in `steering_summary` while **keeping** the 1.18.29 stamp. It is extra evidence, not a defect in the stamp.

1.18.17 remains the historical native-steering probe (`-32601`), not the verified-versions stamp.

### Closeout

No production manifest, docs, policy, or tests will change. A last-live RED draft was proven on `5dd18da` then withdrawn uncommitted. Closing as no product defect.
