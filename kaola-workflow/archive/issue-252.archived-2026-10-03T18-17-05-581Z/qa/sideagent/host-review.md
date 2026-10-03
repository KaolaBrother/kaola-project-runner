# Issue 252 Sideagent follow-up for Host review

Candidate: `6bc6a2845435424452d36ea9f57184b9ea678307`
Parent: `df69f546f0a99c847a9bbd8fc38ac54d0714670e` (unchanged accepted source candidate)
Subject: `fix: rename orchestration role to Sideagent (#252)`
Branch: `workflow/issue-252`; exactly one follow-up commit; worktree clean.

Current scope: the corrected issue title/body including Latest owner correction.
Source prompts, generated Skills, README/docs and public session role metadata
now use Sideagent. Responsibilities, authorization and execute mutation scope
are unchanged. Legacy sidekick flags/records/plans remain readable and preserve
identity; same-native recovery retains a stored legacy role without renaming,
relabeling or replaying an active session. Native Devin Fusion identifiers and
model component roles remain distinct provider facts. The necessary public
compatibility note is in docs/api.md (Session role).

Final `./scripts/render-skills.py --write`: exit 0.
Final `./scripts/render-skills.py --check`: exit 0.
Final `./scripts/validate.sh` with FORCE_COLOR and CLICOLOR_FORCE removed from
its child environment: exit 0. All 64 touched file hashes stayed unchanged.
The final run includes 46 passing #244 dispatch/guidance checks and 13 passing
#245 role/consumer checks, including mocked canonical/legacy wire projections,
recovery identity and capacity invariants. Existing native Fusion checks passed.

Named skips due to bash 3.2.57 lacking mapfile/BASHPID:

- validate-watchdog monitor disabled; affected suites ran unwatched.
- test_a_finished_suite_passes_its_status_through (watchdog monitor/kill path).
- test_a_hung_suite_is_killed_diagnosed_and_reported (watchdog monitor/kill path).

The two watchdog test cases were actually skipped; no entire contract suite or
missing-log skip occurred. Full named receipts are in skips.txt and
skip-summary.json. Passing tests whose description contains SKIPPED are not
counted as a skip.
The initial 8193-byte reference finding, intentionally interrupted validation
wrapper (130), and initial focused fixture resume-capability failure (1) are
preserved. Their narrow repairs and final outcomes are described in
consumer-consistency.md; the final full validation passed on unchanged bytes.

bytes.md/json lists each of 64 touched surfaces relative to the parent,
net +10003 bytes. Budgets, including 17408 and 8192,
remain unchanged. The reference's final size is 8191 bytes.

Historical source/QA evidence remains unchanged under
kaola-workflow/archive/issue-252. Finalization was interrupted after the local
archive and advisory claim cleanup, before any new commit, merge, push or issue
closure. Same local claim identity, session marker, branch and worktree were
preserved; installed resume returned true, reason finalize_incomplete. New
correction evidence belongs to this same claim; no second claim was opened.
The four named untracked harness documents remain byte/mtime-identical. This
agent did not write either control JSON or rewrite supporting /tmp notes.

No additional live trial ran; these consumer behavior checks use mocks/fixtures.
The historical live limitations remain in archived qa/host-review.md and raw
receipts. Normal live acceptance is not asserted by this follow-up.

Doc impact is the guidance, docs and role metadata this rename touches.
Source candidate readiness: PASS for implemented and executed checks.
Project acceptance: pending Host review. Stop here; do not finalize or sink.
