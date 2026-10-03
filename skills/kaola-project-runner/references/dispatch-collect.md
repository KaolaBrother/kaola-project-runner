# Dispatch and collect

`scripts/kaola-dispatch.py` executes an adopted plan; it does not choose workers,
grant, accept or stop seats. Host allocates within authorization. Index is
correlation, not a ledger; trivial calls use no model.

## Routine context

Keep goals, progress, Class meanings and `capability_summary`.
At a relevant claim, dispatch, adoption or acceptance decision, fetch only
fresh facts that can affect it. Reuse state read this turn; a Runner return
uses its correlated receipt, not a heartbeat reload. Update changed
Host facts/duties without write/read-back.

`project` reads authorization plus manifests (`platforms/` or a Runner's
`scripts/platform.yaml`). Availability JSON lists `present` and `absent`;
every other id is `unknown`, not a mismatch or refusal.
`capability_summary` lists eligible preset ids and copies no profile
text. Exact id, Class, profile and selection stay on
`candidates`. The Host's capability paragraph changes only when a
grant, profile or availability fact changes. Unknown availability is no capability. `absent` is withheld; ungranted
Expert does not appear.

Input: `grants[]` (`id`, `state`, `count`, `shared_seat`,
`special_requirements`, `model_switch`), `exclusions`, `paused`, `revoked`,
`elite_cap`, `model_switches`. `rows` is not grants. `state`: `granted`,
`paused`, `revoked` or `excluded`. Historical `N live` is granted; any other
state is `state-unreadable`. Elite and Expert need `granted`.

## Sideagent

Sideagent is optional and short-lived: default `zcode/default`, or an
owner-selected authorized available alternative. For nontrivial allocation,
Host gives outcome, abilities, constraints, expected artifacts, the authorized
current candidate projection or its locator, and the known relevant facts.
Sideagent reuses them, queries only missing or stale evidence (unknown is not
absent; PATH is not adapter availability), and proposes useful count, exact
presets, bounded assignments and ownership by profile and task fit. Host adopts/adjusts against current grants
and pending changes, then executes. A simple exact dispatch skips it. Do not
invent parallel work to fill seats or force model balance.

It may reconcile conflicts, check omissions, synthesize or do
explicitly scoped light work. It does not start other workers, dispatch, grant or accept, write control
JSON, or run a scheduler. Keep useful conclusions, sources
and outputs; Host records adopted decisions. Native history stays native;
keep the only recovery anchor. Exact-stop finished Sideagent.

## Commands and compact reads

Call `python3 "$SKILL_DIR/scripts/kaola-dispatch.py"` with:

- `project --authorization "$AUTH" [--availability "$AVAIL"]`: candidates.
- `project --seats --repo "$PROJECT" --authorization "$AUTH" [--live "$LIVE"]
  [--index "$INDEX"] [--skills-root "$SKILLS"]`: observed seats against supplied
  grants, count/cap/shared occupancy and unknown reasons. No authority verdict.
- `execute --plan "$PLAN" --authorization "$AUTH" --skills-root "$SKILLS"
  [--availability "$AVAIL"] [--prior-index "$PRIOR"] [--index "$INDEX"] [--live "$LIVE"]`.
- `collect --index "$INDEX" --skills-root "$SKILLS"`: update correlation.
- Add `--item <exact item_id>` to `collect` for a read-only turn view: index
  stays untouched. Identity/cursor-bound outcome, pending/historical permissions
  and structured failures survive the 480-character reply excerpt. Full native
  capture reads rotated logs; source/as-of, raw event-log/Runner pointers and
  truncation/unknown reasons stay visible. Missing ranges are uncertainty.
- `snapshot --state "$STATE" --out "$PROJECT/.kaola/heartbeat-prompt.json"`.

`$SKILLS` contains `<platform>-kaola-project-runner`. `$LIVE` is `{ "rows": [...] }`
from `kaola-acp.py list --repo`, or omitted for a fresh list. A supplied file is
an observation, not proof of freshness. Compact reads store no state or
acceptance verdict. If live facts a count/cap/shared seat needs cannot be
read, execute reports `not-run` / `occupancy-unknown`.

