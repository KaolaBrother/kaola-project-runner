# Finalization Summary — issue #225

## Delivered

Published v0.6.9. Content commit R carries the CHANGELOG section
`## 0.6.9 — 2026-09-29 (quota mappings, heartbeat authorization rows, permission wording)`
with `Seats: restart required`. Pin commit P names R at release `v0.6.9` and
renders the Grok Bot bridge `saveable: true`. Annotated tag `v0.6.9` points at
R and is on origin. The GitHub release is non-draft and non-prerelease.

No installation. The ten worker platforms keep their v0.6.8 `acp_command`,
`acp_wrapper_pin`, and `acp_verified_versions`; that retention is recorded in
the CHANGELOG. The operator diff from v0.6.8 to R changes
`scripts/kaola-quota.py`, `platforms/cursor-cli.yaml`, `platforms/droid.yaml`,
`platforms/dsh.yaml`, `platforms/opencode.yaml`, `platforms/zcode.yaml`,
`scripts/adapters/dsh.sh`, and `scripts/adapters/opencode.sh`.
`scripts/kaola-acp-holder.py` and `scripts/kaola-zcode-acp.py` are unchanged.
Restart is required because the holder pins the quota catalog at startup.

## Candidate

`workflow/issue-225` at pin P `07b4858e00fd3d8d6910c404b1bb8ed76b17f850`.
Content R is `0a00d068318b5be02bc3432687b389a2876a917f`. Annotated tag
`v0.6.9` is object `39662ce5c240f260fe12dccdf654b5f7a5fc9dbc` and peels to R.
Host acceptance received for this delivery.

## Evidence

- `kaola-workflow/.ledger/issue-225.jsonl`: three missions done.
- `kaola-workflow/issue-225/.cache/final-validation.md`: `verdict: pass`,
  command `./scripts/render-skills.py --check --require-pinned`,
  `validated_candidate_hash: 655f97e2ec23b55547f7b3d0f94ec62961ec6ba7684528ca8e8ee7eb51ddce54`.
  Reconfirmed on P immediately before the record: `render-skills: PASS`
  (bridge 2478 B, pinned at `0a00d068318b`, pin verified, budgets OK).
- `kaola-workflow-run-chains.js --project issue-225`: `chains_config_missing`
  (no `package.json` `test:kaola-workflow:*` scripts). Consumer gate is the
  recorded final-validation file.
- Earlier on this same P, before Host acceptance: `kaola-grok-bot-verify.py
  --repo --require-pinned` PASS; `tests/contract/test-issue-49-grok-bot-host.py`
  45 tests OK. #222/#223/#224 evidence covers surfaces this release did not
  change.
- GitHub release: https://github.com/KaolaBrother/kaola-project-runner/releases/tag/v0.6.9

## Known failures / unverified scope

- `./scripts/validate.sh` was not rerun. This release's own edits are the
  CHANGELOG and the four pin files; #222/#223/#224 evidence covers the rest.
- No install (`install-local.sh` not authorized). The published tag and
  release are left as published.

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
- templates/grok-bot/accepted-revision.json

## Follow-Up Items

None filed. No run-discovered defect. The issue body's parenthetical that the
holder changed is corrected on the issue: the measured operator diff leaves
`scripts/kaola-acp-holder.py` and `scripts/kaola-zcode-acp.py` unchanged, and
`Seats: restart required` still holds because the quota catalog changed.

## Final readiness

Ready: accepted by Host; merge sink, close #225, archive.

## Finalize Findings

### residue_unattributed

The residue mirror did not copy the paths below out of the main checkout: this run's HEAD does not contain them. Presence in main, an untracked status, or a neighboring file this run committed is not evidence they belong to this run. Nothing was copied, staged, committed, deleted, reverted or relocated — they remain in the main checkout. Read them before the sink runs: commit what belongs to the run, leave what does not.

Paths left in the main checkout:

- docs/harness-acp-compat-2026-09-25.md
- docs/harness-acp-compat-2026-09-26.md
- docs/harness-acp-compat-2026-09-29.md

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-225/.cache/final-validation.md
- kaola-workflow/archive/issue-225/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-225/finalization-summary.md
- kaola-workflow/archive/issue-225/mission-ledger.jsonl
- kaola-workflow/archive/issue-225/workflow-state.md
