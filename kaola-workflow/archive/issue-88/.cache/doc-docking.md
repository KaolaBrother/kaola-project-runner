# Documentation docking — Issue #88

Candidate: `db6bc71` (base `7d14782`). Checklist source: `AGENTS.md` Documentation Map.

## Checked files

| File | Outcome | Detail |
|---|---|---|
| `README.md` | **FIXED** | Permission-defaults paragraph now states the per-platform split (six with an advertised ACP skip-all option; Cursor/Grok launch-flag only; OpenCode none), names the derived no-verified-skip-all roster, and routes a possible request through the existing `permission_required` carrier event and `permit`. Separately the `steer` section no longer pins "today Claude Code and Codex" / "Everywhere else"; it sends the reader to `native_steering` in `platforms/<id>.yaml` and explains all three values. |
| `CHANGELOG.md` | **FIXED** | One `## Unreleased` entry covering both halves of the issue. Sits alongside the existing #87 entry; neither was disturbed. |
| `docs/api.md` | **FIXED** | The `steer` section no longer freezes a native-steering roster or count. It names `native_steering` / `steering_summary` as the source of truth, tells the reader to read `platforms/*.yaml`, and keeps the OpenCode `unknown` case concrete with both versions (1.18.17 probe vs 1.18.29 verified) and its receipt shape. |
| `docs/README.md` | no impact | Index only; no steering or permission-default claim. |
| `docs/runner-v2-dual-transport-design.md` | no impact | Design record; carries no native-steering roster and no permission-default guarantee. |
| `docs/zcode-host.md` | no impact | Its only "steering" mention (line 266) is that a worker event is delivered as an ordinary prompt and is never steering — a ZCode Host statement, unaffected by `native_steering`. |
| `docs/droid-live-verification-2026-09-17.md` | no impact | Dated live-evidence record. Historical by construction; not a live capability claim. |
| `docs/live-smoke-evidence-first-2026-08-30.md` | no impact | Dated live-evidence record; same reasoning. |
| Generated `skills/**` | regenerated | Never hand-edited. `render-skills.py --write` produced no diff against the committed output on the rebased tree. |

## Verification that no stale claim survives

- `grep -rn "opencode" docs/*.md README.md | grep -i "steer\|unsupported"` -> no hits, so no
  document still asserts OpenCode native steering is unsupported.
- The retired phrasings are asserted absent by contract, not by eye:
  `ReadmeDefersToTheManifestsForNativeSteering` and `ApiDocDefersToTheManifests` in
  `tests/contract/test-issue-88-permission-defaults.py`.
- `test_the_native_example_really_is_a_supported_platform` ties README's native example to the
  manifest set, so the example cannot rot silently.

## Status

**DOCKED**
