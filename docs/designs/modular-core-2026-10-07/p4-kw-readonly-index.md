# P4 contract — Kaola-Workflow bridge as a READ-ONLY original index

Status: P4 contract text (issue #277, P4 half only; P5/B0 out of scope). Implements the migration.md
P4 row and ADR-7/design.md §3 C8. Citations are to Kaola-Workflow source **at commit `16cab12d`**
(the revision read for this contract). KW is read-only; nothing here writes to it, copies its content
into KPR state, or obligates KW to change anything.

## 1. What KPR may index — original record locations

KPR indexes **locators to KW's own original records**: `{kind, path, sha256, schema_or_unknown}` per
record. The index is a pointer table. Content, ownership, semantics, and lifecycle stay with KW; a
stale index entry is repaired by re-reading the original, never by storing a copy.

Paths are relative to the consuming project's **main checkout root** (`main_root`; in the standard
worktree run posture KW resolves it the same way its `ledgerPath`/`resolveMainRoot` helpers do —
Kaola-Workflow `scripts/kaola-workflow-adaptive-schema.js:1653-1658`). A linked worktree is not a
record location: the live ledger and run folders are main-resident.

### Run-scoped records — `kaola-workflow/{project}/` (one `{project}` per claimed run, e.g. `issue-277`)

The authoritative inventory is KW's `KERNEL_ARTIFACT_REGISTRY`
(`scripts/kaola-workflow-adaptive-schema.js:841-897`), machine-checked against
`docs/workflow-state-contract.md:42-64`. The `record`-class rows (the durable originals) plus the two
telemetry `preference` rows are:

| kind | path (under `kaola-workflow/{project}/`) | writer | KW-declared schema/version |
|---|---|---|---|
| `workflow-state` | `workflow-state.md` | script (claim/finalize) | none — markdown blocks `## Project` / `## Claim Identity` / `## Sink` / `## Closure` (`docs/workflow-state-contract.md:243-280`; path rule `kaola-workflow-claim.js:764`) |
| `finalization-summary` | `finalization-summary.md` | agent + script-owned `## Attestation` | none (registry :863-864; `docs/workflow-state-contract.md:123-127`) |
| `chain-receipt` | `.cache/chain-receipt.json` | script (`run-chains`) | none — fields `headSha, workTreeHash, codeTreeHash, validationTestConsumes, startedAt, completedAt, source, scope, preamble, chains` (`kaola-workflow-run-chains.js:1261-1274`; path :841-846) |
| `final-validation-record` | `.cache/final-validation.md` | agent evidence + `record` verb owns three column-0 fields | none — column-0 fields `verdict`, `validation_command`, `validated_candidate_hash` (`kaola-workflow-validation-runner.js:1183-1188`; parser `adaptive-schema.js:314,341-342`) |
| `validation-vector` | `.cache/validation-vectors/*.json` | script (`validation-runner --output`) | `schema_version: 1`, `kind: 'validation_vector'` (`validation-runner.js:15,654-655`; registry :857-858) |
| `selection-record` | `.cache/origin/selection-record.json` | script (claim) | none (registry :855-856; claim.js:876) |
| `run-gaps` | `.cache/run-gaps.json` | script (gap sweep) | none (registry :853-854) |
| `sink-receipt` | `.cache/sink-receipt.json` | script (sink) | none — ordered step journal (registry :867-868; `kaola-workflow-sink-merge.js:1569-1606`) |
| `sink-fallback` | `.cache/sink-fallback.json` | script (sink) | none (registry :869-870) |
| `outcome-log` | `.cache/outcome-log.jsonl` | script | per-line `v: 1` (`adaptive-schema.js:665,702,789`; preference ruling :879-880) |
| `node-timings` | `.cache/node-timings.jsonl` | script | none (:877-878) |

### Coordination record — the mission ledger

| kind | path | KW-declared schema/version |
|---|---|---|
| `mission-ledger` (live) | `kaola-workflow/.ledger/issue-<N>.jsonl` — **main checkout only, gitignored, never in a worktree** | none — shape-enforced: one JSON object/line, keys exactly `n,name,details,status`, statuses `todo|in-flight|done|failed|blocked` (`adaptive-schema.js:64,67-68`; path :1653-1658; shape :1664-1682) |
| `mission-ledger-archive` | `kaola-workflow/archive/{project}/mission-ledger.jsonl` — moved there at archive (`kaola-workflow-claim.js:3045-3049`; `ARCHIVED_LEDGER_FILE` adaptive-schema.js:66) | same shape |

`N` is `workflow-state.md`'s `issue_number` (a bundle uses its primary issue). Presence under
`.ledger/` means a live run (`docs/workflow-state-contract.md:105-118`).

