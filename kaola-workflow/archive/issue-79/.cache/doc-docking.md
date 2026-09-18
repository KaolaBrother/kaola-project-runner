# Issue #79 — documentation docking

Checked against `AGENTS.md`'s Documentation Map for changed public behavior.

| file | outcome |
|---|---|
| `README.md` | **FIXED.** Described the pre-3.12 `runtimeModel` mechanism as the mechanism, and implied the 2026-09-16 live Coding Plan gate covered current ZCode. Now states both paths, that the CLI version string cannot discriminate them, and names each live gate with the desktop build it ran against (3.11.2 on 2026-09-16, 3.12.3 on 2026-09-19) plus the explicit boundary that neither receipt carries to a build it was not run against. |
| `CHANGELOG.md` | **FIXED.** New `## Unreleased` entry for Issue #79 covering all three breaks, the error-driven protocol choice, the preserved policy boundaries, and the live verification. |
| `docs/api.md` | **FIXED.** Stated the adapter "hands ... the `runtimeModel` overlay" unconditionally. Now describes the pre-3.12 overlay and the 3.12+ path (two provider-config env names derived from the verified entry, `provider/updateAccountConfig`, `session/setModel` on the `account:*` provider with `options.reasoningLevel` and `persistAsWorkspaceLastUsed: false`, credential via `interaction/requestProviderRuntimeHeaders`). |
| `docs/zcode-host.md` | **FIXED.** Said the in-memory overlay carries the plan credential, which is only true pre-3.12. Now states the credential path per build and records that the two provider-config env names are derived from the verified entry, never inherited. |
| `third_party/zcode-acp/UPSTREAM.md` | **FIXED** (during the run, corrected again after outer review). Records the 3.12+ surface, the exact `states[<id>]` shape (`availability` + `entitled` + `current`), `session/setModel` carrying `options.reasoningLevel`, that both facts came only from running the real app-server, and that where upstream and the installed build disagree the installed build wins. |
| `platforms/zcode.yaml` | **FIXED** (template source; `skills/` regenerated, never hand-edited). |
| `docs/architecture.md` | **NO IMPACT.** No ZCode protocol claims; the shared worker/orchestrator template architecture is unchanged. |
| `docs/README.md` | **NO IMPACT.** Index only, no protocol claims. |
| `docs/conventions.md`, `docs/decisions/` | **NO IMPACT.** No decision was reversed; this run implements compatibility within the existing Gate 2 owned-adapter decision recorded in `UPSTREAM.md`. |
| setup / environment | **NO IMPACT.** `KAOLA_ZCODE_ENTRY` / `KAOLA_ZCODE_NODE` remain the required explicit inputs; no new user-facing configuration, and the two new env names are derived internally, never asked of the user. |
| examples | **NO IMPACT.** No example references the ZCode private protocol. |

Public behavior changes docked: the ZCode ACP transport now works against desktop 3.12+ in addition
to pre-3.12, with no change to the Runner's command surface, receipts schema, refusal vocabulary, or
credential boundary.

DOCKED
