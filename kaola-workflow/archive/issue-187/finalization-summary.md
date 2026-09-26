# Finalization Summary — Issue #187

## Delivered

Kaola-Delegator lets any delegating platform, Grok Bot included, select any of the ten
supported CLI Hosts instead of only ZCode (history: #74 ZCode-only; #119/#122/#126 admitted all
ten Host entries). One live Host per canonical repo remains, whatever its platform.

- The Host platform is its own fact, apart from `authorized_platforms`.
- The Delegator uses that platform's own Runner `<platform>-kaola-project-runner`, its exact
  `host_skill_entry` as the first line of every turn-opening prompt (codex `$kaola-project-runner`,
  kimi-cli `/skill:kaola-project-runner ` with its trailing space), the standard
  `<platform>-<PROJECT_CODE>-orchestrator-<purpose>` name, and its native resume id (zcode `sess_*`
  after the first prompt; claude-code newest `native_session_identity` UUID, never a fresh
  `acp_session_id`; other native ACP agents the recorded agent session id).
- New rendered reference `kaola-delegator/references/host-platforms.md`, rows generated from
  `platforms/<id>.yaml` by `scripts/render-skills.py` (`host_platform_rows`).
- Startup proof is beat-level per `docs/host-entry-evidence.md`: zcode E1, every other row E2 (devin
  included); the handoff carries a `startup_proof=` line; only zcode treats a missing tool_call as a
  bad install. codex-acp 1.13.1 isolated E2 probes answered `SKILL-NOT-LOADED` (Host-reported) and
  the owner's acceptance of the live Codex Host is recorded as owner acceptance, not E1/E2; no
  unconditional tool_call rule.
- One-Host admission (`host-exists` → attach), exact stop (`--expected-holder-instance-id`), safe
  recovery (attach live, no second start, no `--continue`, authorization before a new start, no
  blank Host), recovery with the Host platform unknown via shared `list`.
- Grok Bot co-location: locator `--worker <Host platform>`; the `KAOLA_ZCODE_*` launch gate is
  zcode-only, a non-zcode `--intent start|resume` gives no launchability check; liveness is Runner
  `status`/`list`. Thin bridge byte-identical.
- Installer (Host verdict B): Codex/generic destinations install `kaola-delegator` whatever
  `--platform` selects; the zcode prerequisite is removed; #160 Host-runtime leftover rule unchanged.

Issue statement coverage:

| Issue part | Satisfied by |
|---|---|
| Generated Skill and handoff select platform Runner, standard name, `host_skill_entry`, native resume id without assuming ZCode | `templates/kaola-delegator/*`, `host-platforms.md`; `test-issue-187` static tests (every manifest row, exact codex/kimi entries, no fixed ZCode Host, native resume id rules) |
| Preserve verified same-root identity, one-Host admission, exact stop, Grok Bot co-location | `test-issue-187` lifecycle tests (codex Host blocks kimi-cli and zcode; live claude-code Host blocks zcode; `holder-instance-mismatch`; exact stop `residual_pids: []`); locator test (`--worker codex`, zcode gate zcode-only); tests 74/132 pins in generated-skills |
| Keep the thin Grok Bot bridge unchanged if possible | bridge sha256 `54fbdf39…08ef` identical to base; `test-issue-49`, `kaola-grok-bot-verify` PASS |
| Update renderer, templates, generated output, tests, README, docs | Files Changed below; `render-skills.py --check` PASS |
| Maintain progressive disclosure budgets | SKILL 4075/4096 B, description 318/320, handoff 8186/8192 B, host-platforms 4653/8192 B, bridge 2555/2560 B; `test-progressive-disclosure` PASS |
| Evidence for a non-ZCode Delegator handoff; state Grok Bot account-side UAT unverified | `test-issue-187` (codex/claude-code/kimi-cli Hosts over the mock ACP agent, handoff first line on the wire); README/CHANGELOG state Grok Bot account-side live UAT unverified |

## Files Changed

- `templates/kaola-delegator/SKILL.md.tmpl`, `references/handoff.md.tmpl`,
  `references/host-platforms.md.tmpl` (new), `references/host-brick.md` — source.
- `scripts/render-skills.py` — `host_platform_rows`, `external_values(manifests)`.
- `scripts/install-local.sh` — Delegator planned on Codex/generic without the zcode prerequisite; help text.
- `templates/orchestrator/SKILL.md.tmpl` — two platform-neutral sentences.
- `skills/kaola-delegator/**`, `skills/kaola-project-runner/SKILL.md`,
  `skills/*/scripts/main-skill-build.json` — regenerated.
- `tests/contract/test-issue-187-delegator-any-host.py` (new); `test-issue-74-kaola-delegator.py`,
  `test-issue-94-zcode-native-skill-entry.py`, `test-generated-skills.py`,
  `test-installer-runtimes.sh` — ZCode-locked assertions updated; `scripts/validate.sh` registers the new suite.
