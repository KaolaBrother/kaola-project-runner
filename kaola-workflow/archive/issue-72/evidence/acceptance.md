# Issue #72 — worker self-verification package

Frozen candidate: **`6d78c61`** on `workflow/issue-72`, four commits ahead of `main`
(`b229f84`) and zero behind at freeze time. Worktree clean. Nothing pushed, no PR, no
finalize, no archive, no sink, no issue close, no release, no global install.

```text
6d78c61  fix(orchestrator): restore the verbatim consumer-boundary paragraph
e674577  docs: dock the issue-scoped dispatch rule (Issue #72)
5c65525  test(issue-72): pin the issue-scoped naming and one-issue-per-run contract
08faeae  feat(orchestrator): require issue-scoped dispatch names and one issue per run
```

## Diff scope

```text
 CHANGELOG.md                                              |  28 +
 README.md                                                 |  18 +-
 docs/conventions.md                                       |  14 +
 scripts/validate.sh                                       |   2 +
 skills/kaola-project-runner/SKILL.md                      |  53 +--
 skills/.../references/heartbeat-skeleton.md               |   8 +-
 skills/.../references/issue-dispatch.md                   |  75 +
 skills/.../references/workflow-worktree.md                |  14 +-
 templates/orchestrator/SKILL.md.tmpl                      |  53 +--
 templates/orchestrator/references/heartbeat-skeleton.txt  |   8 +-
 templates/orchestrator/references/issue-dispatch.md       |  75 +
 templates/orchestrator/references/workflow-worktree.md    |  14 +-
 tests/contract/test-issue-72-session-naming.py            | 241 +
 13 files changed, 535 insertions(+), 68 deletions(-)
```

`git diff --name-only main..HEAD` over `templates/grok-golden`, `templates/budgets.json`,
`hosts/`, `platforms/`, `scripts/adapters`, every worker Skill package, and `kaola-workflow/`
is **empty**. The nine worker Skills, the adapters, the transports, the manifests, the frozen
golden, the Grok Bot bridge, and every other run's folder are byte-identical to `main`.

## Commands and exact outcomes

```text
./scripts/render-skills.py --check
  render-skills: PASS (9 workers + kaola-project-runner + grok-bot host:
  1 bridge skill, 2526 B, content stage, unpinned (not saveable); budgets OK)

./scripts/validate.sh
  exit 0, 3m02s, 23 suites OK, 0 FAILED
  full log: validate-final.log

python3 tests/contract/test-issue-72-session-naming.py
  Ran 14 tests — OK
```

