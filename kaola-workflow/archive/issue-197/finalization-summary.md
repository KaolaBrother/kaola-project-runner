# Finalization Summary — issue-197

## Delivered

Fresh #197 run (clean restart from main d420d510; the abandoned prior run is archived at
`kaola-workflow/archive/issue-197.discarded-2026-09-27T15-31-57-990Z` with backup ref
`abandoned/issue-197-7bbd3ff4`, not used as delivery).

- Assessment: no Runner code defect. A Devin `start` receipt already separates the requested preset
  (`requested_tier`, `resolved_runtime_model_id`), the launch application
  (`config_application.model.applied_via: "argv"`), the ACP-advertised value
  (`effective_selection.advertised_model`), and the actual model (`actual_runtime_model_id: null`,
  `model_verified: "unknown"`), without promoting the ACP echo to a verdict.
- Corrected the demonstrated documentation defect in `platforms/devin.yaml` `acp_quirks`: ACP
  `currentValue` does not echo, and need not list, the argv model; the note no longer claims it always
  stays `swe-2-high` or that the `-medium` opus-fusion id was unmeasured.
- Regression: the Devin argv test now covers `default` and `opus-fusion` and asserts that the actual
  model stays null/unknown.
- CHANGELOG Unreleased entry; Grok Bot accepted revision returned to the content stage.

Issue walk (#197 body):
- Independent assessment from clean current main — mission 1 (commit 34ef7e33 on base d420d510).
- Distinguish requested / applied / advertised / native-verified-or-unknown — the live receipts
  (mission 3) plus the regression assertions.
- Honest unknown — `actual_runtime_model_id` stays null; the original historical consumer seat
  remains unknown (no argv or native evidence for it on this machine).
- Minimal correction only; no catalog gate, silent switch, fabricated verdict, or new receipt fields —
  the diff touches only the manifest note, rendered copies, the test, the CHANGELOG, and the Grok
  content stage.
- Bounded check on the fresh candidate — focused tests, render/validate, and one disposable live
  Devin session.

## Files Changed

CHANGELOG.md; platforms/devin.yaml; skills/devin-kaola-project-runner/references/acp.md;
skills/devin-kaola-project-runner/scripts/platform.yaml; tests/contract/test-acp-contract.py;
templates/grok-bot/accepted-revision.json; hosts/grok-bot/{INSTALL.md,bridge.json,kaola-delegator.md}.
Integration: merge of archive-only main 071ab951 (#200 discard archive) at 4b3f9c68.

## Test Coverage

- Automated: `tests/contract/test-acp-contract.py`
  `Issue34ModelSelectionAcpTests.test_argv_carried_model_skips_the_redundant_option_apply`
  (default + opus-fusion subtests) and `test_model_not_in_argv_still_goes_through_the_option`: OK.
  Adding devin to `ECHO_VERIFIED_PLATFORMS` makes the regression fail.
- Required: `./scripts/render-skills.py --check` PASS (34ef7e33 and 4b3f9c68); `./scripts/validate.sh`
  exit 0 on 34ef7e33 (no FAILED; only the named Bash>=4 watchdog rows skipped on bash 3.2.57). No
  product byte changed at 4b3f9c68.
- Live UAT: one disposable Devin CLI 3000.11.3 ACP session (charm-catfish) ran
  start/observe/send/capture/stop:
  - requested opus-fusion → `fusion-claude-opus-5-5-medium-sidekick-swe-2-medium`, launched through argv;
  - ACP advertised `fusion-claude-opus-5-5-high-sidekick-swe-2-medium` (the medium id was not among the
    95 options);
  - the Runner reported the actual model as unknown;
  - the native sessions.db row records medium;
  - exact stop: `residual_pids=[]`.
- Host QA: accepted 34ef7e33 and reaccepted 4b3f9c68.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- hosts/grok-bot/INSTALL.md
- hosts/grok-bot/bridge.json
- hosts/grok-bot/kaola-delegator.md
- platforms/devin.yaml
- skills/devin-kaola-project-runner/references/acp.md
- skills/devin-kaola-project-runner/scripts/platform.yaml
- templates/grok-bot/accepted-revision.json
- tests/contract/test-acp-contract.py

## Documentation Docking

DOCKED — see `.cache/doc-docking.md` (devin.yaml note and CHANGELOG fixed; docs/api.md, README,
architecture, and conventions need no change).

## Follow-Up Items

- Not filed (observation for Host): while the Grok Bot `accepted-revision.json` stage is `pinned`,
  `./scripts/render-skills.py --check` on main failed after the archive-only release commits
  d420d510 and 071ab951, because the pin rule counts `kaola-workflow/archive/**` as content.
  - Measured on main 071ab951 with `./scripts/render-skills.py --check` (pin lines naming the archive
    files).
  - Merging this run returns main to the content stage.
  - Hypothesis: this is the intended "first post-pin commit must un-pin" rule, not a defect. Whether
    archive-only commits should be exempt is a Host/owner design call.
- Environment facts, not product defects:
  - A Devin start dispatched from a worker seat whose environment inherits the Host's
    `KAOLA_ACP_HEARTBEAT_HOST` refuses `heartbeat-host-conflict`, as documented.
  - Stale installed main Skills refuse `main-skill-build-skew`. The Host refreshed
    `~/.config/devin/skills` and `~/.cursor/skills`.

## Readiness

READY — all missions done (3/3), Host acceptance recorded, validation bound, docs docked.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-197/.cache/doc-docking.md
- kaola-workflow/archive/issue-197/.cache/final-validation.md
- kaola-workflow/archive/issue-197/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-197/finalization-summary.md
- kaola-workflow/archive/issue-197/mission-ledger.jsonl
- kaola-workflow/archive/issue-197/workflow-state.md
