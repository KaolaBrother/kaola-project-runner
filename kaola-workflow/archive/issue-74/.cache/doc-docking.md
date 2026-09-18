# Documentation Docking — issue-74

verdict: DOCKED

Changed public behavior: Kaola-Delegator (`kaola-delegator`) is the external
delegation Skill; Grok Bot is no longer a Project Runner host. Project Runner
entries are Codex, generic, and ZCode. Recover a live Host from canonical repo
+ standard Runner name + status/receipts (no pointer file). Exact stop uses
`--expected-holder-instance-id`. Native resume after stop is
backend-dependent. Installer `--platform` still filters workers; an already
installed Delegator is updated/removed on a filtered Codex/generic
reinstall/uninstall. `external_skill_bytes` 4096; existing ceilings unchanged
(`main_skill_bytes` 17408, `reference_bytes` 8192, `bridge_bytes` 2560).
Generated sizes on accepted `eb9585208d40da0c9f21add3596278833b0ba3bb`:
Skill 3824/4096, handoff 8189/8192, bridge 2536/2560, Project Runner 16494/17408.
Grok Bot live UAT is unexecuted and not claimed. This issue does not publish a
release, install globally, or rewrite the account Skill.

Checked files (no product mutation of accepted `eb9585208d40da0c9f21add3596278833b0ba3bb`):

- `README.md` — four-tier table, A→B recover, Grok Bot UAT not run, installer
  filtered Delegator contract. Status "in development on this candidate" / not
  a released install remains true: no release tag. No further edit.
- `AGENTS.md` — managed snapshot names `hosts/grok-bot/kaola-delegator.md` and
  the two-layer matrix; layered entry restates recover/stop/UAT. Matches.
- `CHANGELOG.md` — Unreleased entries cover Delegator, recover, first-beat
  check, holder-bound stop, backend-dependent resume, installer stale
  Delegator. Matches.
- `docs/README.md` — index points at the four-tier / Delegator docs. Matches.
- `docs/conventions.md` — Kaola-Delegator template/render path and Grok Bot
  bridge loading `skills/kaola-delegator`. Matches.
- `docs/architecture.md` — generated `skills/kaola-delegator/` and
  `hosts/grok-bot/kaola-delegator.md`; Grok Bot is a bridge host for
  Kaola-Delegator. Matches.
- `docs/api.md` — renderer emits Delegator Skill and Grok Bot bridge
  `kaola-delegator.md`. Matches.
- `docs/grok-bot-host.md` — account Skill is the Delegator bridge; loads
  `ROOT/skills/kaola-delegator/SKILL.md`. Matches. INSTALL remains
  account-side and is not executed this run.
- `docs/zcode-host.md` — Host vs worker platform; unchanged Host semantics.
  No impact beyond existing ZCode Host facts.
- `hosts/grok-bot/INSTALL.md` — generated; two-commit pin model unchanged;
  entry is `kaola-delegator`. Not executed.
- `templates/grok-golden/` — frozen, not edited.

## Issue statement walk

Original body named **Zcode Orchestrator** / `zcode-orchestrator`. Later
comments and the delivered product use **Kaola-Delegator** / `kaola-delegator`.
That correction is posted on the issue before close; it is not a follow-up.

1. Two-layer names and entry matrix; no inner per-worker leakage — README
   four-tier table, AGENTS layered entry, `test_generated_entry_matrix_and_no_engine_leak`.
2. Isolated real path (task/quota → Delegator → ZCode Host → Project Runner →
   allowed worker → `end_turn` → event wake → B attach → exact stop) —
   `kaola-workflow/issue-74/evidence/live-ab-44a17b9/` (authentic ZCode 3.12.3;
   token `KAOLA74-AB-TOKEN`; B same holder/`acp_session_id`; `residual_pids=[]`).
   Outer independently reviewed that raw evidence.
3. Recover without a second Host; missing authorization does not expand —
   recover from repo + standard name + status; adopt-nonstandard test;
   missing-token-quota non-start independently measured on a fresh Agent
   (Issue comment 5734458075; Host `zcode-I74S-orchestrator-main` stayed
   `no-session`). External Skill does not copy a Mission List or run the
   inner heartbeat.
4. Grok Bot routing and device boundary — `docs/grok-bot-host.md`, locator
   attestation tests, generated bridge 2536 B. Criterion 4 allows missing
   live Bot access: **Grok Bot account UAT remains unexecuted, not claimed**
   (user-owned acceptance exception). No follow-up filed unless asked.
5. Nine workers + standalone; `#70/#72/#73` semantics kept; budgets not
   raised; generated files renderer-owned — installer runtime tests,
   `templates/grok-golden/` frozen, `external_skill_bytes` 4096, no new
   canonical-root mechanism (#73 stays its own issue, already closed).
6. `render --check`, full `validate.sh`, isolation install checks — this
   finalize run on exact accepted bytes: RENDER:0, VALIDATE:0, 151 issue-74
   assertions, `kaola-grok-bot-verify: PASS`. Outer ACCEPT then this
   finalize/archive/sink/close/audit/cleanup.

Product boundary honored: no global install, no account Skill rewrite, no
release tag.

Evidence: `kaola-workflow/issue-74/evidence/live-ab-44a17b9/`,
`validate-quota-figures/`, `finalize-eb95852/`, outer comment
https://github.com/KaolaBrother/kaola-project-runner/issues/74#issuecomment-5734458075
