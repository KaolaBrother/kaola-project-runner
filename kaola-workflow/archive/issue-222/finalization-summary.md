# Finalization Summary — issue #222

## Delivered

Owner-confirmed, compatibility-preserving corrections to the model-to-quota-package catalog,
plus a display-name shortening — exactly the issue #222 scope, nothing more:

- **cursor-cli** explicit map: `grok-4.7`, `grok-4.7-xhigh`, `grok-4.7-xhigh-fast` moved to
  `cursor-models`; the `claude-opus-5-5` family stays `other-models`; `auto`/`default` stay
  `cursor-models`. Unknown ids remain unmapped.
- **droid** `native_field` billingPool: static preset knowledge `auto→standard`,
  `claude-opus-5-5→standard`, `kimi-k3→core`, serving the static query and the
  missing/null/empty-field case only. A live row's present native value still wins
  (`billingPool: "core"` → `droid:core` against the static `standard`); a present unknown
  value stays unmapped; nothing is guessed into an unrelated pool.
- **zcode** `provider_prefix`: the bare configured model id `GLM-5.3` maps to
  `bigmodel-coding-plan`; the provider-qualified routes (`builtin:bigmodel-coding-plan\…`,
  `account:bigmodel-individual-coding-plan\…`) are unchanged. Package display name becomes
  **GLM Coding Plan** (id `bigmodel-coding-plan`, window `5h` unchanged).
- **Resolver** (`scripts/kaola-quota.py`): optional per-rule `models` map accepted for
  `provider_prefix` and `native_field`, normalized through the explicit-map validator so a
  static entry can never name a balance package; present-null equals omitted (matching the
  `absent` convention). This adopts the outer assistant's uncommitted draft design with one
  hardening (`_model_bindings` raises a clear `QuotaError` for non-object/empty `models`).
- **Display names** (display text only): dsh and opencode `default_model_name` become exactly
  **DeepSeek V4.1 Flash** (dsh launch_summary mention included; adapters updated; preset ids,
  launch model ids, provider routing, and the `OpenCode Go` package display name unchanged).
- **Regenerated surfaces**: `render-skills.py --write` (README preset table, generated
  `skills/`, `hosts/`). Contract expectations updated in
  `tests/contract/test-issue-148-quota-packages.py` (corrected rows, droid static rows, zcode
  bare `GLM-5.3`, native-wins/missing-field/unknown-id cases, GLM Coding Plan name) and
  `tests/contract/test-issue-111-model-tiers.py`. `docs/api.md` and the orchestrator
  `references/quota-packages.md` template/examples updated: the droid `claude-opus-5-5`
  unmapped example is now mapped, replaced by a genuinely unmapped id (`brand-new-model`).
  The orchestrator quota reference stayed inside the locked 8192 B budget (8173 B; no ceiling
  raised). `templates/grok-bot/accepted-revision.json` returned to the `content` stage per
  the documented post-pin flow for the first content change after a release pin; the next
  release re-pins (not a release action; no tag was created).

## Candidate

