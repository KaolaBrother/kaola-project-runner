# Finalization Summary — issue-204

## Delivered

Issue #204: a fresh Host-managed worker start now expresses the selected authorized configuration
explicitly instead of "Use Runner default start" — `--tier <selected-preset>`, including `--tier
default` when default is the actual choice — and lets the manifest resolve that preset's
model/effort; an explicit authorized model/effort override keeps its own existing precedence.
Before the first send, the Host reads that start's own receipt and reconciles `model_selection`/
`config_application`/`effective_selection` against the originally authorized selection, not the
command's own resolved default, interpreting aliases and stale echoes through existing platform
evidence (`applied: true` is application evidence, not proof of the actual model). A seat
demonstrably outside the intended grant gets no project work: an unused seat is exact-stopped and
restarted with the intended configuration; a working seat keeps its existing safe stop/resume or
`drain-restart` route, with the correction carrying the intended preset explicitly. Resume
semantics are unchanged: a legitimate same-assignment resume still preserves its saved authorized
model/effort. The shared Platform Runner wording (`templates/SKILL.md.tmpl`) now also clarifies
that an existing grant — including the default-authorized pool — authorizes preset selection
without a fresh user naming; standalone (non-Host) omitted-tier resolution to `default` is
unchanged. Prompt/reference correction only: no new receipt format, authorization registry, CLI
flag, transport classifier, model probe, or dispatch service.

Issue parts → evidence (wording verified against the template diffs; this is a prompt/reference
correction, so there is no runtime test surface to add — see Test Coverage for the regression
suites that must keep passing unchanged):
- AC1 pool Codex Luna/max start carries `--tier luna`; a default-resolving receipt is recognized
  before send → `templates/orchestrator/references/{host-startup,zcode-host-dispatch}.md.tmpl`
  examples now show `--tier luna`; zcode-host-dispatch.md.tmpl's new paragraph requires matching
  `model_selection`/`config_application`/`effective_selection` against the selected preset "not
  the command's default" before the first send.
