# Finalization Summary — Issue #58

project: bundle-58
branch: workflow/bundle-58
sink: merge
candidate: 1bca06b (workflow/bundle-58, 8 commits over base 3d0fc66, clean worktree)

## Delivered

Issue #58 adds Factory's **Droid CLI** as the **ninth worker platform** with **both transports adapted**:

- **ACP** — the native agent `droid exec --output-format acp` (no vendored bridge, no Runner-owned translator; `acp_wrapper_pin` empty), driven by the existing ACP client/holder path. Session config options verified live: `model`, `reasoning_effort`, `autonomy_level` (declared in the `session/new` result). `session/resume` works; the native session id surfaces in the `session/new` result.
- **PTY** — the native TUI in the exact owned tmux session: quit `/quit`, resume `--resume <session-id>`, continue `--resume --last`, binary env `DROID_BIN`.

**Default setup (as the user specified): Auto Model + bypass permissions on both transports.** ACP start applies `model=auto` (droid's native ACP default is `gpt-5.6-sol`) and `autonomy_level=auto-high` (droid's native ACP default is already full bypass). PTY launches with `--skip-permissions-unsafe` plus a process-scoped `--settings` overlay pinning `{"model":"auto"}` (run-scoped temp file; the Runner never writes `~/.factory`).

**No upgrade setup:** `upgrade_model_*` mirrors the default (`--tier upgrade` is a no-op on droid); reasoning effort is passed only when the caller explicitly selects it; `fast_support: "none"` (`-fast` catalog ids are explicit `--model` choices).

New manifest key `acp_mode_config_id` on all nine manifests (droid `autonomy_level`; claude-code/codex/devin/kimi-cli/zcode `mode`; grok/cursor-cli/opencode empty) makes the ACP mode/permission option id manifest-driven; existing-platform behavior is byte-identical and covered by contract tests.

Version bumped: `## 0.3.3 — 2026-09-17` prepared in a CHANGELOG-only commit, per the user's instruction and the repo's release pattern.

## Files Changed

Commits on `workflow/bundle-58` over base 3d0fc66 (all carry the factory-droid co-author trailer):

- `4974a77` feat(droid): add Droid as the ninth worker platform (65 files, +9060/−61) — manifest, adapter, all enumerations, tests, generated skills.
- `4dce730` fix(render): count nine platform Runner Skills across orchestrator surfaces (12 files).
- `0c42077` fix(droid): detect live 0.220.0 TUI readiness in activity hints.
- `6acf3ac` docs: record droid live ACP and PTY verification (docs/droid-live-verification-2026-09-17.md).
- `664c4d0` feat(acp): drive the ACP mode config id from the manifest acp_mode_config_id (31 files, +83/−125).
- `9bbf880` docs(droid): document ninth worker platform (7 files, +93/−32).
- `9e6ca73` docs: prepare v0.3.3 changelog (CHANGELOG.md only, +2).
- `1bca06b` docs(grok-bot): say tenth, not eighth, now that nine workers exist (doc-docking fix).

## Test Coverage

- `./scripts/validate.sh` on the frozen candidate: **exit 0** — includes `render-skills.py --check` (9 workers + orchestrator + grok-bot host, budgets OK), per-skill `validate-skill.py`, `bash -n`, installer suites, and all contract suites including the new `tests/contract/test-droid-acp-contract.py` (11 tests: manifest renderer/inventory 49 checks, skip-all-mode bypass on ACP+PTY 8 checks, start/send/cancel/stop schema v3 32 checks) over the new `tests/contract/fake-droid-acp-agent.py`.
- `./scripts/render-skills.py --check`: PASS (run repeatedly during the run and on the frozen candidate).
- Byte budgets: droid `SKILL.md` 11799 ≤ 12288; droid description 233 ≤ 320 chars; droid `references/acp.md` 5608 ≤ 8192; orchestrator `SKILL.md` 16366 ≤ 17408 (`templates/budgets.json` `main_skill_bytes` re-measured 16384→17408 for the ninth roster row; padding gate preserved).
- `git diff --check`: clean.

## Validation

