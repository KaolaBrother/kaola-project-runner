# Canonical root and Workflow worktrees

These are decision defaults for ordinary Workflow-backed project work. They are not
transport gates, security boundaries, or a second lifecycle engine.

## Facts

The **canonical project root** is the consuming project's main Git checkout: the Git
top-level the human named as the project, not a Workflow-owned child. A **child
worktree** is a linked Git worktree that Kaola Workflow created or recovered for one
claim (often under that project's `.kw/worktrees/`, but path shape is not an
authorization rule). Each linked worktree is itself a Git top-level. Runner `--repo`
must name some Git top-level; receipts report that selected path as a bounded fact.
`KAOLA_PROJECT_RUNNER_REPO` is the realpath of that Agent-selected Git top-level, not
proof that the path is the canonical project root.

Inspect current Git and Workflow evidence before choosing where to start a worker:
`git worktree list`, `git rev-parse --show-toplevel`, active `kaola-workflow/*/workflow-state.md`
and `mission-list.md`, and existing exact Runner sessions. Those records remain lifecycle
evidence. They do not authorize or refuse transport.

## Normal path

1. Start the runtime worker session with Runner `--repo` bound to the canonical project
   root.
2. From that runtime's main conversation, ask it to invoke its installed `workflow-next`.
3. Let that runtime and its Workflow create, resume, recover, or otherwise reconcile the
   run, branch, Mission List, and child worktree.
4. Keep Runner responsible only for exact-session transport, model selection, observation,
   prompt delivery, and exact stop.
5. Keep `kaola-workflow-finalize` in the worker conversation; the outer Agent verifies
   evidence and decides whether to direct it.

Example: Claude Code is started with `--repo /path/to/project` (the main checkout). The
controlling Agent sends a prompt that names issue #52 and asks the CLI to invoke
`workflow-next`. Workflow claims that one issue and creates `.kw/worktrees/issue-52` (or
resumes that run). The Runner session identity stays the canonical-root session; the
child worktree is Workflow's working location, not a second Runner `--repo` unless the
Agent later chooses otherwise.

## Evidence-backed exception

Linked-worktree starts, outer-created branches and Mission Lists, and existing-run
recovery are **Agent decisions rather than transport gates**. The controlling Agent may
choose a different startup or recovery path when current evidence, explicit authorization,
review-only work, an existing handoff, a damaged run, or another concrete circumstance makes
that safer. Report the chosen Git root honestly. PTY and ACP retain identical decision
authority: neither transport classifies Workflow mode or rejects a linked worktree.

Example: Issues #50/#51 already had live bundles and child worktrees. The controlling Agent
stopped the earlier in-worktree Claude Code sessions and restarted at the canonical
repository root with instructions to invoke `workflow-next`. That was an Agent-chosen
correction for those runs, not a machine refusal and not a universal requirement. Starting
inside a linked worktree for review, diagnosis, recovery, or a non-Workflow task remains
valid when the Agent selects that Git top-level.

## Concurrent sessions

Several exact Runner sessions may share one canonical project root. Each session keeps its
own session name and transport identity. Their Workflows may own distinct runs,
branches, and child worktrees. Seeing another run's worktree or Mission List is not write
authorization. Several workers may share one issue's run and Mission List under distinct
Runner names and native sessions; the naming and one-issue-per-run rules that make that
association explicit live in [issue-dispatch.md](issue-dispatch.md).

## Recovery

Preserve existing work by default. After inspecting state, the Agent chooses resume,
repair, handoff, or a fresh run according to Workflow rules and evidence. Do not
mechanically rebuild, delete, move, or adopt an existing run. Do not force an
outer-created worktree onto a worker that can invoke `workflow-next` itself.

## Migration

A session already running in a child worktree is advisory, not a defect:

1. Preserve work and inspect Git plus Workflow records.
2. Then choose whether to continue there, stop and restart at the canonical project root
   with in-session `workflow-next`, or use another Workflow recovery path.

## Non-goals

Do not make `runtime-tmux.sh` reject linked worktrees. Do not require the transport to
classify Workflow mode. Do not turn `.kw/worktrees` into a security or authorization
boundary. Do not move Workflow lifecycle semantics into platform adapters. Do not prevent
legitimate review, diagnosis, recovery, or non-Workflow sessions from starting in a linked
worktree.
