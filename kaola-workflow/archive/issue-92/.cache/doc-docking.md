# Documentation docking — Issue #92

status: DOCKED

Checked against AGENTS.md's Documentation Map and the run's changed public behavior
(carrier retention/retry, the `undelivered_worker_events` status field, the new
`heartbeat_carrier_*` record kinds, and the Host-side freshness obligation).

| surface | outcome |
|---|---|
| `docs/zcode-host.md` | **UPDATED.** It is the authoritative carrier document and described the Issue #76 `permission_required` behaviour this run changes. Added the retry to the trigger diagram, one bullet for undelivered-wake retention (owed-code set, no cap/expiry, `undelivered_worker_events`), and one for the delivered-but-stale distinction and the Host's freshness duty. Transcribed from the shipped code, not paraphrased. |
| `README.md` | **UPDATED earlier in the run** — the permission-defaults paragraph carries the recovery and the explicit statement that a post-write settlement can still leave the Host a locator for a gone request. |
| `CHANGELOG.md` | **UPDATED earlier in the run** — one Unreleased entry, narrowed in the final round to remove the false no-stale-send absolute. |
| `skills/kaola-project-runner/references/heartbeat-skeleton.md` | **UPDATED via its template** (`templates/orchestrator/references/heartbeat-skeleton.txt`), re-rendered; pinned by `test_the_host_contract_requires_fresh_verification`. |
| `skills/kaola-project-runner/references/zcode-host-dispatch.md` | **NO IMPACT, deliberately.** It already states the event is a locator decided from the worker's live `pending_permissions`; it sits at 8174/8192 B and its sentences are pinned verbatim by the #65/#70 contract tests. |
| `docs/api.md` | **NO IMPACT.** It documents CLI commands and receipt bounding, not worker-event record kinds; `undelivered_worker_events` is an additive status field inside the already-documented bounded receipt. |
| `docs/architecture.md`, `docs/conventions.md`, `docs/decisions/` | **NO IMPACT.** No new component, convention, or architectural decision — the change reuses the existing carrier, the existing watchdog tick, and the existing dedup. |
| `docs/codex-host.md`, `docs/grok-bot-host.md`, `docs/acp-watch/` | **NO IMPACT.** Non-ZCode hosts and the watch guide are untouched; the carrier op stays ZCode-only. |
| setup / environment / examples | **NO IMPACT.** No new flag, env var, install step, or example. |

Scope note preserved: all evidence in this run is hermetic (fake ACP app-servers, a
test-owned `FakePeer`). No live ZCode model run was performed; the docs describe
transport and carrier behaviour, not a full-chain release verification.
