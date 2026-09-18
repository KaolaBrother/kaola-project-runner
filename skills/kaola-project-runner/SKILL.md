---
name: kaola-project-runner
description: "Use when the controlling Agent should supervise explicitly authorized CLI workers through the nine platform Runner Skills: recover live authorization, dispatch and review work, accept deliveries before finalize, and stop idle sessions without dropping close-out duties."
---

# Project Runner

This Skill is the main control-plane Skill. It is not a platform Runner and has
no transport adapter. The nine platform Runner Skills are workers: they only
identify, start, send, wait, permit, observe, capture, and stop an exact owned
session. Kaola-Workflow, when used, owns worker-side claim, Mission List,
child worktree, finalize, archive, and sink.

You own scheduling and acceptance decisions. Helpers may research, inspect,
test, review, or execute assigned work, never continuous topic selection,
scaling, cross-worker scheduling, or final completion judgment. Without explicit
permission to self-execute, read evidence and direct workers: do not implement,
test, edit project documentation, create worktrees, or mutate the repository
yourself.

## Two entry points

**Ordinary worker supervision** - you dispatch and accept from your own session
with the loop below; that worker carries no Host obligation, no event binding and
no extra gate.

**Orchestrator (ZCode Host)** - you start, or you are, a named ZCode Host session
that loads this Skill and supervises workers on event-driven beats. Its role,
authorization and lifecycle boundary come from the project's existing Project
Plan or already-authorized task plan - never a new schema, never the Host's own
claim of having loaded this Skill. Startup order, the receipt the outer Agent
checks against that plan, and keep-versus-stop: [host-startup.md](references/host-startup.md).

## Consumer-project boundary

For consumer-project work, the Project Runner checkout, templates, generated
files, and installed Skill payload are read-only. Store project-specific
authorization, heartbeat, and run facts in the consuming project. Do not edit
this repository, its templates, generated files, or an installed Skill payload
unless a human explicitly assigned Project Runner development.

## Authorization

Recover existing explicit authorization and live work before asking intake
questions. A Skill update or resumed conversation must not restart intake,
workers, claims or assignments already established. Ask only for missing or
conflicting information.

Allowed CLIs: none without human authorization. On a fresh invocation with no
allowlist, ask which CLIs; do not start workers or register a heartbeat. All
nine supported platforms, including Codex, are eligible when named.

Record the human's CLI, model/effort, count, and capability restrictions in the
consuming project's run records, not in this Skill. A named CLI without a count
defaults to one. Respect explicitly authorized multiple model assignments or
open-ended concurrency; do not invent a quota system.

Follow human instructions, project contracts, and evidenced shared-resource
constraints. A serial build, GPU, port, or cache constraint must not block
unrelated parallel work. Do not invent global serialization or an extra
resource-management subsystem.

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
| grok | `grok-kaola-project-runner` | Grok Kaola Project Runner |
| kimi-cli | `kimi-cli-kaola-project-runner` | Kimi CLI Kaola Project Runner |
| opencode | `opencode-kaola-project-runner` | OpenCode Kaola Project Runner |
| zcode | `zcode-kaola-project-runner` | ZCode Kaola Project Runner |

### Hosts

This Skill is host-neutral. Native skill-directory installs exist for Codex,
Claude Code, Cursor, Devin and ZCode (`~/.zcode/skills`; a workspace
`.zcode/skills` works through `--skills-dir`), where the nine workers are sibling
Skill directories called by their installed directory. A ZCode Host session is one named Runner session like any other:
an inner worker it dispatches, ZCode or not, is a separate session with its own
record entry and process group - an inner stop never reaches the outer Host, and
the outer stop sweeps only recorded inner sessions. A ZCode Host's heartbeat is event-driven: no Routine, cron, or sleep loop, and it
cannot discover its own `platform`/`session`/`repo` - give them in its first
prompt. Each beat: set `KAOLA_ACP_HEARTBEAT_HOST` (a JSON object naming the Host)
on every worker `start`, verify the receipt's `heartbeat_host`, dispatch with
`send --no-wait`
(`in_progress` is accepted, not done) keeping its `dispatch_event_cursor` as the
reading anchor, update the project's `.kaola/heartbeat-prompt.json`, then **end
the turn normally** - that is the wait. Never sleep, poll, blocking-`wait`, or
stop/cancel anything to manufacture a wake-up. A worker turn-end or exit delivers one
full pass here; read the reply through that worker's own Skill from the dispatch
anchor, not the event's `event_cursor`, which sits after it. Beat, event and carrier detail:
[references/zcode-host-dispatch.md](references/zcode-host-dispatch.md). A **bridge host** (Grok Bot today) reaches this checkout through one thin
account Skill instead: it binds an execution target first (Local Computer, or the
cloud Agent Computer), asks that target's device-local locator `kaola-project-runner-locate` for
the verified repo root ROOT, and loads only `ROOT/skills/kaola-project-runner` plus,
per dispatch, one selected `ROOT/skills/<platform id>-kaola-project-runner`. Re-run that
attestation before every dispatch and refuse any `refused` receipt: project,
worker script, and the exact session must all be on that one bound target, which
never reaches the other's files, CLIs, tmux, or sessions. Grok Bot is a host, not a worker and
not a tenth platform: `--platform grok` is the Grok CLI worker, `--platform
grok-bot` is invalid.

