# Finalization Summary — issue-332

## Delivered

Claude-code/haiku worker `claude-code-KPR-i332-expert-admission` fixed the expert-row admission
defect in two commits on `workflow/issue-332` (base = main `0c5e1e82`, v0.9.13):
`eca10c70` (opens the post-v0.9.13 content cycle — grok-bot pin paths back to the R content
stage, `a6af2d88` convention; required for any post-release content change, same as #326's
post-v0.9.12 open) and `34c93082` (the fix).

**Chosen fix: admission-side, manifest class unchanged.** New `admission_catalog()`: a preset
the manifest classes Elite that has an `expert_task_grants` row admits, counts and occupies as
that Expert task choice — never as an Elite seat. Manifest classes stay as written (classes are
owner-defined; reclassifying opus-xhigh would change Elite/Expert capacity counts and public
docs — recorded as an open owner value question, not decided here). The empty-`{}` evidence
defect is fixed on the execute refusal path: a no-grant refusal now names
`{class, elite_row, expert_row}`.

## Candidate

Branch `workflow/issue-332`, `eca10c70` + `34c93082` over main `0c5e1e82`.
Recorder-bound hash: `9795e1bc9208caaa…`.

## Evidence

- Delegator reproduction (`.ka/repro332.py`) rerun by the Host against both trees: worktree —
  `claude-code/opus-xhigh` → `dry-run` with `lifetime: standing` evidence; controls
  (`claude-code/fable`, `codex/astra`) unchanged. Unfixed control: main still returns
  `above-ceiling` with `{}` for opus-xhigh. The reproduction is the regression test, per the
  owner rule.
- `test-issue-294-expert-ceiling.py` extended (9 cases, all green); the 3 new cases fail on the
  base export (worker mutation check).
- Worker runs: the 24 suites referencing `kaola-dispatch` all green; `render-skills.py --check`
  exit 0 on the branch.
- Host runs on the exact candidate: **full inventory rc=0** (1640 s); render PASS; 294 suite OK.
- `project --seats` after the fix shows opus-xhigh as `class Expert`, `lifetime standing`,
  `expert_authorization: present` (previously withheld `above-ceiling`).
- Validation record: `kaola-workflow/issue-332/.cache/final-validation.md` (verdict pass).

## Known failures and unverified scope

- Behavioral note (worker-declared): a preset with both an Elite grant and an Expert row is now
  judged by the Expert row's lifetime/expires — an expired Expert row refuses it even with an
  open Elite window; shared-group count for such a preset is `min(expert, elite)`. No
  KaolaTerminal data was available to confirm whether such a combination exists in the wild.
- The `project` withheld list still lacks an evidence field (outside the issue's named execute
  path); not fixed here.
- No live ACP smoke (dry-run admission path only); `gh issue view` needed `gh api` fallback
  (token lacks `read:project`).

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/dispatch-collect.md
- hosts/grok-bot/INSTALL.md
- hosts/grok-bot/bridge.json
- hosts/grok-bot/kaola-delegator.md
- scripts/kaola-dispatch.py
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/grok-bot/accepted-revision.json
- tests/contract/test-issue-294-expert-ceiling.py

## Follow-Up Items

- Open owner value question (recorded, not decided): whether `claude-code/opus-xhigh`'s
  manifest class should become Expert. No issue filed (no new KPR issues without owner
  direction).
- searched: duplicate probe not applicable (Delegator-filed issue with reproduction).

## Final readiness

Ready: candidate accepted (repro verified both sides + full inventory rc=0), validation
recorded pass, no tag/release/install performed.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-332/.cache/final-validation.md
- kaola-workflow/archive/issue-332/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-332/finalization-summary.md
- kaola-workflow/archive/issue-332/mission-ledger.jsonl
- kaola-workflow/archive/issue-332/workflow-state.md
