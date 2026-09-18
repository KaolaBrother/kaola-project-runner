# Issue #72 — issue-scoped Runner session names and one issue per run

Run: `issue-72` · branch `workflow/issue-72` · worktree
`/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner/.kw/worktrees/issue-72`
Canonical repository: `https://github.com/KaolaBrother/kaola-project-runner.git`
(main root `/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner`).
This project's declared short code, as given by the outer Agent for this run: **KPR**.
Implementer session: `claude-code-KPR-i72-naming` (Claude Opus, high, Fast off, ACP, Workflow on).

Goal: the control-plane surfaces (main Skill template, heartbeat skeleton, and the Workflow
reference) require `--session <platform>-<CODE>-i<ISSUE>-<purpose>` for every new issue-backed
ACP dispatch and one real issue per Workflow run, with no new transport gate, registry, daemon,
or Workflow state field, and no edit to the nine worker Skills or to KaolaTerminal.

Hard constraints carried from the authorization:
- Main Skill effective ceiling is **17349 B** (17408 declared minus the 59 B probe in
  `tests/contract/test-issue-49-grok-bot-host.py`; see Issue #71). Trim duplicated prose;
  never raise `templates/budgets.json`. Issue #71 itself is not claimed here.
- Co-active runs to protect: `issue-70` (ZCode binding, live), `issue-65` (evidence archive),
  `issue-68` (merged at `b229f84`, outer close-out pending). Touch no other folder, branch,
  or worktree.
- Downstream KaolaTerminal#274 display is out of Runner scope: state the unknown boundary,
  never claim an end-to-end verification that was not run.

1. **item**: Freeze the contract wording and write it into the three orchestrator templates —
   the naming grammar and project-code slot plus one-issue-per-run in
   `templates/orchestrator/SKILL.md.tmpl`, the detail and negative cases in
   `references/workflow-worktree.md`, the project-code slot and both rules in
   `references/heartbeat-skeleton.txt` — then `render-skills.py --write` and `--check`,
   keeping the rendered main Skill at or under 17349 B by deleting duplicated text only.
   **status**: done
   **dispatched**: self, in `.kw/worktrees/issue-72`; output to
   `templates/orchestrator/{SKILL.md.tmpl, references/issue-dispatch.md,
   references/workflow-worktree.md, references/heartbeat-skeleton.txt}` plus the rendered
   `skills/kaola-project-runner/`.
   **result**: commits `08faeae` and `6d78c61`. The naming grammar, the project-code slot, and
   one-issue-per-run are in the main Skill; the detail, negatives, consumer meaning, and
   non-goals are in the new `references/issue-dispatch.md` (4132 B); `workflow-worktree.md` is
   reconciled from bundle wording to run wording and points at it; the heartbeat skeleton
   declares `本项目短码与仓库身份：` and both rules, and keeps the short code in the Issue #68
   keep list. Paid for by nine duplicate-prose deletions, not by a budget change: the rendered
   main Skill is 17292 B against the 17349 B effective ceiling (`render-skills.py --check`
   PASS). A tenth trim compressed the consumer-boundary paragraph that
   `test-generated-skills.py` pins verbatim; the first full validate caught it and `6d78c61`
   restored the exact wording.

2. **item**: Add `tests/contract/test-issue-72-session-naming.py` asserting the rendered
   surfaces carry the rule, the anchored-name grammar accepts the contract's examples within
   the existing 1–80 syntax and rejects the cross-bind negatives (different issue, different
   repository, malformed, no `i` delimiter), and that no budget was raised; wire it into
   `scripts/validate.sh` (full list plus one lane).
   **status**: done
   **dispatched**: self; output to `tests/contract/test-issue-72-session-naming.py` and
   `scripts/validate.sh`.
   **result**: commit `5c65525`. 14 tests, OK. Baseline check on a `b229f84` export: 7 of the
   14 fail there — every surface-content and template test. The grammar tests state the
   contract's meaning rather than detect regression, and the suite docstring says so along with
   the no-consumer-verified boundary. Wired into `python_suites_all` and lane A.

3. **item**: Produce the real-ACP evidence the acceptance asks for: two simultaneous sessions
   named for one issue keep distinct Runner names, distinct native session IDs, and independent
   transport, and an exact stop of one leaves the other alive; plus the record facts a consumer
   would join on (repository identity, `workflow-state.md` `issue_number`). No harness — direct
   `start`/`status`/`stop` receipts, stored under `kaola-workflow/issue-72/evidence/`.
   **status**: done
   **dispatched**: self, via `scripts/kaola-acp.py` from the issue-72 worktree; output to
   `kaola-workflow/issue-72/evidence/` (raw receipts plus `two-session-isolation.md`).
   **result**: `codex-KPR-i72-probe-a` and `codex-KPR-i72-probe-b` ran simultaneously on the
   same platform, repo and issue with different native `acp_session_id`s
   (`01a0b3d0-a01d-…9e0e` / `01a0b3d0-c860-…9461`), PIDs and holder instances, and each
   answered only its own prompt (`PROBE-A` / `PROBE-B`, both `end_turn`). Stopping probe A
   removed exactly that session — `stopped: true`, `agent_exit_code: 0`, `residual_pids: []` —
   while all nine other live sessions stayed alive, including Issue #70's worker under its
   pre-contract name and four sessions of another project; probe B was stopped afterwards and
   neither probe remains. The name→run join was then applied read-only to real host state with
   four active runs on one repository: each anchored name resolved to its own issue run, while
   the grandfathered name and every other-repository session fell back to unknown.

4. **item**: Dock the rule in project documentation where the repo already keeps it, run
   `./scripts/render-skills.py --check` and `./scripts/validate.sh` on the frozen candidate,
   and record the exact outcomes, the frozen SHA, the diff scope, and the explicit
   downstream-unknown boundary as this run's acceptance package.
   **status**: done
   **dispatched**: self; output to `README.md`, `docs/conventions.md`, `CHANGELOG.md`
   (commit `e674577`) and `kaola-workflow/issue-72/evidence/{acceptance.md,validate-final.log}`.
   **result**: `./scripts/render-skills.py --check` PASS; `./scripts/validate.sh` **exit 0** in
   3m02s, 23 suites OK, 0 FAILED (log kept). Candidate frozen at **`6d78c61`**, four commits
   ahead of `main` `b229f84` and zero behind; `git diff --name-only main..HEAD` over
   `templates/grok-golden`, `templates/budgets.json`, `hosts/`, `platforms/`,
   `scripts/adapters`, every worker Skill and `kaola-workflow/` is empty. The acceptance package
   states the downstream boundary explicitly: KaolaTerminal was not touched and nothing was
   verified end to end against it.

5. **item**: Owner review of `6d78c61` (issue comment 5728871221) found the ordinary-worker
   example in `references/host-startup.md.tmpl` still teaching `codex-kaola-issue-77`, which
   an Agent would copy and thereby bypass this Issue's rule. Make that one example conform to
   the declared-short-code grammar, keep one exact name across all five operations, change only
   that reference and its generated product, add no new validator, and leave the project-level
   ZCode Host example alone (it is not an issue-backed worker; its naming is Issue #74's
   Delegator integration). Then rebase onto the new `main` and re-verify the integration.
   **status**: done
   **dispatched**: self, in `.kw/worktrees/issue-72`; output to
   `templates/orchestrator/references/host-startup.md.tmpl`, its rendered copy, and the
   Issue #72 contract suite.
   **result**: commits `f7cb69d` and `9db4673`, then the rebase. The five worker operations now
   share one exact conforming name, `codex-KT-i274-parser`, matching the examples the main Skill
   and `issue-dispatch.md` already use, plus one sentence naming the contract it comes from. No
   validator was added and no other reference changed. The suite gained the guard that would
   have caught this: every `--session` example in the rendered orchestrator package must parse
   as an issue-scoped name, and `host-startup.md` must keep one exact name across
   start/send/observe/capture/stop. Both new tests fail on the reviewed `6d78c61`.

   The sweep found exactly one further offender, and it was **not** fixed here: the
   `codex-kaola-feature-a` worker examples in `references/zcode-host-dispatch.md`. That is a
   genuine violation of this rule, but the file is the surface Issue #70's in-flight candidate
   is rewriting line by line — the name also appears inside its `event_id` payloads — so
   fixing it here would have manufactured a conflict on a live branch and gone outside the
   "only that reference" instruction. It is recorded as a documented exemption in the test, with
   its owner, and raised to the outer Agent. `zcode-kaola-host` is exempt on different grounds:
   it is a Host, not an issue-backed worker, and Issue #74's Delegator naming owns it.

   Rebased onto `main` `464c4f9` (Issue #71 sunk). One conflict, in `CHANGELOG.md` — an add/add
   at the top of Unreleased — resolved by keeping **both** entries, this run's first. The
   `kaola-workflow/archive/issue-71/` tree that arrived with `main` is intact and byte-identical
   to `main`. Issue #71's integration also changed a fact this run depended on: its equal-length
   probe (`c19cdde`) removed the 59 B the #49 host-invariance test used to append, so
   `main_skill_bytes` 17408 is the real ceiling again and the rendered main Skill sits at
   17292 B with 116 B clear. `9db4673` replaces the now-meaningless derived assertion with the
   declared budget plus the recorded history. `test-issue-49-grok-bot-host.py` was run alone
   three times on the integrated tree: 43 tests, OK each time (one earlier run in the same
   shell reported a transient error that did not reproduce).

Run status: 5 done / 0 in-flight / 0 todo. Missions done establishes readiness only.
Finalize, merge, issue closure, archive, and sink are **not** mission items and have not
happened: nothing is pushed, no PR exists, the branch is local, and the run awaits the outer
Agent's ACCEPT.
