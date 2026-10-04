# Opus response to the final reconciliation

2026-10-04. Design only. Read whole: `final-design-reconciliation.md` and the outer's
`design.md`. I did not open `index.html` or the CSS. Revision 4 of `opus-lifecycle-design.md`
stands as the long record and was not rewritten. My agreement below is agreement between the two
designers. It is not the user's approval to implement, and nothing live has changed.

## Five points

| # | Point | Position |
|---|---|---|
| 1 | Scoped plan checks, not transport; mixed-capability fan-out; no silent downgrade; no Worker cap from the DSH 3/4 sample | **Agreed.** My narrow check is exactly this: an `execute` plan admission, before any effect, against a requirement the Host stated for that item or against explicitly named presets. It is not a Runner refusal, not a ranking, not a blanket Class test. Support items that declare no requirement are not compared. A count shows "of N" only where an owner or resource limit exists |
| 2 | Ordinary permissions strictly inside existing authorization | **Agreed.** This is tighter than my revision 4 wording and replaces it: the Sideagent mechanically settles only an operation already authorized inside the exact assignment and the applicable tool policy, and gains no approval authority. Anything absent, ambiguous or value-laden stays pending as a durable record and goes through the Host and the Delegator to the user. A gate that needs the user's explicit confirmation is never satisfied by the Sideagent or the Host. It is a proposed boundary for the user to review, not a live permission |
| 3 | Alerts: watch / warn / severe by evidence and impact; persist after acknowledgement; coalesce on existing events; shown at every inquiry; no clock-based escalation | **Agreed**, as a recommendation the user may rename or re-scope. This closes the one item revision 4 still listed as open |
| 4 | Host verdict: the decision is the Host's; default record is a Sideagent transcription with its exact source; the Host's one-command record is the bootstrap and degraded path | **Agreed.** This supersedes the ordering in revision 4 §12. One condition keeps the default safe and is already in the design: the transcription names the Host turn it copies, and the recorded verdict is shown back to the Host in its next view, so a wrong transcription is visible to the one who decided |
| 5 | One active maintenance Sideagent; bounded parallel research helpers are workers | **Agreed.** This supersedes the sentence in revision 4 §10 and §19.1 row 14 that other `--role sideagent` helpers stay seat-exempt. Helpers are dispatched as worker items and are authorized and counted as workers. Only the one bound maintenance Sideagent has the role's seat exemption |

No concrete disagreement remains on my side.

## `design.md`

- **Event-to-state loop: present.** §9 states it: event arrives, the Sideagent reads the task and
  the real receipts, the tool updates the affected records, the views are regenerated, and what
  needs a judgment is recorded durably and the right role is notified.
- **Durable pending decisions: present.** §9 says a notification does not clear the pending
  duty and the item stays visible until adoption or resolution has evidence; §8 says the same
  for alerts. These are records, not prompts.
- **No material contradiction** with the reconciliation or the owner requirements, in the file
  as it stands now. The plan check is described as scoped to the item and not a Runner gate
  (§7); the permission boundary is in §2; capacity wait, Expert ask, hold recovery, process
  preservation, late-clear protection, the Host view and the timer rule all match.
- **`design.md` is left exactly as the outer wrote it. I touched it once and undid it.** My first
  read had no permission boundary, so I added one paragraph to §9. The outer had added the same
  boundary to §2 in the meantime, which I saw on re-reading. I removed my paragraph so the file
  holds no duplicate. Net change by me: none. `index.html` was never opened.
- Not material, not edited: §8 states the three alert levels as adopted; it could say they are a
  recommendation and that severity never rises by elapsed time alone. §2 does not say in so many
  words that the permission boundary is proposed rather than live; the document's "not yet
  implemented" heading covers it.

## Unproven implementation risks

1. **Process preservation.** Sparing a live worker on a replacement stop depends on group-level
   identity from existing records. Which platforms record nested holders, and whether an agent
   always ends when its holder dies, were not measured. Needs a per-platform test.
2. **Carrier re-anchor.** Works only on holders running the new build. Older holders stay
   listed and are read each pass; their results are found at the next pass, not when they happen.
   The cross-platform path has never been exercised.
3. **Relay.** Delivery to the Sideagent's holder is at-least-once. Across that holder's death,
   wakes are rebuilt by a full adoption pass. Correctness rests on that pass being complete.
4. **Timer read-back** is unverified on every outer platform.
5. **`eligibility()` in `kaola-dispatch.py` was never read line by line.** Whether a standing
   Expert grant's scope is a field a tool can compare is unknown.
6. **State size.** No managed state was measured for a real project. The plan depends on the
   holder change that bounds only the injected view, and on adopting state and that holder
   together.
7. **Late detection.** A direct Runner `start` bypasses every `execute` check. An item that does
   required work without declaring it is caught only at review, not before it runs.
8. **Raw edits.** A record deleted by hand is undetectable; a decision deleted that way is lost.
   Source pointers and the worker-role write refusal are traces, not security.
9. **Escalation latency.** No carrier exists from the Host to the Delegator; a request reaches
   the user at the Delegator's next read.
10. **Skill budgets** are at their ceilings; the role rewrite is unproven until rendered.
11. **Citations** are line numbers read before the v0.8.2 pin and were not re-checked against it.
