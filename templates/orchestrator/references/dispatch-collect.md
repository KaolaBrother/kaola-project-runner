# Dispatch and collect

`scripts/kaola-dispatch.py` admits an adopted finite plan through existing
Runners and correlates receipts. It doesn't choose workers, grant
seats, accept, or stop seats. Index is correlation only, not a
ledger. Trivial start, count, and stop do not call a model.

## Routine context

Keep goals, progress, the three Class meanings, and `capability_summary`.
At a dispatch decision, run `project`.

`project` reads authorization plus manifests (`platforms/` or a Runner's
`scripts/platform.yaml`). Availability JSON lists `present` and `absent`;
every other id is `unknown` and is not a mismatch or a refusal.
`capability_summary` lists eligible preset ids and does not read profile
wording or copy profiles. Exact id, Class, profile, and selection stay on
`candidates`. The Host's short capability paragraph changes only when a
grant, profile, or availability fact changes. Unknown availability is
`availability unknown`, not a capability. `absent` is withheld. Ungranted
Expert does not appear.

Input keys: `grants[]` (`id`, `state`, `count`, `shared_seat`,
`special_requirements`, `model_switch`), `exclusions`, `paused`, `revoked`,
`elite_cap`, `model_switches`. `rows` is not grants. `state` is `granted`,
`paused`, `revoked`, or `excluded`. Historical `N live` is granted. Any other
state is `state-unreadable` for the Host. Elite and Expert need `granted`.

## Sidekick

Default `zcode/default`, or an owner-selected authorized available
alternative. One short-lived assignment may draft,
synthesize, or do other explicitly scoped light work; the Host then
exact-stops it. It does not start other workers, grant permission, accept
the product, or run a scheduling loop. A simple exact selection skips it.

## Commands

```bash
python3 "$SKILL_DIR/scripts/kaola-dispatch.py" project \
  --authorization "$AUTH" --availability "$AVAIL"
python3 "$SKILL_DIR/scripts/kaola-dispatch.py" execute \
  --plan "$PLAN" --authorization "$AUTH" --availability "$AVAIL" \
  --skills-root "$SKILLS" --prior-index "$PRIOR" --index "$INDEX" --live "$LIVE"
python3 "$SKILL_DIR/scripts/kaola-dispatch.py" collect \
  --index "$INDEX" --skills-root "$SKILLS"
python3 "$SKILL_DIR/scripts/kaola-dispatch.py" snapshot \
  --state "$STATE" --out "$PROJECT/.kaola/heartbeat-prompt.json"
```

`$SKILLS` contains `<platform>-kaola-project-runner`. `$LIVE` is
`{ "rows": [...] }` from `kaola-acp.py list --repo`, or omitted. If a cap,
count, or shared seat is in force and live facts cannot be read, those items
are `not-run` / `occupancy-unknown`.

## execute

`scope` is `research`, `qa`, or `report`. `repo` is absolute and realpathed
before comparison. Each item has `item_id`, `preset`, `session`, and
`prompt`, plus optional `overrides`, `resources`, `expected_holder_instance_id`,
`shared_seat`, and `role`.

`--tier` comes from the preset. `--model` and `--effort` are passed only for
an explicit owner or item value. Owner `special_requirements` win. A
conflicting item override is `not-run` / `override-conflicts-owner`. A model
that differs from the catalog model is `not-run` / `model-switch-unauthorized`
unless the owner named it, `model_switch` is true, or `model_switches` lists
the preset. A bare model does not inherit preset effort. `task_scope` is
copied onto the item. Other override keys are `override-unapplied`.

Shared seat, write path, `desktop: true`, account, or port: all conflicting
items are `not-run` / `resource-conflict`. A string `writes` value is
`resources-unreadable`. A non-string `ports` entry says `ports must be strings`.
A live shared seat is `shared-occupied`.

