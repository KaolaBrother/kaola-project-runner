# Finalization Summary — Issue #68

Heartbeat 只保留最新有效约束：额度变更立即生效，每拍清除过时项目记录

- run: issue-68 · branch `workflow/issue-68` · sink `merge` · issue #68
- candidate accepted by the outer coordinator: `19eda62387db96f579970f92bae69b8f2065e9a0`
- head at finalization: `77a9ecf` (the documentation docking commit on top of the accepted merge)
- missions: 7, all `done`; no `BLOCKED`, no open in-flight item

## Delivered

The heartbeat is now stated to be the working prompt itself, and the main Skill names which trigger
delivers it on which host: Codex and Grok Bot from their own timer system, a ZCode Host from each
worker return or existing worker event. No shared path or schema was imposed, no timer was added to
ZCode, and no event mechanism was forced on Codex or Grok Bot — this is the terminology the user
fixed in issuecomment-5726132231, which outranks the issue body.

The prompt is an effective-now snapshot rather than an append-only change log:

- The constraint header carries quota beside CLI, model and concurrency, in the user's own unit, with
  an explicit rule against fusing concurrency, account quota and token budget into one number.
- A user-confirmed quota, priority, platform, model or concurrency change replaces the old value and
  is re-planned in the **same** beat — not the next one — and dispatch never quotes a superseded quota.
- A platform failure or a measured exhaustion is evidence only; it does not widen the authorization to
  switch platforms. A lowered quota is not by itself a cancellation of in-flight work, whose locator
  and remaining close-out duty are preserved.
- Every beat rewrites the prompt through an explicit subtraction rule with a drop list (superseded
  quota/priority/platform/model choices, void plans, repeated narration, inert completed items,
  transient failures and staffing history) and a keep list (stable skeleton rules, currently effective
  project constraints, in-flight locators — session, worktree, Issue/PR — unfinished delivery,
  acceptance, sync and cleanup duties with their owners, open decisions, and the minimum recovery
  pointer), plus the invariant that no two contradictory quotas or priorities may coexist.
- Removing a line from the heartbeat is not deleting evidence and never rewrites a completed Mission's
  `result`; history stays in Workflow, the Issue and the existing run records, reached by pointer.
- Carriers stay host-native: the ZCode Host updates `.kaola/heartbeat-prompt.json` (the #66 `body`
  field guidance preserved verbatim, now scoped to the host it belongs to), Codex and Grok Bot update
  their own existing timer-prompt carriers. No schema, quota ledger, scheduler, cleanup script, retry
  or auto-cancel mechanism was added.

