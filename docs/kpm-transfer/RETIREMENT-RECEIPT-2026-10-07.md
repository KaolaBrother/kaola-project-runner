# KPM source-retirement per-file receipt — 2026-10-07

Executor: Host `zcode-KPR-orchestrator-main` (holder `eb9f120438d48c82131ada5bc1e56919`).
Authorization: owner directive 2026-10-07. Authoritative candidate list: the
34 `retirement_candidates` `source_path` rows of
`~/Documents/Codex/2026-10-06/task/kpr-target-verification-a13c6d6.json`
(target commit `a13c6d6f264cf965ca45a07670dbf46cd1eb1e5f`; 105/105 target
sha256+bytes pass, 80 Git sources byte-identical, `bad: []`).

## Accounting (against the authoritative 34 candidates)

- **Candidates retired: 33** — every removed file's local sha256 re-verified
  equal to its KPM mirror row (`/tmp/kpm-target-manifest.json`) before removal.
- **Candidates dependency-retained: 1** —
  `docs/designs/ddd-component-2026-10-07/design.md`: in the authorized 34,
  retained because the kept `docs/ddd` operating contract cites it nine times
  in-repo (README, cases, c4-state-retire, kw-c8-seam). An initial same-day
  retirement of it was reverted before push and its `kpm/…`-prefixed
  citations were restored to in-repo paths.
- **Inventory separately redirected: 1 (non-candidate)** —
  `docs/kpm-transfer/kpr-source-inventory.md`, removed under its own redirect
  authorization; superseded by `HANDOFF.md`. Arithmetic note: the old
  inventory's 34-file set omitted `docs/research/i272-loop-execution.md`;
  the verification JSON's candidate rows are authoritative and this
  retirement follows them exactly.
- Total files removed: 34 (33 candidates + 1 inventory).

## Per-file audit

Method, per file: (1) local sha256 re-verified equal to the KPM mirror row;
(2) live-consumer grep over tracked files at HEAD, excluding
`kaola-workflow/` historical evidence and fellow retirees; (3) action with
the fix named.

### Retired with no live consumers (27)

| path (under docs/) | note |
|---|---|
| designs/modular-core-2026-10-07/fable-addendum.md | cited only by i270-fable-final-review.md (retiree) |
| designs/modular-core-2026-10-07/fable-convergence-review.md | no consumers |
| designs/modular-core-2026-10-07/inventory-appendix.md | no consumers |
| designs/modular-core-2026-10-07/inventory-matrix.json | no test/runtime consumer |
| designs/modular-core-2026-10-07/matrix-source-review-patch.json | no consumer |
| designs/modular-core-2026-10-07/matrix-source-review.md | no consumer |
| designs/modular-core-2026-10-07/recount.py | pure research script, zero consumers |
| designs/modular-core-2026-10-07/migration.md | cited only by kpr-source-inventory.md (removed) |
| research/i270-fable-stage-critique.md | cited only by the modular-architecture survey (retiree) |
| research/i270-worker-dsh-repo.md | survey-only |
| research/i270-worker-durable-engines.md | survey + i270-worker-f4-river (retirees) |
| research/i270-worker-f1a-opencode-goose.md | no consumers |
| research/i270-worker-f3-agentframework.md | no consumers |
| research/i270-worker-f4-river.md | survey-only |
| research/i270-worker-f5-isolation.md | no consumers |
| research/i270-worker-kw-audit.md | survey-only |
| research/i270-worker-openhands-sdk.md | no consumers |
| research/i270-worker-openwork.md | no consumers |
| research/i270-worker-orchestration-repos.md | no consumers |
| research/i270-worker-paseo.md | survey-only |
| research/i270-worker-pi-interfaces.md | survey-only |
| research/i270-worker-t3-sources.md | survey-only |
| research/i272-loop-execution.md | zero consumers; candidate row (KPM #8 §9) |
| research/i279-ddd-contract-tests.md | no external consumer |
| research/i279-ddd-source-register.md | cited by retirees only |
| research/i279-fable-review.md | cited only by i279-ddd-method.md (retiree) |
| kpm-transfer/kpr-source-inventory.md | non-candidate; separately-authorized redirect (see accounting) |

### Retired after entry-reference fix (6)

| path (under docs/) | consumer fixed |
|---|---|
| designs/modular-core-2026-10-07/adr.md | kw-c8-seam.md citations → `kpm/…` pinned prefix |
| designs/modular-core-2026-10-07/design.md | context-map.md link → KPM blob URL; c1/c4/kw-c8 citations → `kpm/…` |
| designs/modular-core-2026-10-07/p4-kw-readonly-index.md | scripts/kaola-kw-index.py docstring pointer (docstring-only change) |
| research/i270-fable-final-review.md | cited only by i270-fable-ab-addendum.md (retiree) |
| research/i279-ddd-method.md | docs/ddd/README.md + cases links → KPM blob URL |
| research/modular-architecture-and-unified-data-2026-10-07.md | kw-c8-seam.md citation → `kpm/…` |

### Dependency-retained candidate (1)

`docs/designs/ddd-component-2026-10-07/design.md` — see accounting above.

## Checker integrity

`scripts/kaola-ddd-pack.py` was NOT modified and no path validation was
exempted. Pack citations to retired sources use the checker's pre-existing
foreign-root citation convention — the same form as the long-standing
`KW/scripts/kaola-workflow-validation-runner.js` citation already present in
`docs/ddd/packs/kw-c8-seam.md` — pinned to repo + commit
`a13c6d6f264cf965ca45a07670dbf46cd1eb1e5f` in each file's mirror note and in
`HANDOFF.md`. `scripts/kaola-kw-index.py` changed its docstring only; no
implementation line moved.

## Retained sets (outside the candidate flow)

- `docs/ddd/` seven files — operating contract (entries redirected where they
  pointed at retirees).
- `docs/research/i270-tool-entry-audit-complete.md`,
  `docs/research/i270-tool-entry-audit-final.md` — the two A-line audits.
- `kaola-workflow/archive/**` original workflow evidence (35 manifest
  entries) — untouched.
- P2/P3 uncommitted results, `/tmp` originals — untouched, never pushed.

## Validation after all edits

- `./scripts/validate.sh --suite test-ddd-pack.py` → Ran 29 OK (exit 0),
  re-run after every citation round including the ddd-component restore.
- `./scripts/validate.sh --suite test-issue-277-kw-readonly-index.py` → Ran 5 OK.
- `./scripts/render-skills.py --check` → PASS (working content-stage state,
  not saveable — standing pre-release fact).
- Bridge reference-check stats (read-only,
  `/tmp/kpm-target-reference-check.json`): path-mention-in-mirror 101,
  path-mention-unmigrated 159, external-url 72, relative-resolves-in-mirror
  37, relative-to-unmigrated 5.
