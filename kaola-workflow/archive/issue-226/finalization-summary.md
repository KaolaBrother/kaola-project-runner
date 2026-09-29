# Finalization Summary — issue #226

## Delivered

Paired pin of `@openai/codex` 0.158.0 and `@agentclientprotocol/codex-acp` 2.0.0,
with the Codex mode records rewritten to the 2.0.0 access presets. The live
evidence is startup, configuration, and one round trip on an isolated
gpt-6-luna seat, plus the adapter's `AgentMode` source. It is not an exhaustive
live tool-call or sandbox-write test.

`platforms/codex.yaml` now pins
`npx --yes --package @openai/codex@0.158.0 --package @agentclientprotocol/codex-acp@2.0.0 codex-acp`,
`acp_verified_versions` `cli=0.158.0;adapter=2.0.0;protocol=1`, and
`acp_wrapper_pin` `2.0.0`. `acp_quirks` and `permission_summary` record
`read-only` as the upstream Read-only sandbox (a write needs client approval),
`workspace-write` as Workspace access, `agent` as Auto review, and
`agent-full-access` as Full access. The same facts are in `docs/api.md` and
the README permission note. The Codex Skill surfaces were regenerated.
`accepted-revision.json` returns to the content stage per the post-pin flow.
No new release, tag, or install. The published v0.6.9 tag and release are
untouched.

## Candidate

`workflow/issue-226` at `8737b093fee52c06f3bd79b39590c0f4d401e4ba`.
Owner (Delegator) targeted review of this commit: PASS. No further approval
was required.

## Evidence

- `kaola-workflow/.ledger/issue-226.jsonl`: three missions done.
- Isolated pair at `/tmp/kaola-issue-226-npm`: `@openai/codex` 0.158.0 and
  `@agentclientprotocol/codex-acp` 2.0.0. The seat's app-server was that
  prefix's vendor binary (`codex-cli 0.158.0`). No global install was changed.
- Session `codex-kpr-i226-pair` on `/private/tmp/kaola-issue-226-seat`, record
  root `/tmp/kaola-issue-226-acp-records`. Start `--tier luna
  --permission-mode read-only`: `state=ready`,
  `acp_session_id=01a0eae0-fe56-7093-b784-0712ed7f2fce`, applied
  `gpt-6-luna` / effort `max` / fast `off` / mode `read-only` (display name
  Read-only). `agent_info` version `2.0.0`.
- Send: `turn_completed`, `stop_reason=end_turn`, `final_text=LUNA_PAIR_OK`,
  tool calls 0, files changed 0. Stop: `residual_pids: []`.
- Receipts: `/tmp/kaola-issue-226-start.json`, `send.json`, `observe.json`,
  `capture.json`, `stop.json`.
- Mode catalog on the live `configOptions` matches `AgentMode.ts` at tag
  `v2.0.0` (#480). #530's breaking tool-call contract is AIR-only
  (`_meta.jetbrains.air`); this client did not declare it.
- `kaola-workflow/issue-226/.cache/final-validation.md`: `verdict: pass`,
  command `./scripts/validate.sh`,
  `validated_candidate_hash: b10e064166219dc7ad65a4a157c9a7fd1685a58277a8ee175bc9ff6975f4cc60`.
  That command completed exit 0 on these bytes before the commit (about 629 s;
  no FAILED or Traceback; `render-skills.py --check` inside it PASS).
- `kaola-workflow-run-chains.js --project issue-226`: `chains_config_missing`
  (no `package.json` `test:kaola-workflow:*` scripts). Consumer gate is the
  recorded final-validation file.

## Known failures / unverified scope

- Not an exhaustive live tool or sandbox test. The round trip made zero tool
  calls, so the #530 diff/tool-call path was not exercised live. Read-only
  write blocking was not probed with a rejected or approved write; the sandbox
  semantics are the applied config option plus the 2.0.0 `AgentMode` source.
- `session/new` `modes.currentModeId` stayed `agent` after the Runner set the
  `mode` config option to `read-only`. The turn sandbox follows that config
  option. `session/set_mode` was not called.
- No install (`install-local.sh` not authorized). v0.6.9 tag and GitHub
  release were not edited.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- README.md
- docs/api.md
- hosts/grok-bot/INSTALL.md
- hosts/grok-bot/bridge.json
- hosts/grok-bot/kaola-delegator.md
- platforms/codex.yaml
- skills/codex-kaola-project-runner/SKILL.md
- skills/codex-kaola-project-runner/references/acp.md
- skills/codex-kaola-project-runner/scripts/platform.yaml
- templates/grok-bot/accepted-revision.json
- tests/contract/mock-acp-agent.py
- tests/contract/test-acp-holder-continue.py
- tests/contract/test-issue-22-bypass-all-approvals.py
- tests/contract/test-runner-v2.py

## Follow-Up Items

None filed. No run-discovered defect. The issue body asked for a Studio seat;
the owner-directed isolated luna seat is the accepted verification, recorded
on the issue before close.

## Final readiness

Ready: owner targeted review PASS on `8737b093`; merge sink, close #226, archive.

## Finalize Findings

### residue_unattributed

The residue mirror did not copy the paths below out of the main checkout: this run's HEAD does not contain them. Presence in main, an untracked status, or a neighboring file this run committed is not evidence they belong to this run. Nothing was copied, staged, committed, deleted, reverted or relocated — they remain in the main checkout. Read them before the sink runs: commit what belongs to the run, leave what does not.

Paths left in the main checkout:

- docs/harness-acp-compat-2026-09-25.md
- docs/harness-acp-compat-2026-09-26.md
- docs/harness-acp-compat-2026-09-29.md

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-226/.cache/final-validation.md
- kaola-workflow/archive/issue-226/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-226/finalization-summary.md
- kaola-workflow/archive/issue-226/mission-ledger.jsonl
- kaola-workflow/archive/issue-226/workflow-state.md
