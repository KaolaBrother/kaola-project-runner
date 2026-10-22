# Finalization Summary — Issue #386

## Delivered

Issue #386's high-frequency receipt cost is removed on `workflow/issue-386` without weakening the
Issue #25 L0 contract or the repository identity check.

- `send --no-wait`, `steer` and `permit` omit `git` and skip the two facts queries
  (`git rev-parse --abbrev-ref HEAD`, `git status --porcelain`) by default.
- A `send` follows its resolved wait: explicit `--wait` and an omitted selection that resolves to
  blocking keep `git` and the pre-existing L0 receipt shape.
- `--git-facts` / `--no-git-facts` override either default; the last occurrence wins. Both are
  accepted by `kaola-acp.py` and forwarded by `kaola-tmux.sh` and the generated `runtime-tmux.sh`.
- `status`, `observe`, `start` and the other schema-3 receipts are unchanged; `view` was already
  outside `base_receipt`.
- The eight pre-mutation refusal helpers that built a receipt and then discarded `git` now pass
  `include_git=False`, so they skip the facts helper as well.
- No cross-process `resolve_repo` cache was added. Each ACP CLI call that carries `--repo` still
  runs exactly one `git rev-parse --show-toplevel` root check, which this issue deliberately leaves
  unchanged.
- `docs/api.md` and `CHANGELOG.md` state the two skipped facts queries, the remaining root check,
  and the last-occurrence-wins order.
- `tests/contract/test-issue-386-git-facts.py` (11 cases, including the dual-flag order matrix
  across all three entrypoints) is registered in `scripts/validate.sh`; the shared scripts are
  re-rendered into the twelve generated Skill copies.

Candidate: `2f54669c527d8a5cc7b85daa0d40df36219624d8` on `workflow/issue-386`; the feature commit
is `f847a430d391d1a09cdd4cdb65e066b674b53816`; base `f3964ff052b57fc87dccf7773ca902a956d907d6`.
This run performed no tag, release, publish, install, or KPM-side operation.

## Acceptance Evidence

- Host acceptance of `2f54669c` after the review repair, independently rechecking the 11-case dual
  flag coverage, `render-skills.py --check` plus the suites (exit 0), and the 98-call probe counts.
- Final clean-tip validation at `2f54669c`, exit 0:
  `./scripts/validate.sh --suite test-issue-386-git-facts.py --suite test-acp-contract.py`
  - `test-issue-386-git-facts.py`: 11/11 OK, 8.989 s.
  - `test-acp-contract.py`: 87/87 OK, 126.335 s (L0 send/wait included).
  - `render-skills.py --check`: PASS; total wall 127.215 s; no residual pids.
  - Log: `/tmp/kpr386-386-validate-reviewfix-tip.log`.
- `test-issue-383-holder-timeout.py`: 29/29 OK at `f847a430`; `2f54669c` changed only tests and
  documentation, so that product-code evidence remains valid.
- clean-env reviewer `probe.py` rerun at `2f54669c`: `COMPLETED 98 CLI calls`, exit 0.
  Default `send --no-wait` / `steer` / `permit` on all three entrypoints: no `git` field, 0 facts
  queries, 1 remaining `resolve_repo` invocation. Waiting and opt-in sends: `git` present, 2 facts
  queries, 3 total. Both dual-flag orders across all three entrypoints: last occurrence wins.
  `status` / `observe`: `git` present, 2 facts, 3 total; tier/rebind refusals: no `git`, 0 facts,
  1 total. Logs: `/tmp/kpr386-386-probe.log`, `/tmp/kpr386-386-probe/results.json`.
- Pre-fix counter-proof on base `f3964ff0` with the reviewed ten-test revision: 12 failures + 1
  error by subTest (8 failed methods, 1 error, 1 pass), direction unchanged.
  Log: `/tmp/kpr386-386-prefix-r2.log`.

## Known Failures and Unverified Scope

- No full-inventory `validate.sh` run: the selected suites cover the changed receipt decision, the
  L0 contract, and the bounded transport surface; the change touches no holder or adapter.
- The probe uses the repository's mock ACP agent with a real local holder; no external vendor
  service UAT was run, and none of the changed bytes are on a platform transport path.
- The remaining one `git rev-parse --show-toplevel` per `--repo` CLI call is intentional and out of
  #386's scope; the docs and CHANGELOG state it explicitly.
- The new dual-flag test exercises the generated `grok` Skill runtime wrapper; render checks keep
  that copy consistent with `scripts/kaola-tmux.sh`.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/api.md
- scripts/kaola-acp.py
- scripts/kaola-tmux.sh
- scripts/validate.sh
- skills/antigravity-kaola-project-runner/scripts/kaola-acp.py
- skills/antigravity-kaola-project-runner/scripts/kaola-tmux.sh
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-tmux.sh
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-tmux.sh
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-tmux.sh
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-tmux.sh
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-tmux.sh
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-tmux.sh
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-tmux.sh
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-tmux.sh
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-tmux.sh
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-tmux.sh
- tests/contract/test-issue-386-git-facts.py

## Documentation Docking

DOCKED — `docs/api.md` documents the command-scoped `git` facts, the two skipped facts queries, the
remaining `resolve_repo` root check and both overrides; `CHANGELOG.md` `Unreleased` records the
same boundary. No template, budget, installer, holder or platform manifest changed.

## Follow-Up Items

- No new follow-up issue was filed by this run.
- No release, tag, publish, install, or KPM-side operation is part of this finalization.
- #386 closes with the Host-supplied closing comment after the merge is verified.

Final readiness: ready. Merge sink to `main`, verify publication, close #386 with the Host-supplied
comment, archive under `kaola-workflow/archive/issue-386/`, and remove the run worktree and branch.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-386/.cache/final-validation.md
- kaola-workflow/archive/issue-386/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-386/finalization-summary.md
- kaola-workflow/archive/issue-386/mission-ledger.jsonl
- kaola-workflow/archive/issue-386/workflow-state.md
