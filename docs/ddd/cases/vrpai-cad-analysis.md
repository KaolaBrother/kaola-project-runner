# VRPAI/CAD consumer-bridge analysis case — Q2 (`kaola-ddd/1` phase 6, issue [#285](https://github.com/KaolaBrother/kaola-project-runner/issues/285))

Status: **analysis only.** It writes no consumer file, starts no session, and changes no consumer
bridge, timer, task graph, orchestration or deployment. Every claim about a consumer is cited to
the evidence read below, or marked `[ASSUMPTION]`.

Method: [`docs/research/i279-ddd-method.md`](../../research/i279-ddd-method.md) §4–§5 and the
counter-example rule (§5 "Counter-example", §6b). Pack/context vocabulary:
[`docs/designs/ddd-component-2026-10-07/design.md`](../../designs/ddd-component-2026-10-07/design.md)
revision 2 (`8b3779c9`, §2.1, §5) and the merged phase-1 outputs at `4c30b71d`
([`README.md`](../README.md), [`context-map.md`](../context-map.md),
[`packs/c4-state-retire.md`](../packs/c4-state-retire.md)).

KPR-side source citations (`scripts/…`, `templates/…`, `tests/…`) are at `4c30b71d`, this run's
worktree HEAD. The consumer files are uncommitted working-tree reads; §7 records their sha256 so a
reader can re-check them.

## 1. The question, made precise

Q2 (design §5): "do VRPAI/CAD bridges expose a Published Language?"

The **consumer bridge** is the outer delegation layer that runs in each consumer project — the
"original CAD bridge" of #269, the layers whose sessions
[`docs/operations/kpr-host-on-demand-2026-10-07.md`](../../operations/kpr-host-on-demand-2026-10-07.md):13
verifies. It is *not* the KPR Host's own state (`heartbeat-prompt.json`, C4) and *not* a platform
Runner. The bridge owns `.kaola/delegator-heartbeat.json` and its current-fact record, as stated at
[`templates/kaola-delegator/references/snapshot.md:1-25`](../../../templates/kaola-delegator/references/snapshot.md).

Two different seams answer Q2 differently, and keeping them apart is the crux of the case:

- **S1 — KPR ↔ consumer (the consumer bridge proper).** The bridge's own current-fact record, plus
  the prose/evidence it writes around it.
- **S2 — VRPAI ↔ CAD (a consumer-to-consumer project contract).** A separate cross-project wire
  contract that KPR does not own.

This follows the method's own instruction to name collaboration contracts rather than collapse a
work unit into one boundary (`i279-ddd-method.md` §5).

## 2. S1 — the consumer bridge's own record

**A real, versioned Published Language exists for the bridge record.** Both consumer files declare
`"schema": "kaola-delegator-heartbeat/1"`. KPR owns that schema:
`scripts/kaola-record-contract.py:22` (`DELEGATOR_SCHEMA = "kaola-delegator-heartbeat/1"`), the
bridge's fields are documented at `templates/kaola-delegator/references/snapshot.md:1-25`, and the
record contract is exercised by `tests/contract/test-issue-259-record-contract.py` (delegator
writes at `:324`, `:1457`, `:1531`; read at source, **not executed here** — see §7).

**The schema is closed and enforced, not a loose bag.** Unknown top-level keys are refused
(`scripts/kaola-record-contract.py:1416`), as are unknown `host.`/`project.`/`cadence.`/
`watch.<id>.` keys (`:1440-1442`, `:1452-1453`, `:1463-1465`, `:1537-1545`). `stop` is explicitly
"string or object", and the object form is closed to `{boundary, state, evidence}`
(`:1472-1476`; `DELEGATOR_STOP_KEYS` `:151`). `watch.<id>` admits only listed keys
(`WATCH_KIND` `:119`, `WATCH_KEYS` `:120-123`).

**The observed instances conform, and their per-project differences are schema-allowed.** CAD's
record (`vrpcadcore/.kaola/delegator-heartbeat.json`, rev 6) uses the `stop` object form
(`{boundary, evidence, state}`); VRPAI's record (`vrpai/.kaola/delegator-heartbeat.json`, rev 11)
uses the `stop` string form and a `final_stop` string; both are permitted by the validator. Fields
such as CAD `authorization.known_resource_limits`, VRPAI `authorization.priority` and
`expert_task_grants`, and per-group `special_requirements` are optional schema fields
(`scripts/kaola-record-contract.py:136-161`), not ad-hoc.

