# Phase 4 decision — optional pack pointer in `templates/orchestrator/` (#283)

Status: recommendation for the Host. The Host decides. Nothing in `templates/` or `skills/` was
changed in this round. Checked at `4c30b71d0b964628c5a39159ff0cd89504adcd6b`.

Question (design §3, #283): should the Project Runner Skill source get a short optional pointer
saying that an assignment may cite a context pack? Whatever the answer, a pack stays optional. It
is never mandatory, never a dispatch precondition and never authority.

## Recommendation

**Do not change `templates/orchestrator/` in this round.** Keep the exact text below ready. Apply
it only if the comparison in "Re-open criterion" shows a measurable benefit.

## Evidence

1. **The capability already exists without Skill text.** The Host has already cited the pilot
   pack in two real assignments. Its only route was the existing free-text assignment: the main
   Skill tells the Host to "State the task, working location, write ownership, constraints,
   delivery requirements, and the doc-impact call" in the dispatch prompt
   (`templates/orchestrator/SKILL.md.tmpl:186-188`). Design §3 already allows a Host to cite a
   pack path. The two assignments:
   - [#286](https://github.com/KaolaBrother/kaola-project-runner/issues/286): the issue body cites
     `docs/ddd/packs/c4-state-retire.md`, gaps G5/G6/G9, as its source. Run: `workflow/issue-286`,
     worktree `.kw/worktrees/issue-286`, claimed 2026-10-07T08:56:30Z. In progress.
   - [#281](https://github.com/KaolaBrother/kaola-project-runner/issues/281): phase 2, contract
     fixtures for the pack's `suite: none (gap: …)` lines. Run: `workflow/issue-281`, worktree
     `.kw/worktrees/issue-281`. In progress.

   These two assignments are the comparison input. I did not run them, and I did not observe their
   prompts or results. The Host reported that they cite the pack.
2. **No benefit is measured yet.** Neither run has a result. No comparable assignment without a
   pack has been paired with them. So there is no rework, clarification or elapsed-time
   comparison yet. The honest result today is "not measured", not "no benefit". AGENTS.md item 5
   says not to let speculative optimization replace delivery, and to retire guidance instead of
   adding a rule for every case.
3. **The Skill reaches consumers that have no packs.** Project Runner is installed into consumer
   Hosts (VRPAI, CAD, KT). `docs/ddd/` exists only in this checkout. A pointer would put
   KPR-internal design-aid guidance into a consumer-facing Skill. The text below keeps it generic
   ("where the project keeps…") for this reason.
4. **A pointer has real costs:**
   - The main `SKILL.md` has 15 B of headroom (17393 of 17408 B, `main_skill_bytes` in
     `templates/budgets.json`). Only a reference file can carry the text.
   - Any reference change changes the main-Skill build id. That id is recorded in the
     `scripts/main-skill-build.json` of each of the ten worker Skills
     (`scripts/render-skills.py:663-671`). Until an installed copy is refreshed, a Host start
     against it refuses with `main-skill-build-skew` (`scripts/kaola-acp.py:4731-4767`). This is
     normal for a release, but here it has no measured benefit.
   - The pointer becomes one more integration to remove on uninstall (`docs/ddd/README.md`,
     "Uninstall").
5. **`--check` cannot pass this round.** The #283 output contract requires a template change to
   pass `./scripts/render-skills.py --check`. On `main` it currently exits 1, with only `pin:`
   findings. Those findings come from the inherited Grok Bot pin `3de9f61afbfa`, which is stale
   (protected path `templates/grok-bot/accepted-revision.json`). There are no budget or drift
   findings. A template change made now could not be shown passing.

## Exact proposed text (for the Host, not applied)

File: `templates/orchestrator/references/doc-maintenance.md`, section `## Dispatch — the worker
judges impact`. Insert this as a new paragraph after line 17 ("documentation-editing
authority."), before "Write in accordance with ASD-STE100.":

```text
Where the project keeps an optional context pack for the work area (for
example `docs/ddd/packs/<id>.md` in the Project Runner checkout), the dispatch
prompt may cite its path as context. A pack is optional, is never a dispatch
precondition and carries no authority; the worker checks it against the
current source.
```

Why this file: it already holds what goes into a dispatch prompt besides the task itself (the
doc-impact call). It is the smallest reference (2370 B), and the main Skill already links to it
(`templates/orchestrator/SKILL.md.tmpl:216`).

**Byte-budget impact** (measured with `wc -c`):

| Surface | Now | After | Budget | Headroom after |
|---|---|---|---|---|
| `references/doc-maintenance.md` (template and render are identical bytes) | 2370 B | 2687 B (+317 B, including the blank separator line) | `reference_bytes` 8192 B | 5505 B |
| `skills/kaola-project-runner/SKILL.md` | 17393 B | 17393 B (unchanged) | `main_skill_bytes` 17408 B | 15 B |
| `skills/*/scripts/main-skill-build.json` (10 files) | — | new build id; same size class | — | — |

No ceiling is raised. Affected suites, if it is applied:

- `./scripts/render-skills.py --write` and `--check`;
- `./scripts/validate.sh --suite test-issue-75-codex-compact-hook.py`
  (`DocMaintenanceSurface`: its eight needles and the budget still hold with this text);
- `--suite test-progressive-disclosure.py`;
- `--suite test-generated-skills.py`.

## Re-open criterion

Apply the text above only if both of these hold:

- the #286/#281 results, compared with a comparable assignment without a pack (the Host picks
  the pair), show a measurable benefit attributable to the citation, in rework, clarification
  rounds or elapsed time; and
- there is evidence that a Host would not cite a pack without being prompted.

Otherwise keep the free-text route, and record "no measurable benefit" as the result. Apply it
in a normal reviewed template commit, after the pin is refreshed, so that `--check` can pass.

## Checker integration sub-item — not done

The sub-item that would cite a `kaola-ddd-pack.py` run in Host usage guidance waits for #282.
#282 is in progress on `workflow/issue-282`, at `4c30b71d`, and no checker exists on `main`.
This round leaves the sub-item out. Its absence does not block #283 (#283 acceptance; design §6).

## Second-pack findings (input to #282)

These come from writing [`packs/c1-exact-stop.md`](packs/c1-exact-stop.md) by hand. They
complement the pilot table in [`README.md`](README.md#pilot-findings-phase-1-c4-retire-a-record).

| Check | Result on the second pack |
|---|---|
| Required front matter and sections; forbidden keys | All present, none forbidden. Nothing caught. |
| Cited paths exist; `suite:` names in `validate.sh --list`; `baseline_commit` resolves | All pass. Nothing caught. |
| `path:line` accuracy | **41 cited ranges were off by 1–5 lines on first writing.** Re-reading found and corrected them, in two passes. Most were an endpoint off by one *inside the right function*, so a `path:line` → symbol check would catch only some of them. Path existence caught none. |
| Suite descriptions | **Three description errors**, found only by re-reading the suites: a wrong platform name (the Claude Code bridge was called ZCode), a test cited for a code path it does not exercise (a SIGKILL path cited for `_exit_after_reply`), and an overclaim ("every live stop" is followed by a pid check). No mechanical check would catch these. |
| Meaning, read from source | **Two real findings:** (1) the receipt key `stopped` means different things on different paths: always `true` from the holder and the dead-holder sweep, `not leftover` on the reused-pid path (`scripts/kaola-acp.py:2347`); (2) "exact" holds only while the holder is alive (gaps S1/S2). |
| Seam coverage, read from suites | Three gaps (S1–S3). The pilot's G9 was re-measured. |

Same conclusion as the pilot: the value came from reading and probing, not from mechanical
checks. The measured line-drift rate is the strongest argument for an advisory `path:line`
check, if #282 builds one.

S1–S3 are new seam gaps. #281 covers the pilot's G1–G9 only, so whether S1/S2 are defects, and
who fixes them, is a Host decision. A new issue is the usual route.