Integration: the run implemented its own scope first, then merged main `68845bd` (already containing
#65 and #66) — a merge, never a rebase, no history rewritten. The single `### Hosts` conflict was
resolved by taking #65's accepted paragraph verbatim, so #65's steering/Host dispatch contract and
#66's startup contract survive intact.

## Files Changed

9 files, +177/−30 against main `68845bd`.

| File | What |
|---|---|
| `templates/orchestrator/references/heartbeat-skeleton.txt` | the substantive change: per-host definition, snapshot rule, quota header, same-beat effect, in-flight protection, step-7 subtraction rule with drop/keep lists and per-host carriers |
| `templates/orchestrator/SKILL.md.tmpl` | the same contract in short form in `## Heartbeat`, plus the Defaults `Heartbeat` row |
| `skills/kaola-project-runner/SKILL.md` | generated — renderer only |
| `skills/kaola-project-runner/references/heartbeat-skeleton.md` | generated — renderer only |
| `tests/contract/test-issue-68-heartbeat-snapshot.py` | new contract suite, 98 lines, 7 tests |
| `tests/contract/test-zcode-heartbeat-contract.py` | one proxy assertion replaced by the invariant it was protecting |
| `scripts/validate.sh` | registers the new suite in the all-list and lane A |
| `CHANGELOG.md` | Unreleased entry (documentation docking) |
| `docs/zcode-host.md` | stale per-beat enumeration replaced by the snapshot rule (documentation docking) |

`templates/grok-golden/` is byte-identical to main and `templates/budgets.json` is unchanged. Nothing
under `skills/` or `hosts/` was hand-edited.

## Test Coverage

`tests/contract/test-issue-68-heartbeat-snapshot.py` — 7 tests — checks the shipped obligation in the
rendered Skill and skeleton: the per-host definition, the drop and keep lists, the same-beat effect of
a confirmed change, the in-flight protection, the three separate quota kinds, host-native carriers with
no invented mechanism, and the unraised budgets.

It is deliberately **not** a behavioral suite. The first draft was 418 lines and 10 tests asserting over
`after`/`next_action` constants this same worker had written; the outer coordinator ruled that is not
behavioral evidence, and mission 6 cut it to 98 lines and 7 tests, deleting the Snapshot class, the nine
invariant functions, the three scenario constant blocks, the eight wrong variants and the three behavior
tests.

The behavioral record is the live sentinel instead (mission 5): one isolated ACP session on Claude
Opus high, Fast off, against a scratch `/tmp` checkout holding only the candidate's two rendered files
and the scenario input — no real project, account quota or scheduler touched. Given the three `before`
heartbeats and their user-change events with every expected answer withheld, its own 18 048-byte output
dropped every superseded value, kept concurrency / account quota / token budget as three separate
numbers, kept every in-flight locator and unfinished duty, switched platform only where authorized,
re-planned in the same beat, and refused to cancel in-flight work to fit a lowered ceiling. It also
answered the terminology question correctly cold. Two divergences from the hand-written fixtures were
recorded rather than hidden, and on both the sentinel was judged right. Evidence:
`evidence/sentinel/` with `00-findings.md`.

Not executed, stated as such: no live tmux/CLI smoke per platform (no transport, script or receipt byte
changed — this run is prompt text only), and no real Codex/Grok Bot/ZCode host driven through a real
timer or worker-event beat. This remains single-worker self-verification.

## Validation

Recorded by `kaola-workflow-validation-runner.js` — `verdict: pass`, command
`./scripts/render-skills.py --check && ./scripts/validate.sh`,
`validated_candidate_hash: 4b5577d95f36cbec754fa0c5f2c323c340d07fad88af3074975c44b100fa399a`
(`.cache/final-validation.md`). This project has no `test:kaola-workflow:*` chains, so the chain runner
does not apply and the project's own validation was recorded with its exact command.

| Candidate | `render-skills.py --check` | `validate.sh` | Log |
|---|---|---|---|
| `54bc864` (first freeze) | 0 | 0 | `evidence/validate-54bc864.log` |
| `230ca83` (after the test cut) | 0 | 0 | `evidence/validate-230ca83.log` |
| `19eda62` (accepted integration) | 0 | 0 | `evidence/validate-19eda62.log` |
| `77a9ecf` (after doc docking) | **0** | **0**, 22 suites OK | `evidence/validate-77a9ecf.log` |

Each mutation re-earned its PASS; none was carried over.

Finalize precondition check: `ok: true`, `reasons: []`, `staging_guard: ok`, `validation: chains_green`,
`dirty_paths: []`.

Two real failures were met and fixed during the run rather than worked around, both recorded in the
mission results: the #49 bridge probe busting the byte budget at 17405 B (fixed by compressing the main
Skill, not by raising the budget), and a proxy assertion in `test-zcode-heartbeat-contract.py` that the
user's final terminology made wrong (replaced by the invariant it was protecting). One intermediate
`validate.sh` exit 2 during integration is recorded in mission 7: the `git diff --check --cached` gate
firing on #65's already-committed archive because the merge was not yet committed. That archive was not
edited; committing the merge cleared it.

Byte budget on the delivered head: `main_skill_bytes` 17408, unchanged; rendered `SKILL.md` 17337 B,
which clears the 17349 B effective ceiling the #49 probe imposes by 12 B — verified by running
`test-issue-49-grok-bot-host.py` directly (42 tests, exit 0) and again inside the full suite.
`heartbeat-skeleton.md` 5153 B against `reference_bytes` 8192.

