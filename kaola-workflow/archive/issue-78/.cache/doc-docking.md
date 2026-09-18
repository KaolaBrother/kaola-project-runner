# Documentation docking — Issue #78

Checked against AGENTS.md's Documentation Map: README.md, CHANGELOG.md, docs/.

| surface | verdict | reason |
|---|---|---|
| `CHANGELOG.md` | UPDATED | The change is user-visible: a refused `start` could consume a whole 60 s budget and leave an orphan. Entry added under `## Unreleased`, in the existing per-issue voice. |
| `docs/conventions.md` | UPDATED | "Shell safety" is where this rule belongs. A 7-line paragraph states the invariant (no here-document, no here-string in `scripts/kaola-tmux.sh`), why bash's pipe path deadlocks, and the two replacements. Landed in candidate 9632571. |
| `scripts/kaola-tmux.sh` | UPDATED | An 11-line comment above `usage()` carries the same rule at the point of use, with the measured pipe figures and a pointer to the enforcing test. |
| `README.md` | NO IMPACT | Describes project purpose and usage. No command, flag, or output changed. |
| `docs/api.md` | NO IMPACT | Documents the receipt schema and CLI surface. Refusal receipts are byte-identical before and after (verified for codex/pty and grok/acp), `usage()` output is `cmp`-identical, and no reason code, field, or exit status moved. |
| `docs/architecture.md` | NO IMPACT | Describes the transport/relay architecture. The repair is an implementation detail inside one entrypoint; no component, boundary, or data flow changed. |
| `docs/runner-v2-dual-transport-design.md` | NO IMPACT | Design record for dual transport. Both transports pass through the same entrypoint unchanged; transport selection and defaults are untouched. |
| `docs/grok-bot-host.md`, `docs/zcode-host.md` | NO IMPACT | Host bridge contracts. No host-facing behavior, budget, or Skill byte count changed; `render-skills --check` reports budgets OK. |
| `docs/acp-watch/list-view.md` | NO IMPACT | Mentions `kaola-tmux.sh` only as an invocation example; the invocation is unchanged. |
| live-verification records under `docs/` | NO IMPACT | Dated evidence of past live runs. Historical records are not rewritten. |

No public signature, JSON field, help text, environment variable, or validation
command changed, so nothing was transcribed that could drift from the real output.
The one new validation entry is the contract suite registered in
`scripts/validate.sh`, which is itself part of the candidate.

status: DOCKED
