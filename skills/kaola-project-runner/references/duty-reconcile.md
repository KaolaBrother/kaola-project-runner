# Bounded duty reconciliation

At recovery and before quiescence or closeout, the Host reads applicable owner
goal/stop records and relevant newer corrections, comparing authorized duties
with actual evidence. Load this reference when a record-visible source/evidence
mismatch, an unreconciled latest owner change, genuinely unaccounted coverage
after a handoff, or an explicit owner/Delegator request calls for one bounded,
read-only Sideagent check. Remembered confidence alone is insufficient. Reuse
sufficient unchanged evidence for the same scope and candidate; reuse a check
already in flight. A heartbeat, issue completion, Host replacement or multi-issue closeout alone
does not require an audit. A verified completed HOST compaction owes the bounded
recovery check below; a worker compaction owes no node.

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
current authorization. The check itself decides no finding, claims no work,
grants no permission and accepts no work; the bound Sideagent records only the
Host's adopted outcome ([lifecycle-state.md](lifecycle-state.md)). A separate
check helper is a counted worker item
([dispatch-collect.md](dispatch-collect.md)); reclaim it when finished, with no
idle permanent assistant. Findings use
existing QA/Workflow boundaries, not a new approval or completion gate.

Write in accordance with ASD-STE100.

## Independent Delegator inquiry and scheduling

The Delegator can request one source-scoped check during its existing inquiry.
The sole Host deduplicates it and uses an authorized Sideagent or sufficient
unchanged evidence. An unresponsive Host delays this path; it does not transfer
worker control. The existing `cadence`, `timer_owner` and static entry wake an
inquiry, not a node every interval. No interval alone calls for an audit.

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

Later owner direction can supersede earlier scope, including a stop. Preserve
newer grants/revocation. Reconcile ambiguous sends, partial effects and interrupted
Host/Sideagent from original records before replay; continue unaffected work.
Use no new queue, marker protocol, ledger or scheduler.

## Recovery input and checkpoint

The exact verified Host registers an inquiry without a business write:

```bash
$S recovery-input --file FILE --kind request --source '<inquiry>' --evidence '<original locator>'
```

The carrier uses `--kind host-compaction --signal-cursor C`. The tool verifies the
original completed, session-bound HOST event. Kind alone attests nothing.
`maintenance.recovery_input` has closed fields `seq`, `kind`, `occurrence_id`,
`source`, `holder`, `at`, `evidence`; `recovery_seq` is monotonic. The existing
batch receipt owns sent identity. Repeats coalesce; unsent work uses one node.
Occurrence-less signals can owe another check. This is not exactly-once.

At an unchanged handled revision, the carrier sends a recovery-only batch.
Read goal/grants, duties/decisions and task-dispatch-result-reclaim links from
AGENTS, Delegator locators, Workflow, index and Runner originals. Preserve original Host retirement references.
Invent, accept and judge no tasks. Add `--recovery-seq N` to the sent checkpoint:

```json
{"input":"recovery#N","checked":{"authorization":["original"],"duties":["original"],"links":["original"]}}
```

Use `unavailable:{scope:reason}` for unread originals instead of a checked scope.
Missing/empty sources cannot PASS and stay visible Host duties. Optional `applied`
needs records this node wrote. Settlement requires the original sent batch,
selected input and node holder. Revision-only checkpoints and `last_verified`
cannot settle it. Related alerts need separate scoped entries and unchanged
selection evidence. Keep newer/unrelated inputs; checkpoint N leaves N+1 pending.

Recipe/start/admission/lost-node/checkpoint/stop failures keep the duty and a
`maintenance-returned` obligation with original evidence and Host next action.
One safe wake and both current views expose it. Reconcile original effects,
confirm the old holder stopped, repair the binding, then request a bounded check.
Equal sequence, elapsed time or a justified live node needs no repeated reminder.

The existing resume event scan reoffers an unregistered Host completion. Failed
writes retain the signal locator and Host notice; the existing tick can retry.
An old tool refuses visibly. A new tool reports `carrier_supported:false` for an
old holder and retains the request; update at an authorized safe boundary.
Migration preserves typed input/scalar or refuses malformed data with the duty
intact. No install is implicit.

Codex alone adds `session.compaction:{}` at both initialize paths and records its
request. Installed codex-acp 2.0.1 supports the shape (inspected child 0.160.1).
Live proof is pending. Without a verified signal, use inquiry recovery.
