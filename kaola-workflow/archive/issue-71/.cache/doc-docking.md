# Documentation docking — Issue #71

Candidate: `c19cdde4113792bfd8ac68881c740dd1d37296f8`
Status: **DOCKED**
No additional production documentation was written at finalize. Docking landed in the accepted
candidate. This file only records the checklist.

## Checked files

| File | Verdict | Reason |
|---|---|---|
| `CHANGELOG.md` | docked in candidate | Unreleased bullet: equal-length #49 probe, `main_skill_bytes` 17408 remains the ceiling, budget not raised. |
| `docs/architecture.md` | docked in candidate | Host-adapter paragraph now states the canonical half of `Issue49BridgeInvariance` uses equal-length substitutions and `templates/budgets.json` is the only ceiling. |
| `docs/conventions.md` | docked in candidate | Progressive-disclosure budgets bullet names the #49 host-invariance probe and that it does not reduce those numbers. |
| `docs/api.md` | no-impact | Already describes `--check` against `templates/budgets.json` and `budget: <surface> is N B > M B (<key>)`. The hidden 17349 ceiling was never documented here; after the fix that description is the whole truth. No API, flag, or renderer output shape changed. |
| `docs/grok-bot-host.md` | no-impact | Host adapter / pin-gate prose. Probe size side-effect was not a host contract. |
| `docs/README.md` | no-impact | Index only. |
| `README.md` | no-impact | Project overview; does not list byte budgets. |
| `AGENTS.md` | no-impact | Validation policy already names `render-skills.py --check` and `validate.sh`; budgets live in `templates/budgets.json`. |
| `docs/zcode-host.md`, dated live-smoke / decision notes | no-impact | Unrelated surfaces. |
| Setup / install / environment | no-impact | No installer, pin, or runtime change. |

## Generated surfaces

`skills/` and `hosts/grok-bot/` were not edited. `./scripts/render-skills.py --check` at the
candidate reports `budgets OK`. `templates/budgets.json` numbers are unchanged.

DOCKED
