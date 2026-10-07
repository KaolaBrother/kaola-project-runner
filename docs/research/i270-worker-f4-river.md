# Issue #270 family-4 — River (one lightweight durable-job representative)

Choice: [riverqueue/river](https://github.com/riverqueue/river), a maintained Go library with jobs in Postgres. Oban was not used. GitHub API 2026-10-07: not archived; default branch `master`; pushed `2026-10-07T03:58:46Z`; stable `v0.49.0` (`2026-10-05`); prerelease `rust/v0.1.0-alpha.1` (`2026-10-07T03:58:08Z`).

Pin: commit `1e4d6f8e638288ed1614a7988be1f1b55a698c35` (`2026-10-07T03:56:14Z`, "Prepare Rust release v0.1.0-alpha.1"), tree `38ddfae027fa94dea997fd59bc38f481db1e2cd8`. Not diffed against tag `v0.49.0` (`da5a26e21c18`).

## License partition

SOURCE_VERIFIED: root `LICENSE` is Mozilla Public License 2.0; Exhibit A and Exhibit B are inside that text. GitHub's license API reports SPDX `MPL-2.0`. `rust/Cargo.toml` sets `license = "MPL-2.0"`. The `rust/` listing has no separate LICENSE file.

SOURCE_VERIFIED: `js/LICENSE` is GNU LGPL Version 3. `js/package.json` sets `"license": "LGPL-3.0-or-later"`.

SOURCE_VERIFIED: sampled Go files (`client.go`, `job.go`, `worker.go`, `riverdriver/river_driver_interface.go`) have no per-file Exhibit A/B header.

Reviewed surface: Go client plus `riverdriver/riverpgxv5` SQL. Also present, unread: `riverdatabasesql`, `riversqlite`, `rust/`, `js/`.

## Durability and recovery

README_MENTIONED (`docs/README.md`; same paragraph in `doc.go`): one Postgres for application data and the queue. A job is enqueued if that transaction commits, removed on rollback, and hidden from workers until commit.

SOURCE_VERIFIED: durability is a `river_job` row and a state machine (`docs/state_machine.md`; `rivertype.JobState*`), not an execution history. `JobGetAvailable` (`riverdriver/riverpgxv5/internal/dbsqlc/river_job.sql`) takes `state = 'available'` with `FOR UPDATE SKIP LOCKED`, then in that statement sets `running` and increments `attempt`.

SOURCE_VERIFIED: a crash leaves the row `running`. `JobRescuer.runOnce` (`internal/maintenance/job_rescuer.go`) loads rows with `attempted_at` before `now - RescueAfter`. `JobRescueMany` updates one only while it is still `running` and before that horizon: `retryable` if `attempt < max_attempts`, else `discarded`, or `cancelled` if metadata has `cancel_attempted_at`. `JobSchedule` then sets due `retryable`/`scheduled` rows to `available`, or `discarded` on a unique-key conflict. `Config` comment: `RescueStuckJobsAfter` defaults to 1 hour and can re-run a job still working. `JobStateRunning`'s comment says `available`; the rescuer SQL writes `retryable`, `discarded`, or `cancelled`.

SOURCE_VERIFIED: `ResumableStep` skips a named step on retry after an earlier success. `ResumableSetCursor` stores a cursor only if the attempt errors; `ResumableSetStepCursorTx` can persist it inside a transaction immediately. Step skip, not a server journal.

## Exactly-once and idempotency

SOURCE_VERIFIED: README, `doc.go`, and the Go/SQL read here never say "exactly-once" or "at-least-once". `Worker.Work` can run again after an error or a rescue. The `Config.MaxAttempts` comment says the default is 25. `internal/retrypolicy/default.go` waits `errorCount^4` seconds, ±10% jitter.

SOURCE_VERIFIED: idempotency is optional insert dedup. `UniqueOpts` hashes kind and enabled dimensions (`internal/dbunique.UniqueKey`, SHA-256). `JobInsertFastMany` uses `ON CONFLICT (unique_key)` on a partial index (`unique_key` and `unique_states` set, state in the bitmask) `DO UPDATE SET kind = river_job.kind`, and flags the existing row via `xmax`, PostgreSQL 18 `OLD`, or a metadata nonce. The `ByState` comment default includes `completed` and `running`, so a finished row still blocks insert until cleanup. That is not exactly-once `Work`.

## Transaction coupling

SOURCE_VERIFIED: `Client.InsertTx` uses the caller's transaction. Its comment: not worked until commit; gone on rollback. `Client.Insert` opens its own transaction. `JobCompleteTx` requires `job.State == running` and calls `JobSetStateIfRunningMany`, which changes `state` only while the row is still `running`. Its comment: rollback undoes completion; a later worker error leaves a committed completion in place.

Representative interfaces: `Worker.Work`, `Client.Insert`, `Client.InsertTx`, `JobCompleteTx`, `UniqueOpts`, `JobGetAvailable`, `JobRescueMany`, `ResumableStep`.

## Against Temporal and Restate

Compared with `docs/research/i270-worker-durable-engines.md` (pages not re-fetched). Temporal: separate multi-service log, replay from the start, "effectively once" plus idempotent handlers, MIT server. Restate: one binary, journal resume at the suspension point, exactly-once only for idempotency-key webhooks, BSL 1.1 server. River keeps the queue in the application's Postgres and recovers by re-running a job row. Enqueue and completion can share that transaction with application writes. No workflow-history replay, and `Work` effects outside that transaction are not exactly-once.

Limits: read-only fetch; no install, test run, or full-repo audit. Host compiles; this worker does not self-finalize.
