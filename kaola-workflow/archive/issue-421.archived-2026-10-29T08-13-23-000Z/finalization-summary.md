# Finalization Summary — issue-421

## Delivered

Fail-closed retire evidence routes, failed Sideagent binding recovery, and a bounded
`maintenance-returned` alert. All evidence kinds are typed in `scripts/kaola-record-contract.py`;
the routes are in `scripts/kaola-dispatch.py`.

- (a) Sideagent failed-binding recovery: `state ensure-sideagent --recover-failed --live L
  --evidence E`. Host caller only, binding state `failed`, original evidence (no `ORIGINAL_*`
  placeholder), `--live` shows the old node gone, no `holds/*` or `decisions/*` row names the old
  session or the Sideagent (`sideagent-held`). No sweep, no `host_revision` move. `state check`
  reports `sideagent-failed` with the command (read-only). Routes: `sideagent-failed`,
  `sideagent-held`, `sideagent-not-failed`, `old-node-live`.
- (b) `state retire --index` accepts `kpm.dispatch-index/1.x` identified by
  `project.canonical_root`. KPM items resolve as `<task_id>/<id>` or a unique bare id; a repeated
  bare id is ambiguous. KPM closed set `returned|failed|cancelled`. The index mirror never writes a
  KPM index.
- (c) `--stop-evidence` kind `index-stop-receipt` (holder- and session-bound row evidence with
  `stopped: true`, `residual_pids: []`, `observed_at` before boot time) and kind `archived-ledger`
  (committed ledger under `kaola-workflow/archive/`, ancestor of HEAD, committed before boot time,
  every line terminal, one line naming the session with its holder or preset). `evidence()` now keeps
  `session`, `stopped`, `residual_pids` and `observed_at` when a receipt carries `stopped`.
- (d) `--stop-evidence` kind `direct-dispatch`: no dispatch refs, no recorded holder, a recorded
  preset, the task's own evidence names the session. No index rows are made.
- (e) `--stop-evidence` kind `sweep-purge`: the purge id is in the current
  `maintenance.last_sweep.removed`; holder and platform match. Report-only provenance;
  `stop_receipt: null`.
- (f) `maintenance-returned` bounded by construction: repeated `binding-or-recipe-unavailable`
  `recovery#N` failures coalesce into the latest same-(why, next) row (`count`, `coalesced_from`,
  max `host_revision_through`); a Host task retire removes that task's own non-stop
  `host:tasks/<id>@<rev>` inputs atomically (`settled_inputs`), and the alert leaves when no input
  remains. Stop duties, other whys, `batch:` rows and current-record `host:` rows never merge or
  leave. Checkpoint and read paths are unchanged.
- Every new route is Host writer and accepted-done only; an absent `--live` row alone, free text,
  an unbound receipt and a non-accepted task still refuse.
- Contract suite `tests/contract/test-issue-421-retire-recovery.py`, 45 tests, registered in
  `python_suites_all` and `python_suites_b`.
- Docs: `docs/api.md`, `docs/dispatch-collect.md`,
  `templates/orchestrator/references/lifecycle-state.md` (held at 8191 of 8192 bytes; meaning-bearing
  lines kept).

## Candidate

`workflow/issue-421` @ `b7caf9c22f82ce559bc2bf0fb861e1286c608672` (commits `4671b965`, `b7caf9c2`;
base `0852ed75`).

## Acceptance

Host verdict FULL SCOPE ACCEPTED. `4671b965` accepted for (a)–(e); repair `b7caf9c2` (f) verified
independently by the Host: test-issue-421-retire-recovery 45/45, render --check PASS, guards clean.

## Evidence

- Recorded validation: `.cache/final-validation.md` (verdict pass, bound to the candidate tree).
- Final-bytes suites: render --check PASS; 421 (45/45), 255 (171), 259 (63), 412 (31), 324 (10),
  327 (4), 362 (4) OK. Earlier on `4671b965`: 397, 406, 349, 354, 286, 289, 309, generated-skills OK.
- Field shapes read (read-only): KPM `.kaola/dispatch-index.json` (`kpm.dispatch-index/1.7`),
  KPM `.kaola/heartbeat-prompt.pre-t987u.json` (56203-byte alert, 156 `recovery#` rows of
  `binding-or-recipe-unavailable`, 3 `host:tasks/` rows, 83 alert evidence refs).

## Known failures or unverified scope

- KPM: 0 of 219 current task dispatch refs are in KPM's current `kpm.dispatch-index/1.7`; those
  tasks now refuse with `not in the index` instead of `index-unidentified`. This stands until
  KPM-side cleanup.
- No existing index row carries a stop receipt; for seats stopped before this change (c) uses
  `archived-ledger`.
- Claire (Studio) and Selena (vrpai) rows were not readable from here; their fit to (d)/(e) is
  unverified.
- `test-issue-298-absent-decision-retire` `test_docs_name_the_absent_receipt` fails identically on
  unmodified main (the v0.9.34 release emptied the Unreleased CHANGELOG section); pre-existing.
- `test-issue-244-dispatch` has 9 failures identical on unmodified main; pre-existing.
- Whole inventory was not run; focused suites only. No live seat measurement.
- Release note: `scripts/kaola-record-contract.py` is in the CHANGELOG operator restart set, so the
  release that ships this states `Seats: restart required`. `scripts/kaola-acp-holder.py` is
  unchanged. No release or tag in this run.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- docs/api.md
- docs/dispatch-collect.md
- scripts/kaola-dispatch.py
- scripts/kaola-record-contract.py
- scripts/kaola-recovery-routes.py
- scripts/validate.sh
- skills/antigravity-kaola-project-runner/scripts/kaola-record-contract.py
- skills/antigravity-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/kaola-record-contract.py
- skills/claude-code-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/kaola-record-contract.py
- skills/codex-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/kaola-record-contract.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/kaola-record-contract.py
- skills/devin-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/kaola-record-contract.py
- skills/droid-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/kaola-record-contract.py
- skills/dsh-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/kaola-record-contract.py
- skills/grok-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/hermes-kaola-project-runner/scripts/kaola-record-contract.py
- skills/hermes-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/hermes-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/references/lifecycle-state.md
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kaola-project-runner/scripts/kaola-record-contract.py
- skills/kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-record-contract.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-record-contract.py
- skills/opencode-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-record-contract.py
- skills/zcode-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/orchestrator/references/lifecycle-state.md
- tests/contract/test-issue-421-retire-recovery.py

## Follow-Up Items

- None filed. The KPM index mismatch is a KPM consumer item (Muse tracks KPM).

## Readiness

Ready to finalize and sink (merge).

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-421/.cache/final-validation.md
- kaola-workflow/archive/issue-421/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-421/finalization-summary.md
- kaola-workflow/archive/issue-421/mission-ledger.jsonl
- kaola-workflow/archive/issue-421/workflow-state.md
