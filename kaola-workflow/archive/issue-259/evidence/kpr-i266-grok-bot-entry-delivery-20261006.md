# Issue #266 delivery — Grok Bot entry/launch boundary

Project: kaola-project-runner. Issue: 266. Branch: `workflow/issue-266`.
Base commit: `dad228e4` (main). Worktree: `.kw/worktrees/issue-266`.
Date: 2026-10-06. Author: OpenCode Worker `opencode-KPR-i266-grok-entry`.

This report answers the owner-scoped request. It is a proposal and evidence record. It does not
finalize the issue and it does not modify shared source.

## 1. Result in one paragraph

The reported v0.9.0 build already detaches the holder (new session, stdio redirected). So the
reported death is not explained by a missing detach flag, and the proposed cause stays unproven.
The Grok Bot bridge and the Kaola-Delegator guidance currently tell the Agent inside Grok Bot to
`start`/`resume` the Host on the bound target. On Local Computer, that runs the holder inside the
Grok Bot app's own process tree. No supported automated route exists to launch the holder outside
Grok Bot. The correct fix is guidance, not a detachment redesign: instruct the Grok Bot Agent never
to `start`/`resume` in its own environment, attach only to an already-running Host, and otherwise
ask the owner to start the Host in an independent shell. A minimal, budget-safe template patch is
proposed for the #259 sole writer.

## 2. Reported install verified against current main (read-only)

| Fact | Value |
|---|---|
| Reported | v0.9.0 `f775be93`, runner_build `ffe071dc8f96` |
| Tag check | `git describe --tags f775be93` = `v0.9.0`; ancestor of HEAD `dad228e4` |
| runner_build rule | `sha256(kaola-acp-holder.py)[:12]` (`kaola-acp-holder.py:1177-1179`) |
| v0.9.0 holder sha256 | `ffe071dc8f96efb7...` → build `ffe071dc8f96` (exact match) |
| HEAD holder sha256 | `f599b1c792f189e7...` → build `f599b1c792f1` |
| Operator-test diff v0.9.0→HEAD | only `scripts/kaola-acp-holder.py` and `platforms/codex.yaml`; `scripts/kaola-acp.py` unchanged |

The v0.9.0 holder spawn is
`subprocess.Popen(holder_argv, stdin=DEVNULL, stdout=log, stderr=log, start_new_session=True, env=holder_env)`
(`git show f775be93:scripts/kaola-acp.py`, lines 4528-4531). The agent spawn is
`subprocess.Popen(argv, stdin=PIPE, stdout=PIPE, stderr=PIPE, ..., start_new_session=True)`
(`kaola-acp-holder.py:910-918`). Both are present at v0.9.0. Because `kaola-acp.py` is byte-unchanged
from v0.9.0 to HEAD, the spawn region is identical on current main.

Result: the report's build string is exact, and the holder already ran detached at v0.9.0. The
`holder_lost` event cannot be caused by a missing `setsid`/detach flag.

Original live evidence status: no record for `claude-code-KT-orchestrator-main` exists on this host,
and the reported PIDs 63067 and 63488 are gone. I did not attempt any identity takeover. Verification
is therefore exact at the source/build level, not at the live-session level.

## 3. Existing outside-Grok-Bot launch route: none

I inspected the full Grok Bot chain: the bridge, the Delegator Skill, its references
(`handoff.md`, `host-platforms.md`), `INSTALL.md`, `docs/grok-bot-host.md`, and the locator.

- The bridge (`hosts/grok-bot/kaola-delegator.md`, step 4) allows Host `status/start/resume/send/stop`
  on the bound target.
- `skills/kaola-delegator/SKILL.md` §One Host says "Start/resume/replace/attach: handoff.md".
- `handoff.md` §Recover gives the literal launch: `"$RUNNER" start ... --resume "$NATIVE_ID"`, then
  "start once under `$HOST`".
- `docs/grok-bot-host.md` lines 105-107 say "That Skill starts or resumes one CLI Host of the chosen
  platform on the same target".
