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
by exact preset id, optional `elite_cap` (an integer covering Elite and
Expert; the Worker pool is excluded), per-grant `model_switch`, top-level
`model_switches`, `count`, `shared_seat`, and owner `special_requirements`.
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
and selection. The Host writes the short capability paragraph and changes it
only when a grant, profile, or availability fact changes.

## 2. Admit an adopted plan

`scope` is `research`, `qa`, or `report`. `repo` is `$REPO`. Each item has
one `item_id`, exact `preset`, `session`, and `prompt`. Pass `--live` from a
fresh Runner list when a cap or shared seat matters. A list row whose
`host_class` is true is the project's Host and is not a worker seat. Omitting
`seat_cap` does not erase `elite_cap`. A stopped session name is not absent
and needs a new name.

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
Only the maintenance Sideagent bound in lifecycle state is outside `elite_cap` and
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
