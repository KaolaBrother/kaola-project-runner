# Finalization summary — issue #111

Issue: **#111** — v0.5.5: re-point Kimi/Droid/DSH/ZCode/Devin model presets at live-verified ids
and add a third (alternative/fable) tier
Branch: `workflow/issue-111` · Candidate: **d6bd56b** · Sink: merge

## Delivered

Five platforms' Runner model presets re-pointed at ids read from the live ACP catalog on
2026-09-21, and a generic, optional third preset slot so a platform can declare a
**default + alternative** pair under its own word.

- **kimi-cli** — default `kimi-code/k3` "Kimi K3 Max" at `thinking=max`; new `--tier alternative`
  `kimi-code/kimi-for-coding` "Kimi K2.8" at `thinking=max`; no distinct upgrade tier.
- **droid** — default `kimi-k3` at `reasoning_effort=max` through Droid's own first-class catalog
  id, so `acp_model_map` stays empty; `--tier alternative` `kimi-k2.7-code`, the Kimi-family
  analogue (Host-confirmed), carrying no Runner effort; no distinct upgrade tier; the
  `model=auto` sentence in `launch_summary` rewritten.
- **dsh** — first Runner model selection for this platform: default
  `opencode-go/deepseek-v4.1-flash`, whose ACP wire value the existing `acp_model_map` already
  carried unchanged.
- **zcode** — `default_model_*` and the upgrade preset pinned to `GLM-5.3` at `thought=max`,
  generalising the Issue #108 Host gate to the ordinary preset path.
- **devin** — third tier `fable` → `claude-fable-5-1-high`, coexisting with default `swe-2-max`
  and the existing fusion upgrade; `acp_verified_versions` refreshed to `cli=3000.10.31`.

Both sources of truth moved together: `platforms/*.yaml` feeds the ACP path through
`kaola-acp.py`, `scripts/adapters/*.sh` feeds the PTY path through `kaola-tmux.sh`, and nothing
but the new test made them agree.

## Files Changed

30 source files, 1 new test, 62 regenerated files under `skills/` and `hosts/`.

- Mechanism — `scripts/render-skills.py` (the `alt_*` field registry, the all-or-nothing shape
  check, `tier_block()` and `alt_tier_line()`), `templates/SKILL.md.tmpl`,
  `templates/references/platform.md.tmpl`
- CLI — `scripts/kaola-acp.py` (`tier_prefix`, `tier_declared`, `tier_refusal`),
  `scripts/kaola-tmux.sh`, `scripts/kaola-model-policy.py`
- Facts — all ten `platforms/*.yaml`; `scripts/adapters/{kimi-cli,droid,dsh,zcode,devin}.sh`
- Tests — new `tests/contract/test-issue-111-model-tiers.py`; updated
  `test-droid-acp-contract.py` + `fake-droid-acp-agent.py`, `test-zcode-heartbeat-contract.py`,
  `test-generated-skills.py`; `scripts/validate.sh`
- Docs — `docs/api.md`, `docs/architecture.md`, `README.md`, `CHANGELOG.md`

## Test Coverage

`tests/contract/test-issue-111-model-tiers.py` — 22 tests, ~2 s, registered in
`scripts/validate.sh` in `python_suites_all` and lane b (the lanes still partition the 49-suite
list exactly). It pins each new default and alternative id, manifest/adapter agreement across all
ten platforms, the optionality of the third slot (empty computed blocks and no trace in the seven
non-declaring packages), the typed refusal on both entrypoints, the equality of
`platforms/zcode.yaml` with `ZCODE_HOST_MODEL_ID`/`ZCODE_HOST_EFFORT`, and the
`thought`/`thoughtLevel`/`thought_level` tolerance on the read path behaviourally and on the
adapter write path structurally (AST, so a narrowed tuple fails).

Mutation-checked, not merely green: re-pointing the ZCode default to `GLM-5.3-Flash` (5 failures),
narrowing the thought tuple (1), drifting an adapter id from its manifest (1), and dropping Devin's
`fable` label (5) each fail it; the baseline restores to OK.

An earlier draft drove resolution end to end through `preflight`, which probes the real CLI
catalogs — a single Droid probe ran past two minutes — so resolution is asserted
deterministically and only the refusal path, which returns before any probe, stays end to end on
both transports.

Three pre-existing suites pinned the replaced behaviour and were **updated, not weakened**:
`test-droid-acp-contract.py` now pins the `kimi-k3` default and gains alternative-tier and
typed-refusal cases (11 → 13 tests), with its fake agent's catalog extended to the three live Kimi
entries; `test-zcode-heartbeat-contract.py` keeps the real #108 boundary — no Host machinery on a
worker — while accepting the new preset underneath it, and gains a case proving an explicit worker
effort still wins; `test-generated-skills.py` gains narrow, named cross-platform leakage
exemptions for the exact declared model facts, in the style it already uses for cursor-cli and
devin, with the one avoidable token (`gpt-5.6-sol`) removed from Droid's prose instead of exempted.

## Validation

