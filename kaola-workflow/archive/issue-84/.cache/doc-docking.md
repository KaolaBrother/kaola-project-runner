# Documentation docking — Issue #84

status: DOCKED
candidate: fef74d15afcdef3c3bd165abbc121ab3805141e1 (pre-docking); docked in the finalize commit
scope of changed public behavior: ZCode adapter native `sess_*` resume model/provider recovery,
resume failure reporting, and the model config-option round trip. No API signature, CLI flag,
env var, install step, or architecture change.

## Checked against the AGENTS.md documentation map

| File | Verdict | Reason |
| --- | --- | --- |
| `CHANGELOG.md` | FIXED | Issue #84 entry under Unreleased: the five measured 3.12 wire defects, what is now read and re-registered, the explicit non-substitution guarantee, the narrowed pre-3.12 retry, the config-option round trip, and the live 3.12.3 verification incl. the failing pre-fix A/B. Kept alongside the Issue #74 block on rebase. |
| `docs/zcode-host.md` | FIXED | New "Resuming a native session's model (3.12+)" subsection, transcribed from the measured wire: both real transcript shapes, newest-by-`info.time.created`, the empty-registry re-registration through `provider/updateAccountConfig` + `account:*` `session/setModel`, no `runtimeModel` on that path, fail-closed with no substitution, `-32004 Session not found`, the `Model config is missing` condition on the legacy retry, and the account-qualified `currentValue` round trip. |
| `docs/api.md` | NO IMPACT (verified, not assumed) | Its resume paragraph (`--resume <native-session-id>` … "unsupported resume never blocks a fresh `start`") and its `resume-preserved` selection sentence were already written as the intended contract; this change makes them true on 3.12+ rather than altering them. Its ZCode three-identity paragraph and `configOptions` paragraph remain accurate: identity emission and option-refresh semantics are unchanged. |
| `platforms/zcode.yaml` | NO IMPACT (verified) | `acp_quirks` already states 3.12+ registers via `provider/updateAccountConfig` plus `session/setModel` on the `account:*` provider, and that a pre-3.12 app-server keeps the `runtimeModel` overlay on create/resume/setModel. Both remain true; the fix makes the 3.12+ description apply to resume as well. Editing it would also re-render every worker Skill for no factual gain. |
| `README.md` | NO IMPACT | Describes the four-tier entry and per-platform launch requirements; states no ZCode resume model semantics. |
| `docs/` (other) | NO IMPACT | No other file asserts ZCode resume model/provider behavior (`grep` over `docs/` for resume/setModel/provider). |
| Install / setup / env | NO IMPACT | No new dependency, flag, or environment variable; `KAOLA_ZCODE_ENTRY`/`KAOLA_ZCODE_NODE` unchanged. |
| Examples | NO IMPACT | No example encodes resume model behavior. |

## Transcription discipline

Every fact written into `docs/zcode-host.md` is transcribed from this run's own receipts —
`kaola-workflow/issue-84/evidence/live-frozen3/` (real ZCode.app 3.12.3, adapter
`6dc12633ddb6e157`) and the archived Issue #69 probe receipts — or from the adapter source at the
accepted SHA. No field, method, or error code was invented: `-32004 Session not found`,
`Model config is missing`, `info.time.created`, `info.model`, `info.modelId`/`info.providerId`,
`provider/updateAccountConfig` and `account:*` all appear verbatim in the receipts or the code.
