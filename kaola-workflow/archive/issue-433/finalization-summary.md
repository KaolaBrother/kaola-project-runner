# Issue 433 finalization

## Delivered

Host accepted candidate `7ef26824219ea3e786edf82e28ba1a31bbfd6df7`. OpenCode 2.2.5 and its bundled native ACP protocol 1 are recorded in the manifest; quirks, generated Skills and Unreleased changelog reflect verified behavior and the seats restart requirement. Owner authorized merging and the content-stage bridge. Merge and bridge `8ee8e7e2ecf48142c0e4df2934e0cfc8f2950b4c` were published to origin/main and verified with `git ls-remote` before issue closure. #433 closed at 2026-10-31T04:21:05Z; evidence comment https://github.com/KaolaBrother/kaola-project-runner/issues/433#issuecomment-6538933330.

Live proof and limitations: `docs/verification/issue-433-opencode-acp.md` and `docs/verification/issue-433-receipts.json` at the merge. Both 2.2.5 and 2.0.32 exercised six-key stripping, managed policy, explicit ask/permit, cancellation, resume and controlled delayed model advertisement with actual model use; native steer adoption was observed. The controlled six-second delay does not establish arbitrary delay tolerance. Mini was not tested.

Host reported direct candidate suite passes: #24 26, #254 5, #263 30, #292 5, #309 10, #412 31, #421 45, #425 26, #426 53, #427 21. Host reported #255's two HolderNodeMode timeouts reproduced with the same direct invocation on published main P, and accepted these as non-regression entry artifacts; these two tests are not recorded as passing. Candidate standard validation was blocked before suites by the published pin gate. Post-merge main `./scripts/render-skills.py --write` and `--check` both passed after the owner-authorized content bridge. No tag, release, global installation, AGY pin or consumer change.

## Validation

classification: final_validation_unverified
green: false
mode: final-validation

The finalize transaction found no machine-recorded candidate validation receipt. Host acceptance and the reported direct suite results are described above; the transaction did not independently mark validation green.

## Changed Paths

The transaction measured none because candidate was already merged to main before archive. The delivered paths are the manifest, CHANGELOG, verification evidence, and generated OpenCode Skill files in merge `8ee8e7e2`.

## Follow-Up Items

None filed. Publication pin and release remain Host-owned future lifecycle work, not part of this run.

## Final readiness

Accepted and published; issue closed. The merge sink owns archive publication and final cleanup.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-433/finalization-summary.md
- kaola-workflow/archive/issue-433/mission-ledger.jsonl
- kaola-workflow/archive/issue-433/workflow-state.md
