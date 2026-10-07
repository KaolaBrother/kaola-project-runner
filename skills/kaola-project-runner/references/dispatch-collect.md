# Dispatch and collect

`scripts/kaola-dispatch.py` executes an adopted plan; it does not choose workers,
grant, accept or stop seats. Host allocates within authorization. The Delegator file is the ceiling. Index is correlation, not a ledger.

Gathering, research, counterexamples or critique, edge exploration,
verification: spread useful parallel items as evenly as reasonably possible across
fitting Worker-Class presets, not one habitual runtime. Fit, authority and real
limits first; no invented work or fixed quota ([Choosing](worker-profiles.md)).

## Routine context

Keep current goals and source pointers. Derive Class/defaults from matched
catalog/templates. Fetch decision-relevant fresh facts; reuse current-turn
reads and correlated Runner receipts. Update changed duties without read-back.

`project` reads authorization plus manifests (`platforms/` or a Runner's
`scripts/platform.yaml`). Availability JSON lists `present` and `absent`;
every other id is `unknown`: no capability, mismatch or refusal.
`capability_summary` lists eligible preset ids, copies no profile text.
Exact id, Class, profile and selection stay on `candidates`. `absent` is
withheld; ungranted Expert does not appear.

Input: `grants[]` (`id` or grouped `preset_ids`, `state`, exact `count`,
`special_requirements`, `model_switch`, `lifetime`, `expires`), `exclusions`,
account quotas. One group owns one count, choices, switch authority;
compatibility rows are generated. A per-choice restriction map retains owner overrides. `rows` is not grants. `state`: `granted`,
`paused`, `revoked` or `excluded`. Legacy `N live` is granted; other tokens are `state-unreadable`. Elite and Expert need `granted` and an exact count; a missing count is `count-unreadable`.

## Who dispatches

Host selects counts, presets, assignments by fit and authority. Unknown is not absent; PATH is not adapter availability. Split
at independent context/resource boundaries; keep coupled code/tests together.

The Sideagent (default `zcode/default`, or an owner-selected authorized available
alternative) reconciles state in batches ([lifecycle-state.md](lifecycle-state.md)):
conflicts, omissions, or explicitly scoped light work the Host assigned. It
writes and allocates no assignment, grants and accepts nothing and runs no
scheduler. A parallel helper is a counted worker item; it does not start other workers.

## Commands and compact reads

