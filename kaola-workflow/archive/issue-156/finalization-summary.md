# Finalization summary — issue-156

Propose-only review of the skill prompt surface for Issue #156 "review: Claude Code audit of Runner
skill prompts for concision and accuracy". The Host accepted it on 2026-09-24. **Disposition:
review delivered; issue kept OPEN**, because the Owner holds the accept/implement decision on the
proposals (issue body Delivery 3). No repo file changed, no sink-merge of content, no release, no CLI
upgraded, `~/.dsh` untouched, #155 untouched.

## Delivered

- Review receipt (gitignored local evidence): `.kaola/skill-prompt-review-2026-09-24.md`
  (41,471 B), with these sections: §0 headline, §1 Project Runner, §2 Kaola-Delegator, §3 ten
  platform workers, §4 accuracy sweep (~165 claims checked, mismatches only), §5 adjacent
  observations, §6 risk notes (R1–R14: what must not be shortened away), §7 landing order,
  §8 draft comment.
- Surface read: `skills/kaola-project-runner` (SKILL + 9 refs), `skills/kaola-delegator`
  (SKILL + 2 refs), ten `skills/<platform>-kaola-project-runner` (SKILL + acp/platform/steering).
  53 files, 5,462 lines, 387,918 B at main `9cbb87c` (content head `e147059`).
- Issue summary comment (Host-authorized, posted as drafted in receipt §8):
  https://github.com/KaolaBrother/kaola-project-runner/issues/156#issuecomment-5806975227
- Findings, summarized: budgets are saturated (Delegator SKILL 4095/4096, main SKILL
  17392/17408, heartbeat-skeleton 8190/8192, zcode acp 8179/8192). The ZCode-only Host/heartbeat
  wording conflicts with #119/#126. Stale fields and examples: `self_hosting_risk`, `turn-end`,
  `zcode-kaola-host`, `--stdin`, PTY-era `launch_summary`, dsh `--mode`. The worker SESSION/REPO
  examples conflict with issue-scoped naming and the canonical root. Two statements are missing:
  `permit --option` and "never shell eval". The same rules repeat in 3–6 files, and ~7.6 KB of
  measurement history sits in loaded references.

Issue statement walk:

| Issue part | Satisfied by |
|---|---|
| Delivery 1: one Claude Code review seat on Mac Studio via the live ZCode Host | This seat, dispatched by Host `zcode-KPR-orchestrator-harness` (Host-owned fact) |
| Delivery 2: receipt under `.kaola/` with findings, concrete proposals, risk notes | Receipt §1–§4 (findings plus proposals with template/manifest pointers and byte estimates), §6 (risk notes) |
| Delivery 3: do not implement without Owner greenlight | Zero repo changes (`git diff` empty; branch has no commits) |
| Delivery 4: sink-merge only if Owner later asks to land edits | Not applicable; no content to land |
| Stop boundary: receipt + issue comment, no release, leave #155 | Receipt written, comment posted, no release, #155 not read or written |

## Files Changed

None. Zero repo file changes. The run branch `workflow/issue-156` sits at main `9cbb87c` with
no commits. The `.kaola` receipt is gitignored local evidence by design.

## Test Coverage

No production bytes changed, so no new tests are owed. Receipt §6 R14 records that ~25 contract
tests pin prose from the reviewed files; any future landing of the proposals must update them in
the same commit.

## Validation

Candidate: `workflow/issue-156` == main tip `9cbb87c` (main == origin/main), worktree
`.kw/worktrees/issue-156`, clean. The validation receipt is `kaola-workflow/issue-156/.cache/final-validation.md`:
`verdict: pass`, `validated_candidate_hash
4d0d89e4eae4fe9227fe825db3677a96a24e442f7379593d10d0e31b1b595dbc`. The commands
`./scripts/render-skills.py --check` (rc=0; budgets OK; bridge content stage, unpinned) and
`./scripts/validate.sh` (rc=0; 281 rows ok; zero FAILED/ERROR; watchdog skipped on bash 3.2 with
a named receipt per #151) were run separately from the worktree. Suite log:
`/tmp/validate-issue156.log`.

## Changed Paths

(none, expected from the finalize transaction as `changed_paths: []`)

## Documentation Docking

DOCKED; see `kaola-workflow/issue-156/.cache/doc-docking.md`. No public behavior changed.

## Follow-Up Items

- **No follow-up issues filed, deliberately.** Every finding is a proposal under #156, and the
  Owner decides whether and how to split them into delivery issues (issue body Delivery 3/4).
  Filing them now would pre-empt that decision.
- Owner rulings requested (receipt §4 S1–S3): whether to retire the legacy bundle-run
  grandfather text, the old Grok Bot entry clause, and the pre-automatic-binding holder recovery
  text.
- Adjacent code-level observations recorded in receipt §5 (not prompt edits): the
  `adapter_build_launch` functions unused since #130 in all 10 adapters; PTY-era verbs/flags in
  `kaola-tmux.sh` usage text; prose-pinned contract tests. These are left for the Owner's triage.

## Measured

- Byte sizes of all 53 files: `wc -c` at main `9cbb87c`. Budget ceilings: `templates/budgets.json`
  at `9cbb87c`.
- Stale and inaccuracy findings marked ✔ in the receipt were re-checked against source at
  `9cbb87c` with grep and read commands. Evidence: no script emits `self_hosting_risk`; holder
  idle `reason` is built at `kaola-acp-holder.py:1863-1864`; the `ZCODE_HOST_SESSION` regex is in
  `kaola-acp.py`; `kaola-tmux.sh:172` has no `--stdin` flag; `adapter_build_launch` has no caller
  in `kaola-tmux.sh`/`kaola-acp.py`; `--if-snapshot` is not forwarded; `editor` is absent from the
  ACP scripts; `permit` without `--option` answers cancelled at `kaola-acp-holder.py:2834`.

## Hypothesis

- Estimated byte savings (orchestrator ~12–14 KB, Delegator ~1.4 KB, workers ~5 KB per platform)
  are reading-based estimates, not measured renders.
- Receipt §6 R7: whether a non-Host Codex timer carrier delivers the heartbeat body without
  reloading the main Skill is unconfirmed. It gates one proposed cut (PR-R3).

## Readiness

Ready: accepted (Host acceptance granted), validated (receipt above), comment posted, issue kept
OPEN by recorded disposition (`issue_action: comment_keep_open`; the Owner decides), and archived
by the finalize transaction. No content sink (empty branch).

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-156/.cache/doc-docking.md
- kaola-workflow/archive/issue-156/.cache/final-validation.md
- kaola-workflow/archive/issue-156/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-156/finalization-summary.md
- kaola-workflow/archive/issue-156/mission-ledger.jsonl
- kaola-workflow/archive/issue-156/workflow-state.md
