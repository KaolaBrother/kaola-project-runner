# Finalization Summary — issue-329

## Delivered

Antigravity worker `antigravity-KPR-i329-quota-usage` (antigravity/default) verified and exposed
real antigravity account usage data, scoped exactly as the issue body (not widened). Commits:
`de2c1ce1` (worker) + `5c41e221` (Host repair) on `workflow/issue-329` (base = main `2d818dd5`).

1. **Discovery (live)**: `agy -p /usage --output-format json` (alias `/quota`, one-shot print
   mode, 0 turns, 0 tokens, no `~/.gemini` write) returns `command.data.groups` — `Gemini
   Models` (gemini-weekly, gemini-5h) and third-party model families (3p-weekly, 3p-5h) — each
   with `remaining_fraction` ∈ [0,1] and RFC3339 `reset_time`.
2. **Live evidence, BOTH tiers** (isolated `i329-`-prefixed sessions, all stopped): default
   (`gemini-4-argon-medium`, PONG-DEFAULT) and xhigh (`gemini-4-argon-high`, PONG-XHIGH) real
   start/send/stop receipts; `kaola-quota.py --probe` live runs on both models returned
   `antigravity:account` with real numbers (weekly used 5.87%, 5h used 7.55%, reset times).
3. **Standard contract** (`scripts/kaola-quota.py`, +418 lines): parse + probe + CLI for
   antigravity usage, same shape as other runtimes (used/limit/used_percent/
   remaining_percent/remaining_fraction/reset_at/window). An unsigned account gets immediate
   SIGINT on the OAuth stderr prompt and `status: login_required` (no 60 s block).
4. **Manifest verified**: `platforms/antigravity.yaml` `quota_packages` windows `[5h, weekly]`,
   `acp_verified_versions: cli=1.3.5;protocol=1;condition=live-one-turn-two-turn-resume-steer-cancel-usage`;
   quirks document the `/usage` facts (Host reworded "Claude and GPT models" to "third-party
   model families" — the original wording leaked the claude-code platform token into the
   rendered `references/acp.md` and failed `test-generated-skills`).
5. **Tests**: `mock-agy.py` models `/usage` and `/quota` (ok, inner-json, unsigned,
   unsigned-oauth-wait, ineligible); coverage in the 148-quota, 323, and 331 suites for both
   tiers, third-party models, and login states; docs/README/CHANGELOG (`Seats: restart
   required`) and renders updated.

## Candidate

Branch `workflow/issue-329`, `de2c1ce1` + `5c41e221` over main `2d818dd5`.
Recorder-bound hash: `da7dbc407277d2e9…`.

## Evidence

- Worker focused runs: 148 (15) + 323 (58) + 331 + progressive-disclosure all green; render
  PASS.
- Host runs on the repaired final candidate: **full inventory rc=0** (1267 s; first run's only
  failure was the leak test, fixed by `5c41e221` and PASS since); `render-skills.py --check`
  PASS; suites 323 OK and generated-skills PASS standalone.
- `test-issue-148`'s `opencode-go` KeyError standalone failure is pre-existing (fails
  identically on unmodified main) and passed inside the full run.
- Validation record: `kaola-workflow/issue-329/.cache/final-validation.md` (verdict pass).

## Known failures and unverified scope

- Downstream KT usage-page consumption (KaolaTerminal #672) must align to this verified
  contract in its own repository; not verified here.
- Scope kept to antigravity per the Delegator directive; zcode/Grok exhaustion handling was
  not touched.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- README.md
- docs/api.md
- platforms/antigravity.yaml
- scripts/kaola-quota.py
- skills/antigravity-kaola-project-runner/references/acp.md
- skills/antigravity-kaola-project-runner/scripts/kaola-quota.py
- skills/antigravity-kaola-project-runner/scripts/platform.yaml
- skills/claude-code-kaola-project-runner/scripts/kaola-quota.py
- skills/codex-kaola-project-runner/scripts/kaola-quota.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-quota.py
- skills/devin-kaola-project-runner/scripts/kaola-quota.py
- skills/droid-kaola-project-runner/scripts/kaola-quota.py
- skills/dsh-kaola-project-runner/scripts/kaola-quota.py
- skills/grok-kaola-project-runner/scripts/kaola-quota.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-quota.py
- skills/opencode-kaola-project-runner/scripts/kaola-quota.py
- skills/zcode-kaola-project-runner/scripts/kaola-quota.py
- tests/contract/mock-agy.py
- tests/contract/test-issue-148-quota-packages.py
- tests/contract/test-issue-323-antigravity-acp.py

## Follow-Up Items

- None filed (no new KPR issues without owner direction).

## Final readiness

Ready: candidate accepted (live two-tier evidence + full inventory rc=0 on the final
candidate), validation recorded pass, no tag/release/install performed.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-329/.cache/final-validation.md
- kaola-workflow/archive/issue-329/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-329/finalization-summary.md
- kaola-workflow/archive/issue-329/mission-ledger.jsonl
- kaola-workflow/archive/issue-329/workflow-state.md
