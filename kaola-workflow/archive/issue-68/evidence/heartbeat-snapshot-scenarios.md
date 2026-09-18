# Issue #68 — the three scenarios, and where their evidence actually lives

These are the three beats the candidate is judged on. They were first written up with a
hand-authored "after" snapshot for each, asserted by a contract suite. The outer coordinator was
right to reject that as behavioral evidence: the same worker wrote the rule, the expected output and
the checker, so a green run only proved the constants matched each other. Two of those constants
later turned out to be wrong (see the sentinel findings).

So the division is now:

- **This file** — the scenario inputs and what the rule requires of each. Design evidence.
- **`sentinel/`** — an isolated ACP session that read the candidate cold, was given these same raw
  inputs and no expected answers, and produced its own compacted heartbeat and next step.
  Behavioral evidence. Start at `sentinel/00-findings.md`.
- **`tests/contract/test-issue-68-heartbeat-snapshot.py`** — only what a contract check can honestly
  check: that the rendered Skill and skeleton state the obligation, scope the carrier per host, add
  no new mechanism, and stay inside the budgets.

All of it is single-worker self-verification. No independent implementation or review agent was
dispatched.

---

## Scenario 1 — the authorized quota ran out and the human approved a substitute

Input heartbeat: `Codex ×2（账户额度本周剩余 20%）`, `并发 2`, `Claude Code 未授权`; in-flight
`codex worker kpr-issue-101` in `.kw/worktrees/issue-101` on Issue #101; unfinished
`#101 交付后仍需 review 与合并` and `#98 的 worktree 清理未做`; plus three inert lines — a 429 retry,
a Cursor model mismatch already recorded in Issue #99, and an abandoned plan A.

Human event in the beat: 「Codex 额度用尽，改用 Claude Code ×1，其他不变。」

What the rule requires: the exhausted Codex quota and the stale "Claude Code 未授权" go; Claude Code
×1 is in force from this beat, not the next; the three inert lines go, with Issue #99 left as the
pointer for the Cursor fact; the in-flight worker's session, worktree and Issue stay, together with
both unfinished duties; exhaustion alone authorizes no further platform substitution and cancels
nothing.

## Scenario 2 — concurrency raised last beat, lowered this beat, three workers live

Input heartbeat: `Codex ×3`, `并发 4（用户 2026-09-17 上调）`, `token 预算 本周 8M`;
`Issue #107 (P0) 先于 #103 (P2)`; three live workers A=#107, B=#103, C=#111 with their worktrees;
unfinished `#103 的验收证据未补` and `#107 合并后需通知其他 worker 同步`; one inert line about having
dispatched worker C after the raise.

Human event: 「并发降回 2，其他不变。」

What the rule requires: 并发 4 is replaced, not annotated — no "新规则优先" line beside the old value;
the three quota kinds stay three values (worker count, concurrency, token budget); the beat re-plans
under 并发 2 immediately; and the three live workers are *not* cancelled to fit the new ceiling —
their locators and remaining close-out duties stay.

## Scenario 3 — an ordinary beat: clear obsolete project messages only

Input heartbeat: `Claude Code ×1`, `并发 1`; in-flight `claude worker kpr-issue-112`; unfinished
`#112 候选待外层验收` and `#109 的 archive/sink 未完成`; and five lines of accumulation — the same
"#109 已合并到 main" narration twice, a transient tmux reconnect, a plan B the #112 design replaced,
and the project description for the third time.

Human event: none.

What the rule requires: subtraction with no human input at all. The duplicated merge narration, the
transient failure and the superseded plan go; the repeated description collapses to one. What must
survive is the live locator and both unfinished duties — including `#109 的 archive/sink 未完成`,
which is a finished *merge* but an unfinished *close-out duty*.

---

## How the acceptance lines are met

| Acceptance line | Evidence |
|---|---|
| quota exhausted + approved platform substitution | Scenario 1, sentinel output §1 |
| priority or quota raised / lowered | Scenario 2, sentinel output §2 |
| obsolete messages cleared, in-flight + close-out kept | Scenario 3, sentinel output §3, and the keep-lists of 1 and 2 |
| final heartbeat holds current constraints only | sentinel output: superseded values absent, `并发 2（本拍用户确认，唯一有效值）` |
| acts under the new constraint immediately | sentinel output §2: 「本拍立即按并发 2 执行」 |
| no unauthorized platform switch, no mistaken cancel | sentinel output §1–§2, with the one judgment call reported in `sentinel/00-findings.md` |
| behavior, not keyword presence | the sentinel was given no expected answer and wrote its own; it disagreed with two of my constants, which is the point |
| guidance covers all hosts, not only ZCode | sentinel answer C, read cold; plus the per-host contract tests |

## Not executed

- No live tmux/PTY smoke: this change is prompt text, adding no transport or script behavior. The
  sentinel exercised the ACP channel end to end (start / send / read / exact stop) as a side effect,
  but that was not a transport test.
- No real host was driven through a real beat on a real project. The sentinel answered from
  constructed inputs in a scratch directory; it registered no heartbeat and dispatched no worker.
- The sentinel is not an independent review. It had no stake in the candidate, but it was set up and
  read by the same worker that wrote the candidate.
