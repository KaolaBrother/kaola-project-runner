# Dispatch and collect

`scripts/kaola-dispatch.py` executes an adopted finite plan and correlates
Runner receipts. Host chooses, grants, accepts and stops. Index is correlation,
not a ledger; trivial transport/counting calls no model.

## Routine context

Keep goals, progress, Class meanings and `capability_summary`.
At a relevant claim, dispatch, adoption or acceptance decision, fetch only
fresh facts that can affect it. Reuse state read in this turn; a Runner return
uses its correlated receipt, not a full heartbeat reload. Update changed
Host facts/duties without a write/read-back loop. Detailed profiles stay on demand.

`project` reads authorization plus manifests (`platforms/` or a Runner's
`scripts/platform.yaml`). Availability JSON lists `present` and `absent`;
every other id is `unknown` and is not a mismatch or a refusal.
`capability_summary` lists eligible preset ids and does not read profile
wording or copy profiles. Exact id, Class, profile, and selection stay on
`candidates`. The Host's short capability paragraph changes only when a
grant, profile, or availability fact changes. Unknown availability is no capability. `absent` is withheld. Ungranted
Expert does not appear.

Input keys: `grants[]` (`id`, `state`, `count`, `shared_seat`,
`special_requirements`, `model_switch`), `exclusions`, `paused`, `revoked`,
`elite_cap`, `model_switches`. `rows` is not grants. `state` is `granted`,
`paused`, `revoked`, or `excluded`. Historical `N live` is granted. Any other
state is `state-unreadable` for the Host. Elite and Expert need `granted`.

## Sidekick

Sidekick is optional and short-lived: default `zcode/default`, or an
owner-selected authorized available alternative. For nontrivial allocation,
Host gives outcome, abilities, constraints and expected artifacts. Using
current candidates/profiles, Sidekick proposes useful count, exact presets,
bounded assignments and ownership. Host adopts/adjusts against current grants
and pending changes, then executes. A simple exact dispatch skips it. Do not
invent parallel work to fill seats or force model balance.

It may reconcile conflicts, check omissions, synthesize or do
explicitly scoped light work. It does not start other workers, dispatch, grant or accept; writes neither
control JSON and runs no scheduler. Keep useful conclusions, sources
and output files; Host records adopted decisions. Native history stays native,
with the only recovery anchor preserved. Exact-stop a finished Sidekick.

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
  truncation/unknown reasons remain visible. Missing ranges are uncertainty.
- `snapshot --state "$STATE" --out "$PROJECT/.kaola/heartbeat-prompt.json"`.

`$SKILLS` contains `<platform>-kaola-project-runner`. `$LIVE` is `{ "rows": [...] }`
from `kaola-acp.py list --repo`, or omitted for a fresh list. A supplied file is
a source observation, not proof of freshness. Compact reads store no state or
acceptance verdict. If live facts needed by a count/cap/shared seat cannot be
read, execute reports `not-run` / `occupancy-unknown`.

## execute

`scope` is `research`, `qa`, or `report`. `repo` is absolute and realpathed
before comparison. Each item has `item_id`, `preset`, `session`, and
`prompt`, plus optional `overrides`, `resources`, `expected_holder_instance_id`,
`shared_seat`, and `role`.

Preset supplies `--tier`. Model/effort overrides require explicit owner/item
values; owner `special_requirements` win (`override-conflicts-owner` otherwise).
Noncatalog model needs owner choice, `model_switch` or `model_switches`, else
`model-switch-unauthorized`. A bare model inherits no effort. `task_scope`
only narrows; other keys are `override-unapplied`.

Shared seat, write path, `desktop: true`, account, or port: all conflicting
items are `not-run` / `resource-conflict`. Unreadable resources are reported.
A live shared seat is `shared-occupied`.

`elite_cap` limits Elite+Expert; plan `seat_cap` only tightens it. Worker pool
is outside it; `count` limits that preset. Host rows (`host_class: true`) are
not worker seats. Resolve a row's preset from the row, identity-bound index
(repo/session/holder/preset), or applied status/start model+effort. Platform
name is no Class. Unresolved occupancy is unknown where a cap/count/shared
seat depends on it, unless known rows already fill that limit. Shared labels
come from the row or resolved preset's grant, never from a platform name.

Assignment identity is repo, preset, session and prompt; admission is separate.
Reconcile an identity/holder-bound `in-flight`/`returned` item before capacity
(no second seat/send). Missing session stays `session-gone` with its binding.
Matching unknown with an absent record stays `reconciliation-needed`, no
start/send. Same `--index` is prior. Capacity applies only to new starts.
Rejected re-execution preserves correlation and uses `evidence.blocked_attempt`.
`--dry-run` writes no index: admitted rows are `reconciled`, new rows `dry-run`.

New items call `status`, `start` only for absent (`no-session`), then
`send --no-wait`. Stopped records need a new name, even with no residual PIDs. The start holder is stored and sent as
`--expected-holder-instance-id` when known. An expected holder whose session
is absent is `not-run` and is not started. Duplicate session names are
`not-run`. Admission is `in-flight` / `admitted`, `acceptance: pending`, not
a result. Timeout or an unreadable receipt is `unknown`, not `failed`. Send-time holder mismatch or unknown mutation/outcome stays unknown,
even at exit 0. Index updates per item; hashes use `sha256:` plus hex.

Applied selection comes from `config_application` (including nested
`start_evidence`), never `resolved_*`. Explicit unapplied/unverified fields
do not send (`selection-mismatch`); missing application is unknown and does
not block. Mapped `requested_id` matches catalog id. Advertised differences
remain unknown, not applied mismatches. Provider qualification matches after
`\`; a slash stays part of the id.

A live assignment binds only matching repo, session, preset, holder and prompt
hash; fingerprint alone is `assignment-unbound`. Bound active/completed work
is never replayed. `not_started` may take its first send; matching unknown may not.

Coverage is `in-flight`, `returned`, `failed`, `unknown`, `not-run`.
Coverage is not acceptance. Another scope, or `mutation: true`, is `not-run`
and calls no Runner.

## collect

For each in-flight item, status supplies active/outcome/stop (including
`record.last_prompt`) and prompt fingerprint. `turn_failed`, `turn_canceled`, and `process_exited` are
`failed` before the in-progress check. `still-running` requires `turn_active`
true; `mutation_status` `in_progress` alone does not. A completed match, even stopped, gets `capture --since` its dispatch cursor:
`returned` / `collected`, acceptance pending. No completed idle result stays `in-flight` / `no-result`; identity mismatch is unknown.

## snapshot

`snapshot` atomically replaces `--out` with only `body`, a string parsing
as the state object.

## Outside this entry

No production-mutation fan-out, pipeline, or automatic choose-and-dispatch.
No second scheduler. Quota stays in [quota-packages.md](quota-packages.md).
Never log in, relogin, or repair credentials.
