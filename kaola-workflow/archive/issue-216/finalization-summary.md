# Finalization Summary — issue-216

## Delivered

Issue #216: pause an unusable account seat and route login recovery to the user. The Delegator
Host-recovery and Project Runner failure/quota references now separate three causes from existing
Runner receipts, captures and events, without adding any classifier, credential store, registry,
timer, login automation, or fixed QA stage.

Issue parts → evidence (commit 9577effd, review fixes 7305fbda, merge d25dc8d6 onto main 9f126987):
- **Limit failure** — explicit quota exhaustion, a reached rate limit, or a stated
  reset/window/account limit → `quota-packages.md` §Confirmed exhaustion ¶1. Reuses the existing
  #207 class handoff unchanged (Expert → user; Elite → safe reclaim, run-seat availability removed
  from the heartbeat snapshot, hand to another already-authorized Elite not sharing the limited
  pool; Worker → another suitable Worker under the pool permission; no suitable replacement →
  report and ask); the full class table is not duplicated into the Host prompts.
- **Degenerate evidence is not proof** — a bare 429, timeout, network error or reset-window
  metadata without an explicit limiting reason, and a session still connecting or awaiting a reply
  → `quota-packages.md` §Confirmed exhaustion ¶1; `host-brick.md` §Limit-failed Host ¶1.
- **Authentication / account-access failure** — `login expired`, `authentication required`,
  revoked or invalid credentials, `account disabled`, or an equivalent refusal; also an explicit
  refusal with no supported class remedy → `quota-packages.md` §Account unavailable ¶1. Pause only
  the affected seat: task, worktree/ledger locator, valid output and exact Runner identity
  preserved, no new work, exact-stop at the existing safe lifecycle boundary once the failed turn
  settles, marked temporarily paused in the run's authorization/heartbeat snapshot — a pause, not
  the grant revocation of a limit failure, deleting no model/profile; unrelated authorized work
  continues (¶2). User report names the affected runtime and seat, the exact runtime message and
  what was preserved; no secrets in chat and no other seat dispatched for the blocked task before
  user direction (¶3). Resume after user-confirmed restoration and direction from existing
  receipts/records with no duplicate claim or lost valid work; a user-directed replacement follows
  the existing seat/class boundaries; no automatic login probe or scheduled retry (¶3).
- **Delegator Host case** → `host-brick.md` §Account-unavailable Host: preserve the frontier and
  every in-flight worker's ownership evidence (session, native resume id, worktree) and valid
  output, contain the Host through that evidence and the safe handoff boundary, force-clean no
  in-flight seat and drop no worker, and never invoke the #207 ZCode fallback or any other Host
  replacement for an authentication failure.
- **Never log in for any cause** → `quota-packages.md` §Confirmed exhaustion ¶2 and §Account
  unavailable ¶1/¶3; `host-brick.md` §Limit-failed Host ¶5 and §Account-unavailable Host ¶1/¶4.
- **Host-recovery heading** renamed "Quota-exhausted Host" → "Limit-failed Host"; reference H1 →
  "Bricked, limit-failed or account-unavailable Host".
- Entry pointers → `worker-profiles.md.tmpl` (limit failure by class + account-unavailable pause),
  main `SKILL.md.tmpl` step-1 quota line, README (new "Login or account access failure" section;
  "authentication error" removed from the ignored-with-429 bucket). CHANGELOG entry states all
  three branches, pause vs revocation, no-login-for-any-cause, user-led resume, and
  `Seats: restart not required`.

## Coordination

- Based on 3bbdb373; rebased onto 9f126987 after #209/#213/#214 landed.
- Merge conflicts resolved keeping BOTH semantics: #214's `## Local availability and authorized
  rows` section and #213's QA-ownership material coexist with the account-unavailable/limit-failure
  branches in `worker-profiles.md.tmpl` and `quota-packages.md`.
- The rebased main-Skill pointer briefly exceeded `main_skill_bytes` (17418/17408) because #213's
  additions consumed the headroom; trimmed to 17406/17408 rather than raising a budget.

## Verification

- `render-skills.py --write` then `--check`: PASS, budgets OK on the frozen candidate, on the
  rebased branch, and on merged main. Generated copies byte-identical to templates.
- Sizes: quota-packages 8131/8192, host-brick 4682/8192, main skill 17406/17408, delegator
  4094/4096 (unchanged; the longer entry-pointer label does not fit and budgets are never raised).
- Focused suites PASS: test-generated-skills, test-issue-123-shared-refs,
  test-issue-148-quota-packages, test-issue-74-kaola-delegator, test-issue-86-delegator-quota,
  test-progressive-disclosure, test-issue-187-delegator-any-host, test-issue-118-seat-cap,
  test-issue-41-orchestrator, test-issue-65-host-contract (27/27), test-issue-162-upgrade-safety.
  The two suites that failed before this run's rebase are now green, fixed by landed #209.
- Independent clean-context review of the frozen candidate (subagent 5f714d8d, read-only): NO
  BLOCKERS; the five acceptance scenarios distinguish correctly; both anchors
  (`#confirmed-exhaustion`, `#account-unavailable`) and all cross-references resolve. Its four
  minor findings were addressed except the Delegator entry-pointer label, which the frozen
  `external_skill_bytes` budget forbids.
- Scenario coverage: explicit rate limiting; confirmed quota exhaustion; bare/ambiguous 429;
  explicit login expiry; still-connecting session.
- Protected docs: never staged, never copied; verified at their expected hashes before and after
  the merge, with the exclude guard applied before any sink step and restored byte-exact.

## Closure

- Sink: merge into `main`, pushed `9f126987..d25dc8d6`.
- Issue #216 closed with a summary referencing the merge commit and the three-branch scope.
- No release, tag, or install. Operator-test paths untouched (`Seats: restart not required`).
- Worktree and branch removed after archive.
