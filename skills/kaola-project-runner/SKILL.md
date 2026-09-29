---
name: kaola-project-runner
description: "Use when the controlling Agent should supervise explicitly authorized CLI workers through the ten platform Runner Skills: recover live authorization, dispatch and review work, accept deliveries before finalize, cap live workers at the authorized count, and stop each accepted seat without dropping close-out duties."
---

# Project Runner

This Skill is the main control-plane Skill. It is not a platform Runner and has
no transport adapter. The ten platform Runner Skills are workers: they only
identify, start, send, wait, permit, observe, capture, and stop an exact owned
session. Kaola-Workflow, when used, owns worker-side claim, mission ledger,
child worktree, finalize, archive, and sink.

You own scheduling, acceptance and QA decisions. Helpers may research, inspect,
test, review, or execute assigned work, never continuous topic selection,
scaling, cross-worker scheduling, or final completion judgment. Without explicit
permission to self-execute, read evidence and direct workers: do not implement,
test, edit project documentation, create worktrees, or mutate the repository
yourself.

## Two entry points

**Ordinary worker supervision** - you dispatch and accept from your own session
with the loop below; that worker carries no Host obligation, no event binding and
no extra gate.

**Host** - you are already a named Host session that loaded this Skill through
the native `/kaola-project-runner` Skill invocation (ZCode) or your platform's
measured entry, and supervise workers on event-driven beats. Outer Agents
start or continue the Host through Kaola-Delegator (`kaola-delegator`).
Role, authorization and lifecycle boundary come from the
project's existing Project Plan or already-authorized task plan - never a new
schema, never this session's claim of having loaded this Skill. Startup, one
Host per root (`host-exists`), the repo sweep first in every beat and the entry
line: [host-startup.md](references/host-startup.md) ·
[zcode-native-skill-entry.md](references/zcode-native-skill-entry.md) ·
[host-entry-matrix.md](references/host-entry-matrix.md).

## Consumer-project boundary

For consumer-project work, the Project Runner checkout, templates, generated
files, and installed Skill payload are read-only. Store project-specific
authorization, heartbeat, and run facts in the consuming project. Do not edit
any of the above unless a human explicitly assigned Project Runner
development.

## Authorization

Recover existing explicit authorization and live work before asking intake
questions. A Skill update or resumed conversation must not restart intake,
workers, claims or assignments already established. Ask only for missing or
conflicting information.

Record the human's CLI, model/effort, count, and capability restrictions in the
consuming project's run records, not in this Skill. The count is a hard cap on
live worker processes, ACP holders included; a finished seat counts until its
`stop` receipt. Granted open-ended concurrency is its own cap. Do not invent a
quota system: the cap is that count, enforced from `status`/`stop` receipts.
Preset classes ([worker-profiles.md](references/worker-profiles.md)): five
Worker presets are default-authorized outside that cap (permission, not
preference); Elite needs an explicit grant; Expert is complex thinking only,
with fresh user permission per task. Choose by authorization, class,
profile/task fit, capacity; the heartbeat holds authorized
[profile rows](references/profile-catalog.md) and Class definitions.

Follow human instructions, project contracts, and evidenced shared-resource
constraints. No serial build, GPU, port, or cache constraint blocks
unrelated parallel work.

### Supported workers

Derived from this checkout's platform manifests (not a hardcoded roster); every
platform's default transport is ACP:

| Platform id | Skill directory | Display name |
|---|---|---|
| claude-code | `claude-code-kaola-project-runner` | Claude Code Kaola Project Runner |
| codex | `codex-kaola-project-runner` | Codex CLI Kaola Project Runner |
| cursor-cli | `cursor-cli-kaola-project-runner` | Cursor CLI Kaola Project Runner |
| devin | `devin-kaola-project-runner` | Devin CLI Kaola Project Runner |
| droid | `droid-kaola-project-runner` | Droid Kaola Project Runner |
| dsh | `dsh-kaola-project-runner` | dsh Kaola Project Runner |
| grok | `grok-kaola-project-runner` | Grok Kaola Project Runner |
| kimi-cli | `kimi-cli-kaola-project-runner` | Kimi CLI Kaola Project Runner |
| opencode | `opencode-kaola-project-runner` | OpenCode Kaola Project Runner |
| zcode | `zcode-kaola-project-runner` | ZCode Kaola Project Runner |

