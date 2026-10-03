# QA evidence: Host-owned adaptive coverage

Testing executes defined checks and produces results. QA judges whether the
product, its documentation and their evidence satisfy the work, and whether
the verification itself stays necessary and proportionate. QA is not a second
test-running phase and never repeats the same suite under a QA label.

## Ownership

The Host is the one quality owner: it decides what evidence is needed, who
supplies it, whether it suffices, and when project-level QA and documentation
accuracy are checked, from actual change scope, risk, integration state,
progress and the user's delivery boundary. No fixed interval, issue count,
mandatory separate reviewer or extra QA seat.

A worker supplies its actual outcome, relevant checks and results, and the
documentation changes its task affects. Task acceptance (main Skill step 3)
honestly judges that assignment, not project-level QA: an aggregate check not
yet run stays pending, never PASS because an issue closed. Keep it, with its
delivery point, as one heartbeat `pending` entry until evidence and your
verdict settle it — no QA ledger, timer, table, score or scheduler.

Kaola-Workflow owns claims, run recovery, workspace/commit ownership, truthful
lifecycle/evidence records, delivery, merge, closure, archive and cleanup; its
receipts are evidence. A successful finalize or documentation docking is a
lifecycle fact, never QA PASS; quality judgment is never delegated to it.
Where the installed finalize still requires validation or docking artifacts,
the worker produces them honestly — never bypass a required mechanic or
fabricate a receipt; report a concrete transition constraint.

## When to check

Reuse valid evidence first; a change invalidates only the evidence it
affects. Finishing a worker or issue does not itself trigger a QA round, full
suite or comprehensive doc review; related issues may share one bounded
integration QA/doc pass before their delivery boundary. Check earlier, still
bounded, for a concrete uncertainty, high-risk or important affected behavior,
an undemonstrated in-scope user-facing outcome (behavior, output, rendering,
doc accuracy), evidenced redundancy, or an explicit user request
(exploratory, user-flow, release QA). Small changes normally end at reuse.
Check relevant edge cases and failure paths according to the risk of affected
behavior; reuse valid evidence without exhaustive or duplicate testing.
Project- and user-required checks stay binding at their boundary: reduce
redundant optional coverage or frequency, never silently waive a binding
check or claim validation nobody performed.
Uncertainty about relevant edges, expected behavior or an observed result may
justify public research ([public-research.md](public-research.md)), including
while forming the plan; routine planning alone does not.

## Who

Host judgment from existing profile rows, not a router: the original owner
when the check is a command or step it can run and record; a separate
authorized seat when independence or profile fit helps. A better-fitting
authorized seat may draft the QA plan; the verdict stays yours. Prefer
suitable available Worker-Class seats for exploratory checks and heavy or
long-running test runs, chosen per scope by profile fit, not one habitual
runtime; use a fitting authorized Elite when they lack a needed capability.
Independent checks may run in parallel with distinct scopes, non-interfering
state (data, accounts, ports, desktop) and one Host verdict; an exploratory
check fixes its question, scope and stopping point, not its route or findings.
An integrated-candidate check waits for that candidate. For visual analysis or
screenshot review, the owner's preference remains an authorized Opus preset or
GPT-6.1 Sol first, then Kimi — selection guidance, not a measured ranking or
new grant. "Opus" names only the already-defined runtime/preset/effort. Grok
means Grok CLI default and Cursor CLI default, not Cursor's Opus preset.
Visual review does not establish computer-operation capability.

For a task that operates a computer, follow
[worker-profiles.md](worker-profiles.md) Computer interaction; do not restate
it here. An Expert review needs its own per-task permission and informs, never
replaces, Host acceptance.

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
executed or explored and why. No record means unverified or insufficient evidence, not
necessarily unexecuted — distinguish "no record", "recorded as not run", and
"recorded as run with a result"; only the third supports acceptance.

## Reading a failure

Keep separate: the **observation** (exact command/step and result, on which
build); the **plausible cause** (candidate regression; pre-existing bug also on
baseline; unsupported/misconfigured setup; tool/environment failure; flake);
the **uncertainty** (what was and was not tried). A judgment with no spec,
including an unspecified preference, is an observation, not a proven failure.
Failing on the baseline too does not by itself prove an environment cause. The
Host decides whether it blocks, needs a narrower repro, is an open observation,
or is out of scope.

## Redundancy

At a delivery/integration point, or when progress is slow, weigh existing
results and timing records for overlapping checks without distinct coverage,
regenerated still-valid evidence, unrelated full-suite reruns, and duplicate
review stages. When evidenced, give the appropriate worker a bounded task:
reuse existing commands/results, name which distinct acceptance coverage a
cut removes and why none is lost, and keep required contracts, meaningful
regression coverage and unresolved failures — speed is not a waiver.

## Repair and stopping

An incomplete or unclear QA record goes back to its owner as the same
assignment, with the concrete gap named. A concrete product defect goes to the
implementing owner. Release each seat per main Skill step 5; enough evidence
is enough.
