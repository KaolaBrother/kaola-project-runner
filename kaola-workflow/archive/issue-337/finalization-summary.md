# Finalization Summary — issue-337

## Delivered

Devin's Host-capability records now name the verified CLI, and the production
Devin-as-Host run is recorded with its true provenance. All work by the Host
`zcode-KPR-orchestrator-main` in commit `2236329e` on `workflow/issue-337`
(base = main `ac12635d` via the content-cycle cherry-pick `7c568f5d`).

- **`platforms/devin.yaml` `acp_verified_versions` → `cli=3000.11.92;protocol=1;agent=0.0.0-dev`.**
  The `protocol` and `agent` values were re-read from a live `devin acp`
  `initialize` on the installed 3000.11.92 (MacBook, scratch directory
  `/tmp/kpr-acp-init-scratch`, pid 23930, exit 0, terminated and reaped): the
  response reports `protocolVersion: 1` and `agentInfo: {name: "affogato",
  title: "Devin Agent", version: "0.0.0-dev"}` — the old `agent=0.0.0-dev`
  was verified, not carried over. Generated skills re-rendered
  (`render-skills.py --check` PASS).
- **`docs/host-compact-capabilities.md`**: a `Production 2026-10-16 (REPORTED,
  not measured by KPR)` paragraph records Muse's production observation
  (Host `devin-orchestrator-main` on the Studio, runner
  v0.9.14 pin `899f3c3c`, 3000.11.92, `--tier default` swe-2-max, started
  16:10; by 17:18 fourteen turns all ended normally, nine compactions all
  reported recovered, ~6 tasks merged; by 20:27 4+ hours with more merges;
  Delegator webhook wakes handled). The Studio Host event log was not read by
  KPR, so every production figure is marked reported. The 2026-10-06
  r1/r2/r3 edge rows are kept unchanged as history, and no README capability
  cell is flipped on a reported figure.
- **README § Host runtime capabilities and limits** (the sync pair with this
  doc): the Devin row gains a reported-production pointer in its gap cell;
  the measured version and verdict cells are unchanged.
- **Known receipt gap noted** (#197, doc note only as the issue asked): a
  Devin seat's Runner `status` still says `model_verified: unknown` although
  Devin's own `sessions.db` records the model. Reproduced on 3000.11.92 by
  reading the live seat `devin-KPR-i340-argv-model` (status 2026-10-16:
  `model_verified: unknown`, `effective_model` from
  `effective_model_source: launch-argv`, live model-option currentValue
  echoed the fusion id on that opus-fusion seat). Changing that readout is
  KPR #340, not this note.

## Candidate

Branch `workflow/issue-337`, commits `7c568f5d` (content-cycle opening) and
`2236329e` over main `ac12635d`.
Validation record: `kaola-workflow/issue-337/.cache/final-validation.md`
(verdict pass, hash bound to the candidate worktree).

## Evidence

- Live `devin acp` initialize receipt (protocol/agent) and the live-seat
  status readback described above; both from this Mac on 2026-10-16.
- Muse's production report as relayed by the Delegator in issue #337's body
  (reported figures, source named; Studio event log not read here).
- `render-skills.py --check` PASS; `./scripts/validate.sh --suite
  test-devin-regressions.py --suite test-generated-skills.py --suite
  test-progressive-disclosure.py --suite test-issue-264-validate-lane-integrity.py
  --suite test-issue-119-host-entry.py` — all selected suites PASS (exit 0;
  `tests/contract/test-devin-regressions.py` 28 tests OK, generated-skills,
  progressive-disclosure 15 tests OK, lane integrity 4 tests OK).

## Known failures and unverified scope

- The production figures are reported (Muse via the Delegator), not measured
  by KPR; KPR could not reach the Studio. No capability cell was flipped.
- No tag/release/install; CHANGELOG untouched (release notes are prepared at
  release time per `docs/conventions.md`).

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- README.md
- docs/host-compact-capabilities.md
- hosts/grok-bot/INSTALL.md
- hosts/grok-bot/bridge.json
- hosts/grok-bot/kaola-delegator.md
- platforms/devin.yaml
- skills/devin-kaola-project-runner/scripts/platform.yaml
- templates/grok-bot/accepted-revision.json

## Follow-Up Items

- KPR #340 (open) owns the `model_verified` readout change for Devin argv
  tiers; this run only documents the gap.
- Running seats pick up the new `platforms/devin.yaml` only after restart;
  the next release's notes carry the `Seats: restart required` line per the
  operator test (`git diff OLD NEW -- ... platforms ...`).

Final readiness: ready — issue #337 closes on the merge sink.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-337/.cache/final-validation.md
- kaola-workflow/archive/issue-337/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-337/finalization-summary.md
- kaola-workflow/archive/issue-337/mission-ledger.jsonl
- kaola-workflow/archive/issue-337/workflow-state.md
