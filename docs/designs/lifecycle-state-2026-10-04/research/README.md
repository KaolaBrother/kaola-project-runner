# #255 lifecycle research and agreements

Source evidence behind the consolidated #255 design, copied from the run's
working directory so it survives close-out. These files are historical
evidence, not live instructions; [../design.md](../design.md) is the current
design.

| File | What it is |
|---|---|
| `checkpoint-state.md`, `ckptstate-retrieval-notes.md` | Worker report on LangGraph-style checkpoints and research state, with retrieval notes |
| `durable-returns.md`, `durable-returns-sources.md` | Worker report on Temporal-style durable messaging and returns, with primary sources |
| `fanout.md`, `fanout-retrieval-notes.md` | Worker report on Argo-style fan-out/fan-in |
| `reclaim.md`, `kpr255-reclaim-retrieval-20261004.md` | Worker report on Kubernetes-style reconciliation and reclaim |
| `*-host-verdict.md` | The Host's verdict on each report |
| `lifecycle-closure-agreement.md` | Lifecycle closure agreement (revision 2) |
| `sideagent-nodes-agreement.md`, `sideagent-nodes-final-reconciliation.md` | Sideagent node agreement and its final reconciliation |

Adopted only as narrow mechanisms on existing fields: assignment identity
apart from transport identity, original intent and revision before effects,
exact incarnation ownership, sourced partial results apart from semantic
acceptance, interrupted effects kept unknown, derived-view reconciliation, a
durable pending/acknowledged distinction, explicit cleanup intent, and evidence
by reference.
