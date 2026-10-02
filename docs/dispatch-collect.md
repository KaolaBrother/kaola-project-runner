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

`$AUTH` is the existing Host heartbeat, the file `snapshot` writes. It is
`{"body":"<state JSON>"}`. The state object's `authorization` holds grants
by exact preset id, optional `elite_cap` (an integer covering Elite and
Expert; the Worker pool is excluded), per-grant `model_switch`, top-level
`model_switches`, `count`, `shared_seat`, and owner `special_requirements`.
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
