# Issue #68 candidate 54bc864 — integration surface against the live #65 run

Computed read-only with `git merge-tree --write-tree --name-only HEAD workflow/issue-65` from the
issue-68 worktree. No ref, branch, worktree or index outside this run was touched; merge-tree writes
objects only and updates nothing. `workflow/issue-65` was read, never merged, rebased, or modified.

Re-checked three times as #65 moved during this run: against its tip `4b8168c`, then against
`bc720e3` ("Merge branch 'main' into workflow/issue-65"), and finally — after the outer accepted #65
and it finalized — **against main itself at `90842e7`, which now contains #65**. All three give the
identical conflict set, and the other side's rendered `SKILL.md` is 17262 B in every case, so every
number below still holds. The target has simply changed from a sibling branch to main.

`workflow/issue-68` is still based on `039c278` and has NOT been updated onto the new main: per the
outer coordinator, the `### Hosts` conflict is not to be resolved until the user has confirmed it.
This candidate's own change set is unaffected — measured from the merge base it is still 7 files,
+156/−32.

## Conflict set: one hunk

```
Auto-merging scripts/validate.sh                       <- clean
Auto-merging skills/kaola-project-runner/SKILL.md      <- CONFLICT (generated product)
Auto-merging templates/orchestrator/SKILL.md.tmpl      <- CONFLICT (one hunk, the `### Hosts` paragraph)
```

Everything else merges clean: `templates/orchestrator/references/heartbeat-skeleton.txt` and its
rendered product (untouched by #65), `tests/contract/test-issue-68-heartbeat-snapshot.py` (new
file), `tests/contract/test-zcode-heartbeat-contract.py` (untouched by #65), and `scripts/validate.sh`
— the #68 suite was deliberately registered next to `test-issue-41-orchestrator.py` in the middle of
both arrays instead of appended, which keeps it clear of the array tails where #65 adds its three
suites.

`skills/kaola-project-runner/SKILL.md` is generated output. It is not resolved by hand: resolve the
template, then run `./scripts/render-skills.py --write`.

## Minimal meaning-preserving resolution

**Take the `workflow/issue-65` side of the `### Hosts` paragraph verbatim. Nothing of #68 is lost.**

#68's only edit inside that paragraph replaced

> `updates the file (project info, pace, plans, coordination) so the next heartbeat pass carries fresh state`

with

> `rewrites that file as the next beat's snapshot`

because the per-beat content list moved into the skeleton's subtraction rule, where it is now a drop
list and a keep list rather than a four-word enumeration. #65's rewrite of the same paragraph already
drops that enumeration on its own (`update the project's .kaola/heartbeat-prompt.json`), so taking
#65's side keeps both meanings. #68's substantive text — the per-host heartbeat definition, the
snapshot rule, the immediate effect of a confirmed change, the in-flight protection — lives in the
`## Heartbeat` paragraph and in the skeleton, both of which merge clean.

After resolving, re-run `./scripts/render-skills.py --write`, then `--check`, then
`./scripts/validate.sh`.

## Byte budget after integration — the one thing to watch

`main_skill_bytes` stays 17408; neither run raises it.

| Tree | rendered `SKILL.md` |
|---|---|
| main `039c278` | 17281 B |
| main `90842e7` (now contains #65; same size as its tip `bc720e3`) | 17262 B |
| #68 candidate `54bc864` | 17297 B |
| projected merge, resolved as above | **17337 B** (71 B free) |

The projection is exact rather than estimated: the resolved template equals #65's template plus
#68's two non-conflicting edits (`## Heartbeat` paragraph + the Defaults `Heartbeat` row, +75 B
together), and #68's −59 B Hosts trim is subsumed by #65's own rewrite.

`tests/contract/test-issue-49-grok-bot-host.py::test_pin_changes_exactly_one_line_...` appends a
59-byte probe sentence to the orchestrator template and requires the render to still succeed, so the
**effective** ceiling is 17408 − 59 = 17349 B. The projected merge sits at 17337 B, i.e. **12 bytes
of slack on that test**. That is the failure #68 hit and fixed during this run (at 17405 B the probe
busted the budget and the suite went red), so it is a live trap, not a hypothetical: if #65 grows the
main Skill any further before acceptance, the integrator must trim the main Skill rather than raise
the budget. Candidates for that trim, if it is ever needed, are the duplications #68 deliberately
left alone because they sit inside #65's own hunks — "Idle is not keep-alive. ACP idle left running
is not completion and not keep-alive." in loop step 5 (#65 already compresses this) and "No CLI
allowlist means no heartbeat.", which restates the Authorization section.

## Ordering

