# Finalization summary — issue-308

## Delivered

Fix for #308: a stale exited launchd job no longer blocks
`start --resume`, exact-stop/attest clean it, a slow big-session resume
is waited out correctly, and the owner's compaction question is answered
with evidence.

- `scripts/kaola-launchd-broker.py`: a one-shot job that is exited and
  owned by no live holder or agent is **stale** — `submit` reaps it
  before bootstrap and the on-demand `reconcile` route does the same; an
  exited job whose agent is still live is **not** reaped; a running job
  owned by another attempt still refuses, and the refusal names the
  reconcile route (#309 principle).
- `kaola-acp-holder.py` / `kaola-acp.py` / `kaola-locate.py`:
  `exact-stop` and `attest --intent resume` call the reap route (a bare
  attest does not). Resume wait = the manifest `session/new` base plus
  `KAOLA_RESUME_TOKENS / 10000` seconds (a 960 000-token session adds
  96 s), capped at 600 s; an explicit `KAOLA_RESUME_TIMEOUT` wins; the
  holder receives `--resume-timeout`. A `session/resume` success landing
  after the wait but inside the 20 s `RESUME_RECOVERY_GRACE` (holder
  still alive, and inside the broker ready window) rewrites the record
  to `ready` and appends `resume_recovered` — a slow-but-successful
  resume is no longer `resume-failed`/`holder-lost`.
- **Owner answer (documented in docs/api.md)**: the runner does not
  compact on resume and never calls `session/compact` while loading —
  the resume wait is the **load** wait; compaction is a turn-time
  behavior. The fix therefore allows time for the load (size-aware),
  which is where the 960k-token session was actually slow.
- Tests: `test-issue-308-resume-reconcile.py` (8 cases, 369 lines):
  stale exited job lets `start --resume` proceed; live foreign job
  refuses with the route; an exited job with a live agent is not reaped;
  exact-stop reaps; attest-intent-resume reaps and bare attest does not;
  late resume success recorded ready; in-wait resume is not a recovery;
  timeout configurable and size-aware.
- `docs/api.md` (+31) — reconcile routes and resume-wait semantics;
  CHANGELOG Unreleased — **Seats: restart required** (holder changed;
  broker and CLI are per-call).

## Candidate

- Implementation commit `53b6cf03` on `workflow/issue-308` (worktree
  `.kw/worktrees/issue-308`, base `4cb1acc7`). Implemented by the
  `grok/default` seat `grok-KPR-i308-broker-resume`; reviewed and
  finalized by the Host.

## Evidence

- Host diff review (this run): reap semantics verified honest (stale =
  exited + no live owner); late-success grace bounded and inside the
  broker window; the compaction answer matches the code paths.
- `./scripts/render-skills.py --check` — PASS.
- Affected suites, all exit 0: `test-issue-308-resume-reconcile.py`
  (new), `test-issue-244-dispatch.py`, `test-issue-162-upgrade-safety.py`,
  `test-issue-271-dispatch-help.py`, `test-issue-255-lifecycle-state.py`,
  `test-issue-289-dead-holder-stop.py` (logs `/tmp/kpr-i308-*.log`).
- `.cache/final-validation.md`: verdict `pass`, candidate hash
  `098ba861a539e012…`.
- Worker seat exact-stopped after acceptance (`state: stopped`).

## Known failures / unverified scope

- Full inventory after the last of the four issues, per the run plan.
  No release or install in this run (owner approval required). The
  Studio-side end-to-end (the actual VRPCadCore resume) validates at
  the owner's install step.

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
- scripts/kaola-launchd-broker.py
- scripts/kaola-locate.py
- scripts/validate.sh
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-launchd-broker.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-launchd-broker.py
- tests/contract/mock-acp-agent.py
- tests/contract/test-issue-308-resume-reconcile.py

## Follow-Up Items

- KPM mirror comment on KaolaBrother/kaola-project-manager#131 after
  merge; the owner's compaction question answered as a comment on #308
  by the Host.

## Final readiness

Ready: candidate reviewed, affected scope green, validation recorded.
Proceed to sink (merge) and archive.
