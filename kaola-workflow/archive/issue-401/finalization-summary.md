# Finalization Summary — Issue #401

## Delivered

Aligned `tests/contract/test-issue-94-zcode-native-skill-entry.py` with the
product surfaces it pins; no product code, docs, generated output or CHANGELOG
changed.

- `test_interrupt_resend_is_verbatim_with_no_host_marker`: the fake holder now
  supplies the #380 legacy no-id answer `(None, None)` for
  `_client_message_id_param` (these params carry no `client_message_id`) and
  `holder_instance_id`, which `op_steer_interrupt` reads unconditionally when it
  builds the follow-up prompt. The `op_prompt` assertion names that verified
  holder binding. The suite's contract is unchanged: the real method still runs
  with in-memory doubles, sends the caller text verbatim exactly once, and
  carries no host marker. The client-message-id paths stay covered by
  `test-issue-380-client-message-id.py` and are not duplicated here.
- `test_entry_is_the_first_payload_line`: removed the stale
  `src.index("kaola-host-notify/1")` offset, which #387 moved into the
  `HOST_NOTIFY_SCHEMA` constant definition, and anchors the ordering on the
  `f"{HOST_NOTIFY_SCHEMA}: ..."` carrier header in the actual payload assembly
  (`scripts/kaola-acp-holder.py:6158-6160`). The pinned contract still holds:
  the payload opens with `self.host_entry` before the carrier schema header.

Candidate: `21f30398` on `workflow/issue-401`, which is fix commit `c4b9b58f`
plus the accepted integration of `818a8a31` (the Host-landed standard
post-v0.9.25 content cycle). The content-cycle commit is release-cycle state,
not issue behavior; this run authored no generated output.

Host acceptance: independent Elite review (devin/opus-fusion, read-only)
confirmed the double is faithful on the no-id path, the `op_prompt` assertion
matches the real send, the entry-line anchor pins the payload order, and nothing
was loosened or gamed. The Host re-ran the suite in this worktree (30 OK,
clean). One optional hardening note (a single combined multi-line regex) was
recorded as not required and was not acted on.

## Evidence

- Pre-fix repro from the issue: on `10761cc2`,
  `python3 tests/contract/test-issue-94-zcode-native-skill-entry.py` gave
  `FAILED (failures=1, errors=8)` (the missing helper and the stale anchor).
- Post-fix suite on the integrated tree `21f30398`, exit 0: `Ran 30 tests ...
  OK`. Log: `/tmp/kpr-401-integrated-suite.log`.
- `./scripts/render-skills.py --check` on the integrated tree, exit 0:
  `render-skills: PASS (11 workers + kaola-project-runner + kaola-delegator +
  grok-bot host: 1 bridge skill, 2555 B, content stage, unpinned (not
  saveable); budgets OK)`. Log: `/tmp/kpr-401-integrated-render.log`.
- Host acceptance verdict: PASS (independent Elite review, read-only); Host
  suite re-run: 30 OK, clean.
- Full-gate proof context on proof tree `0b4513f6` (`c4b9b58f` + the standard
  content-cycle chore): `KAOLA_FULL_GATE=1 ./scripts/validate.sh` ran the full
  inventory of 162 suites: 161 passed, 1 failed, 0 skipped; gate exit 1. The
  single failure is the pre-existing `test-issue-349-checkpoint-verb.py`
  (`AssertionError: '## Unreleased' not found`, because the v0.9.25 release
  notes replaced that heading). It reproduces on pristine `10761cc2` and is out
  of #401 scope; the Host handles it as its own issue run. Logs:
  `/tmp/kpr-401-full-gate.log`, `/tmp/kpr-401-349-baseline.log`.
- Final-validation record bound to the integrated tree (main-resident run
  folder): `kaola-workflow/issue-401/.cache/final-validation.md`, verdict
  `pass`, validated candidate hash
  `4e837391652058cdad9684fee51785a843900654bba2ebc8c32b09106f4b2284`.

## Known failures or unverified scope

- The whole-inventory gate is 161/162, not 162/162, solely because of the
  pre-existing #349 CHANGELOG-staleness failure above. No other suite failed or
  skipped, and this run does not claim whole-inventory green.
- This is a test-only change: no product, transport or platform behavior
  changed, so no live ACP UAT applies. The suite executes the real holder
  method against in-memory doubles; no holder process or CLI was started.
- The optional review hardening note (single combined multi-line regex) is
  recorded and deliberately not implemented.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- tests/contract/test-issue-94-zcode-native-skill-entry.py

## Documentation Docking

No documentation or CHANGELOG change: the fix is test-side alignment only, and
`docs/zcode-host.md` plus the orchestrator reference already state both pinned
contracts. The suite asserts those texts as they are. No generated `skills/` or
`hosts/` output was authored by this run; the branch only carries the Host's
accepted content-cycle integration.

## Follow-Up Items

- `test-issue-349-checkpoint-verb.py` post-release CHANGELOG staleness is
  tracked by the Host as its own issue run; this run did not file it and did
  not touch it.
- No tag, release, install or KPM-side operation is part of this finalization.
  KPM #770 is left uncommented for the Host.

Final readiness: ready. Merge sink to `main`, verify publication and issue
closure, archive the run under `kaola-workflow/archive/issue-401/`, and remove
the run worktree and branch.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-401/.cache/final-validation.md
- kaola-workflow/archive/issue-401/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-401/finalization-summary.md
- kaola-workflow/archive/issue-401/mission-ledger.jsonl
- kaola-workflow/archive/issue-401/workflow-state.md
