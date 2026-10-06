# QA evidence: Host-owned adaptive coverage

Testing yields results. QA judges whether product, docs and evidence satisfy the
work and verification is proportionate. QA is not a second test phase; never
repeat a suite under a QA label.

## Ownership

The Host owns quality: it decides what evidence is needed, who supplies it,
whether it suffices, and when project QA and doc accuracy are checked, from
change scope, risk, integration state and the delivery boundary. No fixed
interval, issue count, mandatory reviewer or extra seat.

A worker supplies outcomes, checks, results and affected docs. Task acceptance (main Skill step 3)
judges that assignment, not
project QA: an aggregate check not yet run stays pending, never PASS because an
issue closed. Keep it, with its delivery point, as one heartbeat `pending` entry
until evidence and your verdict settle it — no QA ledger, timer, table, score or
scheduler.

Kaola-Workflow owns claims, recovery, workspace/commit ownership,
lifecycle/evidence records, delivery, merge, closure, archive and cleanup; its
receipts are evidence. Finalize and doc docking are lifecycle facts,
never QA PASS; QA is not delegated to them. Where
the installed finalize requires validation or docking artifacts, the worker
produces them honestly, without bypassing a mechanic or fabricating a receipt.

## When to check

Reuse valid evidence first. Finishing a worker or issue does not itself trigger
a QA round, full suite or doc review; related issues may share one bounded
integration pass. Check earlier, still bounded, for a concrete uncertainty,
high-risk affected behavior, an undemonstrated in-scope user-facing outcome
(behavior, output, rendering, doc accuracy), evidenced redundancy, or an
explicit user request (exploratory, user-flow, release QA). Small changes normally
end at reuse. Check relevant edge cases and failure paths by risk; avoid duplicate
testing. Required checks stay binding: reduce redundant optional coverage, never
silently waive a binding check or claim unperformed validation. Uncertainty
about edges or expected behavior may justify public research
([public-research.md](public-research.md)); routine planning does not.

## Who

Host judgment from existing profile rows, not a router: the original owner when
it can run and record the check; a separate authorized seat when independence or
fit helps. A better-fitting seat may draft the plan; the verdict stays yours.
Prefer available Worker-Class seats for exploratory checks and heavy test runs
by profile fit, not one habitual runtime; use a fitting Elite for a missing
capability. Independent checks may run in parallel with distinct scopes,
non-interfering state (data, accounts, ports, desktop) and one Host verdict; an
exploratory check fixes its question, scope and stopping point, not its route. An
integrated-candidate check waits for that candidate. For visual analysis or
screenshot review, prefer an authorized Opus preset or GPT-6.1 Sol, then Kimi —
guidance, not a ranking or grant. "Opus" names only the defined
runtime/preset/effort. Grok means Grok CLI default and Cursor CLI default, not
Cursor's Opus preset. Visual review does not prove computer-operation
capability.

For a task that operates a computer, follow
[worker-profiles.md](worker-profiles.md) Computer interaction; do not restate it
here. An Expert review needs an applicable task or standing grant and informs,
never replaces, acceptance.

## Tools and authority

Use tools already authorized for the project or task; a granted
browser/device/UI tool needs no new grant. The Host resolves an ordinary tool or
environment failure within existing authority; not every hiccup is
`HUMAN_DECISION_REQUIRED`. Escalate only a real gap: no seat holds the
permission or environment.

## Brief

Short message: the issue/task reference and the outcome to check (quoted where
one exists); the exact candidate (commit/worktree/build/URL); the checks and
what "wrong" looks like; a stopping point; authorized tools; where to write the
record. A bounded check is record-only; an evidenced-redundancy simplification
goes to an implementation owner, who may edit affected tests or guidance within scope.
Do not self-finalize; `HUMAN_DECISION_REQUIRED` for value/authority gaps.

Write in accordance with ASD-STE100.

## Return

Return facts, not a verdict: build, per-check execution and observations; artifacts
and uncertainty for visual/interpretive findings; unrun scope with reasons.
No record means unverified or insufficient
evidence, not necessarily unexecuted — distinguish "no record", "recorded as not
run", and "recorded as run with a result"; only the third supports acceptance.

Write in accordance with ASD-STE100.

## Reading a failure

Keep separate: the **observation** (exact command/step and result, on which
build); the **plausible cause** (candidate regression; pre-existing bug on
baseline; misconfigured setup; tool/environment failure; flake); the
**uncertainty** (what was and was not tried). A judgment with no spec, including
an unspecified preference, is an observation, not a proven failure. Failing on
the baseline too does not prove an environment cause. The Host decides whether
it blocks, needs a narrower repro, is an open observation, or is out of scope.

## Continuous improvement

Look for structural waste during normal planning, result review and QA; failure
is not necessary. Judge duplicated responsibilities, unnecessary tests, coupled
modules, functions or interfaces, long waits, costly checks, and configuration,
documentation or coordination overlap against the simplest sufficient design.
Deliberate isolation and a different contract are not automatically redundant.

Use this path:

1. Read the actual change, dependencies, entry points and original results;
   name the affected boundary.
2. State the end-to-end behavior, compatibility and constraints to keep.
3. Compare a bounded merge, split, reuse or removal with the current form.
4. Give an authorized improvement to the existing owner; use a Worker-Class
   seat for independent research, counterexamples, edge exploration or
   verification. Resolve material scope, API, migration or value choices with
   the user.
5. Verify affected parts and their integrated interfaces, data flow and
   recovery. Reuse valid evidence; a mutation invalidates only affected
   evidence. Keep it only when outcomes justify it.

The Host keeps architecture, scheduling and verdict. A Sideagent keeps process
facts and unresolved duties, not verdicts. The Delegator compares useful
outcomes over time and relays pacing problems through existing supervision.
Keep current duties in existing task fields; use normal issues and Git history.
No compulsory optimization phase, audit, queue, ledger, or new mechanism
without a demonstrated gap.

## Slow feedback, redundancy and repair

When feedback is slow or repeats coverage, give the owner a bounded task: reuse
valid results, name the coverage a cut removes and why none is lost; keep required
contracts, meaningful coverage and unresolved failures. State one concrete corrective
action: a smaller justified scope, a reused result, or a bounded
fixture/module split or decoupling. If a costly check cannot shrink, name its unique
coverage and reason and move it to
the allowed integration or release boundary. Keep the pacing problem in the
existing task or warning field. Do not only raise a timeout or run more copies
of the full gate; the watchdog is not a feedback budget, and no universal
elapsed gate or monitor is added.

Development feedback runs affected suites and preparation through the
controlled entry. Integration and release run the checks that actual change,
remaining gaps and binding release and live-ACP contracts require, not the label
alone. An unchanged valid result stays valid; a new commit does not invalidate
every result. A build cache is not a result cache. A toolchain, configuration,
fixture, feature, platform or external input change can invalidate evidence.
Return an incomplete record to its owner with the gap named; a defect goes to
its owner. Release each seat per main Skill step 5; enough evidence is enough.
