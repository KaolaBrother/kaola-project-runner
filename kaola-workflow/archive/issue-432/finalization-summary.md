# Issue 432 finalization summary

## Delivered

Codex ACP adapter pin 2.5.0; measured CLI 0.165.0 / adapter 2.5.0 / protocol 1; standard subagent event isolation and child permission identity; generated Skills, operator restart note and Owner ACP-first rule in AGENTS.md. Detailed evidence and limits: `docs/research/issue-432-codex-acp.md`.

## Candidate and acceptance

Candidate: `b19815055332ffb9587652a83da0a36a7e4f6a74`, on `workflow/issue-432`, based on `dbbc55e24b8ef4e73704b264df04ca839828232e`. Host explicitly accepted and reported an independent 12-suite rerun, render PASS and manifest diff review. Producer ran seven focused suites (149 tests), three bounded ACP core cases, render check and scoped live tests. Exact producer validation command is recorded in `.cache/final-validation.md` and the study.

Green is confined to the tested KPR protocol-1 path with adapter 2.5.0 and CLI 0.165.0. 0.162.1 and 0.166.0 pairings were observed but lie outside the adapter's declared range and were not exhaustively verified. Bare same-identity resume read high as low; cause unproven; explicit tier restored high. ACP v2 and AIR-private typed failure notices were not advertised or tested. The longer invalidated validation run was stopped and is not counted. Temporary test artifacts and authentication copy were removed.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- AGENTS.md
- CHANGELOG.md
- docs/research/issue-432-codex-acp.md
- platforms/codex.yaml
- scripts/kaola-acp-holder.py
- skills/antigravity-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/SKILL.md
- skills/codex-kaola-project-runner/references/acp.md
- skills/codex-kaola-project-runner/references/platform.md
- skills/codex-kaola-project-runner/references/steering.md
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/platform.yaml
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/hermes-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- tests/contract/test-issue-173-codex-system-error-turn.py
- tests/contract/test-issue-22-bypass-all-approvals.py
- tests/contract/test-issue-247-codex-child.py
- tests/contract/test-runner-v2.py

## Follow-Up Items

No new issue filed: the Owner directed forge writes only to #432. Resume readback difference and unverified protocols are disclosed above; no root cause is asserted.

## Readiness

Host accepted the candidate for merge, push and #432 closure. Finalize uses the local/offline path because the claim was local and the user prohibited label changes; remote push and issue closure are independently verified after local merge.

## Finalize Findings

### claim_release_skipped_offline

This finalize released no claim: KAOLA_WORKFLOW_OFFLINE=1, so the release returned before making any forge call. Nothing local records whether this run was ever claimed online, so this does not assert the artifacts are there — but IF the claim was posted, the `workflow:in-progress` label and the `kw:claim` marker comment are still on the issues below. The marker expires after 24h; the label does not, and either one blocks a later claim of that issue until it is removed.

Issues whose claim release was skipped:

- #432

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-432/.cache/final-validation.md
- kaola-workflow/archive/issue-432/finalization-summary.md
- kaola-workflow/archive/issue-432/mission-ledger.jsonl
- kaola-workflow/archive/issue-432/workflow-state.md

## Sink and closure reconciliation

The offline Workflow merge sink advanced local `main` to `dfbd6ea6e3db626bf628906783b33e463f9add7e`, containing implementation candidate `b19815055332ffb9587652a83da0a36a7e4f6a74` and this archive. Post-merge `./scripts/render-skills.py --check` passed. A separate push published that sink commit to `origin/main`, independently verified with `git ls-remote`. The user-authorized [closure comment](https://github.com/KaolaBrother/kaola-project-runner/issues/432#issuecomment-6538465183) records measured scope and limitations. GitHub then reported #432 `CLOSED`, reason `COMPLETED`, at `2026-10-31T03:33:53Z`; no labels were present or changed. The #432 run worktree and branch were removed. The earlier `close-pending` and `kept` values in workflow-state are the offline finalization snapshot; the later reconciliation records actual closure and cleanup. The scoped Workflow closure audit reported `current_project_clean: true`.