- The locator (`scripts/kaola-locate.py`) only attests. `--intent start|resume` is a zcode path gate,
  not a launcher.
- No command in the repository runs a launch on an actor outside Grok Bot.

Conclusion: there is no existing supported automated outside-Grok-Bot launch handoff. The setup gap
is that Grok Bot's Local Computer binding executes commands as the Grok Bot app's own descendants.
The required user action is a manual launch in an independent shell on the same target.

## 4. Actionable setup and attachment path

Actor: the owner, or any non-Grok-Bot shell on the bound Local Computer (Terminal.app, SSH, or a
pre-existing tmux session).

```bash
ROOT="<clean checkout at the accepted revision>"
PROJECT="<consumer project canonical Git root>"
PLATFORM="<host platform id>"                       # e.g. claude-code
RUNNER="$ROOT/skills/$PLATFORM-kaola-project-runner/scripts/runtime-tmux.sh"
HOST="$PLATFORM-<PROJECT_CODE>-orchestrator-main"

# Launch OUTSIDE Grok Bot (first start, or after a proven exact stop):
"$RUNNER" start --repo "$PROJECT" --session "$HOST"                    # first start
"$RUNNER" start --repo "$PROJECT" --session "$HOST" --resume "<NATIVE_ID>"
```

Return evidence to keep from the outside shell: `holder_instance_id`, `acp_session_id`,
`agent_pid`, `session`, `repo`, `state: ready`.

Then, from Grok Bot (attach only):

```bash
kaola-project-runner-locate --target local --project "$PROJECT" \
  --worker "$PLATFORM" --session "$HOST"                    # must be "ok"
"$RUNNER" status --repo "$PROJECT" --session "$HOST"        # read-only identity check
"$RUNNER" send --repo "$PROJECT" --session "$HOST" --no-wait --text '<handoff>'
```

Identity rule: `$HOST`, `acp_session_id`, and the native resume id are three separate facts. `stop`
and live attach use the receipt's `holder_instance_id` (`--expected-holder-instance-id`).

## 5. Bounded, model-free launch-boundary proof

Disposable probe: `/tmp/kpr-i266-entry/launch-boundary-test.py`. It reproduces the holder spawn flags
and kills only its own PIDs. Full raw result: `/tmp/kpr-i266-entry/launch-boundary-test.json`.

| Test | Action | Raw result | Conclusion |
|---|---|---|---|
| A | `killpg(caller_pgid, SIGTERM)` | caller died; child alive; child `pgid==pid`, `sid==pid`, `sid != caller sid` | the child survives a signal aimed at the caller's group |
| B | `SIGKILL` only the caller pid | child alive; child `ppid` became `1` | a normal caller exit does not kill the child; the kernel reparents it |
| C | walk the ppid tree, kill every descendant | descendant set contained the child; child died | a caller-side descendant sweep reaches the `start_new_session` child |

Cleanup: `residual_pids: []`; the work directory was removed. No Runner, agent, model, or live
session was touched.

Meaning: `start_new_session=True` gives independence from process-group signals and from a normal
caller exit, but not from an app that actively tears down its descendants. This is consistent with
the reported death and does not prove the app's mechanism. It supports the owner's ruling that a
background/`setsid` declaration alone is not proof of independence.

## 6. `holder_lost` with a live agent: recovery

Full detail: `/tmp/kpr-i266-entry/recovery-path.md`.

- `status` preserves the unknown effect: `outcome: holder_lost`, `error.code: holder-lost`, and
  `mutation_status: unknown` when a prompt was written with no stop reason (`kaola-acp.py:1807-1848`).
- `send`/`steer` are impossible: `op_or_holder_lost()` returns `holder_lost` for every op but `stop`.
- `stop --force` sweeps only identity-checked recorded groups, keeps `mutation_status: unknown`, and
  retires the record only at `residual_pids: []` (`kaola-acp.py:2212-2269`).
