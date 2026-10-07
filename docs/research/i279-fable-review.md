# Fable bounded review — #279 DDD method, commit 41b12e85c0b46ac3ee592185c1f83074ae758271

Read-only review of `docs/research/i279-ddd-method.md`, `i279-ddd-contract-tests.md`,
`i279-ddd-source-register.md` at the exact commit (verified HEAD == 41b12e85; diff 9d8de351..41b12e85 inspected).

## Verdict: CHANGES-REQUIRED (minor, wording-level; no redesign)

The six root corrections and both complements are carried in the sections the Integration
status names, and the diff shows every previously offending sentence was rewritten (aggregate
≠ work unit; candidate contexts/labels; deployment-choice framing; expected-change surface;
no `.kaola/` store; KW/VRPAI/CAD unverified; Q1–Q3 technical). Two residual spots still
contradict corrected points and should be fixed before this text is cited as the corrected
baseline. Both are one-line edits.

## Findings

### F1 — contract-tests §"One NEW contract test per context-edge" (line 25) contradicts §4 grouping and prejudges Q3
- Text: heading "One NEW contract test per **context-edge**", fixtures "C4→C5" and "C1→C3".
- Why: method §4 (lines 87–91) places C4, C5, C6 in ONE candidate context (orchestration-state)
  and C1, C3 in ONE candidate context (session-runtime). §6 Q3 (line 170) explicitly leaves open
  whether C4/C5 are one or two contexts. Calling C4→C5 and C1→C3 "context-edges" asserts them as
  cross-context boundaries, which violates point (b) (contexts are candidates) and the complement
  rule stated 10 lines earlier (line 16–18: suites are component-seam evidence, "do not establish
  that the candidate DDD bounded contexts … are real"). It also prejudges Q3, against point (f).
- Minimal fix: rename heading to "One NEW contract test per component seam named in a pack
  (described fixtures — proposed, NOT executed)" and add after line 27: "C4→C5 and C1→C3 are
  seams inside the §4 candidate groupings; they are not evidence that those groupings are
  separate contexts (Q3)." Method §6 line 155 and §7 line 229 already say "per dependency" and
  need no change.

### F2 — method §5 pack items 1 and 3 (lines 115, 117) retain one-context / one-consistency-boundary wording
- Text: item 1 "the exact terms (**this context's** ubiquitous language)"; item 3 "the few rules
  that must hold across the unit …; **they define the consistency boundary**".
- Why: the new §5 lead (lines 110–113) states a unit "may touch several aggregates or contexts"
  and is not an aggregate (point a). Item 3's singular "the consistency boundary" re-equates the
  unit with one aggregate; item 1's "this context's" re-equates it with one context. The filled
  C4 example is fine because it happens to be single-context, but the generic list is what gets
  reused.
- Minimal fix: item 1 → "the exact terms of the context(s) the unit touches"; item 3 → "the few
  rules that must hold across the unit …; they name the consistency boundaries the unit must
  respect (one or several)."

## Residual non-blocking notes

- N1 §7 data vs failure rows (lines 225–227): "No new canonical `.kaola/` store … a runtime
  artifact would require separate justification" sits next to "retire → read-only export of
  packs" and "the same pack schema" / "cannot interpret a pack". Not a contradiction if a pack is
  a versioned Git document with an explicit version field, but "export" presumes a store. Suggest:
  "retire → the versioned pack documents simply remain in the project's Git; nothing else is
  removed." Interface, failure and data boundaries are otherwise coherent and match contract-tests
  line 34.
- N2 §4 line 104–105 "an in-process translator **suffices**" states a deployment conclusion as a
  definite inside an `[ASSUMPTION]` paragraph; "may suffice" matches point (c) better.
- N3 §4 table row 1 "core (differentiator: …)" reads as a hypothesis only via the column header;
  keep the header if the table is excerpted.
- N4 §6b tags the Vernon redesign patterns `[SRC]` while §6b lines 176–179 and register line 129
  disclose the Vernon quotes are worker-reported, not Host-verified. Disclosure is adequate;
  a `[SRC, worker-reported]` tag would be tighter.
- N5 §3 lines 69–71 quote Tolerant Reader without the per-schema permission-field carve-out
  (contract-tests line 29, §7 line 226); a cross-reference would prevent a blanket reading.
- N6 Verified: aa1c1444 exists and matches the "#271 partial evidence" note; `/tmp/` paths are
  gone; "allowed-change" no longer appears; Integration-status section references (§3/§4/§5/§6/§7)
  point to text that actually carries each point.

Not assessed (out of scope): B0 design/migration, source accuracy, style.

## Re-check @6986f6e6

Scope: F1/F2 resolution and whether the F1/F2/N1/N2/N4/N5 edits introduced a new contradiction
with the six points. Diff `41b12e85..6986f6e6 -- docs/research/` inspected; commit verified.

### Verdict: PASS

- **F1 resolved.** `i279-ddd-contract-tests.md:25` now reads "One NEW contract test per component
  seam named in a pack"; lines 27–29 add "C4→C5 and C1→C3 are seams inside the … §4 candidate
  groupings; they are not evidence that those groupings are separate contexts (Q3)." No
  "context-edge" remains anywhere in `docs/research/` (git grep at 6986f6e6). Consistent with
  §4 candidacy (point b), Q3 open (point f) and the seam-evidence complement.
- **F2 resolved.** `i279-ddd-method.md:117` "the exact terms of the context(s) the unit touches";
  `:119` "they name the consistency boundaries the unit must respect (one or several)". Matches
  the §5 lead (unit ≠ aggregate, may span contexts; point a).
- **N1 edit** (`:231`): "retire → the versioned pack documents simply remain in the project's Git,
  nothing else is removed" removes the implied store; consistent with point (e) and the
  data-ownership row.
- **N2 edit** (`:107`): "may suffice" keeps the ASSUMPTION paragraph hypothetical (point c).
- **N4 edit** (`:205`): provenance tag matches register line 129.
- **N5 edit** (`:70–72`): per-schema carve-out cross-referenced; same rule as contract-tests line 29.

No new contradiction with points (a)–(f) found; Integration-status section references remain valid.

### Residual non-blocking (no fix required)

- `i279-ddd-method.md:131` and `:141` still say "retire = … read-only export" for retiring a
  *context/component boundary* (design §5 keep-data rule), while §7 `:231` says pack documents
  "remain in Git" for uninstalling the *DDD component*. Different objects, so not a contradiction;
  if desired, `:131` could read "uninstall + data kept read-only by the consuming project".
- `:70–72` places the `[DERIV]` per-schema carve-out inside a line opened by a `[SRC]` tag; a reader
  could take the carve-out as sourced. Optional: prefix the parenthetical with `[DERIV]`.
