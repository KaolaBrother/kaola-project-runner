## Host acceptance and finalization evidence correction

The owner accepted candidate `8115c73df48458f79da73037184257f0730c35c9`, parent exactly `1b6c6f6642349a8838a6f0c0c5bb5bff03d29e82`, and authorized this run's finalize, sink, closure, archive and cleanup with its existing claim digest unchanged.

The omitted-wait live trial on `1b6c6f66` remains **FAILED**: `source: standalone-default`, `wait: true`, detail `caller record does not prove a live Host role and identity`, `duration_ms: 763316`, outcome `turn_completed`. That send was not rerun, and no live record was edited to add `session_role`.

The exact existing legacy Host and worker ownership facts were present; only the new persisted role field was absent. The accepted fix reuses the existing `host_session()` derivation defining `host_class` for absent/null roles. Exact platform, session, repo, holder, dispatcher and heartbeat binding still must match. A supplied `host_class` boolean or nonstandard name grants no Host role. Explicit `--wait`/`--no-wait` still win; missing/mismatched identity remains blocking with detail and no new refusal.

Evidence includes the read-only real-record decision comparison and an isolated actual Grok CLI admission trial: omission returns `owning-host-default`, `wait: false`, `in_progress` in 93 ms while the worker remains active; the useful read-only QA task completes and exact stops report no residual processes. These are transport proofs. Full model-driven Host assignment choice, turn-boundary permission handling and delivery without rescue remain **UNVERIFIED**, within the owner's recorded acceptance boundary. The original failed trial is not rewritten as a passing result.

The previous frozen full validate log covers **1b6c6f66 only**. Affected tests actually run on the accepted frozen bytes are recorded separately: holder binding 7 tests, wait/event contract 24 tests/654 checks, ACP 84 tests, permission wake 5 tests/78 checks, session role 11 tests, and renderer/budget checks. Finalization's measured full repository validation result will be recorded below only after that command exits.

Run evidence and the finalization summary are preserved under `kaola-workflow/issue-246/` and will move to `kaola-workflow/archive/issue-246/` through the installed transaction. No install, release or tag; no change to the 17408/8192 ceilings or #244's `start-timeout` assertion. #251 remains outside scope.

Measured finalization validation on **8115c73**: `env -u FORCE_COLOR -u CLICOLOR_FORCE NO_COLOR=1 CLICOLOR=0 ./scripts/validate.sh` exited **0**. Log: `qa/validate-8115c73.log`. All listed contract suites ran; Bash 3.2 lacks mapfile/BASHPID, so only the watchdog wrapper is skipped and suites run unwatched. This is new evidence for 8115c73, not relabeling the frozen 1b6c6f66 log.
