# Dispatch and collect — consumer guide

Use this when a Host adopts a bounded research, QA, or report plan and runs it
through the installed `kaola-dispatch.py`. Paths below are variables the
operator sets. This guide does not start a session.

```bash
REPO="<canonical git root>"
SKILL_DIR="<loaded kaola-project-runner skill directory>"
SKILLS="<directory containing <platform>-kaola-project-runner>"
ENTRY="$SKILL_DIR/scripts/kaola-dispatch.py"
RUNNER="$SKILLS/<platform>-kaola-project-runner/scripts/kaola-acp.py"
AUTH="$REPO/.kaola/heartbeat-prompt.json"
AVAIL="$REPO/.kaola/dispatch-availability.json"
PLAN="$REPO/.kaola/dispatch-plan.json"
INDEX="$REPO/.kaola/dispatch-index.json"
LIVE="$REPO/.kaola/dispatch-live.json"
```

Do not log in, relogin, or repair credentials. Prompts in a bounded plan do
not edit the repository. The Host exact-stops every session the plan starts.

## 1. Project the candidates

`$AUTH` is the existing Host heartbeat. A legacy file is `{"body":"<state JSON>"}`
written by `snapshot`; a lifecycle-state file (`kaola-heartbeat-prompt/2`, written only by
`state`) is read from its `state.authorization`. The authorization object holds grants
by exact preset/shared group counts. Each grant has `id` or `preset_ids`,
`count`, current `state`, optional owner `special_requirements`, and one
`model_switch` authority. A grouped grant has one count and choice set.
Per-choice restrictions stay on that same grant. Compatibility rows are
computed; they are not independent writers. Choices alone grant no switching.
Missing counts authorize no Elite/Expert admission. Repeated legacy group
counts or switch conflicts require source-based migration or owner recovery.
An Expert grant may also carry `lifetime` (`task`, the default when absent, or
`standing`) and `expires` (an ISO-8601 instant with an offset, `Z` accepted).
Both are read for Expert presets only; Elite and Worker rows ignore them. A
task grant ends with its task; a standing grant holds until the owner revokes
it or it expires, and the tool never infers `standing`. An unknown `lifetime`
is withheld as `lifetime-unreadable`, an unparseable `expires` as
`expiry-unreadable`, and a past one as `expired`; `execute` reports the same
reason as `not-run`. The Host removes a finished task grant; exact-stopping an
Expert session releases the seat and keeps a standing grant.
Do not keep a second durable copy such as `.kaola/dispatch-auth.json`.
`--authorization` also accepts that authorization object directly. An
unreadable body is an error, not an empty grant list. `$AVAIL` lists
`present` and `absent` preset ids from a read-only survey. Every other id
is unknown: it stays in `candidates` and is not a capability, a mismatch,
or a refusal. The plan and the index are run inputs, not another grant file.

```bash
python3 "$ENTRY" project \
  --authorization "$AUTH" \
  --availability "$AVAIL"
```

`capability_summary` lists eligible preset ids. It does not read a capability
out of profile wording and does not copy each profile. Ungranted Expert does
not appear. `candidates` still carry the exact id, Class, catalog profile,
and selection. The tools derive this output from grants, default Worker pool, exclusions,
current holds and availability. Class definitions and preset defaults come
from version-matched catalog/templates; only owner overrides are stored.

## 2. Admit an adopted plan

