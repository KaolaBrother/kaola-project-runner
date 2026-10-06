# KPR1035C scratch consumer — QA fixture (opencode Host)

Disposable consumer root for the Issue 264 core-lane Host-compaction
maintenance QA. This is seeded test data, not a real project.

<!-- KPR-USER-REQUIREMENTS-START -->
## User special requirements — scratch QA fixture

1. Keep this disposable run finite: report exact command, receipt and cursor
   outcomes; do not add mechanisms.
2. The bound maintenance node reconciles only seeded duties; it invents,
   accepts and judges no tasks.
3. Preserve the seeded dispatch link `qa-prior-reclaim-1` as a visible Host
   obligation until the Host resolves it.
4. Checkpoint entry contract (`state checkpoint --entries`): a `recovery#N`
   input accepts ONLY the keys `input`, `checked`, `unavailable`, and the
   optional `applied` (for records the node wrote itself). The `retained` key
   belongs only to `host:*` inputs — never put `retained` on a `recovery#N`
   entry.

<!-- KPR-USER-REQUIREMENTS-END -->
