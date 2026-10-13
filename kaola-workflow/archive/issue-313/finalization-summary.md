# Finalization summary — issue-313

## Delivered

Fix for #313: start and list stamp an advisory `issue_name` on
issue-named worker sessions; the exact platform id is the documented
requirement; a shared contract fixture defines the parser and join rule
for Kaola Terminal.

- `scripts/kaola-session-names.py` (new, 461 lines): parses
  `<platform>-<CODE>-i<ISSUE>-<purpose>` against the platform ids
  derived from `platforms/*.yaml` `session_prefix` values (no
  hand-listed ids); classifies a name (`ok`, `malformed`,
  `platform-token-mismatch`, plus non-worker roles via `name_role`);
  looks up whether an active `workflow-state.md` claim covers an issue
  number (skips archive/closed; from a worktree, reads the main
  checkout only).
- `scripts/kaola-acp.py`: `stamp_issue_name_receipt` — start receipts
  and list rows carry `issue_name` (one of the four closed values) for
  issue-named workers and `name_role` for host/sideagent/seat names
  (which omit `issue_name`). **Advisory only**: every value starts; the
  1-80 syntax validator is unchanged (negative test).
- `tests/contract/kaola-terminal-name-contract.json` (628 lines): the
  shared consumer fixture — schema, grammar, exact-platform-id rule
  with alias examples, the advisory field and its closed vocabulary,
  `advisory_blocks_start: false`, `name_role`, the join rule (name
  parses AND the repo's active run claims that issue number ⇒ bound),
  and 22 representative rows (including the live-repro shapes).
- Docs: `docs/conventions.md` (exact id required; advisory nature),
  `docs/issue-dispatch-display.md` (the fixture is the consumer
  contract), `docs/api.md` (receipt fields). CHANGELOG Unreleased
  entry (per-call CLI; no seat restart required).
- Tests: `test-issue-313-name-advisory.py` (9 cases): fixture states
  the closed vocabularies and join rule; every row matches the parser
  and join; platform ids come from `session_prefix`; claim reading
  skips archive/closed and reads the main checkout from a worktree;
  docs state the rules; validate registration (both groups); the
  syntax validator is unchanged; each advisory value still starts and
  list marks the row.

## Candidate

- Implementation commit `eba97400` on `workflow/issue-313` (worktree
  `.kw/worktrees/issue-313`, base `426e3c89`). Implemented by the
  `grok/default` seat `grok-KPR-i313-name-advisory`; reviewed and
  finalized by the Host.

## Evidence

- Host diff review (this run): closed vocabulary exactly the owner's;
  advisory-only proven; fixture self-describing; platform ids derived
  from manifests.
- `./scripts/render-skills.py --check` — PASS.
- Affected suites, all exit 0: `test-issue-313-name-advisory.py` (new),
  `test-issue-271-dispatch-help.py`, `test-issue-273-list-identity.py`,
  `test-issue-244-dispatch.py`, `test-progressive-disclosure.py`,
  `test-issue-299-delegator-webhook.py` (logs `/tmp/kpr-i313-*.log`).
- `.cache/final-validation.md`: verdict `pass`, candidate hash
  `4e38ec8d02f0b944…`.
- Worker seat exact-stopped after acceptance (`state: stopped`).

## Known failures / unverified scope

- #312 (drift check + template sentence) follows as its own run on this
  merged parser, per the owner's one-issue-one-run instruction. No
  release (owner releases #308-#313 together).

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/api.md
- docs/conventions.md
- docs/issue-dispatch-display.md
- scripts/kaola-acp.py
- scripts/kaola-session-names.py
- scripts/render-skills.py
- scripts/validate.sh
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-session-names.py
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-session-names.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-session-names.py
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-session-names.py
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-session-names.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-session-names.py
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-session-names.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-session-names.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-session-names.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-session-names.py
- tests/contract/kaola-terminal-name-contract.json
- tests/contract/test-issue-313-name-advisory.py

## Follow-Up Items

- None.

## Final readiness

Ready: candidate reviewed, affected scope green, validation recorded.
Proceed to sink (merge) and archive.
