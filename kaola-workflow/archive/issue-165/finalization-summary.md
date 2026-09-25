# Finalization Summary — issue #165

## Delivered

`status` and `list` now name two reported-only build-drift conditions that
#162 left silent:

- `recorded-path-missing` (with the names in `missing_files`) — a recorded
  runner path that no longer resolves to a file because the checkout moved or
  was deleted. #162's byte comparison yields no digest for an unreadable path,
  so such a path was neither "changed" nor "unchanged" and went unreported.
- `install-root-mismatch` (with `recorded_root` and `install_root`) — a seat
  whose recorded runner tree is not the tree its own platform is expected to
  live under, e.g. a reinstall under a different root.

The root comparison is per platform: the expected tree is the seat's OWN
`skills/<platform>-kaola-project-runner` sibling when this CLI runs from an
installed Skill tree, else this checkout. A seat of another platform listed
from one platform's tree (the documented Host sweep) is therefore not falsely
flagged, while a genuinely re-rooted seat still is. Both conditions are
evidence only: they never set `stale` and never gate transport.

The candidate was rebased from `d283283` onto current main
`4b04654ac9d4e5a5d8b0f5271bd595b37cc31b1e` as a single linear commit. The
rebase had textual conflicts in `CHANGELOG.md` (kept every Unreleased bullet:
#162, #164, #163, #166, #167, and #165) and `scripts/validate.sh` (kept every
suite line: both `test-issue-164-pre-spawn-bridge-facts.py` and
`test-issue-165-path-drift.py`), plus the generated worker copies, regenerated
from the resolved source with `./scripts/render-skills.py --write`.

## Files Changed

`scripts/kaola-acp.py` (three new helpers `_unresolved_recorded_files`,
`_recorded_tree`, `_resolved_str`, `_expected_install_tree`; two new
`reported_drift` conditions in `seat_freshness`; three new `list` row fields),
its ten generated worker copies, `tests/contract/test-issue-165-path-drift.py`
(new), `scripts/validate.sh` (wired), and `CHANGELOG.md`. The holder, ZCode
bridge, and protocol are unchanged.

## Test Coverage

- `./scripts/validate.sh` — exit 0, 897 tests across 46 unittest suites; the
  #162 suite ran 20 tests and the #165 suite 6.
- `./scripts/render-skills.py --check` — PASS (generated set matches source).
- Validation log: `/tmp/i165-finalize-validate.log`.
- The full live per-platform ACP smoke was not run; Host acceptance, the
  claude-code review PASS, and the offline contract validation are the
  acceptance evidence for this run.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- scripts/kaola-acp.py
- scripts/validate.sh
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- tests/contract/test-issue-165-path-drift.py

## Documentation Docking

DOCKED — see `.cache/doc-docking.md`. The CHANGELOG bullet is the docking
surface; `docs/api.md`, `README.md`, conventions, and architecture docs were
checked and did not require changes; no generated surface was hand-edited.

## Follow-Up Items

None. Issue #165 closure is performed by the merge sink; no GitHub issue
actions were performed by this seat beyond the claim.

## Final Readiness Status

READY — candidate frozen at `c54d22e8b2fabe858fd00836c8164d85de680bd6`.
No tag, release, or pin commit.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-165/.cache/doc-docking.md
- kaola-workflow/archive/issue-165/.cache/final-validation.md
- kaola-workflow/archive/issue-165/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-165/finalization-summary.md
- kaola-workflow/archive/issue-165/mission-ledger.jsonl
- kaola-workflow/archive/issue-165/workflow-state.md
