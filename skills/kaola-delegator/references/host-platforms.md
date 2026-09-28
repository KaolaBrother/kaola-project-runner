# Host platforms

Every shipped platform can be the project's one Host (#119, #122, #126). Take
the row of the Host platform the user chose; a live Host keeps its own
platform. The Host platform is its own fact, apart from `authorized_platforms`:
being the Host authorizes no worker seat, and a worker authorization chooses no
Host. Rows are rendered from `platforms/<id>.yaml`; an empty entry cannot be a
Host (`host-entry-unsupported`).

| Platform (`<runtime_name>`) | Runner Skill (`$RUNNER` dir) | `host_skill_entry` (first line) | Host name |
|---|---|---|---|
| claude-code (`Claude Code`) | `claude-code-kaola-project-runner` | `/kaola-project-runner` | `claude-code-<PROJECT_CODE>-orchestrator-<purpose>` |
| codex (`Codex CLI`) | `codex-kaola-project-runner` | `$kaola-project-runner` | `codex-<PROJECT_CODE>-orchestrator-<purpose>` |
| cursor-cli (`Cursor CLI`) | `cursor-cli-kaola-project-runner` | `/kaola-project-runner` | `cursor-cli-<PROJECT_CODE>-orchestrator-<purpose>` |
| devin (`Devin CLI`) | `devin-kaola-project-runner` | `/kaola-project-runner` | `devin-<PROJECT_CODE>-orchestrator-<purpose>` |
| droid (`Droid`) | `droid-kaola-project-runner` | `/kaola-project-runner` | `droid-<PROJECT_CODE>-orchestrator-<purpose>` |
| dsh (`dsh`) | `dsh-kaola-project-runner` | `/kaola-project-runner` | `dsh-<PROJECT_CODE>-orchestrator-<purpose>` |
| grok (`Grok CLI`) | `grok-kaola-project-runner` | `/kaola-project-runner` | `grok-<PROJECT_CODE>-orchestrator-<purpose>` |
| kimi-cli (`Kimi CLI`) | `kimi-cli-kaola-project-runner` | `/skill:kaola-project-runner ` | `kimi-cli-<PROJECT_CODE>-orchestrator-<purpose>` |
| opencode (`OpenCode`) | `opencode-kaola-project-runner` | `/kaola-project-runner` | `opencode-<PROJECT_CODE>-orchestrator-<purpose>` |
| zcode (`ZCode`) | `zcode-kaola-project-runner` | `/kaola-project-runner` | `zcode-<PROJECT_CODE>-orchestrator-<purpose>` |

- **kimi-cli**: the entry ends with one space before the newline; keep it.
- **codex**: `$kaola-project-runner` is a `$` Skill mention; a shell passes
  it single-quoted, or pipes stdin without `--text`.
