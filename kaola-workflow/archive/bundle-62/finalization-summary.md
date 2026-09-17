# Finalization summary — bundle-62 (issue #62)

## Delivered
Issue #62 "ZCode Host：通过 ACP 接入 Project Runner 并调度其他 ACP Worker" delivered in full:
- (A) ZCode as worker — pre-existing surface, unchanged, regression-held (zcode-acp contract 26/26).
- (B) ZCode as host, full lifecycle — install `--runtime zcode` → `~/.zcode/skills` (+ workspace `.zcode/skills` via `--skills-dir`); generic external-ACP → ZCode Host → Runner entry (`kaola-zcode-acp.py` 0.3.0) with three separately trackable session identities (Runner session / ACP id / native `sess_*`); nested Host→Worker isolation (separate pgids/record roots; exact stop; inner never kills outer; outer sweeps recorded inner).
- (C) Any ACP client → ZCode → Project Runner → other ACP workers — live-proven, including nested ZCode Host → ZCode Worker (E2E S3).
- (D) Event-driven heartbeat (ZCode-Host-only) — child terminated/idle → holder-to-holder notify over the existing admin socket → bounded in-memory staging (cap 32, dedup) → ONE literal `session/prompt` at the next turn boundary carrying event metadata + the FULL current heartbeat prompt body read at delivery time from `.kaola/heartbeat-prompt.json` → in-session confirmation; `--resume` redelivers unconfirmed events from the existing EventLog; other hosts keep periodic carriers; skeleton/grok-golden/hosts untouched (audit-verified zero diff).

Commits: `3cdcad8` (Phase 1), `70f384f` (Phase 2). Phase 3 real-run E2E found no code defects — no fix commit.

## Files Changed
35 files vs main `ef6dff8` (`git diff --name-only ef6dff8..workflow/bundle-62`):
- docs: `CHANGELOG.md`, `README.md`, `docs/api.md`, `docs/architecture.md`, `docs/zcode-host.md` (new)
- scripts: `scripts/install-local.sh`, `scripts/kaola-acp-holder.py`, `scripts/kaola-acp.py`, `scripts/kaola-zcode-acp.py` (new), `scripts/validate.sh`
- templates: `templates/orchestrator/SKILL.md.tmpl`
- tests: `tests/contract/test-installer-runtimes.sh`, `tests/contract/test-zcode-acp-contract.py`, `tests/contract/test-zcode-heartbeat-contract.py` (new), `tests/contract/test-zcode-host-contract.py` (new)
- generated: 20 vendored skill copies under `skills/**` (byte-identical re-renders, render --check PASS)

## Test Coverage
- New suites: `test-zcode-host-contract.py` 3/3 (47 checks); `test-zcode-heartbeat-contract.py` 7/7 (138 checks), registered in `scripts/validate.sh`.
- Regression: `test-zcode-acp-contract.py` 26/26; installer migration + runtimes PASS; issue-50 11/11 (216 checks) + runner integration 7/7 (181 checks); issue-51 6/6 (119 checks); issue-49 grok-bot host 42/42; render `--write`/`--check` PASS (173 B template headroom).
- Acceptance legs — automated: contract suites above; local: full `./scripts/validate.sh`; manual/live: Phase 3 real-run E2E (below); UAT: n/a (no UI surface changed; ZCode desktop login flow untouched).

