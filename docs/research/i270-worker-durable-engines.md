# Issue #270 — Official-docs review: Temporal vs Restate (durable-execution comparison facts)

- Date: 2026-10-07. Mode: READ-ONLY web review. No installs, no repo writes; this file in `/tmp` is the only output.
- Sources: official pages only — `docs.temporal.io`, `docs.restate.dev`, and the two vendors' official GitHub `LICENSE` files (neither docs site publishes a license page; both docs `llms.txt` indexes were checked and contain no license entry — see Method notes).
- All quotes verbatim from the cited pages as fetched today. Pages are living docs; re-verify before long-lived citation.

## At a glance

| Dimension | Temporal | Restate |
|---|---|---|
| Server license | MIT (repo LICENSE) | BSL 1.1 → Apache-2.0 after Change Date (repo LICENSE) |
| Deployment unit | Separate multi-service "Temporal Service" (ex-Cluster) + persistence/visibility stores; Workers are separate polling processes | Single self-contained binary server; SDK embedded in your service; Cloud / BYOC / self-hosted |
| Durable semantics | Append-only Event History; deterministic replay from the beginning, results reused not recomputed | Per-invocation execution journal; replay skips recorded actions, resumes at suspension point |
| Exactly-once | Not claimed unconditionally: "'effectively once' experience, even though there may be several Activity Task Executions" | Claimed for durable webhooks (idempotency-key dedup) and "exactly-once semantics" in docs-home Reliable communication; general page avoids the term |
| Local / self-host | CLI dev server, Docker, Kubernetes, manual, embedded Go library | `restate up` lightweight dev server; brew/npm/binary/Docker; single node needs a persistent volume |

## Facts

### Temporal

