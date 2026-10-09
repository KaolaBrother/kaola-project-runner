# Finalization summary — issue-297

## Delivered

Fix for #297: the Delegator seat view counts counted Worker-class grants as
seats, closing the remaining gap from #295.

- `scripts/kaola-dispatch.py`:
  - `seat_summary`: a Worker-class preset with a readable count (a Host
    grant `count`, or a counted Delegator `elite_grants` row admitted by
    `worker_pool`) becomes a seat group (class `Worker`, that count),
    counted in `authorized_total` and `idle_available_total`; occupancy
    rows cover Worker presets with only counted seats listed. Uncounted
    Worker presets stay in `worker_pool` only. The ceiling still applies:
    a blocked counted Worker grant shows `unavailable` with its reason;
    `above-ceiling`, `revoked`, or a missing `worker_pool` key omits it.
    Delegator-only counted Worker rows join via the extras pass without
    `host-grant-missing` (the pool needs no Host grant).
  - `ceiling_count`: a Delegator-stated Worker count is now read, so it
    also narrows that Worker's admission count.
- Tests: `tests/contract/test-issue-295-delegator-seats.py` updated
  (`devin/default` count 1 → class Worker group, `authorized_total` 7) and
  extended: uncounted Worker host grant stays pool; excluded Worker seat
  shows unavailable; Worker grant above an empty ceiling pool is omitted;
  counted Delegator Worker row is a seat; cross-check that the sum of
  counted `project --seats` grant groups equals the delegator
  `authorized_total`, covering the KPM shape (grok 2, cursor-cli 2,
  droid 1, devin 1, claude-shared 1).
- `docs/dispatch-collect.md`: the "Worker-pool presets are not seats"
  paragraph now states the rule — a counted Worker grant is a seat; the
  uncounted default pool is not. CHANGELOG Unreleased entry (dispatch CLI
  only; seats restart not required).
- `8f80644a`: post-v0.9.3 content-cycle opener (accepted-revision.json
  back to content stage + re-rendered bridge), required because base
  `106e360f` carries the v0.9.3 pin whose gate locks the tree to the pin
  paths (same convention as `a6af2d88`/`2a22c81b`).

## Candidate

- Commits `8f80644a` + `cbfab326` on `workflow/issue-297` (worktree
  `.kw/worktrees/issue-297`, base `106e360f`). Implemented by the
  `devin/opus-fusion` seat `devin-KPR-i297-worker-seats`; reviewed and
  finalized by the Host.

## Evidence

- Host diff review (this run): all four Expected behaviors and the
  #294 owner rules verified non-regressed (294 suite green).
- `./scripts/render-skills.py --check` — PASS.
- Affected suites, all exit 0: `test-issue-295-delegator-seats.py`
  (updated), `test-issue-294-expert-ceiling.py`,
  `test-issue-271-dispatch-help.py`, `test-issue-259-record-contract.py`,
  `test-issue-244-dispatch.py`, `test-issue-273-list-identity.py`
  (logs `/tmp/kpr-i297-*.log`).
- `.cache/final-validation.md`: verdict `pass`, candidate hash
  `971a970e9a909175…`.
- Worker seat exact-stopped after acceptance (`state: stopped`).

## Known failures / unverified scope

- Full inventory and per-platform live ACP smoke run once at the v0.9.4
  release boundary over the integrated candidate, per the run plan.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/dispatch-collect.md
- hosts/grok-bot/INSTALL.md
- hosts/grok-bot/bridge.json
- hosts/grok-bot/kaola-delegator.md
- scripts/kaola-dispatch.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/grok-bot/accepted-revision.json
- tests/contract/test-issue-295-delegator-seats.py

## Follow-Up Items

- #298 (absent-decision retire) is next in this run's frontier.

## Final readiness

Ready: candidate reviewed, affected scope green, validation recorded.
Proceed to sink (merge) and archive.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-297/finalization-summary.md
