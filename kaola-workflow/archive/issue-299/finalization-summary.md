# Finalization summary — issue-299

## Delivered

Fix for #299 plus the owner addendum (2026-10-09 21:57, issue comment
6082387407): the Delegator (Grok Bot) is woken by a holder-emitted webhook
signal on every Host stop path, with death recovery — no stop path ends
silently.

- `scripts/kaola-acp-holder.py` (`_delegator_wake`): signal-only payload
  `kaola-delegator-wake/1` {schema, project, session, holder_instance_id,
  event_seq, state, state_detail, ts} handed to a DETACHED
  `kaola-acp.py delegator-webhook deliver` child over stdin — the holder
  never touches the network, delivery can survive holder exit, a spawn
  failure is one event-log line. Triggers: permission_required →
  `blocked`; turn end → `end_turn` with `state_detail` carrying the
  verbatim ACP stopReason (clean token only, else `other`; `cancelled`
  stays distinct; a cancel under a requested stop is covered by the
  stop's own wake); turn_failed → `error`; unrequested agent exit and
  boot failure → `error`; exact stop → `stopped` (inline spawn so the
  child holds the payload before exit).
- Death recovery (`recover_host_death_wake` in `scripts/kaola-acp.py`):
  exactly-once `error`/`state_detail: holder_lost` wake for a dead Host
  holder that never signalled, emitted from `command_start` (dead or
  pid-reused record) and the dead-holder `stop` paths; deduplicated by a
  `delegator_death_wake` event under a record-dir flock; clean stops
  (which write their own `stopped` wake first) and non-host records are
  excluded.
- `kaola-acp.py delegator-webhook configure / status / test / remove /
  deliver`: per-machine `~/.config/kaola/delegator-webhook.json` (0600,
  atomic, flock across read-modify-write), keyed by project root with
  `owner_agent`; multi-project isolation; `remove` cleans only its own
  entry; URL/key from stdin or a 0600 file (never argv; no-echo
  interactive fallback); receipts JSON with the key redacted; sender-key
  attachment is configured data (`{"style":"header","name",...}` or
  `{"style":"url"}`), never a hard-coded header; bounded retries (≤3,
  backoff, redirects refused); per-attempt receipts
  (delivered/failed-with-status/skipped: not-configured) in a bounded
  ring under the project's `.kaola/`, never containing the URL or key;
  `deliver` validates the signal-only payload shape.
- Skill text through the template sources
  (`templates/kaola-delegator/SKILL.md.tmpl`,
  `references/webhook-wake.md`, `references/snapshot.md`): the owner's
  8-step agent self-configuration procedure with the owner-verified
  facts applied — one webhook routine plus at most one cron fallback
  routine as the single Delegator timer (webhook+cron cannot be grouped),
  URL/key via Grok Bot masked secret input arriving as env vars,
  configure via stdin/0600 file, test + confirm own routine woke,
  per-agent/per-project entries, rotate/remove, heartbeat-only fallback
  with the exact blocker on decline/failure; "payload is not evidence"
  and dedupe on holder_instance_id + event_seq stated; `wake_mode:
  webhook+heartbeat` record key wired through the delegator tooling.
  The grok-bot bridge renders from the same templates (byte budget held
  at 4086/4096 with neutral rewordings).
- `docs/api.md` (+104 lines) and CHANGELOG (holder changed → Seats:
  restart required).
- Tests: `tests/contract/test-issue-299-delegator-webhook.py` (20 cases,
  866+ lines) against a local mock HTTP endpoint — one receipt per turn
  end, skipped when unconfigured, dead/slow endpoint never blocks the
  holder, no URL/key in any receipt/log/argv (secret-leak scans),
  multi-project isolation + concurrent configure, 0600 modes, header and
  URL attachment forms, retry/redirect policy, non-signal payload
  refusal, receipt-ring bound, blocked/stopped wakes, SIGKILL recovery
  on next start and on dead-holder stop, non-host/clean-stop exclusion,
  stop_reason detail carried, wake_mode accept/refuse.

## Repair round (recorded honestly)

Host review round 1 accepted the original assignment and found exactly
one addendum gap — no death-recovery mechanism or SIGKILL test — which
was returned to the same seat; round 2 verified the repaired delivery
(`a1eaa034`, `bdb3b1a4`).

## Candidate

- Commits `97cf5277`, `c29292df`, `db5ab087`, `a1eaa034`, `bdb3b1a4` on
  `workflow/issue-299` (worktree `.kw/worktrees/issue-299`, base
  `06632a44`). Implemented by the `devin/opus-fusion` seat
  `devin-KPR-i299-webhook`; reviewed and finalized by the Host.

## Evidence

- Host diff review (two rounds; see ledger m2).
- `./scripts/render-skills.py --check` — PASS (bridge budget 4086/4096).
- Affected suites, all exit 0: `test-issue-299-delegator-webhook.py`
  (new), `test-issue-273-list-identity.py`,
  `test-issue-289-dead-holder-stop.py`,
  `test-issue-255-lifecycle-state.py`, `test-issue-271-dispatch-help.py`,
  `test-ddd-pack.py`, `test-issue-292-state-record-root.py`,
  `test-issue-130-pty-retired.py` (logs `/tmp/kpr-i299-*.log`).
- `.cache/final-validation.md`: verdict `pass`, candidate hash
  `4f3cd9eaa693e18a…`.
- Worker seat exact-stopped after acceptance (`state: stopped`).

## Known failures / unverified scope

- No live Grok Bot routine was created or called (owner boundary); the
  mechanism is verified against local mock endpoints only. Real-endpoint
  behavior, including the exact sender-key attachment format, is taken
  from the routine panel as configured data at adoption time.
- The full inventory runs immediately after this merge as the run's
  final gate; affected suites re-run on the published tree after the
  rebase.

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
- scripts/kaola-record-contract.py
- scripts/validate.sh
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-record-contract.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-record-contract.py
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-record-contract.py
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-record-contract.py
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-record-contract.py
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-record-contract.py
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-record-contract.py
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-delegator/SKILL.md
- skills/kaola-delegator/references/snapshot.md
- skills/kaola-delegator/references/webhook-wake.md
- skills/kaola-project-runner/scripts/kaola-record-contract.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-record-contract.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-record-contract.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-record-contract.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/kaola-delegator/SKILL.md.tmpl
- templates/kaola-delegator/references/snapshot.md
- templates/kaola-delegator/references/webhook-wake.md
- tests/contract/mock-acp-agent.py
- tests/contract/test-issue-299-delegator-webhook.py

## Follow-Up Items

- None. This run's boundary is merge + full suite green; release and
  installs need separate owner approval.

## Final readiness

Ready: candidate reviewed (two rounds), affected scope green, validation
recorded. Proceed to sink (merge) and archive.
