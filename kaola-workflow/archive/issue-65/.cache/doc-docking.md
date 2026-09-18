# Documentation docking — Issue #65 (candidate bc720e38722e67a860149f8a931287b9f000ee5a)

status: DOCKED

Checked against AGENTS.md's documentation map and the run's changed public
behavior: a new `steer` operation with two Agent-selected modes, new receipt
fields and refusals, the ZCode Host post-dispatch event-wait contract, and the
integrated Issue #66 startup flows.

| File | Checked | Outcome |
|---|---|---|
| `README.md` | yes | **Updated.** The steering snippet now shows both modes — native `steer` and `steer --steer-mode interrupt` — states that the composite interrupts and continues the same ACP session, and that `injected` / `written` / `unknown` are not interchangeable. |
| `docs/api.md` | yes | **Updated.** The `steer` section carries the ACP-only scope, both modes, the `steer-mode-required` refusal, the full outcome table with `steer_consumed` and `steer_confirmation`, `no-acp-session`, the turn-object-bound cancel with `cancel_sent`, and the `resent_without_interrupt` case. Every field name was transcribed from `scripts/kaola-acp-holder.py`, not invented. |
| `docs/zcode-host.md` | yes | **Updated** earlier in the run for the event-wait contract; re-read at the candidate. Its "never steering" rule is still true — a worker event is delivered at a turn boundary and is never converted into a `steer` — and it now sits beside a `steer` that exists on all nine platforms. |
| `docs/README.md` | yes | **Updated.** The API entry now names the `steer` operation; the ZCode Host entry (from Issue #66, merged) already covers the two startup flows. |
| `CHANGELOG.md` | yes | **Updated.** Issue #66's two entries and Issue #65's five entries both present under Unreleased; the merge conflict was resolved by keeping both, not by choosing. |
| `docs/architecture.md` | yes | No impact: no boundary, ownership or generation rule changed. Skills are still generated from templates and manifests only. |
| `docs/conventions.md` | yes | No impact: the change boundary, source-of-truth and validation conventions are unchanged; the new suites follow them. |
| `docs/runner-v2-dual-transport-design.md` | yes | No impact: a design-baseline record of the transport split, which this run did not alter. |
| `docs/acp-watch/*`, `docs/decisions/*`, PoC and live-smoke reports | yes | No impact: dated records of past work. |
| `docs/grok-bot-host.md` | yes | No impact: the bridge host is untouched; `templates/grok-golden/` stayed frozen and `kaola-grok-bot-verify.py` passes. |

Generated surfaces (`skills/`, `hosts/grok-bot/`) are not hand-docked: they come
from `templates/` through `scripts/render-skills.py --write`, which was re-run,
and `--check` passes with `budgets OK`. The user-facing reference
`references/steering.md` is new in this run and generated the same way.
