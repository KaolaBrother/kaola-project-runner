# Finalization Summary — issue-388

## Delivered

Only a `session_role: "host"` holder receives the Host heartbeat carrier. `scripts/kaola-acp.py`
computes the seat role before the holder argv and appends `--host-entry` only for a Host; every
worker, Expert and Sideagent start is entry-less. `scripts/kaola-acp-holder.py` keeps the second
guard at worker-event delivery: the carrier requires both a non-empty `host_entry` and
`session_role == "host"`, so a live holder armed with a legacy entry still receives only the
compact `kaola-worker-notify/1` event lines, never `/kaola-project-runner`, `kaola-host-notify/1`
or the heartbeat body. The holder parser's empty default makes an omitted flag mean entry-less
while a direct `Holder` construction without the attribute keeps the legacy ZCode fallback. The
Sideagent node's separate `kaola-sideagent-relay/1` batch prompt is unchanged.

`tests/contract/test-issue-388-role-carrier.py` adds 7 tests: dsh/devin worker and Expert payloads
with and without a legacy Host entry, the Host carrier control, the Sideagent node's own batch,
and real dsh/devin starts proving a non-Host holder argv has no `--host-entry` while a Host start
records and passes it. The existing #90 and #255 fixtures now declare the Host role they intend;
the ZCode heartbeat fixture uses standard Host names and keeps its second-Host conflict case in a
separate repo under the one-Host-per-repo rule. `docs/api.md` and `CHANGELOG.md` Unreleased carry
the rule and `Seats: restart required`; generated Skill copies were re-rendered.

## Candidate

Branch `workflow/issue-388` at `f46e1d4e` (`fix: gate the Host carrier on session_role (#388)`).
The branch was rebased onto current main `90b583cc` (which already carries #378 and #389); rebase
conflicts were limited to `CHANGELOG.md` and `docs/api.md` and both sides were kept, while
`scripts/kaola-acp-holder.py` auto-merged with the #378 cwd-notice changes. The merge is a
fast-forward of the accepted candidate. `git diff --check` is clean and
`./scripts/render-skills.py --check` is PASS. The Grok Bot bridge remains at the unpinned content
stage on main.

## Evidence

- Host acceptance in conversation of `f46e1d4e`: CLI passes `--host-entry` only for the host role;
  the holder's double role guard chooses the carrier only when the entry is non-empty and
  `session_role == "host"`; the 7 contract tests, two affected-suite batches, and render PASS were
  verified. The full Host carrier received by the old `dsh-KPR-i388-rolecarrier` worker holder is
  recorded as the live reproduction.
- Live reproduction event:
  `dsh/dsh-KPR-i388-rolecarrier/cwd_repaired/767`, `event_cursor: 767`, delivered as
  `kaola-host-notify/1` with the Host heartbeat body by the pre-fix holder. The seat must restart
  to load the guard; after restart the same event takes the worker-notice path.
- Final 16-suite affected batch on the frozen candidate, exit 0 (total wall 554.8 s):
  #388 role carrier, `test-acp-contract`, #119 host entry, #245 session role, #255 lifecycle state,
  #341 agent-initiated turn, #90 event confirmation, #369 holder cwd repair, #378 cwd notice
  delivery, devin regressions, #98 dsh acp, #340 devin argv model, #345 dsh commandcode,
  #65 host contract, zcode heartbeat contract, #264 lane integrity.
- Additional 8-suite platform parity batch, exit 0 (total wall 291.9 s): zcode acp contract,
  droid acp contract, #323 antigravity, #24 opencode no-skip-all, #50 claude acp bridge,
  #50 runner integration, #187 delegator-any-host, #94 zcode native skill entry.
- Freeze re-check on `f46e1d4e`: `./scripts/validate.sh --suite test-issue-388-role-carrier.py`
  exit 0 (7/7 tests, 13.4 s) and `./scripts/render-skills.py --check` PASS.
- Final validation record: `kaola-workflow/issue-388/.cache/final-validation.md`, verdict `pass`,
  validated candidate hash
  `0090525f28c106393e6c39a7994a3146d85390c8fe918b8e7cfeedbbca3699b2`.

## Known failures or unverified scope

- Validation is a diff-scoped subset (16 + 8 suites), not whole-inventory coverage.
- No real platform CLI live smoke was run; the contract tests use real holder processes with the
  mock ACP agent. The affected behaviour is role/argv selection, not a platform-specific adapter.
- `Seats: restart required`: `scripts/kaola-acp-holder.py` is in the operator restart set. A
  holder started before this change keeps the old carrier selection until it restarts; this
  finalize does not install, restart another Host, tag or release.
- The live old-holder reproduction remains a historical event; no new Host scheduler or state
  write was added for it.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/api.md
- scripts/kaola-acp-holder.py
- scripts/kaola-acp.py
- scripts/validate.sh
- skills/antigravity-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/antigravity-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- tests/contract/test-issue-255-lifecycle-state.py
- tests/contract/test-issue-388-role-carrier.py
- tests/contract/test-issue-90-event-confirmation-race.py
- tests/contract/test-zcode-heartbeat-contract.py

## Follow-Up Items

- None filed by this run. No new defect was discovered during finalization.

Readiness: accepted candidate, affected batches and freeze check green, ready to merge and archive.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-388/.cache/final-validation.md
- kaola-workflow/archive/issue-388/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-388/finalization-summary.md
- kaola-workflow/archive/issue-388/mission-ledger.jsonl
- kaola-workflow/archive/issue-388/workflow-state.md
