# #271 regression receipts — verbatim archive (2026-10-08)

Dot personal-read requirement: `8440d2a1` bound only a summary; these are the original
receipts, archived byte-identical (hashes below, verified after copy). Live originals remain
at the `/tmp` locators; this directory is the fixed, pushed copy.

| File | Bytes | sha256 (original = archived) | Original locator |
|---|---|---|---|
| `r271-execute.json` | 3953 | `a03cc3f6fb98eb2351195f533126d6d1e5ecaf74be2d752bb04681784956d241` | `/tmp/r271-execute.json` |
| `r271-collect.json` | 3600 | `e1d11fc6a220fe2b483dffe1f11ed556e453c17f4a50ec50a8ecf9efc8deb92a` | `/tmp/r271-collect.json` |
| `r271-stop.json` | 370 | `cc0af84d88d98220b928cf375d1e81a57ef953a879bd748d2ca0fb78bc27a64c` | `/tmp/r271-stop.json` |
| `kpr-271-regression-result.md` | 233 | `45656c9eb23ac88561be6846577aab61702241e35957c4a92fea5c831a732fee` | `/tmp/kpr-271-regression-result.md` |

Supplementary locators (not archived here, recorded for cross-checking only):
`/tmp/r271-plan.json` 1023 B sha256 `de489dfa6393b6caa2985636f11d6fab9cf949ba26eaa43810716508e5e50901`;
`/tmp/r271-index.json` 3913 B sha256 `5552cd0c0d73cd12af9b83d15d726fa0419bdfa97307bb77c3dbe118975c5ff1`.

Chain facts the receipts show: execute carried `dispatch_event_cursor: 7` verbatim
(worker holder `af4426fd…`, prompt fp `sha256:723f0e5e…`, pool preset `codex/luna`);
collect ran on the live session BEFORE stop, `since: 7 → through: 95`,
`range_complete: true`, actual counts `failure_count: 0`, `permission_count: 0`,
`pending_permission_count: 0`, no truncation; stop after collect returned
`stopped: true, residual_pids: []`, exit 0. The bridge independently re-verified the full
range and the stop.

## Candidate-tree clarifications (kept explicit)

- The four protected dirty files (`hosts/grok-bot/INSTALL.md`, `hosts/grok-bot/bridge.json`,
  `hosts/grok-bot/kaola-delegator.md`, `templates/grok-bot/accepted-revision.json`) are
  content-stage/pin inputs that affect render, but they are NOT new source-code changes made
  by the #271 regression; their dispatch-test impact has not been adjudicated here and needs
  source reading to settle.
- The render PASS and suite results recorded in `kpr-271-regression-result.md` are
  working-tree facts on `13a0e271` + protected dirty files; they are NOT the release
  final-tree PASS.

Issue #271 remains open awaiting dot's ruling on this receipt package.