`elite_cap` limits Elite and Expert. Plan `seat_cap` may only tighten it.
Worker-pool items do not consume it. `count` limits that preset. A Runner
list row has no preset or class. A row whose `host_class` is true is this
project's Host and is not a worker seat. Any other row counts only when its
preset is on the row, on an identity-bound index item (repo, session,
holder, and preset), or on that session's status/start applied model and
effort. Class comes from that preset. A platform name is not a Class. An
unresolved row stays unknown: it is not an Elite seat, and a cap, count, or
shared seat that depends on it is `occupancy-unknown` unless the resolved
rows already fill that limit. A shared seat is occupied when the resolved
preset's grant names it, or the row itself carries `shared_seat`. That label
is not a platform name.

The same assignment is repo, preset, session, and prompt; admission state is
separate. Already admitted (identity, holder, `in-flight`/`returned`) is
reconciled before capacity: no new seat, no second send. An absent record
stays that status with reason `session-gone`, not `not-run`; the binding
stays for the Host. Matching `unknown`, including `send-timeout`, with an
absent record stays `unknown` / `reconciliation-needed`: no start, no send.
Same `--index` is the prior. Capacity applies only to a new start. A session
name alone is not the assignment. Holder, cursor, evidence, and result stay
only for this identity. A rejected re-execution keeps that status; this
attempt is `evidence.blocked_attempt`, not `not-run`. `--dry-run` writes no
index at all. Admitted plan row is `reconciled`; a new row is `dry-run`.

Each ready new item calls `status`, then `start` only when the session is absent
(`no-session`), then `send --no-wait`. A stopped record, including one with
`residual_pids: []`, is not absent: that session name cannot be reused and
needs a new name. The start holder is stored and sent as
`--expected-holder-instance-id` when known. An expected holder whose session
is absent is `not-run` and is not started. Duplicate session names are
`not-run`. Admission is `in-flight` / `admitted`, `acceptance: pending`, not
a result. Timeout or an unreadable receipt is `unknown`, not `failed`. A
send-time `holder-instance-mismatch` is `unknown`. Exit 0
with unknown mutation and outcome is `unknown`. The index is replaced after
each item. `prompt_sha256` is `sha256:` plus hex.

Applied fields come from `config_application`, including nested
`start_evidence`. `resolved_*` is not applied evidence. `applied: false` and
`model_verified: false` are not reported as applied and do not send
(`selection-mismatch`). A missing application is `unknown` and does not block
send. A mapped slot matches when `requested_id` is the catalog id. An
advertised difference, including a non-string value, is `unknown` and does
not set `comparison` to `mismatch`. A provider-qualified id matches on the
tail after `\`. A slash stays part of the id.

A live record binds this assignment only when repo, session, preset, holder,
and `prompt_sha256` all match. Fingerprint equality alone is
`assignment-unbound` and does not send. A bound in-progress or completed row
is not replayed. `mutation_status` `not_started` may take the first send.
A matching `unknown` prior may not.

Coverage is `in-flight`, `returned`, `failed`, `unknown`, `not-run`.
Coverage is not acceptance. Another scope, or `mutation: true`, is `not-run`
and calls no Runner.

## collect

One `status` per `in-flight` item reads `turn_active`, `turn_outcome`,
`stop_reason` (including `record.last_prompt`), and the fingerprint against
the current prompt. `turn_failed`, `turn_canceled`, and `process_exited` are
`failed` before the in-progress check. `still-running` requires `turn_active`
true; `mutation_status` `in_progress` alone does not. A completed turn on an
already-stopped seat is collected, not `no-result`. A completed match then
gets one `capture --since` the dispatch cursor and becomes `returned` /
`collected`. `acceptance` stays `pending`. Idle with no completed turn stays
`in-flight` / `no-result`. An identity mismatch is `unknown`.

## snapshot

`snapshot` replaces `--out` atomically. The file's only key is `body`, a
string that parses as the state object. No schema key is added.

## Outside this entry

No production-mutation fan-out, pipeline, or automatic choose-and-dispatch.
No second scheduler. Quota stays in [quota-packages.md](quota-packages.md).
Never log in, relogin, or repair credentials.