- `README.md`, `AGENTS.md`, `CHANGELOG.md`, `docs/architecture.md`, `docs/conventions.md`,
  `docs/grok-bot-host.md`, `docs/host-entry-evidence.md`, `docs/zcode-host.md`.

Implementation commit: `798ad58` on `workflow/issue-187` (base `d08f5c3`); its tracked diff equals
the Host-accepted candidate (sha256 `8bcefb2e85868c199848f56f4c60b78cba1fa102141cda7dc9917f749e6a753b`,
new files `80795d0c…7476`, `e7ea162d…7e03`, `af40ebc0…42ba`).

## Test Coverage

`tests/contract/test-issue-187-delegator-any-host.py` — 14 tests, offline, sandbox HOME and record
root, mock ACP agent, no real CLI, no account:

- every manifest is a selectable row with its exact entry, runtime name, Runner, Host name;
- exact codex `$` and kimi-cli trailing-space entries, also on the wire;
- no fixed ZCode Host in SKILL/handoff; Host platform apart from worker authorization;
- native resume id rules; beat-level startup proof derived from the evidence matrix (devin E2 beat);
- zcode `host_selection` as a start-receipt fact tied to the Runner constants;
- codex Host: verified `host_class` row, `host-exists` refusal of kimi-cli and zcode, handoff
  delivered, `holder-instance-mismatch`, exact stop, attested `--resume`, exact stop;
- live claude-code Host refuses a zcode Host;
- locator `--worker codex`: worker script attested, no zcode runtime gate, no ACP liveness claim.

Installer: `test-installer-runtimes.sh` asserts `--runtime codex --platform grok` and
`--skills-dir --platform grok,codex` install `kaola-delegator` without the zcode worker and print no skip note.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- AGENTS.md
- CHANGELOG.md
- README.md
- docs/architecture.md
- docs/conventions.md
- docs/grok-bot-host.md
- docs/host-entry-evidence.md
- docs/zcode-host.md
- scripts/install-local.sh
- scripts/render-skills.py
- scripts/validate.sh
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-delegator/SKILL.md
- skills/kaola-delegator/agents/openai.yaml
- skills/kaola-delegator/references/handoff.md
- skills/kaola-delegator/references/host-brick.md
- skills/kaola-delegator/references/host-platforms.md
- skills/kaola-project-runner/SKILL.md
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/kaola-delegator/SKILL.md.tmpl
- templates/kaola-delegator/references/handoff.md.tmpl
- templates/kaola-delegator/references/host-brick.md
- templates/kaola-delegator/references/host-platforms.md.tmpl
- templates/orchestrator/SKILL.md.tmpl
- tests/contract/test-generated-skills.py
- tests/contract/test-installer-runtimes.sh
- tests/contract/test-issue-187-delegator-any-host.py
- tests/contract/test-issue-74-kaola-delegator.py
- tests/contract/test-issue-94-zcode-native-skill-entry.py

## Acceptance

- Automated (independent, Host-assigned DSH, foreground, on the exact accepted hashes):
  `./scripts/render-skills.py --check` rc 0; `./scripts/validate.sh` rc 0; #187 14/14, #186 7/7;
  only the named bash 3.2 watchdog skips; final sweep `residual_pids: []`. Receipt `/tmp/187-validate.log`.
- Local (this run, foreground): render `--check` rc 0; installer runtimes and migration PASS;
  `test-issue-{187,74,94,86,49,118,52,162,123,147}`, `test-generated-skills`,
  `test-progressive-disclosure` rc 0.
- Review: independent clean-context review (findings 1–11 addressed) and Host review F1–F3 repaired.
- Host acceptance: explicit ACCEPT of the final candidate at base `d08f5c3`.
- Unexecuted: live Host run on any non-ZCode platform (D3/E1/E2 on this build); Grok Bot
  account-side live UAT; re-measurement of codex-acp 1.13.1 E2; live check of non-ZCode/Claude
  native resume ids.

## Documentation Docking

DOCKED — see `.cache/doc-docking.md`.

## Follow-Up Items

- None filed. The unexecuted live legs above are acceptance boundaries already stated in README,
  CHANGELOG, and `docs/host-entry-evidence.md`, not newly discovered defects.

## Release Notes

- Not released: no tag, publish, or pin of v0.6.4 in this run. The Grok Bot bridge stays at the
  unpinned content stage. Installed hosts must rerun `install-local.sh` (main Skill build id moved).

## Status

Ready: all four missions done; Host accepted; validation pass recorded; documentation docked.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-187/.cache/doc-docking.md
- kaola-workflow/archive/issue-187/.cache/final-validation.md
- kaola-workflow/archive/issue-187/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-187/finalization-summary.md
- kaola-workflow/archive/issue-187/mission-ledger.jsonl
- kaola-workflow/archive/issue-187/workflow-state.md
