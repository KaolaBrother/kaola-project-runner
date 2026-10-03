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

You own scheduling, acceptance and QA decisions. One Host owns this project.
Helpers may plan, design, research, inspect, test, review, prepare bounded
cross-worker material, synthesize evidence, do explicitly scoped light work,
or execute an assignment. They never continuously select topics, scale the
pool, run another scheduling loop, control other workers, grant permission,
or judge final completion. Sidekick:
[dispatch-collect.md](references/dispatch-collect.md).
Without explicit permission to self-execute, read evidence and direct workers:
do not implement, test, edit project documentation, create worktrees, or mutate
the repository yourself.

Authorized release/install mechanics may stay Host-owned without an issue or
worker solely for them; honor owner allocation and project lifecycle.

## Two entry points

**Ordinary worker supervision** - you dispatch and accept from your own session
with the loop below; that worker carries no Host obligation, no event binding and
no extra gate.

**Host** - you are already a named Host session that loaded this Skill through
the native `/kaola-project-runner` Skill invocation (ZCode) or your platform's
measured entry, and supervise workers on event-driven beats. Outer Agents
start or continue the Host through Kaola-Delegator (`kaola-delegator`).
Use existing project plans for role, authorization and lifecycle; this Skill
creates none. Startup and one Host per root (`host-exists`), plus a
Delegator-inquiry sweep (one owned permission event needs no full sweep):
[host-startup.md](references/host-startup.md) ·
[zcode-native-skill-entry.md](references/zcode-native-skill-entry.md) ·
[host-entry-matrix.md](references/host-entry-matrix.md).
A Host (any platform with a `host_skill_entry`) is event-driven: no
Routine, cron, or sleep loop. Its first prompt names its
`platform`/`session`/`repo`; `KAOLA_ACP_DISPATCHER` carries them to its shell.
Beat mechanics - binding, non-blocking dispatch, ending the
turn as the wait: [references/zcode-host-dispatch.md](references/zcode-host-dispatch.md).
Each inner worker is its own session and process group: an inner stop never
reaches the Host, and the Host's stop sweeps only recorded inner sessions.
Grok Bot is not an entry for this Skill: it loads generated `kaola-delegator`,
which starts one Host of any platform that loads this Skill. `--platform grok` is the
Grok CLI worker; `--platform grok-bot` is invalid. Do not create a Grok Bot
Routine to run this Skill. Keep the Host shell cwd at the canonical root: never
`cd` into a worktree finalize/sink may remove; use absolute paths, `git -C`, or
`(cd ... && ...)`.

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
with fresh user permission per task. Delegate substantial planning, design or
review to an available authorized seat when its profile or the owner's
task-specific judgment makes it a better fit than your own known model/preset.
The heartbeat holds the three Class meanings and a compact capability
summary. Catalog profiles stay in
[profile-catalog.md](references/profile-catalog.md). Exact grants stay in the
heartbeat authorization. At a dispatch decision, project eligible candidates
instead of keeping the profile roster in routine context
([dispatch-collect.md](references/dispatch-collect.md)).

Obey owner/project and single-writer rules. Holds stop only source-named actions.
Distinguish implementation prerequisites, merge order and resource occupancy;
a copied Host summary alone establishes no dependency. Unaffected authorized
work proceeds.

### Selected platform

Call the matching platform Runner by its installed directory
`<id>-kaola-project-runner`. Every platform's default transport is ACP.
Eligible seats come from the dispatch projection, not a roster in this Skill.

### Progressive disclosure

This Skill loads on its own. Load one selected worker Skill only at dispatch, a
reference only when the current step needs it, and never read script source or
whole files into context: receipts, hashes, counts and bounded excerpts are the
evidence. Ordinary `observe`, `status` and `capture --lines` receipts stay bounded
(`truncated` names dropped fields); `capture --full` is the only unbounded
request.
Never log in, relogin, switch accounts, or repair credentials. A confirmed limit or account refusal follows [quota-packages.md](references/quota-packages.md); that rule does not change the count cap.

### Defaults

