# Finalization Summary — Issue #379

## Delivered

Fixed KPR #379 on `workflow/issue-379`: send, steer and steer_interrupt error
receipts now state the mutation fact for **this** request.

- `no-session`, `record-lost`, `holder-socket-missing` and a `holder-lost`
  observed before any wire attempt report `mutation_performed: false` with
  `mutation_status: not_started`; that pre-wire `holder-lost` also carries
  `previous_prompt`, while `record.last_prompt` still serves `status`/`observe`.
- `holder-closed`, send/read-stage failures, a stage-less `holder-unreachable`,
  and a `holder-lost` discovered only after a wire attempt report `null` with
  `mutation_status: unknown`. A frame that may have been written is never
  flattened to false.
- The holder busy receipt now uses `outcome: refused_busy` instead of the
  successful `--no-wait` word `in_progress`; `mutation_performed: false` and the
  active turn's `mutation_status` are unchanged.
- A `start --text`/`--stdin` failure receipt keeps the internal prompt
  request's mutation, so an unknown brief frame stays unknown.
- Steer error receipts carry the matching
  `steer_outcome`/`steer_consumed`/`steer_confirmation`.
- `status`, `observe`, `capture`, `permit`, `cancel` and `stop` keep their
  previous `holder_lost_receipt` facts.
- The `error.stage` hook is in place for #383: connect will be definite
  `false`, send/read stay `unknown`; the post-wire holder-loss source marker
  keeps today's stage-less wire death unknown.
- `docs/api.md` and `CHANGELOG.md` updated; templates and the 8191/8192-byte
  budgets are unchanged. Generated Skill script copies were re-rendered.

Candidate: `56a65dabc93427477ff77a4435ac92655bdd3e14` on `workflow/issue-379`;
parent `9781d9342788fce1718f828bf50919b29695f5d6`. No tag, release, install, or
amplification of the change was performed.

## Acceptance Evidence

- Independent review: `/tmp/kpr379rev/REVIEW.md` (F1/F2 raised and fixed).
- Post-fix boundary probes: `/tmp/kpr379r2/evidence/boundary-probes.json`
  (`post_write_holder_death` null/unknown; `start_brief_text` and
  `start_brief_stdin` null/unknown).
- Seven-shape reproduction: `/tmp/kpr379/evidence-fixed.json`.
- Host acceptance: `56a65dab` diff reviewed; joint run plus two isolated reruns
  were 19/19 OK; the astra first-run holder-closed difference was not
  reproduced after the fixture hardening.
- Focused validation logs: `/tmp/i379-r2-joint.log`,
  `/tmp/i379-r2-isolated.log`, `/tmp/i379-r2-related.log`, and
  `/tmp/i379-joint-fixed-*.log`.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/api.md
- scripts/kaola-acp-holder.py
- scripts/kaola-acp.py
- scripts/validate.sh
- skills/antigravity-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/antigravity-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- tests/contract/test-acp-contract.py
- tests/contract/test-issue-255-lifecycle-state.py
- tests/contract/test-issue-263-steer-adaptation.py
- tests/contract/test-issue-341-agent-initiated-turn.py
- tests/contract/test-issue-379-receipt-mutation.py
- tests/contract/test-issue-65-steering.py

## Documentation Docking

DOCKED — `.cache/doc-docking.md`. `docs/api.md` records the request-scoped
contract, false vs null, `refused_busy`, the brief-failure preservation and the
`error.stage` forward boundary; `CHANGELOG.md` records the behavior and the
holder-restart/CLI-per-call facts.

## Finalize Findings

### residue_unattributed

The `chore: finalize` commit did not carry `.cache/doc-docking.md` because the
branch had not previously tracked a file in that directory. Repair: the file
was copied into this archive at `.cache/doc-docking.md` before the sink, so the
archive carries the documentation docking record.

## Follow-Up Items

- #383 will add `error.stage` (`connect`/`send`/`read`) and the holder timeout;
  the #379 wrapper and the post-wire stage preservation are ready for it.
- `scripts/kaola-acp-holder.py` is in the operator restart set, so a running
  holder keeps the old busy word until it restarts; `scripts/kaola-acp.py` is
  the per-call CLI and takes effect with installation.
- No release, tag, publish, or install is part of this finalization.

Final readiness: ready. Merge sink to `main`, close #379 with the requested
comment, archive the run, and remove the run worktree and branch. No release,
tag, or install.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-379/.cache/doc-docking.md
- kaola-workflow/archive/issue-379/.cache/final-validation.md
- kaola-workflow/archive/issue-379/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-379/finalization-summary.md
- kaola-workflow/archive/issue-379/mission-ledger.jsonl
- kaola-workflow/archive/issue-379/workflow-state.md