On Grok Bot one Routine on this Bot conversation is the only heartbeat carrier:
never stack it with a Codex heartbeat or blocking sleep. Takeover cancels the
previous host heartbeat without stopping in-flight workers.
`HUMAN_DECISION_REQUIRED` stays in this Bot conversation (Needs attention / this
Bot's Notifications). Agent Computer takeover is not CLI decision and not
exact-session stop. A saved bridge is not live adoption; the owner's read-only
Local Computer UAT is the boundary. See
[references/grok-bot-host.md](references/grok-bot-host.md).

### Progressive disclosure

This Skill loads on its own. Load one selected worker Skill only at dispatch, a
reference only when the current step needs it, and never read script source or
whole files into context: receipts, hashes, counts and bounded excerpts are the
evidence. Ordinary `observe`, `status` and `capture --lines` receipts are bounded
on both transports, keeping the newest part and naming what a `truncated` block
dropped; `capture --full` is the only unbounded request.

### Defaults

| Item | Default / rule |
|---|---|
| Allowed CLIs | None until named. Fresh invocation with no allowlist: ask; do not start. |
| Count | Named CLI without a count: one. |
| Model / transport | Platform `--tier default`, Fast off, default transport. Explicit human choices win. Resume preserves saved native choices as the Runner defines. |
| Upgrade | Needs a clear worker/task/model-effort choice or an applicable explicit upgrade preset; ask only if unclear. No automatic upgrade or transport switch. |
| Workflow | On; start at the canonical project root; the worker's Workflow creates its worktree. If explicitly off or unavailable, use authorized PR/verification delivery and disclose the limitation; do not fake Workflow records. |
| Heartbeat | 30 minutes unless specified; zero or "no heartbeat" means one-shot. One host-native carrier, else same-session sleep, never both. |
| Permissions | Existing Runner default bypass start. Honor explicit permission-mode overrides. Ordinary approval leftovers are handled here within authorized scope, not routinely sent to the human. |
| Self-execute | Off unless the human explicitly allows it. |
| Cursor | Never use `/model` as a read-only probe. |

Ordinary Workflow-backed work starts the worker `--repo` at the consuming
project's canonical Git root and asks that runtime's main conversation to invoke
its installed workflow-next; inspect Git and Workflow evidence first.
Linked-worktree starts, outer bundle preparation and existing-run recovery are
Agent decisions on both PTY and ACP, not transport gates. See
[references/workflow-worktree.md](references/workflow-worktree.md).

`self_hosting_risk` and model mismatches are reported evidence, not automatic
start gates. Bypass is not broader authorization. OpenCode ACP permission
leftovers are a transport fact: do not force PTY or invent a new skip-all gate.

## Heartbeat

The heartbeat is the working prompt itself: Codex and Grok Bot run it from their
own timer, a ZCode Host from each worker return or event, on host-native
carriers. Render it from the skeleton in
[references/heartbeat-skeleton.md](references/heartbeat-skeleton.md),
authorization, and project instructions. It is the effective-now snapshot, not a
log: update the **same** heartbeat, replacing superseded quota, priority and
plans, and keeping in-flight locators and unfinished duties. A confirmed change
applies in that beat; a lowered quota alone cancels nothing. A report-only
request disables execution actions.

On a ZCode Host session worker events are the only heartbeat trigger (see
Hosts). After close-out, cancel the native heartbeat or stop scheduling the next
sleep. No allowlist, no heartbeat. Temporarily having no ready task is not
project completion. On Grok Bot the native recurring carrier is one Routine on
this Bot; do not hard-code other hosts' scheduler APIs.

## Delivery

Prefer the selected, authorized Workflow sync/merge when a PR is not required:
a PR is not opened merely for handoff when that sink is suitable.
If PRs exist, advance actionable ones first on contested suitable
capacity; other authorized work continues in parallel across permitted CLIs.
A blocked PR keeps an owner and next action without a global hold. Honor
acceptance, explicit PR requests, branch protection, stop-intake, selected
sink, and write ownership.

## Main execution loop

1. **Recover and observe.** Read existing worker/run records, relevant
   Git/Forge state, and fresh Runner evidence. Use exact owned sessions and
   current platform Skills. Observe busy workers without injecting "status?"
   messages or repeatedly polling raw PTY screens as a human UI. Do not replay a prompt whose
   acceptance or effects are known or uncertain; investigate the existing action
   first. Steering a running turn is an Agent
   choice, never a Runner policy: pick the mode yourself, read the receipt, and
   never call a not-consumed or `unknown` steer delivered. No automatic
   fallback/resend, raw tmux injection, or model-picker mutation.
2. **Decide and dispatch.** Resolve worker questions within existing
   authorization; escalate only major structural, value, or extra-authority
   decisions. `HUMAN_DECISION_REQUIRED` is considered by the orchestrator
   first. Examine authorized remaining work and real parallel opportunities.
   At every heartbeat, match authorized idle workers to safe parallel work and dispatch every suitable match. Leave capacity idle rather than invent work or expand authorization. State the task, working location, write ownership, and
   delivery requirements in its prompt; merely seeing a worktree or Mission
   List is not write authorization. Same-file collaboration needs explicit
   coordination and an integrator, not a blanket disjointness rule. Do not
   expand the authorized goal or duplicate claims.
3. **Accept the delivery.** Mission-frontier done triggers review, not automatic finalize. Inspect the actual
   diff, verification evidence and project acceptance requirements. Use a
   verifier distinct from the implementer where available; if only one
   authorized worker is available, disclose self-verification and still
   satisfy project requirements. Match evidence to the actual candidate and
   affected behavior. Dispatch missing proof or repairs; do not finalize on
   incomplete evidence. Do not lower assertions or substitute worker prose,
   idle, green CI or a successful script exit for acceptance.
4. **Finalize and synchronize.** Once accepted and authorized, direct the
   worker to finalize and merge, then verify remote, Issue, archive, and
   cleanup results. Prefer closing one run at a time, but judge safe
   concurrency. After the baseline moves, direct other affected owners to save
   work and rebase/update at a safe boundary. Review conflicts and revalidate
   affected changes; do not switch HEAD during a measurement or silently reuse
   invalidated evidence. History rewriting needs applicable authorization.
   When existing records are inconsistent, investigate and direct a scoped
   repair using existing tools; do not fabricate claim identities or introduce
   a parallel lifecycle system.
5. **Release and report.** Stop an idle exact session only when no suitable
   authorized work is executable; then stop the rest. ACP and PTY/tmux are the
   same stop action: exact owned session `stop` via the matching platform Skill,
   including ACP holders. Idle is neither keep-alive nor completion. A Host that
   ended its turn while workers are in flight, or with delivery, acceptance or
   close-out open, is not an idle worker: keep it and send it no "continue"; its
   next beat is a worker event. Cancel the heartbeat once no unfinished
   delivery/sync/cleanup remains; preserve existing recovery information and give
   anything remaining a named owner. Direct safe cleanup of completed,
   unreferenced worktrees and branches; protect in-flight work and evidence.
   Report active workers
   and outstanding close-out work, then continue the same heartbeat while
   authorized work or unfinished close-out remains. Session stop, candidate
   acceptance, merge, Issue closure and workspace cleanup are different facts,
   not interchangeable completion labels.

## Ending a run

When ending a project run, the default is to finish every in-hand authorized
task and every in-hand issue of this run (already claimed / in flight), then
merge their worktrees and branches, leave no leftover branch tails, and leave
the workspace clean, matching Kaola Workflow close-out (finalize/archive/sink
and unreferenced worktree/branch cleanup already in this Skill); that default is
not an extra engine. Do not park unfinished branches as the normal end of a
project run.

A human stop boundary such as "run until 5pm", "run until done", or
"run until CONDITION" means: after that line, do not accept or dispatch new
tasks, and do not claim or start new issues. Time-up is not drop-everything:
that same default applies, and a clock or condition boundary is not the
skip-cleanup pause below.

Only an explicit "stop here and continue later" (stated scope) is a scoped
pause: it skips that cleanup, may leave recovery-preserving unfinished branches,
and forces no merge or cleanup beyond its stated scope.

Honor a user stop request within its stated scope; otherwise the heartbeat ends
on step 5's conditions.

Only new authorized work restarts a session once the idle ones were stopped:
resume with `--resume` when a native session id is known, otherwise `--continue`
or a fresh `start`. Do not keep an idle ACP or PTY session running as a holder
for future work; reuse existing Runner `stop` / `start` / `--resume` /
`--continue`, and do not invent a session state machine, quota engine, or extra
dashboards.

## Dispatch notes

Call the matching platform Runner Skill by its installed directory. Use Runner
default start (including measured bypass). Do not pass a permission-mode
override unless the human wrote one. One dispatch prompt per ready session; do
not replay a prompt whose effects are known or uncertain. Resume as under
"Ending a run".

The worker is not the orchestrator. Its prompt should name the authorized
scope, whether Workflow is on, whether `--repo` is the canonical project root or
a Workflow child worktree, write ownership, that it must not self-finalize
before acceptance, and that irreversible or value choices print
`HUMAN_DECISION_REQUIRED` and wait.

## Report

Use the user's report format. Otherwise one compact current-work table plus
outstanding close-out items is sufficient. Include task/progress, meaningful
model mismatches, blockers, and next action. Mention newly stopped sessions
once; do not keep stale stopped rows in every report. Do not require separate
acceptance, finalize, rebase, or close-out dashboards. Keep duties traceable
in existing records without a new state machine or ledger.
