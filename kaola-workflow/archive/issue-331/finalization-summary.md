# Finalization Summary — issue-331

## Delivered

Claude-code/haiku worker `claude-code-KPR-i331-effort-evidence` fixed the false
`selection-mismatch` for antigravity dispatch in two commits on `workflow/issue-331`
(base = main `2e4b37fd`): `ddf2c159` (fix + renders + 323 assertion updates + docs +
CHANGELOG) and `4765a767` (regression suite + validate.sh registration).

1. **Preferred fix implemented verbatim** (`scripts/kaola-acp.py`):
   `effort_applied_by_model_id` — when the platform advertises no effort config option
   and the agent accepted the model, `picker_effort_suffix(applied model id) == requested
   effort` records `{applied: true, applied_via: "model-id", value}`. An unaccepted model
   or a disagreeing suffix stays `unapplied`; dispatch logic unchanged (the
   `application_slot`/`effort_applied_verdict`/`applied_mismatch` gate now passes on true
   evidence).
2. **Continuity guard** (worker-initiated, regression-preventing): an effort carried by the
   model id has no readback of its own, so it stands or falls with the model axis in
   `reconcile_selection_continuity` — without this, antigravity resume `preserved` would
   degrade from `True` to `None`.
3. Renders regenerated (`render-skills.py --check` PASS); `test-issue-323-antigravity-acp.py`
   assertions updated to the new true record; `docs/api.md` documents `applied_via:
   "model-id"`; CHANGELOG Unreleased notes `Seats: restart not required` for this entry
   (`kaola-acp.py` is not in the operator restart set; the section-level `restart required`
   from #326's holder change remains).

## Candidate

Branch `workflow/issue-331`, commits `ddf2c159` + `4765a767` over main `2e4b37fd`.
Recorder-bound hash: `08e0615d57058291…`.

## Evidence

- Dispatch fp `49b3a353…` after an explicit availability probe (haiku session-limit reset
  verified with a live "OK" before briefing); three turns (align → implement → report).
- New suite `test-issue-331-effort-model-id.py` (8 tests): (a) antigravity default and
  xhigh start through a real holder (mock agy) and pass the dispatch gate with no mismatch;
  (b) a real model mismatch still fails `selection-mismatch`; (c) cursor-cli keeps its own
  effort option with no `applied_via`; plus unit coverage of the predicate and continuity.
- Worker runs: new suite 8/8; focused suites 323 (54/54), 268 (26/26), 244 (80/80),
  acp-contract (87/87), 162 (58/58), 130 (27/27); mutation check on the base commit
  (defect cases fail pre-fix, true-mismatch and cursor cases pass).
- Host runs on the exact candidate: full inventory `./scripts/validate.sh` **rc=0**
  (1267 s, proxies and ambient `KAOLA_ACP_DISPATCHER` unset); render `--check` PASS;
  suites 331 and 323 green standalone.
- Validation record: `kaola-workflow/issue-331/.cache/final-validation.md` (verdict pass).

## Known failures and unverified scope

- The full `kaola-dispatch.py execute` chain was not run live (needs a live Host and
  authorization); the verified surface is the real start receipt that `execute`'s
  `applied_mismatch` gate reads.
- Mock agy only — no live agy 1.3.5 verification for this change (the model-id suffix
  mapping itself comes from the manifest).
- Devin's empty effort config id with default-empty effort is unchanged behavior; only an
  explicitly requested effort matching the model suffix takes the new branch (not
  separately tested).
- A pre-existing `resume-without-prior-applied` behavior in the mock flow is identical
  before and after this change (not introduced here); the continuity guard is covered by
  unit tests instead of the integration path.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/api.md
- scripts/kaola-acp.py
- scripts/validate.sh
- skills/antigravity-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- tests/contract/test-issue-323-antigravity-acp.py
- tests/contract/test-issue-331-effort-model-id.py

## Follow-Up Items

- None filed. The KPM-side mirror rule does not apply (no KPM mirror per directive).
- searched: duplicate probe `gh issue list --state all --search "selection-mismatch
  antigravity"` before filing → no hits.

## Final readiness

Ready: candidate accepted (Host review + full inventory rc=0 on the candidate + worker
mutation checks), validation recorded pass, no tag/release/install performed.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-331/.cache/final-validation.md
- kaola-workflow/archive/issue-331/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-331/finalization-summary.md
- kaola-workflow/archive/issue-331/mission-ledger.jsonl
- kaola-workflow/archive/issue-331/workflow-state.md