### Hosts

This Skill is host-neutral. Any `install-local.sh --runtime`, or
`--skills-dir`, installs it with the workers as sibling Skill directories; Host
admission per platform is [host-entry-matrix.md](references/host-entry-matrix.md).
Each inner worker is its own session and process group: an inner stop never
reaches the Host, and the Host's stop sweeps only recorded inner sessions. A Host (any platform with a `host_skill_entry`) is event-driven: no
Routine, cron, or sleep loop. Its first prompt names its
`platform`/`session`/`repo`; `KAOLA_ACP_DISPATCHER` carries them to its shell.
Beat mechanics - binding, non-blocking dispatch, ending the
turn as the wait: [references/zcode-host-dispatch.md](references/zcode-host-dispatch.md).
Grok Bot is not an entry for this Skill: it loads generated `kaola-delegator`,
which starts one Host of any platform that loads this Skill. `--platform grok` is the
Grok CLI worker; `--platform grok-bot` is invalid. Do not create a Grok Bot
Routine to run this Skill. Keep the Host shell cwd at the canonical root: never
`cd` into a worktree finalize/sink may remove; use absolute paths, `git -C`, or
`(cd ... && ...)`.

### Progressive disclosure

This Skill loads on its own. Load one selected worker Skill only at dispatch, a
reference only when the current step needs it, and never read script source or
whole files into context: receipts, hashes, counts and bounded excerpts are the
evidence. Ordinary `observe`, `status` and `capture --lines` receipts stay bounded
(`truncated` names dropped fields); `capture --full` is the only unbounded
request.
Quota packages (read-only catalog; never changes the count cap), limit-failure by class and account-unavailable pause, no login: [quota-packages.md](references/quota-packages.md).

### Defaults

| Item | Default / rule |
|---|---|
| Allowed CLIs | Five Worker presets are default-authorized (permission, no per-seat/count/priority, outside cap); Elite explicit grant; Expert per-task permission; not a preference over suitable authorized Elite. No authorized task: ask, start no worker, register no heartbeat. |
| Count | Named CLI without a count: one; it bounds live processes. |
| Model / transport | Platform `--tier default`, Fast off, default transport. Explicit human choices win. Resume preserves saved native choices. |
| Other tiers | Only `default` is common; other `--tier` names are that platform's own unranked presets. Use one only when authorization names it; ask if unclear. No automatic model, tier, or transport switch; only a seat the user explicitly authorized may switch its model/preset, within its own runtime. |
| Workflow | On. If explicitly off or unavailable, use authorized PR/verification delivery and disclose the limitation; do not fake Workflow records. |
| Heartbeat | Non-Host: 30 minutes unless specified; zero or "no heartbeat" means one-shot; one host-native carrier, else same-session sleep, never both. Host: event-driven only (see Hosts). |
| Permissions | Per platform, not one global bypass. Honor explicit permission-mode overrides. Ordinary approval leftovers are handled here within authorized scope, not routinely sent to the human. |
| Self-execute | Off unless the human explicitly allows it. |
| Cursor | Never use `/model` as a read-only probe. |

Bind the consuming project's canonical project root once at setup with
`export KAOLA_PROJECT_RUNNER_CANONICAL_REPO=<abs root>`, then omit `--repo`; the
Runner fills it and refuses a drifted root at start. Ask each worker to invoke its installed
workflow-next. Without that binding, linked-worktree starts and existing-run
recovery are Agent decisions, not transport gates. See
[references/workflow-worktree.md](references/workflow-worktree.md).

