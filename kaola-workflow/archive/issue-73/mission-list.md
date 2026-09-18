# Issue #73 — Pin Orchestrator worker dispatch to the canonical project root, and make exact stop instance-safe

Scope is Issue #73 only. Two outcomes, per the Issue body and the owner corrections (the
"单项目单编排者" comment overrides the earlier two-Orchestrator ownership comment; the architecture
review comment adds the stop instance-protection fact):

- A. One explicitly bound canonical project root, used by every Orchestrator-context worker
  `start`; an explicit mismatched `--repo` (including a linked worktree of the same remote) is
  refused before any side effect. Standalone (no binding) and legacy original-locator close-out
  keep today's behavior.
- B. `stop` carries `expected_holder_instance_id` end to end so a same-name/re-created holder
  instance is refused before any stop side effect. No registry, no lock, no daemon, no multi-Host
  arbitration.

## 1. Acceptance tests for both outcomes, failing on the recorded baseline
- status: done
- dispatched: self
- item: Write distinguishing contract tests: (A) with a real main checkout plus two linked
  worktrees on one origin — bound root accepted, symlink spelling resolving to it accepted,
  child worktree refused, unrelated repo refused, missing/invalid binding refused, omitted
  `--repo` completed from the binding, zero process/record side effect on every refusal, on at
  least two platform adapters covering both the PTY and the ACP delegation; standalone (unset
  binding) unchanged; legacy worktree-rooted session still observable and exactly stoppable.
  (B) `stop --expected-holder-instance-id` mismatching the live holder returns
  `holder-instance-mismatch` with `mutation_performed:false` and the session still alive;
  matching id stops; omitted id behaves as today. Record the baseline failures.
- result: `tests/contract/test-issue-73-canonical-root.py`, 29 tests. Baseline on 1f87666:
  16 failures (every canonical-root case, both live-dispatch cases, and 3 of 5 stop-instance
  cases). The first harness draft launched real Codex sessions; it now points tmux and every
  runtime binary at nonexistent paths, so an accepted invocation dies at "tmux executable not
  found" and a refused one says `canonical-root-*` - that contrast is the discriminator. The 12
  tmux sessions that first draft leaked were killed; the unrelated `kaola-9d0873b0` was not
  touched. Registered in `scripts/validate.sh` (all-list plus lane B).

## 2. Canonical-root binding guard in the one shared entrypoint
- status: done
- dispatched: self
- item: Implement the binding in `scripts/kaola-tmux.sh` — the single entrypoint both transports
  and all nine platforms already pass through — as `realpath` normalization, Git-top-level
  validation, completion of an omitted `--repo`, and a typed pre-side-effect refusal on an
  explicit mismatch for `start`. Report the bound root as a bounded receipt fact.

## 3. Exact-stop instance protection through existing fields
- status: done
- dispatched: self
- item: Pass `expected_holder_instance_id` on `stop` in `scripts/kaola-acp.py` and check it first
  in `op_stop` in `scripts/kaola-acp-holder.py`, reusing the existing
  `_holder_instance_mismatch` path so a mismatch refuses before `stop_requested`/state mutation.
- result: 9 changed lines total. The refusal returns before `_exit_after_reply` is ever set, so a
  refused stop leaves the holder serving. `--expected-holder-instance-id` already reached
  `kaola-acp.py` from the shell entrypoint for every command; only the `stop` params dict and
  `op_stop` needed it.

## 4. Shorten the prompt surface the mechanical check replaces
- status: done
- dispatched: self
- item: With the check mechanical, cut the repeated manual path-equality prose from
  `templates/orchestrator/SKILL.md.tmpl`, `references/workflow-worktree.md` and the heartbeat
  skeleton down to the concise binding rule, typed-refusal handling and legacy close-out; keep
  `templates/grok-golden/` frozen; re-render and prove the byte reduction.
- result: rendered `skills/kaola-project-runner/` 55837 -> 55651 bytes. Sources: SKILL.md.tmpl
  16086 -> 16138, workflow-worktree.md 4830 -> 4373, heartbeat-skeleton.txt 6747 -> 6966.
  `templates/grok-golden/` untouched. `host-startup.md` examples were left alone on purpose:
  Issue #72's live test pins `"$WORKER" <op> --repo "$PROJECT"` verbatim for five operations,
  and editing it would reach outside this Issue. Docs docked in `docs/architecture.md` and
  `docs/api.md`.

## 5. Full validation and independent review of the frozen candidate
- status: done
- dispatched: `./scripts/validate.sh` run inline on the candidate: exit 0, whole suite green,
  including the new 29-test #73 suite. Candidate frozen at `a066a80` (parent `1f87666`) on branch
  `workflow/issue-73`, local-only. An independent `code-reviewer` in a clean context is reading
  exactly `a066a80`, briefed on guard-ordering/bypass, false refusals against preserved behavior,
  the `canonical_repo` receipt injection, `op_stop` lock ordering, and whether the new suite can
  pass vacuously; its findings return here for my verdict.
- result: the outer reviewer ACCEPTed `a066a806fc3cea4b76a670a92bb4b2a92fb19571` after its own
  independent review and a clean 29-test / `render --check` run at that SHA. The clean-context
  `code-reviewer` I had dispatched never returned: it was stopped when the previous session
  ended, so it produced **no findings at all** - nothing was reported and nothing was fixed from
  it. The outer ACCEPT stands on its own review, not on that agent.
  Sync: rebased onto main `0dacb07` (which carries #67 and #70). One conflict, in
  `scripts/validate.sh`, where #70 and #73 each appended a suite to lane B - both kept, and the
  lane split re-checked (all 31 = A 12 + B 19, each suite listed once). Both sides' semantics
  verified present afterwards: my guard and stop check, #70's binding-fact fields, #67's ZCode
  redaction. `render-skills.py --write` produced no diff, so the auto-merged generated output
  already equalled a clean render from source. On the new base the Skill payload still shrinks,
  57432 -> 57246 bytes. `./scripts/validate.sh` exit 0 on the rebased candidate `38b177c`.
- item: Run `./scripts/render-skills.py --check` and `./scripts/validate.sh`, freeze the candidate
  SHA, and take an independent clean-context review of that exact diff before handing the
  candidate and raw evidence to the outer reviewer. No finalize, push or close before outer ACCEPT.
