# Design: mechanical `KAOLA_ACP_HEARTBEAT_HOST` binding on the Project Runner dispatch path

Issue #99 · design only · 2026-09-19 · baseline `main` d300c7a

Scope of this document: a design that makes the worker→Host notification binding a side effect of
running `start` from inside a ZCode Host, not an instruction the Host has to follow. Nothing here is
implemented. Line numbers cite the baseline above.

Hard constraints honoured: no change under `~/.dsh/`; `templates/grok-golden/` untouched; no new
registry, lock, scheduler, pointer file, or second gate concept (AGENTS.md "Layered entry").

---

## 0. The owner's rule, restated as script behaviour

> A worker dispatched through the Project Runner Skill path has its `start` bind
> `KAOLA_ACP_HEARTBEAT_HOST` to the dispatching Host automatically, effective in the holder and in
> the receipt. If the binding cannot be established, that `start` fails and opens nothing. The
> refusal exists to guarantee the automatic binding; it is not a gate product of its own.

Two consequences drive every section below:

1. **The script must know who dispatched it.** Today it cannot (§1.2). The design adds exactly one
   identity fact, set by the Host's own holder, and derives the binding from it.
2. **Standalone use must not change.** A `start` run from a human shell, a Codex/Claude Code Host
   under its native CLI, or a test harness has no dispatching Host holder. It stays an ordinary
   unbound start with `heartbeat_host: null` (Issue #66/#70 contract, `tests/contract/test-zcode-heartbeat-contract.py:870-885`).
   Refusal is therefore scoped to "a ZCode Host holder is provably the dispatcher and the binding
   still cannot be effected", never to "no binding was given".

---

## 1. Code facts the design rests on

### 1.1 What `start` does with the variable today

| Fact | Where |
|---|---|
| Env names | `scripts/kaola-acp.py:85-86` (`HEARTBEAT_HOST_ENV`, `HEARTBEAT_HOST_SOCKET_ENV`); mirrored `scripts/kaola-acp-holder.py:144-145` |
| Absent variable ⇒ `None`, no error | `kaola-acp.py:1251-1253` (`heartbeat_host_target`) |
| Validation when present: JSON object, `platform == "zcode"`, session syntax, repo is a Git root, not self | `kaola-acp.py:1254-1271`; all failures are `die()` (`:239-241`, stderr text, **exit 2**, no JSON) |
| Socket derived deterministically from `(platform, session, repo)` | `kaola-acp.py:1272-1275` via `record_root` (`:289-296`) and `sock_path_for_directory` (`:313-316`) |
| `start` records the request, spawns the holder with the two env names only when a target exists | `kaola-acp.py:1314-1317`, `:1360-1367` |
| Receipt reports the holder's own adopted binding (`attach_binding_fact`) | `kaola-acp.py:1279-1295`, applied `:1402`; `observe`/`status` `:1794-1803` |
| Holder re-parses the env, disables the carrier loudly on a bad shape, never fatal | `kaola-acp-holder.py:184-204` |
| Holder stores `heartbeat_host` in `record.json` and in `state` | `kaola-acp-holder.py:1262`, `:1309`, `:1732` |
| Every carrier path returns early on `None` | `kaola-acp-holder.py:1959-1961` (`_notify_heartbeat_host_now`), `:2121-2122` (undelivered-wake re-offer) |
| Host side accepts `worker_event` only on a `zcode` holder | `op_worker_event` in `kaola-acp-holder.py` (`worker-event-unsupported`); `event_id` derivation `:58-66` |

So: unset ⇒ a live worker whose `idle`, `terminated` and `permission_required` events never leave
its holder, and a receipt that says so truthfully (`heartbeat_host: null`, `heartbeat_host_known:
true`). The truth is reported; nothing acts on it.

### 1.2 Why the Host's shell cannot currently identify its own holder

- The holder spawns the agent with the inherited environment plus **one** Runner fact,
  `KAOLA_ACP_CHILD_RECORD` = `<record_dir>/children.jsonl` (`kaola-acp-holder.py:595-616`, set at
  `:604`). That path would encode `platform/session/<repo digest>`, but:
- The ZCode bridge builds the agent's environment from a strict allowlist
  (`scripts/kaola-zcode-acp.py:311-325`, `build_child_env` `:413-440`) and the comment at
  `:303-310` states that `KAOLA_ACP_CHILD_RECORD` is **deliberately not forwarded** because it is a
  write handle to another holder's record (Issue #62 trust boundary).
- Therefore a ZCode Host agent's Bash tool sees none of: its Runner session name, its repo, its
  holder's record dir, its socket. The only Runner-owned facts it sees are `KAOLA_ZCODE_ENTRY` /
  `KAOLA_ZCODE_NODE` (allowlisted, `:324-325`), which the nested-ZCode-worker path already relies
  on — proof that environment **does** propagate from the ZCode process into the commands the Host
  runs.
- Every other bridge inherits the environment whole (`kaola-acp.py:194-201` `agent_environment`,
  and the holder's `dict(os.environ)` at `kaola-acp-holder.py:597`), so only the ZCode allowlist needs an entry.

### 1.3 The two established shapes this design reuses

- **Orchestrator-context marker.** `KAOLA_PROJECT_RUNNER_CANONICAL_REPO` (Issue #73,
  `scripts/kaola-tmux.sh:138-181`): absent ⇒ standalone, nothing applies; present ⇒ the one shared
  entrypoint completes/checks the root and refuses drift **before any process, tmux session, or
  record exists**, with a typed JSON refusal and exit 1 (`refuse_canonical_root`, `:149-157`).
- **Binding fact contract.** Issue #70: three honest answers (target / explicit `null` / `known:
  false`), a live holder's binding is immutable, `session-exists` reports the binding in force,
  `heartbeat_host_requested` keeps the request apart from the fact (`kaola-acp.py:1279-1295`,
  `docs/api.md:292-298`).

The design adds one identity fact and one refusal reason family to these; it does not add a
second marker system.

---

## a) Enforcement point and responsibility split

### a.1 One new identity fact: `KAOLA_ACP_DISPATCHER`

**Set by:** the holder, for the agent it hosts, at `AgentProcess.spawn`
(`kaola-acp-holder.py:595-616`, beside `KAOLA_ACP_CHILD_RECORD` at `:604`).

**Value:** one JSON object, `sort_keys`, identity only:

```json
{"holder_instance_id":"<this holder's id>","platform":"zcode","repo":"/abs/git/root","session":"zcode-kaola-host"}
```

`platform`, `session`, `repo` are the holder's own `args` (the same three the record carries,
`kaola-acp-holder.py:1288-1290`); `holder_instance_id` is the holder's `:1292` value. No socket path, no record path,
no pid. Every holder sets it regardless of platform; only the ZCode bridge needs to forward it.

**Forwarded by:** `scripts/kaola-zcode-acp.py` `ENV_ALLOWLIST` (`:311-325`) gains
`"KAOLA_ACP_DISPATCHER"`. The `:303-310` comment is extended with one sentence: this name is an
identity fact, not a handle — the socket it implies is already deterministic from
`(platform, session, repo)` (`kaola-acp.py:1272-1275`) and reachable by any local process that
knows those three strings, so forwarding it grants nothing new. `KAOLA_ACP_CHILD_RECORD` stays
excluded.

**Why an env fact and not process ancestry.** A pgid/ppid walk against `*/*/*/record.json` (the
`list` glob already exists, `kaola-acp.py:359`) was considered and rejected: it silently degrades
to "standalone" the moment an agent's tool runner calls `setsid`, which is exactly the silent
unbound case the owner wants gone. An explicit fact set by the holder either arrives or is
provably missing.

**Why not a shell-side (`kaola-tmux.sh`) check.** The shell cannot compute the socket path, read
`record.json`, or test holder liveness without duplicating `kaola-acp.py`. The shell keeps one
cheap responsibility (PTY, §c.4). All ACP enforcement lives in `command_start`; the shell `exec`s it (`kaola-tmux.sh:229`).

### a.2 Resolution in `command_start` (`kaola-acp.py:1298`)

`heartbeat_host_target` (`:1247`) becomes a resolver with a documented order. It runs at the same
point as today (`:1314`), i.e. **before** the tmux name check, the record read, and the holder
spawn, so a refusal creates nothing.

| # | `KAOLA_ACP_HEARTBEAT_HOST` | `KAOLA_ACP_DISPATCHER` | Outcome | `heartbeat_host_source` |
|---|---|---|---|---|
| 1 | absent | absent | unbound start, exactly today (`:1251-1253`) | `"none"` |
| 2 | present | absent | validated as today (`:1254-1275`); malformed ⇒ `die` exit 2 as today | `"explicit"` |
| 3 | absent | present, `platform == "zcode"` | **derive** target `{platform, session, repo}` from the dispatcher, run the same validation and socket resolution, then **verify** it is live (§a.3); any verification failure ⇒ **refuse** | `"dispatcher"` |
| 4 | absent | present, other platform | unbound start; the carrier is ZCode-only by design (`kaola-acp.py:79-84`, `op_worker_event`) — not a refusal | `"dispatcher-no-carrier"` |
| 5 | present | present, `zcode`, same `session`+`repo` | as row 2 (the explicit value is redundant but consistent) | `"explicit"` |
| 6 | present | present, `zcode`, different `session` or `repo` | **refuse** `heartbeat-host-conflict`: a Host may only bind its workers to itself | — |
| 7 | any | present, `session == --session` and `repo == --repo` | `die` as today `:1268-1270` (a session cannot be its own host) | — |

Row 3 is the mechanical binding. `die` exits and refusals are both printed before `main` reaches its normal `return 0` (`:1655-1658`). Rows 1, 2, 4 preserve every existing behaviour and every existing
test that sets the variable by hand (`test-issue-70-binding-fact.py`, `test-issue-76-permission-wake.py:334-338`,
`test-issue-92-permission-wake-recovery.py:424-428`, `test-issue-74-kaola-delegator.py:481-485`).

Nested chains fall out of the table: a ZCode worker W bound to Host H has its own holder, so any
sub-worker W starts is dispatched by **W** (row 3 with W's identity), and W's holder accepts
`worker_event` because it is a `zcode` holder. A Claude Code ACP worker starting sub-workers hits
row 4. "The dispatcher is whoever ran `start`" needs no special case.

### a.3 Verification before binding (row 3 only)

All facts are already computable in `kaola-acp.py`:

1. `record_dir(dispatcher)` = `record_root / "zcode" / session / sha256(repo)[:16]` (`:299-301`)
   must contain `record.json` (`read_record`, `:702-703`).
2. That record's `holder_pid` must be alive (`pid_alive`, used at `:1331`).
3. That record's `holder_instance_id` must equal the dispatcher's — an agent whose holder was
   replaced under the same name is an orphan of a dead holder; binding to the *new* holder would be
   a foreign target.
4. `sock_path_for_directory(record_dir)` must exist on disk (the Host holder's admin socket the
   worker holder will connect to, `kaola-acp-holder.py:1976` `_carrier_send`).

Any miss ⇒ `heartbeat-host-unresolved` with a `detail` naming which step failed. The four checks are
reads only; the design adds no new store and no probe op (a `state` round trip to the Host holder
is deliberately not required — liveness of the pid plus the socket file is the same evidence
`command_start` already accepts for its own holder at `:1378-1387`).

### a.4 What flows to the holder

Unchanged: the resolved target plus socket travel in `KAOLA_ACP_HEARTBEAT_HOST` /
`KAOLA_ACP_HEARTBEAT_HOST_SOCKET` (`:1360-1367`), and the holder adopts them through the existing
`parse_heartbeat_host` (`kaola-acp-holder.py:184-204`). The holder does **not** learn the source;
`record.json` and `state` keep their current shape (no new carrier field — see the Issue #90 note
that `bare_holder()` in tests hand-initialises every carrier field).

### a.5 Receipt additions (start only)

- `heartbeat_host_source`: `"none" | "explicit" | "dispatcher" | "dispatcher-no-carrier"` — this
  command's input fact, sibling of `heartbeat_host_requested` (`:1317`).
- `dispatcher`: the parsed `KAOLA_ACP_DISPATCHER` object when present (identity only), so a Host
  reading its own worker's receipt sees itself named without any check of its own.

`heartbeat_host` / `heartbeat_host_known` / `heartbeat_host_requested` keep their #70 meaning.

---

## b) Failure shape

### b.1 Where and what

Refusals are emitted by `command_start` **before** `:1319` (tmux name probe). Nothing has been
probed, written, or spawned. Shape mirrors `refuse_canonical_root` (`kaola-tmux.sh:149-157`) so a
Host, the Delegator's locator habit ("refuse `refused`"), and existing readers see one refusal
grammar on both transports:

```json
{"schema_version":3,"result":"refused","reason":"heartbeat-host-unresolved","action":"start",
 "platform":"codex","session":"codex-KT-i274-parser","repo":"/abs/project",
 "heartbeat_host_source":"dispatcher",
 "heartbeat_host_requested":{"platform":"zcode","session":"zcode-kaola-host","repo":"/abs/project","socket":"/tmp/kaola-501-acp/….sock"},
 "dispatcher":{"holder_instance_id":"…","platform":"zcode","repo":"/abs/project","session":"zcode-kaola-host"},
 "detail":"host holder record present but holder_pid 4132 is not alive",
 "mutation_performed":false,"mutation_status":"not_started",
 "transport":{"selected":"acp","default":"acp","alternatives":["pty"],"reason":"manifest-default"},
 "canonical_repo":"/abs/project"}
```

`canonical_repo` appears exactly when the #73 guard ran (`base_receipt`, `:778-781`).

### b.2 Reasons and exit codes

| `reason` | Meaning | Exit |
|---|---|---|
| `heartbeat-host-unresolved` | dispatcher names a ZCode Host that has no record, a dead holder, a different `holder_instance_id`, or no socket file (§a.3) | 1 |
| `heartbeat-host-conflict` | explicit `KAOLA_ACP_HEARTBEAT_HOST` names a different Host than the dispatcher (row 6) | 1 |
| `heartbeat-host-pty-unsupported` | `--transport pty` requested on the Project Runner dispatch path — any dispatcher, or orchestrator context with none (§c.4, ruled 2026-09-19; emitted by `kaola-tmux.sh`) | 1 |
| (unchanged) `die` text on stderr | malformed explicit variable, self-reference (`:1255-1270`) | 2 |

Exit 1 is the value `kaola-tmux.sh` already uses for typed refusals (`:156`); because the shell
`exec`s `kaola-acp.py` for ACP (`:229`), the Python exit code is the command's exit code. Note the
asymmetry that already exists and is kept: other `start` errors (`acp-bridge-missing`,
`session-exists`, `holder-start-timeout`) are `error` receipts with exit 0 (`main`, `:1655-1658`).
The refusal is a `result: refused` receipt because, like `canonical-root-mismatch`, it is a
pre-mutation decision, not a transport outcome.

### b.3 What the Host sees

The Host runs `"$W" start …` in its Bash tool and gets the JSON above on stdout with a non-zero
exit. The three ACP reasons all mean the same thing for the Host: *the process it is running in is
not attached to a live holder it can be woken through*. There is nothing to retry with a hand-set
variable — that path is row 6 and refuses too. The only correct Host action is to report the
receipt to the outer Agent (Delegator) as the one exception `zcode-host-dispatch.md.tmpl:78-80`
already describes. The Skill text shrinks to that sentence (§f).

---

## c) Relation to existing contracts

### c.1 `heartbeat_host` receipt contract (Issue #70)

Unchanged in meaning; the design only adds *how the target was chosen*. A `session-exists` start
(`:1329-1338`) still binds nothing and still returns the reused holder's own fact; it additionally
carries `heartbeat_host_source` and `dispatcher` so a Host can see at a glance that a reused
worker's `null` predates this change (§d). `observe`/`status` are untouched.

### c.2 `permission_required` → `permit` (Issues #76, #92)

Untouched mechanically. What changes is coverage: today a wake is only guaranteed for workers whose
Host remembered the variable; after row 3 every dispatch-path worker is bound, so `pending
permission` wakes (`_notify_heartbeat_host_now("permission_required", …)`, holder `:1579`), the
undelivered-wake retention (`:2121-2150`), and the Host's "read live `pending_permissions`, then
`permit`" rule (`heartbeat-skeleton.txt` beat step 2) apply uniformly. No event schema change:
`worker_event_id` (`:58-66`) and `WORKER_EVENT_KINDS` (`:161`) are the same.

### c.3 Delegator receipt-verification habit (Issue #74)

The Delegator never dispatches workers and never sets the variable (`handoff.md.tmpl:100`,
`SKILL.md.tmpl:52-53`); its habit is to *read* the Host's first worker receipt and require
`heartbeat_host` to name the Host (`handoff.md.tmpl:154-156`, pinned by
`test-issue-74-kaola-delegator.py:362-363` and exercised live at `:481-495`).

With the binding mechanical, that check no longer protects anything the script does not already
refuse — with one transitional exception (§d.2: a Host whose holder predates the change). Design
decision: **drop the per-worker binding check from the Delegator** and keep the Delegator's
first-beat verification focused on what only it can check (plan, authorization, issue-scoped
worker name, stop boundary). The transitional case is covered by the Host restart rule in §d.2,
not by an outer Agent reading env-derived facts. The live test at `:481-495` changes from
"set the variable, expect it echoed" to "set no variable inside the Host agent, expect
`heartbeat_host_source: dispatcher`".

The Delegator's own `start` of the Host runs outside any holder on Grok Bot / Codex / generic,
so the Host itself lands on row 1 and stays unbound — correct, it is the top. If someone runs the
Delegator from *inside* a Runner-managed ZCode session, the Host it starts binds to that session
(row 3). That is a consequence to state in `docs/zcode-host.md`, not a case to special-case.

### c.4 PTY transport

Facts: the variable is read only by `kaola-acp.py`; the PTY start path (`kaola-tmux.sh:593-627`)
has no carrier at all, its tmux session receives only the `CLAUDE_*|GROK_*|…` env whitelist
(`:618`), and every platform's default transport is ACP, so PTY under a Host arises only from an
explicit `--transport pty` caller override (`:127-136`).

**Ruled 2026-09-19 (owner), general rule:** worker dispatch on the Project Runner
instruction/Skill path is **ACP-only**. A `--transport pty` `start` on that path is always refused
with `heartbeat-host-pty-unsupported`. The ZCode Host case is one instance of the rule, not its
scope: the same refusal applies to a Codex, Claude Code, or any other Host dispatching through
Project Runner. The allow-with-`pty-no-carrier` alternative below is **not** adopted and is kept
only as the record of what was considered. (An earlier draft of this section scoped the refusal to
a ZCode dispatcher; corrected to the general rule on 2026-09-19.)

Design (ruled): **refuse** a PTY `start` whenever the dispatch path is mechanically evident —
`KAOLA_ACP_DISPATCHER` present with **any** platform (rows 3–4), **or** orchestrator context
declared by `KAOLA_PROJECT_RUNNER_CANONICAL_REPO` (Issue #73, `kaola-tmux.sh:158`) with no
dispatcher at all (a Host under its native CLI) — reason `heartbeat-host-pty-unsupported`, emitted in `kaola-tmux.sh`
right after transport resolution (`:136`) using the existing `emit_json` refusal shape, before
`adapter_preflight`. Rationale: rule 0 says "cannot bind ⇒ does not open"; a PTY worker under an
event-driven Host has no wake source, which the reference already calls "not reliably
event-driven" (`zcode-host-dispatch.md.tmpl:166-167`). The shell test is `[[ -n "$KAOLA_ACP_DISPATCHER" || -n "$KAOLA_PROJECT_RUNNER_CANONICAL_REPO" ]]`;
no platform parse, socket, or record knowledge needed.

Rejected alternative (record only, ruled out 2026-09-19): allow PTY dispatch and add
`heartbeat_host_source: "pty-no-carrier"` to the PTY status receipt. It keeps the silent gap the
owner wants removed.

Standalone PTY — no dispatcher env and no orchestrator-context export — is unchanged: Platform
Runner used directly keeps both transports (AGENTS.md "Control-plane limits do not change standalone
Platform Runner transport").

### c.5 Canonical-root binding (Issue #73)

Independent and additive. `KAOLA_PROJECT_RUNNER_CANONICAL_REPO` remains the root guard; it is
**not** reused as the dispatcher marker because a Codex Host under its native CLI also sets it and
has no ZCode holder to bind to (row 1 must stay legal there). Both facts appear side by side in the
receipt (`canonical_repo`, `dispatcher`). Under the 2026-09-19 ruling the canonical-root export is
also the second mechanical trigger of the ACP-only rule (§c.4) for Hosts that run under no holder.

---

## d) Compatibility for sessions already live with `heartbeat_host: null`

### d.1 Live worker holders

A holder's binding is fixed at start (#70). Existing unbound workers keep `heartbeat_host: null,
heartbeat_host_known: true` on `observe`/`status`, keep running, and keep waking nobody. A repeated
`start` on their name returns `session-exists` with that fact (`:1329-1338`) — now plus
`heartbeat_host_source` showing what a fresh start *would* do. Recovery is the existing exact
`stop` at a safe idle point followed by `start`; the new `start` binds by itself. The reference's
four-step recovery (`zcode-host-dispatch.md.tmpl:54-80`) reduces to that one sentence (§f).

### d.2 Live ZCode Host holders started before the change

Their holder never set `KAOLA_ACP_DISPATCHER`, so every worker they start is row 1: unbound and
**not refused**, indistinguishable from standalone. This is the one residual gap and it closes only
by restarting the Host on the new build (Delegator `--resume` with the attested `sess_*`, or a fresh
standard-named Host, per `handoff.md.tmpl:71-78` and `:94-96`). State it in `CHANGELOG.md` and in
`docs/zcode-host.md` ("Arming"); do not add a runtime probe for it.

### d.3 Records without the field

`heartbeat_host_known: false` (pre-#70 records) is unchanged. `heartbeat_host_source` is a
start-receipt field, so its absence on `observe` carries no meaning and needs no "unknown" value.

### d.4 Tests and fixtures

Every existing test that binds by setting the variable keeps working (row 2). Tests that assert
"unarmed ⇒ null, not refused" keep working (row 1). The ZCode bridge allowlist test (if any) and
`tests/contract/test-issue-62*`-era assertions about `KAOLA_ACP_CHILD_RECORD` exclusion stay
true.

---

## e) Script-level acceptance cases (design state)

Harness: the existing `Sandbox` in `tests/contract/test-zcode-heartbeat-contract.py` (`start`
at `:293-300`, `record_dir` `:246`, `KAOLA_ACP_RECORD_ROOT` `:232`), extended with one `cli`
override `KAOLA_ACP_DISPATCHER=…` the same way `heartbeat_host=` sets the explicit variable, and
one fake-agent scenario that runs a nested `kaola-acp.py start` from *inside* the agent process so
the holder-set env is exercised for real, not injected by the test.

Negative (each must leave no `record.json`, no holder pid, no socket for the worker, exit 1,
`result: refused`, `mutation_performed: false`):

| # | Setup | Expect |
|---|---|---|
| N1 | `KAOLA_ACP_DISPATCHER` names a ZCode session with **no record** | `heartbeat-host-unresolved`, `detail` names the missing record |
| N2 | dispatcher record exists, holder pid dead | `heartbeat-host-unresolved` |
| N3 | dispatcher record live but `holder_instance_id` differs (name reused by a new holder) | `heartbeat-host-unresolved` |
| N4 | dispatcher record live, socket file removed | `heartbeat-host-unresolved` |
| N5 | dispatcher = live ZCode Host A, explicit variable names live ZCode Host B | `heartbeat-host-conflict`; A's and B's holders receive nothing |
| N6 | dispatcher = live ZCode Host, `--transport pty` | `heartbeat-host-pty-unsupported` from `kaola-tmux.sh`; `tmux has-session` false afterwards |
| N6b | dispatcher with `platform: "claude-code"` (row 4), `--transport pty` | same refusal — the ACP-only rule is not ZCode-scoped (ruled 2026-09-19) |
| N6c | no dispatcher, `KAOLA_PROJECT_RUNNER_CANONICAL_REPO` exported (Codex-style Host under its native CLI), `--transport pty` | same refusal; no tmux session created |
| N6d | no dispatcher, no canonical-root export, `--transport pty` | standalone PTY start proceeds exactly as today (regression guard) |
| N7 | dispatcher session equals the worker `--session` and repo | today's `die`, exit 2, unchanged |
| N8 | **the owner's negative:** inside a real ZCode Host fake agent, the nested start is run with `env -u KAOLA_ACP_DISPATCHER` *and* a Host whose holder is then killed — i.e. the only mechanical source is gone | the first form is row 1 (documented residual, §d.2, asserted as `source: none`, not refused); the second form is N2. The test pins both so the boundary of the guarantee is explicit |

Positive:

| # | Setup | Expect |
|---|---|---|
| P1 | live ZCode Host H (fake agent); nested fake-agent scenario runs `start` for worker W with **no variable** | W receipt: `heartbeat_host == expected_fact(H)`, `heartbeat_host_known: true`, `heartbeat_host_source: "dispatcher"`, `dispatcher.session == H`; `record.json` of W stores the same target; `observe` W agrees |
| P2 | as P1, then W's turn ends | H's holder receives `idle` with `event_id == zcode/W/idle/<cursor>` (reuse `test_issue_66…`/`#76` carrier assertions with the env line deleted) |
| P3 | as P1, W raises `session/request_permission` | H receives `permission_required` carrying `request_id`; `permit` on W settles it (reuse #76 flow) |
| P4 | explicit variable equal to the dispatcher | `source: "explicit"`, bound, no refusal |
| P5 | dispatcher with `platform: "claude-code"` | `source: "dispatcher-no-carrier"`, `heartbeat_host: null`, not refused |
| P6 | no dispatcher, no variable | today's `test_issue_66_unarmed_worker_stays_ungated` passes byte-for-byte plus `source: "none"` |
| P7 | `session-exists` on a live null-bound worker started before the change | `error.code == session-exists`, `heartbeat_host: null`, `heartbeat_host_source` present; then exact `stop` + `start` under the dispatcher ⇒ bound (row 3) |
| P8 | holder unit: `AgentProcess.spawn` env contains `KAOLA_ACP_DISPATCHER` with the four keys and **still** `KAOLA_ACP_CHILD_RECORD` | assert both, assert JSON `sort_keys` |
| P9 | bridge unit: `build_child_env` with `KAOLA_ACP_DISPATCHER` set forwards it and still drops `KAOLA_ACP_CHILD_RECORD` and every `DENIED_ENV` name | assert |
| P10 | `./scripts/render-skills.py --check` and `./scripts/validate.sh` after the prose changes in §f | budgets hold (main ≤ 17408 B, references ≤ 8192 B, external ≤ 4096 B); moved pins pass |

Live (recorded, not automated): Delegator-started ZCode Host on this Mac, Host runs one Codex
worker `start` with no variable ⇒ receipt bound; worker `idle` wakes the Host; a
`permission_required` wake arrives and `permit` settles it; a deliberate `--transport pty` start
from the Host is refused with no tmux session left behind; the same from a Codex Host shell with
only the canonical-root export is refused too.

---

## f) Prose-reduction inventory (templates, docs, and the pins that move with them)

Principle: after row 3, the Host is told **what the receipt means**, not **what to set**. Every
"bind it yourself" sentence goes; every "here is the fact and its unknown case" sentence stays.
Sizes: main Skill renders at 16722 B of 17408 (686 B headroom); `zcode-host-dispatch.md` at
8191 B of 8192; `handoff.md` at 8190 B of 8192; Delegator `SKILL.md` at 4010 B of 4096. Every
change below is a net deletion, so budgets only gain room.

### f.1 `templates/orchestrator/SKILL.md.tmpl`

| Lines | Today | Change |
|---|---|---|
| `:81-82` "Each beat: set `KAOLA_ACP_HEARTBEAT_HOST` (a JSON object naming the Host) on every worker `start`, verify the receipt's `heartbeat_host`, dispatch with …" | manual bind + verify | **Rewrite** to: "Each beat: a worker `start` run from this Host binds to it by itself (`KAOLA_ACP_HEARTBEAT_HOST` is derived; a refused `start` opened nothing and names why), dispatch with …". One mention of the variable survives because `test-zcode-heartbeat-contract.py:1337-1339` pins exactly one occurrence and `test-issue-65-host-contract.py:63-72` pins the fragment; both pins keep passing. Net ≈ −20 B |
| `:120-126` canonical-root paragraph | unrelated | unchanged |

### f.2 `templates/orchestrator/references/zcode-host-dispatch.md.tmpl`

| Lines | Today | Change |
|---|---|---|
| `:18-34` "### Bind the notification target on every worker `start`" with the 6-line runnable example and the "Exporting it, or setting it on a later `send`, binds nothing" sentence | the manual procedure | **Replace** the heading with "### Start a worker from this Host" and the body with the example **minus** the `KAOLA_ACP_HEARTBEAT_HOST='…' \` line (`:27`), plus one sentence: "Run `start` from your own session: it binds the worker to you and refuses (`result: refused`, `reason: heartbeat-host-…`) instead of starting unbound." Keep `:33-34` (issue-scoped names). Pins to move: `test-issue-65-host-contract.py:88-89` assert the `KAOLA_ACP_HEARTBEAT_HOST='{"platform":"zcode"` and `"session":"zcode-kaola-host"` literals in the reference — the first is deleted with the line, the second stays via the `dispatcher` receipt example below. Net ≈ −330 B |
| `:36-52` "### Verify the binding in force, new worker or reused" with the JSON fact and three bullets | the verification habit | **Shorten** to the JSON fact (now also showing `"heartbeat_host_source":"dispatcher"` and `"dispatcher":{…"session":"zcode-kaola-host"…}`) and two bullets: `heartbeat_host_known: false` (unknown, treat as unbound) and `session-exists` (reused live holder keeps its binding; a `null` there predates automatic binding — exact `stop` at idle, then `start`). Drop the "Check the fact's `session`/`repo` are yours" instruction (`:44`) and the "ordinary unbound worker … another Host's binding wakes that Host" bullet (`:47-48`): the script refuses those cases. Pins kept: `'"heartbeat_host"'`, "`heartbeat_host` is the running holder's own binding", `heartbeat_host_known` (`test-issue-65:96-100`). Net ≈ −250 B |
| `:54-80` "### A missing or wrong binding" (four-step recovery + exception paragraph) | the whole manual recovery | **Delete** steps 1–4 (`:56-76`). Keep two sentences: "A worker started before automatic binding shows `heartbeat_host: null`: read its in-flight result with the bounded `wait --timeout <seconds>`, then exact `stop` and `start` it at that idle point. A refused `start`, or a session that is gone, is the exception you report with the decision you need." Keep the `--resume`/`sess_…` sentence (`:70-73`) only if the `--resume` rule is not already in `host-startup.md.tmpl:72-78` (it is — delete here). Net ≈ −1500 B |
| `:166-167` "Dispatch failure, unknown acceptance, or an unverified binding means you are not reliably event-driven" | still true for the first two | **Shorten** to "Dispatch failure or unknown acceptance means you are not reliably event-driven: recover it this beat, or report the exception." Net ≈ −30 B |

### f.3 `templates/orchestrator/references/host-startup.md.tmpl`

| Lines | Today | Change |
|---|---|---|
| `:63-65` startup receipt lists "whether notification binding is in place" | asks the Host to attest a manual step | **Delete** that clause; the receipt still lists role, authorization, lifecycle, sources, conflicts |
| `:80-85` "The beat itself - per-worker `KAOLA_ACP_HEARTBEAT_HOST` binding and its receipt check, non-blocking dispatch, …" | names the manual step | **Rewrite** to "The beat itself - starting workers from this session, non-blocking dispatch, the `dispatch_event_cursor` reading anchor, …". Note `test-zcode-heartbeat-contract.py:1337-1339` counts occurrences in the **main** `SKILL.md` only, so this deletion is free |
| `:90` table row "`.kaola/heartbeat-prompt.json` `body` — current identity, binding, run paths, next step" | "binding" here is the heartbeat prompt's content | keep "binding" if it refers to canonical-root binding; otherwise drop the word (owner's call at acceptance) |

### f.4 `templates/orchestrator/references/heartbeat-skeleton.txt`

No change. It never names the variable (pinned by `test-zcode-heartbeat-contract.py:1327`) and
its beat step 2 already describes `permission_required` handling as the Host's job.

### f.5 `templates/kaola-delegator/references/handoff.md.tmpl`

| Lines | Today | Change |
|---|---|---|
| `:100` "Do not set `KAOLA_ACP_HEARTBEAT_HOST` or start another platform." | forbids a manual step nobody needs | **Shorten** to "Do not start another platform." (The variable stays valid input, row 2, but the Delegator has no reason to know it.) Pins: `test-issue-74:261` and `test-generated-skills.py:575-579` assert the name is *absent* from the Delegator `SKILL.md` — already true; the handoff reference is not pinned for absence, so removing it is free. Net ≈ −40 B |
| `:142` handoff text "Finish planning, worker dispatch, notification binding, heartbeat, acceptance, and Workflow close-out internally." | tells the Host it owns binding | **Delete** "notification binding," — binding is no longer something the Host finishes. Net ≈ −22 B |
| `:154-156` "That `start` receipt must echo `heartbeat_host` for this Host (`session` and `repo`); the worker `--session` is an issue-scoped worker name, not `$HOST`; …" | the Delegator's per-worker binding check | **Delete** the `heartbeat_host` clause, keep the issue-scoped-name and platforms/counts/stop-boundary checks. Pin to move: `test-issue-74-kaola-delegator.py:362-363` ("echo heartbeat_host") is retired; the live check at `:481-495` becomes "worker started inside the Host with no variable reports `heartbeat_host_source: dispatcher` and `heartbeat_host.session == host`" (the same assertion, sourced from the script instead of the Delegator). Net ≈ −80 B |

### f.6 `templates/kaola-delegator/SKILL.md.tmpl`

| Lines | Today | Change |
|---|---|---|
| `:13-14` "A ZCode Host loads it and owns planning, worker dispatch, notification binding, path binding, heartbeat, acceptance, and Workflow close-out." | lists binding as an owned duty | **Delete** "notification binding," (keep "path binding" — that is #73). Net ≈ −22 B |
| `:52-53` "Do not pass per-worker notification bindings, per-worker `--repo`, scheduling, or heartbeat instructions." | forbids passing something that no longer exists as an instruction | **Shorten** to "Do not pass per-worker `--repo`, scheduling, or heartbeat instructions." Net ≈ −33 B |

### f.7 Docs (outside the byte budgets; listed for the implementation issue)

- `docs/zcode-host.md:162-167` "Arming": rewrite from "the Host agent exports …" to "the Host's
  holder names itself to its agent (`KAOLA_ACP_DISPATCHER`); a worker `start` run there derives the
  target, verifies the Host holder is live, and refuses otherwise". Add the §d.2 transitional note.
- `docs/zcode-host.md:176-180` (recovery of an unbound worker by the Host) and `:310-312`
  ("bind `KAOLA_ACP_HEARTBEAT_HOST` per worker `start`, check the receipt's `heartbeat_host` fact
  on every worker including reused ones"): shorten to match f.2.
- `docs/zcode-host.md:338` "No Host, no `KAOLA_ACP_HEARTBEAT_HOST`, no heartbeat prompt file, and
  no added gate": still true (row 1); keep.
- `docs/api.md:292-298`: add `heartbeat_host_source`, `dispatcher`, and the three refusal reasons
  next to the #73 refusal paragraph at `:242-248`.
- `docs/architecture.md:230-238`: one sentence that the dispatcher identity is the second
  holder→agent fact after `KAOLA_ACP_CHILD_RECORD`, and why the ZCode allowlist forwards one and not
  the other.
- `CHANGELOG.md`: user-visible: automatic binding, three refusal reasons, ACP-only dispatch on the Project Runner path (PTY `start` refused),
  Host restart needed for Hosts started on older builds.

### f.8 Test pins summary (what an implementer must touch, nothing else)

| Test | Line | Action |
|---|---|---|
| `test-issue-65-host-contract.py` | `:63` fragment `KAOLA_ACP_HEARTBEAT_HOST` in main | keeps passing (one mention survives) |
| same | `:88` literal `KAOLA_ACP_HEARTBEAT_HOST='{"platform":"zcode"` in reference | retire; replace with `"heartbeat_host_source":"dispatcher"` |
| same | `:89` `"session":"zcode-kaola-host"` | keeps passing via the `dispatcher` example |
| same | `:96-100` binding-fact sentences | keep |
| same | `:141-144` script mechanics (`HEARTBEAT_HOST_ENV`, `heartbeat_host_requested`, `attach_binding_fact`) | keep; add `heartbeat_host_source` |
| `test-zcode-heartbeat-contract.py` | `:1327` skeleton has no variable | keep |
| same | `:1337-1339` main Skill mentions the variable exactly once | keep (rewrite keeps one) |
| same | `:870-885` unarmed stays ungated | keep; add `source: none` |
| `test-issue-74-kaola-delegator.py` | `:261` Delegator Skill lacks the variable | keep |
| same | `:362-363` handoff requires "echo heartbeat_host" | retire |
| same | `:481-495` live inner worker bound via explicit env | rewrite to no-env-inside-Host |
| `test-generated-skills.py` | `:575-579` external Skill lacks the variable | keep |
| new | — | N1–N8, P1–P9 above |

---

## g) Out of scope, stated so the implementer does not drift

- No Host-side registry of workers, no rebind op, no probe op, no new store (AGENTS.md).
- No change to `worker_event` schema, `event_id`, staging cap, confirmation, or #92 retention.
- No change to standalone Platform Runner transport (row 1) or to `templates/grok-golden/`.
- No attempt to detect a pre-change Host at runtime (§d.2 is a documented restart).
- No `~/.dsh/` or dsh-specific behaviour; Issue #98 (dsh worker) is unaffected: a dsh worker started
  from a ZCode Host lands on row 3 like any other ACP worker, and dsh ACP has no permission gate to
  wake on, which is a dsh fact, not a binding fact.

## h) Summary for acceptance

- **Mechanism:** the holder tells its agent who it is (`KAOLA_ACP_DISPATCHER`, identity only, one
  allowlist entry in the ZCode bridge); `kaola-acp.py start` derives and verifies the binding from
  that fact and refuses with a typed `result: refused` receipt and exit 1 when the named Host holder
  is not live. Standalone starts and explicit-variable starts are unchanged.
- **Failure:** `heartbeat-host-unresolved`, `heartbeat-host-conflict`, `heartbeat-host-pty-unsupported`;
  nothing created; the Host reports, never hand-binds.
- **Compatibility:** live bindings immutable (#70); pre-change unbound workers recover by exact
  stop/start; pre-change Hosts must be restarted on the new build (documented residual).
- **Prose:** ~2.3 KB removed across the main Skill, the dispatch reference, host-startup, the
  Delegator Skill and its handoff; five test pins retire or move; no budget pressure.
- **Runner dispatch is ACP-only (ruled 2026-09-19):** on the Project Runner instruction/Skill path,
  workers are dispatched over ACP only; a `--transport pty` `start` there — under a ZCode Host or any
  other Host — is refused with `heartbeat-host-pty-unsupported`. The allow-with-`pty-no-carrier`
  alternative is not adopted. Standalone Platform Runner use keeps both transports.