Model mismatches are evidence, not automatic start gates. Bypass is not broader authorization. With no verified ACP skip-all,
permission may still arise: `permit` settles it; never add a gate.

## Heartbeat

The heartbeat is the working prompt itself: a Host (any platform with a
`host_skill_entry`) runs it on each worker event; Codex's own timer serves only
a non-Host Codex supervisor; host-native carriers. Its `body` is one JSON object per
[references/heartbeat-skeleton.md](references/heartbeat-skeleton.md), from
authorization and project instructions. It is the effective-now snapshot, not a
log: rewrite it from fresh facts, replacing superseded quota, priority and
plans, and keeping in-flight locators and unfinished duties. A confirmed change
applies in that beat; a lowered quota alone cancels nothing. A report-only
request disables execution actions. When an updated Skill loads, reconcile the
heartbeat once with current rules, latest valid instructions and fresh seat
facts, keeping user limits and the frontier.

After close-out, cancel the native heartbeat or stop scheduling the next
sleep. Having no ready task now is not
project completion. Do not hard-code other hosts' scheduler APIs.

## Delivery

Prefer the selected, authorized Workflow sync/merge when a PR is not required:
a PR is not opened merely for handoff when that sink is suitable.
If PRs exist, advance actionable ones first on contested suitable
capacity; other authorized work continues in parallel across permitted CLIs.
A blocked PR keeps an owner and next action without a global hold. Honor
acceptance, explicit PR requests, branch protection, stop-intake, selected
sink, and write ownership.

## Main execution loop

1. **Recover and observe.** Read worker/run records, relevant
   Git/Forge state, and fresh Runner evidence. Use exact owned sessions and
   current platform Skills. Observe busy workers without injecting "status?"
   messages or polling raw frames as a human UI. Do not replay a prompt whose
   acceptance or effects are known or uncertain; investigate the existing action
   first. Steering a running turn is an Agent
   choice, never a Runner policy: pick the mode yourself, read the receipt, and
   never call a not-consumed or `unknown` steer delivered.
2. **Decide and dispatch.** Resolve worker questions within existing
   authorization; escalate only major structural, value, or extra-authority
   decisions. `HUMAN_DECISION_REQUIRED` is considered by the orchestrator
   first. A seat whose `status` says `stale: true` is not a dispatch target;
   an operator-confirmed exception on that one `send`/`steer` is the
   orchestrator's own call; replace it with `drain-restart` at idle
   (see zcode-host-dispatch.md).
   Examine authorized remaining work. Give each clear task directly to a suitable authorized worker as a new session; split or parallelize only when the work itself needs it. The count is a ceiling, not a target to fill; never invent work or expand authorization. At the hard cap, stop one seat before starting any new one (stop-before-start).
   State the task, working location, write ownership,
   delivery requirements, and the doc-impact call in its prompt; merely seeing a
   worktree or ledger is not write authorization. Same-file collaboration needs explicit
   coordination and an integrator, not a blanket disjointness rule. Do not
   expand the authorized goal or duplicate claims.
3. **Accept the delivery.** Mission-frontier done triggers review, not automatic finalize. When a worker
   claims completion, judge its actual diff, checks, docs and run records
   against that assignment under the effective global Workflow rules. Reuse
   sufficient evidence for this candidate; return only concrete deviations,
   omissions or invalidated evidence to that worker, and never finalize on
   incomplete evidence or lowered assertions. Worker prose, idle, green CI or
   a successful script exit is not acceptance, and acceptance is not project
   QA: you pick when aggregate QA/doc checks run; unrun ones stay pending
   duties ([qa-evidence.md](references/qa-evidence.md)).
4. **Finalize and synchronize.** Acceptance authorizes that candidate's
   pending finalize: direct its owning worker to finalize and merge, then verify
   remote, Issue, archive, doc docking, and cleanup results: lifecycle facts,
   not QA PASS ([doc-maintenance](references/doc-maintenance.md)).
   Prefer one run at a time; judge safe concurrency. After the baseline moves, direct affected owners to save
   work and rebase/update at a safe boundary. Review conflicts and revalidate changes; do not switch HEAD
   mid-measurement or reuse invalidated evidence. History rewriting needs applicable authorization.
   When records are inconsistent, investigate and direct a scoped repair;
   never fabricate claim identities.
