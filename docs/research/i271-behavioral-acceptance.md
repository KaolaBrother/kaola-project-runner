# #271 isolated behavioral QA — fixture run 2 (2026-10-07, gaps closed)

Supersedes the withdrawn PASS (@91373205). Fresh-context fixture; every step's original receipts below; no full gates rerun.

## Step 1 — source-SHA'd rendered Skill body (load original)
Rendered `skills/kaola-project-runner/SKILL.md`: git blob `9c27bd5f77d888729d6a97f93706f349c856cff9`, 17,393 B; `references/dispatch-collect.md` blob `f7dcb32f73c3e1046d2ae89ba71a9deadda8f92a`, 8,183 B. This is the D2-era body: `project --seats` (1×) and `` `collect` `` (5×) present at BODY level. The fixture reads THIS body (isolated; no install claim, no live-Host load claim beyond it).

## Step 2 — discovery from body alone
Three entries name-checkable with **0 reference hops** (`execute` 1×, `project --seats` 1×, `collect` 5×). The flag CONTRACT (six JSON-file-path flags) still needs the dispatch-collect preamble — 1 hop, by design (body budget), counted.

## Step 3 — minimal correct params (body+--help only; refusal cost)
Real `execute --help` receipt: "JSON file path" appears on all six flags (6/6, `/tmp/fx-help.txt`). Fixture plan+auth authored from body+help with **0 refusals, 0 undocumented prompts**.

## Step 4 — autonomous dispatch (real admission)
`execute` on a one-item research plan (reply-exactly-FX-DONE): rc 0 in 1.9 s; item `fx-item` **in-flight/admitted**, holder `88ec9415ddfe22…` (full id `88ec9415ddfe229de35a2f39581d7bb2`).

## Step 5 — original result collection + precise reclamation
Status: alive→idle; events show `turn_ended` + idle. Guarded stop: FIRST attempt with a TRUNCATED holder id refused `holder-instance-mismatch` (guard works — this is the 2nd observation of the truncated-id ergonomics gap, reinforcing the earlier candidate fix); full-id stop: `stopped:true, exit 0, residual_pids []`.

## Step 6 — the two probes
(a) **No-eligible stale-done / fresh-forge**: rule verified READ-ONLY — live `gh issue view --json state` readback works at the boundary (#261 readback CLOSED, matching snapshot; the CAD counter-case #967/#536 reopen evidence remains the historical proof the rule is needed). GUIDANCE GAP CONFIRMED: neither `issue-dispatch.md` (4,853 B) nor the SKILL body contains any fresh-re-read/reopen rule at a no-eligible/done boundary — the D3 candidate sentence is ABSENT from the shipped tree; this fixture records it as an OPEN gap (not silently passed).
(b) **Acceptance-only-dependency**: no typed dependency-kind exists yet (D4 undecided by design); the fixture cannot probe behavior that is not implemented — recorded OPEN, mapped to the D4-after-replay-test decision, not claimed verified.

## Totals
Hops: 1 (flag contract reference, by-design). Refusals: 0 in fixture + 1 real guard refusal (ergonomics evidence). Undocumented prompts: 0. OPEN gaps: D3 boundary sentence absent (candidate text exists in the #271 design); D4 unimplemented (by decision).
Verdict: steps 1–5 PASS on isolated-fixture evidence; step 6 = one rule verified read-only + two named OPEN gaps. No blanket PASS language.
