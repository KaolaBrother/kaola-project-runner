# Finalization Summary — Issue #385

## Delivered

Implemented and repaired KPR #385 on `workflow/issue-385`: the `view`
projection now dedupes user echoes per logical message instead of per chunk.

- A `user_message_chunk` is an echo only when its accumulated logical message
  whitespace-normalizes to the current prompt; `messageId` is no longer an
  exemption.
- Prompt rows carry a non-serializable internal `_prompt_row` marker, so a
  chunk can never concatenate into the delivered prompt text.
- Unknown non-echo chunks become their own rows; existing `messageId` and
  `clientMessageId` identities are unchanged.
- A proper prefix is held as an echo probe. Once the probe matches the prompt,
  it keeps absorbing whitespace-only tail chunks so the whole message is
  dropped at the boundary; divergence or extension publishes the entire
  accumulated text as one row, and later chunks append to it without another
  prompt comparison. This is the review F1 repair.
- The prompt identity and chunk classification share the projection lock; the
  holder captures the update's turn fingerprint under its lock, so a
  concurrent prompt admission cannot re-identify an in-flight classification.
- `_prompt_texts` history and the exact-or-substring predicates are gone,
  removing both false-drop directions; the event log still records every echo.
- `tests/contract/test-issue-385-view-echo-dedupe.py` now has 30 cases,
  including review F1/F2 counterexample families and split-equivalence over
  every cut point, plus four reconstructed pre-fix counter-proofs. It is in
  `scripts/validate.sh` (155-suite inventory).
- `docs/api.md`, `docs/acp-watch/list-view.md`, `CHANGELOG.md`, and the 11
  generated holder copies are updated.

Candidate: `0fb2c510cf2baba235e991e9aeb7d69af7727daf` on
`workflow/issue-385`; prior candidate `c817261d`; base
`84594886f3ef93622d5c531ef302bb65197c31c9`. No tag, release, publish,
install, or KPM-side operation was performed.

## Acceptance Evidence

- Host acceptance of `0fb2c510`: F1/F2 independently confirmed; clean-env
  review probes 227/227 pass; render and six affected suites exit 0; pre-fix
  mutation copy fails 32 checks.
- Review probes: `/tmp/kpr385fix/probes-postcommit.log` (`227 checks, 227
  passed, 0 failed`); reviewer minimal reproduction passes F1 and F2.
- Mutation self-proof: `git archive c817261d` plus the current 30-case suite
  produced 32 failures (F1/F2 families); `/tmp/kpr385fix/mutation.log`.
- Clean-env validation at candidate `0fb2c510`, exit 0, 87.5 s:
  `test-issue-385-view-echo-dedupe.py` 30/30,
  `test-issue-381-view-snapshot.py` 18/18,
  `test-acp-watch-contract.py` 20/20,
  `test-acp-follow-contract.py` 12/12,
  `test-issue-380-client-message-id.py` 20/20,
  `test-issue-384-view-disclosure.py` 9/9; render check PASS.
  Log: `/tmp/kpr385fix/validate-postcommit.log`.
- Validation record: `kaola-workflow/issue-385/.cache/final-validation.md`
  (candidate hash `9638682b12e3b12428f45d405c4c5eb2f3042ae2e317ba9bcefdf8ac6cb9dcc5`).

## Known Failures and Unverified Scope

- No full-inventory `validate.sh` run; the selected six suites cover the
  changed holder, view, follow, snapshot, disclosure and client-id paths.
- No live external platform UAT; the contract suites use mock ACP agents.
- `scripts/kaola-acp-holder.py` is in the operator restart set, so a running
  holder keeps the old echo behavior until it restarts.
- Echo classification is projection-only; the raw event log remains the audit
  surface and is intentionally not filtered.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/acp-watch/list-view.md
- docs/api.md
- scripts/kaola-acp-holder.py
- scripts/validate.sh
- skills/antigravity-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- tests/contract/test-issue-381-view-snapshot.py
- tests/contract/test-issue-385-view-echo-dedupe.py

## Follow-Up Items

- No new follow-up issue was filed by this run.
- Holder restart remains an operational note.
- No release, tag, publish, install, or KPM-side operation is part of this
  finalization.

Final readiness: ready. Merge sink to `main`, close #385 with the
Host-supplied closing comment after publication is verified, archive under
`kaola-workflow/archive/issue-385/`, and remove the run worktree.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-385/.cache/final-validation.md
- kaola-workflow/archive/issue-385/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-385/finalization-summary.md
- kaola-workflow/archive/issue-385/mission-ledger.jsonl
- kaola-workflow/archive/issue-385/workflow-state.md
