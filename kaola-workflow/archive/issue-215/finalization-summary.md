# Finalization Summary — issue-215

## Delivered

Issue #215: scoped install truthfulness, safe obsolete owned-copy retirement, and owner-aware
build-skew refusal recovery — one run, one commit on `workflow/issue-215`, rebased onto main
d25dc8d6 (post-#213/#214/#216). Gap-by-gap, measured at f12f3789:

- **Verification truthfulness** (`scripts/render-skills.py`): `--verify-install` now separates
  present-file alignment from expected-set completeness. Before, a root holding only
  `kaola-project-runner` reported `aligned`; now it reports `result=incomplete`, exit 1, with the
  ten absent workers in `missing`. Receipt-owned names this checkout no longer generates surface
  as `obsolete_owned`, stale receipts as `stale_receipts`, foreign directories as `unmanaged`
  (reported, never findings). New `--expect NAMES` (Skill names or worker platform ids) verifies
  a deliberate partial install under `scope: filtered` — it stays `aligned` while
  `root_complete: false` and stderr say the root is not a complete install. Read-only; the
  `kaola-project-runner-install-verify/1` receipt gains `scope`, `expected`, `missing`,
  `obsolete_owned`, `stale_receipts`, `unmanaged`, `unselected`, `root_complete`.
- **Installer honesty** (`scripts/install-local.sh`): install runs the checkout's own
  `render-skills.py --check` before any mutation and refuses with the existing
  `./scripts/render-skills.py --write` remedy when the generated tree is stale (uninstall is not
  gated — it reads no payload bytes). After writing, every requested Skill is verified at every
  requested destination (`-ef` link target for `--method link`, tree digest for `--method copy`);
  a payload that did not land sets `install_verify_failed` and the run exits nonzero — a write
  failure is never reported complete. `--platform`/`--no-orchestrator` requests report
  `scope: filtered` with `selected:` and per-sibling `unselected:` states, never as a
  complete-root upgrade. Obsolete copies (receipt-owned names no longer generated) retire only
  when unmodified and unreferenced (`retire-obsolete`); modified bytes, surviving referrers,
  link/non-copy paths, and receipt-less foreign paths are preserved and named (`keep-obsolete` /
  `release-obsolete` / foreign-path note). Droid's retired `~/.factory/skills` and Kimi's dual
  roots follow the existing destination rules unchanged.
- **Helper links and refusal recovery** (`scripts/install-local.sh`, `scripts/kaola-acp.py`,
  `templates/orchestrator/references/host-startup.md.tmpl`): with `--bin-links`, each helper link
  reports its actual target, build digest, and referrers as `helper:` rows separate from Skill
  alignment; a usable link still on another accepted checkout prints `helper not upgraded:` with
  the owner-safe transition (withdraw other referrers first; `kaola-locate.py register` for the
  locator link) — never silently retargeted, deleted, or claimed upgraded. The
  `worker-skill-build-skew` and `main-skill-build-skew` refusal `detail` now emits the root's
  owner route — `--runtime NAME` where the root is a runtime's own destination or a receipt
  records that runtime, generic `--skills-dir` only where nothing owns it — plus the matching
  `render-skills.py --verify-install [--expect ...]` command, a complete-root refresh (no
  `--platform`) when siblings are stale, the Delegator/operator handoff for a Host that cannot
  install (task and seat preserved), and the explicit pre-mutation
  (`mutation_status=not_started`) retry condition. Existing #198/#205 wording kept verbatim where
  tests pin it; no parallel refusal framework.

Host acceptance: ZCode Host zcode-KPR-orchestrator-main accepted tip c13ca97c, re-ran the focused
suite (8/8, 85 checks) and render --check on the worktree, then issued finalize-go after the
#213/#216 serialization gate opened. Post-acceptance deltas before this finalize: fabc2a33
(one-character repair of a list marker the first rebase splice dropped from the #208 CHANGELOG
entry) and the d25dc8d6 re-sync — CHANGELOG.md conflict at the shared "## Unreleased" anchor
resolved keeping #213/#214/#215 entries; ten generated `main-skill-build.json` conflicts resolved
by re-render (`render-skills.py --write`, then `--check` PASS, budgets OK including the 8192 B
host-startup.md cap). Squashed back to a single commit f12f3789 for a clean merge sink.

## Files Changed

CHANGELOG.md, docs/api.md, docs/zcode-host.md, scripts/install-local.sh, scripts/kaola-acp.py,
scripts/render-skills.py, scripts/validate.sh,
templates/orchestrator/references/host-startup.md.tmpl,
tests/contract/test-installer-migration.sh, tests/contract/test-installer-runtimes.sh,
tests/contract/test-issue-123-shared-refs.py, tests/contract/test-issue-162-upgrade-safety.py,
tests/contract/test-issue-215-install-truthfulness.py (new), and regenerated
skills/*/scripts/{kaola-acp.py,main-skill-build.json} plus
skills/kaola-project-runner/references/host-startup.md.

## Test Coverage

New focused suite `tests/contract/test-issue-215-install-truthfulness.py` (registered in
validate.sh lanes all+a): 8/8 tests, 85 checks — single-Skill root reported incomplete; filtered
`--expect` scope honest both directions; receipt-owned obsolete inventory + foreign reporting;
preflight render gate refuses pre-write (stale and missing renderer); filtered install scope
reporting + post-verify + repeat-safe complete install; obsolete retirement matrix
(unchanged/co-owned/modified/stale-receipt/foreign); --bin-links helper report with a usable
older-checkout link kept and named not-upgraded; owner-aware refusal routes (native `--runtime`
owner, shared-root referrer, unmapped complete-root refresh, single-platform route, renamed-copy
owner-confirm, main-skill route).

Existing applicable suites on the rebased tree: test-installer-migration.sh PASS,
test-installer-runtimes.sh PASS, test-issue-123-shared-refs.py 6/6 (62 checks),
test-issue-119-host-entry.py 11/11 (164 checks), test-generated-skills.py PASS,
test-issue-98-dsh-acp.py 37/37, test-issue-162-upgrade-safety.py 27/27 (one assertion updated —
its stale root is codex's own destination, so the route legitimately became `--runtime codex`;
the other two in-flight #209 fixes came in with the rebase). Fixture render stubs added to the
three installer-fixture builders so the new pre-mutation gate sees a coherent render.

Full `./scripts/validate.sh`: ran to completion twice — first run surfaced only the
test-issue-98 literal-selection regex failure (my blast radius, fixed by restoring the literal
`selection=(...)` list); second run on c13ca97c green end-to-end (zero FAILED/SKIPPED; log
/tmp/devin-overflows-501/shell-217591-2bf6ed91e8043b19/content.txt). Re-run on the rebased
candidate f12f3789: see `## Validation` and .cache/final-validation.md. bash 3.2.57 skips
per-suite watchdog wrapping (named receipt, expected per AGENTS.md #151).

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/api.md
- docs/zcode-host.md
- scripts/install-local.sh
- scripts/kaola-acp.py
- scripts/render-skills.py
- scripts/validate.sh
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/references/host-startup.md
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/orchestrator/references/host-startup.md.tmpl
- tests/contract/test-installer-migration.sh
- tests/contract/test-installer-runtimes.sh
- tests/contract/test-issue-123-shared-refs.py
- tests/contract/test-issue-162-upgrade-safety.py
- tests/contract/test-issue-215-install-truthfulness.py

## Documentation Docking

DOCKED — see .cache/doc-docking.md. docs/api.md and docs/zcode-host.md updated to match the new
installer/verification/refusal behavior; CHANGELOG.md carries the Unreleased entry with
`Seats: restart not required` — the operator-test surface
(`scripts/kaola-acp-holder.py`, `scripts/kaola-zcode-acp.py`, `scripts/kaola-quota.py`,
`scripts/adapters`, `platforms/`) is untouched; `scripts/kaola-acp.py` is worker-Skill payload,
not a restart-required path. README unchanged (no pinned behavior altered); grok-golden frozen.

## Follow-Up Items

None filed. Run-discovered items were corrected inline pre-commit (CHANGELOG list marker, the
test-issue-98 literal-selection regex, the test-issue-162 route assertion).

## Readiness

READY — Host accepted and issued finalize-go; merge sink; close #215 on verified merge.
No release, tag, or install.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-215/.cache/doc-docking.md
- kaola-workflow/archive/issue-215/.cache/final-validation.md
- kaola-workflow/archive/issue-215/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-215/finalization-summary.md
- kaola-workflow/archive/issue-215/mission-ledger.jsonl
- kaola-workflow/archive/issue-215/workflow-state.md
