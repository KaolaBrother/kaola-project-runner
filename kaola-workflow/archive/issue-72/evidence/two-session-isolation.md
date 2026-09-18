# Issue #72 — live ACP evidence for the naming contract

Run `issue-72`, worktree `.kw/worktrees/issue-72`, candidate at the commits recorded in this
run's mission list. Every command below was run with `scripts/kaola-acp.py` from that
worktree on 2026-09-18. Raw receipts sit beside this file.

## 1. Two simultaneous same-issue workers stay distinct (acceptance item 2)

Both probes were the **same platform**, the **same repo**, and the **same issue** — the
sharpest case the contract has to survive — and differed only in the purpose token.

| | `codex-KPR-i72-probe-a` | `codex-KPR-i72-probe-b` |
|---|---|---|
| native `acp_session_id` | `01a0b3d0-a01d-7661-9e1d-ddeb54df0e9e` | `01a0b3d0-c860-79e0-95bd-c51ac2ad9461` |
| `agent_pid` | 95086 | 95357 |
| `holder_instance_id` | `0b8c88ffa7f7cdee5b7aa6157bbf8b22` | `a074b567c0aaeb49efbaaf66db2132ac` |

Receipts: `start-probe-a.json`, `start-probe-b.json`.

Independent transport, not just independent records: one minimal prompt went to each and each
answered its own, with no crosstalk (`send-probe-a.json`, `send-probe-b.json`):

```text
codex-KPR-i72-probe-a  ->  "PROBE-A"   stop_reason end_turn
codex-KPR-i72-probe-b  ->  "PROBE-B"   stop_reason end_turn
```

## 2. Exact stop stays exact (acceptance item 4)

`stop --session codex-KPR-i72-probe-a` returned `stopped: true`, `agent_exit_code: 0`,
`residual_pids: []`, `swept_child_pgids: []`. Diffing the full host session list before and
after (`list-before-stop.json`, `list-after-stop.json`): **removed** exactly
`codex-KPR-i72-probe-a`, **added** nothing. The other nine sessions — including this run's own
session, Issue #70's live worker, and four sessions belonging to a different project — were
all still `agent_alive`. `codex-KPR-i72-probe-b` was stopped afterwards; neither probe remains.

## 3. The join does not cross-bind (acceptance item 3)

This host happened to carry the harder case already: **four active runs on one repository**
(`issue-67`, `issue-70`, `issue-71`, `issue-72`, each `workflow-state.md` naming
`https://github.com/KaolaBrother/kaola-project-runner.git`). Applying the reference's rule —
anchored name, then repository identity, then the claimed `issue_number` — to the live
sessions:

```text
claude-code-KPR-i72-naming            -> issue run issue-72
codex-KPR-i72-probe-b                 -> issue run issue-72
grok-KPR-i67-fix                      -> issue run issue-67
grok-KPR-i71-fix                      -> issue run issue-71
claude-code-kaola-issue70-0918        -> unknown (name is not the anchored contract)
claude-code-kaola-vrpcadcore          -> unknown (other repository)
claude-code-kaola-vrpcadcore-b        -> unknown (other repository)
grok-kaola-vrpcadcore                 -> unknown (other repository)
kimi-cli-kaola-vrpcadcore             -> unknown (other repository)
zcode-kaola-vrpcadcore-orchestrator   -> unknown (other repository)
```

Two sessions share `issue-72` and stay distinct ACP cards; three different issue numbers on
one repository resolve to three different runs. `claude-code-kaola-issue70-0918` is a real
grandfathered session started before this contract: it falls back to **unknown** rather than
being guessed onto the newest or nearest run, and it was not renamed or restarted — it is
still running, untouched.

## 4. What this evidence does not cover

- No consumer was exercised. Whether KaolaTerminal (or anything else) parses these names and
  draws the bar was **not** verified here, end to end or otherwise; that is issue #274's
  scope in that repository.
- The join above was computed by applying the written rule to real host state in a read-only
  way. It demonstrates that the facts the rule needs are present and sufficient on a real
  host; it is not a shipped implementation, and this repository ships no such parser.
- No live check of the "different numeric issue on a different repository" case: this host has
  active runs for one repository only. The repository-identity requirement that covers it is
  stated in the reference and asserted in the contract suite.
