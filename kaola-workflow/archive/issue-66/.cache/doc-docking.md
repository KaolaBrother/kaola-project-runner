# Documentation docking — issue-66

candidate: 2da5f92dd5838cd7545b2ea13ae8de56abb35e24
status: DOCKED

Checked against `AGENTS.md`'s Documentation Map (`README.md`, `CHANGELOG.md`, `docs/`) for the
public behavior this run changed: two main-Skill entry points, one new generated reference
`skills/kaola-project-runner/references/host-startup.md`, the heartbeat-skeleton `body` field, and
the heartbeat prompt-file defect receipt (`present but UNUSABLE …` in the delivered notification,
`heartbeat_body_error` on the host holder's `worker_event_delivered` entry).

| File | Verdict |
|---|---|
| `docs/zcode-host.md` | FIXED — new "Two startup flows (Issue #66)" section naming both entry points and what the startup reference carries; the Payload bullet now separates an absent prompt file from one present-but-unusable and transcribes the real receipt text and field name. |
| `docs/README.md` | FIXED — the index had no `zcode-host.md` entry at all (pre-existing gap); added one line naming the host doc, the carrier, its defect receipt, and the two flows. |
| `CHANGELOG.md` | FIXED — one `## Unreleased` block: the two entry points and the new on-demand reference, and the defect receipt including the single-read `(body, defect)` guarantee. |
| `README.md` | NO IMPACT — project overview and install/usage commands are unchanged; it enumerates no orchestrator references. |
| `docs/api.md` | NO IMPACT — renderer/installer/CLI contracts, receipt bounds and flags are unchanged; no CLI surface, flag, or receipt field was added or renamed (`heartbeat_body_error` is a holder event-log field, documented in `docs/zcode-host.md` where the carrier is specified). |
| `docs/architecture.md` | NO IMPACT — it names "the main Skill and its references" generically and enumerates no reference files; the one canonical Skill system, budget enforcement and boundary story are unchanged. |
| `docs/conventions.md` | NO IMPACT — change boundary, source-of-truth and validation policy are unchanged; this run followed them (template edit → `render-skills.py --write`/`--check` → `validate.sh`). |
| `docs/grok-bot-host.md`, `docs/acp-watch/**`, `docs/decisions/**`, live-smoke and PoC reports | NO IMPACT — no Grok Bot bridge, watch-surface, decision-record or historical-report behavior changed; `templates/grok-golden` and `templates/budgets.json` are byte-identical to the baseline. |

Transcribed, not invented: the receipt strings and field names above were copied from
`scripts/kaola-acp-holder.py` (`_heartbeat_payload`, `heartbeat_prompt_body`) and observed in the
live run's own records (`evidence/live/10-event-chain.txt`, `heartbeat_maintained` /
`heartbeat_body_error` keys) and in `tests/contract/test-zcode-heartbeat-contract.py`.

Skill payload text itself is generated, never hand-edited: the shipped
`skills/kaola-project-runner/**` came from `./scripts/render-skills.py --write` and is verified by
`--check` (budgets OK) inside `./scripts/validate.sh`.
