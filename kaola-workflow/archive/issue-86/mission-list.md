# Issue #86 — Delegator must not turn an unspecified token quota into an extra hard start gate

Scope: `templates/kaola-delegator/SKILL.md.tmpl`, `templates/kaola-delegator/references/handoff.md.tmpl`,
necessary README/contract-test changes. Generated `skills/` and `hosts/grok-bot/` only via
`scripts/render-skills.py --write`. No new schema, state file, quota engine, or transport gate.

Hard constraint discovered at intake: rendered `skills/kaola-delegator/references/handoff.md` is
8189 bytes against a `reference_bytes` budget of 8192 — 3 bytes of headroom. The handoff edit must
be net-neutral or net-negative.

## 1. Baseline behavioral evidence: prove the current prompt wrongly stops
- item: With the frozen pre-fix rendered prompt text, run isolated clean-context model legs over
  scenarios A (worker platforms/counts/concurrency + account quota given, no separate token cap,
  all other key items present), B (explicit token cap), C (missing platform/count, and ambiguous
  quota meaning), D (live Host A→B attach). Record raw verdicts as the preserved baseline.
- status: done
- dispatched: 5 isolated clean-context Opus legs (one per scenario), each given ONLY the frozen
  pre-fix rendered SKILL.md + handoff.md staged at /tmp/kpr-delegator-eval/skill-v1/ and its own
  scenario file; raw verdicts land in /tmp/kpr-delegator-eval/out-v1/{A,B,C1,C2,D}.md and are
  copied to kaola-workflow/issue-86/evidence/baseline/
- result: kaola-workflow/issue-86/evidence/baseline/ (RESULTS.md + A/B/C1/C2/D.md + frozen
  SKILL.md/handoff.md + sha256.txt + base-commit.txt). Defect reproduced: leg A returned ASK and
  demanded a separate `quota_token` although platforms/counts/concurrency/account quota/priority/
  boundary/path were all present, citing the three sentences this run replaces. Guard legs B
  (START, cap verbatim), C1 (ASK), C2 (ASK), D (ATTACH_AND_SEND, no re-ask) were already correct.

## 2. Contract test that distinguishes correct from incorrect
- item: Add the Issue #86 acceptance assertions pinning the decisive sentences: quota is carried in
  the units the user actually gave; an absent separate token cap is not a missing-authorization
  stop and is not reported as unlimited; ambiguous quota meaning or a genuinely missing key value
  still asks; a live Host does not re-ask. Prove the test FAILS on the pre-fix candidate.
- status: done
- dispatched: self
- result: tests/contract/test-issue-86-delegator-quota.py (46 checks), registered in
  scripts/validate.sh python_suites_all + python_suites_b. Pre-fix run recorded at
  evidence/baseline/contract-test-on-baseline.txt — FAIL on the first assertion
  ("Skill no longer demands three separate quota figures at extraction"). Post-fix: PASS.

## 3. Minimal prompt fix in the two shared templates
- item: Edit `SKILL.md.tmpl` "Extract once" and `handoff.md.tmpl` step 4 + handoff text so the three
  quota figures stop being three mandatory numbers, while unit non-fusion, no-guessing, and
  no-authorization-expansion survive. Keep the handoff within `reference_bytes`.
- status: done
- dispatched: self
- result: templates/kaola-delegator/SKILL.md.tmpl (Extract once) and
  templates/kaola-delegator/references/handoff.md.tmpl (step 3 reflow, step 4, handoff-text
  header, quota_concurrency slot). `reference_bytes` had only 3 B of headroom, and the budget is
  a locked invariant, so the handoff edit is net-negative (template 8175 -> 8172 B; rendered
  8189 -> 8186 B) — funded by two lossless rewordings that drop no rule. The fuller statement of
  the rule lives in SKILL.md, which had real headroom (3824 -> 4010 B of 4096).

## 4. README docking
- item: State the given-units rule in the README A→B paragraph without weakening the existing
  "only after current authorization is complete" contract the #74 test pins.
- status: done
- dispatched: self
- result: README.md A→B paragraph — quota travels in the units actually given; an ungiven unit is
  carried as unspecified and does not block the start, is not unlimited, and is not a fourth
  question; an unclear unit is ambiguous, so ask. The #74 sentence the contract test pins is
  untouched.

## 5. Render, check, validate
- item: `./scripts/render-skills.py --write`, `--check`, `./scripts/validate.sh`. Record exact
  outcomes and byte headroom.
- status: done
- dispatched: self. First validate attempt was cut short with the previous session and left no
  exit code (it had reached installer acceptance + the ACP sweep) — discarded, not counted.
  Candidate committed, then rebased onto main 18db64b (#85 sink): the only conflict was
  scripts/validate.sh, where #85 and #86 register a suite in the same two lists; resolved by
  keeping both (#85 in python_suites_all + lane a, #86 in python_suites_all + lane b).
  Post-rebase: render-skills.py --check PASS (budgets OK; SKILL 4010/4096, handoff 8186/8192),
  test-issue-86 46 checks PASS, test-issue-74 151 assertions PASS. The rendered delegator files
  at the rebased candidate are sha256-identical to the frozen text the fixed legs read, so the
  behavioral evidence still binds. Full ./scripts/validate.sh re-running with the exit code
  captured to evidence/validate-postfix.exit and the raw log to evidence/validate-postfix.txt.
- result: PASS. Two earlier background attempts died with their sessions and left no exit code —
  both discarded, neither counted as evidence. The run that counts was executed in the
  foreground in this worktree: `./scripts/validate.sh` exit 0, recorded in
  evidence/validate-postfix.exit, raw 348-line log in evidence/validate-postfix.txt. Zero
  `^FAILED: ` and zero `^SKIPPED: ` lane lines. render-skills PASS with budgets OK (log line 1);
  test-issue-74 151 assertions, 0 failed (line 335); test-issue-86 46 checks PASS (line 346);
  grok-bot bridge verify PASS. Working tree clean at c0bcaf5.

## 6. Post-fix behavioral evidence and freeze
- item: Re-run the same isolated model legs against the fixed rendered text, preserving both raw
  results side by side. Freeze the candidate commit SHA, report diff/verification/model evidence,
  and STOP for outer review. No finalize/sink/close without explicit user ACCEPT.
- status: done
- dispatched: 5 isolated clean-context Opus legs with briefs verbatim identical to the baseline
  legs, pointed at the fixed rendered text staged at /tmp/kpr-delegator-eval/skill-v2/; raw
  verdicts land in /tmp/kpr-delegator-eval/out-v2/{A,B,C1,C2,D}.md and are copied to
  kaola-workflow/issue-86/evidence/fixed/
- result: evidence/fixed/{A,B,C1,C2,D}.md and evidence/COMPARISON.md. Exactly one decision
  flipped and it is the one Issue #86 names: leg A now STARTs and sends
  `quota_token=unspecified`, explicitly not unlimited and not fused into the account figure.
  Guard legs unchanged — B carries the 200000-token cap verbatim, C1 still asks (and no longer
  demands a token figure), C2 still asks on the unclear unit and declines to default the
  ambiguous "3" to unspecified, D attaches to the live Host with a delta-only send and no
  re-ask. Candidate frozen at c0bcaf5 (rebased onto 18db64b). STOPPED for outer review: the
  user's own decision on whether a token cap is mandatory is still pending, so no Workflow
  finalize, archive, sink, or Issue closure.