`scope` is `research`, `qa`, `report`, or `implementation`. `repo` is `$REPO`. Each item has
one `item_id`, exact `preset`, `session`, and `prompt`. Pass `--live` from a
fresh Runner list when a count or shared seat matters. A list row whose
`host_class` is true is the project's Host and is not a worker seat. Legacy plan `seat_cap` is refused with an owner recovery action. A stopped session name is not absent
and needs a new name. A fresh item whose named session is already live, with
the same repo, platform and preset, `identity: verified`, a status receipt
naming that session and holder, and nothing sent yet (`mutation_status:
not_started`) holds that seat: `count` and its shared seat are
judged against the other live rows only, `execute` does not start it again
and sends the first prompt to that holder (`evidence.seat_note`). Any other
live row of the preset still counts against the item, and a refused attempt
(`not-run`, no holder) binds no assignment for a later retry. Planned Host
dispatch runs through `execute`; a direct Runner `start`/`send` is the
standalone, degraded, or same-assignment recovery path.
When `<repo>/.kaola/delegator-heartbeat.json` has schema `kaola-delegator-heartbeat/1`,
that file is the eligibility ceiling for new dispatch.
Host grants may be narrower. They cannot add a preset or enlarge a granted/shared count.
A preset the Delegator revoked, paused, or omitted is `not-run`.
An in-flight or returned row with the same identity stays.
Its evidence names the pending duty: `stop`, `handoff`, `finalize`, or `reclaim`.
A missing Delegator file leaves standalone Host authorization unchanged.
An unreadable ceiling blocks new dispatch and leaves running work in place.
No independently writable aggregate or Worker pool cap is supported.
A stated Delegator `count` applies when the Host grant omits `count`.
One `elite_grants` entry with several `preset_ids` and one `count` is one shared pool.
`lifetime`, `switch_authorization`, and structured `special_requirements` stay on that decision.
A string `special_requirements`, or a `lifetime` outside `task` and `standing`, blocks only those presets.
The row keeps the exact text, the preset names, the Delegator field, and the Host role.
That prose is not written as `revoked` or `excluded`.
`keep_open` and nonempty `wait` or `next` do not keep or finish a task.

```bash
python3 "$RUNNER" list --repo "$REPO" > "$LIVE"
python3 "$ENTRY" execute \
  --plan "$PLAN" --authorization "$AUTH" --availability "$AVAIL" \
  --skills-root "$SKILLS" --index "$INDEX" --live "$LIVE"
```

A `--no-wait` admission is `in-flight` with reason `admitted` and
`acceptance: pending`. That is not a result. `returned` is not expected from
`execute`. Timeout, an unreadable receipt, or a send-time
`holder-instance-mismatch` is `unknown`. Coverage also lists `failed` and
`not-run`. `correlation_only` is true. The Host still accepts.