## Changed Paths

As reported by the finalize transaction:

```
scripts/validate.sh
skills/kaola-project-runner/SKILL.md
skills/kaola-project-runner/references/heartbeat-skeleton.md
templates/orchestrator/SKILL.md.tmpl
templates/orchestrator/references/heartbeat-skeleton.txt
tests/contract/test-issue-68-heartbeat-snapshot.py
tests/contract/test-zcode-heartbeat-contract.py
```

`dirty_paths: []`. The transaction computed this set at the accepted candidate `19eda62`; the two
documentation-docking paths committed on top of it — `CHANGELOG.md` and `docs/zcode-host.md` — are
additional to the list above and are reported here so the delivered set is complete at 9 files.

## Acceptance

- **Automated / local.** `./scripts/render-skills.py --check` exit 0 and `./scripts/validate.sh` exit 0
  (22 suites) on every freeze, table above. Run by this worker in its own worktree.
- **Live (isolated).** The ACP validation sentinel of mission 5 — real session, real reads of the
  candidate files whose sha256 match byte for byte, exact-session stop afterwards with
  `residual_pids []`.
- **Outer coordinator review.** Round 1 on `54bc864`: prompt diff read, direction and minimalism
  accepted, and the hand-written constants rejected as behavioral evidence — which produced missions 5
  and 6. Formal ACCEPT of `19eda62` recorded in `workflow-state.md` under *Outer Acceptance*: source
  template/test diff read, the three-scenario full sentinel output read, the integration validation
  record read, with an independent re-run of `render --check` and 7 contract suites, all exit 0, tree
  clean; #65's Host paragraph preserved and #68's rule semantics within authorization; no blocking
  finding.
- **Not executed.** No user UAT on a real host, no live per-platform tmux smoke, no release and no
  global install — none was authorized, and the change alters no transport byte.

## Issue statement walk

| Issue #68 acceptance clause | Satisfied by |
|---|---|
| ≥3 before/after scenarios: quota exhausted with approved platform swap; priority/quota raised and lowered; obsolete records cleared while in-flight and close-out survive | all three built and carried end to end in `evidence/heartbeat-snapshot-scenarios.md`, and replayed live in `evidence/sentinel/` |
| scenarios must prove current-constraints-only, immediate action, no unauthorized platform switch, no wrongful cancel — **not** keyword-presence assertions | the live sentinel's own raw output; the keyword-style suite was cut for exactly this reason (mission 6) |
| the template gives explicit per-beat subtraction guidance covering **all** hosts, not only ZCode | skeleton step 7's drop/keep lists plus per-host carriers; `## Heartbeat` names Codex/Grok Bot timer delivery and ZCode event delivery; asserted by the contract suite |
| exact exit status of `render-skills.py --check` and `./scripts/validate.sh`; budgets not raised; existing authorization / wait / close-out contracts not lost | validation table above; `budgets.json` unchanged; the merge preserves #65's and #66's contracts verbatim |
| frozen candidate handed to the outer for review; single-worker self-verification with unexecuted items marked honestly; no finalize/merge/push/close before acceptance; full archive/sink/cleanup after | `54bc864` → `230ca83` → `19eda62` frozen and handed over each time; unexecuted items stated in missions 3, 5 and here; nothing pushed before the ACCEPT recorded above; this finalization |
| change boundary: main source template, the existing skeleton, genuinely necessary docs/tests; renderer-only generated output; `grok-golden` frozen; `budgets.json` not raised; no runtime quota enforcer or auto-cancel | 9 files above; `git diff main -- templates/grok-golden templates/budgets.json hosts/` empty |
| same template as #65: independent Workflow worktree, read its candidate only, do not merge unaccepted work early; outer coordinates the mainline merge; re-verify final integration bytes; no rebase, no history rewrite | #65 read read-only via `git merge-tree` three times and never merged while unaccepted; merged only after it landed in main; bytes re-verified at 17337; merge commit `19eda62`, no rebase |
| execution authority: one Claude Code worker, Opus high, Fast off, Workflow on; no further implementation or review sub-agents; no real account quota, global CLI config, running project or other worker touched; no release, no global install | held throughout — every mission dispatched `self (inline)`, including this finalization; the sentinel ran against a `/tmp` scratch repo |