Commands (`python3 "$SKILL_DIR/scripts/kaola-dispatch.py"`; $SKILL_DIR =
this Skill's dir):

- `project --authorization "$AUTH" [--availability "$AVAIL"]`: candidates.
- `project --seats --repo "$PROJECT" --authorization "$AUTH" [--live "$LIVE"]
[--index "$INDEX"] [--skills-root "$SKILLS"]`: observed seats against supplied
grants, count/shared occupancy and unknown reasons. No authority verdict.
- `execute --plan "$PLAN" --authorization "$AUTH" --skills-root "$SKILLS"
[--availability "$AVAIL"] [--prior-index "$PRIOR"] [--index "$INDEX"] [--live "$LIVE"]`.
- `collect --index "$INDEX" --skills-root "$SKILLS"`: update correlation.
- Add `--item <exact item_id>` to `collect` for a read-only turn view.
Identity/cursor-bound outcome, permissions/failures survive the 480-char excerpt. Full native capture reads rotated logs; source/as-of, raw pointers and truncation reasons are visible. Missing ranges are uncertainty.
- `snapshot --state "$STATE" --out "$PROJECT/.kaola/heartbeat-prompt.json"`: atomically replaces
`--out` with only `body`; a v2 `--out` is `state-managed`: use `state`.

`$SKILLS`: sibling Runner root.
`--plan --authorization --availability --live --index --prior-index` take
JSON **file** paths; `--set`: inline JSON or `@path`. `$LIVE`:
`{"rows":[...]}` from `list --repo --include-dead` (omit=fresh);
supplied rows not fresh proof. Unreadable occupancy: `not-run`/`occupancy-unknown`.

## execute

`scope` is `research`, `qa`, `report` or `implementation`
([sideagent-node.md](sideagent-node.md)). `repo` is absolute, realpathed.
Each item has `item_id`, `preset`, `session` and `prompt`, plus optional `overrides`, `resources`, `expected_holder_instance_id`,
`shared_seat`, `role`, `task_id`, `output` and `requires` (stated
`class`/`presets`; unmet: `not-run` / `requirement-unmet`).

Preset supplies `--tier`. Model/effort overrides need explicit owner/item
values; owner `special_requirements` win (`override-conflicts-owner`).
Noncatalog model needs owner choice, grant/group `model_switch`, else
`model-switch-unauthorized`. A bare model inherits no effort. `task_scope`
only narrows; other keys are `override-unapplied`.

Grouped `preset_ids` share one exact `count`. Legacy repeated `shared_seat`
rows need consistent count/switch migration; missing counts grant no seats.
Each item uses a seat. Full pools return `shared-occupied`; other conflicts are `resource-conflict`.

`count` and shared counts are the capacity. Totals derive from them and current
occupancy; no standalone authorization or plan cap is accepted. Legacy limits
need source-based owner reconciliation before removal; a redundant integer
no smaller than all explicit counts can migrate safely. Worker pool is unchanged. Host rows (`host_class: true`) and the bound Sideagent (`seat_exempt`) are not worker seats. Resolve a row's preset from the row, identity-bound index
(repo/session/holder/preset), or applied start/status model+effort. Platform
name is no Class. Unresolved occupancy is unknown where a count/shared
seat depends on it, unless known rows already fill the limit. Shared labels
come from the row or resolved preset's grant, never from a platform name.

Assignment identity is repo, preset, session and prompt; admission is separate.
Reconcile an identity/holder-bound `in-flight`/`returned` item first (no
second seat/send). Missing session stays `session-gone` with its binding.
Matching unknown with an absent record stays `reconciliation-needed`, no
start/send. Same `--index` is prior.
Rejected re-execution keeps correlation, adds `evidence.blocked_attempt`.
`--dry-run` writes no index (admitted: `reconciled`, new: `dry-run`).

New items call `status`, `start` only for absent (`no-session`), then
`send --no-wait`. An item's own verified, unprompted live seat is its count, not a new start. Stopped records need a new name, even with no residual PIDs. The start holder is stored and sent as
`--expected-holder-instance-id` when known. An expected holder whose session
is absent is `not-run`, not started. Duplicate session names are
`not-run`. Admission is `in-flight` / `admitted`, `acceptance: pending`, not
a result. Timeout or an unreadable receipt is `unknown`, not `failed`. Send-time
holder mismatch or unknown mutation/outcome stays unknown even at exit 0. Index updates per item, locked and merged by field; hashes are `sha256:` hex.

Applied selection uses `config_application` (also nested `start_evidence`),
never `resolved_*`. Explicit `applied: false` or `model_verified: false` does
not send (`selection-mismatch`). Missing application, unknown observations and
advertised differences stay unknown and do not block send. Mapped
`requested_id` matches catalog id. Provider qualification matches after `\\`;
a slash is part of the id.

A live assignment binds matching repo, session, preset, holder, prompt
hash; fingerprint alone is `assignment-unbound`. Bound active/completed work
is never replayed. `not_started` may take its first send; matching unknown may not.

Coverage (`in-flight`, `returned`, `failed`, `unknown`, `not-run`) is not
acceptance. Another scope, or `mutation: true` outside `implementation`,
is `not-run`; no Runner call.

## collect

Per in-flight item, status supplies active/outcome/stop (incl.
`record.last_prompt`) and fingerprint. `turn_failed`, `turn_canceled` and `process_exited` are
`failed` before the in-progress check. `still-running` requires `turn_active`
true; `mutation_status` `in_progress` alone does not. A completed match, even stopped, gets `capture --since` its dispatch cursor:
`returned` / `collected`, acceptance pending, plus `locator` and `gaps`. No
completed idle result stays `in-flight` /
`no-result`; identity mismatch is unknown.

Quota: [quota-packages.md](quota-packages.md).
