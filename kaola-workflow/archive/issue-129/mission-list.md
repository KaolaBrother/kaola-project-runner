# #129 harness-compat 2026-09-22 class 2: record ZCode 0.16.9/0.46.6 and batched CLI versions; OpenCode pin per owner ruling

- item: ZCode acp_verified_versions + summaries aligned to cli=0.16.9 / reference zcode-acp 0.46.6 (turnId+permissions), record-only, with "verify the actual CLI version before the next live run" note; no local upgrade
  status: done
  dispatched: self, worktree .kw/worktrees/issue-129 (branch workflow/issue-129)
  result: 3fd4672 — zcode.yaml verified cli 0.16.5→0.16.9; acp_quirks names v0.46.6 (bc240d3) as newer reference, pin 80aa4e2 kept; static read shows installed ZCode.app 3.14.1 bundles CLI 0.16.9 (no live run)
- item: optional batch records — Claude cli=2.1.278, Droid cli=0.223.0 (record fields + pinned test assertions); Codex 0.155.1/codex-acp 1.12.0 only if it can be recorded without moving the executed npx pin
  status: done
  dispatched: self, same worktree
  result: 3fd4672 — claude-code cli 2.1.272→2.1.278, droid cli 0.220.0→0.223.0; no test pinned the record fields (fixtures model measured surfaces, kept). Codex NOT changed: acp_verified_versions describes the executed npx pin (acp_command/acp_wrapper_pin @openai/codex@0.153.4 + codex-acp@1.11.0); moving it is a runtime change → HUMAN_DECISION_REQUIRED
- item: OpenCode pin 1.18.29→1.18.31 — premise stale (repo records V2 cli=2.0.11 since #112; local brew opencode-v2 2.0.11; 1.18.31 is the V1 npm latest); HUMAN_DECISION_REQUIRED before any change
  status: done
  dispatched: Host ruling 2026-09-22
  result: N/A by Host ruling A (V2 2.0.11 accepted; V1 pin premise stale; Pink to update); no change. Codex deferred to #126 live entry measurement. Comment https://github.com/KaolaBrother/kaola-project-runner/issues/129#issuecomment-5766638830
- item: gates — render --write/--check, validate.sh rc=0, CHANGELOG entry, doc-impact; candidate commit on workflow/issue-129 (no merge/push)
  status: done
  dispatched: self
  result: render --write/--check PASS (budgets OK); validate.sh rc=0 on 3fd4672 tree (kaola-workflow/issue-129/validate-candidate.log); CHANGELOG Unreleased entry; doc-impact: README 2.1.272/0.16.5 lines are dated measurements, NO IMPACT
