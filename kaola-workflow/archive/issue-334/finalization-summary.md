# Finalization Summary — issue-334

## Delivered

Antigravity worker `antigravity-KPR-i334-opus-tier` (antigravity/default) added the antigravity
Opus tier in commit `a039b04d` on `workflow/issue-334` (base = main `40162cda`).

- **Named tier** `antigravity/opus` → `claude-opus-5-5-high`, class Elite
  (`platforms/antigravity.yaml`: `named_tiers: "xhigh,opus"`, opus model fields), with the
  owner-CONFIRMED profile text (Yanlei via Delegator 21:28, exactly as drafted, not a word
  changed): "Deep-reasoning escalation seat for tasks beyond the Argon tiers: architecture and
  cross-cutting design review, hardest debugging, and final-quality passes. Not a default
  worker; select when depth outweighs latency."
- **Effort carried in the model id** (#331 handling reused): `config_application.effort =
  {applied: true, applied_via: "model-id", value: "high"}`; the adapter keeps never passing
  `--effort` separately (asserted by test).
- `antigravity/default` (`gemini-4-argon-medium`) and `antigravity/xhigh`
  (`gemini-4-argon-high`) unchanged; renders regenerated (`render-skills.py --check` PASS);
  CHANGELOG Unreleased with `Seats: restart required` (manifest + adapter changed).
- **Tests**: tier resolution and no-`--effort` (323 suite), `applied_via: "model-id"` for the
  new id and zero dispatch mismatch (331 suite), preset rows (218 suite), declared model
  literals allowlisted in the cross-platform leak check (generated-skills, same structure as
  cursor-cli/devin/droid).

## Candidate

Branch `workflow/issue-334`, single commit `a039b04d` over main `40162cda`.
Validation record: `kaola-workflow/issue-334/.cache/final-validation.md` (verdict pass).

## Evidence

- **Live acceptance** (isolated temp repo, `i334-opus-live`, agy 1.3.5): `start --tier opus` →
  ready, `claude-opus-5-5-high`, effort applied via model-id; `send "Reply with exactly: OK"` →
  `turn_completed`, `final_text: "OK\n"`; exact-stop clean (`residual_pids: []`).
- Worker focused runs: 9 affected suites green; render PASS.
- Host runs on the exact candidate: **full inventory rc=0** (1456.9 s, zero failures);
  render PASS; suites 323/331/218/generated-skills green standalone.
- Owner confirmation of the profile text: Delegator relay, Yanlei 2026-10-15 21:28 Taipei,
  "confirmed exactly as drafted… do not change a word" — the merged text is verbatim.

## Known failures and unverified scope

- Worker-declared: the full inventory was not run by the worker (the Host ran it on the
  candidate); long-horizon Opus-tier behavior on agy beyond the acceptance turn is future
  observation, covered by the tier's profile scoping.
- No tag/release/install (the Delegator releases).

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- README.md
- platforms/antigravity.yaml
- scripts/adapters/antigravity.sh
- skills/antigravity-kaola-project-runner/SKILL.md
- skills/antigravity-kaola-project-runner/references/platform.md
- skills/antigravity-kaola-project-runner/scripts/adapters/antigravity.sh
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/antigravity-kaola-project-runner/scripts/platform.yaml
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/references/profile-catalog.md
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- tests/contract/test-generated-skills.py
- tests/contract/test-issue-218-preset-ids.py
- tests/contract/test-issue-323-antigravity-acp.py
- tests/contract/test-issue-331-effort-model-id.py

## Follow-Up Items

- None filed.

## Final readiness

Ready: candidate accepted (owner-confirmed text + full inventory rc=0 + live acceptance),
validation recorded pass, merge authorized by the confirmation.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-334/.cache/final-validation.md
- kaola-workflow/archive/issue-334/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-334/finalization-summary.md
- kaola-workflow/archive/issue-334/mission-ledger.jsonl
- kaola-workflow/archive/issue-334/workflow-state.md
