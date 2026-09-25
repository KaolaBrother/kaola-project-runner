# Documentation docking — issue #183

Candidate: `79f140a440ccfca1bb153f5add503aac57a3e746` (workflow/issue-183)
Validation: `/tmp/kpr-i183-validate-final.log` — `./scripts/validate.sh` exit 0, 0 FAIL.

## Verdict

DOCKED

## Checklist against changed public behavior

The change is documentation plus test-side model-read-back coverage. No
production behavior, protocol surface, CLI signature, or receipt field
changed: the operator diff
(`git diff 8ab96d7 HEAD -- scripts/kaola-acp-holder.py scripts/kaola-zcode-acp.py scripts/kaola-quota.py scripts/adapters platforms`)
is empty, confirming holder, bridge, quota catalog, adapters, and manifests
are byte-identical.

| Surface | Action | Evidence |
|---|---|---|
| `docs/api.md` (the `session_meta.configOptions` paragraph, ~:333) | **updated** | Names `session_meta.models.currentModelId` and `initial_config_options` as `session/new` snapshots that a set never refreshes, and names the current-selection fields `session_meta.configOptions[model].currentValue` (`status`/`observe`) and `effective_selection.effective_model` (`start`). Adds the ACP 0.225.1 protocol limitation (selection observable, serving model unprovable per turn) with the probe persistence measurement. |
| `CHANGELOG.md` | **updated** | Unreleased entry referencing #183, `Seats: restart not required`, the Auto-Model-only no-substitution rule, and the mock-fidelity fix. Operator diff recorded as empty. |
| `README.md` | no impact | No user-facing entry point, install step, or usage changed. |
| `docs/architecture.md` | no impact | No component, data flow, or transport change. |
| `docs/conventions.md` | no impact | The Seats/operator-test convention is unchanged; this run follows it and its operator diff is empty. |
| `docs/codex-host.md`, `docs/zcode-host.md` | no impact | Host-path facts are unchanged; the droid Host path was measured to apply the identical preset, and no Host mechanism was added. |
| API/receipt schema | no impact | Field set unchanged; the docs change only how to *read* existing fields correctly. |
| Environment/setup | no impact | No new prerequisite; no install or locator change. |
| Examples | no impact | No example referenced the misread snapshot fields. |

## Accuracy check

Every field name and claim transcribed into `docs/api.md` and `CHANGELOG.md`
was taken from the verified sources, not invented:

- `session_meta.models.currentModelId` / `session_meta.configOptions` /
  `initial_config_options` — read from the live droid 0.225.1 `session/new`
  result and the holder's record (`scripts/kaola-acp-holder.py:1495`,
  `:1683`, `:1750`).
- `session_meta.configOptions[model].currentValue` and
  `effective_selection.effective_model` — read from
  `effective_selection()` (`scripts/kaola-acp.py:2495`).
- Persistence figure (one set, three prompts, zero reverts) — measured from
  `/tmp/kpr-i183-probe2-q2/all_frames.jsonl`, corroborated by the i174 (9)
  and i180 (5) live echo streams in `/tmp/kpr-i183-probe2-scratch/`.
- The `Seats: restart not required` claim — verified by running the operator
  diff, not assumed.

## Notes

No BLOCK condition: no field, signature, or JSON shape was invented, and no
doc claim is unverifiable from the cited evidence.
