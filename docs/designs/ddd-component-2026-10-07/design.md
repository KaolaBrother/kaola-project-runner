# Optional DDD component for KPR — versioned design `kaola-ddd/1`

Status: DESIGN, revision 2 — applies dot root's five technical corrections to revision 1
(`1a2f577e`): #283 dependency, multi-context packs, per-pack/aggregate checker results, uninstall
keeps current documents, advisory-only matching and content ownership. Implementation proceeds per
the phase issues below; a pushed design, issue or commit is not implementation acceptance.

Baseline: [#279](https://github.com/KaolaBrother/kaola-project-runner/issues/279) research and
optional-component contract, accepted by dot root as a documentation-design baseline at
`f4accb11c451d3390f92e77693d3a4e0e903fb89` ([method](../../research/i279-ddd-method.md),
[contract tests](../../research/i279-ddd-contract-tests.md),
[Fable review](../../research/i279-fable-review.md)). That acceptance covers documentation
design only; it does not establish the candidate bounded contexts, consumer adoption or B0.
Authorization: owner, 2026-10-07 (`Sentinel_1a65261dd40881919cf33d1e46067e73`, correcting
`Sentinel_f615def921c4819185007ca896ea3cf2`): formalize the converged DDD design in KPR and track
implementation and records through GitHub issues.

## 1. What this component is

An optional, uninstallable design aid. It gives Agents a small, versioned **context pack** per
work area (vocabulary, inputs/outputs, invariants, dependency contracts, acceptance, expected-change
surface) and a **candidate context map**, both kept as Git engineering documents, plus one optional
checker for the mechanical parts a pilot proves useful.

It is not: a B0 or migration precondition; a permission gate; an automatic task splitter; a
second authorization or history store; a mandate for microservices, separate processes,
databases, event sourcing or CQRS. Agent and Host judgment stays with the Agent and Host. Absence
of the component changes nothing in KPR, Kaola-Workflow or any consumer.

## 2. Artifacts and versions

| Artifact | Path | Version contract | Content owner (responsibility, not a lock) |
|---|---|---|---|
| Component design | this file | `kaola-ddd/1`; a breaking change adds `kaola-ddd/2` beside it | Host, reviewed by dot |
| Candidate context map | `docs/ddd/context-map.md` | front matter `map_schema: kaola-ddd-map/1` | Host |
| Context pack | `docs/ddd/packs/<pack-id>.md` | front matter `pack_schema: kaola-ddd-pack/1` | the pack's named `owner` |
| Checker (optional) | `scripts/kaola-ddd-pack.py` | result `schema: kaola-ddd-check/1`; supports pack schema 1 | implementing issue, then Host |
| Checker suite | `tests/contract/test-ddd-pack.py` | in the `validate.sh` inventory, runnable via `--suite` | implementing issue |

Everything is a versioned Git document or repo script. Nothing is written to `.kaola/`, the
heartbeat state, the dispatch index or any consumer project. History is Git history.

An owner is responsible for keeping that content current and coherent. Ownership is not a lock,
a single-writer mechanism or an approval step: anyone may change these documents through the
project's normal reviewed commits, and no tool enforces who edits them.

### 2.1 Pack format `kaola-ddd-pack/1`

Flat front matter (one `key: value` per line between `---` lines, the same flat style
`parse_flat_yaml` already reads), then fixed level-2 sections.

Required front matter: `pack_schema`, `id`, `status` (`draft|current|retired`), `owner`
(content responsibility, as above), `context_primary` (a candidate name from the context map, or
`unmapped`), `contexts_touched` (comma-separated other candidate contexts the unit crosses, or
`none`), `baseline_commit` (the commit the pack was checked against). Optional:
`related_issues`, `supersedes`.

A work unit may span several candidate contexts. `context_primary` only says where most of the
change lands; every other context the unit crosses is listed in `contexts_touched`, and each
crossed boundary has its own `## Dependency contracts` bullet naming both sides. A cross-context
unit is never collapsed into its primary context, and listing a context never forbids touching
another one (see the expected-change surface).

Phase 1 demonstrates this on a real cross-component unit: retiring a task record. The state tool
refuses `retire-unmet` until the task's dispatch items are closed and its seats are stopped
(`retire_record` in `scripts/kaola-dispatch.py`), so the unit crosses C4 state, C5 dispatch index
and C1 session lifecycle. Its pack lists all three, and each of those dependencies appears as its
own contract bullet with its suite or named gap.

Forbidden front matter: any authorization, grant, seat, writer-permission or approval field.
A pack describes design; it never carries authority. This is the pack schema's explicit
tolerance rule (per-schema, as required by the baseline): unknown *descriptive* keys are an
advisory finding; an authority-bearing key is an error.

Required sections, in order:

1. `## Vocabulary` — exact terms and their meaning in the context(s) the unit touches.
2. `## Inputs and outputs` — typed artifacts read/produced, each with its schema and version.
3. `## Invariants` — the rules that must hold; each names the consistency boundary it protects.
4. `## Dependency contracts` — one bullet per seam: provider, consumer, contract version, and
   `suite: <validate inventory name>` or `suite: none (gap: <what is unverified>)`.
5. `## Acceptance` — observable outcomes, including refusal paths.
6. `## Expected-change surface` — paths/interfaces anticipated. Planning information only;
   legitimate work outside it is coordinated, never refused.
7. `## Evolution` — split/merge/retire signals with the evidence that would trigger them.
8. `## Evidence` — commits, suites and original records the pack was checked against.

### 2.2 Candidate context map `kaola-ddd-map/1`

Lists the §4 candidate groupings from the baseline (session-runtime, orchestration-state,
build/install; KW as a candidate separate model) with the label `candidate` and, per grouping,
the evidence collected so far and the open technical question. A grouping becomes `observed` only
with language, invariant and change-coupling evidence recorded in the map; the map never becomes
a gate.

### 2.3 Checker contract `kaola-ddd-check/1` (implemented only as the pilot justifies)

`scripts/kaola-ddd-pack.py check [--repo ROOT] [PACK ...]` prints one JSON object:
`{"schema": "kaola-ddd-check/1", "result": ..., "packs": [...], "counts": {...}}`.

Every selected pack is evaluated independently and always appears in `packs[]` with its own
`status` and findings; an `unsupported` or `invalid` pack never stops evaluation of the others.

| Per-pack `status` | Meaning |
|---|---|
| `ok` | schema 1 readable, no errors (advisory findings allowed) |
| `invalid` | schema 1, but at least one error finding |
| `unsupported` | `pack_schema` is not a version this checker supports; no further checks on that pack |

Aggregate `result` and exit code, decided after all packs are evaluated, by this precedence:

| Aggregate condition | `result` | Exit |
|---|---|---|
| Bad command line (nothing evaluated) | `usage` | 2 |
| No `docs/ddd/` or no packs | `absent` | 0 |
| At least one pack `invalid` (with or without `unsupported` packs) | `invalid` | 1 |
| No `invalid`, at least one `unsupported` | `unsupported` | 3 |
| All packs `ok` | `ok` | 0 |

So `invalid` + `unsupported` together yield `invalid` / exit 1, with both packs listed and counted;
phase 3 tests this combination. The exit code is for whoever chose to run the checker. Nothing
in KPR core, render, release, Host dispatch or Kaola-Workflow consumes it, so it never blocks core
work.

Candidate checks (each kept only if the pilot finds it caught a real problem or saved real
work): required front matter and sections; forbidden authority keys; referenced repo paths exist
at HEAD; `suite:` names exist in `validate.sh --list`; `baseline_commit` resolves; vocabulary
terms present in the referenced code (advisory); files changed since `baseline_commit` outside the
expected-change surface (advisory report, never a refusal). The checker reads only; it writes
nothing and calls no network.

Vocabulary matches and path-change reports are always advisory, never errors. A clean checker run
shows only that the pack's form and references are consistent. It does not prove that the
vocabulary is used consistently in meaning, or that a dependency contract actually holds; that
evidence comes from the named suites and from Agent/Host review.

The checker is not wired into `render-skills.py --check`, release gates or Host dispatch. Its
suite only tests the checker itself.

## 3. Interfaces with existing KPR contracts

- **Host / Project Runner:** a Host *may* cite a pack path in an assignment as context. The
  assignment, worker choice, acceptance and QA stay Host judgments. No Skill text requires packs.
  Whether a short optional reference is added to `templates/orchestrator/` is decided in phase 4
  from pilot evidence, within existing byte budgets.
- **Kaola-Workflow:** untouched. KW keeps claim, ledger, worktree and finalize. A KW-facing pack
  describes the C8 seam read-only.
- **State tool / dispatch index:** packs never enter `heartbeat-prompt.json`, task records or
  the dispatch index. A task may reference a pack path in its existing free-text fields.
- **Validation:** pack dependency contracts point at existing suites; drift is checked with
  `validate.sh --suite <name>` (existing explicit-subset mechanism). No new gate.

## 4. Failure, degradation and uninstall

- Component absent → `absent`, exit 0; all KPR behaviour unchanged.
- Unsupported pack version → `unsupported` for that pack only; other packs and all core work
  continue.
- A stale pack (code moved on) → advisory findings and an evidence refresh by its owner; never a
  block on unrelated work.
- Default uninstall → remove only the tool and its integrations: `scripts/kaola-ddd-pack.py`, its
  suite and inventory line, and any optional Skill pointer added in phase 4, in one reviewed
  commit. The current `docs/ddd/` engineering documents stay in the working tree. Removing those
  documents is a separate action taken only when the user asks for it; Git history keeping old
  versions is not a reason to delete current documents by default. Phase 3 proves with a test that
  core render and suites pass with the tool removed and the documents still present.
- Simplified path for small or single-context work: a one-paragraph vocabulary + invariants +
  expected-change note, or no pack at all (baseline §6b).

## 5. Technical unknowns, resolved locally

| Question | Resolved where | Never |
|---|---|---|
| Q3: are C4/C5 one language or two? | phase 1 pilot, from source vocabulary and invariants | a gate for any other phase |
| Q1: is KW one context or several? | phase 5, read-only KW source analysis | a precondition for KPR packs or B0 |
| Q2: do VRPAI/CAD bridges expose a Published Language? | phase 6, analysis of existing bridge evidence only | a deployment, orchestration or task-graph change in those projects |

A question that turns out to need a value choice goes to the Owner; otherwise it stays technical.

## 6. Phases and issues

Order follows real dependencies; phases 2–6 can all start after phase 1. Only the checker
integration sub-item of phase 4 waits for phase 3.

| Phase | Issue | Responsibility | Depends on |
|---|---|---|---|
| 1 | #280 | Pack schema v1 + candidate context map + KPR C4 pilot pack incl. a cross-component sample; Q3 local | baseline only |
| 2 | #281 | Contract fixtures only for pilot-pack seams with a measured coverage gap | 1 |
| 3 | #282 | Optional checker `kaola-ddd-pack.py` + suite, only pilot-justified checks; uninstall test | 1 |
| 4 | #283 | Host optional usage path (orchestrator reference decision) + second KPR pack; checker integration sub-item | 1; checker sub-item: 3 |
| 5 | #284 | KW C8 seam pack; Q1 local, KW source read-only | 1 |
| 6 | #285 | VRPAI/CAD analysis case; Q2 local, analysis only | 1 |

Each issue states responsibility, inputs/outputs and version contract, dependencies, acceptance
and required evidence. Completion is judged on the delivered artifacts and evidence, not on the
issue existing.

## 7. Relation to the migration main line

Independent. B0/P1–P5 (#275–#277) neither wait for nor require this component. Where a pack
describes a component that P1 later moves, the pack's owner refreshes its paths and evidence after
that change; the pack never blocks the move.
