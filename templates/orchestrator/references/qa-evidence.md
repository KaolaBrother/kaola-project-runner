# QA evidence: testing vs QA, bounded execution, redundancy

Testing executes defined checks and produces results. QA judges whether the
product and its evidence satisfy the task, and whether the verification work
itself stays necessary and proportionate. QA is not a second test-running
phase and never repeats the same suite under a QA label.

## When to assign bounded QA

Reuse sufficient evidence for the current candidate first. Assign a bounded
check when a user-facing outcome within the authorized task scope (behavior,
output, rendering, doc accuracy) is undemonstrated by recorded evidence, when
evidenced verification redundancy needs simplifying, or when the user
explicitly requests exploratory, user-flow, or release QA — at any point in
scope, not only after a finished, frozen delivery. A worker merely finishing
is not itself a trigger; small or low-impact changes normally end at reuse.

## Who

Host judgment from existing profile rows, not a router: the original owner
when the check is a command or step it can run and record; a separate
authorized seat when independence or profile fit helps. For visual work the
owner's stated preference is an authorized Opus preset or GPT-6 Sol first,
then Kimi — selection guidance, not a measured ranking; "Opus" names only the
already-defined runtime/preset/effort, never a new grant. Grok means Grok CLI
default and Cursor CLI default, not Cursor's Opus preset. GPT-6 Sol's profile
also covers computer use. An Expert review needs its own per-task permission
and informs, never replaces, Host acceptance. See
[worker-profiles.md](worker-profiles.md); this adds no new row or score.

## Tools and authority

Use tools already authorized for the project or task; a browser/device/UI
tool already granted needs no new grant for a QA pass. An ordinary tool or
environment failure is the Host's to resolve within its existing authority —
not every hiccup is `HUMAN_DECISION_REQUIRED`. Escalate only a real gap: no
seat holds the permission, or a credential or environment nobody has.

## Brief

Short natural-language message: the issue/task reference and the outcome to
check (quoted where one exists); the exact candidate (commit/worktree/build/
URL); the checks and what "wrong" looks like; a stopping point; tools already
authorized; where to write the record. A bounded QA check is record-only; an
evidenced-redundancy simplification goes to an implementation owner, who may
edit the affected tests/guidance within scope. Do not self-finalize;
`HUMAN_DECISION_REQUIRED` for value/authority gaps.

## Return

A factual record, not a verdict: the build actually tested; per check what ran
and what was observed; artifacts (output, screenshot, snapshot) for visual or
interpretive findings, with uncertainty stated in a phrase; anything not
executed and why. No record means unverified or insufficient evidence, not
necessarily unexecuted — distinguish "no record", "recorded as not run", and
"recorded as run with a result"; only the third supports acceptance.

## Reading a failure

Keep separate: the **observation** (exact command/step and result, on which
build); the **plausible cause** (candidate regression; pre-existing bug also on
baseline; unsupported/misconfigured setup; tool/environment failure; flake);
the **uncertainty** (what was and was not tried). Failing on the baseline too
does not by itself prove an environment cause. The Host decides whether it
blocks, needs a narrower repro, is an open observation, or is out of scope.

## Redundancy and adaptive cadence

At a meaningful delivery/integration point, and when progress is slow, weigh
existing results and execution/timing records for overlapping checks without
distinct coverage, repeatedly regenerated still-valid evidence, unrelated
full-suite reruns, and duplicate review stages. When evidenced, give the
appropriate worker a bounded task: reuse existing commands/results, name which
distinct acceptance coverage a proposed cut removes and why no coverage is
lost, and keep required contracts, meaningful regression coverage, and
unresolved failures intact — speed is not a waiver. This is ordinary quality
judgment at delivery points, not a scheduled audit, a numeric threshold, or a
new dashboard; a binding required check is never silently waived or postponed
past its required boundary.

## Repair and stopping

An incomplete or unclear QA record goes back to its owner as the same
assignment, with the concrete gap named. A concrete product defect goes to the
implementing owner. Exact-stop the seat once its delivery is accepted or
abandoned; enough evidence is enough.

## Examples

- **CLI.** Issue: `export --format json` exits 0 with valid JSON; an invalid
  format exits 2 with a one-line error. Unit tests cover the parser only.
  Bounded check: run the three commands on the built binary, capture
  stdout/exit codes, pipe JSON through a validator, diff `--help` against the
  README usage block. One finding (README shows a stale flag) routes to the
  implementer; re-check only the README diff after the fix — no
  repository-wide doc sweep.
- **UI / user flow.** Issue: the settings page saves the timezone and the
  dashboard shows it. Component tests are green; nothing shows the dashboard.
  Bounded check on a seat with the project's browser tooling already
  authorized: save a value, reload, start a fresh session, confirm the
  dashboard reflects it; screenshot attached; a narrow-width spacing
  observation is recorded with "layout judgment, no spec" and not treated as
  a required-scope failure.
- **Docs-only.** Issue: document `--dry-run`. No runtime behavior changed.
  Read the diff and any recorded `--help` output for this candidate; if none
  exists and self-execute is off, assign the owner to run and record it — no
  separate QA seat, no new test framework.
