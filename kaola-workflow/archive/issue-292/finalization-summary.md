# Finalization summary — issue-292

## Delivered

Fix for #292: the state tool resolves ACP holder records across the fixed
per-user root (`/tmp/kaola-<uid>`) and legacy TMPDIR roots through the shared
#278 path helper (`kaola-acp-paths.py`), replacing the caller-TMPDIR-only
resolution that refused node Sideagent checkpoints as `binding-superseded`.

- `scripts/kaola-dispatch.py`: `caller_role`, `caller_record`,
  `carrier_replaced_by_older` route through `acp_paths.find_directory`
  (`RecordRootMismatch` added to the handled exceptions; it is a
  `RuntimeError`, not `OSError`/`ValueError`).
- `scripts/kaola-record-contract.py`: `node_is_running` uses the shared
  resolver; the helper loads at module top level (bytecode-write guarded) so
  the holder-pinned contract is self-contained.
- Packaging: `render-skills.py` ships `kaola-acp-paths.py` beside
  `kaola-record-contract.py` in the orchestrator package (v0.9.2 shipped it
  only in the platform packages, which already carry it since #278);
  `skills/` regenerated.
- Tests: new `tests/contract/test-issue-292-state-record-root.py` (fixed root,
  legacy TMPDIR root, no-record refusal, explicit `KAOLA_ACP_RECORD_ROOT`
  scoped view); suite registered in `validate.sh` (both suite groups); four
  packaging fixtures aligned (`test-ddd-pack.py`, `test-issue-244-dispatch.py`,
  `test-issue-274-package-closure.py`, `test-progressive-disclosure.py`).
- `CHANGELOG.md` Unreleased entry with restart semantics.

## Candidate

- Final implementation commit `b1e47cd4` on `workflow/issue-292` (base
  `57ab88df`, on main). Amended from the owner-requested WIP safe point
  `fcf0c00e`; tree byte-identical, message reworded. Implementation by the
  sidekick seat (Devin) in the pre-migration checkout; review and finalization
  by the dev-clone Host.

## Evidence

- Host diff review of the full change (this run): all four lookups share the
  multi-root resolver; no `runner_record_root`/`_record_root` references
  remain in `scripts/`; platform packages already ship the helper (verified in
  `57ab88df` tree).
- `./scripts/render-skills.py --check` — PASS.
- `./scripts/validate.sh` full inventory — EXIT=0, 18 PASS groups, 0 FAIL,
  wall 1043.7 s; log `/tmp/kpr-i292-validate-full.log`.
- Live smoke: `state init/update/view/retire` executed through the candidate
  `scripts/kaola-dispatch.py` against this run's live holder record in the
  fixed root (`c5ee3ca51766c60a4f31f456e045c4a0`), including a carrier
  `maintenance-returned` reconciliation and retire — receipts in this run's
  conversation and state file.
- `.cache/final-validation.md`: verdict `pass`, candidate hash
  `e91afa0428ec2ad0b36c029fdc9442f547a527d0e5bf58d49583bf355e81b43e`.

## Known failures / unverified scope

- Per-platform live ACP smoke (start/observe/send/capture/stop on each of the
  ten platforms) was not re-run for this change; it is carried as a pending
  release-boundary duty for the upcoming release cut, per repo validation
  policy (the change is exercised live on the zcode host path by this run).
- Observation (not filed; owner directive 2026-10-07 prohibits new KPR
  issues): an unbound Host on this holder generation registers a
  `maintenance-returned` input at each state-writing turn end
  (`binding-or-recipe-unavailable`), while the record-contract host view
  treats unbound ordinary Host changes as not a compulsory node duty. The
  alert re-grows for unbound Hosts; reported to the owner in the run report.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- scripts/kaola-dispatch.py
- scripts/kaola-record-contract.py
- scripts/render-skills.py
- scripts/validate.sh
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
- skills/kaola-project-runner/scripts/kaola-acp-paths.py
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kaola-project-runner/scripts/kaola-record-contract.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-record-contract.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-record-contract.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-record-contract.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- tests/contract/test-ddd-pack.py
- tests/contract/test-issue-244-dispatch.py
- tests/contract/test-issue-274-package-closure.py
- tests/contract/test-issue-292-state-record-root.py
- tests/contract/test-progressive-disclosure.py

## Follow-Up Items

- None filed. New KPR issues are prohibited by the owner's 2026-10-07
  directive; the unbound-Host maintenance-registration observation above is
  reported to the owner instead. Related open issues #293 (holder node-record
  lookup across roots) and #294/#295 (expert_task_grants in ceiling/seats)
  already exist and are queued by the owner's priority for this run.

## Final readiness

Ready: candidate reviewed, full inventory green, live smoke green, validation
recorded. Proceed to sink (merge) and archive.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-292/finalization-summary.md
