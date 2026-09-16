---
name: kaola-project-runner
description: "Use when the controlling Agent should supervise explicitly authorized CLI workers through the seven platform Runner Skills: recover live authorization, dispatch and review work, accept deliveries before finalize, and stop idle sessions without dropping close-out duties."
---

# Project Runner

This Skill is the main control-plane Skill. It is not a platform Runner and has
no transport adapter. The seven platform Runner Skills are workers: they only
identify, start, send, wait, permit, observe, capture, and stop an exact owned
session. Kaola-Workflow, when used, owns worker-side claim, Mission List,
worktree, finalize, archive, and sink.

You own scheduling and acceptance decisions. Helpers may research, inspect,
test, review, or execute assigned work. They must not take over continuous topic
selection, scaling, cross-worker scheduling, or final completion judgment.

Without explicit permission to self-execute, read evidence and direct workers.
Do not implement, test, edit project documentation, create worktrees, or mutate
the repository yourself.

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
seven supported platforms, including Codex, are eligible when named.

Record the human's CLI, model/effort, count, and capability restrictions in the
consuming project's run records, not in this Skill. A named CLI without a count
defaults to one. Respect explicitly authorized multiple model assignments or
open-ended concurrency; do not invent a quota system.

Follow human instructions, project contracts, and evidenced shared-resource
constraints. A serial build, GPU, port, or cache constraint must not block
unrelated parallel work. Do not invent global serialization or an extra
resource-management subsystem.

### Supported workers

Derived from this checkout's platform manifests (not a hardcoded roster):

| Platform id | Skill directory | Display name | Default transport |
|---|---|---|---|
| claude-code | `claude-code-kaola-project-runner` | Claude Code Kaola Project Runner | pty |
| codex | `codex-kaola-project-runner` | Codex CLI Kaola Project Runner | acp |
| cursor-cli | `cursor-cli-kaola-project-runner` | Cursor CLI Kaola Project Runner | acp |
| devin | `devin-kaola-project-runner` | Devin CLI Kaola Project Runner | acp |
| grok | `grok-kaola-project-runner` | Grok Kaola Project Runner | acp |
| kimi-cli | `kimi-cli-kaola-project-runner` | Kimi CLI Kaola Project Runner | acp |
| opencode | `opencode-kaola-project-runner` | OpenCode Kaola Project Runner | acp |

### Hosts

This Skill is host-neutral. Native skill-directory installs exist for Codex,
Claude Code, Cursor, and Devin; there the seven workers are sibling Skill
directories next to this one, called by their installed directory. A **bridge
host** (Grok Bot today) reaches this checkout through one thin account Skill
instead: it binds an execution target first (Local Computer, or the cloud Agent
Computer), asks that target's device-local locator `kaola-project-runner-locate` for the verified
repo root ROOT, and loads only `ROOT/skills/kaola-project-runner` and, per dispatch,
one selected `ROOT/skills/<platform id>-kaola-project-runner`. On a bridge host, before
each worker dispatch run the locator attestation on the bound target
(`kaola-project-runner-locate --target local|cloud --expect-revision <accepted> --project <root>
--worker <platform id> --session <name>`) and refuse any `refused` receipt: the
consumer project, the selected worker script under the same ROOT, and a session of
the exact name must all be on that one target (`--target` is your declaration;
compare the receipt's `host.fingerprint` with the value recorded when that
target's locator was registered; session ownership is the worker preflight's
proof). Local Computer and the cloud Agent Computer never reach each other's
files, CLIs, tmux, or sessions, and nothing clones, installs, or updates Local
Computer from the cloud. Grok Bot is a host, not a worker and not an eighth
platform: `--platform grok` is the Grok CLI worker; `--platform grok-bot` is
invalid.

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
whole files into context: receipts, hashes, counts, and bounded excerpts are the
evidence. Ordinary `observe`, `status`, and `capture --lines` receipts are
bounded on both transports (a truncation marker names the dropped part and the
sha256 of the whole stream); `capture --full` is an explicit, unbounded request.

### Defaults

| Item | Default / rule |
|---|---|
| Allowed CLIs | None until named. Fresh invocation with no allowlist: ask; do not start. |
| Count | Named CLI without a count: one. |
| Model / transport | Platform `--tier default`, Fast off, default transport. Explicit human choices win. Resume preserves saved native choices as the Runner defines. |
| Upgrade | Needs a clear worker/task/model-effort choice or an applicable explicit upgrade preset; ask only if unclear. No automatic upgrade or transport switch. |
| Workflow | On; the worker's Workflow creates its worktree. If explicitly off or unavailable, use authorized PR/verification delivery and disclose the limitation; do not fake Workflow records. |
| Heartbeat | 30 minutes unless specified; zero or "no heartbeat" means one-shot. Prefer one host-native recurring task, otherwise same-session blocking sleep. Never use both. |
| Permissions | Existing Runner default bypass start. Honor explicit permission-mode overrides. Ordinary approval leftovers are handled here within authorized scope, not routinely sent to the human. |
| Self-execute | Off unless the human explicitly allows it. |
| Cursor | Never use `/model` as a read-only probe. |

`self_hosting_risk` and model mismatches are reported evidence, not automatic
start gates. Bypass is not broader authorization. OpenCode ACP permission
leftovers are a transport fact: do not force PTY or invent a new skip-all gate.