- `start` refuses while the old agent lives (`kaola-acp.py:4507-4509`), so an unknown in-flight
  mutation is never silently replayed.
- No `attach` command exists. `rebind-host` needs a live holder and leaves the agent and holder
  unchanged. The holder owns the agent's stdio pipes, so a dead holder cannot be re-attached.
- Native restoration happens only through `start --resume <NATIVE_ID>`, run from an independent shell,
  with an id a receipt or event attests. The record's `acp_session_id` is process-local metadata, not
  proof of native restoration.

## 7. Proposed template guidance patch (proposal only, for the #259 sole writer)

Patch: `/tmp/kpr-i266-entry/proposed/issue-266-guidance.patch`. I did not modify shared source.

- `templates/kaola-delegator/references/host-platforms.md.tmpl`: append the launch-environment rule
  to the existing "Grok Bot attestation, non-zcode Host" bullet. Rendered budget 7283 → 7724 of 8192.
- `templates/kaola-delegator/references/handoff.md.tmpl`: add a one-line pointer in
  §Grok Bot co-location, with a byte-neutral trade (drop the native-resume clause that duplicates
  host-platforms.md, and compress `--intent start|resume`). Rendered budget 8185 → 8181 of 8192.
- `skills/kaola-delegator/SKILL.md`: unchanged (4086 of 4096).

Rule text (host-platforms.md):

> On the Grok Bot account bridge, never `start` or `start --resume` the Host in Grok Bot's own
> execution environment: Grok Bot runs commands as its descendants, and a Grok Bot quit or relaunch
> can kill them and the in-flight turn. Attach only to a Host that already runs; if none runs, ask
> the owner to run the start (or resume) command in an independent shell on the same target, then
> attach. Never fall back to a local `start`.

Pointer text (handoff.md): "From Grok Bot, never `start`/`resume` in its own environment
(host-platforms.md)."

