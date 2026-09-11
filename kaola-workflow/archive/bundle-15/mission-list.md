# Issue 15 — PoC: validate the Runner v2 ACP transport (Grok + Kimi) and measure the token drop

Issue: https://github.com/KaolaBrother/kaola-project-runner/issues/15
Spec: `docs/runner-v2-dual-transport-design.md` v0.2 (merged via PR #16), sections §3.3, §4, §5.3, §6, §7, §10.
Worktree: `.kw/worktrees/bundle-15`, branch `workflow/bundle-15`.
Scope: throwaway/prototype files only — `scripts/kaola-acp.py`, `scripts/kaola-acp-holder.py`,
`tests/contract/mock-acp-agent.py`, `tests/contract/test-acp-contract.py` (+ validate.sh hook per §9).
No manifest/template/installer changes; `templates/grok-golden/` frozen; `skills/` generated only.
Run evidence lands in `kaola-workflow/bundle-15/evidence/`; PoC report lands in the worktree under `docs/`.

## Missions

- item: Part A — author the offline contract suite: `tests/contract/mock-acp-agent.py` (scriptable
  mock ACP agent: delays, half-lines, non-JSON lines, stderr flood, crash, multiple concurrent
  permissions, `$/cancel_request`, protocolVersion rejection, unknown/unsupported outbound methods,
  numeric-string ids) and `tests/contract/test-acp-contract.py` covering every branch in design
  §7.3/§7.4/§7.6 per the issue Part A checklist (10 items); wire into `scripts/validate.sh`
  (offline, fast); record baseline FAIL before implementation exists.
  status: done
  dispatched: self (inline; session policy: no subagent dispatch)
  result: authored `tests/contract/mock-acp-agent.py` (12 scenarios) +
  `tests/contract/test-acp-contract.py` (12 tests covering all 10 checklist branches);
  wired into `scripts/validate.sh`; baseline FAIL = `missing ACP CLI` as expected.

- item: Part A — implement `scripts/kaola-acp.py` (CLI / socket client: preflight, start,
  send --wait, wait, observe, capture L0–L3, permit, key escape→cancel, cancel, stop [--force],
  status) and `scripts/kaola-acp-holder.py` (per-session holder per design §3.3/§7: spawn with
  start_new_session, NDJSON JSON-RPC reader thread, pending-permission map, five-state
  mutation_status, stop sequence §7.6, record dir §3.2) until the contract suite is green and
  `./scripts/validate.sh` + `./scripts/render-skills.py --check` stay green.
  status: todo
  dispatched: self (inline)
  result:

- item: Part B — Grok live (`grok agent stdio`, v1.0.25): run all 13 §10.1 scenarios, record real
  receipts incl. `configOptions` ids; evidence → `kaola-workflow/bundle-15/evidence/part-b-grok.md`.
  status: done
  dispatched: self (inline)
  result: evidence/part-b-grok.md — 11/13 PASS live; #2 permission NOT TRIGGERED
  (Grok always-approve auto-approves over ACP; permit path covered by Part A);
  #6 PRECONDITION-NOT-MET (already authenticated; login_required:false reported).
  configOptions ids captured: `model` (grok-4.6/4.5), `reasoning_effort`
  (xhigh/high/medium/low).

- item: Part B — Kimi live (`kimi acp`, v0.41.0): run all 13 §10.1 scenarios, record real receipts
  incl. `configOptions` ids; evidence → `kaola-workflow/bundle-15/evidence/part-b-kimi.md`.
  status: done
  dispatched: self (inline)
  result: evidence/part-b-kimi.md — 11/13 PASS live; #2 permission NOT TRIGGERED
  (default mode never emits request_permission in 0.41.0); #6
  PRECONDITION-NOT-MET (authenticated; login_required:false). configOptions:
  `model` (k3 current + 3 others), `thinking` (low/high/max), `mode`
  (default/plan/auto/yolo). Kimi emits usage_update; real agentInfo.

- item: Part C — token measurement: same task over acp and pty, ≥5 runs each, report medians
  (UTF-8 bytes + cl100k tokens handed to orchestrator, Runner command invocations, reasoning turns,
  wall time, recovery attempts + mutation_status accuracy); publish PoC report in worktree
  `docs/` and note the four-platform default-transport decision input.
  status: done
  dispatched: self (inline)
  result: docs/poc-acp-transport-2026-09-11.md + evidence/measure.py +
  part-c-raw.json. Medians over 5 runs: acp 2453 B / 791 cl100k / 3 invocations
  / 7.9 s vs pty 29982 B / 9313 cl100k / 6 invocations / 13.1 s → ~12× token
  drop, 2× fewer calls, 1.7× faster; task 5/5 both, 0 retries.