No clause is unsatisfied, so there is no blocker and nothing is deferred as a footnote.

**Issue correction:** none required. Nothing this run measured contradicts the issue body or
issuecomment-5726132231; the one deviation from the body's plan — merging main instead of reading
`workflow/issue-65` read-only — happened because #65 was accepted and finalized mid-run, which the body
already anticipated ("外层协调在安全边界合入主线"), and it is recorded in mission 7 rather than posted as
a correction.

## Follow-Up Items

- **filed: #71** (P3) — the main Skill's effective byte ceiling is 59 B below the declared
  `main_skill_bytes`, because `test-issue-49-grok-bot-host.py` appends a 59-byte probe to the
  orchestrator template, and no budget file, `--check` output or document names the real 17349 B limit.
  This run hit it as a genuinely red suite at 17405 B and now ships with 12 B of slack, so the next run
  to grow the main Skill will hit it too. `searched:` `gh issue list --state all --limit 100 --search
  "main_skill_bytes budget probe"` → 0 hits; `gh issue list --state open --limit 100` → 4 items, no
  duplicate. Confirmed after filing: issue #71 exists, state OPEN, label P3, body 1824 bytes.
- No other deferred item, partial delivery, unresolved conflict or open review finding exists in this
  run's records. The two trim candidates named in `evidence/integration-with-issue-65.md` are advice for
  a future integrator, not work owed by this run.

## Documentation Docking

`DOCKED` — `.cache/doc-docking.md`. `docs/zcode-host.md` fixed (stale per-beat enumeration),
`CHANGELOG.md` entry added; `README.md`, `docs/README.md`, `docs/conventions.md`,
`docs/architecture.md`, `docs/api.md`, `docs/grok-bot-host.md` and the dated decision/live-smoke records
checked with a stated no-impact reason each. Setup, install and environment unaffected.

## Readiness

**READY.** Accepted by the outer coordinator, validated green on the delivered head, documented, and
the one run-discovered defect filed as #71. Remaining: sink merge to main, remote sync, issue #68
closure, archive, closure audit, and cleanup of only this run's worktree and branch. Not authorized and
not performed: release, global install, and any change to another run's records, branches or history —
#70 and the #65 supplementary-evidence areas are untouched.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-68/.cache/doc-docking.md
- kaola-workflow/archive/issue-68/.cache/final-validation.md
- kaola-workflow/archive/issue-68/.cache/mirror-digest.json
- kaola-workflow/archive/issue-68/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-68/evidence/heartbeat-snapshot-scenarios.md
- kaola-workflow/archive/issue-68/evidence/integration-diff-19eda62.patch
- kaola-workflow/archive/issue-68/evidence/integration-with-issue-65.md
- kaola-workflow/archive/issue-68/evidence/merge-commit-19eda62.txt
- kaola-workflow/archive/issue-68/evidence/sentinel/00-findings.md
- kaola-workflow/archive/issue-68/evidence/sentinel/01-prompt.txt
- kaola-workflow/archive/issue-68/evidence/sentinel/02-scenario-input.md
- kaola-workflow/archive/issue-68/evidence/sentinel/03-raw-reply.txt
- kaola-workflow/archive/issue-68/evidence/sentinel/04-send-receipt.json
- kaola-workflow/archive/issue-68/evidence/sentinel/05-stop-receipt.json
- kaola-workflow/archive/issue-68/evidence/sentinel/06-acp-events.jsonl
- kaola-workflow/archive/issue-68/finalization-summary.md
- kaola-workflow/archive/issue-68/mission-list.md
- kaola-workflow/archive/issue-68/workflow-state.md
