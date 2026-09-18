# Baseline (pre-fix) isolated behavioral legs — Issue #86

Frozen input: `evidence/baseline/SKILL.md` + `evidence/baseline/handoff.md`
(rendered from base commit in `base-commit.txt`; sha256 in `sha256.txt`;
3824 B and 8189 B on disk). Staged at a neutral path `/tmp/kpr-delegator-eval/skill-v1/`
so no leg could see this Issue, the repo, or the intended fix.

Five clean-context Opus legs, one per scenario, each told only "these two files are
your Skill; follow them literally" plus its own scenario file. Raw verdicts: `A.md`,
`B.md`, `C1.md`, `C2.md`, `D.md`.

| Scenario | Expected by #74+#86 | Baseline decision | Baseline correct? |
|---|---|---|---|
| A — platforms/counts/concurrency + account quota + all other key items; **no separate token cap** | START | **ASK** (demands `quota_token` as its own figure) | **NO — defect reproduced** |
| B — explicit 200000-token cap | START, cap carried verbatim, units unfused | START, `quota_token=200000 tokens` kept apart from `quota_account`/`quota_concurrency` | yes |
| C1 — no platforms, no counts, no quota at all | ASK | ASK | yes |
| C2 — "额度就 3", unit never stated | ASK | ASK | yes |
| D — live Host, Agent A→B, only priority changed | attach in place, no re-ask, no start | ATTACH_AND_SEND, delta only | yes |

Leg A is the failure Issue #86 names. It cited exactly the sentences this run removes:

- SKILL.md — "quota as separate concurrency, account, and token figures"
- handoff.md step 4 — "account and token quota as separate figures"
- handoff.md — "Handoff text (concurrency, account quota, and token budget stay three numbers)"

Leg A refused `start` although worker platforms (`zcode:1, codex:1`), concurrency (2),
account quota (40 conversations), priority (P1), goal, done/remaining, stop boundary, and
the canonical project path were all present. It did not fabricate an unlimited token
budget — it turned the absent one into a blocking question. That is the extra hard gate.

B, C1, C2, and D are the guard legs: the fix must leave all four unchanged.
