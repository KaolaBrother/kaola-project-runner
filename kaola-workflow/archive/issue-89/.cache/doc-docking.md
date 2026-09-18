# Documentation docking — Issue #89

No-code closeout. Candidate tree is origin/main `5dd18da` (worktree `workflow/issue-89` has
zero product diff). Outer ACCEPT of mission 6: 1.18.29 is a real live ACP PASS; the existing
contract has no last-live obligation; the issue's stale-defect hypothesis is falsified.
No production manifest, docs, policy, or tests were changed.

## Checked files

| File | Outcome | Detail |
|---|---|---|
| `README.md` | no impact | Does not name `acp_verified_versions` or claim OpenCode 1.18.29 is stale. |
| `CHANGELOG.md` | no impact | #88 Unreleased entry records the 1.18.17 probe vs stamped 1.18.29; that is #88's native-steering calibration, not a last-live restamp. Left as historical. |
| `docs/api.md` | no impact | Names `acp_verified_versions` 1.18.29 as the OpenCode stamp beside the 1.18.17 probe. That matches the live 2026-09-11 PASS. No "latest" claim. |
| `docs/conventions.md` | no impact | Does not define `acp_verified_versions`. No last-live policy was added. |
| `docs/acp-live-verification-2026-09-11.md` | no impact | Dated live record of OpenCode CLI/agent 1.18.29, scenarios 1/3/4/7 PASS. This is the evidence that 1.18.29 is not a defect. Historical by construction. |
| `docs/runner-v2-dual-transport-design.md` | no impact | §7.5: the field records a verified CLI version and negotiated protocolVersion as a fact. Not a last-live duty. Design record; not rewritten. |
| `platforms/opencode.yaml` | no impact | Stamp remains `cli=1.18.29;protocol=1`. `steering_summary` still distinguishes the 1.18.17 native probe from that stamp and records 1.18.31 composite interrupt as extra live evidence. |
| Generated `skills/**` | no impact | Not regenerated; no source change. |

## Status

**DOCKED**
