# Finalization Summary — issue-184

## Delivered

`drain-restart` ran the pre-spawn refusal decision and then called `start`, which ran it
again, so one restart walked the installed Skill roots twice. `command_start` now accepts a
`decided` tuple from a caller that already computed it, and `drain-restart` hands over the
one it made before stopping anything: one scan per command instead of two. The holder's
`SIBLING_MODULES = ("kaola-quota.py",)`, its loop, and the `if name == "kaola-quota.py"`
branch inside it collapse to the single constant `QUOTA_MODULE` that loop ever loaded.

No observable receipt changes. After three repair rounds the owner ruled Option B: main's
single read-only pre-check stays, and #184 narrows to receipt-preserving consolidations.
The pre-stop state pre-read, `_seat_idle`, and both the `drain-not-idle` and
`drain-stop-failed` branches are byte-identical to main.

## Files Changed

Branch `workflow/issue-184`, two commits plus a `main` merge:

- `8d59700` Consolidate drain-restart pre-spawn scan and holder sibling import (#184)
- `9692804` CHANGELOG: record #184's single pre-spawn scan and holder sibling consolidation
- `de02db8` Merge branch 'main' into workflow/issue-184 (CHANGELOG entry conflict only;
  resolved preserving both #184's and #185's Unreleased entries)

Production: `scripts/kaola-acp.py`, `scripts/kaola-acp-holder.py`, plus 20 regenerated
`skills/*/scripts/kaola-acp*.py`. Tests: `test-issue-162-upgrade-safety.py` (new
agent-exit-window test + busy-path assertions), `test-issue-164-pre-spawn-bridge-facts.py`
(scan count 2 to 1), `test-issue-168-drift-enumeration.py` (`QUOTA_MODULE`).

## Test Coverage

`tests/contract/test-issue-162-upgrade-safety.py` — the new
`test_drain_restart_refuses_while_the_agent_exit_window_is_open` is a verified
discriminator: it fails when the pre-read is disabled and passes with it restored.
Verified against main key-by-key across the busy, unreachable-holder, exited-but-ready,
both stop-timeout sub-cases, and success paths; the only success-path differences are
per-run random holder instance ids, shown non-observable by running main against itself.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- scripts/kaola-acp-holder.py
- scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- tests/contract/test-issue-162-upgrade-safety.py
- tests/contract/test-issue-164-pre-spawn-bridge-facts.py
- tests/contract/test-issue-168-drift-enumeration.py

## Documentation Docking

DOCKED — `.cache/doc-docking.md`. Only `CHANGELOG.md` needed a change, adding the
Unreleased entry with **Seats: restart required** because `scripts/kaola-acp-holder.py`
is touched. No README, `docs/`, AGENTS.md, template, or public-CLI surface changed.

## Follow-Up Items

None filed. The owner resolved the only open fork (the drain-restart pre-check) as
Option B mid-run; no run-discovered defect remains unfiled.

## Readiness

Ready to merge. `render-skills.py --check` PASS and `validate.sh` exit 0 in the merged
state. Issue #184 closes on the merge sink; no PR, tag, or pin change.

Net lines vs base `714776d`: production **+5** (26+/21−), tests **+95** (105+/10−),
whole **+150** (391+/241−) including regenerated `skills/`. Production is net-positive:
Option B restored main's pre-read, leaving the single pre-spawn scan and the
`QUOTA_MODULE` collapse as the consolidations. The owner pre-authorized honest reporting.

## Finalize Findings

### residue_unattributed

The `chore: finalize` commit did NOT carry the paths below: this branch's own commits touch no file in their directories, so the transaction has no evidence they are this run's work. Nothing was committed, reverted or deleted — they are exactly where they were. Read them before the sink runs: commit what belongs to the run, remove what does not.

Paths not attributed to this run:

- .cache/

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-184/.cache/doc-docking.md
- kaola-workflow/archive/issue-184/.cache/final-validation.md
- kaola-workflow/archive/issue-184/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-184/finalization-summary.md
- kaola-workflow/archive/issue-184/mission-ledger.jsonl
- kaola-workflow/archive/issue-184/workflow-state.md