Byte ceiling: `skills/kaola-project-runner/SKILL.md` renders at **17292 B**, under
`main_skill_bytes` (17408) and under the **17349 B** effective ceiling that the 59 B probe in
`test-issue-49-grok-bot-host.py` imposes (Issue #71) — 57 B to spare. `templates/budgets.json`
is unchanged. The new section was paid for by deleting duplicated prose in nine places
(allowlist prose already in the Defaults table, the repeated "no allowlist, no heartbeat",
a repeated prompt-replay rule, the idle-holder restatement, a duplicated dashboards ban,
close-out detail already in loop steps 4-5, a repeated Grok Bot carrier sentence, a repeated
report duty, and two Defaults cells restated in the paragraph below the table).

One trim was wrong and was reverted: the Consumer-project boundary paragraph is pinned
verbatim by `test-generated-skills.py`. The first full validate run caught it (exit 1,
`FAILED: test-generated-skills.py`); `6d78c61` restores the exact wording and the re-run is
the exit-0 above.

## Acceptance items

1. **Template and rendered Skill/heartbeat contain the rule and the project-code slot; render
   check and validation pass; `skills/` is not hand-edited.** Met. The rule is in
   `templates/orchestrator/SKILL.md.tmpl`, `references/issue-dispatch.md`, and the heartbeat
   skeleton, which declares `本项目短码与仓库身份：` and carries the short code in the Issue #68
   keep list so a per-beat rewrite cannot drop it. Everything under `skills/` was produced by
   `render-skills.py --write`; `--check` is green, and the suite asserts template/rendered
   equality for both references.
2. **Two simultaneous workers for one issue keep distinct names and their own transport
   identity, and both can be associated with the same issue run.** Met on real ACP — two
   same-platform, same-repo, same-issue sessions with different native `acp_session_id`s,
   PIDs and holders, each answering only its own prompt; see `two-session-isolation.md`.
   The downstream *display* was not exercised (below).
3. **Different issue numbers, same number on another repository, malformed or old names, and
   multiple active runs never cross-bind.** Asserted in the suite, and demonstrated on live
   host state where four active runs share one repository: each anchored name resolved to its
   own run, while a grandfathered non-conforming name and every other-repository session fell
   back to unknown rather than being guessed. The "same number, different repository" leg is
   contract- and test-level only: this host has active runs for one repository.
4. **Running sessions and native ACP ids unaffected; no extra transport gate, daemon,
   registry, or Workflow state field.** Met. Nine live sessions, including Issue #70's worker
   under its pre-contract name and four sessions of another project, were untouched across
   this run; an exact `stop` removed exactly one session and nothing else. The suite asserts
   the single 1-80 validator is unchanged, that no worker Skill learned an issue rule, that
   issue-less names still validate, and that no budget or state field moved.

## Boundary — what this run did not verify

- **KaolaTerminal was not touched and nothing was verified end to end against it.** This
  repository ships no name parser and no consumer. Whether KaolaTerminal#274 draws the bar
  from these names is that repository's scope; the Runner side stops at producing the name and
  the facts a consumer must check.
- The name→run join shown in the evidence was computed read-only by applying the written rule
  to real host state. It shows the facts are present and sufficient; it is not an implementation.
- This run's own short code **KPR** and the canonical repository
  `https://github.com/KaolaBrother/kaola-project-runner.git` are recorded here and in the
  mission list. They are this project's declaration, not a value hardcoded into the contract
  or into any consuming project — the contract only requires that each consuming project's
  heartbeat declare one.
- Self-verification only: implementation, tests, and this package were produced by the same
  worker. No independent review agent was dispatched (none was authorized).

---

## Round 2 — owner review fix and integration (frozen at `9db4673`)

Owner review of `6d78c61` (issue comment 5728871221) rejected an example, not the contract:
`references/host-startup.md.tmpl` still taught `codex-kaola-issue-77` in the ordinary-worker
flow, which an Agent would have copied straight past the new rule.

**Fixed:** the five operations now share one exact conforming name, `codex-KT-i274-parser`,
with one sentence naming the contract it follows. Only that reference and its generated copy
changed; no validator was added; the project-level `zcode-kaola-host` example was left alone
as instructed.

**Guard added:** every `--session` example in the rendered orchestrator package must parse as
an issue-scoped name, and `host-startup.md` must keep one exact name across the five
operations. Both tests fail on `6d78c61`.

**Raised, not fixed:** `references/zcode-host-dispatch.md` teaches `codex-kaola-feature-a` for
worker start/send/observe/capture — a real violation of this rule. It sits in the file Issue
#70's in-flight candidate is rewriting line by line (the name is also inside its `event_id`
payloads), so fixing it here would have created a conflict on a live branch and exceeded the
"only that reference" instruction. Recorded as a documented exemption with its owner. **This
needs an owner decision: fold it into Issue #70's candidate, or a follow-up after #70 merges.**

**Rebase:** onto `main` `464c4f9`. One add/add conflict in `CHANGELOG.md`, resolved by keeping
both Unreleased entries. `kaola-workflow/archive/issue-71/` arrived with main and is
byte-identical to it — `git diff --name-only main..HEAD -- kaola-workflow/` is empty.

**Integration change re-verified:** Issue #71's `c19cdde` made the #49 host-invariance probe
equal-length, so the 59 B deduction this run budgeted against is gone and `main_skill_bytes`
17408 is the true ceiling. The rendered main Skill is **17292 B, 116 B clear**. `9db4673`
replaces the derived assertion with the declared budget and keeps the history as a named fact.
`test-issue-49-grok-bot-host.py` alone: 43 tests OK, three consecutive runs.

```text
./scripts/render-skills.py --check   PASS (budgets OK)
./scripts/validate.sh                exit 0, 2m40s, 23 suites OK, 0 FAILED  (validate-rebased.log)
test-issue-72-session-naming.py      Ran 16 tests — OK
```

Frozen at **`9db4673`**, six commits ahead of `main` `464c4f9`, zero behind, worktree clean,
branch local-only. `git diff --name-only main..HEAD` over `templates/grok-golden`,
`templates/budgets.json`, `hosts/`, `platforms/`, `scripts/adapters`, every worker Skill,
`zcode-host-dispatch.md.tmpl`, and `kaola-workflow/` is empty. Still no push, PR, finalize,
archive, sink, or issue close.

### Alignment read against Issue #74 (`380ca2b`, on `workflow/issue-74`, not yet on main)

Read, not merged. No conflict with this candidate: #74 rewrites the top of `README.md`
(lines 2-42) and the Grok Bot paragraph, while this run's README addition sits in the
canonical-root collaboration section further down. The principles agree — #74 states "several
issues are not a bundle", which is this Issue's one-issue-per-run rule seen from the entry-level
table.

One foreseeable follow-up, flagged rather than pre-guessed: #74 names the Host session
`zcode-KPR-orchestrator-main` — a short-coded but deliberately **not** issue-backed name. This
run's guard exempts the Host example by its current literal value, `zcode-kaola-host`. When #74
lands its rename, that one line in `ExamplesDoNotTeachTheOldName.NOT_ISSUE_BACKED` needs the new
value; the failure will be a single explicit test message naming the session, not a silent gap.
