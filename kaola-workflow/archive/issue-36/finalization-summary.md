# Finalization Summary — issue-36

Issue: https://github.com/KaolaBrother/kaola-project-runner/issues/36
PR: https://github.com/KaolaBrother/kaola-project-runner/pull/38 (OPEN, `Closes #36`)
Candidate: `workflow/issue-36` @ `74d6b3f` — `bcbd6d8` + merges of `origin/main`
@ `3650a28` (#34) and @ `27e277b` (#33) + supervisor review fix
(comment 5655133645: `place_staged` rollback — a failed staged rename now
restores the previous target from backup; a failed rollback retains the
backup and reports its recovery path; callers remove only the staged temp;
PYTHON_BIN fault-injection tests cover both cases) + supervisor-applied
Bash 3.2 correction `74d6b3f` (`for row in ${bin_actions[@]+"${bin_actions[@]}"}`
— empty-array expansion under `set -u` on macOS bash 3.2; verified by
independent supervisor installer run `/tmp/kpr36-supervisor-install2.log` and
combined render+validate `/tmp/kpr36-supervisor-combined.log` exit marker 0).
Conflicts: CHANGELOG.md,
README.md, docs/api.md — all resolved keeping both sides (#34 two-tier model
table with neutralized `Skill` header; #33 configOptions paragraph + #36
installer wording; #34/#33/#36 CHANGELOG entries in merge order).
`scripts/validate.sh` auto-merged with the neutral-HOME sandbox AND the
`test-issue-33-config-meta.py` wire intact. Generated `skills/` re-rendered
from merged sources — no manual generated-file merges;
`render-skills.py --check` PASS; generated payloads carry #33
`initial_config_options` and #34 presets.
Status: **FINAL candidate ready — held for supervisor final acceptance; no
merge performed.**

## Delivered

- Runtime-neutral Agent Skills payload: all seven manifests describe a generic
  controlling Agent; every invocation example resolves
  `"$SKILL_DIR/scripts/runtime-tmux.sh"` absolutely, so copied Skills work
  outside the checkout and under paths with spaces. Seven Skill names
  preserved; `agents/openai.yaml` retained as optional Codex metadata;
  `templates/grok-golden/` byte-identical.
- Installer contract in `scripts/install-local.sh`:
  `--runtime codex|claude-code|cursor|devin`, `--skills-dir ABS_PATH`
  (mutually exclusive), `--method link|copy` (default `link`),
  `--bin-links`/`--no-bin-links`, `--platform` unchanged, scoped `--uninstall`.
  Copy installs record per-Skill ownership/content receipts outside the payload
  (`<dest>/.kaola-install-receipts/`), no-op on identical owned content, refuse
  foreign or edited paths, staged same-filesystem replacement; shared helper
  links preserved unless explicitly requested. No registry/refcounts;
  no-argument Codex default preserved.
- Repository-owned neutral validator `scripts/validate-skill.py` replaces the
  external `~/.codex/.../quick_validate.py` dependency; `scripts/validate.sh`
  runs under a controlled temporary HOME with `CODEX_HOME`,
  `CLAUDE_CONFIG_DIR`, `DEVIN_CONFIG_DIR` unset.
- Runtime-neutral documentation: README/architecture/api/AGENTS/CHANGELOG
  updated; consuming-runtime vs target-platform terminology and
  authenticated-tested vs standard-format compatibility documented.

## Files Changed

51 files: 7 platform manifests, 3 template files, 7 generated Skill trees
(regenerated only, never hand-edited), installer, validator, validate.sh,
render-skills.py docstring, 4 test files (1 new), README, 2 docs, AGENTS.md,
CHANGELOG.md. `templates/grok-golden/` untouched (diff empty).

## Test Coverage

- `tests/contract/test-installer-runtimes.sh` (new): named runtimes, arbitrary
  `--skills-dir` with spaces, argument validation, link/copy, copy fidelity
  incl. exec bits, no-op reinstall, update, edited-copy preservation,
  clean uninstall incl. receipts, copy↔link switching, foreign-path refusal,
  coexistence + scoped uninstall, shared/explicit/foreign bin-links.
- `tests/contract/test-generated-skills.py`, `test-lifecycle-contract.py`:
  markers updated to pin the quoted absolute-path invocation form.
- `tests/contract/test-acp-watch-contract.py`: updated to new shared-link
  contract (uninstall preserves; `--bin-links` removes). 13/13 PASS.
- Neutral validator accept/reject cases; all seven generated Skills validate.

## Validation

- `./scripts/render-skills.py --check && ./scripts/validate.sh` → `VALIDATE_RC=0`
  on the FINAL tree (recorded: `kaola-workflow/issue-36/.cache/final-validation.md`,
  `validated_candidate_hash 1181407f…`, binds worktree tree at `74d6b3f`;
  includes #34 model-policy/ACP suites, #33 config-meta contract (9 tests),
  and the place_staged fault-injection cases). Independent supervisor combined
  run: `/tmp/kpr36-supervisor-combined.exit` = `0`.
- `git diff -- templates/grok-golden` → empty.
- Live e2e (full receipt:
  `kaola-workflow/issue-36/.cache/live-portability-evidence.md`):
  - FINAL leg @ `d948b90` — Devin (non-Codex controller) → Codex ACP via
    EXPLICIT Skill reading of the NEW candidate's copied payload (in-place
    `update:` install): `start` applied default preset `gpt-5.6-sol`/`high`
    with `fast-mode=off` explicitly configured (`runner-default`/`tier:default`);
    `send` → `KPR36_FINAL_OK`/`end_turn`; `observe` reported CURRENT
    `configOptions` (sol/high/full-access/off) distinct from
    `initial_config_options` (agent/medium) — #33 reporting live; `stop` →
    `residual_pids:[]`, `status` stopped, zero `kpr36` residue.
  - Leg A (prior, bcbd6d8) — Devin → Codex ACP target via EXPLICIT Skill
    reading of the copied payload at a path with spaces:
    preflight `login_required:false` → `start` ready → `send` →
    `final_text "KPR36_DEVIN_OK"`, `end_turn` → `stop` `residual_pids:[]` →
    `status` stopped.
  - Leg B — Codex consuming runtime → Grok ACP target: Codex read the copied
    `grok-kaola-project-runner/SKILL.md` and invoked its absolute
    `runtime-tmux.sh` (read:1, execute:6) for preflight/start/send/capture/
    stop/status; observed `KPR36_CODEX_OK`; target record `state:stopped`.
  - Native discovery vs explicit reading distinguished in the evidence file:
    Codex's `availableCommands` natively listed `$grok-kaola-project-runner`
    from `~/.codex/skills`; the drive path was explicit copied-Skill reading.
  - Self-containment proven: holder spawned as `Path(__file__).parent /
    "kaola-acp-holder.py"` sibling; no `~/.local/bin` or checkout dependency
    on the executed path; receipts live outside the payload.
  - No PTY or Claude-auth legs (issue scope); only pre-existing foreign tmux
    sessions remain; zero `kpr36` residue.

## Changed Paths

```
AGENTS.md
CHANGELOG.md
README.md
docs/api.md
docs/architecture.md
platforms/{claude-code,codex,cursor-cli,devin,grok,kimi-cli,opencode}.yaml
scripts/install-local.sh
scripts/render-skills.py
scripts/validate-skill.py        (new)
scripts/validate.sh
skills/*-kaola-project-runner/   (generated output, 7 trees)
templates/SKILL.md.tmpl
templates/references/platform.md.tmpl
templates/references/transport.md.tmpl
tests/contract/test-acp-watch-contract.py
tests/contract/test-generated-skills.py
tests/contract/test-installer-runtimes.sh (new)
tests/contract/test-lifecycle-contract.py
```

## Documentation Docking

`.cache/doc-docking.md` → DOCKED. README, architecture, api, AGENTS, CHANGELOG
updated; conventions/README-index checked, no change needed; grok-golden and
`agents/openai.yaml` confirmed no-impact.

## Follow-Up Items

- Awaiting supervisor FINAL ACCEPTANCE of PR #38 (`d948b90`). Integration vs
  #34 AND #33 DONE: merges + re-render + full revalidation + refreshed live leg
  on the new payload all complete. On acceptance: finalize transaction
  (finalize → archive → issue close → merge sink → closure audit). No manual
  generated-file merges were used at any step.
- Owner correction recorded: final v0.1.0 release waits for ALL of #33/#34/#36;
  #33 and #34 are merged — #36 is the last release prerequisite. This run does
  not publish independently.
- #33 fix verified live on the final candidate: current `configOptions`
  reflects applied config (sol/high/full-access) vs `initial_config_options`
  baseline (agent/medium) — the pre-#33 snapshot-only behavior is gone.
- No run-discovered defects requiring follow-up issues.

## Final readiness status

READY-FOR-REVIEW. All eight missions `done` in `mission-list.md`; offline and
live evidence preserved; PR #38 open and unmerged by design.

Finalize precondition check (read-only, recorded at
`.cache/finalize-check.json`): `ok:true`, `reasons:[]` — mirror ready
(workflow_state `pending_mirror`), validation `chains_green`, staging_guard
`ok`, `dirty_paths:[]`, `changed_paths` matches the PR diff exactly.

Finalize transaction (finalize → archive → merge sink → closure audit) is
staged for execution on the main-ready authorization; nothing merged, closed,
or published by this run.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-36/.cache/doc-docking.md
- kaola-workflow/archive/issue-36/.cache/final-validation.md
- kaola-workflow/archive/issue-36/.cache/finalize-check.json
- kaola-workflow/archive/issue-36/.cache/live-portability-evidence.md
- kaola-workflow/archive/issue-36/.cache/mirror-digest.json
- kaola-workflow/archive/issue-36/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-36/finalization-summary.md
- kaola-workflow/archive/issue-36/mission-list.md
- kaola-workflow/archive/issue-36/workflow-state.md