## Validation
- Full `./scripts/validate.sh` at frozen candidate `70f384f` in the bundle-62 worktree: **EXIT=0** (finalization re-run 2026-09-17). Receipt: `kaola-workflow/bundle-62/.cache/final-validation.md` — verdict `pass`, command `./scripts/validate.sh`, `validated_candidate_hash: 9261b88a185e3ab1e4809622edad6994e19796eb53b5c866fa84d9890b2843bc` (binds the worktree tree).
- Phase 3 live E2E (REAL RUN: real ZCode 0.16.5 app-server via `KAOLA_ZCODE_ENTRY`/`KAOLA_ZCODE_NODE`, enabled GLM Coding Plan provider in-memory, zero mocks on core paths; evidence `/tmp/kw-i62-e2e/receipts/`, 44 files):
  - S1 PASS both legs — workspace `.zcode/skills` discovery (10 skills listed by real session) AND bounded real `~/.zcode/skills` install → discovery → exact uninstall, machine restored as found.
  - S2 PASS — real host session `state: ready`, codeword LION-62 restated; three identities recorded (Runner `zcode-i62-host` / ACP `zcode-1` / native `sess_146f2a1c-…`).
  - S3 PASS — the real host agent used the installed Skill to start a REAL child ZCode worker (PUMA-62 round-trip); nested isolation live-proven (separate pgids/record roots; inner exact stop left outer holder alive).
  - S4 PASS ×4 live events — full chain `heartbeat_carrier_sent` → `worker_event` → `worker_event_delivered` → `worker_event_confirmed`; delivered prompt byte-exact (sha256 reconstruction); in-session HORSE-62 confirmations; busy path conclusive (event staged mid-stream between chunks 116/118, NOT sent mid-turn, delivered at turn boundary); bonus live proof: provider stall ~18 min → exact stop (zero residue) → `--resume` → `worker_event_restored` + redelivery → confirmed.
  - S5 PASS — credential scan over 290 files: provider credential value absent everywhere; EventLog scrub redaction PASS.
  - S6 PASS — full `./scripts/validate.sh` EXIT=0 during E2E; zero leaked own processes; foreign processes untouched.
- Issue statement walk: A → pre-existing + 26/26 regression; B → install/entry/isolation (S1-S3 + host-contract 47 checks); C → S3 nested live proof; D → S4 live proof + Phase 2 audit 12/12; issue acceptance criteria E1-E5 satisfied by the S1-S6 evidence set. No unsatisfied part.

## Changed Paths
Finalize transaction finding (from `finalize --check`): 30 paths — `scripts/` (5: install-local.sh, kaola-acp-holder.py, kaola-acp.py, kaola-zcode-acp.py, validate.sh), `skills/**` (20 vendored copies incl. `skills/kaola-project-runner/SKILL.md`), `templates/orchestrator/SKILL.md.tmpl` (1), `tests/contract/` (4: test-installer-runtimes.sh, test-zcode-acp-contract.py, test-zcode-heartbeat-contract.py, test-zcode-host-contract.py). Commit-level diff adds the 5 docs files listed under Files Changed (35 total).

## Documentation Docking
DOCKED — receipt `kaola-workflow/bundle-62/.cache/doc-docking.md`. README (install paths, 19 mentions), docs/api.md (13), docs/architecture.md (7), CHANGELOG (38, incl. `KAOLA_ACP_HEARTBEAT_HOST`), docs/zcode-host.md (dedicated doc, 37) all cover the changed public behavior; Phase 2 audit verified docs match implementation line-for-line.

## Follow-Up Items
- filed: #63 (P3) — "validate.sh interrupted run can orphan contract-suite holder processes"; body confirmed non-empty; Measured/Hypothesis/Proposed-remedy recorded there; duplicate probes: 'orphan' → 1 unrelated closed hit (#49), 'validate holder leak' → 0 hits.
- Phase 2 audit low-severity notes, no action (fail-safe by design): record-root coupling yields an honest host-unreachable receipt; bounded 5 s notify / 6 s stop-grace latency.

## Final readiness
READY — all three missions done; validation pass at frozen candidate; docs docked; follow-up filed. Sink: merge `workflow/bundle-62` → main, close #62.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/bundle-62/.cache/doc-docking.md
- kaola-workflow/archive/bundle-62/.cache/final-validation.md
- kaola-workflow/archive/bundle-62/.cache/mirror-digest.json
- kaola-workflow/archive/bundle-62/.cache/origin/selection-record.json
- kaola-workflow/archive/bundle-62/finalization-summary.md
- kaola-workflow/archive/bundle-62/mission-list.md
- kaola-workflow/archive/bundle-62/workflow-state.md