### Archive records — `kaola-workflow/archive/{project}/`

Archive copies the whole run folder byte-for-byte (`verifyArchiveComplete`,
`docs/workflow-state-contract.md:184-221`): the same relative paths as the live table, plus
`mission-ledger.jsonl` and a `## Closure` block in `workflow-state.md`. The archive band is never a
write target (`kaola-workflow-validation-runner.js:1297-1358`).

### Optional roadmap

`kaola-workflow/.roadmap/_rules.md` — the one optional local roadmap file
(`docs/workflow-state-contract.md:102-104`). No schema.

## 2. Reference-only rule

- An index entry is exactly `{kind, path, sha256, schema_or_unknown, status}` — the artifact's own
  content hash, never extracted content. Digest *values* inside records (e.g. `codeTreeHash`,
  `candidate_digest`, `validated_candidate_hash`) are KW-internal bindings and are **not** lifted
  into KPR state.
- KPR never writes under `kaola-workflow/` — no mirror, no cache, no annotation file, no ledger or
  state edits (KW single-writer rules at `docs/workflow-state-contract.md:79-94` stay intact).
- `schema_or_unknown` reports the version KW declares **in the artifact** (`validation_vector` →
  `validation_vector/1`; `outcome-log` → `outcome-log/1`). Most KW records carry no version field;
  their shape is contract-enforced, not versioned — those report `unknown`, and an older KW layout
  reads as `unsupported`, never as a guess.
- The index is regenerable on demand; it is not a KPR-owned copy of run state and must never be used
  to satisfy a KW gate, drive a KW transition, or answer "is the work done".

## 3. Typed results — `present` | `absent` | `unsupported`

| status | meaning |
|---|---|
| `present` | path exists as a regular readable file; `sha256` populated; `schema_or_unknown` populated with the declared version or `unknown` |
| `absent` | the named record path does not exist — a normal mid-run state for terminal records (`finalization-summary`, `sink-receipt`, archive copies), reported, never guessed at |
| `unsupported` | the path exists but the reader cannot stand behind it: non-regular file, unreadable, JSON kind that fails to parse, a ledger line violating the exact-keys/status shape (`adaptive-schema.js:1664-1682`), or a declared `schema_version`/`v` the reader does not support (`reason` names the class) |

`absent` and `unsupported` are distinct: absent means "no original here"; unsupported means "an
original exists that this reader version does not safely understand". Neither is synthesized into a
`present` entry with guessed fields.

## 4. The two named digest views — explicit reconciliation

KW already ships **two different functions** that each claim to hash "the code-relevant landable
tree". They live in different modules, answer different questions, and produce different values on
the same tree. This contract names them as **two views of one landable-tree concept**, not one
digest with two spellings.

### 4.1 What each view is FOR

- **`finalize-gate` view — `computeCodeTreeHash(root, project, testConsumedExtra, opts)`**
  (`adaptive-schema.js:1124-1143`). The freshness binding the finalize gate recomputes: stamped as
  `codeTreeHash` in `.cache/chain-receipt.json` by the producer (`run-chains.js:1178-1180,1264`) and
  compared against a recomputed value at `adaptive-schema.js:1389-1397`; stamped as
  `validated_candidate_hash` in `.cache/final-validation.md` by the `record` verb
  (`validation-runner.js:1160-1164`) and compared at `adaptive-schema.js:1455-1468`. A mismatch is
  `chains_stale` / `final_validation_stale`. Returns `null` on any git failure → the gate fails
  closed. Comment at :1113-1123: "THE PRODUCER AND THE GATE MUST BOTH REACH THIS ONE FUNCTION".
- **`landable-record` view — `computeLandableTreeDigest(repoRoot, options)`**
  (`validation-runner.js:554-599`). The candidate binding **recorded inside** `validation_vector`
  receipts: the vector's `candidate_digest` (:657) plus per-run `pre_candidate_digest` /
  `post_candidate_digest` (:891-892), checked run-to-run by `reduceRuns` as `candidate_mutation`
  (:636), and durably written via `--output` (:1538-1542) — conventionally under
  `.cache/validation-vectors/`. It binds a validation receipt to the tree it measured; nothing
  recomputes it at a gate.

### 4.2 What each covers

Both intend the same tree: seed a throwaway index from `HEAD` (`read-tree HEAD`; the record view
explicitly falls back to `--empty` on a zero-commit repo, :565-566), layer `git add -A` on top
(tracked changes incl. tracked-but-gitignored + untracked-non-ignored; genuinely ignored untracked
paths stay out — :1084-1093, :561-573), `write-tree`, enumerate `ls-tree -r`, drop the
validation-invisible band, hash the survivors. The band is: repo-root `README.md`/`CHANGELOG.md`/
`docs/**` plus the whole `kaola-workflow/` run-state tree, **minus** test-consumed prose which stays
code-visible, with `docs/api.md`-class lists applied only to self-host repos (`detectSelfHostNpm`).

