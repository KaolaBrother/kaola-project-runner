# v0.1.0 — Draft release notes (not published)

Scope: combined issues #33, #34, #36 (per owner — single v0.1.0, no earlier release).
This draft covers the #34 contribution; merge the #33/#36 sections when those runs dock.

## Highlights

- Seven generated Runner Skills (Grok, Claude Code, OpenCode, Kimi CLI, Cursor CLI, Devin, Codex)
  with exact-owned tmux/PTY and ACP transports, relay-mediated prompt delivery, and truthful
  receipts.
- Per-run model presets and explicit Fast opt-in (issue #34).
- (#33) ACP observation refreshes model metadata after successful configuration — pending that
  run's own finalization record.
- (#36) — pending that run's own finalization record.

## Model selection and Fast (issue #34)

- Every platform declares `default` and `upgrade` presets; `--tier default|upgrade` selects the
  preset, explicit `--model` wins, bare `--model` inherits no preset effort, and resume/continue
  without selection flags preserves the native saved selection.
- `--fast on` is a per-run explicit opt-in (default off) through each platform's native surface:
  Codex ACP `fast-mode` + PTY `-c service_tier`; Cursor parameterized ACP `fast` option
  (`"true"`/`"false"` strings) + `-fast` PTY picker variants; Claude Code process-scoped
  `--settings '{"fastMode": ...}'` passed verbatim (the native CLI decides model support;
  effective reports `unknown` without native evidence); Devin `-fast` catalog variants.
- Cursor ACP negotiates `clientCapabilities._meta.parameterizedModelPicker` so resolved picker IDs
  decompose onto native `model`/`effort`/`fast` options exactly — verified live with Grok 4.6
  Extra High Fast Off (`VERIFIED_XHIGH_OFF`, end_turn, zero tools).
- No automatic model escalation; rejected or unadvertised options are reported limitations, never
  session failures; receipts never claim an unproven effective state.

## Also in this release

- ACP status/observe report a recorded, fully exited stop as `stopped` (#32).
- Uniform end-of-delegation and resume guidance across all Skills (#30).
- Pinned ACP wrapper versions, per-platform env allowlists, and preflight capability reporting.

## Notes for reviewers

- `templates/grok-golden/` remains frozen; `skills/` is generated output.
- Live ACP smoke evidence: `kaola-workflow/bundle-34/evidence/acp-live-smoke-34.md`.
- Known limitations are recorded per platform in each manifest's `acp_quirks` and the evidence
  file (e.g. Claude ACP wrapper remains probe-eof; PTY login requirement reported honestly).
