# Doc docking — issue-178

Candidate: `4c1a63d` on `workflow/issue-178` (rebased onto `3455e4f`; originally
reviewed as `5041a6e` on base `0c3d200`). Change: removal of the transport
seat-stale send/steer gate — `refuse_if_stale` and its send/steer call sites
deleted from `scripts/kaola-acp.py`, `--confirm-stale` deleted from
`scripts/kaola-acp.py` argparse and `scripts/kaola-tmux.sh` (init, case arm,
send/steer-only check, pass-through), the flag mechanics reworded in the
orchestrator templates (policy kept), the gate sentences removed from
`templates/references/acp.md.tmpl` and `docs/api.md`, gate tests replaced with
stale-seat transport evidence in `tests/contract/test-issue-162-upgrade-safety.py`,
the drift enumeration re-asserted against `seat_freshness` in
`tests/contract/test-issue-168-drift-enumeration.py`, plus the rendered copies
(`skills/**`, `hosts/` unchanged) and the CHANGELOG entry.

## Checked

- `AGENTS.md` — documentation map and constraints. Generated-surface rule
  followed: `skills/` re-rendered via `./scripts/render-skills.py --write`
  after the rebase, verified byte-identical by `--check` (PASS, budgets OK);
  never hand-edited. The Project-Specific Runner Contract ("Refuse only
  objective transport impossibility or ambiguous/foreign target identity. A
  new classifier that blocks previously working automation is regression
  evidence; remove the restriction instead of adding another gate") is the
  rule this change implements; no edit needed.
- `CHANGELOG.md` — `## Unreleased` carries the #178 entry. It states
  **`Seats: restart not required.`** Verified against the operator test
  myself: `git diff 3455e4f 4c1a63d -- scripts/kaola-acp-holder.py scripts/kaola-zcode-acp.py scripts/adapters platforms`
  is empty — only per-call CLI files (`kaola-acp.py`, `kaola-tmux.sh`),
  templates, docs, and tests changed, which is exactly the restart-not-required
  case per `docs/conventions.md` and the AGENTS.md release rule.
- `docs/conventions.md` — the Seats-line rule was read and applied; the entry
  names the operator test and its empty result explicitly. The
  evidence-never-gate principles (lines 96/103/124) are unchanged and now
  match the code.
- `docs/api.md` — updated: the `send`/`steer` refuse `seat-stale` sentences are
  removed from the #162 status paragraph; `stale`, `stale_reasons`,
  `restart_files`, and `reported_drift` remain documented as `status`/`list`
  facts. No other paragraph describes the gate.
- `templates/references/acp.md.tmpl` (rendered into all ten workers'
  `references/acp.md`) — updated: the worker command-surface doc no longer
  describes a send/steer gate.
- `templates/orchestrator/SKILL.md.tmpl` +
  `templates/orchestrator/references/zcode-host-dispatch.md.tmpl` (rendered
  into `skills/kaola-project-runner/`) — updated: "Do not dispatch a
  `stale: true` seat" and "replace it with `drain-restart` at idle" policy
  kept; the `--confirm-stale` mechanics became "an operator-confirmed
  exception on that one `send`/`steer` is the orchestrator's own call; there
  is no flag."
- `templates/kaola-delegator/references/handoff.md.tmpl` — unchanged by design
  and re-verified: the handoff command shape
  `"$ZCODE" send --repo "$PROJECT" --session "$HOST" --no-wait --text '<handoff>'`
  now delivers to a stale Host seat (contract test
  `test_delegator_handoff_shape_delivers_to_a_stale_host_seat`, exit 0,
  `outcome: in_progress`); the template needed no new flag or remedy text,
  which is the issue's acceptance 4.
- `README.md`, `docs/zcode-host.md`, `docs/architecture.md` — no gate, flag,
  or send/steer refusal statement (verified by token search over the tree:
  no `refuse_if_stale` / `seat-stale` / `--confirm-stale` / `confirm_stale`
  matches outside CHANGELOG history). No impact.
- Dated historical evidence docs and `kaola-workflow/archive/**` — history
  records that describe the pre-#178 gate; not rewritten.

Total changed paths outside run state: 51 (9 source/template/docs/tests +
42 rendered). Public-behavior doc surfaces updated: `docs/api.md`,
`templates/references/acp.md.tmpl`, `templates/orchestrator/SKILL.md.tmpl`,
`templates/orchestrator/references/zcode-host-dispatch.md.tmpl`, `CHANGELOG.md`.

## Not in scope

S2 (#179, `reported_drift` vocabulary), S3 (#180, start-decision site), and
S4 (#181, mode recording and `drain-restart` slimming) are the already-filed
follow-ups; no run-discovered defect beyond them was found. No new follow-up
to file.

## Verdict

DOCKED
