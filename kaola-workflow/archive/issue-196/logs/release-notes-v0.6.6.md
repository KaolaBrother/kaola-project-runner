## 0.6.6 — 2026-09-27 (quota reset windows, Droid shared Skill root, Host QA and pacing, five-preset worker pool)

Seats: restart required

The operator test
`git diff v0.6.5 v0.6.6 -- scripts/kaola-acp-holder.py scripts/kaola-zcode-acp.py scripts/kaola-quota.py scripts/adapters platforms`
is not empty: it reports `scripts/kaola-quota.py` and all ten `platforms/*.yaml` (#192 adds
`windows` to every `quota_packages` row and a second Kimi package, and rewrites the catalog's
`windows` docstrings; #195 adds "Very low-cost" to the ZCode `default` profile).
`scripts/kaola-acp-holder.py`, `scripts/kaola-zcode-acp.py`, and `scripts/adapters/` are
byte-identical to v0.6.5. The note is `Seats: restart required` because the operator test is
non-empty and the holder pins the quota catalog at startup (#162): a seat started on v0.6.5 keeps
the old catalog and platform facts. Run `install-local.sh` for every runtime you use, then restart
seats: the main Skill and every worker's `kaola-quota.py` and `platform.yaml` changed, so every
worker's `main-skill-build.json` moves, a Host start from a stale install refuses
`main-skill-build-skew`, and any other platform's stale worker Skills refuse
`worker-skill-skew`. Droid users rerun `--runtime droid` to move to `~/.agents/skills` (#193).
`templates/grok-bot/accepted-revision.json` is back at the content stage for this release's
content commit; the pin commit that follows names the v0.6.6 tag.

- **Five worker presets are default-authorized under an authorized project task (Issue
  #195).** The Host may dispatch Claude Code `sonnet`, Codex `luna`, dsh `default`, Devin
  `default`, and ZCode `default` from the exact list in `references/worker-profiles.md`
  without per-seat, per-preset, or priority-order approval, and those seats neither consume
  nor are limited by the general worker concurrency cap. Every other runtime/preset still
  needs explicit authorization, prior grants stay valid, and actual quota/resource limits
  still apply; a runtime's `default` tier alone never qualifies. Reports show pool seats as
  live, exempt from `live N / authorized M` accounting. Operator-diff fact:
  `platforms/zcode.yaml` `default_model_profile` only.

- **Droid installs into the shared `~/.agents/skills` (Issue #193).** `--runtime droid`
  now joins `kimi-cli` and `dsh` in `$HOME/.agents/skills`, a documented Droid user root
  that Droid reads in the same bucket as `~/.factory/skills`, where same-name Skills are
  invalid. The same run withdraws only the `droid` reference from the retired
  `~/.factory/skills`: a copy only droid referred to is removed, a copy another runtime
  still refers to is kept with a duplicate-name warning, and a droid-only copy with edited
  bytes or a same-name directory without a receipt refuses the run before any write.
  Personal Skills are never touched; `--runtime droid --uninstall` withdraws from both
  roots. A pre-ledger receipt counts droid only in `~/.factory/skills`, where droid wrote
  it. Every other runtime keeps its current root, and the kimi-cli dual-root contract is
  unchanged. Existing installs move only when an operator reruns `--runtime droid`.

- **Host QA distinct from testing, evidenced redundancy, and adaptive verification
  cadence (Issue #194).** Testing executes checks; QA judges whether the product and its
  evidence satisfy the task and whether the verification work itself stays proportionate.
  The Host reuses sufficient recorded evidence by default and assigns a bounded,
  proportionate check when an in-scope user-facing outcome is undemonstrated, evidenced
  verification redundancy needs simplifying, or the user explicitly requests
  exploratory/user-flow/release QA — usually the original owner, not automatically a new
  seat: one short pointer in main-loop step 3 to the new `references/qa-evidence.md`
  (who, brief, return, reading a failure, redundancy/adaptive-cadence, compact
  CLI/UI/docs-only examples). Kaola-Delegator's existing follow-up cadence also compares
  outcomes, blockers, and repeated testing/QA against prior checks and relays one new
  pacing note when warranted, marking stall uncertainty; it still does not dispatch
  workers, copy the ledger, or re-run acceptance. No permanent QA seat,
  ledger, scoring table, or new scheduler.

- **Quota packages declare their reset windows (Issue #192).** `kaola-acp packages` no
  longer reports `windows: null` for every package: each row lists its confirmed reset
  windows from `5h`, `weekly`, and `monthly` (several may apply), `[]` means verified to
  have no time-based reset, and `null` remains only where the period is not established
  (Claude Code `extra_usage`, Devin `overage`, OpenCode `zen`). Weekly: Claude Code,
  Codex, Devin `max`, Grok; monthly: both Cursor packages; weekly + monthly: Droid `core`,
  dsh and OpenCode `opencode-go`; 5h + weekly + monthly: Droid `standard` (Factory's
  documented rolling windows); 5h: ZCode and OpenCode ZhipuAI coding plans; `[]`: Droid
  `extra_usage`. Kimi's two plans are told apart: `kimi-cli:managed` (weekly + monthly)
  and the new `kimi-cli:managed_monthly` (monthly only, `binds_models: false`, so model
  resolution is unchanged). The field names windows only, not amounts or reset times
  (`docs/api.md`); `references/quota-packages.md` adds the display rule (show weekly or
  monthly when a plan has one, 5h only when it has neither). Operator-diff fact: every
  `platforms/*.yaml` `quota_packages` and the `scripts/kaola-quota.py` docstrings; no
  catalog logic changed.
