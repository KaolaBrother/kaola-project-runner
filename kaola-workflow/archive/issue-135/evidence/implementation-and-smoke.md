# Issue #135 — implementation + acceptance smoke (impl run)

Candidate: `workflow/issue-135` @ `08eea7c` (847ca90 impl + 08eea7c pin/quirk fix), base main `d2d2953`.
Delivery per Owner correction issuecomment-5773251004: no PR; Workflow sink-merge close-out after Host acceptance.

## Gates
- `./scripts/render-skills.py --write` then `--check`: PASS (budgets OK).
- `./scripts/validate.sh` (foreground) on 847ca90: exit 1 (`validate-847ca90.log`) — four exact
  `effective_selection` dict pins (test-issue-119 x2, test-issue-130 x2) lacked the new `effort_config_id`
  key, and the design's quirk text named grok/claude tokens (test-generated-skills leakage check).
  Fixed in 08eea7c (pins extended; quirk made model-neutral). On 08eea7c: exit 0 (`validate-08eea7c.log`).
- `git diff --check d2d2953 08eea7c`: clean.

## Live smoke (design §9) — cursor-agent 2026.09.18-9a7762b, candidate installed (copy) into ~/.agents/skills
| file | sha256 |
|---|---|
| smoke-default.json | bfc8c4e6beed8722948a8a4ee9dbcf91ec858073696938917cc97452adfe013b |
| smoke-default-stop.json | db70a7257316e68bb71657aae482b02bb9bb8cc2052b44da03f5fabaae974663 |
| smoke-upgrade.json | d1ac110105f1a7d0d1bb9c5383b38177773ce87892a8d5853f2fc9a5de437876 |
| smoke-upgrade-stop.json | 1c4ad3685bdc68cebdd9a0992cfc233d3bb082c9ad0eaa050134e8d7a212613c |
| smoke-cli-version.txt | 228f6305ccdf2396f74331ad489bc10d2a39ea66772250bd34e95f8a5fedafab |

Default tier — PASS: model `{applied:true, value:grok-4.7, requested_id:grok-4.7-xhigh, mapped:true}`;
effort `{applied:true, config_id:reasoning_effort, value:xhigh, advertised:true, candidates:[reasoning_effort,effort]}`;
configured_options `reasoning_effort` → value_name "Extra High"; fast `{applied:true, value:"false"}`, effective off;
effective_selection `{effective_model:grok-4.7, effective_effort:xhigh, effort_config_id:reasoning_effort}`; stop `stopped:true`, residual [].

Upgrade tier — PASS: model claude-fable-5-1 (mapped from claude-fable-5-1-high); effort `{applied:true, config_id:effort,
value:high, advertised:true}`, value_name "High"; effective_effort high, effort_config_id effort; stop `stopped:true`, residual [].
`pgrep -f i135-smoke` empty after both stops.

Deviations from the §9 text (facts, not failures of this change):
- `transport.cli_version` is `null` in both receipts: Cursor's `agentInfo` is empty (manifest quirk), identical at v0.5.7
  (probe-1). The CLI version is recorded separately in `smoke-cli-version.txt` (`cursor-agent --version`).
- Upgrade tier `fast` apply is rejected (`Unknown model config option: fast`): Claude Fable 5.1 advertises no fast option
  (probe-9). Pre-existing, reported as a limitation receipt (`fast.effective` unknown); fast was out of scope (§5.2).
