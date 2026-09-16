# Documentation docking — Issue #49 / bundle-49

DOCKED. Frozen candidate P3 `db4b0d5813111ef71afbcf165be0fb91d9a7d976` pinning R3 `bc8592d323864c30010b48ae724f329f8df6753e`. Candidate product bytes were not mutated in Finalization.

Checked against AGENTS.md Documentation Map (README, CHANGELOG, docs/) and the owner-corrected acceptance (Issue #49 comments 5693161395, 5693224801, 5693267500): Grok Bot is a first-class **bridge host** with exactly one thin account Skill `kaola-project-runner`, a device-local locator, progressive disclosure, and a two-commit content/pin model. It is not an eighth CLI worker and has no installer destination.

## Checked files

- `README.md` — MATCH: Agents-that-load section states the one-bridge-Skill host, locator/target binding, no cross-host reach, seven platforms, `--platform grok` remains the Grok CLI worker, and `--runtime grok-bot` is not an install destination.
- `docs/grok-bot-host.md` — MATCH on delivery shape, R/P pin gate, locator/attestation, budgets, no `platforms/grok-bot.yaml`, no Marketplace. OWNER ACCEPTANCE EXCEPTION (not a byte fix in this run): UAT verify text still names Settings → Plugins → Yours and `/` discovery. Owner correction 5693224801 and this-turn instruction reclassify those as unavailable on this individual-account rollout, not hard gates; owner forbade R4/P4 and candidate mutation. Functional UAT PASS is native Skill write + unique name + fresh 1:1 exposure (5693267500).
- `hosts/grok-bot/INSTALL.md` — MATCH on R3/P3 SHAs, one-write same-name update, Local Computer register/`--expect-revision`, read-only preflight. Same OWNER ACCEPTANCE EXCEPTION as above for the Yours/`/` verify sentence. Trailing-newline serializer observation accepted as non-semantic (5693267500).
- `docs/api.md` — MATCH: renderer emits the bridge/manifest/guide; pin gate and `--require-pinned`; installer refuses `--runtime grok-bot`; locator `register` requires `--expect-revision`, origin-form refusals, registration receipt, attestation fields (session presence-only).
- `docs/architecture.md` — MATCH: generated Skills, progressive disclosure with bounded observe/status/capture on both transports, host-adapter boundary (`GROK_BOT_ADAPTER_INPUTS` = `templates/grok-bot/` only), two-commit model, no eighth platform.
- `docs/conventions.md` — MATCH: one canonical Skill system, Grok Bot adapter inputs, budgets, frozen `templates/grok-golden/`, `skills/` and `hosts/grok-bot/` never hand-edited.
- `docs/README.md` — MATCH: index points at the Grok Bot host page (bridge, targets, locator, one-write install).
- `CHANGELOG.md` — MATCH: Unreleased entries cover Missions 7–10 (bridge, R/P, R2/P2, R3/P3 bounding). No version bump; this Finalization does not create a release or tag.
- `AGENTS.md` — MATCH: managed snapshot names the thin generated account Skill, locator, progressive-disclosure budgets, and “not an eighth worker / no installer destination”. Public commands remain `render-skills.py` / `install-local.sh` / `validate.sh`.
- `templates/grok-golden/` — NO-IMPACT: empty diff vs `main`.
- Worker Skills / `platforms/` / `scripts/adapters/` — NO-IMPACT as an eighth platform: seven ids only; workers remain transport-only; host policy stays in the orchestrator/bridge adapter.

## Owner exceptions recorded (not BLOCKED)

1. Yours and slash-command discovery are not acceptance gates for this account rollout (5693224801). Guide/docs still mention them; owner declined a fresh R4/P4 to rewrite that prose.
2. Official Skill-write serializer dropping one trailing newline is non-semantic (5693267500).
3. No Marketplace publication, no Grok Bot account mutation, no release/tag in this Finalization.

Live seven-platform start/observe/send/capture/stop smoke was not re-run as a new harness: this close-out re-ran `./scripts/validate.sh` (exit 0) and the live private-tmux suite `tests/contract/test-kaola-tmux.sh` (PASS) over the frozen P3 tree. Owner UAT already proved the account Skill write, unique name, native 1:1 exposure, locator, and exact worker preflight.
