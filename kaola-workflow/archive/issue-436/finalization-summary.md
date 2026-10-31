# Finalization Summary — issue 436

## Delivered

Phase A candidate ec5b2f5b forces CLAUDE_CODE_ENTRYPOINT=custom for each Claude ACP child and preserves removal of ANTHROPIC_API_KEY and ANTHROPIC_AUTH_TOKEN. Content-stage bridge commit 1cdb1947 was merged with the candidate into main as f769b3e2403f9752a1d51f7128ea381258f2c85f, published to origin/main. Seats require restart. No vendor replacement, wrapper pin, verified-version update, fleet CLI upgrade, or release was performed.

Host accepted implementation and independently verified the first live transcript. Owner authorized real-login probing in https://github.com/KaolaBrother/kaola-project-runner/issues/436#issuecomment-6546255594. The candidate live evidence is https://github.com/KaolaBrother/kaola-project-runner/issues/436#issuecomment-6546270689. After merge and push, a second direct ACP probe in main returned KPR436_OWNER_LIVE_OK, end_turn and bridge exit 0; child PID 21357 exited, with custom observed in its environment. ACP session 8dfda13d5b7181620674139a5f64e377 and native session 94eed163-6b15-4ee3-a475-75ca5c201866 correspond to ~/.claude/projects/-Users-ylpromax5-Workspace-kaola-project-runner-dev/94eed163-6b15-4ee3-a475-75ca5c201866.jsonl; user row 0237333d-237d-48c7-be29-12165852e11c and assistant row 68fff43c-94cc-46b4-8487-a688f3670bd8 show entrypoint custom. This single Mac probe is not a fleet CLI qualification.

Prior focused evidence: fork test 11/11; issue-50 direct 11/11 (327 checks), issue-186 direct 7/7 (44 checks), dist derivation byte-identical. The earlier standard subset was blocked at pinned-stage render; the integrated main content-stage render --check passed at f769b3e2. No full inventory was claimed.

Phase B matrix: https://github.com/KaolaBrother/kaola-project-runner/issues/436#issuecomment-6546103534. Owner approved bounded hybrid without production cutover: https://github.com/KaolaBrother/kaola-project-runner/issues/436#issuecomment-6546274964. Any prototype remains non-default and replacement/cutover needs separate Owner GO.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

none outside the kaola-workflow/ run-state band.

## Follow-Up Items

Bounded hybrid investigation remains optional future work under Owner direction; no production switch is authorized. No new issue was requested.

## Readiness

Accepted by Host; mainline publication and live evidence verified. Finalize and merge sink remain to be recorded.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-436/.cache/final-validation.md
- kaola-workflow/archive/issue-436/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-436/finalization-summary.md
- kaola-workflow/archive/issue-436/mission-ledger.jsonl
- kaola-workflow/archive/issue-436/workflow-state.md