#68 implemented its own scope first and did not wait on #65. #65 has since been accepted and merged
into main, so the remaining step is resolving the one `### Hosts` hunk against main and re-rendering
— which stays undispatched until the outer coordinator has the user's confirmation for it.

The candidate is frozen at `230ca83` on `workflow/issue-68` (`54bc864` prompt change + `230ca83`
test reduction). No finalize, merge, push, issue close, release, or global install has been
performed, and the branch has not been updated onto the new main.

---

## Integration performed — merge commit `19eda62` (2026-09-18)

The outer coordinator confirmed the resolution, so the plan above was executed exactly as written.

```
git merge main            # merge, not rebase; no history rewritten
parents: 230ca83 (issue-68 candidate) + 68845bd (main, contains #65 and #66)
```

**Conflicts: the predicted one, and only it.**

```
Auto-merging   scripts/validate.sh                      clean
CONFLICT       templates/orchestrator/SKILL.md.tmpl     one hunk, the `### Hosts` paragraph
CONFLICT       skills/kaola-project-runner/SKILL.md     its generated product
```

Resolution, as planned: the `### Hosts` paragraph was taken from **main's side verbatim** — the
accepted #65 text, 2141 B replacing #68's 2048 B. Nothing of #68 is lost, because #68's only edit
inside that paragraph was trimming the per-beat enumeration, and #65's own rewrite already drops it.
Everything #65 and #66 own there survives intact: the ZCode Host `KAOLA_ACP_HEARTBEAT_HOST` receipt
check, `send --no-wait` with the `dispatch_event_cursor` anchor, "end the turn normally — that is the
wait", the pointer to `references/zcode-host-dispatch.md`, and the bridge-host locator attestation
with its per-target isolation boundary.

The generated `skills/kaola-project-runner/SKILL.md` was **not** hand-resolved: the template was
resolved, then `./scripts/render-skills.py --write` produced it (exit 0). No hand edit under
`skills/` or `hosts/`.

**#68's own contribution, now measured on top of the new main** — the same 7 files, +152/−28
(previously +156/−32 against `039c278`; the 4-line difference is exactly the `### Hosts` hunk now
coming from #65):

```
scripts/validate.sh                                  |  2 +
skills/kaola-project-runner/SKILL.md                 | 18 +++---
skills/kaola-project-runner/references/heartbeat-skeleton.md | 16 ++++--
templates/orchestrator/SKILL.md.tmpl                 | 18 +++---
templates/orchestrator/references/heartbeat-skeleton.txt | 16 ++++--
tests/contract/test-issue-68-heartbeat-snapshot.py   | 98 ++++++++++++++++++++
tests/contract/test-zcode-heartbeat-contract.py      | 12 +++-
```

Full patch: `integration-diff-19eda62.patch`. Merge record: `merge-commit-19eda62.txt`.

### Exact validation on the integrated tree

| Check | Exit | Note |
|---|---|---|
| `./scripts/render-skills.py --check` | **0** | `PASS … budgets OK` |
| `./scripts/validate.sh` | **0** | 22 suites `OK`, full log `validate-19eda62.log` |

One intermediate result is recorded rather than hidden: run **before** the merge was committed,
`./scripts/validate.sh` exited **2** on its final acceptance gate, `git diff --check --cached`,
reporting `kaola-workflow/archive/issue-65/mission-list.md:252: new blank line at EOF`. All 22 test
suites passed in that run too. The cause is the uncommitted merge state — that file is #65's
archive, already committed on main with a trailing blank line, and `--cached` sees the whole
incoming archive as staged additions. It is another run's archive and was **not** edited. Committing
the merge cleared the gate; the clean-tree re-run is the exit 0 above.

### Byte budget after integration

`templates/budgets.json` is unchanged (`main_skill_bytes` 17408) and `templates/grok-golden/` is
byte-identical to main.

| Tree | rendered `SKILL.md` |
|---|---|
| main `68845bd` | 17262 B |
| **integrated `19eda62`** | **17337 B** — exactly the projection above |
| effective ceiling (#49 probe appends 59 B) | 17349 B → **12 B of slack** |

The 12-byte slack was not left on trust: `tests/contract/test-issue-49-grok-bot-host.py` was run
directly on the integrated tree — 42 tests, exit 0 — and again inside the full suite. No wording was
compressed, because none needed to be; the trim candidates named above remain available to whoever
next grows the main Skill, and the rule still stands that the main Skill gets trimmed rather than
the budget raised.

### Boundaries held

`git diff main -- templates/grok-golden templates/budgets.json hosts/` is empty, and
`git diff --name-only main -- kaola-workflow/` is empty: no other run's archive, no accepted
checkout, no sibling worktree and no global config was touched. The worktree is clean at `19eda62`.

**Not done, pending the outer coordinator's acceptance:** finalize, push, issue close, release,
global install.