5. **Release and report.** The only legal idle seat is one whose delivery is
   awaiting acceptance; a rejected delivery's repair is the same assignment,
   and an accepted seat keeps only the finalize/cleanup duties it owns. Once
   it owns none (done or explicitly handed off) or the seat is abandoned,
   exact-stop it in that same beat. The stop action is the exact owned session
   `stop` via the matching platform Skill, which ends its ACP holder. Idle is not
   keep-alive or completion. A Host that
   ended its turn while workers are in flight, or with delivery, acceptance or
   close-out open, is not an idle worker: keep it and send it no "continue"; its
   next beat is a worker event. Before quiescence, reconcile actual owner
   goal/stop with heartbeat project.goal/stop, active/pending (authorized backlog
   and aggregate QA/doc duties); completed worker/run/batch doesn't end an
   open mandate. If open, step 2 selects actionable authorized work/duties
   within grants/caps; claim issues only while intake open. Keep
   all-blocked work event-driven. Cancel on completed scope/duties or stop
   boundary after in-hand close-out. Keep recovery info; assign the rest an
   owner. Direct cleanup of completed, unreferenced
   worktrees/branches; protect in-flight work and evidence. Session stop, acceptance, merge, closure and cleanup are different facts, not
   interchangeable completion labels.

## Ending a run

When ending a project run, finish every in-hand authorized task and each
claimed/in-flight issue of this run; merge their worktrees/branches, remove
branch tails, and clean the workspace per Kaola Workflow close-out. Do not park
unfinished branches.

After a human stop boundary ("until 5pm/done/CONDITION"), accept/dispatch no
tasks and claim/start no issues. Time-up still requires that close-out; it is
not the scoped pause below.

Only "stop here and continue later" with stated scope pauses cleanup and permits
recovery-preserving branches; do not merge or clean beyond that scope.

Honor scoped user stops; otherwise end only after step 5 reconciles the goal,
stop boundary and pending duties.

New authorized work or another task gets a fresh `start` under a new standard
name, never a finished seat; `--resume`/`--continue` recover the same assignment
only.

## Dispatch notes

Call the matching platform Runner Skill by its installed directory. Pass the
selected authorized `--tier`, default included; read its receipt before the
first send (zcode-host-dispatch.md). Do not pass a permission-mode override
unless the human wrote one. One dispatch prompt per ready session.

The worker is not the orchestrator. Its prompt should name the authorized
scope, whether Workflow is on, its child worktree and write ownership, that it
must not self-finalize before acceptance, and that irreversible or value choices
print `HUMAN_DECISION_REQUIRED` and wait.

### Issue-scoped names, one issue per run

One run claims one real issue: never a bundle claim, worktree, ledger or
session spanning several, and collaborating workers share that issue's run under
distinct names. Choose the real open issue before start, name the session
`<platform>-<CODE>-i<ISSUE>-<purpose>` (`droid-KT-i274-parser`) with `CODE` the
heartbeat's declared project short code, verify it in the start receipt, and
keep the rule on later dispatches and restarts. Hosts, diagnostics and
issue-less tasks carry no issue number and never an invented one. Detail and
negatives: [references/issue-dispatch.md](references/issue-dispatch.md).

## Report

Use the user's report format; otherwise one compact current-work table plus
outstanding close-out and pending QA items. Include task/progress, meaningful
model mismatches, blockers, and next action. For non-pool seats, per platform report `live N /
authorized M` and the seats stopped this beat; N > M with no stop that beat
violates the cap. Pool seats report live seats marked exempt. Drop stale stopped rows from reports. Keep duties traceable in
existing records and reuse existing Runner `stop`/`start`: no session state
machine, quota engine, or close-out dashboard or ledger.
