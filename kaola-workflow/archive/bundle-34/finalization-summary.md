# Finalization summary — bundle-34 (issue #34)

Candidate: `7226f4d` on `workflow/bundle-34` (accepted impl `1545404` +
test-harness-only commit: bash 3.2 empty-array expansion fix in
`tests/contract/test-model-policy.sh` — supervisor's independent run hit
`override_effort_args[@]: unbound variable` under `set -u` at devin's empty
`override_effort`; fixed by explicit with/without-effort branches at both call
sites; suite re-verified PASS)
PR: https://github.com/KaolaBrother/kaola-project-runner/pull/35 — OPEN, non-draft.
Release scope (per owner): combined v0.1.0 across issues 33/34/36 — no earlier release;
this run covers #34 only. v0.1.0 remains unpublished pending 33 and 36.

## Delivered

- Per-run `default`/`upgrade` model presets on all seven platforms with precedence
  explicit `--model` > `--tier` > default; bare `--model` inherits no preset effort;
  resume/continue without selection flags preserves the native saved selection
  (`resume-preserved`).
- Explicit per-run Fast opt-in (`--fast on`, default off) through each platform's
  native surface: Codex ACP `fast-mode` + PTY `-c service_tier`; Cursor parameterized
  ACP `fast` option (`"true"`/`"false"` strings) + `-fast` PTY picker variants;
  Claude process-scoped `--settings '{"fastMode": ...}'` passed verbatim; Devin
  `-fast` catalog variants; honest `unsupported`/`unknown` elsewhere.
- Cursor-only `_meta.parameterizedModelPicker` initialization negotiation on both
  holder `start` and `preflight` (`acp_init_meta`), with picker IDs decomposed via
  `acp_model_map` (base model value) + ID-suffix effort + `acp_fast_values`
  conversion — verified live: `model=grok-4.6`, `effort=xhigh`, `fast="false"`,
  reply `VERIFIED_XHIGH_OFF`, `end_turn`, zero tools, `residual_pids=[]`.
- ACP `start` applies model → effort → Fast in order with per-option
  `config_application` receipts; rejected/unadvertised options are limitations,
  never session failures or transport gates; `preflight` reports
  `advertised_config_options`.
- Truthful fast reporting: `effective` reflects proven native state only —
  rejected config/unapplied fast-variant model report `unknown`, never false
  on/off; no inferred-capability classifiers anywhere (native CLI decides support).
- No automatic escalation; `templates/grok-golden/` frozen; all seven Skills
  regenerated.

## Files Changed

95 files changed vs merge-base `6e9fd43` (+6708/−697): 7 platform manifests,
7 adapters, `kaola-acp.py`/`kaola-acp-holder.py`/`kaola-model-policy.py`/
`kaola-tmux.sh`/`render-skills.py`, `templates/` (SKILL, acp, platform refs),
all 7 generated `skills/` trees, 6 contract test files, README/CHANGELOG/
docs(api,architecture).

## Test Coverage

- `tests/contract/test-acp-contract.py` — 38 tests (incl. 16 issue-34 cases:
  ordered config, precedence, resume-preserved, rejected fast/model, Cursor
  parameterized init meta/order/values, upgrade mapping, verbatim fast-variant
  decomposition, manifest no-descriptor guard).
- `tests/contract/test-model-policy.sh` — per-platform resolution/launch suite
  incl. Codex service_tier, Cursor variant, Devin unsupported, Claude settings
  pin/opt-in/verbatim cases.
- `tests/contract/test-adapters.sh` — launch-shape assertions incl. Claude
  fastMode pin.
- `tests/contract/test-generated-skills.py`, `test-devin-regressions.py`,
  `test-claude-code-runtime.sh` — updated and passing.
- Live ACP smoke (`/tmp/kpr-34-live`, evidence file): codex default/upgrade/
  fast/resume/explicit, grok, kimi, opencode, devin, cursor parameterized
  round-trip — all send/reply/stop with empty residuals.

## Validation

- `./scripts/render-skills.py --check` — PASS (7 Skills)
- `./scripts/validate.sh` — exit 0, all suites PASS (recorded in
  `.cache/final-validation.md`, bound to this tree's candidate hash
  `7323a1e9f7b003512956a63649e866a163d28a9e613b8df05b2d8b433691522f`)
- Live evidence: `kaola-workflow/bundle-34/evidence/acp-live-smoke-34.md`
  (dated 2026-09-13, per-session record dirs + stop proof; parameterized
  Cursor round appended after supervisor's measured route)
- Acceptance legs: automated suites above + supervisor's own independent
  Cursor test (`FINAL_CURSOR_OK`, end_turn, `residual[]`) — the only live
  Cursor evidence relied upon; no Claude login/live PTY (owner restriction).

## Changed Paths

See Files Changed — 95 paths, enumerated by
`git diff --name-only 6e9fd43..1545404` (canonical list preserved in the run
record at `/tmp/b34-changed.txt` during this session).

## Documentation Docking

`DOCKED` — `.cache/doc-docking.md` covers README, CHANGELOG, docs/api.md,
docs/architecture.md, templates, manifests, generated skills, AGENTS.md,
and the frozen `templates/grok-golden/`.

## Follow-Up Items

- Issue #33 (ACP stale model metadata) — separate owner, untouched.
- Issue #36 — separate worker; combined v0.1.0 release covers 33/34/36.
- Claude ACP wrapper remains `probe-eof` (initialize never completes) — a
  real platform limitation reported in `acp_quirks`, not a Runner defect.
- Live PTY/Cloud/Claude-account testing not performed on this machine per
  owner restriction — static contract coverage only.
- Draft release notes: `kaola-workflow/bundle-34/release-notes-v0.1.0.draft.md`
  (prepared, not published — needs updating to combined 33/34/36 scope).

## Readiness

Candidate frozen at `1545404`, validation recorded, docs docked, summary
written. Stopped before sink/merge/archive/closure pending final supervisor
diff acceptance — no issue closed, no archive, no merge performed.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/bundle-34/.cache/doc-docking.md
- kaola-workflow/archive/bundle-34/.cache/final-validation.md
- kaola-workflow/archive/bundle-34/.cache/mirror-digest.json
- kaola-workflow/archive/bundle-34/.cache/origin/selection-record.json
- kaola-workflow/archive/bundle-34/evidence/acp-live-smoke-34.md
- kaola-workflow/archive/bundle-34/finalization-summary.md
- kaola-workflow/archive/bundle-34/mission-list.md
- kaola-workflow/archive/bundle-34/release-notes-v0.1.0.draft.md
- kaola-workflow/archive/bundle-34/workflow-state.md
