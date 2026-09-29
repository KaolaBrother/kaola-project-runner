# Finalization Summary — issue #228

## Delivered

Claude Code preset policy for Issue #228, on the accepted candidate. Native
alias strings stay `opus`, `sonnet`, and `fable`. Preset ids stay
`claude-code/default` and `claude-code/sonnet` (`opus` is the native model
alias, not a preset id). Fable's preset, effort, and profile are unchanged.

`claude-code/sonnet` is Elite at effort `high`, profile exactly: All-round
execution worker, well suited to well-scoped work. It left the Worker pool.
It uses the existing Elite grant (preset and count): no default seat, no
preset-specific cap, and no ordinary Sonnet seat for this project. The five
remaining Worker presets stay default-authorized and outside the general
worker cap: `codex/luna`, `dsh/default`, `devin/default`, `opencode/default`,
`zcode/default`.

`claude-code/default` stays Elite and stays the Claude Code runtime default,
including when Claude Code is the Host, at effort `xhigh`. Profile exactly:
Plans and reviews difficult, complex work and handles deep reasoning tasks;
does not perform implementation. Thinking-only still permits Host planning,
dispatch, and acceptance. It does not restore a revoked ordinary Opus worker
seat, and it does not copy this limit onto other runtimes' Opus or Fusion
rows.

Source manifests, the adapter, the rendered catalog, README, and the Host
dispatch guidance were synchronized through the existing render. No new gate.
No install, no new release, and the published v0.6.9 tag was not moved.

Unreleased notes state `Seats: restart required` because the operator diff
`v0.6.9..1e8644a8` is non-empty on `platforms/claude-code.yaml`,
`platforms/codex.yaml`, and `scripts/adapters/claude-code.sh`. This
finalization does not restart a live seat.

## Candidate

`workflow/issue-228` at `1e8644a81456649b7a2ef899cf79d30b78e8ad94`.
Delegator scoped review of this commit: PASS. No further approval was
required. The pre-amend hash `25768c23` remains in mission 3 of the ledger
because that done line is immutable; the accepted tree is `1e8644a8`.

## Evidence

Native alias proof versus served-model unknown, measured on CLI 2.1.284 at
`~/.local/bin/claude` (package `@anthropic-ai/claude-code` 2.1.284),
first-party path (no provider-switch env). Baked `aliases.default` and
`latest_per_family` in that binary, matched by the local model-catalog
first-of-family order:

| Preset | Requested alias | Native target from the binary | Served API model |
|---|---|---|---|
| `claude-code/default` | `opus` | `claude-opus-5-5` | unknown |
| `claude-code/sonnet` | `sonnet` | `claude-sonnet-5-5` | unknown |
| `claude-code/fable` | `fable` | `claude-fable-5-1` | unknown |

The served column is unknown because the weekly quota was exhausted and no
live turn ran. That column is not a PASS. Bridge echo is the alias string,
not a resolved id. No alias mismatch was proven, so no mapping correction
was made. Ledger: `kaola-workflow/.ledger/issue-228.jsonl` (missions 1–2).

Profile and class evidence is the catalog on `1e8644a8` and Delegator PASS
of the correction delta (preset ids, restart declaration, removal of the
literal-effort helper, scoped catalog assertions).

- `python3 tests/contract/test-issue-218-preset-ids.py`: 16 tests, exit 0,
  on this candidate.
- `kaola-workflow/issue-228/.cache/final-validation.md`: `verdict: pass`,
  command `python3 tests/contract/test-issue-218-preset-ids.py`,
  `validated_candidate_hash: 67bbfd13b3635121bc451dc13c3309ad681b8d69a55ecb62531d4ae0c41ff8b5`.
- `kaola-workflow-run-chains.js --project issue-228`: `chains_config_missing`
  (no `package.json` `test:kaola-workflow:*` scripts). Consumer gate is the
  recorded final-validation file.

## Known failures / unverified scope

- Actual served model for `opus`, `sonnet`, and `fable` was not observed.
  Native alias resolution in the 2.1.284 binary is the proof. It does not
  establish what the API served.
- `./scripts/validate.sh` was not rerun. The Delegator accepted the scoped
  checks and asked for no repeated review suite.
- No install. No live seat was restarted. The v0.6.9 tag and GitHub release
  were not edited.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- README.md
- docs/api.md
- docs/architecture.md
- docs/zcode-host.md
- platforms/claude-code.yaml
- scripts/adapters/claude-code.sh
- skills/claude-code-kaola-project-runner/SKILL.md
- skills/claude-code-kaola-project-runner/references/platform.md
- skills/claude-code-kaola-project-runner/scripts/adapters/claude-code.sh
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/platform.yaml
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/SKILL.md
- skills/kaola-project-runner/references/heartbeat-skeleton.md
- skills/kaola-project-runner/references/profile-catalog.md
- skills/kaola-project-runner/references/worker-profiles.md
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/orchestrator/SKILL.md.tmpl
- templates/orchestrator/references/heartbeat-skeleton.txt
- templates/orchestrator/references/worker-profiles.md.tmpl
- tests/contract/test-issue-218-preset-ids.py

## Follow-Up Items

None filed. The served-model unknown is the accepted verification boundary,
not a separate defect.

## Final readiness

Ready: Delegator PASS on `1e8644a8`; merge sink, close #228, archive.

## Finalize Findings

### residue_unattributed

The residue mirror did not copy the paths below out of the main checkout: this run's HEAD does not contain them. Presence in main, an untracked status, or a neighboring file this run committed is not evidence they belong to this run. Nothing was copied, staged, committed, deleted, reverted or relocated — they remain in the main checkout. Read them before the sink runs: commit what belongs to the run, leave what does not.

Paths left in the main checkout:

- docs/harness-acp-compat-2026-09-25.md
- docs/harness-acp-compat-2026-09-26.md
- docs/harness-acp-compat-2026-09-29.md

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-228/.cache/final-validation.md
- kaola-workflow/archive/issue-228/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-228/finalization-summary.md
- kaola-workflow/archive/issue-228/mission-ledger.jsonl
- kaola-workflow/archive/issue-228/workflow-state.md