## execute

`scope` is `research`, `qa` or `report`. `repo` is absolute and realpathed
before comparison. Each item has `item_id`, `preset`, `session` and
`prompt`, plus optional `overrides`, `resources`, `expected_holder_instance_id`,
`shared_seat` and `role`.

Preset supplies `--tier`. Model/effort overrides require explicit owner/item
values; owner `special_requirements` win (`override-conflicts-owner` otherwise).
Noncatalog model needs owner choice, `model_switch` or `model_switches`, else
`model-switch-unauthorized`. A bare model inherits no effort. `task_scope`
only narrows; other keys are `override-unapplied`.

Shared seat, write path, `desktop: true`, account or port: conflicting
items are `not-run` / `resource-conflict`. Unreadable resources are reported.
A live shared seat is `shared-occupied`.

`elite_cap` limits Elite+Expert; plan `seat_cap` only tightens it. Worker pool
is outside it; `count` limits that preset. Host rows (`host_class: true`) are not worker seats. Resolve a row's preset from the row, identity-bound index
(repo/session/holder/preset), or applied start/status model+effort. Platform
name is no Class. Unresolved occupancy is unknown where a cap/count/shared
seat depends on it, unless known rows already fill the limit. Shared labels
come from the row or resolved preset's grant, never from a platform name.

Assignment identity is repo, preset, session and prompt; admission is separate.
Reconcile an identity/holder-bound `in-flight`/`returned` item before capacity
(no second seat/send). Missing session stays `session-gone` with its binding.
Matching unknown with an absent record stays `reconciliation-needed`, no
start/send. Same `--index` is prior. Capacity applies only to new starts.
Rejected re-execution keeps correlation in `evidence.blocked_attempt`.
`--dry-run` writes no index: admitted rows are `reconciled`, new ones `dry-run`.

New items call `status`, `start` only for absent (`no-session`), then
`send --no-wait`. Stopped records need a new name, even with no residual PIDs. The start holder is stored and sent as
`--expected-holder-instance-id` when known. An expected holder whose session
is absent is `not-run`, not started. Duplicate session names are
`not-run`. Admission is `in-flight` / `admitted`, `acceptance: pending`, not
a result. Timeout or an unreadable receipt is `unknown`, not `failed`. Send-time holder mismatch or unknown mutation/outcome stays unknown
even at exit 0. Index updates per item; hashes are `sha256:` hex.

Applied selection uses `config_application` (also nested `start_evidence`),
never `resolved_*`. Explicit `applied: false` or `model_verified: false` does
not send (`selection-mismatch`). Missing application, unknown observations and
advertised differences stay unknown and do not block send. Mapped
`requested_id` matches catalog id. Provider qualification matches after `\\`;
a slash stays part of the id.

A live assignment binds only matching repo, session, preset, holder and prompt
hash; fingerprint alone is `assignment-unbound`. Bound active/completed work
is never replayed. `not_started` may take its first send; matching unknown may not.

Coverage (`in-flight`, `returned`, `failed`, `unknown`, `not-run`)
is not acceptance. Another scope or `mutation: true` is `not-run`;
no Runner call.

## collect

For each in-flight item, status supplies active/outcome/stop (including
`record.last_prompt`) and prompt fingerprint. `turn_failed`, `turn_canceled` and `process_exited` are
`failed` before the in-progress check. `still-running` requires `turn_active`
true; `mutation_status` `in_progress` alone does not. A completed match, even stopped, gets `capture --since` its dispatch cursor:
`returned` / `collected`, acceptance pending. No completed idle result stays `in-flight` / `no-result`; identity mismatch is unknown.

## snapshot

`snapshot` atomically replaces `--out` with only `body`, a string that parses
as the state object.

## Outside this entry

No production-mutation fan-out, pipeline or automatic choose-and-dispatch.
No second scheduler. Quota stays in [quota-packages.md](quota-packages.md).
Never log in, relogin or repair credentials.
