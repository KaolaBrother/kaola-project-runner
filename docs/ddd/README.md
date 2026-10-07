# Optional DDD context packs (`kaola-ddd/1`)

Status: phase 1 of [#280](https://github.com/KaolaBrother/kaola-project-runner/issues/280)
delivered these documents. Phase 3 of [#282](https://github.com/KaolaBrother/kaola-project-runner/issues/282)
adds the optional checker `scripts/kaola-ddd-pack.py`. Phase 4
([#283](https://github.com/KaolaBrother/kaola-project-runner/issues/283)) adds a second pack and the
Host usage decision. Design:
[`docs/designs/ddd-component-2026-10-07/design.md`](../designs/ddd-component-2026-10-07/design.md)
revision 2 at `8b3779c9c9c76e03f6794b5bf5cf6ffb76bd27c0`. Method baseline:
[`docs/research/i279-ddd-method.md`](../research/i279-ddd-method.md) (§4, §5, §6b), accepted as a
documentation-design baseline at `f4accb11`.

This directory is an optional design aid. It is not a B0 or migration precondition, a permission
gate, a task splitter, an authorization or history store, or a mandate for services, processes or
databases. `render-skills.py --check`, release gates, the state tool, the dispatch index, Host
prompts and consumer projects do not read it. `validate.sh` runs `test-ddd-pack.py` only as that
suite's own test of the checker. A pack carries no authority and is not a gate. If you delete this
directory, KPR, Kaola-Workflow and consumers keep working exactly as before. The default uninstall
below does not delete it.

| File | Version contract | Role |
|---|---|---|
| [`context-map.md`](context-map.md) | `map_schema: kaola-ddd-map/1` | Candidate groupings with their evidence and open questions |
| [`packs/<pack-id>.md`](packs/) | `pack_schema: kaola-ddd-pack/1` | One context pack per work unit |
| [`packs/c4-state-retire.md`](packs/c4-state-retire.md) | `kaola-ddd-pack/1` | Pilot pack: C4 state "retire a record" |
| [`packs/c1-exact-stop.md`](packs/c1-exact-stop.md) | `kaola-ddd-pack/1` | Second pack: C1 lifecycle "exact-stop a seat" |
| [`host-usage-decision.md`](host-usage-decision.md) | — | Phase 4 decision on an optional Skill pointer (none added) |
| [`../../scripts/kaola-ddd-pack.py`](../../scripts/kaola-ddd-pack.py) | result `schema: kaola-ddd-check/1` | Optional read-only checker |

## Pack schema `kaola-ddd-pack/1`

A pack is one Markdown file at `docs/ddd/packs/<id>.md`. It has flat front matter and then
eight fixed level-2 sections.

### Front matter

Front matter is placed between two `---` lines at the top of the file. Each line is `key: value`,
with no nesting, lists or multi-line values. This is the same flat style that `parse_flat_yaml`
reads (`scripts/kaola-dispatch.py:145-161`). That function has no `---` fence handling. It skips
only lines that start with whitespace or `#`, so a body line such as `- suite: x` or
`Status: phase 1` would be read as a key. A reader must cut the front matter out of the file
first.

| Key | Required | Value |
|---|---|---|
| `pack_schema` | yes | `kaola-ddd-pack/1` |
| `id` | yes | the file stem, e.g. `c4-state-retire` |
| `status` | yes | `draft`, `current` or `retired` |
| `owner` | yes | who is responsible for keeping the content current, e.g. `host`. This is content responsibility only: it is not a lock, not a single-writer rule and not an approval step. Anyone may change a pack through normal reviewed commits, and no tool enforces who edits it. |
| `context_primary` | yes | where most of the change lands: `<grouping>/<component>` from `context-map.md`, or `unmapped` |
| `contexts_touched` | yes | comma-separated other `<grouping>/<component>` boundaries the unit crosses, or `none` |
| `baseline_commit` | yes | the full commit the pack's claims were checked against |
| `related_issues` | no | comma-separated issue numbers |
| `supersedes` | no | the id of a pack this one replaces |

**Forbidden keys.** A pack must never carry authority. That rules out any authorization, grant,
seat, writer-permission or approval field, under any spelling: `authorization`, `grant`,
`grants`, `seat`, `seats`, `writer`, `writers`, `permission`, `permissions`, `approval`,
`approved_by`, `cap`, `*_cap`, and similar.

**Cross-context units.** A work unit may span several candidate contexts. Every boundary in
`contexts_touched` gets its own `## Dependency contracts` bullet, naming both sides. Two rules
follow:

- A cross-context unit is never collapsed into `context_primary`.
- Listing a context never forbids touching another one.

Components that share one language still count as separate boundaries when they have separate
stores, locks or schemas. An example is C4/C5 (see the Q3 result in the map). The pilot pack is
the sample: it lists C4, C5 and C1.

**Tolerance rule.** This rule belongs to this schema only. An unknown *descriptive* key is an
advisory finding. An authority-bearing key is an error. A pack that describes a writer, for
example "the Host is the single writer of `heartbeat-prompt.json`", says so in the body, citing
the code. It never says so in the front matter.

### Sections (all required, in this order)

1. `## Vocabulary` — the exact terms the unit touches and what each means in that context, with
   the code location that defines it. Do not coin synonyms. A term that means something
   different in another context (for example "retire" in C1 vs C4) is listed with both meanings.
2. `## Inputs and outputs` — the typed artifacts the unit reads and produces, each with its schema
   and version.
3. `## Invariants` — the rules that must hold. Each rule names the consistency boundary it
   protects.
4. `## Dependency contracts` — one bullet per seam, naming the provider, the consumer and the
   contract version. Each bullet ends with exactly one of:
   - `suite: <name>` — `<name>` is a line of `./scripts/validate.sh --list`, and that suite
     actually asserts this seam. You find out by reading the suite, not by matching its name.
   - `suite: none (gap: <exactly what is unverified>)`
5. `## Acceptance` — the observable outcomes, including refusal paths.
6. `## Expected-change surface` — the paths and interfaces you expect to change. This is planning
   information only: legitimate work outside it is coordinated with the owner, never refused.
7. `## Evolution` — the signals for splitting, merging or retiring the unit, and the evidence that
   would trigger each one.
8. `## Evidence` — the commits, suites and original records the pack was checked against.

Every claim cites `path:line` or a suite name, at the stated `baseline_commit`.

## How to write a pack

1. Pick one bounded, verifiable work unit. A work unit is not an aggregate (baseline §5). It may
   touch several consistency boundaries.
2. Read the current source for that unit. Record the full HEAD commit as `baseline_commit`.
3. Fill in the vocabulary from the identifiers and refusal codes the code actually uses. Where a
   word in an issue or design has more than one meaning in the code, list each meaning separately.
4. List the invariants. For each one, cite the line that enforces it, or say that nothing
   enforces it.
5. For each seam, read the candidate suites and find the assertion that exercises it. If a suite
   only reaches the seam through a shared helper, say so. If nothing asserts it, write
   `suite: none (gap: …)` and describe precisely what is unverified. Never mark a seam as
   covered just because a suite's name sounds right.
6. Check every cited path and suite name (commands below). Commit the pack in a normal reviewed
   commit.
7. When the code changes, the pack's owner refreshes the citations and `baseline_commit`. A stale
   pack is an advisory finding for its owner. It never blocks unrelated work.

**What checks can and cannot show.** All vocabulary matches and path or change reports are
advisory, by hand or by any future checker. A clean check shows only that a pack's form and
references are consistent: required keys and sections present, cited paths and suite names
existing. It does **not** prove that the vocabulary is used consistently in meaning, or that a
dependency contract actually holds. That evidence comes only from:

- reading the cited source;
- the named suites' assertions;
- Agent/Host review.

Verification used for this phase (no new gate; plain commands):

```bash
./scripts/validate.sh --list                      # suite names
git rev-parse --verify <baseline_commit>^{commit} # baseline resolves
test -e <path>                                    # each cited path
./scripts/validate.sh --suite <name>              # optional: re-run a cited suite on drift
```

## Simplified path

For small or single-context work there are two lighter options (baseline §6b, design §4):

- write one paragraph — vocabulary, invariants and expected change — in the issue or the
  assignment; or
- write no pack at all.

The counter-example in baseline §5 applies. A one-line consumer config or documentation fix gets a
direct reviewed edit with a focused check, not a pack. The method never applies itself
automatically, at any scale.

## Checker (`kaola-ddd-check/1`)

`scripts/kaola-ddd-pack.py` reads packs. It writes nothing and calls no network. Nothing in
`render-skills.py`, a release gate, `scripts/kaola-dispatch.py` or Kaola-Workflow calls it.

```bash
./scripts/kaola-ddd-pack.py check
./scripts/kaola-ddd-pack.py check --repo . docs/ddd/packs/c4-state-retire.md
```

With no pack paths, `check` reads `docs/ddd/packs/*.md`. If `docs/ddd/` is missing, or that
directory has no packs, the result is `absent` and the exit code is 0. Every selected pack is
evaluated on its own. One pack's result does not stop the others. Every invocation prints one
JSON object. A bad command line is `result: usage`, exit 2, and evaluates nothing.

```json
{"schema": "kaola-ddd-check/1", "result": "ok", "note": "A clean run proves form and references only, not meaning or contract satisfaction.", "counts": {"ok": 0, "invalid": 0, "unsupported": 0}, "packs": []}
```

The `note` is always that sentence. Advisory findings are allowed when `result` is `ok`.

| Condition | `result` | Exit |
|---|---|---|
| Bad command line (nothing evaluated) | `usage` | 2 |
| No `docs/ddd/` or no packs | `absent` | 0 |
| At least one pack `invalid` (with or without `unsupported`) | `invalid` | 1 |
| No `invalid`, at least one `unsupported` | `unsupported` | 3 |
| All packs `ok` | `ok` | 0 |

Per-pack `status` is `ok` (schema 1, no errors), `invalid` (schema 1 with at least one error),
or `unsupported` (`pack_schema` is not `kaola-ddd-pack/1`, and that pack is not checked further).

### Kept checks

The phase-1 pilot justified these checks:

- Forbidden authority keys in front matter are errors. A key is forbidden when, after lowercasing
  and reading `-` as `_`, it is or contains `authorization`, `grant`, `grants`, `seat`, `seats`,
  `writer`, `writers`, `permission`, `permissions`, `approval`, `approved_by` or `cap`, or it
  ends with `_cap`.
- Required front matter and the eight level-2 sections, in order, including `context_primary`
  and `contexts_touched`.
- Each `suite: <name>` is a name `./scripts/validate.sh --list` prints. The checker reads the
  `shell_suites` and `python_suites_all` arrays that `--list` prints. It does not run
  `validate.sh`. `suite: none (gap: ...)` is the gap form and is not an inventory name.
- Cited repo paths exist. Those are explicit `scripts/`, `tests/`, `docs/`, `templates/` and
  `platforms/` files, plus a path introduced by `` `Alias` means `path` ``.
- `baseline_commit` is a 7 to 40 hex commit that `git rev-parse --verify <commit>^{commit}`
  resolves in the local repository.

An unknown descriptive key is an advisory finding. It leaves the pack `ok` when nothing else
is an error.

### Checks not automated

Each dropped candidate has one reason, from the pilot findings below:

- Vocabulary terms present in referenced code: the pilot's presence check passed every term; the four real findings were differences of meaning.
- Files changed since `baseline_commit` outside the expected-change surface: the pilot had no code change after `baseline_commit`, so this check is unmeasured.
- Advisory `path:line` symbol drift: citations are prose aliases and line ranges, with no grammar that binds a symbol to those lines, so a simple scan cannot reliably detect the off-by-a-few-lines edits the pilot fixed by reading.

## Uninstall

**Default uninstall removes only the tool and its integrations**, in one reviewed commit:

- `scripts/kaola-ddd-pack.py`;
- `tests/contract/test-ddd-pack.py`;
- the `"test-ddd-pack.py"` lines in `scripts/validate.sh` (`python_suites_all` and the one lane array);
- any optional Skill pointer added in phase 4.

Phase 3 added the checker, its suite, and the inventory lines named above, so those are what
this uninstall removes. Phase 1 adds none of the other integrations. Phase 4 adds no Skill
pointer ([decision](host-usage-decision.md)), so there is nothing to remove under `templates/`
or `skills/`. For phase 1 and phase 4, that part of the default uninstall is a no-op.

**The current `docs/ddd/` documents stay in the working tree.** Deleting them is a separate action,
taken only when the user asks for it. The fact that Git history keeps old versions is not a
reason to delete current documents by default.

`tests/contract/test-ddd-pack.py` performs that removal on a copy: `docs/ddd` stays byte for byte,
and the unrelated suite `test-issue-271-dispatch-help.py` still passes. `render-skills.py` does
not call the checker. A Host assignment or task that cites a pack path as free text keeps working.

## Pilot findings (phase 1, C4 "retire a record")

These findings come from writing [`packs/c4-state-retire.md`](packs/c4-state-retire.md) by hand
against `8b3779c9`. For each design §2.3 candidate check, the table records whether doing the
check by hand on this pack caught a real problem or saved real work. This decides what phase 3
(#282) automates. "No value" is reported as such.

| Candidate check (design §2.3) | Caught a real problem? | Saved real work? | Phase 3 signal |
|---|---|---|---|
| Required front matter and sections | No. Written by the author; nothing was missing. The one real format event was a design change (`context_candidate` replaced by `context_primary` + `contexts_touched`) during the pilot. A checker would only have flagged the old key after the fact. | No | Low. Cheap. Useful mainly when the schema changes. |
| Forbidden authority keys | No. The pack has none. One temptation appeared: "the Host is the single writer of the state file" is a fact *about the code*. It belongs in `## Invariants` (I1), which is where it went. | No | No measured value. It is still the only check that guards the component's own boundary (no authority in packs). Keep it only if a checker is built at all. |
| Referenced repo paths exist at HEAD | No. Every cited path exists (see verification). | No. Path existence never failed. **Line drift did occur:** 13 of my own `path:line` ranges were off by 1–3 lines on first writing and were corrected by re-reading. A path-only check would have passed all of them. | Path existence: no value observed. A `path:line` → symbol drift check (not in the design list) would have caught real errors. It is advisory, and it still cannot judge whether the cited line supports the claim. |
| `suite:` names exist in `validate.sh --list` | No. All cited suites are listed. | No | No value as a coverage signal. Every real coverage finding came from **reading** the suites. For example, `test-issue-244-dispatch.py` is an issue input, but it contains no `state retire` call; a name check passes it. A clean name check must never be reported as "seam covered". |
| `baseline_commit` resolves | No | Slight. During the pilot the design moved `1a2f577e` → `8b3779c9`. Checking `git diff --stat` between the two (design file only) showed that every source citation carried over unchanged. That saved re-reading the source, but the work was the diff, not the "resolves" check. | Low. Trivial. |
| Vocabulary terms present in code (advisory) | **The presence check: no.** Every term is present, so it would have passed. **Reading the meanings: yes, four real findings** (details below). | Yes. Without these, the baseline example would have planned the wrong expected-change surface (no C5 write) and the wrong invariant wording. | **Not automatable beyond advisory presence.** All four came from semantic reading. The value stays with Host/Agent review, as design §2.3 revision 2 says. |
| Changed files outside the expected-change surface since `baseline_commit` (advisory) | Not exercised. No code changed after `baseline_commit`. | No evidence | Unmeasured. Re-evaluate when the pack ages (phase 4). |

The four findings from reading meanings were:

- three corrections to the accepted baseline example (§5):
  1. "monotonic `rev`" merges three counters: per-record `rev`, file `revision` and
     `host_revision`;
  2. "C5 writes are not expected" is false: `state retire --index` mirrors the verdict into C5
     rows;
  3. "no tombstone" needs precision: a `retired` stone is still kept while it names seats/dispatch
     and no receiver, i.e. a pending reclaim, which is a current duty;
- one word collision: "retire" also names C1's session-record move (`kaola-acp.py:2194`), with a
  different meaning.

**Seams with no suite (input to phase 2, #281).** There are nine gaps; the exact text is in the
pack's [`## Dependency contracts`](packs/c4-state-retire.md#dependency-contracts).

| Gap | Seam | What is unverified | Measured at `8b3779c9` |
|---|---|---|---|
| G1 | C4 schema → retire | The `legacy-format` refusal for a v1 file (asserted for no command) | read |
| G2 | C4 retire | The `record-missing` and `evidence-required` refusal codes | read |
| G3 | C4 → Git | Retiring an accepted task with no `--cite` → `cite-required` | read |
| G4 | C4 stones | Pending-reclaim stones (`seats`/`dispatch`, no `handed_to`): the keep and `record-retired` branches | read |
| G5 | C5 → C4 | Retire's index read checks neither `schema` nor `repo` | **probe: foreign index → `written`** |
| G6 | C5 → C4 | A status that is absent or unknown counts as closed (deny-list `:4913` vs allow-list `:5184`) | **probe: no status / `"inflight"` → `written`** |
| G7 | C5 producer → C4 | No real `execute`/`collect` index is fed into retire | read |
| G8 | C4 → C5 mirror | The mirror failure after the state write landed (`index_mirror.error`) | read |
| G9 | C1 producer → C4 | No real `kaola-acp.py list` output is fed into retire. The documented `$LIVE` source (`list --repo`) omits stopped seats. | **probe: default list → `retire-unmet`; `--include-dead` → `written`** |

G5, G6 and G9 are measured behaviour, not only missing tests. They may be defects; whether they
are is a Host judgment. This phase changes no code, template or suite.

**Summary for phase 3.** None of the seven candidate checks, done mechanically, caught a problem
in this pilot. What paid off was not mechanical:

- semantic reading of the source (four findings);
- reading the suites to measure seam coverage (nine gaps);
- two small probes (G5, G6, G9).

The evidence supports at most a small checker: forbidden authority keys, front-matter/section
shape (including the new keys), `suite:`/path/baseline existence and, worth evaluating,
advisory `path:line` symbol drift. A checker must label all of these as form/reference checks
that never prove meaning or coverage. Building no checker is equally consistent with this
evidence; #282 decides.

Phase 3 ([#282](https://github.com/KaolaBrother/kaola-project-runner/issues/282)) built that
small checker. The kept checks, the three dropped reasons, usage and the default uninstall are
in the Checker and Uninstall sections above. Symbol drift was not kept: the citations have no
grammar that binds a symbol to a line.
