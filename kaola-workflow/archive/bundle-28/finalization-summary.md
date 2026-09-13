# Finalization Summary — bundle-28 (issue #28)

Issue: https://github.com/KaolaBrother/kaola-project-runner/issues/28
## Final supervisor acceptance and closure

Final accepted candidate: `b5854f007891751485bc6b1fbd57542f8d6f9c76`.
PR #29 merged as `9a9a91da396eeb4f9d6a3f104ffdac7b4c981e8c`; issue #28 closed.
PR #31 then merged as `10f109bdbc7d622de8fe515fd8347cf0313bf4b3`.
Codex independently verified render/check, validate.sh, adapter contracts, actual
ACP two-turn memory, exact stop/resume with memory, PTY reply and exact stop.
Post-merge render/check and validate.sh also passed (exit 0). Evidence is in
`/Users/ylpromax5/Documents/Codex/runner-issue28-design/`.

Corrections to the initial record below: `820a228` fixed RFC3339 ordering,
missing timestamp handling and deduplication, and the real null-timeout cancel
crash (the earlier cosmetic-race attribution was wrong). The native ACP mode
`read-only` means workspace-write/on-request; this is documented and is distinct
from strict PTY read-only. Real permission requests and permit settlement were
subsequently verified. `b5854f0` fixed advisory native plugin discovery.
Authenticated Devin/Claude smoke limitations remain quota/expired-login facts,
not claims of all-platform authenticated PASS.

Both run archives are published. Exact bundle-28 and bundle-30 worktrees and
local/remote branches were removed after merged/pushed proof; main is synced.
No release was performed. Completed Mission List results remain unchanged.

## Initial PR handoff record (historical; superseded above)

Initial candidate: `workflow/bundle-28` @ `9923974`
Spec: frozen issue body (2026-09-13 rewrite); Codex supervisor owns review/validation.

## Delivered

- Codex CLI as the seventh platform, ACP-default via pinned
  `npx --yes --package @openai/codex@0.153.4 --package @agentclientprotocol/codex-acp@1.11.0 codex-acp`.
- Explicit `--transport pty` runs `codex --cd <repo> --no-alt-screen` with the
  specified sandbox/approval mappings; no automatic fallback between transports.
- Runner default model `gpt-5.6-luna` at `low` effort on both transports;
  explicit `--model`/`--effort` overrides win; no global Codex config written.
- ACP modes `read-only|agent|agent-full-access` via configId `mode`; PTY maps to
  `read-only`+`on-request`, `workspace-write`+`on-request`,
  `danger-full-access`+`never`. Unsupported permission values are refused.
- Shared holder fixes: capability objects including `{}` mean supported;
  `continue` follows `session/list` `nextCursor` over cwd-filtered pages and
  selects the factual latest `updatedAt`.
- Seventh generated Skill `codex-kaola-project-runner` rendered from the shared
  template; `templates/grok-golden/` untouched.
- `CODEX_PATH` selects the Codex binary for the adapter; bundled pinned Codex is
  the default. No credentials in receipts.

## Files Changed

- New: `platforms/codex.yaml`, `scripts/adapters/codex.sh`,
  `skills/codex-kaola-project-runner/` (generated),
  `tests/contract/test-acp-holder-continue.py`.
- Modified: `scripts/kaola-tmux.sh`, `kaola-acp.py`, `kaola-acp-holder.py`,
  `kaola-model-policy.py`, `install-local.sh`, `render-skills.py`;
  regenerated helper copies under `skills/*/scripts/`;
  contract test suites extended for codex + ACP-default staleness repaired;
  `README.md`, `docs/api.md`, `docs/architecture.md`, `docs/conventions.md`,
  `AGENTS.md`, `CHANGELOG.md`.
- 79 files, +7869/−247 in `9923974`.

## Test Coverage

- `./scripts/render-skills.py --check` — PASS (7 Skills).
- `./scripts/validate.sh` — PASS (all gated suites + 7 skill validators).
- `bash tests/test-issue-1-acceptance.sh` — PASS (full contract battery,
  incl. relay PTY/fence, guarded actions, installer, generated-skills,
  observation, model-policy, live-smoke adapters, grok compat/isolation).
- `tests/contract/test-acp-holder-continue.py` — 17 tests covering `{}`
  capabilities, nextCursor pagination, cwd filtering, out-of-order updatedAt,
  exact resume, indeterminate-latest refusal.
- Stale six/five-platform suites repaired: explicit `--transport pty` where
  they exercise fake tmux runtimes, schema v3 receipts, `transport` field,
  `relay-attestation-failed` refusal code, seven-platform inventories.

## Validation

- final-validation.md: verdict pass, command
  `./scripts/render-skills.py --check && ./scripts/validate.sh && bash tests/test-issue-1-acceptance.sh`,
  candidate hash bb365a37e0e57f160342fbfa55508bdc9147c598b747fad991f94c4c4ccc58e4.
- Live evidence (disposable `/tmp/kpr-i28-smoke/` repos):
  - Codex ACP: preflight (adapter 1.11.0, all caps incl. `{}` objects);
    start configured model/effort/mode; two real replies (ALPHA + recall);
    capture; stop → holder+agent absent; `--resume` reattached the same
    `acp_session_id` with post-stop history recall; `--continue` cwd-filtered
    to latest `updatedAt` across two repos; cancel → `turn_canceled`.
  - Codex PTY: start argv confirmed, trust via `key enter`, `tui_detected`,
    `model_verified` actual `gpt-5.6-luna`, send → `BRAVO`, stop → `absent`.
  - Existing platforms: grok/kimi-cli/cursor-cli/opencode full ACP cycles PASS;
    devin ACP transport OK, upstream `-32011` quota exhausted (unexecuted turn);
    claude-code PTY transport OK, upstream login expired (unexecuted turn).

## Changed Paths

`AGENTS.md`, `CHANGELOG.md`, `README.md`, `docs/{api,architecture,conventions}.md`,
`platforms/codex.yaml`, `scripts/adapters/codex.sh`, `scripts/install-local.sh`,
`scripts/kaola-acp-holder.py`, `scripts/kaola-acp.py`,
`scripts/kaola-model-policy.py`, `scripts/kaola-tmux.sh`,
`scripts/render-skills.py`, `skills/` (7 generated trees incl. new codex tree),
`tests/` (lib + contract suites + legacy grok test).

## Documentation Docking

`.cache/doc-docking.md` — DOCKED. All current-state platform enumerations moved
to seven; historical dated records preserved.

## Initial review findings (resolved or qualified above)

- FACTUAL FINDING: ACP `mode: read-only` was accepted (`configured: true`) but
  the codex-acp adapter still executed a file-write turn (`HELLO.txt` created).
  Upstream `read-only` does not sandbox tool calls the way PTY
  `--sandbox read-only` does. Runner sets/reports the mode faithfully; the
  semantic difference is adapter-side. Reported for supervisor decision —
  no Runner-side workaround added per spec.
- MINOR: `cancel` op receipt raced `holder-closed` while the cancel itself
  landed (`turn_canceled`, `stop_reason: cancelled`). Cosmetic socket-teardown
  artifact on the cancel reply path.
- devin/claude-code live turns unexecuted due to upstream quota/auth —
  transport proven, agent-side limits recorded honestly.

## Initial readiness (historical)

Candidate `9923974` on `workflow/bundle-28` is ready for independent Codex
supervisor validation via reviewable PR. No merge, issue closure, or release
performed by this run.