- **Host model**: a zcode Host start pins GLM 5.3 at effort `max` (a Runner
  requirement, #108) and reports it in that start receipt's `host_selection`;
  `host-model-*` refuses. Other platforms resolve `--tier`/`--model`/`--effort`
  as a worker `start` does.
- **Grok Bot attestation, non-zcode Host**: the locator attests the bound
  target, the checkout, that platform's worker script under ROOT, and the exact
  session name. `--intent start|resume` adds no launchability check for that
  CLI (the `KAOLA_ZCODE_*` gate is zcode-only). Liveness is Runner
  `status`/`list`.

## Worker classes

Read on demand to advise the user: classes, profiles and the seat-switch rule
in `skills/kaola-project-runner/references/worker-profiles.md` of the Project
Runner checkout; all rows in `profile-catalog.md` beside it. Each
runtime/preset (not runtime) has one owner-defined operating class, a role
and not a benchmark:

- **Expert**: complex thinking only (difficult analysis, design, objective
  decomposition, review judgments); no concrete implementation. Each task/use
  needs explicit user permission; a completed task authorizes no reuse; the
  same approved task continues across turns and recovery without re-approval.
  Its review never replaces Host acceptance.
- **Worker**: cheaper and generally weaker; simpler, well-defined work for
  parallel throughput. The six-preset pool is default-authorized (no per-seat,
  count or priority approval; outside the general cap); real account/service
  limits and owner restrictions apply. Relay only exclusions.
- **Elite**: all other presets; the main execution workforce, under explicit
  runtime/preset/count grants that stay valid within their scope.

Relay grants, never tables: Elite in `authorized_platforms=` (a non-default
preset as `<id>/<tier>`), an approved Expert task by preset and task in
`project_context=`; the Host derives its scoped rows. A seat stays bound to its
preset. Relay a user's explicit grant for one seat to switch model/preset
within its runtime verbatim in `project_context=` (or a later update); never
invent or widen one. The Host chooses by authorization, class, profile/task
fit, then capacity; the Delegator does not judge task fit.

## KPR updates

A release notice neither proves that the installed Skill changed or loaded nor
authorizes installation or restart; follow existing installation and recovery
guidance. Once updated guidance is loaded, reconcile this Delegator's active
handoff or already-authorized inquiry against current rules, latest valid user
instructions, and fresh records, replacing superseded wording. Read the current
`worker-profiles.md` in the bound Project Runner checkout for exact pool
membership and concurrency treatment. Preserve Elite grants, counts,
limits and exclusions; each seat's bound runtime/model/preset restrictions and
same-seat switch grants; and current live/stopped identities from Runner status
and start receipts (keep session, ACP, holder and native resume ids distinct).
Remove stopped seats from the live roster while preserving in-flight work and
its locator. A Skill update grants no seats, model switches or other-project
permissions. Keep the current task frontier and valid user restrictions.

Then use the existing idle `send` / busy `steer` route in
[handoff.md](handoff.md#handoff-and-updates) to ask the same Host to reconcile
its working prompt with current rules, latest valid user instructions and
fresh session facts, replacing superseded wording under its existing heartbeat
snapshot rule. The Delegator changes only its own active instructions or
authorized inquiry; the Host owns its heartbeat and inner worker facts. Do not
repeat intake, claims or dispatch, discard in-flight work, start a duplicate
Host or restart automatically. Use existing restart-required evidence and safe
lifecycle only when applicable. Create no heartbeat, change no cadence,
duplicate no ledger, alter no conversation or archive, and do not affect
another project. Reconcile once when updated guidance is loaded, without a
repeated rule dump or per-poll check.

## Native resume id

Only an id a receipt or event attests; never synthesize one, never
`--continue`:

- **zcode**: `sess_*`, the `native_session_identity.nativeSessionId` event,
  present only after the first prompt; `session_meta` holds the bridge
  `zcode-N` id, not `sess_*`.
- **claude-code**: the native UUID in the newest `native_session_identity`
  event (from turn one); a fresh seat's `acp_session_id` is process-local
  and unresumable.
- **every other platform** (native ACP agents): the newest
  `native_session_identity` id when the platform publishes one, else the
  agent's own session id the receipt records as `acp_session_id` (from
  `session_meta.sessionId`, or the id a resumed start re-used: dsh's resume
  result carries none).

No attested id: start a new Host (handoff §Recover) and say so.

## Startup proof

`docs/host-entry-evidence.md` in the Project Runner checkout records, per
row, an isolated probe and the D3 handoff/beat steps; the Delegator checks the
handoff beat. **E1** is a Skill tool_call naming `kaola-project-runner`; **E2** is
a reply quoting a sentence only in the installed Skill body, with no tool read
of it. At the beat, zcode proves by E1; every other row by E2, devin included
(its E1 is the probe's `Invoked skill`, its beat is E2); an E1 there also
counts. The handoff's `startup_proof=` line asks for the quote; check it
against the installed Skill. A manual `SKILL.md` read is neither. Neither:
report the Host as not entry-proven and do not accept its self-description or
completion. On zcode a missing tool_call means the install is wrong: fix it,
never substitute a manual read. Elsewhere a missing quote may also be the
runtime; escalate to the owner rather than guess.

codex: its E2 row was measured on codex-acp 1.13.0; isolated 1.13.1 E2
probes answered `SKILL-NOT-LOADED`. A codex Host accepted by the owner on an
explicit installed-Skill read plus a working bind/wake loop is that owner
acceptance, not E1/E2.
