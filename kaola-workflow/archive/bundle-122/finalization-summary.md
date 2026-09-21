# Finalization summary — bundle-122 (Issue #122)

## Delivered
Owner ruling on #122 (Yanlei, issuecomment-5762341657; Fable review issuecomment-5762407235) implemented:
an entry-less platform (`host_skill_entry` empty — codex today) fails closed in every Host role with the
typed refusal `reason: host-entry-unsupported` before any record, socket, or holder exists
(`mutation_performed: false`, exit 1): a Host-named start on it, a worker start it dispatches
(row 4 `dispatcher-no-carrier`, previously unbound), and a start whose `KAOLA_ACP_HEARTBEAT_HOST` names it
(previously a usage error). No plain-text fallback. Holder `worker_event` refusal kept as depth. Codex as
an ordinary worker is unchanged. Candidate: beb8a04 on workflow/bundle-122 (parent 5f4f40c = main; no rebase needed).

Issue statement walk:
- Scope 2 (HUMAN_DECISION_REQUIRED a/b) — decided (a) by owner; satisfied by beb8a04 + T1..T5.
- Scope 1 (live Codex `$kaola-project-runner` measurement) — NOT executed in this run: the dispatch
  authorized implementation of the ruling only, and the Codex account usage limit runs until
  2026-09-23. The owner's decision comment states Scope 1 "仍按原文执行"; see Follow-Up Items.

## Files Changed
scripts/kaola-acp.py (host_entry_unsupported() :162; resolve_heartbeat_host explicit + row 4; command_start
Host-named gate), generated skills/*/scripts/kaola-acp.py (10), templates/orchestrator/references/
host-entry-matrix.md + host-startup.md.tmpl (+ rendered copies), docs/api.md, docs/zcode-host.md,
CHANGELOG.md, tests/contract/test-issue-119-host-entry.py, tests/contract/test-zcode-heartbeat-contract.py.

## Test Coverage
New `test_issue_122_entryless_host_fails_closed` (25 checks): T1 codex dispatcher → host-entry-unsupported,
no record; codex Host-named start refused; codex worker start still ready. T2 the nine entry platforms reach
#104 `heartbeat-host-unresolved`, not this refusal. T3 explicit target codex → refused. T4 filling the entry in
an installed codex tree's manifest + table admits the Host and its worker binds (`source: dispatcher`),
stop residual_pids []. T5 table == manifests test passes; matrix codex row names the refusal.
Updated: #104 P5 row and the entry-less target check now assert the refusal; #119 H1 skips entry-less platforms.

## Validation
- `./scripts/render-skills.py --check` — PASS (budgets OK).
- `./scripts/validate.sh` — rc=0, 535 s, 0 FAIL lines; log archived as validate.log.
- run-chains: `chains_config_missing` (consumer repo, expected); record via validation-runner:
  validated_candidate_hash ff0636e4ff14a1ca88b74bc18b8a692da5e870c1d439a34d23840c00dafce6ea.
- Acceptance legs: automated (above); outer Host review PASS (T1..T5, pre-spawn refusals, doc sync).
  Live tmux smoke: not run — no live Codex session needed per dispatch (fake agent through the real CLI);
  Codex account is usage-limited until 2026-09-23.

## Changed Paths
From finalize --check changed_paths (source-scoped; docs/api.md, docs/zcode-host.md, CHANGELOG.md also changed in beb8a04):
- scripts/kaola-acp.py
- skills/{claude-code,codex,cursor-cli,devin,droid,dsh,grok,kimi-cli,opencode,zcode}-kaola-project-runner/scripts/kaola-acp.py
- skills/kaola-project-runner/references/host-entry-matrix.md
- skills/kaola-project-runner/references/host-startup.md
- templates/orchestrator/references/host-entry-matrix.md
- templates/orchestrator/references/host-startup.md.tmpl
- tests/contract/test-issue-119-host-entry.py
- tests/contract/test-zcode-heartbeat-contract.py

## Documentation Docking
DOCKED — .cache/doc-docking.md.

## Follow-Up Items
- filed: #126 (P2, enhancement) — Scope 1 of #122 (live Codex `$kaola-project-runner` entry measurement),
  carried unchanged; confirmed exists, body 1785 chars. Scope correction posted on #122
  (issuecomment-5763257592) before closure; #122 closes per Host authorization.
- Known boundary (Host ruling, not a defect): a PTY Host-named codex start is not refused — the Host/carrier
  semantics live on the ACP path; adding a PTY gate would be a new restriction and needs a human ruling.
- Deviation noted per Host ruling: the run folder is named `bundle-122` although it claims a single issue
  (claim script default naming); not renamed, to keep the records intact.

## Readiness
Candidate accepted; validation and docking PASS; Scope 1 carried to #126. READY to close #122 and sink.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/bundle-122/.cache/doc-docking.md
- kaola-workflow/archive/bundle-122/.cache/final-validation.md
- kaola-workflow/archive/bundle-122/.cache/mirror-digest.json
- kaola-workflow/archive/bundle-122/.cache/origin/selection-record.json
- kaola-workflow/archive/bundle-122/finalization-summary.md
- kaola-workflow/archive/bundle-122/mission-list.md
- kaola-workflow/archive/bundle-122/workflow-state.md