| Item | Default / rule |
|---|---|
| Allowed CLIs | See Authorization above. No authorized task: ask; start no worker or heartbeat. |
| Count | Named CLI without a count: one; it bounds live processes. |
| Model / transport | Platform `--tier default`, Fast off, default transport. Explicit human choices win. Resume preserves saved native choices. |
| Other tiers | Only default is common; tiers are platform-specific/unranked. No automatic model, tier, or transport switch; only owner-authorized model/preset changes stay within runtime. |
| Workflow | On. If explicitly off or unavailable, use authorized PR/verification delivery and disclose the limitation; do not fake Workflow records. |
| Heartbeat | Non-Host: 30 minutes unless specified; zero or "no heartbeat" means one-shot; one host-native carrier, else same-session sleep, never both. Host beats are event-driven (Heartbeat). |
| Permissions | Per platform, not one global bypass. Honor explicit permission-mode overrides. Ordinary approval leftovers are handled here within authorized scope, not routinely sent to the human. |
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
   Examine authorized remaining work. Give each clear task directly to a suitable authorized worker as a new session, chosen from the current eligible-candidate projection by owner direction, class responsibility, profile/task fit and capacity; past dispatch or success informs that choice, never replaces it. Split or parallelize when independent parts gain real time or coverage. The count is a ceiling, not a target to fill; never invent work or expand authorization. At the hard cap, stop one seat before starting any new one (stop-before-start).
   Before planning, assigning or judging QA, read
   [qa-evidence.md](references/qa-evidence.md) unless the current version is
   already in context. Call `<id>-kaola-project-runner`. Pass the selected authorized `--tier`,
   default included; read its receipt before the first send
   (zcode-host-dispatch.md). Do not pass a permission-mode override unless the
   human wrote one. One dispatch prompt per ready session. An adopted research, QA, or report
   plan — one item or a bounded fan-out — runs through the dispatch/collect
   entry ([dispatch-collect.md](references/dispatch-collect.md)); a simple exact
   selection skips the Sidekick. You still accept and exact-stop. State the task,
   working location, write ownership, constraints, delivery requirements, and
   the doc-impact call in its prompt, plus whether Workflow is on. That prompt
   carries the assignment only: never orchestration policy or the seat roster.
   The worker must not self-finalize before acceptance; irreversible or value
   choices print `HUMAN_DECISION_REQUIRED` and wait. Merely seeing a
   worktree or ledger is not write authorization. Same-file collaboration needs explicit
   coordination and an integrator, not a blanket disjointness rule. Do not
   expand the authorized goal or duplicate claims. Pass still-valid candidate
   evidence; recheck changed/invalidated facts or actual gaps. Keep required
   project/release checks. Substantive failure: [task-failure.md](references/task-failure.md).
   One run claims one real issue: never a bundle claim, worktree, ledger or
   session spanning several, and collaborating workers share that issue's run under
   distinct names. Choose the real open issue before start, name the session
   `<platform>-<CODE>-i<ISSUE>-<purpose>` (`droid-KT-i274-parser`) with `CODE` the
   heartbeat's declared project short code, verify it in the start receipt, and
   keep the rule on later dispatches and restarts. Hosts, diagnostics and
   issue-less tasks carry no issue number and never an invented one. Detail:
   [references/issue-dispatch.md](references/issue-dispatch.md).
3. **Accept the delivery.** Mission-frontier done triggers review, not automatic finalize. When a worker
   claims completion, judge its actual diff, checks, docs and run records
   against that assignment under the effective global Workflow rules. Reuse
   sufficient evidence for this candidate; return only concrete routine deviations,
   omissions or invalidated evidence to that worker, and never finalize on
   incomplete evidence or lowered assertions. Worker prose, idle, green CI or
   a successful script exit is not acceptance, and acceptance is not project
   QA: you pick when aggregate QA/doc checks run; unrun ones stay pending duties.
4. **Finalize and synchronize.** Acceptance authorizes that candidate's
   pending finalize: direct its owning worker to finalize and merge, then verify
   remote, Issue, archive, doc docking, and cleanup results: lifecycle facts,
   not QA PASS ([doc-maintenance](references/doc-maintenance.md)).
   Prefer one run at a time; judge safe concurrency. After the baseline moves, direct affected owners to save
   work and rebase/update at a safe boundary. Review conflicts and revalidate changes; do not switch HEAD
   mid-measurement or reuse invalidated evidence. History rewriting needs applicable authorization.
   When records are inconsistent, investigate and direct a scoped repair;
   never fabricate claim identities.
5. **Reclaim seats and report.** The only legal idle seat is one whose delivery is
   awaiting acceptance; a rejected delivery's repair is the same assignment unless substantive (task-failure),
   and an accepted seat keeps only the finalize/cleanup duties it owns. Once
   it owns none (done or explicitly handed off) or the seat is abandoned,
   exact-stop it in that same beat. The stop action is the exact owned session
   `stop` via the matching platform Skill, which ends its ACP holder. Idle is not
   keep-alive or completion. New authorized work or another task gets a fresh
   `start` under a new standard name, never a finished seat;
   `--resume`/`--continue` recover the same assignment only.

   Keep Hosts with in-flight or open delivery/acceptance/close-out; no "continue";
   next beat: worker event. Before quiescence match owner/heartbeat project.goal/stop
   and QA/docs; worker done ends no open mandate.
   [duty-reconcile.md](references/duty-reconcile.md).
   Claim only with intake open. Blocked duties keep next action/reopening condition
   in existing heartbeat values. Assignment-local retry bounds imply no project
   pause; owner/project bounds keep scope. Worker stop/replacement never resets
   attempt limits. Stop/pause/cleanup: Ending a run;
   stop/acceptance/merge/closure/cleanup differ.

## Ending a run

When ending a project run, finish every in-hand authorized task and each
claimed/in-flight issue of this run; merge their worktrees/branches, remove
branch tails, and clean the workspace per Kaola Workflow close-out. Do not park
unfinished branches as the normal end.

Do not accept or dispatch new tasks after the stop boundary. Do not claim or
start new issues. After time-up, still finish in-hand and merge/clean.

The time/condition boundary is not the scoped pause. Only an explicit owner
"stop here and continue later" with stated scope skips cleanup and permits
recovery-preserving branches; do not merge or clean beyond that scope.

## Report

Use the user's report format; otherwise one compact current-work table plus
outstanding close-out and pending QA items. Include task/progress, meaningful
model mismatches, blockers, and next action. For non-pool seats, per platform report `live N /
authorized M` and the seats stopped this beat; N > M with no stop that beat
violates the cap. Pool seats report live seats marked exempt. Drop stale stopped rows from reports. Keep duties traceable in
existing records and reuse existing Runner `stop`/`start`: no session state
machine, quota engine, or close-out dashboard or ledger.
