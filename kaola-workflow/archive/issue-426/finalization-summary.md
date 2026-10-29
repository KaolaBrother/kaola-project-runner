# Finalization Summary — issue-426

## Delivered

Accepted-done heartbeat task rows whose dispatch sessions are gone from `--live`
can now retire fail-closed. Three legacy shapes are covered by
`scripts/kaola-dispatch.py` + `scripts/kaola-record-contract.py`:

1. **Seat fallback** — a task row that names no seat binds its seats from the
   single supplied `kaola-dispatch-index/1` items (exactly one index file; a
   second sighting of a ref — in one file or two — is ambiguous and refuses).
2. **`collect-terminal` settlement** — an item whose collect finished
   (`mutation_status` exactly `accepted`/`completed`; collected session, repo
   and holder all matching) settles its seat when the session is absent from
   `--live` or stopped under the recorded holder. (`stale-collect-session-gone`
   settles the session-gone unknown shape.)
3. **`refs-unindexed` stop-evidence kind** — for tasks whose every dispatch ref
   never entered any index: the task id must embed exactly one issue number N
   (no other `i<digits>`/`I<digits>` token), the citation is exactly
   `kaola-workflow/archive/issue-N/mission-ledger.jsonl` at a commit that is an
   ancestor of HEAD, every ledger line is terminal (non-empty handed-over
   target), that commit's `workflow-state.md` declares exactly one
   `issue_number: N` at column 0 outside a CommonMark code fence (backtick
   openers carry no backtick in their info string; unterminated fences refuse),
   and no task-named session is live/ready.

Contract suite `tests/contract/test-issue-426-retire-legacy-seats.py`
(53 tests, red-first per shape) registered in both validate.sh groups.
Rendered skill copies included in-commit. Docs updated
(`docs/api.md`, `docs/dispatch-collect.md`); CHANGELOG `Unreleased` entry with
`Seats: restart required` (`scripts/kaola-record-contract.py` is in the
operator restart test).

## Candidate

- Branch `workflow/issue-426`: `a917d6e0` + `70969594` (round 1, grok seat 1) →
  `928d908e` (Host render follow-up) → `8b255412` (six fail-opens closed) →
  `bbd4a67c` (binding, devin) → `600166ba` (like-token guard + fence v1) →
  `eef428cd` (CommonMark fence state machine, grok seat 2) → `21ff668a`
  (info-string restriction) → `578d9b1a` (docs + CHANGELOG).
- Base: main `be4a26a8`.

## Evidence

- Suites on `21ff668a`: 426:53 / 421:45 / 412:31 / 372:13 / 397:27 all exit 0;
  `render-skills --check` exit 0 (docs commit `578d9b1a` is docs/CHANGELOG only).
- Expert review (codex/astra), six bounded rounds: round 1 FAIL (6 fail-opens),
  re-check FAIL (2 binding holes), review3 FAIL (2 token edges), review4 FAIL
  (3 fence edges), review5 FAIL (1 info-string edge), **review6 PASS** (repro
  refuses; 19/19 delta probes pass; real archive baseline still accepts).
  Two implementation-owner escalations per task-failure (grok seat 1 after two
  repair verdicts → devin after two → grok seat 2 completed).
- Real-row acceptance evidence (this run, live `.kaola` state): **10 of the 11
  stuck accepted-done rows retired with typed receipts** — i369 via
  `stale-collect-session-gone` (rev 848), i371/i373/i374/i375/i377/i378/i388/i389
  via `collect-terminal` (revs 849–856), i412 via `refs-unindexed`
  (`e005402b`, rev 857). Every settled fact was independently verified first
  (merged, issue CLOSED, archive committed, seats stopped at the time).

## Known failures / unverified scope

- `profiles-20261026` remains unretired, honestly: it has no conforming
  `kaola-workflow/archive/*/mission-ledger.jsonl` citation (Host-branch task;
  outcome lives in tag v0.9.30 + CHANGELOG). Widening the citation kinds is an
  owner-level design call, deliberately not made here.
- Reviewer-accepted residual risks: the workflow-state recognizer is a
  restricted declaration/fence parser, not a full Markdown parser; review
  verified settlement in memory, persistence relies on the suite evidence.
- Whole-inventory `./scripts/validate.sh` not rerun this run; focused
  validation covers the changed surface plus four retire-machinery neighbors.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/api.md
- docs/dispatch-collect.md
- scripts/kaola-dispatch.py
- scripts/kaola-record-contract.py
- scripts/validate.sh
- skills/antigravity-kaola-project-runner/scripts/kaola-record-contract.py
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/kaola-record-contract.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/kaola-record-contract.py
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/kaola-record-contract.py
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/kaola-record-contract.py
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/kaola-record-contract.py
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/kaola-record-contract.py
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/kaola-record-contract.py
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/hermes-kaola-project-runner/scripts/kaola-record-contract.py
- skills/hermes-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kaola-project-runner/scripts/kaola-record-contract.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-record-contract.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-record-contract.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-record-contract.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- tests/contract/test-issue-426-retire-legacy-seats.py

## Follow-Up Items

- **#427 (P2, filed post-sink):** the merged collect-terminal route requires a `session` key the `collect` tool never writes (only `acp_session_id`), so tool-collected terminal items cannot settle — this run's own `i426` task row is the repro (three items stopped/dead under their recorded holders, terminal collects, still `retire-unmet`). Also names the `superseded`-disposition settle gap. The `i426` heartbeat row stays done+accepted, done-not-retired (warn-level) until #427 lands.
- #421 (Layer-2 cleanup umbrella) stays OPEN per owner decision
  `owner-hb-two-layers-issues-do-sync-20261029`: not advanced this run; the
  merged #426 mechanism is available to it when the owner clears path-B.
- #425 (prevent-first P1–P5) on HOLD pending the Muse dual-Expert draft.

## Final readiness

Ready: mission ledger 2 done / 1 failed / 0 in-flight; candidate frozen at
`578d9b1a`; issue #426's acceptance basis met (routes + red-green suite +
review PASS + real-row proof); sink = merge to main, close #426, archive/sink
on -dev.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-426/.cache/final-validation.md
- kaola-workflow/archive/issue-426/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-426/finalization-summary.md
- kaola-workflow/archive/issue-426/mission-ledger.jsonl
- kaola-workflow/archive/issue-426/workflow-state.md
