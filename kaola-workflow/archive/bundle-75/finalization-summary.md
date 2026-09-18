# Finalization summary — bundle-75

Issue: #75 — Codex/ZCode 宿主压缩恢复与 Project Runner 文档维护边界
Branch: `workflow/bundle-75` · Base: `aa5fdad` (post-#81 main) · Sink: merge
Accepted candidate: `c96e605b5bde5589a71a64f15b6bc4ff26120970` (outer ACCEPT, comment 5737537411)

## Delivered

1. **Codex `SessionStart(compact)` recovery — project-local, Host-bound, two-phase.**
   `scripts/kaola-codex-compact-hook.py` owns exactly one entry
   (`kaola-project-runner:compact-context`) in the consuming project's
   `<root>/.codex/hooks.json`, with assets at
   `.codex/kaola-project-runner/hooks/` (payload, emitter copy, `binding.json`).
   `prepare` installs an inert `session_id:null` binding before Host start; `bind`
   writes only `binding.json` after the Host exposes its session id. The emitter
   prints the recovery payload only for `SessionStart` + `source:"compact"` whose
   stdin `session_id` + realpath `cwd` match the binding — ordinary Workers,
   other repositories, and non-compact starts emit nothing. Repeat `prepare`
   preserves a valid binding byte-for-byte and refuses malformed/ambiguous
   shapes before any write. No `CODEX_HOME`/`~/.codex` writes; A/B projects
   coexist; uninstall is strictly local.
   Hardening delivered across review rounds: atomic 0600-adjacent writes with
   no backup copies of foreign config; `status` echo-safe metadata only;
   dangerous `--project-root` refusal (filesystem root, home, effective
   `CODEX_HOME`); realpath containment of `hooks.json`, the asset directory,
   and all three owned leaf files (dir + leaf symlinks refused, in-project
   symlinks legal); blank `--session-id` refusal; `bound` requires non-empty
   id + exact canonical root.

2. **ZCode compact recovery — Skill-layer carriers (no native hook exists).**
   ZCode 0.16.5's `runSessionStartHooks` has only startup/resume call sites;
   `SessionStart(compact)` cannot fire (binary-verified). Shipped:
   `templates/orchestrator/references/zcode-compact-recovery.md` (generated
   into `skills/kaola-project-runner/references/`), covering the
   owner-authorized durable AGENTS.md standing-instruction block (scoped to
   the designated Host; Workers told to ignore it) and the per-send carrier
   fallback. Proof paths verified for BOTH installed Skills —
   `kaola-project-runner` via `KPR-SKILL-RELOAD-V1` in
   `references/zcode-compact-recovery.md`, `kaola-delegator` via
   `zcode-<PROJECT_CODE>-orchestrator-main` in `references/handoff.md`.

3. **Project Runner documentation-maintenance boundary** — generated
   `references/doc-maintenance.md`: dispatch-time doc-impact judgment,
   Workflow docking as acceptance (no second ledger/gate), AGENTS.md
   verified-facts-only discipline per ADR 0023, post-sink verification,
   safe-point in-flight sync.

4. **Contract coverage** — `test-issue-75-codex-compact-hook.py` (37 tests)
   + `test-issue-75-zcode-compact-recovery.py` (15 tests), registered in
   `scripts/validate.sh`.

## Historical blocked items — factual explanation

Three mission entries carry `status: blocked`; their results are immutable
history and were later superseded by completed items under new authorization:

- "Isolated real ZCode verification" and "ZCode carrier deliverable" blocked
  when outer assignment prohibited ZCode live work and #79's adapter fix was
  pending. After #79 landed (`b40813f`), live verification ran: real manual
  `/compact` verified end-to-end (model re-read the planted Skill, quoted the
  marker); UserPromptSubmit plugin hook verified live for typed + RPC compact;
  real `trigger:"auto"` compactions observed on a mock provider with the
  AGENTS prefix surviving on the wire.
- "ZCode compact-recovery follow-on" blocked at phase 2 (live leg gated on
  #79); phase 1's static findings shipped and the live legs completed in the
  follow-on items above.

**Honest limits:** real-GLM `trigger:"auto"` compaction was never observed
(both catalog models have 1M-token windows; ~8M provider tokens needed) —
auto coverage is mock-verified plus by-construction prefix durability, and is
stated as such. The UserPromptSubmit native-hook carrier is live-verified
evidence recorded for a boundary decision, not shipped. The durable AGENTS
block requires explicit project-owner consent; not adopted anywhere.

## Issue statement walk

| Acceptance clause | satisfied by |
|---|---|
| Codex `SessionStart(compact)` recovery | hook script + payload template; live proof rounds 2–3 (`evidence/codex-compact-live/`): inert compact → foreign marker only; bind → same-session compact emits `KPR-COMPACT-RECOVERY-V1`; Worker contrast silent |
| ZCode capability + compact-recovery investigation | `evidence/capability-matrix.md`, `evidence/zcode-compact-mechanism.md`, `evidence/zcode-compact-live/` (4 live rounds); shipped carrier reference |
| Doc-maintenance boundary | generated `references/doc-maintenance.md` + SKILL.md pointer |
| Evidence matrix + isolated real-compaction proof | evidence pack in `kaola-workflow/bundle-75/evidence/` |
| `render --check` + `validate.sh` PASS | recorded below on the accepted SHA |
| No finalize/sink/close without outer ACCEPT | held through 10 frozen candidates; ACCEPT at c96e605 |

## Files Changed

18 files, +2501/−33 vs `aa5fdad`: `scripts/kaola-codex-compact-hook.py` (new),
`templates/codex-host/compact-recovery.md` (new),
`templates/orchestrator/{SKILL.md.tmpl,references/doc-maintenance.md,references/zcode-compact-recovery.md,references/host-startup.md.tmpl}`,
generated `skills/kaola-project-runner/{SKILL.md,references/*}`,
`scripts/validate.sh` (suite registration), `docs/{codex-host.md,zcode-host.md,README.md}`,
`README.md`, `CHANGELOG.md`, `tests/contract/test-issue-75-{codex-compact-hook,zcode-compact-recovery}.py` (new).

## Test Coverage

- `test-issue-75-codex-compact-hook.py` — 37 tests: install/prepare/bind/uninstall/status,
  foreign-hook preservation, malformed/null refusal, binding preservation +
  ambiguity refusal, no-backup secrecy, status echo-safety, dangerous roots,
  dir+leaf symlink containment, blank session ids, emit match matrix
  (Host/Worker/other-repo/non-compact/malformed stdin).
- `test-issue-75-zcode-compact-recovery.py` — 15 tests: carrier semantics,
  role scoping, proof-detail existence for both installed Skills.
- Failure-first discipline kept across all review rounds; monotone.

## Validation

- `verdict: pass` — `.cache/final-validation.md`, `validated_candidate_hash`
  `6f33180eba95df5f93eec844bd9c60e337c38c5abe0bf178dfbd7abfb074bdc0`
- Exact command recorded: `bash scripts/validate.sh` + `python3 scripts/render-skills.py --check`
- Full `bash scripts/validate.sh` on `c96e605` → **exit 0**: all lanes PASS
  (i74 151 assertions, i81 acp 46, i86 46, i90 19, i75 codex 37/37,
  i75 zcode 15/15), `kaola-grok-bot-verify` PASS, `residual_pids=[]`,
  no env mitigation
- `render-skills.py --check` → PASS (9 workers + runner + delegator + bridge; budgets OK)
- `git diff --check` → clean
- Live legs executed: real Codex compact (0.153.4, isolated scratch repo),
  real ZCode manual compact + UserPromptSubmit hook + mock-provider auto —
  all exact-stopped, `residual_pids=[]`, no credentials touched
- Not executed: real-GLM auto-compaction (1M-window infeasible at bounded
  cost — stated as unverified), owner adoption of the AGENTS block (pending
  user consent), Grok Bot live UAT.

## Changed Paths

`CHANGELOG.md`, `README.md`, `docs/README.md`, `docs/codex-host.md`,
`docs/zcode-host.md`, `scripts/kaola-codex-compact-hook.py`,
`scripts/validate.sh`, `skills/kaola-project-runner/SKILL.md`,
`skills/kaola-project-runner/references/{doc-maintenance.md,host-startup.md,zcode-compact-recovery.md}`,
`templates/codex-host/compact-recovery.md`, `templates/orchestrator/SKILL.md.tmpl`,
`templates/orchestrator/references/{doc-maintenance.md,host-startup.md.tmpl,zcode-compact-recovery.md}`,
`tests/contract/test-issue-75-codex-compact-hook.py`,
`tests/contract/test-issue-75-zcode-compact-recovery.py`

## Documentation Docking

`DOCKED` — `.cache/doc-docking.md`. README/docs index/CHANGELOG docked;
no API/setup/architecture impact.

## Follow-Up Items

- **Filed: #93** (P3, OPEN) — ZCode compact-recovery residual: native
  UserPromptSubmit carrier boundary decision + real-GLM auto-compact
  verification gap. Measured/Hypothesis/non-binding remedy; `searched:` probe
  recorded.
- **Correction posted on #75 before closure** (comment 5737600468): the
  issue's original text presumed a possible native ZCode hook; delivered
  truth is the Skill-layer carrier (binary-verified no
  `SessionStart(compact)` call site).
- **#91** (P3, OPEN, from issue-90) — untouched, unrelated residual.
- **#92** (P2, in progress, another run) — untouched.

## Readiness

READY — accepted candidate `c96e605`, validation pass on the frozen SHA,
docs docked, blocked history explained, residual follow-up filed.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/bundle-75/.cache/doc-docking.md
- kaola-workflow/archive/bundle-75/.cache/final-validation.md
- kaola-workflow/archive/bundle-75/.cache/mirror-digest.json
- kaola-workflow/archive/bundle-75/.cache/origin/selection-record.json
- kaola-workflow/archive/bundle-75/evidence/capability-matrix.md
- kaola-workflow/archive/bundle-75/evidence/codex-compact-live/00-project-hooks.json
- kaola-workflow/archive/bundle-75/evidence/codex-compact-live/10-post-compact-pane.txt
- kaola-workflow/archive/bundle-75/evidence/codex-compact-live/20-transcript-extracts.json
- kaola-workflow/archive/bundle-75/evidence/codex-compact-live/30-status-before.json
- kaola-workflow/archive/bundle-75/evidence/codex-compact-live/31-install-receipt.json
- kaola-workflow/archive/bundle-75/evidence/codex-compact-live/32-installed-hooks.json
- kaola-workflow/archive/bundle-75/evidence/codex-compact-live/33-reinstall-receipt.json
- kaola-workflow/archive/bundle-75/evidence/codex-compact-live/34-uninstall-receipt.json
- kaola-workflow/archive/bundle-75/evidence/codex-compact-live/35-after-uninstall-hooks.json
- kaola-workflow/archive/bundle-75/evidence/codex-compact-live/40-repo4-project-hooks.json
- kaola-workflow/archive/bundle-75/evidence/codex-compact-live/41-repo4-binding.json
- kaola-workflow/archive/bundle-75/evidence/codex-compact-live/42-repo4-pane.txt
- kaola-workflow/archive/bundle-75/evidence/codex-compact-live/43-repo4-rollout-extracts.json
- kaola-workflow/archive/bundle-75/evidence/codex-compact-live/50-repo5-project-hooks.json
- kaola-workflow/archive/bundle-75/evidence/codex-compact-live/51-repo5-binding.json
- kaola-workflow/archive/bundle-75/evidence/codex-compact-live/52-repo5-pane.txt
- kaola-workflow/archive/bundle-75/evidence/codex-compact-live/53-repo5-sessionA-rollout-extracts.json
- kaola-workflow/archive/bundle-75/evidence/codex-compact-live/54-repo5-env-compare.json
- kaola-workflow/archive/bundle-75/evidence/codex-compact-live/55-repo5-sessionB-rollout-extracts.json
- kaola-workflow/archive/bundle-75/evidence/codex-compact-live/FINDINGS.md
- kaola-workflow/archive/bundle-75/evidence/validation-receipts.md
- kaola-workflow/archive/bundle-75/evidence/zcode-compact-live/AGENTS.md.fixture
- kaola-workflow/archive/bundle-75/evidence/zcode-compact-live/FINDINGS-auto-compact.md
- kaola-workflow/archive/bundle-75/evidence/zcode-compact-live/FINDINGS-durable-prefix.md
- kaola-workflow/archive/bundle-75/evidence/zcode-compact-live/FINDINGS-native-hook.md
- kaola-workflow/archive/bundle-75/evidence/zcode-compact-live/FINDINGS.md
- kaola-workflow/archive/bundle-75/evidence/zcode-compact-live/auto-compact-parts.jsonl
- kaola-workflow/archive/bundle-75/evidence/zcode-compact-live/db-compaction-parts.json
- kaola-workflow/archive/bundle-75/evidence/zcode-compact-live/events.jsonl
- kaola-workflow/archive/bundle-75/evidence/zcode-compact-live/hook-invocations.jsonl
- kaola-workflow/archive/bundle-75/evidence/zcode-compact-live/mock-requests.jsonl
- kaola-workflow/archive/bundle-75/evidence/zcode-compact-live/provider_config.json
- kaola-workflow/archive/bundle-75/evidence/zcode-compact-live/rpc-compact-events.jsonl
- kaola-workflow/archive/bundle-75/evidence/zcode-compact-mechanism.md
- kaola-workflow/archive/bundle-75/finalization-summary.md
- kaola-workflow/archive/bundle-75/mission-list.md
- kaola-workflow/archive/bundle-75/workflow-state.md
