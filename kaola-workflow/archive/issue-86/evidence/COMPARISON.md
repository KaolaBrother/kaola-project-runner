# Issue #86 — isolated behavioral A/B over the frozen Delegator prompt

Same five scenarios, same five briefs verbatim, same model (Opus), ten independent
clean-context legs. The only variable is the rendered Delegator text:

- `baseline/` — pre-fix, sha256 in `baseline/sha256.txt` (SKILL 3824 B, handoff 8189 B)
- `fixed/`    — post-fix, sha256 in `fixed/sha256.txt`   (SKILL 4010 B, handoff 8186 B)

No leg could see this Issue, the repo, the templates, the tests, or the other leg:
each was given only its two staged files plus its own scenario file, at a neutral path.

| Scenario | Correct behaviour | Baseline | Fixed | Changed? |
|---|---|---|---|---|
| **A** — platforms `zcode:1, codex:1`, concurrency 2, account quota "40 conversations", goal, done/remaining, P1, stop boundary, canonical path; **no separate token cap** | START | **ASK** — demanded `quota_token` as its own figure before `start` | **START** — `quota_token=unspecified`, explicitly "not unlimited", not fused into the account figure | **YES — the defect, now fixed** |
| **B** — same, plus an explicit 200000-token cap | START, cap carried verbatim, units unfused | START, `quota_token=200000 tokens` kept apart from account/concurrency | START, identical treatment | no |
| **C1** — no platforms, no counts, no quota at all | ASK | ASK (for 5 items, including a token figure) | ASK (for platforms/counts/concurrency only; explicitly states the absent token figure is *not* the blocker) | decision unchanged; the question no longer includes a token demand |
| **C2** — "额度就 3", unit never stated | ASK | ASK | ASK — and refuses to default the ambiguous 3 to `unspecified`, because 3 might itself be the token figure | no |
| **D** — live Host, Agent A→B, only priority changed | attach in place, no `start`, no re-ask | ATTACH_AND_SEND, delta only | ATTACH_AND_SEND, delta only, quota untouched | no |

Exactly one decision flipped, and it is the one Issue #86 names. The four guard legs —
explicit cap carried verbatim, genuinely missing authorization still asks, ambiguous unit
still asks, live Host never re-asks — are unchanged.

Two properties worth reading in the raw legs:

- Fixed leg A sent `quota_token=unspecified`. It did not claim an unlimited token budget,
  did not convert 40 conversations into tokens, and did not raise anything.
- Fixed leg C2 explicitly declined to write `unspecified` for the ambiguous "3", on the
  grounds that the ungiven-unit rule does not cover a unit that was given unclearly. That
  is the distinction Issue #86 asks for, reached from the prompt alone.

Raw verdicts: `baseline/{A,B,C1,C2,D}.md` and `fixed/{A,B,C1,C2,D}.md`, unedited.
Contract-test leg: `baseline/contract-test-on-baseline.txt` (FAIL) vs PASS after the fix.