- `.cache/final-validation.md`: `verdict: pass`, command `./scripts/validate.sh`, `validated_candidate_hash: ad24e261fbacafcc46da92e4bad5aa4f7f42c266c0a0bac55c69302678ba2d0a` (frozen candidate 1bca06b; log `/tmp/bundle58-final-validate.log`, VALIDATE_EXIT=0).
- Live gates (committed evidence `docs/droid-live-verification-2026-09-17.md`, real droid 0.220.0): **ACP PASS** — manifest-default transport, `model=auto` + `autonomy_level=auto-high` applied, pong and file-write turns with zero permission requests, clean stop with `residual_pids: []`, native-id resume with history. **PTY PASS** — `--skip-permissions-unsafe` + process-scoped `{"model":"auto"}` overlay, native folder-trust answered once (a native act by the CLI itself), bypass-proving write turn, `/quit` stop, `--resume --last` continue with history; zero residue on both gates; foreign Factory daemon tree untouched. `default_transport: acp` confirmed.
- Acceptance legs: automated (validate.sh + render --check + contract suites) — executed, pass; live/local (ACP + PTY gates) — executed, pass; manual/UAT — none required beyond the live gates (the user's "validate that it works before the merge sink" is satisfied by the committed live evidence). Unexecuted: none.
- Issue walk: every claimed member of issue #58 is satisfied — goal (ninth platform, both transports), default setup (Auto Model + bypass on both transports), no-upgrade requirement (mirrored upgrade tier; effort only when explicitly called; no Fast wiring), full change checklist (all enumerations; the manifest key-count estimate in the issue body was corrected on the issue by comment), offline validation, live gates, evidence doc, out-of-scope respected (`templates/grok-golden/` untouched, no vendoring, no login automation, no heartbeat changes, Grok Bot bridge unchanged beyond count phrasing).

## Changed Paths

Per the finalize transaction report (read-only check): nine platform manifests (`platforms/*.yaml` incl. new `droid.yaml`), `scripts/adapters/droid.sh`, enumerations in `scripts/render-skills.py`, `scripts/kaola-tmux.sh`, `scripts/kaola-acp.py`, `scripts/install-local.sh`, `scripts/kaola-locate.py`, `scripts/kaola-grok-bot-verify.py`, `scripts/kaola-model-policy.py`, `scripts/validate.sh`, the full new `skills/droid-kaola-project-runner/` tree plus regenerated worker/orchestrator outputs, `templates/budgets.json`, `templates/orchestrator/SKILL.md.tmpl` + reference, twelve test files including the new droid contract test and fake agent, and docs (`README.md`, `docs/api.md`, `docs/architecture.md`, `docs/conventions.md`, `docs/runner-v2-dual-transport-design.md`, `docs/grok-bot-host.md`, `docs/droid-live-verification-2026-09-17.md`, `AGENTS.md`, `CHANGELOG.md`). The transaction's appended findings below carry the authoritative list.

## Documentation Docking

`.cache/doc-docking.md` → **DOCKED** (README, api, architecture, conventions, runner-v2 design, grok-bot-host count fix, AGENTS managed facts, CHANGELOG 0.3.3, live evidence doc; `docs/README.md` and `docs/acp-watch/README.md` verified no-impact; `hosts/grok-bot/`, `templates/grok-bot/`, `templates/orchestrator/` verified clean of stale counts).

## Follow-Up Items

- **Filed: #59 (P3)** — `tests/contract/test-lifecycle-contract.py` `SKILL_IDS` roster is stale (missing `zcode-kaola-project-runner` and `droid-kaola-project-runner`); iterative and passing, so a coverage gap, not a failure. searched: `gh search issues --repo KaolaBrother/kaola-project-runner 'SKILL_IDS'` — 1 hit (#59 itself); no duplicate existed.
- Recorded corrections on issue #58 (comment, pre-close): the real manifest schema is 41 required keys + `acp_mode_config_id` (not the issue's 53-key estimate); the probe-decided ACP config ids; the budgets re-measure; the native folder-trust note.
- No other deferred items: `test-observation-contract.py`'s answer-mode list correctly omits droid (its answer mode is unsupported); historical v0.3 prose in the runner-v2 design doc is baseline narrative, not current inventory.

## Closure Decision

Issue set: #58 only. All acceptance parts are satisfied (see Validation and the issue walk); follow-up #59 is new out-of-run work, not open work of #58. Close #58 on Workflow sink. No keep-open.

## Readiness

READY_FOR_FINALIZE — pending the finalize transaction, merge sink, and closure audit.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/bundle-58/.cache/doc-docking.md
- kaola-workflow/archive/bundle-58/.cache/droid-acp-probe.md
- kaola-workflow/archive/bundle-58/.cache/final-validation.md
- kaola-workflow/archive/bundle-58/.cache/mirror-digest.json
- kaola-workflow/archive/bundle-58/.cache/origin/selection-record.json
- kaola-workflow/archive/bundle-58/finalization-summary.md
- kaola-workflow/archive/bundle-58/mission-list.md
- kaola-workflow/archive/bundle-58/workflow-state.md
