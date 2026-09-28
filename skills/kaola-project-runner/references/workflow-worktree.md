# Canonical root and Workflow worktrees

Decision defaults for ordinary Workflow-backed project work, plus the one
mechanical binding an Orchestrator sets at setup.

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

A Host shell may keep its working directory between calls, so entering a
worktree or issue directory and relying on returning before finalize is not
safe: finalize or sink can move or remove it first and brick every later call
(for example `spawn /bin/bash ENOENT`). The primary procedure is absolute
paths, `git -C`, or a subshell `( cd ... && ... )`, keeping the persistent cwd
at the project root throughout - never `cd` directly into `.kw/worktrees/` or
`kaola-workflow/issue-N/`. Subagents follow the same rule. A bricked Host
reports `brick`, asks to be replaced, and stops acting.

## Foreign files and finalize safeguards

Kaola-Workflow finalize mirrors untracked residue from the main checkout into
the finalize worktree. An upstream defect (tracked as Kaola-Workflow #1110,
unresolved pending a verified fixed-version adoption) can copy a foreign file
into that mirror and then exempt it as machinery-owned, so files belonging to
another session have reached delivered trees (#192, #194, #206; the #206 copy
was a dangling local commit caught before push). Treat finalize residue as
untrusted and keep the duties below.

1. **Convey the constraint.** When a known foreign or protected file or an
   upstream finalize limitation affects the current run, pass that concrete
   constraint to the worker responsible for finalization through existing
   task/run records (dispatch prompt, run duties). This Skill adds no global
   ownership table, scan schedule, classifier, or filter.
2. **The finalizing worker preserves what it does not own.** It reads the
   run's existing Workflow preview/finalization receipts, preserves unrelated
   files, and reports ownership ambiguity or a blocked sink honestly:
   copying a file mechanically does not establish that it belongs to the
   task. Never delete, stage, or adopt unrelated files merely to make the
   checkout clean.
3. **The Host reuses those receipts for acceptance/closeout.** Existing
   receipts plus the candidate diff are the evidence: confirm known protected
   paths did not enter the delivered candidate or archive and that any
   temporary protection was restored. Concrete mismatches return to the
   responsible worker - no second acceptance engine, no unconditional
   duplicate test run.
4. **Run-scoped exclude workaround.** In the presently affected run, keep the
   existing narrow `.git/info/exclude` protection for its already-identified
   protected research files: the finalization owner preserves the original
   exclude bytes, applies the scoped protection before mirroring or sink, and
   restores it on completion or interruption, never overwriting a concurrent
   legitimate edit when restoring. If restoration is unsafe, report the exact
   remaining duty through the existing run record. This is a temporary,
   project-specific compatibility measure carried in that run's records,
   never a global prompt naming any file.

Retire the workaround by conditions, not by issue closure: keep it only while
the affected Kaola-Workflow version is actually used; remove it after an
authorized fixed-version adoption plus the bounded consumer evidence that the
known foreign file stays excluded and unchanged. The general handoff and
receipt duties above are durable and stay.

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