### 4.3 Where they actually differ (measured, not stylistic)

| axis | `finalize-gate` (`adaptive-schema.js`) | `landable-record` (`validation-runner.js`) |
|---|---|---|
| module / consumers | producer `run-chains.js:1180` + gate `adaptive-schema.js:1389-1397,1455-1468` | producer `validation-runner.js:842-844` + receipt internals only |
| `ls-tree` form | `ls-tree -r <sha>` text lines, `\r` stripped (:1135-1136) — git **C-quotes** special/non-ASCII paths | `ls-tree -r -z` raw NUL records, no quoting (:574-589) |
| filter signature | `isValidationInvisible(p, project, extra, opts)` (:1038-1045) — takes `project` | `isValidationInvisible(relative, extra, opts)` (:531-543) — no `project` |
| band constants | `SELF_HOST_TEST_CONSUMED` (:994-999) + `isBookkeepingPath` (:971-983) + `testConsumes` (:1025-1032) | `TEST_CONSUMED_PATHS` (:37-43) — same five paths **duplicated**, not shared |
| record preimage | visible lines JS-string-sorted, sha256 over `lines.join('\n')` (:1141-1142) | surviving raw records `Buffer.compare`-sorted, sha256 over `record + NUL` each (:590-592) |
| failure | `null` on any git error (:1132-1135) | `null` (:560,567-575) |
| realpath | none | `fs.realpathSync(repoRoot)` first (:560) |

Consequences already proven in KW's own suite: the two functions yield different 64-hex values over
one tree — `record` mode documents that storing the record-view value in `final-validation.md`
"buys `final_validation_stale`" (`validation-runner.js:1166-1172`), and test T8e asserts they never
coincide (`scripts/test-finalize-door.js:1154-1167`).

Beyond encoding, the band checks can genuinely disagree: the gate view's `ls-tree` output arrives
C-quoted, so a non-ASCII path under an inert dir (e.g. `docs/日本語.md`) reaches the invisibility
predicate as a quoted token like `"docs/\346\227\245\346\234\254\350\252\236.md"`, matches no
inert-dir prefix, and stays **in** the gate-view hash — while the record view, seeing raw `-z`
bytes, excludes it. The `project` parameter is a second asymmetry: the gate view's bookkeeping band
can be narrowed to the active run folder before its `kaola-workflow/` catch-all, the record view's
cannot.

### 4.4 Why aligning field names does NOT close the hazard

- The values differ **by construction** even on identical trees (NUL-suffixed raw records vs
  `\n`-joined stripped text). Renaming `codeTreeHash` → `candidate_digest` (or vice versa) merges
  labels, not algorithms — a reader can no longer tell which view bound the artifact, and the wrong
  comparison still yields `stale` on a green tree or, worse, passes a digest computed under the
  wrong band.
- The coverage bands are **two copies** of the inert/test-consumed lists in two files
  (`SELF_HOST_TEST_CONSUMED` vs `TEST_CONSUMED_PATHS`), already maintained by convention, not by
  code. Any future edit to one silently drifts the views further; field-name alignment hides this
  because both fields still read as "the landable digest".
- The signatures differ semantically: `project` scoping and C-quoted vs raw path handling mean the
  same field name can cover a different path set. A shared field name without a named view says
  *which field to read* but not *which algorithm produced it*.

**What closes it (per ADR-7 scope note): one contract with two NAMED views.** Artifacts declare the
view their digest fields belong to (`finalize-gate` vs `landable-record`) — this contract's reader
already annotates indexed records with that view — and cross-repo generated validators assert the
two implementations cover the **same path set** for a shared fixture (set-equality, not
digest-equality: the digest values differ by design). Encoding convergence (one preimage format) is
an optional later simplification for KW to take or leave; P4 does not require it and KPR does not
prescribe it. Cross-repo same-schema validators are a later sub-stage, not part of this text.

## 5. Boundary

- Read-only, reference-only, no writes anywhere, no network. Nothing in this contract is a
  precondition for P5/B0; it is parallel per the issue body and migration.md.
- KPR never forces its heartbeat schema on KW; there is no cross-repo sync. The index answers "what
  KW originals exist here and which bytes are they", nothing more.
- The reader ships as a standalone repo script (`scripts/kaola-kw-index.py`) in this stage — not
  wired into `skills/`, `templates/`, render, or Host dispatch.