- AC2 pool Claude Sonnet/max start explicitly selects sonnet → the same rule is platform-generic
  (`templates/orchestrator/SKILL.md.tmpl` Dispatch notes: "Pass the selected authorized `--tier`,
  default included"); `worker-profiles.md.tmpl`'s existing pool table already names `sonnet`.
- AC3 authorized default/explicit override still works, no fabricated effort/Fast → untouched:
  `templates/SKILL.md.tmpl`'s existing override-precedence paragraph (lines 53-57) was not edited.
- AC4 same-assignment resume preserves saved config; correction passes intended selection → the
  Defaults table ("Resume preserves saved native choices") and `--resume`/`--continue` paragraph
  are untouched; the new zcode-host-dispatch.md.tmpl paragraph says a working seat's correction
  uses drain-restart "correcting explicitly", and `worker-profiles.md.tmpl`'s existing
  `drain-restart --resume ID` "with an explicit `--tier`/`--model`" mechanism is unchanged.
- AC5 stale/alias/missing-field interpretation without invented claims → "aliases read through
  this platform's evidence, and `applied: true` isn't proof" (zcode-host-dispatch.md.tmpl);
  `templates/SKILL.md.tmpl`'s existing "mismatch or unreadable actual model remains evidence...
  does not disable the communication channel" is untouched.
- AC6 refused/reused/unknown-effect handling unchanged → no semantic edits to the stale-seat,
  `session-exists`, or refusal-handling paragraphs, only byte-budget rewording of adjacent
  sentences (verified no meaning change while trimming to fit `reference_bytes`).
- AC7 no new QA seat/registry/schema/live model test → diff inspection: only prose changed in the
  4 template files; no new script, test fixture, or registry.

## Files Changed

`templates/SKILL.md.tmpl`; `templates/orchestrator/SKILL.md.tmpl`;
`templates/orchestrator/references/host-startup.md.tmpl`;
`templates/orchestrator/references/zcode-host-dispatch.md.tmpl`; `CHANGELOG.md`; cascading
generated output (`skills/*/SKILL.md`, `skills/*/scripts/main-skill-build.json`,
`skills/kaola-project-runner/references/{host-startup,zcode-host-dispatch}.md` — 28 files, +174/-146
lines). Commits 4af3686b, ac7ab398, merge f0cd8715 (resync onto main 34560d5d after #203 landed;
the only conflict was both issues inserting a new CHANGELOG Unreleased bullet at the same point,
resolved by keeping both, #204 first).

## Test Coverage

No new tests: this is a prompt/reference correction with no runtime behavior change (acceptance
case 7). Existing suites verified to still pass, unchanged, both before and after the resync onto
main (post-#203, including its 72 new lines in `test-acp-contract.py`):
- `test-acp-contract.py` — 78/78 (includes #203's `Issue203StartEvidenceTests` and the existing
  `Issue34ModelSelectionAcpTests`)
- `test-issue-111-model-tiers.py` — 25/25 (tier resolution / `tier-not-declared`)
- `test-issue-85-zcode-resume-advertised-model.py` — 7/7 (resume preservation)
- `test-issue-64-receipt-bound.py` — 6/6 (receipt boundedness)
- `test-issue-41-orchestrator.py` — 23/23 (orchestrator template contract)
- `test-issue-123-shared-refs.py` — 6/6 tests, 62 checks (shared-refs/install contract)
- `test-progressive-disclosure.py` — 15/15 (byte-budget contract)
- `test-generated-skills.py` — PASS
- `validate-skill.py` — PASS on `kaola-project-runner`, `codex-kaola-project-runner`,
  `claude-code-kaola-project-runner`
- `render-skills.py --write`/`--check` — PASS both before and after the #203 resync; budgets OK
  (`main_skill_bytes` 17405/17408, both touched `reference_bytes` files within single-digit bytes
  of their 8192 B cap)

No live model probe was run, and the full `./scripts/validate.sh` (~70 suites, mostly unrelated
platforms) was not run by scope — same scope decision #203 recorded. See `.cache/final-validation.md`.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- skills/claude-code-kaola-project-runner/SKILL.md
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/SKILL.md
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/SKILL.md
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/SKILL.md
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/SKILL.md
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/SKILL.md
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/SKILL.md
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/SKILL.md
- skills/kaola-project-runner/references/host-startup.md
- skills/kaola-project-runner/references/zcode-host-dispatch.md
- skills/kimi-cli-kaola-project-runner/SKILL.md
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/SKILL.md
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/SKILL.md
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/SKILL.md.tmpl
- templates/orchestrator/SKILL.md.tmpl
- templates/orchestrator/references/host-startup.md.tmpl
- templates/orchestrator/references/zcode-host-dispatch.md.tmpl

## Documentation Docking

DOCKED — see `.cache/doc-docking.md`.

## Follow-Up Items

None filed. Cross-check against #203 (per the issue's own boundary note) found no wording break:
`docs/api.md` confirms #203 kept `model_selection`/`config_application`/`effective_selection` as
the same start-receipt field names this run's reference text cites, only adding `start_evidence` as
an additional status/observe carrier of that same evidence. Optionally, `zcode-host-dispatch.md.tmpl`
could someday also mention `start_evidence` for reconciling an already-working seat whose original
start receipt has scrolled away — #203's own finalization-summary.md flagged this as "may [do],
not required" for #204, and it remains a nice-to-have, not a defect, for the same reason: the
existing start-receipt-based reconciliation this run added is already correct and sufficient for
its stated cases, and near-zero remaining byte budget on that file makes it a real cost, not a
one-line addition.

## Readiness

Ready. The Host accepted 4af3686b + ac7ab398. Validation passed (see above; recorded, byte-identical
to what ran). Docs are docked. `templates/grok-golden/` and the v0.6.7 tag/pin are untouched; the
grok-bot bridge stays at content stage, unpinned, 2555 B (no change from baseline). Sink: merge into
local main, then close #204.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-204/.cache/doc-docking.md
- kaola-workflow/archive/issue-204/.cache/final-validation.md
- kaola-workflow/archive/issue-204/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-204/finalization-summary.md
- kaola-workflow/archive/issue-204/mission-ledger.jsonl
- kaola-workflow/archive/issue-204/workflow-state.md