## Heartbeat

Render a project-specific heartbeat from the short skeleton in
[references/heartbeat-skeleton.md](references/heartbeat-skeleton.md), current
authorization, and project instructions. Keep stable policy in this Skill,
project constraints in the consuming project's instructions, and changing
facts in that project's run records. Update the **same** heartbeat when
instructions materially change; replace obsolete text rather than append
conflicting versions. Do not hard-code host tool names into this Skill. A
report-only request disables execution actions.

Native recurring wake and blocking sleep must not be stacked. After close-out,
cancel the native heartbeat or stop scheduling the next sleep. No CLI
allowlist means no heartbeat. Temporarily having no ready task is not project
completion. On Grok Bot the native recurring carrier is one Routine on this Bot;
do not hard-code other hosts' scheduler APIs.

## Delivery

Prefer the selected, authorized Workflow sync/merge when a PR is not
required. A PR is not opened merely for handoff when that sink is suitable.
If PRs exist, advance actionable ones first on contested suitable
capacity; other authorized work continues in parallel across permitted CLIs.
A blocked PR keeps an owner and next action without a global hold. Honor
acceptance, explicit PR requests, branch protection, stop-intake, selected
sink, and write ownership.

## Main execution loop

1. **Recover and observe.** Read existing worker/run records, relevant
   Git/Forge state, and fresh Runner evidence. Use exact owned sessions and
   current platform Skills. Observe busy workers without injecting "status?"
   messages or repeatedly polling raw PTY screens as a human UI. Do not replay
   a prompt whose acceptance or effects are already known or uncertain;
   investigate the existing action first. No automatic fallback/resend, raw
   tmux injection, or global model-picker mutation.
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
   authorized work is executable. ACP and PTY/tmux are the same stop action:
   exact owned session `stop` via the matching platform Runner Skill,
   including ACP holders. Idle is not keep-alive. ACP idle left running is
   not completion and not keep-alive. When the authorized goal is complete,
   or no suitable authorized work is executable, stop remaining idle owned
   sessions, including ACP holders. Then cancel heartbeat once no unfinished
   delivery/sync/cleanup remains. Preserve its existing recovery information
   and give any remaining delivery/sync/cleanup a named owner. Direct safe cleanup of completed, unreferenced worktrees
   and branches; protect in-flight work and evidence. Report active workers
   and outstanding close-out work, then continue the same heartbeat while
   authorized work or unfinished close-out remains. Session stop, candidate
   acceptance, merge, Issue closure and workspace cleanup are different facts,
   not interchangeable completion labels.

## Ending a run

When ending a project run, the default is to finish every in-hand authorized
task and every in-hand issue of this run (already claimed / in flight), then
merge their worktrees and branches, leave no leftover branch tails, and leave
the workspace clean, matching Kaola Workflow close-out (finalize/archive/sink
and unreferenced worktree/branch cleanup already in this Skill). That default
is not an extra engine. Do not park unfinished branches as the normal end of
a project run.

A human stop boundary such as "run until 5pm", "run until done", or
"run until CONDITION" means: after that line, do not accept or dispatch new
tasks, and do not claim or start new issues. Time-up is not drop-everything.
Default after any such termination: still finish in-hand authorized work and
in-hand issues, merge worktrees/branches, and leave the workspace clean. A
clock or condition boundary must not be treated as that skip-cleanup pause.

Only an explicit "stop here and continue later" (stated scope) is a scoped
pause: do not force merge/cleanup beyond that scope; preserve recovery so
work can resume. Only an explicit "stop here and continue later" skips that
cleanup and may leave recovery-preserving unfinished branches.

Honor a user stop request within its stated scope. Otherwise cancel the
heartbeat when the authorized goal is complete, no unfinished
delivery/sync/cleanup remains, and remaining idle owned sessions have been
stopped.

Restart a session only when there is new authorized work. After remaining
idle owned sessions have been stopped, later authorized work starts or
resumes a session only then. Resume with `--resume` when a native session id
is known, otherwise `--continue` or a fresh `start`. Do not keep an idle ACP
or PTY session running as a holder for future work. Reuse existing Runner
`stop` / `start` / `--resume` / `--continue`. Do not invent a session state
machine, quota engine, or extra dashboards.

## Dispatch notes

Call the matching platform Runner Skill by its installed directory. Use Runner
default start (including measured bypass). Do not pass a permission-mode
override unless the human wrote one. Resume with `--resume` when a native
session id is known, otherwise `--continue` or a fresh `start`. One dispatch
prompt per ready session; do not replay a prompt whose effects are known or
uncertain.

The worker is not the orchestrator. Its prompt should name the authorized
scope, whether Workflow is on, write ownership, that it must not self-finalize
before acceptance, and that irreversible or value choices print
`HUMAN_DECISION_REQUIRED` and wait.

## Report

Use the user's report format. Otherwise one compact current-work table plus
outstanding close-out items is sufficient. Include task/progress, meaningful
model mismatches, blockers, and next action. Mention newly stopped sessions
once; do not keep stale stopped rows in every report. Do not require separate
acceptance, finalize, rebase, or close-out dashboards. Keep duties traceable
in existing records without a new state machine or ledger.