- `verdict: pass`, recorded via `kaola-workflow-validation-runner.js record`
- Receipt: `.cache/final-validation.md`; `validated_candidate_hash`
  `fc70d93330fb99004c56040c760d744f7a1fd1617c180510a39500bb9671f2f7`, bound to the candidate
  worktree at d6bd56b
- Command:
  `env -u KAOLA_ZCODE_ENTRY -u KAOLA_ZCODE_NODE -u KAOLA_ACP_DISPATCHER -u KAOLA_ACP_HEARTBEAT_HOST ./scripts/render-skills.py --check && … ./scripts/validate.sh`
- Outputs: `render-skills: PASS (… budgets OK)`; `validate.sh` exit **0**, no `FAILED` line
  (`/tmp/validate-111-final.log`). Run in the foreground against the frozen candidate; the tree was
  clean before and after.
- Budgets: every worker `SKILL.md` inside `worker_skill_bytes` 12288 — tightest devin 12154
  (134 B), cursor-cli 12136 (152 B), opencode 12090 (198 B), kimi-cli 12068 (220 B). Largest
  `references/platform.md` 5448 B against 8192. `templates/grok-golden/` byte-identical.
- Not executed: live tmux smoke per platform (no authorization to start worker sessions in this
  run). The Host closed part of that gap independently — see Acceptance.

### Acceptance walk

Every acceptance box in the issue, and what satisfies it:

| Criterion | Satisfied by |
|---|---|
| kimi-cli default/alternative, no upgrade tier | manifest + adapter; `LiveVerifiedPresets`, `ManifestAndAdapterAgree` |
| droid default/alternative, empty `acp_model_map`, rewritten `launch_summary` | manifest + adapter; `test_droid_needs_no_model_map_for_its_first_class_id`, `test_droid_launch_summary_no_longer_claims_model_auto`, Droid ACP suite |
| dsh default, map unchanged, display-name distinction recorded | manifest; `test_dsh_default_is_already_carried_by_the_model_map`, `test_dsh_records_the_runner_side_display_name` |
| zcode `default_model_*` = GLM-5.3 at max, no second source of truth | `ZcodeHasOneSourceOfTruth` (manifest ≡ `ZCODE_HOST_MODEL_ID`/`ZCODE_HOST_EFFORT`) |
| devin `fable` tier coexisting with default and upgrade | manifest + adapter; `LiveVerifiedPresets`, rendered `--tier fable` |
| third slot generic, optional, computed-block rendered, absent where undeclared | `ThirdTierIsOptional` (4 tests) + `render-skills.py --check` |
| `--tier` accepts the new value in both scripts; undeclared tier is a typed refusal | `UndeclaredTierIsRefused` (3 tests) + Droid suite's refusal case |
| every `SKILL.md` ≤ 12288 and every reference ≤ 8192, margins checked | `--check` budgets OK + the margin table above |
| `docs/api.md` lists the new field names | `.cache/doc-docking.md` |
| `skills/`/`hosts/` regenerated only by `--write`; grok-golden byte-identical | `git status` on `templates/grok-golden/` clean; `--check` PASS |
| `render-skills.py --check` passes | PASS |
| `validate.sh` passes in the foreground, exit line recorded | exit 0 |
| a test pins each new id and the ZCode config-id tolerance | `test-issue-111-model-tiers.py`, mutation-checked |
| CHANGELOG entry for v0.5.5 | `## 0.5.5 — unreleased` |
| pre-tag pin/adapter verification recorded per platform | **deferred to the Host's release step** by explicit direction; see Follow-Up |

### Host acceptance

**PASS** for `workflow/issue-111@d6bd56b`, verified independently of this run's prose:
`--check` PASS with budgets OK; `templates/grok-golden/` zero-diff; manifest diffs matched the
issue's live-verified ids exactly; the three generated third-tier Skills render correctly and only
on explicit request; 0 `FAILED` in the validate log; and a **live probe** through this worktree's
generated kimi-cli runner with `--tier alternative` resolved `model=kimi-code/kimi-for-coding`,
`effort=max`, `source=runner-alternative`, with the probe session stopped cleanly.

The Host's own rerun hit one failure, `test-zcode-acp-contract::test_resolve_runtime_fails_closed`,
root-caused to the Host environment leaking `KAOLA_ZCODE_ENTRY`/`KAOLA_ZCODE_NODE` into that static
test; with those stripped the ZCode contract suite passes 71/71.

## Changed Paths

Reported by the finalize transaction; see `## Changed Paths` appended below by that run.

## Documentation Docking

**DOCKED** — `.cache/doc-docking.md`.

## Follow-Up Items

Host-accepted residuals, deliberately **not** fixed in this run:

1. **`validate.sh` env-hermeticity gap** — `KAOLA_ZCODE_ENTRY`/`KAOLA_ZCODE_NODE` and
   `KAOLA_ACP_HEARTBEAT_HOST` leak from a live Host into static tests
   (`test_resolve_runtime_fails_closed`; `test-issue-73`'s `heartbeat-host-unresolved` becomes
   `heartbeat-host-conflict`). Pre-existing, reproduced from both sides in this run, and now
   **Host-held for the release phase** — no follow-up issue filed, by direction.