**T1. License: MIT.** The temporalio/temporal `LICENSE` states "MIT License" (SPDX: MIT), "Copyright (c) 2025 Temporal Technologies Inc. All rights reserved." plus "Copyright (c) 2020 Uber Technologies, Inc."
URL: https://github.com/temporalio/temporal/blob/master/LICENSE
(Note: docs.temporal.io only says "open source Durable Execution platform"; no license page exists in its docs index — https://docs.temporal.io/)

**T2. Deployment model: a separate server ("Temporal Service", formerly "Temporal Cluster"), not a library.** "We now refer to the Temporal Cluster as the Temporal Service." The Service is "the group of services, known as the Temporal Server" combined with Persistence and Visibility stores. Workers are separate processes: "Workers poll for and process them [Tasks on Task Queues] to advance Workflows." Root docs: "Self-Host the Temporal Service or use Temporal Cloud."
URLs: https://docs.temporal.io/clusters/ , https://docs.temporal.io/tasks.md , https://docs.temporal.io/

**T3. Durable semantics: event-sourced history + deterministic replay from the beginning.** Event History is "a complete and durable log of everything that has happened in the lifecycle of a Workflow Execution." On Worker crash, the Worker replays the history to "recreate the state of the Workflow Execution" and "resumes progress from the point of failure as if the failure never occurred." Replay is re-execution, not snapshot restore: "Temporal doesn't restore memory from a snapshot. It starts the Workflow code from the beginning … replays the Event History step by step, and uses that history to guide the code back to the exact state as before." Side effects are not recomputed during replay: "When a Workflow calls an Activity, the Activity runs once, its result is recorded in the Event History … So Activities aren't executed again during replay." "This history is the source of truth for everything that happens in the Workflow."
URLs: https://docs.temporal.io/encyclopedia/event-history.md , https://docs.temporal.io/workflows.md

**T4. Determinism is the boundary of the replay guarantee.** Workflow code "has to make the same decisions when given the same history" and "shouldn't depend on any values not recorded in the history." Concrete exclusions: "A direct call to `Date.now()` could return a different value on replay", "A random number could change", "A network call, which wasn't performed inside an Activity, could return something new." Consequence: "If those values changed, the Workflow could take a different path and fail to match the recorded history." Replay-safe substitutes exist (context time, recorded timers/randomness).
URL: https://docs.temporal.io/workflows.md

**T5. Exactly-once claims are hedged; effective semantics are run-or-timeout plus retries (at-least-once tasks).** Activity scheduling "provides an 'effectively once' experience, even though there may be several Activity Task Executions." For Nexus operations, the handler "should be idempotent" because "the Temporal Service may issue several Nexus Tasks to attempt to start the Operation." Per-activity guarantee: "Temporal guarantees that an Activity Task either runs or timeouts" — lost tasks are not detected directly; a Start-To-Close Timeout then triggers retry per the Activity Retry Policy. No unconditional exactly-once statement appears on these pages.
URLs: https://docs.temporal.io/tasks.md , https://docs.temporal.io/activity-execution.md

**T6. Local / self-host options: CLI dev server, Docker, Kubernetes, manual, or in-process Go library.** The self-hosted guide offers "Docker, Kubernetes, or manual" deployment plus an "Embedded server" option: "Run Temporal in-process as a Go library for local development and testing scenarios." For local development, the Temporal CLI server "starts a complete Temporal Service with Web UI on your local machine" via `temporal server start-dev`.
URL: https://docs.temporal.io/self-hosted-guide/

### Restate

**R1. License: BSL 1.1 (server), converting to Apache-2.0.** The restatedev/restate `LICENSE` is the Business Source License 1.1 (SPDX: LicenseRef-BUSL-1.1); Licensor "Restate Software, Inc., Restate GmbH"; Change Date "4 years after release"; Change License "Apache License, Version 2.0". Additional Use Grant: production and internal deployments are permitted (including internal managed platforms); the grant excludes operating a "Public Restate Platform Service" — a managed service letting third parties register and invoke their own deployments over Restate's own APIs.
URL: https://github.com/restatedev/restate/blob/main/LICENSE

**R2. Deployment model: one self-contained server binary + SDK embedded in your services.** "Restate is distributed as a single binary that implements all features required to run a single- or multi-node cluster"; the installation page: "a single self-contained binary. No external dependencies needed." Single-node deployments require "a persistent volume"; clusters additionally need "an object store to store snapshots" (AWS S3 and MinIO supported today; GCS/Azure listed as coming soon). Your application embeds the SDK, which talks to the server per action: "The Restate SDK under-the-hood sends a message to the Restate server for each Context operation." Hosting choices: Restate Cloud, Restate BYOC, or Self-hosted.
URLs: https://docs.restate.dev/server/overview , https://docs.restate.dev/installation.md , https://docs.restate.dev/guides/request-lifecycle.md , https://docs.restate.dev/

**R3. Durable semantics: per-invocation journal, replay-and-skip resume.** "Restate persists the request and creates a new execution journal for this invocation" and "guarantees that it will process the request to completion, even in the face of failures." Each Context operation is recorded by the server in the journal; on retry the SDK "checks the journal for the last recorded result. If it finds a previous result, it skips executing that action" and "the handler resumes from exactly where it left off." Cross-service calls gain "end-to-end idempotency" via logged invocation events converted into target invocations.
URL: https://docs.restate.dev/guides/request-lifecycle.md

**R4. Exactly-once is claimed where dedup is enforceable (webhooks via idempotency key); the general lifecycle page avoids the term.** Docs home (Reliable communication): "guaranteed execution and exactly-once semantics." Durable webhooks page: "Restate persists all incoming events, and ensures that they are processed exactly once, across failures and restarts", deduplicating "on an idempotency key" — "If the sender of the event retries, Restate will not process the event again." Boundaries: no dedup-window duration is stated on that page, and the request-lifecycle page itself never uses "exactly-once"/"at-least-once" — the general mechanism is documented as journal replay + completion, not a delivery-guarantee claim for arbitrary external side effects.
URLs: https://docs.restate.dev/ , https://docs.restate.dev/guides/durable-webhooks.md , https://docs.restate.dev/guides/request-lifecycle.md

**R5. Local / self-host options: brew, npm, binaries, Docker; `restate up` for a lightweight dev server.** `brew install restatedev/tap/restate-server restatedev/tap/restate`, `npm install --global @restatedev/restate-server@latest …`, prebuilt binaries from GitHub releases, or Docker (`docker.restate.dev/restatedev/restate:latest`). "You can use `restate up` to start a lightweight, local dev server." Bundled UI at http://localhost:9070; "Remove the `restate-data` directory to wipe all invocations, state, registered services, etc."
URL: https://docs.restate.dev/installation.md

## Method notes and verification limits

- Official-only sourcing: every quote above came from `docs.temporal.io` / `docs.restate.dev` pages or the two vendors' own GitHub `LICENSE` files. No third-party summaries were used.
- License provenance caveat: neither docs site states its own license in prose or in its `llms.txt` URL index; the LICENSE files in the official repos are the closest official source and were fetched today (2026-10-07).
- Docs drift observed live (affects citation hygiene, not conclusions): `https://docs.temporal.io/develop/determinism` returns 404 — determinism content now lives in `https://docs.temporal.io/workflows.md`; `https://docs.temporal.io/cli/llms.txt` returns 404, so the `temporal server start-dev` statement is cited via the self-hosted guide page that quotes it.
- Terminology drift relevant to #270 comparisons: Temporal now brands the server "Temporal Service" (formerly "Temporal Cluster"); Restate brands hosting tiers Cloud / BYOC / Self-hosted.
- Not covered (no official-docs evidence in scope): SDK licenses for either vendor, Temporal Cloud/BYOC commercial terms, Restate TypeShare/`restatectl` cluster tooling beyond the installation page, and any performance or scale claims.

## Relevance sketch for KPR research (#270)

- Both systems centralize durability in a server-owned log (Event History vs execution journal) and restore by deterministic replay rather than memory snapshots — the same recovery shape KPR's worker-state reconciliation problem addresses.
- Neither vendor claims unconditional exactly-once: Temporal scopes it as "effectively once" with idempotent-handler requirements; Restate scopes it to dedupable ingress (webhook idempotency keys) and internal state/calls. External side effects remain the application's idempotency responsibility in both.
- Licensing is the sharpest adoption difference: Temporal server is MIT (permissive); the Restate server is BSL 1.1 with a production-friendly Additional Use Grant but a source-availability (not OSI) license until the 4-year Change Date converts it to Apache-2.0.

— End of report. Host compiles; this worker does not self-finalize.