**What is genuinely ad-hoc is the semantic payload written around the record.** The CAD relocation
is the clearest case: `vrpcadcore/.kaola/e2s1-d1c7-confirmation-20261006/delivery-log.md:283`
narrates an exclusion change, a stored-grant summary and a "CURRENT STATE" authorization line in
prose ([`docs/cad-recurrence-diagnosis-2026-10-07.md:7`](../../cad-recurrence-diagnosis-2026-10-07.md);
issue #269). The state JSON itself is clean (`{exclusions, grants}` — diagnosis §8), so the
governance meaning exists only outside any versioned field. #269 records the same class again in an
adjacent OWNER RULING paragraph and a later tail-write observation. Free text inside the schema is
deliberate but open: `summary`/`detail`/`source`/`next` are unconstrained strings
(`scripts/kaola-record-contract.py:1548-1551`).

**S1 answer: a published envelope with an ad-hoc semantic layer.** The bridge's record is
KPR-published, versioned, closed and tested — a genuine Published Language, and upstream (KPR) to
the consumer. But the consumer's *meaning* (why authorization changed, what a migration settled) is
carried as free text and prose with no schema or version. The consumer does not expose its own
domain language to KPR; it fills a KPR-shaped record.

## 3. S2 — the VRPAI ↔ CAD cross-project wire contract

- CAD drafted a four-state execution envelope:
  `vrpcadcore/.kaola/crossproj-wire-contract-proposal-20261006/proposal.md`
  (`cad.execution-envelope.proposal.20261006`, §4; runtime receipt §7).
- Astra judged it "AMENDED FOR DOCKING", with review-profile tags
  `cad.execution-envelope.review.20261006` and `cad.runtime-receipt.review.20261006`
  (`vrpcadcore/.kaola/crossproj-wire-contract-confirmation-20261006/decision.md` M1, M8).
- This is a genuine **Published-Language attempt** — shared schema, status vocabulary, presence
  matrix, typed rejection classes, route-bound receipt (`proposal.md` §4–§7).
- It is explicitly **not yet a published language**: "PROPOSAL ONLY" (`proposal.md:7`),
  "documentary review profile, not a registered or negotiated production protocol"
  (`decision.md:39`), and "adoption requires a separately versioned, negotiated interface and
  old/new consumer compatibility evidence" (`decision.md:43`, M1). Its hashes are sealed — the
  proposal's sha256 `56e648a0…` matches the input hash stated in `decision.md:11` — so the
  documents are verifiable, but they confirm a *proposal*, not a live contract.

**S2 answer: a documented Published-Language intent, not a negotiated one, and not KPR's seam.** It
matters to Q2 as evidence that VRPAI and CAD are genuinely separate models with their own
vocabulary — the raw material a context map is for.

## 4. Classification against the DDD criterion

"Published Language" = a documented shared schema with a versioned contract (method §3: "share
contracts, not types"); "ad-hoc" = an unversioned field set.

| Seam | Versioned schema? | Enforced? | Semantic payload | Verdict |
|---|---|---|---|---|
| S1 bridge record | yes, `kaola-delegator-heartbeat/1` | yes (closed-key validator + suite) | partly free text | Published-Language **envelope + ad-hoc semantic layer** |
| S1 bridge prose (delivery-log narration) | no | no | the load-bearing governance content | **ad-hoc field set** |
| S2 VRPAI↔CAD wire contract | yes, but review/proposal-tagged | no (documentary) | typed in the draft | **Published-Language proposal, not negotiated** |
| consumer's own domain model | no | n/a | `[ASSUMPTION]` — not read at source | unverified; do not model from it |

## 5. Would a context pack help here, or only add ceremony? (counter-example rule)

Method §5 "Counter-example": a small consumer config/document fix gets "a direct reviewed edit with
a focused check, not a pack. A context pack adds ceremony, not safety." §6b and
[`README.md`](../README.md) §"Simplified path" repeat it: "The method never applies itself
automatically, at any scale."

Applying it to S1/S2:

1. **The mechanical contract already exists and is enforced.** A pack's `## Inputs and outputs` and
   `## Dependency contracts` would restate `kaola-delegator-heartbeat/1`, the validator's key sets
   and `test-issue-259-record-contract.py`. It adds no invariant the validator does not already
   refuse. Ceremony.
2. **The one observed defect is not a missing artifact.** The CAD relocation is content placed
   outside the typed state (`delivery-log.md:283`; #269). A pack is a Git document that "never
   carries authority" (design §2.1; README "Forbidden keys"). It cannot prevent or repair prose in
   a consumer's working tree; the effective route already exists (the state tool's typed refusals
   plus the owner's current-only rule). A pack would be a third document with no consumer.
3. **KPR-side evidence cannot promote `consumer-*` to `observed`.** The map still records VRPAI/CAD
   as `[ASSUMPTION]` ([`context-map.md`](../context-map.md) §"consumer-*"). Reading the bridge record and the two consumer
   `AGENTS.md` files shows language drift and separate ownership, not a stable, coupled model.
   Method §6b and baseline §7 warn that premature first-cut contexts fragment a small codebase; a
   pack built there would harden a boundary the evidence does not support.
4. **The applicable form is the simplified path.** For the small, real unit here — a governance
   prose cleanup against a schema-shaped record — the method's own lighter option is correct: a
   one-paragraph vocabulary + invariant + expected-change note in the consumer's own AGENTS/docs,
   or no artifact at all. That is what the counter-example prescribes, and it is what the consumer
   already did (`vrpcadcore/AGENTS.md` "Delegator special requirements"; the deliveries in #269).

**Verdict: the pack format does not apply to the VRPAI/CAD consumer bridge.** At S1 it would
duplicate an existing enforced contract; at the relocated-prose gap it carries no authority and
cannot act. The method applies only in its simplified form (or not at all), which is the
counter-example rule working as intended. This is a *local* Q2 resolution: it creates no consumer
pack, changes no S2 proposal, and is not a verdict on whether the consumer projects are well
designed.

## 6. What would change this verdict

- A **negotiated** S2 profile registering `cad.execution-envelope…` as a real versioned contract,
  with old/new compatibility evidence, would create a genuine second Published Language; even then
  a pack belongs at the KPR/KW seam, not inside VRPAI/CAD.
- Repeated, source-verified **change coupling** between KPR and a consumer's own model (not just the
  bridge record) would justify promoting `consumer-*` toward `observed` and re-testing whether a
  pack pays for itself.
- A KPR-side, read-only **bridge-seam pack** of the phase-5 style could be considered if KPR's own
  bridge code — not the consumer — becomes the unit of change. Out of scope here.

## 7. Evidence read (read-only) and hashes

KPR-side, at `4c30b71d` unless noted:

- `docs/designs/ddd-component-2026-10-07/design.md` (revision 2, `8b3779c9`) §2.1, §5, §6
- `docs/ddd/README.md`, `docs/ddd/context-map.md`, `docs/ddd/packs/c4-state-retire.md`
- `docs/research/i279-ddd-method.md` (§4, §5 counter-example, §6b)
- `docs/cad-recurrence-diagnosis-2026-10-07.md`
- issue #269 body and comments: `gh issue view 269 --json body,comments`
- `scripts/kaola-record-contract.py:22, 119-123, 136-166, 1416, 1440-1442, 1452-1453, 1463-1465, 1472-1476, 1537-1551`
- `tests/contract/test-issue-259-record-contract.py` (delegator writes at `:324`, `:1457`, `:1531`)

**Suite execution: not executed here.** `./scripts/validate.sh --suite
test-issue-259-record-contract` selects the suite (`coverage: SUBSET RUN (1 of 88 suites
selected)`) but aborts at the mandatory render-check with exit 1 — the known pre-existing stale
protected Grok Bot pin (`3de9f61a`; `render-skills.py --check` prints 93 identical
`pin: P may differ from 3de9f61afbfa …` lines) — so the selected suite never ran. No direct
contract-suite run was performed: a direct run inherits the caller's `KAOLA_ACP_*` environment
(dispatcher, heartbeat host socket) and could touch live sessions. The record-contract claims above
therefore rest on the source read at `4c30b71d`, not on an executed suite.
- `templates/kaola-delegator/references/snapshot.md:1-25`
- `docs/operations/kpr-host-on-demand-2026-10-07.md:13`
- `docs/research/i270-tool-entry-audit-final.md` Part B (consumer-bridge cross-check)

Consumer-side, read-only (no write, no session); sha256 at read time:

| File | sha256 |
|---|---|
| `vrpai/.kaola/delegator-heartbeat.json` (schema/1, rev 11, `stop` string, `final_stop`) | `3e3b1192021b4b58e59877c173482584b295f54f28d1cf510a7e620f28d16c59` |
| `vrpcadcore/.kaola/delegator-heartbeat.json` (schema/1, rev 6, `stop` object) | `d2a6ac89eb2bf4001ae25f2d6b0dcbcdfacc1ee4808c8db05240b146707e9993` |
| `vrpai/AGENTS.md` | `a5b2be0e6dda21e1579c3b18d3245b4ed12e8c98071b17b2d9db90ca85255393` |
| `vrpcadcore/AGENTS.md` | `67f9ce4f2be3de1903453ffd9c8e12926ff233065cf5bed500da34ce032e3aa0` |
| `vrpcadcore/.kaola/crossproj-wire-contract-proposal-20261006/proposal.md` | `56e648a025c288294639397485d527d8c5ff6ddc4f809eb2ea5f1af9695635ee` |
| `vrpcadcore/.kaola/crossproj-wire-contract-proposal-20261006/evidence.json` | `7a18034ab56aebb30bd4a83de313b8be7982c498c62bc241546a422567610f6a` |
| `vrpcadcore/.kaola/crossproj-wire-contract-confirmation-20261006/decision.md` | `c83971538063848f08afa38b020403afe8ad365473cd04c08682dda368fb2bd6` |
| `vrpcadcore/.kaola/crossproj-wire-contract-confirmation-20261006/evidence.json` | `beaabe40dccaa1aac93e80c59b26f18a0fdeda8111913c341d71bc354d0424eb` |

`[ASSUMPTION]`: the consumer's internal domain model (revision identity, task semantics) is **not**
read at source in this case and stays `[ASSUMPTION]` in the context map. Nothing above claims
otherwise.

## 8. Acceptance check

- Every consumer claim cites the file/hash read, or is `[ASSUMPTION]`: §2–§4, §7.
- The conclusion states whether the pack format applies, simplifies, or does not apply: §5 —
  **does not apply**; the simplified form is the fit.
- No consumer file touched: no write, no session, no timer, orchestration, task-graph or code
  change in VRPAI/CAD or their bridges.
