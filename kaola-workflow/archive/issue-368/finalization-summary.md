# Finalization Summary — issue-368

## Delivered

Grok and Cursor usage draw from one shared quota pool, `cursor-grok`, that
each runtime reads through its own acquisition with no cross-mapping. Each
manifest keeps its own package id — `cursor-cli:account` and `grok:account`,
both named `Cursor+Grok account usage`, window `monthly`, carrying a new
`pool: "cursor-grok"` marker validated as a bare token; a model still
resolves to its own runtime's id and never to the other platform's. The old
`cursor-models`/`other-models` split and its `explicit` map are removed.
`quotaPool` on emitted model rows stamps the shared pool `cursor-grok` on
both platforms, so `packages`, `model-package` (which now emits `pool`),
`observe`/`status`/`view`, Delegator view, and Host view present the two
runtimes under one shared pool. `scripts/kaola-quota.py` gains two
independent read-only HTTP acquisitions dispatched by `--probe` on each
runtime's own platform — the Cursor acquisition reads `GET
{CURSOR_API_ENDPOINT|api2.cursor.sh}/auth/usage` with a
`CURSOR_API_KEY`/`~/.cursor` bearer and sums per-model `numRequests`
against `maxRequestUsage`; the Grok acquisition reads `GET
{GROK_WEB_BASE_URL|code.grok.com}/billing?format=credits` with a
`GROK_API_KEY`/`~/.grok`/`grok login` `auth.json` bearer and reads
`includedUsed`/`monthlyLimit`/`creditUsagePercent`/`currentPeriod.end`.
Neither spawns a binary, writes a record, or derives from the other; the
Cursor reading works with every Grok credential surface absent. Stale
`quotaPool` values are re-derived on every emission (a stored
`cursor-cli:cursor-models` row re-stamps to `cursor-grok`); an installed
seat holding the old catalog reports `stale` until restart. Dispatchable
presets are unchanged.

## Candidate

Branch `workflow/issue-368`, one commit on `153409b8` (current main):

- `981bee10` Share one Cursor+Grok quota pool across two independent
  acquisitions (#368): `platforms/cursor-cli.yaml`, `platforms/grok.yaml`,
  `scripts/kaola-quota.py`, `scripts/kaola-acp.py`,
  `tests/contract/test-issue-148-quota-packages.py`, `docs/api.md`,
  `CHANGELOG.md` Unreleased entry, and regenerated `skills/` + `hosts/`
  output (Grok Bot bridge stays content stage, `saveable: false`).

Rebased per Host acceptance direction from `45238ea0` (base `72488b3c`) to
`61db4d3d` (base `51de87ae`) to `981bee10` (base `153409b8`, carrying #367
and #363). CHANGELOG conflicts resolved by entry union each time
(#365/#364/#367/#363 + #368). `git diff origin/main HEAD --
scripts/kaola-recovery-routes.py` is empty — 315 route rows, only grew.

## Evidence

- `./scripts/render-skills.py --check` -> PASS on `981bee10` (11 workers +
  kaola-project-runner + kaola-delegator + grok-bot bridge, content stage,
  `saveable: false`; budgets OK).
- `./scripts/validate.sh --suite` on `981bee10`, all OK:
  test-issue-148-quota-packages (21 — incl. the five new #368 cases: shared
  pool with per-runtime ids, per-runtime acquisition dispatch hitting only
  the expected fixture route, two-acquisition agreement on
  used/limit/used_percent/reset_at, Cursor reads with every Grok credential
  absent, `packages`/`model-package` pool markers),
  test-issue-346-worker-grants (14), test-issue-363-dsh-resume-permission
  (10), test-issue-345-dsh-commandcode (3), test-issue-347-commandcode-usage
  (23), test-issue-147-installed-survey (10), test-issue-33-config-meta (9),
  test-generated-skills (render + 13 validate-skill + grok-bot-verify PASS).
- Recorded at `kaola-workflow/issue-368/.cache/final-validation.md`
  (verdict: pass, bound to this worktree).
- No Grok seat, agent, or binary was started; all provider reads are
  `ThreadingHTTPServer` fixture-backed contract tests.

## Known failures or unverified scope

- `test-issue-309-recovery-routes.py` fails one case on clean `main`
  `153409b8` itself: `missing-host-holder-instance-id` (introduced by #365's
  holder change, after #364's route sweep) has no `ROUTES` row. Unrelated
  to this diff; filed as a follow-up below.
- Live provider responses were not exercised — both acquisitions are
  fixture-verified; the endpoint shapes come from the shipped CLI binaries
  and the documented `/auth/usage` surface.

## Follow-Up Items

- filed: #370 — `missing-host-holder-instance-id` has no `ROUTES` row
  (introduced by #365 after #364's route sweep;
  `test-issue-309-recovery-routes.py` fails identically on clean main).
  searched: `gh issue list --state open --search
  "missing-host-holder-instance-id"` -> 1 hit (#370 itself, already filed);
  verified the issue exists with a non-empty body.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/api.md
- platforms/cursor-cli.yaml
- platforms/grok.yaml
- scripts/kaola-acp.py
- scripts/kaola-quota.py
- skills/antigravity-kaola-project-runner/scripts/kaola-acp.py
- skills/antigravity-kaola-project-runner/scripts/kaola-quota.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-quota.py
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-quota.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-quota.py
- skills/cursor-cli-kaola-project-runner/scripts/platform.yaml
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-quota.py
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-quota.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-quota.py
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-quota.py
- skills/grok-kaola-project-runner/scripts/platform.yaml
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-quota.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-quota.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-quota.py
- tests/contract/test-issue-148-quota-packages.py

## Readiness

Candidate `981bee10` is accepted by the Host, rebased on current main
`153409b8`, validated at the diff scope, and ready for the merge sink
(sink: merge, issue #368, branch `workflow/issue-368`).

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-368/.cache/final-validation.md
- kaola-workflow/archive/issue-368/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-368/finalization-summary.md
- kaola-workflow/archive/issue-368/mission-ledger.jsonl
- kaola-workflow/archive/issue-368/workflow-state.md
