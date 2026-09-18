# Doc Docking — bundle-85 (Issue #85)

Candidate: `workflow/bundle-85` (fix commit `70bfce0` + docs delta).
Public surface changed: the ZCode ACP adapter no longer emits
`config_option_update` on a native `sess_*` resume that fails closed;
successful resumes unchanged.

| Checked | Result |
| --- | --- |
| `docs/zcode-host.md` | FIXED — fail-closed resume paragraph gained one sentence: a dropped resume emits no `config_option_update`, so no refused model is ever advertised. |
| `CHANGELOG.md` | FIXED — `## Unreleased` entry added describing the ordering fix and unchanged fail-closed semantics. |
| `docs/api.md` | NO-IMPACT — §`config_option_update` semantics ("notifications refresh `session_meta.configOptions`; failed/absent updates leave last proven config untouched") remain accurate: a dropped session now has no update at all, which is strictly consistent. |
| `README.md` | NO-IMPACT — no command, flag, install, or usage change; the fix is adapter-internal emission timing on a failure path. |
| `docs/architecture.md` / `docs/conventions.md` | NO-IMPACT — resume responsibility split (Runner facts vs adapter transport) unchanged; no new state, gate, or layer introduced. |
| `templates/` + generated `skills/` | NO-IMPACT — the adapter mirror `skills/zcode-kaola-project-runner/scripts/kaola-zcode-acp.py` was regenerated via `render-skills.py --write` (byte-identical to `scripts/`); no Skill prose documents the emission ordering. |
| `hosts/grok-bot/` | NO-IMPACT — untouched; grok-bot verify PASS. |

Verdict: DOCKED
