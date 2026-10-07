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
(a) **No-eligible stale-done / fresh-forge**: CLOSED by probe + minimal fix. Isolated mock-forge fixture (read-only; no real issues touched): snapshot says 9001/9002 CLOSED, live shows 9002 OPEN -> boundary decision DEFERS to live (stale snapshot must not decide) — probe PASS both before (rule absent, gap confirmed) and after the fix (rule present and applied). The minimal authorized A fix SHIPPED: one boundary sentence in `templates/orchestrator/references/issue-dispatch.md` (re-read live state; reopened = eligible; acceptance-stage dependency never blocks START) — budget-paid, original asserts untouched, render PASS, 244 EXIT=0. The AI replay-test for the dependency conflation remains root's decision gate for any D4 field; no new schema field was added or required for this probe.
(b) **Acceptance-only-dependency**: probe CLOSED at the baseline level — current source has NO runtime gating of needs/depends (stored fields only; verified by semantic-read scan), so the conflation was always a Host-judgment behavior; the fix is the same shipped guidance sentence (kind recorded when it matters; acceptance-kind never blocks start). D4 typed fields remain deferred behind the root replay gate BY DESIGN — not a prerequisite this fixture leaves open.

## Totals (run 2 + probe completion, corrected)
Hops: 1 (flag contract reference, by-design). Refusals: 0 in fixture + 1 real guard refusal (ergonomics evidence). Undocumented prompts: 0. The former OPEN gaps (D3 sentence absent; D4 unimplemented) are RESOLVED as of @5e3378a8: the boundary sentence is shipped and probed; the dependency rule is guidance-level on the no-field baseline (D4 fields stay deferred behind root's replay gate).
Verdict: CONDITIONAL — steps 1-5 have real fixture receipts; step 6's two probes passed via mock-forge with the fix shipped. TWO evidence qualities remain open until the independent-reader run completes (in flight, opencode-KPR-i271-reader): (i) fresh-context autonomous discovery + authoring by a reader with no prior project context (the fixture author's own text counts are not that), and (ii) a collect-entry ORIGINAL receipt (event capture + guarded stop are not collect). No full-document PASS is claimed until those land; the doc will be updated with the reader's hop counts and collect receipt verbatim.
