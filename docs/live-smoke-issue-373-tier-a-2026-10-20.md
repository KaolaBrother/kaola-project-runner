# Live ZCode smoke — Issue #373 tier A (2026-10-20)

Controlled fixture, not a managed worker seat. It used one independent, explicitly named ZCode
session and an isolated temporary Git clone, then removed the clone and exact-stopped the session.

## Environment

- Host machine: this MacBook; ZCode CLI/app-server `0.16.9`.
- Runner: the candidate checkout at `.kw/worktrees/issue-373` (holder, adapter, and
  `platforms/zcode.yaml` `tool_shell: "zsh"` from this branch).
- Session: `zcode-KPR-tierA-iso-083525`, record root `/tmp/kpr-373-live2`, direct launch.
- Fixture repo: `/private/tmp/kpr-373-smoke-repo` (local clone of the run worktree).
- Fixture worktree: `/private/tmp/kpr-373-smoke-repo/.kw/worktrees/issue-373-live`, a real
  linked worktree inside the session workspace (the incident's shape).

The first attempt used a fixture worktree under the run checkout itself. It was discarded: this
session's own outer DSH holder (previous, pre-#373 code) also watches that checkout, so its V2
pre-emption repaired a probe worktree and contaminated the evidence. The final smoke is isolated.

## Result

1. The Host ran `cd <fixture-worktree> && pwd` in its Bash tool; stdout was the fixture path.
2. A following `pwd` stayed in the fixture path. `status.tool_cwd` then reported
   `last_known: <fixture-worktree>`, `source: "trace"` — tier A reached the ZCode tool shell
   through the holder → adapter → app-server inheritance chain.
3. From another shell the worktree was removed out of band with
   `git -C <fixture-repo> worktree remove --force <fixture-worktree>`.
4. The next prompt ran `echo shell-ok`. The turn completed with two execute tool calls and no
   failed tool; stdout contained `shell-ok`, and the model reported moving the shell back to the
   main repo. There was no repeating `spawn /bin/zsh ENOENT` loop.
5. The holder's own event log recorded, in order:
   `tool_cwd_vanished` (`trigger: V1`), `tool_cwd_placeholder_created` (`trigger: V1`),
   `tool_cwd_notice_staged`, `tool_cwd_notice_delivered` (`via: steer`), then
   `turn_ended` (`outcome: turn_completed`).
6. `status.tool_cwd` after the recovery reported `placeholder: [<fixture-worktree>]`,
   `repairs: 1`, `notice: "delivered"`, `tool_cwd_errors: []`; the placeholder was an empty
   directory.
7. Exact stop reported `stopped: true`, no residual PIDs, and removed the empty placeholder.
   The fixture repo and record root were then deleted.

## Measured platform detail

On this ZCode build, the Bash tool captures a `cd` only when the resolved directory is inside the
session workspace; a `cd` outside it is reset to the workspace root. The incident's
`.kw/worktrees/<issue>` path is inside the project workspace, so the pinned scenario is the
supported one. The smoke's `status.tool_cwd` source is `trace`, which also verifies the tier A
prerequisite that the tool shell inherits the agent process environment on ZCode.

No install, release, restart of another Host, or managed worker seat was used.