- Branch `workflow/issue-222`, commit `dfc77ac8` ("fix(quota): #222 correct model-package
  mappings, shorten DeepSeek names"), 50 files changed, working tree clean.
- Worktree: `/Users/ylmacstudio/Workspace/kaola-project-runner/.kw/worktrees/issue-222`.
- The canonical checkout's uncommitted outer draft on the four overlapped paths was never
  modified; the branch supersedes it (Host authorized restoring those paths pre-merge).

## Evidence

- `./scripts/validate.sh` → exit 0, full suite green (bash-4 watchdog rows SKIP with named
  receipts per #151 — pre-existing machine condition, bash 3.2.57).
- `python3 tests/contract/test-issue-148-quota-packages.py` → 16/16 OK;
  `python3 tests/contract/test-issue-111-model-tiers.py` → 25/25 OK;
  `./scripts/render-skills.py --check` → PASS, budgets OK. All re-run against the committed
  state.
- API outputs (`scripts/kaola-acp.py`, worktree): cursor-cli `grok-4.7-xhigh|grok-4.7|
  grok-4.7-xhigh-fast|auto|default → cursor-cli:cursor-models`, `claude-opus-5-5|-high|
  -medium → cursor-cli:other-models`, unknown → unmapped; droid static `auto|
  claude-opus-5-5 → droid:standard`, `kimi-k3 → droid:core`; zcode bare `GLM-5.3` and both
  provider-qualified forms → `zcode:bigmodel-coding-plan`; zcode packages row
  `GLM Coding Plan`, windows `["5h"]`; dsh/opencode package rows and `opencode-go`
  resolutions unchanged. README lines 325-326 and generated dsh/opencode/zcode Skills show
  `DeepSeek V4.1 Flash` / `GLM Coding Plan`.
- Native billingPool precedence exercised without a live agent (live droid start is out of
  scope — no model probes) through the resolver surface `annotate_observe` uses, with
  synthetic rows; also pinned by `test_native_field_uses_the_row_and_never_guesses`.
- Host independently verified all of the above and accepted (recorded in conversation,
  2026-09-29): render --check PASS budgets OK; 16/16 and 25/25 OK; validate.sh rc=0; direct
  API outputs confirmed; no protected files touched; CHANGELOG untouched.
- Validation receipt: `kaola-workflow/issue-222/.cache/final-validation.md` — verdict `pass`,
  candidate hash bound to the worktree tree.

## Known failures / unverified scope

- None. Out-of-scope by design: live-agent droid native-row verification (would require
  starting an agent; no model probes per issue boundary); runtime model verification is never
  claimed from a preset name.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- README.md
- docs/api.md
- hosts/grok-bot/INSTALL.md
- hosts/grok-bot/bridge.json
- hosts/grok-bot/kaola-delegator.md
- platforms/cursor-cli.yaml
- platforms/droid.yaml
- platforms/dsh.yaml
- platforms/opencode.yaml
- platforms/zcode.yaml
- scripts/adapters/dsh.sh
- scripts/adapters/opencode.sh
- scripts/kaola-quota.py
- skills/claude-code-kaola-project-runner/scripts/kaola-quota.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/kaola-quota.py
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/kaola-quota.py
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/platform.yaml
- skills/devin-kaola-project-runner/scripts/kaola-quota.py
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/kaola-quota.py
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/platform.yaml
- skills/dsh-kaola-project-runner/SKILL.md
- skills/dsh-kaola-project-runner/references/platform.md
- skills/dsh-kaola-project-runner/scripts/adapters/dsh.sh
- skills/dsh-kaola-project-runner/scripts/kaola-quota.py
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/platform.yaml
- skills/grok-kaola-project-runner/scripts/kaola-quota.py
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/references/profile-catalog.md
- skills/kaola-project-runner/references/quota-packages.md
- skills/kimi-cli-kaola-project-runner/scripts/kaola-quota.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/SKILL.md
- skills/opencode-kaola-project-runner/references/platform.md
- skills/opencode-kaola-project-runner/scripts/adapters/opencode.sh
- skills/opencode-kaola-project-runner/scripts/kaola-quota.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/platform.yaml
- skills/zcode-kaola-project-runner/scripts/kaola-quota.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/platform.yaml
- templates/grok-bot/accepted-revision.json
- templates/orchestrator/references/quota-packages.md
- tests/contract/test-issue-111-model-tiers.py
- tests/contract/test-issue-148-quota-packages.py

## Follow-Up Items

- None filed. No run-discovered defects; no corrections to the issue body were needed (the
  delivery matches it).

## Final readiness

Ready: accepted by Host, candidate frozen and verified, mission ledger 3/3 done. Proceed to
merge sink, close #222, archive, sink.

## Finalize Findings

### residue_unattributed

The residue mirror did not copy the paths below out of the main checkout: this run's HEAD does not contain them. Presence in main, an untracked status, or a neighboring file this run committed is not evidence they belong to this run. Nothing was copied, staged, committed, deleted, reverted or relocated — they remain in the main checkout. Read them before the sink runs: commit what belongs to the run, leave what does not.

Paths left in the main checkout:

- docs/harness-acp-compat-2026-09-25.md
- docs/harness-acp-compat-2026-09-26.md

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-222/.cache/final-validation.md
- kaola-workflow/archive/issue-222/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-222/finalization-summary.md
- kaola-workflow/archive/issue-222/mission-ledger.jsonl
- kaola-workflow/archive/issue-222/workflow-state.md
