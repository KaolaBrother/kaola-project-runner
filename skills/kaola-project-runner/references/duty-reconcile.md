# Bounded duty reconciliation

At recovery and before quiescence or closeout, the Host reads applicable owner
goal/stop records and relevant newer corrections, comparing authorized duties
with actual evidence. Load this reference when a record-visible source/evidence
mismatch, an unreconciled latest owner change, genuinely unaccounted coverage
after a handoff, or an explicit owner/Delegator request calls for one bounded,
read-only Sideagent check. Remembered confidence alone is insufficient. Reuse
sufficient unchanged evidence for the same scope and candidate; reuse a check
already in flight. A heartbeat, issue completion, compaction, Host replacement
or multi-issue closeout alone does not require an audit.

## Brief and sources

Give the Sideagent the canonical root, affected scope and question, candidate or
baseline when relevant, and independent source pointers, not a prefiltered duty
list or a conversation/repository dump. It reads applicable requirements before
the Host snapshot, using only relevant slices of:

- Latest owner requirements, goal/stop and issue corrections; for a mandate
  check include the mandate record (Delegator goal/stop or project plan).
- Existing Workflow plans/ledger and delivery, lifecycle and check evidence,
  including relevant archived unverified scope/follow-ups for closed issues
  within this mandate.
- Current Host goal/stop, active/pending and their evidence.

The Delegator retains new owner requirements and source pointers through its
existing snapshot/issue handoff. Trusted Delegator records of an owner change
remain usable without a raw transcript; disclose uncertainty only where it
affects a finding. Missing sources remain explicit uncertainty, never authority
to invent work or claim full coverage. A Host-originated duty lost from every
available record cannot be reconstructed: this check does not promise perfect
recall.

## Result and Host decision

Return a brief receipt of checked scope, sources read, when, and unavailable
sources, followed by concrete findings in these four classes:

- Missing duty.
- Unsupported completion claim.
- Stale or duplicate pending duty.
- Conflict or missing source.

Each finding names its source, evidence or gap, and the smallest proposed
correction. Identify the candidate/revision or correction time when material;
no required hash/mtime inventory. Later explicit owner corrections win;
completed ledger lines are immutable. No record is not proof an action never
happened. A change explicitly awaiting relay, work genuinely in flight, or an
obligation covered by the current acceptance scope is not missing merely
because it lacks a separate row. No findings establishes only the stated scope.

The Host judges each finding and completion, records its decision and remaining
duties in its own existing JSON/run records, and assigns any repair under
current authorization. Sideagent writes no Host state, claims or dispatches no
work, grants no permission, and accepts no work. Use the existing
[Sideagent assignment, repair and exact-stop lifecycle](dispatch-collect.md);
reclaim the finished seat, with no idle permanent assistant. Findings use
existing QA/Workflow boundaries, not a new approval or completion gate.

## Independent Delegator inquiry and scheduling

The Delegator may initiate a request during its existing inquiry even when the
Host has not requested a check. For example: “Please check this mandate for
omitted duties against these goal/stop, correction and run-record pointers;
reuse the same in-flight check or sufficient unchanged result.” The sole Host
deduplicates and, if needed, assigns an authorized Sideagent. This preserves
independent initiation without a second inner-worker controller; an
unresponsive Host may delay the check, not transfer control to the Delegator.
An interval without a check is not alone a failure or reason for another audit.

Reuse existing Delegator `cadence`, `timer_owner` and the static Skill/project
entry: the single native timer wakes an inquiry, not an unconditional Sideagent
every interval. This gives the owner a recurring opportunity for independent
reconciliation while preserving scoped pauses, current authorization and Host
identity recovery under the existing snapshot/handoff rules.

## Owner changes at a decision boundary

Direct Delegator relay owns delivery: idle send, native noninterrupting steer
when supported, otherwise retain until idle. Urgent scoped stop/revocation
uses the existing immediate interrupt route; never delay for Sideagent or reads.
A trusted relay needs no verbatim quote. Missing/unreadable Delegator snapshot
means absent/unknown, not proof of no Delegator or no changes; direct relay works.

At a relevant claim, dispatch, plan adoption or acceptance, Host may read
relevant pending changes in the existing Delegator snapshot, without waiting
for its timer or mechanically sweeping every state. Delegator alone retains
scoped source-backed changes in its own snapshot until adoption is evidenced;
Host alone adopts into its body. Delegator observes that evidence and confirms
or compacts its record. Neither writes the other's file.

Admission, end-turn, file read or Sideagent receipt alone proves no adoption.
An ordinary scoped adopted value/duty with source correlation can suffice
without an extra reply. Identical values do not prove a one-shot action ran;
urgent stops require actual cessation evidence. Keep independent pending
actions and partial effects, not one scalar or an exactly-once claim.

Authority/scope precede time. Later explicit owner direction may supersede
earlier direction, including reauthorization after a stop. Stale drafts
cannot overwrite newer grants or runtime revocation. Re-evaluate only affected
items. Recover ambiguous sends, partial fan-out and interrupted Host/Sideagent
from existing records before replaying admitted work; unaffected authorized
work continues. No new queue, marker/revision protocol, ledger or scheduler.