2. **Droid's alternative tier carries no effort** — `reasoning_effort=max` was verified live
   against `kimi-k3` only, and the agent states available options depend on the selected model.
   Documented in the manifest prose and asserted by the Droid ACP suite.
3. **ZCode `thought` vs live `thoughtLevel`** — tolerated by both the read and write paths and now
   pinned by tests, so a future narrowing fails loudly instead of silently dropping the default.
4. **Release step** — tagging v0.5.5 and the Grok Bot `saveable: true` pin
   (`workflow/grok-bot-pin-v0.5.5`) belong to the Host, after this run and the separate OpenCode V2
   investigation both land. `CHANGELOG.md` stays `## 0.5.5 — unreleased` deliberately.

No run-discovered defect was left unaddressed: the two found in-run
(`kaola-model-policy.py` rejecting a `runner-<tier>` source; the shell's doubled tier label in its
refusal message) were fixed inside this candidate rather than filed.

## Readiness

**READY** — accepted by the Host, validation receipt bound to the candidate, documentation docked.

---

## Finalize-transaction addendum — sink blocker and its repair (2026-09-21)

The merge sink refused its first run with **zero mutation**:

```json
{"result":"refuse","reason":"sink_blocked",
 "foreign_dirt":[".kaola/heartbeat-prompt.json"],
 "detail":"main checkout carries changes not owned by this sink; resolve
           (commit/stash/restore) before re-running."}
```

`<project>/.kaola/heartbeat-prompt.json` is the Project Runner heartbeat carrier: the ZCode Host
writes it (`templates/orchestrator/**`) and `kaola-acp-holder.py:2269` reads it at delivery time.
It is per-project runtime state, has never been tracked in this repository, and was not covered by
`.gitignore` — so it reads as foreign dirt and trips the sink's clean-main invariant
(`INVARIANT: if foreign_dirt is non-empty, NO mutation occurs`; the sink exposes no override flag).

Raised to the Host as `HUMAN_DECISION_REQUIRED`, because clearing the file is both value-laden and
another session's property. **Host decision: option 2** — add `.kaola/` to `.gitignore`.

> Rationale, as recorded by the Host: the ZCode-Host heartbeat carrier is required by the Project
> Runner Skill to live at `<project>/.kaola/heartbeat-prompt.json` and is never meant to be tracked;
> without the ignore line, every ZCode-Hosted run on this repository deadlocks the merge sink's
> clean-main invariant the same way. Moving or deleting the live file (options 1/3) races heartbeat
> delivery. The one-line ignore is the permanent, surgical fix.

Repair commit **a92c569** — `.gitignore` only, one line, no other scope. The live carrier file was
never moved, deleted, stashed, or committed.

### Gate re-run on the repaired candidate

- Candidate: **a92c569** (implementation `d6bd56b` + the ignore line); tree clean before and after.
- `./scripts/render-skills.py --check` → `PASS (… budgets OK)`, exit 0
- `./scripts/validate.sh` → exit **0**, no `FAILED` line (`/tmp/validate-111-gitignore.log`)
- Both run in the foreground under
  `env -u KAOLA_ZCODE_ENTRY -u KAOLA_ZCODE_NODE -u KAOLA_ACP_DISPATCHER -u KAOLA_ACP_HEARTBEAT_HOST -u ZCODE_BIN`.
  Three further ZCode variables present in the Host environment
  (`ZCODE_BUILTIN_PROVIDER_CONFIG_FILE`, `ZCODE_PERSONAL_PROVIDER_CONFIG_FILE`, `ZCODE_RUNTIME_ENV`)
  and `KAOLA_ACP_HEARTBEAT_HOST_SOCKET` were **not** stripped and did not leak into any suite.

### Validation-record binding

`.cache/final-validation.md` binds `validated_candidate_hash`
`fc70d93330fb99004c56040c760d744f7a1fd1617c180510a39500bb9671f2f7` — the **d6bd56b** tree, the
accepted implementation candidate. It was deliberately **not** re-bound to a92c569: rerunning
`kaola-workflow-validation-runner.js record` after the archive answered `outcome: inconclusive`,
`record_path: null`, writing nothing, on the ground that an archived run's record is closed
evidence and must not be amended retroactively. That refusal was respected rather than worked
around; the repaired candidate's green gate is recorded here instead, which is where a
finalize-transaction finding belongs.

This addendum also closes follow-up item 1 in a narrower sense than it was written: the
`.kaola/` half of the environment/dirt leak class is now fixed permanently in-repo. The
`KAOLA_ZCODE_*` / `KAOLA_ACP_HEARTBEAT_HOST` **test-environment** hermeticity gap in
`scripts/validate.sh` is untouched and remains Host-held for the release phase.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-111/.cache/doc-docking.md
- kaola-workflow/archive/issue-111/.cache/final-validation.md
- kaola-workflow/archive/issue-111/.cache/mirror-digest.json
- kaola-workflow/archive/issue-111/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-111/finalization-summary.md
- kaola-workflow/archive/issue-111/mission-list.md
- kaola-workflow/archive/issue-111/workflow-state.md
