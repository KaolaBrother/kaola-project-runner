# Canonical root and Workflow worktrees

Decision defaults for ordinary Workflow-backed project work, plus the one
mechanical binding an Orchestrator sets at setup. Not a second lifecycle engine.

## Facts

The **canonical project root** is the consuming project's main Git checkout: the
Git top-level the human named as the project, not a Workflow-owned child. A
**child worktree** is a linked Git worktree that Kaola Workflow created or
recovered for one claim (often under `.kw/worktrees/`, but path shape is not an
authorization rule). Each linked worktree is itself a Git top-level, so two of
them can share one remote and still carry different Runner `repo` identities.
A Runner `repo` is the realpath of the Agent-selected Git top-level, not proof
that the path is the canonical project root.

## Orchestrator binding

An Orchestrator binds the root the human chose, once, before any dispatch:

```bash
export KAOLA_PROJECT_RUNNER_CANONICAL_REPO=/abs/path/to/project
```

The Runner then checks it mechanically on every `start`, so no dispatch re-proves
the path by hand. An omitted `--repo` is completed from the binding; an explicit
`--repo` must resolve to exactly that root; anything else - a child worktree of
the same repository, an unrelated checkout, or a binding that is not a Git
top-level - returns `canonical-root-mismatch` or `canonical-root-invalid` with
`mutation_performed: false` before any process, session, or record exists. An
accepted dispatch reports `canonical_repo` in its receipt. Name the child
worktree in the worker's prompt, never in Runner `--repo`.

A session that already exists keeps its own `--repo`, so a legacy worktree-rooted
session can still be observed and exactly stopped by its verified original
locator. Pair that stop with `--expected-holder-instance-id` from the session's
own record, so a same-named session rebuilt by a later holder instance is refused
rather than stopped. Without the binding exported, none of this section applies.

## Normal path

1. Start the worker at the bound canonical project root.
2. From that runtime's main conversation, ask it to invoke its installed
   `workflow-next`.
3. Let that runtime and its Workflow create, resume, recover, or otherwise
   reconcile the run, branch, mission ledger, and child worktree.
4. Keep Runner responsible only for exact-session transport, model selection,
   observation, prompt delivery, and exact stop.
5. Keep `kaola-workflow-finalize` in the worker conversation; the outer Agent
   verifies evidence and decides whether to direct it.

## Evidence-backed exception

Outside an Orchestrator binding, linked-worktree starts, outer-created branches
and runs, and existing-run recovery are **Agent decisions rather than
transport gates**. The controlling Agent may choose a different startup or
recovery path when current evidence, explicit authorization, review-only work, an
existing handoff, a damaged run, or another concrete circumstance makes that
safer. Report the chosen Git root honestly. The transport never classifies Workflow
mode, and standalone Runner use is unchanged.

## Concurrent sessions

Several exact Runner sessions may share one canonical project root, each keeping
its own name, transport identity, run, branch, and child worktree. Seeing another
run's worktree or ledger is not write authorization. Workers sharing one
issue's run follow [issue-dispatch.md](issue-dispatch.md).

## Host shell cwd

A Host shell may keep its working directory between calls, so a directory that
finalize or sink moves or removes bricks every later call (for example
`spawn /bin/bash ENOENT`). Never `cd` into `.kw/worktrees/` or
`kaola-workflow/issue-N/`; use absolute paths, `git -C`, or a subshell
`( cd ... && ... )`, and return to the project root before finalize or sink.
Subagents follow the same rule. A bricked Host reports `brick`, asks to be
replaced, and stops acting.

## Recovery and migration

Preserve existing work by default; after inspecting Git plus Workflow records the
Agent chooses resume, repair, handoff, or a fresh run. A session already running
in a child worktree is advisory, not a defect: continue there, restart at the
canonical project root with in-session `workflow-next`, or use another Workflow
recovery path. Do not mechanically rebuild, delete, move, or adopt an existing
run, and do not force an outer-created worktree onto a worker that can invoke
`workflow-next` itself.

## Non-goals

Do not turn `.kw/worktrees` into an authorization boundary, move Workflow
lifecycle semantics into platform adapters, add a registry, lock, or daemon, or
stop legitimate review, diagnosis, recovery, and non-Workflow sessions from
starting in a linked worktree when no binding is set.