Optional item `role` is session-identity metadata, not a second Class and
not an admission rule. Omit it, or set JSON `null`, for an ordinary preset
start; a null role is not written onto the index. The current value that
reaches the holder is exact `sideagent`: `execute` passes `--role sideagent`
on that item's Runner `start`. Apart from the legacy alias below, other values stay on the index as raw
metadata. It does not authorize that role, relabel a holder, or refuse an
otherwise valid item. The seat's identity still comes from the Host name,
that explicit sideagent flag, or the preset this start actually selected.
Only the maintenance Sideagent bound in lifecycle state is outside worker
preset `count` (`seat_exempt: true`); a shared seat it uses stays occupied. Any other
`sideagent` item is a counted worker (`evidence.seat_note`). On recovery of a live session, the
entry does not start again and does not change that session's
`session_role`. When a requested `sideagent` is not the persisted role, the
item gains `evidence.role_note` and keeps the status it already had. Legacy
`sidekick` plans remain accepted and correlate unchanged; both spellings denote
Sideagent for recovery. See [session-role compatibility](api.md#session-role).

The same assignment is repo, preset, session, and prompt. A matching
`unknown` prior, including `send-timeout`, whose record is now absent stays
`unknown` / `reconciliation-needed`: no start and no send. An already-admitted
assignment whose record is absent stays `in-flight` or `returned` with reason
`session-gone`; that is not `not-run`. A rejected re-execution keeps that
status and records `evidence.blocked_attempt`. Holder, cursor, evidence, and
result stay only when the assignment matches. `--dry-run` does not write
`--index`. A matching already-admitted item is a plan row `reconciled`; a
new item is `dry-run`. Neither replaces the live index.
A later actual `execute` on the same index keeps an unrelated pending row.
`in-flight` stays, including a disposition already on that row.
`unknown` stays until its status changes. A mirrored acceptance does not drop it.
`returned` and `failed` stay while acceptance is absent, `pending`, `undecided`, or `repair`.
`repair` on those rows is an open repair reference. It is not duty settlement.
The kept bytes are the row on disk, so a collect update stays.
An omitted row uses that locked disk status, not the older baseline status.
A baseline `in-flight` row that the lock finds `returned` and `accepted` does not stay.
A baseline `returned` and `accepted` row that the lock finds `in-flight`, `unknown`, or `repair` stays as those disk bytes.
A `not-run` row does not stay.
A `returned` or `failed` row whose acceptance is `accepted`, `cancelled`, `superseded`, or `handed-off` does not stay.
A per-result disposition does not settle every duty.
That write does not store history and does not retire a row.
It does not decide live close-out or task retirement.

Current-state resolution uses the existing state tools. Active alerts and holds
stay until handled. `state retire --kind alerts|holds --id ID --expect-rev REV
--source ORIGINAL --evidence ORIGINAL` removes the row from stored state.
Host `state update --kind decisions --id ID --expect-rev REV --source ORIGINAL
--set '{"status":"settled","evidence":"ORIGINAL"}'` removes an answered
decision. A Sideagent transcription stays pending until Host adoption.
Delegator `update --expect-revision REV --source ORIGINAL
--set '{"watch":{"ID":null}}'` clears a handled watch row. A sourced
`adopted|settled` transition with original effect evidence also removes it.
Every role view and injected body derives from the current stored collection.
There is no resolved flag, history window or alternative retrospective text slot.

A sourced authorization write or migration removes revoked grants and supported
expired Expert grants. The existing `revoked` ids retain effective stop
restrictions; they are not grant rows. Remove those restrictions only when the
owner changes authorization. Current tasks keep their stop/handoff/reclaim
links. Pause/exclusion restrictions stay while effective. Unreadable expiry or
unknown preset authority is unresolved, not an inferred expiration.

A refusal gives the exact collection/id, revision and existing removal command.
Use original evidence of the handled duty; accepted tasks also need a retrievable
`--cite` and closed dispatch/reclaim links. If the row is absent, do not create
it or put its text elsewhere. Keep unresolved original evidence on the existing
current decision/reconciliation route until the proper type is established.
The Agent decides semantic currentness. The tool checks types, ownership and CAS.
A Host may retire an accepted same-assignment continuation whose initial
index row is `unknown/fingerprint-differs`. Record an accepted per-item task
`dispositions` entry from the original result and custody evidence. Pass a
copy of that original index and fresh `--live` rows to `state retire`, with
`--evidence` and `--cite`. The collected result must show completed/stopped
under the same holder and root; the live row must prove exact reclaim. The
command reports the reconciliation but preserves the unknown index row.
This route refuses missing links, foreign holders and unknown effects. It
does not settle remaining integration or issue lifecycle duties.
A pending recovery input requires its exact scoped checkpoint. Retiring an old
alert does not clear a newer recovery input. Plan `state migrate` before `--write`;
repeat migration preserves pending adoption, grants, duties and current links.

### Owner-required user-facing Elite and Expert seat summary (2026-10-06)

This is a product design requirement for the Delegator's standard USER-FACING heartbeat report. It is for the user to inspect authorization and usage. The Host is NOT required to repeat this summary in every heartbeat or receive another compulsory injected section. Expose the same current facts to the Host on demand when needed for dispatch. This owner correction supersedes the earlier requirement for both role heartbeat reports to always list it. Native timer text remains the canonical entry only.

The user report shows:
- Authorized Elite and Expert preset IDs (`runtime/tier`), counts and applicable grant lifetime.
- Currently occupied seats and their linked tasks.
- Idle, available capacity within each effective grant; held/unavailable/unknown shown separately.

Count a shared seat group once across its permitted tiers. Idle but unreclaimed/reserved sessions are not automatically available. Capacity derives only from effective grant/shared counts and occupancy. Service/quota/fault restrictions remain in their proper roles; there is no separate authorization concurrency cap. Host and Sideagent roles do not consume worker seats. Show no Expert authorization as none, without implying a grant.

Derive the report from existing current authorization and verified occupancy/task links. Do not create a second writable seat table, copy occupancy into Delegator JSON, retain historical seat rows, or inject complete model profiles. Reuse the existing Host dispatch view when needed; no new mandatory Host reading or reporting cycle.

Acceptance: the generated Delegator reporting guidance and its user-facing current view expose the summary with correct shared counts, task links and available/held/unknown distinctions. Reuse applicable existing checks. Host access remains need-driven. No new permission, registry, timer or separate QA phase.

The existing `project --seats` output adds a derived `summary`. The Delegator
`state view --role delegator` and `delegator view` expose it as `seats`.
No seat summary is stored in either current JSON or added to Host injection.
Use existing `--live`, `--index`, `--availability` and `--skills-root` inputs
when an original source requires an explicit locator. Without `--live`, the
existing Runner lists fresh verified holders. Missing task/availability facts
remain unknown; an empty project list does not prove external account or
native QA target capacity. Shared counts use the current grant groups and
existing Delegator grant restrictions. Profiles stay on demand. The same read-only
`project --seats` interface remains available to Host when dispatch needs it.
Update generated Skills through the renderer. Existing state migration keeps
the schemas and pending duty links; installed old views need the accepted
generated tool update before this summary is present. Do not write a seat
summary into an old file as a substitute. No timer text change is needed.

## 3. Collect finished work

Later, without waiting for the slowest branch:

```bash
python3 "$ENTRY" collect --index "$INDEX" --skills-root "$SKILLS"
```

`turn_failed`, `turn_canceled`, and `process_exited` are `failed` before a
still-running check. Still-running requires `turn_active` true. A completed
turn on an already-stopped seat is collected. A completed turn whose repo,
session, holder, and prompt fingerprint match becomes `returned` with reason
`collected`, a short excerpt, and evidence pointers. `acceptance` stays
`pending`. Idle or an ack alone stays `in-flight` and is not acceptance.

## 4. Reclaim

The Host exact-stops each session this plan started, with that platform's
Runner, `$REPO`, and the holder stored on the index item. After an exact
stop that name cannot be reused.

```bash
"$SKILLS/<platform>-kaola-project-runner/scripts/runtime-tmux.sh" stop \
  --repo "$REPO" --session "$SESSION" \
  --expected-holder-instance-id "$HOLDER"
```

Do not stop a session this plan did not start.

### Owner correction: seat counts are the authorization capacity (2026-10-06)

The authorization JSON records which runtime/tier choices or shared groups are granted and how many seats each has. Do not offer an independently writable aggregate concurrency cap such as `elite_cap`, `total_cap`, or an equivalent renamed field. This supersedes earlier language retaining an optional extra aggregate cap.

Compute available capacity from effective individual/shared grant counts and current occupancy. Shared tiers refer to one shared count, not separate additive grants. Derived totals may be shown to the user but are not another stored authorization value. Preserve model-switch scope, grant lifetime and applicable owner restrictions; keep service/quota/fault facts in their existing proper current-state locations, not an invented concurrency grant limit.

Update the existing admission and role/report projections to consume this same authority. Migration must remove obsolete standalone aggregate limits without changing individual/shared grants or interrupting active work; if legacy total-limit intent conflicts with grant counts, make that specific ambiguity actionable rather than silently inventing authority. For this run the owner explicitly revoked the old cap4: current individual/shared grants authorize six possible Elite worker seats.

Use existing affected checks to prove all granted seats can be used, shared counts are respected and excess per-grant admission remains refused. Do not substitute a huge numeric cap, another override list or a free-text capacity policy.


Migration plans remove null or demonstrably redundant known legacy aggregate keys.
A legacy integer must be at least the sum of all explicit shared counts, counted
once, with every count known. Total-only, smaller, malformed or Worker-pool
limits stay actionable blockers. Active work, original duty links and grants stay
unchanged. Resolve from original owner evidence, then use the existing Host
`state update --file FILE --writer host --source ORIGINAL_OWNER_DECISION
--section authorization --expect-revision REV --set '{"elite_cap":null}'` or Delegator
`update --expect-revision REV --set '{"authorization":{"elite_cap":null}}'`
with the exact file, writer and source. Repeat the read-only migration plan
before `--write`. This Host null-only aggregate removal also works on a schema 1
body (use revision 0 when absent); it keeps that schema, grants and duties intact.
For a current file it maps known legacy copies through the existing migration
before section validation. It does not infer missing counts or discard a pause.
Do not move the old limit to a note or renamed field.
A missing Elite/Expert count is `count-unreadable`; source the exact count.
Worker pool defaults and grant-specific restrictions remain unchanged.

### Owner correction: minimal current facts and owner requirements only (2026-10-06)

The owner requires the two routinely read JSONs to allow only concise CURRENT information and effective owner requirements. This is a field/source/lifecycle design constraint, not a word blacklist or an instruction to shorten arbitrary prose. Ordinary project notes and original evidence outside these routinely injected surfaces retain their existing scope.

Personal source review found seven concrete groups to consolidate in this issue:

1. Remove independently writable aggregate concurrency limits, as already specified above. Capacity comes from individual/shared seat grants.
2. Keep model-switch authorization in one canonical grant/group location. Do not independently maintain both per-grant `model_switch` and a second `model_switches` list. Preserve the exact owner-approved choices and switching permission; a list of permitted tiers alone must not invent permission to switch a running seat.
3. Derive eligible/capability preset lists from current grants, the declared default Worker pool, exclusions, scoped holds and actual availability evidence. `capability_summary.presets` must not be a second manually maintained authority or a shortcut that bypasses those sources. Preserve unknown availability honestly.
4. Derive catalog-owned Class definitions, preset Class, profile and default model/effort from the existing version-matched catalog/templates. They remain visible in the appropriate Host view/candidate tool and user report, but are not separately agent-authored routine state. Retain explicit owner overrides as overrides, not copied defaults.
5. A shared grant has one authoritative count and one set of permitted choices/restrictions. Repeated tier rows must not each own a competing copy of the group count. Reuse the existing grouped owner grant representation and generate any compatibility rows mechanically. Do not add another group registry or lose per-choice restrictions.
6. Revoked/expired/completed entries are not authorization history to retain in current JSON. Remove settled entries. A still-effective exclusion of a default-authorized Worker preset remains a current exclusion; a revoked seat still requiring exact stop/handoff retains that CURRENT recovery duty until resolved. Do not erase those duties or silently restore default-pool authorization. A paused/on-hold grant remains authorized but unavailable, with its current reason and reopening route. No duplicate pause state in several independently writable collections.
7. Keep one concise current objective and original source pointers. Do not append issue-by-issue adoption history, earlier decisions, copied Skill rules or completed relay narratives into `project.goal`, `rules`, `requirements_source`, `watch` or equivalent fields. Task details stay with their current task/forge source. Resolved relays and exceptions leave routine state; history remains in the existing original evidence/Git/forge/Runner locations.

Owner requirements: project-specific owner requirements stay in the existing user section of AGENTS.md; current operating settings and grants use their existing typed configuration fields. Keep only a source reference in routine views when the source owns the full text. Do not create a second requirements narrative or let an agent invent requirements. Reflect a new owner correction by replacing superseded current content while preserving unfulfilled duties.

For each field retained, identify its authoritative writer/source and the CURRENT decision, delivery, recovery or consistency need it serves. Computable totals/occupancy/candidates are tool outputs, not independent agent-maintained records. Keep necessary exact identities, concurrency revisions, pending-delivery/maintenance sequence and scoped recovery checkpoints: these cannot safely be reconstructed from a count or current text. A tool-generated compatibility body/cache can remain where an actual consumer requires it; it must be regenerated from the same source and never become a second writable authority. Authorization relay/adoption across Delegator and Host must retain its real ownership boundary.

Apply this through the existing shared field contract, writers, consumer projections and migration. Do not merely hide duplicate stored fields in the user report. Reuse current checks to show a grant/count/switch/exclusion change updates every derived view, resolved records disappear without losing active duties, and old readers cannot silently expand authorization. Keep mixed-version limitations and actionable migration explicit. No new schema framework, state store, periodic full audit or blanket live-file rewrite is authorized by this correction. Preserve the active sole writer and in-flight work.