Docs impact: `docs/grok-bot-host.md` lines 105-107 ("That Skill starts or resumes one CLI Host ...
on the same target") conflicts with the new rule. Recommended follow-up sentence: "That Skill
attaches to one CLI Host already started outside Grok Bot, or asks the owner to start it; it never
starts a Host in Grok Bot's own environment."

`render-skills.py --check` currently passes on unmodified main (confirmed: PASS, 2555 B bridge,
content stage). After the writer applies the patch, re-run `--write` then `--check`.

## 8. Meaningful limits and unknowns

- The reported app mechanism is unproven. I did not test or restart the Grok Bot app, and I killed no
  live sessions.
- The probe shows descendant-cleanup reachability, not proof that Grok Bot does it.
- The exact v0.9.0 live session record is not present on this host. Live-level causation cannot be
  re-derived here.
- Native resume availability for that seat is unverified: no attested native id is present for
  `claude-code-KT-orchestrator-main`.
- No ancestry hard gate is proposed; the rule is procedural. The owner scoped #260 item 6 out, and I
  did not reopen it.

## 9. Source custody frontier

- Shared holder/launch/state source and shared guidance are owned by the #259 sole writer (`f888`).
  This run did not touch them.
- This run wrote only its own issue-266 workflow records, `/tmp/kpr-i266-entry/`, and this report.
- Handoff: give `/tmp/kpr-i266-entry/proposed/issue-266-guidance.patch` to the Host for coordination
  with #259, then let the single writer apply, render, and validate.

## 10. Implementation update (2026-10-06, later owner authorization)

The owner then authorized implementation for Host and seats, all adapters and
`start`/`resume`/`restart`/`drain-restart`. This supersedes the guidance-only limit. The work
stays on issue 266 and the same worktree; the #259 writer keeps custody of overlapping sources.

### Artifacts (candidate commit `7778fa22` on `workflow/issue-266`)

| Artifact | sha256 |
|---|---|
| `scripts/kaola-launchd-broker.py` (new) | `abb701898a45c2ed9180f3fe8a99b8874ed4613351960a2418147034eefec210` |
| `tests/contract/test-issue-266-launch-broker.py` (new) | `216d9dd6a952c9f3b0e1c8fbbbdb2809bf5394f39aef8953210eb377b3d1a813` |

Design and the hard-requirement map: `/tmp/kpr-i266-entry/broker-design.md`.

### What it does

One shared helper launches the holder under the per-user service manager instead of under the
caller. A one-shot job runs a validated internal startup, spawns the holder, waits for the
holder's own `ready` record, writes a receipt, and exits. `submit` then unloads the job; the
detached holder survives. ProgramArguments is a literal argv; the internal path is gated by a
private mode-600 armed spec; the holder environment is an explicit minimal map. `KeepAlive=false`;
no login/boot/crash restart, no scheduler, no registry. The job PID is never the holder PID.

### Actual proof (macOS, disposable, model-free)

`python3 tests/contract/test-issue-266-launch-broker.py` → `pass`, 24 checks. Receipt:
`/tmp/kpr-i266-entry/launch-broker-test.json`.

- `broker_survival_and_control`: the holder survives broker exit and a later `launchctl bootout`,
  is re-parented to `ppid 1`, and the one-shot job is unloaded; `status`, `send`, `steer`,
  `capture`, and `stop` all work, and the prompt reaches the agent (agent-side receipt).
- `repeat_reconciles`: a second `submit` returns `existing` — no duplicate.
- `failed_bootstrap_cleanup`: a bad agent argv is refused; the spawned holder is terminated; no
  stale job, plist, or spec remains.
- `job_cleanup_preserves_dispatched_tree`: a job unload does not sweep the detached holder; exact
  `stop` ends it with `residual_pids: []`.
- `literal_argv_and_private_seam`: a `/bin/zsh -c` argv, a missing spec, and a permissive spec are
  all refused.

Leak scan after the run: no `kaola-runner` launchd job, no leftover process, no temp directory.

### Integration patch (pending, for the #259 writer)

Base: accepted commit `badca11e` (worktree `workflow/issue-259`). Proposal directory:
`/tmp/kpr-i266-entry/proposed/integration/`.

- `kaola-acp.py`: add `LAUNCH_BROKER`; add `outside_launch_requested` and `spawn_holder_outside`;
  branch the spawn site in `command_start`; add `--launch-backend` (`direct` default). The
  readiness loop uses the holder pid hint so it works for both backends. `drain-restart` inherits
  it through `command_start`.
- `kaola-tmux.sh`: forward `--launch-backend` to `kaola-acp.py` for `start`/`drain-restart`.
- `render-skills.py`: copy `kaola-launchd-broker.py` into each generated skill's `scripts/`.

Both files pass `python3 -m py_compile` and `bash -n`. No shared source was edited here.

### OS disposition

macOS launchd is proven. Linux user systemd is designed but unmeasured; other systems are refused
with actionable recovery. See `/tmp/kpr-i266-entry/os-disposition.md`. No silent fallback to the
vulnerable parent, no universal OS claim.

### Meaningful limits

- The broker is proven on macOS only.
- GUI/TCC/Keychain capability, logout/reboot survival, model quota, and outer timer availability are
  not addressed and stay unverified.
- No new stdio attach to a live agent is claimed.
- The reported holder-loss cause remains unproven.

## 11. Repaired solution (historical; superseded by §14)

This was the solution at commit `52298ebd`. Section 14 is the current answer. Sections 2-7 are
earlier history and are superseded too.

Candidate commit **`52298ebd`** on `workflow/issue-266` (new files only; overlapping source stays
with the #259 writer):

| Artifact | sha256 |
|---|---|
| `scripts/kaola-launchd-broker.py` | `e93f6040b2c89a22f2bcb865ae15c4b8b35ea2f861a4e2bc9c46180e0b0522d4` |
| `tests/contract/test-issue-266-launch-broker.py` | `8b09fa20a8edf4225703da8e34a3a8631c1424df1d1433c990d2769d6ed9e829` |
| `tests/contract/test-issue-266-launch-broker-composed.py` | `277aa0b0a9a26f121b25745d404b9b6e63f4c9e828b5e3b8c80e05c285dd7e9e` |

### Host-review repairs

1. **Identity/readiness/repeat.** `verified_holder` now requires the holder's own socket `state`
   reply to match the record instance and a live-pid `--record-dir` argv anchor; a matching string
   plus any live PID is rejected. `internal-run` waits for the holder it spawned
   (`expect_pid`). `wait_receipt` re-verifies the new attempt's identity. `launchd_bootstrap` no
   longer blindly boots out the label: a running job is reconciled; per-attempt exclusive dirs
   stop a concurrent start from overwriting another spec.
2. **Integration security/cleanup.** The whole-env file is gone: `spawn_holder_outside` passes only
   `holder_env` to the broker, which filters it. The literal argv travels in an `O_EXCL` mode-600
   file consumed and removed in `finally`. The broker's private files are `O_EXCL` 600; the
   readiness receipt and attempt dir are consumed. `stop` derives the owned prefixed label and
   does not trust an arbitrary label or run dir.
3. **Lifecycle.** The broker appends the spawned holder to the outer agent's child record, so
   dispatcher/child ownership and `--preserve-dispatched-workers` survive the outside launch. The
   backend is recorded in `start_selection` and reused by `apply_recorded_selection` on a restart.
4. **Proof.** The overclaiming assertions are tightened (`residual_pids` must be present and empty;
   `steer` must not be an error receipt and must reach the agent). New edges cover a foreign
   PID/record, a concurrent running job, and failed-start cleanup. Raw per-operation evidence is in
   the receipts.
5. **Linux.** A minimal `systemd-run --user --collect` adapter is implemented behind availability
   detection; it is unmeasured here and is not labelled proven.

### Proof (macOS, disposable, model-free)

- Helper suite: `tests/contract/test-issue-266-launch-broker.py` → **pass, 29 checks**.
- Composed proof: the real `command_start` in a scratch export of the accepted base with the
  integration patch applied (`K266_COMPOSED_ROOT`) → **pass, 9 checks**. It starts a Host and a
  Worker the Host dispatched, records the Worker in the Host child record, survives a job unload,
  preserves the Worker through the Host `--preserve-dispatched-workers` stop, and exact-stops it.

Receipts: `/tmp/kpr-i266-entry/launch-broker-test.json`,
`/tmp/kpr-i266-entry/launch-broker-composed.json`. No `kaola-runner` job, process, or temp dir is
left. Source, mock, and native are separate: no native target was exercised in this round.

### Integration patch (pending, for the #259 writer, base `badca11e`)

`/tmp/kpr-i266-entry/proposed/integration/`:

| File | sha256 |
|---|---|
| `kaola-acp.py.patch` | `bfee8945882982b78799569f0fcd988f70f0a83105a3720ccf82191322d3e69c` |
| `kaola-tmux.sh.patch` | `49350dfbaa59558e49380ca680e83c4156419b26d4202e773ce2bfc8c06e3aae` |
| `render-skills.py.patch` | `7d52525aee238f635a842ee33dd3b35d06ad3745e5b5f505f729a29308c00a46` |

It adds the `--launch-backend` flag, the broker spawn branch with child-record and rollback, the
backend in `start_selection`, the `apply_recorded_selection` propagation, the `kaola-tmux.sh`
forwarding, and the renderer copy. All pass `py_compile` / `bash -n`.

### Guidance update

`/tmp/kpr-i266-entry/proposed/issue-266-guidance.patch` now tells the Grok Bot Agent to launch
through the shared outside-caller launcher (`--launch-backend launchd`) and to keep the launcher
receipt as the attachment identity; the independent-shell action is the fallback. This supersedes
the earlier manual prohibition.

### OS disposition and limits

macOS launchd is proven; Linux systemd is implemented but unmeasured; other systems refuse with
actionable recovery. See `/tmp/kpr-i266-entry/os-disposition.md`. No new stdio attach to a live
agent is claimed. GUI/TCC/Keychain, logout/reboot, quota, and outer-timer stay unverified. The
reported holder-loss cause remains unproven.

## 12. Lifecycle and disposition

- One claim, one run, one worktree (`issue-266`). No second KPR Host. No live session, worker, or
  consumer was stopped; the active Claude 264 diagnostic resource was left untouched.
- The integration patch and the guidance patch are proposals for the #259 single writer. The broker
  and its two tests are new files owned by this run and committed on `workflow/issue-266`.
- No finalization, release, archive, or sink. Host acceptance and the outer Opus integrated review
  come first, and must include the 266 scoped result plus the original lifecycle/disposition.

## 13. Second repair round (current answer)

Host reviewed `52298ebd`. Candidate is now **`fcce8c1e`** on `workflow/issue-266`.

| Artifact | sha256 |
|---|---|
| `scripts/kaola-launchd-broker.py` | `351471b3c4f61f98434c93cf990917ab7f6830a68b84a69fda7cac0de2ea2391` |
| `tests/contract/test-issue-266-launch-broker.py` | `357ad0ff134c7cc3313ec905ed115e56a109dc368d928683b2a8a563a92e6359` |
| `tests/contract/test-issue-266-launch-broker-composed.py` | `0c5f6ea18c2ed1e51efcc5dbcca27859dfd403c9a0eb9a605d63c648b0dff950` |

Repairs:

1. **Rejected-configuration rollback.** The integration patch makes
   `stop_started_holder(sock, proc, holder_pid)` accept `proc=None` and report the
   reply's residual facts plus the holder identity, never polling a process it
   does not own; both call sites pass the holder pid hint. The composed proof
   executes the patched function with `proc=None` and asserts honest facts and no
   exception.
2. **OS isolation.** Broker job operations branch by backend: launchd on macOS, a
   user systemd transient unit on Linux (`KillMode=process` lifetime policy), and
   a clean refusal elsewhere. A forced `systemd-user` backend on macOS now refuses
   `launch-backend-unsupported` with no launchctl call and no artifact. Linux
   survival stays unmeasured.
3. **Literal argv identity.** The fragile ps-text `argv_anchor` is removed;
   readiness is the holder's own socket reply only. `validate_holder_argv` parses
   the literal list and compares exact argument bindings, so a record path with a
   space still launches (proven).
4. **Normal launch routes.** The backend resolves from `--launch-backend`, then
   the inherited `KAOLA_LAUNCH_BACKEND`, then direct; a non-direct start exports
   `KAOLA_LAUNCH_BACKEND` to the holder so its seats inherit the path. The
   composed proof starts a Worker with no flag but the inherited backend and
   shows it re-parented and recorded `launchd`.
5. **Attempt ownership.** `submit` unloads only the job it bootstrapped; a running
   job is reconciled, never booted out. Refusals carry `holder_may_exist`, and the
   integration sets `mutation_status=unknown` when a holder may exist instead of
   stamping `not_started`. `cleanup` never unloads a running job.
6. **Test env and product env.** The helper suite uses its explicit scratch env
   only (no `os.environ` merge). `filter_env` forwards named Runner keys, proxy
   keys, login-lookup keys, and manifest keys — not every `KAOLA_*`.
7. **Guidance and inventory.** The guidance now states the demonstrated boundary
   (caller shell and one-shot job exit) and that Grok Bot app quit/relaunch
   survival is not demonstrated. The two 266 tests are added to the existing
   `validate.sh` contract lane; the composed test uses the checkout root when no
   `K266_COMPOSED_ROOT` is set, so an integrated candidate runs it directly.

Proof: helper suite **35 checks**, composed proof **15 checks**, all pass; no
`kaola-runner` job, process, or temp dir left. Source, mock, and native are
separate; no native target was exercised in this round.

Integration proposal (base `badca11e`), pending the #259 writer:
`/tmp/kpr-i266-entry/proposed/integration/` — `kaola-acp.py.patch`,
`kaola-tmux.sh.patch`, `render-skills.py.patch`, `validate.sh.patch`.

## 14. Current conclusion (single answer)

Host955 reviewed `703cde3e`. Candidate is now **`cfa491dd`** on `workflow/issue-266`:

| Artifact | sha256 |
|---|---|
| `scripts/kaola-launchd-broker.py` | `63cc4efb2e03eac2766c4c06a69e073ffb6c836e22b3a91ca0e235bc2e73b6d4` |
| `tests/contract/test-issue-266-launch-broker.py` | `5c3b55150e2aebbb0abd8e3ee5741dd3e11567272d936669d31a9f7c15dbc3cc` |
| `tests/contract/test-issue-266-launch-broker-composed.py` | `7044000052f47581cdf6aea52de52a948dfbbf890be4c7bb5006e6d2bbded249` |

Latest fix: `do_cleanup` keeps a leftover attempt while this session's own recorded
holder **or native agent** is still alive (refuses `attempt-unresolved` with
exact-stop recovery), and removes it only after the exact identities are gone. A
successful normal launch leaves no attempt artifact, so it is never blocked. The
recovery hint no longer offers cleanup as an alternative to exact-stop. Affected
evidence: `/tmp/kpr-i266-entry/launch-broker-custody-probes.json` (10 checks,
`40eb9951…`) and `launch-broker-custody-composed.json` (7 checks, `928cd6e8…`).
The older `launch-broker-test.json` (35) and `launch-broker-composed.json` are
retained prior results.

Repairs in this round:

1. **Truthful stop custody.** `_stop_owned_holder` reports clean only for a
   positive stop with an actual empty residual list and a reaped child; a
   missing/refused reply or a null residual keeps the native/worker custody
   unknown (no false-clean `not_started`). Failed-attempt reconciliation keeps the
   attempt evidence and stays unresolved while this session's own recorded holder
   is still alive, even after its job is unloaded.
2. **Attempt-bound cleanup.** `do_cleanup` unloads only an exited job proven owned
   by a recorded attempt spec; an unknown manager state is refused and leaves the
   job and its attempt artifacts untouched. No blanket cleanup.
3. **Bound rollback request.** The integration proposal uses a bound
   `expected_holder_instance_id` request plus a positive stop/residual/reaped
   outcome (`holder_reclaimed`); the holder echo is not required and no false
   mismatch gate is added.
4. **Exact residual identity.** The composed residual checks now use the recorded
   exact holder and agent PIDs, not a ps argv scan. The helper suite adds the
   smallest fault-injection probes for the two repaired paths.

Proof: helper suite **39 checks**, composed proof **22 checks**, all pass; no
`kaola-runner` job, process, or temp dir left. Integration proposal (base
`badca11e`): `kaola-acp.py.patch` `61413906…`, `kaola-tmux.sh.patch` `9e44bfc7…`,
`render-skills.py.patch` `7d52525a…`, `validate.sh.patch` `a32d8b27…`.

**Conclusion.** The outside-caller launcher is implemented and proven on macOS for
the normal Host and dispatched-seat entry, with truthful partial/custody outcomes,
attempt-bound cleanup, and real refusal/failure recovery. `auto` degrades to direct
with a receipt flag when the manager is unavailable; an explicit backend refuses
with actionable recovery. Linux user systemd is implemented but unmeasured; other
systems are unmeasured and degrade only under `auto`. Source and fixture results do
not prove Grok Bot app-quit/relaunch survival or any all-platform native PASS. The
overlapping integration and guidance patches are proposals for the #259 writer. No
finalize, release, or sink.

Workflow project: issue-266
Issue: 266
Branch: workflow/issue-266
Mission ledger: 10 done / 0 in-flight / 0 todo / 0 blocked / 0 failed
Next: Host acceptance of this candidate, #259 coordination on the integration
patch, then `/kaola-workflow-finalize issue-266`.
